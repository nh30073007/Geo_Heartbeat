# backend/app/api/routes/news.py
"""
News API Routes - Real-time news + sentiment for any country.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
import logging

from ...sentiment.news_aggregator import news_aggregator, COUNTRY_MAP

logger = logging.getLogger(__name__)

router = APIRouter(tags=["news"])


@router.get("/news/country/{country_id}")
async def get_country_news(
    country_id: str,
    hours_back: int = Query(24, ge=1, le=168),
    force_refresh: bool = Query(False),
) -> Dict[str, Any]:
    """
    Get real-time news + aggregated sentiment for a country.

    Sources: GDELT 2.0 (global) + curated RSS feeds + World Bank.
    Cached for 5 minutes.
    """
    country_id = country_id.lower()
    if country_id not in COUNTRY_MAP:
        raise HTTPException(404, f"Country '{country_id}' not supported")

    snapshot = await news_aggregator.fetch_country(
        country_id,
        hours_back=hours_back,
        force_refresh=force_refresh,
    )
    if not snapshot:
        raise HTTPException(500, f"Failed to fetch news for {country_id}")

    return {"success": True, "data": snapshot}


@router.get("/news/countries")
async def get_multiple_country_news(
    country_ids: str = Query(..., description="Comma-separated country codes"),
    hours_back: int = Query(24, ge=1, le=168),
) -> Dict[str, Any]:
    """Fetch news for multiple countries in parallel."""
    ids = [c.strip().lower() for c in country_ids.split(",") if c.strip()]
    if not ids:
        raise HTTPException(400, "No country IDs provided")

    results = await news_aggregator.fetch_multiple(ids, hours_back)
    return {"success": True, "data": results}


@router.get("/news/supported-countries")
async def get_supported_countries() -> Dict[str, Any]:
    """List countries with news coverage."""
    countries = [
        {"id": cid, "name": meta["name"], "region": meta["region"]}
        for cid, meta in COUNTRY_MAP.items()
    ]
    return {"success": True, "data": {"countries": countries, "total": len(countries)}}