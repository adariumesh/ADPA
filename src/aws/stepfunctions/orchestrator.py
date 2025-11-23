"""
AWS Step Functions Orchestration for ADPA Pipelines
"""

import json
import logging
import boto3
import time
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
from datetime import datetime

from ...agent.core.interfaces import ExecutionResult, StepStatus


class StepFunctionsOrchestrator:
    """
    AWS Step Functions orchestrator for ADPA pipeline execution.
    Manages end-to-end pipeline workflows with error handling and monitoring.
    """
    
    def __init__(self, region: str = "us-east-1", role_arn: Optional[str] = None):
        """
        Initialize Step Functions orchestrator.
        
        Args:
            region: AWS region
            role_arn: IAM role ARN for Step Functions execution
        """
        self.region = region
        self.role_arn = role_arn or f"arn:aws:iam::123456789012:role/ADPAStepFunctionsRole"
        self.logger = logging.getLogger(__name__)
        
        try:
            self.client = boto3.client('stepfunctions', region_name=region)
            self.logger.info(f"Step Functions client initialized in region {region}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Step Functions client: {e}")
            self.client = None
    
    def create_pipeline_state_machine(self, 
                                    pipeline_config: Dict[str, Any],
                                    name: str = None) -> Dict[str, Any]:
        """
        Create a Step Functions state machine for the pipeline.
        
        Args:
            pipeline_config: Pipeline configuration with steps
            name: State machine name
            
        Returns:
            Dictionary with state machine ARN and creation details
        """
        try:
            state_machine_name = name or f"adpa-pipeline-{int(time.time())}"
            
            # Generate state machine definition
            definition = self._create_state_machine_definition(pipeline_config)
            
            if not self.client:
                return self._simulate_state_machine_creation(state_machine_name, definition)
            
            response = self.client.create_state_machine(
                name=state_machine_name,
                definition=json.dumps(definition),
                roleArn=self.role_arn,
                type='STANDARD',
                loggingConfiguration={
                    'level': 'ALL',
                    'includeExecutionData': True,
                    'destinations': [
                        {
                            'cloudWatchLogsLogGroup': {
                                'logGroupArn': f'arn:aws:logs:{self.region}:123456789012:log-group:/aws/stepfunctions/{state_machine_name}'
                            }
                        }
                    ]
                },
                tags=[
                    {'key': 'Project', 'value': 'ADPA'},
                    {'key': 'Environment', 'value': 'Development'},
                    {'key': 'CreatedBy', 'value': 'ADPA-Agent'}
                ]
            )
            
            self.logger.info(f"Created state machine: {state_machine_name}")
            
            return {
                'state_machine_arn': response['stateMachineArn'],
                'name': state_machine_name,
                'definition': definition,
                'created_at': datetime.now().isoformat(),
                'status': 'ACTIVE'
            }
            
        except ClientError as e:
            error_msg = f"AWS Error creating state machine: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            ).__dict__
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            ).__dict__
    
    def execute_pipeline(self, 
                        state_machine_arn: str,
                        input_data: Dict[str, Any],
                        execution_name: str = None) -> Dict[str, Any]:
        """
        Execute a pipeline using Step Functions.
        
        Args:
            state_machine_arn: ARN of the state machine
            input_data: Input data for pipeline execution
            execution_name: Name for this execution
            
        Returns:
            Dictionary with execution details and status
        """
        try:
            execution_name = execution_name or f"adpa-execution-{int(time.time())}"
            
            if not self.client:
                return self._simulate_pipeline_execution(execution_name, input_data)
            
            response = self.client.start_execution(
                stateMachineArn=state_machine_arn,
                name=execution_name,
                input=json.dumps(input_data)
            )
            
            execution_arn = response['executionArn']
            
            self.logger.info(f"Started pipeline execution: {execution_name}")
            
            # Monitor execution
            execution_result = self.monitor_execution(execution_arn)
            
            return {
                'execution_arn': execution_arn,
                'execution_name': execution_name,
                'status': execution_result['status'],
                'result': execution_result,
                'started_at': datetime.now().isoformat()
            }
            
        except ClientError as e:
            error_msg = f"AWS Error executing pipeline: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return {'status': 'FAILED', 'error': error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg)
            return {'status': 'FAILED', 'error': error_msg}
    
    def monitor_execution(self, execution_arn: str, max_wait_time: int = 3600) -> Dict[str, Any]:
        """
        Monitor Step Functions execution until completion.
        
        Args:
            execution_arn: ARN of the execution to monitor
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            Dictionary with final execution status and results
        """
        try:
            if not self.client:
                return self._simulate_execution_monitoring(execution_arn)
            
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                response = self.client.describe_execution(executionArn=execution_arn)
                
                status = response['status']
                
                if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                    # Execution completed
                    result = {
                        'status': status,
                        'start_date': response['startDate'].isoformat(),
                        'stop_date': response.get('stopDate', datetime.now()).isoformat(),
                        'input': json.loads(response['input']) if response.get('input') else {},
                        'output': json.loads(response['output']) if response.get('output') else {},
                        'execution_arn': execution_arn
                    }
                    
                    if status == 'FAILED':
                        result['error'] = response.get('error', 'Unknown error')
                        result['cause'] = response.get('cause', 'Unknown cause')
                    
                    self.logger.info(f"Execution {execution_arn} completed with status: {status}")
                    return result
                
                # Still running, wait before checking again
                time.sleep(30)
            
            # Timeout reached
            self.logger.warning(f"Execution {execution_arn} monitoring timed out after {max_wait_time} seconds")
            return {
                'status': 'TIMEOUT',
                'error': f'Monitoring timed out after {max_wait_time} seconds',
                'execution_arn': execution_arn
            }
            
        except ClientError as e:
            error_msg = f"AWS Error monitoring execution: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return {'status': 'MONITORING_FAILED', 'error': error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.error(error_msg)
            return {'status': 'MONITORING_FAILED', 'error': error_msg}
    
    def get_execution_history(self, execution_arn: str) -> List[Dict[str, Any]]:
        """
        Get detailed execution history for debugging and analysis.
        
        Args:
            execution_arn: ARN of the execution
            
        Returns:
            List of execution events
        """
        try:
            if not self.client:
                return self._simulate_execution_history()
            
            events = []
            next_token = None
            
            while True:
                if next_token:
                    response = self.client.get_execution_history(
                        executionArn=execution_arn,
                        nextToken=next_token,
                        reverseOrder=True
                    )
                else:
                    response = self.client.get_execution_history(
                        executionArn=execution_arn,
                        reverseOrder=True
                    )
                
                events.extend(response['events'])
                
                if 'nextToken' not in response:
                    break
                next_token = response['nextToken']
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error getting execution history: {e}")
            return []
    
    def _create_state_machine_definition(self, pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create Step Functions state machine definition."""
        
        states = {}
        
        # Add pipeline steps as states
        pipeline_steps = pipeline_config.get('steps', [])
        
        for i, step in enumerate(pipeline_steps):
            step_name = step.get('step', f'Step{i}')
            step_type = step.get('type', 'lambda')
            
            if step_type == 'lambda':
                states[step_name] = {
                    "Type": "Task",
                    "Resource": f"arn:aws:lambda:{self.region}:123456789012:function:adpa-data-processor",
                    "Parameters": {
                        "step_config": step,
                        "input.$": "$"
                    },
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 2,
                            "MaxAttempts": 3,
                            "BackoffRate": 2
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "ErrorHandler",
                            "ResultPath": "$.error"
                        }
                    ]
                }
            elif step_type == 'glue':
                states[step_name] = {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::glue:startJobRun.sync",
                    "Parameters": {
                        "JobName": f"adpa-{step_name.lower()}",
                        "Arguments": {
                            "--input-path.$": "$.data_path",
                            "--output-path.$": "$.output_path"
                        }
                    },
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 30,
                            "MaxAttempts": 2,
                            "BackoffRate": 2
                        }
                    ]
                }
            elif step_type == 'sagemaker':
                states[step_name] = {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::sagemaker:createTrainingJob.sync",
                    "Parameters": {
                        "TrainingJobName.$": "$.training_job_name",
                        "RoleArn": f"arn:aws:iam::123456789012:role/SageMakerExecutionRole",
                        "AlgorithmSpecification": {
                            "TrainingImage": "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:0.23-1-cpu-py3",
                            "TrainingInputMode": "File"
                        },
                        "InputDataConfig": [
                            {
                                "ChannelName": "training",
                                "DataSource": {
                                    "S3DataSource": {
                                        "S3DataType": "S3Prefix",
                                        "S3Uri.$": "$.training_data_path",
                                        "S3DataDistributionType": "FullyReplicated"
                                    }
                                }
                            }
                        ],
                        "OutputDataConfig": {
                            "S3OutputPath.$": "$.model_output_path"
                        },
                        "ResourceConfig": {
                            "InstanceType": "ml.m5.large",
                            "InstanceCount": 1,
                            "VolumeSizeInGB": 10
                        },
                        "StoppingCondition": {
                            "MaxRuntimeInSeconds": 86400
                        }
                    }
                }
            
            # Set next state
            if i < len(pipeline_steps) - 1:
                next_step = pipeline_steps[i + 1].get('step', f'Step{i+1}')
                states[step_name]["Next"] = next_step
            else:
                states[step_name]["Next"] = "Success"
        
        # Add success and error states
        states["Success"] = {
            "Type": "Succeed",
            "Result": "Pipeline completed successfully"
        }
        
        states["ErrorHandler"] = {
            "Type": "Task",
            "Resource": f"arn:aws:lambda:{self.region}:123456789012:function:adpa-error-handler",
            "Parameters": {
                "error.$": "$.error",
                "context.$": "$"
            },
            "Next": "Failure"
        }
        
        states["Failure"] = {
            "Type": "Fail",
            "Cause": "Pipeline execution failed"
        }
        
        # Build complete definition
        definition = {
            "Comment": "ADPA Pipeline State Machine",
            "StartAt": pipeline_steps[0].get('step', 'Step0') if pipeline_steps else "Success",
            "States": states,
            "TimeoutSeconds": 7200,  # 2 hour timeout
            "Version": "1.0"
        }
        
        return definition
    
    def _simulate_state_machine_creation(self, name: str, definition: Dict) -> Dict[str, Any]:
        """Simulate state machine creation for development."""
        self.logger.warning("Simulating Step Functions state machine creation")
        return {
            'state_machine_arn': f'arn:aws:states:{self.region}:123456789012:stateMachine:{name}',
            'name': name,
            'definition': definition,
            'created_at': datetime.now().isoformat(),
            'status': 'SIMULATED'
        }
    
    def _simulate_pipeline_execution(self, execution_name: str, input_data: Dict) -> Dict[str, Any]:
        """Simulate pipeline execution for development."""
        self.logger.warning("Simulating Step Functions pipeline execution")
        return {
            'execution_arn': f'arn:aws:states:{self.region}:123456789012:execution:adpa-pipeline:{execution_name}',
            'execution_name': execution_name,
            'status': 'SUCCEEDED',
            'result': {
                'status': 'SUCCEEDED',
                'output': {'message': 'Simulated successful pipeline execution'},
                'duration': '00:15:30'
            },
            'started_at': datetime.now().isoformat()
        }
    
    def _simulate_execution_monitoring(self, execution_arn: str) -> Dict[str, Any]:
        """Simulate execution monitoring for development."""
        self.logger.warning("Simulating Step Functions execution monitoring")
        return {
            'status': 'SUCCEEDED',
            'start_date': datetime.now().isoformat(),
            'stop_date': datetime.now().isoformat(),
            'output': {'pipeline_result': 'success', 'metrics': {'accuracy': 0.85}},
            'execution_arn': execution_arn
        }
    
    def _simulate_execution_history(self) -> List[Dict[str, Any]]:
        """Simulate execution history for development."""
        return [
            {
                'timestamp': datetime.now().isoformat(),
                'type': 'ExecutionStarted',
                'id': 1,
                'executionStartedEventDetails': {'input': '{}'}
            },
            {
                'timestamp': datetime.now().isoformat(),
                'type': 'ExecutionSucceeded',
                'id': 2,
                'executionSucceededEventDetails': {'output': '{"result": "success"}'}
            }
        ]