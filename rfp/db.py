"""SQLite persistence layer.

Tables: categories, evaluation_criteria (per category), criteria_change_log (audit), users, audit_events,
rfp_runs, supplier_results, rfp_documents (original files for evidence snippets) and llm_cache.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from rfp import config
from rfp.catalog import CATEGORIES, category_label

SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username             TEXT NOT NULL UNIQUE,
    full_name            TEXT NOT NULL,
    role                 TEXT NOT NULL CHECK (role IN ('evaluator', 'senior_reviewer')),
    password_hash        TEXT NOT NULL,
    salt                 TEXT NOT NULL,
    password_set_by      TEXT NOT NULL DEFAULT 'seed',      -- 'seed' or 'user'
    password_changed_at  TEXT,
    is_active            INTEGER NOT NULL DEFAULT 1,
    created_at           TEXT NOT NULL
);

-- Logins, failed logins and password changes
CREATE TABLE IF NOT EXISTS audit_events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    success     INTEGER NOT NULL,
    detail      TEXT,
    event_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    category_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    code           TEXT NOT NULL UNIQUE,
    group_name     TEXT NOT NULL,
    name           TEXT NOT NULL,
    description    TEXT NOT NULL,
    icon           TEXT NOT NULL DEFAULT '📦',
    requires_note  INTEGER NOT NULL DEFAULT 0,
    sort_order     INTEGER NOT NULL DEFAULT 0,
    is_active      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS evaluation_criteria (
    criterion_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id   INTEGER NOT NULL REFERENCES categories(category_id),
    name          TEXT NOT NULL,
    description   TEXT NOT NULL,
    weight        REAL NOT NULL CHECK (weight >= 0 AND weight <= 100),
    max_score     INTEGER NOT NULL CHECK (max_score > 0),
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    updated_at    TEXT NOT NULL,
    updated_by    TEXT NOT NULL,
    UNIQUE (category_id, name)
);

CREATE TABLE IF NOT EXISTS criteria_change_log (
    change_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    change_batch_id  TEXT NOT NULL,
    category_id      INTEGER NOT NULL,
    criterion_id     INTEGER NOT NULL,
    criterion_name   TEXT NOT NULL,
    field_name       TEXT NOT NULL,
    old_value        TEXT,
    new_value        TEXT,
    changed_by       TEXT NOT NULL,
    changed_at       TEXT NOT NULL,
    reason           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rfp_runs (
    rfp_run_id              TEXT PRIMARY KEY,
    category_id             INTEGER REFERENCES categories(category_id),
    category_label          TEXT,
    category_note           TEXT,
    rfp_title               TEXT,
    rfp_reference           TEXT,
    created_at              TEXT NOT NULL,
    completed_at            TEXT,
    status                  TEXT NOT NULL,
    created_by              TEXT,
    llm_mode                TEXT,
    model                   TEXT,
    criteria_snapshot_json  TEXT,
    warnings_json           TEXT,
    run_json                TEXT,
    trace_json              TEXT
);

CREATE TABLE IF NOT EXISTS supplier_results (
    result_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    rfp_run_id          TEXT NOT NULL REFERENCES rfp_runs(rfp_run_id),
    supplier_name       TEXT NOT NULL,
    submission_date     TEXT NOT NULL,
    experience_rating   REAL NOT NULL,
    absolute_score      REAL,
    ppi                 REAL,
    final_rank          INTEGER,
    status              TEXT NOT NULL DEFAULT 'ranked',
    result_json         TEXT NOT NULL,
    UNIQUE (rfp_run_id, supplier_name)
);

-- Original supplier files, kept so reviewers can see the evidence in context
CREATE TABLE IF NOT EXISTS rfp_documents (
    document_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    rfp_run_id      TEXT NOT NULL REFERENCES rfp_runs(rfp_run_id),
    supplier_name   TEXT NOT NULL,
    file_name       TEXT NOT NULL,
    file_type       TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    size_bytes      INTEGER NOT NULL,
    pages           INTEGER,
    extracted_text  TEXT,
    file_bytes      BLOB NOT NULL,
    UNIQUE (rfp_run_id, supplier_name)
);

CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key       TEXT PRIMARY KEY,
    supplier_name   TEXT NOT NULL,
    model           TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    raw_response    TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_runs_category ON rfp_runs(category_id, created_at);
CREATE INDEX IF NOT EXISTS ix_results_run ON supplier_results(rfp_run_id);
"""

