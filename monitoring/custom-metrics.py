"""
ADPA Custom CloudWatch Metrics and Monitoring
Production-grade observability for autonomous ML pipelines
"""

import boto3
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import os

class ADPAMetrics:
    """Custom CloudWatch metrics for ADPA system monitoring"""
    
    def __init__(self, environment: str = 'prod'):
        self.cloudwatch = boto3.client('cloudwatch', region_name='us-east-2')
        self.environment = environment
        self.namespace = f'ADPA/{environment.upper()}'
        self.logger = logging.getLogger(__name__)
        
    def put_pipeline_metric(self, 
                           metric_name: str,
                           value: float,
                           unit: str = 'Count',
                           pipeline_id: str = None,
                           dimensions: Dict[str, str] = None) -> bool:
        """
        Send custom metrics to CloudWatch
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: CloudWatch unit (Count, Seconds, Bytes, etc.)
            pipeline_id: Optional pipeline ID for filtering
            dimensions: Additional dimensions
            
        Returns:
            bool: Success status
        """
        try:
            metric_dimensions = [
                {'Name': 'Environment', 'Value': self.environment},
            ]
            
            if pipeline_id:
                metric_dimensions.append({'Name': 'PipelineId', 'Value': pipeline_id})
                
            if dimensions:
                for key, value in dimensions.items():
                    metric_dimensions.append({'Name': key, 'Value': value})
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Value': value,
                        'Unit': unit,
                        'Timestamp': datetime.now(timezone.utc),
                        'Dimensions': metric_dimensions
                    }
                ]
            )
            
            self.logger.info(f"Metric sent: {metric_name}={value} {unit}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send metric {metric_name}: {str(e)}")
            return False
    
    def track_pipeline_duration(self, pipeline_id: str, duration_seconds: float):
        """Track pipeline execution duration"""
        self.put_pipeline_metric(
            'PipelineExecutionDuration',
            duration_seconds,
            'Seconds',
            pipeline_id
        )
    
    def track_pipeline_status(self, pipeline_id: str, status: str):
        """Track pipeline status changes"""
        status_map = {
            'created': 1,
            'running': 2, 
            'succeeded': 3,
            'failed': 4,
            'cancelled': 5
        }
        
        self.put_pipeline_metric(
            'PipelineStatusChange',
            status_map.get(status, 0),
            'Count',
            pipeline_id,
            {'Status': status}
        )
    
    def track_api_response_time(self, endpoint: str, response_time_ms: float):
        """Track API endpoint response times"""
        self.put_pipeline_metric(
            'APIResponseTime',
            response_time_ms,
            'Milliseconds',
            dimensions={'Endpoint': endpoint}
        )
    
    def track_data_processing_volume(self, pipeline_id: str, data_size_bytes: int):
        """Track volume of data processed"""
        self.put_pipeline_metric(
            'DataProcessingVolume',
            data_size_bytes,
            'Bytes',
            pipeline_id
        )
    
    def track_sagemaker_training_cost(self, pipeline_id: str, estimated_cost: float):
        """Track estimated SageMaker training costs"""
        self.put_pipeline_metric(
            'SageMakerTrainingCost',
            estimated_cost,
            'None',  # Dollar amount
            pipeline_id
        )
    
    def track_error_count(self, error_type: str, component: str):
        """Track error counts by type and component"""
        self.put_pipeline_metric(
            'ErrorCount',
            1,
            'Count',
            dimensions={
                'ErrorType': error_type,
                'Component': component
            }
        )
    
    def track_concurrent_executions(self, count: int):
        """Track number of concurrent pipeline executions"""
        self.put_pipeline_metric(
            'ConcurrentExecutions',
            count,
            'Count'
        )

