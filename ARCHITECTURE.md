# System Architecture & Design Documentation

## Overview

The Sentiment-Market Analyzer is built on a modular, layered architecture with clear separation of concerns. This enables easy testing, replacement of components, and clear data flow.

---

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        USER LAYER                                  │
│  Command-line CLI (main.py) | Jupyter Notebooks | Custom Scripts  │
└────────────────┬───────────────────────────────────────────────────┘
                 │
┌────────────────▼───────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                             │
│  Pipeline: coordinate data flows, manage dependencies              │
│  - SentimentMarketPipeline (main.py::main_orchestrator)            │
└────────────────┬───────────────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┬──────────────┐
    │                         │              │
┌───▼─────────────┐ ┌────────▼────────┐ ┌───▼─────────────┐
│ DATA COLLECTION │ │  PROCESSING     │ │  STORAGE LAYER  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
    │                         │              │
    ├─ NewsCollector     ├─ SentimentParser  ├─ DatabaseMgr
    └─ KalshiMarket      ├─ MarketProcessor  ├─ Caching
       Collector         └─ TimeSeriesAgg    └─ Logging


    ┌─────────────────┬──────────────────┬─────────────────┐
    │    ANALYSIS     │   VISUALIZATION  │   UTILITIES     │
    ├─────────────────┼──────────────────┼─────────────────┤
    │ TimeSeriesAnal  │ TimeSeriesViz    │ DatabaseMgr     │
    │ - Correlation   │ - Plot types     │ Normalization   │
    │ - Lag analysis  │ - Reporting      │ Error handling  │
    │ - Causality     │ - Export         │ Logging         │
    └─────────────────┴──────────────────┴─────────────────┘
```

---

## Module Dependency Graph

```
┌─────────────┐
│  config.py  │ ◄─── All modules import from here
└──────┬──────┘
       │
       ├────────────────────────────────────────────────────────┐
       │                                                        │
       ▼                    ▼                    ▼
┌────────────────┐ ┌─────────────────┐ ┌──────────────────┐
│  logger.py     │ │  news_collector │ │  market_data.py  │
└────────────────┘ │     .py         │ └──────────────────┘
                   └────────┬────────┘          │
                            │                  │
                            ▼                  ▼
                   ┌─────────────────────────────────────┐
                   │ sentiment_analyzer.py               │
                   │ - analyze_text()                    │
                   │ - analyze_dataframe()               │
                   │ - aggregate_sentiment()             │
                   └────────────┬────────────────────────┘
                                │
                                ▼
                   ┌─────────────────────────────────────┐
                   │ time_series.py                      │
                   │ - align_timeseries()                │
                   │ - compute_correlations()            │
                   │ - lag_analysis()                    │
                   └────────────┬────────────────────────┘
                                │
                                ▼
                   ┌─────────────────────────────────────┐
                   │ visualization.py                    │
                   │ - plot_* methods                    │
                   │ - create_summary_report()           │
                   └─────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────┐
    │ utils.py (used by all)                               │
    │ - DatabaseManager()                                  │
    │ - normalize_series()                                 │
    │ - resample_dataframe()                               │
    └──────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

### Complete Pipeline Flow