DEFAULT_USERS = [
    ("evaluator", "Procurement Evaluator", "evaluator", "EVALUATOR_PASSWORD", "evaluator123"),
    ("reviewer", "Senior Reviewer", "senior_reviewer", "REVIEWER_PASSWORD", "reviewer123"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = Path(path or config.db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =========================================================================================== setup
def _backup_old_database(path: Path) -> Path | None:
    """Databases from version 1 (no categories) are backed up and recreated."""
    if not path.exists():
        return None
    conn = sqlite3.connect(path)
    try:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        has_tables = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0] > 0
    finally:
        conn.close()
    if version >= SCHEMA_VERSION or not has_tables:
        return None
    backup = path.with_name(f"{path.stem}.v{version or 1}-backup-{datetime.now():%Y%m%d%H%M%S}{path.suffix}")
    shutil.move(str(path), str(backup))
    return backup


def init_db(path: Path | None = None) -> dict:
    """Create tables and seed categories, criteria and users if missing (idempotent)."""
    from rfp import auth  # local import avoids a cycle

    db_file = Path(path or config.db_path())
    backup = _backup_old_database(db_file)
    with connect(db_file) as conn:
        conn.executescript(SCHEMA)
        if "trace_json" not in {r[1] for r in conn.execute("PRAGMA table_info(rfp_runs)")}:
            conn.execute("ALTER TABLE rfp_runs ADD COLUMN trace_json TEXT")   # added in 2.1
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        ts = now_iso()
        for order, cat in enumerate(CATEGORIES):
            row = conn.execute("SELECT category_id FROM categories WHERE code = ?", (cat["code"],)).fetchone()
            if row:
                continue
            cur = conn.execute(
                "INSERT INTO categories (code, group_name, name, description, icon, requires_note, sort_order)"
                " VALUES (?,?,?,?,?,?,?)",
                (cat["code"], cat["group_name"], cat["name"], cat["description"], cat["icon"], cat["requires_note"],
                 order),
            )
            conn.executemany(
                "INSERT INTO evaluation_criteria (category_id, name, description, weight, max_score, is_active,"
                " updated_at, updated_by) VALUES (?, ?, ?, ?, ?, 1, ?, 'system-seed')",
                [(cur.lastrowid, n, d, w, m, ts) for n, d, w, m in cat["criteria"]],
            )
        for username, full_name, role, env_key, default_pw in DEFAULT_USERS:
            user = conn.execute("SELECT password_set_by FROM users WHERE username = ?", (username,)).fetchone()
            configured = config.get(env_key)
            if not user:
                pw_hash, salt = auth.hash_password(configured or default_pw)
                conn.execute(
                    "INSERT INTO users (username, full_name, role, password_hash, salt, created_at)"
                    " VALUES (?,?,?,?,?,?)",
                    (username, full_name, role, pw_hash, salt, ts),
                )
            elif configured and user["password_set_by"] == "seed":
                # a password from secrets applies until the user changes it in the app
                pw_hash, salt = auth.hash_password(configured)
                conn.execute("UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
                             (pw_hash, salt, username))
    return {"backup": str(backup) if backup else None}


# =========================================================================================== users & audit
def get_user(username: str, path: Path | None = None) -> dict | None:
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)).fetchone()
        return dict(row) if row else None


def set_password(username: str, pw_hash: str, salt: str, path: Path | None = None) -> None:
    with connect(path) as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ?, password_set_by = 'user', password_changed_at = ?"
            " WHERE username = ?",
            (pw_hash, salt, now_iso(), username),
        )


def log_event(username: str, event_type: str, success: bool, detail: str = "", path: Path | None = None) -> None:
    with connect(path) as conn:
        conn.execute(
            "INSERT INTO audit_events (username, event_type, success, detail, event_at) VALUES (?,?,?,?,?)",
            (username, event_type, int(success), detail, now_iso()),
        )


