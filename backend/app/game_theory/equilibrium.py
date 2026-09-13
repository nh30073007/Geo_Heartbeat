"""
Advanced Equilibrium Analysis
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx
from scipy.optimize import minimize, Bounds
import logging

logger = logging.getLogger(__name__)

class EquilibriumType(Enum):
    """Types of equilibria"""
    PURE_NASH = "Pure Nash"
    MIXED_NASH = "Mixed Nash"
    CORRELATED = "Correlated"
    EVOLUTIONARY_STABLE = "Evolutionary Stable"
    COALITION_PROOF = "Coalition-Proof"

@dataclass
class EquilibriumResult:
    """Complete equilibrium analysis result"""
    equilibria: List[Dict]
    equilibrium_type: EquilibriumType
    stability_score: float
    pareto_optimal: bool
    social_welfare: float
    fairness_index: float
    dynamics: List[Dict] = field(default_factory=list)

class EquilibriumAnalyzer:
    """
    Comprehensive equilibrium analysis including:
    1. Pure Nash Equilibrium
    2. Mixed Nash Equilibrium
    3. Correlated Equilibrium
    4. Evolutionary Stable Strategy
    5. Coalition-Proof Equilibrium
    """
    
    def __init__(self, payoff_matrix):
        self.payoff_matrix = payoff_matrix
        self.hegemon_strategies = ['H1', 'H2', 'H3', 'H4']
        self.sovereign_strategies = ['S1', 'S2', 'S3', 'S4']
        
        logger.info("✅ Equilibrium Analyzer initialized")
    
    def analyze_all(
        self,
        state: Dict[str, float],
        include_mixed: bool = True
    ) -> Dict[EquilibriumType, EquilibriumResult]:
        """Run complete equilibrium analysis"""
        results = {}
        
        # Pure Nash
        results[EquilibriumType.PURE_NASH] = self.find_pure_nash(state)
        
        # Mixed Nash
        if include_mixed:
            results[EquilibriumType.MIXED_NASH] = self.find_mixed_nash(state)
        
        # Correlated Equilibrium
        results[EquilibriumType.CORRELATED] = self.find_correlated_equilibrium(state)
        
        # Evolutionary Stable
        results[EquilibriumType.EVOLUTIONARY_STABLE] = self.find_evolutionary_stable(state)
        
        return results
    
    def find_pure_nash(self, state: Dict[str, float]) -> EquilibriumResult:
        """Find all pure strategy Nash equilibria"""
        equilibria = []
        stability_scores = []
        
        for h in self.hegemon_strategies:
            for s in self.sovereign_strategies:
                # Get payoff
                result = self.payoff_matrix.get_adaptive_payoff(h, s, state)
                h_payoff = result.hegemon_payoff
                s_payoff = result.sovereign_payoff
                
                # Check if best response
                h_best = self._is_best_response_hegemon(h, s, state)
                s_best = self._is_best_response_sovereign(s, h, state)
                
                if h_best and s_best:
                    equilibria.append({
                        'hegemon_strategy': h,
                        'sovereign_strategy': s,
                        'hegemon_payoff': h_payoff,
                        'sovereign_payoff': s_payoff,
                        'total_payoff': h_payoff + s_payoff
                    })
                    stability_scores.append(self._calculate_stability(h, s, state))
        
        # Calculate social welfare
        if equilibria:
            total_payoff = sum(e['total_payoff'] for e in equilibria)
            social_welfare = total_payoff / len(equilibria)
            pareto_optimal = self._check_pareto_optimal(equilibria)
            fairness = self._calculate_fairness(equilibria)
            avg_stability = np.mean(stability_scores) if stability_scores else 0.5
        else:
            social_welfare = 0
            pareto_optimal = False
            fairness = 0
            avg_stability = 0
        
        return EquilibriumResult(
            equilibria=equilibria,
            equilibrium_type=EquilibriumType.PURE_NASH,
            stability_score=avg_stability,
            pareto_optimal=pareto_optimal,
            social_welfare=social_welfare,
            fairness_index=fairness
        )
    
    def find_mixed_nash(self, state: Dict[str, float]) -> EquilibriumResult:
        """Find mixed strategy Nash equilibrium"""
        # Use linear programming
        from .mixed_strategy import MixedStrategySolver
        
        solver = MixedStrategySolver(self.payoff_matrix)
        result = solver.solve_linear_programming(state)
        
        equilibria = [{
            'hegemon_strategy': result.hegemon_strategy,
            'sovereign_strategy': result.sovereign_strategy,
            'hegemon_payoff': result.expected_payoff_hegemon,
            'sovereign_payoff': result.expected_payoff_sovereign,
            'total_payoff': result.expected_payoff_hegemon + result.expected_payoff_sovereign,
            'convergence': result.convergence,
            'iterations': result.iterations
        }]
        
        return EquilibriumResult(
            equilibria=equilibria,
            equilibrium_type=EquilibriumType.MIXED_NASH,
            stability_score=result.convergence,
            pareto_optimal=False,
            social_welfare=(result.expected_payoff_hegemon + result.expected_payoff_sovereign) / 2,
            fairness_index=self._calculate_fairness(equilibria)
        )
    
    def find_correlated_equilibrium(self, state: Dict[str, float]) -> EquilibriumResult:
        """
        Find correlated equilibrium using linear programming
        """
        # Build payoff matrix
        payoff_matrix = self._build_payoff_matrix(state)
        n = len(self.hegemon_strategies)
        m = len(self.sovereign_strategies)
        
        # Decision variables: probability distribution over strategy profiles
        n_vars = n * m
        
        # Objective: Maximize social welfare
        c = -payoff_matrix.flatten()  # Minimize negative payoff
        
        # Constraints for correlated equilibrium
        # For each hegemon strategy i and alternative i'
        A_eq = []
        b_eq = []
        
        for i in range(n):
            for i_prime in range(n):
                if i != i_prime:
                    constraint = np.zeros(n_vars)
                    for j in range(m):
                        idx = i * m + j
                        idx_prime = i_prime * m + j
                        constraint[idx] = payoff_matrix[i, j] - payoff_matrix[i_prime, j]
                    A_eq.append(constraint)
                    b_eq.append(0)
        
        # For each sovereign strategy j and alternative j'
        for j in range(m):
            for j_prime in range(m):
                if j != j_prime:
                    constraint = np.zeros(n_vars)
                    for i in range(n):
                        idx = i * m + j
                        idx_prime = i * m + j_prime
                        constraint[idx] = payoff_matrix[i, j] - payoff_matrix[i, j_prime]
                    A_eq.append(constraint)
                    b_eq.append(0)
        
        # Sum of probabilities = 1
        A_eq.append(np.ones(n_vars))
        b_eq.append(1)
        
        # Solve LP
        bounds = Bounds(0, 1)
        result = minimize(
            lambda x: np.dot(c, x),
            np.ones(n_vars) / n_vars,
            constraints={'type': 'eq', 'fun': lambda x: A_eq @ x - b_eq},
            bounds=bounds,
            method='SLSQP'
        )
        
        if result.success:
            probabilities = result.x.reshape(n, m)
            distributions = []
            for i in range(n):
                for j in range(m):
                    if probabilities[i, j] > 0.01:
                        distributions.append({
                            'hegemon': self.hegemon_strategies[i],
                            'sovereign': self.sovereign_strategies[j],
                            'probability': probabilities[i, j]
                        })
            
            expected_payoff = -result.fun
            
            equilibria = [{
                'distributions': distributions,
                'expected_payoff': expected_payoff,
                'social_welfare': expected_payoff
            }]
            
            return EquilibriumResult(
                equilibria=equilibria,
                equilibrium_type=EquilibriumType.CORRELATED,
                stability_score=0.8,
                pareto_optimal=False,
                social_welfare=expected_payoff,
                fairness_index=0.5
            )
        else:
            logger.warning("Correlated equilibrium not found, returning default")
            return self.find_pure_nash(state)
    
    def find_evolutionary_stable(
        self,
        state: Dict[str, float],
        max_iterations: int = 1000
    ) -> EquilibriumResult:
        """
        Find Evolutionary Stable Strategy (ESS)
        Using replicator dynamics
        """
        n = len(self.hegemon_strategies)
        m = len(self.sovereign_strategies)
        
        # Initialize populations
        h_population = np.ones(n) / n
        s_population = np.ones(m) / m
        
        # Build payoff matrix
        payoff_matrix = self._build_payoff_matrix(state)
        
        dynamics = []
        
        for iteration in range(max_iterations):
            # Calculate fitness
            h_fitness = payoff_matrix @ s_population
            s_fitness = h_population @ payoff_matrix
            
            # Average fitness
            h_avg_fitness = np.dot(h_population, h_fitness)
            s_avg_fitness = np.dot(s_population, s_fitness)
            
            # Replicator equation
            h_new = h_population * (h_fitness / max(h_avg_fitness, 1e-10))
            s_new = s_population * (s_fitness / max(s_avg_fitness, 1e-10))
            
            # Normalize
            h_new = h_new / np.sum(h_new)
            s_new = s_new / np.sum(s_new)
            
            dynamics.append({
                'iteration': iteration,
                'h_population': h_new.copy(),
                's_population': s_new.copy()
            })
            
            # Check convergence
            if np.max(np.abs(h_new - h_population)) < 1e-6 and \
               np.max(np.abs(s_new - s_population)) < 1e-6:
                break
            
            h_population = h_new
            s_population = s_new
        
        # Check if ESS
        is_ess = self._check_ess(h_population, s_population, payoff_matrix)
        
        equilibria = [{
            'hegemon_population': {h: p for h, p in zip(self.hegemon_strategies, h_population)},
            'sovereign_population': {s: p for s, p in zip(self.sovereign_strategies, s_population)},
            'is_ess': is_ess,
            'convergence_iterations': len(dynamics)
        }]
        
        return EquilibriumResult(
            equilibria=equilibria,
            equilibrium_type=EquilibriumType.EVOLUTIONARY_STABLE,
            stability_score=0.9 if is_ess else 0.5,
            pareto_optimal=False,
            social_welfare=np.mean(payoff_matrix),
            fairness_index=0.5,
            dynamics=dynamics
        )
    
    def _is_best_response_hegemon(
        self,
        h_strategy: str,
        s_strategy: str,
        state: Dict[str, float]
    ) -> bool:
        """Check if h_strategy is best response to s_strategy"""
        h_payoffs = []
        
        for h in self.hegemon_strategies:
            result = self.payoff_matrix.get_adaptive_payoff(h, s_strategy, state)
            h_payoffs.append(result.hegemon_payoff)
        
        current_payoff = self.payoff_matrix.get_adaptive_payoff(
            h_strategy, s_strategy, state
        ).hegemon_payoff
        
        return current_payoff >= max(h_payoffs) - 1e-6
    
    def _is_best_response_sovereign(
        self,
        s_strategy: str,
        h_strategy: str,
        state: Dict[str, float]
    ) -> bool:
        """Check if s_strategy is best response to h_strategy"""
        s_payoffs = []
        
        for s in self.sovereign_strategies:
            result = self.payoff_matrix.get_adaptive_payoff(h_strategy, s, state)
            s_payoffs.append(result.sovereign_payoff)
        
        current_payoff = self.payoff_matrix.get_adaptive_payoff(
            h_strategy, s_strategy, state
        ).sovereign_payoff
        
        return current_payoff >= max(s_payoffs) - 1e-6
    
    def _calculate_stability(
        self,
        h_strategy: str,
        s_strategy: str,
        state: Dict[str, float]
    ) -> float:
        """Calculate stability score for equilibrium"""
        stability = 0.5
        
        # Check deviation gains
        h_deviation_gain = self._max_deviation_gain_hegemon(h_strategy, s_strategy, state)
        s_deviation_gain = self._max_deviation_gain_sovereign(s_strategy, h_strategy, state)
        
        # Lower deviation gain = higher stability
        stability -= (h_deviation_gain + s_deviation_gain) * 0.2
        
        # State stability influences
        stability += (1 - state.get('strategic_tension', 50) / 100) * 0.2
        
        return max(0, min(1, stability))
    
    def _max_deviation_gain_hegemon(
        self,
        h_strategy: str,
        s_strategy: str,
        state: Dict[str, float]
    ) -> float:
        """Maximum gain from deviating for hegemon"""
        current = self.payoff_matrix.get_adaptive_payoff(
            h_strategy, s_strategy, state
        ).hegemon_payoff
        
        max_deviation = 0
        for h in self.hegemon_strategies:
            if h != h_strategy:
                dev = self.payoff_matrix.get_adaptive_payoff(
                    h, s_strategy, state
                ).hegemon_payoff
                max_deviation = max(max_deviation, dev - current)
        
        return max(0, max_deviation)
    
    def _max_deviation_gain_sovereign(
        self,
        s_strategy: str,
        h_strategy: str,
        state: Dict[str, float]
    ) -> float:
        """Maximum gain from deviating for sovereign"""
        current = self.payoff_matrix.get_adaptive_payoff(
            h_strategy, s_strategy, state
        ).sovereign_payoff
        
        max_deviation = 0
        for s in self.sovereign_strategies:
            if s != s_strategy:
                dev = self.payoff_matrix.get_adaptive_payoff(
                    h_strategy, s, state
                ).sovereign_payoff
                max_deviation = max(max_deviation, dev - current)
        
        return max(0, max_deviation)
    
    def _check_pareto_optimal(self, equilibria: List[Dict]) -> bool:
        """Check if equilibria are Pareto optimal"""
        if not equilibria:
            return False
        
        for i, eq1 in enumerate(equilibria):
            for j, eq2 in enumerate(equilibria):
                if i != j:
                    # Check if eq2 dominates eq1
                    if eq2['hegemon_payoff'] >= eq1['hegemon_payoff'] and \
                       eq2['sovereign_payoff'] >= eq1['sovereign_payoff'] and \
                       (eq2['hegemon_payoff'] > eq1['hegemon_payoff'] or \
                        eq2['sovereign_payoff'] > eq1['sovereign_payoff']):
                        return False
        
        return True
    
    def _calculate_fairness(self, equilibria: List[Dict]) -> float:
        """Calculate fairness index (1 = perfectly fair)"""
        if not equilibria:
            return 0
        
        fairness_scores = []
        for eq in equilibria:
            if 'hegemon_payoff' in eq and 'sovereign_payoff' in eq:
                h = eq['hegemon_payoff']
                s = eq['sovereign_payoff']
                total = h + s
                if total > 0:
                    fairness = 1 - abs(h - s) / total
                    fairness_scores.append(fairness)
        
        return np.mean(fairness_scores) if fairness_scores else 0
    
    def _build_payoff_matrix(self, state: Dict[str, float]) -> np.ndarray:
        """Build payoff matrix for current state"""
        matrix = np.zeros((len(self.hegemon_strategies), len(self.sovereign_strategies)))
        
        for i, h in enumerate(self.hegemon_strategies):
            for j, s in enumerate(self.sovereign_strategies):
                result = self.payoff_matrix.get_adaptive_payoff(h, s, state)
                matrix[i, j] = result.hegemon_payoff
        
        return matrix
    
    def _check_ess(
        self,
        h_population: np.ndarray,
        s_population: np.ndarray,
        payoff_matrix: np.ndarray
    ) -> bool:
        """Check if strategy profile is ESS"""
        # Check if Nash equilibrium
        h_best = self._best_response_hegemon(s_population, payoff_matrix)
        s_best = self._best_response_sovereign(h_population, payoff_matrix)
        
        if not h_best or not s_best:
            return False
        
        # Check stability against mutants
        n_mutants = 100
        for _ in range(n_mutants):
            # Generate mutant
            h_mutant = np.random.dirichlet(np.ones(len(h_population)))
            s_mutant = np.random.dirichlet(np.ones(len(s_population)))
            
            # Check if mutant can invade
            if self._can_invade(h_population, h_mutant, s_population, payoff_matrix):
                return False
        
        return True
    
    def _can_invade(
        self,
        h_pop: np.ndarray,
        h_mutant: np.ndarray,
        s_pop: np.ndarray,
        payoff_matrix: np.ndarray
    ) -> bool:
        """Check if mutant can invade population"""
        # Check if mutant has higher payoff
        mutant_payoff = self._calculate_hegemon_payoff(h_mutant, s_pop, payoff_matrix)
        resident_payoff = self._calculate_hegemon_payoff(h_pop, s_pop, payoff_matrix)
        
        return mutant_payoff > resident_payoff
    
    def _calculate_hegemon_payoff(
        self,
        h_strategy: np.ndarray,
        s_strategy: np.ndarray,
        payoff_matrix: np.ndarray
    ) -> float:
        """Calculate expected payoff for hegemon"""
        return float(h_strategy @ payoff_matrix @ s_strategy)
    
    def _best_response_hegemon(
        self,
        s_strategy: np.ndarray,
        payoff_matrix: np.ndarray
    ) -> bool:
        """Check if hegemon has a best response"""
        expected_payoffs = payoff_matrix @ s_strategy
        return np.max(expected_payoffs) > 0
    
    def _best_response_sovereign(
        self,
        h_strategy: np.ndarray,
        payoff_matrix: np.ndarray
    ) -> bool:
        """Check if sovereign has a best response"""
        expected_payoffs = h_strategy @ payoff_matrix
        return np.max(expected_payoffs) > 0