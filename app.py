from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, field_validator

import store
from store import StoreError

app = FastAPI()


@app.exception_handler(StoreError)
async def _store_error_handler(request: Request, exc: StoreError):
    # The cloud database is unreachable or misconfigured. Surface a clear
    # error rather than silently falling back — the data lives in Supabase.
    return JSONResponse(
        status_code=503,
        content={"detail": f"Could not reach the cloud database: {exc}"},
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _monday_of(d: date) -> date:
    """The Monday that starts the week containing d."""
    return d - timedelta(days=d.weekday())


def _week_id(week_start: date) -> str:
    """Stable ISO id like '2026-W23' used to prevent duplicate weeks."""
    iso = week_start.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _week_label(week_start: date) -> str:
    end = week_start + timedelta(days=6)
    if week_start.month == end.month:
        return f"{week_start.strftime('%b')} {week_start.day}–{end.day}, {end.year}"
    return f"{week_start.strftime('%b %-d')} – {end.strftime('%b %-d, %Y')}"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _decorate(week: dict) -> dict:
    """Add derived display fields without mutating stored data."""
    start = date.fromisoformat(week["week_start"])
    out = dict(week)
    out["label"] = _week_label(start)
    out["done_count"] = sum(1 for p in week["priorities"] if p.get("done"))
    out["total"] = len(week["priorities"])
    return out


def _decorate_win(win: dict) -> dict:
    """Add the human-friendly week label to a stored win."""
    start = date.fromisoformat(win["week_start"])
    out = dict(win)
    out["label"] = _week_label(start)
    return out


def _quarter_start(d: date) -> date:
    """First day of the calendar quarter containing d (Q1=Jan, Q2=Apr, …)."""
    q = (d.month - 1) // 3  # 0..3
    return date(d.year, q * 3 + 1, 1)


def _quarter_id(quarter_start: date) -> str:
    """Stable id like '2026-Q2' used to prevent duplicate quarters."""
    return f"{quarter_start.year}-Q{(quarter_start.month - 1) // 3 + 1}"


def _quarter_label(quarter_start: date) -> str:
    q = (quarter_start.month - 1) // 3 + 1
    end_month = quarter_start.month + 2
    months = (
        f"{quarter_start.strftime('%b')}–{date(quarter_start.year, end_month, 1).strftime('%b')}"
    )
    return f"Q{q} {quarter_start.year} · {months}"


def _decorate_quarter(quarter: dict) -> dict:
    """Add derived display fields without mutating stored data."""
    start = date.fromisoformat(quarter["quarter_start"])
    out = dict(quarter)
    out["label"] = _quarter_label(start)
    out["done_count"] = sum(1 for t in quarter["targets"] if t.get("done"))
    out["total"] = len(quarter["targets"])
    return out


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class CreateWeek(BaseModel):
    week_start: str  # ISO date; any day in the target week is fine
    priorities: List[str]

    @field_validator("priorities")
    @classmethod
    def _exactly_three(cls, v: List[str]) -> List[str]:
        cleaned = [p.strip() for p in v if p and p.strip()]
        if len(cleaned) != 3:
            raise ValueError("Provide exactly 3 non-empty priorities.")
        return cleaned


class CreateQuarter(BaseModel):
    quarter_start: str  # ISO date; any day in the target quarter is fine
    targets: List[str]

    @field_validator("targets")
    @classmethod
    def _exactly_three(cls, v: List[str]) -> List[str]:
        cleaned = [t.strip() for t in v if t and t.strip()]
        if len(cleaned) != 3:
            raise ValueError("Provide exactly 3 non-empty targets.")
        return cleaned


class TextUpdate(BaseModel):
    text: str


class CreateWin(BaseModel):
    week_start: str  # ISO date; any day in the target week is fine
    text: str

    @field_validator("text")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Win text cannot be empty.")
        return cleaned


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/")
async def index():
    html = (Path(__file__).parent / "static" / "index.html").read_text()
    return HTMLResponse(html)


@app.get("/api/weeks")
async def list_weeks():
    weeks = sorted(store.get_weeks(), key=lambda w: w["week_start"], reverse=True)
    return {"weeks": [_decorate(w) for w in weeks]}


@app.post("/api/weeks")
async def create_week(req: CreateWeek):
    try:
        start = _monday_of(date.fromisoformat(req.week_start))
    except ValueError:
        raise HTTPException(400, "Invalid week_start date.")

    wid = _week_id(start)
    if store.get_week(wid) is not None:
        raise HTTPException(409, "Priorities for this week already exist.")

    week = {
        "id": wid,
        "week_start": start.isoformat(),
        "created_at": _now_iso(),
        "priorities": [
            {"text": t, "done": False, "done_at": None} for t in req.priorities
        ],
    }
    return _decorate(store.insert_week(week))


def _require_week(wid: str) -> dict:
    week = store.get_week(wid)
    if week is None:
        raise HTTPException(404, "Week not found.")
    return week


@app.post("/api/weeks/{wid}/priorities/{idx}/toggle")
async def toggle_priority(wid: str, idx: int):
    week = _require_week(wid)
    if not 0 <= idx < len(week["priorities"]):
        raise HTTPException(404, "Priority not found.")
    p = week["priorities"][idx]
    p["done"] = not p["done"]
    p["done_at"] = _now_iso() if p["done"] else None
    return _decorate(store.update_week_priorities(wid, week["priorities"]))


@app.patch("/api/weeks/{wid}/priorities/{idx}")
async def edit_priority(wid: str, idx: int, body: TextUpdate):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Priority text cannot be empty.")
    week = _require_week(wid)
    if not 0 <= idx < len(week["priorities"]):
        raise HTTPException(404, "Priority not found.")
    week["priorities"][idx]["text"] = text
    return _decorate(store.update_week_priorities(wid, week["priorities"]))


@app.delete("/api/weeks/{wid}")
async def delete_week(wid: str):
    if not store.delete_week(wid):
        raise HTTPException(404, "Week not found.")
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Weekly Win — one reflective win per week, captured on Friday
# --------------------------------------------------------------------------- #
@app.get("/api/wins")
async def list_wins():
    wins = sorted(store.get_wins(), key=lambda w: w["week_start"], reverse=True)
    return {"wins": [_decorate_win(w) for w in wins]}


@app.post("/api/wins")
async def create_win(req: CreateWin):
    try:
        start = _monday_of(date.fromisoformat(req.week_start))
    except ValueError:
        raise HTTPException(400, "Invalid week_start date.")

    wid = _week_id(start)
    if store.get_win(wid) is not None:
        raise HTTPException(409, "A win for this week already exists.")

    win = {
        "id": wid,
        "week_start": start.isoformat(),
        "created_at": _now_iso(),
        "text": req.text,
    }
    return _decorate_win(store.insert_win(win))


@app.patch("/api/wins/{wid}")
async def edit_win(wid: str, body: TextUpdate):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Win text cannot be empty.")
    if store.get_win(wid) is None:
        raise HTTPException(404, "Win not found.")
    return _decorate_win(store.update_win_text(wid, text))


@app.delete("/api/wins/{wid}")
async def delete_win(wid: str):
    if not store.delete_win(wid):
        raise HTTPException(404, "Win not found.")
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Quarterly targets — three goals per calendar quarter
# --------------------------------------------------------------------------- #
@app.get("/api/quarters")
async def list_quarters():
    quarters = sorted(
        store.get_quarters(), key=lambda q: q["quarter_start"], reverse=True
    )
    return {"quarters": [_decorate_quarter(q) for q in quarters]}


@app.post("/api/quarters")
async def create_quarter(req: CreateQuarter):
    try:
        start = _quarter_start(date.fromisoformat(req.quarter_start))
    except ValueError:
        raise HTTPException(400, "Invalid quarter_start date.")

    qid = _quarter_id(start)
    if store.get_quarter(qid) is not None:
        raise HTTPException(409, "Targets for this quarter already exist.")

    quarter = {
        "id": qid,
        "quarter_start": start.isoformat(),
        "created_at": _now_iso(),
        "targets": [
            {"text": t, "done": False, "done_at": None} for t in req.targets
        ],
    }
    return _decorate_quarter(store.insert_quarter(quarter))


def _require_quarter(qid: str) -> dict:
    quarter = store.get_quarter(qid)
    if quarter is None:
        raise HTTPException(404, "Quarter not found.")
    return quarter


@app.post("/api/quarters/{qid}/targets/{idx}/toggle")
async def toggle_target(qid: str, idx: int):
    quarter = _require_quarter(qid)
    if not 0 <= idx < len(quarter["targets"]):
        raise HTTPException(404, "Target not found.")
    t = quarter["targets"][idx]
    t["done"] = not t["done"]
    t["done_at"] = _now_iso() if t["done"] else None
    return _decorate_quarter(store.update_quarter_targets(qid, quarter["targets"]))


@app.patch("/api/quarters/{qid}/targets/{idx}")
async def edit_target(qid: str, idx: int, body: TextUpdate):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Target text cannot be empty.")
    quarter = _require_quarter(qid)
    if not 0 <= idx < len(quarter["targets"]):
        raise HTTPException(404, "Target not found.")
    quarter["targets"][idx]["text"] = text
    return _decorate_quarter(store.update_quarter_targets(qid, quarter["targets"]))


@app.delete("/api/quarters/{qid}")
async def delete_quarter(qid: str):
    if not store.delete_quarter(qid):
        raise HTTPException(404, "Quarter not found.")
    return {"ok": True}
