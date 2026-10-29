"""Orchestrator Agent: a LangGraph state machine that calls each tool/agent in the required order.

    load_criteria -> extract_documents -> evaluate_suppliers -> validate_scorecards
        -> score_absolute -> benchmark_peers -> rank_suppliers -> persist_results -> END
    (any step that leaves nothing to rank routes to fail_run -> END)

When LANGSMITH_API_KEY is set, every node, tool and LLM call is traced to LangSmith. Supplier files and the
OpenAI API key are kept outside the graph state, so they are never written to traces.
"""

import hashlib
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from rfp import config as settings
from rfp import db, llm
from rfp.agents import evaluation_agent
from rfp.llm import LLMSettings
from rfp.models import SupplierInput
from rfp.tracing import TracingSettings, run_context
from rfp.tools import document_tool, ranking_tool, validation_tool

AI_DISCLAIMER = (
    "AI-generated assessment. Criterion scores, justifications and evidence were produced by a large language "
    "model and can be incomplete or wrong. Check them against the source documents before making a procurement "
    "decision. Totals, benchmarks and rankings are calculated deterministically from these AI scores."
)
MOCK_DISCLAIMER = ("Mock mode: scores were produced by the offline simulator for demonstration, not by an AI "
                   "model. Do not use them for real decisions.")


class RunState(TypedDict, total=False):
    rfp_run_id: str
    created_by: str
    created_at: str
    category: dict
    rfp_title: str
    rfp_reference: str
    category_note: str
    llm: dict                      # mode + model only (no key)
    suppliers: list[dict]          # validated SupplierInput dicts without file bytes
    options: dict                  # use_cache, inject_malformed_for
    criteria: list[dict]
    documents: dict[str, dict]
    llm_outputs: dict[str, dict]
    scorecards: dict[str, dict]
    excluded: dict[str, str]
    scored: list[dict]
    benchmarks: dict[int, dict]
    peer_scored: list[dict]
    ranked: list[dict]
    tie_breaks: list[dict]
    warnings: list[str]
    events: list[dict]
    status: str
    error: str
    result: dict


# Per-run objects kept out of the (traced) graph state
_FILE_STORE: dict[str, dict[str, bytes]] = {}
_SETTINGS_STORE: dict[str, LLMSettings] = {}


# ------------------------------------------------------------------------------------------- helpers
def new_run_id() -> str:
    return f"RFP-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6].upper()}"


def validate_inputs(suppliers: list[dict], today: date | None = None
                    ) -> tuple[list[SupplierInput], list[str], dict[int, list[str]]]:
    """Validate the user's supplier rows before a batch is created.

    Returns (valid suppliers, general errors, errors per row index) - per-row errors are shown next to the row.
    """
    today = today or date.today()
    general: list[str] = []
    rows: dict[int, list[str]] = {}
    valid: list[SupplierInput] = []

    def add(i: int, msg: str) -> None:
        rows.setdefault(i, []).append(msg)

    if len(suppliers) < settings.MIN_SUPPLIERS:
        general.append(f"Add at least {settings.MIN_SUPPLIERS} suppliers; peer benchmarking needs more than one.")
    if len(suppliers) > settings.MAX_SUPPLIERS:
        general.append(f"A single evaluation can include at most {settings.MAX_SUPPLIERS} suppliers.")
    seen_names: dict[str, int] = {}
    seen_files: dict[str, int] = {}
    for i, s in enumerate(suppliers):
        name = " ".join(str(s.get("supplier_name") or "").split())
        if not name:
            add(i, "Enter the supplier name.")
        elif len(name) < 2 or not any(ch.isalpha() for ch in name):
            add(i, "Supplier name must be at least 2 characters and contain letters.")
        elif len(name) > 120:
            add(i, "Supplier name must be 120 characters or fewer.")
        sub = s.get("submission_date")
        if sub is None:
            add(i, "Choose the submission date.")
        else:
            sub = sub if isinstance(sub, date) else date.fromisoformat(str(sub))
            if sub > today:
                add(i, f"Submission date {sub} is in the future.")
            elif sub < today - timedelta(days=settings.MAX_SUBMISSION_AGE_DAYS):
                add(i, f"Submission date {sub} is more than {settings.MAX_SUBMISSION_AGE_DAYS} days ago.")
        rating = s.get("experience_rating")
        if rating is None or not (0 <= float(rating) <= 100):
            add(i, "Past performance rating must be between 0 and 100.")
        data, fname = s.get("file_bytes") or b"", s.get("file_name") or ""
        if not data:
            add(i, "Attach the supplier's proposal (PDF, DOCX or DOC).")
        else:
            _, file_errors = document_tool.check_file(fname, data)
            for e in file_errors:
                add(i, e)
            digest = hashlib.sha256(data).hexdigest()
            if digest in seen_files:
                add(i, f"Same file as row {seen_files[digest] + 1}.")
            else:
                seen_files[digest] = i
        if name:
            key = name.casefold()
            if key in seen_names:
                add(i, f"Supplier name is already used in row {seen_names[key] + 1}.")
            else:
                seen_names[key] = i
        if i not in rows:
            valid.append(SupplierInput(supplier_name=name, submission_date=sub, experience_rating=float(rating),
                                       file_name=fname, file_bytes=data))
    errors = general + [f"Row {i + 1}: {m}" for i, msgs in sorted(rows.items()) for m in msgs]
    return valid, errors, rows


