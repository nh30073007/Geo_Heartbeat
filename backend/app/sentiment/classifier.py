"""
Advanced Sentiment Classifier with:
1. Multi-model support
2. Ensemble voting
3. Confidence calibration
4. Fine-tuning support
5. Export/Import
"""
import torch
import torch.nn as nn
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    AutoConfig,
    TrainingArguments,
    Trainer,
    pipeline
)
from sentence_transformers import SentenceTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report
import joblib
import json
import logging
from pathlib import Path
from dataclasses import dataclass
import pandas as pd

from .models import SentimentLabel, SentimentResult, SentimentScore

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for sentiment model"""
    model_name: str
    max_length: int = 512
    batch_size: int = 32
    learning_rate: float = 2e-5
    epochs: int = 3
    warmup_steps: int = 500
    weight_decay: float = 0.01
    num_labels: int = 3
    use_pretrained: bool = True

class SentimentClassifier:
    """
    Advanced sentiment classifier with ensemble support
    """
    
    def __init__(self, model_dir: str = "models/sentiment"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.models: Dict[str, Any] = {}
        self.tokenizers: Dict[str, Any] = {}
        self.configs: Dict[str, ModelConfig] = {}
        
        # Label mapping
        self.label_map = {
            0: SentimentLabel.NEGATIVE,
            1: SentimentLabel.NEUTRAL,
            2: SentimentLabel.POSITIVE
        }
        
        # Label reverse mapping
        self.label_reverse = {v: k for k, v in self.label_map.items()}
        
        logger.info("🧠 Sentiment Classifier initialized")
    
    def load_pretrained(
        self,
        model_name: str = 'finbert',
        model_path: Optional[str] = None
    ):
        """
        Load a pre-trained model
        """
        try:
            if model_name == 'finbert':
                model_path = model_path or "ProsusAI/finbert"
            elif model_name == 'roberta':
                model_path = model_path or "cardiffnlp/twitter-roberta-base-sentiment-latest"
            elif model_name == 'distilbert':
                model_path = model_path or "distilbert-base-uncased-finetuned-sst-2-english"
            else:
                model_path = model_path or model_name
            
            # Load model and tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForSequenceClassification.from_pretrained(model_path)
            
            self.models[model_name] = model
            self.tokenizers[model_name] = tokenizer
            self.configs[model_name] = ModelConfig(model_name=model_path)
            
            logger.info(f"✅ Loaded model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load {model_name}: {e}")
    
    def train(
        self,
        texts: List[str],
        labels: List[int],
        model_name: str = 'distilbert',
        epochs: int = 3,
        batch_size: int = 32
    ) -> Dict[str, float]:
        """
        Fine-tune a model
        """
        try:
            # Prepare data
            train_texts, val_texts, train_labels, val_labels = train_test_split(
                texts, labels, test_size=0.2, random_state=42
            )
            
            # Load model
            if model_name not in self.models:
                self.load_pretrained(model_name)
            
            # Prepare training
            tokenizer = self.tokenizers[model_name]
            model = self.models[model_name]
            
            # Tokenize data
            train_encodings = tokenizer(
                train_texts,
                truncation=True,
                padding=True,
                max_length=512,
                return_tensors='pt'
            )
            
            val_encodings = tokenizer(
                val_texts,
                truncation=True,
                padding=True,
                max_length=512,
                return_tensors='pt'
            )
            
            # Create dataset
            train_dataset = torch.utils.data.TensorDataset(
                train_encodings['input_ids'],
                train_encodings['attention_mask'],
                torch.tensor(train_labels)
            )
            
            val_dataset = torch.utils.data.TensorDataset(
                val_encodings['input_ids'],
                val_encodings['attention_mask'],
                torch.tensor(val_labels)
            )
            
            # Training arguments
            training_args = TrainingArguments(
                output_dir=str(self.model_dir / model_name),
                num_train_epochs=epochs,
                per_device_train_batch_size=batch_size,
                per_device_eval_batch_size=batch_size,
                warmup_steps=500,
                weight_decay=0.01,
                logging_dir=str(self.model_dir / 'logs'),
                logging_steps=10,
                evaluation_strategy="epoch",
                save_strategy="epoch",
                load_best_model_at_end=True,
                metric_for_best_model="accuracy"
            )
            
            # Create trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=val_dataset,
                compute_metrics=self._compute_metrics
            )
            
            # Train
            trainer.train()
            
            # Evaluate
            eval_results = trainer.evaluate()
            
            # Save model
            model.save_pretrained(str(self.model_dir / model_name))
            tokenizer.save_pretrained(str(self.model_dir / model_name))
            
            logger.info(f"✅ Model {model_name} fine-tuned successfully")
            
            return eval_results
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {}
    
    def predict(
        self,
        texts: List[str],
        model_name: str = 'ensemble',
        return_probs: bool = True
    ) -> List[SentimentResult]:
        """
        Predict sentiment for texts
        """
        results = []
        
        if model_name == 'ensemble':
            # Ensemble prediction
            for text in texts:
                result = self._predict_ensemble(text, return_probs)
                results.append(result)
        else:
            # Single model prediction
            if model_name not in self.models:
                logger.warning(f"Model {model_name} not found, using ensemble")
                return self.predict(texts, 'ensemble', return_probs)
            
            model = self.models[model_name]
            tokenizer = self.tokenizers[model_name]
            
            # Tokenize
            encodings = tokenizer(
                texts,
                truncation=True,
                padding=True,
                max_length=512,
                return_tensors='pt'
            )
            
            # Predict
            with torch.no_grad():
                outputs = model(**encodings)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1).numpy()
            
            # Convert to results
            for i, text in enumerate(texts):
                prob = probs[i]
                pred_label = np.argmax(prob)
                confidence = np.max(prob)
                
                scores = SentimentScore(
                    positive=float(prob[2] if len(prob) > 2 else 0),
                    negative=float(prob[0] if len(prob) > 0 else 0),
                    neutral=float(prob[1] if len(prob) > 1 else 0)
                )
                
                result = SentimentResult(
                    text=text,
                    sentiment=self.label_map[pred_label],
                    scores=scores,
                    confidence=float(confidence),
                    model_name=model_name
                )
                
                results.append(result)
        
        return results
    
    def _predict_ensemble(
        self,
        text: str,
        return_probs: bool = True
    ) -> SentimentResult:
        """
        Ensemble prediction using all models
        """
        predictions = []
        confidences = []
        score_dicts = []
        
        for model_name, model in self.models.items():
            try:
                tokenizer = self.tokenizers[model_name]
                
                # Tokenize
                encodings = tokenizer(
                    text,
                    truncation=True,
                    padding=True,
                    max_length=512,
                    return_tensors='pt'
                )
                
                # Predict
                with torch.no_grad():
                    outputs = model(**encodings)
                    logits = outputs.logits
                    probs = torch.softmax(logits, dim=-1).numpy()[0]
                
                # Get prediction
                pred_idx = np.argmax(probs)
                confidence = np.max(probs)
                
                predictions.append(self.label_map[pred_idx])
                confidences.append(confidence)
                
                # Get scores
                scores = {
                    'positive': float(probs[2] if len(probs) > 2 else 0),
                    'negative': float(probs[0] if len(probs) > 0 else 0),
                    'neutral': float(probs[1] if len(probs) > 1 else 0)
                }
                score_dicts.append(scores)
                
            except Exception as e:
                logger.error(f"Model {model_name} failed: {e}")
                continue
        
        if not predictions:
            # Fallback
            return SentimentResult(
                text=text,
                sentiment=SentimentLabel.NEUTRAL,
                scores=SentimentScore(positive=0.33, negative=0.33, neutral=0.34),
                confidence=0.0,
                model_name='ensemble'
            )
        
        # Majority voting with weighted confidence
        from collections import Counter
        weighted_votes = {}
        
        for pred, conf, scores in zip(predictions, confidences, score_dicts):
            weighted_votes[pred] = weighted_votes.get(pred, 0) + conf
        
        final_sentiment = max(weighted_votes, key=weighted_votes.get)
        
        # Average scores
        avg_scores = {
            'positive': np.mean([s['positive'] for s in score_dicts]),
            'negative': np.mean([s['negative'] for s in score_dicts]),
            'neutral': np.mean([s['neutral'] for s in score_dicts])
        }
        
        # Confidence is average confidence
        avg_confidence = np.mean(confidences)
        
        # Create result
        result = SentimentResult(
            text=text,
            sentiment=final_sentiment,
            scores=SentimentScore(**avg_scores),
            confidence=float(avg_confidence),
            model_name='ensemble'
        )
        
        return result
    
    def _compute_metrics(self, eval_pred):
        """Compute metrics for evaluation"""
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        
        return {
            'accuracy': accuracy_score(labels, predictions),
            'f1': f1_score(labels, predictions, average='weighted')
        }
    
    def save_model(self, model_name: str):
        """Save model to disk"""
        if model_name in self.models:
            model = self.models[model_name]
            tokenizer = self.tokenizers[model_name]
            
            model_dir = self.model_dir / model_name
            model.save_pretrained(str(model_dir))
            tokenizer.save_pretrained(str(model_dir))
            
            logger.info(f"💾 Model {model_name} saved")
    
    def load_model(self, model_name: str):
        """Load model from disk"""
        model_dir = self.model_dir / model_name
        
        if model_dir.exists():
            model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
            tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
            
            self.models[model_name] = model
            self.tokenizers[model_name] = tokenizer
            
            logger.info(f"📂 Model {model_name} loaded")
            return True
        
        return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return list(self.models.keys())
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a model"""
        if model_name not in self.models:
            return {'error': 'Model not found'}
        
        model = self.models[model_name]
        config = model.config
        
        return {
            'name': model_name,
            'type': config.model_type,
            'num_labels': config.num_labels,
            'hidden_size': config.hidden_size,
            'num_attention_heads': config.num_attention_heads,
            'vocab_size': config.vocab_size,
            'max_position_embeddings': getattr(config, 'max_position_embeddings', None)
        }