# backend/app/environment/environment.py
"""
Main Environment Class - Orchestrates all components
FIXED: Reward function with STRONG NEGATIVE rewards for bad states
STEP 2A: Real-world data injection (news sentiment + WorldBank economics)
STEP 2A-FIX: Timeout-safe injection + last-known-good snapshot reuse
STEP 3A-FIX: Sentiment=0.0 fallback to last-known-good snapshot
"""
from typing import Dict, Any, Optional, Tuple
import asyncio
from datetime import datetime
import logging
import os
import numpy as np

from .state import EnvironmentState
from .transition import StateTransitionEngine
from ..game_theory.payoff import AdaptivePayoffMatrix
from ..game_theory.mixed_strategy import MixedStrategySolver
from ..game_theory.equilibrium import EquilibriumAnalyzer

logger = logging.getLogger(__name__)


# ============================================================
# STEP 2A-FIX: Real data injection config
# ============================================================
INJECT_EVERY_N_ROUNDS = int(os.getenv("REAL_DATA_INJECT_INTERVAL", "10"))
SENTIMENT_WEIGHT = float(os.getenv("SENTIMENT_INJECT_WEIGHT", "0.35"))
ECON_WEIGHT = float(os.getenv("ECON_INJECT_WEIGHT", "0.25"))

# Hard timeout for external fetch inside injection
INJECT_FETCH_TIMEOUT = float(os.getenv("REAL_DATA_FETCH_TIMEOUT", "8.0"))

DEFAULT_COUNTRY_ID = os.getenv("SIM_DEFAULT_COUNTRY", "bd")


