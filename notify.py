#!/usr/bin/env python3
"""Fire a macOS notification on ritual days — but only if that period's ritual
is still undone, so it never nags about something already captured.

Run by a launchd LaunchAgent (see install-reminders.sh):
  * Sunday morning  — plan the week ahead
  * Friday morning  — capture this week's win
  * First of Jan/Apr/Jul/Oct — set the new quarter's 3 targets

Deliberately pure stdlib so it runs under the system /usr/bin/python3 without the
app's dependencies. The "already done?" check queries Supabase over its REST API
(the live store; the old ~/.rituals/data.json is no longer written to). The date
logic mirrors app.py / index.html.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

# "Rituals Notifier.app" is our own signed agent (notifier/RitualsNotifier.swift).
# It posts via the modern UserNotifications framework, so banners are branded
# "Rituals", render their text on current macOS, and open the app when clicked —
# none of which terminal-notifier 2.0.0's dead NSUserNotification path can do.
NOTIFIER = (Path.home() / "Applications" / "Rituals Notifier.app"
            / "Contents" / "MacOS" / "RitualsNotifier")

# .env locations, in precedence order (matches store.py: project dir first).
ENV_FILES = (Path(__file__).parent / ".env", Path.home() / ".rituals" / ".env")


# --------------------------------------------------------------------------- #
# Supabase "is this row already there?" check (pure stdlib)
# --------------------------------------------------------------------------- #
def _env(key: str) -> str | None:
    if os.environ.get(key):
        return os.environ[key]
    for f in ENV_FILES:
        try:
            for line in f.read_text().splitlines():
                line = line.strip()
                if line.startswith(f"{key}=") and not line.startswith("#"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            continue
    return None


def _exists(table: str, row_id: str) -> bool:
    """True if a row with this id is already in Supabase.

    On any uncertainty (no credentials, network error) returns False, so the
    reminder still fires — a rare redundant nudge beats a silently missed one.
    """
    url = _env("SUPABASE_URL")
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return False
    endpoint = (
        f"{url.rstrip('/')}/rest/v1/{table}"
        f"?id=eq.{urllib.parse.quote(row_id)}&select=id&limit=1"
    )
    req = urllib.request.Request(
        endpoint, headers={"apikey": key, "Authorization": f"Bearer {key}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            rows = json.loads(resp.read().decode())
            return bool(rows)
    except (urllib.error.URLError, ValueError, OSError):
        return False


# --------------------------------------------------------------------------- #
# Date helpers (mirror app.py)
# --------------------------------------------------------------------------- #
def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _week_id(monday: date) -> str:
    iso = monday.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _quarter_start(d: date) -> date:
    return date(d.year, ((d.month - 1) // 3) * 3 + 1, 1)


def _quarter_id(quarter_start: date) -> str:
    return f"{quarter_start.year}-Q{(quarter_start.month - 1) // 3 + 1}"


# --------------------------------------------------------------------------- #
# Notification
# --------------------------------------------------------------------------- #
def _notify(title: str, message: str) -> None:
    if NOTIFIER.exists():
        # The agent runs an NSApplication that posts the notification and waits
        # briefly for a click (it self-exits via its own safety-net timeout).
        subprocess.run([str(NOTIFIER), title, message], check=False)
        return

    # Fallback if the notifier app isn't installed: osascript still renders text
    # on modern macOS, though the banner is branded "Script Editor" and clicking
    # it won't open Rituals.
    t = title.replace('\\', '\\\\').replace('"', '\\"')
    m = message.replace('\\', '\\\\').replace('"', '\\"')
    script = f'display notification "{m}" with title "{t}" sound name "Glass"'
    subprocess.run(["osascript", "-e", script], check=False)


def main() -> None:
    today = date.today()
    wd = today.weekday()  # Mon=0 .. Sun=6

    # Test hooks: `notify.py sun|fri|qtr` force that branch on any day, still
    # honouring the "already done?" check. No arg = real calendar behaviour.
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if arg.startswith("sun"):
        wd = 6
    elif arg.startswith("fri"):
        wd = 4
    force_quarter = arg.startswith("q")

    # Quarterly — first morning of a calendar quarter (Jan/Apr/Jul/Oct 1).
    if force_quarter or (today.day == 1 and today.month in (1, 4, 7, 10)):
        qstart = _quarter_start(today)
        if not _exists("quarters", _quarter_id(qstart)):
            q = (qstart.month - 1) // 3 + 1
            _notify("Rituals — New quarter",
                    f"Set your 3 targets for Q{q} {qstart.year}.")

    if wd == 6:  # Sunday — plan the week ahead (matches the app's Sunday shift)
        wid = _week_id(_monday_of(today + timedelta(days=1)))
        if not _exists("weeks", wid):
            _notify("Rituals — Sunday", "Set your top 3 priorities for the week ahead.")
    elif wd == 4:  # Friday — capture this week's win
        wid = _week_id(_monday_of(today))
        if not _exists("wins", wid):
            _notify("Rituals — Friday", "Capture this week's win before you wrap up.")


if __name__ == "__main__":
    main()
