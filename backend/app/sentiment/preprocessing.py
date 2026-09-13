"""
Advanced Text Preprocessing Pipeline with:
- Language detection
- Text cleaning
- Tokenization
- Stop word removal
- Lemmatization
- Spelling correction
- Emoji handling
"""
import re
import unicodedata
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
import langdetect
from langdetect import detect, DetectorFactory
from textblob import TextBlob
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import emoji
import contractions
import string

# Download NLTK data (first time)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')
    nltk.download('omw-1.4')

logger = logging.getLogger(__name__)

@dataclass
class PreprocessConfig:
    """Configuration for preprocessing"""
    remove_emojis: bool = True
    remove_urls: bool = True
    remove_mentions: bool = True
    remove_hashtags: bool = True
    remove_numbers: bool = False
    remove_punctuation: bool = True
    remove_stopwords: bool = True
    lowercase: bool = True
    lemmatize: bool = True
    correct_spelling: bool = False
    min_word_length: int = 2
    max_word_length: int = 50
    max_text_length: int = 10000

class TextPreprocessor:
    """
    Advanced text preprocessing with:
    1. Language detection
    2. Text cleaning
    3. Tokenization
    4. Feature extraction
    5. Batch processing
    """
    
    def __init__(self, config: Optional[PreprocessConfig] = None):
        self.config = config or PreprocessConfig()
        
        # Initialize components
        self.lemmatizer = WordNetLemmatizer()
        
        # Load stopwords
        try:
            self.stopwords = set(stopwords.words('english'))
            logger.info("✅ Stopwords loaded")
        except:
            self.stopwords = set()
            logger.warning("⚠️ Could not load stopwords")
        
        # Set language detection seed
        DetectorFactory.seed = 0
        
        logger.info("🔧 Text Preprocessor initialized")
    
    def preprocess_batch(
        self,
        texts: List[str],
        detect_language: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Preprocess batch of texts
        """
        results = []
        
        for text in texts:
            result = self.preprocess_text(text, detect_language)
            results.append(result)
        
        return results
    
    def preprocess_text(
        self,
        text: str,
        detect_language: bool = True
    ) -> Dict[str, Any]:
        """
        Preprocess single text with full pipeline
        """
        if not text or not text.strip():
            return {
                'original': text,
                'clean': '',
                'tokens': [],
                'language': None,
                'is_valid': False
            }
        
        # Store original
        original = text
        
        # 1. Language detection
        language = None
        if detect_language:
            try:
                language = detect(text)
            except:
                language = 'en'  # Default to English
        
        # 2. Basic cleaning
        clean_text = self._clean_text(text)
        
        # 3. Tokenization
        tokens = self._tokenize(clean_text)
        
        # 4. Stop word removal
        tokens = self._remove_stopwords(tokens)
        
        # 5. Lemmatization
        tokens = self._lemmatize(tokens)
        
        # 6. Filter tokens
        tokens = self._filter_tokens(tokens)
        
        # 7. Reconstruct cleaned text
        clean_text_reconstructed = ' '.join(tokens)
        
        # 8. Extract features
        features = self._extract_features(tokens, original)
        
        return {
            'original': original,
            'clean': clean_text_reconstructed,
            'tokens': tokens,
            'language': language,
            'is_valid': len(tokens) > 0,
            'features': features,
            'original_text': original[:500]  # For reference
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean text"""
        # Lowercase
        if self.config.lowercase:
            text = text.lower()
        
        # Fix contractions
        text = contractions.fix(text)
        
        # Remove URLs
        if self.config.remove_urls:
            text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        
        # Remove mentions
        if self.config.remove_mentions:
            text = re.sub(r'@\w+', '', text)
        
        # Remove hashtags
        if self.config.remove_hashtags:
            text = re.sub(r'#\w+', '', text)
        else:
            # Keep hashtag text
            text = re.sub(r'#', '', text)
        
        # Remove emojis
        if self.config.remove_emojis:
            text = emoji.replace_emoji(text, replace='')
        
        # Remove numbers
        if self.config.remove_numbers:
            text = re.sub(r'\d+', '', text)
        
        # Remove punctuation
        if self.config.remove_punctuation:
            text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text"""
        try:
            tokens = word_tokenize(text)
            return tokens
        except:
            # Fallback tokenization
            return text.split()
    
    def _remove_stopwords(self, tokens: List[str]) -> List[str]:
        """Remove stopwords"""
        if not self.config.remove_stopwords:
            return tokens
        
        return [t for t in tokens if t not in self.stopwords]
    
    def _lemmatize(self, tokens: List[str]) -> List[str]:
        """Lemmatize tokens"""
        if not self.config.lemmatize:
            return tokens
        
        return [self.lemmatizer.lemmatize(t) for t in tokens]
    
    def _filter_tokens(self, tokens: List[str]) -> List[str]:
        """Filter tokens by length"""
        filtered = []
        
        for token in tokens:
            token_len = len(token)
            if self.config.min_word_length <= token_len <= self.config.max_word_length:
                filtered.append(token)
        
        return filtered
    
    def _extract_features(self, tokens: List[str], original: str) -> Dict[str, Any]:
        """Extract features from tokens"""
        features = {
            'token_count': len(tokens),
            'char_count': len(original),
            'word_count': len(original.split()),
            'avg_word_length': 0,
            'unique_tokens': 0,
            'vocabulary_richness': 0
        }
        
        if tokens:
            features['avg_word_length'] = sum(len(t) for t in tokens) / len(tokens)
            features['unique_tokens'] = len(set(tokens))
            features['vocabulary_richness'] = features['unique_tokens'] / len(tokens)
        
        return features
    
    def detect_language(self, text: str) -> Optional[str]:
        """Detect language of text"""
        try:
            return detect(text)
        except:
            return None
    
    def correct_spelling(self, text: str) -> str:
        """Correct spelling using TextBlob"""
        if not self.config.correct_spelling:
            return text
        
        try:
            blob = TextBlob(text)
            return str(blob.correct())
        except:
            return text
    
    def remove_emojis(self, text: str) -> str:
        """Remove emojis from text"""
        return emoji.replace_emoji(text, replace='')
    
    def clean_dataframe(self, df: pd.DataFrame, text_column: str) -> pd.DataFrame:
        """
        Clean text column in dataframe
        """
        if text_column not in df.columns:
            return df
        
        df_clean = df.copy()
        
        # Apply preprocessing
        df_clean['clean_text'] = df_clean[text_column].apply(
            lambda x: self._clean_text(str(x))
        )
        
        # Tokenize
        df_clean['tokens'] = df_clean['clean_text'].apply(
            lambda x: self._tokenize(x)
        )
        
        # Remove stopwords
        df_clean['tokens'] = df_clean['tokens'].apply(
            lambda x: self._remove_stopwords(x)
        )
        
        # Lemmatize
        df_clean['tokens'] = df_clean['tokens'].apply(
            lambda x: self._lemmatize(x)
        )
        
        # Join tokens
        df_clean['processed_text'] = df_clean['tokens'].apply(
            lambda x: ' '.join(x)
        )
        
        return df_clean