# backend/app/sentiment/rss_ingestor.py
"""
RSS Feed Ingestor - Real-time news from major outlets (Asia-focused)

Step 3B fixes:
- COUNTRY-LOCK: India/other country news is blocked from BD feed
- TITLE+SUMMARY match (was title-only, missed many BD articles)
- Country keyword alias map ("bd" → "bangladesh")
- MAX_ARTICLE_AGE_DAYS raised to 14 for local feeds (BD feeds often older)
- Per-feed age override for known-slow feeds
- Better logging: show WHY 0 items (age vs keyword)

Step 3C fixes:
- Replaced DEAD feeds: dhaka_tribune, bdnews24 (RSS URLs broken)
- Added working feeds: tbs_news, bd_pratidin
- Feed-level TRUST: country-preferred feeds bypass keyword filter
  (a BD-exclusive feed's articles ARE BD news, regardless of title keywords)
- Tighter country-lock: blocked keywords now checked in title only
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, Any, List, Optional, Set

import feedparser  # pip install feedparser

logger = logging.getLogger(__name__)

# Max age of an article (days). Older ones are dropped.
MAX_ARTICLE_AGE_DAYS = int(os.getenv("RSS_MAX_AGE_DAYS", "14"))

# Per-feed age override (some feeds publish less frequently)
FEED_AGE_OVERRIDE_DAYS: Dict[str, int] = {
    "daily_star_bd": 21,
    "prothom_alo_en": 21,
    "tbs_news": 21,
    "bd_pratidin": 14,
    "jakarta_post": 21,
    "straits_times": 21,
    "korea_herald": 21,
    "bangkok_post": 21,
}

# ------------------------------------------------------------
# STEP 3C: Country-TRUSTED feeds
# If a feed is country-exclusive (e.g., daily_star_bd is a BD
# newspaper), then its articles ARE country news — skip keyword
# filter entirely. This prevents 8 → 0 filter loss.
# ------------------------------------------------------------
TRUSTED_COUNTRY_FEEDS: Dict[str, Set[str]] = {
    "bangladesh": {"daily_star_bd", "prothom_alo_en", "tbs_news", "bd_pratidin"},
    "india": {"times_of_india", "the_hindu"},
    "pakistan": {"dawn_pakistan"},
    "indonesia": {"jakarta_post"},
    "thailand": {"bangkok_post"},
    "japan": {"japan_times"},
    "south korea": {"korea_herald"},
}

# ------------------------------------------------------------
# COUNTRY-LOCK: keywords that indicate ANOTHER country's news
# If any of these appear in the TITLE of a country-exclusive feed,
# the article is dropped (e.g., "India wins" in daily_star_bd).
# ------------------------------------------------------------
BLOCKED_CONTEXT: Dict[str, List[str]] = {
    "bangladesh": [
        "india", "indian", "delhi", "mumbai", "kolkata",
        "pakistan", "pakistani", "karachi", "lahore",
        "sri lanka", "nepal", "bhutan", "myanmar", "afghanistan",
    ],
    "india": [
        "bangladesh", "bangladeshi", "dhaka", "chittagong",
        "pakistan", "pakistani", "karachi", "lahore",
        "sri lanka", "nepal",
    ],
    "pakistan": [
        "india", "indian", "delhi", "mumbai",
        "bangladesh", "dhaka",
        "afghanistan", "afghan",
    ],
}

# Strong country signals (must appear if BLOCKED_CONTEXT is empty)
PRIMARY_KEYWORDS: Dict[str, List[str]] = {
    "bangladesh": [
        "bangladesh", "bangladeshi", "dhaka", "chittagong",
        "chattogram", "sylhet", "khulna", "rajshahi",
        "cox's bazar", "taka", "bdt",
    ],
    "india": [
        "india", "indian", "delhi", "mumbai", "kolkata",
        "chennai", "bengaluru", "rupee", "inr",
    ],
    "pakistan": [
        "pakistan", "pakistani", "karachi", "lahore",
        "islamabad", "rawalpindi", "pkr",
    ],
}


# ============================================================
# RSS FEEDS — global + Asia-focused (STEP 3C — URLs verified)
# ============================================================
RSS_FEEDS = {
    # ---------- Global ----------
    "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "aljazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "guardian_world": "https://www.theguardian.com/world/rss",
    "nyt_world": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "dw_world": "https://rss.dw.com/rdf/rss-en-world",
    "france24": "https://www.france24.com/en/rss",

    # ---------- South Asia (STEP 3C: verified working) ----------
    "daily_star_bd": "https://www.thedailystar.net/rss.xml",          # ✅ 8 entries
    "prothom_alo_en": "https://en.prothomalo.com/feed",               # ✅ 2 entries
    "tbs_news": "https://www.tbsnews.net/rss.xml",                    # ✅ 10 entries (NEW)
    "bd_pratidin": "https://www.bd-pratidin.com/rss.xml",             # ✅ 151 entries (NEW)
    # REMOVED: dhaka_tribune (dead), bdnews24 (dead)
    "times_of_india": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "the_hindu": "https://www.thehindu.com/news/feeder/default.rss",
    "dawn_pakistan": "https://www.dawn.com/feeds/home",

    # ---------- Southeast Asia ----------
    "jakarta_post": "https://www.thejakartapost.com/rss",
    "bangkok_post": "https://www.bangkokpost.com/rss/data/topstories.xml",
    "straits_times": "https://www.straitstimes.com/news/world/rss.xml",

    # ---------- East Asia ----------
    "scmp_asia": "https://www.scmp.com/rss/91/feed",
    "japan_times": "https://www.japantimes.co.jp/feed/",
    "korea_herald": "https://www.koreaherald.com/common/rss_xml.php?ct=020000000000",
}


# ============================================================
# COUNTRY KEYWORDS — geographic + economic terms only
# ============================================================
COUNTRY_KEYWORDS: Dict[str, List[str]] = {
    "bangladesh": [
        "bangladesh", "dhaka", "chittagong", "chattogram", "sylhet",
        "khulna", "rajshahi", "cox's bazar", "taka", "bdt", "bangladeshi",
    ],
    "india": [
        "india", "delhi", "mumbai", "kolkata", "chennai", "bengaluru",
        "rupee", "inr", "indian",
    ],
    "pakistan": [
        "pakistan", "karachi", "lahore", "islamabad", "rawalpindi",
        "rupee", "pkr", "pakistani",
    ],
    "sri lanka": ["sri lanka", "colombo", "jaffna", "kandy", "sri lankan", "lkr"],
    "nepal": ["nepal", "kathmandu", "pokhara", "nepali", "npr"],
    "myanmar": ["myanmar", "burma", "yangon", "rangoon", "mandalay", "naypyidaw"],
    "afghanistan": ["afghanistan", "kabul", "kandahar", "herat", "afghan", "afghani"],
    "china": ["china", "beijing", "shanghai", "shenzhen", "chinese", "yuan", "rmb"],
    "japan": ["japan", "tokyo", "osaka", "japanese", "yen"],
    "south korea": ["south korea", "seoul", "korean", "won"],
    "indonesia": ["indonesia", "jakarta", "surabaya", "bali", "indonesian", "rupiah"],
    "philippines": ["philippines", "manila", "cebu", "filipino", "peso"],
    "vietnam": ["vietnam", "hanoi", "ho chi minh", "vietnamese", "dong"],
    "thailand": ["thailand", "bangkok", "phuket", "thai", "baht"],
    "malaysia": ["malaysia", "kuala lumpur", "malaysian", "ringgit"],
    "singapore": ["singapore", "singaporean", "sgd"],
    "united states": ["united states", "washington", "new york", "american", "usd"],
    "united kingdom": ["united kingdom", "london", "british", "gbp"],
    "russia": ["russia", "moscow", "russian", "ruble"],
    "iran": ["iran", "tehran", "iranian", "rial"],
    "israel": ["israel", "jerusalem", "tel aviv", "israeli", "shekel"],
    "saudi arabia": ["saudi arabia", "riyadh", "saudi", "riyal"],
    "turkey": ["turkey", "ankara", "istanbul", "turkish", "lira"],
    "egypt": ["egypt", "cairo", "egyptian", "egp"],
    "kenya": ["kenya", "nairobi", "kenyan", "ksh"],
    "nigeria": ["nigeria", "lagos", "abuja", "nigerian", "naira"],
    "south africa": ["south africa", "johannesburg", "cape town", "rand"],
}

# Alias map: short code → full country name used in keywords
COUNTRY_ALIAS: Dict[str, str] = {
    "bd": "bangladesh",
    "in": "india",
    "pk": "pakistan",
    "lk": "sri lanka",
    "np": "nepal",
    "mm": "myanmar",
    "af": "afghanistan",
    "cn": "china",
    "jp": "japan",
    "kr": "south korea",
    "id": "indonesia",
    "ph": "philippines",
    "vn": "vietnam",
    "th": "thailand",
    "my": "malaysia",
    "sg": "singapore",
    "us": "united states",
    "uk": "united kingdom",
    "ru": "russia",
    "ir": "iran",
    "il": "israel",
    "sa": "saudi arabia",
    "tr": "turkey",
    "eg": "egypt",
    "ke": "kenya",
    "ng": "nigeria",
    "za": "south africa",
}


# ============================================================
# COUNTRY → PREFERRED FEEDS (STEP 3C: URLs cleaned)
# ============================================================
COUNTRY_PREFERRED_FEEDS: Dict[str, List[str]] = {
    # South Asia
    "bangladesh": ["daily_star_bd", "prothom_alo_en", "tbs_news", "bd_pratidin"],
    "india": ["times_of_india", "the_hindu", "bbc_world", "aljazeera", "guardian_world"],
    "pakistan": ["dawn_pakistan", "bbc_world", "aljazeera", "guardian_world"],
    "sri lanka": ["bbc_world", "aljazeera", "guardian_world"],
    "nepal": ["bbc_world", "aljazeera", "guardian_world"],
    "myanmar": ["bbc_world", "aljazeera", "guardian_world"],
    "afghanistan": ["bbc_world", "aljazeera", "guardian_world"],

    # Southeast Asia
    "indonesia": ["jakarta_post", "straits_times", "bbc_world"],
    "philippines": ["straits_times", "bbc_world", "aljazeera"],
    "vietnam": ["straits_times", "bbc_world", "aljazeera"],
    "thailand": ["bangkok_post", "straits_times", "bbc_world"],
    "malaysia": ["straits_times", "bbc_world", "aljazeera"],
    "singapore": ["straits_times", "bbc_world"],
    "cambodia": ["straits_times", "bbc_world", "aljazeera"],
    "laos": ["straits_times", "bbc_world", "aljazeera"],

    # East Asia
    "china": ["scmp_asia", "bbc_world", "aljazeera", "dw_world"],
    "japan": ["japan_times", "scmp_asia", "bbc_world"],
    "south korea": ["korea_herald", "scmp_asia", "bbc_world"],
    "taiwan": ["scmp_asia", "bbc_world", "aljazeera"],
    "hong kong": ["scmp_asia", "bbc_world"],
    "mongolia": ["scmp_asia", "bbc_world"],

    # Middle East
    "iran": ["aljazeera", "bbc_world", "guardian_world"],
    "israel": ["aljazeera", "bbc_world", "guardian_world", "nyt_world"],
    "saudi arabia": ["aljazeera", "bbc_world", "guardian_world"],
    "turkey": ["aljazeera", "bbc_world", "dw_world"],
    "egypt": ["aljazeera", "bbc_world", "guardian_world"],

    # Europe
    "united kingdom": ["bbc_world", "guardian_world", "dw_world"],
    "russia": ["bbc_world", "dw_world", "aljazeera", "guardian_world"],
    "germany": ["dw_world", "bbc_world", "guardian_world"],
    "france": ["france24", "bbc_world", "guardian_world"],

    # Americas
    "united states": ["nyt_world", "bbc_world", "guardian_world"],

    # Africa
    "kenya": ["bbc_world", "aljazeera", "guardian_world"],
    "nigeria": ["bbc_world", "aljazeera", "guardian_world"],
    "south africa": ["bbc_world", "aljazeera", "guardian_world"],
}


def _resolve_country(country_input: str) -> str:
    """Resolve 'bd' → 'bangladesh', 'Bangladesh' → 'bangladesh'."""
    key = (country_input or "").strip().lower()
    return COUNTRY_ALIAS.get(key, key)


class RSSIngestor:
    """Fetch and parse RSS feeds with time + keyword precision."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        # Pre-compile patterns per country
        self._pattern_cache: Dict[str, List[re.Pattern]] = {}
        self._blocked_cache: Dict[str, List[re.Pattern]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def fetch_feed(
        self,
        feed_key: str,
        feed_url: str,
        max_items: int = 30,
    ) -> List[Dict[str, Any]]:
        try:
            loop = asyncio.get_event_loop()
            parsed = await loop.run_in_executor(
                None, self._fetch_sync, feed_url, max_items, feed_key
            )
            logger.info(f"📰 RSS {feed_key}: {len(parsed)} items (post-filter)")
            return parsed
        except Exception as e:
            logger.warning(f"RSS {feed_key} failed: {e}")
            return []

    def _fetch_sync(
        self,
        feed_url: str,
        max_items: int,
        feed_key: str = "",
    ) -> List[Dict[str, Any]]:
        """Synchronous parse + time filter + dedupe."""
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            logger.warning(f"feedparser error for {feed_url}: {e}")
            return []

        # Per-feed age override
        age_days = FEED_AGE_OVERRIDE_DAYS.get(feed_key, MAX_ARTICLE_AGE_DAYS)
        cutoff = datetime.now(timezone.utc) - timedelta(days=age_days)

        items: List[Dict[str, Any]] = []
        seen_titles: Set[str] = set()
        dropped_old = 0
        dropped_dup = 0

        for entry in feed.entries:
            if len(items) >= max_items:
                break

            title = (entry.get("title") or "").strip()
            if not title:
                continue

            title_key = title.lower()[:120]
            if title_key in seen_titles:
                dropped_dup += 1
                continue
            seen_titles.add(title_key)

            published_raw = (
                entry.get("published")
                or entry.get("updated")
                or entry.get("pubDate")
                or ""
            )

            published_dt = self._parse_published(published_raw)
            if published_dt is None:
                published_iso = published_raw or datetime.now(timezone.utc).isoformat()
            else:
                if published_dt < cutoff:
                    dropped_old += 1
                    continue
                published_iso = published_dt.isoformat()

            summary_raw = entry.get("summary") or entry.get("description") or ""

            items.append({
                "title": title,
                "summary": self._strip_html(summary_raw)[:500],
                "url": entry.get("link", ""),
                "source": feed.feed.get("title", ""),
                "published": published_iso,
                "published_raw": published_raw,
                "language": feed.feed.get("language", "en"),
                "tone": 0.0,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "_source_type": "rss",
            })

        if dropped_old or dropped_dup:
            logger.debug(
                f"📰 RSS {feed_key}: kept={len(items)} "
                f"dropped_old={dropped_old} dropped_dup={dropped_dup} "
                f"(age={age_days}d)"
            )

        return items

    @staticmethod
    def _parse_published(raw: str) -> Optional[datetime]:
        if not raw:
            return None

        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass

        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(raw, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                continue

        return None

    async def fetch_all_feeds(
        self,
        max_items_per_feed: int = 20,
    ) -> Dict[str, List[Dict[str, Any]]]:
        tasks = {
            key: self.fetch_feed(key, url, max_items_per_feed)
            for key, url in RSS_FEEDS.items()
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        output: Dict[str, List[Dict[str, Any]]] = {}
        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning(f"Feed {key} raised: {result}")
                output[key] = []
            else:
                output[key] = result

        total = sum(len(v) for v in output.values())
        logger.info(f"📰 RSS total: {total} items from {len(output)} feeds")
        return output

    # ------------------------------------------------------------------
    # Keyword matching with COUNTRY-LOCK + TRUSTED feeds
    # ------------------------------------------------------------------
    def _get_patterns(self, country_lower: str) -> tuple[List[re.Pattern], List[re.Pattern]]:
        """Return (primary_patterns, blocked_patterns) for a country."""
        if country_lower in self._pattern_cache:
            return self._pattern_cache[country_lower], self._blocked_cache[country_lower]

        keywords = COUNTRY_KEYWORDS.get(country_lower, [country_lower])
        patterns = [
            re.compile(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", re.IGNORECASE)
            for kw in keywords
        ]

        blocked_words = BLOCKED_CONTEXT.get(country_lower, [])
        blocked_patterns = [
            re.compile(rf"(?<![a-z]){re.escape(kw)}(?![a-z])", re.IGNORECASE)
            for kw in blocked_words
        ]

        self._pattern_cache[country_lower] = patterns
        self._blocked_cache[country_lower] = blocked_patterns
        return patterns, blocked_patterns

    async def fetch_country_feeds(
        self,
        country_name: str,
        max_items_per_feed: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Country-aware fetch with COUNTRY-LOCK + TRUSTED feed bypass.

        STEP 3C fix:
        - TRUSTED feeds (e.g. daily_star_bd for BD) keep ALL articles
          regardless of title keywords — because the feed IS the source.
        - Blocked-context check still applies (drop "India wins" in BD feed).
        - Non-trusted feeds (bbc_world etc.) still require keyword match.
        """
        country_lower = _resolve_country(country_name)

        preferred = COUNTRY_PREFERRED_FEEDS.get(country_lower)
        if preferred:
            feed_keys = [k for k in preferred if k in RSS_FEEDS]
        else:
            feed_keys = list(RSS_FEEDS.keys())

        tasks = [
            self.fetch_feed(key, RSS_FEEDS[key], max_items_per_feed)
            for key in feed_keys
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        feed_items: Dict[str, List[Dict[str, Any]]] = {}
        for key, r in zip(feed_keys, results):
            feed_items[key] = r if isinstance(r, list) else []

        patterns, blocked_patterns = self._get_patterns(country_lower)
        trusted_feeds = TRUSTED_COUNTRY_FEEDS.get(country_lower, set())

        blocked_count = 0
        keyword_matched = 0
        trusted_kept = 0

        matches: List[Dict[str, Any]] = []
        for feed_key, items in feed_items.items():
            is_trusted = feed_key in trusted_feeds

            for item in items:
                title = item.get("title", "") or ""
                summary = item.get("summary", "") or ""
                title_haystack = title
                full_haystack = f"{title} {summary}"

                # ---- Blocked-context check (title-only, strict) ----
                if blocked_patterns:
                    blocked_hit = [
                        p.pattern for p in blocked_patterns
                        if p.search(title_haystack)
                    ]
                    if blocked_hit:
                        # If another country is in the title, drop it
                        blocked_count += 1
                        continue

                # ---- Trusted feed: bypass keyword match ----
                if is_trusted:
                    item = dict(item)
                    item["feed"] = feed_key
                    item["_matched_keywords"] = ["__trusted_feed__"]
                    matches.append(item)
                    trusted_kept += 1
                    continue

                # ---- Non-trusted: require primary keyword match ----
                matched = [p.pattern for p in patterns if p.search(full_haystack)]
                if not matched:
                    continue

                item = dict(item)
                item["feed"] = feed_key
                item["_matched_keywords"] = matched
                matches.append(item)
                keyword_matched += 1

        logger.info(
            f"📰 RSS filtered: {len(matches)} items for {country_lower} "
            f"(trusted_kept={trusted_kept}, keyword_matched={keyword_matched}, "
            f"blocked_cross={blocked_count})"
        )
        return matches

    async def fetch_regional_feeds(
        self,
        region: str,
        max_items_per_feed: int = 20,
    ) -> List[Dict[str, Any]]:
        """Regional fallback when a country has too few articles."""
        region_feed_map = {
            "south_asia": [
                "daily_star_bd", "prothom_alo_en", "tbs_news", "bd_pratidin",
                "times_of_india", "the_hindu", "dawn_pakistan",
            ],
            "southeast_asia": ["jakarta_post", "bangkok_post", "straits_times"],
            "east_asia": ["scmp_asia", "japan_times", "korea_herald"],
            "middle_east": ["aljazeera", "bbc_world", "guardian_world"],
            "europe": ["bbc_world", "guardian_world", "dw_world", "france24"],
            "north_america": ["nyt_world", "bbc_world", "guardian_world"],
            "africa": ["bbc_world", "aljazeera", "guardian_world"],
            "oceania": ["bbc_world", "aljazeera", "guardian_world"],
        }

        feed_keys = region_feed_map.get(region, [])
        if not feed_keys:
            return []

        tasks = [
            self.fetch_feed(key, RSS_FEEDS[key], max_items_per_feed)
            for key in feed_keys
            if key in RSS_FEEDS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        items: List[Dict[str, Any]] = []
        for r in results:
            if isinstance(r, list):
                items.extend(r)

        logger.info(f"📰 Regional fallback [{region}]: {len(items)} items")
        return items

    @staticmethod
    def _strip_html(text: str) -> str:
        clean = re.sub(r"<[^>]+>", " ", text or "")
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()


COUNTRY_FEED_MAP = COUNTRY_PREFERRED_FEEDS