def _event(state: RunState, step: str, message: str, level: str = "info") -> None:
    state.setdefault("events", []).append(
        {"at": datetime.now(timezone.utc).strftime("%H:%M:%S"), "step": step, "level": level, "message": message})


def _progress(config_: RunnableConfig | None, step: str, message: str, fraction: float) -> None:
    cb: Callable | None = ((config_ or {}).get("configurable") or {}).get("progress")
    if cb:
        cb(step, message, fraction)


def _remaining(state: RunState) -> list[dict]:
    excluded = state.get("excluded", {})
    return [s for s in state["suppliers"] if s["supplier_name"] not in excluded]


def _context(state: RunState) -> str:
    cat = state["category"]
    parts = [cat["label"]]
    if state.get("category_note"):
        parts.append(state["category_note"])
    parts.append(f"RFP: {state['rfp_title']}")
    return " | ".join(parts)


# ------------------------------------------------------------------------------------------- nodes
def load_criteria(state: RunState, config: RunnableConfig | None = None) -> RunState:
    _progress(config, "load_criteria", "Loading the category's active criteria", 0.05)
    criteria = db.list_criteria(state["category"]["category_id"], active_only=True)
    errors = db.validate_criteria_set(criteria)
    if errors:
        state["error"] = f"Criteria for {state['category']['label']} are invalid: " + " ".join(errors)
        _event(state, "load_criteria", state["error"], "error")
        return state
    state["criteria"] = criteria
    _event(state, "load_criteria", f"{len(criteria)} active criteria loaded for {state['category']['label']}.")
    return state


def extract_documents(state: RunState, config: RunnableConfig | None = None) -> RunState:
    docs, excluded = {}, state.setdefault("excluded", {})
    files = _FILE_STORE.get(state["rfp_run_id"], {})
    n = len(state["suppliers"])
    for i, s in enumerate(state["suppliers"]):
        name = s["supplier_name"]
        _progress(config, "extract_documents", f"Reading {s['file_name']}", 0.08 + 0.12 * i / n)
        try:
            d = document_tool.extract_text(files.get(name, b""), s["file_name"])
            docs[name] = d
            where = f"{d['pages']} pages" if d["pages"] else document_tool.TYPE_LABELS[d["file_type"]]
            _event(state, "extract_documents", f"{name}: {where}, {d['chars']:,} characters extracted.")
            if d["truncated"]:
                state["warnings"].append(
                    f"{name}: document truncated to {settings.MAX_DOC_CHARS:,} characters for the LLM.")
        except document_tool.DocumentError as exc:
            excluded[name] = str(exc)
            state["warnings"].append(f"{name}: excluded from ranking. {exc}")
            _event(state, "extract_documents", f"{name}: {exc}", "error")
    state["documents"] = docs
    return state


