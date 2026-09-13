# backend/app/sentiment/gdelt_ingestor.py
"""
GDELT 2.0 Ingestor - OPTIONAL source, fail-fast, RSS-first architecture.

Key changes for production:
- Fast timeout (6s) so unreachable GDELT never blocks user requests
- Only 1 retry (was 3) to minimize latency
- Environment toggle: ENABLE_GDELT=true/false
- Circuit breaker: if GDELT fails N times in a row, skip it for X minutes
- Everything else (sanitization, rate-limit, logging) preserved
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger(__name__)

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

# ---------------------------------------------------------------------------
# Environment toggles
# ---------------------------------------------------------------------------
ENABLE_GDELT = os.getenv("ENABLE_GDELT", "true").lower() in ("1", "true", "yes")
GDELT_TIMEOUT = float(os.getenv("GDELT_TIMEOUT", "6.0"))         # was 30
GDELT_CONNECT_TIMEOUT = float(os.getenv("GDELT_CONNECT_TIMEOUT", "3.0"))
GDELT_MAX_RETRIES = int(os.getenv("GDELT_MAX_RETRIES", "1"))     # was 3

# Circuit breaker: after N consecutive failures, skip GDELT for M seconds
_CB_FAIL_THRESHOLD = int(os.getenv("GDELT_CB_THRESHOLD", "2"))
_CB_OPEN_SECONDS = int(os.getenv("GDELT_CB_OPEN_SECONDS", "600"))  # 10 min

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_GDELT_LOCK = asyncio.Lock()
_LAST_GDELT_CALL: float = 0.0
_GDELT_MIN_INTERVAL = 5.5

_cb_fail_count: int = 0
_cb_open_until: float = 0.0


def _circuit_is_open() -> bool:
    """Return True if circuit breaker is currently open (skip GDELT)."""
    return time.monotonic() < _cb_open_until


def _cb_record_failure() -> None:
    global _cb_fail_count, _cb_open_until
    _cb_fail_count += 1
    if _cb_fail_count >= _CB_FAIL_THRESHOLD:
        _cb_open_until = time.monotonic() + _CB_OPEN_SECONDS
        logger.warning(
            f"🔴 GDELT circuit breaker OPEN for {_CB_OPEN_SECONDS}s "
            f"(after {_cb_fail_count} consecutive failures)"
        )


def _cb_record_success() -> None:
    global _cb_fail_count, _cb_open_until
    _cb_fail_count = 0
    _cb_open_until = 0.0


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9 \-'.]", re.UNICODE)
_MAX_RESPONSE_BYTES = 5 * 1024 * 1024


def _sanitize_country_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    cleaned = _SAFE_NAME_RE.sub("", name).strip()
    cleaned = cleaned.replace('"', "").replace("'", "'")
    return cleaned[:80]


async def _enforce_rate_limit() -> None:
    global _LAST_GDELT_CALL
    async with _GDELT_LOCK:
        now = time.monotonic()
        elapsed = now - _LAST_GDELT_CALL
        if elapsed < _GDELT_MIN_INTERVAL:
            wait_for = _GDELT_MIN_INTERVAL - elapsed
            logger.debug(f"🌐 GDELT throttle: sleeping {wait_for:.2f}s")
            await asyncio.sleep(wait_for)
        _LAST_GDELT_CALL = time.monotonic()


class GDELTIngestor:
    """Optional GDELT source. Fails fast so it never blocks the request."""

    def __init__(self, timeout: float = GDELT_TIMEOUT):
        limits = httpx.Limits(max_connections=3, max_keepalive_connections=1)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=GDELT_CONNECT_TIMEOUT),
            limits=limits,
            headers={
                "User-Agent": "GeoAI-Nexus/1.0 (geopolitical simulation research)",
                "Accept": "application/json",
            },
            follow_redirects=True,
        )

    async def fetch_country_news(
        self,
        country_name: str,
        hours_back: int = 24,
        max_records: int = 75,
        language: Optional[str] = "english",
    ) -> List[Dict[str, Any]]:
        """Fetch country news. Returns [] immediately if disabled or CB open."""

        # ---- Gate 1: disabled by env? ----
        if not ENABLE_GDELT:
            logger.debug("GDELT disabled via ENABLE_GDELT env var")
            return []

        # ---- Gate 2: circuit breaker open? ----
        if _circuit_is_open():
            remaining = _cb_open_until - time.monotonic()
            logger.debug(f"GDELT circuit open — skipping ({remaining:.0f}s left)")
            return []

        safe_name = _sanitize_country_name(country_name)
        if not safe_name:
            logger.warning("GDELT: empty country name after sanitization")
            return []

        hours_back = max(1, min(int(hours_back), 24 * 7))
        max_records = max(1, min(int(max_records), 250))

        query_parts = [f'"{safe_name}"']
        if language:
            lang = _sanitize_country_name(language).lower()
            if lang:
                query_parts.append(f"sourcelang:{lang}")
        query = " ".join(query_parts)

        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": max_records,
            "format": "json",
            "timespan": f"{hours_back}h",
            "sort": "datedesc",
        }

        # ---- Retry loop: fail-fast, max 1 retry ----
        last_error: Optional[str] = None
        for attempt in range(GDELT_MAX_RETRIES):
            try:
                await _enforce_rate_limit()

                logger.debug(f"🌐 GDELT attempt={attempt+1} query={query!r}")
                response = await self.client.get(GDELT_DOC_API, params=params)

                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                    logger.warning(
                        f"GDELT HTTP {response.status_code} for {country_name}: "
                        f"{response.text[:200]!r}"
                    )
                    if response.status_code == 429:
                        _cb_record_failure()
                        return []
                    if 400 <= response.status_code < 500:
                        return []
                    await asyncio.sleep(1.5)
                    continue

                if len(response.content) > _MAX_RESPONSE_BYTES:
                    logger.warning(f"GDELT response too large for {country_name}")
                    _cb_record_failure()
                    return []

                body = (response.text or "").strip()
                if not body:
                    logger.info(f"🌐 GDELT: 0 articles for {country_name} (empty body)")
                    _cb_record_success()
                    return []

                if body[0] not in "[{":
                    logger.warning(f"GDELT non-JSON for {country_name}: {body[:200]!r}")
                    _cb_record_failure()
                    return []

                data = response.json()
                articles = data.get("articles") or []
                if not isinstance(articles, list):
                    articles = []

                parsed = [self._parse_article(a) for a in articles if isinstance(a, dict)]
                logger.info(f"🌐 GDELT: {len(parsed)} articles for {country_name}")
                _cb_record_success()
                return parsed

            except httpx.TimeoutException as e:
                last_error = f"timeout: {e}"
                logger.warning(
                    f"GDELT timeout for {country_name} (attempt {attempt+1}): {e}"
                )
                await asyncio.sleep(1.0)
            except httpx.HTTPStatusError as e:
                last_error = f"HTTPStatusError: {e}"
                logger.error(f"GDELT HTTPStatusError for {country_name}")
                await asyncio.sleep(1.0)
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.error(
                    f"GDELT fetch failed for {country_name}: {type(e).__name__}: {e}",
                    exc_info=True,
                )
                await asyncio.sleep(0.8)

        # All attempts failed → trip the breaker
        logger.warning(
            f"GDELT gave up for {country_name} after {GDELT_MAX_RETRIES} attempts: "
            f"{last_error}"
        )
        _cb_record_failure()
        return []

    async def fetch_topic_news(
        self,
        topic: str,
        hours_back: int = 24,
        max_records: int = 50,
    ) -> List[Dict[str, Any]]:
        return await self.fetch_country_news(
            country_name=topic,
            hours_back=hours_back,
            max_records=max_records,
            language=None,
        )

    def _parse_article(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        tone_raw = raw.get("tone", 0)
        try:
            tone = float(tone_raw) / 100.0
            tone = max(-1.0, min(1.0, tone))
        except (ValueError, TypeError):
            tone = 0.0

        return {
            "title": str(raw.get("title", ""))[:500],
            "url": str(raw.get("url", ""))[:2000],
            "source": str(raw.get("domain", ""))[:200],
            "seendate": str(raw.get("seendate", ""))[:32],
            "language": str(raw.get("language", ""))[:16],
            "tone": tone,
            "image": str(raw.get("socialimage", ""))[:2000],
            "fetched_at": datetime.now().isoformat(),
            "_source_type": "gdelt",
        }

    async def close(self):
        try:
            await self.client.aclose()
        except Exception as e:
            logger.debug(f"GDELT client close error: {e}")


def gdelt_status() -> Dict[str, Any]:
    """Introspection for /health endpoints."""
    now = time.monotonic()
    return {
        "enabled": ENABLE_GDELT,
        "timeout_seconds": GDELT_TIMEOUT,
        "max_retries": GDELT_MAX_RETRIES,
        "circuit_open": _circuit_is_open(),
        "circuit_open_until_seconds": max(0, round(_cb_open_until - now, 1)),
        "consecutive_failures": _cb_fail_count,
    }