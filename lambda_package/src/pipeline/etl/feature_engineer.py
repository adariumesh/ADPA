"""
Feature engineering pipeline step with comprehensive transformations.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
from sklearn.preprocessing import (
    StandardScaler, RobustScaler, MinMaxScaler, 
    LabelEncoder, OneHotEncoder
)
from sklearn.feature_selection import (
    SelectKBest, f_classif, f_regression, 
    mutual_info_classif, mutual_info_regression
)
from sklearn.preprocessing import PolynomialFeatures
import warnings
warnings.filterwarnings('ignore')

from ...agent.core.interfaces import PipelineStep, PipelineStepType, ExecutionResult, StepStatus


class FeatureEngineeringStep(PipelineStep):
    """
    Pipeline step for comprehensive feature engineering.
    
    Supports:
    - Categorical encoding (one-hot, label, target)
    - Feature scaling (standard, robust, min-max)
    - Feature selection (correlation, importance, statistical)
    - Polynomial feature generation
    - Date/time feature extraction
    - Missing value imputation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.FEATURE_ENGINEERING, "feature_engineering")
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Store fitted transformers for consistent transformation
        self.encoders = {}
        self.scalers = {}
        self.selectors = {}
        self.poly_features = None
        
    def execute(self, 
                data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Execute feature engineering step.
        
        Args:
            data: Input dataset
            config: Step configuration
            context: Execution context with target column and problem type
            
        Returns:
            ExecutionResult with engineered features
        """
        if data is None:
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=["No data provided for feature engineering"]
            )
        
        if isinstance(data, pd.DataFrame) and data.empty:
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=["Empty DataFrame provided for feature engineering"]
            )
        
        try:
            self.logger.info("Starting feature engineering...")
            start_time = pd.Timestamp.now()
            
            # Make a copy to avoid modifying original data
            engineered_data = data.copy()
            
            # Get context information
            target_column = context.get('target_column') if context else None
            problem_type = context.get('problem_type', 'classification') if context else 'classification'
            
            # Separate target if provided
            y = None
            if target_column and target_column in engineered_data.columns:
                y = engineered_data[target_column]
                X = engineered_data.drop(columns=[target_column])
            else:
                X = engineered_data
            
            # Track transformations
            feature_engineering_stats = {
                "initial_features": len(X.columns),
                "initial_rows": len(X),
                "transformations_applied": []
            }
            
            # 1. Handle missing values in features
            if self.config.get("handle_missing", True):
                missing_stats = self._handle_missing_values(X)
                feature_engineering_stats.update(missing_stats)
                feature_engineering_stats["transformations_applied"].append("missing_value_imputation")
            
            # 2. Extract date/time features
            if self.config.get("extract_datetime_features", True):
                datetime_stats = self._extract_datetime_features(X)
                feature_engineering_stats.update(datetime_stats)
                if datetime_stats.get("datetime_columns_processed", 0) > 0:
                    feature_engineering_stats["transformations_applied"].append("datetime_extraction")
            
            # 3. Encode categorical variables
            if self.config.get("encode_categorical", True):
                X, encoding_stats = self._encode_categorical_features(X, y, problem_type)
                feature_engineering_stats.update(encoding_stats)
                if encoding_stats.get("categorical_columns_encoded", 0) > 0:
                    feature_engineering_stats["transformations_applied"].append("categorical_encoding")
            
            # 4. Generate polynomial features (if configured)
            if self.config.get("polynomial_features", False):
                poly_degree = self.config.get("polynomial_degree", 2)
                poly_stats = self._generate_polynomial_features(X, poly_degree)
                feature_engineering_stats.update(poly_stats)
                if poly_stats.get("polynomial_features_added", 0) > 0:
                    feature_engineering_stats["transformations_applied"].append("polynomial_features")
            
            # 5. Scale numerical features
            if self.config.get("scale_features", True):
                scaling_method = self.config.get("scaling_method", "standard")
                scaling_stats = self._scale_features(X, scaling_method)
                feature_engineering_stats.update(scaling_stats)
                feature_engineering_stats["transformations_applied"].append(f"{scaling_method}_scaling")
            
            # 6. Feature selection (if configured)
            if self.config.get("feature_selection", False) and y is not None:
                selection_method = self.config.get("selection_method", "statistical")
                k_features = self.config.get("k_features", min(20, len(X.columns)))
                selection_stats = self._select_features(X, y, selection_method, k_features, problem_type)
                feature_engineering_stats.update(selection_stats)
                if selection_stats.get("features_selected", 0) > 0:
                    feature_engineering_stats["transformations_applied"].append(f"{selection_method}_selection")
            
            # 7. Remove highly correlated features (if configured)
            if self.config.get("remove_correlated", False):
                correlation_threshold = self.config.get("correlation_threshold", 0.95)
                correlation_stats = self._remove_correlated_features(X, correlation_threshold)
                feature_engineering_stats.update(correlation_stats)
                if correlation_stats.get("correlated_features_removed", 0) > 0:
                    feature_engineering_stats["transformations_applied"].append("correlation_removal")
            
            # Combine with target if it was separated
            if y is not None:
                engineered_data = X.copy()
                engineered_data[target_column] = y
            else:
                engineered_data = X
            
            # Final statistics
            feature_engineering_stats["final_features"] = len(X.columns)
            feature_engineering_stats["final_rows"] = len(X)
            feature_engineering_stats["features_added"] = len(X.columns) - feature_engineering_stats["initial_features"]
            
            execution_time = (pd.Timestamp.now() - start_time).total_seconds()
            
            self.logger.info(
                f"Feature engineering completed. "
                f"Features: {feature_engineering_stats['initial_features']} -> {feature_engineering_stats['final_features']}"
            )
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=engineered_data,
                metrics=feature_engineering_stats,
                execution_time=execution_time,
                artifacts={
                    "feature_names": list(X.columns),
                    "feature_importance_scores": self._calculate_feature_importance(X, y, problem_type) if y is not None else {},
                    "transformers": {
                        "encoders": list(self.encoders.keys()),
                        "scalers": list(self.scalers.keys()),
                        "selectors": list(self.selectors.keys())
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(f"Feature engineering failed: {str(e)}", exc_info=True)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[f"Feature engineering error: {str(e)}"]
            )
    
    def _handle_missing_values(self, X: pd.DataFrame) -> Dict[str, Any]:
        """Handle missing values with intelligent imputation."""
        stats = {
            "missing_values_before": X.isnull().sum().sum(),
            "columns_with_missing": X.isnull().any().sum()
        }
        
        if stats["missing_values_before"] == 0:
            stats["missing_values_after"] = 0
            return stats
        
        strategy = self.config.get("missing_value_strategy", "auto")
        
        for col in X.columns:
            if X[col].isnull().any():
                if pd.api.types.is_numeric_dtype(X[col]):
                    # Numerical columns: use median by default
                    if strategy == "mean":
                        X[col] = X[col].fillna(X[col].mean())
                    else:  # median (more robust to outliers)
                        X[col] = X[col].fillna(X[col].median())
                else:
                    # Categorical columns: use mode
                    mode_value = X[col].mode()[0] if not X[col].mode().empty else "MISSING"
                    X[col] = X[col].fillna(mode_value)
        
        stats["missing_values_after"] = X.isnull().sum().sum()
        stats["imputation_strategy"] = strategy
        
        return stats
    
    def _extract_datetime_features(self, X: pd.DataFrame) -> Dict[str, Any]:
        """Extract features from datetime columns."""
        stats = {
            "datetime_columns_processed": 0,
            "datetime_features_created": 0
        }
        
        datetime_columns = X.select_dtypes(include=['datetime64']).columns
        
        for col in datetime_columns:
            try:
                # Extract common datetime features
                X[f'{col}_year'] = X[col].dt.year
                X[f'{col}_month'] = X[col].dt.month
                X[f'{col}_day'] = X[col].dt.day
                X[f'{col}_dayofweek'] = X[col].dt.dayofweek
                X[f'{col}_quarter'] = X[col].dt.quarter
                X[f'{col}_is_weekend'] = (X[col].dt.dayofweek >= 5).astype(int)
                
                # Drop original datetime column
                X.drop(columns=[col], inplace=True)
                
                stats["datetime_columns_processed"] += 1
                stats["datetime_features_created"] += 6
                
            except Exception as e:
                self.logger.warning(f"Failed to extract datetime features from {col}: {e}")
        
        return stats
    
    def _encode_categorical_features(self, X: pd.DataFrame, y: Optional[pd.Series], 
                                    problem_type: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Encode categorical variables using appropriate strategy.
        
        Returns:
            Tuple of (modified DataFrame, stats dictionary)
        """
        stats = {
            "categorical_columns_encoded": 0,
            "encoding_methods_used": []
        }
        
        categorical_columns = X.select_dtypes(include=['object', 'category']).columns
        
        if len(categorical_columns) == 0:
            return X, stats
        
        encoding_method = self.config.get("categorical_encoding", "auto")
        
        for col in categorical_columns:
            n_unique = X[col].nunique()
            
            # Auto-select encoding strategy based on cardinality
            if encoding_method == "auto":
                if n_unique == 2:
                    # Binary: use label encoding
                    method = "label"
                elif n_unique <= 10:
                    # Low cardinality: use one-hot encoding
                    method = "onehot"
                else:
                    # High cardinality: use target encoding if target available, else label
                    method = "target" if y is not None else "label"
            else:
                method = encoding_method
            
            try:
                if method == "onehot":
                    # One-hot encoding
                    dummies = pd.get_dummies(X[col], prefix=col, drop_first=True)
                    X.drop(columns=[col], inplace=True)
                    X = pd.concat([X, dummies], axis=1)
                    stats["encoding_methods_used"].append(f"{col}:onehot")
                    
                elif method == "label":
                    # Label encoding
                    le = LabelEncoder()
                    X[col] = le.fit_transform(X[col].astype(str))
                    self.encoders[col] = le
                    stats["encoding_methods_used"].append(f"{col}:label")
                    
                elif method == "target" and y is not None:
                    # Target encoding (mean encoding)
                    target_means = X.groupby(col)[col].transform(
                        lambda x: y[X[col] == x.iloc[0]].mean() if len(x) > 0 else y.mean()
                    )
                    X[f'{col}_target_enc'] = target_means
                    X.drop(columns=[col], inplace=True)
                    stats["encoding_methods_used"].append(f"{col}:target")
                
                stats["categorical_columns_encoded"] += 1
                
            except Exception as e:
                self.logger.warning(f"Failed to encode {col}: {e}")
        
        return X, stats
    
    def _generate_polynomial_features(self, X: pd.DataFrame, degree: int = 2) -> Dict[str, Any]:
        """Generate polynomial and interaction features."""
        stats = {
            "polynomial_features_added": 0,
            "polynomial_degree": degree
        }
        
        # Only apply to numerical columns
        numerical_cols = X.select_dtypes(include=[np.number]).columns
        
        if len(numerical_cols) == 0:
            return stats
        
        # Limit to prevent explosion of features
        max_cols_for_poly = self.config.get("max_poly_columns", 10)
        selected_cols = numerical_cols[:max_cols_for_poly]
        
        try:
            poly = PolynomialFeatures(degree=degree, include_bias=False)
            poly_features = poly.fit_transform(X[selected_cols])
            
            # Create feature names
            feature_names = poly.get_feature_names_out(selected_cols)
            
            # Add only new features (exclude original features)
            n_original = len(selected_cols)
            new_features = poly_features[:, n_original:]
            new_feature_names = feature_names[n_original:]
            
            # Add to dataframe
            for i, name in enumerate(new_feature_names):
                X[name] = new_features[:, i]
            
            self.poly_features = poly
            stats["polynomial_features_added"] = len(new_feature_names)
            
        except Exception as e:
            self.logger.warning(f"Failed to generate polynomial features: {e}")
        
        return stats
    
    def _scale_features(self, X: pd.DataFrame, method: str = "standard") -> Dict[str, Any]:
        """Scale numerical features."""
        stats = {
            "scaling_method": method,
            "features_scaled": 0
        }
        
        # Only scale numerical columns
        numerical_cols = X.select_dtypes(include=[np.number]).columns
        
        if len(numerical_cols) == 0:
            return stats
        
        try:
            # Select scaler
            if method == "standard":
                scaler = StandardScaler()
            elif method == "robust":
                scaler = RobustScaler()
            elif method == "minmax":
                scaler = MinMaxScaler()
            else:
                self.logger.warning(f"Unknown scaling method: {method}, using standard")
                scaler = StandardScaler()
            
            # Fit and transform
            X[numerical_cols] = scaler.fit_transform(X[numerical_cols])
            
            # Store scaler for later use
            self.scalers['numerical'] = scaler
            stats["features_scaled"] = len(numerical_cols)
            
        except Exception as e:
            self.logger.warning(f"Failed to scale features: {e}")
        
        return stats
    
    def _select_features(self, X: pd.DataFrame, y: pd.Series, 
                        method: str, k: int, problem_type: str) -> Dict[str, Any]:
        """Select top k features based on statistical tests."""
        stats = {
            "selection_method": method,
            "features_before_selection": len(X.columns),
            "features_selected": 0
        }
        
        try:
            # Select scoring function based on problem type
            if problem_type == "classification":
                score_func = f_classif if method == "statistical" else mutual_info_classif
            else:  # regression
                score_func = f_regression if method == "statistical" else mutual_info_regression
            
            # Apply feature selection
            k = min(k, len(X.columns))  # Can't select more features than we have
            selector = SelectKBest(score_func=score_func, k=k)
            
            X_selected = selector.fit_transform(X, y)
            selected_features = X.columns[selector.get_support()].tolist()
            
            # Update dataframe with selected features
            X.drop(columns=[col for col in X.columns if col not in selected_features], inplace=True)
            
            # Store selector
            self.selectors[method] = selector
            stats["features_selected"] = len(selected_features)
            stats["selected_feature_names"] = selected_features
            
        except Exception as e:
            self.logger.warning(f"Failed to select features: {e}")
        
        return stats
    
    def _remove_correlated_features(self, X: pd.DataFrame, threshold: float = 0.95) -> Dict[str, Any]:
        """Remove highly correlated features."""
        stats = {
            "correlation_threshold": threshold,
            "correlated_features_removed": 0
        }
        
        # Only numerical features
        numerical_cols = X.select_dtypes(include=[np.number]).columns
        
        if len(numerical_cols) < 2:
            return stats
        
        try:
            # Calculate correlation matrix
            corr_matrix = X[numerical_cols].corr().abs()
            
            # Find features to drop
            upper_triangle = corr_matrix.where(
                np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
            )
            
            to_drop = [column for column in upper_triangle.columns 
                      if any(upper_triangle[column] > threshold)]
            
            # Drop correlated features
            X.drop(columns=to_drop, inplace=True)
            
            stats["correlated_features_removed"] = len(to_drop)
            stats["removed_features"] = to_drop
            
        except Exception as e:
            self.logger.warning(f"Failed to remove correlated features: {e}")
        
        return stats
    
    def _calculate_feature_importance(self, X: pd.DataFrame, y: Optional[pd.Series],
                                     problem_type: str) -> Dict[str, float]:
        """Calculate feature importance scores."""
        if y is None or len(X.columns) == 0:
            return {}
        
        try:
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            
            # Use random forest for quick importance estimation
            if problem_type == "classification":
                model = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
            else:
                model = RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1)
            
            model.fit(X, y)
            
            # Get feature importance
            importance_scores = dict(zip(X.columns, model.feature_importances_))
            
            # Sort by importance
            importance_scores = dict(sorted(importance_scores.items(), 
                                          key=lambda x: x[1], reverse=True))
            
            return importance_scores
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate feature importance: {e}")
            return {}
    
    def validate_inputs(self, 
                       data: Optional[pd.DataFrame] = None,
                       config: Optional[Dict[str, Any]] = None,
                       context: Optional[Dict[str, Any]] = None) -> bool:
        """Validate inputs before execution."""
        if data is None:
            self.logger.error("No data provided")
            return False
        
        if not isinstance(data, pd.DataFrame):
            self.logger.error("Data must be a pandas DataFrame")
            return False
        
        if data.empty:
            self.logger.error("Data is empty")
            return False
        
        return True
    
    def get_requirements(self) -> Dict[str, Any]:
        """Get step requirements."""
        return {
            "required_inputs": ["data"],
            "optional_inputs": ["config", "context"],
            "required_config": [],
            "optional_config": [
                "handle_missing", "missing_value_strategy",
                "extract_datetime_features",
                "encode_categorical", "categorical_encoding",
                "scale_features", "scaling_method",
                "polynomial_features", "polynomial_degree",
                "feature_selection", "selection_method", "k_features",
                "remove_correlated", "correlation_threshold"
            ],
            "produces": ["engineered_features", "feature_importance"]
        }
