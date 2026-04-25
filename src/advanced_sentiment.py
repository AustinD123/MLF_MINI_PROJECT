"""
Advanced Sentiment Analysis Module
Implements weighted sentiment scoring with multiple models
"""
import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Optional
from src.logger import setup_logger

logger = setup_logger("advanced_sentiment")

# Source reliability scores
SOURCE_WEIGHTS = {
    "reuters": 0.95,
    "bloomberg": 0.93,
    "wsj": 0.92,
    "wall street journal": 0.92,
    "cnbc": 0.85,
    "financial times": 0.90,
    "ft": 0.90,
}

# Keywords that increase headline relevance
MARKET_KEYWORDS = {
    "inflation": 1.2,
    "fed": 1.1,
    "central bank": 1.15,
    "interest rate": 1.1,
    "monetary policy": 1.15,
    "price": 0.9,
    "market": 0.9,
    "economic": 1.0,
    "dollar": 1.0,
    "commodity": 0.95,
}


class AdvancedSentimentAnalyzer:
    """Enhanced sentiment analysis with multiple models and weighting"""
    
    def __init__(self, model_type: str = "vader", use_weighting: bool = True):
        """
        Initialize advanced sentiment analyzer
        
        Args:
            model_type: "vader" or "finbert"
            use_weighting: Whether to apply source/keyword weighting
        """
        self.model_type = model_type
        self.use_weighting = use_weighting
        
        # Initialize base model
        if model_type == "vader":
            try:
                from nltk.sentiment import SentimentIntensityAnalyzer
                import nltk
                try:
                    nltk.data.find('vader_lexicon')
                except LookupError:
                    nltk.download('vader_lexicon', quiet=True)
                self.vader = SentimentIntensityAnalyzer()
                logger.info("VADER sentiment analyzer initialized")
            except ImportError:
                logger.error("VADER requires vaderSentiment")
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
                logger.error("FinBERT requires transformers and torch")
                raise
    
    def compute_source_weight(self, source: str) -> float:
        """
        Compute source reliability weight
        
        Args:
            source: News source name
            
        Returns:
            Weight in [0.5, 1.0] range
        """
        if not source:
            return 0.7
        
        source_lower = str(source).lower().strip()
        
        # Check for exact matches first
        for key, weight in SOURCE_WEIGHTS.items():
            if key in source_lower:
                return weight
        
        # Unknown sources get default weight
        return 0.7
    
    def compute_keyword_weight(self, text: str) -> float:
        """
        Compute keyword relevance weight
        
        Args:
            text: Headline text
            
        Returns:
            Weight multiplier for relevance
        """
        if not text:
            return 1.0
        
        text_lower = str(text).lower()
        weight = 1.0
        
        for keyword, multiplier in MARKET_KEYWORDS.items():
            if keyword.lower() in text_lower:
                weight = max(weight, multiplier)
        
        return weight
    
    def compute_length_weight(self, text: str) -> float:
        """
        Compute headline length weight
        
        Longer, more detailed headlines are more valuable
        
        Args:
            text: Headline text
            
        Returns:
            Weight based on length
        """
        if not text:
            return 0.5
        
        length = len(str(text).split())
        
        # Optimal length is 8-15 words
        if length < 4:
            return 0.6
        elif length < 8:
            return 0.8
        elif length <= 15:
            return 1.0
        elif length <= 25:
            return 0.95
        else:
            return 0.85
    
    def analyze_text(self, text: str) -> Tuple[float, str, float]:
        """
        Analyze sentiment of text
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (polarity_score, sentiment_label, confidence)
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
        
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"
        
        confidence = max(scores["pos"], scores["neg"], scores["neu"])
        
        return compound, label, confidence
    
    def _analyze_finbert(self, text: str) -> Tuple[float, str, float]:
        """FinBERT sentiment analysis"""
        import torch
        
        inputs = self.tokenizer(
            text[:512],
            return_tensors="pt",
            padding=True,
            truncation=True
        )
        
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)
        
        # FinBERT: 0=negative, 1=neutral, 2=positive
        probs_cpu = probs[0].cpu().numpy()
        pred_label = np.argmax(probs_cpu)
        confidence = float(np.max(probs_cpu))
        
        label_map = {0: "negative", 1: "neutral", 2: "positive"}
        label = label_map[pred_label]
        
        # Score: -1 to 1
        score = probs_cpu[2] - probs_cpu[0]  # positive - negative
        
        return score, label, confidence
    
    def compute_weighted_sentiment(self, headlines_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute weighted sentiment scores for headlines
        
        Args:
            headlines_df: DataFrame with columns [title, source, publishedAt, ...]
            
        Returns:
            DataFrame with added columns:
            - sentiment_score (raw)
            - sentiment_label
            - confidence
            - source_weight
            - keyword_weight
            - length_weight
            - article_weight (combined)
            - weighted_sentiment
        """
        df = headlines_df.copy()
        
        logger.info(f"Computing weighted sentiment for {len(df)} articles")
        
        # Get base sentiment scores
        sentiment_data = []
        for idx, row in df.iterrows():
            score, label, conf = self.analyze_text(row.get("title", ""))
            sentiment_data.append({
                "sentiment_score": score,
                "sentiment_label": label,
                "confidence": conf
            })
        
        sentiment_df = pd.DataFrame(sentiment_data)
        df = pd.concat([df, sentiment_df], axis=1)
        
        # Compute individual weights
        if self.use_weighting:
            df["source_weight"] = df["source"].apply(self.compute_source_weight)
            df["keyword_weight"] = df["title"].apply(self.compute_keyword_weight)
            df["length_weight"] = df["title"].apply(self.compute_length_weight)
            
            # Combined article weight (geometric mean of components)
            df["article_weight"] = (
                df["source_weight"] * 
                df["keyword_weight"] * 
                df["length_weight"]
            ) ** (1/3)
        else:
            df["source_weight"] = 1.0
            df["keyword_weight"] = 1.0
            df["length_weight"] = 1.0
            df["article_weight"] = 1.0
        
        # Weighted sentiment
        df["weighted_sentiment"] = df["sentiment_score"] * df["article_weight"]
        
        logger.info(
            f"Sentiment computed. Mean weighted sentiment: {df['weighted_sentiment'].mean():.3f}"
        )
        
        return df


def analyze_dataframe(
    df: pd.DataFrame,
    text_column: str = "title",
    model_type: str = "vader",
    use_weighting: bool = True
) -> pd.DataFrame:
    """
    Convenience function to analyze sentiment for a dataframe
    
    Args:
        df: Input dataframe
        text_column: Column containing text to analyze
        model_type: "vader" or "finbert"
        use_weighting: Apply source/keyword weighting
        
    Returns:
        DataFrame with sentiment columns added
    """
    analyzer = AdvancedSentimentAnalyzer(model_type=model_type, use_weighting=use_weighting)
    return analyzer.compute_weighted_sentiment(df)
