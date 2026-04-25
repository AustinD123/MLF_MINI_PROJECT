"""
Finnhub News Data Fetcher
Fetches financial news from Finnhub API with caching
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
import json
import time
from src.config import DATA_DIR, MAX_RETRIES, RETRY_DELAY_SECONDS, CACHE_EXPIRY_HOURS
from src.logger import setup_logger

logger = setup_logger("finnhub_fetcher")


class FinnhubFetcher:
    """Fetches financial news from Finnhub API"""
    
    def __init__(self, api_key: str):
        """
        Initialize Finnhub fetcher
        
        Args:
            api_key: Finnhub API key
        """
        self.api_key = api_key
        self.base_url = "https://finnhub.io/api/v1"
        self.timeout = 30
        self.session = requests.Session()
        
        if not api_key:
            logger.warning("Finnhub API key not provided")
            self.available = False
        else:
            self.available = True
    
    def fetch_news(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_sentiment: float = None
    ) -> pd.DataFrame:
        """
        Fetch news from Finnhub
        
        Args:
            query: Search query
            start_date: Start date (Finnhub returns last 30 days by default)
            end_date: End date
            min_sentiment: Filter by minimum sentiment
            
        Returns:
            DataFrame with columns: [timestamp, headline, source, url, sentiment]
        """
        if not self.available:
            logger.warning("Finnhub not available")
            return pd.DataFrame()
        
        try:
            params = {
                "q": query,
                "token": self.api_key,
            }
            
            response = self.session.get(
                f"{self.base_url}/news",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Finnhub returns either a list or dict with "result" key
            if isinstance(data, list):
                articles = data
            else:
                articles = data.get("data", data.get("result", []))
            
            if not articles:
                logger.warning(f"No articles found for query: {query}")
                return pd.DataFrame()
            
            logger.info(f"Found {len(articles)} articles for query: {query}")
            
            # Parse articles
            records = []
            for article in articles:
                try:
                    # Handle different response formats
                    if isinstance(article, dict):
                        timestamp_val = article.get("datetime") or article.get("publishedAt") or article.get("date")
                        if isinstance(timestamp_val, int):
                            timestamp = datetime.fromtimestamp(timestamp_val)
                        else:
                            timestamp = datetime.fromisoformat(str(timestamp_val).replace('Z', '+00:00')) if timestamp_val else datetime.utcnow()
                        
                        headline = article.get("headline") or article.get("title") or ""
                        
                        # Skip if outside date range
                        if start_date and timestamp < start_date:
                            continue
                        if end_date and timestamp > end_date:
                            continue
                        
                        records.append({
                            "timestamp": timestamp,
                            "headline": headline,
                            "source": article.get("source", "Finnhub"),
                            "url": article.get("url", ""),
                            "sentiment": float(article.get("sentiment", 0.0)) if article.get("sentiment") else 0.0,
                        })
                except Exception as e:
                    logger.warning(f"Error parsing article: {e}")
                    continue
            
            if records:
                df = pd.DataFrame(records)
                logger.info(f"Successfully parsed {len(df)} articles")
                return df
            else:
                return pd.DataFrame()
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Finnhub request failed: {e}")
            return pd.DataFrame()
    
    def fetch_company_news(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Fetch news for specific company
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with news articles
        """
        if not self.available:
            logger.warning("Finnhub not available")
            return pd.DataFrame()
        
        try:
            if start_date is None:
                start_date = datetime.utcnow() - timedelta(days=30)
            if end_date is None:
                end_date = datetime.utcnow()
            
            from_date = start_date.strftime("%Y-%m-%d")
            to_date = end_date.strftime("%Y-%m-%d")
            
            params = {
                "symbol": symbol,
                "from": from_date,
                "to": to_date,
                "token": self.api_key,
            }
            
            response = self.session.get(
                f"{self.base_url}/company-news",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            articles = response.json()
            
            if not articles:
                logger.warning(f"No articles found for symbol: {symbol}")
                return pd.DataFrame()
            
            logger.info(f"Found {len(articles)} articles for symbol: {symbol}")
            
            records = []
            for article in articles:
                try:
                    timestamp = datetime.utcfromtimestamp(article.get("datetime", 0))
                    records.append({
                        "timestamp": timestamp,
                        "headline": article.get("headline", ""),
                        "source": article.get("source", "Finnhub"),
                        "url": article.get("url", ""),
                        "symbol": symbol,
                    })
                except Exception as e:
                    logger.warning(f"Error parsing article: {e}")
                    continue
            
            if records:
                df = pd.DataFrame(records)
                logger.info(f"Successfully parsed {len(df)} articles for {symbol}")
                return df
            else:
                return pd.DataFrame()
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Finnhub company news request failed: {e}")
            return pd.DataFrame()


class FinnhubDataManager:
    """High-level interface for Finnhub data with caching"""
    
    def __init__(self, api_key: str):
        """Initialize Finnhub manager"""
        self.fetcher = FinnhubFetcher(api_key)
        self.cache_dir = os.path.join(DATA_DIR, "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_path(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """Get cache file path for query and date range"""
        range_key = ""
        if start_date is not None:
            range_key += start_date.strftime("%Y%m%d")
        range_key += "_"
        if end_date is not None:
            range_key += end_date.strftime("%Y%m%d")

        query_hash = str(hash(f"{query}|{range_key}"))
        return os.path.join(self.cache_dir, f"finnhub_{query_hash}.json")
    
    def _load_cache(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """Load cached data if available and not expired"""
        cache_path = self._get_cache_path(query, start_date, end_date)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            file_age_hours = (datetime.now() - datetime.fromtimestamp(
                os.path.getmtime(cache_path)
            )).total_seconds() / 3600
            
            if file_age_hours > CACHE_EXPIRY_HOURS:
                logger.info(f"Cache expired for query: {query}")
                return None
            
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            df = pd.read_json(data)
            logger.info(f"Loaded {len(df)} articles from cache for query: {query}")
            return df
        
        except Exception as e:
            logger.warning(f"Error loading cache: {e}")
            return None
    
    def _save_cache(
        self,
        query: str,
        df: pd.DataFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ):
        """Save data to cache"""
        cache_path = self._get_cache_path(query, start_date, end_date)
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(df.to_json(), f)
            logger.info(f"Cached {len(df)} articles for query: {query}")
        except Exception as e:
            logger.warning(f"Error saving cache: {e}")
    
    def fetch_news(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """Fetch news with caching"""
        # Try cache first
        if use_cache:
            cached = self._load_cache(query, start_date, end_date)
            if cached is not None:
                return cached
        
        # Fetch from API
        df = self.fetcher.fetch_news(query, start_date, end_date)
        
        # Cache results
        if not df.empty and use_cache:
            self._save_cache(query, df, start_date, end_date)
        
        return df
    
    def fetch_macro_news(
        self,
        category: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Fetch news for macro categories
        
        Args:
            category: 'inflation', 'fed', 'economy', 'employment', etc.
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with news articles
        """
        queries = {
            "inflation": "inflation OR CPI OR consumer price",
            "fed": "fed OR federal reserve OR interest rate OR FOMC",
            "economy": "economic OR economy OR recession OR GDP",
            "employment": "unemployment OR jobs OR employment",
            "trade": "trade OR tariff OR export OR commerce",
        }
        query = queries.get(category, category)
        return self.fetch_news(query, start_date, end_date)
    
    def fetch_all_macro_news(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Fetch news across all political categories"""
        all_news = []
        
        for category in ["election", "trump", "biden", "congress", "policy", "geopolitical"]:
            try:
                df = self.fetch_macro_news(category, start_date, end_date)
                if not df.empty:
                    all_news.append(df)
            except Exception as e:
                logger.warning(f"Error fetching {category} news: {e}")
        
        if all_news:
            combined = pd.concat(all_news, ignore_index=True)
            # Remove duplicates
            combined = combined.drop_duplicates(subset=["headline"])
            logger.info(f"Retrieved {len(combined)} unique articles across all political categories")
            return combined
        else:
            return pd.DataFrame()

