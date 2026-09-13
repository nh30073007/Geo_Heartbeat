"""
Sentiment Aggregator for Environment State
"""
from typing import Dict, Any, List, Optional
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SentimentAggregator:
    """
    Integrates sentiment with environment state
    """
    
    def __init__(self):
        self.sentiment_history: List[Dict[str, Any]] = []
        self.current_sentiment: Dict[str, Any] = {}
        
        logger.info("📊 Sentiment Aggregator initialized")
    
    def update_environment(
        self,
        sentiment_results: Dict[str, Any],
        current_state: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Update environment state with sentiment data
        """
        # Get global sentiment
        global_sentiment = sentiment_results.get('global', {})
        
        # Convert to state metrics
        state_updates = {}
        
        # 1. Public sentiment
        if 'score' in global_sentiment:
            state_updates['public_sentiment'] = global_sentiment['score']
        
        # 2. Stability - based on sentiment consistency
        if 'regions' in global_sentiment:
            regional_scores = [r['score'] for r in global_sentiment['regions']]
            if regional_scores:
                sentiment_variance = np.var(regional_scores)
                # Higher variance = less stability
                stability_impact = 1 - min(1, sentiment_variance)
                state_updates['stability'] = 50 + (stability_impact * 50)
        
        # 3. Trade stability - sentiment on economic topics
        if 'topics' in sentiment_results:
            economic_topics = sentiment_results['topics'].get('economic', {})
            if 'sentiment' in economic_topics:
                # Map sentiment to trade stability
                economic_sentiment = economic_topics['sentiment']
                if economic_sentiment == 'positive':
                    state_updates['trade_stability'] = min(100, current_state.get('trade_stability', 70) + 5)
                elif economic_sentiment == 'negative':
                    state_updates['trade_stability'] = max(0, current_state.get('trade_stability', 70) - 5)
        
        # 4. Strategic tension - based on negative sentiment intensity
        if 'negative_intensity' in global_sentiment:
            tension_impact = global_sentiment['negative_intensity'] * 20
            state_updates['strategic_tension'] = min(
                100,
                current_state.get('strategic_tension', 25) + tension_impact
            )
        
        # Store history
        self.sentiment_history.append({
            'timestamp': datetime.now().isoformat(),
            'sentiment': sentiment_results,
            'updates': state_updates
        })
        
        # Keep limited history
        if len(self.sentiment_history) > 1000:
            self.sentiment_history = self.sentiment_history[-1000:]
        
        self.current_sentiment = sentiment_results
        
        logger.info(f"📊 Sentiment updates: {state_updates}")
        
        return state_updates