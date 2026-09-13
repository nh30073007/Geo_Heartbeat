# backend/app/sentiment/__init__.py
"""
Sentiment Ecosystem Package - Complete

Includes:
- Base NLP pipeline (models, ingestion, preprocessing, classifier, aggregator)
- Live data ingestors (GDELT, RSS, WorldBank) + NewsAggregator
"""
from .models import (
    SentimentLabel,
    SentimentInput,
    SentimentResult,
    SentimentScore,
    RegionalSentiment,
    GlobalSentiment,
    NewsArticle,
    SocialMediaPost,
    SentimentBatch,
    SentimentStats,
    Region,
    SourceType,
)
from .ingestion import DataIngestionPipeline, DataSource
from .preprocessing import TextPreprocessor, PreprocessConfig
from .classifier import SentimentClassifier, ModelConfig
from .aggregator import SentimentAggregator

# ---- Live data ingestors ----
from .gdelt_ingestor import GDELTIngestor, gdelt_status, ENABLE_GDELT
from .rss_ingestor import RSSIngestor, RSS_FEEDS, COUNTRY_FEED_MAP

try:
    from .worldbank_ingestor import WorldBankIngestor
    _HAS_WB = True
except Exception:
    WorldBankIngestor = None  # type: ignore
    _HAS_WB = False

from .news_aggregator import news_aggregator, NewsAggregator, COUNTRY_MAP

__all__ = [
    "SentimentLabel", "SentimentInput", "SentimentResult", "SentimentScore",
    "RegionalSentiment", "GlobalSentiment", "NewsArticle", "SocialMediaPost",
    "SentimentBatch", "SentimentStats", "Region", "SourceType",

    "DataIngestionPipeline", "DataSource",
    "TextPreprocessor", "PreprocessConfig",
    "SentimentClassifier", "ModelConfig", "SentimentAggregator",

    "GDELTIngestor", "gdelt_status", "ENABLE_GDELT",
    "RSSIngestor", "RSS_FEEDS", "COUNTRY_FEED_MAP",
    "WorldBankIngestor",
    "NewsAggregator", "news_aggregator", "COUNTRY_MAP",
]