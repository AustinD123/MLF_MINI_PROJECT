"""
Market Data Collection Module
Fetches Kalshi prediction market data
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from src.config import (
    KALSHI_API_URL, KALSHI_API_KEY, KALSHI_TIMEOUT,
    KALSHI_MARKETS, MAX_RETRIES, RETRY_DELAY_SECONDS
)
from src.logger import setup_logger
import time

logger = setup_logger("market_data")


class KalshiMarketCollector:
    """Collects prediction market data from Kalshi"""
    
    def __init__(self, api_key: str = KALSHI_API_KEY):
        self.api_key = api_key
        self.base_url = KALSHI_API_URL
        self.timeout = KALSHI_TIMEOUT
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
    
    def fetch_market_prices(
        self,
        market_slug: str,
        days_back: int = 30
    ) -> pd.DataFrame:
        """
        Fetch price history for a market.
        
        Args:
            market_slug: Market identifier (e.g., "CPI-INFLATION-2024-04")
            days_back: Days of history to retrieve
            
        Returns:
            DataFrame with columns: [timestamp, mid_price, yes_price, no_price, volume]
        """
        from_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
        
        url = f"{self.base_url}/markets/{market_slug}/prices"
        params = {
            "from": from_date,
            "limit": 1000
        }
        
        prices = []
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                logger.info(f"Fetching prices for market: {market_slug}")
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                
                for tick in data.get("data", {}).get("ticks", []):
                    prices.append({
                        "timestamp": pd.to_datetime(tick.get("created_time")),
                        "yes_price": float(tick.get("yes_price", 0)),
                        "no_price": float(tick.get("no_price", 0)),
                        "mid_price": (float(tick.get("yes_price", 0.5)) + float(tick.get("no_price", 0.5))) / 2,
                        "volume": float(tick.get("volume", 0)),
                    })
                
                logger.info(f"Successfully fetched {len(prices)} price ticks")
                break
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                logger.warning(f"Request failed (attempt {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error("Max retries exceeded")
            except (KeyError, ValueError) as e:
                logger.error(f"Error parsing response: {e}")
                break
        
        if not prices:
            logger.warning(f"No prices retrieved for market: {market_slug}")
            return pd.DataFrame()
        
        df = pd.DataFrame(prices)
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        # Remove duplicates
        df = df.drop_duplicates(subset=["timestamp"], keep="last")
        
        return df
    
    def fetch_market_info(self, market_slug: str) -> Dict:
        """
        Fetch market metadata.
        
        Args:
            market_slug: Market identifier
            
        Returns:
            Dictionary with market info
        """
        url = f"{self.base_url}/markets/{market_slug}"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            market_info = data.get("data", {})
            logger.info(f"Retrieved info for market: {market_slug}")
            
            return {
                "slug": market_info.get("slug"),
                "title": market_info.get("title"),
                "description": market_info.get("description"),
                "category": market_info.get("category"),
                "close_time": market_info.get("close_time"),
                "is_binary": market_info.get("is_binary", True),
            }
        
        except Exception as e:
            logger.error(f"Error fetching market info: {e}")
            return {}
    
    def fetch_all_markets(
        self,
        markets_dict: Dict = KALSHI_MARKETS
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for all configured markets.
        
        Args:
            markets_dict: Dictionary mapping category -> list of market slugs
            
        Returns:
            Dictionary mapping market_slug -> DataFrame
        """
        results = {}
        
        for category, market_slugs in markets_dict.items():
            logger.info(f"Fetching markets in category: {category}")
            
            for market_slug in market_slugs:
                try:
                    df = self.fetch_market_prices(market_slug)
                    if not df.empty:
                        results[market_slug] = df
                    time.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Error fetching {market_slug}: {e}")
        
        return results
    
    def compute_probability_changes(
        self,
        df: pd.DataFrame,
        window_minutes: int = 60
    ) -> pd.DataFrame:
        """
        Compute probability changes over time windows.
        
        Args:
            df: Market price DataFrame
            window_minutes: Time window in minutes
            
        Returns:
            DataFrame with changes
        """
        df_copy = df.copy()
        df_copy = df_copy.sort_values("timestamp")
        
        # Create time bins
        df_copy["time_bin"] = df_copy["timestamp"].dt.floor(f"{window_minutes}T")
        
        # Get first and last prices in each window
        changes = []
        for bin_time, group in df_copy.groupby("time_bin"):
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
                "tick_count": len(group),
                "volume": group["volume"].sum(),
            })
        
        return pd.DataFrame(changes)
    
    def detect_price_jumps(
        self,
        df: pd.DataFrame,
        threshold_pct: float = 2.0
    ) -> pd.DataFrame:
        """
        Detect significant price jumps.
        
        Args:
            df: Market price DataFrame
            threshold_pct: Percentage change threshold
            
        Returns:
            DataFrame of detected jumps
        """
        df_copy = df.copy()
        df_copy = df_copy.sort_values("timestamp")
        
        df_copy["price_change"] = df_copy["mid_price"].diff()
        df_copy["pct_change"] = (df_copy["price_change"] / df_copy["mid_price"].shift()) * 100
        
        jumps = df_copy[df_copy["pct_change"].abs() > threshold_pct].copy()
        
        logger.info(f"Detected {len(jumps)} significant price jumps (>{threshold_pct}%)")
        
        return jumps
    
    def resample_prices(
        self,
        df: pd.DataFrame,
        freq: str = "1H"
    ) -> pd.DataFrame:
        """
        Resample prices to regular interval using forward-fill.
        
        Args:
            df: Market price DataFrame (must have timestamp index)
            freq: Resampling frequency (e.g., '1H', '4H', '1D')
            
        Returns:
            Resampled DataFrame
        """
        df_copy = df.copy()
        df_copy = df_copy.set_index("timestamp")
        
        # Resample and forward-fill
        resampled = df_copy.resample(freq).first().fillna(method="ffill")
        
        return resampled.reset_index()


class MockKalshiDataGenerator:
    """Generate synthetic Kalshi market data for testing"""
    
    @staticmethod
    def generate_synthetic_prices(
        start_price: float = 0.50,
        num_points: int = 100,
        volatility: float = 0.02,
        drift: float = 0.001
    ) -> pd.DataFrame:
        """
        Generate synthetic market prices using geometric Brownian motion.
        
        Args:
            start_price: Initial price
            num_points: Number of price points
            volatility: Daily volatility
            drift: Daily drift
            
        Returns:
            DataFrame with synthetic prices
        """
        np.random.seed(42)
        
        prices = [start_price]
        timestamps = [datetime.utcnow() - timedelta(hours=num_points)]
        
        for i in range(1, num_points):
            dW = np.random.normal(0, 1)
            dt = 1 / 24  # Daily timesteps
            
            price = prices[-1] * np.exp(
                (drift - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * dW
            )
            # Clip to [0, 1] for probability
            price = np.clip(price, 0.01, 0.99)
            prices.append(price)
            timestamps.append(timestamps[-1] + timedelta(hours=1))
        
        df = pd.DataFrame({
            "timestamp": timestamps,
            "mid_price": prices,
            "yes_price": [p + np.random.normal(0, 0.01) for p in prices],
            "no_price": [1 - p + np.random.normal(0, 0.01) for p in prices],
            "volume": np.random.exponential(1000, num_points)
        })
        
        return df
