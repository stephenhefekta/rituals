import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator

app = FastAPI()

# Disk-backed store in the user's home dir so the archive survives app rebuilds.
DATA_DIR = Path.home() / ".rituals"
DATA_FILE = DATA_DIR / "data.json"


# --------------------------------------------------------------------------- #
# Storage helpers
# --------------------------------------------------------------------------- #
def _load() -> dict:
    if not DATA_FILE.exists():
        return {"weeks": [], "wins": []}
    try:
        data = json.loads(DATA_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"weeks": [], "wins": []}
    # Tolerate older files written before a given ritual existed.
    data.setdefault("weeks", [])
    data.setdefault("wins", [])
    return data


def _save(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = DATA_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(DATA_FILE)


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
    data = _load()
    weeks = sorted(data["weeks"], key=lambda w: w["week_start"], reverse=True)
    return {"weeks": [_decorate(w) for w in weeks]}


@app.post("/api/weeks")
async def create_week(req: CreateWeek):
    try:
        start = _monday_of(date.fromisoformat(req.week_start))
    except ValueError:
        raise HTTPException(400, "Invalid week_start date.")

    wid = _week_id(start)
    data = _load()
    if any(w["id"] == wid for w in data["weeks"]):
        raise HTTPException(409, "Priorities for this week already exist.")

    week = {
        "id": wid,
        "week_start": start.isoformat(),
        "created_at": _now_iso(),
        "priorities": [
            {"text": t, "done": False, "done_at": None} for t in req.priorities
        ],
    }
    data["weeks"].append(week)
    _save(data)
    return _decorate(week)


def _find_week(data: dict, wid: str) -> dict:
    for w in data["weeks"]:
        if w["id"] == wid:
            return w
    raise HTTPException(404, "Week not found.")


@app.post("/api/weeks/{wid}/priorities/{idx}/toggle")
async def toggle_priority(wid: str, idx: int):
    data = _load()
    week = _find_week(data, wid)
    if not 0 <= idx < len(week["priorities"]):
        raise HTTPException(404, "Priority not found.")
    p = week["priorities"][idx]
    p["done"] = not p["done"]
    p["done_at"] = _now_iso() if p["done"] else None
    _save(data)
    return _decorate(week)


@app.patch("/api/weeks/{wid}/priorities/{idx}")
async def edit_priority(wid: str, idx: int, body: TextUpdate):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Priority text cannot be empty.")
    data = _load()
    week = _find_week(data, wid)
    if not 0 <= idx < len(week["priorities"]):
        raise HTTPException(404, "Priority not found.")
    week["priorities"][idx]["text"] = text
    _save(data)
    return _decorate(week)


@app.delete("/api/weeks/{wid}")
async def delete_week(wid: str):
    data = _load()
    before = len(data["weeks"])
    data["weeks"] = [w for w in data["weeks"] if w["id"] != wid]
    if len(data["weeks"]) == before:
        raise HTTPException(404, "Week not found.")
    _save(data)
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Weekly Win — one reflective win per week, captured on Friday
# --------------------------------------------------------------------------- #
@app.get("/api/wins")
async def list_wins():
    data = _load()
    wins = sorted(data["wins"], key=lambda w: w["week_start"], reverse=True)
    return {"wins": [_decorate_win(w) for w in wins]}


@app.post("/api/wins")
async def create_win(req: CreateWin):
    try:
        start = _monday_of(date.fromisoformat(req.week_start))
    except ValueError:
        raise HTTPException(400, "Invalid week_start date.")

    wid = _week_id(start)
    data = _load()
    if any(w["id"] == wid for w in data["wins"]):
        raise HTTPException(409, "A win for this week already exists.")

    win = {
        "id": wid,
        "week_start": start.isoformat(),
        "created_at": _now_iso(),
        "text": req.text,
    }
    data["wins"].append(win)
    _save(data)
    return _decorate_win(win)


def _find_win(data: dict, wid: str) -> dict:
    for w in data["wins"]:
        if w["id"] == wid:
            return w
    raise HTTPException(404, "Win not found.")


@app.patch("/api/wins/{wid}")
async def edit_win(wid: str, body: TextUpdate):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Win text cannot be empty.")
    data = _load()
    win = _find_win(data, wid)
    win["text"] = text
    _save(data)
    return _decorate_win(win)


@app.delete("/api/wins/{wid}")
async def delete_win(wid: str):
    data = _load()
    before = len(data["wins"])
    data["wins"] = [w for w in data["wins"] if w["id"] != wid]
    if len(data["wins"]) == before:
        raise HTTPException(404, "Win not found.")
    _save(data)
    return {"ok": True}
