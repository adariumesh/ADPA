"""
Concrete Pipeline Step Implementations

This module provides executable implementations of all pipeline steps
that can be used by the pipeline planner and executor.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from abc import ABC
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, LabelEncoder, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import SelectKBest, mutual_info_classif, f_regression
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    mean_absolute_error, mean_squared_error, r2_score
)

from ..core.interfaces import PipelineStep, PipelineStepType, ExecutionResult, StepStatus


class BaseStep(PipelineStep):
    """Base class for all concrete pipeline steps."""
    
    def __init__(self, step_type: PipelineStepType, name: str, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(step_type, name)
        self.parameters = parameters or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.execution_time = 0.0
        self.artifacts = {}
    
    def validate_inputs(self, data: Optional[pd.DataFrame] = None, 
                       config: Optional[Dict[str, Any]] = None) -> bool:
        """Default input validation."""
        if data is None:
            self.logger.warning(f"No data provided to {self.name}")
            return False
        if data.empty:
            self.logger.warning(f"Empty DataFrame provided to {self.name}")
            return False
        return True
    
    def _record_time(self, start_time: float):
        """Record execution time."""
        self.execution_time = time.time() - start_time


class DataValidationStep(BaseStep):
    """Validates data schema and integrity."""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.INGESTION, "data_validation", parameters)
    
    def execute(self, data: Optional[pd.DataFrame] = None, 
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute data validation."""
        start_time = time.time()
        self.status = StepStatus.RUNNING
        
        try:
            if not self.validate_inputs(data, config):
                return ExecutionResult(
                    status=StepStatus.FAILED,
                    errors=["Input validation failed"]
                )
            
            validation_results = {
                "total_rows": len(data),
                "total_columns": len(data.columns),
                "missing_values": data.isnull().sum().to_dict(),
                "duplicate_rows": data.duplicated().sum(),
                "dtypes": data.dtypes.astype(str).to_dict()
            }
            
            # Check for issues
            issues = []
            if data.isnull().sum().sum() > 0:
                issues.append(f"Missing values detected: {data.isnull().sum().sum()} cells")
            if data.duplicated().sum() > 0:
                issues.append(f"Duplicate rows detected: {data.duplicated().sum()}")
            
            # Check for constant columns
            constant_cols = [col for col in data.columns if data[col].nunique() <= 1]
            if constant_cols:
                issues.append(f"Constant columns detected: {constant_cols}")
            
            validation_results["issues"] = issues
            validation_results["is_valid"] = len(issues) == 0
            
            self._record_time(start_time)
            self.status = StepStatus.COMPLETED
            self.artifacts = validation_results
            
            self.logger.info(f"Data validation completed. Issues found: {len(issues)}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=data,
                artifacts={"validation": validation_results},
                metrics={"validation_time": self.execution_time, "issues_count": len(issues)},
                execution_time=self.execution_time
            )
            
        except Exception as e:
            self.status = StepStatus.FAILED
            self.logger.error(f"Data validation failed: {e}")
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[str(e)],
                execution_time=time.time() - start_time
            )


