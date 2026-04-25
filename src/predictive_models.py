"""
Predictive Models Module
Linear Regression and Random Forest for sentiment-market prediction
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Optional
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.logger import setup_logger

logger = setup_logger("predictive_models")


class SentimentPredictiveModel:
    """Machine learning models for sentiment-based market prediction"""
    
    def __init__(self):
        self.lr_model = None
        self.rf_model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        self.target_name = None
    
    def prepare_data(
        self,
        dataset: pd.DataFrame,
        feature_cols: List[str],
        target_col: str = "price_change_24h",
        test_split: float = 0.2,
        dropna: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare features and target for modeling
        
        Args:
            dataset: Full dataset
            feature_cols: List of feature column names
            target_col: Target column name
            test_split: Train/test split ratio
            dropna: Drop rows with NaN
            
        Returns:
            Tuple of (X_train, X_test, y_train, y_test)
        """
        # Remove rows with NaN in target
        df = dataset[[*feature_cols, target_col]].copy()
        if dropna:
            df = df.dropna()
        
        # Extract features and target
        X = df[feature_cols].values
        y = df[target_col].values
        
        # Standardize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train/test split
        split_idx = int(len(X_scaled) * (1 - test_split))
        X_train = X_scaled[:split_idx]
        X_test = X_scaled[split_idx:]
        y_train = y[:split_idx]
        y_test = y[split_idx:]
        
        self.feature_names = feature_cols
        self.target_name = target_col
        
        logger.info(
            f"Prepared data: {len(X_train)} train, {len(X_test)} test, "
            f"{len(feature_cols)} features"
        )
        
        return X_train, X_test, y_train, y_test
    
    def train_linear_regression(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: int = 5
    ) -> Dict:
        """
        Train linear regression model
        
        Args:
            X_train: Training features
            y_train: Training target
            cv_folds: Cross-validation folds
            
        Returns:
            Dictionary with model performance
        """
        self.lr_model = LinearRegression()
        self.lr_model.fit(X_train, y_train)
        
        # Cross-validation
        cv_scores = cross_val_score(
            self.lr_model, X_train, y_train,
            cv=cv_folds, scoring='r2'
        )
        
        result = {
            "model": "Linear Regression",
            "r2_train": self.lr_model.score(X_train, y_train),
            "cv_r2_mean": cv_scores.mean(),
            "cv_r2_std": cv_scores.std(),
            "coefficients": dict(zip(self.feature_names, self.lr_model.coef_)),
            "intercept": self.lr_model.intercept_
        }
        
        logger.info(f"Linear Regression trained: R²={result['r2_train']:.4f}")
        
        return result
    
    def train_random_forest(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        n_estimators: int = 100,
        cv_folds: int = 5,
        random_state: int = 42
    ) -> Dict:
        """
        Train random forest model
        
        Args:
            X_train: Training features
            y_train: Training target
            n_estimators: Number of trees
            cv_folds: Cross-validation folds
            random_state: Random seed
            
        Returns:
            Dictionary with model performance
        """
        self.rf_model = RandomForestRegressor(
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2
        )
        self.rf_model.fit(X_train, y_train)
        
        # Cross-validation
        cv_scores = cross_val_score(
            self.rf_model, X_train, y_train,
            cv=cv_folds, scoring='r2'
        )
        
        # Feature importance
        importance = dict(zip(
            self.feature_names,
            self.rf_model.feature_importances_
        ))
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        
        result = {
            "model": "Random Forest",
            "n_estimators": n_estimators,
            "r2_train": self.rf_model.score(X_train, y_train),
            "cv_r2_mean": cv_scores.mean(),
            "cv_r2_std": cv_scores.std(),
            "feature_importance": importance,
            "top_features": list(importance.keys())[:5]
        }
        
        logger.info(f"Random Forest trained: R²={result['r2_train']:.4f}")
        
        return result
    
    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        model_type: str = "both"
    ) -> Dict:
        """
        Evaluate models on test set
        
        Args:
            X_test: Test features
            y_test: Test target
            model_type: "linear", "forest", or "both"
            
        Returns:
            Dictionary with test performance
        """
        results = {}
        
        if model_type in ["linear", "both"] and self.lr_model is not None:
            y_pred_lr = self.lr_model.predict(X_test)
            results["linear_regression"] = {
                "r2": r2_score(y_test, y_pred_lr),
                "mae": mean_absolute_error(y_test, y_pred_lr),
                "rmse": np.sqrt(mean_squared_error(y_test, y_pred_lr)),
                "predictions": y_pred_lr
            }
        
        if model_type in ["forest", "both"] and self.rf_model is not None:
            y_pred_rf = self.rf_model.predict(X_test)
            results["random_forest"] = {
                "r2": r2_score(y_test, y_pred_rf),
                "mae": mean_absolute_error(y_test, y_pred_rf),
                "rmse": np.sqrt(mean_squared_error(y_test, y_pred_rf)),
                "predictions": y_pred_rf
            }
        
        logger.info(f"Evaluation complete: {len(results)} models evaluated")
        
        return results
    
    def predict(
        self,
        X_new: np.ndarray,
        model_type: str = "random_forest"
    ) -> np.ndarray:
        """
        Make predictions on new data
        
        Args:
            X_new: New features (unscaled)
            model_type: "linear_regression" or "random_forest"
            
        Returns:
            Predictions
        """
        X_scaled = self.scaler.transform(X_new)
        
        if model_type == "linear_regression" and self.lr_model is not None:
            return self.lr_model.predict(X_scaled)
        elif model_type == "random_forest" and self.rf_model is not None:
            return self.rf_model.predict(X_scaled)
        else:
            raise ValueError(f"Unknown model type or not trained: {model_type}")


def train_sentiment_prediction_models(
    dataset: pd.DataFrame,
    feature_cols: List[str],
    target_col: str = "price_change_24h",
    test_split: float = 0.2
) -> Dict:
    """
    Train and evaluate both models
    
    Args:
        dataset: Full dataset
        feature_cols: Feature column names
        target_col: Target column name
        test_split: Train/test split ratio
        
    Returns:
        Dictionary with all results
    """
    model = SentimentPredictiveModel()
    
    # Prepare data
    X_train, X_test, y_train, y_test = model.prepare_data(
        dataset, feature_cols, target_col, test_split
    )
    
    # Train models
    lr_results = model.train_linear_regression(X_train, y_train)
    rf_results = model.train_random_forest(X_train, y_train)
    
    # Evaluate
    eval_results = model.evaluate(X_test, y_test, model_type="both")
    
    result = {
        "linear_regression": {**lr_results, **eval_results.get("linear_regression", {})},
        "random_forest": {**rf_results, **eval_results.get("random_forest", {})},
        "dataset_info": {
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_features": len(feature_cols),
            "target": target_col
        },
        "model_object": model
    }
    
    logger.info("Model training and evaluation complete")
    
    return result


def get_top_features(
    model_results: Dict,
    n_top: int = 10
) -> List[Tuple[str, float]]:
    """
    Get top predictive features from Random Forest
    
    Args:
        model_results: Results from train_sentiment_prediction_models
        n_top: Number of top features
        
    Returns:
        List of (feature_name, importance) tuples
    """
    rf_importance = model_results["random_forest"]["feature_importance"]
    top_features = sorted(rf_importance.items(), key=lambda x: x[1], reverse=True)[:n_top]
    return top_features
