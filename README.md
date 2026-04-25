# Sentiment-Market Analyzer: News Sentiment vs Kalshi Predictions

A lightweight, research-grade Python framework for analyzing the correlation between financial news sentiment and prediction market probabilities on Kalshi.

## Project Overview

This system investigates whether macroeconomic news sentiment influences probability movements in Kalshi prediction markets. It combines NLP sentiment analysis with quantitative time series methods to:

- **Collect** financial news headlines from NewsAPI
- **Analyze** sentiment using VADER or FinBERT
- **Fetch** real-time prediction market data from Kalshi
- **Correlate** sentiment signals with probability changes
- **Visualize** relationships and generate actionable insights

### Key Features

✅ **Clean Modular Architecture** - Separated data collection, sentiment, market data, and analysis modules  
✅ **Multiple Sentiment Engines** - VADER (fast) or FinBERT (high-accuracy)  
✅ **Statistical Rigor** - Pearson/Spearman correlations, Granger causality, lag analysis  
✅ **Production-Ready** - Logging, error handling, database caching, rate limiting  
✅ **Publication-Quality Plots** - Time series, rolling correlations, scatter plots  
✅ **Fast Prototyping** - Mock data generation for testing without APIs  

---

## Project Structure

```
sentiment_market_analyzer/
├── src/
│   ├── config.py                 # Central configuration & constants
│   ├── logger.py                 # Logging setup
│   ├── news_collector.py         # News API integration
│   ├── sentiment_analyzer.py     # VADER/FinBERT sentiment scoring
│   ├── market_data.py            # Kalshi market data fetching
│   ├── time_series.py            # Correlation & lag analysis
│   ├── visualization.py          # Plotting & reporting
│   └── utils.py                  # Database & utility functions
├── main.py                       # Pipeline orchestrator
├── run_example.py                # Quick start example
├── requirements.txt              # Python dependencies
├── data/                         # Raw data cache
│   └── market_sentiment.db       # SQLite database
├── output/                       # Generated plots & reports
├── logs/                         # Execution logs
└── notebooks/                    # Jupyter notebooks (analysis, examples)
```

---

## Quick Start

### 1. Installation

```bash
# Clone or download the project
cd sentiment_market_analyzer

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```bash
NEWSAPI_KEY=your_newsapi_key_here
KALSHI_API_KEY=your_kalshi_key_here
KALSHI_SECRET_KEY=your_kalshi_secret_here
```

Get free API keys:
- **NewsAPI**: https://newsapi.org (free tier: 100 requests/day, 30-day lookback)
- **Kalshi**: https://kalshi.com/api (sign up for trading account)

### 3. Run Analysis with Mock Data (No API Keys Required)

```bash
# Quick test with synthetic market data
python main.py --mock --category inflation --days 7 --window 24
```

### 4. Run with Real Data

```bash
# Analyze inflation sentiment vs market probabilities
python main.py --category inflation --days 7 --window 24

