#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Installing build deps…"
python3 -m pip install pywebview pyinstaller --quiet

echo "Building .app…"
python3 -m PyInstaller \
  --windowed \
  --name "Rituals" \
  --icon "icon.icns" \
  --add-data "static:static" \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.lifespan.on \
  --collect-all webview \
  --noconfirm \
  main.py

echo ""
echo "Done: dist/Rituals.app"
echo "  Drag it to /Applications to install."
