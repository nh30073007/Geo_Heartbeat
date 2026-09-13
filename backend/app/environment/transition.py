# backend/app/environment/transition.py
"""
Advanced State Transition Engine with:
- Multi-factor effects
- Strategy-specific impacts
- Sentiment feedback loops
- Stochastic elements
"""
from typing import Dict, Tuple, Any
import numpy as np
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class TransitionEffect:
    """Effect of a strategy pair on state metrics"""
    economic_stability: float = 0.0
    technology_independence: float = 0.0
    trade_stability: float = 0.0
    currency_stability: float = 0.0
    public_sentiment: float = 0.0
    supply_chain_stability: float = 0.0
    strategic_tension: float = 0.0
    ai_capability: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'economic_stability': self.economic_stability,
            'technology_independence': self.technology_independence,
            'trade_stability': self.trade_stability,
            'currency_stability': self.currency_stability,
            'public_sentiment': self.public_sentiment,
            'supply_chain_stability': self.supply_chain_stability,
            'strategic_tension': self.strategic_tension,
            'ai_capability': self.ai_capability
        }

class StateTransitionEngine:
    """
    Calculates state transitions based on:
    1. Strategy pair effects
    2. Current state context
    3. Sentiment feedback
    4. Stochastic elements
    """
    
    def __init__(
        self,
        stochastic: bool = True,
        noise_scale: float = 0.35,
        recovery_rate: float = 0.035,
        tension_relaxation: float = 0.055,
        max_effect_per_step: float = 7.5,
    ):
        self.stochastic = stochastic
        self.noise_scale = noise_scale
        self.recovery_rate = recovery_rate
        self.tension_relaxation = tension_relaxation
        self.max_effect_per_step = max_effect_per_step
        self._rng = np.random.default_rng()
        
        # Strategy effect templates
        self.effect_templates = self._initialize_effect_templates()
        
        logger.info("✅ State Transition Engine initialized")
    
    def _initialize_effect_templates(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Initialize effect templates for each strategy pair"""
        return {
            'H1': {  # Maximum Economic Pressure
                'S1': {  # De-dollarized Trade
                    'economic_stability': -8.0,
                    'trade_stability': -6.0,
                    'currency_stability': -5.0,
                    'strategic_tension': 10.0,
                    'public_sentiment': -0.05,
                },
                'S2': {  # Local AI
                    'economic_stability': -5.0,
                    'technology_independence': 5.0,
                    'strategic_tension': 5.0,
                    'public_sentiment': -0.03,
                },
                'S3': {  # Trade Diversification
                    'economic_stability': -6.0,
                    'trade_stability': -3.0,
                    'strategic_tension': 3.0,
                    'public_sentiment': -0.02,
                },
                'S4': {  # Defensive Alliance
                    'economic_stability': -3.0,
                    'strategic_tension': 15.0,
                    'public_sentiment': -0.08,
                }
            },
            'H2': {  # Information Influence
                'S1': {
                    'public_sentiment': -0.10,
                    'strategic_tension': 5.0,
                    'economic_stability': -2.0,
                },
                'S2': {
                    'public_sentiment': -0.08,
                    'technology_independence': 2.0,
                    'ai_capability': 3.0,
                },
                'S3': {
                    'public_sentiment': -0.05,
                    'trade_stability': -2.0,
                    'strategic_tension': 3.0,
                },
                'S4': {
                    'public_sentiment': -0.12,
                    'strategic_tension': 8.0,
                    'supply_chain_stability': -3.0,
                }
            },
            'H3': {  # Currency/Financial Pressure
                'S1': {
                    'currency_stability': -10.0,
                    'economic_stability': -5.0,
                    'strategic_tension': 8.0,
                },
                'S2': {
                    'currency_stability': -5.0,
                    'economic_stability': -3.0,
                    'technology_independence': 3.0,
                },
                'S3': {
                    'currency_stability': -7.0,
                    'trade_stability': -3.0,
                    'strategic_tension': 5.0,
                },
                'S4': {
                    'currency_stability': -5.0,
                    'strategic_tension': 12.0,
                    'economic_stability': -4.0,
                }
            },
            'H4': {  # High-Escalation Policy
                'S1': {
                    'strategic_tension': 20.0,
                    'economic_stability': -8.0,
                    'trade_stability': -8.0,
                    'public_sentiment': -0.15,
                },
                'S2': {
                    'strategic_tension': 15.0,
                    'technology_independence': 8.0,
                    'ai_capability': 5.0,
                    'public_sentiment': -0.10,
                },
                'S3': {
                    'strategic_tension': 18.0,
                    'trade_stability': -6.0,
                    'public_sentiment': -0.12,
                },
                'S4': {
                    'strategic_tension': 25.0,
                    'supply_chain_stability': -10.0,
                    'public_sentiment': -0.18,
                }
            }
        }
    
    def apply_transition(
        self,
        current_state: Dict[str, float],
        hegemon_strategy: str,
        sovereign_strategy: str,
        hegemon_payoff: float,
        sovereign_payoff: float
    ) -> Dict[str, float]:
        """
        Apply state transition based on strategy pair
        Returns new state dictionary
        """
        # Get base effect
        base_effect = {k: v * 0.55 for k, v in self._get_base_effect(hegemon_strategy, sovereign_strategy).items()}
        
        # Apply context modifiers
        context_effect = self._apply_context_modifiers(
            current_state, hegemon_strategy, sovereign_strategy
        )
        
        # Apply payoff feedback
        payoff_effect = self._apply_payoff_feedback(
            hegemon_payoff, sovereign_payoff
        )
        
        # Apply sentiment feedback loop
        sentiment_effect = self._apply_sentiment_feedback(
            current_state, hegemon_strategy, sovereign_strategy
        )
        
        # Combine all effects.  The transition model is intentionally damped:
        # repeated adverse actions should matter, but must not deterministically
        # drive the world to 0/100 after a few rounds.
        combined_effect = self._combine_effects(
            base_effect, context_effect, payoff_effect, sentiment_effect
        )

        # Mean-reversion provides a soft recovery force and prevents absorbing
        # states.  Recovery is strongest near the boundaries and near-neutral
        # for healthy states.
        recovery = self._apply_recovery(current_state)
        combined_effect = self._combine_effects(combined_effect, recovery, {}, {})

        # Conflict fatigue: once tension is already elevated, additional
        # escalation has sharply diminishing state impact. This is the main
        # guard against a runaway 100-tension attractor.
        tension = current_state.get('strategic_tension', 50.0)
        if tension > 45.0 and combined_effect.get('strategic_tension', 0.0) > 0:
            fatigue = 1.0 - 0.97 * min(1.0, (tension - 45.0) / 55.0)
            combined_effect['strategic_tension'] *= fatigue

        # Apply nonlinear boundary damping before noise.
        combined_effect = self._apply_boundary_damping(current_state, combined_effect)

        # Apply small stochastic noise.
        if self.stochastic:
            combined_effect = self._apply_noise(combined_effect)

        # Hard cap one-step movement for numerical stability.
        combined_effect = {
            key: float(np.clip(value, -self.max_effect_per_step, self.max_effect_per_step))
            for key, value in combined_effect.items()
        }

        # Update state
        new_state = current_state.copy()
        for key, value in combined_effect.items():
            if key in new_state:
                new_state[key] = new_state.get(key, 50) + value
            else:
                new_state[key] = value

        # Ensure values are in valid ranges
        new_state = self._clamp_state(new_state)
        
        return new_state
    
    def _get_base_effect(
        self,
        hegemon_strategy: str,
        sovereign_strategy: str
    ) -> Dict[str, float]:
        """Get base effect from templates"""
        if hegemon_strategy in self.effect_templates:
            if sovereign_strategy in self.effect_templates[hegemon_strategy]:
                return self.effect_templates[hegemon_strategy][sovereign_strategy].copy()
        
        # Default effect if not found
        return {
            'economic_stability': 0.0,
            'technology_independence': 0.0,
            'trade_stability': 0.0,
            'currency_stability': 0.0,
            'public_sentiment': 0.0,
            'supply_chain_stability': 0.0,
            'strategic_tension': 0.0,
            'ai_capability': 0.0
        }
    
    def _apply_recovery(self, state: Dict[str, float]) -> Dict[str, float]:
        """Soft mean reversion toward a healthy strategic equilibrium."""
        target = {
            'economic_stability': 62.0,
            'technology_independence': 60.0,
            'trade_stability': 62.0,
            'currency_stability': 62.0,
            'public_sentiment': 0.10,
            'supply_chain_stability': 60.0,
            'strategic_tension': 38.0,
            'ai_capability': 60.0,
        }
        recovery = {}
        for key, target_value in target.items():
            current = state.get(key, target_value)
            rate = self.recovery_rate
            if key == 'strategic_tension':
                rate = self.tension_relaxation
            recovery[key] = (target_value - current) * rate
        return recovery

    def _apply_boundary_damping(
        self, state: Dict[str, float], effect: Dict[str, float]
    ) -> Dict[str, float]:
        """Dampen harmful movement as a metric approaches 0 or 100."""
        damped = effect.copy()
        for key, delta in effect.items():
            if key == 'public_sentiment':
                continue
            value = state.get(key, 50.0)
            if delta < 0 and value < 25.0:
                factor = max(0.20, value / 25.0)
                damped[key] = delta * factor
            elif delta > 0 and value > 75.0:
                factor = max(0.20, (100.0 - value) / 25.0)
                damped[key] = delta * factor
        return damped

    def _apply_context_modifiers(
        self,
        state: Dict[str, float],
        hegemon_strategy: str,
        sovereign_strategy: str
    ) -> Dict[str, float]:
        """Apply context-based modifiers"""
        modifiers = {}
        
        # Economic context: avoid cliff effects when the economy is already weak.
        economy = state.get('economic_stability', 50)
        if economy < 40:
            modifiers['economic_stability'] = 1.5 * (40.0 - economy) / 40.0
        elif economy > 80:
            modifiers['economic_stability'] = 1.0 * (80.0 - economy) / 20.0
        
        # Technology context
        if state.get('technology_independence', 50) < 40:
            if sovereign_strategy == 'S2':  # Local AI
                modifiers['technology_independence'] = 5.0
                modifiers['ai_capability'] = 3.0
        
        # Trade context
        if state.get('trade_stability', 50) < 40:
            if sovereign_strategy == 'S3':  # Trade Diversification
                modifiers['trade_stability'] = 4.0
        
        # Sentiment context: damp, rather than amplify, negative feedback.
        sentiment = state.get('public_sentiment', 0)
        if sentiment < -0.3:
            modifiers['public_sentiment'] = 0.02 * (-sentiment)
            modifiers['strategic_tension'] = 1.5 * (-sentiment)
        
        # Tension context: escalation becomes progressively less effective at high tension.
        tension = state.get('strategic_tension', 50)
        if tension > 70 and hegemon_strategy == 'H4':
            excess = min(30.0, tension - 70.0) / 30.0
            modifiers['strategic_tension'] = 3.0 * excess
            modifiers['economic_stability'] = -2.0 * excess
        
        return modifiers
    
    def _apply_payoff_feedback(
        self,
        hegemon_payoff: float,
        sovereign_payoff: float
    ) -> Dict[str, float]:
        """Apply feedback from payoffs"""
        feedback = {}
        
        # Hegemon payoff feedback
        if hegemon_payoff > 20:
            feedback['economic_stability'] = 1.0
            feedback['strategic_tension'] = -1.0
        elif hegemon_payoff < 10:
            feedback['economic_stability'] = -1.0
            feedback['strategic_tension'] = 1.0
        
        # Sovereign payoff feedback
        if sovereign_payoff > 20:
            feedback['trade_stability'] = 1.0
            feedback['public_sentiment'] = 0.025
        elif sovereign_payoff < 10:
            feedback['trade_stability'] = -1.0
            feedback['public_sentiment'] = -0.025
        
        return feedback
    
    def _apply_sentiment_feedback(
        self,
        state: Dict[str, float],
        hegemon_strategy: str,
        sovereign_strategy: str
    ) -> Dict[str, float]:
        """Apply sentiment feedback loop"""
        feedback = {}
        current_sentiment = state.get('public_sentiment', 0)
        
        # Positive sentiment reinforces stability
        if current_sentiment > 0.3:
            feedback['economic_stability'] = 1.0
            feedback['trade_stability'] = 1.0
            feedback['strategic_tension'] = -1.0
        
        # Negative sentiment amplifies tension
        elif current_sentiment < -0.3:
            pressure = min(1.0, (-current_sentiment - 0.3) / 0.7)
            feedback['strategic_tension'] = 1.0 * pressure
            feedback['economic_stability'] = -0.5 * pressure
            feedback['trade_stability'] = -0.5 * pressure
        
        # Strategy-specific sentiment effects
        if hegemon_strategy == 'H2':  # Information influence
            feedback['public_sentiment'] = -0.03
        elif sovereign_strategy == 'S1':  # De-dollarization
            feedback['public_sentiment'] = 0.02
        
        return feedback
    
    def _combine_effects(
        self,
        base: Dict[str, float],
        context: Dict[str, float],
        payoff: Dict[str, float],
        sentiment: Dict[str, float]
    ) -> Dict[str, float]:
        """Combine all effects"""
        combined = base.copy()
        
        for effect in [context, payoff, sentiment]:
            for key, value in effect.items():
                if key in combined:
                    combined[key] = combined.get(key, 0) + value
                else:
                    combined[key] = value
        
        return combined
    
    def _apply_noise(self, effect: Dict[str, float]) -> Dict[str, float]:
        """Apply stochastic noise to effects"""
        noisy = effect.copy()
        
        for key in noisy:
            noise = self._rng.normal(0, self.noise_scale)
            noisy[key] = noisy.get(key, 0) + noise
        
        return noisy
    
    def _clamp_state(self, state: Dict[str, float]) -> Dict[str, float]:
        """Clamp state values to valid ranges"""
        clamped = state.copy()
        
        for key, value in clamped.items():
            if key == 'public_sentiment':
                clamped[key] = max(-1.0, min(1.0, value))
            else:
                clamped[key] = max(0.0, min(100.0, value))
        
        return clamped
    
    def get_transition_explanation(
        self,
        hegemon_strategy: str,
        sovereign_strategy: str,
        state: Dict[str, float]
    ) -> Dict[str, Any]:
        """Get detailed explanation of transition"""
        explanation = {
            'strategy_pair': f"{hegemon_strategy} vs {sovereign_strategy}",
            'current_state': state.copy(),
            'effects': {},
            'reasoning': []
        }
        
        # Get base effect
        base_effect = {k: v * 0.55 for k, v in self._get_base_effect(hegemon_strategy, sovereign_strategy).items()}
        explanation['effects']['base'] = base_effect
        explanation['reasoning'].append(f"Base effect from {hegemon_strategy} vs {sovereign_strategy}")
        
        # Context modifiers
        context = self._apply_context_modifiers(state, hegemon_strategy, sovereign_strategy)
        if context:
            explanation['effects']['context'] = context
            explanation['reasoning'].append(f"Context modifiers applied: {list(context.keys())}")
        
        # Sentiment feedback
        sentiment = self._apply_sentiment_feedback(state, hegemon_strategy, sovereign_strategy)
        if sentiment:
            explanation['effects']['sentiment'] = sentiment
            explanation['reasoning'].append(f"Sentiment feedback applied: {list(sentiment.keys())}")
        
        return explanation