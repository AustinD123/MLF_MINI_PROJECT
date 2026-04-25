"""
Historical Dataset Loader
Loads news and market data from local CSV files
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Optional
import os
from src.logger import setup_logger

logger = setup_logger("dataset_loader")


class DJIADatasetLoader:
    """Loads DJIA news and market data from local CSV files"""
    
    def __init__(self, dataset_dir: str = "dataset"):
        """
        Initialize loader
        
        Args:
            dataset_dir: Path to dataset directory
        """
        self.dataset_dir = dataset_dir
        self.news_file = os.path.join(dataset_dir, "Combined_News_DJIA.csv")
        self.djia_file = os.path.join(dataset_dir, "upload_DJIA_table.csv")
        
        self._validate_files()
    
    def _validate_files(self):
        """Check that required files exist"""
        if not os.path.exists(self.news_file):
            logger.warning(f"News file not found: {self.news_file}")
        if not os.path.exists(self.djia_file):
            logger.warning(f"DJIA file not found: {self.djia_file}")
    
    def load_news(self, start_date: Optional[datetime] = None, 
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Load news data from CSV
        
        Args:
            start_date: Start date (optional)
            end_date: End date (optional)
            
        Returns:
            DataFrame with columns: [timestamp, headline, source, label]
        """
        try:
            df = pd.read_csv(self.news_file)
            logger.info(f"Loaded {len(df)} rows from {self.news_file}")
            
            # Convert Date column to datetime
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Filter by date range if provided
            if start_date:
                df = df[df['Date'] >= start_date]
            if end_date:
                df = df[df['Date'] <= end_date]
            
            logger.info(f"Filtered to {len(df)} rows in date range")
            
            # Melt top news headlines into individual rows
            # Columns are: Top1, Top2, ..., Top25
            news_cols = [col for col in df.columns if col.startswith('Top')]
            
            records = []
            for _, row in df.iterrows():
                date = row['Date']
                label = row['Label']
                
                for col in news_cols:
                    headline = str(row[col]).strip()
                    
                    # Clean up headline (remove b' Python representation)
                    if headline.startswith("b'") or headline.startswith('b"'):
                        headline = headline[2:-1]
                    if headline.startswith('"') or headline.startswith("'"):
                        headline = headline[1:-1]
                    
                    if headline and len(headline) > 10:
                        records.append({
                            'timestamp': date,
                            'headline': headline,
                            'source': 'Reddit',
                            'label': label,  # 0=down, 1=up
                        })
            
            result_df = pd.DataFrame(records)
            logger.info(f"Extracted {len(result_df)} individual news headlines")
            return result_df
            
        except Exception as e:
            logger.error(f"Error loading news: {e}")
            return pd.DataFrame()
    
    def load_djia(self, start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Load DJIA price data from CSV
        
        Args:
            start_date: Start date (optional)
            end_date: End date (optional)
            
        Returns:
            DataFrame with columns: [timestamp, open, high, low, close, volume, mid_price]
        """
        try:
            df = pd.read_csv(self.djia_file)
            logger.info(f"Loaded {len(df)} rows from {self.djia_file}")
            
            # Convert Date column to datetime
            df['Date'] = pd.to_datetime(df['Date'])
            
            # Rename for consistency
            df.rename(columns={
                'Date': 'timestamp',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Adj Close': 'adj_close'
            }, inplace=True)
            
            # Compute mid price (average of high and low)
            df['mid_price'] = (df['high'] + df['low']) / 2
            
            # Normalize prices to 0-1 range (like prediction market)
            price_min = df['close'].min()
            price_max = df['close'].max()
            df['normalized_price'] = (df['close'] - price_min) / (price_max - price_min)
            
            # Filter by date range if provided
            if start_date:
                df = df[df['timestamp'] >= start_date]
            if end_date:
                df = df[df['timestamp'] <= end_date]
                
            logger.info(f"Filtered to {len(df)} rows in date range")
            logger.info(f"Price range: {df['close'].min():.2f} to {df['close'].max():.2f}")
            
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'mid_price', 'normalized_price']]
            
        except Exception as e:
            logger.error(f"Error loading DJIA: {e}")
            return pd.DataFrame()
    
    def load_aligned_dataset(self, start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load both news and DJIA data
        
        Args:
            start_date: Start date (optional)
            end_date: End date (optional)
            
        Returns:
            Tuple of (news_df, djia_df)
        """
        news_df = self.load_news(start_date, end_date)
        djia_df = self.load_djia(start_date, end_date)
        
        logger.info(f"Loaded dataset: {len(news_df)} news items, {len(djia_df)} DJIA prices")
        
        return news_df, djia_df
    
    def get_date_range(self) -> Tuple[datetime, datetime]:
        """Get available date range in datasets"""
        try:
            news_df = pd.read_csv(self.news_file)
            news_df['Date'] = pd.to_datetime(news_df['Date'])
            news_min = news_df['Date'].min()
            news_max = news_df['Date'].max()
            
            djia_df = pd.read_csv(self.djia_file)
            djia_df['Date'] = pd.to_datetime(djia_df['Date'])
            djia_min = djia_df['Date'].min()
            djia_max = djia_df['Date'].max()
            
            combined_min = max(news_min, djia_min)
            combined_max = min(news_max, djia_max)
            
            logger.info(f"Available date range: {combined_min.date()} to {combined_max.date()}")
            
            return combined_min, combined_max
        except Exception as e:
            logger.error(f"Error getting date range: {e}")
            return None, None
