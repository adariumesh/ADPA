"""
Unified ADPA Monitoring Integration
Connects Adariprasad's sophisticated monitoring with deployed AWS infrastructure
"""

import boto3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import os

# Import Adariprasad's monitoring components
from ..monitoring.cloudwatch_monitor import ADPACloudWatchMonitor
from ..monitoring.kpi_tracker import KPITracker
from ..monitoring.performance_analytics import PerformanceAnalytics
from ..monitoring.anomaly_detection import AnomalyDetectionSystem
from ..monitoring.alerting_system import AlertingSystem


class UnifiedADPAMonitoring:
    """
    Unified monitoring system that integrates Adariprasad's components
    with the deployed AWS infrastructure (Girik's setup)
    """
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.logger = logging.getLogger(__name__)
        
        # AWS clients
        self.cloudwatch = boto3.client('cloudwatch')
        self.logs = boto3.client('logs')
        
        # Adariprasad's monitoring components
        self.adpa_monitor = ADPACloudWatchMonitor()
        self.kpi_tracker = KPITracker()
        self.alerting = AlertingSystem()
        
        # Infrastructure information from deployed stack
        self.infrastructure = self._load_infrastructure_config()
        
        self.logger.info("Unified ADPA monitoring initialized")
    
    def _load_infrastructure_config(self) -> Dict[str, str]:
        """Load infrastructure configuration from CloudFormation stack"""
        
        try:
            cf_client = boto3.client('cloudformation')
            
            # Get stack outputs
            response = cf_client.describe_stacks(
                StackName=f'adpa-infrastructure-{self.environment}'
            )
            
            if not response['Stacks']:
                raise ValueError(f"Stack adpa-infrastructure-{self.environment} not found")
            
            outputs = response['Stacks'][0]['Outputs']
            
            infrastructure = {}
            for output in outputs:
                infrastructure[output['OutputKey']] = output['OutputValue']
            
            self.logger.info(f"Loaded infrastructure configuration: {list(infrastructure.keys())}")
            return infrastructure
            
        except Exception as e:
            self.logger.error(f"Failed to load infrastructure config: {e}")
            return {}
    
    def publish_pipeline_metrics(self, pipeline_result: Dict[str, Any]):
        """
        Publish comprehensive pipeline metrics using both systems
        """
        
        try:
            # Use Adariprasad's sophisticated analytics
            processed_metrics = self._process_pipeline_metrics(pipeline_result)
            
            # Publish to CloudWatch using deployed infrastructure
            self._publish_to_cloudwatch(processed_metrics)
            
            # Track KPIs using Adariprasad's system
            self._track_advanced_kpis(processed_metrics)
            
            # Check for anomalies
            self._check_anomalies(processed_metrics)
            
            self.logger.info("Pipeline metrics published successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to publish pipeline metrics: {e}")
            self.alerting.send_alert(
                message=f"Monitoring system error: {e}",
                severity="HIGH",
                source="UnifiedMonitoring"
            )
    
    def _process_pipeline_metrics(self, pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process pipeline results using Adariprasad's analytics"""
        
        processed = {
            'execution_time': pipeline_result.get('execution_time', 0),
            'success': pipeline_result.get('status') == 'completed',
            'timestamp': datetime.utcnow(),
            'pipeline_id': pipeline_result.get('pipeline_id', 'unknown')
        }
        
        # Extract model performance metrics
        if 'model_performance' in pipeline_result:
            performance = pipeline_result['model_performance']
            if isinstance(performance, dict):
                processed['model_metrics'] = performance
        
        # Extract resource usage
        if 'resource_usage' in pipeline_result:
            processed['resource_usage'] = pipeline_result['resource_usage']
        
        # Add infrastructure context
        processed['infrastructure'] = {
            'data_bucket': self.infrastructure.get('DataBucketName', ''),
            'lambda_function': self.infrastructure.get('DataProcessorFunctionArn', ''),
            'environment': self.environment
        }
        
        return processed
    
    def _publish_to_cloudwatch(self, metrics: Dict[str, Any]):
        """Publish metrics to CloudWatch in deployed infrastructure"""
        
        namespace = f"ADPA/{self.environment.title()}"
        
        metric_data = []
        
        # Basic pipeline metrics
        metric_data.append({
            'MetricName': 'PipelineExecutions',
            'Value': 1,
            'Unit': 'Count',
            'Dimensions': [
                {'Name': 'Environment', 'Value': self.environment},
                {'Name': 'Success', 'Value': str(metrics['success'])}
            ]
        })
        
        # Execution time
        if metrics['execution_time'] > 0:
            metric_data.append({
                'MetricName': 'ExecutionTime',
                'Value': metrics['execution_time'],
                'Unit': 'Seconds',
                'Dimensions': [
                    {'Name': 'Environment', 'Value': self.environment}
                ]
            })
        
        # Model performance metrics
        if 'model_metrics' in metrics:
            for metric_name, value in metrics['model_metrics'].items():
                if isinstance(value, (int, float)):
                    metric_data.append({
                        'MetricName': f'ModelPerformance_{metric_name}',
                        'Value': value,
                        'Unit': 'None',
                        'Dimensions': [
                            {'Name': 'Environment', 'Value': self.environment},
                            {'Name': 'Metric', 'Value': metric_name}
                        ]
                    })
        
        # Publish in batches (CloudWatch limit is 20 metrics per call)
        batch_size = 20
        for i in range(0, len(metric_data), batch_size):
            batch = metric_data[i:i + batch_size]
            
            self.cloudwatch.put_metric_data(
                Namespace=namespace,
                MetricData=batch
            )
    
    def _track_advanced_kpis(self, metrics: Dict[str, Any]):
        """Track advanced KPIs using Adariprasad's sophisticated system"""
        
        try:
            # Calculate business KPIs
            kpis = self.kpi_tracker.calculate_kpis(
                execution_result=metrics,
                timestamp=metrics['timestamp']
            )
            
            # Publish KPIs to CloudWatch
            for kpi_name, kpi_value in kpis.items():
                if isinstance(kpi_value, (int, float)):
                    self.cloudwatch.put_metric_data(
                        Namespace=f"ADPA/KPI/{self.environment.title()}",
                        MetricData=[{
                            'MetricName': kpi_name,
                            'Value': kpi_value,
                            'Unit': 'None',
                            'Dimensions': [
                                {'Name': 'Environment', 'Value': self.environment}
                            ]
                        }]
                    )
            
            self.logger.info(f"Advanced KPIs tracked: {list(kpis.keys())}")
            
        except Exception as e:
            self.logger.error(f"Failed to track advanced KPIs: {e}")
    
    def _check_anomalies(self, metrics: Dict[str, Any]):
        """Check for anomalies using Adariprasad's detection system"""
        
        try:
            # Use Adariprasad's anomaly detection
            anomaly_detector = AnomalyDetectionSystem()
            
            anomalies = anomaly_detector.detect_anomalies(
                metrics=metrics,
                context={'environment': self.environment}
            )
            
            # Send alerts for anomalies
            for anomaly in anomalies:
                self.alerting.send_alert(
                    message=f"Anomaly detected: {anomaly.get('description', 'Unknown')}",
                    severity=anomaly.get('severity', 'MEDIUM'),
                    source="AnomalyDetection",
                    details=anomaly
                )
                
                # Also publish anomaly metric
                self.cloudwatch.put_metric_data(
                    Namespace=f"ADPA/Anomalies/{self.environment.title()}",
                    MetricData=[{
                        'MetricName': 'AnomalyDetected',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Environment', 'Value': self.environment},
                            {'Name': 'Type', 'Value': anomaly.get('type', 'Unknown')}
                        ]
                    }]
                )
            
            if anomalies:
                self.logger.warning(f"Detected {len(anomalies)} anomalies")
            
        except Exception as e:
            self.logger.error(f"Anomaly detection failed: {e}")
    
    def create_unified_dashboard(self) -> str:
        """Create unified CloudWatch dashboard combining all monitoring"""
        
        dashboard_name = f"ADPA-Unified-{self.environment.title()}"
        
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0, "y": 0,
                    "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            [f"ADPA/{self.environment.title()}", "PipelineExecutions", "Environment", self.environment],
                            [f"ADPA/{self.environment.title()}", "ExecutionTime", "Environment", self.environment]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": os.getenv('AWS_REGION', 'us-east-2'),
                        "title": "Pipeline Execution Overview"
                    }
                },
                {
                    "type": "metric",
                    "x": 0, "y": 6,
                    "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            [f"ADPA/KPI/{self.environment.title()}", "Success_Rate", "Environment", self.environment],
                            [f"ADPA/KPI/{self.environment.title()}", "Avg_Performance", "Environment", self.environment]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": os.getenv('AWS_REGION', 'us-east-2'),
                        "title": "Key Performance Indicators"
                    }
                },
                {
                    "type": "log",
                    "x": 0, "y": 12,
                    "width": 24, "height": 6,
                    "properties": {
                        "query": f"SOURCE '{self.infrastructure.get('LogGroupName', '/aws/adpa/development')}'\n| fields @timestamp, @message\n| sort @timestamp desc\n| limit 100",
                        "region": os.getenv('AWS_REGION', 'us-east-2'),
                        "title": "Recent ADPA Logs"
                    }
                }
            ]
        }
        
        try:
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            dashboard_url = f"https://{os.getenv('AWS_REGION', 'us-east-2')}.console.aws.amazon.com/cloudwatch/home?region={os.getenv('AWS_REGION', 'us-east-2')}#dashboards:name={dashboard_name}"
            
            self.logger.info(f"Unified dashboard created: {dashboard_name}")
            return dashboard_url
            
        except Exception as e:
            self.logger.error(f"Failed to create unified dashboard: {e}")
            return ""
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        
        health = {
            'timestamp': datetime.utcnow().isoformat(),
            'environment': self.environment,
            'infrastructure_status': 'healthy' if self.infrastructure else 'degraded',
            'components': {
                'cloudwatch_monitor': True,
                'kpi_tracker': True,
                'alerting_system': True,
                'anomaly_detection': True
            }
        }
        
        # Check AWS infrastructure health
        try:
            # Check Lambda function
            lambda_client = boto3.client('lambda')
            function_arn = self.infrastructure.get('DataProcessorFunctionArn')
            
            if function_arn:
                function_name = function_arn.split(':')[-1]
                response = lambda_client.get_function(FunctionName=function_name)
                health['lambda_status'] = response['Configuration']['State']
            
            # Check S3 buckets
            s3_client = boto3.client('s3')
            data_bucket = self.infrastructure.get('DataBucketName')
            
            if data_bucket:
                s3_client.head_bucket(Bucket=data_bucket)
                health['s3_status'] = 'accessible'
            
        except Exception as e:
            health['infrastructure_status'] = 'degraded'
            health['infrastructure_error'] = str(e)
        
        return health


# Singleton instance
_unified_monitoring = None

def get_unified_monitoring(environment: str = "development") -> UnifiedADPAMonitoring:
    """Get or create unified monitoring instance"""
    global _unified_monitoring
    
    if _unified_monitoring is None:
        _unified_monitoring = UnifiedADPAMonitoring(environment)
    
    return _unified_monitoring