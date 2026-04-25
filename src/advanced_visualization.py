"""
Advanced Visualization Module
Research-quality plots for sentiment-market analysis
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional
import os

from src.logger import setup_logger

logger = setup_logger("advanced_visualization")

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['lines.linewidth'] = 2


class ResearchVisualizer:
    """Create publication-quality visualizations"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def plot_sentiment_market_overlay(
        self,
        data: pd.DataFrame,
        title: str = "Sentiment vs Market Probability",
        filename: Optional[str] = None
    ) -> str:
        """Plot sentiment and market probability overlaid"""
        fig, ax1 = plt.subplots(figsize=(14, 7))
        
        # Sentiment
        ax1.plot(data["timestamp"], data["mean_sentiment"], 
                 label="Sentiment Score", color="steelblue", linewidth=2)
        ax1.fill_between(data["timestamp"], data["mean_sentiment"], 
                         alpha=0.3, color="steelblue")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Sentiment Score", color="steelblue")
        ax1.tick_params(axis='y', labelcolor="steelblue")
        
        # Market price on secondary axis
        ax2 = ax1.twinx()
        ax2.plot(data["timestamp"], data["mid_price"],
                 label="Market Price", color="coral", linewidth=2, linestyle='--')
        ax2.set_ylabel("Market Price", color="coral")
        ax2.tick_params(axis='y', labelcolor="coral")
        
        # Legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.title(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if filename:
            filepath = os.path.join(self.output_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            logger.info(f"Saved: {filepath}")
        else:
            filepath = os.path.join(self.output_dir, "sentiment_market_overlay.png")
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
        
        plt.close()
        return filepath
    
    def plot_lag_correlation(
        self,
        lag_df: pd.DataFrame,
        optimal_lag: Optional[Dict] = None,
        filename: Optional[str] = None
    ) -> str:
        """Plot lag correlation function"""
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Plot correlations
        ax.bar(lag_df["lag"], lag_df["correlation"], color="steelblue", alpha=0.7)
        ax.axhline(0, color="black", linestyle="-", linewidth=0.8)
        
        # Highlight optimal lag
        if optimal_lag:
            opt_lag = optimal_lag["optimal_lag"]
            opt_corr = optimal_lag["correlation_at_lag"]
            ax.scatter([opt_lag], [opt_corr], color="red", s=200, zorder=5,
                      label=f"Optimal Lag: {opt_lag}h")
            ax.legend(fontsize=11)
        
        ax.set_xlabel("Lag (hours)", fontsize=12)
        ax.set_ylabel("Correlation", fontsize=12)
        ax.set_title("Cross-Correlation: Sentiment vs Price", fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if filename:
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = os.path.join(self.output_dir, "lag_correlation.png")
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {filepath}")
        plt.close()
        
        return filepath
    
    def plot_feature_importance(
        self,
        feature_importance: Dict[str, float],
        n_top: int = 15,
        filename: Optional[str] = None
    ) -> str:
        """Plot feature importance from Random Forest"""
        # Sort and take top N
        top_features = dict(sorted(
            feature_importance.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:n_top])
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        features = list(top_features.keys())
        importances = list(top_features.values())
        
        # Horizontal bar plot
        y_pos = np.arange(len(features))
        colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(features)))
        
        ax.barh(y_pos, importances, color=colors)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features, fontsize=10)
        ax.set_xlabel("Importance", fontsize=12)
        ax.set_title(f"Top {n_top} Feature Importance (Random Forest)", 
                    fontsize=14, fontweight='bold')
        ax.invert_yaxis()
        
        # Add value labels
        for i, v in enumerate(importances):
            ax.text(v + 0.002, i, f"{v:.4f}", va='center', fontsize=9)
        
        plt.tight_layout()
        
        if filename:
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = os.path.join(self.output_dir, "feature_importance.png")
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {filepath}")
        plt.close()
        
        return filepath
    
    def plot_event_markers(
        self,
        events_df: pd.DataFrame,
        price_data: pd.DataFrame,
        filename: Optional[str] = None
    ) -> str:
        """Plot detected events on price timeline"""
        fig, ax = plt.subplots(figsize=(16, 7))
        
        # Price line
        ax.plot(price_data["timestamp"], price_data["mid_price"], 
               color="steelblue", linewidth=2, label="Price", zorder=3)
        
        # Event markers
        events_only = events_df[events_df["is_event"] == 1]
        
        event_colors = {
            "sentiment_spike": "orange",
            "volume_spike": "green",
            "sentiment_volume_spike": "red"
        }
        
        for event_type, color in event_colors.items():
            events_type = events_only[events_only["event_type"] == event_type]
            if len(events_type) > 0:
                ax.scatter(events_type["timestamp"], events_type["mid_price"],
                          color=color, s=200, marker='^', alpha=0.7,
                          label=event_type.replace("_", " ").title(), zorder=5)
        
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Market Price", fontsize=12)
        ax.set_title("Detected Events on Market Timeline", fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if filename:
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = os.path.join(self.output_dir, "event_markers.png")
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {filepath}")
        plt.close()
        
        return filepath
    
    def plot_sentiment_distribution(
        self,
        sentiment_data: pd.Series,
        filename: Optional[str] = None
    ) -> str:
        """Plot sentiment distribution"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Histogram
        ax.hist(sentiment_data, bins=50, color="steelblue", alpha=0.7, edgecolor='black')
        
        # Mean and std
        mean = sentiment_data.mean()
        std = sentiment_data.std()
        ax.axvline(mean, color="red", linestyle="--", linewidth=2, label=f"Mean={mean:.3f}")
        ax.axvline(mean - std, color="orange", linestyle=":", linewidth=2, label=f"±1σ")
        ax.axvline(mean + std, color="orange", linestyle=":", linewidth=2)
        
        ax.set_xlabel("Sentiment Score", fontsize=12)
        ax.set_ylabel("Frequency", fontsize=12)
        ax.set_title("Distribution of Sentiment Scores", fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        if filename:
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = os.path.join(self.output_dir, "sentiment_distribution.png")
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {filepath}")
        plt.close()
        
        return filepath
    
    def plot_model_predictions_vs_actual(
        self,
        y_true: np.ndarray,
        y_pred_lr: np.ndarray,
        y_pred_rf: np.ndarray,
        filename: Optional[str] = None
    ) -> str:
        """Plot model predictions vs actual values"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Linear Regression
        ax = axes[0]
        ax.scatter(y_true, y_pred_lr, alpha=0.6, s=30)
        min_val, max_val = y_true.min(), y_true.max()
        ax.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2)
        ax.set_xlabel("Actual Price Change", fontsize=11)
        ax.set_ylabel("Predicted Price Change", fontsize=11)
        ax.set_title("Linear Regression", fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Random Forest
        ax = axes[1]
        ax.scatter(y_true, y_pred_rf, alpha=0.6, s=30, color="green")
        ax.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2)
        ax.set_xlabel("Actual Price Change", fontsize=11)
        ax.set_ylabel("Predicted Price Change", fontsize=11)
        ax.set_title("Random Forest", fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        fig.suptitle("Model Predictions vs Actual Values", fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if filename:
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = os.path.join(self.output_dir, "predictions_vs_actual.png")
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {filepath}")
        plt.close()
        
        return filepath
    
    def plot_news_volume_vs_price(
        self,
        data: pd.DataFrame,
        news_col: str = "article_count",
        price_col: str = "mid_price",
        title: str = "News Volume vs Market Probability",
        filename: Optional[str] = None
    ) -> str:
        """
        Plot news article volume overlaid with market prices
        
        Args:
            data: DataFrame with aligned news and market data
            news_col: Column name for news volume
            price_col: Column name for market price
            title: Plot title
            filename: Output filename
            
        Returns:
            Path to saved figure
        """
        fig, ax1 = plt.subplots(figsize=(14, 7))
        
        # News volume as bar chart
        if news_col in data.columns:
            ax1.bar(data["timestamp"], data[news_col], 
                   label="News Article Count", color="lightcoral", alpha=0.7, width=0.8)
            ax1.set_ylabel("Article Count", color="darkred", fontsize=11)
            ax1.tick_params(axis='y', labelcolor="darkred")
        
        # Market price on secondary axis
        ax2 = ax1.twinx()
        if price_col in data.columns:
            ax2.plot(data["timestamp"], data[price_col],
                    label="Market Probability", color="steelblue", linewidth=2.5, marker='o', markersize=4)
            ax2.set_ylabel("Market Probability", color="steelblue", fontsize=11)
            ax2.tick_params(axis='y', labelcolor="steelblue")
            
            # Add fill for price
            ax2.fill_between(data["timestamp"], data[price_col], 
                            alpha=0.2, color="steelblue")
        
        ax1.set_xlabel("Date", fontsize=11)
        ax1.set_title(title, fontsize=14, fontweight='bold')
        
        # Combine legends
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)
        
        ax1.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if filename:
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = os.path.join(self.output_dir, "news_volume_vs_price.png")
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {filepath}")
        plt.close()
        
        return filepath


def create_research_report(
    results: Dict,
    output_dir: str = "output"
) -> str:
    """Create comprehensive research report"""
    filepath = os.path.join(output_dir, "research_report.txt")
    
    with open(filepath, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("SENTIMENT-MARKET ANALYSIS: COMPREHENSIVE RESEARCH REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        # Correlation results
        if "optimal_lag" in results:
            f.write("LAG ANALYSIS\n")
            f.write("-" * 80 + "\n")
            lag_info = results["optimal_lag"]
            f.write(f"Optimal Lag: {lag_info['optimal_lag']} hours\n")
            f.write(f"Correlation at Lag: {lag_info['correlation_at_lag']:.4f}\n")
            f.write(f"P-value: {lag_info['pvalue_at_lag']:.6f}\n")
            f.write(f"Significant: {lag_info['significant']}\n")
            f.write(f"Interpretation: {lag_info['interpretation']}\n\n")
        
        # Event detection
        if "events" in results:
            f.write("EVENT DETECTION\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Events Detected: {results['events']['event_count']}\n")
            if results['events']['event_types']:
                f.write("Event Types:\n")
                for event_type, count in results['events']['event_types'].items():
                    f.write(f"  - {event_type}: {count}\n")
            f.write("\n")
        
        # Model results
        if "models" in results:
            f.write("PREDICTIVE MODELS\n")
            f.write("-" * 80 + "\n")
            
            lr = results['models']['linear_regression']
            f.write(f"\nLinear Regression:\n")
            f.write(f"  Train R²: {lr.get('r2_train', 'N/A')}\n")
            f.write(f"  CV R² (mean ± std): {lr.get('cv_r2_mean', 'N/A')} ± {lr.get('cv_r2_std', 'N/A')}\n")
            if 'r2' in lr:
                f.write(f"  Test R²: {lr['r2']:.4f}\n")
                f.write(f"  Test MAE: {lr['mae']:.4f}\n")
            
            rf = results['models']['random_forest']
            f.write(f"\nRandom Forest:\n")
            f.write(f"  Train R²: {rf.get('r2_train', 'N/A')}\n")
            f.write(f"  CV R² (mean ± std): {rf.get('cv_r2_mean', 'N/A')} ± {rf.get('cv_r2_std', 'N/A')}\n")
            if 'r2' in rf:
                f.write(f"  Test R²: {rf['r2']:.4f}\n")
                f.write(f"  Test MAE: {rf['mae']:.4f}\n")
            
            if 'top_features' in rf:
                f.write(f"\nTop Predictive Features:\n")
                for i, feature in enumerate(rf['top_features'][:5], 1):
                    f.write(f"  {i}. {feature}\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    logger.info(f"Research report saved: {filepath}")
    return filepath
