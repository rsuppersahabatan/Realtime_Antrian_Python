import os
import sys
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_socketio import SocketManager

# ---------------------------------------------------------------------------
# Ensure the server directory is in sys.path so modules can be imported
# when running via: python app.py  OR  uvicorn app:app
# ---------------------------------------------------------------------------
_server_dir = os.path.dirname(os.path.abspath(__file__))
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

# ---------------------------------------------------------------------------
# Import routers from modules
# ---------------------------------------------------------------------------
from modules.antrian import router as antrian_router
from modules.auth import router as auth_router
from modules.layanan import router as layanan_router
from modules.loket import router as loket_router
from modules.users import router as users_router
from modules.groups import router as groups_router
from modules.client import router as client_router
from modules.panggilan import router as panggilan_router
from modules.tts import router as tts_router, setup_tts

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
APP_TITLE = "Realtime Antrian API - Python & ReactJS"
APP_VERSION = "0.3.0"
APP_DESCRIPTION = (
    "REST API + Socket.IO backend untuk sistem antrian rumah sakit.\n\n"
    "**Modul:** Auth · Antrian · Layanan · Loket · Users · Groups · Client · Panggilan · TTS"
)

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — sesuaikan origins jika sudah production
# ---------------------------------------------------------------------------
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "*"   # Development: izinkan semua. Ganti dengan domain spesifik di production.
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Socket.IO — instance disimpan di app.state agar bisa diakses dari router
# ---------------------------------------------------------------------------
# Engine.IO punya CORS check terpisah dari FastAPI's CORSMiddleware.
# Wildcard harus passed sebagai string '*', bukan list ['*']
# (list di-match strict-equality, jadi origin "http://x" tidak match "*").
_SIO_CORS = "*" if "*" in CORS_ORIGINS else CORS_ORIGINS
sio_manager = SocketManager(app=app, cors_allowed_origins=_SIO_CORS)
app.state.sio = sio_manager

@app.sio.on("connect")
async def handle_connect(sid, environ):
    print(f"[SocketIO] Client connected: {sid}")

@app.sio.on("disconnect")
async def handle_disconnect(sid):
    print(f"[SocketIO] Client disconnected: {sid}")

@app.sio.on("message")
async def handle_message(sid, data):
    """Echo balik pesan dari client (opsional / debugging)."""
    await sio_manager.emit("message", data)

# ---------------------------------------------------------------------------
# TTS — pasang slowapi limiter & exception handler sebelum register router
# ---------------------------------------------------------------------------
setup_tts(app)

# ---------------------------------------------------------------------------
# Register API routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(antrian_router)
app.include_router(layanan_router)
app.include_router(loket_router)
app.include_router(users_router)
app.include_router(groups_router)
app.include_router(client_router)
app.include_router(panggilan_router)
app.include_router(tts_router)

# ---------------------------------------------------------------------------
# Health-check endpoint
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    return {
        "status": True,
        "app": APP_TITLE,
        "version": APP_VERSION,
        "docs": "/docs",
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Endpoint untuk Docker healthcheck atau monitoring."""
    from database.dbmysql import get_db_conn
    try:
        conn = get_db_conn()
        conn.close()
        db_ok = True
        db_message = "OK"
    except Exception as e:
        db_ok = False
        db_message = str(e)

    return {
        "status": True,
        "database": {
            "connected": db_ok,
            "message": db_message,
        },
    }

# ---------------------------------------------------------------------------
# Entry point — jalankan dengan: python app.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    import uvicorn

    host = os.environ.get("SERVER_HOST", "0.0.0.0")
    port = int(os.environ.get("SERVER_PORT", 8000))
    reload = os.environ.get("APP_RELOAD", "true").lower() == "true"

    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
