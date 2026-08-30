from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine, sync_schema
from app import models  # noqa: F401 -- registers models on Base before create_all
from app.routers import auth, dashboard, jobs, match, resume

Base.metadata.create_all(bind=engine)
sync_schema()

app = FastAPI(
    title="CareerLens AI",
    description="Explainable job search, resume intelligence, and career optimization platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Failed-Sources"],
)

# Every router lives under /api — both in dev (Vite's proxy forwards /api/*
# to this backend unmodified, see frontend/vite.config.js) and in production
# (the frontend's own build, served below from the same origin, also calls
# /api/*). One path scheme for both modes instead of two.
app.include_router(auth.router, prefix="/api")
app.include_router(resume.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(match.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}


# Production mode: serve the built React app from this same process/port
# instead of running a separate `npm run dev` Vite server. Only active when
# `frontend/dist` exists (i.e. `npm run build` has been run) — absent that,
# nothing below registers, and the API still works standalone for the
# Vite-dev-server + proxy workflow.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # React Router (BrowserRouter) owns client-side routes like /jobs or
        # /resumes — a hard refresh/direct link on one of those is still a
        # real GET this server sees, so anything that isn't a known static
        # file falls back to index.html and lets the client-side router
        # take it from there.
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
