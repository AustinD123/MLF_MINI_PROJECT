"""
Data Alignment and Merging Module
Aligns sentiment scores with market prices and handles missing values
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List
from src.logger import setup_logger

logger = setup_logger("data_alignment")


class DataAligner:
    """Aligns sentiment and market data time series"""
    
    @staticmethod
    def resample_sentiment_to_frequency(
        sentiment_df: pd.DataFrame,
        frequency: str = "1h",  # 1h, 1d, etc.
        agg_method: str = "mean"
    ) -> pd.DataFrame:
        """
        Resample sentiment scores to specified frequency
        
        Args:
            sentiment_df: DataFrame with sentiment scores and timestamps
            frequency: Frequency string (e.g., '1h', '1d')
            agg_method: Aggregation method ('mean', 'median', 'max', 'min', 'std')
            
        Returns:
            Resampled DataFrame
        """
        if sentiment_df.empty:
            return sentiment_df
        
        df = sentiment_df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Find the sentiment column
        sentiment_col = None
        for col in ["weighted_sentiment", "mean_sentiment", "sentiment_score", "sentiment"]:
            if col in df.columns:
                sentiment_col = col
                break
        
        if not sentiment_col:
            logger.warning("No sentiment column found, returning original data")
            return df
        
        # Set timestamp as index for resampling
        df_indexed = df.set_index("timestamp")
        
        # Build aggregation dict
        agg_dict = {sentiment_col: agg_method}
        if "sentiment_score" in df.columns and sentiment_col != "sentiment_score":
            agg_dict["sentiment_score"] = agg_method
        if "article_count" in df.columns:
            agg_dict["article_count"] = "sum"
        
        # Resample and aggregate
        resampled = df_indexed.resample(frequency).agg(agg_dict).reset_index()
        
        # Remove NaN values from resampling
        resampled = resampled.dropna(subset=[sentiment_col])
        
        logger.info(f"Resampled sentiment to {frequency}: {len(resampled)} periods")
        return resampled
    
    @staticmethod
    def resample_market_data_to_frequency(
        market_df: pd.DataFrame,
        frequency: str = "1h"
    ) -> pd.DataFrame:
        """
        Resample market prices to specified frequency
        
        Args:
            market_df: DataFrame with market prices
            frequency: Frequency string
            
        Returns:
            Resampled DataFrame
        """
        if market_df.empty:
            return market_df
        
        df = market_df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Ensure mid_price exists
        if "mid_price" not in df.columns:
            if "yes_price" in df.columns and "no_price" in df.columns:
                df["mid_price"] = (df["yes_price"] + df["no_price"]) / 2
            elif "bid_price" in df.columns and "ask_price" in df.columns:
                df["mid_price"] = (df["bid_price"] + df["ask_price"]) / 2
            else:
                logger.warning("Cannot compute mid_price, no price columns found")
                return pd.DataFrame()
        
        # Set timestamp as index
        df_indexed = df.set_index("timestamp")
        
        # Resample - only aggregate mid_price and optional volume
        agg_dict = {
            "mid_price": ["first", "last", "min", "max", "mean"],
        }
        if "volume" in df.columns:
            agg_dict["volume"] = "sum"
        
        resampled = df_indexed.resample(frequency).agg(agg_dict).reset_index()
        
        # Flatten column names
        if resampled.columns.nlevels > 1:
            resampled.columns = ["_".join(col).strip("_") if col[1] else col[0] for col in resampled.columns]
        
        # Rename for consistency
        resampled = resampled.rename(columns={
            "mid_price_first": "open_price",
            "mid_price_last": "close_price",
            "mid_price_min": "low_price",
            "mid_price_max": "high_price",
            "mid_price_mean": "avg_price"
        })
        
        # Use close price as mid_price reference
        if "close_price" in resampled.columns:
            resampled["mid_price"] = resampled["close_price"]
        
        # Remove rows with all NaNs in price columns
        price_cols = ["mid_price", "open_price", "close_price"]
        resampled = resampled.dropna(subset=[c for c in price_cols if c in resampled.columns], how="all")
        
        logger.info(f"Resampled market data to {frequency}: {len(resampled)} candles")
        return resampled
    
    @staticmethod
    def align_time_series(
        sentiment_df: pd.DataFrame,
        market_df: pd.DataFrame,
        sentiment_col: str = "weighted_sentiment",
        market_col: str = "mid_price",
        method: str = "inner",  # 'inner', 'outer', 'left', 'right'
        fill_method: str = "forward",  # 'forward', 'backward', 'linear'
    ) -> pd.DataFrame:
        """
        Align sentiment and market data on common timestamps
        
        Args:
            sentiment_df: Sentiment DataFrame with timestamp column
            market_df: Market DataFrame with timestamp column
            sentiment_col: Name of sentiment column to use
            market_col: Name of market price column
            method: Join method ('inner', 'outer', 'left', 'right')
            fill_method: Method to fill missing values
            
        Returns:
            Aligned DataFrame
        """
        if sentiment_df.empty or market_df.empty:
            logger.warning("Cannot align empty DataFrames")
            return pd.DataFrame()
        
        sent = sentiment_df.copy()
        mkt = market_df.copy()
        
        # Ensure timestamp columns and strip timezone for consistent merging
        sent["timestamp"] = pd.to_datetime(sent["timestamp"]).dt.tz_localize(None)
        mkt["timestamp"] = pd.to_datetime(mkt["timestamp"]).dt.tz_localize(None)
        
        # Sort by timestamp
        sent = sent.sort_values("timestamp").reset_index(drop=True)
        mkt = mkt.sort_values("timestamp").reset_index(drop=True)
        
        # Merge on timestamp
        merged = pd.merge(
            sent[["timestamp", sentiment_col]],
            mkt[["timestamp", market_col]],
            on="timestamp",
            how=method
        )
        
        if merged.empty:
            logger.warning("Aligned result is empty, trying outer join")
            merged = pd.merge(
                sent[["timestamp", sentiment_col]],
                mkt[["timestamp", market_col]],
                on="timestamp",
                how="outer"
            )
        
        # Handle missing values
        if fill_method == "forward":
            merged[sentiment_col] = merged[sentiment_col].ffill()
            merged[market_col] = merged[market_col].ffill()
        elif fill_method == "backward":
            merged[sentiment_col] = merged[sentiment_col].bfill()
            merged[market_col] = merged[market_col].bfill()
        elif fill_method == "linear":
            merged[sentiment_col] = merged[sentiment_col].interpolate(method="linear")
            merged[market_col] = merged[market_col].interpolate(method="linear")
        
        # Remove any remaining NaNs
        merged = merged.dropna()
        merged = merged.sort_values("timestamp").reset_index(drop=True)
        
        logger.info(f"Aligned datasets: {len(merged)} common timestamps")
        return merged
    
    @staticmethod
    def merge_sentiment_and_market(
        sentiment_df: pd.DataFrame,
        market_df: pd.DataFrame,
        frequency: str = "1d",
        sentiment_col: str = "weighted_sentiment",
        market_col: str = "mid_price",
        join_method: str = "inner"
    ) -> pd.DataFrame:
        """
        Comprehensive merge of sentiment and market data with resampling
        
        Args:
            sentiment_df: Raw sentiment data
            market_df: Raw market data
            frequency: Target frequency for resampling
            sentiment_col: Sentiment column name
            market_col: Market column name
            join_method: Join method
            
        Returns:
            Merged and aligned DataFrame
        """
        logger.info(f"Starting sentiment-market merge with frequency={frequency}")
        
        # Find actual sentiment column
        actual_sentiment_col = sentiment_col
        for col in [sentiment_col, "mean_sentiment", "weighted_sentiment", "sentiment_score"]:
            if col in sentiment_df.columns:
                actual_sentiment_col = col
                break
        
        # Find actual market column
        actual_market_col = market_col
        for col in [market_col, "mid_price", "close_price"]:
            if col in market_df.columns:
                actual_market_col = col
                break
        
        logger.info(f"Using sentiment column: {actual_sentiment_col}, market column: {actual_market_col}")
        
        # Resample both to same frequency
        sentiment_resampled = DataAligner.resample_sentiment_to_frequency(
            sentiment_df, frequency=frequency
        )
        market_resampled = DataAligner.resample_market_data_to_frequency(
            market_df, frequency=frequency
        )
        
        if sentiment_resampled.empty or market_resampled.empty:
            logger.error("Resampling produced empty dataframes")
            return pd.DataFrame()
        
        # Align time series
        aligned = DataAligner.align_time_series(
            sentiment_resampled,
            market_resampled,
            sentiment_col=actual_sentiment_col,
            market_col=actual_market_col,
            method=join_method
        )
        
        logger.info(f"Merge complete: {len(aligned)} records")
        return aligned
    
    @staticmethod
    def handle_missing_values(
        df: pd.DataFrame,
        columns: List[str],
        method: str = "forward",
        limit: int = 10
    ) -> pd.DataFrame:
        """
        Handle missing values in DataFrame
        
        Args:
            df: DataFrame with missing values
            columns: Columns to fill
            method: Fill method ('forward', 'backward', 'linear', 'mean', 'drop')
            limit: Maximum consecutive fills
            
        Returns:
            DataFrame with filled values
        """
        df = df.copy()
        
        if method == "forward":
            df[columns] = df[columns].fillna(method="ffill", limit=limit)
        elif method == "backward":
            df[columns] = df[columns].fillna(method="bfill", limit=limit)
        elif method == "linear":
            df[columns] = df[columns].interpolate(method="linear", limit=limit)
        elif method == "mean":
            for col in columns:
                if col in df.columns:
                    mean_val = df[col].mean()
                    df[col].fillna(mean_val, inplace=True)
        elif method == "drop":
            df = df.dropna(subset=columns)
        
        # Remove any rows that still have NaNs in critical columns
        remaining_cols = [c for c in columns if c in df.columns]
        df = df.dropna(subset=remaining_cols, how="any")
        
        logger.info(f"Filled missing values: {len(df)} records remaining")
        return df
    
    @staticmethod
    def create_aligned_dataset(
        sentiment_df: pd.DataFrame,
        market_df: pd.DataFrame,
        frequency: str = "1h",
        join_method: str = "inner"
    ) -> Dict[str, pd.DataFrame]:
        """
        Create a comprehensive aligned dataset for analysis
        
        Args:
            sentiment_df: Processed sentiment data
            market_df: Processed market data
            frequency: Resampling frequency
            join_method: Join method
            
        Returns:
            Dictionary containing aligned and derived data
        """
        logger.info("Creating aligned dataset...")
        
        # Main merge
        aligned = DataAligner.merge_sentiment_and_market(
            sentiment_df,
            market_df,
            frequency=frequency,
            join_method=join_method
        )
        
        if aligned.empty:
            logger.error("Alignment failed, returning empty result")
            return {"aligned": pd.DataFrame()}
        
        # Create derived metrics
        for col in ["weighted_sentiment", "mean_sentiment", "sentiment"]:
            if col in aligned.columns:
                aligned["sentiment_60d_ma"] = aligned[col].rolling(60, min_periods=1).mean()
                break
        
        if "mid_price" in aligned.columns:
            aligned["price_60d_ma"] = aligned["mid_price"].rolling(60, min_periods=1).mean()
            aligned["price_change_1h"] = aligned["mid_price"].diff()
            aligned["price_change_pct"] = aligned["mid_price"].pct_change() * 100
        
        # Compute correlation
        sentiment_col = None
        for col in ["weighted_sentiment", "mean_sentiment", "sentiment"]:
            if col in aligned.columns:
                sentiment_col = col
                break
        
        correlation = None
        if sentiment_col and "mid_price" in aligned.columns:
            try:
                correlation = aligned[[sentiment_col, "mid_price"]].corr().iloc[0, 1]
            except Exception as e:
                logger.warning(f"Could not compute correlation: {e}")
        
        if correlation:
            logger.info(f"Correlation between sentiment and price: {correlation:.3f}")
        else:
            logger.info("Could not compute sentiment-price correlation")
        
        # Normalize timestamps to remove timezone info for compatibility
        if "timestamp" in aligned.columns:
            aligned["timestamp"] = pd.to_datetime(aligned["timestamp"], utc=False)
        
        return {
            "aligned": aligned,
            "correlation": correlation,
            "summary": {
                "total_records": len(aligned),
                "date_range": f"{aligned['timestamp'].min()} to {aligned['timestamp'].max()}",
                "frequency": frequency,
            }
        }


class DataAlignmentPipeline:
    """High-level pipeline for data alignment"""
    
    def __init__(self):
        self.aligner = DataAligner()
        logger.info("DataAlignmentPipeline initialized")
    
    def align_sentiment_with_market(
        self,
        sentiment_df: pd.DataFrame,
        market_df: pd.DataFrame,
        target_frequency: str = "1d",
        join_method: str = "inner"
    ) -> pd.DataFrame:
        """
        Main entry point for alignment
        
        Args:
            sentiment_df: Sentiment analysis results
            market_df: Market price data
            target_frequency: Target resampling frequency
            join_method: Join method
            
        Returns:
            Aligned DataFrame ready for analysis
        """
        logger.info(f"Starting alignment pipeline (frequency={target_frequency})")
        
        # Log input data
        logger.info(f"Input: {len(sentiment_df)} sentiment records, {len(market_df)} market records")
        
        # Merge with resampling
        result = DataAligner.create_aligned_dataset(
            sentiment_df,
            market_df,
            frequency=target_frequency,
            join_method=join_method
        )
        
        aligned = result.get("aligned", pd.DataFrame())
        logger.info(f"Output: {len(aligned)} aligned records")
        
        return aligned
