"""
API Gateway Lambda Handler for ADPA

This module handles all REST API requests from API Gateway
and routes them to appropriate ADPA components.
"""

import json
import boto3
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add src directory to path
sys.path.insert(0, '/var/task/src')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import centralized AWS configuration
try:
    from config.aws_config import (
        AWS_ACCOUNT_ID, AWS_REGION, MODEL_BUCKET,
        get_credentials_from_csv
    )
except ImportError:
    # Fallback values
    AWS_ACCOUNT_ID = "083308938449"
    AWS_REGION = "us-east-2"
    MODEL_BUCKET = f"adpa-models-{AWS_ACCOUNT_ID}-development"
    get_credentials_from_csv = None

from orchestration.step_function_handler import StepFunctionOrchestrator


class APIHandler:
    """Handle API Gateway requests"""
    
    def __init__(self):
        """Initialize API handler"""
        self.orchestrator = StepFunctionOrchestrator()
        self.model_bucket = MODEL_BUCKET
        
        # Try to load credentials from rootkey.csv
        try:
            if get_credentials_from_csv:
                creds = get_credentials_from_csv()
                if creds['access_key_id'] and creds['secret_access_key']:
                    self.s3 = boto3.client(
                        's3',
                        aws_access_key_id=creds['access_key_id'],
                        aws_secret_access_key=creds['secret_access_key']
                    )
                    self.cloudwatch_logs = boto3.client(
                        'logs', 
                        region_name=AWS_REGION,
                        aws_access_key_id=creds['access_key_id'],
                        aws_secret_access_key=creds['secret_access_key']
                    )
                else:
                    raise ValueError("No credentials in CSV")
            else:
                raise ValueError("Config module not available")
        except Exception:
            # Fallback to default credential chain
            self.s3 = boto3.client('s3')
            self.cloudwatch_logs = boto3.client('logs', region_name=AWS_REGION)
        
    def handle_request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route API Gateway request to appropriate handler
        
        Args:
            event: API Gateway event
            
        Returns:
            Dict containing status code, headers, and body
        """
        # Extract request details
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        path_parameters = event.get('pathParameters', {})
        query_parameters = event.get('queryStringParameters', {}) or {}
        body = event.get('body', '{}')
        
        # Parse body if present
        try:
            body_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return self._error_response(400, "Invalid JSON in request body")
        
        # Route to appropriate handler
        try:
            if path == '/health' and http_method == 'GET':
                return self._health_check()
            
            elif path == '/pipelines' and http_method == 'POST':
                return self._create_pipeline(body_data)
            
            elif path == '/pipelines' and http_method == 'GET':
                return self._list_pipelines(query_parameters)
            
            elif path.startswith('/pipelines/') and http_method == 'GET':
                pipeline_id = path_parameters.get('pipeline_id')
                if '/logs' in path:
                    return self._get_pipeline_logs(pipeline_id, query_parameters)
                else:
                    return self._get_pipeline_status(pipeline_id)
            
            elif path.endswith('/cancel') and http_method == 'POST':
                pipeline_id = path_parameters.get('pipeline_id')
                return self._cancel_pipeline(pipeline_id, body_data)
            
            elif path == '/models' and http_method == 'GET':
                return self._list_models()
            
            elif path.endswith('/predict') and http_method == 'POST':
                model_id = path_parameters.get('model_id')
                return self._predict(model_id, body_data)
            
            else:
                return self._error_response(404, f"Endpoint not found: {http_method} {path}")
                
        except Exception as e:
            return self._error_response(500, f"Internal server error: {str(e)}")
    
    def _health_check(self) -> Dict[str, Any]:
        """Health check endpoint"""
        return self._success_response({
            "status": "healthy",
            "components": {
                "api_gateway": True,
                "lambda": True,
                "step_functions": True
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def _create_pipeline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new ML pipeline"""
        # Validate required fields
        if 'objective' not in data or 'dataset_path' not in data:
            return self._error_response(400, "Missing required fields: objective, dataset_path")
        
        # Start pipeline via Step Functions
        result = self.orchestrator.start_pipeline(
            objective=data['objective'],
            dataset_path=data['dataset_path'],
            config=data.get('config', {})
        )
        
        if result['status'] == 'started':
            return self._success_response(result, status_code=201)
        else:
            return self._error_response(500, result.get('error', 'Failed to start pipeline'))
    
    def _list_pipelines(self, params: Dict[str, str]) -> Dict[str, Any]:
        """List recent pipelines"""
        status_filter = params.get('status', '').upper()
        limit = int(params.get('limit', '10'))
        
        # Map user-friendly status to Step Functions status
        status_map = {
            'RUNNING': 'RUNNING',
            'COMPLETED': 'SUCCEEDED',
            'FAILED': 'FAILED',
            'ALL': None
        }
        
        sf_status = status_map.get(status_filter)
        executions = self.orchestrator.list_executions(
            status_filter=sf_status,
            max_results=limit
        )
        
        return self._success_response({
            "pipelines": executions,
            "count": len(executions)
        })
    
    def _get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get detailed pipeline status"""
        if not pipeline_id:
            return self._error_response(400, "Missing pipeline_id")
        
        status = self.orchestrator.get_execution_status(pipeline_id)
        
        if status['status'] == 'NOT_FOUND':
            return self._error_response(404, f"Pipeline {pipeline_id} not found")
        
        return self._success_response(status)
    
    def _cancel_pipeline(self, pipeline_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel a running pipeline"""
        if not pipeline_id:
            return self._error_response(400, "Missing pipeline_id")
        
        reason = data.get('reason', 'User requested cancellation')
        result = self.orchestrator.stop_execution(pipeline_id, reason)
        
        if result['status'] == 'stopped':
            return self._success_response(result)
        else:
            return self._error_response(500, result.get('error', 'Failed to cancel pipeline'))
    
    def _get_pipeline_logs(self, pipeline_id: str, params: Dict[str, str]) -> Dict[str, Any]:
        """Get pipeline execution logs"""
        if not pipeline_id:
            return self._error_response(400, "Missing pipeline_id")
        
        logs = self.orchestrator.get_execution_logs(pipeline_id)
        
        return self._success_response({
            "pipeline_id": pipeline_id,
            "logs": logs
        })
    
    def _list_models(self) -> Dict[str, Any]:
        """List trained models from S3"""
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.model_bucket,
                Prefix='models/'
            )
            
            models = []
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.pkl') or obj['Key'].endswith('.joblib'):
                    models.append({
                        "model_id": obj['Key'].split('/')[-1].replace('.pkl', '').replace('.joblib', ''),
                        "s3_location": f"s3://{self.model_bucket}/{obj['Key']}",
                        "size_bytes": obj['Size'],
                        "last_modified": obj['LastModified'].isoformat()
                    })
            
            return self._success_response({
                "models": models,
                "count": len(models)
            })
            
        except Exception as e:
            return self._error_response(500, f"Failed to list models: {str(e)}")
    
    def _predict(self, model_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make predictions using a trained model"""
        # This would load the model from S3 and make predictions
        # For now, return placeholder
        return self._error_response(501, "Prediction endpoint not yet implemented")
    
    def _success_response(
        self,
        data: Dict[str, Any],
        status_code: int = 200
    ) -> Dict[str, Any]:
        """Create successful API response"""
        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, X-API-Key"
            },
            "body": json.dumps(data)
        }
    
    def _error_response(
        self,
        status_code: int,
        message: str
    ) -> Dict[str, Any]:
        """Create error API response"""
        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Error",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            })
        }


# Lambda handler
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for API Gateway requests
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        Dict containing HTTP response
    """
    handler = APIHandler()
    return handler.handle_request(event)
