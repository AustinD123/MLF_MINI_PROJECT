"""
Main Orchestration Script
Runs the complete analysis pipeline
"""
import pandas as pd
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import KALSHI_MARKETS, OUTPUT_DIR
from src.logger import setup_logger
from src.news_collector import NewsCollector
from src.sentiment_analyzer import SentimentAnalyzer
from src.market_data import KalshiMarketCollector, MockKalshiDataGenerator
from src.time_series import TimeSeriesAnalyzer
from src.visualization import TimeSeriesVisualizer
from src.utils import DatabaseManager

logger = setup_logger("main")


class SentimentMarketPipeline:
    """Main pipeline orchestrator."""
    
    def __init__(self, use_mock_data: bool = False):
        self.use_mock_data = use_mock_data
        self.news_collector = NewsCollector()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.market_collector = KalshiMarketCollector()
        self.ts_analyzer = TimeSeriesAnalyzer()
        self.visualizer = TimeSeriesVisualizer()
        self.db = DatabaseManager()
        
        logger.info("Pipeline initialized")
    
    def run_full_analysis(
        self,
        category: str = "inflation",
        sentiment_window_hours: int = 24,
        days_back: int = 7
    ) -> Dict:
        """
        Run complete analysis pipeline.
        
        Args:
            category: Macro category (inflation, fed_rates, etc.)
            sentiment_window_hours: Aggregation window for sentiment
            days_back: Historical days to analyze
            
        Returns:
            Dictionary with all analysis results
        """
        logger.info(f"Starting full analysis for category: {category}")
        
        # Step 1: Collect and analyze news
        logger.info("Step 1: Collecting news...")
        if self.use_mock_data:
            news_df = self._generate_mock_news()
        else:
            news_df = self._collect_news(category)
        
        if news_df.empty:
            logger.error("No news articles collected")
            return {"error": "No news data"}
        
        # Step 2: Compute sentiment
        logger.info("Step 2: Computing sentiment...")
        news_with_sentiment = self._compute_sentiment(news_df)
        
        # Step 3: Aggregate sentiment
        logger.info("Step 3: Aggregating sentiment...")
        agg_sentiment = self._aggregate_sentiment(
            news_with_sentiment,
            window_hours=sentiment_window_hours
        )
        
        # Step 4: Collect market data
        logger.info("Step 4: Collecting market data...")
        market_data = self._collect_market_data(category)
        
        if not market_data or all(df.empty for df in market_data.values()):
            logger.warning("No market data collected, using mock data")
            market_data = self._generate_mock_market_data()
        
        # Step 5: Align and analyze
        results = {}
        for market_slug, market_df in market_data.items():
            logger.info(f"Analyzing market: {market_slug}")
            
            # Align signals
            aligned = self.ts_analyzer.align_timeseries(agg_sentiment, market_df)
            
            if aligned.empty:
                logger.warning(f"No aligned data for {market_slug}")
                continue
            
            # Compute correlations
            signal_strength = self.ts_analyzer.compute_signal_strength(aligned)
            rolling_corr = self.ts_analyzer.compute_rolling_correlation(aligned)
            lag_analysis = self.ts_analyzer.lag_analysis(aligned)
            
            # Generate visualizations
            self._generate_visualizations(
                agg_sentiment,
                market_df,
                aligned,
                rolling_corr,
                lag_analysis,
                market_slug
            )
            
            results[market_slug] = {
                "aligned_data": aligned,
                "signal_strength": signal_strength,
                "rolling_correlation": rolling_corr,
                "lag_analysis": lag_analysis,
                "news_count": len(news_df),
                "sentiment_mean": agg_sentiment["mean_sentiment"].mean(),
                "sentiment_std": agg_sentiment["mean_sentiment"].std(),
            }
        
        logger.info("Analysis complete")
        return results
    
    def _collect_news(self, category: str) -> pd.DataFrame:
        """Collect news for category."""
        df = self.news_collector.fetch_macro_news(category)
        df = self.news_collector.deduplicate_articles(df)
        df = self.news_collector.filter_by_source_reliability(df)
        
        logger.info(f"Collected {len(df)} unique news articles")
        
        # Optionally save to database
        if not df.empty:
            self.db.save_articles(df)
        
        return df
    
    def _generate_mock_news(self) -> pd.DataFrame:
        """Generate synthetic news data for testing."""
        from datetime import datetime, timedelta
        
        # Sample news headlines for testing (positive, negative, neutral mix)
        headlines = [
            "CPI inflation rises faster than expected, Fed may need to act",
            "Consumer prices surge amid supply chain issues",
            "Moderate inflation growth reported in latest data",
            "Fed official: interest rates may need to rise further",
            "Economic outlook improves despite inflation concerns",
            "Unemployment claims fall to lowest level in months",
            "Stock market rebounds on positive inflation signals",
            "Central bank signals cautious approach to rate hikes",
            "Inflation moderates in key sectors, economists hopeful",
            "Market volatility reflects investor concerns over rates",
            "Strong retail sales boost economic growth expectations",
            "Wage growth accelerates, adding pressure to inflation",
            "Manufacturing activity shows unexpected resilience",
            "Consumer confidence reaches higher levels",
            "Trade tensions ease, supporting market sentiment",
        ]
        
        # Generate articles spread across 15 days (multiple 24h windows for time series)
        now = datetime.utcnow()
        news_data = []
        
        for i, headline in enumerate(headlines):
            # Spread articles across 15 days to create multiple time windows
            hours_ago = (i % 15) * 24 + (i // 15) * 6
            news_data.append({
                "title": headline,
                "description": f"Detailed report on economic sentiment. {headline}",
                "source": "Bloomberg" if i % 2 == 0 else "Reuters",
                "publishedAt": now - timedelta(hours=hours_ago),
                "url": f"http://example.com/article_{i}",
                "author": "Test Author",
            })
        
        df = pd.DataFrame(news_data)
        logger.info(f"Generated {len(df)} mock news articles")
        return df
    
    def _compute_sentiment(self, news_df: pd.DataFrame) -> pd.DataFrame:
        """Add sentiment scores to news."""
        df_with_sentiment = self.sentiment_analyzer.analyze_dataframe(
            news_df,
            text_column="title"
        )
        logger.info(f"Computed sentiment for {len(df_with_sentiment)} articles")
        return df_with_sentiment
    
    def _aggregate_sentiment(
        self,
        news_df: pd.DataFrame,
        window_hours: int = 24
    ) -> pd.DataFrame:
        """Aggregate sentiment over time windows."""
        agg_sentiment = self.sentiment_analyzer.aggregate_sentiment(
            news_df,
            time_column="publishedAt",
            window_hours=window_hours
        )
        logger.info(f"Aggregated into {len(agg_sentiment)} time windows")
        return agg_sentiment
    
    def _collect_market_data(self, category: str) -> Dict[str, pd.DataFrame]:
        """Collect market data for category."""
        markets_for_category = KALSHI_MARKETS.get(category, [])
        
        if not markets_for_category:
            logger.warning(f"No markets configured for category: {category}")
            return {}
        
        results = {}
        for market_slug in markets_for_category:
            try:
                df = self.market_collector.fetch_market_prices(market_slug)
                if not df.empty:
                    results[market_slug] = df
            except Exception as e:
                logger.warning(f"Error fetching {market_slug}: {e}")
        
        return results
    
    def _generate_mock_market_data(self) -> Dict[str, pd.DataFrame]:
        """Generate synthetic market data for testing."""
        # Generate data points over 15 days (same range as mock news data)
        # 24 points per day = 360 total points
        df_mock = MockKalshiDataGenerator.generate_synthetic_prices(
            start_price=0.50,
            num_points=360  # 15 days of hourly data
        )
        # Adjust timestamps to start 15 days ago
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        df_mock["timestamp"] = [now - timedelta(hours=(360-i-1)) for i in range(len(df_mock))]
        return {"mock-market": df_mock}
    
    def _generate_visualizations(
        self,
        agg_sentiment: pd.DataFrame,
        market_df: pd.DataFrame,
        aligned: pd.DataFrame,
        rolling_corr: pd.DataFrame,
        lag_analysis: pd.DataFrame,
        market_slug: str
    ):
        """Generate and save all visualizations."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sentiment timeline
        self.visualizer.plot_sentiment_timeline(
            agg_sentiment,
            save_as=f"{market_slug}_sentiment_timeline_{timestamp}.png"
        )
        
        # Market probability
        self.visualizer.plot_market_probability(
            market_df,
            save_as=f"{market_slug}_market_price_{timestamp}.png"
        )
        
        # Aligned series
        self.visualizer.plot_aligned_series(
            aligned,
            save_as=f"{market_slug}_aligned_{timestamp}.png"
        )
        
        # Rolling correlation
        if not rolling_corr.empty:
            self.visualizer.plot_rolling_correlation(
                rolling_corr,
                save_as=f"{market_slug}_rolling_correlation_{timestamp}.png"
            )
        
        # Lag analysis
        if not lag_analysis.empty:
            self.visualizer.plot_lag_analysis(
                lag_analysis,
                save_as=f"{market_slug}_lag_analysis_{timestamp}.png"
            )
        
        # Scatter plot
        self.visualizer.plot_scatter_correlation(
            aligned,
            save_as=f"{market_slug}_scatter_{timestamp}.png"
        )
        
        # Summary report
        signal_strength = self.ts_analyzer.compute_signal_strength(aligned)
        self.visualizer.create_summary_report(
            signal_strength,
            lag_analysis,
            aligned,
            save_as=f"{market_slug}_summary_{timestamp}.txt"
        )
        
        logger.info(f"Generated visualizations for {market_slug}")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sentiment Market Analyzer - Analyze news sentiment vs Kalshi predictions"
    )
    parser.add_argument(
        "--category",
        default="inflation",
        choices=["inflation", "fed_rates", "recession", "unemployment"],
        help="Macro category to analyze"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Days of history to analyze"
    )
    parser.add_argument(
        "--window",
        type=int,
        default=24,
        help="Sentiment aggregation window in hours"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data (for testing)"
    )
    
    args = parser.parse_args()
    
    # Create pipeline
    pipeline = SentimentMarketPipeline(use_mock_data=args.mock)
    
    # Run analysis
    results = pipeline.run_full_analysis(
        category=args.category,
        sentiment_window_hours=args.window,
        days_back=args.days
    )
    
    # Print results
    logger.info("\n" + "="*70)
    logger.info("ANALYSIS RESULTS")
    logger.info("="*70)
    
    for market_slug, market_results in results.items():
        if "error" in market_results:
            logger.error(f"{market_slug}: {market_results['error']}")
            continue
        
        sig = market_results["signal_strength"]
        logger.info(f"\n{market_slug}:")
        logger.info(f"  Correlation: {sig.get('pearson_correlation', 0):.4f}")
        logger.info(f"  P-value: {sig.get('pearson_pvalue', 1):.6f}")
        logger.info(f"  R-squared: {sig.get('r_squared', 0):.4f}")
        logger.info(f"  Observations: {sig.get('n_observations', 0)}")
        
        lag_df = market_results["lag_analysis"]
        if not lag_df.empty:
            best_lag = lag_df.loc[lag_df["correlation"].abs().idxmax()]
            logger.info(f"  Best lag: {int(best_lag['lag_hours'])} hours (r={best_lag['correlation']:.4f})")
    
    logger.info("\nOutput saved to: " + OUTPUT_DIR)


if __name__ == "__main__":
    main()
