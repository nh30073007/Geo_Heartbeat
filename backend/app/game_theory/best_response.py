from typing import Dict, Tuple, Optional
import numpy as np
from .payoff import PayoffMatrix

class BestResponse:
    """Calculate best responses for both agents"""
    
    def __init__(self, payoff_matrix: PayoffMatrix):
        self.payoff_matrix = payoff_matrix
        self.hegemon_strategies = ['H1', 'H2', 'H3', 'H4']
        self.sovereign_strategies = ['S1', 'S2', 'S3', 'S4']
    
    def hegemon_best_response(self, sovereign_strategy: str) -> Tuple[str, float]:
        """Find hegemon's best response to sovereign strategy"""
        payoffs = self.payoff_matrix.get_hegemon_payoffs(sovereign_strategy)
        best_strategy = max(payoffs, key=payoffs.get)
        return best_strategy, payoffs[best_strategy]
    
    def sovereign_best_response(self, hegemon_strategy: str) -> Tuple[str, float]:
        """Find sovereign's best response to hegemon strategy"""
        payoffs = self.payoff_matrix.get_sovereign_payoffs(hegemon_strategy)
        best_strategy = max(payoffs, key=payoffs.get)
        return best_strategy, payoffs[best_strategy]
    
    def find_nash_equilibrium(self) -> list:
        """Find all pure strategy Nash equilibria"""
        equilibria = []
        
        for h in self.hegemon_strategies:
            for s in self.sovereign_strategies:
                payoff = self.payoff_matrix.get_payoff(h, s)
                h_payoff, s_payoff = payoff
                
                # Check if this is a best response for both
                h_best = self.hegemon_best_response(s)
                s_best = self.sovereign_best_response(h)
                
                if h_best[1] == h_payoff and s_best[1] == s_payoff:
                    equilibria.append((h, s, h_payoff, s_payoff))
        
        return equilibria