class ADPAAlarms:
    """CloudWatch Alarms for ADPA system"""
    
    def __init__(self, environment: str = 'prod'):
        self.cloudwatch = boto3.client('cloudwatch', region_name='us-east-2')
        self.environment = environment
        self.namespace = f'ADPA/{environment.upper()}'
        self.sns_topic_arn = f'arn:aws:sns:us-east-2:083308938449:adpa-{environment}-alerts'
        
    def create_production_alarms(self):
        """Create comprehensive alarm set for production monitoring"""
        
        alarms = [
            # High error rate alarm
            {
                'AlarmName': f'ADPA-{self.environment}-HighErrorRate',
                'AlarmDescription': 'Pipeline failure rate exceeded threshold',
                'MetricName': 'ErrorCount',
                'Namespace': self.namespace,
                'Statistic': 'Sum',
                'Period': 300,  # 5 minutes
                'EvaluationPeriods': 2,
                'Threshold': 5.0,
                'ComparisonOperator': 'GreaterThanThreshold',
                'TreatMissingData': 'notBreaching'
            },
            
            # Long running pipelines
            {
                'AlarmName': f'ADPA-{self.environment}-LongRunningPipelines',
                'AlarmDescription': 'Pipeline execution time exceeded normal range',
                'MetricName': 'PipelineExecutionDuration',
                'Namespace': self.namespace,
                'Statistic': 'Average',
                'Period': 300,
                'EvaluationPeriods': 1,
                'Threshold': 1800.0,  # 30 minutes
                'ComparisonOperator': 'GreaterThanThreshold'
            },
            
            # High API latency
            {
                'AlarmName': f'ADPA-{self.environment}-HighAPILatency',
                'AlarmDescription': 'API response time degraded',
                'MetricName': 'APIResponseTime',
                'Namespace': self.namespace,
                'Statistic': 'Average',
                'Period': 300,
                'EvaluationPeriods': 2,
                'Threshold': 5000.0,  # 5 seconds
                'ComparisonOperator': 'GreaterThanThreshold'
            },
            
            # Too many concurrent executions
            {
                'AlarmName': f'ADPA-{self.environment}-HighConcurrency',
                'AlarmDescription': 'Too many concurrent pipeline executions',
                'MetricName': 'ConcurrentExecutions',
                'Namespace': self.namespace,
                'Statistic': 'Maximum',
                'Period': 60,
                'EvaluationPeriods': 1,
                'Threshold': 10.0,
                'ComparisonOperator': 'GreaterThanThreshold'
            },
            
            # Cost threshold alarm
            {
                'AlarmName': f'ADPA-{self.environment}-HighCosts',
                'AlarmDescription': 'SageMaker training costs exceeded budget',
                'MetricName': 'SageMakerTrainingCost',
                'Namespace': self.namespace,
                'Statistic': 'Sum',
                'Period': 3600,  # 1 hour
                'EvaluationPeriods': 1,
                'Threshold': 100.0,  # $100/hour
                'ComparisonOperator': 'GreaterThanThreshold'
            }
        ]
        
        for alarm_config in alarms:
            self.create_alarm(alarm_config)
    
    def create_alarm(self, config: Dict[str, Any]):
        """Create a CloudWatch alarm"""
        try:
            self.cloudwatch.put_metric_alarm(
                AlarmName=config['AlarmName'],
                ComparisonOperator=config['ComparisonOperator'],
                EvaluationPeriods=config['EvaluationPeriods'],
                MetricName=config['MetricName'],
                Namespace=config['Namespace'],
                Period=config['Period'],
                Statistic=config['Statistic'],
                Threshold=config['Threshold'],
                ActionsEnabled=True,
                AlarmActions=[self.sns_topic_arn],
                AlarmDescription=config['AlarmDescription'],
                TreatMissingData=config.get('TreatMissingData', 'missing'),
                Unit='None'
            )
            print(f"✅ Created alarm: {config['AlarmName']}")
            
        except Exception as e:
            print(f"❌ Failed to create alarm {config['AlarmName']}: {str(e)}")

