# test_game_theory.py
from app.game_theory.payoff_matrix import AdaptivePayoffMatrix
from app.game_theory.mixed_strategy import MixedStrategySolver
from app.game_theory.equilibrium import EquilibriumAnalyzer

# Initialize
payoff = AdaptivePayoffMatrix()
solver = MixedStrategySolver(payoff)
analyzer = EquilibriumAnalyzer(payoff)

# Test state
state = {
    'economic_stability': 75,
    'technology_independence': 62,
    'trade_stability': 70,
    'currency_stability': 68,
    'public_sentiment': 0.22,
    'strategic_tension': 25,
    'ai_capability': 66
}

# Get equilibrium
results = analyzer.analyze_all(state)
print("Equilibrium Results:", results)