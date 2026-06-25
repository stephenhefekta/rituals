import sys
import os
from pathlib import Path

# For PyInstaller bundles, resources live in sys._MEIPASS
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

import socket
import threading
import time
import urllib.request
import uvicorn
import webview
from app import app as fastapi_app


def _pick_port(preferred: int = 8011) -> int:
    # A stable port keeps the web origin constant, so the Supabase login session
    # (stored in localStorage, keyed by origin) survives across launches. Fall
    # back to a random free port only if the preferred one is already in use.
    s = socket.socket()
    try:
        s.bind(('127.0.0.1', preferred))
        return preferred
    except OSError:
        with socket.socket() as f:
            f.bind(('127.0.0.1', 0))
            return f.getsockname()[1]
    finally:
        s.close()


def _run_server(port: int):
    uvicorn.run(fastapi_app, host='127.0.0.1', port=port, log_level='error')


def main():
    port = _pick_port()
    threading.Thread(target=_run_server, args=(port,), daemon=True).start()

    # Wait up to ~4 s for server to accept connections
    url = f'http://127.0.0.1:{port}'
    for _ in range(30):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.15)

    webview.create_window('Focus', url, width=900, height=820, min_size=(640, 560))
    webview.start()


if __name__ == '__main__':
    main()