class MissingValueImputationStep(BaseStep):
    """Handles missing values with various imputation strategies."""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.CLEANING, "missing_value_imputation", parameters)
        self.imputers = {}
    
    def execute(self, data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute missing value imputation."""
        start_time = time.time()
        self.status = StepStatus.RUNNING
        
        try:
            if not self.validate_inputs(data, config):
                return ExecutionResult(status=StepStatus.FAILED, errors=["Input validation failed"])
            
            df = data.copy()
            imputation_stats = {"columns_imputed": [], "values_imputed": 0}
            
            numeric_method = self.parameters.get("numeric_method", "median")
            categorical_method = self.parameters.get("categorical_method", "mode")
            drop_threshold = self.parameters.get("drop_threshold", 0.5)
            
            # Drop columns with too many missing values
            missing_ratio = df.isnull().sum() / len(df)
            cols_to_drop = missing_ratio[missing_ratio > drop_threshold].index.tolist()
            if cols_to_drop:
                df = df.drop(columns=cols_to_drop)
                imputation_stats["columns_dropped"] = cols_to_drop
                self.logger.info(f"Dropped columns with >{drop_threshold*100}% missing: {cols_to_drop}")
            
            # Impute numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if df[col].isnull().sum() > 0:
                    values_before = df[col].isnull().sum()
                    if numeric_method == "median":
                        df[col].fillna(df[col].median(), inplace=True)
                    elif numeric_method == "mean":
                        df[col].fillna(df[col].mean(), inplace=True)
                    else:
                        df[col].fillna(0, inplace=True)
                    
                    imputation_stats["columns_imputed"].append(col)
                    imputation_stats["values_imputed"] += values_before
            
            # Impute categorical columns
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns
            for col in categorical_cols:
                if df[col].isnull().sum() > 0:
                    values_before = df[col].isnull().sum()
                    if categorical_method == "mode":
                        mode_val = df[col].mode()
                        if len(mode_val) > 0:
                            df[col].fillna(mode_val[0], inplace=True)
                        else:
                            df[col].fillna("Unknown", inplace=True)
                    else:
                        df[col].fillna("Unknown", inplace=True)
                    
                    imputation_stats["columns_imputed"].append(col)
                    imputation_stats["values_imputed"] += values_before
            
            self._record_time(start_time)
            self.status = StepStatus.COMPLETED
            
            self.logger.info(f"Imputed {imputation_stats['values_imputed']} values in {len(imputation_stats['columns_imputed'])} columns")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=df,
                artifacts={"imputation_stats": imputation_stats},
                metrics={"values_imputed": imputation_stats["values_imputed"]},
                execution_time=self.execution_time
            )
            
        except Exception as e:
            self.status = StepStatus.FAILED
            self.logger.error(f"Missing value imputation failed: {e}")
            return ExecutionResult(status=StepStatus.FAILED, errors=[str(e)])


class OutlierDetectionStep(BaseStep):
    """Detects and handles outliers in numeric features."""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.CLEANING, "outlier_detection", parameters)
    
    def execute(self, data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute outlier detection and handling."""
        start_time = time.time()
        self.status = StepStatus.RUNNING
        
        try:
            if not self.validate_inputs(data, config):
                return ExecutionResult(status=StepStatus.FAILED, errors=["Input validation failed"])
            
            df = data.copy()
            method = self.parameters.get("method", "iqr")
            action = self.parameters.get("action", "clip")
            threshold = self.parameters.get("threshold", 1.5)
            
            outlier_stats = {"columns_processed": [], "outliers_found": 0, "outliers_handled": 0}
            
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                if method == "iqr":
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - threshold * IQR
                    upper_bound = Q3 + threshold * IQR
                elif method == "zscore":
                    mean = df[col].mean()
                    std = df[col].std()
                    lower_bound = mean - threshold * std
                    upper_bound = mean + threshold * std
                else:
                    continue
                
                outliers_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
                outliers_count = outliers_mask.sum()
                
                if outliers_count > 0:
                    outlier_stats["outliers_found"] += outliers_count
                    outlier_stats["columns_processed"].append(col)
                    
                    if action == "clip":
                        df[col] = df[col].clip(lower_bound, upper_bound)
                        outlier_stats["outliers_handled"] += outliers_count
                    elif action == "remove":
                        df = df[~outliers_mask]
                        outlier_stats["outliers_handled"] += outliers_count
                    # action == "flag" would just identify, not modify
            
            self._record_time(start_time)
            self.status = StepStatus.COMPLETED
            
            self.logger.info(f"Found {outlier_stats['outliers_found']} outliers, handled {outlier_stats['outliers_handled']}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=df,
                artifacts={"outlier_stats": outlier_stats},
                metrics={"outliers_found": outlier_stats["outliers_found"]},
                execution_time=self.execution_time
            )
            
        except Exception as e:
            self.status = StepStatus.FAILED
            self.logger.error(f"Outlier detection failed: {e}")
            return ExecutionResult(status=StepStatus.FAILED, errors=[str(e)])


class CategoricalEncodingStep(BaseStep):
    """Encodes categorical variables for machine learning."""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.FEATURE_ENGINEERING, "categorical_encoding", parameters)
        self.encoders = {}
    
    def execute(self, data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute categorical encoding."""
        start_time = time.time()
        self.status = StepStatus.RUNNING
        
        try:
            if not self.validate_inputs(data, config):
                return ExecutionResult(status=StepStatus.FAILED, errors=["Input validation failed"])
            
            df = data.copy()
            default_method = self.parameters.get("default_method", "one_hot")
            high_cardinality_method = self.parameters.get("high_cardinality_method", "label")
            high_cardinality_columns = self.parameters.get("high_cardinality_columns", [])
            
            encoding_stats = {"columns_encoded": [], "new_columns_created": 0}
            
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            
            for col in categorical_cols:
                cardinality = df[col].nunique()
                
                # Use high cardinality method for specified columns or high cardinality
                if col in high_cardinality_columns or cardinality > 10:
                    # Label encoding for high cardinality
                    le = LabelEncoder()
                    df[f"{col}_encoded"] = le.fit_transform(df[col].astype(str))
                    self.encoders[col] = le
                    encoding_stats["columns_encoded"].append(col)
                    encoding_stats["new_columns_created"] += 1
                    df = df.drop(columns=[col])
                else:
                    # One-hot encoding for low cardinality
                    dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
                    df = pd.concat([df.drop(columns=[col]), dummies], axis=1)
                    encoding_stats["columns_encoded"].append(col)
                    encoding_stats["new_columns_created"] += len(dummies.columns)
            
            self._record_time(start_time)
            self.status = StepStatus.COMPLETED
            
            self.logger.info(f"Encoded {len(encoding_stats['columns_encoded'])} columns, created {encoding_stats['new_columns_created']} new columns")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=df,
                artifacts={"encoding_stats": encoding_stats, "encoders": self.encoders},
                metrics={"columns_encoded": len(encoding_stats["columns_encoded"])},
                execution_time=self.execution_time
            )
            
        except Exception as e:
            self.status = StepStatus.FAILED
            self.logger.error(f"Categorical encoding failed: {e}")
            return ExecutionResult(status=StepStatus.FAILED, errors=[str(e)])


class FeatureScalingStep(BaseStep):
    """Scales numeric features for machine learning."""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.FEATURE_ENGINEERING, "feature_scaling", parameters)
        self.scaler = None
    
    def execute(self, data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute feature scaling."""
        start_time = time.time()
        self.status = StepStatus.RUNNING
        
        try:
            if not self.validate_inputs(data, config):
                return ExecutionResult(status=StepStatus.FAILED, errors=["Input validation failed"])
            
            df = data.copy()
            method = self.parameters.get("method", "standard")
            columns = self.parameters.get("columns", None)
            
            # Determine columns to scale
            if columns is None:
                columns = df.select_dtypes(include=[np.number]).columns.tolist()
            
            # Exclude target column if specified
            target_col = context.get("target_column") if context else None
            if target_col and target_col in columns:
                columns.remove(target_col)
            
            if not columns:
                self.logger.warning("No columns to scale")
                return ExecutionResult(
                    status=StepStatus.COMPLETED,
                    data=df,
                    metrics={"columns_scaled": 0},
                    execution_time=time.time() - start_time
                )
            
            # Select scaler
            if method == "standard":
                self.scaler = StandardScaler()
            elif method == "minmax":
                self.scaler = MinMaxScaler()
            elif method == "robust":
                self.scaler = RobustScaler()
            else:
                self.scaler = StandardScaler()
            
            # Apply scaling
            df[columns] = self.scaler.fit_transform(df[columns])
            
            self._record_time(start_time)
            self.status = StepStatus.COMPLETED
            
            self.logger.info(f"Scaled {len(columns)} columns using {method} scaler")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=df,
                artifacts={"scaler": self.scaler, "scaled_columns": columns},
                metrics={"columns_scaled": len(columns)},
                execution_time=self.execution_time
            )
            
        except Exception as e:
            self.status = StepStatus.FAILED
            self.logger.error(f"Feature scaling failed: {e}")
            return ExecutionResult(status=StepStatus.FAILED, errors=[str(e)])


