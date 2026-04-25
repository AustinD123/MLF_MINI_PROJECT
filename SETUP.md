# Setup Guide - Getting Started

## Prerequisites

- **Python**: 3.8 or higher
- **pip**: Package manager (comes with Python)
- **Git**: For version control (optional)

Check your versions:
```bash
python --version
pip --version
```

---

## Installation Options

### Option 1: Quick Start (Recommended for Testing)

1. **Clone/Extract the project**
   ```bash
   cd sentiment_market_analyzer
   ```

2. **Create virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download VADER lexicon** (one-time)
   ```bash
   python -c "import nltk; nltk.download('vader_lexicon')"
   ```

5. **Run example with mock data (no API keys needed!)**
   ```bash
   python run_example.py
   ```

   **Output**: Check `output/` folder for plots

### Option 2: With API Keys (Real Data)

1. **Get free API keys**

   - **NewsAPI**: Go to https://newsapi.org
     - Sign up for free account
     - Copy API key
   
   - **Kalshi**: Go to https://kalshi.com/api
     - Create account & enable API access
     - Generate API credentials

2. **Create `.env` file** in project root:
   ```bash
   # .env (DO NOT COMMIT THIS FILE)
   NEWSAPI_KEY=your_newsapi_key_here
   KALSHI_API_KEY=your_kalshi_api_key_here
   KALSHI_SECRET_KEY=your_kalshi_secret_key_here
   ```

3. **Run analysis**
   ```bash
   python main.py --category inflation --days 7
   ```

### Option 3: Advanced Setup (FinBERT Model)

For higher accuracy sentiment analysis using FinBERT (slower but more accurate):

```bash
# Basic installation
pip install -r requirements.txt

# Add FinBERT & PyTorch
pip install transformers torch

# Verify installation
python -c "from transformers import AutoTokenizer; print('FinBERT ready')"
```

Then use in code:
```python
from src.sentiment_analyzer import SentimentAnalyzer
analyzer = SentimentAnalyzer(model_type="finbert")
```

> **Note**: FinBERT inference is slower (~200ms per article). For large datasets, use VADER (default).

---

## Post-Installation Verification

Run the verification script to ensure everything is working:

```bash
python -c "
from src.news_collector import NewsCollector
from src.sentiment_analyzer import SentimentAnalyzer
from src.market_data import MockKalshiDataGenerator
from src.time_series import TimeSeriesAnalyzer
from src.visualization import TimeSeriesVisualizer
print('✓ All modules imported successfully')
"
```

If you see `✓ All modules imported successfully`, you're ready!

---

## Configuration Guide

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
# Required for real data
NEWSAPI_KEY=your_key
KALSHI_API_KEY=your_key
KALSHI_SECRET_KEY=your_secret

# Optional: Customize behavior
LOG_LEVEL=INFO
SENTIMENT_MODEL=vader
```

Load in Python:
```python
from dotenv import load_dotenv
load_dotenv()
```

### 2. Modify Configuration (src/config.py)

**Change sentiment analysis window:**
```python
SENTIMENT_WINDOW_HOURS = 6  # Instead of 24
```

**Add new markets:**
```python
KALSHI_MARKETS["tech_stocks"] = ["NVDA-CLOSING-2024-Q4"]
MACRO_KEYWORDS["tech_stocks"] = ["nvidia", "gpu", "tech"]
```

**Switch to FinBERT:**
```python
SENTIMENT_MODEL = "finbert"  # Instead of "vader"
```

**Change correlation window:**
```python
ROLLING_CORRELATION_WINDOW_DAYS = 7  # Instead of 14
```

---

## Directory Structure After Setup

```
sentiment_market_analyzer/
├── src/                          # Core modules (installed)
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   ├── news_collector.py
│   ├── sentiment_analyzer.py
│   ├── market_data.py
│   ├── time_series.py
│   ├── visualization.py
│   └── utils.py
├── main.py                       # Main script
├── run_example.py                # Quick example
├── requirements.txt              # Dependencies
├── README.md                      # Documentation
├── ARCHITECTURE.md               # System design
├── SETUP.md                       # This file
├── .env                          # API keys (create manually)
├── .gitignore                    # Git ignore
│
├── data/                         # Created automatically
│   └── market_sentiment.db       # SQLite database (auto-created)
│
├── output/                       # Created automatically
│   ├── sentiment_timeline.png
│   ├── market_price.png
│   ├── aligned.png
│   ├── rolling_correlation.png
│   ├── lag_analysis.png
│   ├── scatter.png
│   └── summary.txt
│
├── logs/                         # Created automatically
│   ├── news_collector_20240415.log
│   ├── sentiment_analyzer_20240415.log
│   ├── time_series_20240415.log
│   └── main_20240415.log
│
└── venv/                         # Virtual environment (created)
    ├── bin/                      # or Scripts/ on Windows
    ├── lib/
    └── pyvenv.cfg