# Other categories
python main.py --category fed_rates --days 14
python main.py --category recession --days 30
python main.py --category unemployment --days 7
```

**Output**: Check `output/` folder for plots and `logs/` for detailed execution logs.

---

## Architecture & Methodology

### System Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION LAYER                        │
├──────────────────────────┬──────────────────────────────────────┤
│   News Collection        │   Market Data Collection             │
│   - NewsAPI fetch        │   - Kalshi API integration           │
│   - Keyword filtering    │   - Price history aggregation        │
│   - Deduplication        │   - Volume tracking                  │
└──────────────────┬───────┴──────────────────┬────────────────────┘
                   │                          │
┌──────────────────▼──────────┐  ┌───────────▼──────────────────────┐
│  SENTIMENT ANALYSIS LAYER    │  │  MARKET DATA PREPROCESSING      │
├──────────────────────────────┤  ├────────────────────────────────┤
│ - VADER/FinBERT scoring     │  │ - Resampling to regular freq   │
│ - Per-article sentiment      │  │ - Detecting price jumps        │
│ - Aggregation over windows   │  │ - Computing probability changes│
│ - Confidence scoring         │  │ - Volume-weighted analysis    │
└──────────────────┬───────────┘  └────────────┬────────────────────┘
                   │                          │
                   └──────────────┬───────────┘
                                  │
                    ┌─────────────▼────────────────┐
                    │  TIME SERIES ALIGNMENT      │
                    ├─────────────────────────────┤
                    │ - Merge on common timestamps│
                    │ - Forward-fill missing data │
                    │ - Normalization             │
                    └────────────────┬────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
┌───────▼──────────┐  ┌──────────────▼───────┐  ┌──────────────────▼────┐
│ CORRELATION      │  │  LAG ANALYSIS        │  │ GRANGER CAUSALITY     │
│ - Pearson/       │  │ - Lead/lag periods   │  │ - Causality testing   │
│   Spearman       │  │ - Max correlation lag│  │ - Statistical rigor   │
│ - Rolling window │  │ - Direction testing  │  │ - p-value computation │
│ - Significance   │  │ - AIC/BIC ranking    │  │                       │
└────────┬─────────┘  └──────────┬───────────┘  └───────────┬────────────┘
         │                       │                          │
         └───────────────────────┼──────────────────────────┘
                                 │
                    ┌────────────▼──────────────┐
                    │  VISUALIZATION & REPORTING│
                    ├───────────────────────────┤
                    │ - Time series plots       │
                    │ - Correlation heatmaps    │
                    │ - Lag analysis charts     │
                    │ - Summary statistics      │
                    │ - Event detection alerts  │
                    └───────────────────────────┘
```

### Key Metrics

#### 1. **Sentiment Score** (Per Article)
- **Range**: [-1, 1] where -1 = very negative, 0 = neutral, +1 = very positive
- **Confidence**: [0, 1] based on analyzer strength
- **Label**: "positive", "negative", or "neutral"

#### 2. **Aggregated Sentiment** (Per Time Window)
```
Mean Sentiment = Average polarity of all headlines in window
Median Sentiment = Median polarity (robust to outliers)
Std Sentiment = Standard deviation (volatility)
Article Count = Total headlines in window
Composition = [Positive%, Negative%, Neutral%]
```

#### 3. **Market Signal** (Per Time Window)
```
Mid Price = (Yes Price + No Price) / 2  [Market probability]
Price Change = End Price - Start Price over window
Percentage Change = (Price Change / Start Price) * 100
Volume = Total contract volume traded
```

#### 4. **Correlation Metrics**
- **Pearson Correlation**: Linear relationship strength [-1, 1]
- **P-value**: Statistical significance (< 0.05 = significant)
- **R-squared**: Proportion of variance explained (0-1)
- **Spearman Correlation**: Rank-based (robust to outliers)

#### 5. **Lag Analysis**
- Tests if sentiment **leads** or **lags** price movement
- Negative lag: Sentiment changes before price (predictive signal)
- Positive lag: Price changes before sentiment (reactive market)
- Lag with maximum correlation = optimal prediction window

---

## Module Documentation

### 1. **config.py** - Configuration Management

Central repository for all parameters:

```python
from src.config import MACRO_KEYWORDS, KALSHI_MARKETS

# Keywords for each macro category
MACRO_KEYWORDS = {
    "inflation": ["inflation", "CPI", "consumer price"],
    "fed_rates": ["fed", "interest rate", "FOMC"],
    "recession": ["recession", "GDP", "downturn"],
}

# Markets to track
KALSHI_MARKETS = {
    "inflation": ["CPI-INFLATION-2024-04", "CORE-INFLATION-2024-Q2"],
    "fed_rates": ["FOMC-RATE-DEC-2024"],
}
```

### 2. **news_collector.py** - News Fetching