class FeatureEngineeringStep(BaseStep):
    """Creates new features to improve model performance."""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.FEATURE_ENGINEERING, "feature_engineering", parameters)
    
    def execute(self, data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute feature engineering."""
        start_time = time.time()
        self.status = StepStatus.RUNNING
        
        try:
            if not self.validate_inputs(data, config):
                return ExecutionResult(status=StepStatus.FAILED, errors=["Input validation failed"])
            
            df = data.copy()
            create_interactions = self.parameters.get("create_interactions", True)
            create_ratios = self.parameters.get("create_ratios", True)
            create_aggregations = self.parameters.get("create_aggregations", True)
            
            fe_stats = {"new_features": [], "original_features": len(df.columns)}
            
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            # Exclude target column
            target_col = context.get("target_column") if context else None
            if target_col and target_col in numeric_cols:
                numeric_cols.remove(target_col)
            
            # Create interaction features (limit to avoid explosion)
            if create_interactions and len(numeric_cols) >= 2:
                max_interactions = min(5, len(numeric_cols) * (len(numeric_cols) - 1) // 2)
                interaction_count = 0
                
                for i, col1 in enumerate(numeric_cols[:5]):
                    for col2 in numeric_cols[i+1:6]:
                        if interaction_count >= max_interactions:
                            break
                        new_col = f"{col1}_x_{col2}"
                        df[new_col] = df[col1] * df[col2]
                        fe_stats["new_features"].append(new_col)
                        interaction_count += 1
            
            # Create ratio features
            if create_ratios and len(numeric_cols) >= 2:
                for i, col1 in enumerate(numeric_cols[:3]):
                    for col2 in numeric_cols[i+1:4]:
                        # Avoid division by zero
                        if (df[col2] != 0).any():
                            new_col = f"{col1}_div_{col2}"
                            df[new_col] = df[col1] / (df[col2] + 1e-10)
                            fe_stats["new_features"].append(new_col)
            
            # Create aggregation features
            if create_aggregations:
                if len(numeric_cols) >= 3:
                    df["numeric_mean"] = df[numeric_cols].mean(axis=1)
                    df["numeric_std"] = df[numeric_cols].std(axis=1)
                    df["numeric_sum"] = df[numeric_cols].sum(axis=1)
                    fe_stats["new_features"].extend(["numeric_mean", "numeric_std", "numeric_sum"])
            
            fe_stats["total_features"] = len(df.columns)
            fe_stats["features_created"] = len(fe_stats["new_features"])
            
            self._record_time(start_time)
            self.status = StepStatus.COMPLETED
            
            self.logger.info(f"Created {fe_stats['features_created']} new features")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=df,
                artifacts={"feature_engineering_stats": fe_stats},
                metrics={"features_created": fe_stats["features_created"]},
                execution_time=self.execution_time
            )
            
        except Exception as e:
            self.status = StepStatus.FAILED
            self.logger.error(f"Feature engineering failed: {e}")
            return ExecutionResult(status=StepStatus.FAILED, errors=[str(e)])


class FeatureSelectionStep(BaseStep):
    """Selects most important features."""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.FEATURE_ENGINEERING, "feature_selection", parameters)
        self.selector = None
        self.selected_features = []
    
    def execute(self, data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute feature selection."""
        start_time = time.time()
        self.status = StepStatus.RUNNING
        
        try:
            if not self.validate_inputs(data, config):
                return ExecutionResult(status=StepStatus.FAILED, errors=["Input validation failed"])
            
            df = data.copy()
            method = self.parameters.get("method", "mutual_information")
            k_best = self.parameters.get("k_best", 20)
            target_column = context.get("target_column") if context else None
            
            if target_column is None or target_column not in df.columns:
                self.logger.warning("No target column specified for feature selection")
                return ExecutionResult(
                    status=StepStatus.COMPLETED,
                    data=df,
                    metrics={"features_selected": len(df.columns)},
                    execution_time=time.time() - start_time
                )
            
            # Prepare features and target
            X = df.drop(columns=[target_column])
            y = df[target_column]
            
            # Select only numeric columns for selection
            numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
            X_numeric = X[numeric_cols]
            
            # Apply feature selection
            k_best = min(k_best, len(numeric_cols))
            
            if method == "mutual_information":
                score_func = mutual_info_classif
            else:
                score_func = f_regression
            
            self.selector = SelectKBest(score_func=score_func, k=k_best)
            self.selector.fit(X_numeric, y)
            
            # Get selected feature names
            selected_mask = self.selector.get_support()
            self.selected_features = [col for col, selected in zip(numeric_cols, selected_mask) if selected]
            
            # Include non-numeric columns
            non_numeric_cols = [col for col in X.columns if col not in numeric_cols]
            final_columns = self.selected_features + non_numeric_cols + [target_column]
            
            df_selected = df[final_columns]
            
            self._record_time(start_time)
            self.status = StepStatus.COMPLETED
            
            self.logger.info(f"Selected {len(self.selected_features)} features from {len(numeric_cols)}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=df_selected,
                artifacts={"selected_features": self.selected_features, "selector": self.selector},
                metrics={"features_selected": len(self.selected_features)},
                execution_time=self.execution_time
            )
            
        except Exception as e:
            self.status = StepStatus.FAILED
            self.logger.error(f"Feature selection failed: {e}")
            return ExecutionResult(status=StepStatus.FAILED, errors=[str(e)])


class TrainTestSplitStep(BaseStep):
    """Splits data into training and testing sets."""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.TRAINING, "train_test_split", parameters)
    
    def execute(self, data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute train-test split."""
        start_time = time.time()
        self.status = StepStatus.RUNNING
        
        try:
            if not self.validate_inputs(data, config):
                return ExecutionResult(status=StepStatus.FAILED, errors=["Input validation failed"])
            
            df = data.copy()
            test_size = self.parameters.get("test_size", 0.2)
            stratify = self.parameters.get("stratify", False)
            random_state = self.parameters.get("random_state", 42)
            target_column = context.get("target_column") if context else None
            
            if target_column is None or target_column not in df.columns:
                # If no target, just do random split
                train_df, test_df = train_test_split(df, test_size=test_size, random_state=random_state)
            else:
                X = df.drop(columns=[target_column])
                y = df[target_column]
                
                stratify_col = y if stratify else None
                
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=random_state, stratify=stratify_col
                )
                
                train_df = pd.concat([X_train, y_train], axis=1)
                test_df = pd.concat([X_test, y_test], axis=1)
            
            split_info = {
                "train_size": len(train_df),
                "test_size": len(test_df),
                "train_ratio": len(train_df) / len(df),
                "test_ratio": len(test_df) / len(df)
            }
            
            self._record_time(start_time)
            self.status = StepStatus.COMPLETED
            
            self.logger.info(f"Split data: train={len(train_df)}, test={len(test_df)}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=train_df,  # Return training data as main output
                artifacts={"train_data": train_df, "test_data": test_df, "split_info": split_info},
                metrics=split_info,
                execution_time=self.execution_time,
                step_output={"test_data": test_df}
            )
            
        except Exception as e:
            self.status = StepStatus.FAILED
            self.logger.error(f"Train-test split failed: {e}")
            return ExecutionResult(status=StepStatus.FAILED, errors=[str(e)])


class ModelTrainingStep(BaseStep):
    """Trains machine learning models."""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.TRAINING, "model_training", parameters)
        self.model = None
    
    def execute(self, data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute model training."""
        start_time = time.time()
        self.status = StepStatus.RUNNING
        
        try:
            if not self.validate_inputs(data, config):
                return ExecutionResult(status=StepStatus.FAILED, errors=["Input validation failed"])
            
            algorithm = self.parameters.get("algorithm", "random_forest")
            model_params = self.parameters.get("params", {})
            target_column = context.get("target_column") if context else None
            
            if target_column is None or target_column not in data.columns:
                return ExecutionResult(
                    status=StepStatus.FAILED,
                    errors=["Target column not specified or not found"]
                )
            
            X = data.drop(columns=[target_column])
            y = data[target_column]
            
            # Select only numeric columns for training
            X = X.select_dtypes(include=[np.number])
            
            # Initialize model based on algorithm
            self.model = self._get_model(algorithm, model_params)
            
            # Train model
            self.logger.info(f"Training {algorithm} model...")
            self.model.fit(X, y)
            
            # Get feature importance if available
            feature_importance = {}
            if hasattr(self.model, 'feature_importances_'):
                feature_importance = dict(zip(X.columns, self.model.feature_importances_))
            elif hasattr(self.model, 'coef_'):
                coef = self.model.coef_
                if len(coef.shape) == 1:
                    feature_importance = dict(zip(X.columns, np.abs(coef)))
                else:
                    feature_importance = dict(zip(X.columns, np.abs(coef).mean(axis=0)))
            
            training_info = {
                "algorithm": algorithm,
                "n_samples": len(X),
                "n_features": len(X.columns),
                "feature_importance": feature_importance
            }
            
            self._record_time(start_time)
            self.status = StepStatus.COMPLETED
            
            self.logger.info(f"Model training completed in {self.execution_time:.2f}s")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=data,
                artifacts={"model": self.model, "training_info": training_info, "feature_columns": X.columns.tolist()},
                metrics={"training_time": self.execution_time, "n_features": len(X.columns)},
                execution_time=self.execution_time
            )
            
        except Exception as e:
            self.status = StepStatus.FAILED
            self.logger.error(f"Model training failed: {e}")
            return ExecutionResult(status=StepStatus.FAILED, errors=[str(e)])
    
    def _get_model(self, algorithm: str, params: Dict[str, Any]):
        """Get model instance based on algorithm name."""
        models = {
            "logistic_regression": LogisticRegression,
            "linear_regression": LinearRegression,
            "random_forest": RandomForestClassifier,
            "random_forest_regressor": RandomForestRegressor,
            "gradient_boosting": GradientBoostingClassifier,
            "gradient_boosting_regressor": GradientBoostingRegressor
        }
        
        model_class = models.get(algorithm, RandomForestClassifier)
        return model_class(**params)


