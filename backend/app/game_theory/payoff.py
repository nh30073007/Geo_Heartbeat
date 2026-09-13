"""Compatibility API for the project's adaptive payoff matrix."""
from __future__ import annotations

from typing import Dict, Tuple

from .payoff_matrix import AdaptivePayoffMatrix


class PayoffMatrix(AdaptivePayoffMatrix):
    """Backward-compatible payoff matrix used by best-response agents.

    The original codebase had a ``PayoffMatrix`` API while the newer adaptive
    implementation is named ``AdaptivePayoffMatrix``. This adapter keeps both
    call styles working from one source of truth.
    """

    def get_payoff(self, hegemon_strategy: str, sovereign_strategy: str) -> Tuple[float, float]:
        return self.base_matrix[hegemon_strategy][sovereign_strategy]

    def get_hegemon_payoffs(self, sovereign_strategy: str) -> Dict[str, float]:
        return {
            h: self.base_matrix[h][sovereign_strategy][0]
            for h in self.hegemon_strategies
        }

    def get_sovereign_payoffs(self, hegemon_strategy: str) -> Dict[str, float]:
        return {
            s: self.base_matrix[hegemon_strategy][s][1]
            for s in self.sovereign_strategies
        }


__all__ = ["PayoffMatrix", "AdaptivePayoffMatrix"]
