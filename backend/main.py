"""MaximoBRD backend entry point. Run with:
    uvicorn main:app --reload --port 8765 --host 127.0.0.1
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Body/query validation failures also use the envelope instead of FastAPI's
    raw detail list (spec §10)."""
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(part) for part in first.get("loc", []) if part != "body")
    message = f"{field}: {first.get('msg', 'invalid value')}" if field else "Invalid request"
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION", "message": message}})


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

class SpaStaticFiles(StaticFiles):
    """Serve the built frontend, but tell the browser never to cache index.html.

    The JS/CSS files have content-hashed names (e.g. index-B4m2zVEm.js), so they
    are safe to cache forever. index.html is not hashed — if the browser caches
    it, a freshly rebuilt app stays hidden behind the stale page. no-cache forces
    the browser to re-check index.html on every load, which picks up new builds.
    """

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if getattr(response, "media_type", None) == "text/html":
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


# Single-command / desktop mode: if the frontend has been built, serve it at /.
# Path comes from config (bundled inside the PyInstaller binary when packaged).
if config.FRONTEND_DIST.exists():
    app.mount("/", SpaStaticFiles(directory=str(config.FRONTEND_DIST), html=True), name="frontend")
