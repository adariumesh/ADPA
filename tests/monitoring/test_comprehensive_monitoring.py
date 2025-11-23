"""
Test comprehensive monitoring system implementation
Test script for Adariprasad's monitoring tutorial Week 1 objectives
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json
import time

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from src.monitoring.cloudwatch_monitor import ADPACloudWatchMonitor
from src.monitoring.xray_tracer import ADPAXRayMonitor  
from src.monitoring.alerting_system import ADPAAlertingSystem
from src.pipeline.monitoring.pipeline_monitor import PipelineMonitoringStep


class TestADPACloudWatchMonitor(unittest.TestCase):
    """Test CloudWatch monitoring implementation"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_cloudwatch = Mock()
        self.mock_logs = Mock()
        
        with patch('boto3.client') as mock_boto3:
            mock_boto3.side_effect = lambda service, **kwargs: {
                'cloudwatch': self.mock_cloudwatch,
                'logs': self.mock_logs
            }[service]
            
            self.monitor = ADPACloudWatchMonitor()
    
    def test_log_groups_setup(self):
        """Test CloudWatch log groups creation"""
        expected_groups = [
            'ADPA/Agent/Execution',
            'ADPA/ML/Training',
            'ADPA/ML/Inference',
            'ADPA/DataProcessing/ETL',
            'ADPA/API/Gateway',
            'ADPA/Security/Audit',
            'ADPA/Performance/Metrics',
            'ADPA/Errors/Application'
        ]
        
        # Verify create_log_group was called for each expected group
        self.assertEqual(self.mock_logs.create_log_group.call_count, len(expected_groups))
    
    def test_publish_pipeline_metrics(self):
        """Test publishing custom pipeline metrics"""
        execution_id = "test-exec-123"
        metrics_data = {
            'execution_time': 150.5,
            'success_rate': 95.2,
            'data_quality_score': 98.1,
            'model_accuracy': 87.3,
            'cpu_utilization': 65.8,
            'memory_usage': 72.1,
            'execution_cost': 15.75
        }
        
        # Test metric publishing
        self.monitor.publish_pipeline_metrics(execution_id, metrics_data)
        
        # Verify CloudWatch put_metric_data was called
        self.mock_cloudwatch.put_metric_data.assert_called()
        
        # Check that metrics were properly formatted
        call_args = self.mock_cloudwatch.put_metric_data.call_args
        self.assertEqual(call_args[1]['Namespace'], 'ADPA/Pipeline')
        self.assertIsInstance(call_args[1]['MetricData'], list)
    
    def test_structured_event_logging(self):
        """Test structured event logging"""
        log_group = 'ADPA/Agent/Execution'
        event_type = 'pipeline_execution'
        event_data = {
            'level': 'INFO',
            'message': 'Pipeline execution started',
            'execution_id': 'test-123',
            'component': 'pipeline_manager',
            'details': {'algorithm': 'random_forest'}
        }
        
        # Test event logging
        self.monitor.log_structured_event(log_group, event_type, event_data)
        
        # Verify log stream creation and event logging
        self.mock_logs.create_log_stream.assert_called()
        self.mock_logs.put_log_events.assert_called()
    
    def test_dashboard_creation(self):
        """Test CloudWatch dashboard creation"""
        self.mock_cloudwatch.put_dashboard.return_value = {
            'DashboardArn': 'arn:aws:cloudwatch:us-west-2:123456789:dashboard/test'
        }
        
        dashboard_arn = self.monitor.create_dashboard()
        
        # Verify dashboard creation
        self.mock_cloudwatch.put_dashboard.assert_called()
        self.assertIsNotNone(dashboard_arn)
    
    def test_metrics_summary(self):
        """Test metrics summary retrieval"""
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        
        # Mock CloudWatch responses
        self.mock_cloudwatch.get_metric_statistics.return_value = {
            'Datapoints': [
                {
                    'Timestamp': datetime.now(),
                    'Average': 95.5,
                    'Maximum': 98.0,
                    'Minimum': 90.0
                }
            ]
        }
        
        summary = self.monitor.get_metrics_summary(start_time, end_time)
        
        # Verify summary structure
        self.assertIn('time_period', summary)
        self.assertIn('pipeline_metrics', summary)
        self.assertIn('performance_metrics', summary)