def evaluate_suppliers(state: RunState, config: RunnableConfig | None = None) -> RunState:
    outputs = {}
    opts = state.get("options", {})
    faulty = set(opts.get("inject_malformed_for", []))
    llm_settings = _SETTINGS_STORE.get(state["rfp_run_id"], LLMSettings())
    todo = _remaining(state)
    for i, s in enumerate(todo):
        name = s["supplier_name"]
        _progress(config, "evaluate_suppliers", f"Scoring {name} with {llm_settings.label}",
                  0.2 + 0.55 * i / max(1, len(todo)))
        try:
            out = evaluation_agent.evaluate(name, state["criteria"], state["documents"][name]["text"], llm_settings,
                                            use_cache=opts.get("use_cache", True), inject_malformed=name in faulty,
                                            context=_context(state))
            outputs[name] = out
            note = " (malformed output injected for demo)" if out["fault_injected"] else ""
            _event(state, "evaluate_suppliers", f"{name}: scored by {out['model']} [{out['source']}] "
                                                f"in {out['latency_s']}s{note}.")
        except Exception as exc:  # API/auth/network failure
            reason = llm.friendly_error(exc) if type(exc).__module__.startswith("openai") else str(exc)
            state["excluded"][name] = f"AI evaluation failed: {reason}"
            state["warnings"].append(f"{name}: excluded from ranking. AI evaluation failed: {reason}")
            _event(state, "evaluate_suppliers", f"{name}: AI evaluation failed ({reason}).", "error")
    state["llm_outputs"] = outputs
    return state


def validate_scorecards(state: RunState, config: RunnableConfig | None = None) -> RunState:
    _progress(config, "validate_scorecards", "Validating the AI output", 0.78)
    cards = {}
    for s in _remaining(state):
        name = s["supplier_name"]
        card = validation_tool.validate(state["llm_outputs"][name]["raw"], state["criteria"], name,
                                        state["documents"][name]["text"])
        cards[name] = card.model_dump()
        for w in card.validation_warnings:
            state["warnings"].append(f"{name}: {w}")
        _event(state, "validate_scorecards", f"{name}: {len(card.validation_warnings)} validation warning(s).",
               "warning" if card.validation_warnings else "info")
    state["scorecards"] = cards
    return state


def score_absolute(state: RunState, config: RunnableConfig | None = None) -> RunState:
    _progress(config, "score_absolute", "Calculating weighted scores", 0.82)
    entries = [{"supplier_name": s["supplier_name"], "submission_date": s["submission_date"].isoformat(),
                "experience_rating": float(s["experience_rating"]), "file_name": s["file_name"],
                "scorecard": state["scorecards"][s["supplier_name"]]} for s in _remaining(state)]
    state["scored"] = ranking_tool.compute_absolute_scores(entries, state["criteria"])
    _event(state, "score_absolute", "Absolute weighted scores calculated.")
    return state


def benchmark_peers(state: RunState, config: RunnableConfig | None = None) -> RunState:
    _progress(config, "benchmark_peers", "Benchmarking suppliers against each other", 0.86)
    state["benchmarks"] = ranking_tool.compute_benchmarks(state["scored"], state["criteria"])
    state["peer_scored"] = ranking_tool.compute_peer_metrics(state["scored"], state["benchmarks"])
    _event(state, "benchmark_peers", "Benchmarks, gaps, relative % and PPI calculated.")
    return state


def rank_suppliers(state: RunState, config: RunnableConfig | None = None) -> RunState:
    _progress(config, "rank_suppliers", "Ranking suppliers and applying tie-breaks", 0.9)
    state["ranked"], state["tie_breaks"] = ranking_tool.rank(state["peer_scored"])
    used = [t for t in state["tie_breaks"] if t["tie_break_used"]]
    _event(state, "rank_suppliers",
           f"{len(state['ranked'])} suppliers ranked; tie-break rules used {len(used)} time(s).")
    return state