```python
from src.news_collector import NewsCollector

collector = NewsCollector(api_key="YOUR_KEY")

# Fetch by keyword
news_df = collector.fetch_news("inflation economy", days_back=7)

# Fetch by category
news_df = collector.fetch_macro_news("inflation")

# Deduplicate similar articles
news_df = collector.deduplicate_articles(news_df)

# Filter by trusted sources
news_df = collector.filter_by_source_reliability(news_df)

# Output columns:
# [title, description, source, publishedAt, url, author, image]
```

### 3. **sentiment_analyzer.py** - Sentiment Scoring

```python
from src.sentiment_analyzer import SentimentAnalyzer

# Initialize (VADER is fast, FinBERT is more accurate)
analyzer = SentimentAnalyzer(model_type="vader")

# Score single headline
polarity, label, confidence = analyzer.analyze_text(
    "Fed signals rate hikes, inflation concerns persist"
)
# Returns: (0.342, "positive", 0.89)

# Analyze dataframe
news_with_sentiment = analyzer.analyze_dataframe(news_df)
# Adds: [sentiment_polarity, sentiment_label, sentiment_confidence]

# Aggregate over time windows
agg_sentiment = analyzer.aggregate_sentiment(news_with_sentiment, window_hours=24)
# Returns: [timestamp, mean_sentiment, std_sentiment, positive_count, ...]
```

### 4. **market_data.py** - Market Data Fetching

```python
from src.market_data import KalshiMarketCollector

collector = KalshiMarketCollector(api_key="YOUR_KEY")

# Fetch price history
prices_df = collector.fetch_market_prices("CPI-INFLATION-2024-04", days_back=30)
# Columns: [timestamp, yes_price, no_price, mid_price, volume]

# Detect price jumps
jumps = collector.detect_price_jumps(prices_df, threshold_pct=2.0)

# Compute probability changes
changes = collector.compute_probability_changes(prices_df, window_minutes=60)
```

**Mock Data Generation** (for testing):

```python
from src.market_data import MockKalshiDataGenerator

# Generate synthetic geometric Brownian motion prices
prices_df = MockKalshiDataGenerator.generate_synthetic_prices(
    start_price=0.50,
    num_points=168,  # 1 week hourly
    volatility=0.02,
    drift=0.001
)
```

### 5. **time_series.py** - Correlation Analysis

```python
from src.time_series import TimeSeriesAnalyzer

analyzer = TimeSeriesAnalyzer()

# Align sentiment and market data
aligned = analyzer.align_timeseries(agg_sentiment, market_prices)

# Compute rolling correlation
rolling_corr = analyzer.compute_rolling_correlation(aligned, window_days=14)
# Columns: [timestamp, correlation, pvalue, significant]

# Lag analysis: sentiment -> price with time delays
lags = analyzer.lag_analysis(aligned, max_lag_hours=72)
# Output: correlation at each lag offset

# Detect sentiment spikes
spikes = analyzer.detect_sentiment_spikes(agg_sentiment, threshold_std=1.5)

# Match spikes to price jumps
pairs = analyzer.detect_event_pairs(spikes, price_jumps, time_window_hours=6)

# Granger causality testing
granger = analyzer.compute_granger_causality(aligned)

# Signal strength metrics
metrics = analyzer.compute_signal_strength(aligned)
# Returns: pearson_corr, r_squared, spearman_corr, change_correlation, ...
```

### 6. **visualization.py** - Plotting & Reporting

```python
from src.visualization import TimeSeriesVisualizer

viz = TimeSeriesVisualizer(output_dir="output/")

# Sentiment timeline
fig = viz.plot_sentiment_timeline(agg_sentiment, save_as="sentiment.png")

# Market probability timeline
fig = viz.plot_market_probability(prices_df, save_as="market.png")

# Dual time series
fig = viz.plot_aligned_series(aligned, save_as="aligned.png")

# Rolling correlation
fig = viz.plot_rolling_correlation(rolling_corr, save_as="correlation.png")

# Lag analysis bar chart
fig = viz.plot_lag_analysis(lag_df, save_as="lags.png")

# Scatter + regression
fig = viz.plot_scatter_correlation(aligned, save_as="scatter.png")

# Generate text report
report_path = viz.create_summary_report(metrics, lags, aligned)
```

