"""
AWS SageMaker client for ADPA ML training and deployment.
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError

from ...agent.core.interfaces import ExecutionResult, StepStatus


class SageMakerClient:
    """
    AWS SageMaker client for managing ML training jobs and model deployment.
    """
    
    def __init__(self, 
                 region: str = "us-east-1",
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None):
        """
        Initialize SageMaker client.
        
        Args:
            region: AWS region
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.region = region
        
        # Initialize boto3 client
        session_kwargs = {'region_name': region}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs.update({
                'aws_access_key_id': aws_access_key_id,
                'aws_secret_access_key': aws_secret_access_key
            })
        
        self.sagemaker_client = boto3.client('sagemaker', **session_kwargs)
        self.s3_client = boto3.client('s3', **session_kwargs)
        
        self.logger.info("AWS SageMaker client initialized")
    
    def create_training_job(self, 
                          job_name: str,
                          algorithm_specification: Dict[str, Any],
                          input_data_config: List[Dict[str, Any]],
                          output_data_config: Dict[str, str],
                          role_arn: str,
                          instance_config: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Create a SageMaker training job.
        
        Args:
            job_name: Name of the training job
            algorithm_specification: Algorithm configuration
            input_data_config: Input data configuration
            output_data_config: Output data configuration
            role_arn: IAM role ARN for SageMaker execution
            instance_config: Instance configuration
            
        Returns:
            ExecutionResult with training job details
        """
        try:
            self.logger.info(f"Creating SageMaker training job: {job_name}")
            
            # Default instance configuration
            if not instance_config:
                instance_config = {
                    'InstanceType': 'ml.m5.large',
                    'InstanceCount': 1,
                    'VolumeSizeInGB': 20
                }
            
            # Create training job
            response = self.sagemaker_client.create_training_job(
                TrainingJobName=job_name,
                AlgorithmSpecification=algorithm_specification,
                RoleArn=role_arn,
                InputDataConfig=input_data_config,
                OutputDataConfig=output_data_config,
                ResourceConfig=instance_config,
                StoppingCondition={
                    'MaxRuntimeInSeconds': 3600  # 1 hour max
                },
                Tags=[
                    {'Key': 'Project', 'Value': 'ADPA'},
                    {'Key': 'Environment', 'Value': 'Development'}
                ]
            )
            
            training_job_arn = response['TrainingJobArn']
            
            self.logger.info(f"Successfully created training job: {training_job_arn}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                metrics={
                    'training_job_name': job_name,
                    'training_job_arn': training_job_arn,
                    'instance_type': instance_config['InstanceType'],
                    'instance_count': instance_config['InstanceCount']
                },
                artifacts={
                    'algorithm_specification': algorithm_specification,
                    'console_url': f"https://{self.region}.console.aws.amazon.com/sagemaker/home?region={self.region}#/jobs/{job_name}"
                }
            )
            
        except ClientError as e:
            error_msg = f"Failed to create training job: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
        except Exception as e:
            error_msg = f"Unexpected error creating training job: {str(e)}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
    
    def create_automl_job(self, 
                         job_name: str,
                         input_data_config: List[Dict[str, Any]],
                         output_data_config: Dict[str, str],
                         role_arn: str,
                         problem_type: str,
                         target_attribute: str) -> ExecutionResult:
        """
        Create a SageMaker AutoML job for automated ML.
        
        Args:
            job_name: Name of the AutoML job
            input_data_config: Input data configuration
            output_data_config: Output data configuration
            role_arn: IAM role ARN
            problem_type: Type of ML problem (BinaryClassification, MulticlassClassification, Regression)
            target_attribute: Target column name
            
        Returns:
            ExecutionResult with AutoML job details
        """
        try:
            self.logger.info(f"Creating SageMaker AutoML job: {job_name}")
            
            # Create AutoML job
            response = self.sagemaker_client.create_auto_ml_job(
                AutoMLJobName=job_name,
                InputDataConfig=input_data_config,
                OutputDataConfig=output_data_config,
                ProblemType=problem_type,
                AutoMLJobObjective={
                    'MetricName': self._get_default_metric(problem_type)
                },
                AutoMLJobConfig={
                    'CompletionCriteria': {
                        'MaxCandidates': 10,
                        'MaxRuntimePerTrainingJobInSeconds': 3600,
                        'MaxAutoMLJobRuntimeInSeconds': 7200
                    }
                },
                RoleArn=role_arn,
                GenerateCandidateDefinitionsOnly=False,
                Tags=[
                    {'Key': 'Project', 'Value': 'ADPA'},
                    {'Key': 'Type', 'Value': 'AutoML'},
                    {'Key': 'ProblemType', 'Value': problem_type}
                ]
            )
            
            automl_job_arn = response['AutoMLJobArn']
            
            self.logger.info(f"Successfully created AutoML job: {automl_job_arn}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                metrics={
                    'automl_job_name': job_name,
                    'automl_job_arn': automl_job_arn,
                    'problem_type': problem_type,
                    'target_attribute': target_attribute,
                    'max_candidates': 10
                },
                artifacts={
                    'console_url': f"https://{self.region}.console.aws.amazon.com/sagemaker/home?region={self.region}#/automl-jobs/{job_name}"
                }
            )
            
        except ClientError as e:
            error_msg = f"Failed to create AutoML job: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
        except Exception as e:
            error_msg = f"Unexpected error creating AutoML job: {str(e)}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
    
    def monitor_training_job(self, job_name: str) -> Dict[str, Any]:
        """
        Monitor a SageMaker training job.
        
        Args:
            job_name: Name of the training job
            
        Returns:
            Dictionary with training job status and details
        """
        try:
            response = self.sagemaker_client.describe_training_job(TrainingJobName=job_name)
            
            status_info = {
                'job_name': job_name,
                'training_job_status': response['TrainingJobStatus'],
                'secondary_status': response.get('SecondaryStatus', ''),
                'creation_time': response['CreationTime'].isoformat(),
                'algorithm_specification': response['AlgorithmSpecification'],
                'instance_type': response['ResourceConfig']['InstanceType'],
                'instance_count': response['ResourceConfig']['InstanceCount']
            }
            
            if 'TrainingStartTime' in response:
                status_info['training_start_time'] = response['TrainingStartTime'].isoformat()
            
            if 'TrainingEndTime' in response:
                status_info['training_end_time'] = response['TrainingEndTime'].isoformat()
                if 'TrainingStartTime' in response:
                    duration = (response['TrainingEndTime'] - response['TrainingStartTime']).total_seconds()
                    status_info['training_duration_seconds'] = duration
            
            if 'FailureReason' in response:
                status_info['failure_reason'] = response['FailureReason']
            
            if 'FinalMetricDataList' in response:
                status_info['final_metrics'] = [
                    {
                        'metric_name': metric['MetricName'],
                        'value': metric['Value'],
                        'timestamp': metric['Timestamp'].isoformat()
                    }
                    for metric in response['FinalMetricDataList']
                ]
            
            return status_info
            
        except ClientError as e:
            self.logger.error(f"Failed to describe training job: {e.response['Error']['Message']}")
            return {'error': e.response['Error']['Message']}
        except Exception as e:
            self.logger.error(f"Unexpected error monitoring training job: {str(e)}")
            return {'error': str(e)}
    
    def monitor_automl_job(self, job_name: str) -> Dict[str, Any]:
        """
        Monitor a SageMaker AutoML job.
        
        Args:
            job_name: Name of the AutoML job
            
        Returns:
            Dictionary with AutoML job status and details
        """
        try:
            response = self.sagemaker_client.describe_auto_ml_job(AutoMLJobName=job_name)
            
            status_info = {
                'job_name': job_name,
                'automl_job_status': response['AutoMLJobStatus'],
                'automl_job_secondary_status': response.get('AutoMLJobSecondaryStatus', ''),
                'creation_time': response['CreationTime'].isoformat(),
                'problem_type': response.get('ProblemType', ''),
                'objective_metric': response.get('AutoMLJobObjective', {}).get('MetricName', '')
            }
            
            if 'EndTime' in response:
                status_info['end_time'] = response['EndTime'].isoformat()
                duration = (response['EndTime'] - response['CreationTime']).total_seconds()
                status_info['duration_seconds'] = duration
            
            if 'FailureReason' in response:
                status_info['failure_reason'] = response['FailureReason']
            
            if 'BestCandidate' in response:
                best_candidate = response['BestCandidate']
                status_info['best_candidate'] = {
                    'candidate_name': best_candidate['CandidateName'],
                    'objective_status': best_candidate['ObjectiveStatus'],
                    'inference_containers': len(best_candidate.get('InferenceContainers', []))
                }
                
                if 'FinalAutoMLJobObjectiveMetric' in best_candidate:
                    metric = best_candidate['FinalAutoMLJobObjectiveMetric']
                    status_info['best_candidate']['final_metric'] = {
                        'metric_name': metric['MetricName'],
                        'value': metric['Value']
                    }
            
            return status_info
            
        except ClientError as e:
            self.logger.error(f"Failed to describe AutoML job: {e.response['Error']['Message']}")
            return {'error': e.response['Error']['Message']}
        except Exception as e:
            self.logger.error(f"Unexpected error monitoring AutoML job: {str(e)}")
            return {'error': str(e)}
    
    def wait_for_completion(self, 
                          job_name: str, 
                          job_type: str = "training",
                          max_wait_time: int = 7200) -> Dict[str, Any]:
        """
        Wait for a SageMaker job to complete.
        
        Args:
            job_name: Name of the job
            job_type: Type of job ("training" or "automl")
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            Final job status
        """
        start_time = time.time()
        check_interval = 60  # Check every minute
        
        monitor_func = self.monitor_training_job if job_type == "training" else self.monitor_automl_job
        status_key = 'training_job_status' if job_type == "training" else 'automl_job_status'
        
        while (time.time() - start_time) < max_wait_time:
            status = monitor_func(job_name)
            
            if 'error' in status:
                return status
            
            job_status = status.get(status_key)
            self.logger.info(f"Job {job_name} status: {job_status}")
            
            if job_status in ['Completed', 'Failed', 'Stopped']:
                return status
            
            time.sleep(check_interval)
        
        return {
            'error': f'Job monitoring timeout after {max_wait_time} seconds',
            'job_status': 'TIMEOUT'
        }
    
    def create_model(self, 
                    model_name: str,
                    model_data_url: str,
                    image_uri: str,
                    role_arn: str) -> ExecutionResult:
        """
        Create a SageMaker model.
        
        Args:
            model_name: Name of the model
            model_data_url: S3 URL of model artifacts
            image_uri: Docker image URI for inference
            role_arn: IAM role ARN
            
        Returns:
            ExecutionResult with model creation details
        """
        try:
            self.logger.info(f"Creating SageMaker model: {model_name}")
            
            response = self.sagemaker_client.create_model(
                ModelName=model_name,
                PrimaryContainer={
                    'Image': image_uri,
                    'ModelDataUrl': model_data_url
                },
                ExecutionRoleArn=role_arn,
                Tags=[
                    {'Key': 'Project', 'Value': 'ADPA'}
                ]
            )
            
            model_arn = response['ModelArn']
            
            self.logger.info(f"Successfully created model: {model_arn}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                metrics={
                    'model_name': model_name,
                    'model_arn': model_arn
                },
                artifacts={
                    'model_data_url': model_data_url,
                    'image_uri': image_uri
                }
            )
            
        except ClientError as e:
            error_msg = f"Failed to create model: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
    
    def get_built_in_algorithm_image_uri(self, algorithm_name: str) -> str:
        """
        Get the image URI for a SageMaker built-in algorithm.
        
        Args:
            algorithm_name: Name of the algorithm (e.g., 'xgboost', 'linear-learner')
            
        Returns:
            Docker image URI for the algorithm
        """
        # Mapping of algorithms to image URIs (simplified)
        # In practice, you'd use sagemaker.image_uris.retrieve()
        algorithm_images = {
            'xgboost': f"246618743249.dkr.ecr.{self.region}.amazonaws.com/xgboost:latest",
            'linear-learner': f"382416733822.dkr.ecr.{self.region}.amazonaws.com/linear-learner:latest",
            'blazingtext': f"382416733822.dkr.ecr.{self.region}.amazonaws.com/blazingtext:latest"
        }
        
        return algorithm_images.get(algorithm_name, algorithm_images['xgboost'])
    
    def _get_default_metric(self, problem_type: str) -> str:
        """Get default metric for AutoML problem type."""
        metrics = {
            'BinaryClassification': 'F1',
            'MulticlassClassification': 'Accuracy',
            'Regression': 'MSE'
        }
        return metrics.get(problem_type, 'Accuracy')
    
    def list_training_jobs(self, name_contains: str = "adpa") -> List[Dict[str, Any]]:
        """List ADPA training jobs."""
        try:
            response = self.sagemaker_client.list_training_jobs(
                NameContains=name_contains,
                MaxResults=50
            )
            
            jobs = []
            for job in response.get('TrainingJobSummaries', []):
                jobs.append({
                    'job_name': job['TrainingJobName'],
                    'status': job['TrainingJobStatus'],
                    'creation_time': job['CreationTime'].isoformat(),
                    'training_end_time': job.get('TrainingEndTime', '').isoformat() if job.get('TrainingEndTime') else None
                })
            
            return jobs
            
        except ClientError as e:
            self.logger.error(f"Failed to list training jobs: {e.response['Error']['Message']}")
            return []
    
    def list_automl_jobs(self, name_contains: str = "adpa") -> List[Dict[str, Any]]:
        """List ADPA AutoML jobs."""
        try:
            response = self.sagemaker_client.list_auto_ml_jobs(
                NameContains=name_contains,
                MaxResults=50
            )
            
            jobs = []
            for job in response.get('AutoMLJobSummaries', []):
                jobs.append({
                    'job_name': job['AutoMLJobName'],
                    'status': job['AutoMLJobStatus'],
                    'creation_time': job['CreationTime'].isoformat(),
                    'end_time': job.get('EndTime', '').isoformat() if job.get('EndTime') else None
                })
            
            return jobs
            
        except ClientError as e:
            self.logger.error(f"Failed to list AutoML jobs: {e.response['Error']['Message']}")
            return []