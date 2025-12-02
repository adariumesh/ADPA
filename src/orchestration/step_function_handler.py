"""
AWS Step Functions Handler for ADPA ML Pipeline Orchestration

This module provides utilities for starting, monitoring, and managing
Step Functions state machine executions for ML pipeline orchestration.
"""

import json
import boto3
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError


class StepFunctionOrchestrator:
    """Orchestrates ML pipelines using AWS Step Functions"""
    
    def __init__(self, region: str = 'us-east-2'):
        """
        Initialize Step Functions orchestrator
        
        Args:
            region: AWS region name
        """
        self.region = region
        self.sfn_client = boto3.client('stepfunctions', region_name=region)
        self.state_machine_arn = self._get_state_machine_arn()
        
    def _get_state_machine_arn(self) -> str:
        """Get the ARN of the ADPA pipeline state machine"""
        # In production, this would be stored in environment variable or SSM Parameter Store
        return f"arn:aws:states:{self.region}:083308938449:stateMachine:adpa-ml-pipeline"
    
    def start_pipeline(
        self,
        objective: str,
        dataset_path: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start a new ML pipeline execution
        
        Args:
            objective: Natural language description of ML objective
            dataset_path: S3 path to input dataset
            config: Optional pipeline configuration
            
        Returns:
            Dict containing execution ARN, pipeline ID, and start time
        """
        # Generate unique pipeline ID
        pipeline_id = f"pipeline-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        
        # Prepare input for state machine
        pipeline_input = {
            "pipeline_id": pipeline_id,
            "objective": objective,
            "dataset_path": dataset_path,
            "config": config or {},
            "start_time": datetime.utcnow().isoformat(),
            "training_job_name": f"adpa-training-{pipeline_id}"
        }
        
        try:
            # Start state machine execution
            response = self.sfn_client.start_execution(
                stateMachineArn=self.state_machine_arn,
                name=pipeline_id,
                input=json.dumps(pipeline_input)
            )
            
            return {
                "status": "started",
                "pipeline_id": pipeline_id,
                "execution_arn": response['executionArn'],
                "start_time": response['startDate'].isoformat()
            }
            
        except ClientError as e:
            return {
                "status": "failed",
                "pipeline_id": pipeline_id,
                "error": str(e),
                "error_code": e.response['Error']['Code']
            }
    
    def get_execution_status(self, pipeline_id: str) -> Dict[str, Any]:
        """
        Get the current status of a pipeline execution
        
        Args:
            pipeline_id: Unique pipeline identifier
            
        Returns:
            Dict containing execution status, current state, and progress
        """
        execution_arn = f"{self.state_machine_arn.replace(':stateMachine:', ':execution:')}:{pipeline_id}"
        
        try:
            # Get execution details
            response = self.sfn_client.describe_execution(
                executionArn=execution_arn
            )
            
            # Parse execution input and output
            execution_input = json.loads(response['input'])
            execution_output = None
            if response['status'] == 'SUCCEEDED':
                execution_output = json.loads(response.get('output', '{}'))
            
            # Get execution history for current state
            history = self.sfn_client.get_execution_history(
                executionArn=execution_arn,
                maxResults=10,
                reverseOrder=True
            )
            
            current_state = self._extract_current_state(history['events'])
            
            return {
                "pipeline_id": pipeline_id,
                "status": response['status'],  # RUNNING, SUCCEEDED, FAILED, TIMED_OUT, ABORTED
                "current_state": current_state,
                "start_time": response['startDate'].isoformat(),
                "stop_time": response.get('stopDate', datetime.utcnow()).isoformat() if response.get('stopDate') else None,
                "input": execution_input,
                "output": execution_output,
                "execution_arn": execution_arn
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ExecutionDoesNotExist':
                return {
                    "pipeline_id": pipeline_id,
                    "status": "NOT_FOUND",
                    "error": f"Pipeline execution {pipeline_id} not found"
                }
            else:
                return {
                    "pipeline_id": pipeline_id,
                    "status": "ERROR",
                    "error": str(e)
                }
    
    def _extract_current_state(self, events: List[Dict]) -> str:
        """Extract current state from execution history events"""
        for event in events:
            if 'stateEnteredEventDetails' in event:
                return event['stateEnteredEventDetails']['name']
        return "Unknown"
    
    def stop_execution(self, pipeline_id: str, reason: str = "User requested") -> Dict[str, Any]:
        """
        Stop a running pipeline execution
        
        Args:
            pipeline_id: Unique pipeline identifier
            reason: Reason for stopping
            
        Returns:
            Dict containing stop status
        """
        execution_arn = f"{self.state_machine_arn.replace(':stateMachine:', ':execution:')}:{pipeline_id}"
        
        try:
            response = self.sfn_client.stop_execution(
                executionArn=execution_arn,
                error="ExecutionStopped",
                cause=reason
            )
            
            return {
                "status": "stopped",
                "pipeline_id": pipeline_id,
                "stop_time": response['stopDate'].isoformat()
            }
            
        except ClientError as e:
            return {
                "status": "failed",
                "pipeline_id": pipeline_id,
                "error": str(e)
            }
    
    def list_executions(
        self,
        status_filter: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List recent pipeline executions
        
        Args:
            status_filter: Filter by status (RUNNING, SUCCEEDED, FAILED, etc.)
            max_results: Maximum number of results to return
            
        Returns:
            List of execution summaries
        """
        try:
            params = {
                "stateMachineArn": self.state_machine_arn,
                "maxResults": max_results
            }
            
            if status_filter:
                params["statusFilter"] = status_filter
            
            response = self.sfn_client.list_executions(**params)
            
            executions = []
            for execution in response['executions']:
                pipeline_id = execution['name']
                executions.append({
                    "pipeline_id": pipeline_id,
                    "status": execution['status'],
                    "start_time": execution['startDate'].isoformat(),
                    "stop_time": execution.get('stopDate', datetime.utcnow()).isoformat() if execution.get('stopDate') else None,
                    "execution_arn": execution['executionArn']
                })
            
            return executions
            
        except ClientError as e:
            return [{
                "error": str(e),
                "error_code": e.response['Error']['Code']
            }]
    
    def get_execution_logs(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """
        Get detailed execution history/logs for a pipeline
        
        Args:
            pipeline_id: Unique pipeline identifier
            
        Returns:
            List of execution events with timestamps and details
        """
        execution_arn = f"{self.state_machine_arn.replace(':stateMachine:', ':execution:')}:{pipeline_id}"
        
        try:
            response = self.sfn_client.get_execution_history(
                executionArn=execution_arn,
                maxResults=100
            )
            
            logs = []
            for event in response['events']:
                log_entry = {
                    "timestamp": event['timestamp'].isoformat(),
                    "type": event['type'],
                    "id": event['id']
                }
                
                # Add state-specific details
                if 'stateEnteredEventDetails' in event:
                    log_entry['state'] = event['stateEnteredEventDetails']['name']
                    log_entry['input'] = event['stateEnteredEventDetails'].get('input', '')
                elif 'stateExitedEventDetails' in event:
                    log_entry['state'] = event['stateExitedEventDetails']['name']
                    log_entry['output'] = event['stateExitedEventDetails'].get('output', '')
                elif 'taskFailedEventDetails' in event:
                    log_entry['error'] = event['taskFailedEventDetails'].get('error', '')
                    log_entry['cause'] = event['taskFailedEventDetails'].get('cause', '')
                
                logs.append(log_entry)
            
            return logs
            
        except ClientError as e:
            return [{
                "error": str(e),
                "pipeline_id": pipeline_id
            }]


# Lambda handler for Step Functions integration
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function handler for Step Functions tasks
    
    This function can be called by individual states in the Step Functions workflow
    to perform specific tasks like validation, data processing, etc.
    
    Args:
        event: Event data from Step Functions
        context: Lambda context object
        
    Returns:
        Dict containing task results
    """
    action = event.get('action', 'start_pipeline')
    orchestrator = StepFunctionOrchestrator()
    
    if action == 'start_pipeline':
        return orchestrator.start_pipeline(
            objective=event['objective'],
            dataset_path=event['dataset_path'],
            config=event.get('config')
        )
    
    elif action == 'get_status':
        return orchestrator.get_execution_status(event['pipeline_id'])
    
    elif action == 'stop_execution':
        return orchestrator.stop_execution(
            pipeline_id=event['pipeline_id'],
            reason=event.get('reason', 'User requested')
        )
    
    elif action == 'list_executions':
        return {
            "executions": orchestrator.list_executions(
                status_filter=event.get('status_filter'),
                max_results=event.get('max_results', 10)
            )
        }
    
    elif action == 'get_logs':
        return {
            "logs": orchestrator.get_execution_logs(event['pipeline_id'])
        }
    
    else:
        return {
            "status": "error",
            "message": f"Unknown action: {action}"
        }
