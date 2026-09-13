# backend/app/agents/hegemon_agent.py
"""
Hegemon Agent with 4 Strategies and Advanced Decision Making
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

class HegemonAgent(SecureAgent):
    """
    Hegemon Agent with FIXED strategy selection - COLD START FIXED
    """
    
    def __init__(self, secret_key: str = None):
        super().__init__(
            agent_id="Hegemon",
            secret_key=secret_key or SECRET_KEY,
            max_requests=200,
            time_window=60
        )
        self.best_response = None
        self.payoff_matrix = None
        self.risk_tolerance = 0.6
        self.aggressiveness = 0.7
        
        # Decision parameters
        self.strategy_values = {s.id: 0.0 for s in self.strategies}
        self.current_strategy = None
        
        logger.info(f"⚔️ Hegemon Agent initialized with ε={self.exploration_rate:.3f}")
    
    def _initialize_strategies(self):
        """Initialize Hegemon's 4 strategies"""
        self.strategies = [
            Strategy(
                id="H1",
                name="Maximum Economic Pressure",
                description="Apply maximum economic sanctions and pressure on adversary",
                risk_level=0.6,
                implementation_cost=0.8,
                expected_duration=90
            ),
            Strategy(
                id="H2",
                name="Information Influence",
                description="Control narrative through information operations and propaganda",
                risk_level=0.5,
                implementation_cost=0.6,
                expected_duration=60
            ),
            Strategy(
                id="H3",
                name="Currency/Financial Pressure",
                description="Apply financial and currency pressure through various mechanisms",
                risk_level=0.7,
                implementation_cost=0.7,
                expected_duration=45
            ),
            Strategy(
                id="H4",
                name="High-Escalation Policy",
                description="High-risk high-reward escalation strategy",
                risk_level=0.9,
                implementation_cost=0.9,
                expected_duration=30
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
        # Validate state
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
        # This is the key fix - checks entire Q-table for this state
        has_learned = any(
            (state_bucket, strategy.id) in self.q_table 
            for strategy in self.strategies
        )
        
        # If we have learned values, use Q-learning with epsilon-greedy
        if has_learned:
            # Epsilon-greedy exploration
            if random.random() < self.exploration_rate:
                # Explore: random strategy
                chosen = random.choice([s.id for s in self.strategies])
                logger.debug(f"🔍 Hegemon exploring: {chosen} (ε={self.exploration_rate:.3f})")
                return chosen
            
            # Exploit: best strategy from Q-table
            best_strategy = self.best_q_strategy(state_bucket)
            if best_strategy:
                best_q = self.q_value(state_bucket, best_strategy)
                logger.debug(f"🎯 Hegemon exploiting: {best_strategy} (Q={best_q:.3f})")
                return best_strategy
        
        # COLD START: Only when NO Q-values exist for this state
        # This should only happen for completely new states
        logger.info(f"🌱 Hegemon cold start - using heuristics for new state (round={context.get('round', 'unknown') if context else 'unknown'})")
        scores = self._calculate_strategy_scores(state, context)
        scores = self._adjust_for_risk(scores, state)
        best_strategy = max(scores, key=scores.get)
        
        # Initialize Q-table with heuristic values for ALL strategies in this state
        for strategy in self.strategies:
            if (state_bucket, strategy.id) not in self.q_table:
                # Scale heuristic score to [-1, 1] range
                heuristic_value = scores.get(strategy.id, 0.0) / 100.0
                # Initialize with a reasonable value
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
        
        # Get strategy values
        for strategy in self.strategies:
            score = self.strategy_values.get(strategy.id, 0.0)
            
            # Add state-based bonuses
            if strategy.id == 'H1':  # Economic Pressure
                trade_stability = state.get('trade_stability', 50)
                score += (100 - trade_stability) * 0.1
                economic_stability = state.get('economic_stability', 50)
                score += (100 - economic_stability) * 0.05
            
            elif strategy.id == 'H2':  # Information Influence
                sentiment = state.get('public_sentiment', 0)
                if sentiment < 0:
                    score += abs(sentiment) * 0.5
                tech_independence = state.get('technology_independence', 50)
                score += (100 - tech_independence) * 0.05
            
            elif strategy.id == 'H3':  # Financial Pressure
                currency_stability = state.get('currency_stability', 50)
                score += (100 - currency_stability) * 0.1
                resilience = state.get('economic_resilience', 50)
                score += (100 - resilience) * 0.05
            
            elif strategy.id == 'H4':  # High Escalation
                tension = state.get('strategic_tension', 50)
                score += tension * 0.1
                advantage = state.get('technology_advantage', 50)
                score += advantage * 0.05
            
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
    
    def _adjust_for_risk(
        self,
        scores: Dict[str, float],
        state: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Adjust scores based on risk tolerance and current situation
        """
        adjusted = scores.copy()
        
        risk_levels = {s.id: s.risk_level for s in self.strategies}
        
        for strategy_id, score in scores.items():
            risk = risk_levels.get(strategy_id, 0.5)
            
            advantage = state.get('technology_advantage', 50)
            if advantage > 70:
                adjusted[strategy_id] = score * (1 + (1 - risk) * 0.2)
            else:
                adjusted[strategy_id] = score * (1 - risk * 0.2 * (1 - self.risk_tolerance))
        
        tension = state.get('strategic_tension', 50)
        if tension > 70:
            for strategy_id in ['H4']:
                adjusted[strategy_id] *= 0.8
        elif tension < 30:
            for strategy_id in ['H4']:
                adjusted[strategy_id] *= 1.2
        
        return adjusted
    
    def calculate_utility(self, state: Dict[str, float]) -> float:
        """
        Calculate utility based on state
        Hegemon wants to maximize:
        - Economic Influence (30%)
        - Technology Advantage (25%)
        - Strategic Utility (25%)
        - Stability (20%)
        """
        return (
            state.get('economic_influence', 0) * 0.3 +
            state.get('technology_advantage', 0) * 0.25 +
            state.get('strategic_utility', 0) * 0.25 +
            state.get('stability', 0) * 0.2
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
        
        logger.debug(f"Updated strategy values: {self.strategy_values}")
    
    def set_payoff_matrix(self, payoff_matrix):
        """Set payoff matrix for best response calculation"""
        self.payoff_matrix = payoff_matrix
        self.best_response = BestResponse(payoff_matrix)
    
    def reset(self):
        """Reset base security/RL state and agent-specific learning state"""
        super().reset()
        self.strategy_values = {s.id: 0.0 for s in self.strategies}
        logger.info("🔄 Hegemon agent learning state reset")

    def analyze_opponent(
        self,
        opponent_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze opponent behavior
        """
        if not opponent_history:
            return {'error': 'No opponent history'}
        
        strategies = [h['strategy'] for h in opponent_history if 'strategy' in h]
        strategy_dist = {}
        for s in strategies:
            strategy_dist[s] = strategy_dist.get(s, 0) + 1
        
        total = sum(strategy_dist.values())
        for s in strategy_dist:
            strategy_dist[s] = strategy_dist[s] / total
        
        recent = opponent_history[-20:] if len(opponent_history) > 20 else opponent_history
        recent_strategies = [h['strategy'] for h in recent if 'strategy' in h]
        
        return {
            'strategy_distribution': strategy_dist,
            'most_common': max(strategy_dist, key=strategy_dist.get) if strategy_dist else None,
            'recent_trend': recent_strategies[-5:] if recent_strategies else [],
            'total_actions': len(opponent_history),
            'avg_utility': np.mean([h.get('utility', 0) for h in opponent_history[-50:]])
        }