"""
Pipeline Planner - Intelligent ML Pipeline Planning Engine

This module provides the core planning capabilities for ADPA, automatically
generating optimal ML pipelines based on dataset characteristics and objectives.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

from ..core.interfaces import (
    PipelineStep, PipelineStepType, DatasetInfo, PipelineConfig,
    ExecutionResult, StepStatus, PipelineOrchestrator
)


class PipelineComplexity(Enum):
    """Pipeline complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"


@dataclass
class PlannerConfig:
    """Configuration for the pipeline planner."""
    enable_feature_engineering: bool = True
    enable_hyperparameter_tuning: bool = True
    enable_ensemble_methods: bool = True
    enable_cross_validation: bool = True
    max_pipeline_steps: int = 10
    time_budget_minutes: int = 60
    optimization_metric: str = "accuracy"
    prefer_interpretability: bool = False
    custom_steps: List[str] = field(default_factory=list)


@dataclass
class PipelinePlan:
    """A complete pipeline plan with all steps and metadata."""
    plan_id: str
    steps: List[Dict[str, Any]]
    estimated_duration_minutes: int
    complexity: PipelineComplexity
    confidence_score: float
    reasoning: str
    alternatives: List[Dict[str, Any]]
    resource_requirements: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "steps": self.steps,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "complexity": self.complexity.value,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "alternatives": self.alternatives,
            "resource_requirements": self.resource_requirements,
            "metadata": self.metadata
        }


