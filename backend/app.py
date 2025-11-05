# backend/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles

from core.config import settings
from routers import brain, vision, scribe


def create_app() -> FastAPI:
    app = FastAPI(
        title="ROSHN PULSE API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    # Static files (for overlays)
    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    # Routers
    app.include_router(brain.router, prefix="", tags=["brain"])
    app.include_router(vision.router, prefix="", tags=["vision"])
    app.include_router(scribe.router, prefix="", tags=["scribe"])

    @app.get("/health")
    async def health():
        return JSONResponse({"status": "ok"})

    return app


app = create_app()