class ModelEvaluationStep(BaseStep):
    """Evaluates model performance."""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.EVALUATION, "model_evaluation", parameters)
    
    def execute(self, data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute model evaluation."""
        start_time = time.time()
        self.status = StepStatus.RUNNING
        
        try:
            model = context.get("model") if context else None
            test_data = context.get("test_data") if context else None
            target_column = context.get("target_column") if context else None
            feature_columns = context.get("feature_columns") if context else None
            
            if model is None:
                return ExecutionResult(status=StepStatus.FAILED, errors=["No model provided for evaluation"])
            
            if test_data is None or target_column is None:
                return ExecutionResult(status=StepStatus.FAILED, errors=["Test data or target column not provided"])
            
            # Prepare test data
            X_test = test_data.drop(columns=[target_column])
            y_test = test_data[target_column]
            
            # Use only feature columns used in training
            if feature_columns:
                X_test = X_test[[col for col in feature_columns if col in X_test.columns]]
            else:
                X_test = X_test.select_dtypes(include=[np.number])
            
            # Make predictions
            y_pred = model.predict(X_test)
            
            # Calculate metrics
            metrics = self.parameters.get("metrics", ["accuracy", "precision", "recall", "f1_score"])
            evaluation_results = {}
            
            # Determine if classification or regression
            is_classification = hasattr(model, 'predict_proba') or len(np.unique(y_test)) <= 20
            
            if is_classification:
                if "accuracy" in metrics:
                    evaluation_results["accuracy"] = accuracy_score(y_test, y_pred)
                if "precision" in metrics:
                    evaluation_results["precision"] = precision_score(y_test, y_pred, average='weighted', zero_division=0)
                if "recall" in metrics:
                    evaluation_results["recall"] = recall_score(y_test, y_pred, average='weighted', zero_division=0)
                if "f1_score" in metrics:
                    evaluation_results["f1_score"] = f1_score(y_test, y_pred, average='weighted', zero_division=0)
                if "roc_auc" in metrics and hasattr(model, 'predict_proba'):
                    try:
                        y_proba = model.predict_proba(X_test)
                        if len(np.unique(y_test)) == 2:
                            evaluation_results["roc_auc"] = roc_auc_score(y_test, y_proba[:, 1])
                    except:
                        pass
            else:
                if "mae" in metrics:
                    evaluation_results["mae"] = mean_absolute_error(y_test, y_pred)
                if "mse" in metrics:
                    evaluation_results["mse"] = mean_squared_error(y_test, y_pred)
                if "rmse" in metrics:
                    evaluation_results["rmse"] = np.sqrt(mean_squared_error(y_test, y_pred))
                if "r2_score" in metrics:
                    evaluation_results["r2_score"] = r2_score(y_test, y_pred)
            
            self._record_time(start_time)
            self.status = StepStatus.COMPLETED
            
            self.logger.info(f"Model evaluation completed: {evaluation_results}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=data,
                artifacts={"evaluation_results": evaluation_results, "predictions": y_pred},
                metrics=evaluation_results,
                execution_time=self.execution_time
            )
            
        except Exception as e:
            self.status = StepStatus.FAILED
            self.logger.error(f"Model evaluation failed: {e}")
            return ExecutionResult(status=StepStatus.FAILED, errors=[str(e)])


class ReportGenerationStep(BaseStep):
    """Generates comprehensive pipeline report."""
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.REPORTING, "generate_report", parameters)
    
    def execute(self, data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Generate pipeline report."""
        start_time = time.time()
        self.status = StepStatus.RUNNING
        
        try:
            report = {
                "summary": {
                    "pipeline_completed": True,
                    "execution_time": context.get("total_execution_time", 0) if context else 0,
                    "steps_executed": context.get("steps_executed", []) if context else []
                },
                "data_summary": {
                    "final_shape": data.shape if data is not None else None,
                    "columns": data.columns.tolist() if data is not None else []
                },
                "model_performance": context.get("evaluation_results", {}) if context else {},
                "recommendations": self._generate_recommendations(context)
            }
            
            self._record_time(start_time)
            self.status = StepStatus.COMPLETED
            
            self.logger.info("Pipeline report generated successfully")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=data,
                artifacts={"report": report},
                metrics={"report_generated": True},
                execution_time=self.execution_time
            )
            
        except Exception as e:
            self.status = StepStatus.FAILED
            self.logger.error(f"Report generation failed: {e}")
            return ExecutionResult(status=StepStatus.FAILED, errors=[str(e)])
    
    def _generate_recommendations(self, context: Optional[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on pipeline results."""
        recommendations = []
        
        if context:
            eval_results = context.get("evaluation_results", {})
            
            if eval_results.get("accuracy", 1.0) < 0.7:
                recommendations.append("Consider more feature engineering or different algorithms")
            if eval_results.get("accuracy", 0) > 0.95:
                recommendations.append("Check for potential overfitting - consider more regularization")
            
            training_info = context.get("training_info", {})
            if training_info.get("n_features", 0) > 100:
                recommendations.append("Consider dimensionality reduction techniques")
        
        if not recommendations:
            recommendations.append("Pipeline completed successfully with good performance")
        
        return recommendations


# Step factory for creating steps from configuration
class StepFactory:
    """Factory for creating pipeline steps from configuration."""
    
    _step_classes = {
        "data_validation": DataValidationStep,
        "missing_value_imputation": MissingValueImputationStep,
        "outlier_detection": OutlierDetectionStep,
        "categorical_encoding": CategoricalEncodingStep,
        "feature_scaling": FeatureScalingStep,
        "feature_engineering": FeatureEngineeringStep,
        "feature_selection": FeatureSelectionStep,
        "train_test_split": TrainTestSplitStep,
        "model_training": ModelTrainingStep,
        "model_evaluation": ModelEvaluationStep,
        "generate_report": ReportGenerationStep
    }
    
    @classmethod
    def create_step(cls, step_config: Dict[str, Any]) -> BaseStep:
        """Create a pipeline step from configuration."""
        step_name = step_config.get("name", "")
        parameters = step_config.get("parameters", {})
        
        step_class = cls._step_classes.get(step_name)
        
        if step_class is None:
            raise ValueError(f"Unknown step type: {step_name}")
        
        return step_class(parameters=parameters)
    
    @classmethod
    def create_steps_from_plan(cls, plan_steps: List[Dict[str, Any]]) -> List[BaseStep]:
        """Create all pipeline steps from a plan."""
        return [cls.create_step(step) for step in plan_steps]
    
    @classmethod
    def get_available_steps(cls) -> List[str]:
        """Get list of available step types."""
        return list(cls._step_classes.keys())
