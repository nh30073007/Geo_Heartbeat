# backend/app/environment/state.py
"""
Advanced Environment State with Stochastic Elements
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import numpy as np
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class RegionalMetrics:
    """Regional-level metrics"""
    region_name: str
    economic_index: float
    technology_index: float
    trade_stability: float
    sentiment: float
    resilience: float
    population_weight: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'region_name': self.region_name,
            'economic_index': self.economic_index,
            'technology_index': self.technology_index,
            'trade_stability': self.trade_stability,
            'sentiment': self.sentiment,
            'resilience': self.resilience,
            'population_weight': self.population_weight
        }

@dataclass
class EnvironmentState:
    """
    Complete Environment State with:
    - Core metrics (0-100)
    - Sentiment (-1 to +1)  
    - Regional variations
    - Historical tracking
    - Stochastic elements
    """
    
    # Core metrics
    economic_stability: float = 75.0
    technology_independence: float = 62.0
    trade_stability: float = 70.0
    currency_stability: float = 68.0
    supply_chain_stability: float = 73.0
    strategic_tension: float = 25.0
    ai_capability: float = 66.0
    
    # Sentiment (global)
    public_sentiment: float = 0.22
    
    # Derived metrics (auto-calculated)
    economic_influence: float = 0.0
    technology_advantage: float = 0.0
    strategic_utility: float = 0.0
    stability: float = 0.0
    economic_resilience: float = 0.0
    sovereignty: float = 0.0
    
    # Regional data
    regions: List[RegionalMetrics] = field(default_factory=list)
    
    # History tracking
    history: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    round_number: int = 0
    
    # Stochastic elements
    random_seed: Optional[int] = None
    _rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng())
    
    def __post_init__(self):
        """Initialize derived metrics and regions"""
        if not self.regions:
            self._initialize_default_regions()
        
        self._calculate_derived_metrics()
        self._rng = np.random.default_rng(self.random_seed)
        
    def _initialize_default_regions(self):
        """Initialize default regions"""
        self.regions = [
            RegionalMetrics(
                region_name="North America",
                economic_index=85.0,
                technology_index=90.0,
                trade_stability=75.0,
                sentiment=0.15,
                resilience=70.0,
                population_weight=1.2
            ),
            RegionalMetrics(
                region_name="Europe",
                economic_index=78.0,
                technology_index=85.0,
                trade_stability=80.0,
                sentiment=0.20,
                resilience=75.0,
                population_weight=1.0
            ),
            RegionalMetrics(
                region_name="Asia Pacific",
                economic_index=72.0,
                technology_index=65.0,
                trade_stability=70.0,
                sentiment=0.10,
                resilience=68.0,
                population_weight=1.5
            ),
            RegionalMetrics(
                region_name="Middle East",
                economic_index=60.0,
                technology_index=45.0,
                trade_stability=55.0,
                sentiment=-0.05,
                resilience=55.0,
                population_weight=0.8
            ),
            RegionalMetrics(
                region_name="Africa",
                economic_index=45.0,
                technology_index=35.0,
                trade_stability=50.0,
                sentiment=-0.10,
                resilience=50.0,
                population_weight=0.7
            ),
            RegionalMetrics(
                region_name="South America",
                economic_index=55.0,
                technology_index=50.0,
                trade_stability=60.0,
                sentiment=0.05,
                resilience=58.0,
                population_weight=0.6
            )
        ]
    
    def _calculate_derived_metrics(self):
        """Calculate derived metrics from core metrics"""
        self.economic_influence = (
            self.economic_stability * 0.4 +
            self.currency_stability * 0.3 +
            self.trade_stability * 0.3
        )
        
        self.technology_advantage = (
            self.technology_independence * 0.5 +
            self.ai_capability * 0.3 +
            self.supply_chain_stability * 0.2
        )
        
        # Stability is a dependency of strategic utility, so calculate it first.
        self.stability = (
            self.economic_stability * 0.25 +
            self.trade_stability * 0.25 +
            self.supply_chain_stability * 0.25 +
            (1 - abs(self.public_sentiment)) * 100 * 0.25
        )

        self.strategic_utility = (
            self.economic_influence * 0.3 +
            self.technology_advantage * 0.3 +
            (100 - self.strategic_tension) * 0.2 +
            self.stability * 0.2
        )
        
        self.economic_resilience = (
            self.economic_stability * 0.3 +
            self.trade_stability * 0.3 +
            self.currency_stability * 0.2 +
            self.supply_chain_stability * 0.2
        )
        
        self.sovereignty = (
            self.technology_independence * 0.3 +
            self.economic_resilience * 0.3 +
            (100 - self.strategic_tension) * 0.2 +
            self.trade_stability * 0.2
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'round': self.round_number,
            'timestamp': self.timestamp.isoformat(),
            'economic_stability': round(self.economic_stability, 2),
            'technology_independence': round(self.technology_independence, 2),
            'trade_stability': round(self.trade_stability, 2),
            'currency_stability': round(self.currency_stability, 2),
            'public_sentiment': round(self.public_sentiment, 3),
            'supply_chain_stability': round(self.supply_chain_stability, 2),
            'strategic_tension': round(self.strategic_tension, 2),
            'ai_capability': round(self.ai_capability, 2),
            'economic_influence': round(self.economic_influence, 2),
            'technology_advantage': round(self.technology_advantage, 2),
            'strategic_utility': round(self.strategic_utility, 2),
            'stability': round(self.stability, 2),
            'economic_resilience': round(self.economic_resilience, 2),
            'sovereignty': round(self.sovereignty, 2),
            'regions': [r.to_dict() for r in self.regions]
        }
    
    def update(self, updates: Dict[str, float], stochastic: bool = True):
        """
        Update state with new values
        Includes stochastic noise if enabled
        """
        # Apply updates with noise
        for key, value in updates.items():
            if hasattr(self, key):
                # Add stochastic noise
                if stochastic and key not in ['public_sentiment']:
                    noise = self._rng.normal(0, 0.5)  # Small noise
                    new_value = value + noise
                else:
                    new_value = value
                
                # Clamp values
                if key == 'public_sentiment':
                    new_value = max(-1.0, min(1.0, new_value))
                else:
                    new_value = max(0.0, min(100.0, new_value))
                
                setattr(self, key, new_value)
        
        # Update derived metrics
        self._calculate_derived_metrics()
        
        # Update timestamp
        self.timestamp = datetime.now()
        self.round_number += 1
        
        # Add to history
        self.history.append(self.to_dict())
        
        # Keep history limited
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
    
    def update_region(self, region_name: str, updates: Dict[str, float]):
        """Update specific region metrics"""
        for region in self.regions:
            if region.region_name == region_name:
                for key, value in updates.items():
                    if hasattr(region, key):
                        setattr(region, key, value)
                break
        
        # Recalculate global metrics from regions
        self._aggregate_from_regions()
    
    def _aggregate_from_regions(self):
        """Aggregate global metrics from regional data"""
        if not self.regions:
            return
        
        total_weight = sum(r.population_weight for r in self.regions)
        
        # Weighted averages
        self.economic_stability = sum(
            r.economic_index * r.population_weight for r in self.regions
        ) / total_weight
        
        self.technology_independence = sum(
            r.technology_index * r.population_weight for r in self.regions
        ) / total_weight
        
        self.trade_stability = sum(
            r.trade_stability * r.population_weight for r in self.regions
        ) / total_weight
        
        self.public_sentiment = sum(
            r.sentiment * r.population_weight for r in self.regions
        ) / total_weight
        
        self._calculate_derived_metrics()
    
    def get_global_state(self) -> Dict[str, float]:
        """Get just the global state metrics"""
        return {
            'economic_stability': self.economic_stability,
            'technology_independence': self.technology_independence,
            'trade_stability': self.trade_stability,
            'currency_stability': self.currency_stability,
            'public_sentiment': self.public_sentiment,
            'strategic_tension': self.strategic_tension,
            'ai_capability': self.ai_capability,
            'stability': self.stability
        }
    
    def get_region_state(self, region_name: str) -> Optional[Dict[str, float]]:
        """Get state for a specific region"""
        for region in self.regions:
            if region.region_name == region_name:
                return region.to_dict()
        return None
    
    def save_state(self, filepath: str):
        """Save state to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_state(cls, filepath: str) -> 'EnvironmentState':
        """Load state from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        state = cls()
        for key, value in data.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        return state
    
    def calculate_hegemon_utility(self) -> float:
        """Calculate utility for Hegemon agent"""
        return (
            self.economic_influence * 0.3 +
            self.technology_advantage * 0.25 +
            self.strategic_utility * 0.25 +
            self.stability * 0.2
        ) / 100
    
    def calculate_sovereign_utility(self) -> float:
        """Calculate utility for Sovereign agent"""
        return (
            self.economic_resilience * 0.3 +
            self.technology_independence * 0.25 +
            self.trade_stability * 0.25 +
            self.sovereignty * 0.2
        ) / 100