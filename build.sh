#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Installing build deps…"
python3 -m pip install -r requirements.txt pyinstaller --quiet

echo "Building .app…"
# Build from Rituals.spec so the supabase sub-packages (collected there) get
# bundled — the CLI-flag build can't discover them.
python3 -m PyInstaller Rituals.spec --noconfirm

echo ""
echo "Done: dist/Rituals.app"
echo "  Drag it to /Applications to install."
