from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# A thin static-file server for the desktop shell (main.py opens it in a native
# window). All data and auth happen client-side, straight to Supabase — see
# static/index.html — so there is no API layer or database code here.
app = FastAPI()

_STATIC = Path(__file__).parent / "static"

# PWA assets, served at the web root so the same paths work whether the UI is
# behind this server (desktop) or a static host (phone).
app.mount("/icons", StaticFiles(directory=_STATIC / "icons"), name="icons")


@app.get("/")
async def index():
    return HTMLResponse((_STATIC / "index.html").read_text())


@app.get("/manifest.json")
async def manifest():
    return FileResponse(_STATIC / "manifest.json", media_type="application/manifest+json")


@app.get("/sw.js")
async def service_worker():
    return FileResponse(_STATIC / "sw.js", media_type="text/javascript")
