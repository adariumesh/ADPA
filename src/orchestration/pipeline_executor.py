"""
Real Pipeline Executor for ADPA
Executes ML pipelines on AWS infrastructure with Step Functions and SageMaker
"""

import boto3
import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd


class RealPipelineExecutor:
    """
    Real Pipeline Executor that integrates with AWS Step Functions and SageMaker.
    
    Capabilities:
    - Upload data to S3
    - Start Step Functions execution
    - Monitor pipeline progress
    - Retrieve SageMaker training results
    - Handle pipeline failures with intelligent fallback
    """
    
    def __init__(self,
                 region: str = 'us-east-2',
                 account_id: str = '083308938449'):
        """
        Initialize the Real Pipeline Executor.
        
        Args:
            region: AWS region
            account_id: AWS account ID
        """
        self.logger = logging.getLogger(__name__)
        self.region = region
        self.account_id = account_id
        
        # Initialize AWS clients
        self.s3 = boto3.client('s3', region_name=region)
        self.stepfunctions = boto3.client('stepfunctions', region_name=region)
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        
        # Resource names
        self.data_bucket = f'adpa-data-{account_id}-production'
        self.model_bucket = f'adpa-models-{account_id}-production'
        self.state_machine_arn = f'arn:aws:states:{region}:{account_id}:stateMachine:adpa-ml-pipeline-workflow'
        
        self.logger.info(f"RealPipelineExecutor initialized for region {region}")
    
    def execute_pipeline(self,
                        data: pd.DataFrame,
                        objective: str,
                        pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute complete ML pipeline on AWS infrastructure.
        
        Args:
            data: Input dataset
            objective: ML objective (e.g., "predict churn")
            pipeline_config: Pipeline configuration
            
        Returns:
            Dictionary with execution results
        """
        execution_id = f"pipeline_{int(time.time())}"
        
        self.logger.info(f"Starting pipeline execution {execution_id}")
        
        try:
            # Step 1: Upload data to S3
            s3_path = self._upload_to_s3(data, execution_id)
            self.logger.info(f"✅ Data uploaded to {s3_path}")
            
            # Step 2: Prepare Step Functions input
            sf_input = self._prepare_stepfunctions_input(
                s3_path, objective, pipeline_config, execution_id
            )
            
            # Step 3: Start Step Functions execution
            execution_arn = self._start_stepfunctions_execution(sf_input, execution_id)
            self.logger.info(f"✅ Step Functions execution started: {execution_arn}")
            
            # Step 4: Monitor execution
            execution_result = self._monitor_execution(execution_arn)
            
            # Step 5: Retrieve results
            if execution_result['status'] == 'SUCCEEDED':
                results = self._retrieve_execution_results(execution_arn, execution_result)
                
                # Send CloudWatch metrics
                self._send_cloudwatch_metrics(execution_id, results, success=True)
                
                return {
                    'execution_id': execution_id,
                    'status': 'success',
                    'execution_arn': execution_arn,
                    's3_path': s3_path,
                    'results': results,
                    'duration': execution_result.get('duration', 0)
                }
            else:
                # Send failure metrics
                self._send_cloudwatch_metrics(execution_id, {}, success=False)
                
                return {
                    'execution_id': execution_id,
                    'status': 'failed',
                    'execution_arn': execution_arn,
                    'error': execution_result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            self._send_cloudwatch_metrics(execution_id, {}, success=False)
            
            return {
                'execution_id': execution_id,
                'status': 'error',
                'error': str(e)
            }
    
    def _upload_to_s3(self, data: pd.DataFrame, execution_id: str) -> str:
        """Upload dataset to S3"""
        
        # Create temporary CSV
        temp_file = f"/tmp/{execution_id}_data.csv"
        data.to_csv(temp_file, index=False)
        
        # Upload to S3
        s3_key = f"datasets/{execution_id}/input_data.csv"
        
        self.s3.upload_file(
            temp_file,
            self.data_bucket,
            s3_key
        )
        
        # Clean up temp file
        import os
        os.remove(temp_file)
        
        return f"s3://{self.data_bucket}/{s3_key}"
    
    def _prepare_stepfunctions_input(self,
                                     s3_path: str,
                                     objective: str,
                                     pipeline_config: Dict[str, Any],
                                     execution_id: str) -> Dict[str, Any]:
        """Prepare input for Step Functions execution"""
        
        return {
            'data_path': s3_path,
            'objective': objective,
            'execution_id': execution_id,
            'training_job_name': f"adpa-training-{execution_id}",
            'pipeline_config': pipeline_config,
            'timestamp': datetime.now().isoformat()
        }
    
    def _start_stepfunctions_execution(self,
                                      sf_input: Dict[str, Any],
                                      execution_id: str) -> str:
        """Start Step Functions state machine execution"""
        
        response = self.stepfunctions.start_execution(
            stateMachineArn=self.state_machine_arn,
            name=execution_id,
            input=json.dumps(sf_input)
        )
        
        return response['executionArn']
    
    def _monitor_execution(self,
                          execution_arn: str,
                          timeout_seconds: int = 3600,
                          poll_interval: int = 10) -> Dict[str, Any]:
        """Monitor Step Functions execution until completion"""
        
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            response = self.stepfunctions.describe_execution(
                executionArn=execution_arn
            )
            
            status = response['status']
            
            if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                duration = time.time() - start_time
                
                result = {
                    'status': status,
                    'duration': duration,
                    'start_date': response['startDate'].isoformat(),
                    'stop_date': response.get('stopDate', datetime.now()).isoformat()
                }
                
                if status == 'FAILED':
                    result['error'] = response.get('error', 'Unknown error')
                    result['cause'] = response.get('cause', 'Unknown cause')
                
                return result
            
            self.logger.info(f"Execution status: {status} (elapsed: {int(time.time() - start_time)}s)")
            time.sleep(poll_interval)
        
        return {
            'status': 'TIMEOUT',
            'duration': timeout_seconds,
            'error': 'Execution monitoring timed out'
        }
    
    def _retrieve_execution_results(self,
                                    execution_arn: str,
                                    execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve and parse execution results"""
        
        response = self.stepfunctions.describe_execution(
            executionArn=execution_arn
        )
        
        output = json.loads(response.get('output', '{}'))
        
        return {
            'evaluation_metrics': output.get('evaluation_result', {}),
            'model_artifacts': output.get('training_result', {}),
            'execution_details': execution_result
        }
    
    def train_sagemaker_model(self,
                             training_data_s3: str,
                             algorithm: str = 'sklearn',
                             instance_type: str = 'ml.m5.large') -> Dict[str, Any]:
        """
        Train a model using SageMaker.
        
        Args:
            training_data_s3: S3 path to training data
            algorithm: Algorithm to use
            instance_type: SageMaker instance type
            
        Returns:
            Dictionary with training job details
        """
        job_name = f"adpa-training-{int(time.time())}"
        
        self.logger.info(f"Starting SageMaker training job: {job_name}")
        
        try:
            # Get algorithm image
            image_uri = self._get_algorithm_image(algorithm)
            
            # Create training job
            response = self.sagemaker.create_training_job(
                TrainingJobName=job_name,
                RoleArn=f'arn:aws:iam::{self.account_id}:role/adpa-sagemaker-execution-role',
                AlgorithmSpecification={
                    'TrainingImage': image_uri,
                    'TrainingInputMode': 'File'
                },
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
                        'ContentType': 'text/csv'
                    }
                ],
                OutputDataConfig={
                    'S3OutputPath': f's3://{self.model_bucket}/sagemaker-output/'
                },
                ResourceConfig={
                    'InstanceType': instance_type,
                    'InstanceCount': 1,
                    'VolumeSizeInGB': 10
                },
                StoppingCondition={
                    'MaxRuntimeInSeconds': 3600
                }
            )
            
            # Wait for completion
            training_result = self._wait_for_training_job(job_name)
            
            return {
                'job_name': job_name,
                'status': training_result['status'],
                'model_artifacts': training_result.get('model_artifacts'),
                'training_metrics': training_result.get('metrics')
            }
            
        except Exception as e:
            self.logger.error(f"SageMaker training failed: {e}")
            return {
                'job_name': job_name,
                'status': 'failed',
                'error': str(e)
            }
    
    def _get_algorithm_image(self, algorithm: str) -> str:
        """Get SageMaker algorithm image URI"""
        
        # Map algorithm names to image URIs
        images = {
            'sklearn': f'683313688378.dkr.ecr.{self.region}.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3',
            'xgboost': f'683313688378.dkr.ecr.{self.region}.amazonaws.com/sagemaker-xgboost:1.7-1',
        }
        
        return images.get(algorithm, images['sklearn'])
    
    def _wait_for_training_job(self,
                               job_name: str,
                               timeout_seconds: int = 3600,
                               poll_interval: int = 30) -> Dict[str, Any]:
        """Wait for SageMaker training job to complete"""
        
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            response = self.sagemaker.describe_training_job(
                TrainingJobName=job_name
            )
            
            status = response['TrainingJobStatus']
            
            if status in ['Completed', 'Failed', 'Stopped']:
                result = {
                    'status': status,
                    'duration': time.time() - start_time
                }
                
                if status == 'Completed':
                    result['model_artifacts'] = response.get('ModelArtifacts', {})
                    result['metrics'] = response.get('FinalMetricDataList', [])
                
                return result
            
            self.logger.info(f"Training job status: {status}")
            time.sleep(poll_interval)
        
        return {
            'status': 'timeout',
            'error': 'Training job monitoring timed out'
        }
    
    def _send_cloudwatch_metrics(self,
                                 execution_id: str,
                                 results: Dict[str, Any],
                                 success: bool):
        """Send metrics to CloudWatch"""
        
        try:
            metrics = [
                {
                    'MetricName': 'PipelineExecutions',
                    'Value': 1.0,
                    'Unit': 'Count',
                    'Timestamp': datetime.now()
                },
                {
                    'MetricName': 'ExecutionsSucceeded' if success else 'ExecutionsFailed',
                    'Value': 1.0,
                    'Unit': 'Count',
                    'Timestamp': datetime.now()
                }
            ]
            
            if results.get('duration'):
                metrics.append({
                    'MetricName': 'ExecutionTime',
                    'Value': results['duration'],
                    'Unit': 'Seconds',
                    'Timestamp': datetime.now()
                })
            
            self.cloudwatch.put_metric_data(
                Namespace='ADPA',
                MetricData=metrics
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to send CloudWatch metrics: {e}")
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get status of a pipeline execution"""
        
        execution_arn = f"arn:aws:states:{self.region}:{self.account_id}:execution:adpa-ml-pipeline-workflow:{execution_id}"
        
        try:
            response = self.stepfunctions.describe_execution(
                executionArn=execution_arn
            )
            
            return {
                'execution_id': execution_id,
                'status': response['status'],
                'start_date': response['startDate'].isoformat(),
                'stop_date': response.get('stopDate', datetime.now()).isoformat()
            }
            
        except Exception as e:
            return {
                'execution_id': execution_id,
                'error': str(e)
            }
