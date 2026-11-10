# backend/app/api/routes/country.py
"""
Country API Routes - Real-time country data from simulation runtime

STEP 3B fixes:
- sentiment.overall_sentiment is now HYBRID (live RSS + simulated fallback)
- Added _meta flag when sentiment is stale/zero
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from datetime import datetime

from ...core.runtime import runtime
from ...database.crud import get_country_full_data, _country_name, _country_region

logger = logging.getLogger(__name__)

router = APIRouter(tags=["country"])

MAP_COUNTRY_IDS = {
    "us","ca","mx","br","ar","uk","fr","de","ru","cn","in","bd","pk","jp","kr",
    "id","sa","ir","il","za","ng","ke","au"
}


def _build_sources_metadata(country_id: str) -> Dict[str, str]:
    return {
        # ----- Economy (LIVE — WorldBank) -----
        "economy.gdp": "live",
        "economy.gdp_growth": "live",
        "economy.inflation": "live",
        "economy.unemployment": "live",
        "economy.foreign_reserves": "hybrid",
        "economy.debt_to_gdp": "live",
        "economy.export_growth": "hybrid",
        "economy.remittance": "hybrid",
        "economy.stability_score": "simulated",

        # ----- Government (SIMULATED — RL agent) -----
        "government.status": "simulated",
        "government.party_name": "simulated",
        "government.leader_name": "simulated",
        "government.stability_score": "simulated",
        "government.state_legitimacy": "simulated",
        "government.human_rights_score": "simulated",
        "government.security_score": "simulated",

        # ----- Corruption (STATIC) -----
        "corruption.cpi_score": "static",
        "corruption.global_rank": "static",
        "corruption.perception_score": "static",
        "corruption.control_of_corruption": "static",
        "corruption.rule_of_law": "static",
        "corruption.government_effectiveness": "static",
        "corruption.regulatory_quality": "static",
        "corruption.bribery_score": "static",
        "corruption.nepotism_score": "static",
        "corruption.embezzlement_score": "static",
        "corruption.press_freedom_score": "static",

        # ----- Prediction (SIMULATED) -----
        "prediction.predicted_tenure_days": "simulated",
        "prediction.confidence_score": "simulated",
        "prediction.predicted_party": "simulated",
        "prediction.next_party_probabilities": "simulated",
        "prediction.best_case_tenure": "simulated",
        "prediction.worst_case_tenure": "simulated",

        # ----- Sentiment (HYBRID — live RSS + heuristic fallback) -----
        # FIX 3B: changed "live" → "hybrid" because BD feeds often
        # fall back to heuristic scoring when RSS returns 0 items.
        "sentiment.overall_sentiment": "hybrid",
        "sentiment.sentiment_score": "hybrid",
        "sentiment.total_mentions": "hybrid",
        "sentiment.source_breakdown": "live",
        "sentiment.party_support": "hybrid",
        "sentiment.emotion_distribution": "simulated",
        "sentiment.top_hashtags": "live",
    }


def _static_fallback(country_id: str) -> Dict[str, Any] | None:
    if country_id not in MAP_COUNTRY_IDS:
        return None
    return {
        "country": {
            "id": country_id, "name": _country_name(country_id),
            "code": country_id.upper(), "region": _country_region(country_id),
            "capital": "N/A", "population": 0, "area": 0, "currency": "USD", "flag": "🌐",
        },
        "economy": {"gdp": 100.0, "gdp_growth": 2.0, "inflation": 4.0,
                    "unemployment": 5.0, "foreign_reserves": 50.0,
                    "debt_to_gdp": 60.0, "export_growth": 3.0,
                    "remittance": 0.0, "stability_score": 60.0},
        "government": {"party_name": "N/A", "leader_name": "N/A",
                       "start_date": "2000-01-01", "stability_score": 60.0,
                       "state_legitimacy": 60.0, "human_rights_score": 60.0,
                       "security_score": 60.0, "status": "stable",
                       "risk_factors": [], "strength_factors": []},
        "corruption": {"cpi_score": 50.0, "global_rank": 90, "perception_score": 50.0,
                       "control_of_corruption": 0.0, "rule_of_law": 0.0,
                       "government_effectiveness": 0.0, "regulatory_quality": 0.0,
                       "bribery_score": 50.0, "nepotism_score": 50.0,
                       "embezzlement_score": 50.0, "press_freedom_score": 50.0,
                       "trend": "stable"},
        "prediction": {"predicted_party": "N/A", "predicted_tenure_days": 365,
                       "confidence_score": 0.25,
                       "next_party_probabilities": {"N/A": 1.0},
                       "best_case_tenure": 540, "worst_case_tenure": 180},
        "sentiment": {"overall_sentiment": 0.0, "party_support": {},
                      "sentiment_score": 0.0, "total_mentions": 0,
                      "source_breakdown": {}, "top_hashtags": [],
                      "emotion_distribution": {"positive": 0, "negative": 0, "neutral": 100}},
        "_source": "static_fallback",
    }


@router.get("/country")
async def list_countries() -> Dict[str, Any]:
    countries = [{"id": cid, "name": _country_name(cid), "code": cid.upper(),
                  "flag": "🌐", "region": _country_region(cid)}
                 for cid in sorted(MAP_COUNTRY_IDS)]
    return {"success": True, "data": {"countries": countries, "total": len(countries)}}


@router.get("/country/{country_id}")
async def get_country_dashboard(country_id: str) -> Dict[str, Any]:
    country_id = (country_id or "").strip().lower()

    data = get_country_full_data(session=None, country_id=country_id, runtime=runtime)
    if data is None:
        data = _static_fallback(country_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Country '{country_id}' not found")

    engines = list(runtime.simulation_runner.simulations.values())
    data["_live"] = bool(engines)
    data["_simulation_count"] = len(engines)
    data["_fetched_at"] = datetime.now().isoformat()
    data["_sources"] = _build_sources_metadata(country_id)

    try:
        from ...sentiment.news_aggregator import news_aggregator
        news = await news_aggregator.fetch_country(country_id, force_refresh=False)
        if news:
            news_sent = news.get("sentiment_score", 0.0)
            if news_sent == 0.0:
                news_sent = news.get("overall_sentiment", 0.0)

            data["_meta"] = {
                "country_id": country_id,
                "news_attached": True,
                "news_article_count": news.get("article_count", 0),
                "news_sentiment": news_sent,
                "news_fetched_at": news.get("fetched_at"),
                # STEP 3B: flag when RSS returned 0 — frontend shows HYB badge
                "news_stale": news.get("rss_count", 0) == 0,
            }
            if "sentiment" in data and isinstance(data["sentiment"], dict):
                existing_sent = data["sentiment"].get("sentiment_score", 0.0)
                final_sent = news_sent if news_sent != 0.0 else existing_sent

                data["sentiment"]["sentiment_score"] = final_sent
                data["sentiment"]["overall_sentiment"] = final_sent
                data["sentiment"]["total_mentions"] = news.get("article_count", 0)
                data["sentiment"]["source_breakdown"] = {
                    "rss": news.get("rss_count", 0),
                    "gdelt": news.get("gdelt_count", 0),
                }
                data["sentiment"]["recorded_at"] = news.get("fetched_at")
        else:
            data["_meta"] = {"country_id": country_id, "news_attached": False}
    except Exception as e:
        logger.debug(f"Live sentiment attach failed for {country_id}: {e}")
        data["_meta"] = {
            "country_id": country_id, "news_attached": False, "error": str(e),
        }

    logger.info(
        f"📊 [{country_id}] source={data.get('_source')} "
        f"round={data.get('_round', 'n/a')} live={data['_live']} "
        f"news_attached={data['_meta'].get('news_attached')} "
        f"sentiment={data.get('sentiment', {}).get('sentiment_score', 'n/a')}"
    )

    return {"success": True, "data": data}


@router.get("/country/{country_id}/economy")
async def get_country_economy(country_id: str) -> Dict[str, Any]:
    data = get_country_full_data(None, country_id.lower(), runtime) or _static_fallback(country_id.lower())
    if not data:
        raise HTTPException(404, f"Country '{country_id}' not found")
    return {"success": True, "data": {
        "country_id": country_id.lower(), "country_name": data["country"]["name"],
        **data["economy"], "round": data.get("_round", 0),
        "_source": data.get("_source"), "recorded_at": datetime.now().isoformat(),
        "_sources": _build_sources_metadata(country_id.lower())}}


@router.get("/country/{country_id}/government")
async def get_country_government(country_id: str) -> Dict[str, Any]:
    data = get_country_full_data(None, country_id.lower(), runtime) or _static_fallback(country_id.lower())
    if not data:
        raise HTTPException(404, f"Country '{country_id}' not found")
    return {"success": True, "data": {
        "country_id": country_id.lower(), "country_name": data["country"]["name"],
        **data["government"], "round": data.get("_round", 0),
        "_source": data.get("_source"), "recorded_at": datetime.now().isoformat(),
        "_sources": _build_sources_metadata(country_id.lower())}}


@router.get("/country/{country_id}/sentiment")
async def get_country_sentiment(country_id: str) -> Dict[str, Any]:
    data = get_country_full_data(None, country_id.lower(), runtime) or _static_fallback(country_id.lower())
    if not data:
        raise HTTPException(404, f"Country '{country_id}' not found")
    return {"success": True, "data": {
        "country_id": country_id.lower(), "country_name": data["country"]["name"],
        **data["sentiment"], "round": data.get("_round", 0),
        "_source": data.get("_source"), "recorded_at": datetime.now().isoformat(),
        "_sources": _build_sources_metadata(country_id.lower())}}


@router.get("/country/{country_id}/prediction")
async def get_country_prediction(country_id: str) -> Dict[str, Any]:
    data = get_country_full_data(None, country_id.lower(), runtime) or _static_fallback(country_id.lower())
    if not data:
        raise HTTPException(404, f"Country '{country_id}' not found")
    return {"success": True, "data": {
        "country_id": country_id.lower(), "country_name": data["country"]["name"],
        **data["prediction"], "round": data.get("_round", 0),
        "_source": data.get("_source"), "predicted_at": datetime.now().isoformat(),
        "_sources": _build_sources_metadata(country_id.lower())}}


@router.get("/country/{country_id}/corruption")
async def get_country_corruption(country_id: str) -> Dict[str, Any]:
    data = get_country_full_data(None, country_id.lower(), runtime) or _static_fallback(country_id.lower())
    if not data:
        raise HTTPException(404, f"Country '{country_id}' not found")
    return {"success": True, "data": {
        "country_id": country_id.lower(), "country_name": data["country"]["name"],
        **data["corruption"], "round": data.get("_round", 0),
        "_source": data.get("_source"), "recorded_at": datetime.now().isoformat(),
        "_sources": _build_sources_metadata(country_id.lower())}}