```
STEP 1: NEWS COLLECTION
┌─────────────────────────────────────────────────┐
│ NewsAPI Endpoint (https://newsapi.org/v2/...)   │
└────────────────┬────────────────────────────────┘
                 │ requests.get()
                 ▼
        ┌────────────────────┐
        │ NewsCollector      │
        │  - fetch_news()    │
        │  - deduplicate()   │
        │  - filter_sources()│
        └────────┬───────────┘
                 │
        Raw DataFrame:
        [title, url, source, publishedAt, author, image]
                 │
                 ▼
        ┌────────────────────┐
        │ Database Cache     │
        │ (SQLite: news)     │
        └────────────────────┘


STEP 2: SENTIMENT ANALYSIS
        ┌────────────────────────┐
        │ Extract: title column  │
        └────────────┬───────────┘
                     │
          ┌──────────▼──────────┐
          │ SentimentAnalyzer   │
          │ - VADER / FinBERT   │
          └──────────┬──────────┘
                     │
        Per-article scores:
        [polarity (-1 to 1), label, confidence]
                     │
                     ▼
        ┌────────────────────────────────┐
        │ Aggregate over time windows    │
        │ (hourly → daily aggregation)   │
        └────────────┬───────────────────┘
                     │
        Aggregated DataFrame:
        [timestamp, mean_sentiment, std_sentiment, 
         positive_count, negative_count, neutral_count,
         article_count]
                     │
                     ▼
        ┌────────────────────────────┐
        │ Database Cache             │
        │ (SQLite: sentiment_agg)    │
        └────────────────────────────┘


STEP 3: MARKET DATA COLLECTION
┌──────────────────────────────────────────────────┐
│ Kalshi API (https://api.kalshi.com/trade-api/...) │
└─────────────────┬──────────────────────────────┘
                  │ requests.get() with auth headers
                  ▼
        ┌────────────────────────┐
        │ KalshiMarketCollector  │
        │  - fetch_prices()      │
        │  - detect_jumps()      │
        │  - compute_changes()   │
        └────────────┬───────────┘
                     │
        Market Price DataFrame:
        [timestamp, yes_price, no_price, mid_price, volume]
                     │
                     ▼
        ┌────────────────────────────┐
        │ Resample to regular freq   │
        │ (e.g., hourly interval)    │
        │ [forward-fill missing]     │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ Database Cache             │
        │ (SQLite: market_prices)    │
        └────────────────────────────┘


STEP 4: TIME SERIES ALIGNMENT
        ┌────────────────┐
        │ Agg Sentiment  │
        └────────┬───────┘
                 │
         ┌───────▼────────┐
         │ TimeSeriesAnal │
         │ align_ts()     │
         └───────┬────────┘
                 │
        ┌────────▼────────┐
        │ Market Prices   │
        └────────────────┘
                 │
        Aligned DataFrame:
        [timestamp, mean_sentiment, mid_price]
        (merged on nearest timestamp, NaN removed)


STEP 5: CORRELATION ANALYSIS
        ┌────────────┐
        │ Aligned TS │
        └─────┬──────┘
              │
      ┌───────▼────────┐
      │ Compute:       │
      │ - Pearson r    │
      │ - p-value      │
      │ - R-squared    │
      │ - Spearman r   │
      └───────┬────────┘
              │
      ┌───────▼────────┐
      │ Rolling Corr   │
      │ (14-day window)│
      └───────┬────────┘
              │
      ┌───────▼────────┐
      │ Lag Analysis   │
      │ (varies lag)   │
      └───────┬────────┘
              │
      ┌───────▼────────┐
      │ Granger Test   │
      │ (if available) │
      └────────────────┘


STEP 6: VISUALIZATION & REPORTING
┌───────────────────────────────────────┐
│ Analysis Results (Dict of metrics)    │
└───────┬───────────────────────────────┘
        │
    ┌───▼───────────────────────────┐
    │ TimeSeriesVisualizer          │
    │ - plot_sentiment_timeline()   │
    │ - plot_market_probability()   │
    │ - plot_aligned_series()       │
    │ - plot_rolling_correlation()  │
    │ - plot_lag_analysis()         │
    │ - plot_scatter_correlation()  │
    └───┬───────────────────────────┘
        │
    ┌───▼──────────────────────────────┐
    │ OUTPUT/ (high-res PNG plots)     │
    │ - sentiment_timeline.png         │
    │ - market_price.png               │
    │ - aligned_series.png             │
    │ - rolling_correlation.png        │
    │ - lag_analysis.png               │
    │ - scatter.png                    │
    │ - summary.txt (text report)      │
    └──────────────────────────────────┘
```

---

## Class Architecture

### NewsCollector
```
NewsCollector
├── __init__(api_key)
├── fetch_news(query, days_back, sort_by) → DataFrame
├── fetch_macro_news(category) → DataFrame
├── fetch_all_categories() → Dict[str, DataFrame]
├── filter_by_source_reliability(df) → DataFrame
└── deduplicate_articles(df, similarity) → DataFrame
```

### SentimentAnalyzer
```
SentimentAnalyzer
├── __init__(model_type: "vader" | "finbert")
├── analyze_text(text) → (polarity, label, confidence)
├── analyze_headlines(List[str]) → DataFrame
├── analyze_dataframe(df, text_column) → DataFrame
│   (adds: sentiment_polarity, sentiment_label, sentiment_confidence)
└── aggregate_sentiment(df, time_col, window_hours) → DataFrame
    (returns: timestamp, mean_sentiment, median_sentiment, std_sentiment,
              positive_count, negative_count, neutral_count)
```

### KalshiMarketCollector
```
KalshiMarketCollector
├── __init__(api_key)
├── fetch_market_prices(market_slug, days_back) → DataFrame
├── fetch_market_info(market_slug) → Dict
├── fetch_all_markets(markets_dict) → Dict[str, DataFrame]
├── compute_probability_changes(df, window_min) → DataFrame
├── detect_price_jumps(df, threshold_pct) → DataFrame
├── resample_prices(df, freq) → DataFrame
└── MockKalshiDataGenerator
    └── generate_synthetic_prices(...) → DataFrame
```

