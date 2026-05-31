"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.dependencies import WebAuthRequired
from app.routers import health, auth, exams, commits, analysis
from app.routers import web

STATIC_DIR = Path(__file__).parent / "web" / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="cheat-buster")

    @app.exception_handler(WebAuthRequired)
    async def web_auth_redirect(request, exc):
        return RedirectResponse(url="/login", status_code=302)

    # Mount static files for web dashboard
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # API routers
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(commits.router, prefix="/commits", tags=["commits"])
    app.include_router(analysis.router, tags=["analysis"])

    # Web dashboard (HTML pages) — registered before exams API so that
    # /exams/new and /exams/{id} browser requests hit HTML routes first.
    app.include_router(web.router)

    # Exams API — /{exam_id:int} only; non-integer paths fall through to web.
    app.include_router(exams.router, prefix="/exams", tags=["exams"])

    return app


app = create_app()
