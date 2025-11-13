import os
import sys
import socket
import threading
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uuid
from typing import Dict, Set


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
    # Redirect to the Live2D web page with embedded controls
    return RedirectResponse(url="/static/live2d/web.html")


def _find_free_port(host: str = "127.0.0.1") -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_server(host: str = "127.0.0.1", port: int = 0) -> int:
    """Start uvicorn server as a daemon thread and return the actual port.

    Uses a minimal logging configuration to avoid dynamic formatter imports
    (e.g., 'uvicorn.logging.DefaultFormatter') that can break in packaged builds.
    """
    try:
        import uvicorn
    except ImportError:
        raise RuntimeError("uvicorn is required to start the web proxy. Please install 'uvicorn'.")

    actual_port = port or _find_free_port(host)

    # Minimal logging config that relies only on stdlib logging.Formatter
    simple_log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": "%(levelname)s %(name)s: %(message)s"},
            "access": {"format": "%(levelname)s %(client_addr)s - \"%(request_line)s\" %(status_code)s"},
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "default"},
            "access": {"class": "logging.StreamHandler", "formatter": "access"},
        },
        "loggers": {
            "uvicorn": {"handlers": ["console"], "level": "INFO"},
            "uvicorn.error": {"handlers": ["console"], "level": "INFO"},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO"},
        },
    }

    config = uvicorn.Config(
        app,
        host=host,
        port=actual_port,
        log_level="info",
        log_config=simple_log_config,
    )
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


# ---------------- Preview message bus (WebSocket + HTTP broadcast) ----------------

_preview_clients: Set[WebSocket] = set()


@app.websocket("/ws/preview")
async def ws_preview(ws: WebSocket):
    await ws.accept()
    _preview_clients.add(ws)
    try:
        while True:
            # We don't expect messages from clients; just keep the connection alive
            await ws.receive_text()
    except WebSocketDisconnect:
        try:
            _preview_clients.remove(ws)
        except KeyError:
            pass


async def _broadcast_to_clients(message: dict):
    # Send to a snapshot of current clients to avoid set mutation issues
    dead_clients = []
    for ws in list(_preview_clients):
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead_clients.append(ws)
    # Cleanup dead clients
    for ws in dead_clients:
        try:
            _preview_clients.remove(ws)
        except KeyError:
            pass


@app.post("/api/preview/broadcast")
async def http_broadcast(request: Request):
    """Accept JSON and broadcast to all connected preview clients."""
    try:
        payload = await request.json()
    except Exception:
        payload = {"type": "error", "message": "Invalid JSON"}
    await _broadcast_to_clients(payload)
    return {"ok": True, "clients": len(_preview_clients)}