class ADPADashboard:
    """CloudWatch Dashboard for ADPA system"""
    
    def __init__(self, environment: str = 'prod'):
        self.cloudwatch = boto3.client('cloudwatch', region_name='us-east-2')
        self.environment = environment
        self.namespace = f'ADPA/{environment.upper()}'
        self.dashboard_name = f'ADPA-{environment.upper()}-Dashboard'
    
    def create_dashboard(self):
        """Create comprehensive CloudWatch dashboard"""
        
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "PipelineExecutionDuration"],
                            [self.namespace, "APIResponseTime"],
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": "us-east-2",
                        "title": "Performance Metrics",
                        "yAxis": {
                            "left": {
                                "min": 0
                            }
                        }
                    }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "ErrorCount", "Component", "Lambda"],
                            [self.namespace, "ErrorCount", "Component", "StepFunctions"],
                            [self.namespace, "ErrorCount", "Component", "SageMaker"],
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": "us-east-2",
                        "title": "Error Rates by Component"
                    }
                },
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 8,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "ConcurrentExecutions"],
                        ],
                        "period": 300,
                        "stat": "Maximum",
                        "region": "us-east-2",
                        "title": "Concurrent Pipeline Executions"
                    }
                },
                {
                    "type": "metric",
                    "x": 8,
                    "y": 6,
                    "width": 8,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "SageMakerTrainingCost"],
                        ],
                        "period": 3600,
                        "stat": "Sum",
                        "region": "us-east-2",
                        "title": "Training Costs ($/hour)"
                    }
                },
                {
                    "type": "metric",
                    "x": 16,
                    "y": 6,
                    "width": 8,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "DataProcessingVolume"],
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": "us-east-2",
                        "title": "Data Processing Volume (Bytes)"
                    }
                },
                {
                    "type": "log",
                    "x": 0,
                    "y": 12,
                    "width": 24,
                    "height": 6,
                    "properties": {
                        "query": "SOURCE '/aws/lambda/adpa-prod-lambda-function'\n| fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 100",
                        "region": "us-east-2",
                        "title": "Recent Errors"
                    }
                }
            ]
        }
        
        try:
            self.cloudwatch.put_dashboard(
                DashboardName=self.dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            print(f"✅ Created dashboard: {self.dashboard_name}")
            return f"https://console.aws.amazon.com/cloudwatch/home?region=us-east-2#dashboards:name={self.dashboard_name}"
            
        except Exception as e:
            print(f"❌ Failed to create dashboard: {str(e)}")
            return None

# Enhanced Lambda function wrapper with metrics
def lambda_handler_with_metrics(original_handler):
    """Decorator to add automatic metrics to Lambda handlers"""
    
    def wrapper(event, context):
        start_time = time.time()
        metrics = ADPAMetrics(os.environ.get('ENVIRONMENT', 'prod'))
        
        try:
            # Track API endpoint if it's an API Gateway event
            if 'path' in event:
                endpoint = event['path']
                metrics.track_api_response_time(endpoint, 0)  # Will update with actual time
            
            # Execute original handler
            result = original_handler(event, context)
            
            # Track success metrics
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            if 'path' in event:
                metrics.track_api_response_time(event['path'], execution_time)
            
            return result
            
        except Exception as e:
            # Track error metrics
            error_type = type(e).__name__
            component = 'Lambda'
            metrics.track_error_count(error_type, component)
            raise
    
    return wrapper

if __name__ == "__main__":
    # Initialize monitoring for production environment
    environment = 'prod'
    
    print(f"🚀 Setting up ADPA monitoring for {environment} environment...")
    
    # Create custom metrics client
    metrics = ADPAMetrics(environment)
    
    # Create alarms
    alarms = ADPAAlarms(environment)
    alarms.create_production_alarms()
    
    # Create dashboard
    dashboard = ADPADashboard(environment)
    dashboard_url = dashboard.create_dashboard()
    
    if dashboard_url:
        print(f"📊 Dashboard available at: {dashboard_url}")
    
    # Test metrics
    print("🧪 Sending test metrics...")
    metrics.track_pipeline_duration("test-pipeline", 45.5)
    metrics.track_api_response_time("/health", 120.0)
    metrics.track_concurrent_executions(3)
    
    print("✅ Monitoring setup complete!")