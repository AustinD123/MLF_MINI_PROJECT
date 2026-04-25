"""
Utility functions for data handling and processing
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional
from src.config import DB_PATH
from src.logger import setup_logger

logger = setup_logger("db_utils")


class DatabaseManager:
    """SQLite database operations for caching."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # News table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE,
                    source TEXT,
                    published_at TIMESTAMP,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sentiment_polarity REAL,
                    sentiment_label TEXT,
                    sentiment_confidence REAL
                )
            """)
            
            # Market prices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_slug TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    mid_price REAL,
                    yes_price REAL,
                    no_price REAL,
                    volume REAL,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(market_slug, timestamp)
                )
            """)
            
            # Analysis results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_type TEXT,
                    market_slug TEXT,
                    correlation REAL,
                    pvalue REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            conn.commit()
            logger.info("Database initialized")
    
    def save_articles(self, df: pd.DataFrame) -> int:
        """Save news articles to database."""
        with sqlite3.connect(self.db_path) as conn:
            # Filter for columns that exist in our table
            cols_to_save = [col for col in ["title", "url", "source", "publishedAt"] 
                          if col in df.columns]
            
            df_save = df[cols_to_save].copy()
            df_save.columns = [col.lower().replace("publishedat", "published_at") 
                             for col in df_save.columns]
            
            # Add sentiment columns if they exist
            if "sentiment_polarity" in df.columns:
                df_save["sentiment_polarity"] = df["sentiment_polarity"]
                df_save["sentiment_label"] = df["sentiment_label"]
                df_save["sentiment_confidence"] = df["sentiment_confidence"]
            
            count = df_save.to_sql("news", conn, if_exists="append", index=False)
            logger.info(f"Saved {count} articles to database")
            return count
    
    def save_market_prices(self, df: pd.DataFrame, market_slug: str) -> int:
        """Save market prices to database."""
        with sqlite3.connect(self.db_path) as conn:
            df_save = df.copy()
            df_save["market_slug"] = market_slug
            
            count = df_save.to_sql("market_prices", conn, if_exists="append", index=False)
            logger.info(f"Saved {count} price records for {market_slug}")
            return count
    
    def load_articles(
        self,
        since: Optional[datetime] = None,
        limit: int = 10000
    ) -> pd.DataFrame:
        """Load articles from database."""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM news WHERE 1=1"
            if since:
                query += f" AND published_at >= '{since.isoformat()}'"
            query += f" ORDER BY published_at DESC LIMIT {limit}"
            
            df = pd.read_sql_query(query, conn)
            logger.info(f"Loaded {len(df)} articles from database")
            return df
    
    def load_market_prices(
        self,
        market_slug: str,
        since: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load market prices from database."""
        with sqlite3.connect(self.db_path) as conn:
            query = f"SELECT * FROM market_prices WHERE market_slug = '{market_slug}'"
            if since:
                query += f" AND timestamp >= '{since.isoformat()}'"
            query += " ORDER BY timestamp"
            
            df = pd.read_sql_query(query, conn)
            logger.info(f"Loaded {len(df)} price records for {market_slug}")
            return df


def safe_divide(numerator, denominator, default=0):
    """Safely divide with default for zero denominator."""
    return numerator / denominator if denominator != 0 else default


def normalize_series(series: pd.Series, method: str = "minmax") -> pd.Series:
    """
    Normalize a pandas Series.
    
    Args:
        series: Input Series
        method: 'minmax' for [0,1] or 'zscore' for standardization
    
    Returns:
        Normalized Series
    """
    if method == "minmax":
        return (series - series.min()) / (series.max() - series.min())
    elif method == "zscore":
        return (series - series.mean()) / series.std()
    else:
        raise ValueError(f"Unknown normalization method: {method}")


def resample_dataframe(
    df: pd.DataFrame,
    time_column: str = "timestamp",
    freq: str = "1H",
    agg_method: str = "last"
) -> pd.DataFrame:
    """Resample DataFrame to regular time intervals."""
    df_copy = df.copy()
    df_copy[time_column] = pd.to_datetime(df_copy[time_column])
    df_copy = df_copy.set_index(time_column)
    
    if agg_method == "last":
        resampled = df_copy.resample(freq).last()
    elif agg_method == "first":
        resampled = df_copy.resample(freq).first()
    elif agg_method == "mean":
        resampled = df_copy.resample(freq).mean()
    else:
        raise ValueError(f"Unknown aggregation method: {agg_method}")
    
    return resampled.reset_index()
