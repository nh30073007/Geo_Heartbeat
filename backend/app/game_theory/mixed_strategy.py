"""
Advanced Mixed Strategy Solver using Linear Programming
"""
import numpy as np
from typing import Dict, Tuple, List, Optional
from scipy.optimize import linprog
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class MixedStrategyResult:
    """Result of mixed strategy calculation"""
    hegemon_strategy: Dict[str, float]  # Strategy probabilities
    sovereign_strategy: Dict[str, float]
    expected_payoff_hegemon: float
    expected_payoff_sovereign: float
    value_game: float
    convergence: float
    iterations: int

class MixedStrategySolver:
    """
    Solves for mixed strategy Nash equilibrium using:
    1. Linear Programming (exact)
    2. Iterative Fictitious Play (approximate)
    3. Q-Learning (adaptive)
    """
    
    def __init__(self, payoff_matrix):
        self.payoff_matrix = payoff_matrix
        self.hegemon_strategies = ['H1', 'H2', 'H3', 'H4']
        self.sovereign_strategies = ['S1', 'S2', 'S3', 'S4']
        
        # Learning parameters
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.exploration_rate = 0.2
        
        # Q-table for RL
        self.q_table: Dict[Tuple[str, str], float] = {}
        self.q_table_history: List[Dict] = []
        
        logger.info("✅ Mixed Strategy Solver initialized")
    
    def solve_linear_programming(
        self,
        state: Dict[str, float],
        epsilon: float = 1e-6
    ) -> MixedStrategyResult:
        """
        Solve mixed strategy using Linear Programming
        """
        # Build payoff matrix for current state
        payoff_matrix = self._build_payoff_matrix(state)
        
        # Hegemon's LP: Maximize minimum payoff
        c = np.array([-1] + [0] * len(self.hegemon_strategies))
        
        # Constraints: For each sovereign strategy
        A = np.zeros((len(self.sovereign_strategies), len(self.hegemon_strategies) + 1))
        b = np.zeros(len(self.sovereign_strategies))
        
        for i, s in enumerate(self.sovereign_strategies):
            for j, h in enumerate(self.hegemon_strategies):
                A[i, j] = -payoff_matrix[j, i]  # Negative for maximization
            A[i, -1] = -1
            b[i] = 0
        
        # Sum of probabilities = 1
        A_eq = np.array([[1] * len(self.hegemon_strategies) + [0]])
        b_eq = np.array([1])
        
        # Bounds
        bounds = [(0, 1)] * len(self.hegemon_strategies) + [(None, None)]
        
        # Solve LP
        result = linprog(
            c,
            A_ub=A,
            b_ub=b,
            A_eq=A_eq,
            b_eq=b_eq,
            bounds=bounds,
            method='highs'
        )
        
        if result.success:
            hegemon_prob = result.x[:-1]
            value = -result.fun
            
            # Now solve for sovereign
            sovereign_prob = self._solve_sovereign_lp(payoff_matrix, value, epsilon)
            
            return MixedStrategyResult(
                hegemon_strategy={h: p for h, p in zip(self.hegemon_strategies, hegemon_prob)},
                sovereign_strategy={s: p for s, p in zip(self.sovereign_strategies, sovereign_prob)},
                expected_payoff_hegemon=value,
                expected_payoff_sovereign=self._calculate_sovereign_payoff(payoff_matrix, hegemon_prob, sovereign_prob),
                value_game=value,
                convergence=1.0,
                iterations=1
            )
        else:
            logger.warning("LP solver failed, using iterative method")
            return self.solve_fictitious_play(state, max_iterations=1000)
    
    def _solve_sovereign_lp(
        self,
        payoff_matrix: np.ndarray,
        hegemon_value: float,
        epsilon: float
    ) -> np.ndarray:
        """
        Solve sovereign's LP given hegemon's value
        """
        # Maximize sovereign payoff
        c = [-1] + [0] * len(self.sovereign_strategies)
        
        # Constraints
        A = np.zeros((len(self.hegemon_strategies), len(self.sovereign_strategies) + 1))
        b = np.zeros(len(self.hegemon_strategies))
        
        for i, h in enumerate(self.hegemon_strategies):
            for j, s in enumerate(self.sovereign_strategies):
                A[i, j] = payoff_matrix[i, j]
            A[i, -1] = -1
            b[i] = 0
        
        A_eq = np.array([[1] * len(self.sovereign_strategies) + [0]])
        b_eq = np.array([1])
        
        bounds = [(0, 1)] * len(self.sovereign_strategies) + [(None, None)]
        
        result = linprog(
            c,
            A_ub=A,
            b_ub=b,
            A_eq=A_eq,
            b_eq=b_eq,
            bounds=bounds,
            method='highs'
        )
        
        if result.success:
            return result.x[:-1]
        else:
            return np.ones(len(self.sovereign_strategies)) / len(self.sovereign_strategies)
    
    def solve_fictitious_play(
        self,
        state: Dict[str, float],
        max_iterations: int = 1000,
        tolerance: float = 1e-4
    ) -> MixedStrategyResult:
        """
        Solve using Fictitious Play (iterative learning)
        """
        # Initialize strategy counts
        h_counts = np.zeros(len(self.hegemon_strategies))
        s_counts = np.zeros(len(self.sovereign_strategies))
        
        # Initialize strategies
        h_strategy = np.ones(len(self.hegemon_strategies)) / len(self.hegemon_strategies)
        s_strategy = np.ones(len(self.sovereign_strategies)) / len(self.sovereign_strategies)
        
        # Build payoff matrix
        payoff_matrix = self._build_payoff_matrix(state)
        
        history = []
        
        for iteration in range(max_iterations):
            # Best response for hegemon
            h_best = self._best_response_hegemon(s_strategy, payoff_matrix)
            h_counts[h_best] += 1
            
            # Best response for sovereign
            s_best = self._best_response_sovereign(h_strategy, payoff_matrix)
            s_counts[s_best] += 1
            
            # Update strategies
            new_h_strategy = h_counts / max(1, np.sum(h_counts))
            new_s_strategy = s_counts / max(1, np.sum(s_counts))
            
            # Check convergence
            h_diff = np.max(np.abs(new_h_strategy - h_strategy))
            s_diff = np.max(np.abs(new_s_strategy - s_strategy))
            
            h_strategy = new_h_strategy
            s_strategy = new_s_strategy
            
            history.append((h_diff, s_diff))
            
            if h_diff < tolerance and s_diff < tolerance:
                break
        
        # Calculate expected payoffs
        h_expected = self._calculate_hegemon_payoff(payoff_matrix, h_strategy, s_strategy)
        s_expected = self._calculate_sovereign_payoff(payoff_matrix, h_strategy, s_strategy)
        
        return MixedStrategyResult(
            hegemon_strategy={h: p for h, p in zip(self.hegemon_strategies, h_strategy)},
            sovereign_strategy={s: p for s, p in zip(self.sovereign_strategies, s_strategy)},
            expected_payoff_hegemon=h_expected,
            expected_payoff_sovereign=s_expected,
            value_game=(h_expected + s_expected) / 2,
            convergence=min(1.0, 1.0 - (h_diff + s_diff) / 2),
            iterations=iteration + 1
        )
    
    def solve_q_learning(
        self,
        state: Dict[str, float],
        episodes: int = 1000,
        max_steps: int = 100
    ) -> MixedStrategyResult:
        """
        Solve using Q-Learning
        """
        # Initialize Q-table if empty
        for h in self.hegemon_strategies:
            for s in self.sovereign_strategies:
                if (h, s) not in self.q_table:
                    self.q_table[(h, s)] = np.random.uniform(0, 1)
        
        # Build payoff matrix
        payoff_matrix = self._build_payoff_matrix(state)
        
        h_counts = np.zeros(len(self.hegemon_strategies))
        s_counts = np.zeros(len(self.sovereign_strategies))
        
        for episode in range(episodes):
            # Decay exploration
            epsilon = self.exploration_rate * (1 - episode / episodes)
            
            # Choose strategies using epsilon-greedy
            h_idx = self._epsilon_greedy_hegemon(state, epsilon)
            s_idx = self._epsilon_greedy_sovereign(state, epsilon)
            
            # Get payoff
            h_payoff = payoff_matrix[h_idx, s_idx]
            s_payoff = payoff_matrix[h_idx, s_idx]
            
            # Update Q-table
            h_strategy = self.hegemon_strategies[h_idx]
            s_strategy = self.sovereign_strategies[s_idx]
            
            # Q-learning update for hegemon
            current_q = self.q_table.get((h_strategy, s_strategy), 0)
            next_q = self._max_next_q_hegemon(s_strategy, state)
            self.q_table[(h_strategy, s_strategy)] = (
                (1 - self.learning_rate) * current_q +
                self.learning_rate * (h_payoff + self.discount_factor * next_q)
            )
            
            # Update counts
            h_counts[h_idx] += 1
            s_counts[s_idx] += 1
            
            self.q_table_history.append(self.q_table.copy())
        
        # Final strategy
        h_strategy = h_counts / max(1, np.sum(h_counts))
        s_strategy = s_counts / max(1, np.sum(s_counts))
        
        return MixedStrategyResult(
            hegemon_strategy={h: p for h, p in zip(self.hegemon_strategies, h_strategy)},
            sovereign_strategy={s: p for s, p in zip(self.sovereign_strategies, s_strategy)},
            expected_payoff_hegemon=self._calculate_hegemon_payoff(payoff_matrix, h_strategy, s_strategy),
            expected_payoff_sovereign=self._calculate_sovereign_payoff(payoff_matrix, h_strategy, s_strategy),
            value_game=0.5,
            convergence=0.8,
            iterations=episodes * max_steps
        )
    
    def _build_payoff_matrix(self, state: Dict[str, float]) -> np.ndarray:
        """Build payoff matrix for current state"""
        matrix = np.zeros((len(self.hegemon_strategies), len(self.sovereign_strategies)))
        
        for i, h in enumerate(self.hegemon_strategies):
            for j, s in enumerate(self.sovereign_strategies):
                result = self.payoff_matrix.get_adaptive_payoff(h, s, state)
                matrix[i, j] = result.hegemon_payoff  # Row player (hegemon)
        
        return matrix
    
    def _best_response_hegemon(
        self,
        s_strategy: np.ndarray,
        payoff_matrix: np.ndarray
    ) -> int:
        """Find hegemon's best response"""
        expected_payoffs = payoff_matrix @ s_strategy
        return np.argmax(expected_payoffs)
    
    def _best_response_sovereign(
        self,
        h_strategy: np.ndarray,
        payoff_matrix: np.ndarray
    ) -> int:
        """Find sovereign's best response"""
        expected_payoffs = h_strategy @ payoff_matrix
        return np.argmax(expected_payoffs)
    
    def _calculate_hegemon_payoff(
        self,
        payoff_matrix: np.ndarray,
        h_strategy: np.ndarray,
        s_strategy: np.ndarray
    ) -> float:
        """Calculate expected payoff for hegemon"""
        return float(h_strategy @ payoff_matrix @ s_strategy)
    
    def _calculate_sovereign_payoff(
        self,
        payoff_matrix: np.ndarray,
        h_strategy: np.ndarray,
        s_strategy: np.ndarray
    ) -> float:
        """Calculate expected payoff for sovereign"""
        return float(h_strategy @ payoff_matrix.T @ s_strategy)
    
    def _epsilon_greedy_hegemon(self, state: Dict[str, float], epsilon: float) -> int:
        """Epsilon-greedy strategy selection for hegemon"""
        if np.random.random() < epsilon:
            return np.random.randint(len(self.hegemon_strategies))
        else:
            # Choose best based on Q-values
            h_strategies = self.hegemon_strategies
            q_values = []
            for h in h_strategies:
                avg_q = np.mean([
                    self.q_table.get((h, s), 0) 
                    for s in self.sovereign_strategies
                ])
                q_values.append(avg_q)
            return np.argmax(q_values)
    
    def _epsilon_greedy_sovereign(self, state: Dict[str, float], epsilon: float) -> int:
        """Epsilon-greedy strategy selection for sovereign"""
        if np.random.random() < epsilon:
            return np.random.randint(len(self.sovereign_strategies))
        else:
            # Choose best based on Q-values
            s_strategies = self.sovereign_strategies
            q_values = []
            for s in s_strategies:
                avg_q = np.mean([
                    self.q_table.get((h, s), 0) 
                    for h in self.hegemon_strategies
                ])
                q_values.append(avg_q)
            return np.argmax(q_values)
    
    def _max_next_q_hegemon(self, s_strategy: str, state: Dict[str, float]) -> float:
        """Maximum next Q value for hegemon"""
        max_q = -float('inf')
        for h in self.hegemon_strategies:
            q_val = self.q_table.get((h, s_strategy), 0)
            if q_val > max_q:
                max_q = q_val
        return max_q