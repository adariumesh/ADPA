"""
AWS Step Functions orchestrator for ADPA pipeline workflows.
"""

import json
import logging
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
import time

from ...agent.core.interfaces import ExecutionResult, StepStatus


class StepFunctionsOrchestrator:
    """
    AWS Step Functions orchestrator for managing ADPA pipeline workflows.
    """
    
    def __init__(self, 
                 region: str = "us-east-1",
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None):
        """
        Initialize Step Functions orchestrator.
        
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
        
        self.sfn_client = boto3.client('stepfunctions', **session_kwargs)
        self.logger.info("Step Functions orchestrator initialized")
    
    def create_adpa_workflow(self, 
                           workflow_name: str,
                           glue_job_prefix: str,
                           s3_bucket: str) -> ExecutionResult:
        """
        Create ADPA data processing workflow in Step Functions.
        
        Args:
            workflow_name: Name for the Step Functions state machine
            glue_job_prefix: Prefix for Glue job names
            s3_bucket: S3 bucket for data storage
            
        Returns:
            ExecutionResult with workflow creation details
        """
        try:
            self.logger.info(f"Creating ADPA workflow: {workflow_name}")
            
            # Define the state machine definition
            definition = self._create_workflow_definition(glue_job_prefix, s3_bucket)
            
            # Create IAM role for Step Functions (simplified - in production use proper roles)
            role_arn = self._get_or_create_execution_role()
            
            # Create state machine
            response = self.sfn_client.create_state_machine(
                name=workflow_name,
                definition=json.dumps(definition),
                roleArn=role_arn,
                type='STANDARD',
                tags=[
                    {'key': 'Project', 'value': 'ADPA'},
                    {'key': 'Environment', 'value': 'Development'}
                ]
            )
            
            state_machine_arn = response['stateMachineArn']
            
            self.logger.info(f"Successfully created workflow: {state_machine_arn}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                metrics={
                    'state_machine_arn': state_machine_arn,
                    'workflow_name': workflow_name,
                    'creation_date': response['creationDate'].isoformat()
                },
                artifacts={
                    'definition': definition,
                    'console_url': f"https://{self.region}.console.aws.amazon.com/states/home?region={self.region}#/statemachines/view/{state_machine_arn}"
                }
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'StateMachineAlreadyExists':
                # Get existing state machine
                try:
                    existing_arn = f"arn:aws:states:{self.region}:*:stateMachine:{workflow_name}"
                    return ExecutionResult(
                        status=StepStatus.COMPLETED,
                        metrics={'state_machine_arn': existing_arn, 'status': 'already_exists'},
                        artifacts={'message': 'State machine already exists'}
                    )
                except:
                    pass
            
            error_msg = f"Failed to create Step Functions workflow: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
        except Exception as e:
            error_msg = f"Unexpected error creating workflow: {str(e)}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
    
    def execute_workflow(self, 
                        state_machine_arn: str,
                        input_data: Dict[str, Any],
                        execution_name: Optional[str] = None) -> ExecutionResult:
        """
        Execute an ADPA workflow.
        
        Args:
            state_machine_arn: ARN of the state machine to execute
            input_data: Input data for the workflow
            execution_name: Optional name for the execution
            
        Returns:
            ExecutionResult with execution details
        """
        try:
            if not execution_name:
                execution_name = f"adpa-execution-{int(time.time())}"
            
            self.logger.info(f"Starting workflow execution: {execution_name}")
            
            # Start execution
            response = self.sfn_client.start_execution(
                stateMachineArn=state_machine_arn,
                name=execution_name,
                input=json.dumps(input_data)
            )
            
            execution_arn = response['executionArn']
            
            self.logger.info(f"Workflow execution started: {execution_arn}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                metrics={
                    'execution_arn': execution_arn,
                    'execution_name': execution_name,
                    'start_date': response['startDate'].isoformat()
                },
                artifacts={
                    'input_data': input_data,
                    'console_url': f"https://{self.region}.console.aws.amazon.com/states/home?region={self.region}#/executions/details/{execution_arn}"
                }
            )
            
        except ClientError as e:
            error_msg = f"Failed to execute workflow: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
        except Exception as e:
            error_msg = f"Unexpected error executing workflow: {str(e)}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
    
    def monitor_execution(self, execution_arn: str) -> Dict[str, Any]:
        """
        Monitor the status of a workflow execution.
        
        Args:
            execution_arn: ARN of the execution to monitor
            
        Returns:
            Dictionary with execution status and details
        """
        try:
            response = self.sfn_client.describe_execution(executionArn=execution_arn)
            
            status = response['status']
            execution_details = {
                'execution_arn': execution_arn,
                'status': status,
                'start_date': response['startDate'].isoformat(),
                'state_machine_arn': response['stateMachineArn']
            }
            
            if 'stopDate' in response:
                execution_details['stop_date'] = response['stopDate'].isoformat()
                duration = (response['stopDate'] - response['startDate']).total_seconds()
                execution_details['duration_seconds'] = duration
            
            if 'output' in response:
                execution_details['output'] = json.loads(response['output'])
            
            if 'error' in response:
                execution_details['error'] = response['error']
            
            return execution_details
            
        except ClientError as e:
            self.logger.error(f"Failed to describe execution: {e.response['Error']['Message']}")
            return {'error': e.response['Error']['Message']}
        except Exception as e:
            self.logger.error(f"Unexpected error monitoring execution: {str(e)}")
            return {'error': str(e)}
    
    def _create_workflow_definition(self, glue_job_prefix: str, s3_bucket: str) -> Dict[str, Any]:
        """Create the Step Functions workflow definition for ADPA using Glue Jobs."""
        
        definition = {
            "Comment": "ADPA Data Processing Workflow with AWS Glue",
            "StartAt": "ProfileData",
            "States": {
                "ProfileData": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::glue:startJobRun.sync",
                    "Parameters": {
                        "JobName": f"{glue_job_prefix}-data-profiling",
                        "Arguments": {
                            "--input_path.$": "States.Format('s3://{}/{}', $.s3_bucket, $.input_key)",
                            "--output_path.$": "States.Format('s3://{}/{}/profiling_results', $.s3_bucket, $.output_prefix)",
                            "--database_name": "adpa_catalog",
                            "--table_name.$": "States.Format('raw_data_{}', $.execution_id)"
                        }
                    },
                    "ResultPath": "$.profiling_result",
                    "Next": "CheckDataQuality",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 30,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "HandleError",
                            "ResultPath": "$.error_info"
                        }
                    ]
                },
                "CheckDataQuality": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.profiling_result.JobRunState",
                            "StringEquals": "SUCCEEDED",
                            "Next": "ParseProfilingResults"
                        }
                    ],
                    "Default": "ProfilingFailed"
                },
                "ParseProfilingResults": {
                    "Type": "Pass",
                    "Parameters": {
                        "profiling_status": "completed",
                        "proceed_to_cleaning": true
                    },
                    "ResultPath": "$.quality_check",
                    "Next": "CleanData"
                },
                "CleanData": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::glue:startJobRun.sync",
                    "Parameters": {
                        "JobName": f"{glue_job_prefix}-data-cleaning",
                        "Arguments": {
                            "--input_path.$": "States.Format('s3://{}/{}', $.s3_bucket, $.input_key)",
                            "--output_path.$": "States.Format('s3://{}/{}/cleaned_data', $.s3_bucket, $.output_prefix)",
                            "--cleaning_config": "{\"remove_duplicates\": true, \"missing_value_strategy\": \"median\", \"outlier_treatment\": \"cap\", \"data_type_conversion\": true}"
                        }
                    },
                    "ResultPath": "$.cleaning_result",
                    "Next": "TransformData",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 30,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "HandleError",
                            "ResultPath": "$.error_info"
                        }
                    ]
                },
                "TransformData": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::glue:startJobRun.sync",
                    "Parameters": {
                        "JobName": f"{glue_job_prefix}-feature-engineering",
                        "Arguments": {
                            "--input_path.$": "States.Format('s3://{}/{}/cleaned_data/data', $.s3_bucket, $.output_prefix)",
                            "--output_path.$": "States.Format('s3://{}/{}/transformed_data', $.s3_bucket, $.output_prefix)",
                            "--transformation_config": "{\"encode_categorical\": true, \"normalize_numeric\": true, \"feature_selection\": true}"
                        }
                    },
                    "ResultPath": "$.transformation_result",
                    "Next": "PrepareForML",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 30,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "HandleError",
                            "ResultPath": "$.error_info"
                        }
                    ]
                },
                "PrepareForML": {
                    "Type": "Pass",
                    "Parameters": {
                        "ml_ready": true,
                        "data_location.$": "States.Format('s3://{}/{}/transformed_data/data', $.s3_bucket, $.output_prefix)",
                        "next_step": "sagemaker_training"
                    },
                    "ResultPath": "$.ml_preparation",
                    "Next": "TrainModel"
                },
                "TrainModel": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::sagemaker:createAutoMLJob.sync",
                    "Parameters": {
                        "AutoMLJobName.$": "States.Format('adpa-automl-{}', $.execution_id)",
                        "InputDataConfig": [
                            {
                                "ChannelName": "training",
                                "DataSource": {
                                    "S3DataSource": {
                                        "S3DataType": "S3Prefix",
                                        "S3Uri.$": "$.ml_preparation.data_location",
                                        "S3DataDistributionType": "FullyReplicated"
                                    }
                                },
                                "ContentType": "text/csv",
                                "CompressionType": "None"
                            }
                        ],
                        "OutputDataConfig": {
                            "S3OutputPath.$": "States.Format('s3://{}/{}/models', $.s3_bucket, $.output_prefix)"
                        },
                        "ProblemType": "BinaryClassification",
                        "AutoMLJobObjective": {
                            "MetricName": "F1"
                        },
                        "RoleArn": "arn:aws:iam::123456789012:role/ADPASageMakerRole",
                        "AutoMLJobConfig": {
                            "CompletionCriteria": {
                                "MaxCandidates": 5,
                                "MaxRuntimePerTrainingJobInSeconds": 3600,
                                "MaxAutoMLJobRuntimeInSeconds": 7200
                            }
                        }
                    },
                    "ResultPath": "$.training_result",
                    "Next": "EvaluateModel",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 60,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "TrainingFailed",
                            "ResultPath": "$.error_info"
                        }
                    ]
                },
                "EvaluateModel": {
                    "Type": "Pass",
                    "Parameters": {
                        "evaluation_complete": true,
                        "model_performance.$": "$.training_result.BestCandidate.FinalAutoMLJobObjectiveMetric.Value",
                        "model_ready": true
                    },
                    "ResultPath": "$.evaluation_result",
                    "Next": "GenerateReport"
                },
                "GenerateReport": {
                    "Type": "Pass",
                    "Parameters": {
                        "report_generated": true,
                        "pipeline_summary": {
                            "status": "SUCCESS",
                            "profiling_completed": true,
                            "cleaning_completed": true,
                            "feature_engineering_completed": true,
                            "training_completed": true,
                            "evaluation_completed": true
                        }
                    },
                    "ResultPath": "$.report_result",
                    "Next": "ProcessingComplete"
                },
                "ProcessingComplete": {
                    "Type": "Pass",
                    "Parameters": {
                        "status": "SUCCESS",
                        "message": "ADPA data processing pipeline completed successfully",
                        "pipeline_summary": {
                            "profiling_job.$": "$.profiling_result.JobRunId",
                            "cleaning_job.$": "$.cleaning_result.JobRunId", 
                            "transformation_job.$": "$.transformation_result.JobRunId",
                            "ml_ready_data.$": "$.ml_preparation.data_location"
                        }
                    },
                    "End": True
                },
                "ProfilingFailed": {
                    "Type": "Pass",
                    "Parameters": {
                        "status": "ERROR",
                        "message": "Data profiling job failed",
                        "failed_job.$": "$.profiling_result"
                    },
                    "End": True
                },
                "TrainingFailed": {
                    "Type": "Pass",
                    "Parameters": {
                        "status": "ERROR",
                        "message": "SageMaker AutoML training job failed",
                        "failed_job.$": "$.training_result",
                        "error_details.$": "$.error_info"
                    },
                    "End": True
                },
                "HandleError": {
                    "Type": "Pass",
                    "Parameters": {
                        "status": "ERROR",
                        "message": "Pipeline execution failed. Check Glue job logs for details.",
                        "error_details.$": "$.error_info"
                    },
                    "End": True
                }
            }
        }
        
        return definition
    
    def _get_or_create_execution_role(self) -> str:
        """Get or create IAM role for Step Functions execution."""
        # This is a simplified implementation
        # In production, you would create proper IAM roles with specific permissions
        
        # For this demo, we'll assume the role exists or return a placeholder
        # You would need to create this role through IAM or CloudFormation
        
        account_id = "123456789012"  # This should be dynamically determined
        role_name = "ADPAStepFunctionsRole"
        
        return f"arn:aws:iam::{account_id}:role/{role_name}"
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all ADPA workflows (state machines)."""
        try:
            response = self.sfn_client.list_state_machines()
            
            adpa_workflows = []
            for state_machine in response.get('stateMachines', []):
                if 'adpa' in state_machine['name'].lower():
                    adpa_workflows.append({
                        'name': state_machine['name'],
                        'arn': state_machine['stateMachineArn'],
                        'creation_date': state_machine['creationDate'].isoformat(),
                        'type': state_machine['type']
                    })
            
            return adpa_workflows
            
        except ClientError as e:
            self.logger.error(f"Failed to list state machines: {e.response['Error']['Message']}")
            return []
    
    def get_execution_history(self, execution_arn: str) -> List[Dict[str, Any]]:
        """Get the execution history for a workflow."""
        try:
            response = self.sfn_client.get_execution_history(executionArn=execution_arn)
            
            events = []
            for event in response.get('events', []):
                events.append({
                    'timestamp': event['timestamp'].isoformat(),
                    'type': event['type'],
                    'id': event['id'],
                    'details': event.get('stateEnteredEventDetails', event.get('stateExitedEventDetails', {}))
                })
            
            return events
            
        except ClientError as e:
            self.logger.error(f"Failed to get execution history: {e.response['Error']['Message']}")
            return []