---

## Example Workflows

### Example 1: Quick Analysis (5 minutes to first insights)

```python
from main import SentimentMarketPipeline

# Initialize with mock data (no API keys needed)
pipeline = SentimentMarketPipeline(use_mock_data=True)

# Run complete analysis
results = pipeline.run_full_analysis(category="inflation")

# Inspect results
for market, data in results.items():
    print(f"Market: {market}")
    print(f"  Correlation: {data['signal_strength']['pearson_correlation']:.3f}")
    print(f"  Best Lag: {data['lag_analysis']['lag_hours'].iloc[0]} hours")
```

### Example 2: Custom Analysis (Advanced)

```python
from src.news_collector import NewsCollector
from src.sentiment_analyzer import SentimentAnalyzer
from src.market_data import KalshiMarketCollector
from src.time_series import TimeSeriesAnalyzer
from src.visualization import TimeSeriesVisualizer

# Step 1: Collect news
collector = NewsCollector(api_key="YOUR_KEY")
news = collector.fetch_macro_news("fed_rates")
news = collector.deduplicate_articles(news)

# Step 2: Analyze sentiment
analyzer = SentimentAnalyzer(model_type="finbert")  # More accurate but slower
sentiment_agg = analyzer.aggregate_sentiment(
    analyzer.analyze_dataframe(news),
    window_hours=6  # 6-hour windows
)

# Step 3: Fetch market data
market_collector = KalshiMarketCollector(api_key="KALSHI_KEY")
prices = market_collector.fetch_market_prices("FOMC-RATE-DEC-2024")

# Step 4: Analyze
ts_analyzer = TimeSeriesAnalyzer()
aligned = ts_analyzer.align_timeseries(sentiment_agg, prices)
signal = ts_analyzer.compute_signal_strength(aligned)
lags = ts_analyzer.lag_analysis(aligned, max_lag_hours=48, lag_step_hours=2)

print(f"Correlation: {signal['pearson_correlation']:.4f}")
print(f"P-value: {signal['pearson_pvalue']:.6f}")

# Step 5: Visualize
viz = TimeSeriesVisualizer()
viz.plot_aligned_series(aligned, save_as="fed_rates_analysis.png")
viz.plot_lag_analysis(lags, save_as="fed_lags.png")
```

### Example 3: Scheduled Monitoring (Daily Updates)

```python
# scheduler.py - Run daily to track sentiment-market dynamics
import schedule
import time
from main import SentimentMarketPipeline

def daily_analysis():
    pipeline = SentimentMarketPipeline()
    results = pipeline.run_full_analysis(category="inflation", days_back=1)
    
    # Log findings
    for market, data in results.items():
        corr = data['signal_strength']['pearson_correlation']
        if abs(corr) > 0.5:
            print(f"STRONG link detected in {market}: r={corr:.3f}")

# Schedule daily at 9am
schedule.every().day.at("09:00").do(daily_analysis)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## Advanced Features

### Adding Custom Markets

Edit `src/config.py`:

```python
KALSHI_MARKETS = {
    "inflation": ["CPI-INFLATION-2024-04"],
    "tech_earnings": ["NVDA-EARNINGS-Q3-2024", "TSLA-EARNINGS-Q3-2024"],
}

MACRO_KEYWORDS = {
    "tech_earnings": ["nvidia earnings", "tesla earnings", "dividend"],
}
```

### Switching Sentiment Models

```python
# VADER (fast, good for financial text)
analyzer = SentimentAnalyzer(model_type="vader")

