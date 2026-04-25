"""
Advanced Lag Analysis Module
Implements cross-correlation, bootstrap, and confidence intervals
"""
import pandas as pd
import numpy as np
from scipy import signal, stats
from typing import Tuple, Dict, List, Optional
import warnings

warnings.filterwarnings('ignore')

from src.logger import setup_logger

logger = setup_logger("lag_analysis")


class AdvancedLagAnalyzer:
    """Advanced lag analysis with statistical rigor"""
    
    @staticmethod
    def compute_cross_correlation(
        x: np.ndarray,
        y: np.ndarray,
        max_lag: int = 50
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute cross-correlation function (CCF)
        
        Args:
            x: First time series (sentiment)
            y: Second time series (price)
            max_lag: Maximum lag to test
            
        Returns:
            Tuple of (lags, correlations)
        """
        # Standardize inputs
        x = (x - np.mean(x)) / (np.std(x) + 1e-8)
        y = (y - np.mean(y)) / (np.std(y) + 1e-8)
        
        # Compute cross-correlation
        correlation = signal.correlate(x, y, mode='same') / len(x)
        
        # Get lag indices
        lags = signal.correlation_lags(len(x), len(y), mode='same')
        
        # Limit to max_lag
        mask = np.abs(lags) <= max_lag
        lags = lags[mask]
        correlation = correlation[mask]
        
        return lags, correlation
    
    @staticmethod
    def compute_lag_correlations(
        data: pd.DataFrame,
        x_col: str,
        y_col: str,
        max_lag: int = 50,
        step: int = 1
    ) -> pd.DataFrame:
        """
        Compute correlations at different lags
        
        Args:
            data: DataFrame with time series
            x_col: Column name for first series (sentiment)
            y_col: Column name for second series (price)
            max_lag: Maximum lag in samples
            step: Lag step size
            
        Returns:
            DataFrame with lag analysis
        """
        x = data[x_col].values
        y = data[y_col].values
        
        results = []
        
        for lag in range(-max_lag, max_lag + 1, step):
            if lag < 0:
                # Sentiment leads price
                x_slice = x[:lag]
                y_slice = y[-lag:]
            elif lag > 0:
                # Price leads sentiment
                x_slice = x[lag:]
                y_slice = y[:-lag]
            else:
                # No lag
                x_slice = x
                y_slice = y
            
            # Skip if slices are too small
            if len(x_slice) < 2:
                continue
            
            corr, pvalue = stats.pearsonr(x_slice, y_slice)
            
            results.append({
                "lag": lag,
                "lag_hours": lag,  # Assuming 1 sample = 1 hour
                "correlation": corr,
                "pvalue": pvalue,
                "significant": pvalue < 0.05
            })
        
        df_results = pd.DataFrame(results)
        logger.info(f"Computed {len(df_results)} lag correlations")
        
        return df_results
    
    @staticmethod
    def bootstrap_correlation(
        x: np.ndarray,
        y: np.ndarray,
        n_bootstrap: int = 1000,
        confidence_level: float = 0.95
    ) -> Dict:
        """
        Bootstrap resampling to estimate correlation confidence intervals
        
        Args:
            x: First time series
            y: Second time series
            n_bootstrap: Number of bootstrap samples
            confidence_level: Confidence level (0.95 for 95%)
            
        Returns:
            Dictionary with bootstrap statistics
        """
        correlations = []
        n = len(x)
        
        np.random.seed(42)
        for _ in range(n_bootstrap):
            # Random sampling with replacement
            indices = np.random.choice(n, size=n, replace=True)
            
            x_sample = x[indices]
            y_sample = y[indices]
            
            # Compute correlation
            if np.std(x_sample) > 0 and np.std(y_sample) > 0:
                corr = np.corrcoef(x_sample, y_sample)[0, 1]
                correlations.append(corr)
        
        correlations = np.array(correlations)
        
        # Compute confidence intervals
        alpha = 1 - confidence_level
        ci_lower = np.percentile(correlations, alpha/2 * 100)
        ci_upper = np.percentile(correlations, (1 - alpha/2) * 100)
        
        result = {
            "mean_correlation": np.mean(correlations),
            "std_correlation": np.std(correlations),
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "median_correlation": np.median(correlations),
            "bootstrap_samples": n_bootstrap,
            "confidence_level": confidence_level
        }
        
        logger.info(
            f"Bootstrap CI: [{ci_lower:.4f}, {ci_upper:.4f}] "
            f"(mean={np.mean(correlations):.4f})"
        )
        
        return result
    
    @staticmethod
    def detect_optimal_lag(
        lag_df: pd.DataFrame,
        use_absolute: bool = True
    ) -> Dict:
        """
        Detect optimal lag using statistical criteria
        
        Args:
            lag_df: DataFrame from compute_lag_correlations
            use_absolute: Use absolute correlation value
            
        Returns:
            Dictionary with optimal lag info
        """
        if use_absolute:
            idx = lag_df["correlation"].abs().idxmax()
        else:
            idx = lag_df["correlation"].idxmax()
        
        optimal = lag_df.loc[idx]
        
        result = {
            "optimal_lag": int(optimal["lag"]),
            "optimal_lag_hours": int(optimal["lag_hours"]),
            "correlation_at_lag": float(optimal["correlation"]),
            "pvalue_at_lag": float(optimal["pvalue"]),
            "significant": bool(optimal["significant"])
        }
        
        # Interpretation
        if result["optimal_lag"] < 0:
            result["interpretation"] = f"Sentiment leads price by {abs(result['optimal_lag'])} hours"
        elif result["optimal_lag"] > 0:
            result["interpretation"] = f"Price leads sentiment by {result['optimal_lag']} hours"
        else:
            result["interpretation"] = "Contemporaneous correlation"
        
        logger.info(f"Optimal lag: {result['optimal_lag']} hours ({result['interpretation']})")
        
        return result
    
    @staticmethod
    def compute_granger_causality(
        data: pd.DataFrame,
        cause_col: str,
        effect_col: str,
        max_lag: int = 5
    ) -> Dict:
        """
        Granger causality test: Does sentiment Granger-cause price?
        
        Args:
            data: DataFrame with time series
            cause_col: Column that may cause effect
            effect_col: Column that may be affected
            max_lag: Maximum lag for test
            
        Returns:
            Dictionary with test results
        """
        try:
            from statsmodels.tsa.stattools import grangercausalitytests
            
            # Prepare data
            test_data = data[[cause_col, effect_col]].dropna()
            
            # Run Granger causality test
            results = grangercausalitytests(test_data, max_lag, verbose=False)
            
            # Extract p-values
            pvalues = [results[lag][0]["ssr_ftest"][1] for lag in range(1, max_lag + 1)]
            min_pvalue = min(pvalues)
            optimal_lag = pvalues.index(min_pvalue) + 1
            
            result = {
                "cause_column": cause_col,
                "effect_column": effect_col,
                "rejects_null": min_pvalue < 0.05,
                "min_pvalue": min_pvalue,
                "optimal_lag": optimal_lag,
                "all_pvalues": pvalues,
                "interpretation": (
                    f"Sentiment Granger-causes price at lag {optimal_lag}" 
                    if min_pvalue < 0.05 
                    else "No Granger causality detected"
                )
            }
            
            logger.info(f"Granger causality: {result['interpretation']} (p={min_pvalue:.4f})")
            
            return result
            
        except Exception as e:
            logger.warning(f"Granger causality test failed: {e}")
            return {
                "error": str(e),
                "rejects_null": False,
                "interpretation": "Test could not be performed"
            }


def comprehensive_lag_analysis(
    data: pd.DataFrame,
    x_col: str = "mean_sentiment",
    y_col: str = "mid_price",
    max_lag: int = 50
) -> Dict:
    """
    Comprehensive lag analysis combining multiple methods
    
    Args:
        data: Aligned sentiment and price data
        x_col: Sentiment column
        y_col: Price column
        max_lag: Maximum lag hours
        
    Returns:
        Dictionary with all analysis results
    """
    analyzer = AdvancedLagAnalyzer()
    
    # Standardize data
    x = data[x_col].values
    y = data[y_col].values
    x_std = (x - np.mean(x)) / (np.std(x) + 1e-8)
    y_std = (y - np.mean(y)) / (np.std(y) + 1e-8)
    
    # Lag correlations
    lag_df = analyzer.compute_lag_correlations(
        data, x_col, y_col, max_lag=max_lag, step=1
    )
    
    # Optimal lag
    opt_lag = analyzer.detect_optimal_lag(lag_df)
    
    # Bootstrap CI
    bootstrap_stats = analyzer.bootstrap_correlation(x_std, y_std, n_bootstrap=1000)
    
    # Granger causality
    granger = analyzer.compute_granger_causality(data, x_col, y_col, max_lag=5)
    
    result = {
        "lag_correlations": lag_df,
        "optimal_lag": opt_lag,
        "bootstrap_statistics": bootstrap_stats,
        "granger_causality": granger,
        "max_lag_tested": max_lag
    }
    
    logger.info("Comprehensive lag analysis complete")
    
    return result
