# Quick Reference Card

## Installation (5 minutes)

```bash
cd sentiment_market_analyzer
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -c "import nltk; nltk.download('vader_lexicon')"
```

## Quick Start (No API Keys Needed)

```bash
python run_example.py
# Check output/ for plots
```

## Real Analysis (With API Keys)

```bash
# Set API keys
export NEWSAPI_KEY=your_key
export KALSHI_API_KEY=your_key
export KALSHI_SECRET_KEY=your_secret

# Run analysis
python main.py --category inflation --days 7 --window 24

# View results
cat output/*_summary.txt
```

## Command Line Options

```bash
python main.py --help

Options:
  --category {inflation|fed_rates|recession|unemployment}
  --days DAYS              (default: 7)
  --window WINDOW          (default: 24, in hours)
  --mock                   (use synthetic data)
```

## Python API

```python
from main import SentimentMarketPipeline

# Create pipeline
pipeline = SentimentMarketPipeline(use_mock_data=True)

# Run analysis
results = pipeline.run_full_analysis(
    category="inflation",
    sentiment_window_hours=24,
    days_back=7
)

# Access results
for market, data in results.items():
    corr = data['signal_strength']['pearson_correlation']
    lag = data['lag_analysis']['lag_hours'].iloc[0]
    print(f"{market}: r={corr:.3f}, lag={lag}h")
```

## File Structure

```
src/
├── config.py              # Configuration & constants
├── logger.py              # Logging setup
├── news_collector.py      # News API integration
├── sentiment_analyzer.py  # VADER/FinBERT sentiment
├── market_data.py         # Kalshi market data
├── time_series.py         # Correlation analysis
├── visualization.py       # Plots & reports
└── utils.py               # Database & utilities

main.py                    # Main CLI
run_example.py             # Quick example
requirements.txt           # Dependencies

data/                      # Created automatically
├── market_sentiment.db    # SQLite cache

output/                    # Created automatically
├── *.png                  # Generated plots
└── *.txt                  # Summary reports

logs/                      # Created automatically
└── *.log                  # Execution logs
```

## Common Tasks

### Fetch News
```python
from src.news_collector import NewsCollector
collector = NewsCollector(api_key="YOUR_KEY")
news = collector.fetch_macro_news("inflation")
print(f"Fetched {len(news)} articles")
```

### Compute Sentiment
```python
from src.sentiment_analyzer import SentimentAnalyzer
analyzer = SentimentAnalyzer(model_type="vader")
news = analyzer.analyze_dataframe(news)
agg = analyzer.aggregate_sentiment(news, window_hours=24)
print(agg[['timestamp', 'mean_sentiment']].head())
```

### Fetch Market Data
```python
from src.market_data import KalshiMarketCollector
collector = KalshiMarketCollector(api_key="YOUR_KEY")
prices = collector.fetch_market_prices("CPI-INFLATION-2024-04")
print(prices[['timestamp', 'mid_price']].head())
```

### Analyze Correlation
```python
from src.time_series import TimeSeriesAnalyzer
analyzer = TimeSeriesAnalyzer()
aligned = analyzer.align_timeseries(sentiment, prices)
corr = analyzer.compute_correlation(aligned)
print(f"Correlation: {corr:.3f}")

lags = analyzer.lag_analysis(aligned)
print(lags[['lag_hours', 'correlation']].head())
```

### Create Plots
```python
from src.visualization import TimeSeriesVisualizer
viz = TimeSeriesVisualizer()
viz.plot_sentiment_timeline(sentiment, save_as="sentiment.png")
viz.plot_market_probability(prices, save_as="market.png")
viz.plot_aligned_series(aligned, save_as="aligned.png")
viz.plot_lag_analysis(lags, save_as="lags.png")
```

## Output Interpretation

### Correlation Levels
- **r > 0.5**: Strong correlation
- **r = 0.3-0.5**: Moderate correlation
- **r = 0.1-0.3**: Weak correlation
- **r < 0.1**: Very weak/no correlation

### Significance
- **p < 0.05**: Statistically significant ✓
- **p ≥ 0.05**: Not significant

