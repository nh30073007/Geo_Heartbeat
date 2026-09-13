"""
Data Models for Sentiment Ecosystem with:
- Pydantic validation
- Type safety
- Serialization support
- Database ready
"""
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator, ConfigDict
import numpy as np

class SentimentLabel(str, Enum):
    """Sentiment labels"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class SourceType(str, Enum):
    """Data source types"""
    KAGGLE = "kaggle"
    HUGGINGFACE = "huggingface"
    CSV = "csv"
    API = "api"
    WEBSOCKET = "websocket"
    STREAM = "stream"

class Region(str, Enum):
    """Supported regions"""
    NORTH_AMERICA = "North America"
    EUROPE = "Europe"
    ASIA_PACIFIC = "Asia Pacific"
    MIDDLE_EAST = "Middle East"
    AFRICA = "Africa"
    SOUTH_AMERICA = "South America"
    GLOBAL = "Global"

class SentimentInput(BaseModel):
    """Input for sentiment analysis"""
    text: str = Field(..., min_length=1, max_length=10000)
    region: Optional[Region] = None
    language: Optional[str] = None
    source: Optional[str] = None
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty')
        return v.strip()

class SentimentScore(BaseModel):
    """Sentiment scores"""
    positive: float = Field(0.0, ge=0.0, le=1.0)
    negative: float = Field(0.0, ge=0.0, le=1.0)
    neutral: float = Field(0.0, ge=0.0, le=1.0)
    
    @validator('positive', 'negative', 'neutral')
    def validate_scores(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Score must be between 0 and 1')
        return v
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'positive': self.positive,
            'negative': self.negative,
            'neutral': self.neutral
        }

class SentimentResult(BaseModel):
    """Complete sentiment analysis result"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    text: str
    sentiment: SentimentLabel
    scores: SentimentScore
    confidence: float = Field(..., ge=0.0, le=1.0)
    model_name: str
    region: Optional[Region] = None
    language: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Confidence must be between 0 and 1')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'sentiment': self.sentiment.value,
            'scores': self.scores.to_dict(),
            'confidence': self.confidence,
            'model_name': self.model_name,
            'region': self.region.value if self.region else None,
            'language': self.language,
            'timestamp': self.timestamp.isoformat()
        }

class RegionalSentiment(BaseModel):
    """Regional sentiment aggregation"""
    region: Region
    sentiment: SentimentLabel
    score: float = Field(..., ge=-1.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    count: int = Field(..., ge=0)
    distribution: Dict[SentimentLabel, int] = Field(default_factory=dict)
    trend: Optional[str] = None  # 'rising', 'falling', 'stable'
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'region': self.region.value,
            'sentiment': self.sentiment.value,
            'score': self.score,
            'confidence': self.confidence,
            'count': self.count,
            'distribution': {k.value: v for k, v in self.distribution.items()},
            'trend': self.trend,
            'timestamp': self.timestamp.isoformat()
        }

class GlobalSentiment(BaseModel):
    """Global sentiment aggregation"""
    sentiment: SentimentLabel
    score: float = Field(..., ge=-1.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    total_count: int = Field(..., ge=0)
    regions: List[RegionalSentiment] = Field(default_factory=list)
    topics: Dict[str, SentimentResult] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sentiment': self.sentiment.value,
            'score': self.score,
            'confidence': self.confidence,
            'total_count': self.total_count,
            'regions': [r.to_dict() for r in self.regions],
            'topics': {k: v.to_dict() for k, v in self.topics.items()},
            'timestamp': self.timestamp.isoformat()
        }

class NewsArticle(BaseModel):
    """News article model"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: Optional[str] = None
    title: str
    content: str
    source: str
    region: Region
    category: Optional[str] = None
    published_date: datetime
    author: Optional[str] = None
    url: Optional[str] = None
    sentiment: Optional[SentimentResult] = None
    keywords: List[str] = Field(default_factory=list)
    relevance_score: float = Field(0.5, ge=0.0, le=1.0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content[:500] + '...' if len(self.content) > 500 else self.content,
            'source': self.source,
            'region': self.region.value,
            'category': self.category,
            'published_date': self.published_date.isoformat(),
            'author': self.author,
            'url': self.url,
            'sentiment': self.sentiment.to_dict() if self.sentiment else None,
            'keywords': self.keywords,
            'relevance_score': self.relevance_score
        }

class SocialMediaPost(BaseModel):
    """Social media post model"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    id: Optional[str] = None
    text: str
    platform: str
    region: Region
    language: Optional[str] = None
    created_at: datetime
    user_id: Optional[str] = None
    likes: int = 0
    shares: int = 0
    comments: int = 0
    sentiment: Optional[SentimentResult] = None
    hashtags: List[str] = Field(default_factory=list)
    mentions: List[str] = Field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'text': self.text[:200] + '...' if len(self.text) > 200 else self.text,
            'platform': self.platform,
            'region': self.region.value,
            'language': self.language,
            'created_at': self.created_at.isoformat(),
            'user_id': self.user_id,
            'likes': self.likes,
            'shares': self.shares,
            'comments': self.comments,
            'sentiment': self.sentiment.to_dict() if self.sentiment else None,
            'hashtags': self.hashtags,
            'mentions': self.mentions
        }

class SentimentBatch(BaseModel):
    """Batch of sentiment analysis requests"""
    texts: List[str] = Field(..., min_items=1, max_items=100)
    region: Optional[Region] = None
    language: Optional[str] = None
    model: Optional[str] = 'ensemble'
    
    @validator('texts')
    def validate_texts(cls, v):
        if not all(t.strip() for t in v):
            raise ValueError('All texts must be non-empty')
        return [t.strip() for t in v]

class SentimentStats(BaseModel):
    """Sentiment statistics"""
    total_analyzed: int
    positive_count: int
    negative_count: int
    neutral_count: int
    avg_confidence: float
    avg_score: float
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_analyzed': self.total_analyzed,
            'positive_count': self.positive_count,
            'negative_count': self.negative_count,
            'neutral_count': self.neutral_count,
            'avg_confidence': self.avg_confidence,
            'avg_score': self.avg_score,
            'timestamp': self.timestamp.isoformat()
        }