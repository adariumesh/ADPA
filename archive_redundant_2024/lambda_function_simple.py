"""
ADPA Simplified API Lambda Function Handler
Provides API endpoints without heavy ML dependencies
"""

import json
import logging
import os
import sys
import traceback
import uuid
import base64
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import urllib.parse
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS Account Configuration - Single source of truth
AWS_ACCOUNT_ID = "083308938449"
AWS_REGION_DEFAULT = "us-east-2"
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# AWS resource configuration from environment with consistent defaults
AWS_CONFIG = {
    'data_bucket': os.getenv('DATA_BUCKET', f'adpa-data-{AWS_ACCOUNT_ID}-{ENVIRONMENT}'),
    'model_bucket': os.getenv('MODEL_BUCKET', f'adpa-models-{AWS_ACCOUNT_ID}-{ENVIRONMENT}'),
    'region': os.getenv('AWS_REGION', AWS_REGION_DEFAULT),
    'account_id': AWS_ACCOUNT_ID
}

# CORS configuration
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, PUT, DELETE',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token, x-filename'
}

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=AWS_CONFIG['region'])
dynamodb = boto3.resource('dynamodb', region_name=AWS_CONFIG['region'])

# In-memory pipeline store (simulating DynamoDB)
pipeline_store = {}


def create_api_response(status_code: int, body: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create standardized API Gateway response with CORS"""
    response = {
        'statusCode': status_code,
        'headers': CORS_HEADERS.copy(),
        'body': json.dumps(body, default=str)
    }
    if headers:
        response['headers'].update(headers)
    return response


def handle_options_request() -> Dict[str, Any]:
    """Handle OPTIONS preflight requests for CORS"""
    return create_api_response(200, {'message': 'CORS preflight successful'})


def handle_health_endpoint() -> Dict[str, Any]:
    """Handle /health endpoint"""
    health_status = {
        'status': 'healthy',
        'components': {
            'api': True,
            's3_access': check_s3_access(),
            'lambda': True
        },
        'aws_config': {
            'data_bucket': AWS_CONFIG['data_bucket'],
            'model_bucket': AWS_CONFIG['model_bucket'],
            'region': AWS_CONFIG['region']
        },
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.0.0'
    }
    return create_api_response(200, health_status)


def check_s3_access() -> bool:
    """Check if we can access S3 buckets"""
    try:
        s3_client.head_bucket(Bucket=AWS_CONFIG['data_bucket'])
        return True
    except Exception:
        return False


def handle_upload_data(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /data/upload endpoint"""
    try:
        body = event.get('body', '')
        headers = event.get('headers', {})
        is_base64 = event.get('isBase64Encoded', False)
        
        if not body:
            return create_api_response(400, {
                'status': 'error',
                'error': 'No file data provided',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Decode if base64 encoded
        if is_base64:
            file_content = base64.b64decode(body)
        else:
            file_content = body.encode() if isinstance(body, str) else body
        
        # Get filename from headers or generate one
        filename = headers.get('x-filename') or headers.get('X-Filename') or f'upload-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.csv'
        
        # Upload to S3
        s3_key = f'datasets/{filename}'
        s3_client.put_object(
            Bucket=AWS_CONFIG['data_bucket'],
            Key=s3_key,
            Body=file_content,
            ContentType='text/csv'
        )
        
        upload_id = str(uuid.uuid4())
        
        return create_api_response(200, {
            'id': upload_id,
            'filename': filename,
            'size': len(file_content),
            'uploadedAt': datetime.utcnow().isoformat(),
            's3_path': f"s3://{AWS_CONFIG['data_bucket']}/{s3_key}",
            'message': 'File uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        return create_api_response(500, {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })


def handle_create_pipeline(body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /pipelines endpoint"""
    try:
        pipeline_id = str(uuid.uuid4())
        
        dataset_path = body.get('dataset_path', '')
        objective = body.get('objective', 'Predict target variable')
        config = body.get('config', {})
        
        # Store pipeline
        pipeline_store[pipeline_id] = {
            'id': pipeline_id,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'dataset_path': dataset_path,
            'objective': objective,
            'config': config,
            'steps': [],
            'result': None
        }
        
        # Simulate pipeline execution (in production, this would trigger Step Functions)
        simulate_pipeline_execution(pipeline_id)
        
        return create_api_response(201, {
            'pipeline_id': pipeline_id,
            'status': pipeline_store[pipeline_id]['status'],
            'message': f'Pipeline created successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Pipeline creation failed: {str(e)}")
        return create_api_response(500, {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })


def simulate_pipeline_execution(pipeline_id: str):
    """Simulate pipeline execution with realistic steps"""
    pipeline = pipeline_store[pipeline_id]
    
    # Update status to running
    pipeline['status'] = 'running'
    pipeline['started_at'] = datetime.utcnow().isoformat()
    
    # Add execution steps
    pipeline['steps'] = [
        {'name': 'Data Ingestion', 'status': 'completed', 'duration': 2.5},
        {'name': 'Data Validation', 'status': 'completed', 'duration': 1.2},
        {'name': 'Feature Engineering', 'status': 'completed', 'duration': 5.8},
        {'name': 'Model Training', 'status': 'completed', 'duration': 45.3},
        {'name': 'Model Evaluation', 'status': 'completed', 'duration': 3.1}
    ]
    
    # Mark as completed
    pipeline['status'] = 'completed'
    pipeline['completed_at'] = datetime.utcnow().isoformat()
    pipeline['updated_at'] = datetime.utcnow().isoformat()
    
    # Add mock results
    pipeline['result'] = {
        'model': 'RandomForestRegressor',
        'performance_metrics': {
            'r2_score': 0.9245,
            'mae': 523.45,
            'rmse': 867.23,
            'mape': 3.21
        },
        'feature_importance': {
            'price': 0.35,
            'quantity': 0.28,
            'category': 0.18,
            'day_of_week': 0.12,
            'month': 0.07
        },
        'training_samples': 2920,
        'test_samples': 730,
        'model_path': f"s3://{AWS_CONFIG['model_bucket']}/models/{pipeline_id}/model.pkl"
    }


def handle_list_pipelines() -> Dict[str, Any]:
    """Handle GET /pipelines endpoint"""
    try:
        pipelines = []
        for pipeline_id, pipeline_info in pipeline_store.items():
            pipeline_summary = {
                'id': pipeline_info['id'],
                'status': pipeline_info['status'],
                'created_at': pipeline_info['created_at'],
                'updated_at': pipeline_info.get('updated_at', pipeline_info['created_at']),
                'objective': pipeline_info['objective'],
                'dataset_path': pipeline_info['dataset_path'],
                'config': pipeline_info.get('config', {})
            }
            
            if 'result' in pipeline_info and pipeline_info['result']:
                pipeline_summary['result'] = pipeline_info['result']
            
            pipelines.append(pipeline_summary)
        
        return create_api_response(200, {
            'pipelines': pipelines,
            'count': len(pipelines),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to list pipelines: {str(e)}")
        return create_api_response(500, {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })


def handle_get_pipeline(pipeline_id: str) -> Dict[str, Any]:
    """Handle GET /pipelines/{id} endpoint"""
    try:
        if pipeline_id not in pipeline_store:
            return create_api_response(404, {
                'status': 'error',
                'error': f'Pipeline {pipeline_id} not found',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        pipeline_info = pipeline_store[pipeline_id]
        return create_api_response(200, {'data': pipeline_info})
        
    except Exception as e:
        logger.error(f"Failed to get pipeline: {str(e)}")
        return create_api_response(500, {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })


def handle_get_pipeline_execution(pipeline_id: str) -> Dict[str, Any]:
    """Handle GET /pipelines/{id}/execution endpoint"""
    try:
        if pipeline_id not in pipeline_store:
            return create_api_response(404, {
                'status': 'error',
                'error': f'Pipeline {pipeline_id} not found'
            })
        
        pipeline = pipeline_store[pipeline_id]
        
        execution_data = {
            'id': f'exec-{pipeline_id}',
            'pipelineId': pipeline_id,
            'status': pipeline['status'],
            'startTime': pipeline.get('started_at', pipeline['created_at']),
            'endTime': pipeline.get('completed_at'),
            'steps': pipeline.get('steps', []),
            'logs': generate_execution_logs(pipeline['status']),
            'metrics': {
                'cpu_usage': 35 if pipeline['status'] == 'completed' else 75,
                'memory_usage': 45 if pipeline['status'] == 'completed' else 68,
                'progress': 100 if pipeline['status'] == 'completed' else 65
            }
        }
        
        return create_api_response(200, {'data': execution_data})
        
    except Exception as e:
        logger.error(f"Failed to get pipeline execution: {str(e)}")
        return create_api_response(500, {
            'status': 'error',
            'error': str(e)
        })


def handle_get_pipeline_results(pipeline_id: str) -> Dict[str, Any]:
    """Handle GET /pipelines/{id}/results endpoint"""
    try:
        if pipeline_id not in pipeline_store:
            return create_api_response(404, {
                'status': 'error',
                'error': f'Pipeline {pipeline_id} not found'
            })
        
        pipeline = pipeline_store[pipeline_id]
        
        if pipeline['status'] != 'completed':
            return create_api_response(400, {
                'status': 'error',
                'error': 'Pipeline has not completed yet'
            })
        
        return create_api_response(200, {'data': pipeline.get('result', {})})
        
    except Exception as e:
        logger.error(f"Failed to get pipeline results: {str(e)}")
        return create_api_response(500, {
            'status': 'error',
            'error': str(e)
        })


def handle_get_pipeline_logs(pipeline_id: str) -> Dict[str, Any]:
    """Handle GET /pipelines/{id}/logs endpoint"""
    try:
        if pipeline_id not in pipeline_store:
            return create_api_response(404, {
                'status': 'error',
                'error': f'Pipeline {pipeline_id} not found'
            })
        
        pipeline = pipeline_store[pipeline_id]
        logs = generate_execution_logs(pipeline['status'])
        
        return create_api_response(200, {'data': logs})
        
    except Exception as e:
        logger.error(f"Failed to get pipeline logs: {str(e)}")
        return create_api_response(500, {
            'status': 'error',
            'error': str(e)
        })


def generate_execution_logs(status: str) -> List[str]:
    """Generate execution logs based on pipeline status"""
    base_time = datetime.utcnow().replace(microsecond=0)
    logs = [
        f'[{base_time.isoformat()}Z] [INFO] Pipeline execution started',
        f'[{base_time.isoformat()}Z] [INFO] Loading dataset...',
        f'[{base_time.isoformat()}Z] [INFO] Data validation passed: 3650 records',
        f'[{base_time.isoformat()}Z] [INFO] Feature engineering: created 12 features',
    ]
    
    if status == 'running':
        logs.append(f'[{base_time.isoformat()}Z] [INFO] Model training in progress... 45%')
    elif status == 'completed':
        logs.extend([
            f'[{base_time.isoformat()}Z] [INFO] Model training completed',
            f'[{base_time.isoformat()}Z] [INFO] Model: RandomForestRegressor',
            f'[{base_time.isoformat()}Z] [INFO] R² Score: 0.9245',
            f'[{base_time.isoformat()}Z] [INFO] MAE: $523.45',
            f'[{base_time.isoformat()}Z] [INFO] Pipeline completed successfully'
        ])
    elif status == 'failed':
        logs.extend([
            f'[{base_time.isoformat()}Z] [ERROR] Model training failed',
            f'[{base_time.isoformat()}Z] [ERROR] Pipeline execution failed'
        ])
    
    return logs


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Main Lambda handler for ADPA API"""
    
    logger.info(f"ADPA Lambda invoked: {json.dumps(event, default=str)[:500]}")
    
    try:
        # Handle API Gateway events
        if 'httpMethod' in event:
            http_method = event.get('httpMethod', '').upper()
            path = event.get('path', '')
            
            # Handle OPTIONS for CORS
            if http_method == 'OPTIONS':
                return handle_options_request()
            
            # Parse body
            body = {}
            if event.get('body'):
                try:
                    if event.get('isBase64Encoded'):
                        body = event  # Pass full event for binary data
                    else:
                        body = json.loads(event['body'])
                except (json.JSONDecodeError, TypeError):
                    body = {}
            
            # Route requests
            if path == '/health' and http_method == 'GET':
                return handle_health_endpoint()
            
            elif path == '/data/upload' and http_method == 'POST':
                return handle_upload_data(event)
            
            elif path == '/pipelines':
                if http_method == 'POST':
                    return handle_create_pipeline(body)
                elif http_method == 'GET':
                    return handle_list_pipelines()
            
            elif path.startswith('/pipelines/'):
                path_parts = path.strip('/').split('/')
                if len(path_parts) >= 2:
                    pipeline_id = path_parts[1]
                    
                    if len(path_parts) == 2 and http_method == 'GET':
                        return handle_get_pipeline(pipeline_id)
                    elif len(path_parts) == 3:
                        sub_resource = path_parts[2]
                        if sub_resource == 'execution':
                            return handle_get_pipeline_execution(pipeline_id)
                        elif sub_resource == 'results':
                            return handle_get_pipeline_results(pipeline_id)
                        elif sub_resource == 'logs':
                            return handle_get_pipeline_logs(pipeline_id)
            
            return create_api_response(404, {
                'status': 'error',
                'error': f'Endpoint not found: {http_method} {path}',
                'supported_endpoints': [
                    'GET /health',
                    'POST /data/upload',
                    'GET /pipelines',
                    'POST /pipelines',
                    'GET /pipelines/{id}',
                    'GET /pipelines/{id}/execution',
                    'GET /pipelines/{id}/results',
                    'GET /pipelines/{id}/logs'
                ]
            })
        
        # Handle direct invocation
        else:
            action = event.get('action', 'health_check')
            
            if action == 'health_check':
                return handle_health_endpoint()
            elif action == 'create_pipeline':
                return handle_create_pipeline(event)
            elif action == 'list_pipelines':
                return handle_list_pipelines()
            else:
                return create_api_response(400, {
                    'status': 'error',
                    'error': f'Unknown action: {action}'
                })
            
    except Exception as e:
        logger.error(f"Lambda error: {str(e)}\n{traceback.format_exc()}")
        return create_api_response(500, {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })


if __name__ == "__main__":
    # Test locally
    test_event = {"action": "health_check"}
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
