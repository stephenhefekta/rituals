"""One-time migration: push the local ~/.rituals/data.json into Supabase.

Usage:
    python migrate.py            # migrate, skipping rows that already exist
    python migrate.py --force    # overwrite rows that already exist in Supabase

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (see .env). Run schema.sql
in your Supabase project first so the tables exist.
"""
import json
import sys
from pathlib import Path

import store

DATA_FILE = Path.home() / ".rituals" / "data.json"


def main() -> None:
    force = "--force" in sys.argv

    if not DATA_FILE.exists():
        print(f"No local data found at {DATA_FILE} — nothing to migrate.")
        return

    data = json.loads(DATA_FILE.read_text())
    weeks = data.get("weeks", [])
    wins = data.get("wins", [])

    existing_weeks = {w["id"] for w in store.get_weeks()}
    existing_wins = {w["id"] for w in store.get_wins()}

    w_added = w_skipped = 0
    for week in weeks:
        if week["id"] in existing_weeks and not force:
            w_skipped += 1
            continue
        row = {
            "id": week["id"],
            "week_start": week["week_start"],
            "created_at": week["created_at"],
            "priorities": week.get("priorities", []),
        }
        if week["id"] in existing_weeks:
            store.update_week_priorities(week["id"], row["priorities"])
        else:
            store.insert_week(row)
        w_added += 1

    n_added = n_skipped = 0
    for win in wins:
        if win["id"] in existing_wins and not force:
            n_skipped += 1
            continue
        row = {
            "id": win["id"],
            "week_start": win["week_start"],
            "created_at": win["created_at"],
            "text": win["text"],
        }
        if win["id"] in existing_wins:
            store.update_win_text(win["id"], row["text"])
        else:
            store.insert_win(row)
        n_added += 1

    print(
        f"Weeks: {w_added} written, {w_skipped} skipped (already present).\n"
        f"Wins:  {n_added} written, {n_skipped} skipped (already present)."
    )
    if (w_skipped or n_skipped) and not force:
        print("Re-run with --force to overwrite the skipped rows.")


if __name__ == "__main__":
    main()
