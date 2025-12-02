"""
ADPA Lambda Function Handler
Integrates Adariprasad's sophisticated agent with Girik's AWS infrastructure
"""

import json
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

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
        
        try:return
        
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


# Global orchestrator instance
orchestrator = ADPALambdaOrchestrator()


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler for ADPA
    Routes requests to appropriate Adariprasad components
    """
    
    logger.info(f"ADPA Lambda invoked with event: {json.dumps(event, default=str)}")
    
    try:
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
            return orchestrator.run_pipeline(event)
            
        elif action == 'get_status':
            return orchestrator.get_pipeline_status(event)
            
        elif action == 'health_check':
            return orchestrator.health_check()
            
        else:
            return {
                'status': 'error',
                'error': f'Unknown action: {action}',
                'supported_actions': ['run_pipeline', 'get_status', 'health_check', 'diagnostic'],
                'timestamp': datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        error_msg = f"Lambda handler error: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': error_msg,
                'timestamp': datetime.utcnow().isoformat()
            })
        }


# For testing locally
if __name__ == "__main__":
    # Test health check
    test_event = {"action": "health_check"}
    result = lambda_handler(test_event, None)
    print("Health check result:", json.dumps(result, indent=2))