# FinBERT (slower, higher accuracy, trained on financial text)
analyzer = SentimentAnalyzer(model_type="finbert")
```

**FinBERT Installation:**
```bash
pip install transformers torch
```

### Granger Causality Testing

Test if sentiment **causally predicts** price movements (not just correlation):

```python
from src.time_series import TimeSeriesAnalyzer

granger_results = TimeSeriesAnalyzer.compute_granger_causality(
    aligned_df,
    max_lag=12
)

# Interpret results
if granger_results['sentiment_causes_price'][3]['significant']:
    print("Sentiment significantly Granger-causes price at 3-hour lag")
```

### Event Pair Detection

Find matching sentiment spikes with market price jumps:

```python
spikes = analyzer.detect_sentiment_spikes(sentiment_df, threshold_std=2.0)
jumps = market_collector.detect_price_jumps(prices_df, threshold_pct=3.0)

pairs = analyzer.detect_event_pairs(spikes, jumps, time_window_hours=4)
print(f"Found {len(pairs)} sentiment-price event pairs")
```

---

## Data Sources & APIs

### News APIs

| Provider | Free Tier | Lookback | Requests/Day | Coverage |
|----------|-----------|----------|--------------|----------|
| **NewsAPI** | 100 | 30 days | 100 | 50K+ sources |
| **GDELT** | Unlimited | 40+ years | Unlimited | 200+ languages |
| **Bing Search** | 50 | - | 50 | Web search |

### Market Data

| Source | Type | API Cost | Latency |
|--------|------|----------|---------|
| **Kalshi** | Prediction Markets | Free tier limited | ~Real-time |
| **PredictIt** | Prediction Markets | Paid | ~Real-time |
| **Polymarket** | Decentralized | Free | ~5 sec |

### Sentiment Analysis

| Model | Accuracy | Speed | Specialized |
|-------|----------|-------|-------------|
| **VADER** | 75-85% | Fast | Financial |
| **TextBlob** | 70-80% | Very Fast | General |
| **FinBERT** | 90%+ | Slow | Financial |
| **GPT-3.5** | 95%+ | Moderate | General (Expensive) |

---

## Model Improvement Ideas

### 1. **Enhanced Sentiment Analysis**
- [ ] Combine multiple models (ensemble)
- [ ] Fine-tune FinBERT on financial news
- [ ] Context-aware negation handling
- [ ] Sarcasm detection
- [ ] Event importance weighting

### 2. **Market Signal Processing**
- [ ] Multi-market aggregation (related markets)
- [ ] Volume-weighted price changes
- [ ] Microstructure analysis (bid-ask dynamics)
- [ ] Intraday seasonality adjustment
- [ ] Implied volatility tracking

### 3. **Advanced Time Series**
- [ ] Dynamic Time Warping (DTW) alignment
- [ ] Wavelet coherence analysis
- [ ] Vector Autoregression (VAR) models
- [ ] Hidden Markov Models (HMM)
- [ ] Transformer-based sequence models

### 4. **Production Features**
- [ ] Real-time sentiment streaming
- [ ] Automated alert system (Slack/Email)
- [ ] A/B testing framework for models
- [ ] Interactive web dashboard
- [ ] Historical backtesting engine

### 5. **Causal Analysis**
- [ ] Instrumental variable estimation
- [ ] Synthetic control methods
- [ ] Causal forests for heterogeneous effects
- [ ] Interrupted time series designs

---

## Troubleshooting

### Issue: "No API key provided"
**Solution**: Set environment variables or create `.env` file:
```bash
export NEWSAPI_KEY=your_key_here
```

### Issue: "VADER lexicon not found"
**Solution**: 
```bash
python -c "import nltk; nltk.download('vader_lexicon')"
```

### Issue: "Insufficient aligned data"
**Solution**: 
- Reduce time window aggregation (use 6H instead of 24H)
- Extend historical lookback period (`--days 30`)
- Check if market has sufficient trading volume

### Issue: Low correlation (r < 0.2)
**Solutions**:
- Use FinBERT for sentiment (higher accuracy)
- Test different lag periods
- Check for structural breaks in market
- Segment analysis by event types
- Consider using Spearman correlation (rank-based)

---

## Performance & Scaling

### Optimization Tips

1. **Batch Processing**: Process multiple articles simultaneously
2. **Caching**: Reuse computed sentiment scores (DB cache)
3. **Parallel Collection**: Fetch news + market data concurrently
4. **GPU Acceleration**: Use FinBERT with GPU for 10x speedup

### Deployment

**Local Machine**: Suitable for analysis up to 1 year of data

**Cloud Options** (for larger scale):
- AWS Lambda + RDS for event-driven updates
- Google Cloud Functions with Firestore caching
- Heroku for scheduled tasks

---

## METHODOLOGY DEEP DIVE

### Why These Metrics?

**Pearson Correlation**: Captures linear relationship; standard in finance  
**Granger Causality**: Tests if sentiment temporally precedes prices  
**Lag Analysis**: Identifies prediction windows (sentiment -> price delay)  
**Rolling Windows**: Detects regime changes and time-varying relationships  

### Statistical Validity

All tests use:
- p-values with Bonferroni correction (multiple comparisons)
- Robust standard errors (heteroskedasticity-consistent)
- Significance threshold: p < 0.05
- Minimum sample size: 30 observations

---

## Expected Output

Running the pipeline generates:

**Plots** (in `output/`):
- `*_sentiment_timeline.png` - Headline sentiment over time
- `*_market_price.png` - Market probability movements
- `*_aligned.png` - Dual time series overlay
- `*_rolling_correlation.png` - 14-day rolling correlation
- `*_lag_analysis.png` - Correlation by sentiment lag
- `*_scatter.png` - Sentiment vs price scatter with regression

**Reports** (in `output/`):
- `*_summary.txt` - Statistical metrics, p-values, interpretation

**Logs** (in `logs/`):
- `news_collector_YYYYMMDD.log` - API calls, articles fetched
- `sentiment_analyzer_YYYYMMDD.log` - Sentiment scores
- `time_series_YYYYMMDD.log` - Correlation computations
- `main_YYYYMMDD.log` - Overall pipeline execution

---

## Citation & References

**Research Areas Covered:**
- Sentiment analysis in finance (Tetlock 2007, Gentzkow & Shapiro 2010)
- Event study methodology (MacKinlay 1997)
- Granger causality frameworks (Granger 1969)
- Prediction markets (Wolfers & Zitzewitz 2004)

### Key Papers

1. Tetlock, P. C. (2007). Giving content to investor sentiment. *Journal of Finance*
2. Gentzkow, M., & Shapiro, J. M. (2010). What drives media slant? Evidence from US newspapers. *Econometrica*
3. Wolfers, J., & Zitzewitz, E. (2004). Prediction markets. *Journal of Economic Literature*

---

## License & Attribution

### License
MIT License - Use freely in academic and commercial projects

### Attribution
Please cite if used in research:
```bibtex
@software{sentiment_kalshi_2024,
  title={Sentiment-Market Analyzer},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/sentiment_market_analyzer}
}
```

---

## Next Steps & Roadmap

- [ ] **Version 2.0**: Multi-market ensemble predictions
- [ ] **Dashboard**: Real-time web UI (Streamlit)
- [ ] **Mobile App**: iOS/Android alerts
- [ ] **Paper**: Academic publication with backtesting results
- [ ] **API**: REST endpoint for prediction scores

---

## Contact & Support

**Questions?** Open an issue or check the documentation.

**Contributions**: Pull requests welcome!

**Have a question or found a bug?**  
Submit an issue with:
- Error message & traceback
- Steps to reproduce
- Python version & OS
- Requirements versions (`pip freeze`)

---

**Happy analyzing! 📊**
