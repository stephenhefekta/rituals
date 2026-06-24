#!/bin/bash
# Install the Sunday/Friday ritual reminders as a launchd LaunchAgent.
# Safe to re-run — it reloads the agent in place.
set -e
cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"
NOTIFY="$SCRIPT_DIR/notify.py"
LABEL="com.rituals.reminder"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$NOTIFY</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Weekday</key><integer>0</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Month</key><integer>1</integer><key>Day</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Month</key><integer>4</integer><key>Day</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Month</key><integer>7</integer><key>Day</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Month</key><integer>10</integer><key>Day</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>StandardErrorPath</key>
  <string>/tmp/rituals-reminder.err</string>
  <key>StandardOutPath</key>
  <string>/tmp/rituals-reminder.out</string>
</dict>
</plist>
PLISTEOF

# Reload in place (bootout is a no-op the first time).
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Installed: reminders fire Sunday & Friday at 9:00am, plus the 1st of each"
echo "quarter (Jan/Apr/Jul/Oct), when that period's ritual isn't done yet."
echo "  Test now:  python3 \"$NOTIFY\""
echo "  Remove:    ./uninstall-reminders.sh"
