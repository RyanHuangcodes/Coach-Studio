from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.rate_limit import limiter
from app.routers import (
    analytics,
    auth,
    drafts,
    drills,
    groups,
    history,
    insights,
    players,
    plans,
    practices,
    rosters,
    tiers,
)

app = FastAPI(title="Coach Studio")

# Rate limiting: register the limiter and a handler that returns 429 with a
# Retry-After header when a client exceeds a route's limit.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

app.include_router(auth.router)
app.include_router(plans.router)
app.include_router(drafts.router)
app.include_router(tiers.router)
app.include_router(players.router)
app.include_router(practices.router)
app.include_router(rosters.router)
app.include_router(groups.router)
app.include_router(drills.router)
app.include_router(insights.router)
app.include_router(history.router)
app.include_router(analytics.router)

_FRONTEND_PATH = Path(__file__).resolve().parent / "static" / "Front.html"
_SW_PATH = _STATIC_DIR / "sw.js"


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return _FRONTEND_PATH.read_text(encoding="utf-8")


@app.get("/sw.js")
def serve_service_worker():
    # Served from the root so its scope covers the whole app ("/"). No-cache so a
    # new worker is picked up promptly on the next visit.
    return Response(
        content=_SW_PATH.read_text(encoding="utf-8"),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
    )
