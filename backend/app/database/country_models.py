# backend/app/database/country_models.py
"""
Country Data Models - Database models for country data

FIXED: Added `arbitrary_types_allowed=True` to CountryFullData so that
Pydantic v2 accepts SQLAlchemy ORM classes (Country, CountryEconomy, etc.)
as field types. Without this, Pydantic tries to build a JSON schema for
the ORM class and fails with PydanticSchemaGenerationError.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

Base = declarative_base()

# ============================================
# SQLAlchemy Models (Database Tables)
# ============================================

class Country(Base):
    """Country table - stores basic country information"""
    __tablename__ = 'countries'

    id = Column(String(3), primary_key=True)  # 'bd', 'us', 'uk', etc.
    name = Column(String(100), nullable=False)
    region = Column(String(50))
    population = Column(Integer)
    area = Column(Float)
    capital = Column(String(100))
    currency = Column(String(10))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'region': self.region,
            'population': self.population,
            'area': self.area,
            'capital': self.capital,
            'currency': self.currency
        }


class CountryEconomy(Base):
    """Country Economy table - stores economic metrics"""
    __tablename__ = 'country_economy'

    id = Column(Integer, primary_key=True, autoincrement=True)
    country_id = Column(String(3), nullable=False)
    gdp = Column(Float)
    gdp_growth = Column(Float)
    inflation = Column(Float)
    unemployment = Column(Float)
    foreign_reserves = Column(Float)
    debt_to_gdp = Column(Float)
    export_growth = Column(Float)
    remittance = Column(Float)
    stability_score = Column(Float)
    recorded_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'country_id': self.country_id,
            'gdp': self.gdp,
            'gdp_growth': self.gdp_growth,
            'inflation': self.inflation,
            'unemployment': self.unemployment,
            'foreign_reserves': self.foreign_reserves,
            'debt_to_gdp': self.debt_to_gdp,
            'export_growth': self.export_growth,
            'remittance': self.remittance,
            'stability_score': self.stability_score,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }


class CountryGovernment(Base):
    """Country Government table - stores government/administration data"""
    __tablename__ = 'country_government'

    id = Column(Integer, primary_key=True, autoincrement=True)
    country_id = Column(String(3), nullable=False)
    party_name = Column(String(100))
    leader_name = Column(String(100))
    start_date = Column(DateTime)
    stability_score = Column(Float)
    state_legitimacy = Column(Float)
    human_rights_score = Column(Float)
    security_score = Column(Float)
    status = Column(String(20))
    risk_factors = Column(JSON)
    strength_factors = Column(JSON)
    recorded_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'country_id': self.country_id,
            'party_name': self.party_name,
            'leader_name': self.leader_name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'stability_score': self.stability_score,
            'state_legitimacy': self.state_legitimacy,
            'human_rights_score': self.human_rights_score,
            'security_score': self.security_score,
            'status': self.status,
            'risk_factors': self.risk_factors or [],
            'strength_factors': self.strength_factors or [],
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }


class CountryCorruption(Base):
    """Country Corruption table - stores corruption and governance metrics"""
    __tablename__ = 'country_corruption'

    id = Column(Integer, primary_key=True, autoincrement=True)
    country_id = Column(String(3), nullable=False)
    cpi_score = Column(Float)
    global_rank = Column(Integer)
    perception_score = Column(Float)
    control_of_corruption = Column(Float)
    rule_of_law = Column(Float)
    government_effectiveness = Column(Float)
    regulatory_quality = Column(Float)
    bribery_score = Column(Float)
    nepotism_score = Column(Float)
    embezzlement_score = Column(Float)
    press_freedom_score = Column(Float)
    trend = Column(String(20))
    recorded_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'country_id': self.country_id,
            'cpi_score': self.cpi_score,
            'global_rank': self.global_rank,
            'perception_score': self.perception_score,
            'control_of_corruption': self.control_of_corruption,
            'rule_of_law': self.rule_of_law,
            'government_effectiveness': self.government_effectiveness,
            'regulatory_quality': self.regulatory_quality,
            'bribery_score': self.bribery_score,
            'nepotism_score': self.nepotism_score,
            'embezzlement_score': self.embezzlement_score,
            'press_freedom_score': self.press_freedom_score,
            'trend': self.trend,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }


class CountryPrediction(Base):
    """Country Prediction table - stores political predictions"""
    __tablename__ = 'country_predictions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    country_id = Column(String(3), nullable=False)
    predicted_party = Column(String(100))
    predicted_tenure_days = Column(Integer)
    confidence_score = Column(Float)
    next_party_probabilities = Column(JSON)
    best_case_tenure = Column(Integer)
    worst_case_tenure = Column(Integer)
    model_version = Column(String(20))
    predicted_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'country_id': self.country_id,
            'predicted_party': self.predicted_party,
            'predicted_tenure_days': self.predicted_tenure_days,
            'confidence_score': self.confidence_score,
            'next_party_probabilities': self.next_party_probabilities or {},
            'best_case_tenure': self.best_case_tenure,
            'worst_case_tenure': self.worst_case_tenure,
            'model_version': self.model_version,
            'predicted_at': self.predicted_at.isoformat() if self.predicted_at else None
        }


class CountrySentiment(Base):
    """Country Sentiment table - stores public sentiment data"""
    __tablename__ = 'country_sentiment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    country_id = Column(String(3), nullable=False)
    overall_sentiment = Column(Float)
    party_support = Column(JSON)
    sentiment_score = Column(Float)
    total_mentions = Column(Integer)
    source_breakdown = Column(JSON)
    top_hashtags = Column(JSON)
    emotion_distribution = Column(JSON)
    recorded_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'country_id': self.country_id,
            'overall_sentiment': self.overall_sentiment,
            'party_support': self.party_support or {},
            'sentiment_score': self.sentiment_score,
            'total_mentions': self.total_mentions,
            'source_breakdown': self.source_breakdown or {},
            'top_hashtags': self.top_hashtags or [],
            'emotion_distribution': self.emotion_distribution or {},
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }


# ============================================
# Pydantic Models (API Request/Response)
# ============================================

class CountryCreate(BaseModel):
    id: str = Field(..., min_length=2, max_length=3)
    name: str
    region: Optional[str] = None
    population: Optional[int] = None
    area: Optional[float] = None
    capital: Optional[str] = None
    currency: Optional[str] = None


class CountryUpdate(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None
    population: Optional[int] = None
    area: Optional[float] = None
    capital: Optional[str] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class EconomyData(BaseModel):
    country_id: str
    gdp: float
    gdp_growth: float
    inflation: float
    unemployment: float
    foreign_reserves: float
    debt_to_gdp: float
    stability_score: float


class GovernmentData(BaseModel):
    country_id: str
    party_name: str
    leader_name: str
    start_date: datetime
    stability_score: float
    status: str


class CorruptionData(BaseModel):
    country_id: str
    cpi_score: float
    global_rank: int
    perception_score: float
    trend: str


class PredictionData(BaseModel):
    country_id: str
    predicted_party: str
    predicted_tenure_days: int
    confidence_score: float
    next_party_probabilities: Dict[str, float]


class SentimentData(BaseModel):
    country_id: str
    overall_sentiment: float
    party_support: Dict[str, float]
    total_mentions: int
    recorded_at: datetime = Field(default_factory=datetime.now)


class CountryFullData(BaseModel):
    """
    Complete country data for dashboard.

    FIXED: Added `arbitrary_types_allowed=True` so Pydantic v2 accepts
    SQLAlchemy ORM classes as field types. Without this, model construction
    raises: "Unable to generate pydantic-core schema for <class 'Country'>".
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    country: Country
    economy: Optional[CountryEconomy] = None
    government: Optional[CountryGovernment] = None
    corruption: Optional[CountryCorruption] = None
    prediction: Optional[CountryPrediction] = None
    sentiment: Optional[CountrySentiment] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'country': self.country.to_dict() if self.country else None,
            'economy': self.economy.to_dict() if self.economy else None,
            'government': self.government.to_dict() if self.government else None,
            'corruption': self.corruption.to_dict() if self.corruption else None,
            'prediction': self.prediction.to_dict() if self.prediction else None,
            'sentiment': self.sentiment.to_dict() if self.sentiment else None
        }


