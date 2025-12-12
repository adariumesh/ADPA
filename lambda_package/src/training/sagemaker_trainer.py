"""
AWS SageMaker Training Integration for ADPA

This module provides functionality to train ML models using SageMaker
instead of Lambda, enabling:
- Training on larger datasets (>1GB)
- GPU-accelerated training
- Hyperparameter tuning
- Model registry integration
"""

import json
import os
import boto3
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

# Import centralized AWS configuration
try:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from config.aws_config import (
        AWS_ACCOUNT_ID, AWS_REGION, MODEL_BUCKET, 
        SAGEMAKER_EXECUTION_ROLE, get_credentials_from_csv
    )
except ImportError:
    # Fallback values
    AWS_ACCOUNT_ID = "083308938449"
    AWS_REGION = "us-east-2"
    MODEL_BUCKET = f"adpa-models-{AWS_ACCOUNT_ID}-development"
    SAGEMAKER_EXECUTION_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/adpa-sagemaker-execution-role"
    get_credentials_from_csv = None


class SageMakerTrainer:
    """Train ML models using AWS SageMaker"""
    
    def __init__(self, region: str = None):
        """
        Initialize SageMaker trainer
        
        Args:
            region: AWS region name (defaults to centralized config)
        """
        self.region = region or AWS_REGION
        
        # Try to load credentials from rootkey.csv
        try:
            if get_credentials_from_csv:
                creds = get_credentials_from_csv()
                if creds['access_key_id'] and creds['secret_access_key']:
                    self.sagemaker = boto3.client(
                        'sagemaker', 
                        region_name=self.region,
                        aws_access_key_id=creds['access_key_id'],
                        aws_secret_access_key=creds['secret_access_key']
                    )
                    self.s3 = boto3.client(
                        's3', 
                        region_name=self.region,
                        aws_access_key_id=creds['access_key_id'],
                        aws_secret_access_key=creds['secret_access_key']
                    )
                else:
                    raise ValueError("No credentials in CSV")
            else:
                raise ValueError("Config module not available")
        except Exception:
            # Fallback to default credential chain
            self.sagemaker = boto3.client('sagemaker', region_name=self.region)
            self.s3 = boto3.client('s3', region_name=self.region)
        
        # Configuration from centralized config
        self.role_arn = SAGEMAKER_EXECUTION_ROLE
        self.output_bucket = MODEL_BUCKET
        self.training_image = self._get_training_image()
        
    def _get_training_image(self) -> str:
        """Get the appropriate SageMaker training container image"""
        # Use AWS pre-built scikit-learn container
        # Format: {account}.dkr.ecr.{region}.amazonaws.com/sagemaker-scikit-learn:{version}
        account_map = {
            'us-east-1': '683313688378',
            'us-east-2': '257758044811',
            'us-west-2': '246618743249'
        }
        account = account_map.get(self.region, '683313688378')
        return f"{account}.dkr.ecr.{self.region}.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3"
    
    def create_training_job(
        self,
        job_name: str,
        training_data_s3: str,
        algorithm: str = 'random_forest',
        hyperparameters: Optional[Dict[str, str]] = None,
        instance_type: str = 'ml.m5.xlarge',
        max_runtime_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Create and start a SageMaker training job
        
        Args:
            job_name: Unique name for the training job
            training_data_s3: S3 URI to training data
            algorithm: ML algorithm to use
            hyperparameters: Model hyperparameters
            instance_type: SageMaker instance type (ml.m5.xlarge, ml.p3.2xlarge for GPU, etc.)
            max_runtime_seconds: Maximum training time
            
        Returns:
            Dict containing job status and ARN
        """
        # Default hyperparameters
        if hyperparameters is None:
            hyperparameters = {
                'n_estimators': '100',
                'max_depth': '10',
                'min_samples_split': '2',
                'algorithm': algorithm
            }
        
        try:
            response = self.sagemaker.create_training_job(
                TrainingJobName=job_name,
                HyperParameters=hyperparameters,
                AlgorithmSpecification={
                    'TrainingImage': self.training_image,
                    'TrainingInputMode': 'File',
                    'EnableSageMakerMetricsTimeSeries': True
                },
                RoleArn=self.role_arn,
                InputDataConfig=[
                    {
                        'ChannelName': 'training',
                        'DataSource': {
                            'S3DataSource': {
                                'S3DataType': 'S3Prefix',
                                'S3Uri': training_data_s3,
                                'S3DataDistributionType': 'FullyReplicated'
                            }
                        },
                        'ContentType': 'text/csv',
                        'CompressionType': 'None'
                    }
                ],
                OutputDataConfig={
                    'S3OutputPath': f's3://{self.output_bucket}/sagemaker-output/',
                    'KmsKeyId': ''  # Add KMS encryption if needed
                },
                ResourceConfig={
                    'InstanceType': instance_type,
                    'InstanceCount': 1,
                    'VolumeSizeInGB': 30
                },
                StoppingCondition={
                    'MaxRuntimeInSeconds': max_runtime_seconds
                },
                EnableNetworkIsolation=False,
                EnableInterContainerTrafficEncryption=False,
                EnableManagedSpotTraining=True,  # Cost optimization
                Tags=[
                    {'Key': 'Project', 'Value': 'ADPA'},
                    {'Key': 'Environment', 'Value': 'development'},
                    {'Key': 'ManagedBy', 'Value': 'ADPA-Agent'}
                ]
            )
            
            return {
                "status": "InProgress",
                "training_job_name": job_name,
                "training_job_arn": response['TrainingJobArn'],
                "created_time": datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            return {
                "status": "Failed",
                "error": str(e),
                "error_code": e.response['Error']['Code']
            }
    
    def get_training_status(self, job_name: str) -> Dict[str, Any]:
        """
        Get the status of a SageMaker training job
        
        Args:
            job_name: Training job name
            
        Returns:
            Dict containing job status, metrics, and model artifacts
        """
        try:
            response = self.sagemaker.describe_training_job(
                TrainingJobName=job_name
            )
            
            # Extract key information
            status_info = {
                "training_job_name": job_name,
                "status": response['TrainingJobStatus'],  # InProgress, Completed, Failed, Stopping, Stopped
                "created_time": response['CreationTime'].isoformat(),
                "start_time": response.get('TrainingStartTime', datetime.utcnow()).isoformat() if response.get('TrainingStartTime') else None,
                "end_time": response.get('TrainingEndTime', datetime.utcnow()).isoformat() if response.get('TrainingEndTime') else None,
                "billable_time_seconds": response.get('BillingTime', 0),
                "instance_type": response['ResourceConfig']['InstanceType'],
                "hyperparameters": response.get('HyperParameters', {}),
            }
            
            # Add model artifact location if training completed
            if response['TrainingJobStatus'] == 'Completed':
                status_info['model_artifacts'] = response['ModelArtifacts']['S3ModelArtifacts']
                status_info['final_metrics'] = response.get('FinalMetricDataList', [])
            
            # Add failure reason if failed
            if response['TrainingJobStatus'] == 'Failed':
                status_info['failure_reason'] = response.get('FailureReason', 'Unknown')
            
            return status_info
            
        except ClientError as e:
            return {
                "status": "Error",
                "error": str(e),
                "training_job_name": job_name
            }
    
    def create_hyperparameter_tuning_job(
        self,
        tuning_job_name: str,
        training_data_s3: str,
        algorithm: str = 'random_forest',
        max_jobs: int = 10,
        max_parallel_jobs: int = 2
    ) -> Dict[str, Any]:
        """
        Create a hyperparameter tuning job for automated optimization
        
        Args:
            tuning_job_name: Unique name for tuning job
            training_data_s3: S3 URI to training data
            algorithm: ML algorithm to use
            max_jobs: Maximum number of training jobs
            max_parallel_jobs: Number of parallel jobs
            
        Returns:
            Dict containing tuning job status
        """
        try:
            response = self.sagemaker.create_hyper_parameter_tuning_job(
                HyperParameterTuningJobName=tuning_job_name,
                HyperParameterTuningJobConfig={
                    'Strategy': 'Bayesian',  # or 'Random'
                    'HyperParameterTuningJobObjective': {
                        'Type': 'Maximize',
                        'MetricName': 'validation:accuracy'
                    },
                    'ResourceLimits': {
                        'MaxNumberOfTrainingJobs': max_jobs,
                        'MaxParallelTrainingJobs': max_parallel_jobs
                    },
                    'ParameterRanges': {
                        'IntegerParameterRanges': [
                            {
                                'Name': 'n_estimators',
                                'MinValue': '50',
                                'MaxValue': '200',
                                'ScalingType': 'Linear'
                            },
                            {
                                'Name': 'max_depth',
                                'MinValue': '5',
                                'MaxValue': '30',
                                'ScalingType': 'Linear'
                            }
                        ],
                        'ContinuousParameterRanges': [
                            {
                                'Name': 'learning_rate',
                                'MinValue': '0.01',
                                'MaxValue': '0.3',
                                'ScalingType': 'Logarithmic'
                            }
                        ],
                        'CategoricalParameterRanges': []
                    }
                },
                TrainingJobDefinition={
                    'StaticHyperParameters': {
                        'algorithm': algorithm
                    },
                    'AlgorithmSpecification': {
                        'TrainingImage': self.training_image,
                        'TrainingInputMode': 'File',
                        'MetricDefinitions': [
                            {
                                'Name': 'validation:accuracy',
                                'Regex': 'validation-accuracy: ([0-9\\.]+)'
                            }
                        ]
                    },
                    'RoleArn': self.role_arn,
                    'InputDataConfig': [
                        {
                            'ChannelName': 'training',
                            'DataSource': {
                                'S3DataSource': {
                                    'S3DataType': 'S3Prefix',
                                    'S3Uri': training_data_s3,
                                    'S3DataDistributionType': 'FullyReplicated'
                                }
                            },
                            'ContentType': 'text/csv'
                        }
                    ],
                    'OutputDataConfig': {
                        'S3OutputPath': f's3://{self.output_bucket}/tuning-output/'
                    },
                    'ResourceConfig': {
                        'InstanceType': 'ml.m5.xlarge',
                        'InstanceCount': 1,
                        'VolumeSizeInGB': 30
                    },
                    'StoppingCondition': {
                        'MaxRuntimeInSeconds': 3600
                    }
                },
                Tags=[
                    {'Key': 'Project', 'Value': 'ADPA'},
                    {'Key': 'Type', 'Value': 'HyperparameterTuning'}
                ]
            )
            
            return {
                "status": "InProgress",
                "tuning_job_name": tuning_job_name,
                "tuning_job_arn": response['HyperParameterTuningJobArn']
            }
            
        except ClientError as e:
            return {
                "status": "Failed",
                "error": str(e)
            }
    
    def register_model(
        self,
        model_name: str,
        model_artifact_s3: str,
        inference_image: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register trained model in SageMaker Model Registry
        
        Args:
            model_name: Name for the model
            model_artifact_s3: S3 URI to model artifacts
            inference_image: Container image for inference (optional)
            
        Returns:
            Dict containing model registration status
        """
        if inference_image is None:
            inference_image = self.training_image
        
        try:
            response = self.sagemaker.create_model(
                ModelName=model_name,
                PrimaryContainer={
                    'Image': inference_image,
                    'ModelDataUrl': model_artifact_s3,
                    'Environment': {
                        'SAGEMAKER_PROGRAM': 'inference.py',
                        'SAGEMAKER_SUBMIT_DIRECTORY': model_artifact_s3
                    }
                },
                ExecutionRoleArn=self.role_arn,
                Tags=[
                    {'Key': 'Project', 'Value': 'ADPA'},
                    {'Key': 'RegisteredBy', 'Value': 'ADPA-Agent'}
                ]
            )
            
            return {
                "status": "Registered",
                "model_name": model_name,
                "model_arn": response['ModelArn']
            }
            
        except ClientError as e:
            return {
                "status": "Failed",
                "error": str(e)
            }
    
    def deploy_endpoint(
        self,
        endpoint_name: str,
        model_name: str,
        instance_type: str = 'ml.t2.medium',
        initial_instance_count: int = 1
    ) -> Dict[str, Any]:
        """
        Deploy model to a SageMaker endpoint for real-time inference
        
        Args:
            endpoint_name: Name for the endpoint
            model_name: Name of registered model
            instance_type: Instance type for endpoint
            initial_instance_count: Number of instances
            
        Returns:
            Dict containing endpoint status
        """
        endpoint_config_name = f"{endpoint_name}-config"
        
        try:
            # Create endpoint configuration
            self.sagemaker.create_endpoint_config(
                EndpointConfigName=endpoint_config_name,
                ProductionVariants=[
                    {
                        'VariantName': 'AllTraffic',
                        'ModelName': model_name,
                        'InitialInstanceCount': initial_instance_count,
                        'InstanceType': instance_type,
                        'InitialVariantWeight': 1.0
                    }
                ],
                Tags=[
                    {'Key': 'Project', 'Value': 'ADPA'}
                ]
            )
            
            # Create endpoint
            response = self.sagemaker.create_endpoint(
                EndpointName=endpoint_name,
                EndpointConfigName=endpoint_config_name,
                Tags=[
                    {'Key': 'Project', 'Value': 'ADPA'},
                    {'Key': 'Environment', 'Value': 'development'}
                ]
            )
            
            return {
                "status": "Creating",
                "endpoint_name": endpoint_name,
                "endpoint_arn": response['EndpointArn']
            }
            
        except ClientError as e:
            return {
                "status": "Failed",
                "error": str(e)
            }


# Lambda handler for SageMaker integration
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to interact with SageMaker
    
    Args:
        event: Contains action and parameters
        context: Lambda context
        
    Returns:
        Dict containing operation results
    """
    action = event.get('action', 'create_training_job')
    trainer = SageMakerTrainer()
    
    if action == 'create_training_job':
        return trainer.create_training_job(
            job_name=event['job_name'],
            training_data_s3=event['training_data_s3'],
            algorithm=event.get('algorithm', 'random_forest'),
            hyperparameters=event.get('hyperparameters'),
            instance_type=event.get('instance_type', 'ml.m5.xlarge')
        )
    
    elif action == 'get_training_status':
        return trainer.get_training_status(event['job_name'])
    
    elif action == 'hyperparameter_tuning':
        return trainer.create_hyperparameter_tuning_job(
            tuning_job_name=event['tuning_job_name'],
            training_data_s3=event['training_data_s3'],
            algorithm=event.get('algorithm', 'random_forest'),
            max_jobs=event.get('max_jobs', 10)
        )
    
    elif action == 'register_model':
        return trainer.register_model(
            model_name=event['model_name'],
            model_artifact_s3=event['model_artifact_s3']
        )
    
    elif action == 'deploy_endpoint':
        return trainer.deploy_endpoint(
            endpoint_name=event['endpoint_name'],
            model_name=event['model_name'],
            instance_type=event.get('instance_type', 'ml.t2.medium')
        )
    
    else:
        return {
            "status": "error",
            "message": f"Unknown action: {action}"
        }
