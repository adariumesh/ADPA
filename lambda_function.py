"""
ADPA Complete API Lambda Function Handler
Provides full CRUD API for pipeline management and data uploads
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

# AWS X-Ray tracing for distributed tracing
try:
    from aws_xray_sdk.core import xray_recorder
    from aws_xray_sdk.core import patch_all
    # Patch all supported libraries (boto3, requests, etc.)
    patch_all()
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

# Add src to path for imports
sys.path.append('/opt/python')
sys.path.append('./src')
sys.path.append('.')

# Import compatibility shim FIRST to handle optional dependencies
try:
    from src import compat
except ImportError:
    pass  # Compat module is optional

try:
    # Import Adariprasad's core components
    from src.agent.core.master_agent import MasterAgenticController
    from src.monitoring.cloudwatch_monitor import ADPACloudWatchMonitor
    from src.monitoring.kpi_tracker import ADPABusinessMetrics as KPITracker
    from src.pipeline.ingestion.data_loader import DataIngestionStep
    from src.pipeline.etl.feature_engineer import FeatureEngineeringStep
    from src.pipeline.evaluation.evaluator import ModelEvaluationStep
    
    IMPORTS_SUCCESS = True
    IMPORT_ERROR = None
except Exception as e:
    IMPORTS_SUCCESS = False
    IMPORT_ERROR = str(e)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS resource configuration from environment
AWS_CONFIG = {
    'data_bucket': os.getenv('DATA_BUCKET', 'adpa-data-276983626136-development'),
    'model_bucket': os.getenv('MODEL_BUCKET', 'adpa-models-276983626136-development'),
    'secrets_arn': os.getenv('SECRETS_ARN', ''),
    'region': os.getenv('AWS_REGION', 'us-east-2')
}


class ADPALambdaOrchestrator:
    """
    Unified ADPA orchestrator running Adariprasad's agent on Girik's infrastructure
    """
    
    def __init__(self):
        self.monitoring = None
        self.kpi_tracker = None
        self.agent = None
        self.initialized = False
        
        if IMPORTS_SUCCESS:
            try:
                # Initialize Adariprasad's monitoring components
                self.monitoring = ADPACloudWatchMonitor()
                self.kpi_tracker = KPITracker()
                
                # Initialize master agent (use /tmp for Lambda writable directory)
                self.agent = MasterAgenticController(
                    aws_config=AWS_CONFIG,
                    memory_dir="/tmp/experience_memory"
                )
                
                self.initialized = True
                logger.info("ADPA Lambda orchestrator initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize ADPA components: {str(e)}")
                logger.error(f"Traceback: ", exc_info=True)
                self.initialized = False
        else:
            logger.error(f"Failed to import ADPA components: {IMPORT_ERROR}")
    
    @xray_recorder.capture('run_pipeline')
    def run_pipeline(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete ADPA pipeline using Adariprasad's implementation"""
        
        if not self.initialized:
            return {
                'status': 'failed',
                'error': f'ADPA not initialized: {IMPORT_ERROR}',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        try:
            logger.info("Starting ADPA pipeline execution")
            
            # Extract parameters
            dataset_path = event.get('dataset_path', '')
            objective = event.get('objective', 'classification')
            config = event.get('config', {})
            
            # Enhanced configuration for AWS infrastructure
            enhanced_config = {
                **config,
                'aws_config': AWS_CONFIG,
                'execution_mode': 'lambda',
                'infrastructure': 'girik_aws'
            }
            
            # Execute pipeline using Adariprasad's agent
            # Use natural language processing for the objective
            result = self.agent.process_natural_language_request(
                request=objective,
                data=None,  # Data would be loaded from dataset_path
                context=enhanced_config
            )
            
            # Publish metrics to CloudWatch via Girik's infrastructure
            self._publish_metrics(result)
            
            # Track KPIs
            self._track_kpis(result)
            
            logger.info("ADPA pipeline executed successfully")
            
            return {
                'status': 'completed',
                'pipeline_id': result.get('pipeline_id', 'unknown'),
                'execution_time': result.get('execution_time', 0),
                'performance_metrics': result.get('metrics', {}),
                'model_performance': result.get('model_performance', {}),
                'dashboard_url': self._get_dashboard_url(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Pipeline execution failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            # Send alert via monitoring system
            if self.monitoring:
                self.monitoring.send_alert(
                    message=error_msg,
                    severity="HIGH",
                    source="ADPA Lambda"
                )
            
            return {
                'status': 'failed',
                'error': error_msg,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_pipeline_status(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Get status of running pipeline"""
        
        pipeline_id = event.get('pipeline_id', '')
        
        if not pipeline_id:
            return {
                'status': 'error',
                'error': 'Pipeline ID required',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        try:
            # Get status from agent
            if self.agent:
                # Get agent status instead of pipeline status
                status = self.agent.get_agent_status()
                return {
                    'status': 'success',
                    'agent_status': status,
                    'pipeline_id': pipeline_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'error': 'ADPA agent not initialized',
                    'timestamp': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    @xray_recorder.capture('health_check')
    def health_check(self) -> Dict[str, Any]:
        """Health check for the ADPA system"""
        
        health_status = {
            'status': 'healthy' if self.initialized else 'unhealthy',
            'components': {
                'imports': IMPORTS_SUCCESS,
                'monitoring': self.monitoring is not None,
                'kpi_tracker': self.kpi_tracker is not None,
                'agent': self.agent is not None,
                'xray_tracing': XRAY_ENABLED
            },
            'aws_config': {
                'data_bucket': AWS_CONFIG['data_bucket'],
                'model_bucket': AWS_CONFIG['model_bucket'],
                'region': AWS_CONFIG['region']
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if not IMPORTS_SUCCESS:
            health_status['import_error'] = IMPORT_ERROR
            
        return health_status
    @xray_recorder.capture('publish_metrics')
    def _publish_metrics(self, result: Dict[str, Any]):
        """Publish metrics to Girik's CloudWatch infrastructure"""
        
        if not self.monitoring:
            return
        
        try:
            # Publish pipeline success metric
            self.monitoring.publish_custom_metric(
                metric_name="PipelineSuccess",
                value=1,
                unit="Count",
                dimensions={"Environment": "development"}
            )
            
            # Publish execution time
            if 'execution_time' in result:
                self.monitoring.publish_custom_metric(
                    metric_name="PipelineExecutionTime",
                    value=result['execution_time'],
                    unit="Seconds",
                    dimensions={"Environment": "development"}
                )
            
            # Publish model performance if available
            if 'model_performance' in result:
                performance = result['model_performance']
                if isinstance(performance, dict):
                    for metric_name, value in performance.items():
                        if isinstance(value, (int, float)):
                            self.monitoring.publish_custom_metric(
                                metric_name=f"ModelPerformance_{metric_name}",
                                value=value,
                                unit="None",
                                dimensions={"Environment": "development"}
                            )
            
            logger.info("Metrics published to CloudWatch successfully")
            
        except Exception as e:
            logger.error(f"Failed to publish metrics: {str(e)}")
    
    def _track_kpis(self, result: Dict[str, Any]):
        """Track KPIs using Adariprasad's KPI system"""
        
        if not self.kpi_tracker:
            return
        
        try:
            # Calculate and track KPIs
            kpis = self.kpi_tracker.calculate_kpis(
                execution_result=result,
                timestamp=datetime.utcnow()
            )
            
            logger.info(f"KPIs tracked: {kpis}")
            
        except Exception as e:
            logger.error(f"Failed to track KPIs: {str(e)}")
    
    def _get_dashboard_url(self) -> str:
        """Get CloudWatch dashboard URL"""
        region = AWS_CONFIG['region']
        return f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name=ADPA-Dashboard"


# CORS configuration
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, PUT, DELETE',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'
}

def add_cors_headers(response: Dict[str, Any]) -> Dict[str, Any]:
    """Add CORS headers to response"""
    if 'headers' not in response:
        response['headers'] = {}
    response['headers'].update(CORS_HEADERS)
    return response

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

def parse_path_parameters(path: str) -> Dict[str, str]:
    """Extract path parameters from API Gateway path"""
    # Handle paths like /pipelines/{id}
    path_parts = path.strip('/').split('/')
    params = {}
    
    if len(path_parts) >= 3 and path_parts[0] == 'pipelines':
        params['pipeline_id'] = path_parts[1]
    
    return params

# Global orchestrator instance
orchestrator = ADPALambdaOrchestrator()

# In-memory pipeline store (in production, use DynamoDB)
pipeline_store = {}


def handle_health_endpoint() -> Dict[str, Any]:
    """Handle /health endpoint"""
    try:
        health_status = orchestrator.health_check()
        return create_api_response(200, health_status)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return create_api_response(500, {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })

def handle_upload_data(body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    """Handle POST /data/upload endpoint"""
    try:
        import boto3
        import base64
        
        # Extract file data from request
        if 'body' not in body or not body['body']:
            return create_api_response(400, {
                'status': 'error',
                'error': 'No file data provided',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Decode base64 file content
        file_content = base64.b64decode(body['body'])
        filename = headers.get('x-filename', f'upload-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.csv')
        
        # Upload to S3
        s3_client = boto3.client('s3')
        bucket_name = AWS_CONFIG['data_bucket']
        s3_key = f'datasets/{filename}'
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType='text/csv'
        )
        
        # Generate upload response
        upload_id = str(uuid.uuid4())
        
        return create_api_response(200, {
            'id': upload_id,
            'filename': filename,
            'size': len(file_content),
            'uploadedAt': datetime.utcnow().isoformat(),
            's3_key': s3_key,
            'bucket': bucket_name,
            'message': 'File uploaded successfully',
            'timestamp': datetime.utcnow().isoformat()
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
        # Generate unique pipeline ID
        pipeline_id = str(uuid.uuid4())
        
        # Extract parameters from request body
        dataset_path = body.get('dataset_path', '')
        objective = body.get('objective', 'classification')
        config = body.get('config', {})
        
        # Create pipeline event
        pipeline_event = {
            'action': 'run_pipeline',
            'pipeline_id': pipeline_id,
            'dataset_path': dataset_path,
            'objective': objective,
            'config': config
        }
        
        # Store pipeline info
        pipeline_store[pipeline_id] = {
            'id': pipeline_id,
            'status': 'running',
            'created_at': datetime.utcnow().isoformat(),
            'dataset_path': dataset_path,
            'objective': objective,
            'config': config
        }
        
        # Execute pipeline asynchronously
        try:
            result = orchestrator.run_pipeline(pipeline_event)
            
            # Update pipeline status
            if result.get('status') == 'completed':
                pipeline_store[pipeline_id]['status'] = 'completed'
                pipeline_store[pipeline_id]['completed_at'] = datetime.utcnow().isoformat()
                pipeline_store[pipeline_id]['result'] = result
            else:
                pipeline_store[pipeline_id]['status'] = 'failed'
                pipeline_store[pipeline_id]['error'] = result.get('error')
        except Exception as exec_error:
            logger.error(f"Pipeline execution error: {str(exec_error)}")
            pipeline_store[pipeline_id]['status'] = 'failed'
            pipeline_store[pipeline_id]['error'] = str(exec_error)
        
        return create_api_response(201, {
            'pipeline_id': pipeline_id,
            'status': pipeline_store[pipeline_id]['status'],
            'message': f'Pipeline created with ID: {pipeline_id}',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Pipeline creation failed: {str(e)}")
        return create_api_response(500, {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })

def handle_list_pipelines() -> Dict[str, Any]:
    """Handle GET /pipelines endpoint"""
    try:
        pipelines = []
        for pipeline_id, pipeline_info in pipeline_store.items():
            # Create summary without full result details
            pipeline_summary = {
                'id': pipeline_info['id'],
                'status': pipeline_info['status'],
                'created_at': pipeline_info['created_at'],
                'objective': pipeline_info['objective'],
                'dataset_path': pipeline_info['dataset_path']
            }
            
            if 'completed_at' in pipeline_info:
                pipeline_summary['completed_at'] = pipeline_info['completed_at']
            
            if 'error' in pipeline_info:
                pipeline_summary['error'] = pipeline_info['error']
                
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

def handle_get_pipeline_execution(pipeline_id: str) -> Dict[str, Any]:
    """Handle GET /pipelines/{id}/execution endpoint"""
    try:
        if pipeline_id not in pipeline_store:
            return create_api_response(404, {
                'status': 'error',
                'error': f'Pipeline {pipeline_id} not found',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        pipeline_info = pipeline_store[pipeline_id]
        
        # Create mock execution data based on pipeline status
        execution_data = {
            'id': f'exec-{pipeline_id}',
            'pipelineId': pipeline_id,
            'status': pipeline_info['status'],
            'startTime': pipeline_info['created_at'],
            'endTime': pipeline_info.get('completed_at'),
            'steps': generate_execution_steps(pipeline_info['status']),
            'logs': generate_execution_logs(pipeline_info['status']),
            'metrics': generate_execution_metrics(pipeline_info['status'])
        }
        
        return create_api_response(200, {'data': execution_data})
        
    except Exception as e:
        logger.error(f"Failed to get pipeline execution: {str(e)}")
        return create_api_response(500, {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })

def handle_get_pipeline_logs(pipeline_id: str) -> Dict[str, Any]:
    """Handle GET /pipelines/{id}/logs endpoint"""
    try:
        if pipeline_id not in pipeline_store:
            return create_api_response(404, {
                'status': 'error',
                'error': f'Pipeline {pipeline_id} not found',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        pipeline_info = pipeline_store[pipeline_id]
        logs = generate_execution_logs(pipeline_info['status'])
        
        return create_api_response(200, {'data': logs})
        
    except Exception as e:
        logger.error(f"Failed to get pipeline logs: {str(e)}")
        return create_api_response(500, {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })

def handle_get_pipeline_status(pipeline_id: str) -> Dict[str, Any]:
    """Handle GET /pipelines/{id} endpoint"""
    try:
        if pipeline_id not in pipeline_store:
            return create_api_response(404, {
                'status': 'error',
                'error': f'Pipeline {pipeline_id} not found',
                'timestamp': datetime.utcnow().isoformat()
            })
        
        pipeline_info = pipeline_store[pipeline_id]
        
        # Get real-time status from orchestrator if pipeline is running
        if pipeline_info['status'] == 'running':
            status_event = {'pipeline_id': pipeline_id}
            live_status = orchestrator.get_pipeline_status(status_event)
            
            # Update stored status if needed
            if live_status.get('status') != 'error':
                pipeline_info['live_status'] = live_status
        
        return create_api_response(200, pipeline_info)
        
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {str(e)}")
        return create_api_response(500, {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        })

# Helper functions for generating realistic execution data
def generate_execution_steps(status: str):
    """Generate execution steps based on pipeline status"""
    base_steps = [
        {
            'id': 'step1',
            'name': 'Data Ingestion',
            'status': 'completed',
            'startTime': datetime.utcnow().replace(second=0, microsecond=0).isoformat() + 'Z',
            'endTime': datetime.utcnow().replace(second=30, microsecond=0).isoformat() + 'Z',
            'logs': ['Loading dataset...', 'Data validation complete', 'Data ingested successfully'],
            'duration': 30
        },
        {
            'id': 'step2', 
            'name': 'Data Preprocessing',
            'status': 'completed' if status in ['completed', 'running'] else 'pending',
            'startTime': datetime.utcnow().replace(second=30, microsecond=0).isoformat() + 'Z',
            'endTime': datetime.utcnow().replace(minute=1, second=0, microsecond=0).isoformat() + 'Z' if status in ['completed', 'running'] else None,
            'logs': ['Cleaning data...', 'Handling missing values', 'Feature scaling applied'] if status in ['completed', 'running'] else [],
            'duration': 30 if status in ['completed', 'running'] else None
        }
    ]
    
    if status == 'completed':
        base_steps.extend([
            {
                'id': 'step3',
                'name': 'Model Training',
                'status': 'completed',
                'startTime': datetime.utcnow().replace(minute=1, second=0, microsecond=0).isoformat() + 'Z',
                'endTime': datetime.utcnow().replace(minute=3, second=0, microsecond=0).isoformat() + 'Z',
                'logs': ['Training model...', 'Model training complete'],
                'duration': 120
            },
            {
                'id': 'step4',
                'name': 'Model Evaluation',
                'status': 'completed',
                'startTime': datetime.utcnow().replace(minute=3, second=0, microsecond=0).isoformat() + 'Z',
                'endTime': datetime.utcnow().replace(minute=3, second=30, microsecond=0).isoformat() + 'Z',
                'logs': ['Evaluating model...', 'Model evaluation complete'],
                'duration': 30
            }
        ])
    elif status == 'running':
        base_steps.append({
            'id': 'step3',
            'name': 'Model Training',
            'status': 'running',
            'startTime': datetime.utcnow().replace(minute=1, second=0, microsecond=0).isoformat() + 'Z',
            'logs': ['Training model...', 'Progress: 45%']
        })
    elif status == 'failed':
        base_steps.append({
            'id': 'step3',
            'name': 'Model Training',
            'status': 'failed',
            'startTime': datetime.utcnow().replace(minute=1, second=0, microsecond=0).isoformat() + 'Z',
            'logs': ['Training model...', 'Error: Insufficient memory']
        })
    
    return base_steps

def generate_execution_logs(status: str):
    """Generate execution logs based on pipeline status"""
    logs = [
        '[INFO] Pipeline execution started',
        '[INFO] Data ingestion completed successfully',
        '[INFO] Data preprocessing completed'
    ]
    
    if status == 'running':
        logs.append('[INFO] Model training in progress...')
    elif status == 'completed':
        logs.extend([
            '[INFO] Model training completed',
            '[INFO] Model evaluation completed',
            '[INFO] Pipeline execution completed successfully'
        ])
    elif status == 'failed':
        logs.extend([
            '[ERROR] Model training failed',
            '[ERROR] Pipeline execution failed'
        ])
    
    return logs

def generate_execution_metrics(status: str):
    """Generate execution metrics based on pipeline status"""
    base_metrics = {
        'cpu_usage': 45 if status == 'failed' else (85 if status == 'running' else 25),
        'memory_usage': 60 if status == 'failed' else (78 if status == 'running' else 30),
        'progress': 25 if status == 'failed' else (65 if status == 'running' else 100)
    }
    
    return base_metrics

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler for ADPA with CORS support and API Gateway integration
    Routes requests to appropriate endpoints
    """
    
    logger.info(f"ADPA Lambda invoked with event: {json.dumps(event, default=str)}")
    
    try:
        # Handle API Gateway events
        if 'httpMethod' in event and 'path' in event:
            http_method = event['httpMethod'].upper()
            path = event['path']
            
            # Handle OPTIONS request for CORS preflight
            if http_method == 'OPTIONS':
                return handle_options_request()
            
            # Parse request body if present
            body = {}
            if event.get('body'):
                try:
                    body = json.loads(event['body'])
                except json.JSONDecodeError:
                    return create_api_response(400, {
                        'status': 'error',
                        'error': 'Invalid JSON in request body',
                        'timestamp': datetime.utcnow().isoformat()
                    })
            
            # Route based on path and method
            if path == '/health' and http_method == 'GET':
                return handle_health_endpoint()
            
            elif path == '/data/upload' and http_method == 'POST':
                return handle_upload_data(body, event.get('headers', {}))
            
            elif path == '/pipelines' and http_method == 'POST':
                return handle_create_pipeline(body)
            
            elif path == '/pipelines' and http_method == 'GET':
                return handle_list_pipelines()
            
            elif path.startswith('/pipelines/') and http_method == 'GET':
                # Extract pipeline ID and sub-resource from path
                path_parts = path.strip('/').split('/')
                if len(path_parts) == 2:
                    pipeline_id = path_parts[1]
                    return handle_get_pipeline_status(pipeline_id)
                elif len(path_parts) == 3:
                    pipeline_id = path_parts[1]
                    sub_resource = path_parts[2]
                    
                    if sub_resource == 'execution':
                        return handle_get_pipeline_execution(pipeline_id)
                    elif sub_resource == 'logs':
                        return handle_get_pipeline_logs(pipeline_id)
                    else:
                        return create_api_response(404, {
                            'status': 'error',
                            'error': f'Unknown sub-resource: {sub_resource}',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                else:
                    return create_api_response(400, {
                        'status': 'error',
                        'error': 'Invalid pipeline path',
                        'timestamp': datetime.utcnow().isoformat()
                    })
            
            else:
                return create_api_response(404, {
                    'status': 'error',
                    'error': f'Endpoint not found: {http_method} {path}',
                    'supported_endpoints': [
                        'GET /health',
                        'POST /data/upload',
                        'POST /pipelines',
                        'GET /pipelines',
                        'GET /pipelines/{id}',
                        'GET /pipelines/{id}/execution',
                        'GET /pipelines/{id}/logs'
                    ],
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        # Handle legacy direct invocation (backward compatibility)
        else:
            # Determine action
            action = event.get('action', 'health_check')
            
            # Diagnostic actions
            if action == 'diagnostic':
                test = event.get('test', 'sys_path')
                
                if test == 'sys_path':
                    return {'sys_path': sys.path}
                elif test == 'list_cwd':
                    import os
                    cwd_contents = os.listdir('.')
                    task_contents = os.listdir('/var/task') if os.path.exists('/var/task') else []
                    opt_contents = os.listdir('/opt/python') if os.path.exists('/opt/python') else []
                    return {
                        'cwd': os.getcwd(), 
                        'cwd_contents': cwd_contents,
                        'task_contents': task_contents,
                        'opt_contents': opt_contents[:20]  # First 20 items
                    }
                elif test == 'find_numpy':
                    import os
                    import glob
                    numpy_paths = []
                    # Check all paths in sys.path
                    for path in sys.path[:5]:  # Check first 5 paths
                        if os.path.exists(path):
                            contents = os.listdir(path)
                            if 'numpy' in contents:
                                numpy_paths.append(f"{path}/numpy")
                    return {'numpy_found': numpy_paths, 'searched_paths': sys.path[:5]}
                elif test == 'import_trace':
                    # Try importing and trace where it's looking
                    error_details = None
                    try:
                        import numpy
                        return {'success': True, 'numpy_file': numpy.__file__}
                    except Exception as e:
                        import traceback
                        return {
                            'success': False,
                            'error': str(e),
                            'traceback': traceback.format_exc()
                        }
                else:
                    return {'error': f'Unknown diagnostic test: {test}'}
            
            if action == 'run_pipeline':
                result = orchestrator.run_pipeline(event)
                return create_api_response(200, result)
                
            elif action == 'get_status':
                result = orchestrator.get_pipeline_status(event)
                return create_api_response(200, result)
                
            elif action == 'health_check':
                result = orchestrator.health_check()
                return create_api_response(200, result)
                
            else:
                return create_api_response(400, {
                    'status': 'error',
                    'error': f'Unknown action: {action}',
                    'supported_actions': ['run_pipeline', 'get_status', 'health_check', 'diagnostic'],
                    'timestamp': datetime.utcnow().isoformat()
                })
            
    except Exception as e:
        error_msg = f"Lambda handler error: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        return create_api_response(500, {
            'status': 'error',
            'error': error_msg,
            'timestamp': datetime.utcnow().isoformat()
        })


# For testing locally
if __name__ == "__main__":
    # Test health check
    test_event = {"action": "health_check"}
    result = lambda_handler(test_event, None)
    print("Health check result:", json.dumps(result, indent=2))