"""Optional semantic/LLM reward shaping with a deterministic safe fallback."""
from __future__ import annotations
import os
from typing import Dict, Any
import aiohttp

class SemanticRewardShaper:
    def __init__(self):
        self.enabled = os.getenv("REWARD_SHAPING_ENABLED", "true").lower() in {"1","true","yes"}
        self.url = os.getenv("REWARD_LLM_URL", "").strip()
        self.weight = float(os.getenv("REWARD_SENTIMENT_WEIGHT", "0.15"))
        self.timeout = float(os.getenv("REWARD_LLM_TIMEOUT", "1.5"))

    async def shape(self, reward: float, state: Dict[str, Any]) -> float:
        if not self.enabled:
            return float(reward)
        sentiment = float(state.get("public_sentiment", 0.0) or 0.0)
        # Deterministic baseline: negative public sentiment lowers reward,
        # positive sentiment slightly improves it. This keeps realtime runs
        # independent of any network service.
        shaped = float(reward) + self.weight * sentiment

        # Optional LLM endpoint. Expected response: {"score": -1..1}.
        # Any network/format failure falls back to the deterministic score.
        if self.url:
            try:
                payload = {
                    "task": "score_public_sentiment_impact",
                    "state": {"public_sentiment": sentiment,
                              "strategic_tension": state.get("strategic_tension", 0)},
                }
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(self.url, json=payload) as resp:
                        if resp.status < 300:
                            data = await resp.json()
                            score = float(data.get("score", 0.0))
                            shaped = float(reward) + self.weight * max(-1.0, min(1.0, score))
            except Exception:
                pass
        return float(max(-1.0, min(1.0, shaped)))
