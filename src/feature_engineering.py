"""
Feature Engineering Module
Creates advanced features for predictive modeling
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from src.logger import setup_logger

logger = setup_logger("feature_engineering")


class FeatureEngineer:
    """Create machine learning features from sentiment and price data"""
    
    @staticmethod
    def compute_sentiment_features(
        sentiment_ts: pd.DataFrame,
        windows_hours: List[int] = [6, 12, 24]
    ) -> pd.DataFrame:
        """
        Compute advanced sentiment features
        
        Args:
            sentiment_ts: Time series with [timestamp, mean_sentiment, sentiment_label]
            windows_hours: List of rolling window sizes in hours
            
        Returns:
            DataFrame with new features
        """
        df = sentiment_ts.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        # Sentinel change (delta)
        df["sentiment_delta"] = df["mean_sentiment"].diff()
        df["sentiment_delta_abs"] = df["sentiment_delta"].abs()
        
        # Sentiment sign change (flip from positive to negative or vice versa)
        df["sentiment_flip"] = (df["sentiment_delta"] * df["sentiment_delta"].shift(1) < 0).astype(int)
        
        # Rolling statistics for each window
        for window in windows_hours:
            # Rolling mean
            df[f"rolling_mean_{window}h"] = (
                df["mean_sentiment"].rolling(window=window, min_periods=1).mean()
            )
            
            # Rolling std (volatility)
            df[f"rolling_std_{window}h"] = (
                df["mean_sentiment"].rolling(window=window, min_periods=1).std()
            )
            
            # Distance from rolling mean
            df[f"dist_from_mean_{window}h"] = (
                df["mean_sentiment"] - df[f"rolling_mean_{window}h"]
            )
        
        # Momentum: change vs previous window
        df["sentiment_momentum_6h"] = (
            df[f"rolling_mean_6h"] - df[f"rolling_mean_6h"].shift(6)
        )
        df["sentiment_momentum_12h"] = (
            df[f"rolling_mean_12h"] - df[f"rolling_mean_12h"].shift(12)
        )
        
        # Extreme sentiment detection (>2 std from rolling mean)
        df["sentiment_extreme_6h"] = (
            np.abs(df["dist_from_mean_6h"]) > 2 * df[f"rolling_std_6h"]
        ).astype(int)
        
        df["sentiment_extreme_24h"] = (
            np.abs(df["dist_from_mean_24h"]) > 2 * df[f"rolling_std_24h"]
        ).astype(int)
        
        logger.info(f"Computed sentiment features for {len(df)} time periods")
        
        return df
    
    @staticmethod
    def compute_market_features(
        price_ts: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compute market price features
        
        Args:
            price_ts: Time series with [timestamp, mid_price]
            
        Returns:
            DataFrame with market features
        """
        df = price_ts.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        # Price changes
        df["price_change"] = df["mid_price"].diff()
        df["price_change_pct"] = df["mid_price"].pct_change() * 100
        df["price_change_abs"] = df["price_change"].abs()
        
        # Direction: 1 for up, -1 for down, 0 for neutral (use fillna)
        df["price_direction"] = np.sign(df["price_change"]).fillna(0).astype('Int64')
        
        # Future price changes (targets for prediction)
        for hours_ahead in [6, 12, 24]:
            df[f"price_change_{hours_ahead}h"] = (
                df["mid_price"].shift(-hours_ahead) - df["mid_price"]
            )
            df[f"price_change_pct_{hours_ahead}h"] = (
                (df[f"price_change_{hours_ahead}h"] / df["mid_price"]) * 100
            )
            df[f"price_direction_{hours_ahead}h"] = (
                np.sign(df[f"price_change_{hours_ahead}h"]).fillna(0)
            ).astype('Int64')
        
        # Volatility
        df["returns"] = df["mid_price"].pct_change()
        df["volatility_6h"] = df["returns"].rolling(window=6, min_periods=1).std()
        df["volatility_24h"] = df["returns"].rolling(window=24, min_periods=1).std()
        
        # Rolling mean (trend)
        df["trend_sma_6h"] = df["mid_price"].rolling(window=6, min_periods=1).mean()
        df["trend_sma_24h"] = df["mid_price"].rolling(window=24, min_periods=1).mean()
        
        # Distance from trend
        df["dist_from_trend_6h"] = df["mid_price"] - df["trend_sma_6h"]
        df["dist_from_trend_24h"] = df["mid_price"] - df["trend_sma_24h"]
        
        logger.info(f"Computed market features for {len(df)} price points")
        
        return df
    
    @staticmethod
    def add_news_volume_features(
        sentiment_ts: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Add news volume features
        
        Args:
            sentiment_ts: Time series with article counts per window
            
        Returns:
            DataFrame with volume features
        """
        df = sentiment_ts.copy()
        
        if "article_count" not in df.columns:
            df["article_count"] = 1
        
        # Volume changes
        df["volume_change"] = df["article_count"].diff()
        df["volume_spike"] = (df["article_count"] > df["article_count"].rolling(24, min_periods=1).mean() * 1.5).astype(int)
        
        # Cumulative articles
        df["cumulative_volume"] = df["article_count"].cumsum()
        
        # Volume ratio
        df["volume_ratio_6h"] = (
            df["article_count"] / (df["article_count"].rolling(6, min_periods=1).mean() + 0.1)
        )
        
        logger.info("Added news volume features")
        
        return df
    
    @staticmethod
    def create_ml_dataset(
        sentiment_ts: pd.DataFrame,
        price_ts: pd.DataFrame,
        merge_on: str = "timestamp"
    ) -> pd.DataFrame:
        """
        Create final ML dataset by merging all features
        
        Args:
            sentiment_ts: Sentiment time series with features
            price_ts: Price time series with features
            merge_on: Column to merge on
            
        Returns:
            Complete feature matrix ready for modeling
        """
        # Ensure timestamps are datetime
        sentiment_ts["timestamp"] = pd.to_datetime(sentiment_ts["timestamp"])
        price_ts["timestamp"] = pd.to_datetime(price_ts["timestamp"])
        
        # Merge on nearest timestamp
        merged = pd.merge_asof(
            price_ts.sort_values("timestamp"),
            sentiment_ts.sort_values("timestamp")[
                ["timestamp", "mean_sentiment", "sentiment_delta", "rolling_mean_6h",
                 "rolling_mean_12h", "rolling_mean_24h", "rolling_std_24h", 
                 "article_count"]
            ],
            on="timestamp",
            direction="nearest",
            tolerance=pd.Timedelta("1H")
        )
        
        # Drop rows with NaN targets
        merged = merged.dropna(subset=["price_change_24h"])
        
        logger.info(f"Created ML dataset with {len(merged)} samples and {len(merged.columns)} features")
        
        return merged
    
    @staticmethod
    def get_feature_columns(
        dataset: pd.DataFrame,
        exclude_patterns: List[str] = None
    ) -> List[str]:
        """
        Get list of feature columns (exclude targets and metadata)
        
        Args:
            dataset: Full dataset
            exclude_patterns: Patterns to exclude (e.g., ['target_', 'timestamp'])
            
        Returns:
            List of feature column names
        """
        if exclude_patterns is None:
            exclude_patterns = [
                'timestamp', 'target', 'price_change_', 'price_direction_',
                'mid_price', 'returns', 'cumulative_'
            ]
        
        features = []
        for col in dataset.columns:
            # Skip if matches any exclude pattern
            skip = False
            for pattern in exclude_patterns:
                if pattern in col:
                    skip = True
                    break
            
            if not skip and col in dataset.columns:
                features.append(col)
        
        return features


def create_features_from_aligned_data(
    aligned_df: pd.DataFrame,
    sentiment_col: str = "mean_sentiment",
    price_col: str = "mid_price"
) -> pd.DataFrame:
    """
    Convenience function to create all features from aligned data
    
    Args:
        aligned_df: Aligned sentiment/price dataframe
        sentiment_col: Column name for sentiment
        price_col: Column name for price
        
    Returns:
        DataFrame with all computed features
    """
    engineer = FeatureEngineer()
    
    # Extract sentiment and price series
    sentiment_ts = aligned_df[["timestamp", sentiment_col]].copy()
    sentiment_ts.columns = ["timestamp", "mean_sentiment"]
    
    price_ts = aligned_df[["timestamp", price_col]].copy()
    price_ts.columns = ["timestamp", "mid_price"]
    
    # Compute features
    sentiment_features = engineer.compute_sentiment_features(sentiment_ts)
    market_features = engineer.compute_market_features(price_ts)
    
    # Merge back
    df = pd.merge_asof(
        market_features.sort_values("timestamp"),
        sentiment_features.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("1H")
    )
    
    logger.info(f"Created feature matrix with {len(df)} rows x {len(df.columns)} columns")
    
    return df
