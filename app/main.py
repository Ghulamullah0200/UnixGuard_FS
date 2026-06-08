"""
main.py — FastAPI application entry point for UnixGuard FS.
Serves the API endpoints and the single-page HTML frontend.
"""

import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routers import filesystem, terminal, scheduler, vm

# ── Application ───────────────────────────────────────────────
app = FastAPI(
    title="UnixGuard FS & VM",
    description="Web-Based Unix File System Simulator, CPU Scheduler & Virtual Memory Simulator",
    version="2.0.0",
)

# ── Static Files & Templates ─────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ── Routers ───────────────────────────────────────────────────
app.include_router(filesystem.router)
app.include_router(terminal.router)
app.include_router(scheduler.router)
app.include_router(vm.router)


# ── Homepage ──────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the single-page dashboard."""
    return templates.TemplateResponse(request, "index.html")


# ── Startup Event ─────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    """Initialize the database on startup. On Vercel the /tmp DB is ephemeral,
    so we also seed the default filesystem tree on every cold start."""
    from app.database import init_db
    init_db()
    # Auto-seed on Vercel (ephemeral /tmp) or if the DB is freshly created
    import os
    if os.environ.get("VERCEL"):
        from app.seed import seed_database
        seed_database()

