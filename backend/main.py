"""TraceBack — FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.api import system, crash, repository, git_routes, analysis, patch, tests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-28s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("traceback.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("TraceBack engine starting…")
    yield
    logger.info("TraceBack engine shutting down…")


app = FastAPI(
    title="TraceBack",
    description="AI-Powered Crash Investigation & Automated Code Repair",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(system.router, prefix="/api")
app.include_router(crash.router, prefix="/api")
app.include_router(repository.router, prefix="/api")
app.include_router(git_routes.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(patch.router, prefix="/api")
app.include_router(tests.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "TraceBack",
        "tagline": "AI-Powered Crash Investigation & Automated Code Repair",
        "version": "1.0.0",
        "docs": "/docs",
    }
