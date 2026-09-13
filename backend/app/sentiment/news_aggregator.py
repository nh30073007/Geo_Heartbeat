# backend/app/sentiment/news_aggregator.py
"""
News Aggregator — RSS-FIRST architecture, GDELT optional.

Key changes:
- RSS is the primary source (always attempted, parallel)
- WorldBank for economic baseline (parallel)
- GDELT is OPTIONAL: runs in parallel but never blocks the response
- If GDELT times out, RSS + lexicon sentiment deliver the snapshot
- Overall per-request deadline (env: NEWS_TOTAL_DEADLINE=15s)
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from .gdelt_ingestor import GDELTIngestor, gdelt_status, ENABLE_GDELT
from .rss_ingestor import RSSIngestor

try:
    from .worldbank_ingestor import WorldBankIngestor
    _HAS_WORLDBANK = True
except Exception as _wb_err:
    logging.getLogger(__name__).warning(f"WorldBank ingestor unavailable: {_wb_err}")
    WorldBankIngestor = None  # type: ignore
    _HAS_WORLDBANK = False

logger = logging.getLogger(__name__)

# Hard wall-clock cap for a single country fetch
TOTAL_DEADLINE_SECONDS = float(os.getenv("NEWS_TOTAL_DEADLINE", "15.0"))


COUNTRY_MAP: Dict[str, Dict[str, str]] = {
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


_POSITIVE_WORDS = {
    "agreement", "peace", "growth", "surge", "rally", "recovery", "boost",
    "cooperation", "partnership", "deal", "success", "win", "gain", "improve",
    "record", "breakthrough", "alliance", "progress", "stability", "reform",
    "investment", "expansion", "profit", "rise", "advance",
}
_NEGATIVE_WORDS = {
    "conflict", "war", "attack", "crisis", "sanction", "protest", "collapse",
    "decline", "tension", "threat", "strike", "recession", "inflation",
    "corruption", "violence", "clash", "dispute", "ban", "tariff", "default",
    "shortage", "loss", "fall", "drop", "risk", "warning", "fail",
}
_WORD_RE = re.compile(r"[a-zA-Z']+")


def _lexicon_sentiment(text: str) -> float:
    if not text:
        return 0.0
    words = [w.lower() for w in _WORD_RE.findall(text)]
    if not words:
        return 0.0
    pos = sum(1 for w in words if w in _POSITIVE_WORDS)
    neg = sum(1 for w in words if w in _NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return max(-1.0, min(1.0, (pos - neg) / total))


class NewsAggregator:
    """RSS-first aggregator with optional GDELT."""

    def __init__(self, cache_ttl_seconds: int = 300):
        self.gdelt = GDELTIngestor()
        self.rss = RSSIngestor()
        self.worldbank = WorldBankIngestor() if _HAS_WORLDBANK else None
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = max(30, int(cache_ttl_seconds))
        self._lock = asyncio.Lock()

    async def fetch_country(
        self,
        country_id: str,
        hours_back: int = 24,
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Any]]:
        country_id = (country_id or "").strip().lower()
        if country_id not in COUNTRY_MAP:
            logger.warning(f"Unknown country requested: {country_id!r}")
            return None

        # Cache hit
        if not force_refresh:
            cached = self._cache.get(country_id)
            if cached:
                age = (datetime.now() - cached["_cached_at"]).total_seconds()
                if age < self._cache_ttl:
                    logger.debug(f"📦 Cache hit: {country_id} (age={age:.0f}s)")
                    return cached

        meta = COUNTRY_MAP[country_id]
        country_name = meta["name"]

        # ---- Fire all sources in parallel, each isolated ----
        gdelt_task = self._safe_call(
            "GDELT",
            self.gdelt.fetch_country_news(country_name, hours_back=hours_back),
        )
        rss_task = self._safe_call(
            "RSS",
            self.rss.fetch_country_feeds(country_name),
        )
        if self.worldbank is not None:
            econ_task = self._safe_call(
                "WorldBank",
                self.worldbank.fetch_all_for_country(meta["iso2"]),
            )
        else:
            econ_task = asyncio.sleep(0, result={})

        # ---- Wrap in overall deadline so no source can hang the request ----
        try:
            gdelt_articles, rss_articles, econ = await asyncio.wait_for(
                asyncio.gather(gdelt_task, rss_task, econ_task),
                timeout=TOTAL_DEADLINE_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"⏱️ Overall news deadline ({TOTAL_DEADLINE_SECONDS}s) hit for "
                f"{country_id} — returning partial data"
            )
            gdelt_articles, rss_articles, econ = [], [], {}

        all_articles = list(gdelt_articles) + list(rss_articles)
        snapshot = self._build_snapshot(
            country_id, country_name, all_articles, econ or {}
        )
        snapshot["_cached_at"] = datetime.now()

        async with self._lock:
            self._cache[country_id] = snapshot

        return snapshot

    @staticmethod
    async def _safe_call(name: str, coro) -> Any:
        try:
            return await coro
        except Exception as e:
            logger.warning(f"{name} source failed: {type(e).__name__}: {e}")
            return []

    def _build_snapshot(
        self,
        country_id: str,
        country_name: str,
        articles: List[Dict[str, Any]],
        econ: Dict[str, float],
    ) -> Dict[str, Any]:
        gdelt_articles = [a for a in articles if a.get("_source_type") == "gdelt"]
        rss_articles = [a for a in articles if a.get("_source_type") == "rss"]

        # ---- Sentiment score ----
        tones = [
            float(a["tone"])
            for a in gdelt_articles
            if isinstance(a.get("tone"), (int, float))
        ]
        if tones:
            gdelt_score = sum(tones) / len(tones)
            gdelt_score = max(-1.0, min(1.0, gdelt_score))
        else:
            gdelt_score = 0.0

        # RSS lexicon fallback
        rss_scores: List[float] = []
        if not tones and rss_articles:
            for a in rss_articles:
                title = a.get("title", "") or ""
                score = _lexicon_sentiment(title)
                a["_lexicon_tone"] = score
                rss_scores.append(score)
            if rss_scores:
                gdelt_score = sum(rss_scores) / len(rss_scores)
                gdelt_score = max(-1.0, min(1.0, gdelt_score))

        sentiment_score = round(gdelt_score, 3)

        # ---- Tone distribution ----
        effective_tones = tones if tones else rss_scores
        pos = sum(1 for t in effective_tones if t > 0.15)
        neg = sum(1 for t in effective_tones if t < -0.15)
        neu = max(0, len(effective_tones) - pos - neg)

        # ---- Top headlines (GDELT preferred, RSS fallback) ----
        if gdelt_articles:
            sorted_articles = sorted(
                gdelt_articles,
                key=lambda a: abs(float(a.get("tone", 0))),
                reverse=True,
            )
            top_headlines = [
                {
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "source": a.get("source", ""),
                    "tone": a.get("tone", 0.0),
                    "seendate": a.get("seendate", ""),
                }
                for a in sorted_articles[:10]
            ]
        else:
            sorted_rss = sorted(
                rss_articles,
                key=lambda a: abs(float(a.get("_lexicon_tone", 0.0))),
                reverse=True,
            )
            top_headlines = [
                {
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "source": a.get("source", ""),
                    "tone": a.get("_lexicon_tone", 0.0),
                    "seendate": a.get("published", ""),
                }
                for a in sorted_rss[:10]
            ]

        top_rss = [
            {
                "title": a.get("title", ""),
                "url": a.get("url", ""),
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
            "sentiment_score": sentiment_score,
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
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Fetch multiple countries, serialized to protect GDELT rate limit."""
        results: Dict[str, Optional[Dict[str, Any]]] = {}
        for cid in country_ids:
            try:
                results[cid] = await self.fetch_country(cid, hours_back)
            except Exception as e:
                logger.error(f"Fetch {cid} failed: {type(e).__name__}: {e}")
                results[cid] = None
        return results

    def get_cached(self, country_id: str) -> Optional[Dict[str, Any]]:
        return self._cache.get((country_id or "").lower())

    def cache_info(self) -> Dict[str, Any]:
        now = datetime.now()
        return {
            "size": len(self._cache),
            "ttl_seconds": self._cache_ttl,
            "entries": {
                cid: {
                    "age_seconds": round((now - v["_cached_at"]).total_seconds(), 1),
                    "article_count": v.get("article_count", 0),
                    "gdelt_count": v.get("gdelt_count", 0),
                    "rss_count": v.get("rss_count", 0),
                }
                for cid, v in self._cache.items()
            },
        }

    def health(self) -> Dict[str, Any]:
        """Combined health for /health endpoints."""
        return {
            "cache": self.cache_info(),
            "gdelt": gdelt_status(),
            "deadline_seconds": TOTAL_DEADLINE_SECONDS,
        }

    async def close(self):
        try:
            await self.gdelt.close()
        except Exception as e:
            logger.debug(f"GDELT close error: {e}")
        if self.worldbank is not None:
            try:
                await self.worldbank.close()
            except Exception as e:
                logger.debug(f"WorldBank close error: {e}")


# Global singleton
news_aggregator = NewsAggregator(cache_ttl_seconds=300)