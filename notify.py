#!/usr/bin/env python3
"""Fire a macOS notification on ritual days — but only if that week's ritual
is still undone, so it never nags about something already completed.

Run by a launchd LaunchAgent (see install-reminders.sh) on Sunday and Friday
mornings. Deliberately pure stdlib so it runs under the system /usr/bin/python3
without the app's dependencies. The date logic mirrors app.py / index.html.
"""
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

DATA_FILE = Path.home() / ".rituals" / "data.json"

# terminal-notifier owns its own signed bundle, so notifications deliver
# reliably even when launchd (no foreground app) runs us. Resolved by absolute
# path because launchd's PATH won't include Homebrew's bin.
TERMINAL_NOTIFIER = next(
    (p for p in ("/opt/homebrew/bin/terminal-notifier",
                 "/usr/local/bin/terminal-notifier") if Path(p).exists()),
    None,
)


def _load() -> dict:
    try:
        data = json.loads(DATA_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {"weeks": [], "wins": []}
    data.setdefault("weeks", [])
    data.setdefault("wins", [])
    return data


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _week_id(monday: date) -> str:
    iso = monday.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _notify(title: str, message: str) -> None:
    if TERMINAL_NOTIFIER:
        # Clicking the banner opens the app (no-op if it isn't installed).
        subprocess.run(
            [TERMINAL_NOTIFIER, "-title", title, "-message", message,
             "-sound", "default", "-execute", "open -a Rituals"],
            check=False,
        )
        return
    # Fallback: AppleScript notification (unreliable under launchd on recent macOS).
    t = title.replace('"', '\\"')
    m = message.replace('"', '\\"')
    script = f'display notification "{m}" with title "{t}" sound name "Glass"'
    subprocess.run(["osascript", "-e", script], check=False)


def main() -> None:
    today = date.today()
    data = _load()
    wd = today.weekday()  # Mon=0 .. Sun=6

    # Test hook: `python3 notify.py sun` / `fri` forces that branch on any day,
    # still honouring the "already done?" check. No arg = real behaviour.
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if arg.startswith("sun"):
        wd = 6
    elif arg.startswith("fri"):
        wd = 4

    if wd == 6:  # Sunday — plan the week ahead (matches the app's Sunday shift)
        wid = _week_id(_monday_of(today + timedelta(days=1)))
        if not any(w.get("id") == wid for w in data["weeks"]):
            _notify("Rituals — Sunday", "Set your top 3 priorities for the week ahead.")
    elif wd == 4:  # Friday — capture this week's win
        wid = _week_id(_monday_of(today))
        if not any(w.get("id") == wid for w in data["wins"]):
            _notify("Rituals — Friday", "Capture this week's win before you wrap up.")


if __name__ == "__main__":
    main()
