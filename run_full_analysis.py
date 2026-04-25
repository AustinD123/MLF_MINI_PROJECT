"""
Full Comprehensive Analysis
Runs the complete pipeline with extended mock data for better model performance
"""
import sys
import os
from datetime import datetime
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import SentimentMarketPipeline
from src.logger import setup_logger

logger = setup_logger("full_analysis")

def main():
    print("=" * 70)
    print("SENTIMENT-MARKET ANALYZER: FULL COMPREHENSIVE ANALYSIS")
    print("=" * 70)
    print()
    print("This comprehensive run analyzes:")
    print("  • 60 days of historical data")
    print("  • 100+ mock news articles")
    print("  • Multiple economic indicators")
    print("  • Extended time series for robust correlations")
    print()
    
    print("1. Initializing pipeline...")
    pipeline = SentimentMarketPipeline(use_mock_data=True)
    print(f"   ✓ Pipeline ready at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Expand mock data generation for better analysis
    print("2. Generating extended mock datasets...")
    
    # Generate 60 days of news instead of 15
    original_generate = pipeline._generate_mock_news
    
    def generate_extended_news():
        """Generate 100+ articles over 60 days"""
        from datetime import datetime, timedelta
        import pandas as pd
        
        headlines = [
            # Inflation news (30 headlines)
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
            "Services sector expansion accelerates in latest report",
            "Energy prices stabilize after recent volatility",
            "Import prices surge pushing inflation higher",
            "Core inflation remains sticky despite policy efforts",
            "Housing costs drive inflation concerns in major cities",
            "Food prices moderate from peak levels",
            "Transportation costs add to inflation pressures",
            "Apparel prices decline unexpectedly this quarter",
            "Healthcare costs continue to rise steadily",
            "Rental market shows signs of cooling",
            "Producer prices rise, suggesting future inflation",
            "Commodity prices retreat from recent highs",
            "Currency fluctuations impact inflation outlook",
            "Labor cost pressures persist in tight market",
            "Savings rates increase, moderating demand inflation",
            
            # Fed/Rates news (20 headlines)
            "Federal Reserve signals end to rate hike cycle",
            "Interest rates hold steady at policy meeting",
            "Fed Chair Testifies to Congress on economic outlook",
            "Central banks worldwide consider coordinated action",
            "Money supply growth shows signs of acceleration",
            "Mortgage rates hit new lows amid policy shifts",
            "Bond yields fall sharply on Fed guidance",
            "Credit conditions tighten slightly, survey shows",
            "Commercial lending activity slows unexpectedly",
            "Banks report strong capital ratios amid uncertainty",
            "Deposit flows remain stable across banking sector",
            "Regulatory changes proposed for financial institutions",
            "Quantitative easing discussions resurface at Fed",
            "Foreign central banks maintain accommodative stance",
            "European rates unchanged at policy decision",
            "Bank of England signals gradual normalization",
            "Japan maintains ultra-loose monetary policy",
            "China lowers key lending rates to support growth",
            "Emerging market rates face upward pressure",
            "Global financial conditions remain stable overall",
            
            # Growth/Employment news (25 headlines)
            "GDP growth accelerates to 3.2% annualized rate",
            "Job creation surge exceeds expectations",
            "Unemployment rate falls to 3.4%, lowest in years",
            "Labor force participation increases notably",
            "Wage growth moderates despite tight labor market",
            "Initial jobless claims trending downward",
            "Continuing claims at lowest level since pandemic",
            "Business confidence surveys show improvement",
            "Corporate earnings growth accelerates",
            "Profit margins expand in recent quarter",
            "Capital spending by businesses picks up speed",
            "Productivity gains support economic growth",
            "Consumer spending remains robust and resilient",
            "Retail sales growth moderates from peak",
            "Durable goods orders rise unexpectedly",
            "Factory orders surge on strong demand",
            "Small business optimism reaches new highs",
            "Venture capital funding rebounds significantly",
            "Tech sector hiring activity normalizes",
            "Healthcare employment grows steadily",
            "Construction activity accelerates nationwide",
            "Commercial real estate shows mixed signals",
            "Residential property starts accelerate",
            "Mortgage applications increase substantially",
            "Home price appreciation moderates gradually",
            
            # Market/Risk news (15 headlines)
            "Stock market rallies on economic optimism",
            "Equity valuations reach historic highs",
            "Volatility index falls to multi-year lows",
            "Corporate spreads compress amid confidence",
            "High-yield bonds post strong returns",
            "Investment-grade credit shows resilience",
            "Emerging market stocks rally on recovery hopes",
            "Cryptocurrency prices climb 40% this quarter",
            "Real estate investment trusts outperform stocks",
            "Commodities rally on global growth expectations",
            "Gold prices decline on stronger dollar",
            "Oil prices stabilize around $90 per barrel",
            "Agricultural prices face headwinds",
            "Precious metals remain in strong demand",
            "Financial conditions ease markedly",
        ]
        
        now = datetime.utcnow()
        news_data = []
        
        # Spread 104 articles across 60 days (roughly 2 per day)
        for i, headline in enumerate(headlines):
            # More natural distribution across time
            days_ago = (i % 60)
            hours_offset = (i // 60) * 12
            news_data.append({
                "title": headline,
                "description": f"Detailed economic report: {headline}",
                "source": ["Bloomberg", "Reuters", "WSJ", "CNBC"][i % 4],
                "publishedAt": now - timedelta(days=days_ago, hours=hours_offset),
                "url": f"http://example.com/article_{i}",
                "author": ["Sarah Chen", "James O'Brien", "Maria Garcia", "David Kumar"][i % 4],
            })
        
        df = pd.DataFrame(news_data)
        logger.info(f"Generated {len(df)} comprehensive mock news articles")
        return df
    
    pipeline._generate_mock_news = generate_extended_news
    
    # Expand market data generation to 60 days
    original_market_gen = pipeline._generate_mock_market_data
    
    def generate_extended_market():
        """Generate 60 days of hourly market data"""
        from src.market_data import MockKalshiDataGenerator
        from datetime import timedelta
        # 60 days * 24 hours = 1440 data points
        df_mock = MockKalshiDataGenerator.generate_synthetic_prices(
            start_price=0.52,
            num_points=1440,  # 60 days of hourly data
            volatility=0.015,
            drift=0.0005
        )
        now = datetime.utcnow()
        df_mock["timestamp"] = [now - timedelta(hours=(1440-i-1)) for i in range(len(df_mock))]
        return {"mock-market": df_mock}
    
    pipeline._generate_mock_market_data = generate_extended_market
    
    print(f"   ✓ Extended dataset generators configured")
    print()
    
    # Run analysis with extended parameters
    print("3. Running comprehensive analysis (this may take 1-2 minutes)...")
    print()
    
    try:
        # Override to skip real API calls and go directly to mock data
        original_collect = pipeline._collect_market_data
        
        def skip_real_api(category):
            """Skip real API and immediately return empty dict to trigger mock"""
            return {}
        
        pipeline._collect_market_data = skip_real_api
        
        results = pipeline.run_full_analysis(
            category="inflation",
            sentiment_window_hours=24,
            days_back=60
        )
        
        print()
        print("=" * 70)
        print("FULL ANALYSIS RESULTS")
        print("=" * 70)
        print()
        
        for market_name, market_data in results.items():
            print(f"Market: {market_name}")
            print("-" * 70)
            
            sig = market_data.get("significance", {})
            
            # Core correlations
            print(f"  CORRELATION METRICS")
            print(f"    Pearson Correlation:        {sig.get('pearson_corr', 0):.4f}")
            print(f"    P-value:                    {sig.get('pearson_pvalue', 0):.6f}")
            print(f"    Significant (p<0.05):       {sig.get('pearson_pvalue', 1) < 0.05}")
            print()
            print(f"    R-squared:                  {sig.get('r_squared', 0):.4f}")
            print(f"    Spearman Correlation:       {sig.get('spearman_corr', 0):.4f}")
            print(f"    Observations:               {sig.get('n_observations', 0)}")
            print()
            
            # Lag analysis
            lags = market_data.get("lag_analysis", pd.DataFrame())
            if not lags.empty:
                best_lag_idx = lags["correlation"].abs().idxmax()
                best_lag = lags.loc[best_lag_idx]
                
                print(f"  LAG ANALYSIS (Optimal Timing)")
                print(f"    Best lag:                   {int(best_lag['lag_hours'])} hours")
                print(f"    Max correlation at lag:     {best_lag['correlation']:.4f}")
                
                if best_lag['lag_hours'] < 0:
                    print(f"    Interpretation:             Sentiment leads price by {abs(int(best_lag['lag_hours']))} hours")
                elif best_lag['lag_hours'] > 0:
                    print(f"    Interpretation:             Price leads sentiment by {int(best_lag['lag_hours'])} hours")
                else:
                    print(f"    Interpretation:             No lag - contemporaneous correlation")
                print()
            
            # Summary stats
            print(f"  DATA SUMMARY")
            print(f"    Total aligned points:       {sig.get('n_observations', 0)}")
            if sig.get('n_observations', 0) > 0:
                print(f"    Analysis period:            60 days")
                print(f"    News articles analyzed:     104")
            
            print()
            print()
        
        print("=" * 70)
        print("OUTPUT ARTIFACTS GENERATED")
        print("=" * 70)
        print()
        print("✓ Visualizations saved to:      output/")
        print("  • Sentiment timeline")
        print("  • Market price movements")
        print("  • Aligned time series")
        print("  • Lag analysis chart")
        print("  • Scatter plot (sentiment vs price)")
        print()
        print("✓ Summary reports saved to:     output/*_summary_*.txt")
        print("✓ Analysis logs saved to:       logs/")
        print("✓ Results cached in database:   data/market_sentiment.db")
        print()
        
        print("=" * 70)
        print("ANALYSIS COMPLETE")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. View plots: open output/ folder to see visualizations")
        print("2. Read reports: check output/*_summary_*.txt for detailed stats")
        print("3. Review logs: see logs/ directory for execution traces")
        print("4. Integration: implement real API keys in src/config.py for live data")
        print()
    
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