def _build_result(state: RunState, status: str) -> dict:
    ranked = state.get("ranked", [])
    suppliers = []
    for r in ranked:
        name = r["supplier_name"]
        sc = r["scorecard"]
        out = state["llm_outputs"][name]
        suppliers.append({
            "final_rank": r["final_rank"], "supplier_name": name, "file_name": r["file_name"],
            "submission_date": r["submission_date"], "experience_rating": r["experience_rating"],
            "absolute_score": r["absolute_score"], "ppi": r["ppi"],
            "criteria": r["criteria_results"], "risks": sc["risks"], "overall_summary": sc["overall_summary"],
            "validation_warnings": sc["validation_warnings"],
            "document": {k: v for k, v in state["documents"][name].items() if k != "text"},
            "llm": {"source": out["source"], "model": out["model"], "fault_injected": out["fault_injected"],
                    "raw_response": out["raw"]},
        })
    by_name = {s["supplier_name"]: s for s in state["suppliers"]}
    mode = state["llm"]["mode"]
    return {
        "rfp_run_id": state["rfp_run_id"],
        "rfp_title": state["rfp_title"],
        "rfp_reference": state.get("rfp_reference", ""),
        "category": {"category_id": state["category"]["category_id"], "code": state["category"]["code"],
                     "label": state["category"]["label"], "note": state.get("category_note", "")},
        "created_at": state["created_at"],
        "completed_at": db.now_iso(),
        "status": status,
        "created_by": state.get("created_by"),
        "llm": {"mode": mode, "model": state["llm"]["model"], "prompt_version": settings.PROMPT_VERSION,
                "temperature": 0},
        "disclaimer": MOCK_DISCLAIMER if mode == "mock" else AI_DISCLAIMER,
        "tracing": {"enabled": False},
        "criteria_snapshot": [{k: c[k] for k in ("criterion_id", "name", "description", "weight", "max_score")}
                              for c in state.get("criteria", [])],
        "formulas": ranking_tool.FORMULAS,
        "tie_break_order": ranking_tool.TIE_BREAK_ORDER,
        "leaderboard": [{k: s[k] for k in ("final_rank", "supplier_name", "absolute_score", "ppi",
                                           "submission_date", "experience_rating")} for s in suppliers],
        "benchmarks": list(state.get("benchmarks", {}).values()),
        "tie_break_explanations": state.get("tie_breaks", []),
        "suppliers": suppliers,
        "excluded_suppliers": [
            {"supplier_name": n, "reason": reason, "file_name": by_name[n]["file_name"],
             "submission_date": by_name[n]["submission_date"].isoformat(),
             "experience_rating": float(by_name[n]["experience_rating"])}
            for n, reason in state.get("excluded", {}).items()],
        "warnings": state.get("warnings", []),
        "agent_log": state.get("events", []),
    }


def persist_results(state: RunState, config: RunnableConfig | None = None) -> RunState:
    _progress(config, "persist_results", "Saving results", 0.95)
    status = "completed_with_warnings" if state["warnings"] else "completed"
    _event(state, "persist_results", f"Run saved with status '{status}'.")
    result = _build_result(state, status)
    rows = [{"supplier_name": s["supplier_name"], "submission_date": s["submission_date"],
             "experience_rating": s["experience_rating"], "absolute_score": s["absolute_score"], "ppi": s["ppi"],
             "final_rank": s["final_rank"], "status": "ranked", "result_json": s} for s in result["suppliers"]]
    rows += [{"supplier_name": e["supplier_name"], "submission_date": e["submission_date"],
              "experience_rating": e["experience_rating"], "status": "excluded", "result_json": e}
             for e in result["excluded_suppliers"]]
    files = _FILE_STORE.get(state["rfp_run_id"], {})
    docs = []
    for s in state["suppliers"]:
        name = s["supplier_name"]
        d = state["documents"].get(name, {})
        data = files.get(name, b"")
        docs.append({"supplier_name": name, "file_name": s["file_name"],
                     "file_type": d.get("file_type") or document_tool.detect_type(data) or "unknown",
                     "sha256": hashlib.sha256(data).hexdigest(), "file_bytes": data, "pages": d.get("pages"),
                     "text": d.get("text")})
    db.save_documents(state["rfp_run_id"], docs)
    db.finish_run(state["rfp_run_id"], status, result["criteria_snapshot"], state["warnings"], rows, result)
    state["status"], state["result"] = status, result
    _progress(config, "done", "Evaluation complete", 1.0)
    return state


def fail_run(state: RunState, config: RunnableConfig | None = None) -> RunState:
    if not state.get("error"):
        state["error"] = "No supplier could be evaluated. " + " ".join(
            f"{n}: {r}" for n, r in state.get("excluded", {}).items())
    _event(state, "fail_run", state["error"], "error")
    db.fail_run(state["rfp_run_id"], state["error"])
    state["status"] = "failed"
    _progress(config, "failed", state["error"], 1.0)
    return state


# ------------------------------------------------------------------------------------------- graph
def _route_after_criteria(state: RunState) -> str:
    return "fail_run" if state.get("error") else "extract_documents"


