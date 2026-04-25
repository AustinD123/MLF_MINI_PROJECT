"""
Configuration and constants for Sentiment Market Analyzer
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List

# ==================== API KEYS & CREDENTIALS ====================
# Store these in environment variables for security
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "YOUR_FINNHUB_API_KEY_HERE")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "YOUR_NEWSAPI_KEY_HERE")
KALSHI_API_KEY = os.getenv("KALSHI_API_KEY", "")
KALSHI_SECRET_KEY = os.getenv("KALSHI_SECRET_KEY", "")

# ==================== NEWS COLLECTION ====================
# NewsAPI configuration
NEWS_API_URL = "https://newsapi.org/v2/everything"
NEWS_API_TIMEOUT = 30  # seconds

# Keywords for filtering political news
MACRO_KEYWORDS = {
    "election": ["election", "vote", "voting", "campaign", "candidate", "2024", "2028"],
    "trump": ["Trump", "Maga", "MAGA", "Republican", "GOP"],
    "biden": ["Biden", "Democratic", "Democrat", "administration", "White House"],
    "congress": ["Congress", "Senate", "House", "Representative", "Senator", "legislation", "bill", "law"],
    "policy": ["policy", "regulation", "executive order", "mandate", "tariff", "trade"],
    "geopolitical": ["China", "Russia", "Ukraine", "war", "conflict", "sanctions", "foreign policy", "international"],
}

# News sources to prioritize
PRIORITY_SOURCES = [
    "reuters",
    "bloomberg",
    "cnbc",
    "ft.com",
    "marketwatch",
    "investing.com",
    "wsj",
]

# Time ranges for news collection
NEWS_LOOKBACK_DAYS = 7
NEWS_BATCH_SIZE = 100
NEWS_COLLECTION_INTERVAL_HOURS = 1

# ==================== SENTIMENT ANALYSIS ====================
# VADER vs FinBERT
SENTIMENT_MODEL = "vader"  # Options: "vader", "finbert"

# Sentiment aggregation windows
SENTIMENT_WINDOW_HOURS = 24  # Aggregate sentiment over 24 hours
MIN_HEADLINES_PER_WINDOW = 3  # Minimum headlines to compute sentiment

# VADER confidence thresholds
VADER_NEUTRAL_THRESHOLD = 0.1  # Scores between -0.1 and 0.1 are neutral

# ==================== KALSHI MARKET DATA ====================
# Kalshi API configuration
KALSHI_API_URL = "https://api.kalshi.com/trade-api/v2"
KALSHI_TIMEOUT = 30  # seconds

# Market slugs to track (political prediction markets on Kalshi)
KALSHI_MARKETS = {
    "election": [
        "US-ELECTION-2024-DEM",      # Will Democrat win 2024 election
        "US-ELECTION-2024-GOP",      # Will Republican win 2024 election
        "US-PRESIDENTIAL-2028",      # 2028 Presidential election
    ],
    "congress": [
        "US-SENATE-CONTROL-2024",    # Which party controls Senate in 2024
        "US-HOUSE-CONTROL-2024",     # Which party controls House in 2024
        "US-CONGRESS-REPUBLICAN",    # Republican control of Congress
    ],
    "policy": [
        "TARIFFS-25-PERCENT",        # Will 25% tariffs be implemented
        "IMMIGRATION-POLICY-2024",   # Immigration policy changes in 2024
        "BITCOIN-LEGAL",             # Bitcoin becomes legal tender in US
    ],
    "geopolitical": [
        "UKRAINE-AID-APPROVED",      # Ukraine aid approved by Congress
        "CHINA-TAIWAN-ACTION",       # Military action in Taiwan strait
        "RUSSIA-CYBERATTACK",        # Major Russian cyberattack on US
    ],
}

# Price check interval
MARKET_PRICE_INTERVAL_MINUTES = 15
MARKET_PRICE_LOOKBACK_DAYS = 30

# ==================== TIME SERIES ANALYSIS ====================
# Rolling window calculations
ROLLING_SENTIMENT_WINDOW_HOURS = 24
ROLLING_CORRELATION_WINDOW_DAYS = 14

# Lag analysis parameters
MAX_LAG_HOURS = 72
LAG_STEP_HOURS = 6
CORRELATION_MIN_THRESHOLD = 0.3  # Significant correlation

# Probability change threshold (percentage points)
MIN_PRICE_CHANGE_FOR_EVENT = 2.0

# ==================== VISUALIZATION ====================
OUTPUT_DPI = 300
FIGURE_SIZE_SMALL = (12, 6)
FIGURE_SIZE_LARGE = (16, 10)
COLORS = {
    "positive": "#2ecc71",
    "negative": "#e74c3c",
    "neutral": "#95a5a6",
    "sentiment": "#3498db",
    "market": "#e67e22",
}

# ==================== LOGGING & STORAGE ====================
LOG_DIR = "logs"
OUTPUT_DIR = "output"
DATA_DIR = "data"

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ==================== DATABASE & CACHING ====================
# SQLite database for storing historical data
DB_PATH = os.path.join(DATA_DIR, "market_sentiment.db")
CACHE_EXPIRY_HOURS = 24

# ==================== PERFORMANCE TUNING ====================
BATCH_PROCESSING_ENABLED = True
PARALLEL_WORKERS = 4
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# ==================== REAL DATA FLAGS ====================
# Enable/disable real data sources
USE_LOCAL_DATASET = False  # Disable local datasets - use live APIs
USE_REAL_NEWS = True  # Fetch real news from NewsAPI/Finnhub
USE_REAL_MARKET_DATA = True  # Fetch real market data from Kalshi API
USE_CACHE = True  # Use cached data when available
FALLBACK_TO_MOCK_DATA = False  # Disable mock data - use only real APIs
FALLBACK_TO_GDELT = False  # Disable GDELT fallback
FALLBACK_TO_SYNTHETIC = True  # Generate synthetic market data if Kalshi API fails

# Data storage
SAVE_RAW_DATA = True  # Save raw data to CSV
RAW_NEWS_FILE = os.path.join(DATA_DIR, "news_raw.csv")
RAW_MARKET_FILE = os.path.join(DATA_DIR, "market_prices.csv")
ALIGNED_DATA_FILE = os.path.join(DATA_DIR, "aligned_sentiment_market.csv")

# Analysis configuration
TARGET_RESAMPLING_FREQUENCY = "1d"  # Resample to daily ("1d", "1h", "4h", "7d") - daily works better with recent API data
DATA_ALIGNMENT_METHOD = "inner"  # How to join sentiment and market data
