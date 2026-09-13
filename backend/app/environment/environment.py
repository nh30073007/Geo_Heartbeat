# backend/app/environment/environment.py
"""
Main Environment Class - Orchestrates all components
FIXED: Reward function with STRONG NEGATIVE rewards for bad states
"""
from typing import Dict, Any, Optional, Tuple
import asyncio
from datetime import datetime
import logging
import random
import os
import numpy as np

from .state import EnvironmentState
from .transition import StateTransitionEngine
from ..game_theory.payoff import AdaptivePayoffMatrix
from ..game_theory.mixed_strategy import MixedStrategySolver
from ..game_theory.equilibrium import EquilibriumAnalyzer

logger = logging.getLogger(__name__)

class StrategicEnvironment:
    """
    Complete Strategic Environment with FIXED reward calculation
    """
    
    def __init__(self, stochastic: bool = True):
        self.state = EnvironmentState()
        self.transition_engine = StateTransitionEngine(
            stochastic=stochastic,
            noise_scale=float(os.getenv("TRANSITION_NOISE_SCALE", "0.35")),
            recovery_rate=float(os.getenv("TRANSITION_RECOVERY_RATE", "0.12")),
            tension_relaxation=float(os.getenv("TRANSITION_TENSION_RELAXATION", "0.30")),
            max_effect_per_step=float(os.getenv("TRANSITION_MAX_EFFECT", "7.5")),
        )
        self.payoff_matrix = AdaptivePayoffMatrix()
        self.mixed_solver = MixedStrategySolver(self.payoff_matrix)
        self.equilibrium_analyzer = EquilibriumAnalyzer(self.payoff_matrix)
        
        self.history: list = []
        self.events: list = []
        self.current_round: int = 0
        self.is_running: bool = False
        
        logger.info("✅ Strategic Environment initialized")
    

    def _state_quality(self, state: Dict[str, float], agent: str) -> float:
        """Normalized welfare score in [-1, 1] for stable RL learning."""
        tension = np.clip(state.get('strategic_tension', 50.0), 0.0, 100.0) / 100.0
        if agent == 'hegemon':
            quality = (
                0.45 * state.get('economic_stability', 50.0) / 100.0
                + 0.20 * state.get('technology_independence', 50.0) / 100.0
                + 0.15 * state.get('trade_stability', 50.0) / 100.0
                + 0.20 * (1.0 - tension)
            )
        else:
            quality = (
                0.35 * state.get('economic_resilience', 50.0) / 100.0
                + 0.20 * state.get('technology_independence', 50.0) / 100.0
                + 0.20 * state.get('trade_stability', 50.0) / 100.0
                + 0.25 * (1.0 - tension)
            )
        return float(2.0 * quality - 1.0)

    def calculate_hegemon_utility(self, state: Dict[str, float]) -> float:
        return self._state_quality(state, 'hegemon')

    def calculate_sovereign_utility(self, state: Dict[str, float]) -> float:
        return self._state_quality(state, 'sovereign')

    async def step(
        self,
        hegemon_strategy: str,
        sovereign_strategy: str
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Take one step in the environment with FIXED reward calculation
        
        Returns: (new_state, rewards)
        """
        # Get current state
        current_state = self.state.get_global_state()
        
        # Get payoff
        payoff_result = self.payoff_matrix.get_adaptive_payoff(
            hegemon_strategy,
            sovereign_strategy,
            current_state
        )
        
        # Calculate transition
        new_state_dict = self.transition_engine.apply_transition(
            current_state,
            hegemon_strategy,
            sovereign_strategy,
            payoff_result.hegemon_payoff,
            payoff_result.sovereign_payoff
        )
        
        # Update state
        self.state.update(new_state_dict, stochastic=self.transition_engine.stochastic)
        
        # Potential-based reward: reward improvement/degradation rather than
        # making an extreme state permanently dominate the learning signal.
        old_h = self.calculate_hegemon_utility(current_state)
        old_s = self.calculate_sovereign_utility(current_state)
        new_h = self.calculate_hegemon_utility(new_state_dict)
        new_s = self.calculate_sovereign_utility(new_state_dict)
        hegemon_reward = float(np.clip(0.75 * (new_h - old_h) + 0.25 * new_h, -1.0, 1.0))
        sovereign_reward = float(np.clip(0.75 * (new_s - old_s) + 0.25 * new_s, -1.0, 1.0))

        logger.info(f"💰 Rewards: H={hegemon_reward:.3f}, S={sovereign_reward:.3f}")
        
        # Log event
        event = {
            'round': self.current_round,
            'timestamp': datetime.now().isoformat(),
            'hegemon_strategy': hegemon_strategy,
            'sovereign_strategy': sovereign_strategy,
            'hegemon_payoff': payoff_result.hegemon_payoff,
            'sovereign_payoff': payoff_result.sovereign_payoff,
            'hegemon_reward': hegemon_reward,
            'sovereign_reward': sovereign_reward,
            'state': new_state_dict,
            'confidence': payoff_result.confidence_score
        }
        
        self.events.append(event)
        self.history.append(self.state.to_dict())
        self.current_round += 1
        
        return new_state_dict, {
            'hegemon': hegemon_reward,
            'sovereign': sovereign_reward
        }
    
    def get_state(self) -> Dict[str, float]:
        """Get current state"""
        return self.state.to_dict()
    
    def get_global_state(self) -> Dict[str, float]:
        """Get global state metrics"""
        return self.state.get_global_state()
    
    def get_region_state(self, region_name: str) -> Optional[Dict[str, float]]:
        """Get state for specific region"""
        return self.state.get_region_state(region_name)
    
    def get_equilibrium_analysis(self) -> Dict[str, Any]:
        """Get equilibrium analysis for current state"""
        current_state = self.state.get_global_state()
        return self.equilibrium_analyzer.analyze_all(current_state)
    
    def get_mixed_strategy(self) -> Dict[str, Any]:
        """Get mixed strategy solution"""
        current_state = self.state.get_global_state()
        result = self.mixed_solver.solve_fictitious_play(current_state)
        return {
            'hegemon_strategy': result.hegemon_strategy,
            'sovereign_strategy': result.sovereign_strategy,
            'expected_payoff_hegemon': result.expected_payoff_hegemon,
            'expected_payoff_sovereign': result.expected_payoff_sovereign,
            'convergence': result.convergence
        }
    
    def reset(self, initial_state: Optional[Dict[str, float]] = None):
        """Reset environment"""
        if initial_state:
            self.state.update(initial_state, stochastic=False)
        else:
            self.state = EnvironmentState()
        
        self.history = []
        self.events = []
        self.current_round = 0
        self.is_running = False
        
        logger.info("🔄 Environment reset")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        if not self.history:
            return {'error': 'No history available'}
        
        # Calculate trends
        recent = self.history[-50:] if len(self.history) > 50 else self.history
        
        trends = {}
        for key in ['economic_stability', 'technology_independence', 
                   'trade_stability', 'public_sentiment']:
            values = [h.get(key, 0) for h in recent]
            if values:
                trends[key] = {
                    'current': values[-1],
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'trend': values[-1] - values[0]
                }
        
        return {
            'total_rounds': len(self.history),
            'current_round': self.current_round,
            'trends': trends,
            'current_state': self.get_state(),
            'agent_performance': {
                'hegemon_utility': self.calculate_hegemon_utility(self.get_state()),
                'sovereign_utility': self.calculate_sovereign_utility(self.get_state())
            }
        }