"""
Pipeline Summary and Logging Module
Generates comprehensive logs and summary statistics for analysis pipeline
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any
import os
import json
from src.logger import setup_logger
from src.config import OUTPUT_DIR, DATA_DIR

logger = setup_logger("pipeline_summary")


class PipelineSummary:
    """Generate comprehensive pipeline summary and logs"""
    
    def __init__(self, output_dir: str = OUTPUT_DIR):
        """
        Initialize summary generator
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    @staticmethod
    def compute_data_statistics(
        news_df: pd.DataFrame,
        market_df: pd.DataFrame,
        aligned_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Compute comprehensive data statistics
        
        Args:
            news_df: News data
            market_df: Market data
            aligned_df: Aligned sentiment-market data
            
        Returns:
            Dictionary with statistics
        """
        stats = {}
        
        # News statistics
        stats["news"] = {
            "total_articles": len(news_df),
            "unique_sources": news_df["source"].nunique() if "source" in news_df.columns else 0,
            "date_range": {
                "start": str(news_df["timestamp"].min()) if "timestamp" in news_df.columns else "N/A",
                "end": str(news_df["timestamp"].max()) if "timestamp" in news_df.columns else "N/A",
            },
            "articles_per_day": len(news_df) / max(1, (news_df["timestamp"].max() - news_df["timestamp"].min()).days),
        }
        
        if "category" in news_df.columns:
            stats["news"]["by_category"] = news_df["category"].value_counts().to_dict()
        
        # Market statistics
        stats["market"] = {
            "total_data_points": len(market_df),
            "unique_tickers": market_df["market_ticker"].nunique() if "market_ticker" in market_df.columns else 1,
            "date_range": {
                "start": str(market_df["timestamp"].min()) if "timestamp" in market_df.columns else "N/A",
                "end": str(market_df["timestamp"].max()) if "timestamp" in market_df.columns else "N/A",
            },
        }
        
        # Price statistics
        if "mid_price" in market_df.columns:
            stats["market"]["price"] = {
                "mean": float(market_df["mid_price"].mean()),
                "median": float(market_df["mid_price"].median()),
                "std": float(market_df["mid_price"].std()),
                "min": float(market_df["mid_price"].min()),
                "max": float(market_df["mid_price"].max()),
            }
        
        # Aligned data statistics
        stats["aligned"] = {
            "total_records": len(aligned_df),
            "date_range": {
                "start": str(aligned_df["timestamp"].min()) if "timestamp" in aligned_df.columns else "N/A",
                "end": str(aligned_df["timestamp"].max()) if "timestamp" in aligned_df.columns else "N/A",
            },
        }
        
        # Sentiment statistics
        if "weighted_sentiment" in aligned_df.columns:
            stats["aligned"]["sentiment"] = {
                "mean": float(aligned_df["weighted_sentiment"].mean()),
                "median": float(aligned_df["weighted_sentiment"].median()),
                "std": float(aligned_df["weighted_sentiment"].std()),
                "min": float(aligned_df["weighted_sentiment"].min()),
                "max": float(aligned_df["weighted_sentiment"].max()),
            }
        elif "mean_sentiment" in aligned_df.columns:
            stats["aligned"]["sentiment"] = {
                "mean": float(aligned_df["mean_sentiment"].mean()),
                "median": float(aligned_df["mean_sentiment"].median()),
                "std": float(aligned_df["mean_sentiment"].std()),
                "min": float(aligned_df["mean_sentiment"].min()),
                "max": float(aligned_df["mean_sentiment"].max()),
            }
        
        # Missing data statistics
        stats["data_quality"] = {
            "news_missing_values": int(news_df.isnull().sum().sum()),
            "market_missing_values": int(market_df.isnull().sum().sum()),
            "aligned_missing_values": int(aligned_df.isnull().sum().sum()),
        }
        
        return stats
    
    @staticmethod
    def compute_correlation_metrics(aligned_df: pd.DataFrame) -> Dict[str, float]:
        """
        Compute correlation metrics between sentiment and market data
        
        Args:
            aligned_df: Aligned data
            
        Returns:
            Dictionary with correlation metrics
        """
        metrics = {}
        
        # Find sentiment column
        sentiment_col = None
        for col in ["weighted_sentiment", "mean_sentiment", "sentiment"]:
            if col in aligned_df.columns:
                sentiment_col = col
                break
        
        # Find price column
        price_col = None
        for col in ["mid_price", "price"]:
            if col in aligned_df.columns:
                price_col = col
                break
        
        if sentiment_col and price_col:
            # Pearson correlation
            pearson_corr = aligned_df[[sentiment_col, price_col]].corr().iloc[0, 1]
            metrics["pearson_correlation"] = float(pearson_corr)
            
            # Spearman correlation (rank-based)
            spearman_corr = aligned_df[[sentiment_col, price_col]].corr(method='spearman').iloc[0, 1]
            metrics["spearman_correlation"] = float(spearman_corr)
            
            # Kendall correlation
            kendall_corr = aligned_df[[sentiment_col, price_col]].corr(method='kendall').iloc[0, 1]
            metrics["kendall_correlation"] = float(kendall_corr)
        
        return metrics
    
    def generate_summary_report(
        self,
        results: Dict,
        configuration: Dict,
        filename: str = "pipeline_summary.json"
    ) -> str:
        """
        Generate comprehensive JSON summary report
        
        Args:
            results: Pipeline results
            configuration: Configuration used
            filename: Output filename
            
        Returns:
            Path to summary file
        """
        news_df = results.get("news", pd.DataFrame())
        market_df = results.get("prices", pd.DataFrame())
        aligned_df = results.get("aligned", pd.DataFrame())
        
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": configuration,
            "data_statistics": self.compute_data_statistics(news_df, market_df, aligned_df),
            "correlation_metrics": self.compute_correlation_metrics(aligned_df),
        }
        
        # Add lag analysis results
        if "lag_analysis" in results and results["lag_analysis"]:
            summary["lag_analysis"] = {
                "optimal_lag_hours": results["lag_analysis"].get("optimal_lag"),
                "correlation_at_lag": results["lag_analysis"].get("correlation_at_lag"),
                "p_value": results["lag_analysis"].get("pvalue_at_lag"),
                "significant": results["lag_analysis"].get("significant"),
            }
        
        # Add event detection results
        if "events" in results and results["events"]:
            summary["event_detection"] = {
                "total_events": results["events"].get("event_count", 0),
                "event_types": results["events"].get("event_types", {}),
            }
        
        # Add model performance
        if "models" in results and results["models"]:
            models = results["models"]
            summary["model_performance"] = {
                "linear_regression": {
                    "test_r2": models.get("linear_regression", {}).get("r2"),
                    "test_mae": models.get("linear_regression", {}).get("mae"),
                },
                "random_forest": {
                    "test_r2": models.get("random_forest", {}).get("r2"),
                    "test_mae": models.get("random_forest", {}).get("mae"),
                    "top_features": models.get("random_forest", {}).get("top_features", [])[:5],
                },
            }
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Summary report saved: {filepath}")
        return filepath
    
    def generate_text_summary(
        self,
        results: Dict,
        configuration: Dict,
        filename: str = "PIPELINE_SUMMARY.txt"
    ) -> str:
        """
        Generate human-readable text summary
        
        Args:
            results: Pipeline results
            configuration: Configuration used
            filename: Output filename
            
        Returns:
            Path to summary file
        """
        news_df = results.get("news", pd.DataFrame())
        market_df = results.get("prices", pd.DataFrame())
        aligned_df = results.get("aligned", pd.DataFrame())
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("SENTIMENT-MARKET ANALYZER: PIPELINE EXECUTION SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            # Execution details
            f.write("EXECUTION DETAILS\n")
            f.write("-" * 80 + "\n")
            f.write(f"Timestamp: {datetime.utcnow().isoformat()}\n")
            f.write(f"Use Real News: {configuration.get('USE_REAL_NEWS', False)}\n")
            f.write(f"Use Real Market Data: {configuration.get('USE_REAL_MARKET_DATA', False)}\n")
            f.write(f"Use Cache: {configuration.get('USE_CACHE', False)}\n")
            f.write(f"Fallback to Mock: {configuration.get('FALLBACK_TO_MOCK_DATA', False)}\n\n")
            
            # Data Collection
            f.write("DATA COLLECTION SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"News Articles Collected: {len(news_df)}\n")
            f.write(f"Market Data Points: {len(market_df)}\n")
            f.write(f"Aligned Records: {len(aligned_df)}\n\n")
            
            if "timestamp" in news_df.columns:
                f.write(f"News Time Range:\n")
                f.write(f"  Start: {news_df['timestamp'].min()}\n")
                f.write(f"  End: {news_df['timestamp'].max()}\n")
                f.write(f"  Days Covered: {(news_df['timestamp'].max() - news_df['timestamp'].min()).days}\n")
            
            if "timestamp" in market_df.columns:
                f.write(f"\nMarket Data Time Range:\n")
                f.write(f"  Start: {market_df['timestamp'].min()}\n")
                f.write(f"  End: {market_df['timestamp'].max()}\n")
                f.write(f"  Days Covered: {(market_df['timestamp'].max() - market_df['timestamp'].min()).days}\n")
            
            if "source" in news_df.columns:
                f.write(f"\nNews Sources:\n")
                sources = news_df["source"].value_counts()
                for source, count in sources.head(10).items():
                    f.write(f"  {source}: {count}\n")
            
            # Sentiment Analysis
            f.write(f"\n\nSENTIMENT ANALYSIS\n")
            f.write("-" * 80 + "\n")
            
            sentiment_col = None
            for col in ["weighted_sentiment", "mean_sentiment", "sentiment"]:
                if col in aligned_df.columns:
                    sentiment_col = col
                    break
            
            if sentiment_col:
                sentiment_data = aligned_df[sentiment_col]
                f.write(f"Sentiment Statistics:\n")
                f.write(f"  Mean: {sentiment_data.mean():.4f}\n")
                f.write(f"  Median: {sentiment_data.median():.4f}\n")
                f.write(f"  Std Dev: {sentiment_data.std():.4f}\n")
                f.write(f"  Min: {sentiment_data.min():.4f}\n")
                f.write(f"  Max: {sentiment_data.max():.4f}\n")
            
            # Market Analysis
            f.write(f"\n\nMARKET ANALYSIS\n")
            f.write("-" * 80 + "\n")
            
            price_col = None
            for col in ["mid_price", "price"]:
                if col in aligned_df.columns:
                    price_col = col
                    break
            
            if price_col:
                price_data = aligned_df[price_col]
                f.write(f"Price Statistics:\n")
                f.write(f"  Mean: {price_data.mean():.4f}\n")
                f.write(f"  Median: {price_data.median():.4f}\n")
                f.write(f"  Std Dev: {price_data.std():.4f}\n")
                f.write(f"  Min: {price_data.min():.4f}\n")
                f.write(f"  Max: {price_data.max():.4f}\n")
            
            # Correlation
            f.write(f"\n\nCORRELATION ANALYSIS\n")
            f.write("-" * 80 + "\n")
            
            corr_metrics = self.compute_correlation_metrics(aligned_df)
            if corr_metrics:
                for metric_name, value in corr_metrics.items():
                    if isinstance(value, (int, float)):
                        f.write(f"{metric_name}: {value:.4f}\n")
                    else:
                        f.write(f"{metric_name}: {value}\n")
            else:
                f.write("No correlation metrics computed\n")
            
            # Lag Analysis
            if "lag_analysis" in results and results["lag_analysis"]:
                f.write(f"\n\nLAG ANALYSIS\n")
                f.write("-" * 80 + "\n")
                lag = results["lag_analysis"]
                opt_lag = lag.get('optimal_lag', 'N/A')
                if isinstance(opt_lag, dict):
                    opt_lag = opt_lag.get('optimal_lag', 'N/A')
                f.write(f"Optimal Lag: {opt_lag}\n")
                
                corr = lag.get('correlation_at_lag', 'N/A')
                if isinstance(corr, (int, float)):
                    f.write(f"Correlation at Lag: {corr:.4f}\n")
                else:
                    f.write(f"Correlation at Lag: {corr}\n")
                
                pval = lag.get('pvalue_at_lag', 'N/A')
                if isinstance(pval, (int, float)):
                    f.write(f"P-value: {pval:.6f}\n")
                else:
                    f.write(f"P-value: {pval}\n")
                    
                f.write(f"Significant: {lag.get('significant', 'N/A')}\n")
                if "interpretation" in lag:
                    f.write(f"Interpretation: {lag['interpretation']}\n")
            
            # Event Detection
            if "events" in results and results["events"]:
                f.write(f"\n\nEVENT DETECTION\n")
                f.write("-" * 80 + "\n")
                events = results["events"]
                f.write(f"Total Events Detected: {events.get('event_count', 0)}\n")
                if events.get("event_types"):
                    f.write(f"Event Types:\n")
                    for event_type, count in events["event_types"].items():
                        f.write(f"  {event_type}: {count}\n")
            
            # Model Performance
            if "models" in results and results["models"]:
                f.write(f"\n\nPREDICTIVE MODELS\n")
                f.write("-" * 80 + "\n")
                
                models = results["models"]
                
                if "linear_regression" in models:
                    lr = models["linear_regression"]
                    f.write(f"\nLinear Regression:\n")
                    f.write(f"  Test R²: {lr.get('r2', 'N/A')}\n")
                    f.write(f"  Test MAE: {lr.get('mae', 'N/A')}\n")
                
                if "random_forest" in models:
                    rf = models["random_forest"]
                    f.write(f"\nRandom Forest:\n")
                    f.write(f"  Test R²: {rf.get('r2', 'N/A')}\n")
                    f.write(f"  Test MAE: {rf.get('mae', 'N/A')}\n")
                    
                    if rf.get("top_features"):
                        f.write(f"  Top Features:\n")
                        for i, feature in enumerate(rf["top_features"][:5], 1):
                            f.write(f"    {i}. {feature}\n")
            
            # Data Quality
            f.write(f"\n\nDATA QUALITY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Missing Values in News: {news_df.isnull().sum().sum()}\n")
            f.write(f"Missing Values in Market Data: {market_df.isnull().sum().sum()}\n")
            f.write(f"Missing Values in Aligned Data: {aligned_df.isnull().sum().sum()}\n")
            
            f.write(f"\n" + "=" * 80 + "\n")
            f.write("End of Report\n")
            f.write("=" * 80 + "\n")
        
        logger.info(f"Text summary saved: {filepath}")
        return filepath
    
    def generate_all_summaries(
        self,
        results: Dict,
        configuration: Dict
    ) -> Dict[str, str]:
        """
        Generate all summary reports
        
        Args:
            results: Pipeline results
            configuration: Configuration used
            
        Returns:
            Dictionary mapping report type to filepath
        """
        reports = {}
        
        # JSON summary
        reports["json"] = self.generate_summary_report(
            results, configuration, "pipeline_summary.json"
        )
        
        # Text summary
        reports["text"] = self.generate_text_summary(
            results, configuration, "PIPELINE_SUMMARY.txt"
        )
        
        logger.info(f"Generated {len(reports)} summary reports")
        return reports
