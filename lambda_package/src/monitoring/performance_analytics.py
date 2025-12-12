"""
Performance Analytics and Dashboards for ADPA
Implementation based on Adariprasad's monitoring tutorial Week 2 Day 7
"""

import json
import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# Mock AWS functionality for development
class MockCloudWatchClient:
    def put_dashboard(self, **kwargs):
        pass
    
    def put_metric_data(self, **kwargs):
        pass
    
    def get_metric_statistics(self, **kwargs):
        import random
        return {
            'Datapoints': [
                {
                    'Timestamp': datetime.now(),
                    'Average': random.uniform(10, 90),
                    'Maximum': random.uniform(50, 100),
                    'Sum': random.uniform(100, 1000)
                }
            ]
        }

class MockS3Client:
    def put_object(self, **kwargs):
        pass

class ADPAPerformanceAnalytics:
    """Comprehensive performance analytics and dashboard system"""
    
    def __init__(self, mock_mode: bool = True):
        self.logger = logging.getLogger(__name__)
        self.mock_mode = mock_mode
        
        if mock_mode:
            self.cloudwatch = MockCloudWatchClient()
            self.s3_client = MockS3Client()
        else:
            import boto3
            self.cloudwatch = boto3.client('cloudwatch')
            self.s3_client = boto3.client('s3')
        
        self.namespace = 'ADPA/Performance'
        self.reports_dir = Path('./data/performance_reports')
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Performance data storage
        self.performance_data = []
        self.dashboard_configs = {}
    
    def create_performance_dashboard(self, dashboard_name: str = "ADPA-Performance-Dashboard") -> Dict[str, Any]:
        """Create comprehensive performance analytics dashboard"""
        
        dashboard_body = {
            "widgets": [
                self._create_pipeline_overview_widget(),
                self._create_execution_metrics_widget(),
                self._create_resource_utilization_widget(),
                self._create_cost_analytics_widget(),
                self._create_data_processing_widget(),
                self._create_model_performance_widget(),
                self._create_error_analysis_widget(),
                self._create_trend_analysis_widget()
            ]
        }
        
        try:
            if self.mock_mode:
                # Save dashboard config locally for development
                dashboard_file = self.reports_dir / f'{dashboard_name}_config.json'
                with open(dashboard_file, 'w') as f:
                    json.dump(dashboard_body, f, indent=2, default=str)
                
                self.logger.info(f"Dashboard config saved locally: {dashboard_file}")
            else:
                response = self.cloudwatch.put_dashboard(
                    DashboardName=dashboard_name,
                    DashboardBody=json.dumps(dashboard_body)
                )
                self.logger.info(f"Created CloudWatch dashboard: {dashboard_name}")
            
            self.dashboard_configs[dashboard_name] = dashboard_body
            
            return {
                'status': 'success',
                'dashboard_name': dashboard_name,
                'widgets_created': len(dashboard_body['widgets'])
            }
            
        except Exception as e:
            self.logger.error(f"Error creating dashboard: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _create_pipeline_overview_widget(self) -> Dict[str, Any]:
        """Create pipeline execution overview widget"""
        return {
            "type": "metric",
            "x": 0, "y": 0,
            "width": 12, "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "PipelineExecutions", {"stat": "Sum"}],
                    [self.namespace, "SuccessRate", {"stat": "Average"}],
                    [self.namespace, "FailureRate", {"stat": "Average"}],
                    [self.namespace, "ExecutionDuration", {"stat": "Average"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": "us-west-2",
                "title": "Pipeline Execution Overview",
                "period": 300,
                "yAxis": {
                    "left": {"min": 0}
                }
            }
        }
    
    def _create_execution_metrics_widget(self) -> Dict[str, Any]:
        """Create execution performance metrics widget"""
        return {
            "type": "metric",
            "x": 12, "y": 0,
            "width": 12, "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "AverageProcessingTime", {"stat": "Average"}],
                    [self.namespace, "ThroughputPerHour", {"stat": "Sum"}],
                    [self.namespace, "DataVolumeProcessed", {"stat": "Sum"}],
                    [self.namespace, "QueueDepth", {"stat": "Average"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": "us-west-2",
                "title": "Execution Performance Metrics",
                "period": 300
            }
        }
    
    def _create_resource_utilization_widget(self) -> Dict[str, Any]:
        """Create resource utilization analytics widget"""
        return {
            "type": "metric",
            "x": 0, "y": 6,
            "width": 8, "height": 6,
            "properties": {
                "metrics": [
                    ["AWS/EC2", "CPUUtilization", "InstanceId", "i-1234567890"],
                    ["AWS/EC2", "NetworkIn", "InstanceId", "i-1234567890"],
                    ["AWS/EC2", "NetworkOut", "InstanceId", "i-1234567890"],
                    [self.namespace, "MemoryUtilization", {"stat": "Average"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": "us-west-2",
                "title": "Resource Utilization",
                "period": 300,
                "yAxis": {
                    "left": {"min": 0, "max": 100}
                }
            }
        }
    
    def _create_cost_analytics_widget(self) -> Dict[str, Any]:
        """Create cost analytics widget"""
        return {
            "type": "metric",
            "x": 8, "y": 6,
            "width": 8, "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "HourlyCost", {"stat": "Sum"}],
                    [self.namespace, "CostPerExecution", {"stat": "Average"}],
                    [self.namespace, "CostPerGB", {"stat": "Average"}],
                    [self.namespace, "EstimatedMonthlyCost", {"stat": "Average"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": "us-west-2",
                "title": "Cost Analytics",
                "period": 300
            }
        }
    
    def _create_data_processing_widget(self) -> Dict[str, Any]:
        """Create data processing performance widget"""
        return {
            "type": "metric",
            "x": 16, "y": 6,
            "width": 8, "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "DataIngestionRate", {"stat": "Sum"}],
                    [self.namespace, "DataValidationErrors", {"stat": "Sum"}],
                    [self.namespace, "DataQualityScore", {"stat": "Average"}],
                    [self.namespace, "ProcessingLatency", {"stat": "Average"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": "us-west-2",
                "title": "Data Processing Performance",
                "period": 300
            }
        }
    
    def _create_model_performance_widget(self) -> Dict[str, Any]:
        """Create model performance analytics widget"""
        return {
            "type": "metric",
            "x": 0, "y": 12,
            "width": 12, "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "ModelAccuracy", {"stat": "Average"}],
                    [self.namespace, "ModelPrecision", {"stat": "Average"}],
                    [self.namespace, "ModelRecall", {"stat": "Average"}],
                    [self.namespace, "ModelF1Score", {"stat": "Average"}],
                    [self.namespace, "InferenceLatency", {"stat": "Average"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": "us-west-2",
                "title": "Model Performance Analytics",
                "period": 300,
                "yAxis": {
                    "left": {"min": 0, "max": 1}
                }
            }
        }
    
    def _create_error_analysis_widget(self) -> Dict[str, Any]:
        """Create error analysis widget"""
        return {
            "type": "metric",
            "x": 12, "y": 12,
            "width": 12, "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "TotalErrors", {"stat": "Sum"}],
                    [self.namespace, "CriticalErrors", {"stat": "Sum"}],
                    [self.namespace, "TimeoutErrors", {"stat": "Sum"}],
                    [self.namespace, "ValidationErrors", {"stat": "Sum"}],
                    [self.namespace, "ErrorRate", {"stat": "Average"}]
                ],
                "view": "timeSeries",
                "stacked": True,
                "region": "us-west-2",
                "title": "Error Analysis",
                "period": 300
            }
        }
    
    def _create_trend_analysis_widget(self) -> Dict[str, Any]:
        """Create trend analysis widget"""
        return {
            "type": "metric",
            "x": 0, "y": 18,
            "width": 24, "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "PerformanceTrend", {"stat": "Average"}],
                    [self.namespace, "CapacityUtilization", {"stat": "Average"}],
                    [self.namespace, "GrowthRate", {"stat": "Average"}],
                    [self.namespace, "EfficiencyScore", {"stat": "Average"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": "us-west-2",
                "title": "Performance Trends & Capacity Planning",
                "period": 300
            }
        }
    
    def track_performance_metrics(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track comprehensive performance metrics"""
        
        timestamp = datetime.utcnow().isoformat()
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(execution_data)
        
        # Store performance data
        performance_record = {
            'timestamp': timestamp,
            'metrics': performance_metrics,
            'execution_data': execution_data
        }
        self.performance_data.append(performance_record)
        
        # Publish to CloudWatch
        self._publish_performance_metrics(performance_metrics, timestamp)
        
        return performance_metrics
    
    def _calculate_performance_metrics(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        
        metrics = {}
        
        # Execution performance metrics
        total_executions = execution_data.get('total_executions', 0)
        successful_executions = execution_data.get('successful_executions', 0)
        execution_time = execution_data.get('execution_time_seconds', 0)
        
        if total_executions > 0:
            metrics['success_rate'] = (successful_executions / total_executions) * 100
            metrics['failure_rate'] = ((total_executions - successful_executions) / total_executions) * 100
            metrics['average_execution_time'] = execution_time / total_executions
        
        # Throughput metrics
        data_volume = execution_data.get('data_volume_gb', 0)
        time_hours = execution_time / 3600 if execution_time else 1
        
        if time_hours > 0:
            metrics['throughput_per_hour'] = total_executions / time_hours
            metrics['data_processing_rate'] = data_volume / time_hours
        
        # Resource efficiency metrics
        cpu_usage = execution_data.get('cpu_utilization_avg', 0)
        memory_usage = execution_data.get('memory_utilization_avg', 0)
        
        metrics['resource_efficiency'] = 100 - ((cpu_usage + memory_usage) / 2)
        metrics['cpu_utilization'] = cpu_usage
        metrics['memory_utilization'] = memory_usage
        
        # Cost metrics
        total_cost = execution_data.get('total_cost', 0)
        if total_executions > 0:
            metrics['cost_per_execution'] = total_cost / total_executions
        if data_volume > 0:
            metrics['cost_per_gb'] = total_cost / data_volume
        
        # Data quality metrics
        data_quality_scores = execution_data.get('data_quality_scores', [])
        if data_quality_scores:
            metrics['average_data_quality'] = np.mean(data_quality_scores)
            metrics['data_quality_variance'] = np.var(data_quality_scores)
        
        # Model performance metrics
        model_metrics = execution_data.get('model_metrics', {})
        metrics.update({
            'model_accuracy': model_metrics.get('accuracy', 0),
            'model_precision': model_metrics.get('precision', 0),
            'model_recall': model_metrics.get('recall', 0),
            'model_f1_score': model_metrics.get('f1_score', 0),
            'inference_latency': model_metrics.get('inference_latency_ms', 0)
        })
        
        # Error analysis metrics
        errors = execution_data.get('errors', {})
        metrics.update({
            'total_errors': errors.get('total', 0),
            'critical_errors': errors.get('critical', 0),
            'timeout_errors': errors.get('timeout', 0),
            'validation_errors': errors.get('validation', 0)
        })
        
        if total_executions > 0:
            metrics['error_rate'] = (metrics['total_errors'] / total_executions) * 100
        
        return metrics
    
    def _publish_performance_metrics(self, metrics: Dict[str, Any], timestamp: str) -> None:
        """Publish performance metrics to CloudWatch"""
        
        metric_data = []
        
        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, (int, float)) and not np.isnan(metric_value):
                metric_data.append({
                    'MetricName': self._format_metric_name(metric_name),
                    'Dimensions': [
                        {'Name': 'Environment', 'Value': 'Production'},
                        {'Name': 'System', 'Value': 'ADPA'}
                    ],
                    'Unit': self._get_metric_unit(metric_name),
                    'Value': float(metric_value),
                    'Timestamp': timestamp
                })
        
        # Publish in batches
        batch_size = 20
        for i in range(0, len(metric_data), batch_size):
            batch = metric_data[i:i + batch_size]
            
            try:
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
                self.logger.info(f"Published {len(batch)} performance metrics to CloudWatch")
            except Exception as e:
                self.logger.error(f"Error publishing performance metrics: {e}")
    
    def _format_metric_name(self, metric_name: str) -> str:
        """Format metric name for CloudWatch"""
        return ''.join(word.capitalize() for word in metric_name.split('_'))
    
    def _get_metric_unit(self, metric_name: str) -> str:
        """Get appropriate unit for metric"""
        if 'rate' in metric_name or 'percentage' in metric_name:
            return 'Percent'
        elif 'time' in metric_name or 'latency' in metric_name:
            return 'Seconds'
        elif 'cost' in metric_name:
            return 'None'  # Currency
        elif 'count' in metric_name or 'errors' in metric_name:
            return 'Count'
        else:
            return 'None'
    
    def generate_performance_report(self, days_back: int = 7) -> Dict[str, Any]:
        """Generate comprehensive performance analytics report"""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)
        
        # Filter performance data for time range
        filtered_data = [
            record for record in self.performance_data
            if start_time <= datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00')) <= end_time
        ]
        
        report = {
            'report_period': f'{days_back} days',
            'generated_at': datetime.utcnow().isoformat(),
            'executive_summary': {},
            'performance_trends': {},
            'resource_utilization': {},
            'cost_analysis': {},
            'recommendations': [],
            'data_points': len(filtered_data)
        }
        
        if not filtered_data:
            report['message'] = 'No performance data available for the specified period'
            return report
        
        # Generate performance analysis
        self._analyze_performance_trends(filtered_data, report)
        self._analyze_resource_utilization(filtered_data, report)
        self._analyze_cost_efficiency(filtered_data, report)
        self._generate_performance_recommendations(report)
        
        # Save report
        report_file = self.reports_dir / f'performance_report_{int(time.time())}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Performance report saved: {report_file}")
        return report
    
    def _analyze_performance_trends(self, data: List[Dict[str, Any]], report: Dict[str, Any]) -> None:
        """Analyze performance trends"""
        
        if not data:
            return
        
        # Extract metrics over time
        df = pd.DataFrame([record['metrics'] for record in data])
        
        trends = {}
        
        for metric in ['success_rate', 'average_execution_time', 'throughput_per_hour', 'error_rate']:
            if metric in df.columns:
                values = df[metric].dropna()
                if len(values) > 1:
                    trend_slope = np.polyfit(range(len(values)), values, 1)[0]
                    trends[metric] = {
                        'current': float(values.iloc[-1]),
                        'average': float(values.mean()),
                        'trend': 'improving' if trend_slope > 0 else 'declining',
                        'trend_magnitude': abs(trend_slope)
                    }
        
        report['performance_trends'] = trends
    
    def _analyze_resource_utilization(self, data: List[Dict[str, Any]], report: Dict[str, Any]) -> None:
        """Analyze resource utilization patterns"""
        
        if not data:
            return
        
        df = pd.DataFrame([record['metrics'] for record in data])
        
        utilization = {}
        
        for metric in ['cpu_utilization', 'memory_utilization', 'resource_efficiency']:
            if metric in df.columns:
                values = df[metric].dropna()
                if not values.empty:
                    utilization[metric] = {
                        'current': float(values.iloc[-1]),
                        'average': float(values.mean()),
                        'peak': float(values.max()),
                        'minimum': float(values.min())
                    }
        
        report['resource_utilization'] = utilization
    
    def _analyze_cost_efficiency(self, data: List[Dict[str, Any]], report: Dict[str, Any]) -> None:
        """Analyze cost efficiency"""
        
        if not data:
            return
        
        df = pd.DataFrame([record['metrics'] for record in data])
        
        cost_analysis = {}
        
        for metric in ['cost_per_execution', 'cost_per_gb']:
            if metric in df.columns:
                values = df[metric].dropna()
                if not values.empty:
                    cost_analysis[metric] = {
                        'current': float(values.iloc[-1]),
                        'average': float(values.mean()),
                        'trend': 'increasing' if len(values) > 1 and np.polyfit(range(len(values)), values, 1)[0] > 0 else 'stable'
                    }
        
        report['cost_analysis'] = cost_analysis
    
    def _generate_performance_recommendations(self, report: Dict[str, Any]) -> None:
        """Generate performance optimization recommendations"""
        
        recommendations = []
        
        # Performance trend recommendations
        trends = report.get('performance_trends', {})
        
        if 'success_rate' in trends and trends['success_rate']['current'] < 95:
            recommendations.append({
                'category': 'reliability',
                'priority': 'high',
                'message': f"Success rate is {trends['success_rate']['current']:.1f}%. Investigate and improve error handling.",
                'suggested_actions': [
                    'Review error logs and failure patterns',
                    'Implement additional retry mechanisms',
                    'Enhance monitoring and alerting'
                ]
            })
        
        if 'error_rate' in trends and trends['error_rate']['current'] > 5:
            recommendations.append({
                'category': 'quality',
                'priority': 'high',
                'message': f"Error rate is {trends['error_rate']['current']:.1f}%. Focus on error reduction.",
                'suggested_actions': [
                    'Implement more robust error handling',
                    'Improve input validation',
                    'Add circuit breaker patterns'
                ]
            })
        
        # Resource utilization recommendations
        utilization = report.get('resource_utilization', {})
        
        if 'cpu_utilization' in utilization and utilization['cpu_utilization']['average'] > 80:
            recommendations.append({
                'category': 'performance',
                'priority': 'medium',
                'message': f"High CPU utilization ({utilization['cpu_utilization']['average']:.1f}%). Consider scaling.",
                'suggested_actions': [
                    'Scale up instance types',
                    'Implement horizontal scaling',
                    'Optimize CPU-intensive operations'
                ]
            })
        
        # Cost optimization recommendations
        cost_analysis = report.get('cost_analysis', {})
        
        if 'cost_per_execution' in cost_analysis and cost_analysis['cost_per_execution']['trend'] == 'increasing':
            recommendations.append({
                'category': 'cost_optimization',
                'priority': 'medium',
                'message': 'Execution costs are increasing. Review resource utilization.',
                'suggested_actions': [
                    'Analyze resource usage patterns',
                    'Consider spot instances',
                    'Optimize processing algorithms'
                ]
            })
        
        report['recommendations'] = recommendations
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics"""
        
        if not self.performance_data:
            return {'message': 'No performance data available'}
        
        # Get latest metrics
        latest_record = self.performance_data[-1]
        
        return {
            'timestamp': latest_record['timestamp'],
            'metrics': latest_record['metrics'],
            'status': 'healthy' if latest_record['metrics'].get('success_rate', 0) > 95 else 'warning'
        }
    
    def create_capacity_planning_analysis(self) -> Dict[str, Any]:
        """Create capacity planning analysis"""
        
        if len(self.performance_data) < 2:
            return {'message': 'Insufficient data for capacity planning'}
        
        # Analyze growth trends
        df = pd.DataFrame([record['metrics'] for record in self.performance_data])
        
        analysis = {
            'current_capacity': {},
            'projected_capacity': {},
            'recommendations': []
        }
        
        # Current capacity analysis
        if 'throughput_per_hour' in df.columns:
            current_throughput = df['throughput_per_hour'].iloc[-1] if not df['throughput_per_hour'].empty else 0
            analysis['current_capacity']['throughput'] = current_throughput
        
        if 'cpu_utilization' in df.columns:
            current_cpu = df['cpu_utilization'].iloc[-1] if not df['cpu_utilization'].empty else 0
            analysis['current_capacity']['cpu_headroom'] = 100 - current_cpu
        
        # Projected capacity (simple linear projection)
        if len(df) > 5:
            for metric in ['throughput_per_hour', 'cpu_utilization']:
                if metric in df.columns:
                    values = df[metric].dropna()
                    if len(values) > 1:
                        trend = np.polyfit(range(len(values)), values, 1)[0]
                        projected_30_days = values.iloc[-1] + (trend * 30)
                        analysis['projected_capacity'][f'{metric}_30_days'] = projected_30_days
        
        return analysis