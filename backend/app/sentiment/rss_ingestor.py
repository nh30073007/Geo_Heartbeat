# backend/app/sentiment/rss_ingestor.py
"""
RSS Feed Ingestor - Real-time news from major outlets

Uses feedparser (pip install feedparser) to pull headlines from:
- BBC, Reuters, Al Jazeera, The Guardian, NYT, etc.

RSS is completely free, no API key, no rate limit. 
Only requirement: be polite (cache aggressively).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

import feedparser  # pip install feedparser

logger = logging.getLogger(__name__)


# Curated list of high-quality geopolitical RSS feeds
RSS_FEEDS = {
    # Global
    "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "reuters_world": "https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best",
    "aljazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "guardian_world": "https://www.theguardian.com/world/rss",
    "nyt_world": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "dw_world": "https://rss.dw.com/rdf/rss-en-world",
    "france24": "https://www.france24.com/en/rss",

    # Regional
    "aljazeera_middleeast": "https://www.aljazeera.com/xml/rss/all.xml",
    "scmp_asia": "https://www.scmp.com/rss/91/feed",
    "times_of_india": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "dawn_pakistan": "https://www.dawn.com/feeds/home",
    "the_hindu": "https://www.thehindu.com/news/feeder/default.rss",
    "japan_times": "https://www.japantimes.co.jp/feed/",
    "korea_herald": "https://www.koreaherald.com/common/rss_xml.php?ct=020000000000",

    # Business / Economics
    "ft_world": "https://www.ft.com/world?format=rss",
    "bloomberg_politics": "https://feeds.bloomberg.com/politics/news.rss",
    "economist": "https://www.economist.com/the-world-this-week/rss.xml",
}


class RSSIngestor:
    """Fetch and parse RSS feeds from major news outlets."""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def fetch_feed(
        self,
        feed_key: str,
        feed_url: str,
        max_items: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Fetch one RSS feed asynchronously.
        feedparser is sync, so we run it in a thread pool.
        """
        try:
            loop = asyncio.get_event_loop()
            parsed = await loop.run_in_executor(
                None, self._fetch_sync, feed_url, max_items
            )
            logger.info(f"📰 RSS {feed_key}: {len(parsed)} items")
            return parsed
        except Exception as e:
            logger.warning(f"RSS {feed_key} failed: {e}")
            return []

    def _fetch_sync(self, feed_url: str, max_items: int) -> List[Dict[str, Any]]:
        """Synchronous RSS parse — runs in executor."""
        # feedparser handles network + parsing in one call
        feed = feedparser.parse(feed_url)
        items = []

        for entry in feed.entries[:max_items]:
            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            link = entry.get("link", "")
            published = entry.get("published", "") or entry.get("updated", "")

            items.append({
                "title": title,
                "summary": self._strip_html(summary)[:500],
                "url": link,
                "source": feed.feed.get("title", ""),
                "published": published,
                "language": feed.feed.get("language", "en"),
                "tone": 0.0,  # RSS doesn't provide tone; NLP classifies later
                "fetched_at": datetime.now().isoformat(),
                "_source_type": "rss",
            })

        return items

    async def fetch_all_feeds(
        self,
        max_items_per_feed: int = 15,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all configured feeds in parallel."""
        tasks = {
            key: self.fetch_feed(key, url, max_items_per_feed)
            for key, url in RSS_FEEDS.items()
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        output = {}
        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning(f"Feed {key} raised: {result}")
                output[key] = []
            else:
                output[key] = result

        total = sum(len(v) for v in output.values())
        logger.info(f"📰 RSS total: {total} items from {len(output)} feeds")
        return output

    async def fetch_country_feeds(
        self,
        country_name: str,
        max_items_per_feed: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all feeds, filter items that mention the country.
        Case-insensitive substring match on title + summary.
        """
        all_feeds = await self.fetch_all_feeds(max_items_per_feed)
        country_lower = country_name.lower()

        matches = []
        for feed_key, items in all_feeds.items():
            for item in items:
                text = f"{item['title']} {item.get('summary', '')}".lower()
                if country_lower in text:
                    item["feed"] = feed_key
                    matches.append(item)

        logger.info(f"📰 RSS filtered: {len(matches)} items for {country_name}")
        return matches

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove HTML tags from RSS summary."""
        import re
        clean = re.sub(r"<[^>]+>", " ", text or "")
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()


# Optional: country → relevant feeds mapping
COUNTRY_FEED_MAP = {
    "india": ["times_of_india", "the_hindu", "bbc_world", "aljazeera", "guardian_world"],
    "bangladesh": ["bbc_world", "aljazeera", "guardian_world", "dw_world"],
    "pakistan": ["dawn_pakistan", "bbc_world", "aljazeera", "guardian_world"],
    "china": ["scmp_asia", "bbc_world", "aljazeera", "dw_world"],
    "us": ["nyt_world", "reuters_world", "bbc_world", "guardian_world"],
    "uk": ["bbc_world", "guardian_world", "reuters_world", "economist"],
    "iran": ["aljazeera", "aljazeera_middleeast", "bbc_world", "reuters_world"],
    "israel": ["aljazeera_middleeast", "bbc_world", "reuters_world", "guardian_world"],
    "russia": ["bbc_world", "dw_world", "aljazeera", "reuters_world"],
    "saudi": ["aljazeera_middleeast", "bbc_world", "reuters_world"],
    "japan": ["japan_times", "bbc_world", "scmp_asia"],
    "korea": ["korea_herald", "scmp_asia", "bbc_world"],
}