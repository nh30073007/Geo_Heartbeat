# backend/app/sentiment/news_aggregator.py
"""
News Aggregator - Combine GDELT + RSS into per-country sentiment snapshots.

This is the KEY FILE that bridges raw news → your simulation state.

Output schema per country:
{
    "country_id": "in",
    "country_name": "India",
    "fetched_at": ISO timestamp,
    "sentiment_score": -0.42,           # -1 to +1
    "article_count": 137,
    "gdelt_count": 89,
    "rss_count": 48,
    "top_headlines": [{"title": ..., "url": ..., "tone": ..., "source": ...}, ...],
    "tone_distribution": {"positive": 22, "neutral": 90, "negative": 25},
    "source_breakdown": {"gdelt": 89, "rss": 48},
    "economic_indicators": {...},
    "_source": "live_news"
}
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .gdelt_ingestor import GDELTIngestor
from .rss_ingestor import RSSIngestor, COUNTRY_FEED_MAP
from .worldbank_ingestor import WorldBankIngestor  # if you have it; else skip

logger = logging.getLogger(__name__)


# Country metadata (extend as needed)
COUNTRY_MAP = {
    "in": {"name": "India", "iso2": "IN", "region": "South Asia"},
    "bd": {"name": "Bangladesh", "iso2": "BD", "region": "South Asia"},
    "pk": {"name": "Pakistan", "iso2": "PK", "region": "South Asia"},
    "us": {"name": "United States", "iso2": "US", "region": "North America"},
    "uk": {"name": "United Kingdom", "iso2": "GB", "region": "Europe"},
    "cn": {"name": "China", "iso2": "CN", "region": "East Asia"},
    "jp": {"name": "Japan", "iso2": "JP", "region": "East Asia"},
    "kr": {"name": "South Korea", "iso2": "KR", "region": "East Asia"},
    "ru": {"name": "Russia", "iso2": "RU", "region": "Europe"},
    "de": {"name": "Germany", "iso2": "DE", "region": "Europe"},
    "fr": {"name": "France", "iso2": "FR", "region": "Europe"},
    "ir": {"name": "Iran", "iso2": "IR", "region": "Middle East"},
    "il": {"name": "Israel", "iso2": "IL", "region": "Middle East"},
    "sa": {"name": "Saudi Arabia", "iso2": "SA", "region": "Middle East"},
    "ae": {"name": "United Arab Emirates", "iso2": "AE", "region": "Middle East"},
    "tr": {"name": "Turkey", "iso2": "TR", "region": "Middle East"},
    "eg": {"name": "Egypt", "iso2": "EG", "region": "Middle East"},
    "za": {"name": "South Africa", "iso2": "ZA", "region": "Africa"},
    "ng": {"name": "Nigeria", "iso2": "NG", "region": "Africa"},
    "ke": {"name": "Kenya", "iso2": "KE", "region": "Africa"},
    "br": {"name": "Brazil", "iso2": "BR", "region": "South America"},
    "ar": {"name": "Argentina", "iso2": "AR", "region": "South America"},
    "mx": {"name": "Mexico", "iso2": "MX", "region": "North America"},
    "ca": {"name": "Canada", "iso2": "CA", "region": "North America"},
    "au": {"name": "Australia", "iso2": "AU", "region": "Asia Pacific"},
    "id": {"name": "Indonesia", "iso2": "ID", "region": "Asia Pacific"},
}


class NewsAggregator:
    """
    Single entry point for real-time news ingestion.
    Combines GDELT (broad) + RSS (curated) + WorldBank (economic baseline).
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        self.gdelt = GDELTIngestor()
        self.rss = RSSIngestor()
        self.worldbank = WorldBankIngestor()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = cache_ttl_seconds
        self._lock = asyncio.Lock()

    async def fetch_country(
        self,
        country_id: str,
        hours_back: int = 24,
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch + aggregate real-time data for one country.
        Uses cache if fresh; otherwise fetches from all sources.
        """
        country_id = (country_id or "").strip().lower()
        if country_id not in COUNTRY_MAP:
            logger.warning(f"Unknown country: {country_id}")
            return None

        # Cache check
        if not force_refresh:
            cached = self._cache.get(country_id)
            if cached:
                age = (datetime.now() - cached["_cached_at"]).total_seconds()
                if age < self._cache_ttl:
                    logger.debug(f"📦 Cache hit: {country_id} (age={age:.0f}s)")
                    return cached

        meta = COUNTRY_MAP[country_id]
        country_name = meta["name"]

        # Parallel fetch
        gdelt_task = self.gdelt.fetch_country_news(country_name, hours_back=hours_back)
        rss_task = self.rss.fetch_country_feeds(country_name)
        econ_task = self.worldbank.fetch_all_for_country(meta["iso2"])

        gdelt_articles, rss_articles, econ = await asyncio.gather(
            gdelt_task, rss_task, econ_task, return_exceptions=True
        )

        if isinstance(gdelt_articles, Exception):
            logger.warning(f"GDELT error: {gdelt_articles}")
            gdelt_articles = []
        if isinstance(rss_articles, Exception):
            logger.warning(f"RSS error: {rss_articles}")
            rss_articles = []
        if isinstance(econ, Exception):
            logger.warning(f"WorldBank error: {econ}")
            econ = {}

        # Combine
        all_articles = list(gdelt_articles) + list(rss_articles)
        result = self._build_snapshot(country_id, country_name, all_articles, econ)
        result["_cached_at"] = datetime.now()

        # Store in cache (with lock to avoid race)
        async with self._lock:
            self._cache[country_id] = result

        return result

    def _build_snapshot(
        self,
        country_id: str,
        country_name: str,
        articles: List[Dict[str, Any]],
        econ: Dict[str, float],
    ) -> Dict[str, Any]:
        """Aggregate all articles into a single sentiment snapshot."""

        gdelt_articles = [a for a in articles if a.get("_source_type") == "gdelt"]
        rss_articles = [a for a in articles if a.get("_source_type") == "rss"]

        # Sentiment score — use GDELT tones (RSS has no tone)
        tones = [
            float(a["tone"])
            for a in gdelt_articles
            if isinstance(a.get("tone"), (int, float))
        ]
        if tones:
            sentiment_score = max(-1.0, min(1.0, sum(tones) / len(tones)))
        else:
            sentiment_score = 0.0

        # Tone distribution
        pos = sum(1 for t in tones if t > 0.15)
        neg = sum(1 for t in tones if t < -0.15)
        neu = len(tones) - pos - neg

        # Top headlines — sorted by abs(tone) descending
        sorted_articles = sorted(
            gdelt_articles,
            key=lambda a: abs(float(a.get("tone", 0))),
            reverse=True,
        )
        top_headlines = [
            {
                "title": a["title"],
                "url": a["url"],
                "source": a.get("source", ""),
                "tone": a.get("tone", 0.0),
                "seendate": a.get("seendate", ""),
            }
            for a in sorted_articles[:10]
        ]

        # Top RSS headlines
        top_rss = [
            {
                "title": a["title"],
                "url": a["url"],
                "source": a.get("source", ""),
                "feed": a.get("feed", ""),
                "published": a.get("published", ""),
            }
            for a in rss_articles[:10]
        ]

        return {
            "country_id": country_id,
            "country_name": country_name,
            "fetched_at": datetime.now().isoformat(),
            "sentiment_score": round(sentiment_score, 3),
            "article_count": len(articles),
            "gdelt_count": len(gdelt_articles),
            "rss_count": len(rss_articles),
            "tone_distribution": {
                "positive": pos,
                "neutral": neu,
                "negative": neg,
            },
            "source_breakdown": {
                "gdelt": len(gdelt_articles),
                "rss": len(rss_articles),
            },
            "top_headlines": top_headlines,
            "top_rss_headlines": top_rss,
            "economic_indicators": econ,
            "_source": "live_news",
        }

    async def fetch_multiple(
        self,
        country_ids: List[str],
        hours_back: int = 24,
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch multiple countries in parallel."""
        tasks = {cid: self.fetch_country(cid, hours_back) for cid in country_ids}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        output = {}
        for cid, res in zip(tasks.keys(), results):
            if isinstance(res, Exception):
                logger.error(f"Fetch {cid} failed: {res}")
                output[cid] = None
            else:
                output[cid] = res
        return output

    def get_cached(self, country_id: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(country_id.lower())

    async def close(self):
        await self.gdelt.close()
        await self.worldbank.close()


# Global singleton — import this from anywhere
news_aggregator = NewsAggregator(cache_ttl_seconds=300)