### Lag Interpretation
- **Negative lag**: Sentiment leads (predictive!)
- **Positive lag**: Price leads sentiment (reactive)
- **0 lag**: Concurrent relationship

## Configuration

### Change Sentiment Window
```python
# config.py
SENTIMENT_WINDOW_HOURS = 6  # Instead of 24
```

### Switch to FinBERT (More Accurate)
```python
# config.py
SENTIMENT_MODEL = "finbert"

# Install: pip install transformers torch
```

### Add New Market
```python
# config.py
KALSHI_MARKETS["tech"] = ["NVDA-EARNINGS-2024-Q3"]
MACRO_KEYWORDS["tech"] = ["nvidia", "gpu", "tech"]
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| `VADER lexicon not found` | `python -c "import nltk; nltk.download('vader_lexicon')"` |
| No news fetched | Check `NEWSAPI_KEY` in `.env` |
| No market data | Check `KALSHI_API_KEY` and market slugs |
| Low correlation | Use FinBERT, increase window, extend data range |
| Out of memory | Use VADER instead of FinBERT, reduce days |

## Performance Tips

| Optimization | Effect |
|--------------|--------|
| Use VADER over FinBERT | 20x faster |
| Use mock data | 100x faster (testing) |
| Reduce window size | Faster aggregation |
| Cache results | Avoid API calls |
| Batch processing | 2-3x faster |

## Key Metrics

**What to Look For:**

1. **Correlation (r)**
   - Quantifies linear relationship
   - Range: -1 to 1
   - Significant if p < 0.05

2. **P-value**
   - Probability result is random
   - < 0.05 = significant
   - > 0.05 = likely noise

3. **Optimal Lag**
   - How many hours sentiment leads/lags price
   - Negative = sentiment predicts
   - Positive = price leads reaction

4. **R-squared**
   - Variance explained by correlation
   - 0.25 (r=0.5) = 25% explained
   - 0.64 (r=0.8) = 64% explained

## Documentation

| File | Purpose |
|------|---------|
| `README.md` | Complete user guide (1000 lines) |
| `ARCHITECTURE.md` | System design & data flow (800 lines) |
| `SETUP.md` | Installation & troubleshooting (600 lines) |
| `PROJECT_SUMMARY.md` | Project overview & roadmap (500 lines) |

## Getting Started Checklist

- [ ] Install Python 3.8+
- [ ] Create virtual environment
- [ ] Install requirements
- [ ] Download VADER lexicon
- [ ] Run `python run_example.py`
- [ ] Review output plots
- [ ] Configure `.env` with API keys
- [ ] Run `python main.py --category inflation`
- [ ] Explore results in `output/`
- [ ] Customize for your analysis

## API Rate Limits

- **NewsAPI Free**: 100 requests/day
- **NewsAPI Paid**: Unlimited
- **Kalshi**: Contact for details

System auto-retries with backoff on rate limits.

## Supported Markets

### Inflation
- CPI (Consumer Price Index)
- Core Inflation
- Producer Price Index

### Fed Rates
- FOMC Decisions
- Interest Rate Decisions
- Forward Guidance

### Recession
- Recession Probability
- Yield Curve Inversion
- GDP Growth

### Unemployment
- Unemployment Rate
- Job Creation
- Labor Force Changes

## Example Output

```
Market: CPI-INFLATION-2024-04
  Pearson Correlation:        0.4264
  P-value:                    0.0023
  Significant (p<0.05):       True
  R-squared:                  0.1818
  Observations:               84

  Lag Analysis (Max Correlation):
    Optimal lag:              -6 hours
    Correlation at lag:       0.5126
    Interpretation:           Sentiment leads price by 6 hours
```

## Next Steps

1. Run `python run_example.py` to see it work
2. Read README.md for full documentation
3. Configure API keys in `.env`
4. Start analyzing real markets!

---

**Need Help?**
- Check README.md for detailed docs
- Review logs/ for error details
- See SETUP.md for troubleshooting
- Modify config.py for customization

**Ready to analyze?** Run:
```bash
python run_example.py
```
