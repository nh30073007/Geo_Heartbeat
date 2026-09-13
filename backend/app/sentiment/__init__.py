"""
Sentiment Ecosystem Package - Complete

Includes:
- Base NLP pipeline (models, ingestion, preprocessing, classifier, aggregator)
- NEW: Live data ingestors (GDELT, RSS, WorldBank) + NewsAggregator
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

# ✅ NEW: Live data ingestors
from .gdelt_ingestor import GDELTIngestor
from .rss_ingestor import RSSIngestor, RSS_FEEDS, COUNTRY_FEED_MAP
from .worldbank_ingestor import WorldBankIngestor
from .news_aggregator import news_aggregator, NewsAggregator, COUNTRY_MAP

__all__ = [
    # ---- Models ----
    'SentimentLabel',
    'SentimentInput',
    'SentimentResult',
    'SentimentScore',
    'RegionalSentiment',
    'GlobalSentiment',
    'NewsArticle',
    'SocialMediaPost',
    'SentimentBatch',
    'SentimentStats',
    'Region',
    'SourceType',

    # ---- Core components ----
    'DataIngestionPipeline',
    'DataSource',
    'TextPreprocessor',
    'PreprocessConfig',
    'SentimentClassifier',
    'ModelConfig',
    'SentimentAggregator',

    # ---- NEW: Live data ----
    'GDELTIngestor',
    'RSSIngestor',
    'RSS_FEEDS',
    'COUNTRY_FEED_MAP',
    'WorldBankIngestor',
    'NewsAggregator',
    'news_aggregator',
    'COUNTRY_MAP',
]