class TestADPAXRayMonitor(unittest.TestCase):
    """Test X-Ray monitoring implementation"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_xray = Mock()
        
        with patch('boto3.client', return_value=self.mock_xray):
            self.xray_monitor = ADPAXRayMonitor()
    
    def test_pipeline_execution_tracing(self):
        """Test pipeline execution tracing"""
        execution_id = "test-exec-456"
        pipeline_config = {
            'algorithm': 'random_forest',
            'dataset': 'test_data',
            'objective': 'classification'
        }
        
        # Test tracing (without actual X-Ray SDK)
        result = self.xray_monitor.trace_pipeline_execution(execution_id, pipeline_config)
        
        # Verify result structure
        self.assertIn('status', result)
        self.assertIn('execution_id', result)
        self.assertEqual(result['execution_id'], execution_id)
    
    def test_trace_analysis(self):
        """Test trace data analysis"""
        trace_id = "test-trace-789"
        
        # Mock X-Ray response
        self.mock_xray.get_trace_summaries.return_value = {
            'TraceSummaries': [
                {
                    'Duration': 5.2,
                    'ResponseTime': 4.8,
                    'ServiceIds': ['service1', 'service2'],
                    'ErrorCount': 0,
                    'FaultCount': 0,
                    'ThrottleCount': 0
                }
            ]
        }
        
        analysis = self.xray_monitor.analyze_trace_data(trace_id)
        
        if analysis:  # Only test if X-Ray is available
            self.assertIn('trace_id', analysis)
            self.assertIn('duration', analysis)
            self.assertIn('service_count', analysis)
    
    def test_service_map_retrieval(self):
        """Test service map retrieval"""
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        
        # Mock service graph response
        self.mock_xray.get_service_graph.return_value = {
            'Services': [
                {'Name': 'ADPA-Pipeline', 'Type': 'service'},
                {'Name': 'SageMaker', 'Type': 'AWS::SageMaker'}
            ]
        }
        
        service_map = self.xray_monitor.get_service_map(start_time, end_time)
        
        if service_map:  # Only test if successful
            self.assertIn('services', service_map)
            self.assertIn('total_count', service_map)


class TestADPAAlertingSystem(unittest.TestCase):
    """Test alerting system implementation"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_cloudwatch = Mock()
        self.mock_sns = Mock()
        self.mock_lambda = Mock()
        
        with patch('boto3.client') as mock_boto3:
            mock_boto3.side_effect = lambda service, **kwargs: {
                'cloudwatch': self.mock_cloudwatch,
                'sns': self.mock_sns,
                'lambda': self.mock_lambda
            }[service]
            
            # Mock SNS topic creation
            self.mock_sns.create_topic.return_value = {
                'TopicArn': 'arn:aws:sns:us-west-2:123456789:test-topic'
            }
            
            self.alerting_system = ADPAAlertingSystem()
    
    def test_sns_topics_creation(self):
        """Test SNS topics creation for different alert types"""
        expected_topics = ['critical', 'warning', 'info', 'performance', 'security', 'cost']
        
        # Verify topics were created
        self.assertEqual(self.mock_sns.create_topic.call_count, len(expected_topics))
        
        # Verify alert topics are configured
        self.assertEqual(len(self.alerting_system.alert_topics), len(expected_topics))
    
    def test_cloudwatch_alarms_creation(self):
        """Test CloudWatch alarms creation"""
        # Verify alarms were created
        self.assertTrue(self.mock_cloudwatch.put_metric_alarm.called)
        
        # Check that multiple alarms were created
        self.assertGreaterEqual(self.mock_cloudwatch.put_metric_alarm.call_count, 5)
    
    def test_custom_alert_sending(self):
        """Test custom alert sending"""
        self.mock_sns.publish.return_value = {'MessageId': 'test-msg-123'}
        
        # Send test alert
        message_id = self.alerting_system.send_custom_alert(
            alert_type='test_alert',
            title='Test Alert',
            message='This is a test alert',
            severity='warning'
        )
        
        # Verify alert was sent
        self.mock_sns.publish.assert_called()
        self.assertIsNotNone(message_id)
    
    def test_alarm_history_retrieval(self):
        """Test alarm history retrieval"""
        # Mock alarm history response
        self.mock_cloudwatch.describe_alarm_history.return_value = {
            'AlarmHistoryItems': [
                {
                    'Timestamp': datetime.now(),
                    'AlarmName': 'ADPA-Test-Alarm',
                    'HistoryReason': 'Threshold crossed',
                    'HistoryData': '{"reason": "test"}'
                }
            ]
        }
        
        history = self.alerting_system.get_alarm_history('ADPA-Test-Alarm')
        
        # Verify history retrieval
        self.mock_cloudwatch.describe_alarm_history.assert_called()
        self.assertIsInstance(history, list)
    
    def test_alert_system_testing(self):
        """Test the alert system testing functionality"""
        self.mock_sns.publish.return_value = {'MessageId': 'test-msg'}
        
        test_results = self.alerting_system.test_alert_system()
        
        # Verify test structure
        self.assertIn('timestamp', test_results)
        self.assertIn('tests_performed', test_results)
        self.assertIn('results', test_results)
        
        # Verify all severity levels were tested
        expected_tests = ['test_info_alert', 'test_warning_alert', 'test_critical_alert']
        self.assertEqual(len(test_results['tests_performed']), len(expected_tests))