def list_events(limit: int = 200, path: Path | None = None) -> list[dict]:
    with connect(path) as conn:
        rows = conn.execute("SELECT * FROM audit_events ORDER BY event_id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


# =========================================================================================== categories
def list_categories(active_only: bool = True, path: Path | None = None) -> list[dict]:
    sql = "SELECT * FROM categories" + (" WHERE is_active = 1" if active_only else "") + " ORDER BY sort_order"
    with connect(path) as conn:
        cats = [dict(r) for r in conn.execute(sql).fetchall()]
    for c in cats:
        c["label"] = category_label(c)
    return cats


def get_category(category_id: int, path: Path | None = None) -> dict | None:
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM categories WHERE category_id = ?", (category_id,)).fetchone()
    if not row:
        return None
    cat = dict(row)
    cat["label"] = category_label(cat)
    return cat


def category_by_code(code: str, path: Path | None = None) -> dict | None:
    with connect(path) as conn:
        row = conn.execute("SELECT category_id FROM categories WHERE code = ?", (code,)).fetchone()
    return get_category(row[0], path) if row else None


# =========================================================================================== criteria
def list_criteria(category_id: int, active_only: bool = False, path: Path | None = None) -> list[dict]:
    sql = "SELECT * FROM evaluation_criteria WHERE category_id = ?"
    if active_only:
        sql += " AND is_active = 1"
    sql += " ORDER BY criterion_id"
    with connect(path) as conn:
        return [dict(r) for r in conn.execute(sql, (category_id,)).fetchall()]


def validate_criteria_set(criteria: list[dict]) -> list[str]:
    """Business rules for a criteria configuration. Returns a list of errors (empty = valid)."""
    errors: list[str] = []
    active = [c for c in criteria if int(c.get("is_active", 0)) == 1]
    if not active:
        errors.append("At least one criterion must be active.")
    total = round(sum(float(c["weight"]) for c in active), 6)
    if abs(total - 100.0) > 1e-6:
        errors.append(f"Active criteria weights must total 100%. Current total: {total:g}%.")
    names = [str(c["name"]).strip().lower() for c in criteria]
    if any(not n for n in names):
        errors.append("Every criterion needs a name.")
    if len(set(names)) != len(names):
        errors.append("Criterion names must be unique within a category.")
    for c in criteria:
        if not (0 <= float(c["weight"]) <= 100):
            errors.append(f"'{c['name']}': weight must be between 0 and 100.")
        if int(c["max_score"]) <= 0:
            errors.append(f"'{c['name']}': max score must be a positive integer.")
        if int(c.get("is_active", 0)) == 1 and float(c["weight"]) == 0:
            errors.append(f"'{c['name']}': an active criterion must have a weight above 0.")
        if not str(c.get("description", "")).strip():
            errors.append(f"'{c['name']}': description is required (it is sent to the LLM).")
    return errors


_TRACKED_FIELDS = ("name", "description", "weight", "max_score", "is_active")


def _norm(v: Any) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def save_criteria(category_id: int, new_criteria: list[dict], changed_by: str, reason: str,
                  path: Path | None = None) -> dict:
    """Apply a full criteria configuration for one category. Every field change is logged.

    Rows with criterion_id are updated, rows without are inserted. Criteria are never deleted
    (deactivate instead) so that historical runs stay traceable.
    """
    if not reason or not reason.strip():
        raise ValueError("A reason for the change is required.")
    errors = validate_criteria_set(new_criteria)
    if errors:
        raise ValueError(" ".join(errors))

    batch_id = uuid.uuid4().hex[:12]
    ts = now_iso()
    changes = 0
    log_sql = ("INSERT INTO criteria_change_log (change_batch_id, category_id, criterion_id, criterion_name, field_name,"
               " old_value, new_value, changed_by, changed_at, reason) VALUES (?,?,?,?,?,?,?,?,?,?)")
    with connect(path) as conn:
        current = {r["criterion_id"]: dict(r) for r in conn.execute(
            "SELECT * FROM evaluation_criteria WHERE category_id = ?", (category_id,)).fetchall()}
        for c in new_criteria:
            values = {
                "name": str(c["name"]).strip(),
                "description": str(c["description"]).strip(),
                "weight": float(c["weight"]),
                "max_score": int(c["max_score"]),
                "is_active": int(c["is_active"]),
            }
            cid = c.get("criterion_id")
            if cid is None or int(cid) not in current:
                cur = conn.execute(
                    "INSERT INTO evaluation_criteria (category_id, name, description, weight, max_score, is_active,"
                    " updated_at, updated_by) VALUES (?,?,?,?,?,?,?,?)",
                    (category_id, *values.values(), ts, changed_by),
                )
                conn.execute(log_sql, (batch_id, category_id, cur.lastrowid, values["name"], "created", None,
                                       json.dumps(values), changed_by, ts, reason.strip()))
                changes += 1
                continue
            old = current[int(cid)]
            diffs = [f for f in _TRACKED_FIELDS if _norm(old[f]) != _norm(values[f])]
            if not diffs:
                continue
            conn.execute(
                "UPDATE evaluation_criteria SET name=?, description=?, weight=?, max_score=?, is_active=?,"
                " updated_at=?, updated_by=? WHERE criterion_id=?",
                (*values.values(), ts, changed_by, int(cid)),
            )
            for f in diffs:
                conn.execute(log_sql, (batch_id, category_id, int(cid), values["name"], f, _norm(old[f]),
                                       _norm(values[f]), changed_by, ts, reason.strip()))
                changes += 1
    return {"change_batch_id": batch_id, "changes": changes}


def list_criteria_history(category_id: int | None = None, limit: int = 1000, path: Path | None = None) -> list[dict]:
    sql = ("SELECT l.*, c.group_name, c.name AS category_name FROM criteria_change_log l"
           " LEFT JOIN categories c ON c.category_id = l.category_id")
    args: tuple = ()
    if category_id is not None:
        sql += " WHERE l.category_id = ?"
        args = (category_id,)
    sql += " ORDER BY l.change_id DESC LIMIT ?"
    with connect(path) as conn:
        rows = [dict(r) for r in conn.execute(sql, (*args, limit)).fetchall()]
    for r in rows:
        r["category_label"] = category_label({"group_name": r["group_name"] or "", "name": r["category_name"] or ""})
    return rows


# =========================================================================================== runs & results
def create_run(rfp_run_id: str, created_by: str, llm_mode: str, model: str, category: dict, rfp_title: str,
               rfp_reference: str = "", category_note: str = "", path: Path | None = None) -> None:
    with connect(path) as conn:
        conn.execute(
            "INSERT INTO rfp_runs (rfp_run_id, category_id, category_label, category_note, rfp_title, rfp_reference,"
            " created_at, status, created_by, llm_mode, model) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (rfp_run_id, category["category_id"], category["label"], category_note, rfp_title, rfp_reference,
             now_iso(), "running", created_by, llm_mode, model),
        )


