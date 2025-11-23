"""
Advanced CloudWatch monitoring for ADPA
Implementation based on Adariprasad's monitoring tutorial
"""

import boto3
import json
from datetime import datetime, timedelta
import time
import logging
from typing import Dict, List, Any, Optional

class ADPACloudWatchMonitor:
    """Advanced CloudWatch monitoring for ADPA"""
    
    def __init__(self, region='us-west-2'):
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.logs_client = boto3.client('logs', region_name=region)
        self.namespace = 'ADPA/Pipeline'
        self.logger = logging.getLogger(__name__)
        
        # Create log groups
        self._setup_log_groups()
    
    def _setup_log_groups(self):
        """Set up CloudWatch log groups for ADPA"""
        
        log_groups = [
            'ADPA/Agent/Execution',
            'ADPA/ML/Training',
            'ADPA/ML/Inference',
            'ADPA/DataProcessing/ETL',
            'ADPA/API/Gateway',
            'ADPA/Security/Audit',
            'ADPA/Performance/Metrics',
            'ADPA/Errors/Application'
        ]
        
        for group_name in log_groups:
            try:
                self.logs_client.create_log_group(
                    logGroupName=group_name,
                    tags={
                        'Project': 'ADPA',
                        'Environment': 'Production',
                        'Owner': 'Adariprasad'
                    }
                )
                self.logger.info(f"Created log group: {group_name}")
            except Exception as e:
                if 'ResourceAlreadyExistsException' not in str(e):
                    self.logger.error(f"Error creating log group {group_name}: {e}")
    
    def publish_pipeline_metrics(self, execution_id: str, metrics_data: Dict[str, Any]) -> None:
        """Publish custom pipeline metrics to CloudWatch"""
        
        metric_data = []
        
        # Core pipeline metrics
        if 'execution_time' in metrics_data:
            metric_data.append({
                'MetricName': 'ExecutionTime',
                'Dimensions': [
                    {'Name': 'ExecutionId', 'Value': execution_id},
                    {'Name': 'Pipeline', 'Value': 'ADPA'}
                ],
                'Unit': 'Seconds',
                'Value': metrics_data['execution_time'],
                'Timestamp': datetime.utcnow()
            })
        
        if 'success_rate' in metrics_data:
            metric_data.append({
                'MetricName': 'SuccessRate',
                'Dimensions': [
                    {'Name': 'Pipeline', 'Value': 'ADPA'},
                    {'Name': 'Environment', 'Value': 'Production'}
                ],
                'Unit': 'Percent',
                'Value': metrics_data['success_rate'],
                'Timestamp': datetime.utcnow()
            })
        
        if 'data_quality_score' in metrics_data:
            metric_data.append({
                'MetricName': 'DataQualityScore',
                'Dimensions': [
                    {'Name': 'ExecutionId', 'Value': execution_id}
                ],
                'Unit': 'Percent',
                'Value': metrics_data['data_quality_score'],
                'Timestamp': datetime.utcnow()
            })
        
        if 'model_accuracy' in metrics_data:
            metric_data.append({
                'MetricName': 'ModelAccuracy',
                'Dimensions': [
                    {'Name': 'ModelVersion', 'Value': metrics_data.get('model_version', 'unknown')},
                    {'Name': 'ExecutionId', 'Value': execution_id}
                ],
                'Unit': 'Percent',
                'Value': metrics_data['model_accuracy'],
                'Timestamp': datetime.utcnow()
            })
        
        # Resource utilization metrics
        if 'cpu_utilization' in metrics_data:
            metric_data.append({
                'MetricName': 'CPUUtilization',
                'Dimensions': [
                    {'Name': 'InstanceType', 'Value': metrics_data.get('instance_type', 'unknown')},
                    {'Name': 'ExecutionId', 'Value': execution_id}
                ],
                'Unit': 'Percent',
                'Value': metrics_data['cpu_utilization'],
                'Timestamp': datetime.utcnow()
            })
        
        if 'memory_usage' in metrics_data:
            metric_data.append({
                'MetricName': 'MemoryUsage',
                'Dimensions': [
                    {'Name': 'InstanceType', 'Value': metrics_data.get('instance_type', 'unknown')},
                    {'Name': 'ExecutionId', 'Value': execution_id}
                ],
                'Unit': 'Percent',
                'Value': metrics_data['memory_usage'],
                'Timestamp': datetime.utcnow()
            })
        
        # Cost metrics
        if 'execution_cost' in metrics_data:
            metric_data.append({
                'MetricName': 'ExecutionCost',
                'Dimensions': [
                    {'Name': 'Pipeline', 'Value': 'ADPA'},
                    {'Name': 'CostType', 'Value': 'Compute'}
                ],
                'Unit': 'None',  # Cost in dollars
                'Value': metrics_data['execution_cost'],
                'Timestamp': datetime.utcnow()
            })
        
        # Publish metrics in batches (CloudWatch limit: 20 metrics per call)
        batch_size = 20
        for i in range(0, len(metric_data), batch_size):
            batch = metric_data[i:i + batch_size]
            
            try:
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
                self.logger.info(f"Published {len(batch)} metrics to CloudWatch")
            except Exception as e:
                self.logger.error(f"Error publishing metrics: {e}")
    
    def log_structured_event(self, log_group: str, event_type: str, event_data: Dict[str, Any]) -> None:
        """Log structured events to CloudWatch Logs"""
        
        log_event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'level': event_data.get('level', 'INFO'),
            'message': event_data.get('message', ''),
            'execution_id': event_data.get('execution_id', ''),
            'component': event_data.get('component', 'unknown'),
            'details': event_data.get('details', {})
        }
        
        try:
            # Create log stream if it doesn't exist
            stream_name = f"{event_type}-{datetime.utcnow().strftime('%Y-%m-%d')}"
            
            try:
                self.logs_client.create_log_stream(
                    logGroupName=log_group,
                    logStreamName=stream_name
                )
            except:
                pass  # Stream might already exist
            
            # Put log event
            self.logs_client.put_log_events(
                logGroupName=log_group,
                logStreamName=stream_name,
                logEvents=[
                    {
                        'timestamp': int(time.time() * 1000),
                        'message': json.dumps(log_event)
                    }
                ]
            )
            
        except Exception as e:
            self.logger.error(f"Error logging event: {e}")
    
    def create_dashboard(self) -> Optional[str]:
        """Create comprehensive CloudWatch dashboard for ADPA"""
        
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
                            ["ADPA/Pipeline", "ExecutionTime", "Pipeline", "ADPA"],
                            [".", "SuccessRate", ".", "."],
                            [".", "DataQualityScore"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": "us-west-2",
                        "title": "ADPA Pipeline Performance",
                        "yAxis": {
                            "left": {
                                "min": 0,
                                "max": 100
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
                            ["ADPA/Pipeline", "ModelAccuracy", "ModelVersion", "v2.1.0"],
                            [".", "CPUUtilization", "InstanceType", "ml.m5.xlarge"],
                            [".", "MemoryUsage", ".", "."]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": "us-west-2",
                        "title": "Resource Utilization & Model Performance"
                    }
                },
                {
                    "type": "log",
                    "x": 0,
                    "y": 6,
                    "width": 24,
                    "height": 6,
                    "properties": {
                        "query": "SOURCE 'ADPA/Errors/Application'\\n| fields @timestamp, level, message, component\\n| filter level = \"ERROR\"\\n| sort @timestamp desc\\n| limit 100",
                        "region": "us-west-2",
                        "title": "Recent Errors"
                    }
                },
                {
                    "type": "metric",
                    "x": 0,
                    "y": 12,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/SageMaker", "Invocations", "EndpointName", "adpa-ml-endpoint"],
                            [".", "ModelLatency", ".", "."],
                            [".", "InvocationErrors", ".", "."]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": "us-west-2",
                        "title": "SageMaker Endpoint Metrics"
                    }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 12,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Lambda", "Invocations", "FunctionName", "adpa-pipeline-trigger"],
                            [".", "Duration", ".", "."],
                            [".", "Errors", ".", "."],
                            [".", "Throttles", ".", "."]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": "us-west-2",
                        "title": "Lambda Function Metrics"
                    }
                },
                {
                    "type": "metric",
                    "x": 0,
                    "y": 18,
                    "width": 24,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["ADPA/Pipeline", "ExecutionCost", "Pipeline", "ADPA", "CostType", "Compute"]
                        ],
                        "period": 3600,
                        "stat": "Sum",
                        "region": "us-west-2",
                        "title": "Cost Analysis - Hourly Compute Costs",
                        "yAxis": {
                            "left": {
                                "min": 0
                            }
                        }
                    }
                }
            ]
        }
        
        try:
            response = self.cloudwatch.put_dashboard(
                DashboardName='ADPA-Comprehensive-Dashboard',
                DashboardBody=json.dumps(dashboard_body)
            )
            self.logger.info(f"Dashboard created: {response}")
            return response.get('DashboardArn')
        except Exception as e:
            self.logger.error(f"Error creating dashboard: {e}")
            return None
    
    def get_metrics_summary(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get summary of key metrics for a time period"""
        
        metrics_summary = {
            'time_period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'pipeline_metrics': {},
            'performance_metrics': {},
            'cost_metrics': {}
        }
        
        # Get pipeline success rate
        try:
            success_rate_response = self.cloudwatch.get_metric_statistics(
                Namespace=self.namespace,
                MetricName='SuccessRate',
                Dimensions=[
                    {'Name': 'Pipeline', 'Value': 'ADPA'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average', 'Maximum', 'Minimum']
            )
            
            if success_rate_response['Datapoints']:
                avg_success_rate = sum(dp['Average'] for dp in success_rate_response['Datapoints']) / len(success_rate_response['Datapoints'])
                metrics_summary['pipeline_metrics']['average_success_rate'] = avg_success_rate
        except Exception as e:
            self.logger.error(f"Error getting success rate metrics: {e}")
        
        # Get execution time metrics
        try:
            exec_time_response = self.cloudwatch.get_metric_statistics(
                Namespace=self.namespace,
                MetricName='ExecutionTime',
                Dimensions=[
                    {'Name': 'Pipeline', 'Value': 'ADPA'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average', 'Maximum', 'Minimum']
            )
            
            if exec_time_response['Datapoints']:
                avg_exec_time = sum(dp['Average'] for dp in exec_time_response['Datapoints']) / len(exec_time_response['Datapoints'])
                metrics_summary['performance_metrics']['average_execution_time'] = avg_exec_time
        except Exception as e:
            self.logger.error(f"Error getting execution time metrics: {e}")
        
        return metrics_summary