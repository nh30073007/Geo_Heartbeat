# backend/app/database/crud.py
"""
Country CRUD Operations - Database + Runtime State Bridge

This module provides a unified interface for country data that:
1. Tries the database first (persistent data)
2. Falls back to the live simulation state (real-time data)
3. Falls back to seed data (static fallback)

This ensures the CountryCard always reflects the latest simulation state.
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from .country_models import (
    Country,
    CountryEconomy,
    CountryGovernment,
    CountryCorruption,
    CountryPrediction,
    CountrySentiment,
    get_country_by_id,
    get_latest_economy,
    get_latest_government,
    get_latest_corruption,
    get_latest_prediction,
    get_latest_sentiment,
)

logger = logging.getLogger(__name__)


# ============================================
# Database CRUD Operations
# ============================================

def create_or_update_country(
    session: Session,
    country_id: str,
    name: str,
    region: Optional[str] = None,
    population: Optional[int] = None,
    area: Optional[float] = None,
    capital: Optional[str] = None,
    currency: Optional[str] = None,
) -> Country:
    """Create or update a country record"""
    country = get_country_by_id(session, country_id)
    if country:
        country.name = name
        country.region = region or country.region
        country.population = population or country.population
        country.area = area or country.area
        country.capital = capital or country.capital
        country.currency = currency or country.currency
        country.updated_at = datetime.now()
    else:
        country = Country(
            id=country_id,
            name=name,
            region=region,
            population=population,
            area=area,
            capital=capital,
            currency=currency,
        )
        session.add(country)
    session.commit()
    session.refresh(country)
    return country


def upsert_economy(session: Session, country_id: str, **kwargs) -> CountryEconomy:
    """Insert a new economy snapshot"""
    record = CountryEconomy(country_id=country_id, **kwargs)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def upsert_government(session: Session, country_id: str, **kwargs) -> CountryGovernment:
    """Insert a new government snapshot"""
    record = CountryGovernment(country_id=country_id, **kwargs)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def upsert_sentiment(session: Session, country_id: str, **kwargs) -> CountrySentiment:
    """Insert a new sentiment snapshot"""
    record = CountrySentiment(country_id=country_id, **kwargs)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def upsert_prediction(session: Session, country_id: str, **kwargs) -> CountryPrediction:
    """Insert a new prediction snapshot"""
    record = CountryPrediction(country_id=country_id, **kwargs)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def upsert_corruption(session: Session, country_id: str, **kwargs) -> CountryCorruption:
    """Insert a new corruption snapshot"""
    record = CountryCorruption(country_id=country_id, **kwargs)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


# ============================================
# Runtime State Bridge
# ============================================

def get_country_state_from_runtime(
    country_id: str,
    runtime,
) -> Optional[Dict[str, Any]]:
    """
    Build country data from the live simulation runtime.
    
    The simulation engine exposes global state, not per-country state.
    We derive country-specific values by modulating global metrics with
    a deterministic per-country factor so the same country always maps
    to the same relative position (e.g. US > UK > BD).
    
    Args:
        country_id: ISO country id (lowercase)
        runtime: ApplicationRuntime singleton
    
    Returns:
        Dict with the same shape as get_country_data() in country.py,
        or None if the country is unknown.
    """
    country_id = (country_id or "").strip().lower()
    
    # Get all engines - use the most recently active one
    engines = list(runtime.simulation_runner.simulations.values())
    if not engines:
        return None
    
    # Most recent engine
    engine = max(
        engines,
        key=lambda e: getattr(e, "start_time", None) or datetime.min,
    )
    
    state = engine.get_state()
    env = state.get("environment", {}) or {}
    perf = state.get("performance", {}) or {}
    rl = state.get("rl_metrics", {}) or {}
    
    # Deterministic country weights (0..1) - stable across calls
    country_weights = {
        "us": 0.95, "cn": 0.85, "uk": 0.80, "de": 0.78, "fr": 0.75,
        "jp": 0.77, "in": 0.60, "br": 0.55, "ru": 0.62, "kr": 0.70,
        "ca": 0.72, "au": 0.70, "sa": 0.65, "ir": 0.50, "il": 0.68,
        "za": 0.45, "ng": 0.35, "ke": 0.30, "pk": 0.40, "bd": 0.42,
        "id": 0.48, "mx": 0.52, "ar": 0.47,
    }
    weight = country_weights.get(country_id, 0.5)
    
    # Global simulation metrics
    eco_stability = float(env.get("economic_stability", 70.0))
    tech_indep = float(env.get("technology_independence", 60.0))
    trade_stab = float(env.get("trade_stability", 65.0))
    currency_stab = float(env.get("currency_stability", 65.0))
    sentiment = float(env.get("public_sentiment", 0.0))
    tension = float(env.get("strategic_tension", 20.0))
    round_no = int(state.get("current_round", 0))
    
    # Country-specific modulation
    country_eco = eco_stability * (0.6 + 0.4 * weight)
    country_tech = tech_indep * (0.5 + 0.5 * weight)
    country_trade = trade_stab * (0.6 + 0.4 * weight)
    
    # GDP derived from economic stability & weight
    base_gdp = 500.0 + (weight ** 2) * 25000.0
    gdp_growth = (country_eco - 50.0) / 10.0  # -5% .. +5%
    inflation = max(0.5, 8.0 - weight * 5.0 + (100.0 - country_eco) / 20.0)
    unemployment = max(2.0, 9.0 - weight * 5.0 + (100.0 - country_eco) / 15.0)
    foreign_reserves = base_gdp * 0.15
    debt_to_gdp = 30.0 + (1.0 - weight) * 100.0 + (100.0 - country_eco) / 5.0
    
    # Government derived from stability + tension
    stability_score = max(0.0, min(100.0, country_eco - tension * 0.5))
    government_status = (
        "stable" if stability_score >= 60
        else "transition" if stability_score >= 40
        else "unstable"
    )
    
    # Prediction derived from stability
    confidence = max(0.1, min(0.95, stability_score / 100.0))
    predicted_tenure_days = int(365 + confidence * 1460)
    best_case = int(predicted_tenure_days * 1.3)
    worst_case = int(predicted_tenure_days * 0.6)
    
    # Sentiment: scale global sentiment into 0..100 party support
    party_a = int(max(10, min(85, 50 + sentiment * 40 + weight * 10)))
    party_b = max(5, 100 - party_a - 10)
    party_c = max(5, 100 - party_a - party_b)
    
    # Corruption: inversely related to stability
    cpi = int(max(10, min(95, stability_score)))
    rank = int(max(1, min(180, 180 - cpi)))
    
    return {
        "country": {
            "id": country_id,
            "name": _country_name(country_id),
            "code": country_id.upper(),
            "region": _country_region(country_id),
            "capital": "N/A",
            "population": int(50_000_000 * (0.3 + weight)),
            "area": 0,
            "currency": "USD",
            "flag": "🌐",
        },
        "economy": {
            "gdp": round(base_gdp, 1),
            "gdp_growth": round(gdp_growth, 2),
            "inflation": round(inflation, 2),
            "unemployment": round(unemployment, 2),
            "foreign_reserves": round(foreign_reserves, 1),
            "debt_to_gdp": round(debt_to_gdp, 1),
            "export_growth": round(gdp_growth * 1.2, 2),
            "remittance": 0.0,
            "stability_score": round(stability_score, 1),
            "round": round_no,
        },
        "government": {
            "party_name": f"Party {country_id.upper()}",
            "leader_name": f"Leader {country_id.upper()}",
            "start_date": "2024-01-01",
            "stability_score": round(stability_score, 1),
            "state_legitimacy": round(stability_score * 0.9, 1),
            "human_rights_score": round(stability_score * 0.8, 1),
            "security_score": round(stability_score * 0.95, 1),
            "status": government_status,
            "risk_factors": ["economic_pressure"] if country_eco < 60 else [],
            "strength_factors": ["strategic_position"] if country_eco > 70 else [],
            "round": round_no,
        },
        "sentiment": {
            "overall_sentiment": round(sentiment, 3),
            "party_support": {
                f"Party A": party_a,
                f"Party B": party_b,
                f"Party C": party_c,
            },
            "sentiment_score": round(sentiment, 3),
            "total_mentions": 1000 + round_no * 10,
            "source_breakdown": {"social": 45, "news": 35, "blogs": 20},
            "top_hashtags": [f"#{country_id.upper()}", "#Simulation"],
            "emotion_distribution": {
                "positive": int(max(0, 50 + sentiment * 50)),
                "negative": int(max(0, 50 - sentiment * 50)),
                "neutral": 30,
            },
            "round": round_no,
        },
        "prediction": {
            "predicted_party": f"Party A",
            "predicted_tenure_days": predicted_tenure_days,
            "confidence_score": round(confidence, 2),
            "next_party_probabilities": {
                "Party A": round(confidence, 2),
                "Party B": round((1 - confidence) * 0.6, 2),
                "Party C": round((1 - confidence) * 0.4, 2),
            },
            "best_case_tenure": best_case,
            "worst_case_tenure": worst_case,
            "round": round_no,
        },
        "corruption": {
            "cpi_score": cpi,
            "global_rank": rank,
            "perception_score": cpi,
            "control_of_corruption": (cpi - 50) / 25.0,
            "rule_of_law": (cpi - 50) / 25.0,
            "government_effectiveness": (cpi - 50) / 25.0,
            "regulatory_quality": (cpi - 50) / 25.0,
            "bribery_score": 100 - cpi,
            "nepotism_score": 100 - cpi,
            "embezzlement_score": 100 - cpi,
            "press_freedom_score": cpi,
            "trend": "improving" if gdp_growth > 0 else "declining",
            "round": round_no,
        },
        "_source": "runtime",
        "_round": round_no,
        "_timestamp": datetime.now().isoformat(),
    }


# ============================================
# Data Access Layer (DB + Runtime + Fallback)
# ============================================

def get_country_full_data(
    session: Optional[Session],
    country_id: str,
    runtime=None,
) -> Optional[Dict[str, Any]]:
    """
    Unified country data accessor.
    
    Priority:
    1. Live runtime state (real-time simulation)
    2. Database (persistent snapshots)
    3. Static fallback (in country.py)
    """
    country_id = (country_id or "").strip().lower()
    if not country_id:
        return None
    
    # 1. Try runtime (highest priority - real-time)
    if runtime is not None:
        try:
            runtime_data = get_country_state_from_runtime(country_id, runtime)
            if runtime_data is not None:
                logger.info(f"📡 [{country_id}] Data from runtime (round={runtime_data.get('_round')})")
                return runtime_data
        except Exception as e:
            logger.warning(f"Runtime lookup failed for {country_id}: {e}")
    
    # 2. Try database
    if session is not None:
        try:
            country = get_country_by_id(session, country_id)
            if country:
                db_data = _build_from_db(session, country)
                if db_data:
                    logger.info(f"💾 [{country_id}] Data from database")
                    return db_data
        except Exception as e:
            logger.warning(f"DB lookup failed for {country_id}: {e}")
    
    # 3. None - caller will use static fallback
    return None


def _build_from_db(session: Session, country: Country) -> Dict[str, Any]:
    """Assemble full country data from DB tables"""
    economy = get_latest_economy(session, country.id)
    government = get_latest_government(session, country.id)
    corruption = get_latest_corruption(session, country.id)
    prediction = get_latest_prediction(session, country.id)
    sentiment = get_latest_sentiment(session, country.id)
    
    return {
        "country": country.to_dict(),
        "economy": economy.to_dict() if economy else {},
        "government": government.to_dict() if government else {},
        "corruption": corruption.to_dict() if corruption else {},
        "prediction": prediction.to_dict() if prediction else {},
        "sentiment": sentiment.to_dict() if sentiment else {},
        "_source": "database",
    }


# ============================================
# Helper maps (fallback metadata)
# ============================================

_COUNTRY_NAMES = {
    "us": "United States", "cn": "China", "uk": "United Kingdom",
    "de": "Germany", "fr": "France", "jp": "Japan", "in": "India",
    "br": "Brazil", "ru": "Russia", "kr": "South Korea",
    "ca": "Canada", "au": "Australia", "sa": "Saudi Arabia",
    "ir": "Iran", "il": "Israel", "za": "South Africa",
    "ng": "Nigeria", "ke": "Kenya", "pk": "Pakistan",
    "bd": "Bangladesh", "id": "Indonesia", "mx": "Mexico",
    "ar": "Argentina",
}

_COUNTRY_REGIONS = {
    "us": "North America", "ca": "North America", "mx": "North America",
    "br": "South America", "ar": "South America",
    "uk": "Europe", "de": "Europe", "fr": "Europe", "ru": "Europe",
    "cn": "East Asia", "jp": "East Asia", "kr": "East Asia",
    "in": "South Asia", "bd": "South Asia", "pk": "South Asia",
    "id": "Asia Pacific", "au": "Asia Pacific",
    "sa": "Middle East", "ir": "Middle East", "il": "Middle East",
    "za": "Africa", "ng": "Africa", "ke": "Africa",
}


def _country_name(country_id: str) -> str:
    return _COUNTRY_NAMES.get(country_id, country_id.upper())


def _country_region(country_id: str) -> str:
    return _COUNTRY_REGIONS.get(country_id, "Global")