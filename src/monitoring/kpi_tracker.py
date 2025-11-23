"""
Business KPI Tracker for ADPA
Implementation based on Adariprasad's monitoring tutorial Week 2 Day 5
"""

import json
import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# Mock boto3 functionality for development
class MockDynamoDBTable:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.data = []
    
    def put_item(self, Item: Dict[str, Any]):
        self.data.append(Item)
    
    def scan(self, **kwargs):
        return {'Items': self.data}

class MockDynamoDBResource:
    def __init__(self):
        self.tables = {}
    
    def create_table(self, TableName: str, **kwargs):
        table = MockDynamoDBTable(TableName)
        self.tables[TableName] = table
        return table
    
    def Table(self, name: str):
        if name not in self.tables:
            self.tables[name] = MockDynamoDBTable(name)
        return self.tables[name]

class MockCloudWatchClient:
    def put_metric_data(self, **kwargs):
        pass

class MockS3Client:
    def put_object(self, **kwargs):
        pass

class ADPABusinessMetrics:
    """Track business-level KPIs and metrics for ADPA"""
    
    def __init__(self, mock_mode: bool = True):
        self.logger = logging.getLogger(__name__)
        self.mock_mode = mock_mode
        
        if mock_mode:
            # Use mock clients for development/testing
            self.cloudwatch = MockCloudWatchClient()
            self.dynamodb = MockDynamoDBResource()
            self.s3_client = MockS3Client()
        else:
            # Use real AWS clients (requires boto3)
            import boto3
            self.cloudwatch = boto3.client('cloudwatch')
            self.dynamodb = boto3.resource('dynamodb')
            self.s3_client = boto3.client('s3')
        
        # Create DynamoDB table for KPI storage
        self._setup_kpi_storage()
    
    def _setup_kpi_storage(self):
        """Set up DynamoDB table for KPI tracking"""
        
        table_name = 'ADPA-KPI-Metrics'
        
        try:
            if self.mock_mode:
                self.kpi_table = self.dynamodb.Table(table_name)
                self.logger.info(f"Mock KPI table created: {table_name}")
            else:
                self.kpi_table = self.dynamodb.create_table(
                    TableName=table_name,
                    KeySchema=[
                        {'AttributeName': 'kpi_name', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'kpi_name', 'AttributeType': 'S'},
                        {'AttributeName': 'timestamp', 'AttributeType': 'S'}
                    ],
                    BillingMode='PAY_PER_REQUEST',
                    Tags=[
                        {'Key': 'Project', 'Value': 'ADPA'},
                        {'Key': 'Purpose', 'Value': 'KPI-Tracking'}
                    ]
                )
                
                # Wait for table creation
                self.kpi_table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
                self.logger.info(f"Created KPI table: {table_name}")
            
        except Exception as e:
            if 'ResourceInUseException' in str(e):
                self.kpi_table = self.dynamodb.Table(table_name)
            else:
                self.logger.error(f"Error creating KPI table: {e}")
    
    def track_business_kpis(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track comprehensive business KPIs"""
        
        timestamp = datetime.utcnow().isoformat()
        
        # Calculate business metrics
        kpis = self._calculate_business_kpis(execution_data)
        
        # Store KPIs in DynamoDB
        for kpi_name, kpi_value in kpis.items():
            try:
                self.kpi_table.put_item(
                    Item={
                        'kpi_name': kpi_name,
                        'timestamp': timestamp,
                        'value': float(kpi_value) if isinstance(kpi_value, (int, float)) else kpi_value,
                        'metadata': execution_data.get('metadata', {})
                    }
                )
            except Exception as e:
                self.logger.error(f"Error storing KPI {kpi_name}: {e}")
        
        # Publish to CloudWatch
        self._publish_kpis_to_cloudwatch(kpis, timestamp)
        
        return kpis
    
    def _calculate_business_kpis(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate business-level KPIs from execution data"""
        
        kpis = {}
        
        # Pipeline efficiency metrics
        total_executions = execution_data.get('total_executions', 0)
        successful_executions = execution_data.get('successful_executions', 0)
        failed_executions = total_executions - successful_executions
        
        if total_executions > 0:
            kpis['pipeline_success_rate'] = (successful_executions / total_executions) * 100
            kpis['pipeline_failure_rate'] = (failed_executions / total_executions) * 100
        
        # Time-based metrics
        average_execution_time = execution_data.get('average_execution_time', 0)
        kpis['average_processing_time_minutes'] = average_execution_time / 60 if average_execution_time else 0
        
        # Data quality metrics
        data_quality_scores = execution_data.get('data_quality_scores', [])
        if data_quality_scores:
            kpis['average_data_quality'] = np.mean(data_quality_scores)
            kpis['data_quality_trend'] = np.polyfit(range(len(data_quality_scores)), data_quality_scores, 1)[0]
        
        # Model performance metrics
        model_accuracies = execution_data.get('model_accuracies', [])
        if model_accuracies:
            kpis['average_model_accuracy'] = np.mean(model_accuracies)
            kpis['model_accuracy_std'] = np.std(model_accuracies)
            kpis['model_performance_trend'] = np.polyfit(range(len(model_accuracies)), model_accuracies, 1)[0]
        
        # Resource efficiency metrics
        total_compute_cost = execution_data.get('total_compute_cost', 0)
        if total_executions > 0:
            kpis['cost_per_execution'] = total_compute_cost / total_executions
        
        total_processing_volume = execution_data.get('total_processing_volume_gb', 0)
        if total_processing_volume > 0:
            kpis['cost_per_gb_processed'] = total_compute_cost / total_processing_volume
        
        # Operational metrics
        kpis['mean_time_to_recovery'] = execution_data.get('mean_time_to_recovery_minutes', 0)
        kpis['uptime_percentage'] = execution_data.get('uptime_percentage', 100)
        
        # User satisfaction metrics (if available)
        user_satisfaction_scores = execution_data.get('user_satisfaction_scores', [])
        if user_satisfaction_scores:
            kpis['average_user_satisfaction'] = np.mean(user_satisfaction_scores)
        
        # Innovation metrics
        kpis['features_released'] = execution_data.get('features_released', 0)
        kpis['experiments_completed'] = execution_data.get('experiments_completed', 0)
        
        return kpis
    
    def _publish_kpis_to_cloudwatch(self, kpis: Dict[str, Any], timestamp: str) -> None:
        """Publish KPIs to CloudWatch for monitoring and alerting"""
        
        metric_data = []
        
        for kpi_name, kpi_value in kpis.items():
            if isinstance(kpi_value, (int, float)) and not np.isnan(kpi_value):
                metric_data.append({
                    'MetricName': kpi_name,
                    'Dimensions': [
                        {'Name': 'Environment', 'Value': 'Production'},
                        {'Name': 'System', 'Value': 'ADPA'}
                    ],
                    'Unit': 'None',
                    'Value': float(kpi_value),
                    'Timestamp': timestamp
                })
        
        # Publish in batches
        batch_size = 20
        for i in range(0, len(metric_data), batch_size):
            batch = metric_data[i:i + batch_size]
            
            try:
                self.cloudwatch.put_metric_data(
                    Namespace='ADPA/BusinessKPIs',
                    MetricData=batch
                )
                self.logger.info(f"Published {len(batch)} KPIs to CloudWatch")
            except Exception as e:
                self.logger.error(f"Error publishing KPIs: {e}")
    
    def generate_kpi_report(self, days_back: int = 7) -> Dict[str, Any]:
        """Generate comprehensive KPI report"""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)
        
        # Query KPIs from DynamoDB
        kpi_data = self._query_kpi_data(start_time, end_time)
        
        # Generate report
        report = {
            'report_period': f'{days_back} days',
            'generated_at': datetime.utcnow().isoformat(),
            'executive_summary': {},
            'detailed_metrics': {},
            'trends': {},
            'recommendations': [],
            'alerts': []
        }
        
        if not kpi_data:
            report['message'] = 'No KPI data available for the specified period'
            return report
        
        # Process KPI data
        if kpi_data:
            kpi_df = pd.DataFrame(kpi_data)
            
            # Executive summary
            latest_metrics = {}
            for kpi_name in kpi_df['kpi_name'].unique():
                kpi_subset = kpi_df[kpi_df['kpi_name'] == kpi_name]
                if not kpi_subset.empty:
                    latest_metrics[kpi_name] = kpi_subset.iloc[-1]['value']
            
            report['executive_summary'] = {
                'pipeline_success_rate': f"{latest_metrics.get('pipeline_success_rate', 0):.1f}%",
                'average_model_accuracy': f"{latest_metrics.get('average_model_accuracy', 0):.1f}%",
                'cost_per_execution': f"${latest_metrics.get('cost_per_execution', 0):.2f}",
                'uptime_percentage': f"{latest_metrics.get('uptime_percentage', 100):.1f}%"
            }
            
            # Detailed metrics with trends
            for kpi_name in kpi_df['kpi_name'].unique():
                kpi_subset = kpi_df[kpi_df['kpi_name'] == kpi_name].sort_values('timestamp')
                
                if len(kpi_subset) > 1:
                    values = kpi_subset['value'].astype(float).values
                    trend_slope = np.polyfit(range(len(values)), values, 1)[0] if len(values) > 1 else 0
                    
                    report['detailed_metrics'][kpi_name] = {
                        'current_value': float(values[-1]),
                        'average_value': float(np.mean(values)),
                        'min_value': float(np.min(values)),
                        'max_value': float(np.max(values)),
                        'trend': 'improving' if trend_slope > 0 else 'declining',
                        'trend_magnitude': abs(trend_slope)
                    }
        
        # Generate recommendations
        self._generate_kpi_recommendations(report)
        
        # Save report to S3
        self._save_kpi_report(report)
        
        return report
    
    def _query_kpi_data(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Query KPI data from DynamoDB"""
        
        kpi_data = []
        
        try:
            if self.mock_mode:
                # Return mock data for development
                response = {'Items': self.kpi_table.data}
            else:
                # Scan table for data in time range
                response = self.kpi_table.scan(
                    FilterExpression='#ts BETWEEN :start_time AND :end_time',
                    ExpressionAttributeNames={'#ts': 'timestamp'},
                    ExpressionAttributeValues={
                        ':start_time': start_time.isoformat(),
                        ':end_time': end_time.isoformat()
                    }
                )
            
            kpi_data.extend(response['Items'])
            
            # Handle pagination for real DynamoDB
            if not self.mock_mode:
                while 'LastEvaluatedKey' in response:
                    response = self.kpi_table.scan(
                        FilterExpression='#ts BETWEEN :start_time AND :end_time',
                        ExpressionAttributeNames={'#ts': 'timestamp'},
                        ExpressionAttributeValues={
                            ':start_time': start_time.isoformat(),
                            ':end_time': end_time.isoformat()
                        },
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    kpi_data.extend(response['Items'])
        
        except Exception as e:
            self.logger.error(f"Error querying KPI data: {e}")
        
        return kpi_data
    
    def _generate_kpi_recommendations(self, report: Dict[str, Any]) -> None:
        """Generate recommendations based on KPI analysis"""
        
        detailed_metrics = report.get('detailed_metrics', {})
        
        # Pipeline success rate recommendations
        if 'pipeline_success_rate' in detailed_metrics:
            success_rate = detailed_metrics['pipeline_success_rate']['current_value']
            if success_rate < 90:
                report['recommendations'].append({
                    'category': 'reliability',
                    'priority': 'high',
                    'message': f'Pipeline success rate is {success_rate:.1f}%. Investigate and improve error handling.',
                    'suggested_actions': [
                        'Review recent error logs',
                        'Implement additional retry mechanisms',
                        'Enhance input validation'
                    ]
                })
        
        # Model accuracy recommendations
        if 'average_model_accuracy' in detailed_metrics:
            accuracy = detailed_metrics['average_model_accuracy']['current_value']
            trend = detailed_metrics['average_model_accuracy']['trend']
            
            if accuracy < 80:
                report['recommendations'].append({
                    'category': 'model_performance',
                    'priority': 'high',
                    'message': f'Model accuracy is {accuracy:.1f}%. Consider model retraining.',
                    'suggested_actions': [
                        'Retrain models with recent data',
                        'Experiment with different algorithms',
                        'Review feature engineering'
                    ]
                })
            elif trend == 'declining':
                report['recommendations'].append({
                    'category': 'model_performance',
                    'priority': 'medium',
                    'message': 'Model accuracy is declining. Monitor for data drift.',
                    'suggested_actions': [
                        'Implement data drift detection',
                        'Schedule regular model retraining',
                        'Review data quality'
                    ]
                })
        
        # Cost optimization recommendations
        if 'cost_per_execution' in detailed_metrics:
            cost_trend = detailed_metrics['cost_per_execution']['trend']
            if cost_trend == 'increasing':
                report['recommendations'].append({
                    'category': 'cost_optimization',
                    'priority': 'medium',
                    'message': 'Execution costs are increasing. Review resource utilization.',
                    'suggested_actions': [
                        'Analyze resource usage patterns',
                        'Consider spot instances for training',
                        'Optimize data processing pipelines'
                    ]
                })
    
    def _save_kpi_report(self, report: Dict[str, Any]) -> None:
        """Save KPI report to S3"""
        
        try:
            if self.mock_mode:
                # Save to local file for development
                local_path = Path('./data/kpi_reports')
                local_path.mkdir(parents=True, exist_ok=True)
                
                report_file = local_path / f"kpi-report-{int(time.time())}.json"
                with open(report_file, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                
                self.logger.info(f"KPI report saved locally: {report_file}")
            else:
                report_key = f"kpi-reports/{datetime.utcnow().strftime('%Y-%m-%d')}/kpi-report-{int(time.time())}.json"
                
                self.s3_client.put_object(
                    Bucket='adpa-monitoring-reports',
                    Key=report_key,
                    Body=json.dumps(report, indent=2, default=str),
                    ContentType='application/json'
                )
                
                self.logger.info(f"KPI report saved: s3://adpa-monitoring-reports/{report_key}")
            
        except Exception as e:
            self.logger.error(f"Error saving KPI report: {e}")
    
    def create_kpi_alarms(self) -> None:
        """Create CloudWatch alarms for critical KPIs"""
        
        if self.mock_mode:
            self.logger.info("Mock mode: KPI alarms would be created in CloudWatch")
            return
        
        alarms = [
            {
                'AlarmName': 'ADPA-Low-Pipeline-Success-Rate',
                'MetricName': 'pipeline_success_rate',
                'Threshold': 90.0,
                'ComparisonOperator': 'LessThanThreshold',
                'AlarmDescription': 'Pipeline success rate below 90%'
            },
            {
                'AlarmName': 'ADPA-Low-Model-Accuracy',
                'MetricName': 'average_model_accuracy',
                'Threshold': 80.0,
                'ComparisonOperator': 'LessThanThreshold',
                'AlarmDescription': 'Model accuracy below 80%'
            },
            {
                'AlarmName': 'ADPA-High-Cost-Per-Execution',
                'MetricName': 'cost_per_execution',
                'Threshold': 50.0,
                'ComparisonOperator': 'GreaterThanThreshold',
                'AlarmDescription': 'Cost per execution exceeding $50'
            },
            {
                'AlarmName': 'ADPA-Low-Uptime',
                'MetricName': 'uptime_percentage',
                'Threshold': 99.0,
                'ComparisonOperator': 'LessThanThreshold',
                'AlarmDescription': 'System uptime below 99%'
            }
        ]
        
        for alarm in alarms:
            try:
                self.cloudwatch.put_metric_alarm(
                    AlarmName=alarm['AlarmName'],
                    ComparisonOperator=alarm['ComparisonOperator'],
                    EvaluationPeriods=2,
                    MetricName=alarm['MetricName'],
                    Namespace='ADPA/BusinessKPIs',
                    Period=300,
                    Statistic='Average',
                    Threshold=alarm['Threshold'],
                    ActionsEnabled=True,
                    AlarmDescription=alarm['AlarmDescription'],
                    AlarmActions=[
                        'arn:aws:sns:us-west-2:account:ADPA-Critical-Alerts'
                    ],
                    Dimensions=[
                        {'Name': 'Environment', 'Value': 'Production'},
                        {'Name': 'System', 'Value': 'ADPA'}
                    ]
                )
                self.logger.info(f"Created KPI alarm: {alarm['AlarmName']}")
            except Exception as e:
                self.logger.error(f"Error creating alarm {alarm['AlarmName']}: {e}")
    
    def get_kpi_summary(self) -> Dict[str, Any]:
        """Get current KPI summary"""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)  # Last 24 hours
        
        kpi_data = self._query_kpi_data(start_time, end_time)
        
        if not kpi_data:
            return {'message': 'No recent KPI data available'}
        
        # Calculate summary statistics
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'data_points': len(kpi_data),
            'time_range': '24 hours',
            'kpis': {}
        }
        
        if kpi_data:
            kpi_df = pd.DataFrame(kpi_data)
            
            for kpi_name in kpi_df['kpi_name'].unique():
                kpi_subset = kpi_df[kpi_df['kpi_name'] == kpi_name]
                values = kpi_subset['value'].astype(float)
                
                summary['kpis'][kpi_name] = {
                    'current': float(values.iloc[-1]) if not values.empty else None,
                    'average': float(values.mean()) if not values.empty else None,
                    'min': float(values.min()) if not values.empty else None,
                    'max': float(values.max()) if not values.empty else None,
                    'data_points': len(values)
                }
        
        return summary