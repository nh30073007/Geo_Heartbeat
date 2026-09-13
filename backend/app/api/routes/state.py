"""
Advanced State Routes with:
- Real-time state access
- History queries
- Region-specific data
- State comparison
- State export/import
- Country-specific data for World Map
"""
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import logging
from pathlib import Path

from ...environment import EnvironmentState
from ...simulation import SimulationRunner
from ...core.runtime import runtime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/state", tags=["state"])

# Global instances
simulation_runner = runtime.simulation_runner

# Response Models
class StateResponse(BaseModel):
    """State response"""
    state: Dict[str, Any]
    timestamp: str
    round: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class StateHistoryResponse(BaseModel):
    """State history response"""
    total: int
    history: List[Dict[str, Any]]
    timestamp: str

class CountryDataResponse(BaseModel):
    """Country data response"""
    country: str
    country_code: str
    data: Dict[str, Any]
    timestamp: str

# Routes
@router.get("/current/{sim_id}")
async def get_current_state(sim_id: str):
    """
    Get current state of a simulation
    """
    try:
        # Check if simulation exists in memory
        if sim_id not in simulation_runner.simulations:
            # Try to recover from cache
            engine = runtime._load_simulation_from_cache(sim_id)
            if engine:
                simulation_runner.simulations[sim_id] = engine
                logger.info(f"♻️ Recovered simulation for state: {sim_id}")
            else:
                raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
        
        engine = simulation_runner.simulations[sim_id]
        state = engine.get_state()
        
        return {
            'sim_id': sim_id,
            'state': state,
            'round': engine.current_round,
            'status': engine.status.value,
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get current state: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ✅ NEW: Country-specific data endpoint for World Map
@router.get("/country/{sim_id}/{country_code}")
async def get_country_data(sim_id: str, country_code: str):
    """
    Get data for a specific country in the simulation
    """
    try:
        if sim_id not in simulation_runner.simulations:
            engine = runtime._load_simulation_from_cache(sim_id)
            if engine:
                simulation_runner.simulations[sim_id] = engine
                logger.info(f"♻️ Recovered simulation for country data: {sim_id}")
            else:
                raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
        
        engine = simulation_runner.simulations[sim_id]
        
        # Get global state
        global_state = engine.get_state()
        environment_state = global_state.get('environment', {})
        
        # Country data mapping with realistic values based on simulation state
        # Base values from simulation
        economic = environment_state.get('economic_stability', 74)
        tension = environment_state.get('strategic_tension', 30)
        tech = environment_state.get('technology_independence', 69)
        trade = environment_state.get('trade_stability', 72)
        supply = environment_state.get('supply_chain_stability', 71)
        ai = environment_state.get('ai_capability', 77)
        sentiment = environment_state.get('public_sentiment', 0.18)
        
        # Country-specific data with realistic modifiers
        country_data = {
            'US': {
                'name': 'United States',
                'economy': round(min(100, economic * 1.0), 1),
                'power_balance': round(min(100, 75 + tension * 0.3), 1),
                'tech_index': round(min(100, tech * 1.1), 1),
                'military': round(min(100, 80 + tension * 0.25), 1),
                'diplomacy': round(max(0, 75 - tension * 0.3), 1),
                'stability': round(min(100, economic), 1),
                'trade': round(min(100, trade), 1),
                'sentiment': round(max(-1, min(1, sentiment * 1.2)), 2),
                'supply_chain': round(min(100, supply), 1),
                'ai_capability': round(min(100, ai * 1.1), 1),
                'region': 'North America'
            },
            'CN': {
                'name': 'China',
                'economy': round(min(100, economic * 0.92), 1),
                'power_balance': round(min(100, 70 + tension * 0.35), 1),
                'tech_index': round(min(100, tech * 0.95), 1),
                'military': round(min(100, 75 + tension * 0.3), 1),
                'diplomacy': round(max(0, 70 - tension * 0.35), 1),
                'stability': round(min(100, economic * 0.9), 1),
                'trade': round(min(100, trade * 0.95), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.8)), 2),
                'supply_chain': round(min(100, supply * 0.9), 1),
                'ai_capability': round(min(100, ai * 0.85), 1),
                'region': 'Asia Pacific'
            },
            'RU': {
                'name': 'Russia',
                'economy': round(min(100, economic * 0.7), 1),
                'power_balance': round(min(100, 65 + tension * 0.4), 1),
                'tech_index': round(min(100, tech * 0.7), 1),
                'military': round(min(100, 70 + tension * 0.4), 1),
                'diplomacy': round(max(0, 60 - tension * 0.4), 1),
                'stability': round(min(100, economic * 0.7), 1),
                'trade': round(min(100, trade * 0.7), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.6)), 2),
                'supply_chain': round(min(100, supply * 0.7), 1),
                'ai_capability': round(min(100, ai * 0.6), 1),
                'region': 'Eurasia'
            },
            'GB': {
                'name': 'United Kingdom',
                'economy': round(min(100, economic * 0.85), 1),
                'power_balance': round(min(100, 65 + tension * 0.2), 1),
                'tech_index': round(min(100, tech * 0.9), 1),
                'military': round(min(100, 70 + tension * 0.15), 1),
                'diplomacy': round(max(0, 80 - tension * 0.2), 1),
                'stability': round(min(100, economic * 0.85), 1),
                'trade': round(min(100, trade * 0.9), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.9)), 2),
                'supply_chain': round(min(100, supply * 0.85), 1),
                'ai_capability': round(min(100, ai * 0.85), 1),
                'region': 'Europe'
            },
            'FR': {
                'name': 'France',
                'economy': round(min(100, economic * 0.82), 1),
                'power_balance': round(min(100, 60 + tension * 0.2), 1),
                'tech_index': round(min(100, tech * 0.85), 1),
                'military': round(min(100, 65 + tension * 0.15), 1),
                'diplomacy': round(max(0, 78 - tension * 0.2), 1),
                'stability': round(min(100, economic * 0.82), 1),
                'trade': round(min(100, trade * 0.85), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.85)), 2),
                'supply_chain': round(min(100, supply * 0.82), 1),
                'ai_capability': round(min(100, ai * 0.8), 1),
                'region': 'Europe'
            },
            'DE': {
                'name': 'Germany',
                'economy': round(min(100, economic * 0.88), 1),
                'power_balance': round(min(100, 55 + tension * 0.1), 1),
                'tech_index': round(min(100, tech * 0.9), 1),
                'military': round(min(100, 60 + tension * 0.1), 1),
                'diplomacy': round(max(0, 82 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.88), 1),
                'trade': round(min(100, trade * 0.9), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.85)), 2),
                'supply_chain': round(min(100, supply * 0.85), 1),
                'ai_capability': round(min(100, ai * 0.85), 1),
                'region': 'Europe'
            },
            'JP': {
                'name': 'Japan',
                'economy': round(min(100, economic * 0.9), 1),
                'power_balance': round(min(100, 50 + tension * 0.1), 1),
                'tech_index': round(min(100, tech * 1.0), 1),
                'military': round(min(100, 55 + tension * 0.1), 1),
                'diplomacy': round(max(0, 72 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.9), 1),
                'trade': round(min(100, trade * 0.9), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.8)), 2),
                'supply_chain': round(min(100, supply * 0.9), 1),
                'ai_capability': round(min(100, ai * 0.95), 1),
                'region': 'Asia Pacific'
            },
            'IN': {
                'name': 'India',
                'economy': round(min(100, economic * 0.8), 1),
                'power_balance': round(min(100, 60 + tension * 0.25), 1),
                'tech_index': round(min(100, tech * 0.8), 1),
                'military': round(min(100, 65 + tension * 0.2), 1),
                'diplomacy': round(max(0, 75 - tension * 0.25), 1),
                'stability': round(min(100, economic * 0.8), 1),
                'trade': round(min(100, trade * 0.8), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.9)), 2),
                'supply_chain': round(min(100, supply * 0.8), 1),
                'ai_capability': round(min(100, ai * 0.7), 1),
                'region': 'Asia Pacific'
            },
            'BR': {
                'name': 'Brazil',
                'economy': round(min(100, economic * 0.7), 1),
                'power_balance': round(min(100, 45 + tension * 0.15), 1),
                'tech_index': round(min(100, tech * 0.6), 1),
                'military': round(min(100, 50 + tension * 0.1), 1),
                'diplomacy': round(max(0, 70 - tension * 0.2), 1),
                'stability': round(min(100, economic * 0.7), 1),
                'trade': round(min(100, trade * 0.7), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.7)), 2),
                'supply_chain': round(min(100, supply * 0.7), 1),
                'ai_capability': round(min(100, ai * 0.5), 1),
                'region': 'South America'
            },
            'AU': {
                'name': 'Australia',
                'economy': round(min(100, economic * 0.85), 1),
                'power_balance': round(min(100, 40 + tension * 0.08), 1),
                'tech_index': round(min(100, tech * 0.8), 1),
                'military': round(min(100, 45 + tension * 0.05), 1),
                'diplomacy': round(max(0, 78 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.85), 1),
                'trade': round(min(100, trade * 0.85), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.85)), 2),
                'supply_chain': round(min(100, supply * 0.85), 1),
                'ai_capability': round(min(100, ai * 0.75), 1),
                'region': 'Oceania'
            },
            'ZA': {
                'name': 'South Africa',
                'economy': round(min(100, economic * 0.6), 1),
                'power_balance': round(min(100, 35 + tension * 0.1), 1),
                'tech_index': round(min(100, tech * 0.5), 1),
                'military': round(min(100, 40 + tension * 0.05), 1),
                'diplomacy': round(max(0, 65 - tension * 0.2), 1),
                'stability': round(min(100, economic * 0.6), 1),
                'trade': round(min(100, trade * 0.6), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.6)), 2),
                'supply_chain': round(min(100, supply * 0.6), 1),
                'ai_capability': round(min(100, ai * 0.4), 1),
                'region': 'Africa'
            },
            'KR': {
                'name': 'South Korea',
                'economy': round(min(100, economic * 0.85), 1),
                'power_balance': round(min(100, 50 + tension * 0.2), 1),
                'tech_index': round(min(100, tech * 0.95), 1),
                'military': round(min(100, 55 + tension * 0.2), 1),
                'diplomacy': round(max(0, 68 - tension * 0.2), 1),
                'stability': round(min(100, economic * 0.85), 1),
                'trade': round(min(100, trade * 0.85), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.8)), 2),
                'supply_chain': round(min(100, supply * 0.8), 1),
                'ai_capability': round(min(100, ai * 0.9), 1),
                'region': 'Asia Pacific'
            },
            'IT': {
                'name': 'Italy',
                'economy': round(min(100, economic * 0.8), 1),
                'power_balance': round(min(100, 45 + tension * 0.1), 1),
                'tech_index': round(min(100, tech * 0.75), 1),
                'military': round(min(100, 50 + tension * 0.1), 1),
                'diplomacy': round(max(0, 75 - tension * 0.2), 1),
                'stability': round(min(100, economic * 0.8), 1),
                'trade': round(min(100, trade * 0.8), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.8)), 2),
                'supply_chain': round(min(100, supply * 0.8), 1),
                'ai_capability': round(min(100, ai * 0.7), 1),
                'region': 'Europe'
            },
            'ES': {
                'name': 'Spain',
                'economy': round(min(100, economic * 0.78), 1),
                'power_balance': round(min(100, 40 + tension * 0.1), 1),
                'tech_index': round(min(100, tech * 0.7), 1),
                'military': round(min(100, 45 + tension * 0.1), 1),
                'diplomacy': round(max(0, 72 - tension * 0.2), 1),
                'stability': round(min(100, economic * 0.78), 1),
                'trade': round(min(100, trade * 0.78), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.8)), 2),
                'supply_chain': round(min(100, supply * 0.78), 1),
                'ai_capability': round(min(100, ai * 0.65), 1),
                'region': 'Europe'
            },
            'NL': {
                'name': 'Netherlands',
                'economy': round(min(100, economic * 0.9), 1),
                'power_balance': round(min(100, 35 + tension * 0.05), 1),
                'tech_index': round(min(100, tech * 0.85), 1),
                'military': round(min(100, 40 + tension * 0.05), 1),
                'diplomacy': round(max(0, 80 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.9), 1),
                'trade': round(min(100, trade * 0.92), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.9)), 2),
                'supply_chain': round(min(100, supply * 0.85), 1),
                'ai_capability': round(min(100, ai * 0.8), 1),
                'region': 'Europe'
            },
            'SE': {
                'name': 'Sweden',
                'economy': round(min(100, economic * 0.85), 1),
                'power_balance': round(min(100, 30 + tension * 0.05), 1),
                'tech_index': round(min(100, tech * 0.9), 1),
                'military': round(min(100, 35 + tension * 0.05), 1),
                'diplomacy': round(max(0, 78 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.85), 1),
                'trade': round(min(100, trade * 0.85), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.9)), 2),
                'supply_chain': round(min(100, supply * 0.85), 1),
                'ai_capability': round(min(100, ai * 0.85), 1),
                'region': 'Europe'
            },
            'PL': {
                'name': 'Poland',
                'economy': round(min(100, economic * 0.75), 1),
                'power_balance': round(min(100, 40 + tension * 0.15), 1),
                'tech_index': round(min(100, tech * 0.65), 1),
                'military': round(min(100, 45 + tension * 0.15), 1),
                'diplomacy': round(max(0, 65 - tension * 0.25), 1),
                'stability': round(min(100, economic * 0.75), 1),
                'trade': round(min(100, trade * 0.75), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.7)), 2),
                'supply_chain': round(min(100, supply * 0.75), 1),
                'ai_capability': round(min(100, ai * 0.6), 1),
                'region': 'Europe'
            },
            'UA': {
                'name': 'Ukraine',
                'economy': round(min(100, economic * 0.4), 1),
                'power_balance': round(min(100, 30 + tension * 0.2), 1),
                'tech_index': round(min(100, tech * 0.4), 1),
                'military': round(min(100, 35 + tension * 0.2), 1),
                'diplomacy': round(max(0, 50 - tension * 0.3), 1),
                'stability': round(min(100, economic * 0.4), 1),
                'trade': round(min(100, trade * 0.4), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.5)), 2),
                'supply_chain': round(min(100, supply * 0.4), 1),
                'ai_capability': round(min(100, ai * 0.3), 1),
                'region': 'Europe'
            },
            'TR': {
                'name': 'Turkey',
                'economy': round(min(100, economic * 0.7), 1),
                'power_balance': round(min(100, 45 + tension * 0.2), 1),
                'tech_index': round(min(100, tech * 0.6), 1),
                'military': round(min(100, 50 + tension * 0.2), 1),
                'diplomacy': round(max(0, 60 - tension * 0.25), 1),
                'stability': round(min(100, economic * 0.7), 1),
                'trade': round(min(100, trade * 0.7), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.7)), 2),
                'supply_chain': round(min(100, supply * 0.7), 1),
                'ai_capability': round(min(100, ai * 0.55), 1),
                'region': 'Eurasia'
            },
            'IR': {
                'name': 'Iran',
                'economy': round(min(100, economic * 0.5), 1),
                'power_balance': round(min(100, 40 + tension * 0.25), 1),
                'tech_index': round(min(100, tech * 0.45), 1),
                'military': round(min(100, 45 + tension * 0.25), 1),
                'diplomacy': round(max(0, 40 - tension * 0.3), 1),
                'stability': round(min(100, economic * 0.5), 1),
                'trade': round(min(100, trade * 0.5), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.5)), 2),
                'supply_chain': round(min(100, supply * 0.5), 1),
                'ai_capability': round(min(100, ai * 0.4), 1),
                'region': 'Middle East'
            },
            'SA': {
                'name': 'Saudi Arabia',
                'economy': round(min(100, economic * 0.75), 1),
                'power_balance': round(min(100, 50 + tension * 0.15), 1),
                'tech_index': round(min(100, tech * 0.5), 1),
                'military': round(min(100, 55 + tension * 0.15), 1),
                'diplomacy': round(max(0, 55 - tension * 0.2), 1),
                'stability': round(min(100, economic * 0.75), 1),
                'trade': round(min(100, trade * 0.75), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.6)), 2),
                'supply_chain': round(min(100, supply * 0.7), 1),
                'ai_capability': round(min(100, ai * 0.45), 1),
                'region': 'Middle East'
            },
            'EG': {
                'name': 'Egypt',
                'economy': round(min(100, economic * 0.55), 1),
                'power_balance': round(min(100, 35 + tension * 0.12), 1),
                'tech_index': round(min(100, tech * 0.4), 1),
                'military': round(min(100, 40 + tension * 0.12), 1),
                'diplomacy': round(max(0, 60 - tension * 0.2), 1),
                'stability': round(min(100, economic * 0.55), 1),
                'trade': round(min(100, trade * 0.55), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.6)), 2),
                'supply_chain': round(min(100, supply * 0.55), 1),
                'ai_capability': round(min(100, ai * 0.35), 1),
                'region': 'Africa'
            },
            'NG': {
                'name': 'Nigeria',
                'economy': round(min(100, economic * 0.5), 1),
                'power_balance': round(min(100, 30 + tension * 0.1), 1),
                'tech_index': round(min(100, tech * 0.35), 1),
                'military': round(min(100, 35 + tension * 0.1), 1),
                'diplomacy': round(max(0, 55 - tension * 0.2), 1),
                'stability': round(min(100, economic * 0.5), 1),
                'trade': round(min(100, trade * 0.5), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.6)), 2),
                'supply_chain': round(min(100, supply * 0.5), 1),
                'ai_capability': round(min(100, ai * 0.3), 1),
                'region': 'Africa'
            },
            'ID': {
                'name': 'Indonesia',
                'economy': round(min(100, economic * 0.65), 1),
                'power_balance': round(min(100, 35 + tension * 0.1), 1),
                'tech_index': round(min(100, tech * 0.5), 1),
                'military': round(min(100, 40 + tension * 0.1), 1),
                'diplomacy': round(max(0, 60 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.65), 1),
                'trade': round(min(100, trade * 0.65), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.7)), 2),
                'supply_chain': round(min(100, supply * 0.65), 1),
                'ai_capability': round(min(100, ai * 0.45), 1),
                'region': 'Asia Pacific'
            },
            'MY': {
                'name': 'Malaysia',
                'economy': round(min(100, economic * 0.7), 1),
                'power_balance': round(min(100, 30 + tension * 0.08), 1),
                'tech_index': round(min(100, tech * 0.6), 1),
                'military': round(min(100, 35 + tension * 0.08), 1),
                'diplomacy': round(max(0, 65 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.7), 1),
                'trade': round(min(100, trade * 0.7), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.7)), 2),
                'supply_chain': round(min(100, supply * 0.7), 1),
                'ai_capability': round(min(100, ai * 0.5), 1),
                'region': 'Asia Pacific'
            },
            'TH': {
                'name': 'Thailand',
                'economy': round(min(100, economic * 0.65), 1),
                'power_balance': round(min(100, 30 + tension * 0.08), 1),
                'tech_index': round(min(100, tech * 0.55), 1),
                'military': round(min(100, 35 + tension * 0.08), 1),
                'diplomacy': round(max(0, 62 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.65), 1),
                'trade': round(min(100, trade * 0.65), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.7)), 2),
                'supply_chain': round(min(100, supply * 0.65), 1),
                'ai_capability': round(min(100, ai * 0.45), 1),
                'region': 'Asia Pacific'
            },
            'VN': {
                'name': 'Vietnam',
                'economy': round(min(100, economic * 0.6), 1),
                'power_balance': round(min(100, 25 + tension * 0.08), 1),
                'tech_index': round(min(100, tech * 0.5), 1),
                'military': round(min(100, 30 + tension * 0.08), 1),
                'diplomacy': round(max(0, 58 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.6), 1),
                'trade': round(min(100, trade * 0.6), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.65)), 2),
                'supply_chain': round(min(100, supply * 0.6), 1),
                'ai_capability': round(min(100, ai * 0.4), 1),
                'region': 'Asia Pacific'
            },
            'PH': {
                'name': 'Philippines',
                'economy': round(min(100, economic * 0.55), 1),
                'power_balance': round(min(100, 25 + tension * 0.08), 1),
                'tech_index': round(min(100, tech * 0.4), 1),
                'military': round(min(100, 30 + tension * 0.08), 1),
                'diplomacy': round(max(0, 55 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.55), 1),
                'trade': round(min(100, trade * 0.55), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.65)), 2),
                'supply_chain': round(min(100, supply * 0.55), 1),
                'ai_capability': round(min(100, ai * 0.35), 1),
                'region': 'Asia Pacific'
            },
            'CL': {
                'name': 'Chile',
                'economy': round(min(100, economic * 0.7), 1),
                'power_balance': round(min(100, 30 + tension * 0.08), 1),
                'tech_index': round(min(100, tech * 0.55), 1),
                'military': round(min(100, 35 + tension * 0.08), 1),
                'diplomacy': round(max(0, 62 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.7), 1),
                'trade': round(min(100, trade * 0.7), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.7)), 2),
                'supply_chain': round(min(100, supply * 0.7), 1),
                'ai_capability': round(min(100, ai * 0.5), 1),
                'region': 'South America'
            },
            'PE': {
                'name': 'Peru',
                'economy': round(min(100, economic * 0.6), 1),
                'power_balance': round(min(100, 25 + tension * 0.08), 1),
                'tech_index': round(min(100, tech * 0.45), 1),
                'military': round(min(100, 30 + tension * 0.08), 1),
                'diplomacy': round(max(0, 58 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.6), 1),
                'trade': round(min(100, trade * 0.6), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.65)), 2),
                'supply_chain': round(min(100, supply * 0.6), 1),
                'ai_capability': round(min(100, ai * 0.4), 1),
                'region': 'South America'
            },
            'CO': {
                'name': 'Colombia',
                'economy': round(min(100, economic * 0.6), 1),
                'power_balance': round(min(100, 25 + tension * 0.08), 1),
                'tech_index': round(min(100, tech * 0.45), 1),
                'military': round(min(100, 30 + tension * 0.08), 1),
                'diplomacy': round(max(0, 55 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.6), 1),
                'trade': round(min(100, trade * 0.6), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.65)), 2),
                'supply_chain': round(min(100, supply * 0.6), 1),
                'ai_capability': round(min(100, ai * 0.4), 1),
                'region': 'South America'
            },
            'PK': {
                'name': 'Pakistan',
                'economy': round(min(100, economic * 0.5), 1),
                'power_balance': round(min(100, 35 + tension * 0.2), 1),
                'tech_index': round(min(100, tech * 0.4), 1),
                'military': round(min(100, 40 + tension * 0.2), 1),
                'diplomacy': round(max(0, 45 - tension * 0.25), 1),
                'stability': round(min(100, economic * 0.5), 1),
                'trade': round(min(100, trade * 0.5), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.5)), 2),
                'supply_chain': round(min(100, supply * 0.5), 1),
                'ai_capability': round(min(100, ai * 0.35), 1),
                'region': 'Asia Pacific'
            },
        }
        
        # Get country data
        country_code_upper = country_code.upper()
        country_data_response = country_data.get(country_code_upper)
        
        if not country_data_response:
            # Return default data for unknown countries
            country_data_response = {
                'name': country_code_upper,
                'economy': round(min(100, economic * 0.5), 1),
                'power_balance': round(min(100, 40 + tension * 0.1), 1),
                'tech_index': round(min(100, tech * 0.4), 1),
                'military': round(min(100, 40 + tension * 0.1), 1),
                'diplomacy': round(max(0, 55 - tension * 0.15), 1),
                'stability': round(min(100, economic * 0.5), 1),
                'trade': round(min(100, trade * 0.5), 1),
                'sentiment': round(max(-1, min(1, sentiment * 0.5)), 2),
                'supply_chain': round(min(100, supply * 0.5), 1),
                'ai_capability': round(min(100, ai * 0.35), 1),
                'region': 'Other'
            }
        
        # Add simulation context
        country_data_response['simulation_round'] = engine.current_round
        country_data_response['simulation_status'] = engine.status.value
        country_data_response['global_tension'] = round(environment_state.get('strategic_tension', 30), 1)
        
        return CountryDataResponse(
            country=country_data_response['name'],
            country_code=country_code_upper,
            data=country_data_response,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get country data: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/global/{sim_id}")
async def get_global_state(sim_id: str):
    """
    Get global state metrics
    """
    try:
        if sim_id not in simulation_runner.simulations:
            engine = runtime._load_simulation_from_cache(sim_id)
            if engine:
                simulation_runner.simulations[sim_id] = engine
            else:
                raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
        
        engine = simulation_runner.simulations[sim_id]
        state = engine.get_global_state()
        
        return {
            'sim_id': sim_id,
            'global_state': state,
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get global state: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/region/{sim_id}/{region_name}")
async def get_region_state(sim_id: str, region_name: str):
    """
    Get state for a specific region
    """
    try:
        if sim_id not in simulation_runner.simulations:
            engine = runtime._load_simulation_from_cache(sim_id)
            if engine:
                simulation_runner.simulations[sim_id] = engine
            else:
                raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
        
        engine = simulation_runner.simulations[sim_id]
        state = engine.get_region_state(region_name)
        
        if not state:
            raise HTTPException(status_code=404, detail=f"Region {region_name} not found")
        
        return {
            'sim_id': sim_id,
            'region': region_name,
            'state': state,
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get region state: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history/{sim_id}")
async def get_state_history(
    sim_id: str,
    start_round: Optional[int] = None,
    end_round: Optional[int] = None,
    limit: int = Query(100, ge=1, le=1000),
    format: str = Query("json", pattern="^(json|csv)$")
):
    """
    Get state history
    """
    try:
        if sim_id not in simulation_runner.simulations:
            engine = runtime._load_simulation_from_cache(sim_id)
            if engine:
                simulation_runner.simulations[sim_id] = engine
            else:
                raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
        
        engine = simulation_runner.simulations[sim_id]
        history = engine.get_history(start_round, end_round, limit)
        
        if format == "csv":
            # Return as CSV
            import pandas as pd
            import io
            
            df = pd.DataFrame([s.state_snapshot for s in history])
            output = io.StringIO()
            df.to_csv(output, index=False)
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=state_history_{sim_id}.csv"
                }
            )
        
        return {
            'sim_id': sim_id,
            'total': len(history),
            'history': [
                {'round': s.round, 'timestamp': s.timestamp.isoformat(), 'state': s.state_snapshot,
                 'hegemon_strategy': s.hegemon_strategy, 'sovereign_strategy': s.sovereign_strategy,
                 'hegemon_utility': s.hegemon_utility, 'sovereign_utility': s.sovereign_utility}
                for s in history
            ],
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get state history: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/metrics/{sim_id}")
async def get_state_metrics(sim_id: str):
    """
    Get state metrics and trends
    """
    try:
        if sim_id not in simulation_runner.simulations:
            engine = runtime._load_simulation_from_cache(sim_id)
            if engine:
                simulation_runner.simulations[sim_id] = engine
            else:
                raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
        
        engine = simulation_runner.simulations[sim_id]
        metrics = engine.get_performance_metrics()
        
        # Calculate trends
        history = engine.get_history(limit=50)
        if history:
            trends = {}
            for key in ['economic_stability', 'technology_independence', 
                       'trade_stability', 'public_sentiment']:
                values = [s.state_snapshot.get(key, 0) for s in history]
                if values:
                    trends[key] = {
                        'current': values[-1],
                        'avg': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'trend': values[-1] - values[0] if len(values) > 1 else 0
                    }
        else:
            trends = {}
        
        return {
            'sim_id': sim_id,
            'metrics': metrics,
            'trends': trends,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get state metrics: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/compare")
async def compare_states(
    sim_id1: str,
    sim_id2: str,
    keys: Optional[str] = None
):
    """
    Compare states of two simulations
    """
    try:
        if sim_id1 not in simulation_runner.simulations:
            engine = runtime._load_simulation_from_cache(sim_id1)
            if engine:
                simulation_runner.simulations[sim_id1] = engine
            else:
                raise HTTPException(status_code=404, detail=f"Simulation {sim_id1} not found")
        
        if sim_id2 not in simulation_runner.simulations:
            engine = runtime._load_simulation_from_cache(sim_id2)
            if engine:
                simulation_runner.simulations[sim_id2] = engine
            else:
                raise HTTPException(status_code=404, detail=f"Simulation {sim_id2} not found")
        
        engine1 = simulation_runner.simulations[sim_id1]
        engine2 = simulation_runner.simulations[sim_id2]
        
        state1 = engine1.get_state()
        state2 = engine2.get_state()
        
        # Get keys to compare
        compare_keys = keys.split(',') if keys else list(state1.keys())
        
        comparison = {}
        for key in compare_keys:
            if key in state1 and key in state2:
                comparison[key] = {
                    'sim1': state1[key],
                    'sim2': state2[key],
                    'difference': state1[key] - state2[key],
                    'percent_change': (
                        (state1[key] - state2[key]) / max(1, state2[key]) * 100
                    )
                }
        
        return {
            'sim1': sim_id1,
            'sim2': sim_id2,
            'comparison': comparison,
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare states: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/export/{sim_id}")
async def export_state(sim_id: str):
    """
    Export state to file
    """
    try:
        if sim_id not in simulation_runner.simulations:
            engine = runtime._load_simulation_from_cache(sim_id)
            if engine:
                simulation_runner.simulations[sim_id] = engine
            else:
                raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
        
        engine = simulation_runner.simulations[sim_id]
        state = engine.get_state()
        
        # Export path
        export_dir = Path("data/exports")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = export_dir / f"state_{sim_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filepath, 'w') as f:
            json.dump({
                'sim_id': sim_id,
                'state': state,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        return {
            'status': 'exported',
            'sim_id': sim_id,
            'filepath': str(filepath),
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export state: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/import")
async def import_state(
    sim_id: str,
    filepath: str
):
    """
    Import state from file
    """
    try:
        if sim_id not in simulation_runner.simulations:
            engine = runtime._load_simulation_from_cache(sim_id)
            if engine:
                simulation_runner.simulations[sim_id] = engine
            else:
                raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        engine = simulation_runner.simulations[sim_id]
        engine.environment.state.update(data['state'])
        
        return {
            'status': 'imported',
            'sim_id': sim_id,
            'filepath': filepath,
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import state: {e}")
        raise HTTPException(status_code=400, detail=str(e))