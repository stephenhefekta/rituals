#!/bin/bash
# Build, sign, and install "Rituals Notifier.app" — the signed agent that posts
# the reminder banners (see RitualsNotifier.swift for why this exists).
#
# Output: ~/Applications/Rituals Notifier.app, which notify.py invokes.
set -euo pipefail
cd "$(dirname "$0")"

APP="Rituals Notifier.app"
ID="Developer ID Application: Stephen Hodges (5R9J54S3RW)"
ICON="../icon.icns"

echo "Compiling…"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
swiftc -O -framework UserNotifications -framework AppKit \
  -o "$APP/Contents/MacOS/RitualsNotifier" RitualsNotifier.swift

cp "$ICON" "$APP/Contents/Resources/applet.icns"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Rituals</string>
  <key>CFBundleDisplayName</key><string>Rituals</string>
  <key>CFBundleIdentifier</key><string>com.rituals.notifier</string>
  <key>CFBundleExecutable</key><string>RitualsNotifier</string>
  <key>CFBundleIconFile</key><string>applet</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSUIElement</key><true/>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
</dict>
</plist>
PLIST

echo "Signing…"
codesign --force --timestamp --options runtime --sign "$ID" "$APP"
codesign --verify --strict "$APP"

echo "Installing to ~/Applications…"
mkdir -p "$HOME/Applications"
rm -rf "$HOME/Applications/$APP"
cp -R "$APP" "$HOME/Applications/"
# Register with Launch Services so macOS resolves the bundle for click-to-open.
LSREGISTER=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
"$LSREGISTER" -f "$HOME/Applications/$APP" 2>/dev/null || true

# Keep the repo clean — the installed copy is what notify.py uses.
rm -rf "$APP"

echo ""
echo "Done: ~/Applications/$APP"
echo "  First reminder will ask once to allow notifications for \"Rituals\" — click Allow."
