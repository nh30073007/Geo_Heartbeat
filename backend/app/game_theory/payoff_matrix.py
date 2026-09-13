"""
Advanced Payoff Matrix with Dynamic Weights
"""
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import numpy as np
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class StrategyType(Enum):
    """Strategy types for both agents"""
    H1 = "Maximum Economic Pressure"
    H2 = "Information Influence"
    H3 = "Currency/Financial Pressure"
    H4 = "High-Escalation Policy"
    S1 = "De-dollarized Trade"
    S2 = "Local Open-Source AI"
    S3 = "Trade Diversification"
    S4 = "Defensive Alliance"

@dataclass
class PayoffResult:
    """Structured payoff result"""
    hegemon_payoff: float
    sovereign_payoff: float
    hegemon_strategy: str
    sovereign_strategy: str
    context_weights: Dict[str, float]
    confidence_score: float

class AdaptivePayoffMatrix:
    """
    Adaptive payoff matrix that changes based on:
    1. Current state of the world
    2. Historical performance
    3. Strategic context
    """
    
    def __init__(self):
        self.base_matrix = self._initialize_base_matrix()
        self.history: List[PayoffResult] = []
        self.learning_rate = 0.1
        
        # Strategy pairs
        self.hegemon_strategies = ['H1', 'H2', 'H3', 'H4']
        self.sovereign_strategies = ['S1', 'S2', 'S3', 'S4']
        
        logger.info("✅ Adaptive Payoff Matrix initialized")
    
    def _initialize_base_matrix(self) -> Dict[str, Dict[str, Tuple[float, float]]]:
        """Initialize with expert-validated base payoffs"""
        return {
            'H1': {
                'S1': (15.0, 20.0),
                'S2': (10.0, 25.0),
                'S3': (12.0, 22.0),
                'S4': (8.0, 28.0),
            },
            'H2': {
                'S1': (18.0, 15.0),
                'S2': (20.0, 18.0),
                'S3': (16.0, 20.0),
                'S4': (14.0, 22.0),
            },
            'H3': {
                'S1': (25.0, 10.0),
                'S2': (15.0, 20.0),
                'S3': (20.0, 15.0),
                'S4': (10.0, 25.0),
            },
            'H4': {
                'S1': (5.0, 30.0),
                'S2': (10.0, 25.0),
                'S3': (8.0, 28.0),
                'S4': (15.0, 20.0),
            }
        }
    
    # Compatibility helpers used by BestResponse.
    def get_payoff(self, hegemon_strategy: str, sovereign_strategy: str) -> Tuple[float, float]:
        return self.base_matrix[hegemon_strategy][sovereign_strategy]

    def get_hegemon_payoffs(self, sovereign_strategy: str) -> Dict[str, float]:
        return {h: self.base_matrix[h][sovereign_strategy][0] for h in self.hegemon_strategies}

    def get_sovereign_payoffs(self, hegemon_strategy: str) -> Dict[str, float]:
        return {s: self.base_matrix[hegemon_strategy][s][1] for s in self.sovereign_strategies}

    def get_adaptive_payoff(
        self,
        hegemon_strategy: str,
        sovereign_strategy: str,
        state: Dict[str, float],
        historical_bias: bool = True
    ) -> PayoffResult:
        """
        Get adaptive payoff considering current state and history
        """
        # Base payoff
        base_h, base_s = self.base_matrix[hegemon_strategy][sovereign_strategy]
        
        # Calculate context weights
        context_weights = self._calculate_context_weights(state)
        
        # Apply context modifiers
        h_modifier = self._calculate_modifier(
            hegemon_strategy, state, 'hegemon'
        )
        s_modifier = self._calculate_modifier(
            sovereign_strategy, state, 'sovereign'
        )
        
        # Apply historical bias
        if historical_bias and self.history:
            h_bias, s_bias = self._calculate_historical_bias(
                hegemon_strategy, sovereign_strategy
            )
            h_modifier += h_bias
            s_modifier += s_bias
        
        # Final payoffs. Keep adaptive multipliers bounded so they cannot
        # become a hidden source of runaway transition pressure.
        h_modifier = float(np.clip(h_modifier, -35.0, 35.0))
        s_modifier = float(np.clip(s_modifier, -35.0, 35.0))
        final_h = base_h * (1 + h_modifier / 100)
        final_s = base_s * (1 + s_modifier / 100)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(
            hegemon_strategy, sovereign_strategy, state
        )
        
        result = PayoffResult(
            hegemon_payoff=float(final_h),
            sovereign_payoff=float(final_s),
            hegemon_strategy=hegemon_strategy,
            sovereign_strategy=sovereign_strategy,
            context_weights=context_weights,
            confidence_score=confidence
        )
        
        # Store history
        self.history.append(result)
        
        return result
    
    def _calculate_context_weights(self, state: Dict[str, float]) -> Dict[str, float]:
        """Calculate context weights based on current state"""
        weights = {
            'economic_weight': 0.0,
            'technology_weight': 0.0,
            'sentiment_weight': 0.0,
            'tension_weight': 0.0
        }
        
        # Economic stability influences weight
        if state.get('economic_stability', 50) > 70:
            weights['economic_weight'] = 0.4
        else:
            weights['economic_weight'] = 0.2
        
        # Technology level influences weight
        if state.get('technology_independence', 50) > 60:
            weights['technology_weight'] = 0.3
        else:
            weights['technology_weight'] = 0.2
        
        # Sentiment influences weight
        sentiment = state.get('public_sentiment', 0)
        if sentiment > 0.3:
            weights['sentiment_weight'] = 0.2
        elif sentiment < -0.3:
            weights['sentiment_weight'] = 0.4
        
        # Tension influences weight
        tension = state.get('strategic_tension', 50)
        if tension > 70:
            weights['tension_weight'] = 0.3
        else:
            weights['tension_weight'] = 0.1
        
        # Normalize
        total = sum(weights.values())
        if total > 0:
            for key in weights:
                weights[key] /= total
        
        return weights
    
    def _calculate_modifier(
        self,
        strategy: str,
        state: Dict[str, float],
        agent_type: str
    ) -> float:
        """Calculate modifier based on strategy and state"""
        modifier = 0.0
        
        # Strategy-specific modifiers
        if strategy == 'H1':  # Economic Pressure
            modifier += state.get('economic_stability', 50) * 0.1
            if state.get('trade_stability', 50) < 50:
                modifier += 10  # More effective when trade is unstable
        
        elif strategy == 'H2':  # Information Influence
            modifier += state.get('public_sentiment', 0) * 50
            if state.get('technology_independence', 50) < 50:
                modifier += 8
        
        elif strategy == 'H3':  # Currency Pressure
            modifier += (100 - state.get('currency_stability', 50)) * 0.15
            if state.get('economic_resilience', 50) < 50:
                modifier += 12
        
        elif strategy == 'H4':  # High Escalation
            tension = state.get('strategic_tension', 50)
            # Escalation has diminishing returns as tension rises.
            modifier += max(0.0, 10.0 - abs(tension - 45.0) * 0.08)
            if tension > 75:
                modifier -= (tension - 75.0) * 0.35
            if state.get('stability', 50) < 30:
                modifier -= 5
        
        # Sovereign strategies
        elif strategy == 'S1':  # De-dollarization
            modifier += (100 - state.get('currency_stability', 50)) * 0.15
            if state.get('economic_resilience', 50) > 60:
                modifier += 10
        
        elif strategy == 'S2':  # Local AI
            modifier += state.get('ai_capability', 50) * 0.2
            if state.get('technology_independence', 50) < 50:
                modifier += 15
        
        elif strategy == 'S3':  # Trade Diversification
            modifier += state.get('trade_stability', 50) * 0.1
            if state.get('economic_resilience', 50) < 50:
                modifier += 8
        
        elif strategy == 'S4':  # Defensive Alliance
            modifier += state.get('stability', 50) * 0.15
            if state.get('strategic_tension', 50) > 60:
                modifier += 12
        
        return modifier
    
    def _calculate_historical_bias(
        self,
        hegemon_strategy: str,
        sovereign_strategy: str
    ) -> Tuple[float, float]:
        """Calculate bias from historical performance"""
        if not self.history:
            return 0.0, 0.0
        
        # Find similar strategy pairs in history
        similar_pairs = [
            h for h in self.history[-50:]  # Last 50 rounds
            if h.hegemon_strategy == hegemon_strategy and
               h.sovereign_strategy == sovereign_strategy
        ]
        
        if not similar_pairs:
            return 0.0, 0.0
        
        # Calculate average bias
        h_avg = np.mean([h.hegemon_payoff for h in similar_pairs])
        s_avg = np.mean([h.sovereign_payoff for h in similar_pairs])
        
        # Get base payoff
        base_h, base_s = self.base_matrix[hegemon_strategy][sovereign_strategy]
        
        # Calculate bias (with learning rate)
        h_bias = (h_avg - base_h) * self.learning_rate
        s_bias = (s_avg - base_s) * self.learning_rate
        
        return h_bias, s_bias
    
    def _calculate_confidence(
        self,
        hegemon_strategy: str,
        sovereign_strategy: str,
        state: Dict[str, float]
    ) -> float:
        """Calculate confidence score for the payoff prediction"""
        confidence = 0.7  # Base confidence
        
        # More data = higher confidence
        if len(self.history) > 100:
            confidence += 0.15
        
        # State stability increases confidence
        state_stability = 1 - (state.get('strategic_tension', 50) / 100)
        confidence += state_stability * 0.1
        
        # Historical accuracy
        if len(self.history) > 10:
            recent_accuracy = self._calculate_recent_accuracy()
            confidence += recent_accuracy * 0.05
        
        return min(confidence, 0.98)  # Cap at 0.98
    
    def _calculate_recent_accuracy(self) -> float:
        """Calculate recent prediction accuracy"""
        if len(self.history) < 2:
            return 0.5
        
        # Simple accuracy metric
        recent = self.history[-20:]
        correct_predictions = 0
        
        for i in range(1, len(recent)):
            prev = recent[i-1]
            curr = recent[i]
            
            # Check if trend continued
            if (prev.hegemon_payoff < curr.hegemon_payoff) == \
               (prev.sovereign_payoff < curr.sovereign_payoff):
                correct_predictions += 1
        
        return correct_predictions / max(1, len(recent) - 1)
    
    def get_nash_equilibrium(self, state: Dict[str, float]) -> List[Tuple[str, str, float, float]]:
        """
        Find Nash Equilibrium using adaptive payoffs
        """
        equilibria = []
        
        for h in self.hegemon_strategies:
            for s in self.sovereign_strategies:
                result = self.get_adaptive_payoff(h, s, state)
                
                # Check best responses
                h_best = self._best_response_hegemon(s, state)
                s_best = self._best_response_sovereign(h, state)
                
                if h_best[0] == h and s_best[0] == s:
                    equilibria.append((h, s, result.hegemon_payoff, result.sovereign_payoff))
        
        return equilibria
    
    def _best_response_hegemon(
        self,
        sovereign_strategy: str,
        state: Dict[str, float]
    ) -> Tuple[str, float]:
        """Find hegemon's best response"""
        best_payoff = -float('inf')
        best_strategy = None
        
        for h in self.hegemon_strategies:
            result = self.get_adaptive_payoff(h, sovereign_strategy, state)
            if result.hegemon_payoff > best_payoff:
                best_payoff = result.hegemon_payoff
                best_strategy = h
        
        return best_strategy, best_payoff
    
    def _best_response_sovereign(
        self,
        hegemon_strategy: str,
        state: Dict[str, float]
    ) -> Tuple[str, float]:
        """Find sovereign's best response"""
        best_payoff = -float('inf')
        best_strategy = None
        
        for s in self.sovereign_strategies:
            result = self.get_adaptive_payoff(hegemon_strategy, s, state)
            if result.sovereign_payoff > best_payoff:
                best_payoff = result.sovereign_payoff
                best_strategy = s
        
        return best_strategy, best_payoff