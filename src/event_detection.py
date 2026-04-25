"""
Event Detection Module
Detects sentiment spikes and news volume anomalies
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from scipy import signal

from src.logger import setup_logger

logger = setup_logger("event_detection")


class EventDetector:
    """Detect market-moving news events"""
    
    @staticmethod
    def detect_sentiment_spikes(
        sentiment_ts: pd.DataFrame,
        threshold_std: float = 2.0,
        sentiment_col: str = "mean_sentiment",
        timestamp_col: str = "timestamp"
    ) -> pd.DataFrame:
        """
        Detect significant sentiment movements
        
        Args:
            sentiment_ts: Time series with sentiment
            threshold_std: Number of standard deviations for spike
            sentiment_col: Column name for sentiment
            timestamp_col: Column name for timestamp
            
        Returns:
            DataFrame marking spike events
        """
        df = sentiment_ts.copy()
        df["timestamp"] = pd.to_datetime(df[timestamp_col])
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        # Compute rolling statistics
        rolling_mean = df[sentiment_col].rolling(window=24, min_periods=1).mean()
        rolling_std = df[sentiment_col].rolling(window=24, min_periods=1).std()
        
        # Distance from rolling mean
        distance = np.abs(df[sentiment_col] - rolling_mean)
        threshold = threshold_std * (rolling_std + 1e-8)
        
        # Detect spikes
        df["is_sentiment_spike"] = (distance > threshold).astype('Int64')
        df["spike_magnitude"] = (distance / (rolling_std + 1e-8))
        df["spike_direction"] = np.sign(df[sentiment_col] - rolling_mean).fillna(0).astype('Int64')
        
        n_spikes = df["is_sentiment_spike"].sum()
        logger.info(f"Detected {n_spikes} sentiment spikes (>{threshold_std} sigma)")
        
        return df
    
    @staticmethod
    def detect_volume_spikes(
        volume_ts: pd.DataFrame,
        threshold_multiplier: float = 1.5,
        volume_col: str = "article_count",
        timestamp_col: str = "timestamp"
    ) -> pd.DataFrame:
        """
        Detect unusual news volume
        
        Args:
            volume_ts: Time series with article counts
            threshold_multiplier: Spike if > mean * multiplier
            volume_col: Column name for volume
            timestamp_col: Column name for timestamp
            
        Returns:
            DataFrame marking volume spikes
        """
        df = volume_ts.copy()
        df["timestamp"] = pd.to_datetime(df[timestamp_col])
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        if volume_col not in df.columns:
            df[volume_col] = 1
        
        # Compute rolling mean
        rolling_mean = df[volume_col].rolling(window=24, min_periods=1).mean()
        threshold = rolling_mean * threshold_multiplier
        
        # Detect spikes
        df["is_volume_spike"] = (df[volume_col] > threshold).astype('Int64')
        df["volume_ratio"] = df[volume_col] / (rolling_mean + 0.1)
        
        n_spikes = df["is_volume_spike"].sum()
        logger.info(f"Detected {n_spikes} volume spikes (>{threshold_multiplier}x)")
        
        return df
    
    @staticmethod
    def combine_detections(
        sentiment_spikes: pd.DataFrame,
        volume_spikes: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Combine sentiment and volume spike detections
        
        Args:
            sentiment_spikes: DataFrame with sentiment spike flags
            volume_spikes: DataFrame with volume spike flags
            
        Returns:
            Combined dataframe with event types
        """
        df = sentiment_spikes.copy()
        # Strip timezone to ensure consistent dtype
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None)
        
        # Merge volume data
        volume_spikes = volume_spikes.copy()
        volume_spikes["timestamp"] = pd.to_datetime(volume_spikes["timestamp"], utc=True).dt.tz_localize(None)
        df = pd.merge_asof(
            df.sort_values("timestamp"),
            volume_spikes[["timestamp", "is_volume_spike", "volume_ratio"]].sort_values("timestamp"),
            on="timestamp",
            direction="nearest",
            tolerance=pd.Timedelta("1H")
        )
        
        # Event classification
        df["event_type"] = "normal"
        df.loc[
            (df["is_sentiment_spike"] == 1) & (df["is_volume_spike"] == 0),
            "event_type"
        ] = "sentiment_spike"
        df.loc[
            (df["is_sentiment_spike"] == 0) & (df["is_volume_spike"] == 1),
            "event_type"
        ] = "volume_spike"
        df.loc[
            (df["is_sentiment_spike"] == 1) & (df["is_volume_spike"] == 1),
            "event_type"
        ] = "sentiment_volume_spike"
        
        # Event flag
        df["is_event"] = (df["event_type"] != "normal").astype('Int64')
        
        logger.info(f"Combined detections: {df['is_event'].sum()} total events")
        
        return df
    
    @staticmethod
    def compute_event_market_response(
        events_df: pd.DataFrame,
        price_ts: pd.DataFrame,
        response_windows: List[int] = [6, 12, 24]
    ) -> pd.DataFrame:
        """
        Compute market price response to detected events
        
        Args:
            events_df: DataFrame with event markers
            price_ts: Price time series
            response_windows: Hours after event to measure response
            
        Returns:
            Events dataframe with market response metrics
        """
        df = events_df.copy()
        
        # Get prices at event times
        price_ts = price_ts.copy()
        price_ts["timestamp"] = pd.to_datetime(price_ts["timestamp"], utc=False)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False)
        
        # Merge prices
        df = pd.merge_asof(
            df.sort_values("timestamp"),
            price_ts[["timestamp", "mid_price"]].sort_values("timestamp"),
            on="timestamp",
            direction="nearest",
            tolerance=pd.Timedelta("1H")
        )
        
        # Compute price response for each window
        for window in response_windows:
            future_prices = []
            for idx, row in df.iterrows():
                event_time = row["timestamp"]
                future_mask = (
                    (price_ts["timestamp"] > event_time) & 
                    (price_ts["timestamp"] <= event_time + pd.Timedelta(hours=window))
                )
                future_data = price_ts[future_mask]
                
                if len(future_data) > 0:
                    future_price = future_data["mid_price"].iloc[-1]
                    price_change = future_price - row["mid_price"]
                    price_change_pct = (price_change / row["mid_price"]) * 100 if row["mid_price"] > 0 else 0
                else:
                    price_change = np.nan
                    price_change_pct = np.nan
                
                future_prices.append((price_change, price_change_pct))
            
            # Unpack results
            df[f"price_response_{window}h"] = [x[0] for x in future_prices]
            df[f"price_response_pct_{window}h"] = [x[1] for x in future_prices]
        
        logger.info(f"Computed market responses for {len(df)} events")
        
        return df