def finish_run(rfp_run_id: str, status: str, criteria_snapshot: list[dict], warnings: list[str],
               supplier_rows: list[dict], run_json: dict, path: Path | None = None) -> None:
    """Write all supplier results and close the run in a single transaction."""
    with connect(path) as conn:
        conn.execute("DELETE FROM supplier_results WHERE rfp_run_id = ?", (rfp_run_id,))
        for r in supplier_rows:
            conn.execute(
                "INSERT INTO supplier_results (rfp_run_id, supplier_name, submission_date, experience_rating,"
                " absolute_score, ppi, final_rank, status, result_json) VALUES (?,?,?,?,?,?,?,?,?)",
                (rfp_run_id, r["supplier_name"], r["submission_date"], r["experience_rating"],
                 r.get("absolute_score"), r.get("ppi"), r.get("final_rank"), r["status"],
                 json.dumps(r["result_json"])),
            )
        conn.execute(
            "UPDATE rfp_runs SET status=?, completed_at=?, criteria_snapshot_json=?, warnings_json=?, run_json=?"
            " WHERE rfp_run_id=?",
            (status, run_json.get("completed_at") or now_iso(), json.dumps(criteria_snapshot), json.dumps(warnings),
             json.dumps(run_json), rfp_run_id),
        )


def set_run_trace(rfp_run_id: str, trace: dict, path: Path | None = None) -> None:
    """Store LangSmith trace details on the run and inside its result JSON."""
    with connect(path) as conn:
        row = conn.execute("SELECT run_json FROM rfp_runs WHERE rfp_run_id = ?", (rfp_run_id,)).fetchone()
        run_json = json.loads(row[0]) if row and row[0] else None
        if run_json is not None:
            run_json["tracing"] = trace
        conn.execute("UPDATE rfp_runs SET trace_json = ?, run_json = COALESCE(?, run_json) WHERE rfp_run_id = ?",
                     (json.dumps(trace), json.dumps(run_json) if run_json is not None else None, rfp_run_id))


def fail_run(rfp_run_id: str, error: str, path: Path | None = None) -> None:
    with connect(path) as conn:
        conn.execute(
            "UPDATE rfp_runs SET status='failed', completed_at=?, warnings_json=? WHERE rfp_run_id=?",
            (now_iso(), json.dumps([error]), rfp_run_id),
        )


