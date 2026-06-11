"""MaximoBRD backend entry point. Run with:
    uvicorn main:app --reload --port 8765 --host 127.0.0.1
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import config
from db.database import init_db
from routes import pipeline, projects, settings, sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="MaximoBRD", version=config.APP_VERSION, lifespan=lifespan)

# Vite dev server origin (browser MVP). Backend itself binds 127.0.0.1 only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """All errors use the {error: {code, message}} envelope (spec §10)."""
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak stack traces to the client (spec §10)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL", "message": "Internal server error"}},
    )


def _health():
    return {"status": "ok", "version": config.APP_VERSION}


# Routes are mounted twice: bare paths per the spec contract, and under /api so the
# Vite dev proxy and the served production build both work without rewrites.
for prefix in ("", "/api"):
    app.add_api_route(f"{prefix}/health", _health, methods=["GET"])
    app.include_router(projects.router, prefix=prefix, include_in_schema=prefix == "")
    app.include_router(sources.router, prefix=prefix, include_in_schema=prefix == "")
    app.include_router(settings.router, prefix=prefix, include_in_schema=prefix == "")
    app.include_router(pipeline.router, prefix=prefix, include_in_schema=prefix == "")

# Single-command mode: if the frontend has been built, serve it at /
_dist = config.REPO_DIR / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