class DataProfiler:
    """
    Intelligent dataset profiler for pipeline planning.
    Analyzes dataset characteristics to inform pipeline decisions.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def profile(self, data: pd.DataFrame, target_column: Optional[str] = None) -> DatasetInfo:
        """
        Create a comprehensive profile of the dataset.
        
        Args:
            data: Input DataFrame to profile
            target_column: Optional target column name
            
        Returns:
            DatasetInfo with comprehensive analysis
        """
        self.logger.info(f"Profiling dataset with shape {data.shape}")
        
        # Basic info
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = data.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
        datetime_cols = data.select_dtypes(include=['datetime64']).columns.tolist()
        
        # Missing values analysis
        missing_values = data.isnull().sum().to_dict()
        
        # Infer target column if not provided
        if target_column is None:
            target_column = self._infer_target_column(data, numeric_cols, categorical_cols)
        
        return DatasetInfo(
            shape=data.shape,
            columns=data.columns.tolist(),
            dtypes=data.dtypes.astype(str).to_dict(),
            missing_values=missing_values,
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            target_column=target_column
        )
    
    def get_detailed_profile(self, data: pd.DataFrame, target_column: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed profiling information for planning decisions.
        
        Args:
            data: Input DataFrame
            target_column: Target column name
            
        Returns:
            Detailed profile dictionary
        """
        basic_info = self.profile(data, target_column)
        
        # Additional detailed analysis
        detailed_profile = {
            "basic_info": basic_info.__dict__,
            "data_quality": self._assess_data_quality(data),
            "feature_analysis": self._analyze_features(data, basic_info),
            "problem_characteristics": self._analyze_problem(data, basic_info),
            "recommendations": self._generate_recommendations(data, basic_info)
        }
        
        return detailed_profile
    
    def _infer_target_column(self, data: pd.DataFrame, numeric_cols: List[str], 
                            categorical_cols: List[str]) -> Optional[str]:
        """Infer the most likely target column."""
        # Common target column names
        target_keywords = ['target', 'label', 'class', 'y', 'output', 'result', 
                          'churn', 'fraud', 'sales', 'price', 'revenue', 'prediction']
        
        for col in data.columns:
            col_lower = col.lower()
            for keyword in target_keywords:
                if keyword in col_lower:
                    return col
        
        # If no keyword match, return the last column (common convention)
        if len(data.columns) > 0:
            return data.columns[-1]
        
        return None
    
    def _assess_data_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Assess overall data quality."""
        total_cells = data.shape[0] * data.shape[1]
        missing_cells = data.isnull().sum().sum()
        missing_ratio = missing_cells / total_cells if total_cells > 0 else 0
        
        # Check for duplicates
        duplicate_rows = data.duplicated().sum()
        
        # Check for constant columns
        constant_cols = [col for col in data.columns if data[col].nunique() <= 1]
        
        # Calculate quality score
        quality_score = 1.0
        quality_score -= missing_ratio * 0.3
        quality_score -= (duplicate_rows / len(data)) * 0.2 if len(data) > 0 else 0
        quality_score -= (len(constant_cols) / len(data.columns)) * 0.2 if len(data.columns) > 0 else 0
        
        if quality_score >= 0.8:
            quality_level = "high"
        elif quality_score >= 0.6:
            quality_level = "medium"
        else:
            quality_level = "low"
        
        return {
            "quality_score": round(quality_score, 3),
            "quality_level": quality_level,
            "missing_ratio": round(missing_ratio, 4),
            "missing_cells": missing_cells,
            "duplicate_rows": duplicate_rows,
            "constant_columns": constant_cols,
            "issues": self._identify_quality_issues(data, missing_ratio, duplicate_rows, constant_cols)
        }
    
    def _identify_quality_issues(self, data: pd.DataFrame, missing_ratio: float, 
                                 duplicates: int, constant_cols: List[str]) -> List[str]:
        """Identify specific data quality issues."""
        issues = []
        
        if missing_ratio > 0.3:
            issues.append("High missing value ratio (>30%)")
        elif missing_ratio > 0.1:
            issues.append("Moderate missing values (10-30%)")
        
        if duplicates > len(data) * 0.1:
            issues.append("Significant duplicate rows detected")
        
        if len(constant_cols) > 0:
            issues.append(f"Constant columns detected: {constant_cols}")
        
        # Check for high cardinality categorical columns
        for col in data.select_dtypes(include=['object']).columns:
            if data[col].nunique() > 100:
                issues.append(f"High cardinality in column '{col}'")
        
        return issues
    
    def _analyze_features(self, data: pd.DataFrame, info: DatasetInfo) -> Dict[str, Any]:
        """Analyze feature characteristics."""
        feature_analysis = {
            "total_features": len(data.columns),
            "numeric_features": len(info.numeric_columns),
            "categorical_features": len(info.categorical_columns),
            "feature_types_distribution": {
                "numeric": len(info.numeric_columns),
                "categorical": len(info.categorical_columns),
                "other": len(data.columns) - len(info.numeric_columns) - len(info.categorical_columns)
            }
        }
        
        # Analyze numeric features
        if info.numeric_columns:
            numeric_stats = data[info.numeric_columns].describe()
            feature_analysis["numeric_summary"] = {
                "mean_range": (numeric_stats.loc['mean'].min(), numeric_stats.loc['mean'].max()),
                "std_range": (numeric_stats.loc['std'].min(), numeric_stats.loc['std'].max()),
                "requires_scaling": any(numeric_stats.loc['std'] > 10)
            }
        
        # Analyze categorical features
        if info.categorical_columns:
            cardinality = {col: data[col].nunique() for col in info.categorical_columns}
            feature_analysis["categorical_summary"] = {
                "cardinality": cardinality,
                "high_cardinality_cols": [col for col, card in cardinality.items() if card > 50]
            }
        
        return feature_analysis
    
    def _analyze_problem(self, data: pd.DataFrame, info: DatasetInfo) -> Dict[str, Any]:
        """Analyze problem characteristics."""
        problem_analysis = {
            "dataset_size": "small" if len(data) < 1000 else "medium" if len(data) < 100000 else "large",
            "dimensionality": "low" if len(data.columns) < 20 else "medium" if len(data.columns) < 100 else "high",
            "rows": len(data),
            "columns": len(data.columns)
        }
        
        # Infer problem type based on target column
        if info.target_column and info.target_column in data.columns:
            target = data[info.target_column]
            unique_values = target.nunique()
            
            if unique_values <= 2:
                problem_analysis["problem_type"] = "binary_classification"
                problem_analysis["class_balance"] = dict(target.value_counts(normalize=True))
            elif unique_values <= 20 and target.dtype == 'object':
                problem_analysis["problem_type"] = "multiclass_classification"
                problem_analysis["num_classes"] = unique_values
            else:
                problem_analysis["problem_type"] = "regression"
                problem_analysis["target_distribution"] = {
                    "mean": float(target.mean()) if np.issubdtype(target.dtype, np.number) else None,
                    "std": float(target.std()) if np.issubdtype(target.dtype, np.number) else None
                }
        else:
            problem_analysis["problem_type"] = "unknown"
        
        return problem_analysis
    
    def _generate_recommendations(self, data: pd.DataFrame, info: DatasetInfo) -> List[Dict[str, Any]]:
        """Generate preprocessing recommendations."""
        recommendations = []
        
        # Missing value recommendations
        total_missing = sum(info.missing_values.values())
        if total_missing > 0:
            missing_ratio = total_missing / (data.shape[0] * data.shape[1])
            if missing_ratio > 0.3:
                recommendations.append({
                    "type": "missing_values",
                    "severity": "high",
                    "recommendation": "Consider dropping columns with >50% missing or using advanced imputation"
                })
            else:
                recommendations.append({
                    "type": "missing_values", 
                    "severity": "medium",
                    "recommendation": "Apply intelligent imputation (median for numeric, mode for categorical)"
                })
        
        # Scaling recommendations
        numeric_cols = info.numeric_columns
        if len(numeric_cols) > 1:
            # Check if columns have very different scales
            mins = data[numeric_cols].min()
            maxs = data[numeric_cols].max()
            ranges = maxs - mins
            if ranges.std() > ranges.mean():
                recommendations.append({
                    "type": "feature_scaling",
                    "severity": "medium",
                    "recommendation": "Apply feature scaling (StandardScaler or RobustScaler)"
                })
        
        # Encoding recommendations
        if len(info.categorical_columns) > 0:
            high_cardinality = [col for col in info.categorical_columns if data[col].nunique() > 10]
            if high_cardinality:
                recommendations.append({
                    "type": "categorical_encoding",
                    "severity": "medium",
                    "recommendation": f"Use target encoding for high cardinality columns: {high_cardinality}"
                })
            else:
                recommendations.append({
                    "type": "categorical_encoding",
                    "severity": "low",
                    "recommendation": "Apply one-hot encoding for categorical columns"
                })
        
        return recommendations


class PipelinePlanner(PipelineOrchestrator):
    """
    Intelligent Pipeline Planner - Creates optimal ML pipelines automatically.
    
    This is the core planning engine for ADPA that:
    - Analyzes dataset characteristics
    - Determines optimal preprocessing steps
    - Selects appropriate algorithms
    - Creates execution plans with resource estimates
    """
    
    def __init__(self, config: Optional[PlannerConfig] = None):
        """
        Initialize the Pipeline Planner.
        
        Args:
            config: Planner configuration (uses defaults if not provided)
        """
        self.config = config or PlannerConfig()
        self.profiler = DataProfiler()
        self.logger = logging.getLogger(__name__)
        self.planning_history: List[PipelinePlan] = []
        
        self.logger.info("Pipeline Planner initialized")
    
    def plan_pipeline(self, 
                     data: pd.DataFrame,
                     objective: str,
                     target_column: Optional[str] = None,
                     constraints: Optional[Dict[str, Any]] = None) -> PipelinePlan:
        """
        Create an intelligent pipeline plan based on data and objectives.
        
        Args:
            data: Input dataset
            objective: ML objective (e.g., "classification", "regression", "predict churn")
            target_column: Optional target column name
            constraints: Optional constraints (time, resources, etc.)
            
        Returns:
            PipelinePlan with complete execution strategy
        """
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        self.logger.info(f"Creating pipeline plan {plan_id} for objective: {objective}")
        
        # Step 1: Profile the dataset
        detailed_profile = self.profiler.get_detailed_profile(data, target_column)
        dataset_info = DatasetInfo(**detailed_profile["basic_info"])
        
        # Step 2: Determine problem type
        problem_type = self._determine_problem_type(objective, detailed_profile)
        
        # Step 3: Assess complexity
        complexity = self._assess_complexity(detailed_profile)
        
        # Step 4: Generate pipeline steps
        steps = self._generate_pipeline_steps(detailed_profile, problem_type, complexity, constraints)
        
        # Step 5: Estimate resources
        resource_requirements = self._estimate_resources(steps, data.shape, complexity)
        
        # Step 6: Generate alternatives
        alternatives = self._generate_alternatives(detailed_profile, problem_type, complexity)
        
        # Step 7: Create reasoning explanation
        reasoning = self._generate_reasoning(detailed_profile, problem_type, steps)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(detailed_profile, problem_type, steps)
        
        plan = PipelinePlan(
            plan_id=plan_id,
            steps=steps,
            estimated_duration_minutes=resource_requirements["estimated_duration_minutes"],
            complexity=complexity,
            confidence_score=confidence,
            reasoning=reasoning,
            alternatives=alternatives,
            resource_requirements=resource_requirements,
            metadata={
                "created_at": datetime.now().isoformat(),
                "objective": objective,
                "problem_type": problem_type,
                "dataset_shape": data.shape,
                "data_quality": detailed_profile["data_quality"]["quality_level"],
                "planner_version": "1.0.0"
            }
        )
        
        self.planning_history.append(plan)
        self.logger.info(f"Created plan with {len(steps)} steps, complexity: {complexity.value}, confidence: {confidence:.2f}")
        
        return plan
    
    def create_pipeline_plan(self, dataset_info: DatasetInfo, config: PipelineConfig) -> List[PipelineStep]:
        """
        Implementation of PipelineOrchestrator interface.
        Creates pipeline steps from dataset info and config.
        """
        # Convert to internal format and create plan
        # This is a simplified version that returns step configurations
        steps = self._generate_pipeline_steps(
            {"basic_info": dataset_info.__dict__, "data_quality": {"quality_level": "medium"}},
            config.problem_type or "classification",
            PipelineComplexity.MODERATE,
            None
        )
        
        # Return step configurations (actual step objects created during execution)
        return steps
    
    def execute_pipeline(self, steps: List[PipelineStep], data: pd.DataFrame, 
                        config: PipelineConfig) -> ExecutionResult:
        """
        Implementation of PipelineOrchestrator interface.
        Execute pipeline using the executor.
        """
        from ..execution.executor import StepExecutor
        
        executor = StepExecutor()
        return executor.execute_pipeline(steps, data, config)
    
    def monitor_execution(self, pipeline_id: str) -> Dict[str, Any]:
        """Monitor pipeline execution status."""
        # Find plan in history
        for plan in self.planning_history:
            if plan.plan_id == pipeline_id:
                return {
                    "pipeline_id": pipeline_id,
                    "status": "completed",
                    "plan": plan.to_dict()
                }
        
        return {"pipeline_id": pipeline_id, "status": "not_found"}
    
    def _determine_problem_type(self, objective: str, profile: Dict[str, Any]) -> str:
        """Determine the ML problem type from objective and data."""
        objective_lower = objective.lower()
        
        # Keyword-based detection
        classification_keywords = ['classify', 'classification', 'predict class', 'categorize', 
                                   'churn', 'fraud', 'spam', 'sentiment', 'binary', 'multiclass']
        regression_keywords = ['regression', 'predict value', 'forecast', 'sales', 'price', 
                              'revenue', 'continuous', 'estimate']
        clustering_keywords = ['cluster', 'segment', 'group', 'unsupervised']
        
        for keyword in classification_keywords:
            if keyword in objective_lower:
                return "classification"
        
        for keyword in regression_keywords:
            if keyword in objective_lower:
                return "regression"
        
        for keyword in clustering_keywords:
            if keyword in objective_lower:
                return "clustering"
        
        # Fallback to profile-based detection
        return profile.get("problem_characteristics", {}).get("problem_type", "classification")
    
    def _assess_complexity(self, profile: Dict[str, Any]) -> PipelineComplexity:
        """Assess pipeline complexity based on dataset profile."""
        complexity_score = 0
        
        basic_info = profile.get("basic_info", {})
        data_quality = profile.get("data_quality", {})
        feature_analysis = profile.get("feature_analysis", {})
        
        # Dataset size factor
        rows = basic_info.get("shape", (0, 0))[0]
        cols = basic_info.get("shape", (0, 0))[1]
        
        if rows > 100000:
            complexity_score += 2
        elif rows > 10000:
            complexity_score += 1
        
        if cols > 100:
            complexity_score += 2
        elif cols > 50:
            complexity_score += 1
        
        # Data quality factor
        if data_quality.get("quality_level") == "low":
            complexity_score += 2
        elif data_quality.get("quality_level") == "medium":
            complexity_score += 1
        
        # Feature complexity
        high_cardinality = feature_analysis.get("categorical_summary", {}).get("high_cardinality_cols", [])
        if len(high_cardinality) > 3:
            complexity_score += 1
        
        # Map score to complexity level
        if complexity_score >= 5:
            return PipelineComplexity.ADVANCED
        elif complexity_score >= 3:
            return PipelineComplexity.COMPLEX
        elif complexity_score >= 1:
            return PipelineComplexity.MODERATE
        else:
            return PipelineComplexity.SIMPLE
    
    def _generate_pipeline_steps(self, profile: Dict[str, Any], problem_type: str,
                                complexity: PipelineComplexity, 
                                constraints: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate the pipeline steps based on analysis."""
        steps = []
        step_order = 0
        
        basic_info = profile.get("basic_info", {})
        data_quality = profile.get("data_quality", {})
        recommendations = profile.get("recommendations", [])
        
        # Step 1: Data Validation (always included)
        step_order += 1
        steps.append({
            "order": step_order,
            "name": "data_validation",
            "type": PipelineStepType.INGESTION.value,
            "description": "Validate data schema and integrity",
            "parameters": {
                "check_schema": True,
                "check_missing": True,
                "check_duplicates": True,
                "validate_types": True
            },
            "estimated_duration_seconds": 30,
            "critical": True
        })
        
        # Step 2: Missing Value Handling (if needed)
        if sum(basic_info.get("missing_values", {}).values()) > 0:
            step_order += 1
            missing_strategy = self._select_missing_value_strategy(profile)
            steps.append({
                "order": step_order,
                "name": "missing_value_imputation",
                "type": PipelineStepType.CLEANING.value,
                "description": "Handle missing values with intelligent imputation",
                "parameters": {
                    "strategy": missing_strategy,
                    "numeric_method": "median",
                    "categorical_method": "mode",
                    "drop_threshold": 0.5
                },
                "estimated_duration_seconds": 60,
                "critical": True
            })
        
        # Step 3: Outlier Detection (for numeric data)
        if len(basic_info.get("numeric_columns", [])) > 0:
            step_order += 1
            steps.append({
                "order": step_order,
                "name": "outlier_detection",
                "type": PipelineStepType.CLEANING.value,
                "description": "Detect and handle outliers in numeric features",
                "parameters": {
                    "method": "iqr",
                    "action": "clip",
                    "threshold": 1.5
                },
                "estimated_duration_seconds": 45,
                "critical": False
            })
        
        # Step 4: Categorical Encoding (if categorical columns exist)
        if len(basic_info.get("categorical_columns", [])) > 0:
            step_order += 1
            encoding_strategy = self._select_encoding_strategy(profile)
            steps.append({
                "order": step_order,
                "name": "categorical_encoding",
                "type": PipelineStepType.FEATURE_ENGINEERING.value,
                "description": "Encode categorical variables",
                "parameters": encoding_strategy,
                "estimated_duration_seconds": 60,
                "critical": True
            })
        
        # Step 5: Feature Scaling (if enabled and needed)
        if self.config.enable_feature_engineering and len(basic_info.get("numeric_columns", [])) > 1:
            step_order += 1
            steps.append({
                "order": step_order,
                "name": "feature_scaling",
                "type": PipelineStepType.FEATURE_ENGINEERING.value,
                "description": "Scale numeric features for model training",
                "parameters": {
                    "method": "standard",  # or "minmax", "robust"
                    "columns": basic_info.get("numeric_columns", [])
                },
                "estimated_duration_seconds": 30,
                "critical": False
            })
        
        # Step 6: Feature Engineering (if enabled)
        if self.config.enable_feature_engineering and complexity in [PipelineComplexity.MODERATE, 
                                                                      PipelineComplexity.COMPLEX,
                                                                      PipelineComplexity.ADVANCED]:
            step_order += 1
            fe_strategy = self._select_feature_engineering_strategy(profile, complexity)
            steps.append({
                "order": step_order,
                "name": "feature_engineering",
                "type": PipelineStepType.FEATURE_ENGINEERING.value,
                "description": "Create new features to improve model performance",
                "parameters": fe_strategy,
                "estimated_duration_seconds": 120,
                "critical": False
            })
        
        # Step 7: Feature Selection (for high-dimensional data)
        if len(basic_info.get("columns", [])) > 50:
            step_order += 1
            steps.append({
                "order": step_order,
                "name": "feature_selection",
                "type": PipelineStepType.FEATURE_ENGINEERING.value,
                "description": "Select most important features",
                "parameters": {
                    "method": "mutual_information" if problem_type == "classification" else "f_regression",
                    "k_best": min(50, len(basic_info.get("columns", [])) // 2),
                    "use_rfe": complexity == PipelineComplexity.ADVANCED
                },
                "estimated_duration_seconds": 90,
                "critical": False
            })
        
        # Step 8: Train-Test Split
        step_order += 1
        steps.append({
            "order": step_order,
            "name": "train_test_split",
            "type": PipelineStepType.TRAINING.value,
            "description": "Split data into training and testing sets",
            "parameters": {
                "test_size": 0.2,
                "stratify": problem_type == "classification",
                "random_state": 42
            },
            "estimated_duration_seconds": 10,
            "critical": True
        })
        
        # Step 9: Model Training
        step_order += 1
        model_config = self._select_model_configuration(profile, problem_type, complexity)
        steps.append({
            "order": step_order,
            "name": "model_training",
            "type": PipelineStepType.TRAINING.value,
            "description": f"Train {model_config['algorithm']} model",
            "parameters": model_config,
            "estimated_duration_seconds": self._estimate_training_time(profile, model_config),
            "critical": True
        })
        
        # Step 10: Hyperparameter Tuning (if enabled)
        if self.config.enable_hyperparameter_tuning and complexity != PipelineComplexity.SIMPLE:
            step_order += 1
            steps.append({
                "order": step_order,
                "name": "hyperparameter_tuning",
                "type": PipelineStepType.TRAINING.value,
                "description": "Optimize model hyperparameters",
                "parameters": {
                    "method": "random_search" if complexity == PipelineComplexity.MODERATE else "bayesian",
                    "n_iterations": 20 if complexity == PipelineComplexity.MODERATE else 50,
                    "cv_folds": 5,
                    "scoring": self.config.optimization_metric
                },
                "estimated_duration_seconds": 300,
                "critical": False
            })
        
        # Step 11: Model Evaluation
        step_order += 1
        eval_metrics = self._select_evaluation_metrics(problem_type)
        steps.append({
            "order": step_order,
            "name": "model_evaluation",
            "type": PipelineStepType.EVALUATION.value,
            "description": "Evaluate model performance",
            "parameters": {
                "metrics": eval_metrics,
                "generate_plots": True,
                "cross_validate": self.config.enable_cross_validation,
                "cv_folds": 5
            },
            "estimated_duration_seconds": 60,
            "critical": True
        })
        
        # Step 12: Model Interpretation (if interpretability preferred)
        if self.config.prefer_interpretability:
            step_order += 1
            steps.append({
                "order": step_order,
                "name": "model_interpretation",
                "type": PipelineStepType.EVALUATION.value,
                "description": "Generate model explanations and feature importance",
                "parameters": {
                    "methods": ["feature_importance", "shap_values"],
                    "sample_size": min(1000, basic_info.get("shape", (1000, 0))[0])
                },
                "estimated_duration_seconds": 120,
                "critical": False
            })
        
        # Step 13: Reporting
        step_order += 1
        steps.append({
            "order": step_order,
            "name": "generate_report",
            "type": PipelineStepType.REPORTING.value,
            "description": "Generate comprehensive pipeline report",
            "parameters": {
                "include_metrics": True,
                "include_visualizations": True,
                "include_recommendations": True,
                "format": "html"
            },
            "estimated_duration_seconds": 30,
            "critical": False
        })
        
        return steps
    
    def _select_missing_value_strategy(self, profile: Dict[str, Any]) -> str:
        """Select appropriate missing value handling strategy."""
        missing_values = profile.get("basic_info", {}).get("missing_values", {})
        total_missing = sum(missing_values.values())
        total_cells = profile.get("basic_info", {}).get("shape", (1, 1))[0] * profile.get("basic_info", {}).get("shape", (1, 1))[1]
        
        missing_ratio = total_missing / total_cells if total_cells > 0 else 0
        
        if missing_ratio < 0.05:
            return "simple_imputation"
        elif missing_ratio < 0.2:
            return "iterative_imputation"
        else:
            return "advanced_imputation"
    
    def _select_encoding_strategy(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate encoding strategy for categorical variables."""
        categorical_summary = profile.get("feature_analysis", {}).get("categorical_summary", {})
        high_cardinality = categorical_summary.get("high_cardinality_cols", [])
        
        return {
            "default_method": "one_hot",
            "high_cardinality_method": "target_encoding",
            "high_cardinality_columns": high_cardinality,
            "handle_unknown": "ignore"
        }
    
    def _select_feature_engineering_strategy(self, profile: Dict[str, Any], 
                                            complexity: PipelineComplexity) -> Dict[str, Any]:
        """Select feature engineering strategy based on complexity."""
        strategies = {
            "create_interactions": complexity in [PipelineComplexity.COMPLEX, PipelineComplexity.ADVANCED],
            "create_polynomial": complexity == PipelineComplexity.ADVANCED,
            "create_aggregations": True,
            "create_ratios": True,
            "max_interaction_degree": 2 if complexity == PipelineComplexity.COMPLEX else 3
        }
        
        return strategies
    
    def _select_model_configuration(self, profile: Dict[str, Any], problem_type: str,
                                   complexity: PipelineComplexity) -> Dict[str, Any]:
        """Select model configuration based on problem type and complexity."""
        rows = profile.get("basic_info", {}).get("shape", (1000, 10))[0]
        
        if problem_type == "classification":
            if complexity == PipelineComplexity.SIMPLE:
                return {
                    "algorithm": "logistic_regression",
                    "params": {"max_iter": 1000, "random_state": 42}
                }
            elif complexity == PipelineComplexity.MODERATE:
                return {
                    "algorithm": "random_forest",
                    "params": {"n_estimators": 100, "max_depth": 10, "random_state": 42}
                }
            else:
                return {
                    "algorithm": "gradient_boosting",
                    "params": {"n_estimators": 200, "max_depth": 6, "learning_rate": 0.1, "random_state": 42}
                }
        
        elif problem_type == "regression":
            if complexity == PipelineComplexity.SIMPLE:
                return {
                    "algorithm": "linear_regression",
                    "params": {}
                }
            elif complexity == PipelineComplexity.MODERATE:
                return {
                    "algorithm": "random_forest_regressor",
                    "params": {"n_estimators": 100, "max_depth": 15, "random_state": 42}
                }
            else:
                return {
                    "algorithm": "gradient_boosting_regressor",
                    "params": {"n_estimators": 200, "max_depth": 6, "learning_rate": 0.1, "random_state": 42}
                }
        
        else:  # clustering
            return {
                "algorithm": "kmeans",
                "params": {"n_clusters": 5, "random_state": 42}
            }
    
    def _select_evaluation_metrics(self, problem_type: str) -> List[str]:
        """Select appropriate evaluation metrics."""
        if problem_type == "classification":
            return ["accuracy", "precision", "recall", "f1_score", "roc_auc"]
        elif problem_type == "regression":
            return ["mae", "mse", "rmse", "r2_score", "mape"]
        else:
            return ["silhouette_score", "calinski_harabasz", "davies_bouldin"]
    
    def _estimate_training_time(self, profile: Dict[str, Any], model_config: Dict[str, Any]) -> int:
        """Estimate training time in seconds."""
        rows = profile.get("basic_info", {}).get("shape", (1000, 10))[0]
        cols = profile.get("basic_info", {}).get("shape", (1000, 10))[1]
        
        # Base time
        base_time = 60
        
        # Scale by data size
        size_factor = (rows * cols) / 10000
        
        # Scale by algorithm complexity
        algorithm = model_config.get("algorithm", "")
        if "gradient_boosting" in algorithm.lower() or "xgboost" in algorithm.lower():
            algo_factor = 3.0
        elif "random_forest" in algorithm.lower():
            algo_factor = 2.0
        elif "neural" in algorithm.lower() or "deep" in algorithm.lower():
            algo_factor = 5.0
        else:
            algo_factor = 1.0
        
        return int(base_time * max(1, size_factor) * algo_factor)
    
    def _estimate_resources(self, steps: List[Dict[str, Any]], data_shape: tuple,
                           complexity: PipelineComplexity) -> Dict[str, Any]:
        """Estimate resource requirements for the pipeline."""
        total_duration = sum(step.get("estimated_duration_seconds", 60) for step in steps)
        
        memory_gb = max(1, (data_shape[0] * data_shape[1] * 8) / (1024 ** 3) * 3)  # 3x data size for processing
        
        return {
            "estimated_duration_minutes": total_duration // 60 + 1,
            "estimated_duration_seconds": total_duration,
            "memory_requirements_gb": round(memory_gb, 2),
            "cpu_cores_recommended": 4 if complexity in [PipelineComplexity.COMPLEX, PipelineComplexity.ADVANCED] else 2,
            "gpu_recommended": complexity == PipelineComplexity.ADVANCED,
            "parallel_execution": True
        }
    
    def _generate_alternatives(self, profile: Dict[str, Any], problem_type: str,
                              complexity: PipelineComplexity) -> List[Dict[str, Any]]:
        """Generate alternative pipeline approaches."""
        alternatives = []
        
        # Alternative 1: Simpler approach
        alternatives.append({
            "name": "simple_pipeline",
            "description": "Faster, simpler pipeline with basic preprocessing",
            "trade_offs": ["Faster execution", "Lower accuracy potential", "Less feature engineering"],
            "recommended_when": "Quick iteration or baseline comparison"
        })
        
        # Alternative 2: AutoML
        alternatives.append({
            "name": "automl_pipeline",
            "description": "Automated machine learning with algorithm search",
            "trade_offs": ["Automated optimization", "Longer execution", "Less control"],
            "recommended_when": "When you want hands-off optimization"
        })
        
        # Alternative 3: Deep learning (for complex problems)
        if complexity in [PipelineComplexity.COMPLEX, PipelineComplexity.ADVANCED]:
            alternatives.append({
                "name": "deep_learning_pipeline",
                "description": "Neural network based approach for complex patterns",
                "trade_offs": ["Better complex pattern recognition", "Requires more data", "Less interpretable"],
                "recommended_when": "Large datasets with complex patterns"
            })
        
        return alternatives
    
    def _generate_reasoning(self, profile: Dict[str, Any], problem_type: str,
                           steps: List[Dict[str, Any]]) -> str:
        """Generate reasoning explanation for the pipeline plan."""
        basic_info = profile.get("basic_info", {})
        data_quality = profile.get("data_quality", {})
        
        reasoning = f"""
Pipeline Planning Analysis:

1. Dataset Characteristics:
   - Shape: {basic_info.get('shape', 'Unknown')}
   - Data Quality: {data_quality.get('quality_level', 'Unknown')}
   - Missing Data: {data_quality.get('missing_ratio', 0)*100:.1f}%
   - Numeric Features: {len(basic_info.get('numeric_columns', []))}
   - Categorical Features: {len(basic_info.get('categorical_columns', []))}

2. Problem Type: {problem_type}

3. Pipeline Strategy:
   - Total Steps: {len(steps)}
   - Key Processing: {'Missing value imputation required' if data_quality.get('missing_ratio', 0) > 0 else 'Clean data'}
   - Feature Engineering: {'Enabled' if self.config.enable_feature_engineering else 'Disabled'}
   - Hyperparameter Tuning: {'Enabled' if self.config.enable_hyperparameter_tuning else 'Disabled'}

4. Rationale:
   - Selected preprocessing steps based on data quality assessment
   - Chose algorithm appropriate for dataset size and complexity
   - Included feature engineering to maximize model performance
   - Added evaluation metrics relevant to {problem_type} problems
        """
        
        return reasoning.strip()
    
    def _calculate_confidence(self, profile: Dict[str, Any], problem_type: str,
                             steps: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for the pipeline plan."""
        confidence = 0.7  # Base confidence
        
        # Adjust based on data quality
        quality_level = profile.get("data_quality", {}).get("quality_level", "medium")
        if quality_level == "high":
            confidence += 0.15
        elif quality_level == "low":
            confidence -= 0.15
        
        # Adjust based on number of issues
        issues = profile.get("data_quality", {}).get("issues", [])
        confidence -= len(issues) * 0.03
        
        # Ensure confidence is in valid range
        return max(0.3, min(0.95, confidence))
    
    def get_planning_history(self) -> List[Dict[str, Any]]:
        """Get the history of created pipeline plans."""
        return [plan.to_dict() for plan in self.planning_history]
    
    def explain_step(self, step_name: str) -> str:
        """Get detailed explanation for a pipeline step."""
        explanations = {
            "data_validation": "Validates data integrity, checks for schema issues, and ensures data meets quality requirements.",
            "missing_value_imputation": "Fills missing values using statistical methods (mean, median, mode) or advanced techniques like iterative imputation.",
            "outlier_detection": "Identifies and handles outliers using statistical methods like IQR or Z-score to prevent model bias.",
            "categorical_encoding": "Converts categorical variables to numeric format using techniques like one-hot encoding or target encoding.",
            "feature_scaling": "Normalizes or standardizes numeric features to ensure they contribute equally to model training.",
            "feature_engineering": "Creates new features from existing ones to capture additional patterns and improve model performance.",
            "feature_selection": "Selects the most relevant features to reduce dimensionality and prevent overfitting.",
            "train_test_split": "Divides data into training and testing sets for model evaluation.",
            "model_training": "Trains the selected machine learning algorithm on the prepared data.",
            "hyperparameter_tuning": "Optimizes model parameters using techniques like grid search or Bayesian optimization.",
            "model_evaluation": "Assesses model performance using appropriate metrics and cross-validation.",
            "model_interpretation": "Generates feature importance scores and SHAP values to explain model predictions.",
            "generate_report": "Creates a comprehensive report with metrics, visualizations, and recommendations."
        }
        
        return explanations.get(step_name, f"No explanation available for step: {step_name}")
