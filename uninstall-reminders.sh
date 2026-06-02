#!/bin/bash
# Remove the ritual reminders LaunchAgent.
LABEL="com.rituals.reminder"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$PLIST"
echo "Reminders removed."