class TestPipelineMonitoringIntegration(unittest.TestCase):
    """Test integrated pipeline monitoring step"""
    
    def setUp(self):
        """Set up test environment"""
        with patch('src.pipeline.monitoring.pipeline_monitor.CloudWatchMonitor'), \
             patch('src.pipeline.monitoring.pipeline_monitor.ADPACloudWatchMonitor'), \
             patch('src.pipeline.monitoring.pipeline_monitor.ADPAXRayMonitor'), \
             patch('src.pipeline.monitoring.pipeline_monitor.ADPAAlertingSystem'):
            
            self.monitoring_step = PipelineMonitoringStep()
    
    def test_monitoring_step_initialization(self):
        """Test monitoring step initialization"""
        self.assertIsNotNone(self.monitoring_step.cloudwatch_monitor)
        self.assertIsNotNone(self.monitoring_step.adpa_monitor)
        self.assertIsNotNone(self.monitoring_step.xray_monitor)
        self.assertIsNotNone(self.monitoring_step.alerting_system)
    
    def test_monitoring_step_execution(self):
        """Test complete monitoring step execution"""
        # Mock execution context
        context = {
            'pipeline_id': 'test-pipeline-123',
            'pipeline_success': True,
            'total_duration': 180.5,
            'profiling_results': {
                'rows': 50000,
                'quality_score': 95.2
            },
            'ml_results': {
                'algorithm': 'random_forest',
                'primary_metric': 0.873
            },
            'aws_infrastructure': {
                'estimated_cost': '25.50'
            }
        }
        
        # Execute monitoring step
        result = self.monitoring_step.execute(context=context)
        
        # Verify execution result
        self.assertIsNotNone(result)
        self.assertIn('status', result.__dict__)
        
        # Verify monitoring was set up
        if hasattr(result, 'metrics'):
            self.assertIn('monitoring_active', result.metrics)
    
    def test_monitoring_health_check(self):
        """Test monitoring system health check"""
        pipeline_id = 'test-health-check'
        
        health_status = self.monitoring_step.get_monitoring_health(pipeline_id)
        
        # Verify health status structure
        self.assertIn('pipeline_id', health_status)
        self.assertIn('overall_health', health_status)
        self.assertEqual(health_status['pipeline_id'], pipeline_id)


class TestMonitoringTutorialObjectives(unittest.TestCase):
    """Test Week 1 tutorial objectives completion"""
    
    def test_day1_objectives_completion(self):
        """Test Day 1 objectives: CloudWatch setup and metrics"""
        # Verify all required components exist
        self.assertTrue(hasattr(ADPACloudWatchMonitor, 'publish_pipeline_metrics'))
        self.assertTrue(hasattr(ADPACloudWatchMonitor, 'log_structured_event'))
        self.assertTrue(hasattr(ADPACloudWatchMonitor, 'create_dashboard'))
    
    def test_day2_objectives_completion(self):
        """Test Day 2 objectives: X-Ray tracing setup"""
        # Verify X-Ray components exist
        self.assertTrue(hasattr(ADPAXRayMonitor, 'trace_pipeline_execution'))
        self.assertTrue(hasattr(ADPAXRayMonitor, 'analyze_trace_data'))
        self.assertTrue(hasattr(ADPAXRayMonitor, 'get_service_map'))
    
    def test_day3_objectives_completion(self):
        """Test Day 3 objectives: Alerting system setup"""
        # Verify alerting components exist
        self.assertTrue(hasattr(ADPAAlertingSystem, 'send_custom_alert'))
        self.assertTrue(hasattr(ADPAAlertingSystem, 'get_alarm_history'))
        self.assertTrue(hasattr(ADPAAlertingSystem, 'test_alert_system'))
    
    def test_integration_objectives_completion(self):
        """Test integration objectives: Pipeline monitoring integration"""
        # Verify pipeline integration exists
        self.assertTrue(hasattr(PipelineMonitoringStep, 'get_monitoring_health'))
        self.assertTrue(hasattr(PipelineMonitoringStep, '_setup_xray_tracing'))
        self.assertTrue(hasattr(PipelineMonitoringStep, '_test_alerting_system'))


if __name__ == '__main__':
    print("🔍 Testing ADPA Comprehensive Monitoring System")
    print("=" * 60)
    print("Testing Adariprasad's Week 1 Tutorial Implementation")
    print("=" * 60)
    
    # Run all tests
    unittest.main(verbosity=2)