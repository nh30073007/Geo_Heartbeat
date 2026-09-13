"""
Advanced Data Ingestion Pipeline with:
- Multi-source support (Kaggle, Hugging Face, APIs)
- Automatic download
- Data validation
- Schema management
- Error handling
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import json
import logging
import requests
import zipfile
import io
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio
import aiohttp
from tqdm import tqdm
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class DataSource:
    """Data source configuration"""
    name: str
    url: str
    source_type: str  # 'kaggle', 'huggingface', 'csv', 'api'
    file_pattern: str
    schema: Dict[str, Any]
    required_columns: List[str]
    data_format: str = 'csv'
    size_mb: float = 0.0
    last_updated: Optional[datetime] = None

class DataIngestionPipeline:
    """
    Complete data ingestion with:
    1. Multi-source support
    2. Automatic download
    3. Validation
    4. Deduplication
    5. Versioning
    """
    
    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Define data sources
        self.sources = self._initialize_sources()
        
        # Cache management
        self.cache: Dict[str, pd.DataFrame] = {}
        self.cache_ttl = 3600  # 1 hour
        
        logger.info("📥 Data Ingestion Pipeline initialized")
    
    def _initialize_sources(self) -> Dict[str, DataSource]:
        """Initialize all data sources"""
        return {
            # 1. Geopolitical News Data
            'geopolitical_news': DataSource(
                name='Geopolitical News & Financial Markets',
                url='https://www.kaggle.com/datasets/kozasalih/geopolitical-news-and-financial-markets-numeric-data',
                source_type='kaggle',
                file_pattern='*.csv',
                schema={
                    'EventDate': 'datetime64[ns]',
                    'Region': 'object',
                    'CountryCode': 'object',
                    'EventRootCode': 'int64',
                    'DailySentimentScore': 'float64',
                    'NewsVolume': 'int64',
                    'MaxImpact': 'float64',
                    'BTC_Price': 'float64',
                    'VIX_Index': 'float64',
                    'Gold_Price': 'float64'
                },
                required_columns=['EventDate', 'Region', 'DailySentimentScore'],
                size_mb=69.4
            ),
            
            # 2. Financial Sentiment Data
            'financial_sentiment': DataSource(
                name='Multilingual Financial Sentiment',
                url='https://huggingface.co/datasets/Kenpache/multilingual-financial-sentiment',
                source_type='huggingface',
                file_pattern='*_labeled.csv',
                schema={
                    'sentence': 'object',
                    'label': 'object'
                },
                required_columns=['sentence', 'label'],
                size_mb=29.5
            ),
            
            # 3. Social Media Sentiment Data
            'social_sentiment': DataSource(
                name='Global Social Media Sentiment',
                url='https://www.kaggle.com/datasets/lanellenwogalanya/global-social-media-sentiment-and-engagement',
                source_type='kaggle',
                file_pattern='*.csv',
                schema={
                    'Text': 'object',
                    'Sentiment': 'object',
                    'Timestamp': 'datetime64[ns]',
                    'Platform': 'object',
                    'Country': 'object',
                    'Likes': 'int64',
                    'Retweets': 'int64'
                },
                required_columns=['Text', 'Sentiment', 'Timestamp'],
                size_mb=0.164
            )
        }
    
    async def ingest_all(self, force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Ingest all data sources
        """
        results = {}
        
        tasks = []
        for source_name, source in self.sources.items():
            tasks.append(self.ingest_source(source_name, force_refresh))
        
        # Run all tasks concurrently
        ingested_data = await asyncio.gather(*tasks, return_exceptions=True)
        
        for source_name, data in zip(self.sources.keys(), ingested_data):
            if isinstance(data, Exception):
                logger.error(f"Failed to ingest {source_name}: {data}")
                results[source_name] = pd.DataFrame()
            else:
                results[source_name] = data
        
        return results
    
    async def ingest_source(
        self,
        source_name: str,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Ingest a single data source
        """
        if source_name not in self.sources:
            raise ValueError(f"Source {source_name} not found")
        
        source = self.sources[source_name]
        
        # Check cache
        cache_key = f"{source_name}_{hashlib.md5(source.url.encode()).hexdigest()[:8]}"
        
        if not force_refresh and cache_key in self.cache:
            logger.info(f"📦 Using cached data for {source_name}")
            return self.cache[cache_key]
        
        # Check local file
        local_file = self.data_dir / source_name / f"{source_name}.parquet"
        if not force_refresh and local_file.exists():
            logger.info(f"📂 Loading local file for {source_name}")
            df = pd.read_parquet(local_file)
            self.cache[cache_key] = df
            return df
        
        # Download based on source type
        if source.source_type == 'kaggle':
            df = await self._download_kaggle(source)
        elif source.source_type == 'huggingface':
            df = await self._download_huggingface(source)
        else:
            df = await self._download_csv(source)
        
        # Validate data
        df = self._validate_dataframe(df, source)
        
        # Cache and save
        self.cache[cache_key] = df
        local_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(local_file)
        
        logger.info(f"✅ Ingested {source_name}: {len(df)} rows")
        
        return df
    
    async def _download_kaggle(self, source: DataSource) -> pd.DataFrame:
        """
        Download from Kaggle using Kaggle API
        """
        try:
            import kaggle
            
            # Extract dataset path
            dataset_path = source.url.split('/')[-1]
            
            # Download to temp directory
            temp_dir = self.data_dir / 'temp'
            temp_dir.mkdir(exist_ok=True)
            
            # Use kaggle API
            await asyncio.get_event_loop().run_in_executor(
                None,
                kaggle.api.dataset_download_files,
                dataset_path,
                path=str(temp_dir),
                unzip=True
            )
            
            # Find and load CSV file
            csv_files = list(temp_dir.glob("*.csv"))
            if not csv_files:
                raise FileNotFoundError("No CSV files found in download")
            
            df = pd.read_csv(csv_files[0])
            
            # Clean up
            import shutil
            shutil.rmtree(temp_dir)
            
            return df
            
        except ImportError:
            logger.warning("Kaggle API not installed, using fallback")
            return await self._download_csv(source)
    
    async def _download_huggingface(self, source: DataSource) -> pd.DataFrame:
        """
        Download from Hugging Face dataset
        """
        try:
            from datasets import load_dataset
            
            # Extract dataset name
            dataset_name = source.url.split('/')[-1]
            
            # Load dataset
            dataset = await asyncio.get_event_loop().run_in_executor(
                None,
                load_dataset,
                f"Kenpache/{dataset_name}",
                split='train'
            )
            
            # Convert to pandas
            df = dataset.to_pandas()
            
            return df
            
        except ImportError:
            logger.warning("Datasets library not installed, using fallback")
            return pd.DataFrame()
    
    async def _download_csv(self, source: DataSource) -> pd.DataFrame:
        """
        Download CSV from URL
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(source.url) as response:
                if response.status == 200:
                    content = await response.read()
                    df = pd.read_csv(io.BytesIO(content))
                    return df
                else:
                    raise Exception(f"Failed to download: {response.status}")
    
    def _validate_dataframe(self, df: pd.DataFrame, source: DataSource) -> pd.DataFrame:
        """
        Validate and clean dataframe
        """
        # Check required columns
        missing = set(source.required_columns) - set(df.columns)
        if missing:
            logger.warning(f"Missing columns: {missing}")
        
        # Convert types
        for col, dtype in source.schema.items():
            if col in df.columns:
                try:
                    if dtype == 'datetime64[ns]':
                        df[col] = pd.to_datetime(df[col])
                    else:
                        df[col] = df[col].astype(dtype)
                except Exception as e:
                    logger.warning(f"Could not convert {col} to {dtype}: {e}")
        
        # Drop duplicates
        df = df.drop_duplicates()
        
        # Handle missing values
        df = df.dropna(subset=source.required_columns)
        
        return df
    
    def get_source_info(self, source_name: str) -> Dict[str, Any]:
        """Get information about a data source"""
        if source_name not in self.sources:
            return {'error': 'Source not found'}
        
        source = self.sources[source_name]
        return {
            'name': source.name,
            'source_type': source.source_type,
            'size_mb': source.size_mb,
            'schema': source.schema,
            'required_columns': source.required_columns
        }
    
    def get_all_sources(self) -> List[str]:
        """Get all source names"""
        return list(self.sources.keys())