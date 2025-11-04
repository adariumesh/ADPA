"""
Model training pipeline step with SageMaker integration.
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional
import pandas as pd

from ...agent.core.interfaces import PipelineStep, PipelineStepType, ExecutionResult, StepStatus
from ...aws.sagemaker.client import SageMakerClient


class ModelTrainingStep(PipelineStep):
    """
    Pipeline step for ML model training using SageMaker.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.TRAINING, "model_training")
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize SageMaker client
        self.sagemaker_client = SageMakerClient()
    
    def execute(self, 
                data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Execute model training step.
        
        Args:
            data: Input dataset (optional if using S3 path)
            config: Step configuration
            context: Execution context
            
        Returns:
            ExecutionResult with training results
        """
        try:
            self.logger.info("Starting model training...")
            
            # Merge configurations
            training_config = {**self.config, **(config or {})}
            
            # Determine training approach
            use_automl = training_config.get('use_automl', True)
            
            if use_automl:
                result = self._train_with_automl(data, training_config, context)
            else:
                result = self._train_with_custom_algorithm(data, training_config, context)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Model training failed: {str(e)}")
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[f"Model training error: {str(e)}"]
            )
    
    def validate_inputs(self, 
                       data: Optional[pd.DataFrame] = None,
                       config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate inputs for model training step.
        
        Args:
            data: Input dataset
            config: Step configuration
            
        Returns:
            True if inputs are valid
        """
        # Check if we have either data or S3 path
        if data is None and not config.get('input_s3_path'):
            self.logger.error("No input data or S3 path provided")
            return False
        
        # Check required configuration
        required_fields = ['problem_type']
        for field in required_fields:
            if not config.get(field):
                self.logger.error(f"Missing required configuration: {field}")
                return False
        
        return True
    
    def _train_with_automl(self, 
                          data: Optional[pd.DataFrame],
                          config: Dict[str, Any],
                          context: Optional[Dict[str, Any]]) -> ExecutionResult:
        """
        Train model using SageMaker AutoML.
        
        Args:
            data: Input dataset
            config: Training configuration
            context: Execution context
            
        Returns:
            ExecutionResult with AutoML training results
        """
        self.logger.info("Training with SageMaker AutoML...")
        
        # Generate job name
        timestamp = int(time.time())
        job_name = f"adpa-automl-{timestamp}"
        
        # Prepare input data configuration
        input_data_config = self._prepare_input_data_config(data, config, context)
        
        # Prepare output configuration
        output_data_config = {
            'S3OutputPath': config.get('output_s3_path', f"s3://{config.get('bucket', 'adpa-bucket')}/models/{job_name}/")
        }
        
        # Get IAM role (would be configured properly in production)
        role_arn = config.get('role_arn', 'arn:aws:iam::123456789012:role/ADPASageMakerRole')
        
        # Determine problem type and target
        problem_type = self._map_problem_type(config.get('problem_type', 'classification'))
        target_attribute = config.get('target_column', 'target')
        
        # Create AutoML job
        create_result = self.sagemaker_client.create_automl_job(
            job_name=job_name,
            input_data_config=input_data_config,
            output_data_config=output_data_config,
            role_arn=role_arn,
            problem_type=problem_type,
            target_attribute=target_attribute
        )
        
        if create_result.status.value != "completed":
            return create_result
        
        # Monitor training (with shorter timeout for demo)
        max_wait_time = config.get('max_wait_time', 3600)  # 1 hour default
        
        self.logger.info(f"Monitoring AutoML job: {job_name}")
        final_status = self.sagemaker_client.wait_for_completion(
            job_name, "automl", max_wait_time
        )
        
        if 'error' in final_status:
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[final_status['error']]
            )
        
        # Extract training results
        training_metrics = self._extract_automl_results(final_status)
        
        return ExecutionResult(
            status=StepStatus.COMPLETED,
            metrics=training_metrics,
            artifacts={
                'automl_job_name': job_name,
                'model_location': output_data_config['S3OutputPath'],
                'console_url': create_result.artifacts.get('console_url'),
                'training_approach': 'automl'
            },
            step_output={
                'model_ready': True,
                'best_model_info': final_status.get('best_candidate', {}),
                'training_duration': final_status.get('duration_seconds', 0)
            }
        )
    
    def _train_with_custom_algorithm(self, 
                                   data: Optional[pd.DataFrame],
                                   config: Dict[str, Any],
                                   context: Optional[Dict[str, Any]]) -> ExecutionResult:
        """
        Train model using SageMaker built-in algorithms.
        
        Args:
            data: Input dataset
            config: Training configuration
            context: Execution context
            
        Returns:
            ExecutionResult with training results
        """
        self.logger.info("Training with SageMaker built-in algorithm...")
        
        # Generate job name
        timestamp = int(time.time())
        job_name = f"adpa-training-{timestamp}"
        
        # Determine algorithm
        algorithm_name = config.get('algorithm', 'xgboost')
        image_uri = self.sagemaker_client.get_built_in_algorithm_image_uri(algorithm_name)
        
        # Prepare algorithm specification
        algorithm_specification = {
            'TrainingImage': image_uri,
            'TrainingInputMode': 'File'
        }
        
        # Prepare input data configuration
        input_data_config = self._prepare_input_data_config(data, config, context)
        
        # Prepare output configuration
        output_data_config = {
            'S3OutputPath': config.get('output_s3_path', f"s3://{config.get('bucket', 'adpa-bucket')}/models/{job_name}/")
        }
        
        # Get IAM role
        role_arn = config.get('role_arn', 'arn:aws:iam::123456789012:role/ADPASageMakerRole')
        
        # Instance configuration
        instance_config = {
            'InstanceType': config.get('instance_type', 'ml.m5.large'),
            'InstanceCount': config.get('instance_count', 1),
            'VolumeSizeInGB': config.get('volume_size', 20)
        }
        
        # Create training job
        create_result = self.sagemaker_client.create_training_job(
            job_name=job_name,
            algorithm_specification=algorithm_specification,
            input_data_config=input_data_config,
            output_data_config=output_data_config,
            role_arn=role_arn,
            instance_config=instance_config
        )
        
        if create_result.status.value != "completed":
            return create_result
        
        # Monitor training
        max_wait_time = config.get('max_wait_time', 3600)
        
        self.logger.info(f"Monitoring training job: {job_name}")
        final_status = self.sagemaker_client.wait_for_completion(
            job_name, "training", max_wait_time
        )
        
        if 'error' in final_status:
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[final_status['error']]
            )
        
        # Extract training results
        training_metrics = self._extract_training_results(final_status)
        
        return ExecutionResult(
            status=StepStatus.COMPLETED,
            metrics=training_metrics,
            artifacts={
                'training_job_name': job_name,
                'model_location': output_data_config['S3OutputPath'],
                'algorithm': algorithm_name,
                'console_url': create_result.artifacts.get('console_url'),
                'training_approach': 'custom_algorithm'
            },
            step_output={
                'model_ready': True,
                'training_duration': final_status.get('training_duration_seconds', 0)
            }
        )
    
    def _prepare_input_data_config(self, 
                                 data: Optional[pd.DataFrame],
                                 config: Dict[str, Any],
                                 context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare input data configuration for SageMaker.
        
        Args:
            data: Input dataset
            config: Configuration
            context: Execution context
            
        Returns:
            List of input data configuration dictionaries
        """
        # If S3 path is provided in config, use it
        if config.get('input_s3_path'):
            s3_path = config['input_s3_path']
        elif context and context.get('s3_data_path'):
            s3_path = context['s3_data_path']
        else:
            # Default path construction
            bucket = config.get('bucket', 'adpa-bucket')
            prefix = config.get('data_prefix', 'processed-data')
            s3_path = f"s3://{bucket}/{prefix}/"
        
        input_data_config = [
            {
                'ChannelName': 'training',
                'DataSource': {
                    'S3DataSource': {
                        'S3DataType': 'S3Prefix',
                        'S3Uri': s3_path,
                        'S3DataDistributionType': 'FullyReplicated'
                    }
                },
                'ContentType': 'text/csv',
                'CompressionType': 'None',
                'InputMode': 'File'
            }
        ]
        
        return input_data_config
    
    def _map_problem_type(self, problem_type: str) -> str:
        """
        Map problem type to SageMaker AutoML format.
        
        Args:
            problem_type: Problem type string
            
        Returns:
            SageMaker-compatible problem type
        """
        mapping = {
            'classification': 'BinaryClassification',
            'binary_classification': 'BinaryClassification',
            'multiclass_classification': 'MulticlassClassification',
            'regression': 'Regression'
        }
        
        return mapping.get(problem_type.lower(), 'BinaryClassification')
    
    def _extract_automl_results(self, final_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metrics from AutoML job results.
        
        Args:
            final_status: Final status from AutoML job monitoring
            
        Returns:
            Dictionary of training metrics
        """
        metrics = {
            'job_status': final_status.get('automl_job_status', 'Unknown'),
            'problem_type': final_status.get('problem_type', 'Unknown'),
            'objective_metric': final_status.get('objective_metric', 'Unknown'),
            'training_duration_seconds': final_status.get('duration_seconds', 0)
        }
        
        # Extract best candidate metrics
        if 'best_candidate' in final_status:
            best_candidate = final_status['best_candidate']
            metrics['best_candidate_name'] = best_candidate.get('candidate_name', 'Unknown')
            metrics['objective_status'] = best_candidate.get('objective_status', 'Unknown')
            
            if 'final_metric' in best_candidate:
                final_metric = best_candidate['final_metric']
                metrics['best_metric_name'] = final_metric.get('metric_name', 'Unknown')
                metrics['best_metric_value'] = final_metric.get('value', 0)
        
        return metrics
    
    def _extract_training_results(self, final_status: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metrics from training job results.
        
        Args:
            final_status: Final status from training job monitoring
            
        Returns:
            Dictionary of training metrics
        """
        metrics = {
            'job_status': final_status.get('training_job_status', 'Unknown'),
            'instance_type': final_status.get('instance_type', 'Unknown'),
            'instance_count': final_status.get('instance_count', 1),
            'training_duration_seconds': final_status.get('training_duration_seconds', 0)
        }
        
        # Extract final metrics if available
        if 'final_metrics' in final_status:
            for metric in final_status['final_metrics']:
                metric_name = metric.get('metric_name', '').replace(':', '_')
                metrics[f"final_{metric_name}"] = metric.get('value', 0)
        
        return metrics
    
    def get_training_recommendations(self, 
                                   dataset_info: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Get training recommendations based on dataset characteristics.
        
        Args:
            dataset_info: Information about the dataset
            
        Returns:
            List of training recommendations
        """
        recommendations = []
        
        # Dataset size recommendations
        row_count = dataset_info.get('row_count', 0)
        
        if row_count < 1000:
            recommendations.append({
                'type': 'algorithm',
                'message': 'Small dataset detected. Consider simpler algorithms like linear models.',
                'priority': 'medium'
            })
        elif row_count > 100000:
            recommendations.append({
                'type': 'infrastructure',
                'message': 'Large dataset detected. Consider using larger instances or AutoML.',
                'priority': 'high'
            })
        
        # Feature count recommendations
        feature_count = dataset_info.get('feature_count', 0)
        
        if feature_count > 100:
            recommendations.append({
                'type': 'preprocessing',
                'message': 'High-dimensional dataset. Feature selection recommended.',
                'priority': 'medium'
            })
        
        # Missing data recommendations
        if dataset_info.get('missing_ratio', 0) > 0.1:
            recommendations.append({
                'type': 'data_quality',
                'message': 'Significant missing data detected. Ensure proper imputation.',
                'priority': 'high'
            })
        
        return recommendations