### TimeSeriesAnalyzer
```
TimeSeriesAnalyzer (all static methods)
├── align_timeseries(sent_df, market_df) → DataFrame
├── compute_rolling_correlation(df, window_days) → DataFrame
├── lag_analysis(df, max_lag_hours, lag_step) → DataFrame
├── detect_sentiment_spikes(df, threshold_std) → DataFrame
├── detect_event_pairs(spikes, jumps, time_window) → DataFrame
├── compute_granger_causality(df, max_lag) → Dict
└── compute_signal_strength(df) → Dict
```

### TimeSeriesVisualizer
```
TimeSeriesVisualizer
├── __init__(output_dir)
├── save_figure(fig, filename) → str
├── plot_sentiment_timeline(...) → Figure
├── plot_market_probability(...) → Figure
├── plot_aligned_series(...) → Figure
├── plot_rolling_correlation(...) → Figure
├── plot_lag_analysis(...) → Figure
├── plot_scatter_correlation(...) → Figure
├── plot_sentiment_breakdown(...) → Figure
└── create_summary_report(...) → str
```

---

## Configuration Management

```
config.py
├── API Credentials
│   ├── NEWSAPI_KEY
│   ├── KALSHI_API_KEY
│   ├── KALSKI_SECRET_KEY
│
├── Keywords & Markets
│   ├── MACRO_KEYWORDS dict
│   │   ├── "inflation": ["inflation", "CPI", ...]
│   │   ├── "fed_rates": ["fed", "interest rate", ...]
│   │   ├── "recession": [...]
│   │   └── "unemployment": [...]
│   └── KALSHI_MARKETS dict
│       ├── "inflation": ["CPI-INFLATION-2024-04", ...]
│       ├── "fed_rates": [...]
│       ├── "recession": [...]
│       └── "unemployment": [...]
│
├── Model Parameters
│   ├── SENTIMENT_MODEL: "vader" | "finbert"
│   ├── SENTIMENT_WINDOW_HOURS: 24
│   ├── MIN_HEADLINES_PER_WINDOW: 3
│   └── VADER_NEUTRAL_THRESHOLD: 0.1
│
├── Market Data Parameters
│   ├── MARKET_PRICE_INTERVAL_MINUTES: 15
│   ├── MARKET_PRICE_LOOKBACK_DAYS: 30
│
├── Analysis Parameters
│   ├── ROLLING_SENTIMENT_WINDOW_HOURS: 24
│   ├── ROLLING_CORRELATION_WINDOW_DAYS: 14
│   ├── MAX_LAG_HOURS: 72
│   ├── LAG_STEP_HOURS: 6
│   └── CORRELATION_MIN_THRESHOLD: 0.3
│
├── I/O Parameters
│   ├── LOG_DIR: "logs/"
│   ├── OUTPUT_DIR: "output/"
│   ├── DATA_DIR: "data/"
│   └── DB_PATH: "data/market_sentiment.db"
│
└── Performance Tuning
    ├── BATCH_PROCESSING_ENABLED: True
    ├── PARALLEL_WORKERS: 4
    ├── MAX_RETRIES: 3
    └── RETRY_DELAY_SECONDS: 5
```

---

## Database Schema

### SQLite Database Structure

```
database: market_sentiment.db

TABLE: news
├── id (INTEGER PRIMARY KEY)
├── title (TEXT NOT NULL)
├── url (TEXT UNIQUE)
├── source (TEXT)
├── published_at (TIMESTAMP)
├── fetched_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
├── sentiment_polarity (REAL)
├── sentiment_label (TEXT)
└── sentiment_confidence (REAL)

TABLE: market_prices
├── id (INTEGER PRIMARY KEY)
├── market_slug (TEXT NOT NULL)
├── timestamp (TIMESTAMP NOT NULL)
├── mid_price (REAL)
├── yes_price (REAL)
├── no_price (REAL)
├── volume (REAL)
├── fetched_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
└── UNIQUE(market_slug, timestamp)

TABLE: analysis_results
├── id (INTEGER PRIMARY KEY)
├── analysis_type (TEXT)
├── market_slug (TEXT)
├── correlation (REAL)
├── pvalue (REAL)
├── created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
└── metadata (TEXT)
```

---

## Error Handling & Resilience

