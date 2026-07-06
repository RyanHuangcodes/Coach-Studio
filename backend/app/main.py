from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.routers import auth, drafts, drills, groups, insights, players, plans, practices, tiers

app = FastAPI(title="Coach Studio")

_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

app.include_router(auth.router)
app.include_router(plans.router)
app.include_router(drafts.router)
app.include_router(tiers.router)
app.include_router(players.router)
app.include_router(practices.router)
app.include_router(groups.router)
app.include_router(drills.router)
app.include_router(insights.router)

_FRONTEND_PATH = Path(__file__).resolve().parent / "static" / "Front.html"


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return _FRONTEND_PATH.read_text(encoding="utf-8")
