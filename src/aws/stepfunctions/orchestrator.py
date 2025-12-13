"""
AWS Step Functions Orchestration for ADPA Pipelines
"""

import json
import logging
import boto3
import time
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
from datetime import datetime, timezone

from ...agent.core.interfaces import ExecutionResult, StepStatus

try:
    from aws_xray_sdk.core import xray_recorder
    XRAY_ENABLED = True
except ImportError:
    XRAY_ENABLED = False
    # Create dummy decorator if X-Ray not available
    class xray_recorder:
        @staticmethod
        def capture(name):
            def decorator(func):
                return func
            return decorator


class StepFunctionsOrchestrator:
    """
    AWS Step Functions orchestrator for ADPA pipeline execution.
    Manages end-to-end pipeline workflows with error handling and monitoring.
    """
    
    def __init__(self, region: str = "us-east-2", role_arn: Optional[str] = None):
        """
        Initialize Step Functions orchestrator.
        
        Args:
            region: AWS region
            role_arn: IAM role ARN for Step Functions execution
        """
        self.region = region
        self.logger = logging.getLogger(__name__)
        
        # Get account ID dynamically
        try:
            sts_client = boto3.client('sts', region_name=region)
            account_id = sts_client.get_caller_identity()['Account']
            self.account_id = account_id
            self.role_arn = role_arn or f"arn:aws:iam::{account_id}:role/adpa-stepfunctions-role"
            self.logger.info(f"Using account ID: {account_id}")
        except Exception as e:
            self.logger.warning(f"Could not get account ID: {e}")
            self.account_id = "123456789012"
            self.role_arn = role_arn or f"arn:aws:iam::{self.account_id}:role/adpa-stepfunctions-role"
        
        # Initialize Step Functions client
        try:
            self.client = boto3.client('stepfunctions', region_name=region)
            # Test client connectivity
            self.client.list_state_machines(maxResults=1)
            self.logger.info(f"Step Functions client initialized successfully in region {region}")
            self.simulation_mode = False
        except Exception as e:
            self.logger.error(f"Step Functions client initialization failed: {e}")
            self.logger.error("Falling back to simulation mode for development")
            self.client = None
            self.simulation_mode = True
    
    def is_simulation_mode(self) -> bool:
        """Check if orchestrator is running in simulation mode."""
        return self.simulation_mode
    
    def get_real_state_machines(self) -> List[Dict[str, Any]]:
        """Get list of existing Step Functions state machines."""
        if self.simulation_mode:
            return []
        
        try:
            response = self.client.list_state_machines()
            return response.get('stateMachines', [])
        except Exception as e:
            self.logger.error(f"Failed to list state machines: {e}")
            return []
    
    def _ensure_log_group_exists(self, log_group_name: str) -> bool:
        """Ensure CloudWatch log group exists for Step Functions logging."""
        if self.simulation_mode:
            return True
            
        try:
            logs_client = boto3.client('logs', region_name=self.region)
            
            # Check if log group exists
            try:
                logs_client.describe_log_groups(logGroupNamePrefix=log_group_name)
                self.logger.info(f"Log group {log_group_name} already exists")
                return True
            except logs_client.exceptions.ResourceNotFoundException:
                pass
            
            # Create log group
            logs_client.create_log_group(
                logGroupName=log_group_name,
                tags={
                    'Project': 'ADPA',
                    'Component': 'StepFunctions',
                    'Environment': 'Development'
                }
            )
            
            # Set retention policy (14 days)
            logs_client.put_retention_policy(
                logGroupName=log_group_name,
                retentionInDays=14
            )
            
            self.logger.info(f"Created log group: {log_group_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create log group {log_group_name}: {e}")
            return False
    
    @xray_recorder.capture('create_pipeline_state_machine')
    def create_state_machine_with_retries(self, 
                                        pipeline_config: Dict[str, Any],
                                        name: str = None,
                                        max_retries: int = 3) -> Dict[str, Any]:
        """Create state machine with automatic retries and better error handling."""
        
        # Ensure Glue jobs exist before creating state machine
        if not self.simulation_mode:
            self.logger.info("Ensuring Glue ETL jobs exist...")
            glue_result = self.ensure_glue_jobs_exist()
            if glue_result.get('status') == 'failed':
                self.logger.warning(f"Glue jobs setup failed: {glue_result.get('error')}")
        
        for attempt in range(max_retries):
            try:
                result = self.create_pipeline_state_machine(pipeline_config, name)
                if result.get('status') != 'FAILED':
                    return result
                    
                if attempt < max_retries - 1:
                    self.logger.warning(f"State machine creation attempt {attempt + 1} failed, retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"All {max_retries} attempts to create state machine failed")
                    raise e
                else:
                    self.logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying...")
                    time.sleep(2 ** attempt)
                    
        return {'status': 'FAILED', 'error': 'Max retries exceeded'}
    
    def ensure_glue_jobs_exist(self) -> Dict[str, Any]:
        """Ensure required Glue ETL jobs exist for Step Functions pipeline."""
        try:
            from ...etl.glue_processor import GlueETLProcessor
            
            glue_processor = GlueETLProcessor(region=self.region)
            
            # Create mock script first
            script_path = glue_processor.create_mock_script_in_s3()
            self.logger.info(f"Mock Glue script created at: {script_path}")
            
            # Ensure standard jobs exist
            results = glue_processor.ensure_standard_jobs_exist()
            
            self.logger.info(f"Glue jobs status: {results}")
            
            return {
                'status': 'success',
                'jobs_checked': len(results),
                'results': results
            }
            
        except Exception as e:
            self.logger.error(f"Failed to ensure Glue jobs exist: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
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
            
            if self.simulation_mode:
                return self._simulate_state_machine_creation(state_machine_name, definition)
            
            # Create state machine without logging for now (can be added later)
            response = self.client.create_state_machine(
                name=state_machine_name,
                definition=json.dumps(definition),
                roleArn=self.role_arn,
                type='STANDARD',
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
            
            if self.simulation_mode:
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
            if self.simulation_mode:
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
    
    def get_execution_history(self, execution_arn: str, reverse_order: bool = False) -> List[Dict[str, Any]]:
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
                        reverseOrder=reverse_order
                    )
                else:
                    response = self.client.get_execution_history(
                        executionArn=execution_arn,
                        reverseOrder=reverse_order
                    )
                
                events.extend(response['events'])
                
                if 'nextToken' not in response:
                    break
                next_token = response['nextToken']
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error getting execution history: {e}")
            return []

    def summarize_execution(self, execution_arn: str) -> Dict[str, Any]:
        """Build a human-friendly execution summary from Step Functions history."""
        if self.simulation_mode or not execution_arn:
            return {
                'steps': [],
                'logs': [],
                'performance_metrics': {},
                'execution_time': 0,
                'samples_processed': 0,
                'features_used': 0
            }

        try:
            execution_details = self.client.describe_execution(executionArn=execution_arn)
        except Exception as exc:  # pragma: no cover - best effort telemetry
            self.logger.error(f"Unable to describe execution {execution_arn}: {exc}")
            execution_details = {}

        history = self.get_execution_history(execution_arn, reverse_order=False)
        steps: List[Dict[str, Any]] = []
        logs: List[str] = []
        performance_metrics: Dict[str, Any] = {}
        step_entries: Dict[str, Dict[str, Any]] = {}

        start_time = execution_details.get('startDate')
        stop_time = execution_details.get('stopDate')
        status = execution_details.get('status', 'UNKNOWN')
        execution_output: Dict[str, Any] = {}

        raw_output = execution_details.get('output')
        if isinstance(raw_output, str):
            try:
                execution_output = json.loads(raw_output)
            except json.JSONDecodeError:
                execution_output = {}
        elif isinstance(raw_output, dict):
            execution_output = raw_output

        def _iso(ts: Optional[datetime]) -> Optional[str]:
            if not ts:
                return None
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

        for event in history:
            event_type = event.get('type', '')
            timestamp = event.get('timestamp')

            if event_type.endswith('StateEntered'):
                details = event.get('stateEnteredEventDetails', {})
                state_name = details.get('name')
                if not state_name:
                    continue
                step_entries[state_name] = {
                    'start': timestamp,
                    'input': details.get('input')
                }
                logs.append(f"[ENTER] {state_name} at {timestamp.isoformat() if timestamp else 'unknown'}")

            elif event_type.endswith('StateExited'):
                details = event.get('stateExitedEventDetails', {})
                state_name = details.get('name')
                if not state_name:
                    continue
                entry = step_entries.pop(state_name, {})
                start = entry.get('start', timestamp)
                duration = None
                if start and timestamp:
                    duration = max(0, (timestamp - start).total_seconds())
                steps.append({
                    'id': state_name.lower().replace(' ', '-'),
                    'name': state_name,
                    'status': 'completed',
                    'startTime': _iso(start),
                    'endTime': _iso(timestamp),
                    'duration': duration,
                    'logs': [
                        f"State input: {entry.get('input', '')}" if entry.get('input') else "",
                        f"State output: {details.get('output', '')}" if details.get('output') else ""
                    ]
                })
                logs.append(f"[EXIT] {state_name} at {timestamp.isoformat() if timestamp else 'unknown'}")

            elif event_type.startswith('Execution'):
                logs.append(f"[{event_type}] at {timestamp.isoformat() if timestamp else 'unknown'}")

        if status and status != 'SUCCEEDED':
            logs.append(f"[ERROR] Execution completed with status {status}")

        # Clean up log noise from empty strings
        for step in steps:
            step['logs'] = [line for line in step['logs'] if line]

        execution_time = None
        if start_time and stop_time:
            execution_time = max(0, (stop_time - start_time).total_seconds())

        if isinstance(execution_output.get('metrics'), dict):
            performance_metrics.update(execution_output['metrics'])

        if isinstance(execution_output.get('result'), dict):
            result_section = execution_output['result']
            if isinstance(result_section.get('metrics'), dict):
                performance_metrics.update(result_section['metrics'])
            if isinstance(result_section.get('evaluation_metrics'), dict):
                performance_metrics.update(result_section['evaluation_metrics'])

        performance_metrics.update({
            'execution_time': execution_time or 0,
            'steps_completed': len(steps),
            'status': status
        })

        return {
            'steps': steps,
            'logs': logs,
            'performance_metrics': performance_metrics,
            'execution_time': execution_time or 0,
            'samples_processed': performance_metrics.get('samples_processed', 0),
            'features_used': performance_metrics.get('features_used', 0)
        }
    
    def _create_state_machine_definition(self, pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create Step Functions state machine definition."""
        
        states = {}
        
        # Add pipeline steps as states
        pipeline_steps = pipeline_config.get('steps', [])
        self.logger.debug(f"Creating state machine with {len(pipeline_steps)} steps")
        
        for i, step in enumerate(pipeline_steps):
            step_name = step.get('name', f"Step{i}_{step.get('type', 'task')}")
            step_type = step.get('type', 'lambda')
            self.logger.debug(f"Creating state {i}: {step_name} (type: {step_type})")
            
            # Map step types to AWS resources
            step_type_mapping = {
                'data_validation': 'lambda',
                'data_cleaning': 'lambda', 
                'feature_engineering': 'lambda',
                'model_training': 'sagemaker',
                'model_evaluation': 'lambda',
                'data_ingestion': 'lambda',
                'data_preprocessing': 'glue'
            }
            
            # Use mapped type or default to lambda
            aws_step_type = step_type_mapping.get(step_type, 'lambda')
            self.logger.debug(f"Mapped {step_type} to AWS type: {aws_step_type}")
            
            if aws_step_type == 'lambda':
                states[step_name] = {
                    "Type": "Task",
                    "Resource": f"arn:aws:lambda:{self.region}:{self.account_id}:function:adpa-data-processor-development",
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
            elif aws_step_type == 'glue':
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
            elif aws_step_type == 'sagemaker':
                states[step_name] = {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::sagemaker:createTrainingJob.sync",
                    "Parameters": {
                        "TrainingJobName.$": "$.training_job_name",
                        "RoleArn": f"arn:aws:iam::{self.account_id}:role/adpa-sagemaker-execution-role",
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
                next_step = pipeline_steps[i + 1].get('name', f"Step{i+1}_{pipeline_steps[i + 1].get('type', 'task')}")
                states[step_name]["Next"] = next_step
            else:
                states[step_name]["Next"] = "Success"
        
        # Add success and error states
        states["Success"] = {
            "Type": "Succeed"
        }
        
        states["ErrorHandler"] = {
            "Type": "Task",
            "Resource": f"arn:aws:lambda:{self.region}:{self.account_id}:function:adpa-error-handler-development",
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
        start_at_state = pipeline_steps[0].get('name', f"Step0_{pipeline_steps[0].get('type', 'task')}") if pipeline_steps else "Success"
        self.logger.debug(f"State machine will start at: {start_at_state}")
        self.logger.debug(f"Available states: {list(states.keys())}")
        
        definition = {
            "Comment": "ADPA Pipeline State Machine",
            "StartAt": start_at_state,
            "States": states,
            "TimeoutSeconds": 7200,  # 2 hour timeout
            "Version": "1.0"
        }
        
        return definition
    
    def _simulate_state_machine_creation(self, name: str, definition: Dict) -> Dict[str, Any]:
        """Simulate state machine creation for development."""
        self.logger.warning("Simulating Step Functions state machine creation")
        return {
            'state_machine_arn': f'arn:aws:states:{self.region}:{self.account_id}:stateMachine:{name}',
            'name': name,
            'definition': definition,
            'created_at': datetime.now().isoformat(),
            'status': 'SIMULATED'
        }
    
    def _simulate_pipeline_execution(self, execution_name: str, input_data: Dict) -> Dict[str, Any]:
        """Simulate pipeline execution for development."""
        self.logger.warning("Simulating Step Functions pipeline execution")
        return {
            'execution_arn': f'arn:aws:states:{self.region}:{self.account_id}:execution:adpa-pipeline:{execution_name}',
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