```
Error Handling Strategy:
├── API Failures
│   ├── Retry with exponential backoff (max 3 attempts)
│   ├── Fallback to cached data if available
│   └── Log warnings, continue with available data
│
├── Data Quality Issues
│   ├── Skip malformed articles
│   ├── Handle missing/NaN values
│   │   └── Forward-fill for time series
│   └── Validate data types
│
├── Sentiment Analysis Errors
│   ├── Default to neutral (0.0) on parse failure
│   ├── Graceful degradation for unsupported languages
│   └── Log and skip problematic articles
│
├── Correlation Failures
│   ├── Return NaN if insufficient data
│   ├── Alert if minimum sample size not met
│   └── Recommend more data
│
└── File I/O Errors
    ├── Auto-create directories
    ├── Atomic writes with temp files
    └── Preserve previous results
```

---

## Performance Considerations

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| fetch_news() | O(n) | Linear in API results |
| analyze_text() VADER | O(m) | m = tokens, very fast |
| analyze_text() FinBERT | O(m log m) | Transformer inference |
| aggregate_sentiment() | O(n log n) | Groupby + aggregation |
| align_timeseries() | O(n log n) | Merge-asof with index |
| rolling_correlation() | O(n * w²) | w = window size |
| lag_analysis() | O(n * L) | L = max lag iterations |
| plotting | O(n) | Linear in data points |

### Memory Usage

- **News articles**: ~2KB per article (title, source, URL)
- **Sentiment scores**: ~100 bytes per article
- **Market prices**: ~100 bytes per price tick
- **Aligned time series**: ~500 bytes per data point

**Typical footprint for 1 week analysis:**
- ~500 articles × 2KB = 1 MB
- Processed data + analysis results = 5-10 MB
- Output plots (PNG) = 2-5 MB per plot × 6 plots = 12-30 MB
- **Total: ~50-60 MB**

### Optimization Tips

1. **Query Optimization**
   - Use indexed lookups for database queries
   - Batch API requests where possible
   - Cache frequently accessed results

2. **Vectorization**
   - Use NumPy/Pandas operations (avoid Python loops)
   - Vectorize sentiment analysis

3. **Parallel Processing**
   - Multi-threading for I/O-bound tasks (API calls)
   - Multi-processing for CPU-bound tasks (FinBERT)

---

## Testing Strategy

### Unit Tests (Not included but recommended)

```python
# tests/test_sentiment_analyzer.py
def test_analyze_text_positive():
    analyzer = SentimentAnalyzer("vader")
    polarity, label, conf = analyzer.analyze_text("Great news!")
    assert polarity > 0
    assert label == "positive"

def test_aggregate_sentiment():
    df = pd.DataFrame({...})
    agg = analyzer.aggregate_sentiment(df)
    assert len(agg) > 0
    assert "mean_sentiment" in agg.columns

# tests/test_correlation.py
def test_lag_analysis():
    aligned_df = pd.DataFrame({...})
    lags = TimeSeriesAnalyzer.lag_analysis(aligned_df)
    assert not lags.empty
    assert "lag_hours" in lags.columns
```

### Integration Tests

```python
# tests/test_pipeline.py
def test_full_pipeline():
    pipeline = SentimentMarketPipeline(use_mock_data=True)
    results = pipeline.run_full_analysis()
    assert "mock-market" in results
    assert "signal_strength" in results["mock-market"]
```

---

## Deployment Considerations

### Local Development
- Python 3.8+
- ~500 MB disk for analysis
- No GPU required (VADER)
- ~5 minutes per analysis cycle

### Cloud Deployment (AWS)
- Lambda for triggered analysis
- RDS for persistent database
- S3 for plot storage
- CloudWatch for monitoring

### Docker Containerization (Optional)

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py", "--category", "inflation"]
```

```bash
docker build -t sentiment-analyzer .
docker run -e NEWSAPI_KEY=xxx sentiment-analyzer
```

---

## Future Architecture Enhancements

### Planned Improvements
1. **Streaming Architecture**: Real-time sentiment updates
2. **Multi-Model Ensemble**: Combine multiple sentiment models
3. **Distributed Processing**: Spark for large-scale analysis
4. **Interactive Dashboard**: Streamlit web UI
5. **API Service**: FastAPI REST endpoint

### Scalability Path
```
Current Setup (1 analyst)
  ↓
Multi-user (SQL backend + API)
  ↓
Real-time streaming (Kafka + Spark)
  ↓
Enterprise analytics (Data warehouse + ML)
```

---

## Summary

The architecture prioritizes:
✅ **Modularity** - Each component is independent  
✅ **Clarity** - Clear data flow between stages  
✅ **Extensibility** - Easy to add new models/markets  
✅ **Robustness** - Error handling and retries  
✅ **Performance** - Vectorized operations, caching  

This design supports both rapid prototyping and production deployment.
