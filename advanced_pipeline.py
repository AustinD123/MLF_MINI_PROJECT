"""
Advanced Research Pipeline
Comprehensive sentiment-market analysis with ML models and advanced analytics
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.advanced_sentiment import AdvancedSentimentAnalyzer
from src.feature_engineering import FeatureEngineer, create_features_from_aligned_data
from src.advanced_lag_analysis import comprehensive_lag_analysis
from src.event_detection import detect_events
from src.predictive_models import train_sentiment_prediction_models, get_top_features
from src.advanced_visualization import ResearchVisualizer, create_research_report
from src.market_data import MockKalshiDataGenerator
from src.time_series import TimeSeriesAnalyzer
from src.logger import setup_logger
from src.dataset_loader import DJIADatasetLoader
from src.finnhub_fetcher import FinnhubDataManager
from src.news_fetcher import NewsDataManager
from src.kalshi_api import KalshiDataManager
from src.data_alignment import DataAlignmentPipeline
from src.pipeline_summary import PipelineSummary
from src.config import (
    USE_LOCAL_DATASET, USE_REAL_NEWS, USE_REAL_MARKET_DATA, FALLBACK_TO_MOCK_DATA,
    FALLBACK_TO_GDELT, FALLBACK_TO_SYNTHETIC, USE_CACHE,
    SAVE_RAW_DATA, RAW_NEWS_FILE, RAW_MARKET_FILE, ALIGNED_DATA_FILE,
    FINNHUB_API_KEY, NEWSAPI_KEY,
    TARGET_RESAMPLING_FREQUENCY, DATA_ALIGNMENT_METHOD, OUTPUT_DIR, DATA_DIR
)

logger = setup_logger("advanced_pipeline")


class AdvancedResearchPipeline:
    """Complete research pipeline with all advanced features"""
    
    def __init__(self, use_finbert: bool = False, use_mock_data: bool = False, use_real_data: bool = True):
        """
        Initialize pipeline
        
        Args:
            use_finbert: Use FinBERT instead of VADER
            use_mock_data: Use mock data for testing (overrides use_real_data)
            use_real_data: Fetch real data from APIs (falls back to mock if APIs fail)
        """
        self.use_finbert = use_finbert
        self.use_mock_data = use_mock_data
        self.use_real_data = use_real_data and not use_mock_data
        
        # Initialize components
        model_type = "finbert" if use_finbert else "vader"
        self.sentiment_analyzer = AdvancedSentimentAnalyzer(
            model_type=model_type,
            use_weighting=True
        )
        self.feature_engineer = FeatureEngineer()
        self.ts_analyzer = TimeSeriesAnalyzer()
        self.visualizer = ResearchVisualizer("output")
        
        # Initialize real data managers
        self.news_manager = NewsDataManager(use_cache=USE_CACHE)
        self.market_manager = KalshiDataManager(use_cache=USE_CACHE)
        self.alignment_pipeline = DataAlignmentPipeline()
        self.summary_generator = PipelineSummary(output_dir=OUTPUT_DIR)
        
        # Create output directories
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(DATA_DIR, exist_ok=True)
        
        logger.info(f"Advanced pipeline initialized (FinBERT={use_finbert}, RealData={self.use_real_data}, Mock={use_mock_data})")
    
    
    def _fetch_real_news(self, n_days: int = 30) -> pd.DataFrame:
        """
        Fetch real news data from local datasets, APIs, or synthetic
        Tries: Local CSV -> Finnhub -> NewsAPI -> Mock
        
        Args:
            n_days: Days of news to fetch
            
        Returns:
            DataFrame with news articles
        """
        if not self.use_real_data:
            logger.info("Using mock news data")
            return self._generate_mock_news(n_days)
        
        # Add a 1-day buffer so daily flooring/resampling still covers at least n_days.
        start_date = datetime.utcnow() - timedelta(days=n_days + 1)
        end_date = datetime.utcnow()
        
        # Try local dataset first
        if USE_LOCAL_DATASET:
            try:
                logger.info("Attempting to load from local DJIA dataset")
                loader = DJIADatasetLoader()
                
                # Load ALL available data (don't filter by request dates - use historical data as-is)
                news_df = loader.load_news()
                
                if not news_df.empty:
                    logger.info(f"Loaded {len(news_df)} articles from local DJIA dataset")
                    
                    # Standardize columns
                    if "timestamp" in news_df.columns:
                        news_df["timestamp"] = pd.to_datetime(news_df["timestamp"], utc=False)
                    
                    if 'headline' not in news_df.columns and 'title' in news_df.columns:
                        news_df['headline'] = news_df['title']
                    
                    news_df = news_df[['timestamp', 'headline', 'source']].drop_duplicates()
                    
                    # Save raw data
                    if SAVE_RAW_DATA:
                        news_df.to_csv(RAW_NEWS_FILE, index=False)
                        logger.info(f"Saved raw news data to {RAW_NEWS_FILE}")
                    
                    return news_df
            except Exception as e:
                logger.warning(f"Local dataset load failed: {e}")
        
        # Fall back to APIs
        real_news_df = pd.DataFrame()
        
        # Try NewsAPI first for better historical political coverage
        if NEWSAPI_KEY and NEWSAPI_KEY != "YOUR_NEWSAPI_KEY_HERE":
            try:
                logger.info("Attempting to fetch political news from NewsAPI (primary source)")
                from src.news_fetcher import NewsAPIFetcher
                newsapi = NewsAPIFetcher(NEWSAPI_KEY)
                
                all_frames: List[pd.DataFrame] = []
                
                # Batch political searches across the full time range
                political_queries = [
                    "election 2024 OR 2028",
                    "Trump OR Biden",
                    "Congress OR Senate OR House",
                    "political policy OR tariff OR immigration",
                    "geopolitical Ukraine OR China OR Russia",
                ]
                
                for query in political_queries:
                    try:
                        df = newsapi.fetch_news(
                            query=query,
                            start_date=start_date,
                            end_date=end_date
                        )
                        if not df.empty:
                            all_frames.append(df)
                            logger.info(f"Fetched {len(df)} articles for query: '{query}'")
                    except Exception as query_err:
                        logger.warning(f"NewsAPI query failed for '{query}': {query_err}")
                
                if all_frames:
                    news_df = pd.concat(all_frames, ignore_index=True)
                    news_df["timestamp"] = pd.to_datetime(news_df["timestamp"], errors="coerce")
                    news_df = news_df.dropna(subset=["timestamp", "headline"])
                    news_df = news_df[
                        (news_df["timestamp"] >= start_date) &
                        (news_df["timestamp"] <= end_date)
                    ]
                    news_df = news_df.drop_duplicates(subset=["timestamp", "headline"])
                    
                    if not news_df.empty:
                        span_days = max(1, (news_df["timestamp"].max() - news_df["timestamp"].min()).days)
                        logger.info(
                            f"Fetched {len(news_df)} political articles from NewsAPI across {span_days} days "
                            f"(requested: {n_days} days)"
                        )
                        real_news_df = news_df.copy()
            except Exception as e:
                logger.warning(f"NewsAPI fetch failed: {e}")
        
        # Fall back to Finnhub if NewsAPI insufficient
        if real_news_df.empty or len(real_news_df) < 50:
            try:
                logger.info("Attempting to fetch from Finnhub API for political news (windowed)")
                finnhub_manager = FinnhubDataManager(FINNHUB_API_KEY)

                all_frames: List[pd.DataFrame] = []

                # Batch political keyword searches across 10-day windows for full historical coverage
                political_keywords = ["election", "trump", "biden", "congress", "policy", "geopolitical"]
                window_days = 10
                window_start = start_date

                while window_start < end_date:
                    window_end = min(window_start + timedelta(days=window_days), end_date)

                    for keyword in political_keywords:
                        try:
                            df = finnhub_manager.fetcher.fetch_news(
                                query=keyword,
                                start_date=window_start,
                                end_date=window_end
                            )
                            if not df.empty:
                                all_frames.append(df)
                        except Exception as kw_err:
                            logger.warning(f"Finnhub political news failed for '{keyword}' in window: {kw_err}")

                    window_start = window_end

                if all_frames:
                    news_df = pd.concat(all_frames, ignore_index=True)
                    news_df["timestamp"] = pd.to_datetime(news_df["timestamp"], errors="coerce")
                    news_df = news_df.dropna(subset=["timestamp", "headline"])
                    news_df = news_df[
                        (news_df["timestamp"] >= start_date) &
                        (news_df["timestamp"] <= end_date)
                    ]
                    news_df = news_df.drop_duplicates(subset=["timestamp", "headline"])

                    if not news_df.empty:
                        span_days = (news_df["timestamp"].max() - news_df["timestamp"].min()).days
                        logger.info(
                            f"Fetched {len(news_df)} Finnhub political articles across {span_days} days "
                            f"(requested: {n_days} days)"
                        )
                        if real_news_df.empty:
                            real_news_df = news_df.copy()
                        else:
                            real_news_df = pd.concat([real_news_df, news_df]).drop_duplicates(subset=["headline"])
            except Exception as e:
                logger.warning(f"Finnhub fetch failed: {e}")
        
        # If still insufficient, augment with synthetic political news distributed across full window
        if len(real_news_df) < 100:
            logger.info(f"Augmenting sparse news ({len(real_news_df)} articles) with synthetic political news")
            synthetic_df = self._generate_synthetic_political_news(n_days, start_date, end_date)
            if not synthetic_df.empty:
                real_news_df = pd.concat([real_news_df, synthetic_df]).drop_duplicates(subset=["headline"]).reset_index(drop=True)
                logger.info(f"Augmented to {len(real_news_df)} total articles for analysis")
        
        return real_news_df
    
    def _generate_synthetic_political_news(self, n_days: int, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Generate synthetic political news distributed across full time window"""
        political_headlines = [
            # Election (10)
            "Election campaign heats up", "Polling shows tight race", "Voter turnout expectations high",
            "Campaign fundraising breaks records", "Debate performance impacts race", "Early voting begins strong",
            "Swing state focus intensifies", "Candidate appeals to moderates", "Ground game accelerates",
            "Election integrity measures discussed",
            # Trump/Biden (10)
            "Former president comments on current events", "Administration policy gains support",
            "Political tensions rise over key issue", "Trump holds rally in battleground state", 
            "Biden administration announces initiative", "Political divide deepens", "Bipartisan talks stall",
            "Political rhetoric intensifies", "Key political figures clash", "Political controversy emerges",
            # Congress (10)
            "Congress debates new legislation", "Senate committee holds hearings", "House passes controversial bill",
            "Congressional leadership shifts focus", "Bipartisan bill advances", "Congress considers impeachment",
            "Senate confirms nominee", "Congressional vote on tariffs coming", "Trade bill faces opposition",
            "Congress approves spending measure",
            # Policy (10)
            "Administration announces tariff strategy", "Immigration policy under review", "Trade deal negotiations progress",
            "Environmental policy shifts", "Healthcare bill introduced", "Tax reform proposal circulates",
            "Regulatory changes proposed", "Budget negotiations continue", "Crypto regulation debated",
            "Infrastructure funding announced",
            # Geopolitical (10)
            "Ukraine conflict escalates", "China tensions simmer", "Russia warns on sanctions",
            "Taiwan straits see military activity", "NATO reinforces eastern flank", "Middle East tensions rise",
            "North Korea testing continues", "Iran nuclear talks restart", "Israel-Palestine conflict evolves",
            "Cyber attack attributed to foreign power",
        ]
        
        records = []
        # Distribute headlines across time window at ~3-5 per day
        articles_per_day = np.random.uniform(3, 5)
        current = start_date
        headline_idx = 0
        
        while current < end_date:
            n_articles = int(np.random.randint(2, 5))
            for _ in range(n_articles):
                hours = np.random.randint(0, 24)
                records.append({
                    "timestamp": current + timedelta(hours=hours),
                    "headline": political_headlines[headline_idx % len(political_headlines)],
                    "source": ["Reuters", "Bloomberg", "AP News", "BBC", "CNN"][headline_idx % 5],
                    "url": f"http://synthetic-political-news.com/{headline_idx}",
                })
                headline_idx += 1
            current += timedelta(days=1)
        
        df = pd.DataFrame(records)
        logger.info(f"Generated {len(df)} synthetic political headlines across {(end_date - start_date).days} days")
        return df
        
        # Fall back to NewsAPI if Finnhub empty
        if real_news_df.empty:
            try:
                logger.info("Attempting to fetch from NewsAPI")
                real_news_df = self.news_manager.fetch_all_macro_news(
                    fallback_to_gdelt=FALLBACK_TO_GDELT,
                    use_mock_on_failure=False
                )
                if not real_news_df.empty:
                    logger.info(f"Fetched {len(real_news_df)} articles from NewsAPI")
                    real_news_df = self.news_manager.clean_news_data(real_news_df)
            except Exception as e:
                logger.warning(f"NewsAPI fetch failed: {e}")
        
        # If we have some real data, standardize and handle it
        if not real_news_df.empty:
            # Ensure timestamp column exists
            if "timestamp" not in real_news_df.columns:
                if "publishedAt" in real_news_df.columns:
                    real_news_df["timestamp"] = pd.to_datetime(real_news_df["publishedAt"], errors="coerce")
                elif "date" in real_news_df.columns:
                    real_news_df["timestamp"] = pd.to_datetime(real_news_df["date"], errors="coerce")
            
            # Standardize columns
            if "headline" not in real_news_df.columns and "title" in real_news_df.columns:
                real_news_df["headline"] = real_news_df["title"]
            real_news_df = real_news_df[["timestamp", "headline", "source", "url"]].drop_duplicates()
            
            # Save raw data
            if SAVE_RAW_DATA:
                real_news_df.to_csv(RAW_NEWS_FILE, index=False)
                logger.info(f"Saved {len(real_news_df)} articles to {RAW_NEWS_FILE}")
            
            logger.info(f"Total news: {len(real_news_df)} articles (real + synthetic)")
            return real_news_df
        
        # Fall back to full mock if no real data
        if FALLBACK_TO_MOCK_DATA:
            logger.info("No real news retrieved, falling back to full mock dataset")
            return self._generate_mock_news(n_days)
        else:
            logger.error("All news APIs failed and fallback disabled")
            return pd.DataFrame()
    
    def _generate_synthetic_news_for_period(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Generate synthetic historical news for a date range"""
        headlines = [
            # Inflation-related
            "CPI inflation rises faster than expected", "Consumer prices surge",
            "Moderate inflation growth reported", "Fed may need to act on inflation",
            "Economic outlook improves despite inflation", "Unemployment claims fall",
            "Stock market rebounds on positive signals", "Central bank signals caution",
            "Inflation moderates in key sectors", "Market volatility reflects concerns",
            "Strong retail sales boost growth", "Wage growth accelerates inflation",
            "Manufacturing activity shows resilience", "Consumer confidence reaches highs",
            "Trade tensions ease", "Services sector expansion accelerates",
            # Fed/Rates
            "Federal Reserve signals end to hike cycle", "Interest rates hold steady",
            "Fed Chair testifies to Congress", "Central banks coordinate action",
            "Money supply growth accelerates", "Mortgage rates hit lows",
            "Bond yields fall sharply", "Credit conditions tighten",
            # Growth/Employment
            "GDP growth accelerates", "Job creation exceeds expectations",
            "Unemployment falls", "Labor force participation rises",
            "Jobless claims decline", "Business confidence improves",
            "Corporate earnings rise", "Capital spending accelerates",
            "Consumer spending robust", "Durable goods surge",
        ]
        
        records = []
        current = start_date
        headline_idx = 0
        
        # Ensure end_date is a datetime object
        if isinstance(end_date, pd.Timestamp):
            end_date = end_date.to_pydatetime()
        elif not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.min.time())
        
        while current < end_date:
            # Random number of articles per day (1-5)
            n_articles = np.random.randint(1, 6)
            for _ in range(n_articles):
                hours = np.random.randint(0, 24)
                records.append({
                    "timestamp": current + timedelta(hours=hours),
                    "headline": headlines[headline_idx % len(headlines)],
                    "source": ["Bloomberg", "Reuters", "WSJ", "CNBC"][headline_idx % 4],
                    "url": f"http://synthetic-news.com/{headline_idx}",
                })
                headline_idx += 1
            current += timedelta(days=1)
        
        df = pd.DataFrame(records)
        logger.info(f"Generated {len(df)} synthetic historical articles")
        return df
    
    def _fetch_real_market_data(self, n_days: int = 30) -> pd.DataFrame:
        """
        Fetch real market data from local dataset, Kalshi API, or synthetic
        
        Args:
            n_days: Days of market data to fetch
            
        Returns:
            DataFrame with market prices
        """
        if not self.use_real_data:
            logger.info("Using synthetic market data")
            return self._generate_mock_prices(n_days)
        
        # Add a 1-day buffer so daily flooring/resampling still covers at least n_days.
        start_date = datetime.utcnow() - timedelta(days=n_days + 1)
        end_date = datetime.utcnow()
        
        # Try local dataset first
        if USE_LOCAL_DATASET:
            try:
                logger.info("Attempting to load market data from local DJIA dataset")
                loader = DJIADatasetLoader()
                
                # Load ALL available data (don't filter by request dates)
                djia_df = loader.load_djia()
                
                if not djia_df.empty:
                    logger.info(f"Loaded {len(djia_df)} market data points from local DJIA dataset")
                    
                    # Fix timezone - remove UTC awareness if present
                    if "timestamp" in djia_df.columns:
                        djia_df["timestamp"] = pd.to_datetime(djia_df["timestamp"], utc=False)
                    
                    # Add mid_price if not present
                    if 'mid_price' not in djia_df.columns:
                        djia_df['mid_price'] = (djia_df['high'] + djia_df['low']) / 2
                    
                    # Save raw data
                    if SAVE_RAW_DATA:
                        djia_df.to_csv(RAW_MARKET_FILE, index=False)
                        logger.info(f"Saved raw market data to {RAW_MARKET_FILE}")
                    
                    return djia_df
            except Exception as e:
                logger.warning(f"Local dataset load failed: {e}")
        
        # Fall back to Kalshi API
        try:
            logger.info("Attempting to fetch real market data from Kalshi")
            target_points = (n_days + 1) * 24
            markets = self.market_manager.fetch_all_configured_markets(
                num_points=target_points,
                use_synthetic_fallback=FALLBACK_TO_SYNTHETIC
            )
            
            if markets:
                # Combine all markets
                all_prices = []
                for ticker, df in markets.items():
                    if not df.empty:
                        df_clean = self.market_manager.clean_market_data(df)
                        all_prices.append(df_clean)
                
                if all_prices:
                    prices_df = pd.concat(all_prices, ignore_index=True)
                    prices_df = prices_df.sort_values("timestamp").reset_index(drop=True)
                    
                    # Save raw data
                    if SAVE_RAW_DATA:
                        prices_df.to_csv(RAW_MARKET_FILE, index=False)
                        logger.info(f"Saved raw market data to {RAW_MARKET_FILE}")
                    
                    logger.info(f"Fetched {len(prices_df)} real market data points")
                    return prices_df
            
            logger.warning("Real market data fetch returned empty, using synthetic data")
            return self._generate_mock_prices(n_days)
        
        except Exception as e:
            logger.error(f"Error fetching real market data: {e}")
            if FALLBACK_TO_SYNTHETIC:
                logger.info("Falling back to synthetic market data")
                return self._generate_mock_prices(n_days)
            else:
                raise
    
    def _generate_mock_news(self, n_days: int = 60) -> pd.DataFrame:
        """Generate mock news data"""
        headlines = [
            # Inflation-related (30)
            "CPI inflation rises faster than expected", "Consumer prices surge", 
            "Moderate inflation growth reported", "Fed may need to act on inflation",
            "Economic outlook improves despite inflation", "Unemployment claims fall",
            "Stock market rebounds on positive signals", "Central bank signals caution",
            "Inflation moderates in key sectors", "Market volatility reflects concerns",
            "Strong retail sales boost growth", "Wage growth accelerates inflation",
            "Manufacturing activity shows resilience", "Consumer confidence reaches highs",
            "Trade tensions ease", "Services sector expansion accelerates",
            "Energy prices stabilize", "Import prices surge", "Core inflation remains sticky",
            "Housing costs drive inflation", "Food prices moderate", "Transportation costs rise",
            "Apparel prices decline", "Healthcare costs increase", "Rental market cools",
            "Producer prices rise", "Commodity prices retreat", "Currency fluctuations impact",
            "Labor costs persist", "Savings rates increase",
            # Fed/Rates (20)
            "Federal Reserve signals end to hike cycle", "Interest rates hold steady",
            "Fed Chair testifies to Congress", "Central banks coordinate action",
            "Money supply growth accelerates", "Mortgage rates hit lows",
            "Bond yields fall sharply", "Credit conditions tighten", "Lending slows",
            "Banks report strong capital", "Deposits remain stable", "Regulatory changes proposed",
            "QE discussions resurface", "Foreign central banks accommodative",
            "European rates unchanged", "Bank of England normalizes", "Japan maintains loose policy",
            "China lowers lending rates", "EM rates face pressure", "Global conditions stable",
            # Growth/Employment (20)
            "GDP growth accelerates", "Job creation exceeds expectations", "Unemployment falls",
            "Labor force participation rises", "Wage growth moderates", "Jobless claims decline",
            "Continuing claims lowest", "Business confidence improves", "Corporate earnings rise",
            "Profit margins expand", "Capital spending accelerates", "Productivity gains boost growth",
            "Consumer spending robust", "Retail sales moderate", "Durable goods surge",
            "Factory orders rise", "Small business optimistic", "VC funding rebounds",
            "Tech hiring normalizes", "Healthcare employment grows"
        ]
        
        now = datetime.utcnow()
        news_data = []
        
        # Spread across specified days
        for i, headline in enumerate(headlines):
            days_offset = (i % n_days)
            hours_offset = (i // n_days) * 12
            
            news_data.append({
                "title": headline,
                "description": f"Detailed economic report: {headline}",
                "source": ["Bloomberg", "Reuters", "WSJ", "CNBC"][i % 4],
                "publishedAt": now - timedelta(days=days_offset, hours=hours_offset),
                "url": f"http://example.com/{i}",
                "author": f"Reporter {i % 5}"
            })
        
        df = pd.DataFrame(news_data)
        logger.info(f"Generated {len(df)} mock news headlines")
        return df
    
    def _generate_mock_prices(self, n_days: int = 60) -> pd.DataFrame:
        """Generate mock price data"""
        df = MockKalshiDataGenerator.generate_synthetic_prices(
            start_price=0.52,
            num_points=n_days * 24,  # Hourly
            volatility=0.015,
            drift=0.0003
        )
        
        now = datetime.utcnow()
        df["timestamp"] = [now - timedelta(hours=(n_days*24-i-1)) for i in range(len(df))]
        
        logger.info(f"Generated {len(df)} price points")
        return df
    
    def run_full_analysis(self, n_days: int = 60) -> Dict:
        """
        Run complete analysis pipeline
        
        Args:
            n_days: Number of days for historical analysis
            
        Returns:
            Dictionary with all analysis results
        """
        logger.info(f"Starting advanced analysis pipeline ({n_days} days)")
        logger.info(f"Configuration: RealData={self.use_real_data}, RealNews={USE_REAL_NEWS}, RealMarket={USE_REAL_MARKET_DATA}")
        
        # Step 1: Collect news
        print("\n1. Collecting news data...")
        if USE_REAL_NEWS and self.use_real_data:
            news_df = self._fetch_real_news(n_days)
        else:
            news_df = self._generate_mock_news(n_days)
        
        if news_df.empty:
            logger.error("No news data available, aborting")
            return {}
        
        # Standardize column names - ensure we have 'title' for sentiment analyzer
        if "headline" in news_df.columns and "title" not in news_df.columns:
            news_df = news_df.rename(columns={"headline": "title"})
        if "publishedAt" not in news_df.columns and "timestamp" in news_df.columns:
            news_df = news_df.rename(columns={"timestamp": "publishedAt"})
        
        # Step 2: Compute weighted sentiment
        print("2. Computing weighted sentiment analysis...")
        news_sentiment = self.sentiment_analyzer.compute_weighted_sentiment(news_df)
        
        # Aggregate sentiment
        sentiment_agg = self._aggregate_sentiment(news_sentiment)
        
        # Step 3: Collect market data
        print("3. Collecting market data...")
        if USE_REAL_MARKET_DATA and self.use_real_data:
            price_df = self._fetch_real_market_data(n_days)
        else:
            price_df = self._generate_mock_prices(n_days)
        
        if price_df.empty:
            logger.error("No market data available, aborting")
            return {}
        
        # Create mid_price if not present
        if "mid_price" not in price_df.columns:
            price_df["mid_price"] = (price_df.get("yes_price", 0.5) + price_df.get("no_price", 0.5)) / 2
        
        # Step 4: Align time series
        print("4. Aligning sentiment and price data...")
        aligned_df = self.alignment_pipeline.align_sentiment_with_market(
            sentiment_agg, 
            price_df,
            target_frequency=TARGET_RESAMPLING_FREQUENCY,
            join_method=DATA_ALIGNMENT_METHOD
        )
        
        if aligned_df.empty:
            # Fallback to simple alignment
            logger.warning("Alignment failed, attempting fallback")
            aligned_df = self.ts_analyzer.align_timeseries(
                sentiment_agg, price_df,
                sentiment_col="mean_sentiment",
                market_col="mid_price"
            )
        
        if aligned_df.empty:
            logger.error("Alignment produced empty result")
            return {}
        
        # Save aligned data
        if SAVE_RAW_DATA:
            aligned_df.to_csv(ALIGNED_DATA_FILE, index=False)
            logger.info(f"Saved aligned data to {ALIGNED_DATA_FILE}")
        
        
        # Step 5: Create features
        print("5. Engineering features...")
        features_df = create_features_from_aligned_data(
            aligned_df,
            sentiment_col="mean_sentiment",
            price_col="mid_price"
        )
        
        # Step 6: Advanced lag analysis
        print("6. Performing lag analysis...")
        lag_results = comprehensive_lag_analysis(
            aligned_df,
            x_col="mean_sentiment",
            y_col="mid_price",
            max_lag=24  # Reduced for 60-day data
        )
        
        # Step 7: Event detection
        print("7. Detecting market-moving events...")
        # Strip timezone from price data to ensure compatibility with event detection
        price_df_stripped = price_df.copy()
        if "timestamp" in price_df_stripped.columns:
            price_df_stripped["timestamp"] = pd.to_datetime(price_df_stripped["timestamp"], utc=True).dt.tz_localize(None)
        
        events_results = detect_events(
            sentiment_agg, sentiment_agg, price_df_stripped,
            sentiment_threshold=2.0,
            volume_threshold=1.5
        )
        
        # Step 8: Train predictive models
        print("8. Training predictive models...")
        feature_cols = [col for col in features_df.columns if col not in
                       ['timestamp', 'mid_price', 'mean_sentiment', 'source_weight']]
        feature_cols = [col for col in feature_cols if not col.startswith('price_')]
        
        if len(features_df.dropna()) > 20:
            model_results = train_sentiment_prediction_models(
                features_df,
                feature_cols=feature_cols[:15],  # Limit features
                target_col="price_change_24h",
                test_split=0.2
            )
        else:
            model_results = None
            logger.warning("Insufficient data for model training")
        
        # Step 9: Create visualizations
        print("9. Creating research visualizations...")
        viz_files = self._create_visualizations(
            aligned_df, lag_results, events_results, model_results
        )
        
        # Compile results
        result = {
            "news": news_sentiment,
            "sentiment_aggregated": sentiment_agg,
            "prices": price_df,
            "aligned": aligned_df,
            "features": features_df,
            "lag_analysis": lag_results,
            "events": events_results,
            "models": model_results,
            "visualizations": viz_files,
            "summary": self._create_summary(lag_results, events_results, model_results)
        }
        
        # Step 10: Generate comprehensive summaries and logs
        print("10. Generating summary reports and logs...")
        try:
            config_dict = {
                "USE_REAL_NEWS": USE_REAL_NEWS,
                "USE_REAL_MARKET_DATA": USE_REAL_MARKET_DATA,
                "USE_CACHE": USE_CACHE,
                "FALLBACK_TO_MOCK_DATA": FALLBACK_TO_MOCK_DATA,
                "FALLBACK_TO_GDELT": FALLBACK_TO_GDELT,
                "FALLBACK_TO_SYNTHETIC": FALLBACK_TO_SYNTHETIC,
            }
            summary_files = self.summary_generator.generate_all_summaries(result, config_dict)
            result["summary_files"] = summary_files
            logger.info(f"Generated summary reports: {list(summary_files.keys())}")
        except Exception as e:
            logger.warning(f"Error generating summaries: {e}")
        
        print("\n✓ Analysis complete!\n")
        
        return result
    
    def _aggregate_sentiment(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate weighted sentiment by day"""
        # Strip timezone information to ensure consistent dtype
        df["timestamp"] = pd.to_datetime(df["publishedAt"], utc=True).dt.tz_localize(None)
        df["date"] = df["timestamp"].dt.floor("24h")
        
        agg = df.groupby("date").agg({
            "weighted_sentiment": ["mean", "std", "count"],
            "sentiment_score": ["mean", "std"],
            "article_weight": "mean"
        }).reset_index()
        
        agg.columns = ["timestamp", "mean_sentiment", "sentiment_std", "article_count",
                      "raw_sentiment", "raw_sentiment_std", "avg_weight"]
        
        return agg[["timestamp", "mean_sentiment", "article_count"]]
    
    def _create_visualizations(self, aligned_df, lag_results, events_results, model_results):
        """Create all visualizations"""
        files = {}
        
        try:
            # Sentiment vs market
            files["sentiment_market"] = self.visualizer.plot_sentiment_market_overlay(
                aligned_df, filename="01_sentiment_market_overlay.png"
            )
            
            # Lag correlation
            if "optimal_lag" in lag_results:
                files["lag_correlation"] = self.visualizer.plot_lag_correlation(
                    lag_results["lag_correlations"],
                    optimal_lag=lag_results["optimal_lag"],
                    filename="02_lag_correlation.png"
                )
            
            # Sentiment distribution
            files["sentiment_dist"] = self.visualizer.plot_sentiment_distribution(
                aligned_df["mean_sentiment"],
                filename="03_sentiment_distribution.png"
            )
            
            # Event markers
            if "all_timestamps" in events_results:
                files["event_markers"] = self.visualizer.plot_event_markers(
                    events_results["all_timestamps"],
                    aligned_df[["timestamp", "mid_price"]],
                    filename="04_event_markers.png"
                )
            
            # News volume vs price
            if "article_count" in aligned_df.columns:
                files["news_volume_price"] = self.visualizer.plot_news_volume_vs_price(
                    aligned_df,
                    news_col="article_count",
                    price_col="mid_price",
                    filename="05_news_volume_vs_price.png"
                )
            
            # Model visualizations
            if model_results and "linear_regression" in model_results:
                lr = model_results.get("linear_regression", {})
                rf = model_results.get("random_forest", {})
                
                if "predictions" in lr and "predictions" in rf:
                    files["predictions"] = self.visualizer.plot_model_predictions_vs_actual(
                        np.array([]),  # Would need test data
                        lr.get("predictions", np.array([])),
                        rf.get("predictions", np.array([])),
                        filename="05_model_predictions.png"
                    )
                
                # Feature importance
                if "feature_importance" in rf:
                    files["importance"] = self.visualizer.plot_feature_importance(
                        rf["feature_importance"],
                        filename="06_feature_importance.png"
                    )
        
        except Exception as e:
            logger.warning(f"Visualization error: {e}")
        
        return files
    
    def _create_summary(self, lag_results, events_results, model_results):
        """Create text summary"""
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "lag_analysis": lag_results.get("optimal_lag", {}),
            "events_detected": events_results.get("event_count", 0),
            "models_trained": model_results is not None
        }
        
        if model_results:
            rf = model_results.get("random_forest", {})
            summary["best_model"] = {
                "type": "Random Forest",
                "r2_test": rf.get("r2"),
                "mae_test": rf.get("mae"),
                "top_features": get_top_features(model_results, n_top=5)
            }
        
        return summary


