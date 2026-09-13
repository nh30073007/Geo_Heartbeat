"""
Advanced Sentiment Analysis with:
1. Multi-model support
2. Pre-trained transformers
3. Ensemble predictions
4. Confidence scoring
5. Regional aggregation
"""
import torch
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    pipeline
)
from sentence_transformers import SentenceTransformer
import logging
from dataclasses import dataclass
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class SentimentResult:
    """Sentiment analysis result"""
    text: str
    sentiment: str  # positive, negative, neutral
    scores: Dict[str, float]
    confidence: float
    model_name: str
    timestamp: Optional[str] = None
    region: Optional[str] = None

class SentimentAnalyzer:
    """
    Advanced sentiment analysis with:
    1. Multiple pre-trained models
    2. Ensemble predictions
    3. Confidence scoring
    4. Regional aggregation
    """
    
    def __init__(self, models_dir: str = "models/sentiment"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize models
        self.models = {}
        self.tokenizers = {}
        
        # Load models
        self._load_models()
        
        logger.info("🧠 Sentiment Analyzer initialized")
    
    def _load_models(self):
        """Load pre-trained models"""
        try:
            # 1. FinBERT for financial sentiment
            self.models['finbert'] = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                device=-1  # CPU
            )
            logger.info("✅ FinBERT loaded")
            
            # 2. Roberta for general sentiment
            self.models['roberta'] = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                device=-1
            )
            logger.info("✅ Roberta loaded")
            
            # 3. DistilBERT for lightweight
            self.models['distilbert'] = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=-1
            )
            logger.info("✅ DistilBERT loaded")
            
            # 4. XLM-RoBERTa for multilingual
            self.models['xlm_roberta'] = pipeline(
                "sentiment-analysis",
                model="xlm-roberta-base",
                device=-1
            )
            logger.info("✅ XLM-RoBERTa loaded")
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            logger.warning("Using fallback models")
    
    def analyze_batch(
        self,
        texts: List[str],
        model_name: str = 'ensemble',
        region: Optional[str] = None
    ) -> List[SentimentResult]:
        """
        Analyze sentiment for batch of texts
        """
        results = []
        
        if model_name == 'ensemble':
            # Use ensemble of all models
            for text in texts:
                result = self._ensemble_analyze(text, region)
                results.append(result)
        else:
            # Use specific model
            if model_name not in self.models:
                logger.warning(f"Model {model_name} not found, using finbert")
                model_name = 'finbert'
            
            model = self.models[model_name]
            
            for text in texts:
                result = self._single_model_analyze(text, model, model_name, region)
                results.append(result)
        
        return results
    
    def _ensemble_analyze(self, text: str, region: Optional[str] = None) -> SentimentResult:
        """
        Ensemble prediction using all models
        """
        predictions = []
        scores = []
        
        for model_name, model in self.models.items():
            try:
                result = self._single_model_analyze(text, model, model_name, region)
                predictions.append(result.sentiment)
                scores.append({
                    'positive': result.scores.get('positive', 0),
                    'negative': result.scores.get('negative', 0),
                    'neutral': result.scores.get('neutral', 0)
                })
            except Exception as e:
                logger.error(f"Model {model_name} failed: {e}")
        
        # Majority voting
        from collections import Counter
        final_sentiment = Counter(predictions).most_common(1)[0][0]
        
        # Average scores
        avg_scores = {
            'positive': np.mean([s['positive'] for s in scores]),
            'negative': np.mean([s['negative'] for s in scores]),
            'neutral': np.mean([s['neutral'] for s in scores])
        }
        
        # Confidence (agreement among models)
        agreement = predictions.count(final_sentiment) / len(predictions)
        confidence = agreement
        
        return SentimentResult(
            text=text,
            sentiment=final_sentiment,
            scores=avg_scores,
            confidence=confidence,
            model_name='ensemble',
            region=region
        )
    
    def _single_model_analyze(
        self,
        text: str,
        model,
        model_name: str,
        region: Optional[str] = None
    ) -> SentimentResult:
        """
        Analyze with single model
        """
        result = model(text)[0]
        
        # Map to consistent format
        label = result['label'].lower()
        score = result['score']
        
        if 'positive' in label:
            sentiment = 'positive'
            scores = {'positive': score, 'negative': 0, 'neutral': 0}
        elif 'negative' in label:
            sentiment = 'negative'
            scores = {'positive': 0, 'negative': score, 'neutral': 0}
        else:
            sentiment = 'neutral'
            scores = {'positive': 0, 'negative': 0, 'neutral': score}
        
        return SentimentResult(
            text=text,
            sentiment=sentiment,
            scores=scores,
            confidence=score,
            model_name=model_name,
            region=region
        )
    
    def aggregate_regional(
        self,
        results: List[SentimentResult],
        region: str
    ) -> Dict[str, Any]:
        """
        Aggregate sentiment by region
        """
        region_results = [r for r in results if r.region == region]
        
        if not region_results:
            return {
                'region': region,
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'count': 0
            }
        
        # Calculate aggregate
        sentiment_counts = {}
        total_confidence = 0
        
        for r in region_results:
            sentiment_counts[r.sentiment] = sentiment_counts.get(r.sentiment, 0) + 1
            total_confidence += r.confidence
        
        # Weighted sentiment
        weighted_score = 0
        for r in region_results:
            if r.sentiment == 'positive':
                weighted_score += 1 * r.confidence
            elif r.sentiment == 'negative':
                weighted_score += -1 * r.confidence
        
        avg_score = weighted_score / len(region_results)
        avg_confidence = total_confidence / len(region_results)
        
        # Determine overall sentiment
        if avg_score > 0.2:
            overall = 'positive'
        elif avg_score < -0.2:
            overall = 'negative'
        else:
            overall = 'neutral'
        
        return {
            'region': region,
            'sentiment': overall,
            'score': avg_score,
            'confidence': avg_confidence,
            'count': len(region_results),
            'distribution': sentiment_counts
        }
    
    def aggregate_global(
        self,
        results: List[SentimentResult]
    ) -> Dict[str, Any]:
        """
        Aggregate sentiment globally
        """
        if not results:
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'count': 0
            }
        
        # Regional aggregation
        regions = set(r.region for r in results if r.region)
        
        regional_results = []
        for region in regions:
            regional = self.aggregate_regional(results, region)
            regional_results.append(regional)
        
        # Weighted by count
        total_count = sum(r['count'] for r in regional_results)
        weighted_score = 0
        for r in regional_results:
            weighted_score += r['score'] * (r['count'] / total_count)
        
        # Determine overall
        if weighted_score > 0.15:
            overall = 'positive'
        elif weighted_score < -0.15:
            overall = 'negative'
        else:
            overall = 'neutral'
        
        return {
            'sentiment': overall,
            'score': weighted_score,
            'confidence': np.mean([r['confidence'] for r in regional_results]),
            'total_count': len(results),
            'regions': regional_results
        }