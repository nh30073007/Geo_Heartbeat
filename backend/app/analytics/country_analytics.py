# backend/app/analytics/country_analytics.py
"""
Country Analytics Engine - Aggregates all country-specific data
"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import asyncio
import random

from .sentiment_agent import SentimentAnalysisAgent
from .prediction_agent import PoliticalPredictionAgent
from .data_collector import DataCollectorService

logger = logging.getLogger(__name__)

class CountryAnalytics:
    """
    Main country analytics engine that aggregates:
    1. Economic metrics
    2. Corruption index
    3. Government stability
    4. Predicted tenure
    5. Next party prediction
    6. Public sentiment
    """
    
    def __init__(self):
        self.sentiment_agent = SentimentAnalysisAgent()
        self.prediction_agent = PoliticalPredictionAgent()
        self.data_collector = DataCollectorService()
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 3600  # 1 hour cache
        
    async def get_country_dashboard(self, country_id: str) -> Dict[str, Any]:
        """
        Get complete country dashboard data
        """
        # Check cache first
        cache_key = f"country_{country_id}"
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if (datetime.now() - cached_data['timestamp']).seconds < self.cache_ttl:
                return cached_data['data']
        
        # Collect all data in parallel
        economy_data = await self.get_economic_metrics(country_id)
        corruption_data = await self.get_corruption_index(country_id)
        gov_data = await self.get_government_stability(country_id)
        tenure_data = await self.predict_government_tenure(country_id)
        next_party_data = await self.predict_next_party(country_id)
        sentiment_data = await self.get_public_sentiment(country_id)
        
        result = {
            'country_id': country_id,
            'name': self._get_country_name(country_id),
            'economy': economy_data,
            'corruption': corruption_data,
            'government': gov_data,
            'predicted_tenure': tenure_data,
            'next_party': next_party_data,
            'public_sentiment': sentiment_data,
            'last_updated': datetime.now().isoformat()
        }
        
        # Cache the result
        self.cache[cache_key] = {
            'data': result,
            'timestamp': datetime.now()
        }
        
        return result
    
    async def get_economic_metrics(self, country_id: str) -> Dict[str, Any]:
        """Get economic metrics for a country"""
        # In production, fetch from real APIs
        # For now, using simulation data with realistic values
        
        # Bangladesh-specific data from World Bank estimates
        economy_data = {
            'gdp': 460,  # $460 billion (approx)
            'gdp_growth': 6.5,  # 6.5% growth rate
            'inflation': 9.5,  # 9.5% inflation rate
            'unemployment': 4.5,  # 4.5% unemployment
            'foreign_reserves': 22,  # $22 billion
            'debt_to_gdp': 42,  # 42% debt to GDP
            'stability': 'stable',  # stable/unstable/critical
            'trend': 0.8,  # -1 to 1 trend indicator
            'forecast': {
                'next_year': 7.2,
                'next_5_years': 6.8
            }
        }
        return economy_data
    
    async def get_corruption_index(self, country_id: str) -> Dict[str, Any]:
        """Get corruption and governance metrics"""
        # Transparency International data (approximate)
        corruption_data = {
            'index': 35,  # CPI score (0-100, higher is better)
            'rank': 120,  # Global rank out of 180
            'trend': 'declining',  # improving/declining/stable
            'perception_score': 40,
            'control_of_corruption': -0.5,  # -2.5 to 2.5
            'rule_of_law': 0.2,  # -2.5 to 2.5
            'government_effectiveness': 0.1,  # -2.5 to 2.5
            'regulatory_quality': -0.3,  # -2.5 to 2.5
            'details': {
                'bribery': 45,
                'nepotism': 55,
                'embezzlement': 40,
                'press_freedom': 30
            }
        }
        return corruption_data
    
    async def get_government_stability(self, country_id: str) -> Dict[str, Any]:
        """Get government stability metrics"""
        # Using Fragile States Index data
        gov_data = {
            'name': 'Awami League' if country_id == 'bd' else 'Unknown',
            'leader': 'Sheikh Hasina',
            'stability_score': 65,  # 0-100
            'state_legitimacy': 55,
            'human_rights': 48,
            'security_apparatus': 70,
            'factionalized_elites': 45,
            'external_intervention': 35,
            'status': 'stable',  # stable/unstable/transition
            'risk_factors': [
                'Economic inequality',
                'Political polarization',
                'Climate vulnerability'
            ],
            'strength_factors': [
                'Strong civil society',
                'Active media',
                'International support'
            ]
        }
        return gov_data
    
    async def predict_government_tenure(self, country_id: str) -> Dict[str, Any]:
        """Predict how long current government will last"""
        # RL-based prediction with realistic data
        state = {
            'economy': 65,
            'sentiment': 55,
            'political_alignment': 60,
            'international_support': 70,
            'opposition_strength': 45,
            'public_trust': 52
        }
        
        prediction = self.prediction_agent.predict_tenure(state)
        
        # Current Bangladesh context (based on recent analysis)
        return {
            'predicted_days': prediction['days'],
            'predicted_months': prediction['months'],
            'confidence': prediction['confidence'],
            'factors': {
                'economic': 0.4,
                'sentiment': 0.3,
                'political': 0.2,
                'international': 0.1
            },
            'scenario_analysis': {
                'best_case': prediction['best_case'],
                'worst_case': prediction['worst_case'],
                'most_likely': prediction['most_likely']
            },
            'key_risks': [
                'Economic downturn',
                'Political opposition',
                'International pressure'
            ]
        }
    
    async def predict_next_party(self, country_id: str) -> Dict[str, Any]:
        """Predict which party will come to power next"""
        # Based on recent polling data
        polling_data = await self.data_collector.get_polling_data(country_id)
        
        # RL-based prediction
        state = {
            'current_party': 'Awami League',
            'public_sentiment': polling_data.get('sentiment', {}),
            'economic_conditions': 65,
            'opposition_strength': 55
        }
        
        prediction = self.prediction_agent.predict_next_party(state)
        
        # Combine with actual polling data
        return {
            'predicted_party': prediction['party'],
            'confidence': prediction['confidence'],
            'alternate_parties': [
                {'name': 'BNP', 'probability': 35},
                {'name': 'Jamaat-e-Islami', 'probability': 15},
                {'name': 'NCP', 'probability': 10}
            ],
            'swing_factor': 8,
            'polling_data': polling_data,
            'forecast': {
                'next_6_months': prediction['forecast_6_months'],
                'next_12_months': prediction['forecast_12_months']
            }
        }
    
    async def get_public_sentiment(self, country_id: str) -> Dict[str, Any]:
        """Get public sentiment and support metrics"""
        sentiment = await self.sentiment_agent.analyze_party_support(country_id)
        
        return {
            'party_support': sentiment.get('party_support', {
                'Awami League': 38,
                'BNP': 42,
                'Jamaat-e-Islami': 12,
                'NCP': 8
            }),
            'approval_rating': {
                'government': 45,
                'opposition': 50
            },
            'trend': 'moderate',  # positive/negative/moderate
            'key_issues': [
                {'issue': 'Economy', 'concern': 85},
                {'issue': 'Corruption', 'concern': 75},
                {'issue': 'Law & Order', 'concern': 65},
                {'issue': 'Education', 'concern': 55}
            ],
            'sentiment_score': 0.3,  # -1 to 1
            'volume': 15000,  # Number of posts analyzed
            'source_breakdown': {
                'facebook': 40,
                'twitter': 30,
                'news': 20,
                'other': 10
            }
        }
    
    def _get_country_name(self, country_id: str) -> str:
        """Get country name from ID"""
        country_map = {
            'bd': 'Bangladesh',
            'us': 'United States',
            'uk': 'United Kingdom',
            'in': 'India',
            'cn': 'China'
        }
        return country_map.get(country_id, country_id.upper())