def _route_if_any_left(next_node: str):
    def route(state: RunState) -> str:
        return next_node if _remaining(state) else "fail_run"
    return route


def build_graph():
    g = StateGraph(RunState)
    for name, fn in [("load_criteria", load_criteria), ("extract_documents", extract_documents),
                     ("evaluate_suppliers", evaluate_suppliers), ("validate_scorecards", validate_scorecards),
                     ("score_absolute", score_absolute), ("benchmark_peers", benchmark_peers),
                     ("rank_suppliers", rank_suppliers), ("persist_results", persist_results),
                     ("fail_run", fail_run)]:
        g.add_node(name, fn)
    g.add_edge(START, "load_criteria")
    g.add_conditional_edges("load_criteria", _route_after_criteria, ["extract_documents", "fail_run"])
    g.add_conditional_edges("extract_documents", _route_if_any_left("evaluate_suppliers"),
                            ["evaluate_suppliers", "fail_run"])
    g.add_conditional_edges("evaluate_suppliers", _route_if_any_left("validate_scorecards"),
                            ["validate_scorecards", "fail_run"])
    g.add_edge("validate_scorecards", "score_absolute")
    g.add_edge("score_absolute", "benchmark_peers")
    g.add_edge("benchmark_peers", "rank_suppliers")
    g.add_edge("rank_suppliers", "persist_results")
    g.add_edge("persist_results", END)
    g.add_edge("fail_run", END)
    return g.compile()


_GRAPH = None


def run_evaluation(suppliers: list[SupplierInput], created_by: str, category: dict, rfp_title: str, *,
                   rfp_reference: str = "", category_note: str = "", llm_settings: LLMSettings | None = None,
                   use_cache: bool = True, inject_malformed_for: list[str] | None = None,
                   progress: Callable[[str, str, float], Any] | None = None,
                   tracing: TracingSettings | None = None) -> RunState:
    """Create a batch (RFP_RUN_ID) and run the full workflow. Returns the final state."""
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    llm_settings = llm_settings or LLMSettings()
    run_id = new_run_id()
    db.create_run(run_id, created_by, llm_settings.mode, llm_settings.model if llm_settings.is_openai else
                  "mock-evaluator", category, rfp_title.strip(), rfp_reference.strip(), category_note.strip())
    state: RunState = {
        "rfp_run_id": run_id, "created_by": created_by, "created_at": db.now_iso(),
        "category": {k: category[k] for k in ("category_id", "code", "label")},
        "rfp_title": rfp_title.strip(), "rfp_reference": rfp_reference.strip(),
        "category_note": category_note.strip(),
        "llm": {"mode": llm_settings.mode,
                "model": llm_settings.model if llm_settings.is_openai else "mock-evaluator"},
        "suppliers": [s.model_dump(exclude={"file_bytes"}) for s in suppliers],
        "options": {"use_cache": use_cache, "inject_malformed_for": inject_malformed_for or []},
        "excluded": {}, "warnings": [], "events": [],
    }
    _FILE_STORE[run_id] = {s.supplier_name: s.file_bytes for s in suppliers}
    _SETTINGS_STORE[run_id] = llm_settings
    _event(state, "create_batch", f"Batch {run_id} created with {len(suppliers)} supplier(s) by {created_by}.")
    meta = {"rfp_run_id": run_id, "category": category["label"], "rfp_title": rfp_title.strip(),
            "llm_mode": llm_settings.mode, "model": state["llm"]["model"]}
    try:
        with run_context(tracing, f"RFP evaluation {run_id}", meta) as trace:
            run_config = {"configurable": {"progress": progress}, "run_name": f"RFP evaluation {run_id}",
                          "metadata": meta, "tags": ["rfp-evaluation", category["code"]]}
            if trace.get("trace_id"):
                run_config["run_id"] = trace["trace_id"]
            final = _GRAPH.invoke(state, config=run_config)
        final["tracing"] = trace
        db.set_run_trace(run_id, trace)
        if final.get("result") is not None:
            final["result"]["tracing"] = trace
        return final
    except Exception as exc:
        db.fail_run(run_id, f"Unexpected error: {exc}")
        raise
    finally:
        _FILE_STORE.pop(run_id, None)
        _SETTINGS_STORE.pop(run_id, None)


def graph_mermaid() -> str:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH.get_graph().draw_mermaid()
