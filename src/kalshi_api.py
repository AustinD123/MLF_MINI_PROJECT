"""
Kalshi Market Data API Module
Fetches real prediction market data from Kalshi with fallback to synthetic data
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import json
import time
from src.config import (
    KALSHI_API_URL, KALSHI_API_KEY, KALSHI_TIMEOUT,
    KALSHI_MARKETS, MAX_RETRIES, RETRY_DELAY_SECONDS,
    DATA_DIR, CACHE_EXPIRY_HOURS
)
from src.logger import setup_logger

logger = setup_logger("kalshi_api")


class KalshiAPIClient:
    """Official Kalshi API client for market data"""
    
    def __init__(self, api_key: str = KALSHI_API_KEY):
        """
        Initialize Kalshi API client
        
        Args:
            api_key: Kalshi API key from environment
        """
        self.api_key = api_key
        self.base_url = KALSHI_API_URL
        self.timeout = KALSHI_TIMEOUT
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
            self.available = True
        else:
            logger.warning("Kalshi API key not configured")
            self.available = False
    
    def get_market_prices(
        self,
        market_ticker: str,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Fetch market price history
        
        Args:
            market_ticker: Market ticker identifier
            limit: Maximum records to fetch
            
        Returns:
            DataFrame with columns: [timestamp, market_ticker, bid_price, ask_price, mid_price]
        """
        if not self.available:
            logger.warning("Kalshi API not available")
            return pd.DataFrame()
        
        url = f"{self.base_url}/markets/{market_ticker}"
        params = {"limit": limit}
        
        prices = []
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                logger.info(f"Fetching market data: {market_ticker}")
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                market_data = data.get("data", {})
                
                # Extract price information
                if "prices" in market_data:
                    for price_tick in market_data["prices"]:
                        prices.append({
                            "timestamp": pd.to_datetime(price_tick.get("timestamp")),
                            "market_ticker": market_ticker,
                            "bid_price": float(price_tick.get("bid", 0)),
                            "ask_price": float(price_tick.get("ask", 1)),
                            "mid_price": (float(price_tick.get("bid", 0)) + float(price_tick.get("ask", 1))) / 2,
                            "volume": float(price_tick.get("volume", 0)),
                        })
                
                logger.info(f"Retrieved {len(prices)} price points for {market_ticker}")
                break
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                logger.warning(f"Request failed (attempt {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS)
        
        if not prices:
            logger.warning(f"No prices retrieved for {market_ticker}")
            return pd.DataFrame()
        
        df = pd.DataFrame(prices)
        df = df.sort_values("timestamp").reset_index(drop=True)
        df = df.drop_duplicates(subset=["timestamp", "market_ticker"], keep="last").reset_index(drop=True)
        
        return df
    
    def get_all_markets(self) -> pd.DataFrame:
        """
        Fetch all available markets
        
        Returns:
            DataFrame with market information
        """
        if not self.available:
            return pd.DataFrame()
        
        url = f"{self.base_url}/markets"
        
        try:
            logger.info("Fetching all available markets")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            markets = []
            
            for market in data.get("data", []):
                markets.append({
                    "ticker": market.get("ticker"),
                    "title": market.get("title"),
                    "description": market.get("description"),
                    "expiration_date": market.get("expiration_date"),
                    "status": market.get("status"),
                })
            
            logger.info(f"Retrieved {len(markets)} markets")
            return pd.DataFrame(markets)
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return pd.DataFrame()
    
    def get_market_info(self, market_ticker: str) -> Dict:
        """
        Get detailed market information
        
        Args:
            market_ticker: Market identifier
            
        Returns:
            Dictionary with market metadata
        """
        if not self.available:
            return {}
        
        url = f"{self.base_url}/markets/{market_ticker}"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json().get("data", {})
            logger.info(f"Retrieved info for market: {market_ticker}")
            
            return {
                "ticker": data.get("ticker"),
                "title": data.get("title"),
                "description": data.get("description"),
                "expiration_date": data.get("expiration_date"),
                "status": data.get("status"),
                "yes_bid": data.get("yes_bid"),
                "yes_ask": data.get("yes_ask"),
                "no_bid": data.get("no_bid"),
                "no_ask": data.get("no_ask"),
            }
        
        except Exception as e:
            logger.error(f"Error fetching market info: {e}")
            return {}


class SyntheticMarketDataGenerator:
    """Generate realistic synthetic market data for development/testing"""
    
    @staticmethod
    def generate_synthetic_prices(
        market_ticker: str,
        start_price: float = 0.50,
        num_points: int = 720,  # 30 days of hourly data
        volatility: float = 0.015,
        drift: float = 0.0003,
        start_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Generate synthetic market price data using geometric Brownian motion
        
        Args:
            market_ticker: Market identifier
            start_price: Initial price
            num_points: Number of price points to generate
            volatility: Price volatility (annualized)
            drift: Price drift (trend)
            start_time: Start timestamp
            
        Returns:
            DataFrame with synthetic prices
        """
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(hours=num_points)
        
        # Generate prices using geometric Brownian motion
        dt = 1/252  # Daily time step (hourly data daily freq)
        prices = [start_price]
        
        for _ in range(num_points - 1):
            # Random normal increment
            dW = np.random.normal(0, np.sqrt(dt))
            # GBM formula: dP = mu*P*dt + sigma*P*dW
            dP = (drift * prices[-1] * dt) + (volatility * prices[-1] * dW)
            new_price = prices[-1] + dP
            # Keep price in [0.01, 0.99] range
            new_price = np.clip(new_price, 0.01, 0.99)
            prices.append(new_price)
        
        # Create bid-ask spread (2-5% typical for prediction markets)
        spread_pct = np.random.uniform(0.02, 0.05, num_points)
        mid_prices = np.array(prices)
        bid_prices = mid_prices - (mid_prices * spread_pct / 2)
        ask_prices = mid_prices + (mid_prices * spread_pct / 2)
        
        # Generate timestamps
        timestamps = [start_time + timedelta(hours=i) for i in range(num_points)]
        
        df = pd.DataFrame({
            "timestamp": timestamps,
            "market_ticker": market_ticker,
            "bid_price": bid_prices,
            "ask_price": ask_prices,
            "mid_price": mid_prices,
            "volume": np.random.exponential(1000, num_points)
        })
        
        logger.info(f"Generated {num_points} synthetic price points for {market_ticker}")
        return df
    
    @staticmethod
    def generate_multiple_markets(
        market_tickers: List[str],
        num_points: int = 720,
        seed: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Generate synthetic data for multiple markets
        
        Args:
            market_tickers: List of market identifiers
            num_points: Points per market
            seed: Random seed
            
        Returns:
            Dictionary mapping ticker -> DataFrame
        """
        if seed is not None:
            np.random.seed(seed)
        
        results = {}
        for ticker in market_tickers:
            # Vary parameters per market
            start_price = np.random.uniform(0.4, 0.6)
            volatility = np.random.uniform(0.01, 0.03)
            
            results[ticker] = SyntheticMarketDataGenerator.generate_synthetic_prices(
                market_ticker=ticker,
                start_price=start_price,
                num_points=num_points,
                volatility=volatility
            )
        
        return results


class KalshiDataManager:
    """Manages market data fetching with caching and fallbacks"""
    
    def __init__(self, use_cache: bool = True):
        """
        Initialize market data manager
        
        Args:
            use_cache: Whether to use caching
        """
        self.api_client = KalshiAPIClient()
        self.synthetic_generator = SyntheticMarketDataGenerator()
        self.use_cache = use_cache
        self.cache_dir = os.path.join(DATA_DIR, "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info("KalshiDataManager initialized")
    
    def _get_cache_path(self, market_ticker: str, num_points: int = 720) -> str:
        """Get cache file path for ticker and requested horizon."""
        return os.path.join(self.cache_dir, f"market_{market_ticker}_{num_points}.json")
    
    def _load_from_cache(self, market_ticker: str, num_points: int = 720) -> Optional[pd.DataFrame]:
        """Load market data from cache"""
        cache_path = self._get_cache_path(market_ticker, num_points)
        
        if not os.path.exists(cache_path):
            return None
        
        # Check freshness
        file_age_hours = (time.time() - os.path.getmtime(cache_path)) / 3600
        if file_age_hours > CACHE_EXPIRY_HOURS:
            logger.info(f"Cache expired for {market_ticker}")
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            if len(df) < num_points:
                logger.info(
                    f"Cache for {market_ticker} has {len(df)} points, "
                    f"less than requested {num_points}; refetching"
                )
                return None

            if len(df) > num_points:
                df = df.sort_values("timestamp").tail(num_points).reset_index(drop=True)

            logger.info(f"Loaded {len(df)} market data points from cache")
            return df
        except Exception as e:
            logger.warning(f"Error loading cache: {e}")
            return None
    
    def _save_to_cache(self, df: pd.DataFrame, market_ticker: str, num_points: int = 720):
        """Save market data to cache"""
        try:
            cache_path = self._get_cache_path(market_ticker, num_points)
            df_copy = df.copy()
            df_copy["timestamp"] = df_copy["timestamp"].astype(str)
            with open(cache_path, 'w') as f:
                json.dump(df_copy.to_dict('records'), f)
            logger.info(f"Cached {len(df)} market data points")
        except Exception as e:
            logger.warning(f"Error saving cache: {e}")
    
    def fetch_market_data(
        self,
        market_ticker: str,
        num_points: int = 720,
        use_synthetic_fallback: bool = True
    ) -> pd.DataFrame:
        """
        Fetch market data with fallback to synthetic data
        
        Args:
            market_ticker: Market identifier
            use_synthetic_fallback: Generate synthetic data if API fails
            
        Returns:
            DataFrame with market prices
        """
        # Check cache first
        if self.use_cache:
            cached_df = self._load_from_cache(market_ticker, num_points)
            if cached_df is not None and not cached_df.empty:
                return cached_df

        # Large-horizon requests are expensive and often timeout on the public API.
        # Use synthetic backfill directly if allowed.
        if num_points > 1000 and use_synthetic_fallback:
            logger.info(
                f"Using synthetic backfill for {market_ticker} "
                f"({num_points} points requested)"
            )
            df = self.synthetic_generator.generate_synthetic_prices(
                market_ticker=market_ticker,
                num_points=num_points
            )
            self._save_to_cache(df, market_ticker, num_points)
            return df
        
        # Try real API
        if self.api_client.available:
            try:
                api_limit = max(1000, num_points * 2)
                df = self.api_client.get_market_prices(market_ticker, limit=api_limit)
                if not df.empty:
                    df = df.sort_values("timestamp").reset_index(drop=True)
                    if len(df) > num_points:
                        df = df.tail(num_points).reset_index(drop=True)

                    self._save_to_cache(df, market_ticker, num_points)
                    return df
            except Exception as e:
                logger.warning(f"API failed for {market_ticker}: {e}")
        
        # Fall back to synthetic data
        if use_synthetic_fallback:
            logger.warning(f"Using synthetic data for {market_ticker}")
            df = self.synthetic_generator.generate_synthetic_prices(
                market_ticker=market_ticker,
                num_points=num_points
            )
            self._save_to_cache(df, market_ticker, num_points)
            return df
        
        return pd.DataFrame()
    
    def fetch_all_configured_markets(
        self,
        num_points: int = 720,
        use_synthetic_fallback: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for all configured markets
        
        Args:
            use_synthetic_fallback: Use synthetic data if API fails
            
        Returns:
            Dictionary mapping market_ticker -> DataFrame
        """
        results = {}
        
        for category, market_tickers in KALSHI_MARKETS.items():
            logger.info(f"Fetching markets in category: {category}")
            
            for ticker in market_tickers:
                try:
                    df = self.fetch_market_data(
                        market_ticker=ticker,
                        num_points=num_points,
                        use_synthetic_fallback=use_synthetic_fallback
                    )
                    if not df.empty:
                        results[ticker] = df
                    time.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.error(f"Error fetching {ticker}: {e}")
        
        return results
    
    @staticmethod
    def clean_market_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and preprocess market data
        
        Args:
            df: Raw market data
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # Remove duplicates
        initial_count = len(df)
        df = df.drop_duplicates(subset=["timestamp", "market_ticker"], keep="last")
        logger.info(f"Removed {initial_count - len(df)} duplicate entries")
        
        # Fix prices (clip to [0, 1])
        df["bid_price"] = df["bid_price"].clip(0, 1)
        df["ask_price"] = df["ask_price"].clip(0, 1)
        df["mid_price"] = df["mid_price"].clip(0, 1)
        
        # Ensure bid <= ask
        mask = df["bid_price"] > df["ask_price"]
        df.loc[mask, ["bid_price", "ask_price"]] = df.loc[mask, ["ask_price", "bid_price"]].values
        
        # Recalculate mid_price
        df["mid_price"] = (df["bid_price"] + df["ask_price"]) / 2
        
        # Normalize timestamps
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        
        # Sort by timestamp
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        # Remove rows with missing critical fields
        df = df.dropna(subset=["timestamp", "market_ticker", "mid_price"]).reset_index(drop=True)
        
        logger.info(f"Cleaned data: {len(df)} records remaining")
        return df
    
    @staticmethod
    def compute_probability_from_price(
        price: float,
        inverse: bool = False
    ) -> float:
        """
        Convert market price to win probability
        
        Args:
            price: Market price (usually 0-1)
            inverse: If True, interpret price as NO probability
            
        Returns:
            Win probability (0-1)
        """
        if inverse:
            return 1 - price
        return price
    
    @staticmethod
    def compute_price_changes(
        df: pd.DataFrame,
        window_hours: int = 24
    ) -> pd.DataFrame:
        """
        Compute price changes over time windows
        
        Args:
            df: Market data
            window_hours: Window size in hours
            
        Returns:
            DataFrame with changes
        """
        df = df.copy().sort_values("timestamp")
        df["time_bin"] = df["timestamp"].dt.floor(f"{window_hours}h")
        
        changes = []
        for bin_time, group in df.groupby("time_bin"):
            if len(group) < 2:
                continue
            
            first_price = group.iloc[0]["mid_price"]
            last_price = group.iloc[-1]["mid_price"]
            price_change = last_price - first_price
            pct_change = (price_change / first_price * 100) if first_price > 0 else 0
            
            changes.append({
                "timestamp": bin_time,
                "start_price": first_price,
                "end_price": last_price,
                "price_change": price_change,
                "pct_change": pct_change,
                "high_price": group["mid_price"].max(),
                "low_price": group["mid_price"].min(),
                "avg_volume": group["volume"].mean(),
            })
        
        return pd.DataFrame(changes)