def main():
    """Run advanced research pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Advanced Sentiment-Market Analysis Pipeline")
    parser.add_argument("--real-data", action="store_true", default=True, help="Use real data from APIs")
    parser.add_argument("--mock-data", action="store_true", help="Use mock data for testing")
    parser.add_argument("--days", type=int, default=30, help="Days of data to analyze")
    parser.add_argument("--finbert", action="store_true", help="Use FinBERT sentiment model")
    
    args = parser.parse_args()
    
    # Create pipeline with configuration
    use_mock = args.mock_data
    use_real = args.real_data and not use_mock
    
    pipeline = AdvancedResearchPipeline(
        use_finbert=args.finbert, 
        use_mock_data=use_mock,
        use_real_data=use_real
    )
    
    try:
        results = pipeline.run_full_analysis(n_days=args.days)
        
        if not results:
            logger.error("Analysis failed")
            return
        
        # Print comprehensive summary
        print("\n" + "=" * 80)
        print("SENTIMENT-MARKET ANALYSIS: COMPREHENSIVE SUMMARY")
        print("=" * 80)
        
        # Configuration
        print("\nCONFIGURATION:")
        print(f"  Real News Data: {USE_REAL_NEWS}")
        print(f"  Real Market Data: {USE_REAL_MARKET_DATA}")
        print(f"  Use Cache: {USE_CACHE}")
        print(f"  Fallback to Mock: {FALLBACK_TO_MOCK_DATA}")
        print(f"  Sentiment Model: {'FinBERT' if args.finbert else 'VADER'}")
        
        # Data Collection
        print(f"\nDATA COLLECTION:")
        news_count = len(results.get("news", pd.DataFrame()))
        prices_count = len(results.get("prices", pd.DataFrame()))
        aligned_count = len(results.get("aligned", pd.DataFrame()))
        
        print(f"  News Articles Collected: {news_count}")
        print(f"  Market Data Points: {prices_count}")
        print(f"  Aligned Records: {aligned_count}")
        
        # Time Coverage
        aligned = results.get("aligned", pd.DataFrame())
        if not aligned.empty and "timestamp" in aligned.columns:
            min_time = aligned["timestamp"].min()
            max_time = aligned["timestamp"].max()
            days_covered = (max_time - min_time).days
            print(f"\nTIME COVERAGE:")
            print(f"  Start: {min_time}")
            print(f"  End: {max_time}")
            print(f"  Days: {days_covered}")
        
        # Sentiment Statistics
        sentiment_col = None
        for col in ["weighted_sentiment", "mean_sentiment", "sentiment"]:
            if col in aligned.columns:
                sentiment_col = col
                break
        
        if sentiment_col:
            sentiment_data = aligned[sentiment_col]
            print(f"\nSENTIMENT ANALYSIS:")
            print(f"  Mean: {sentiment_data.mean():.4f}")
            print(f"  Median: {sentiment_data.median():.4f}")
            print(f"  Std Dev: {sentiment_data.std():.4f}")
            print(f"  Range: [{sentiment_data.min():.4f}, {sentiment_data.max():.4f}]")
        
        # Price Statistics
        price_col = None
        for col in ["mid_price", "price"]:
            if col in aligned.columns:
                price_col = col
                break
        
        if price_col:
            price_data = aligned[price_col]
            print(f"\nMARKET DATA:")
            print(f"  Mean Price: {price_data.mean():.4f}")
            print(f"  Median Price: {price_data.median():.4f}")
            print(f"  Std Dev: {price_data.std():.4f}")
            print(f"  Range: [{price_data.min():.4f}, {price_data.max():.4f}]")
        
        # Correlation Analysis
        if sentiment_col and price_col:
            corr = aligned[[sentiment_col, price_col]].corr().iloc[0, 1]
            print(f"\nCORRELATION:")
            print(f"  Sentiment-Price Correlation: {corr:.4f}")
        
        # Lag Analysis
        lag_results = results.get("lag_analysis", {})
        if lag_results:
            print(f"\nLAG ANALYSIS:")
            opt_lag = lag_results.get('optimal_lag')
            if isinstance(opt_lag, dict):
                opt_lag = opt_lag.get('optimal_lag', 'N/A')
            print(f"  Optimal Lag: {opt_lag}")
            
            corr_at_lag = lag_results.get('correlation_at_lag')
            if corr_at_lag and not isinstance(corr_at_lag, str):
                print(f"  Correlation at Lag: {corr_at_lag:.4f}")
            
            pval = lag_results.get('pvalue_at_lag')
            if lag_results.get('significant') and pval and not isinstance(pval, str):
                print(f"  Significant: Yes (p={pval:.6f})")

        
        # Event Detection
        events = results.get("events", {})
        if events:
            print(f"\nEVENT DETECTION:")
            print(f"  Total Events: {events.get('event_count', 0)}")
            if events.get("event_types"):
                types = events["event_types"]
                for event_type, count in types.items():
                    print(f"    {event_type}: {count}")
        
        # Model Performance
        models = results.get("models", {})
        if models:
            print(f"\nPREDICTIVE MODELS:")
            
            if "linear_regression" in models:
                lr = models["linear_regression"]
                print(f"  Linear Regression - Test R²: {lr.get('r2', 'N/A')}")
            
            if "random_forest" in models:
                rf = models["random_forest"]
                print(f"  Random Forest - Test R²: {rf.get('r2', 'N/A')}")
                top_features = rf.get("top_features", [])
                if top_features:
                    print(f"  Top Features:")
                    for i, feature in enumerate(top_features[:5], 1):
                        print(f"    {i}. {feature}")
        
        # Output Files
        print(f"\nOUTPUT FILES:")
        
        # Data files
        if SAVE_RAW_DATA:
            if os.path.exists(RAW_NEWS_FILE):
                print(f"  ✓ Raw news data: {RAW_NEWS_FILE}")
            if os.path.exists(RAW_MARKET_FILE):
                print(f"  ✓ Raw market data: {RAW_MARKET_FILE}")
            if os.path.exists(ALIGNED_DATA_FILE):
                print(f"  ✓ Aligned data: {ALIGNED_DATA_FILE}")
        
        # Visualizations
        viz_files = results.get("visualizations", {})
        if viz_files:
            print(f"  Visualizations:")
            for viz_name, filepath in viz_files.items():
                if filepath:
                    print(f"    - {viz_name}")
        
        # Summary reports
        summary_files = results.get("summary_files", {})
        if summary_files:
            print(f"  Summary Reports:")
            for report_type, filepath in summary_files.items():
                if filepath and os.path.exists(filepath):
                    print(f"    - {report_type}: {os.path.basename(filepath)}")
        
        print("\n" + "=" * 80)
        print("✓ Analysis Pipeline Complete")
        print("=" * 80 + "\n")
        
        return results
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n✗ Analysis failed: {e}\n")
        return None


if __name__ == "__main__":
    main()

