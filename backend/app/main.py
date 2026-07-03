from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.routers import auth, drafts, groups, players, plans, practices, tiers

app = FastAPI(title="Coach Studio")

app.include_router(auth.router)
app.include_router(plans.router)
app.include_router(drafts.router)
app.include_router(tiers.router)
app.include_router(players.router)
app.include_router(practices.router)
app.include_router(groups.router)

_FRONTEND_PATH = Path(__file__).resolve().parent / "static" / "Front.html"


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return _FRONTEND_PATH.read_text(encoding="utf-8")
