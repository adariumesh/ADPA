"""
AWS CloudWatch monitoring integration for ADPA pipeline observability.
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

from ...agent.core.interfaces import ExecutionResult, StepStatus


class CloudWatchMonitor:
    """
    AWS CloudWatch integration for monitoring ADPA pipeline execution.
    """
    
    def __init__(self, 
                 region: str = "us-east-1",
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None):
        """
        Initialize CloudWatch monitor.
        
        Args:
            region: AWS region
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.region = region
        
        # Initialize boto3 clients
        session_kwargs = {'region_name': region}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs.update({
                'aws_access_key_id': aws_access_key_id,
                'aws_secret_access_key': aws_secret_access_key
            })
        
        self.cloudwatch = boto3.client('cloudwatch', **session_kwargs)
        self.logs = boto3.client('logs', **session_kwargs)
        
        # ADPA namespace for custom metrics
        self.namespace = "ADPA/Pipeline"
        
        self.logger.info("CloudWatch monitor initialized")
    
    def create_dashboard(self, 
                        dashboard_name: str = "ADPA-Pipeline-Dashboard",
                        pipeline_resources: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Create CloudWatch dashboard for ADPA pipeline monitoring.
        
        Args:
            dashboard_name: Name for the dashboard
            pipeline_resources: Dictionary of pipeline resources to monitor
            
        Returns:
            ExecutionResult with dashboard creation details
        """
        try:
            self.logger.info(f"Creating CloudWatch dashboard: {dashboard_name}")
            
            # Define dashboard body
            dashboard_body = self._create_dashboard_definition(pipeline_resources)
            
            # Create dashboard
            response = self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            dashboard_url = f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={dashboard_name}"
            
            self.logger.info(f"Dashboard created successfully: {dashboard_url}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                metrics={
                    'dashboard_name': dashboard_name,
                    'dashboard_created': True,
                    'widgets_count': len(dashboard_body['widgets'])
                },
                artifacts={
                    'dashboard_url': dashboard_url,
                    'dashboard_definition': dashboard_body
                }
            )
            
        except ClientError as e:
            error_msg = f"Failed to create dashboard: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
        except Exception as e:
            error_msg = f"Unexpected error creating dashboard: {str(e)}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
    
    def create_pipeline_alarms(self, 
                             pipeline_name: str,
                             notification_topic_arn: Optional[str] = None) -> ExecutionResult:
        """
        Create CloudWatch alarms for pipeline monitoring.
        
        Args:
            pipeline_name: Name of the pipeline to monitor
            notification_topic_arn: SNS topic for alarm notifications
            
        Returns:
            ExecutionResult with alarm creation details
        """
        try:
            self.logger.info(f"Creating CloudWatch alarms for pipeline: {pipeline_name}")
            
            alarms_created = []
            
            # Pipeline failure alarm
            failure_alarm = self._create_pipeline_failure_alarm(pipeline_name, notification_topic_arn)
            if failure_alarm:
                alarms_created.append('pipeline_failure')
            
            # High execution time alarm
            duration_alarm = self._create_execution_duration_alarm(pipeline_name, notification_topic_arn)
            if duration_alarm:
                alarms_created.append('execution_duration')
            
            # Model performance degradation alarm
            performance_alarm = self._create_model_performance_alarm(pipeline_name, notification_topic_arn)
            if performance_alarm:
                alarms_created.append('model_performance')
            
            # Cost threshold alarm
            cost_alarm = self._create_cost_threshold_alarm(pipeline_name, notification_topic_arn)
            if cost_alarm:
                alarms_created.append('cost_threshold')
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                metrics={
                    'alarms_created': len(alarms_created),
                    'alarm_types': alarms_created
                },
                artifacts={
                    'alarm_names': alarms_created,
                    'notification_topic': notification_topic_arn or 'none'
                }
            )
            
        except Exception as e:
            error_msg = f"Failed to create alarms: {str(e)}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
    
    def log_pipeline_event(self, 
                          event_type: str,
                          pipeline_id: str,
                          event_data: Dict[str, Any],
                          log_group: str = "/aws/adpa/pipeline") -> bool:
        """
        Log pipeline event to CloudWatch Logs.
        
        Args:
            event_type: Type of event (START, COMPLETE, ERROR, etc.)
            pipeline_id: Unique pipeline execution ID
            event_data: Event data to log
            log_group: CloudWatch log group
            
        Returns:
            True if logging successful
        """
        try:
            # Ensure log group exists
            self._ensure_log_group_exists(log_group)
            
            # Prepare log entry
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'pipeline_id': pipeline_id,
                'event_data': event_data
            }
            
            log_stream = f"pipeline-{pipeline_id}"
            
            # Put log events
            self.logs.put_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                logEvents=[
                    {
                        'timestamp': int(time.time() * 1000),
                        'message': json.dumps(log_entry)
                    }
                ]
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log pipeline event: {str(e)}")
            return False
    
    def publish_custom_metric(self, 
                            metric_name: str,
                            value: float,
                            unit: str = 'Count',
                            dimensions: Optional[Dict[str, str]] = None) -> bool:
        """
        Publish custom metric to CloudWatch.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit
            dimensions: Metric dimensions
            
        Returns:
            True if publishing successful
        """
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': key, 'Value': str(value)} 
                    for key, value in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to publish metric {metric_name}: {str(e)}")
            return False
    
    def track_pipeline_execution(self, 
                               pipeline_id: str,
                               execution_data: Dict[str, Any]) -> None:
        """
        Track comprehensive pipeline execution metrics.
        
        Args:
            pipeline_id: Pipeline execution ID
            execution_data: Execution data and metrics
        """
        dimensions = {'PipelineId': pipeline_id}
        
        # Track execution duration
        if 'duration_seconds' in execution_data:
            self.publish_custom_metric(
                'ExecutionDuration',
                execution_data['duration_seconds'],
                'Seconds',
                dimensions
            )
        
        # Track data processing metrics
        if 'rows_processed' in execution_data:
            self.publish_custom_metric(
                'RowsProcessed',
                execution_data['rows_processed'],
                'Count',
                dimensions
            )
        
        # Track model performance metrics
        if 'model_accuracy' in execution_data:
            self.publish_custom_metric(
                'ModelAccuracy',
                execution_data['model_accuracy'],
                'Percent',
                dimensions
            )
        
        # Track cost metrics
        if 'estimated_cost' in execution_data:
            self.publish_custom_metric(
                'EstimatedCost',
                execution_data['estimated_cost'],
                'None',
                dimensions
            )
        
        # Track pipeline success/failure
        success_value = 1 if execution_data.get('status') == 'success' else 0
        self.publish_custom_metric(
            'PipelineSuccess',
            success_value,
            'Count',
            dimensions
        )
    
    def get_pipeline_metrics(self, 
                           pipeline_id: Optional[str] = None,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Retrieve pipeline metrics from CloudWatch.
        
        Args:
            pipeline_id: Specific pipeline ID to filter by
            start_time: Start time for metrics query
            end_time: End time for metrics query
            
        Returns:
            Dictionary of pipeline metrics
        """
        try:
            if not start_time:
                start_time = datetime.utcnow() - timedelta(hours=24)
            if not end_time:
                end_time = datetime.utcnow()
            
            dimensions = []
            if pipeline_id:
                dimensions = [{'Name': 'PipelineId', 'Value': pipeline_id}]
            
            metrics = {}
            
            # Get execution duration metrics
            duration_stats = self._get_metric_statistics(
                'ExecutionDuration', start_time, end_time, dimensions
            )
            if duration_stats:
                metrics['execution_duration'] = duration_stats
            
            # Get success rate metrics
            success_stats = self._get_metric_statistics(
                'PipelineSuccess', start_time, end_time, dimensions
            )
            if success_stats:
                metrics['success_rate'] = success_stats
            
            # Get cost metrics
            cost_stats = self._get_metric_statistics(
                'EstimatedCost', start_time, end_time, dimensions
            )
            if cost_stats:
                metrics['cost_metrics'] = cost_stats
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve metrics: {str(e)}")
            return {}
    
    def _create_dashboard_definition(self, resources: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create CloudWatch dashboard definition."""
        
        widgets = [
            # Pipeline execution overview
            {
                "type": "metric",
                "x": 0, "y": 0, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        [self.namespace, "PipelineSuccess", {"stat": "Sum"}],
                        [self.namespace, "ExecutionDuration", {"stat": "Average"}]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": self.region,
                    "title": "Pipeline Execution Overview",
                    "yAxis": {"left": {"min": 0}}
                }
            },
            
            # Model performance metrics
            {
                "type": "metric",
                "x": 12, "y": 0, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        [self.namespace, "ModelAccuracy", {"stat": "Average"}]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": self.region,
                    "title": "Model Performance",
                    "yAxis": {"left": {"min": 0, "max": 100}}
                }
            },
            
            # Cost tracking
            {
                "type": "metric",
                "x": 0, "y": 6, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        [self.namespace, "EstimatedCost", {"stat": "Sum"}]
                    ],
                    "period": 3600,
                    "stat": "Sum",
                    "region": self.region,
                    "title": "Pipeline Costs",
                    "yAxis": {"left": {"min": 0}}
                }
            },
            
            # Data processing volume
            {
                "type": "metric",
                "x": 12, "y": 6, "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        [self.namespace, "RowsProcessed", {"stat": "Sum"}]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": self.region,
                    "title": "Data Processing Volume",
                    "yAxis": {"left": {"min": 0}}
                }
            }
        ]
        
        # Add AWS service specific widgets if resources provided
        if resources:
            if 'glue_jobs' in resources:
                widgets.append(self._create_glue_metrics_widget())
            if 'sagemaker_jobs' in resources:
                widgets.append(self._create_sagemaker_metrics_widget())
            if 'step_functions' in resources:
                widgets.append(self._create_stepfunctions_metrics_widget())
        
        return {
            "widgets": widgets
        }
    
    def _create_glue_metrics_widget(self) -> Dict[str, Any]:
        """Create Glue ETL job metrics widget."""
        return {
            "type": "metric",
            "x": 0, "y": 12, "width": 8, "height": 6,
            "properties": {
                "metrics": [
                    ["AWS/Glue", "glue.driver.aggregate.numCompletedTasks"],
                    ["AWS/Glue", "glue.driver.aggregate.numFailedTasks"]
                ],
                "period": 300,
                "stat": "Sum",
                "region": self.region,
                "title": "Glue ETL Job Performance"
            }
        }
    
    def _create_sagemaker_metrics_widget(self) -> Dict[str, Any]:
        """Create SageMaker training job metrics widget."""
        return {
            "type": "metric",
            "x": 8, "y": 12, "width": 8, "height": 6,
            "properties": {
                "metrics": [
                    ["AWS/SageMaker", "TrainingJobsInProgress"],
                    ["AWS/SageMaker", "TrainingJobsCompleted"],
                    ["AWS/SageMaker", "TrainingJobsFailed"]
                ],
                "period": 300,
                "stat": "Sum",
                "region": self.region,
                "title": "SageMaker Training Jobs"
            }
        }
    
    def _create_stepfunctions_metrics_widget(self) -> Dict[str, Any]:
        """Create Step Functions execution metrics widget."""
        return {
            "type": "metric",
            "x": 16, "y": 12, "width": 8, "height": 6,
            "properties": {
                "metrics": [
                    ["AWS/States", "ExecutionsSucceeded"],
                    ["AWS/States", "ExecutionsFailed"],
                    ["AWS/States", "ExecutionsTimedOut"]
                ],
                "period": 300,
                "stat": "Sum",
                "region": self.region,
                "title": "Step Functions Executions"
            }
        }
    
    def _create_pipeline_failure_alarm(self, pipeline_name: str, topic_arn: Optional[str]) -> bool:
        """Create alarm for pipeline failures."""
        try:
            alarm_name = f"ADPA-{pipeline_name}-PipelineFailure"
            
            alarm_config = {
                'AlarmName': alarm_name,
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 1,
                'MetricName': 'PipelineSuccess',
                'Namespace': self.namespace,
                'Period': 300,
                'Statistic': 'Sum',
                'Threshold': 1.0,
                'ActionsEnabled': True,
                'AlarmDescription': f'Alert when {pipeline_name} pipeline fails',
                'Unit': 'Count'
            }
            
            if topic_arn:
                alarm_config['AlarmActions'] = [topic_arn]
            
            self.cloudwatch.put_metric_alarm(**alarm_config)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create pipeline failure alarm: {str(e)}")
            return False
    
    def _create_execution_duration_alarm(self, pipeline_name: str, topic_arn: Optional[str]) -> bool:
        """Create alarm for long execution times."""
        try:
            alarm_name = f"ADPA-{pipeline_name}-LongExecution"
            
            alarm_config = {
                'AlarmName': alarm_name,
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 1,
                'MetricName': 'ExecutionDuration',
                'Namespace': self.namespace,
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 7200.0,  # 2 hours
                'ActionsEnabled': True,
                'AlarmDescription': f'Alert when {pipeline_name} execution exceeds 2 hours',
                'Unit': 'Seconds'
            }
            
            if topic_arn:
                alarm_config['AlarmActions'] = [topic_arn]
            
            self.cloudwatch.put_metric_alarm(**alarm_config)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create execution duration alarm: {str(e)}")
            return False
    
    def _create_model_performance_alarm(self, pipeline_name: str, topic_arn: Optional[str]) -> bool:
        """Create alarm for model performance degradation."""
        try:
            alarm_name = f"ADPA-{pipeline_name}-ModelPerformance"
            
            alarm_config = {
                'AlarmName': alarm_name,
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 2,
                'MetricName': 'ModelAccuracy',
                'Namespace': self.namespace,
                'Period': 3600,
                'Statistic': 'Average',
                'Threshold': 70.0,  # 70% accuracy threshold
                'ActionsEnabled': True,
                'AlarmDescription': f'Alert when {pipeline_name} model accuracy drops below 70%',
                'Unit': 'Percent'
            }
            
            if topic_arn:
                alarm_config['AlarmActions'] = [topic_arn]
            
            self.cloudwatch.put_metric_alarm(**alarm_config)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create model performance alarm: {str(e)}")
            return False
    
    def _create_cost_threshold_alarm(self, pipeline_name: str, topic_arn: Optional[str]) -> bool:
        """Create alarm for cost thresholds."""
        try:
            alarm_name = f"ADPA-{pipeline_name}-CostThreshold"
            
            alarm_config = {
                'AlarmName': alarm_name,
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 1,
                'MetricName': 'EstimatedCost',
                'Namespace': self.namespace,
                'Period': 3600,
                'Statistic': 'Sum',
                'Threshold': 50.0,  # $50 threshold
                'ActionsEnabled': True,
                'AlarmDescription': f'Alert when {pipeline_name} costs exceed $50/hour',
                'Unit': 'None'
            }
            
            if topic_arn:
                alarm_config['AlarmActions'] = [topic_arn]
            
            self.cloudwatch.put_metric_alarm(**alarm_config)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create cost threshold alarm: {str(e)}")
            return False
    
    def _ensure_log_group_exists(self, log_group: str) -> None:
        """Ensure CloudWatch log group exists."""
        try:
            self.logs.create_log_group(logGroupName=log_group)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
    
    def _get_metric_statistics(self, 
                             metric_name: str,
                             start_time: datetime,
                             end_time: datetime,
                             dimensions: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Get CloudWatch metric statistics."""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace=self.namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum', 'Average', 'Maximum', 'Minimum']
            )
            
            if response['Datapoints']:
                return {
                    'datapoints': len(response['Datapoints']),
                    'latest_value': response['Datapoints'][-1] if response['Datapoints'] else None,
                    'statistics': response['Datapoints']
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get metric statistics for {metric_name}: {str(e)}")
            return None