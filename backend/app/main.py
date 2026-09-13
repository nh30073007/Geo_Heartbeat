"""Strategic AI Nexus API entrypoint.

The application uses one shared runtime for simulations, analytics and
WebSocket delivery. This avoids route-local state duplication and makes the
frontend's REST/WebSocket contract deterministic.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ✅ Import all routers
from .api.routes import (
    simulation_router,
    state_router,
    analytics_router,
    dashboard_router,
    country_router,   # ✅ Country router
    news_router,      # ✅ NEW: Live news + sentiment router
)
from .api.routes.websocket import router as websocket_router
from .core.runtime import runtime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Strategic AI Nexus",
    description="Advanced Multi-Agent Geopolitical Simulation Platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_START = time.monotonic()


@app.get("/")
async def root():
    return {
        "name": "Strategic AI Nexus API",
        "version": app.version,
        "build": "RL-WS-LIVE-NEWS-2026-09-13",
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
        "build": "RL-WS-LIVE-NEWS-2026-09-13",
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
app.include_router(country_router, prefix="/api")   # ✅ Country routes: /api/country
app.include_router(news_router, prefix="/api")      # ✅ NEW: /api/news/country/{id}
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


# ============================================
# Startup: Log all routes
# ============================================

@app.on_event("startup")
async def startup_event():
    """Print all registered routes on startup for debugging"""
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            methods = getattr(route, "methods", set())
            routes.append(f"{methods} {route.path}")

    logger.info("=" * 60)
    logger.info("📋 REGISTERED ROUTES:")
    for route in sorted(routes):
        if "country" in route or "news" in route:
            logger.info(f"  ✅ {route}")
        else:
            logger.debug(f"  {route}")
    logger.info("=" * 60)

    # ✅ Check country + news routes
    country_routes = [r for r in routes if "country" in r]
    news_routes = [r for r in routes if "news" in r]

    if country_routes:
        logger.info(f"✅ {len(country_routes)} country routes registered")
    else:
        logger.warning("❌ No country routes found! Check router registration.")

    if news_routes:
        logger.info(f"✅ {len(news_routes)} news routes registered:")
        for route in news_routes:
            logger.info(f"  📰 {route}")
    else:
        logger.warning("❌ No news routes found! Check news_router import.")