"""
Comprehensive alerting system for ADPA
Implementation based on Adariprasad's monitoring tutorial
"""

import boto3
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

class ADPAAlertingSystem:
    """Comprehensive alerting system for ADPA"""
    
    def __init__(self, region='us-west-2'):
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.logger = logging.getLogger(__name__)
        
        # Create SNS topics for different alert types
        self.alert_topics = self._create_sns_topics()
        
        # Create CloudWatch alarms
        self._create_cloudwatch_alarms()
    
    def _create_sns_topics(self) -> Dict[str, str]:
        """Create SNS topics for different types of alerts"""
        
        topics = {
            'critical': 'ADPA-Critical-Alerts',
            'warning': 'ADPA-Warning-Alerts', 
            'info': 'ADPA-Info-Alerts',
            'performance': 'ADPA-Performance-Alerts',
            'security': 'ADPA-Security-Alerts',
            'cost': 'ADPA-Cost-Alerts'
        }
        
        topic_arns = {}
        
        for topic_type, topic_name in topics.items():
            try:
                response = self.sns.create_topic(Name=topic_name)
                topic_arn = response['TopicArn']
                topic_arns[topic_type] = topic_arn
                
                # Subscribe email endpoints (replace with actual emails)
                email_endpoints = {
                    'critical': ['adariprasad@critical-alerts.com', 'team-lead@adpa.com'],
                    'warning': ['adariprasad@alerts.com'],
                    'info': ['adariprasad@info.com'],
                    'performance': ['adariprasad@performance.com'],
                    'security': ['security-team@adpa.com'],
                    'cost': ['cost-team@adpa.com']
                }
                
                for email in email_endpoints.get(topic_type, []):
                    try:
                        self.sns.subscribe(
                            TopicArn=topic_arn,
                            Protocol='email',
                            Endpoint=email
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to subscribe {email} to {topic_name}: {e}")
                
                self.logger.info(f"Created SNS topic: {topic_name} - {topic_arn}")
                
            except Exception as e:
                self.logger.error(f"Error creating SNS topic {topic_name}: {e}")
        
        return topic_arns
    
    def _create_cloudwatch_alarms(self) -> None:
        """Create comprehensive CloudWatch alarms"""
        
        alarms = [
            # Pipeline execution failure alarm
            {
                'AlarmName': 'ADPA-Pipeline-Execution-Failures',
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 2,
                'MetricName': 'SuccessRate',
                'Namespace': 'ADPA/Pipeline',
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 90.0,
                'ActionsEnabled': True,
                'AlarmActions': [self.alert_topics.get('critical', '')],
                'AlarmDescription': 'Pipeline success rate below 90%',
                'Dimensions': [
                    {'Name': 'Pipeline', 'Value': 'ADPA'}
                ]
            },
            
            # High execution time alarm
            {
                'AlarmName': 'ADPA-High-Execution-Time',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 3,
                'MetricName': 'ExecutionTime',
                'Namespace': 'ADPA/Pipeline',
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 300.0,  # 5 minutes
                'ActionsEnabled': True,
                'AlarmActions': [self.alert_topics.get('warning', '')],
                'AlarmDescription': 'Pipeline execution time exceeding 5 minutes',
                'Dimensions': [
                    {'Name': 'Pipeline', 'Value': 'ADPA'}
                ]
            },
            
            # Data quality degradation alarm
            {
                'AlarmName': 'ADPA-Data-Quality-Degradation',
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 2,
                'MetricName': 'DataQualityScore',
                'Namespace': 'ADPA/Pipeline',
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 85.0,
                'ActionsEnabled': True,
                'AlarmActions': [self.alert_topics.get('warning', '')],
                'AlarmDescription': 'Data quality score below 85%'
            },
            
            # Model accuracy degradation alarm
            {
                'AlarmName': 'ADPA-Model-Accuracy-Degradation',
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 3,
                'MetricName': 'ModelAccuracy',
                'Namespace': 'ADPA/Pipeline',
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 80.0,
                'ActionsEnabled': True,
                'AlarmActions': [self.alert_topics.get('critical', '')],
                'AlarmDescription': 'Model accuracy below 80%'
            },
            
            # High CPU utilization alarm
            {
                'AlarmName': 'ADPA-High-CPU-Utilization',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 3,
                'MetricName': 'CPUUtilization',
                'Namespace': 'ADPA/Pipeline',
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 90.0,
                'ActionsEnabled': True,
                'AlarmActions': [self.alert_topics.get('performance', '')],
                'AlarmDescription': 'CPU utilization exceeding 90%'
            },
            
            # High memory usage alarm
            {
                'AlarmName': 'ADPA-High-Memory-Usage',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 3,
                'MetricName': 'MemoryUsage',
                'Namespace': 'ADPA/Pipeline',
                'Period': 300,
                'Statistic': 'Average',
                'Threshold': 85.0,
                'ActionsEnabled': True,
                'AlarmActions': [self.alert_topics.get('performance', '')],
                'AlarmDescription': 'Memory usage exceeding 85%'
            },
            
            # Cost spike alarm
            {
                'AlarmName': 'ADPA-Cost-Spike',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 1,
                'MetricName': 'ExecutionCost',
                'Namespace': 'ADPA/Pipeline',
                'Period': 3600,  # 1 hour
                'Statistic': 'Sum',
                'Threshold': 100.0,  # $100 per hour
                'ActionsEnabled': True,
                'AlarmActions': [self.alert_topics.get('cost', '')],
                'AlarmDescription': 'Hourly cost exceeding $100'
            }
        ]
        
        for alarm in alarms:
            # Filter out empty alarm actions
            alarm['AlarmActions'] = [action for action in alarm['AlarmActions'] if action]
            
            try:
                self.cloudwatch.put_metric_alarm(**alarm)
                self.logger.info(f"Created alarm: {alarm['AlarmName']}")
            except Exception as e:
                self.logger.error(f"Error creating alarm {alarm['AlarmName']}: {e}")
    
    def send_custom_alert(self, alert_type: str, title: str, message: str, 
                         severity: str = 'info', metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Send custom alert through SNS"""
        
        topic_mapping = {
            'critical': 'critical',
            'error': 'critical',
            'warning': 'warning',
            'info': 'info',
            'performance': 'performance',
            'security': 'security',
            'cost': 'cost'
        }
        
        topic_type = topic_mapping.get(severity, 'info')
        topic_arn = self.alert_topics.get(topic_type)
        
        if not topic_arn:
            self.logger.error(f"No topic found for severity: {severity}")
            return None
        
        alert_payload = {
            'timestamp': datetime.utcnow().isoformat(),
            'alert_type': alert_type,
            'severity': severity,
            'title': title,
            'message': message,
            'source': 'ADPA-Monitoring-System',
            'environment': 'production',
            'metadata': metadata or {}
        }
        
        try:
            response = self.sns.publish(
                TopicArn=topic_arn,
                Subject=f"[ADPA {severity.upper()}] {title}",
                Message=json.dumps(alert_payload, indent=2)
            )
            self.logger.info(f"Alert sent: {response['MessageId']}")
            return response['MessageId']
        except Exception as e:
            self.logger.error(f"Error sending alert: {e}")
            return None
    
    def get_alarm_history(self, alarm_name: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """Get alarm history for analysis"""
        
        from datetime import timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)
        
        try:
            response = self.cloudwatch.describe_alarm_history(
                AlarmName=alarm_name,
                StartDate=start_time,
                EndDate=end_time,
                MaxRecords=100
            )
            
            return [
                {
                    'timestamp': item['Timestamp'].isoformat(),
                    'summary': item['AlarmName'],
                    'reason': item['HistoryReason'],
                    'data': json.loads(item['HistoryData']) if item.get('HistoryData') else {}
                }
                for item in response.get('AlarmHistoryItems', [])
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting alarm history: {e}")
            return []
    
    def get_alert_summary(self, days_back: int = 7) -> Dict[str, Any]:
        """Get summary of alerts and alarms over the specified period"""
        
        summary = {
            'time_period': f'{days_back} days',
            'total_alarms': 0,
            'alarm_states': {},
            'alarm_history': {},
            'recommendations': []
        }
        
        try:
            # Get all ADPA alarms
            alarms_response = self.cloudwatch.describe_alarms(
                AlarmNamePrefix='ADPA-'
            )
            
            alarms = alarms_response.get('MetricAlarms', [])
            summary['total_alarms'] = len(alarms)
            
            # Count alarm states
            for alarm in alarms:
                state = alarm['StateValue']
                summary['alarm_states'][state] = summary['alarm_states'].get(state, 0) + 1
                
                # Get history for each alarm
                history = self.get_alarm_history(alarm['AlarmName'], days_back)
                if history:
                    summary['alarm_history'][alarm['AlarmName']] = {
                        'total_events': len(history),
                        'recent_events': history[:5]  # Most recent 5 events
                    }
            
            # Generate recommendations
            if summary['alarm_states'].get('ALARM', 0) > 3:
                summary['recommendations'].append({
                    'type': 'multiple_active_alarms',
                    'message': 'Multiple alarms are active. Review system health.',
                    'priority': 'high'
                })
            
            if summary['alarm_states'].get('INSUFFICIENT_DATA', 0) > 0:
                summary['recommendations'].append({
                    'type': 'insufficient_data',
                    'message': 'Some alarms have insufficient data. Check metric collection.',
                    'priority': 'medium'
                })
            
        except Exception as e:
            self.logger.error(f"Error getting alert summary: {e}")
            summary['error'] = str(e)
        
        return summary
    
    def test_alert_system(self) -> Dict[str, Any]:
        """Test the alerting system by sending test alerts"""
        
        test_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'tests_performed': [],
            'results': {}
        }
        
        # Test each severity level
        test_alerts = [
            ('info', 'Test Info Alert', 'This is a test info alert'),
            ('warning', 'Test Warning Alert', 'This is a test warning alert'),
            ('critical', 'Test Critical Alert', 'This is a test critical alert')
        ]
        
        for severity, title, message in test_alerts:
            test_name = f'test_{severity}_alert'
            test_results['tests_performed'].append(test_name)
            
            try:
                message_id = self.send_custom_alert(
                    alert_type='system_test',
                    title=title,
                    message=message,
                    severity=severity,
                    metadata={'test': True}
                )
                
                test_results['results'][test_name] = {
                    'status': 'success' if message_id else 'failed',
                    'message_id': message_id
                }
                
            except Exception as e:
                test_results['results'][test_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return test_results
    
    def create_custom_alarm(self, alarm_config: Dict[str, Any]) -> bool:
        """Create a custom CloudWatch alarm"""
        
        required_fields = [
            'AlarmName', 'MetricName', 'Namespace', 'Threshold', 
            'ComparisonOperator', 'EvaluationPeriods'
        ]
        
        # Validate required fields
        for field in required_fields:
            if field not in alarm_config:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        # Set defaults
        alarm_config.setdefault('Period', 300)
        alarm_config.setdefault('Statistic', 'Average')
        alarm_config.setdefault('ActionsEnabled', True)
        
        try:
            self.cloudwatch.put_metric_alarm(**alarm_config)
            self.logger.info(f"Created custom alarm: {alarm_config['AlarmName']}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating custom alarm: {e}")
            return False
    
    def disable_alarm(self, alarm_name: str) -> bool:
        """Disable a specific alarm"""
        
        try:
            self.cloudwatch.disable_alarm_actions(AlarmNames=[alarm_name])
            self.logger.info(f"Disabled alarm: {alarm_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error disabling alarm {alarm_name}: {e}")
            return False
    
    def enable_alarm(self, alarm_name: str) -> bool:
        """Enable a specific alarm"""
        
        try:
            self.cloudwatch.enable_alarm_actions(AlarmNames=[alarm_name])
            self.logger.info(f"Enabled alarm: {alarm_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error enabling alarm {alarm_name}: {e}")
            return False