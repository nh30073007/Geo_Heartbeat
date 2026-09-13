# backend/app/api/routes/__init__.py
"""
API Routes Package
"""
from .simulation import router as simulation_router
from .state import router as state_router
from .analytics import router as analytics_router
from .dashboard import router as dashboard_router
from .country import router as country_router
from .news import router as news_router          # ✅ NEW

__all__ = [
    "simulation_router",
    "state_router",
    "analytics_router",
    "dashboard_router",
    "country_router",
    "news_router",                                # ✅ NEW
]