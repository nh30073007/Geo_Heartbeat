# backend/app/agents/sovereign_agent.py
"""
Sovereign Agent with 4 Strategies and Adaptive Defense
FIXED: Always uses Q-learning when available - COLD START FIXED
"""
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from datetime import datetime
import logging
import random

from .base_agent import SecureAgent, Strategy, SECRET_KEY
from ..game_theory.best_response import BestResponse

logger = logging.getLogger(__name__)

class SovereignAgent(SecureAgent):
    """
    Sovereign Agent with FIXED strategy selection - COLD START FIXED
    """
    
    def __init__(self, secret_key: str = None):
        super().__init__(
            agent_id="Sovereign",
            secret_key=secret_key or SECRET_KEY,
            max_requests=200,
            time_window=60
        )
        self.best_response = None
        self.payoff_matrix = None
        self.resilience_target = 0.7
        self.adaptation_rate = 0.3
        
        self.strategy_values = {s.id: 0.0 for s in self.strategies}
        self.current_strategy = None
        
        # Alliances
        self.alliances: Dict[str, float] = {}
        self.trust_scores: Dict[str, float] = {}
        
        logger.info(f"🛡️ Sovereign Agent initialized with ε={self.exploration_rate:.3f}")
    
    def _initialize_strategies(self):
        """Initialize Sovereign's 4 strategies"""
        self.strategies = [
            Strategy(
                id="S1",
                name="De-dollarized Trade",
                description="Reduce dollar dependence in international trade",
                risk_level=0.7,
                implementation_cost=0.8,
                expected_duration=120
            ),
            Strategy(
                id="S2",
                name="Local Open-Source AI",
                description="Develop indigenous AI capability",
                risk_level=0.3,
                implementation_cost=0.9,
                expected_duration=180
            ),
            Strategy(
                id="S3",
                name="Trade Diversification",
                description="Diversify trade partners to reduce dependence",
                risk_level=0.4,
                implementation_cost=0.7,
                expected_duration=90
            ),
            Strategy(
                id="S4",
                name="Defensive Alliance",
                description="Form defensive alliances with other nations",
                risk_level=0.5,
                implementation_cost=0.6,
                expected_duration=60
            )
        ]
    
    def select_strategy(
        self,
        state: Dict[str, float],
        opponent_strategy: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        FIXED: Always use Q-learning when available - COLD START FIXED
        
        Now checks if ANY Q-value exists for this state.
        If yes, uses Q-learning. Only uses heuristics when state is completely new.
        """
        if not state:
            logger.warning("Empty state provided, using default")
            state = {'economic_stability': 50, 'strategic_tension': 50}
        
        if self.rl_backend == "dqn" and self.dqn is not None:
            chosen = self.dqn_strategy(state)
            if chosen:
                return chosen

        # Get state bucket
        state_bucket = self.discretize_state(state)
        
        # FIXED: Check if ANY Q-value exists for this state
        has_learned = any(
            (state_bucket, strategy.id) in self.q_table 
            for strategy in self.strategies
        )
        
        # If we have learned values, use Q-learning with epsilon-greedy
        if has_learned:
            # Epsilon-greedy exploration
            if random.random() < self.exploration_rate:
                chosen = random.choice([s.id for s in self.strategies])
                logger.debug(f"🔍 Sovereign exploring: {chosen} (ε={self.exploration_rate:.3f})")
                return chosen
            
            # Exploit: best strategy from Q-table
            best_strategy = self.best_q_strategy(state_bucket)
            if best_strategy:
                best_q = self.q_value(state_bucket, best_strategy)
                logger.debug(f"🎯 Sovereign exploiting: {best_strategy} (Q={best_q:.3f})")
                return best_strategy
        
        # COLD START: Only when NO Q-values exist for this state
        logger.info(f"🌱 Sovereign cold start - using heuristics for new state (round={context.get('round', 'unknown') if context else 'unknown'})")
        scores = self._calculate_strategy_scores(state, context)
        scores = self._adjust_for_resilience(scores, state)
        scores = self._consider_alliances(scores, state)
        best_strategy = max(scores, key=scores.get)
        
        # Initialize Q-table with heuristic values for ALL strategies in this state
        for strategy in self.strategies:
            if (state_bucket, strategy.id) not in self.q_table:
                heuristic_value = scores.get(strategy.id, 0.0) / 100.0
                self.q_table[(state_bucket, strategy.id)] = heuristic_value * 0.5
        
        return best_strategy
    
    def _calculate_strategy_scores(
        self,
        state: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Calculate scores for each strategy based on current state
        """
        scores = {}
        
        for strategy in self.strategies:
            score = self.strategy_values.get(strategy.id, 0.0)
            
            if strategy.id == 'S1':  # De-dollarized Trade
                currency_stability = state.get('currency_stability', 50)
                score += (100 - currency_stability) * 0.1
                economic_resilience = state.get('economic_resilience', 50)
                score += economic_resilience * 0.05
            
            elif strategy.id == 'S2':  # Local AI
                tech_independence = state.get('technology_independence', 50)
                score += (100 - tech_independence) * 0.1
                ai_capability = state.get('ai_capability', 50)
                score += (100 - ai_capability) * 0.05
            
            elif strategy.id == 'S3':  # Trade Diversification
                trade_stability = state.get('trade_stability', 50)
                score += (100 - trade_stability) * 0.1
                diversification = state.get('trade_diversification', 50)
                if 'trade_diversification' not in state:
                    diversification = 50
                score += (100 - diversification) * 0.05
            
            elif strategy.id == 'S4':  # Defensive Alliance
                tension = state.get('strategic_tension', 50)
                score += tension * 0.1
                alliance_strength = sum(self.alliances.values()) / max(1, len(self.alliances))
                score += alliance_strength * 0.2
            
            # Learning from history
            if self.history:
                strategy_history = [
                    h for h in self.history[-20:] 
                    if h['strategy'] == strategy.id
                ]
                if strategy_history:
                    avg_utility = np.mean([h['utility'] for h in strategy_history])
                    score += avg_utility * 0.2

            # Add learned Q-value
            state_bucket = self.discretize_state(state)
            q_val = self.q_value(state_bucket, strategy.id)
            score += q_val * 0.35

            scores[strategy.id] = score
        
        return scores
    
    def _adjust_for_resilience(
        self,
        scores: Dict[str, float],
        state: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Adjust scores based on resilience requirements
        """
        adjusted = scores.copy()
        
        current_resilience = state.get('economic_resilience', 50)
        if current_resilience < self.resilience_target * 100:
            for strategy_id in ['S1', 'S2', 'S3']:
                adjusted[strategy_id] *= 1.3
        
        sovereignty = state.get('sovereignty', 50)
        if sovereignty < 40:
            for strategy_id in ['S1', 'S4']:
                adjusted[strategy_id] *= 1.2
        
        return adjusted
    
    def _consider_alliances(
        self,
        scores: Dict[str, float],
        state: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Adjust scores based on alliance considerations
        """
        adjusted = scores.copy()
        
        if self.alliances:
            alliance_strength = sum(self.alliances.values()) / len(self.alliances)
            if alliance_strength > 0.7:
                adjusted['S4'] *= 1.3
        
        if self.trust_scores:
            avg_trust = sum(self.trust_scores.values()) / len(self.trust_scores)
            if avg_trust > 0.6:
                adjusted['S1'] *= 1.2
                adjusted['S2'] *= 1.1
        
        return adjusted
    
    def calculate_utility(self, state: Dict[str, float]) -> float:
        """
        Calculate utility based on state
        Sovereign wants to maximize:
        - Economic Resilience (30%)
        - Technology Independence (25%)
        - Trade Stability (25%)
        - Sovereignty (20%)
        """
        return (
            state.get('economic_resilience', 0) * 0.3 +
            state.get('technology_independence', 0) * 0.25 +
            state.get('trade_stability', 0) * 0.25 +
            state.get('sovereignty', 0) * 0.2
        ) / 100
    
    def update_from_history(self):
        """
        Learn from historical performance
        """
        if not self.history:
            return
        
        for strategy in self.strategies:
            strategy_history = [
                h for h in self.history[-50:] 
                if h['strategy'] == strategy.id
            ]
            
            if strategy_history:
                avg_utility = np.mean([h['utility'] for h in strategy_history])
                self.strategy_values[strategy.id] = (
                    1 - self.learning_rate
                ) * self.strategy_values.get(strategy.id, 0) + (
                    self.learning_rate * avg_utility
                )
        
        if len(self.history) > 10:
            recent = self.history[-10:]
            successful_outcomes = [
                h for h in recent 
                if h.get('utility', 0) > 0.5
            ]
            
            for h in successful_outcomes:
                if 'alliance_partner' in h:
                    partner = h['alliance_partner']
                    self.trust_scores[partner] = min(
                        1.0,
                        self.trust_scores.get(partner, 0) + 0.1
                    )
        
        logger.debug(f"Updated Sovereign strategy values: {self.strategy_values}")
    
    def set_payoff_matrix(self, payoff_matrix):
        """Set payoff matrix for best response calculation"""
        self.payoff_matrix = payoff_matrix
        self.best_response = BestResponse(payoff_matrix)
    
    def reset(self):
        """Reset base security/RL state and agent-specific learning state"""
        super().reset()
        self.strategy_values = {s.id: 0.0 for s in self.strategies}
        self.alliances = {}
        self.trust_scores = {}
        logger.info("🔄 Sovereign agent learning state reset")

    def add_alliance(
        self,
        partner: str,
        strength: float,
        context: Optional[Dict[str, Any]] = None
    ):
        """Add or update an alliance"""
        self.alliances[partner] = min(1.0, strength)
        self.trust_scores[partner] = self.trust_scores.get(partner, 0.5)
        logger.info(f"🤝 Alliance with {partner} established: {strength:.2f}")
    
    def remove_alliance(self, partner: str):
        """Remove an alliance"""
        if partner in self.alliances:
            del self.alliances[partner]
            if partner in self.trust_scores:
                del self.trust_scores[partner]
            logger.info(f"🚫 Alliance with {partner} removed")
    
    def analyze_threats(self, state: Dict[str, float]) -> Dict[str, Any]:
        """
        Analyze current threats
        """
        threats = {
            'economic_threat': 0.0,
            'technology_threat': 0.0,
            'trade_threat': 0.0,
            'sovereignty_threat': 0.0
        }
        
        if state.get('economic_stability', 50) < 40:
            threats['economic_threat'] = 0.8
        elif state.get('economic_stability', 50) < 60:
            threats['economic_threat'] = 0.5
        
        if state.get('technology_independence', 50) < 40:
            threats['technology_threat'] = 0.8
        elif state.get('technology_independence', 50) < 60:
            threats['technology_threat'] = 0.5
        
        if state.get('trade_stability', 50) < 40:
            threats['trade_threat'] = 0.7
        elif state.get('trade_stability', 50) < 60:
            threats['trade_threat'] = 0.4
        
        if state.get('strategic_tension', 50) > 70:
            threats['sovereignty_threat'] = 0.9
        elif state.get('strategic_tension', 50) > 50:
            threats['sovereignty_threat'] = 0.5
        
        return threats