"""
Pipeline planning module for ADPA.
"""

import logging
from typing import List, Dict, Any, Optional
from ..core.interfaces import (
    PipelineStep, PipelineStepType, DatasetInfo, PipelineConfig,
    PipelineOrchestrator
)


class PipelinePlanner(PipelineOrchestrator):
    """
    Plans and creates pipeline execution sequences based on dataset characteristics
    and objectives.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define step templates
        self.step_templates = {
            PipelineStepType.INGESTION: self._create_ingestion_step,
            PipelineStepType.CLEANING: self._create_cleaning_step,
            PipelineStepType.FEATURE_ENGINEERING: self._create_feature_engineering_step,
            PipelineStepType.TRAINING: self._create_training_step,
            PipelineStepType.EVALUATION: self._create_evaluation_step,
            PipelineStepType.REPORTING: self._create_reporting_step
        }
    
    def create_pipeline_plan(self, 
                           dataset_info: DatasetInfo, 
                           config: PipelineConfig) -> List[PipelineStep]:
        """
        Create a complete pipeline plan based on dataset characteristics and config.
        
        Args:
            dataset_info: Information about the dataset
            config: Pipeline configuration
            
        Returns:
            List of ordered pipeline steps
        """
        self.logger.info("Creating pipeline plan...")
        
        steps = []
        
        # Step 1: Data ingestion (if needed)
        if self._needs_ingestion_step(dataset_info):
            steps.append(self._create_ingestion_step(dataset_info, config))
        
        # Step 2: Data cleaning (almost always needed)
        steps.append(self._create_cleaning_step(dataset_info, config))
        
        # Step 3: Feature engineering
        if self._needs_feature_engineering(dataset_info, config):
            steps.append(self._create_feature_engineering_step(dataset_info, config))
        
        # Step 4: Model training
        steps.append(self._create_training_step(dataset_info, config))
        
        # Step 5: Model evaluation
        steps.append(self._create_evaluation_step(dataset_info, config))
        
        # Step 6: Reporting
        steps.append(self._create_reporting_step(dataset_info, config))
        
        self.logger.info(f"Created pipeline with {len(steps)} steps")
        return steps
    
    def execute_pipeline(self, 
                        steps: List[PipelineStep], 
                        data, 
                        config: PipelineConfig):
        """Execute pipeline - delegated to StepExecutor."""
        raise NotImplementedError("Pipeline execution is handled by StepExecutor")
    
    def monitor_execution(self, pipeline_id: str) -> Dict[str, Any]:
        """Monitor pipeline execution - delegated to monitoring system."""
        raise NotImplementedError("Pipeline monitoring is handled by monitoring system")
    
    def _needs_ingestion_step(self, dataset_info: DatasetInfo) -> bool:
        """Determine if data ingestion step is needed."""
        # For now, assume data is already loaded
        return False
    
    def _needs_feature_engineering(self, dataset_info: DatasetInfo, config: PipelineConfig) -> bool:
        """Determine if feature engineering step is needed."""
        # Check if we have categorical variables that need encoding
        has_categorical = len(dataset_info.categorical_columns) > 0
        
        # Check if we have many features that might need selection
        has_many_features = len(dataset_info.columns) > 50
        
        # Check for missing values that need handling
        has_missing_values = any(count > 0 for count in dataset_info.missing_values.values())
        
        return has_categorical or has_many_features or has_missing_values
    
    def _create_ingestion_step(self, dataset_info: DatasetInfo, config: PipelineConfig) -> PipelineStep:
        """Create data ingestion step."""
        from ...pipeline.ingestion.data_loader import DataIngestionStep
        return DataIngestionStep()
    
    def _create_cleaning_step(self, dataset_info: DatasetInfo, config: PipelineConfig) -> PipelineStep:
        """Create data cleaning step."""
        from ...pipeline.etl.cleaner import DataCleaningStep
        
        # Determine cleaning strategy based on data characteristics
        cleaning_config = {
            "missing_value_strategy": self._choose_missing_value_strategy(dataset_info),
            "outlier_detection": self._should_detect_outliers(dataset_info),
            "duplicate_removal": True,
            "data_type_conversion": True
        }
        
        return DataCleaningStep(config=cleaning_config)
    
    def _create_feature_engineering_step(self, dataset_info: DatasetInfo, config: PipelineConfig) -> PipelineStep:
        """Create feature engineering step."""
        from ...pipeline.etl.feature_engineer import FeatureEngineeringStep
        
        # Determine feature engineering strategy
        fe_config = {
            "categorical_encoding": self._choose_categorical_encoding(dataset_info),
            "feature_scaling": self._choose_feature_scaling(dataset_info, config),
            "feature_selection": self._should_do_feature_selection(dataset_info),
            "create_polynomial_features": len(dataset_info.numeric_columns) <= 10
        }
        
        return FeatureEngineeringStep(config=fe_config)
    
    def _create_training_step(self, dataset_info: DatasetInfo, config: PipelineConfig) -> PipelineStep:
        """Create model training step."""
        from ...pipeline.training.trainer import ModelTrainingStep
        
        # Choose models based on problem type and dataset size
        models_to_try = self._choose_models(dataset_info, config)
        
        training_config = {
            "problem_type": config.problem_type,
            "models": models_to_try,
            "cross_validation": True,
            "hyperparameter_tuning": dataset_info.shape[0] > 1000,  # Only for larger datasets
            "test_size": config.test_size
        }
        
        return ModelTrainingStep(config=training_config)
    
    def _create_evaluation_step(self, dataset_info: DatasetInfo, config: PipelineConfig) -> PipelineStep:
        """Create model evaluation step."""
        from ...pipeline.evaluation.evaluator import ModelEvaluationStep
        
        eval_config = {
            "problem_type": config.problem_type,
            "metrics": self._choose_evaluation_metrics(config),
            "create_plots": True,
            "feature_importance": True
        }
        
        return ModelEvaluationStep(config=eval_config)
    
    def _create_reporting_step(self, dataset_info: DatasetInfo, config: PipelineConfig) -> PipelineStep:
        """Create reporting step."""
        from ...pipeline.evaluation.reporter import ReportingStep
        
        report_config = {
            "include_data_profile": True,
            "include_model_performance": True,
            "include_feature_importance": True,
            "include_recommendations": True,
            "format": "html"
        }
        
        return ReportingStep(config=report_config)
    
    def _choose_missing_value_strategy(self, dataset_info: DatasetInfo) -> str:
        """Choose missing value handling strategy."""
        missing_ratio = sum(dataset_info.missing_values.values()) / (dataset_info.shape[0] * dataset_info.shape[1])
        
        if missing_ratio < 0.05:
            return "drop"
        elif missing_ratio < 0.3:
            return "impute"
        else:
            return "advanced_impute"
    
    def _should_detect_outliers(self, dataset_info: DatasetInfo) -> bool:
        """Determine if outlier detection is needed."""
        return len(dataset_info.numeric_columns) > 0
    
    def _choose_categorical_encoding(self, dataset_info: DatasetInfo) -> str:
        """Choose categorical encoding strategy."""
        max_categories = 0
        for col in dataset_info.categorical_columns:
            # This is a simplified heuristic
            max_categories = max(max_categories, 20)  # Assume max 20 categories for now
        
        if max_categories <= 5:
            return "onehot"
        else:
            return "target"
    
    def _choose_feature_scaling(self, dataset_info: DatasetInfo, config: PipelineConfig) -> str:
        """Choose feature scaling method."""
        if config.problem_type == "classification":
            return "standard"
        else:
            return "robust"
    
    def _should_do_feature_selection(self, dataset_info: DatasetInfo) -> bool:
        """Determine if feature selection is needed."""
        return len(dataset_info.columns) > 20
    
    def _choose_models(self, dataset_info: DatasetInfo, config: PipelineConfig) -> List[str]:
        """Choose models to try based on problem type and dataset characteristics."""
        if config.problem_type == "classification":
            if dataset_info.shape[0] < 1000:
                return ["logistic_regression", "random_forest", "svm"]
            else:
                return ["logistic_regression", "random_forest", "gradient_boosting"]
        else:  # regression
            if dataset_info.shape[0] < 1000:
                return ["linear_regression", "random_forest", "svm"]
            else:
                return ["linear_regression", "random_forest", "gradient_boosting"]
    
    def _choose_evaluation_metrics(self, config: PipelineConfig) -> List[str]:
        """Choose appropriate evaluation metrics."""
        if config.problem_type == "classification":
            return ["accuracy", "precision", "recall", "f1", "roc_auc"]
        else:  # regression
            return ["mse", "rmse", "mae", "r2"]