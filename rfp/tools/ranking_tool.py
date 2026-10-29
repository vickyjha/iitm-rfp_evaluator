"""Ranking Tool: deterministic scoring, peer benchmarking, tie-breaks and ranking. No LLM involved.

Formulas (criterion i, supplier s, weights in % summing to 100):
  normalised_i        = score_i / max_score_i
  weighted_points_i   = normalised_i x weight_i
  absolute_score      = sum(weighted_points_i)                                   (0-100)
  benchmark_i         = max over suppliers of score_i
  gap_i               = score_i - benchmark_i                                   (0 for leaders, else negative)
  relative_pct_i      = score_i / benchmark_i x 100;  = 100 when benchmark_i == 0 (nobody scored, nobody penalised)
  PPI                 = sum(relative_pct_i x weight_i) / sum(weight_i)          (0-100)

Ranking: stable sort on
  1) higher PPI (rounded to config.PPI_DECIMALS)  2) earlier submission date
  3) higher experience rating                     4) supplier name A-Z (case-insensitive)
then ranks 1..N are assigned in that order (no shared ranks).
"""
from __future__ import annotations

from datetime import date

from langsmith import traceable

from rfp import config

TIE_BREAK_ORDER = [
    "1) Higher Peer Performance Index (PPI) first",
    "2) Earlier submission date",
    "3) Higher historical experience rating",
    "4) Supplier name in ascending (A-Z) order",
]

FORMULAS = {
    "absolute_weighted_score": "sum over criteria of (score / max_score) x weight",
    "criterion_benchmark": "highest validated score for the criterion across all ranked suppliers",
    "criterion_gap": "supplier score - benchmark score (0 for the benchmark leader, otherwise negative)",
    "relative_performance_pct": "(supplier score / benchmark score) x 100; 100 when the benchmark is 0",
    "peer_performance_index": "sum(relative_pct x weight) / sum(weights)",
    "rounding": f"absolute score and PPI rounded to {config.PPI_DECIMALS} decimals before sorting",
}


def _r(x: float) -> float:
    return round(x + 0.0, config.SCORE_DECIMALS)


@traceable(name="ranking_tool.absolute_scores", run_type="tool")
def compute_absolute_scores(suppliers: list[dict], criteria: list[dict]) -> list[dict]:
    """suppliers: [{supplier_name, submission_date, experience_rating, scorecard: {criteria: [...]}}]."""
    weights = {int(c["criterion_id"]): float(c["weight"]) for c in criteria}
    out = []
    for s in suppliers:
        rows, total = [], 0.0
        for cr in s["scorecard"]["criteria"]:
            cid = int(cr["criterion_id"])
            normalised = cr["score"] / cr["max_score"]
            points = normalised * weights[cid]
            total += points
            rows.append({**cr, "weight": weights[cid], "normalised_score": _r(normalised),
                         "weighted_points": _r(points)})
        out.append({**s, "criteria_results": rows, "absolute_score": _r(total)})
    return out


@traceable(name="ranking_tool.benchmarks", run_type="tool")
def compute_benchmarks(scored: list[dict], criteria: list[dict]) -> dict[int, dict]:
    bench: dict[int, dict] = {}
    for c in criteria:
        cid = int(c["criterion_id"])
        scores = {s["supplier_name"]: next(r["score"] for r in s["criteria_results"] if r["criterion_id"] == cid)
                  for s in scored}
        best = max(scores.values()) if scores else 0.0
        bench[cid] = {
            "criterion_id": cid, "criterion_name": c["name"], "weight": float(c["weight"]),
            "max_score": int(c["max_score"]), "benchmark_score": best,
            "leaders": sorted([n for n, v in scores.items() if v == best], key=str.casefold),
        }
    return bench


@traceable(name="ranking_tool.peer_metrics", run_type="tool")
def compute_peer_metrics(scored: list[dict], benchmarks: dict[int, dict]) -> list[dict]:
    out = []
    for s in scored:
        rows, weighted_sum, weight_total = [], 0.0, 0.0
        for r in s["criteria_results"]:
            b = benchmarks[r["criterion_id"]]["benchmark_score"]
            rel = 100.0 if b == 0 else r["score"] / b * 100.0
            gap = r["score"] - b
            weighted_sum += rel * r["weight"]
            weight_total += r["weight"]
            rows.append({**r, "benchmark_score": b, "gap": _r(gap), "relative_pct": _r(rel),
                         "is_benchmark_leader": r["score"] == b,
                         "benchmark_note": "benchmark is 0: relative set to 100%" if b == 0 else ""})
        ppi = weighted_sum / weight_total if weight_total else 0.0
        out.append({**s, "criteria_results": rows, "ppi": round(ppi + 0.0, config.PPI_DECIMALS)})
    return out


def _as_date(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def sort_key(s: dict) -> tuple:
    return (-s["ppi"], _as_date(s["submission_date"]), -float(s["experience_rating"]),
            s["supplier_name"].casefold(), s["supplier_name"])


def explain_pair(a: dict, b: dict) -> dict:
    """Explain why supplier a is ranked directly above supplier b."""
    if a["ppi"] != b["ppi"]:
        rule, why = 1, f"higher PPI ({a['ppi']:.4f} vs {b['ppi']:.4f})"
    elif _as_date(a["submission_date"]) != _as_date(b["submission_date"]):
        rule, why = 2, f"equal PPI; earlier submission date ({a['submission_date']} vs {b['submission_date']})"
    elif float(a["experience_rating"]) != float(b["experience_rating"]):
        rule, why = 3, (f"equal PPI and submission date; higher experience rating "
                        f"({float(a['experience_rating']):g} vs {float(b['experience_rating']):g})")
    else:
        rule, why = 4, "equal PPI, submission date and experience rating; supplier name A-Z"
    return {"higher": a["supplier_name"], "lower": b["supplier_name"], "deciding_rule": rule,
            "tie_break_used": rule > 1, "explanation": f"{a['supplier_name']} ranks above {b['supplier_name']}: {why}."}


@traceable(name="ranking_tool.rank", run_type="tool")
def rank(peer_scored: list[dict]) -> tuple[list[dict], list[dict]]:
    ordered = sorted(peer_scored, key=sort_key)
    ranked = [{**s, "final_rank": i} for i, s in enumerate(ordered, start=1)]
    explanations = [explain_pair(ranked[i], ranked[i + 1]) for i in range(len(ranked) - 1)]
    return ranked, explanations


def run_all(suppliers: list[dict], criteria: list[dict]) -> dict:
    """Convenience wrapper used by tests: absolute -> benchmarks -> peer metrics -> rank."""
    scored = compute_absolute_scores(suppliers, criteria)
    bench = compute_benchmarks(scored, criteria)
    peer = compute_peer_metrics(scored, bench)
    ranked, explanations = rank(peer)
    return {"ranked": ranked, "benchmarks": bench, "tie_breaks": explanations}