```

---

## Troubleshooting Installation

### Problem: `ModuleNotFoundError: No module named 'vader'`

**Solution:**
```bash
pip install vaderSentiment nltk
python -c "import nltk; nltk.download('vader_lexicon')"
```

### Problem: `pip: command not found`

**Solution**: Use Python module:
```bash
python -m pip install -r requirements.txt
```

### Problem: Virtual environment won't activate

**Windows:**
```bash
# Try PowerShell if cmd fails
powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
# Use bash instead of zsh
bash
source venv/bin/activate
```

### Problem: `VADER_LEXICON_PATH` not found

**Solution:**
```python
import nltk
nltk.download('vader_lexicon', download_dir='/path/to/data')
```

### Problem: `ImportError` for `newsapi` module

**Solution:**
```bash
pip install newsapi requests
```

### Problem: Low sentiment accuracy with VADER

**Solution**: Switch to FinBERT (more accurate for financial news):
```bash
pip install transformers torch
# Then set in config.py: SENTIMENT_MODEL = "finbert"
```

---

## Running the Application

### Command Line Basics

**Test with mock data (no API keys needed):**
```bash
python main.py --mock --category inflation
```

**Analyze real data:**
```bash
python main.py --category inflation --days 7 --window 24
```

**See all options:**
```bash
python main.py --help
```

**Full example output:**
```
usage: main.py [-h] [--category {inflation,fed_rates,recession,unemployment}]
               [--days DAYS] [--window WINDOW] [--mock]

optional arguments:
  -h, --help            show this help message and exit
  --category {inflation,fed_rates,recession,unemployment}
                        Macro category to analyze (default: inflation)
  --days DAYS           Days of history to analyze (default: 7)
  --window WINDOW       Sentiment aggregation window hours (default: 24)
  --mock                Use mock data for testing (default: False)
```

### Jupyter Notebook Usage

```python
from main import SentimentMarketPipeline

# Initialize
pipeline = SentimentMarketPipeline()

# Run analysis
results = pipeline.run_full_analysis(
    category="inflation",
    sentiment_window_hours=24,
    days_back=7
)

# Access results
for market, data in results.items():
    print(f"Market: {market}")
    print(f"Correlation: {data['signal_strength']['pearson_correlation']:.3f}")
```

---

## API Rate Limits

### NewsAPI

- **Free Tier**: 100 requests/day, 30-day lookback
- **Paid Tier**: Unlimited requests, full history

### Kalshi

- **Free Tier**: Limited, contact for production access
- **Paid Tier**: Unlimited with rate limiting

### Rate Limiting in Code

The system automatically handles rate limiting:
```python
import time
from src.config import RETRY_DELAY_SECONDS, MAX_RETRIES

# Automatic retry with exponential backoff
for attempt in range(MAX_RETRIES):
    try:
        response = collector.fetch_news(...)
        break
    except:
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY_SECONDS)
```

---

## Database Setup

### Automatic Setup

The database is created automatically on first run:
```bash
python main.py --mock  # Creates data/market_sentiment.db
```

### Manual Inspection

View database contents:
```bash
# Install SQLite tools
pip install sqlite3

# Open database
sqlite3 data/market_sentiment.db

# View tables
.tables

# Browse news table
SELECT * FROM news LIMIT 5;

# Check market prices
SELECT * FROM market_prices LIMIT 5;

# Exit
.quit
```

### Backing Up Data

```bash
# Copy database
cp data/market_sentiment.db data/market_sentiment_backup.db

# Or export to CSV
sqlite3 data/market_sentiment.db \
  "SELECT * FROM news" | OUT TO 'news_backup.csv'
```

---

## Performance Tuning

### For Large Datasets (1 month+ of data)

1. **Increase batch size:**
   ```python
   # config.py
   NEWS_BATCH_SIZE = 500  # Instead of 100
   ```

2. **Enable parallel processing:**
   ```python
   # config.py
   BATCH_PROCESSING_ENABLED = True
   PARALLEL_WORKERS = 8  # Adjust based on CPU cores
   ```

3. **Use VADER instead of FinBERT:**
   ```python
   # VADER: ~1000 articles/min
   # FinBERT: ~50 articles/min
   SENTIMENT_MODEL = "vader"
   ```

### For GPU Acceleration (FinBERT)

```bash
# Install GPU-enabled PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify GPU
python -c "import torch; print(torch.cuda.is_available())"
```

---

## Next Steps

1. **Read the README** for full feature documentation
2. **Review ARCHITECTURE.md** for system design details
3. **Run run_example.py** to see the system in action
4. **Explore output/ folder** to see generated plots
5. **Modify config.py** to customize for your use case

---

## Support & Debugging

### Enable Verbose Logging

```python
# In config.py
LOG_LEVEL = "DEBUG"  # Instead of "INFO"
```

### Check Logs

```bash
# See recent logs
tail -f logs/main_*.log

# Check for errors
grep ERROR logs/*.log
```

### Debug Mode

```python
from src.news_collector import NewsCollector
from src.logger import setup_logger

logger = setup_logger("debug")

# Add debug statements
collector = NewsCollector()
news = collector.fetch_news("inflation")
logger.debug(f"Fetched {len(news)} articles")
```

---

## Uninstall / Clean Up

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf venv/  # macOS/Linux
rmdir /s venv  # Windows

# Clean up compiled files
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Keep data (optional):
rm -rf data/  # Remove database
rm -rf output/  # Remove plots
rm -rf logs/  # Remove logs
```

---

## Getting Help

**Common Issues**

- Check logs in `logs/` folder
- Review error messages (usually very descriptive)
- Check ARCHITECTURE.md for system design
- Review config.py for parameter meanings

**API Key Issues**

- Verify key is correctly copied (no extra spaces)
- Check rate limits: https://newsapi.org/account
- For Kalshi: Contact support (limited free tier)

**Data Issues**

- Ensure date range has news availability
- Check if markets are actively trading
- Try `--mock` flag for testing

---

## Happy Analyzing! 📊

You're all set to explore sentiment-market correlations. Start with:
```bash
python run_example.py
```

Then explore the output plots and reports!