_RUN_LIST_SQL = """
SELECT r.rfp_run_id, r.category_id, r.category_label, r.category_note, r.rfp_title, r.rfp_reference,
       r.created_at, r.completed_at, r.status, r.created_by, r.llm_mode, r.model,
       (SELECT COUNT(*) FROM supplier_results s WHERE s.rfp_run_id = r.rfp_run_id AND s.status = 'ranked') AS ranked,
       (SELECT COUNT(*) FROM supplier_results s WHERE s.rfp_run_id = r.rfp_run_id AND s.status = 'excluded') AS excluded,
       (SELECT supplier_name FROM supplier_results s WHERE s.rfp_run_id = r.rfp_run_id AND final_rank = 1) AS winner,
       (SELECT ppi FROM supplier_results s WHERE s.rfp_run_id = r.rfp_run_id AND final_rank = 1) AS top_ppi,
       COALESCE(json_array_length(r.warnings_json), 0) AS warning_count,
       json_extract(r.trace_json, '$.url') AS trace_url,
       json_extract(r.trace_json, '$.trace_id') AS trace_id
FROM rfp_runs r
"""


def list_runs(limit: int = 200, category_id: int | None = None, path: Path | None = None) -> list[dict]:
    sql, args = _RUN_LIST_SQL, []
    if category_id is not None:
        sql += " WHERE r.category_id = ?"
        args.append(category_id)
    sql += " ORDER BY r.created_at DESC, r.rowid DESC LIMIT ?"
    args.append(limit)
    with connect(path) as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def get_run(rfp_run_id: str, path: Path | None = None) -> dict | None:
    with connect(path) as conn:
        run = conn.execute("SELECT * FROM rfp_runs WHERE rfp_run_id = ?", (rfp_run_id,)).fetchone()
        if not run:
            return None
        results = conn.execute(
            "SELECT * FROM supplier_results WHERE rfp_run_id = ? ORDER BY final_rank IS NULL, final_rank, supplier_name",
            (rfp_run_id,),
        ).fetchall()
    run = dict(run)
    run["results"] = [dict(r) for r in results]
    run["data"] = json.loads(run["run_json"]) if run.get("run_json") else None
    return run


def supplier_results_table(path: Path | None = None) -> list[dict]:
    """Flat table of every supplier result with its run and category (for dashboards)."""
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT s.rfp_run_id, s.supplier_name, s.submission_date, s.experience_rating, s.absolute_score, s.ppi,"
            " s.final_rank, s.status, r.category_id, r.category_label, r.rfp_title, r.created_at, r.status AS run_status"
            " FROM supplier_results s JOIN rfp_runs r ON r.rfp_run_id = s.rfp_run_id"
            " WHERE r.status != 'failed' ORDER BY r.created_at"
        ).fetchall()
        return [dict(r) for r in rows]


# =========================================================================================== documents
def save_documents(rfp_run_id: str, docs: list[dict], path: Path | None = None) -> None:
    with connect(path) as conn:
        for d in docs:
            conn.execute(
                "INSERT OR REPLACE INTO rfp_documents (rfp_run_id, supplier_name, file_name, file_type, sha256,"
                " size_bytes, pages, extracted_text, file_bytes) VALUES (?,?,?,?,?,?,?,?,?)",
                (rfp_run_id, d["supplier_name"], d["file_name"], d["file_type"], d["sha256"], len(d["file_bytes"]),
                 d.get("pages"), d.get("text"), sqlite3.Binary(d["file_bytes"])),
            )


def get_document(rfp_run_id: str, supplier_name: str, path: Path | None = None) -> dict | None:
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM rfp_documents WHERE rfp_run_id = ? AND supplier_name = ?",
                           (rfp_run_id, supplier_name)).fetchone()
        return dict(row) if row else None


# =========================================================================================== LLM cache
def cache_get(cache_key: str, path: Path | None = None) -> str | None:
    with connect(path) as conn:
        row = conn.execute("SELECT raw_response FROM llm_cache WHERE cache_key = ?", (cache_key,)).fetchone()
        return row[0] if row else None


def cache_put(cache_key: str, supplier_name: str, model: str, prompt_version: str, raw: str,
              path: Path | None = None) -> None:
    with connect(path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO llm_cache (cache_key, supplier_name, model, prompt_version, raw_response,"
            " created_at) VALUES (?,?,?,?,?,?)",
            (cache_key, supplier_name, model, prompt_version, raw, now_iso()),
        )
