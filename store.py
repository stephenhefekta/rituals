"""Supabase-backed storage for Rituals.

All week/win persistence goes through this module so the API layer in app.py
stays thin. Credentials come from the environment (see .env / .env.example).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from supabase import Client, create_client

# Load a local .env if python-dotenv is available; it's optional in production
# environments where the vars are already exported.
try:
    from dotenv import load_dotenv

    # Project-local .env for dev runs, plus ~/.rituals/.env so the packaged
    # .app (whose own files live read-only inside the bundle) can be configured.
    load_dotenv(Path(__file__).parent / ".env")
    load_dotenv(Path.home() / ".rituals" / ".env")
except ImportError:  # pragma: no cover
    pass


class StoreError(Exception):
    """Raised when the cloud database can't be reached or returns an error."""


@lru_cache(maxsize=1)
def _client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise StoreError(
            "Supabase is not configured. Set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY (see .env.example)."
        )
    return create_client(url, key)


def _run(fn):
    """Run a Supabase call, normalising any failure into StoreError."""
    try:
        return fn()
    except StoreError:
        raise
    except Exception as exc:  # network errors, postgrest errors, etc.
        raise StoreError(str(exc)) from exc


# --------------------------------------------------------------------------- #
# Weeks
# --------------------------------------------------------------------------- #
def get_weeks() -> list[dict]:
    res = _run(lambda: _client().table("weeks").select("*").execute())
    return res.data or []


def get_week(wid: str) -> dict | None:
    res = _run(
        lambda: _client().table("weeks").select("*").eq("id", wid).limit(1).execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def insert_week(week: dict) -> dict:
    res = _run(lambda: _client().table("weeks").insert(week).execute())
    return res.data[0]


def update_week_priorities(wid: str, priorities: list[dict]) -> dict:
    res = _run(
        lambda: _client()
        .table("weeks")
        .update({"priorities": priorities})
        .eq("id", wid)
        .execute()
    )
    return res.data[0]


def delete_week(wid: str) -> bool:
    res = _run(
        lambda: _client().table("weeks").delete().eq("id", wid).execute()
    )
    return bool(res.data)


# --------------------------------------------------------------------------- #
# Wins
# --------------------------------------------------------------------------- #
def get_wins() -> list[dict]:
    res = _run(lambda: _client().table("wins").select("*").execute())
    return res.data or []


def get_win(wid: str) -> dict | None:
    res = _run(
        lambda: _client().table("wins").select("*").eq("id", wid).limit(1).execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def insert_win(win: dict) -> dict:
    res = _run(lambda: _client().table("wins").insert(win).execute())
    return res.data[0]


def update_win_text(wid: str, text: str) -> dict:
    res = _run(
        lambda: _client()
        .table("wins")
        .update({"text": text})
        .eq("id", wid)
        .execute()
    )
    return res.data[0]


def delete_win(wid: str) -> bool:
    res = _run(lambda: _client().table("wins").delete().eq("id", wid).execute())
    return bool(res.data)


# --------------------------------------------------------------------------- #
# Quarters
# --------------------------------------------------------------------------- #
def get_quarters() -> list[dict]:
    res = _run(lambda: _client().table("quarters").select("*").execute())
    return res.data or []


def get_quarter(qid: str) -> dict | None:
    res = _run(
        lambda: _client().table("quarters").select("*").eq("id", qid).limit(1).execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def insert_quarter(quarter: dict) -> dict:
    res = _run(lambda: _client().table("quarters").insert(quarter).execute())
    return res.data[0]


def update_quarter_targets(qid: str, targets: list[dict]) -> dict:
    res = _run(
        lambda: _client()
        .table("quarters")
        .update({"targets": targets})
        .eq("id", qid)
        .execute()
    )
    return res.data[0]


def delete_quarter(qid: str) -> bool:
    res = _run(
        lambda: _client().table("quarters").delete().eq("id", qid).execute()
    )
    return bool(res.data)
