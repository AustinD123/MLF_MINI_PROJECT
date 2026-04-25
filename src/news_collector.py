"""
News Collection Module
Fetches financial news headlines from NewsAPI
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from src.config import (
    NEWSAPI_KEY, NEWS_API_URL, NEWS_API_TIMEOUT,
    MACRO_KEYWORDS, PRIORITY_SOURCES, NEWS_LOOKBACK_DAYS,
    MAX_RETRIES, RETRY_DELAY_SECONDS
)
from src.logger import setup_logger
import time

logger = setup_logger("news_collector")


class NewsCollector:
    """Collects financial news from NewsAPI"""
    
    def __init__(self, api_key: str = NEWSAPI_KEY):
        self.api_key = api_key
        self.base_url = NEWS_API_URL
        self.timeout = NEWS_API_TIMEOUT
        
    def fetch_news(
        self,
        query: str,
        days_back: int = NEWS_LOOKBACK_DAYS,
        sort_by: str = "publishedAt",
        language: str = "en"
    ) -> pd.DataFrame:
        """
        Fetch news articles from NewsAPI.
        
        Args:
            query: Search query (e.g., "inflation economy")
            days_back: How many days back to search
            sort_by: Sort order (publishedAt, relevancy, popularity)
            language: Language code (e.g., "en")
            
        Returns:
            DataFrame with columns: [title, description, source, publishedAt, url, sentiment]
        """
        from_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
        
        params = {
            "q": query,
            "from": from_date,
            "sortBy": sort_by,
            "language": language,
            "apiKey": self.api_key,
            "pageSize": 100
        }
        
        articles = []
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                logger.info(f"Fetching news for query: {query}")
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                if data.get("status") != "ok":
                    logger.error(f"API error: {data.get('message')}")
                    return pd.DataFrame()
                
                for article in data.get("articles", []):
                    articles.append({
                        "title": article.get("title", ""),
                        "description": article.get("description", ""),
                        "source": article.get("source", {}).get("name", "Unknown"),
                        "publishedAt": pd.to_datetime(article.get("publishedAt")),
                        "url": article.get("url", ""),
                        "author": article.get("author", ""),
                        "image": article.get("urlToImage", ""),
                    })
                
                logger.info(f"Successfully fetched {len(articles)} articles")
                break
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                logger.warning(f"Request failed (attempt {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error("Max retries exceeded")
                    return pd.DataFrame()
        
        if not articles:
            logger.warning("No articles retrieved")
            return pd.DataFrame()
        
        df = pd.DataFrame(articles)
        df = df.sort_values("publishedAt", ascending=False)
        return df
    
    def fetch_macro_news(self, category: str = "general_macro") -> pd.DataFrame:
        """
        Fetch macro news by category.
        
        Args:
            category: Key from MACRO_KEYWORDS dictionary
            
        Returns:
            DataFrame of news articles
        """
        keywords = MACRO_KEYWORDS.get(category, MACRO_KEYWORDS["general_macro"])
        query = " OR ".join(keywords)
        
        return self.fetch_news(query)
    
    def fetch_all_categories(self) -> Dict[str, pd.DataFrame]:
        """
        Fetch news for all macro categories.
        
        Returns:
            Dictionary mapping category -> DataFrame
        """
        results = {}
        for category in MACRO_KEYWORDS.keys():
            logger.info(f"Fetching news for category: {category}")
            results[category] = self.fetch_macro_news(category)
            time.sleep(1)  # Rate limiting
        
        return results
    
    def filter_by_source_reliability(
        self,
        df: pd.DataFrame,
        priority_sources: List[str] = PRIORITY_SOURCES
    ) -> pd.DataFrame:
        """
        Filter articles to prioritize reliable financial sources.
        
        Args:
            df: Input DataFrame
            priority_sources: List of trusted source names
            
        Returns:
            Filtered DataFrame, sorted by source reliability
        """
        df_copy = df.copy()
        df_copy["source_priority"] = df_copy["source"].apply(
            lambda x: priority_sources.index(x.lower()) if x.lower() in priority_sources else 999
        )
        return df_copy.sort_values("source_priority")
    
    def deduplicate_articles(
        self,
        df: pd.DataFrame,
        similarity_threshold: float = 0.8
    ) -> pd.DataFrame:
        """
        Remove duplicate or near-duplicate articles.
        
        Args:
            df: Input DataFrame
            similarity_threshold: Cosine similarity threshold for duplicate detection
            
        Returns:
            Deduplicated DataFrame
        """
        from difflib import SequenceMatcher
        
        if len(df) == 0:
            return df
        
        df_copy = df.copy()
        to_drop = set()
        
        for i in range(len(df_copy)):
            if i in to_drop:
                continue
            
            for j in range(i + 1, len(df_copy)):
                if j in to_drop:
                    continue
                
                # Compare titles
                similarity = SequenceMatcher(
                    None,
                    df_copy.iloc[i]["title"],
                    df_copy.iloc[j]["title"]
                ).ratio()
                
                if similarity > similarity_threshold:
                    to_drop.add(j)
        
        df_copy = df_copy.drop(index=[df_copy.index[i] for i in to_drop])
        logger.info(f"Removed {len(to_drop)} duplicate articles")
        return df_copy.reset_index(drop=True)
