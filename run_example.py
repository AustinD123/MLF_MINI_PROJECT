"""
Quick Start Example - Run this to test the complete pipeline with mock data
"""

if __name__ == "__main__":
    from main import SentimentMarketPipeline
    import pandas as pd
    
    print("="*70)
    print("SENTIMENT-MARKET ANALYZER: QUICK START EXAMPLE")
    print("="*70)
    print("\nThis example runs the complete analysis pipeline with mock data.")
    print("No API keys required!\n")
    
    # Initialize pipeline with mock data
    print("1. Initializing pipeline with synthetic market data...")
    pipeline = SentimentMarketPipeline(use_mock_data=True)
    print("   ✓ Pipeline ready\n")
    
    # Run analysis
    print("2. Running full analysis pipeline...")
    print("   - Collecting mock news")
    print("   - Computing sentiment scores") 
    print("   - Generating market prices")
    print("   - Aligning time series")
    print("   - Computing correlations")
    print("   - Generating visualizations\n")
    
    results = pipeline.run_full_analysis(
        category="inflation",
        sentiment_window_hours=24,
        days_back=7
    )
    
    # Display results
    print("3. RESULTS:\n")
    
    if "error" in results:
        print(f"Error: {results['error']}")
    else:
        for market_slug, market_data in results.items():
            print(f"Market: {market_slug}")
            print("-" * 50)
            
            sig = market_data["signal_strength"]
            print(f"  Correlation (Pearson):        {sig.get('pearson_correlation', 0):.4f}")
            print(f"  P-value:                      {sig.get('pearson_pvalue', 1):.6f}")
            print(f"  Significant (p<0.05):         {sig.get('pearson_significant', False)}")
            print(f"  R-squared:                    {sig.get('r_squared', 0):.4f}")
            print(f"  Observations:                 {sig.get('n_observations', 0)}")
            
            # Lag analysis
            lags = market_data["lag_analysis"]
            if not lags.empty:
                best_lag_idx = lags["correlation"].abs().idxmax()
                best_lag = lags.loc[best_lag_idx]  # Use loc instead of iloc
                
                print(f"\n  Lag Analysis (Max Correlation):")
                print(f"    Optimal lag:              {int(best_lag['lag_hours'])} hours")
                print(f"    Correlation at lag:       {best_lag['correlation']:.4f}")
                print(f"    Interpretation:           ", end="")
                
                if best_lag['lag_hours'] < 0:
                    print(f"Sentiment leads price by {abs(int(best_lag['lag_hours']))} hours")
                elif best_lag['lag_hours'] > 0:
                    print(f"Price leads sentiment by {int(best_lag['lag_hours'])} hours")
                else:
                    print("Contemporaneous relationship")
            
            # Summary stats
            print(f"\n  Summary Statistics:")
            print(f"    Mean sentiment:           {market_data['sentiment_mean']:.4f}")
            print(f"    Sentiment std dev:        {market_data['sentiment_std']:.4f}")
            print(f"    News articles analyzed:   {market_data['news_count']}")
            print()
    
    print("="*70)
    print("OUTPUT FILES:")
    print("="*70)
    print("✓ Plots saved to:     output/")
    print("✓ Logs saved to:      logs/")
    print("✓ Database cached to: data/market_sentiment.db")
    print("\nNext steps:")
    print("1. Review generated plots in output/")
    print("2. Read output/*_summary.txt for detailed statistics")
    print("3. Check logs/ for execution details")
    print("4. Configure real API keys to analyze actual market data")
    print("\nFor help, see README.md")
    print("="*70)
