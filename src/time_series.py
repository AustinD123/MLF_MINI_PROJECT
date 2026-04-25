"""
Time Series Analysis Module
Analyzes correlation between sentiment and market movements
"""
import pandas as pd
import numpy as np
from scipy import stats
from typing import Tuple, Dict, List, Optional
from datetime import timedelta
from src.config import (
    ROLLING_SENTIMENT_WINDOW_HOURS,
    ROLLING_CORRELATION_WINDOW_DAYS,
    MAX_LAG_HOURS,
    LAG_STEP_HOURS,
    CORRELATION_MIN_THRESHOLD,
    MIN_PRICE_CHANGE_FOR_EVENT
)
from src.logger import setup_logger

logger = setup_logger("time_series")


class TimeSeriesAnalyzer:
    """Analyzes correlation between sentiment and market movements"""
    
    @staticmethod
    def align_timeseries(
        sentiment_df: pd.DataFrame,
        market_df: pd.DataFrame,
        sentiment_col: str = "mean_sentiment",
        market_col: str = "mid_price"
    ) -> pd.DataFrame:
        """
        Align sentiment and market data on common timestamps.
        
        Args:
            sentiment_df: Aggregated sentiment DataFrame with 'timestamp' column
            market_df: Market prices DataFrame with 'timestamp' column
            sentiment_col: Column name for sentiment values
            market_col: Column name for market prices
            
        Returns:
            Aligned DataFrame with both sentiment and market columns
        """
        # Sort both datasets
        sentiment_df = sentiment_df.sort_values("timestamp").reset_index(drop=True)
        market_df = market_df.sort_values("timestamp").reset_index(drop=True)
        
        # Merge on nearest timestamp (tolerance 1 hour)
        merged = pd.merge_asof(
            sentiment_df[["timestamp", sentiment_col]],
            market_df[["timestamp", market_col]],
            on="timestamp",
            tolerance=pd.Timedelta("1H"),
            direction="nearest"
        )
        
        # Drop rows with NaN values
        merged = merged.dropna()
        
        if len(merged) == 0:
            logger.warning("No aligned data points found between sentiment and market")
        else:
            logger.info(f"Aligned {len(merged)} data points")
        
        return merged
    
    @staticmethod
    def compute_rolling_correlation(
        aligned_df: pd.DataFrame,
        sentiment_col: str = "mean_sentiment",
        market_col: str = "mid_price",
        window_days: int = ROLLING_CORRELATION_WINDOW_DAYS
    ) -> pd.DataFrame:
        """
        Compute rolling correlation between sentiment and market prices.
        
        Args:
            aligned_df: Aligned sentiment and market DataFrame
            sentiment_col: Sentiment column name
            market_col: Market column name
            window_days: Rolling window in days
            
        Returns:
            DataFrame with rolling correlation metrics
        """
        if len(aligned_df) < window_days:
            logger.warning(f"Not enough data for {window_days}-day rolling window")
            return pd.DataFrame()
        
        aligned_df = aligned_df.sort_values("timestamp").reset_index(drop=True)
        
        # Calculate rolling correlation
        window_size = int(24 * window_days)  # Assuming hourly data
        
        rolling_corr = []
        
        for i in range(window_size, len(aligned_df)):
            window_data = aligned_df.iloc[i - window_size:i]
            
            if len(window_data) < 2:
                continue
            
            corr, pvalue = stats.pearsonr(
                window_data[sentiment_col],
                window_data[market_col]
            )
            
            rolling_corr.append({
                "timestamp": aligned_df.iloc[i]["timestamp"],
                "correlation": corr,
                "pvalue": pvalue,
                "significant": pvalue < 0.05
            })
        
        result_df = pd.DataFrame(rolling_corr)
        logger.info(f"Computed rolling correlation with {len(result_df)} windows")
        
        return result_df
    
    @staticmethod
    def lag_analysis(
        aligned_df: pd.DataFrame,
        sentiment_col: str = "mean_sentiment",
        market_col: str = "mid_price",
        max_lag_hours: int = MAX_LAG_HOURS,
        lag_step_hours: int = LAG_STEP_HOURS
    ) -> pd.DataFrame:
        """
        Analyze lead/lag relationship between sentiment and market.
        
        Args:
            aligned_df: Aligned sentiment and market DataFrame
            sentiment_col: Sentiment column name
            market_col: Market column name
            max_lag_hours: Maximum lag to test (in hours, positive = sentiment leads)
            lag_step_hours: Step size for lag (in hours)
            
        Returns:
            DataFrame with correlation for each lag value
        """
        aligned_df = aligned_df.sort_values("timestamp").reset_index(drop=True)
        
        # Assuming hourly data
        lags = range(-max_lag_hours, max_lag_hours + 1, lag_step_hours)
        lag_results = []
        
        for lag in lags:
            if lag == 0:
                # Contemporaneous correlation
                corr, pvalue = stats.pearsonr(
                    aligned_df[sentiment_col],
                    aligned_df[market_col]
                )
            elif lag > 0:
                # Sentiment leads price movement
                if lag < len(aligned_df):
                    corr, pvalue = stats.pearsonr(
                        aligned_df[sentiment_col].iloc[:-lag],
                        aligned_df[market_col].iloc[lag:]
                    )
                else:
                    corr, pvalue = np.nan, 1.0
            else:
                # Price movement leads sentiment
                lag_abs = abs(lag)
                if lag_abs < len(aligned_df):
                    corr, pvalue = stats.pearsonr(
                        aligned_df[sentiment_col].iloc[lag_abs:],
                        aligned_df[market_col].iloc[:-lag_abs]
                    )
                else:
                    corr, pvalue = np.nan, 1.0
            
            lag_results.append({
                "lag_hours": lag,
                "correlation": corr,
                "pvalue": pvalue,
                "significant": pvalue < 0.05 if not np.isnan(pvalue) else False
            })
        
        result_df = pd.DataFrame(lag_results).dropna()
        
        if len(result_df) > 0:
            max_corr_row = result_df.loc[result_df["correlation"].abs().idxmax()]
            logger.info(
                f"Maximum correlation: {max_corr_row['correlation']:.3f} at lag {max_corr_row['lag_hours']} hours"
            )
        
        return result_df
    
    @staticmethod
    def detect_sentiment_spikes(
        sentiment_df: pd.DataFrame,
        sentiment_col: str = "mean_sentiment",
        threshold_std: float = 1.5
    ) -> pd.DataFrame:
        """
        Detect sudden sentiment spikes.
        
        Args:
            sentiment_df: Aggregated sentiment DataFrame
            sentiment_col: Sentiment column name
            threshold_std: Number of standard deviations for spike threshold
            
        Returns:
            DataFrame of detected spikes
        """
        sentiment_df = sentiment_df.sort_values("timestamp").reset_index(drop=True)
        
        mean_sentiment = sentiment_df[sentiment_col].mean()
        std_sentiment = sentiment_df[sentiment_col].std()
        
        threshold_upper = mean_sentiment + threshold_std * std_sentiment
        threshold_lower = mean_sentiment - threshold_std * std_sentiment
        
        spikes = sentiment_df[
            (sentiment_df[sentiment_col] > threshold_upper) |
            (sentiment_df[sentiment_col] < threshold_lower)
        ].copy()
        
        spikes["spike_magnitude"] = spikes[sentiment_col].apply(
            lambda x: (x - mean_sentiment) / std_sentiment if std_sentiment > 0 else 0
        )
        
        logger.info(f"Detected {len(spikes)} sentiment spikes")
        
        return spikes
    
    @staticmethod
    def detect_event_pairs(
        sentiment_spikes: pd.DataFrame,
        price_jumps: pd.DataFrame,
        time_window_hours: float = 6.0
    ) -> pd.DataFrame:
        """
        Match sentiment spikes with market price jumps.
        
        Args:
            sentiment_spikes: DataFrame of sentiment spike events
            price_jumps: DataFrame of price jump events
            time_window_hours: Maximum time between spike and jump to consider related
            
        Returns:
            DataFrame of matched events
        """
        matches = []
        
        for _, spike in sentiment_spikes.iterrows():
            spike_time = spike["timestamp"]
            
            # Find price jumps within the time window
            nearby_jumps = price_jumps[
                (price_jumps["timestamp"] >= spike_time) &
                (price_jumps["timestamp"] <= spike_time + timedelta(hours=time_window_hours))
            ]
            
            for _, jump in nearby_jumps.iterrows():
                time_diff = (jump["timestamp"] - spike_time).total_seconds() / 3600
                
                matches.append({
                    "sentiment_spike_time": spike_time,
                    "price_jump_time": jump["timestamp"],
                    "time_diff_hours": time_diff,
                    "sentiment_value": spike["mean_sentiment"],
                    "price_change_pct": jump.get("pct_change", 0),
                    "price_change": jump.get("price_change", 0),
                })
        
        result_df = pd.DataFrame(matches)
        logger.info(f"Identified {len(result_df)} potential sentiment-price pairs")
        
        return result_df
    
    @staticmethod
    def compute_granger_causality(
        aligned_df: pd.DataFrame,
        sentiment_col: str = "mean_sentiment",
        market_col: str = "mid_price",
        max_lag: int = 5
    ) -> Dict:
        """
        Test for Granger causality between sentiment and price.
        
        Args:
            aligned_df: Aligned sentiment and market DataFrame
            sentiment_col: Sentiment column name
            market_col: Market column name
            max_lag: Maximum lag to test
            
        Returns:
            Dictionary with Granger causality test results
        """
        try:
            from statsmodels.tsa.stattools import grangercausalitytests
            
            # Prepare data
            data = aligned_df[[sentiment_col, market_col]].values
            
            # Run Granger causality test (sentiment -> price)
            gc_test = grangercausalitytests(data, max_lag, verbose=False)
            
            # Extract results for all lags
            results = {
                "sentiment_causes_price": [],
                "price_causes_sentiment": []
            }
            
            for lag in range(1, max_lag + 1):
                # Test 1: Sentiment -> Price
                p_val_1 = gc_test[lag][0][0]["ssr_ftest"][1]
                results["sentiment_causes_price"].append({
                    "lag": lag,
                    "pvalue": p_val_1,
                    "significant": p_val_1 < 0.05
                })
                
                # Test 2: Price -> Sentiment (alternate direction)
                data_reversed = data[:, [1, 0]]
                gc_test_rev = grangercausalitytests(data_reversed, lag, verbose=False)
                p_val_2 = gc_test_rev[lag][0][0]["ssr_ftest"][1]
                results["price_causes_sentiment"].append({
                    "lag": lag,
                    "pvalue": p_val_2,
                    "significant": p_val_2 < 0.05
                })
            
            logger.info("Granger causality test completed")
            
            return results
        
        except ImportError:
            logger.warning("Granger causality requires statsmodels: pip install statsmodels")
            return {}
    
    @staticmethod
    def compute_signal_strength(
        aligned_df: pd.DataFrame,
        sentiment_col: str = "mean_sentiment",
        market_col: str = "mid_price"
    ) -> Dict:
        """
        Compute overall signal strength metrics.
        
        Args:
            aligned_df: Aligned sentiment and market DataFrame
            sentiment_col: Sentiment column name
            market_col: Market column name
            
        Returns:
            Dictionary with signal strength metrics
        """
        if len(aligned_df) < 2:
            return {"error": "Insufficient data"}
        
        # Overall correlation
        corr, pvalue = stats.pearsonr(aligned_df[sentiment_col], aligned_df[market_col])
        
        # Calculate R-squared
        r_squared = corr ** 2
        
        # Spearman correlation (rank-based, robust to outliers)
        spearman_corr, spearman_p = stats.spearmanr(aligned_df[sentiment_col], aligned_df[market_col])
        
        # Price change
        market_returns = aligned_df[market_col].pct_change().dropna()
        
        # Sentiment change
        sentiment_changes = aligned_df[sentiment_col].diff().dropna()
        
        # Correlation of changes
        if len(market_returns) > 1 and len(sentiment_changes) > 1:
            change_corr, change_p = stats.pearsonr(
                sentiment_changes.iloc[:len(market_returns)],
                market_returns
            )
        else:
            change_corr, change_p = np.nan, 1.0
        
        return {
            "pearson_correlation": corr,
            "pearson_pvalue": pvalue,
            "pearson_significant": pvalue < 0.05,
            "r_squared": r_squared,
            "spearman_correlation": spearman_corr,
            "spearman_pvalue": spearman_p,
            "change_correlation": change_corr,
            "change_pvalue": change_p,
            "n_observations": len(aligned_df),
        }
