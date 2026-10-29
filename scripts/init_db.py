"""Create and seed the SQLite database.

Usage:
    python scripts/init_db.py            # create tables + seed categories, criteria and users if missing
    python scripts/init_db.py --reset    # delete the database file first, then recreate it
    python scripts/init_db.py --demo     # also create one demo evaluation per category (mock mode)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rfp import config, db  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="delete the existing database first")
    parser.add_argument("--demo", action="store_true", help="create demo evaluations from the sample proposals")
    args = parser.parse_args()

    path = config.db_path()
    if args.reset and path.exists():
        path.unlink()
        print(f"Deleted {path}")
    info = db.init_db()
    if info["backup"]:
        print(f"Old-format database backed up to {info['backup']}")
    print(f"Database ready at {path}\n")
    for cat in db.list_categories():
        print(cat["label"])
        for c in db.list_criteria(cat["category_id"]):
            print(f"     {c['name']:<36}{c['weight']:>6g}%  max {c['max_score']}{'' if c['is_active'] else '  (inactive)'}")
    if args.demo:
        from rfp.demo import seed_demo_runs

        ids = seed_demo_runs()
        print(f"\nCreated {len(ids)} demo evaluations: {', '.join(ids)}")
    print("\nSign in with evaluator / evaluator123 or reviewer / reviewer123 (unless set in secrets).")


if __name__ == "__main__":
    main()