class StrategicEnvironment:
    """
    Complete Strategic Environment with FIXED reward calculation
    + STEP 2A: Real-world data injection (timeout-safe)
    """

    def __init__(
        self,
        stochastic: bool = True,
        country_id: Optional[str] = None,
    ):
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

        # ---- STEP 2A: country + real-data state ----
        self.country_id = (country_id or DEFAULT_COUNTRY_ID).lower()
        self._real_data_cache: Dict[str, Any] = {
            "news": None,
            "econ": None,
            "last_news_round": -1,
            "last_econ_round": -1,
            "injection_log": [],
            # STEP 2A-FIX: last successful news snapshot (reused on timeout/zero)
            "_last_news_snapshot": None,
            "_last_nonzero_sentiment": 0.0,
        }

        logger.info(
            f"✅ Strategic Environment initialized "
            f"(country={self.country_id}, inject_every={INJECT_EVERY_N_ROUNDS}, "
            f"fetch_timeout={INJECT_FETCH_TIMEOUT}s)"
        )

    # ------------------------------------------------------------------
    # Reward helpers
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # STEP 2A-FIX + STEP 3A-FIX: Real-world data injection (timeout-safe)
    # ------------------------------------------------------------------
    async def _inject_real_data(self):
        """
        Pull real news sentiment + economic indicators, then nudge
        the environment state toward reality.

        STEP 2A-FIX:
        - All external calls wrapped in wait_for(timeout=INJECT_FETCH_TIMEOUT)
        - On timeout/failure, reuses last-known-good snapshot
        - Never blocks the simulation for more than ~8s

        STEP 3A-FIX:
        - If news returns sentiment == 0.0, reuse last non-zero sentiment
          (prevents permanent +0.00 stuck state in dashboard)
        """
        try:
            from ..sentiment.news_aggregator import news_aggregator
        except Exception as e:
            logger.debug(f"news_aggregator not available for injection: {e}")
            return

        # ---- Fetch news (timeout-safe) ----
        news = None
        try:
            news = await asyncio.wait_for(
                news_aggregator.fetch_country(
                    self.country_id, force_refresh=False
                ),
                timeout=INJECT_FETCH_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"[Real→Sim] news fetch timed out after "
                f"{INJECT_FETCH_TIMEOUT}s for {self.country_id}; "
                f"reusing last snapshot"
            )
            news = self._real_data_cache.get("_last_news_snapshot")
        except Exception as e:
            logger.warning(f"[Real→Sim] news fetch failed: {e}")
            news = self._real_data_cache.get("_last_news_snapshot")

        # ---- Extract sentiment with STEP 3A-FIX fallback ----
        raw_sentiment = 0.0
        if news:
            self._real_data_cache["_last_news_snapshot"] = news
            raw_sentiment = float(news.get("sentiment_score", 0.0) or 0.0)

            # STEP 3A-FIX: if new sentiment is exactly 0.0, reuse last non-zero
            if raw_sentiment == 0.0:
                last_nonzero = self._real_data_cache.get("_last_nonzero_sentiment", 0.0)
                if last_nonzero != 0.0:
                    logger.info(
                        f"[Real→Sim] sentiment=0.0 from news, reusing "
                        f"last non-zero sentiment={last_nonzero:+.3f}"
                    )
                    raw_sentiment = last_nonzero
                else:
                    logger.info(
                        "[Real→Sim] sentiment=0.0 and no prior non-zero — "
                        "using 0.0 (no injection)"
                    )
            else:
                # Store as last non-zero for future fallback
                self._real_data_cache["_last_nonzero_sentiment"] = raw_sentiment

            self._real_data_cache["news"] = {
                "sentiment": raw_sentiment,
                "article_count": int(news.get("article_count", 0) or 0),
                "fetched_at": news.get("fetched_at"),
            }
            self._real_data_cache["last_news_round"] = self.current_round

        # ---- Economic indicators ----
        econ = None
        if news:
            econ = news.get("economic_indicators") or {}

        if not econ:
            econ = self._real_data_cache.get("econ") or {}

        if not econ:
            try:
                from ..sentiment.worldbank_ingestor import WorldBankIngestor
                wb = WorldBankIngestor()
                try:
                    econ = await asyncio.wait_for(
                        wb.fetch_all_for_country(
                            self._iso2_for(self.country_id)
                        ),
                        timeout=INJECT_FETCH_TIMEOUT,
                    )
                finally:
                    await wb.close()
            except asyncio.TimeoutError:
                logger.warning(
                    f"[Real→Sim] WorldBank fetch timed out for "
                    f"{self.country_id}"
                )
                econ = None
            except Exception as e:
                logger.debug(f"[Real→Sim] WorldBank fallback failed: {e}")
                econ = None

        if econ:
            self._real_data_cache["econ"] = econ
            self._real_data_cache["last_econ_round"] = self.current_round

        # ---- Apply to environment ----
        sentiment_score = float(raw_sentiment)
        econ = self._real_data_cache.get("econ", {}) or {}

        # Sentiment → public_sentiment + strategic_tension
        # Apply whenever we have a non-zero sentiment (including fallback)
        if sentiment_score != 0.0:
            old_sent = self.state.public_sentiment
            self.state.public_sentiment = float(
                np.clip(
                    (1 - SENTIMENT_WEIGHT) * old_sent
                    + SENTIMENT_WEIGHT * sentiment_score,
                    -1.0, 1.0,
                )
            )
            tension_delta = -sentiment_score * 4.0
            self.state.strategic_tension = float(
                np.clip(self.state.strategic_tension + tension_delta, 0.0, 100.0)
            )

        # Economic indicators → economic_stability
        if econ:
            econ_adjust = 0.0
            inflation = float(econ.get("inflation", 0.0) or 0.0)
            unemployment = float(econ.get("unemployment", 0.0) or 0.0)
            gdp_growth = float(econ.get("gdp_growth", 0.0) or 0.0)

            if inflation > 8:
                econ_adjust -= (inflation - 8) * 0.5
            if inflation > 15:
                econ_adjust -= 2.0
            if unemployment > 5:
                econ_adjust -= (unemployment - 5) * 0.4
            if gdp_growth < 3:
                econ_adjust -= (3 - gdp_growth) * 0.3
            elif gdp_growth > 6:
                econ_adjust += (gdp_growth - 6) * 0.2

            econ_adjust = float(np.clip(econ_adjust, -3.0, 2.0))
            self.state.economic_stability = float(
                np.clip(
                    (1 - ECON_WEIGHT) * self.state.economic_stability
                    + ECON_WEIGHT * (self.state.economic_stability + econ_adjust),
                    0.0, 100.0,
                )
            )

        # ---- Recalculate derived metrics ----
        self.state._calculate_derived_metrics()

        # ---- Log for transparency ----
        log_entry = {
            "round": self.current_round,
            "country": self.country_id,
            "sentiment_in": round(sentiment_score, 3),
            "sentiment_source": "live" if raw_sentiment != 0.0 else "fallback",
            "inflation": round(float(econ.get("inflation", 0.0) or 0.0), 2),
            "unemployment": round(float(econ.get("unemployment", 0.0) or 0.0), 2),
            "gdp_growth": round(float(econ.get("gdp_growth", 0.0) or 0.0), 2),
            "public_sentiment_after": round(self.state.public_sentiment, 3),
            "strategic_tension_after": round(self.state.strategic_tension, 2),
            "economic_stability_after": round(self.state.economic_stability, 2),
        }
        self._real_data_cache["injection_log"].append(log_entry)
        if len(self._real_data_cache["injection_log"]) > 100:
            self._real_data_cache["injection_log"] = (
                self._real_data_cache["injection_log"][-100:]
            )

        logger.info(
            f"🌐 [Real→Sim] round={self.current_round} country={self.country_id} "
            f"sent={sentiment_score:+.3f} infl={log_entry['inflation']}% "
            f"unemp={log_entry['unemployment']}% gdp={log_entry['gdp_growth']}%"
        )

    @staticmethod
    def _iso2_for(country_id: str) -> str:
        """Country-id → ISO2 (minimal map for fallback WB calls)."""
        iso2_map = {
            "bd": "BD", "in": "IN", "pk": "PK", "lk": "LK", "np": "NP",
            "mm": "MM", "af": "AF", "bt": "BT",
            "id": "ID", "ph": "PH", "vn": "VN", "th": "TH", "my": "MY",
            "sg": "SG", "kh": "KH", "la": "LA",
            "cn": "CN", "jp": "JP", "kr": "KR", "tw": "TW", "hk": "HK",
            "mn": "MN",
            "ir": "IR", "il": "IL", "sa": "SA", "ae": "AE", "tr": "TR",
            "eg": "EG", "qa": "QA",
            "uk": "GB", "de": "DE", "fr": "FR", "ru": "RU",
            "us": "US", "ca": "CA", "mx": "MX", "br": "BR", "ar": "AR",
            "za": "ZA", "ng": "NG", "ke": "KE",
            "au": "AU", "nz": "NZ",
        }
        return iso2_map.get(country_id.lower(), "US")

    # ------------------------------------------------------------------
    # Core step
    # ------------------------------------------------------------------
    async def step(
        self,
        hegemon_strategy: str,
        sovereign_strategy: str,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Take one step in the environment.
        STEP 2A: every N rounds, inject real-world data first.
        """
        if self.current_round > 0 and self.current_round % INJECT_EVERY_N_ROUNDS == 0:
            await self._inject_real_data()

        current_state = self.state.get_global_state()

        payoff_result = self.payoff_matrix.get_adaptive_payoff(
            hegemon_strategy,
            sovereign_strategy,
            current_state,
        )

        new_state_dict = self.transition_engine.apply_transition(
            current_state,
            hegemon_strategy,
            sovereign_strategy,
            payoff_result.hegemon_payoff,
            payoff_result.sovereign_payoff,
        )

        self.state.update(new_state_dict, stochastic=self.transition_engine.stochastic)

        old_h = self.calculate_hegemon_utility(current_state)
        old_s = self.calculate_sovereign_utility(current_state)
        new_h = self.calculate_hegemon_utility(new_state_dict)
        new_s = self.calculate_sovereign_utility(new_state_dict)

        hegemon_reward = float(np.clip(0.75 * (new_h - old_h) + 0.25 * new_h, -1.0, 1.0))
        sovereign_reward = float(np.clip(0.75 * (new_s - old_s) + 0.25 * new_s, -1.0, 1.0))

        logger.info(f"💰 Rewards: H={hegemon_reward:.3f}, S={sovereign_reward:.3f}")

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
            'confidence': payoff_result.confidence_score,
            'real_data_injected': (
                self.current_round > 0 and
                self.current_round % INJECT_EVERY_N_ROUNDS == 0
            ),
        }

        self.events.append(event)
        self.history.append(self.state.to_dict())
        self.current_round += 1

        return new_state_dict, {
            'hegemon': hegemon_reward,
            'sovereign': sovereign_reward,
        }

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def get_state(self) -> Dict[str, float]:
        return self.state.to_dict()

    def get_global_state(self) -> Dict[str, float]:
        return self.state.get_global_state()

    def get_region_state(self, region_name: str) -> Optional[Dict[str, float]]:
        return self.state.get_region_state(region_name)

    def get_equilibrium_analysis(self) -> Dict[str, Any]:
        current_state = self.state.get_global_state()
        return self.equilibrium_analyzer.analyze_all(current_state)

    def get_mixed_strategy(self) -> Dict[str, Any]:
        current_state = self.state.get_global_state()
        result = self.mixed_solver.solve_fictitious_play(current_state)
        return {
            'hegemon_strategy': result.hegemon_strategy,
            'sovereign_strategy': result.sovereign_strategy,
            'expected_payoff_hegemon': result.expected_payoff_hegemon,
            'expected_payoff_sovereign': result.expected_payoff_sovereign,
            'convergence': result.convergence,
        }

    def reset(self, initial_state: Optional[Dict[str, float]] = None):
        if initial_state:
            self.state.update(initial_state, stochastic=False)
        else:
            self.state = EnvironmentState()

        self.history = []
        self.events = []
        self.current_round = 0
        self.is_running = False

        self._real_data_cache = {
            "news": None,
            "econ": None,
            "last_news_round": -1,
            "last_econ_round": -1,
            "injection_log": [],
            "_last_news_snapshot": None,
            "_last_nonzero_sentiment": 0.0,
        }

        logger.info("🔄 Environment reset")

    def get_performance_metrics(self) -> Dict[str, Any]:
        if not self.history:
            return {'error': 'No history available'}

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
                    'trend': values[-1] - values[0],
                }

        return {
            'total_rounds': len(self.history),
            'current_round': self.current_round,
            'trends': trends,
            'current_state': self.get_state(),
            'agent_performance': {
                'hegemon_utility': self.calculate_hegemon_utility(self.get_state()),
                'sovereign_utility': self.calculate_sovereign_utility(self.get_state()),
            },
            'real_data': {
                'country': self.country_id,
                'inject_every_n_rounds': INJECT_EVERY_N_ROUNDS,
                'fetch_timeout_seconds': INJECT_FETCH_TIMEOUT,
                'last_news_round': self._real_data_cache.get('last_news_round'),
                'last_econ_round': self._real_data_cache.get('last_econ_round'),
                'latest_news': self._real_data_cache.get('news'),
                'last_nonzero_sentiment': self._real_data_cache.get('_last_nonzero_sentiment', 0.0),
                'latest_econ': {
                    k: v for k, v in (self._real_data_cache.get('econ') or {}).items()
                    if k in ('gdp_growth', 'inflation', 'unemployment', 'gdp_usd')
                },
                'recent_injections': self._real_data_cache.get('injection_log', [])[-5:],
            },
        }