def detect_events(
    sentiment_ts: pd.DataFrame,
    volume_ts: pd.DataFrame,
    price_ts: pd.DataFrame,
    sentiment_threshold: float = 2.0,
    volume_threshold: float = 1.5
) -> Dict:
    """
    Comprehensive event detection
    
    Args:
        sentiment_ts: Sentiment time series
        volume_ts: Volume time series
        price_ts: Price time series
        sentiment_threshold: Std threshold for sentiment spikes
        volume_threshold: Multiplier for volume spikes
        
    Returns:
        Dictionary with event detection results
    """
    detector = EventDetector()
    
    # Detect spikes
    sentiment_spikes = detector.detect_sentiment_spikes(
        sentiment_ts, threshold_std=sentiment_threshold
    )
    volume_spikes = detector.detect_volume_spikes(
        volume_ts, threshold_multiplier=volume_threshold
    )
    
    # Combine detections
    events_df = detector.combine_detections(sentiment_spikes, volume_spikes)
    
    # Compute market response
    events_with_response = detector.compute_event_market_response(
        events_df, price_ts, response_windows=[6, 12, 24]
    )
    
    # Filter to just events
    events_only = events_with_response[events_with_response["is_event"] == 1].copy()
    
    result = {
        "all_timestamps": events_with_response,
        "events_only": events_only,
        "event_count": len(events_only),
        "event_types": events_only["event_type"].value_counts().to_dict() if len(events_only) > 0 else {}
    }
    
    logger.info(
        f"Event detection complete: {result['event_count']} events detected"
    )
    
    return result
