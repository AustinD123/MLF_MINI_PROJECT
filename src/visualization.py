"""
Visualization Module
Generates plots and charts for analysis
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Optional, Tuple, Dict, List
from src.config import OUTPUT_DIR, OUTPUT_DPI, FIGURE_SIZE_SMALL, FIGURE_SIZE_LARGE, COLORS
from src.logger import setup_logger
import os

logger = setup_logger("visualization")

# Set style
sns.set_style("darkgrid")
plt.rcParams["figure.facecolor"] = "white"


class TimeSeriesVisualizer:
    """Creates visualizations for time series analysis"""
    
    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def save_figure(self, fig: plt.Figure, filename: str) -> str:
        """
        Save figure to file.
        
        Args:
            fig: Matplotlib figure object
            filename: Output filename
            
        Returns:
            Full path to saved file
        """
        filepath = os.path.join(self.output_dir, filename)
        fig.savefig(filepath, dpi=OUTPUT_DPI, bbox_inches="tight")
        logger.info(f"Saved figure to {filepath}")
        return filepath
    
    def plot_sentiment_timeline(
        self,
        sentiment_df: pd.DataFrame,
        title: str = "Sentiment Timeline",
        figsize: Tuple = FIGURE_SIZE_SMALL,
        save_as: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot sentiment over time with positive/negative shading.
        
        Args:
            sentiment_df: DataFrame with timestamp, mean_sentiment, std_sentiment
            title: Plot title
            figsize: Figure size
            save_as: Optional filename to save
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot mean with error bands
        ax.plot(
            sentiment_df["timestamp"],
            sentiment_df["mean_sentiment"],
            linewidth=2,
            color=COLORS["sentiment"],
            label="Mean Sentiment"
        )
        
        # Add confidence band
        ax.fill_between(
            sentiment_df["timestamp"],
            sentiment_df["mean_sentiment"] - sentiment_df["std_sentiment"],
            sentiment_df["mean_sentiment"] + sentiment_df["std_sentiment"],
            alpha=0.3,
            color=COLORS["sentiment"],
            label="±1 Std Dev"
        )
        
        # Zero line
        ax.axhline(y=0, color="black", linestyle="--", alpha=0.3, linewidth=1)
        
        # Shading for positive/negative
        ax.fill_between(
            sentiment_df["timestamp"],
            sentiment_df["mean_sentiment"],
            0,
            where=sentiment_df["mean_sentiment"] >= 0,
            alpha=0.2,
            color=COLORS["positive"],
            label="Positive"
        )
        ax.fill_between(
            sentiment_df["timestamp"],
            sentiment_df["mean_sentiment"],
            0,
            where=sentiment_df["mean_sentiment"] < 0,
            alpha=0.2,
            color=COLORS["negative"],
            label="Negative"
        )
        
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Sentiment Score", fontsize=12)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_as:
            self.save_figure(fig, save_as)
        
        return fig
    
    def plot_market_probability(
        self,
        market_df: pd.DataFrame,
        title: str = "Market Probability Timeline",
        figsize: Tuple = FIGURE_SIZE_SMALL,
        save_as: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot market price (probability) over time.
        
        Args:
            market_df: DataFrame with timestamp, mid_price, yes_price, no_price
            title: Plot title
            figsize: Figure size
            save_as: Optional filename to save
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot mid price
        ax.plot(
            market_df["timestamp"],
            market_df["mid_price"],
            linewidth=2,
            color=COLORS["market"],
            label="Mid Price (Probability)"
        )
        
        # Plot bid-ask spread
        if "yes_price" in market_df.columns and "no_price" in market_df.columns:
            ax.fill_between(
                market_df["timestamp"],
                market_df["yes_price"],
                market_df["no_price"],
                alpha=0.2,
                color=COLORS["market"],
                label="Bid-Ask Spread"
            )
        
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Price (Probability)", fontsize=12)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0, 1])
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_as:
            self.save_figure(fig, save_as)
        
        return fig
    
    def plot_aligned_series(
        self,
        aligned_df: pd.DataFrame,
        sentiment_col: str = "mean_sentiment",
        market_col: str = "mid_price",
        title: str = "Aligned Sentiment and Market Probability",
        figsize: Tuple = FIGURE_SIZE_LARGE,
        save_as: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot sentiment and market probability on same chart (normalized).
        
        Args:
            aligned_df: Aligned DataFrame with both sentiment and market columns
            sentiment_col: Sentiment column name
            market_col: Market column name
            title: Plot title
            figsize: Figure size
            save_as: Optional filename to save
            
        Returns:
            Matplotlib figure
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True)
        
        # Normalize both series to [0, 1] for visualization
        sentiment_norm = (aligned_df[sentiment_col] - aligned_df[sentiment_col].min()) / \
                        (aligned_df[sentiment_col].max() - aligned_df[sentiment_col].min())
        market_norm = (aligned_df[market_col] - aligned_df[market_col].min()) / \
                     (aligned_df[market_col].max() - aligned_df[market_col].min())
        
        # Top plot: sentiment
        ax1.plot(
            aligned_df["timestamp"],
            aligned_df[sentiment_col],
            linewidth=2,
            color=COLORS["sentiment"],
            marker="o",
            markersize=4
        )
        ax1.axhline(y=0, color="black", linestyle="--", alpha=0.3)
        ax1.fill_between(
            aligned_df["timestamp"],
            aligned_df[sentiment_col],
            0,
            where=aligned_df[sentiment_col] >= 0,
            alpha=0.2,
            color=COLORS["positive"]
        )
        ax1.fill_between(
            aligned_df["timestamp"],
            aligned_df[sentiment_col],
            0,
            where=aligned_df[sentiment_col] < 0,
            alpha=0.2,
            color=COLORS["negative"]
        )
        ax1.set_ylabel("Sentiment Score", fontsize=11)
        ax1.set_title(f"{title} - Sentiment", fontsize=12, fontweight="bold")
        ax1.grid(True, alpha=0.3)
        
        # Bottom plot: market price
        ax2.plot(
            aligned_df["timestamp"],
            aligned_df[market_col],
            linewidth=2,
            color=COLORS["market"],
            marker="s",
            markersize=4
        )
        ax2.set_ylabel("Market Price", fontsize=11)
        ax2.set_xlabel("Time", fontsize=11)
        ax2.set_title(f"{title} - Market Price", fontsize=12, fontweight="bold")
        ax2.set_ylim([0, 1])
        ax2.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_as:
            self.save_figure(fig, save_as)
        
        return fig
    
    def plot_rolling_correlation(
        self,
        rolling_corr_df: pd.DataFrame,
        title: str = "Rolling Correlation (Sentiment vs Price)",
        figsize: Tuple = FIGURE_SIZE_SMALL,
        save_as: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot rolling correlation with significance shading.
        
        Args:
            rolling_corr_df: DataFrame with timestamp, correlation, significant
            title: Plot title
            figsize: Figure size
            save_as: Optional filename to save
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot correlation
        ax.plot(
            rolling_corr_df["timestamp"],
            rolling_corr_df["correlation"],
            linewidth=2,
            color="darkblue",
            label="Correlation"
        )
        
        # Shade significant periods
        significant = rolling_corr_df[rolling_corr_df["significant"]]
        ax.scatter(
            significant["timestamp"],
            significant["correlation"],
            color="red",
            s=100,
            alpha=0.6,
            label="Significant (p<0.05)",
            zorder=5
        )
        
        # Reference lines
        ax.axhline(y=0, color="black", linestyle="-", alpha=0.3, linewidth=1)
        ax.axhline(y=0.3, color="green", linestyle="--", alpha=0.3, linewidth=1, label="Moderate Correlation")
        ax.axhline(y=-0.3, color="red", linestyle="--", alpha=0.3, linewidth=1)
        
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Pearson Correlation", fontsize=12)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_ylim([-1, 1])
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_as:
            self.save_figure(fig, save_as)
        
        return fig
    
    def plot_lag_analysis(
        self,
        lag_df: pd.DataFrame,
        title: str = "Lag Analysis: Sentiment vs Price",
        figsize: Tuple = FIGURE_SIZE_SMALL,
        save_as: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot correlation as function of lag.
        
        Args:
            lag_df: DataFrame with lag_hours, correlation, significant
            title: Plot title
            figsize: Figure size
            save_as: Optional filename to save
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # Color by lag direction
        colors_list = [
            COLORS["positive"] if lag < 0 else
            COLORS["negative"] if lag > 0 else
            "black"
            for lag in lag_df["lag_hours"]
        ]
        
        ax.bar(
            lag_df["lag_hours"],
            lag_df["correlation"],
            color=colors_list,
            alpha=0.7,
            edgecolor="black"
        )
        
        # Reference line
        ax.axhline(y=0, color="black", linestyle="-", linewidth=1)
        
        # Highlight significant lags
        significant = lag_df[lag_df["significant"]]
        ax.scatter(
            significant["lag_hours"],
            significant["correlation"],
            color="red",
            s=200,
            marker="*",
            zorder=5,
            label="Significant (p<0.05)"
        )
        
        ax.set_xlabel("Lag (hours)\n[Negative = Sentiment Leads | Positive = Price Leads]", fontsize=11)
        ax.set_ylabel("Correlation", fontsize=12)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3, axis="y")
        
        plt.tight_layout()
        
        if save_as:
            self.save_figure(fig, save_as)
        
        return fig
    
    def plot_scatter_correlation(
        self,
        aligned_df: pd.DataFrame,
        sentiment_col: str = "mean_sentiment",
        market_col: str = "mid_price",
        title: str = "Sentiment vs Market Price Correlation",
        figsize: Tuple = FIGURE_SIZE_SMALL,
        save_as: Optional[str] = None
    ) -> plt.Figure:
        """
        Scatter plot with regression line.
        
        Args:
            aligned_df: Aligned DataFrame
            sentiment_col: Sentiment column name
            market_col: Market column name
            title: Plot title
            figsize: Figure size
            save_as: Optional filename to save
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # Scatter plot
        ax.scatter(
            aligned_df[sentiment_col],
            aligned_df[market_col],
            alpha=0.5,
            s=50,
            color=COLORS["sentiment"],
            edgecolors="black",
            linewidth=0.5
        )
        
        # Regression line
        z = np.polyfit(aligned_df[sentiment_col], aligned_df[market_col], 1)
        p = np.poly1d(z)
        x_line = np.linspace(aligned_df[sentiment_col].min(), aligned_df[sentiment_col].max(), 100)
        ax.plot(x_line, p(x_line), "r--", linewidth=2, label=f"Fit: y={z[0]:.3f}x+{z[1]:.3f}")
        
        # Correlation coefficient
        corr = aligned_df[sentiment_col].corr(aligned_df[market_col])
        
        ax.set_xlabel("Sentiment Score", fontsize=12)
        ax.set_ylabel("Market Price", fontsize=12)
        ax.set_title(f"{title}\n(r={corr:.3f})", fontsize=14, fontweight="bold")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_as:
            self.save_figure(fig, save_as)
        
        return fig
    
    def plot_sentiment_sentiment_sentiment(
        self,
        sentiment_df: pd.DataFrame,
        title: str = "Sentiment Breakdown",
        figsize: Tuple = FIGURE_SIZE_SMALL,
        save_as: Optional[str] = None
    ) -> plt.Figure:
        """
        Stacked area chart showing positive, negative, neutral article counts.
        
        Args:
            sentiment_df: DataFrame with positive_count, negative_count, neutral_count
            title: Plot title
            figsize: Figure size
            save_as: Optional filename to save
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        ax.stackplot(
            sentiment_df["timestamp"],
            sentiment_df["positive_count"],
            sentiment_df["negative_count"],
            sentiment_df["neutral_count"],
            labels=["Positive", "Negative", "Neutral"],
            colors=[COLORS["positive"], COLORS["negative"], COLORS["neutral"]],
            alpha=0.7
        )
        
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Article Count", fontsize=12)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.legend(loc="upper left")
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        if save_as:
            self.save_figure(fig, save_as)
        
        return fig
    
    def create_summary_report(
        self,
        signal_strength: Dict,
        lag_df: pd.DataFrame,
        aligned_df: pd.DataFrame,
        save_as: str = "analysis_summary.txt"
    ) -> str:
        """
        Create a text summary report.
        
        Args:
            signal_strength: Dictionary from compute_signal_strength
            lag_df: DataFrame from lag_analysis
            aligned_df: Aligned sentiment and market DataFrame
            save_as: Output filename
            
        Returns:
            Path to saved report
        """
        filepath = os.path.join(self.output_dir, save_as)
        
        with open(filepath, "w") as f:
            f.write("=" * 70 + "\n")
            f.write("SENTIMENT-MARKET CORRELATION ANALYSIS REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")
            
            # Signal Strength Section
            f.write("SIGNAL STRENGTH METRICS\n")
            f.write("-" * 70 + "\n")
            if "error" not in signal_strength:
                f.write(f"Pearson Correlation:           {signal_strength.get('pearson_correlation', 0):.4f}\n")
                f.write(f"Pearson P-value:               {signal_strength.get('pearson_pvalue', 1):.6f}\n")
                f.write(f"Significant (p<0.05):          {signal_strength.get('pearson_significant', False)}\n")
                f.write(f"R-squared:                     {signal_strength.get('r_squared', 0):.4f}\n")
                f.write(f"Spearman Correlation:          {signal_strength.get('spearman_correlation', 0):.4f}\n")
                f.write(f"Change Correlation:            {signal_strength.get('change_correlation', 0):.4f}\n")
                f.write(f"Number of Observations:        {signal_strength.get('n_observations', 0)}\n")
            else:
                f.write(signal_strength["error"] + "\n")
            
            f.write("\n")
            
            # Lag Analysis Section
            f.write("LAG ANALYSIS (Sentiment Leading/Lagging Price)\n")
            f.write("-" * 70 + "\n")
            if not lag_df.empty:
                max_corr_idx = lag_df["correlation"].abs().idxmax()
                max_corr_row = lag_df.loc[max_corr_idx]
                f.write(f"Maximum Correlation:           {max_corr_row['correlation']:.4f}\n")
                f.write(f"Optimal Lag:                   {int(max_corr_row['lag_hours'])} hours\n")
                f.write(f"Interpretation:                ")
                if max_corr_row['lag_hours'] < 0:
                    f.write(f"Sentiment leads by {abs(int(max_corr_row['lag_hours']))} hours\n")
                elif max_corr_row['lag_hours'] > 0:
                    f.write(f"Price leads by {int(max_corr_row['lag_hours'])} hours\n")
                else:
                    f.write("Contemporaneous correlation\n")
            
            f.write("\n")
            
            # Summary Statistics\n"
            f.write("DATA SUMMARY\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total aligned data points:     {len(aligned_df)}\n")
            f.write(f"Time range:                    {aligned_df['timestamp'].min()} to {aligned_df['timestamp'].max()}\n")
            
            f.write("\n")
            f.write("=" * 70 + "\n")
        
        logger.info(f"Saved summary report to {filepath}")
        return filepath
