"""
Sentiment-Market Analyzer Package
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__description__ = "Analyze correlations between financial news sentiment and Kalshi prediction markets"

from src.news_collector import NewsCollector
from src.sentiment_analyzer import SentimentAnalyzer
from src.market_data import KalshiMarketCollector, MockKalshiDataGenerator
from src.time_series import TimeSeriesAnalyzer
from src.visualization import TimeSeriesVisualizer
from src.utils import DatabaseManager

__all__ = [
    "NewsCollector",
    "SentimentAnalyzer",
    "KalshiMarketCollector",
    "MockKalshiDataGenerator",
    "TimeSeriesAnalyzer",
    "TimeSeriesVisualizer",
    "DatabaseManager",
]
