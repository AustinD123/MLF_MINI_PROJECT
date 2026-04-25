"""
Sentiment Analysis Module
Computes sentiment scores for news headlines
"""
import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Optional
from src.config import SENTIMENT_MODEL, VADER_NEUTRAL_THRESHOLD, SENTIMENT_WINDOW_HOURS
from src.logger import setup_logger

logger = setup_logger("sentiment_analyzer")


class SentimentAnalyzer:
    """Computes sentiment scores from text"""
    
    def __init__(self, model_type: str = SENTIMENT_MODEL):
        self.model_type = model_type
        
        if model_type == "vader":
            try:
                from nltk.sentiment import SentimentIntensityAnalyzer
                import nltk
                
                # Download VADER lexicon if needed
                try:
                    nltk.data.find('vader_lexicon')
                except LookupError:
                    nltk.download('vader_lexicon', quiet=True)
                
                self.vader = SentimentIntensityAnalyzer()
                logger.info("VADER sentiment analyzer initialized")
            except ImportError:
                logger.error("VADER requires: pip install vaderSentiment")
                raise
                
        elif model_type == "finbert":
            try:
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                import torch
                
                model_name = "ProsusAI/finbert"
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                self.model.to(self.device)
                logger.info(f"FinBERT model initialized on {self.device}")
            except ImportError:
                logger.error("FinBERT requires: pip install transformers torch")
                raise
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def analyze_text(self, text: str) -> Tuple[float, str, float]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (polarity_score, sentiment_label, confidence)
            - polarity_score: [-1, 1] range
            - sentiment_label: "positive", "negative", "neutral"
            - confidence: [0, 1] confidence score
        """
        if not text or len(str(text).strip()) == 0:
            return 0.0, "neutral", 0.0
        
        if self.model_type == "vader":
            return self._analyze_vader(text)
        elif self.model_type == "finbert":
            return self._analyze_finbert(text)
    
    def _analyze_vader(self, text: str) -> Tuple[float, str, float]:
        """VADER sentiment analysis"""
        scores = self.vader.polarity_scores(text)
        compound = scores["compound"]
        
        # Classify sentiment
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"
        
        # Confidence approximation (max of component scores)
        confidence = max(scores["pos"], scores["neg"], scores["neu"])
        
        return compound, label, confidence
    
    def _analyze_finbert(self, text: str, max_length: int = 512) -> Tuple[float, str, float]:
        """FinBERT sentiment analysis"""
        import torch
        
        # Tokenize and truncate
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=max_length
        ).to(self.device)
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Get probabilities
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        scores = probs.cpu().numpy()[0]
        
        # FinBERT outputs: [negative, neutral, positive]
        label_map = {0: "negative", 1: "neutral", 2: "positive"}
        label_idx = np.argmax(scores)
        label = label_map[label_idx]
        confidence = float(scores[label_idx])
        
        # Convert to [-1, 1] scale
        polarity = float(scores[2] - scores[0])  # positive - negative
        
        return polarity, label, confidence
    
    def analyze_headlines(self, headlines: List[str]) -> pd.DataFrame:
        """
        Analyze sentiment for multiple headlines.
        
        Args:
            headlines: List of headline texts
            
        Returns:
            DataFrame with columns: [headline, polarity, label, confidence]
        """
        results = []
        
        for headline in headlines:
            try:
                polarity, label, confidence = self.analyze_text(headline)
                results.append({
                    "headline": headline,
                    "polarity": polarity,
                    "label": label,
                    "confidence": confidence
                })
            except Exception as e:
                logger.warning(f"Error analyzing headline: {e}")
                results.append({
                    "headline": headline,
                    "polarity": 0.0,
                    "label": "neutral",
                    "confidence": 0.0
                })
        
        return pd.DataFrame(results)
    
    def analyze_dataframe(
        self,
        df: pd.DataFrame,
        text_column: str = "title"
    ) -> pd.DataFrame:
        """
        Add sentiment columns to DataFrame.
        
        Args:
            df: DataFrame with news articles
            text_column: Column name containing text to analyze
            
        Returns:
            DataFrame with added columns: [sentiment_polarity, sentiment_label, sentiment_confidence]
        """
        df_copy = df.copy()
        
        logger.info(f"Analyzing sentiment for {len(df_copy)} articles")
        
        results = self.analyze_headlines(df_copy[text_column].tolist())
        
        df_copy["sentiment_polarity"] = results["polarity"]
        df_copy["sentiment_label"] = results["label"]
        df_copy["sentiment_confidence"] = results["confidence"]
        
        return df_copy
    
    def aggregate_sentiment(
        self,
        df: pd.DataFrame,
        time_column: str = "publishedAt",
        window_hours: int = SENTIMENT_WINDOW_HOURS
    ) -> pd.DataFrame:
        """
        Aggregate sentiment over time windows.
        
        Args:
            df: DataFrame with sentiment columns
            time_column: Timestamp column
            window_hours: Aggregation window in hours
            
        Returns:
            DataFrame with aggregated sentiment metrics:
            [timestamp, mean_sentiment, median_sentiment, std_sentiment, 
             positive_count, negative_count, neutral_count, article_count]
        """
        df_copy = df.copy()
        df_copy[time_column] = pd.to_datetime(df_copy[time_column])
        
        # Create time bins (use lowercase 'h' for modern pandas)
        df_copy["time_bin"] = df_copy[time_column].dt.floor(f"{window_hours}h")
        
        # Aggregate manually to avoid multi-level column issues
        agg_list = []
        for bin_time, group in df_copy.groupby("time_bin"):
            agg_list.append({
                "timestamp": bin_time,
                "mean_sentiment": group["sentiment_polarity"].mean(),
                "median_sentiment": group["sentiment_polarity"].median(),
                "std_sentiment": group["sentiment_polarity"].std(),
                "article_count": len(group),
                "positive_count": (group["sentiment_label"] == "positive").sum(),
                "negative_count": (group["sentiment_label"] == "negative").sum(),
                "neutral_count": (group["sentiment_label"] == "neutral").sum(),
            })
        
        agg_df = pd.DataFrame(agg_list)
        
        # Handle edge cases
        agg_df["std_sentiment"] = agg_df["std_sentiment"].fillna(0)
        
        logger.info(f"Aggregated sentiment into {len(agg_df)} time windows")
        
        return agg_df
