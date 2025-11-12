import os
import sys
import socket
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uuid
from typing import Dict


def _resolve_assets_dir() -> Path:
    """Resolve the assets directory containing 'live2d' and 'vender'.

    Works in both dev and packaged (sys.frozen) environments.
    """
    # Packaged executable (Nuitka/pyinstaller style)
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent
        candidates = [
            base / "GUI" / "assets",
            base / "assets",
            Path(os.getcwd()) / "GUI" / "assets",
        ]
    else:
        # Development environment
        base = Path(__file__).parent
        candidates = [
            base / "assets",
            base.parent / "GUI" / "assets",
        ]

    for p in candidates:
        if p.exists():
            return p
    # Fallback to current working directory / GUI/assets
    return Path(os.getcwd()) / "GUI" / "assets"


assets_dir = _resolve_assets_dir()

app = FastAPI(title="LpkUnpacker Web Proxy")

# Mount static files at /static so relative paths in index.html (../vender/...) resolve to /static/vender/...
app.mount("/static", StaticFiles(directory=str(assets_dir), html=True), name="static")


@app.get("/")
def root():
    # Redirect to the Live2D index page under static mount
    return RedirectResponse(url="/static/live2d/index.html")


def _find_free_port(host: str = "127.0.0.1") -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_server(host: str = "127.0.0.1", port: int = 0) -> int:
    """Start uvicorn server as a daemon thread and return the actual port."""
    try:
        import uvicorn
    except ImportError:
        raise RuntimeError("uvicorn is required to start the web proxy. Please install 'uvicorn'.")

    actual_port = port or _find_free_port(host)
    config = uvicorn.Config(app, host=host, port=actual_port, log_level="info")
    server = uvicorn.Server(config)

    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    return actual_port


# ---------------- Dynamic model directory mounting ----------------

_mounted_models: Dict[str, Path] = {}

def mount_model_dir(dir_path: str) -> str:
    """Mount a local directory under a unique URL prefix and return the base path.

    Example return: "/model/06a1b7e0" so a file "model.json" becomes "/model/06a1b7e0/model.json".

    This allows loading a selected Live2D folder via HTTP, so the web UI can
    fetch JSON and related textures relative to the same base path.
    """
    p = Path(dir_path)
    if not p.exists() or not p.is_dir():
        raise ValueError(f"Model directory does not exist: {dir_path}")

    # Reuse existing mount if already mounted
    for mount_id, mounted_path in _mounted_models.items():
        if mounted_path.resolve() == p.resolve():
            return f"/model/{mount_id}"

    # Create a new unique mount id
    mount_id = uuid.uuid4().hex[:8]
    base_path = f"/model/{mount_id}"
    app.mount(base_path, StaticFiles(directory=str(p), html=False), name=f"model_{mount_id}")
    _mounted_models[mount_id] = p
    return base_path