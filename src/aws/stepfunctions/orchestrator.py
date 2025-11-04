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
                           lambda_function_arn: str,
                           s3_bucket: str) -> ExecutionResult:
        """
        Create ADPA data processing workflow in Step Functions.
        
        Args:
            workflow_name: Name for the Step Functions state machine
            lambda_function_arn: ARN of the Lambda function for processing
            s3_bucket: S3 bucket for data storage
            
        Returns:
            ExecutionResult with workflow creation details
        """
        try:
            self.logger.info(f"Creating ADPA workflow: {workflow_name}")
            
            # Define the state machine definition
            definition = self._create_workflow_definition(lambda_function_arn, s3_bucket)
            
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
    
    def _create_workflow_definition(self, lambda_function_arn: str, s3_bucket: str) -> Dict[str, Any]:
        """Create the Step Functions workflow definition for ADPA."""
        
        definition = {
            "Comment": "ADPA Data Processing Workflow",
            "StartAt": "ProfileData",
            "States": {
                "ProfileData": {
                    "Type": "Task",
                    "Resource": lambda_function_arn,
                    "Parameters": {
                        "bucket": s3_bucket,
                        "input_key.$": "$.input_key",
                        "output_key.$": "States.Format('{}/profiled.json', $.output_prefix)",
                        "processing_config": {
                            "operation": "profile"
                        }
                    },
                    "Next": "CheckDataQuality",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "HandleError"
                        }
                    ]
                },
                "CheckDataQuality": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.processing_results.data_quality.completeness_score",
                            "NumericGreaterThan": 0.7,
                            "Next": "CleanData"
                        }
                    ],
                    "Default": "DataQualityIssue"
                },
                "CleanData": {
                    "Type": "Task",
                    "Resource": lambda_function_arn,
                    "Parameters": {
                        "bucket": s3_bucket,
                        "input_key.$": "$.input_key",
                        "output_key.$": "States.Format('{}/cleaned.csv', $.output_prefix)",
                        "processing_config": {
                            "operation": "clean",
                            "parameters": {
                                "missing_strategy": "fill_median",
                                "handle_outliers": True
                            }
                        }
                    },
                    "Next": "TransformData",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ]
                },
                "TransformData": {
                    "Type": "Task",
                    "Resource": lambda_function_arn,
                    "Parameters": {
                        "bucket": s3_bucket,
                        "input_key.$": "States.Format('{}/cleaned.csv', $.output_prefix)",
                        "output_key.$": "States.Format('{}/transformed.csv', $.output_prefix)",
                        "processing_config": {
                            "operation": "transform",
                            "parameters": {
                                "encode_categorical": True,
                                "normalize_numeric": True
                            }
                        }
                    },
                    "Next": "ProcessingComplete",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ]
                },
                "ProcessingComplete": {
                    "Type": "Pass",
                    "Result": {
                        "status": "SUCCESS",
                        "message": "Data processing pipeline completed successfully"
                    },
                    "End": True
                },
                "DataQualityIssue": {
                    "Type": "Pass",
                    "Result": {
                        "status": "WARNING",
                        "message": "Data quality issues detected. Manual review recommended."
                    },
                    "End": True
                },
                "HandleError": {
                    "Type": "Pass",
                    "Result": {
                        "status": "ERROR",
                        "message": "Pipeline execution failed. Check logs for details."
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