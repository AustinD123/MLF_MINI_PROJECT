"""
Real News Data Fetcher
Fetches financial news from NewsAPI and GDELT with fallback to mock data
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
import json
from src.config import (
    NEWSAPI_KEY, NEWS_API_URL, NEWS_API_TIMEOUT,
    MACRO_KEYWORDS, PRIORITY_SOURCES, NEWS_LOOKBACK_DAYS,
    MAX_RETRIES, RETRY_DELAY_SECONDS, DATA_DIR, CACHE_EXPIRY_HOURS
)
from src.logger import setup_logger
import time

logger = setup_logger("news_fetcher")


class NewsAPIFetcher:
    """Fetches financial news from NewsAPI"""
    
    def __init__(self, api_key: str = NEWSAPI_KEY):
        """
        Initialize NewsAPI fetcher
        
        Args:
            api_key: NewsAPI key from environment variable
        """
        self.api_key = api_key
        self.base_url = NEWS_API_URL
        self.timeout = NEWS_API_TIMEOUT
        self.session = requests.Session()
        
        if not api_key or api_key == "YOUR_NEWSAPI_KEY_HERE":
            logger.warning("NewsAPI key not configured. Set NEWSAPI_KEY environment variable")
            self.available = False
        else:
            self.available = True
    
    def fetch_news(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: int = NEWS_LOOKBACK_DAYS,
        sort_by: str = "publishedAt",
        language: str = "en"
    ) -> pd.DataFrame:
        """
        Fetch news articles from NewsAPI
        
        Args:
            query: Search query
            start_date: Start date for search (optional, overrides days_back)
            end_date: End date for search
            days_back: Days back from now if start_date not provided
            sort_by: Sort order (publishedAt, relevancy, popularity)
            language: Language code
            
        Returns:
            DataFrame with columns: [timestamp, headline, source, url]
        """
        if not self.available:
            logger.warning("NewsAPI not available")
            return pd.DataFrame()
        
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=days_back)
        if end_date is None:
            end_date = datetime.utcnow()
        
        from_date = start_date.isoformat()
        to_date = end_date.isoformat()
        
        params = {
            "q": query,
            "from": from_date,
            "to": to_date,
            "sortBy": sort_by,
            "language": language,
            "apiKey": self.api_key,
            "pageSize": 100
        }
        
        articles = []
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                logger.info(f"Fetching news: query='{query}', from={from_date}")
                response = self.session.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                if data.get("status") != "ok":
                    logger.error(f"API error: {data.get('message')}")
                    return pd.DataFrame()
                
                total_results = data.get("totalResults", 0)
                logger.info(f"Found {total_results} articles for query: {query}")
                
                for article in data.get("articles", []):
                    # Clean and extract fields
                    title = article.get("title", "").strip()
                    source_name = article.get("source", {}).get("name", "Unknown")
                    
                    # Skip very short headlines
                    if len(title) < 10:
                        continue
                    
                    articles.append({
                        "timestamp": pd.to_datetime(article.get("publishedAt")),
                        "headline": title,
                        "description": article.get("description", "").strip(),
                        "source": source_name,
                        "url": article.get("url", ""),
                        "author": article.get("author", ""),
                    })
                
                logger.info(f"Successfully parsed {len(articles)} articles")
                break
                
            except requests.exceptions.Timeout:
                retry_count += 1
                logger.warning(f"Timeout (attempt {retry_count}/{MAX_RETRIES})")
                if retry_count < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS)
            except requests.exceptions.RequestException as e:
                retry_count += 1
                logger.warning(f"Request failed (attempt {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS)
            except (KeyError, ValueError) as e:
                logger.error(f"Error parsing response: {e}")
                break
        
        if not articles:
            logger.warning(f"No articles retrieved for query: {query}")
            return pd.DataFrame()
        
        df = pd.DataFrame(articles)
        df = df.drop_duplicates(subset=["headline"]).reset_index(drop=True)
        df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
        
        logger.info(f"Returning {len(df)} unique articles")
        return df
    
    def fetch_macro_news(self, category: str = "general_macro") -> pd.DataFrame:
        """
        Fetch news for specific macro category
        
        Args:
            category: One of: inflation, fed_rates, recession, unemployment, general_macro
            
        Returns:
            DataFrame of articles
        """
        keywords = MACRO_KEYWORDS.get(category, MACRO_KEYWORDS["general_macro"])
        query = " OR ".join(keywords)
        
        logger.info(f"Fetching macro news for category: {category}")
        df = self.fetch_news(query)
        df["category"] = category
        
        return df
    
    def fetch_all_macro_categories(self) -> pd.DataFrame:
        """
        Fetch news for all macro categories
        
        Returns:
            Combined DataFrame with all categories
        """
        all_articles = []
        
        for category in MACRO_KEYWORDS.keys():
            logger.info(f"Fetching category: {category}")
            try:
                df = self.fetch_macro_news(category)
                if not df.empty:
                    all_articles.append(df)
                time.sleep(1)  # Rate limiting between requests
            except Exception as e:
                logger.error(f"Error fetching {category}: {e}")
        
        if not all_articles:
            logger.warning("No articles fetched for any category")
            return pd.DataFrame()
        
        combined_df = pd.concat(all_articles, ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=["headline"]).reset_index(drop=True)
        
        logger.info(f"Total unique articles across all categories: {len(combined_df)}")
        return combined_df


class GDELTFetcher:
    """Fetches news from GDELT API as fallback"""
    
    def __init__(self):
        """Initialize GDELT fetcher"""
        self.base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
        self.timeout = 30
        self.available = True
    
    def fetch_news(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: int = 7
    ) -> pd.DataFrame:
        """
        Fetch news from GDELT
        
        Args:
            query: Search query
            start_date: Start date
            end_date: End date
            days_back: Days back if start_date not provided
            
        Returns:
            DataFrame with columns: [timestamp, headline, source, url]
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=days_back)
        if end_date is None:
            end_date = datetime.utcnow()
        
        # GDELT uses YYYYMMDDHHMMSS format
        start_str = start_date.strftime("%Y%m%d%H%M%S")
        end_str = end_date.strftime("%Y%m%d%H%M%S")
        
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": 250,
            "sort": "date",
            "startdatetime": start_str,
            "enddatetime": end_str,
            "format": "json"
        }
        
        articles = []
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                logger.info(f"Fetching GDELT news: query='{query}'")
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                
                for article in data.get("articles", []):
                    title = article.get("title", "").strip()
                    
                    # Skip short headlines
                    if len(title) < 10:
                        continue
                    
                    articles.append({
                        "timestamp": pd.to_datetime(article.get("sedate"), format="%Y%m%d%H%M%S"),
                        "headline": title,
                        "source": article.get("source", "GDELT"),
                        "url": article.get("url", ""),
                        "description": "",
                    })
                
                logger.info(f"Retrieved {len(articles)} articles from GDELT")
                break
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                logger.warning(f"GDELT request failed (attempt {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS)
        
        if not articles:
            logger.warning("No articles retrieved from GDELT")
            return pd.DataFrame()
        
        df = pd.DataFrame(articles)
        df = df.drop_duplicates(subset=["headline"]).reset_index(drop=True)
        df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
        
        return df


class NewsDataManager:
    """Manages news fetching with caching, fallbacks, and data cleaning"""
    
    def __init__(self, use_cache: bool = True):
        """
        Initialize news manager
        
        Args:
            use_cache: Whether to use cached data
        """
        self.newsapi_fetcher = NewsAPIFetcher()
        self.gdelt_fetcher = GDELTFetcher()
        self.use_cache = use_cache
        self.cache_dir = os.path.join(DATA_DIR, "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info("NewsDataManager initialized")
    
    def _get_cache_path(self, query_hash: str) -> str:
        """Get cache file path for a query"""
        return os.path.join(self.cache_dir, f"news_{query_hash}.json")
    
    def _load_from_cache(self, query_hash: str) -> Optional[pd.DataFrame]:
        """Load news from cache if fresh"""
        cache_path = self._get_cache_path(query_hash)
        
        if not os.path.exists(cache_path):
            return None
        
        # Check cache freshness
        file_age_hours = (time.time() - os.path.getmtime(cache_path)) / 3600
        if file_age_hours > CACHE_EXPIRY_HOURS:
            logger.info(f"Cache expired for {query_hash}")
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            logger.info(f"Loaded {len(df)} articles from cache")
            return df
        except Exception as e:
            logger.warning(f"Error loading cache: {e}")
            return None
    
    def _save_to_cache(self, df: pd.DataFrame, query_hash: str):
        """Save news data to cache"""
        try:
            cache_path = self._get_cache_path(query_hash)
            df_copy = df.copy()
            df_copy["timestamp"] = df_copy["timestamp"].astype(str)
            with open(cache_path, 'w') as f:
                json.dump(df_copy.to_dict('records'), f)
            logger.info(f"Cached {len(df)} articles")
        except Exception as e:
            logger.warning(f"Error saving cache: {e}")
    
    def fetch_news(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: int = NEWS_LOOKBACK_DAYS,
        fallback_to_gdelt: bool = True,
        use_mock_on_failure: bool = True
    ) -> pd.DataFrame:
        """
        Fetch news with caching and fallbacks
        
        Args:
            query: Search query
            start_date: Start date
            end_date: End date
            days_back: Days back from now
            fallback_to_gdelt: Try GDELT if NewsAPI fails
            use_mock_on_failure: Generate mock data if all APIs fail
            
        Returns:
            DataFrame with news articles
        """
        # Check cache
        query_hash = str(hash(query + str(days_back)))
        
        if self.use_cache:
            cached_df = self._load_from_cache(query_hash)
            if cached_df is not None and not cached_df.empty:
                return cached_df
        
        # Try NewsAPI first
        if self.newsapi_fetcher.available:
            try:
                df = self.newsapi_fetcher.fetch_news(
                    query=query,
                    start_date=start_date,
                    end_date=end_date,
                    days_back=days_back
                )
                if not df.empty:
                    self._save_to_cache(df, query_hash)
                    return df
            except Exception as e:
                logger.warning(f"NewsAPI failed: {e}")
        
        # Try GDELT fallback
        if fallback_to_gdelt and self.gdelt_fetcher.available:
            try:
                logger.info("Falling back to GDELT API")
                df = self.gdelt_fetcher.fetch_news(
                    query=query,
                    start_date=start_date,
                    end_date=end_date,
                    days_back=days_back
                )
                if not df.empty:
                    self._save_to_cache(df, query_hash)
                    return df
            except Exception as e:
                logger.warning(f"GDELT failed: {e}")
        
        # Fall back to mock data
        if use_mock_on_failure:
            logger.warning("All APIs failed, using mock data")
            return self._generate_mock_news(query, days_back)
        
        return pd.DataFrame()
    
    def fetch_macro_news(
        self,
        category: str = "general_macro",
        fallback_to_gdelt: bool = True,
        use_mock_on_failure: bool = True
    ) -> pd.DataFrame:
        """
        Fetch macro news by category
        
        Args:
            category: Macro category
            fallback_to_gdelt: Try GDELT if NewsAPI fails
            use_mock_on_failure: Use mock if all fail
            
        Returns:
            DataFrame with articles
        """
        keywords = MACRO_KEYWORDS.get(category, MACRO_KEYWORDS["general_macro"])
        query = " OR ".join(keywords)
        
        df = self.fetch_news(
            query=query,
            fallback_to_gdelt=fallback_to_gdelt,
            use_mock_on_failure=use_mock_on_failure
        )
        
        if not df.empty:
            df["category"] = category
        
        return df
    
    def fetch_all_macro_news(
        self,
        fallback_to_gdelt: bool = True,
        use_mock_on_failure: bool = True
    ) -> pd.DataFrame:
        """
        Fetch news for all macro categories
        
        Returns:
            Combined DataFrame
        """
        all_articles = []
        
        for category in MACRO_KEYWORDS.keys():
            try:
                df = self.fetch_macro_news(
                    category=category,
                    fallback_to_gdelt=fallback_to_gdelt,
                    use_mock_on_failure=use_mock_on_failure
                )
                if not df.empty:
                    all_articles.append(df)
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Error fetching {category}: {e}")
        
        if not all_articles:
            logger.warning("No articles fetched for any category")
            return pd.DataFrame()
        
        combined_df = pd.concat(all_articles, ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=["headline"]).reset_index(drop=True)
        
        logger.info(f"Retrieved {len(combined_df)} unique articles across all categories")
        return combined_df
    
    @staticmethod
    def clean_news_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and preprocess news data
        
        Args:
            df: Raw news DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # Remove duplicates
        initial_count = len(df)
        df = df.drop_duplicates(subset=["headline"]).reset_index(drop=True)
        logger.info(f"Removed {initial_count - len(df)} duplicate headlines")
        
        # Remove extremely short headlines
        df = df[df["headline"].str.len() >= 10].reset_index(drop=True)
        
        # Normalize timestamps
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        
        # Sort by time
        df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
        
        # Remove rows with missing critical fields
        df = df.dropna(subset=["headline", "timestamp"]).reset_index(drop=True)
        
        logger.info(f"Cleaned data: {len(df)} articles remaining")
        return df
    
    @staticmethod
    def _generate_mock_news(query: str, days_back: int = 30) -> pd.DataFrame:
        """Generate mock news for fallback"""
        headlines = [
            "CPI inflation rises faster than expected",
            "Federal Reserve signals end to hike cycle",
            "Consumer prices surge on energy costs",
            "Fed Chair testifies to Congress",
            "Moderate inflation growth reported",
            "GDP growth accelerates in Q3",
            "Job creation exceeds expectations",
            "Economic outlook improves despite inflation",
            "Unemployment claims fall to 3-month lows",
            "Stock market rebounds on positive signals",
            "Central bank signals caution ahead",
            "Inflation moderates in key sectors",
            "Market volatility reflects economic concerns",
            "Strong retail sales boost growth outlook",
            "Wage growth accelerates inflation pressures",
            "Manufacturing activity shows resilience",
            "Consumer confidence reaches quarterly highs",
            "Trade tensions ease amid negotiations",
            "Services sector expansion accelerates",
            "Energy prices stabilize at new levels"
        ]
        
        now = datetime.utcnow()
        news_data = []
        
        for i, headline in enumerate(headlines):
            days_offset = (i % max(1, days_back))
            hours_offset = (i // max(1, days_back)) * 12
            
            news_data.append({
                "timestamp": now - timedelta(days=days_offset, hours=hours_offset),
                "headline": headline,
                "source": ["Bloomberg", "Reuters", "WSJ", "CNBC"][i % 4],
                "url": f"https://example.com/news-{i}",
                "description": f"Article about: {headline}",
            })
        
        df = pd.DataFrame(news_data)
        logger.info(f"Generated {len(df)} mock news articles")
        return df
