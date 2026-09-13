# backend/app/sentiment/gdelt_ingestor.py
"""
GDELT 2.0 Ingestor - Real-time geopolitical news from GDELT

GDELT (Global Database of Events, Language, and Tone) is:
- Completely free
- No API key required
- Updates every 15 minutes
- Covers 100+ languages
- Provides tone/sentiment scores (-100 to +100)

API Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger(__name__)

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTIngestor:
    """Fetch real-time news articles from GDELT for any country/topic."""

    def __init__(self, timeout: float = 30.0):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "GeoAI-Nexus/1.0 (geopolitical simulation research)",
                "Accept": "application/json",
            },
        )

    async def fetch_country_news(
        self,
        country_name: str,
        hours_back: int = 24,
        max_records: int = 75,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent news articles mentioning a country.

        Args:
            country_name: e.g. "India", "Bangladesh", "United States"
            hours_back: Look-back window in hours (default 24)
            max_records: Max articles to return (GDELT caps at 250)
            language: Optional ISO language filter (e.g. "english")

        Returns:
            List of article dicts with: title, url, source, seendate,
            language, tone, socialimage
        """
        query = f'"{country_name}"'
        if language:
            query += f" sourcelang:{language}"

        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": min(max_records, 250),
            "format": "json",
            "timespan": f"{hours_back}h",
            "sort": "datedesc",
        }

        try:
            response = await self.client.get(GDELT_DOC_API, params=params)
            response.raise_for_status()

            # GDELT sometimes returns empty body for no results
            if not response.text.strip():
                logger.info(f"🌐 GDELT: no articles for {country_name}")
                return []

            data = response.json()
            articles = data.get("articles", []) or []

            parsed = [self._parse_article(a) for a in articles]
            logger.info(f"🌐 GDELT: {len(parsed)} articles for {country_name}")
            return parsed

        except httpx.HTTPStatusError as e:
            logger.error(f"GDELT HTTP error for {country_name}: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"GDELT fetch failed for {country_name}: {e}")
            return []

    async def fetch_topic_news(
        self,
        topic: str,
        hours_back: int = 24,
        max_records: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch news about any topic (e.g. 'geopolitics', 'sanctions', 'election')."""
        return await self.fetch_country_news(
            country_name=topic,
            hours_back=hours_back,
            max_records=max_records,
        )

    def _parse_article(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a GDELT article into our internal schema."""
        tone_raw = raw.get("tone", 0)
        try:
            tone = float(tone_raw) / 100.0  # normalize -100..+100 → -1..+1
        except (ValueError, TypeError):
            tone = 0.0

        return {
            "title": raw.get("title", ""),
            "url": raw.get("url", ""),
            "source": raw.get("domain", ""),
            "seendate": raw.get("seendate", ""),
            "language": raw.get("language", ""),
            "tone": tone,
            "image": raw.get("socialimage", ""),
            "fetched_at": datetime.now().isoformat(),
            "_source_type": "gdelt",
        }

    async def close(self):
        await self.client.aclose()