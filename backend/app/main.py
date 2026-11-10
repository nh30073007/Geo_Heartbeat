"""Strategic AI Nexus API entrypoint."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import (
    simulation_router,
    state_router,
    analytics_router,
    dashboard_router,
    country_router,
    news_router,
)
from .api.routes.websocket import router as websocket_router
from .core.runtime import runtime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_START = time.monotonic()

_HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}


# ============================================
# Route collection — OpenAPI-based (version-agnostic)
# ============================================
def _collect_routes_from_openapi(app: FastAPI) -> List[str]:
    """
    Read all registered routes via OpenAPI schema.

    This is 100% version-agnostic — works on:
      - FastAPI <0.115 (routes merged directly)
      - FastAPI 0.115+ (_IncludedRouter lazy wrapper)
      - Any future version that builds OpenAPI schema
    """
    results: List[str] = []
    try:
        schema = app.openapi()
        paths = schema.get("paths", {}) or {}
        for path, methods in paths.items():
            for method in methods.keys():
                m = method.upper()
                if m in _HTTP_METHODS:
                    results.append(f"{m} {path}")
    except Exception as e:
        logger.warning("OpenAPI schema collection failed: %s", e)
    return results


def _log_registered_routes(app: FastAPI) -> None:
    """Log all routes using OpenAPI schema (works on any FastAPI version)."""
    all_routes = _collect_routes_from_openapi(app)

    logger.info("=" * 60)
    logger.info("📋 REGISTERED ROUTES (%d total):", len(all_routes))
    for route in sorted(all_routes):
        if any(k in route for k in ("country", "news", "simulation")):
            logger.info("  ✅ %s", route)
    logger.info("=" * 60)

    country_routes = [r for r in all_routes if "/country" in r]
    news_routes = [r for r in all_routes if "/news" in r]
    sim_routes = [r for r in all_routes if "/simulation" in r]

    if country_routes:
        logger.info("✅ %d country routes registered", len(country_routes))
    else:
        logger.warning("❌ No country routes found!")

    if news_routes:
        logger.info("✅ %d news routes registered", len(news_routes))
    else:
        logger.warning("❌ No news routes found!")

    if sim_routes:
        logger.info("✅ %d simulation routes registered", len(sim_routes))
    else:
        logger.warning("❌ No simulation routes found!")


# ============================================
# Lifespan
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    _log_registered_routes(app)
    yield
    logger.info("🛑 Shutting down Strategic AI Nexus API...")


app = FastAPI(
    title="Strategic AI Nexus",
    description="Advanced Multi-Agent Geopolitical Simulation Platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "Strategic AI Nexus API",
        "version": app.version,
        "build": "RL-WS-STEP3B-2026-09-21",
        "status": "running",
        "docs": "/docs",
        "websocket": "/ws",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": app.version,
        "build": "RL-WS-STEP3B-2026-09-21",
        "uptime": round(time.monotonic() - _START, 3),
        "websocket_connections": len(runtime.websocket_manager.connections),
        "simulations": len(runtime.simulation_runner.simulations),
        "timestamp": datetime.now().isoformat(),
    }


# ============================================
# API Routers
# ============================================
app.include_router(simulation_router, prefix="/api")
app.include_router(state_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(country_router, prefix="/api")
app.include_router(news_router, prefix="/api")
app.include_router(websocket_router)


# ============================================
# Exception Handlers
# ============================================
@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status": 500,
            "detail": "Internal Server Error",
            "timestamp": datetime.now().isoformat(),
        },
    )