# ============================================
# Enum Classes
# ============================================

class CountryStatus(str, Enum):
    STABLE = "stable"
    UNSTABLE = "unstable"
    TRANSITION = "transition"
    CRITICAL = "critical"


class TrendType(str, Enum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"


class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


# ============================================
# Database Utility Functions
# ============================================

def get_country_by_id(session, country_id: str) -> Optional[Country]:
    """Get country by ID"""
    return session.query(Country).filter(Country.id == country_id).first()


def get_latest_economy(session, country_id: str) -> Optional[CountryEconomy]:
    """Get latest economy data for a country"""
    return (
        session.query(CountryEconomy)
        .filter(CountryEconomy.country_id == country_id)
        .order_by(CountryEconomy.recorded_at.desc())
        .first()
    )


def get_latest_government(session, country_id: str) -> Optional[CountryGovernment]:
    """Get latest government data for a country"""
    return (
        session.query(CountryGovernment)
        .filter(CountryGovernment.country_id == country_id)
        .order_by(CountryGovernment.recorded_at.desc())
        .first()
    )


def get_latest_corruption(session, country_id: str) -> Optional[CountryCorruption]:
    """Get latest corruption data for a country"""
    return (
        session.query(CountryCorruption)
        .filter(CountryCorruption.country_id == country_id)
        .order_by(CountryCorruption.recorded_at.desc())
        .first()
    )


def get_latest_prediction(session, country_id: str) -> Optional[CountryPrediction]:
    """Get latest prediction for a country"""
    return (
        session.query(CountryPrediction)
        .filter(CountryPrediction.country_id == country_id)
        .order_by(CountryPrediction.predicted_at.desc())
        .first()
    )


def get_latest_sentiment(session, country_id: str) -> Optional[CountrySentiment]:
    """Get latest sentiment data for a country"""
    return (
        session.query(CountrySentiment)
        .filter(CountrySentiment.country_id == country_id)
        .order_by(CountrySentiment.recorded_at.desc())
        .first()
    )


def get_complete_country_data(session, country_id: str) -> Optional[CountryFullData]:
    """Get complete country data from all tables"""
    country = get_country_by_id(session, country_id)
    if not country:
        return None

    return CountryFullData(
        country=country,
        economy=get_latest_economy(session, country_id),
        government=get_latest_government(session, country_id),
        corruption=get_latest_corruption(session, country_id),
        prediction=get_latest_prediction(session, country_id),
        sentiment=get_latest_sentiment(session, country_id)
    )