"""
Infrastructure Monitoring for ADPA
Implementation based on Adariprasad's monitoring tutorial Week 2 Day 6
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class MockAWSClient:
    """Mock AWS client for development"""
    def describe_instances(self, **kwargs):
        return {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-1234567890abcdef0',
                            'InstanceType': 'm5.large',
                            'LaunchTime': datetime.now() - timedelta(days=5),
                            'State': {'Name': 'running'}
                        },
                        {
                            'InstanceId': 'i-0987654321fedcba0',
                            'InstanceType': 'm5.xlarge',
                            'LaunchTime': datetime.now() - timedelta(days=2),
                            'State': {'Name': 'running'}
                        }
                    ]
                }
            ]
        }

    def describe_endpoints(self, **kwargs):
        return {
            'Endpoints': [
                {
                    'EndpointName': 'adpa-ml-endpoint',
                    'EndpointStatus': 'InService',
                    'CreationTime': datetime.now() - timedelta(hours=12)
                }
            ]
        }

    def describe_db_instances(self, **kwargs):
        return {
            'DBInstances': [
                {
                    'DBInstanceIdentifier': 'adpa-db-instance',
                    'Engine': 'postgres',
                    'DBInstanceClass': 'db.t3.micro',
                    'DBInstanceStatus': 'available'
                }
            ]
        }

    def get_metric_statistics(self, **kwargs):
        import random
        return {
            'Datapoints': [
                {
                    'Timestamp': datetime.now(),
                    'Average': random.uniform(10, 90),
                    'Maximum': random.uniform(50, 100)
                }
            ]
        }

    def put_metric_data(self, **kwargs):
        pass


class ADPAInfrastructureMonitor:
    """Comprehensive infrastructure monitoring for ADPA"""
    
    def __init__(self, mock_mode: bool = True):
        self.logger = logging.getLogger(__name__)
        self.mock_mode = mock_mode
        
        if mock_mode:
            # Use mock clients for development/testing
            self.cloudwatch = MockAWSClient()
            self.ec2 = MockAWSClient()
            self.rds = MockAWSClient()
            self.s3 = MockAWSClient()
            self.lambda_client = MockAWSClient()
            self.sagemaker = MockAWSClient()
            self.application_autoscaling = MockAWSClient()
        else:
            # Use real AWS clients (requires boto3)
            import boto3
            self.cloudwatch = boto3.client('cloudwatch')
            self.ec2 = boto3.client('ec2')
            self.rds = boto3.client('rds')
            self.s3 = boto3.client('s3')
            self.lambda_client = boto3.client('lambda')
            self.sagemaker = boto3.client('sagemaker')
            self.application_autoscaling = boto3.client('application-autoscaling')
    
    def monitor_ec2_instances(self) -> List[Dict[str, Any]]:
        """Monitor EC2 instances health and performance"""
        
        try:
            # Get all ADPA EC2 instances
            if self.mock_mode:
                response = self.ec2.describe_instances()
            else:
                response = self.ec2.describe_instances(
                    Filters=[
                        {'Name': 'tag:Project', 'Values': ['ADPA']},
                        {'Name': 'instance-state-name', 'Values': ['running']}
                    ]
                )
            
            instance_metrics = []
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_type = instance['InstanceType']
                    
                    # Get CloudWatch metrics for instance
                    metrics = self._get_ec2_metrics(instance_id)
                    
                    instance_info = {
                        'instance_id': instance_id,
                        'instance_type': instance_type,
                        'launch_time': instance['LaunchTime'].isoformat(),
                        'state': instance['State']['Name'],
                        'metrics': metrics,
                        'health_status': self._assess_instance_health(metrics)
                    }
                    
                    instance_metrics.append(instance_info)
                    
                    # Publish custom metrics
                    self._publish_instance_metrics(instance_id, metrics)
            
            self.logger.info(f"Monitored {len(instance_metrics)} EC2 instances")
            return instance_metrics
            
        except Exception as e:
            self.logger.error(f"Error monitoring EC2 instances: {e}")
            return []
    
    def monitor_sagemaker_endpoints(self) -> List[Dict[str, Any]]:
        """Monitor SageMaker endpoints performance"""
        
        try:
            # List all ADPA SageMaker endpoints
            if self.mock_mode:
                response = self.sagemaker.describe_endpoints()
                endpoints = response['Endpoints']
            else:
                response = self.sagemaker.list_endpoints()
                endpoints = response['Endpoints']
            
            endpoint_metrics = []
            
            for endpoint_summary in endpoints:
                if self.mock_mode:
                    endpoint_name = endpoint_summary['EndpointName']
                    endpoint_details = endpoint_summary
                else:
                    endpoint_name = endpoint_summary['EndpointName']
                    
                    if 'adpa' not in endpoint_name.lower():
                        continue
                    
                    # Get endpoint details
                    endpoint_details = self.sagemaker.describe_endpoint(
                        EndpointName=endpoint_name
                    )
                
                # Get CloudWatch metrics
                metrics = self._get_sagemaker_metrics(endpoint_name)
                
                endpoint_info = {
                    'endpoint_name': endpoint_name,
                    'status': endpoint_details.get('EndpointStatus', 'Unknown'),
                    'creation_time': endpoint_details.get('CreationTime', datetime.now()).isoformat(),
                    'metrics': metrics,
                    'health_status': self._assess_endpoint_health(metrics)
                }
                
                endpoint_metrics.append(endpoint_info)
                
                # Publish custom metrics
                self._publish_endpoint_metrics(endpoint_name, metrics)
            
            self.logger.info(f"Monitored {len(endpoint_metrics)} SageMaker endpoints")
            return endpoint_metrics
            
        except Exception as e:
            self.logger.error(f"Error monitoring SageMaker endpoints: {e}")
            return []
    
    def monitor_rds_instances(self) -> List[Dict[str, Any]]:
        """Monitor RDS instances performance"""
        
        try:
            # Get RDS instances
            response = self.rds.describe_db_instances()
            
            rds_metrics = []
            
            for db_instance in response['DBInstances']:
                db_identifier = db_instance['DBInstanceIdentifier']
                
                if self.mock_mode or 'adpa' in db_identifier.lower():
                    # Get CloudWatch metrics
                    metrics = self._get_rds_metrics(db_identifier)
                    
                    db_info = {
                        'db_identifier': db_identifier,
                        'engine': db_instance['Engine'],
                        'instance_class': db_instance['DBInstanceClass'],
                        'status': db_instance['DBInstanceStatus'],
                        'metrics': metrics,
                        'health_status': self._assess_rds_health(metrics)
                    }
                    
                    rds_metrics.append(db_info)
                    
                    # Publish custom metrics
                    self._publish_rds_metrics(db_identifier, metrics)
            
            self.logger.info(f"Monitored {len(rds_metrics)} RDS instances")
            return rds_metrics
            
        except Exception as e:
            self.logger.error(f"Error monitoring RDS instances: {e}")
            return []
    
    def _get_ec2_metrics(self, instance_id: str) -> Dict[str, Any]:
        """Get comprehensive EC2 metrics"""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        metrics = {}
        
        metric_names = [
            'CPUUtilization',
            'NetworkIn',
            'NetworkOut',
            'DiskReadOps',
            'DiskWriteOps',
            'DiskReadBytes',
            'DiskWriteBytes'
        ]
        
        for metric_name in metric_names:
            try:
                if self.mock_mode:
                    response = self.cloudwatch.get_metric_statistics()
                else:
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName=metric_name,
                        Dimensions=[
                            {'Name': 'InstanceId', 'Value': instance_id}
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=300,
                        Statistics=['Average', 'Maximum']
                    )
                
                if response['Datapoints']:
                    latest_datapoint = max(response['Datapoints'], key=lambda x: x['Timestamp'])
                    metrics[metric_name.lower()] = {
                        'average': latest_datapoint.get('Average', 0),
                        'maximum': latest_datapoint.get('Maximum', 0),
                        'timestamp': latest_datapoint['Timestamp'].isoformat()
                    }
                else:
                    metrics[metric_name.lower()] = {'average': 0, 'maximum': 0, 'timestamp': None}
                    
            except Exception as e:
                self.logger.error(f"Error getting EC2 metric {metric_name} for {instance_id}: {e}")
                metrics[metric_name.lower()] = {'error': str(e)}
        
        return metrics
    
    def _get_sagemaker_metrics(self, endpoint_name: str) -> Dict[str, Any]:
        """Get SageMaker endpoint metrics"""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        metrics = {}
        
        metric_configs = [
            {'MetricName': 'Invocations', 'Statistic': 'Sum'},
            {'MetricName': 'InvocationsPerInstance', 'Statistic': 'Average'},
            {'MetricName': 'ModelLatency', 'Statistic': 'Average'},
            {'MetricName': 'OverheadLatency', 'Statistic': 'Average'},
            {'MetricName': 'InvocationErrors', 'Statistic': 'Sum'},
            {'MetricName': 'CPUUtilization', 'Statistic': 'Average'},
            {'MetricName': 'MemoryUtilization', 'Statistic': 'Average'}
        ]
        
        for config in metric_configs:
            try:
                if self.mock_mode:
                    response = self.cloudwatch.get_metric_statistics()
                else:
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace='AWS/SageMaker',
                        MetricName=config['MetricName'],
                        Dimensions=[
                            {'Name': 'EndpointName', 'Value': endpoint_name},
                            {'Name': 'VariantName', 'Value': 'AllTraffic'}
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=300,
                        Statistics=[config['Statistic']]
                    )
                
                if response['Datapoints']:
                    latest_datapoint = max(response['Datapoints'], key=lambda x: x['Timestamp'])
                    metrics[config['MetricName'].lower()] = {
                        'value': latest_datapoint.get(config['Statistic'], 0),
                        'timestamp': latest_datapoint['Timestamp'].isoformat()
                    }
                else:
                    metrics[config['MetricName'].lower()] = {'value': 0, 'timestamp': None}
                    
            except Exception as e:
                self.logger.error(f"Error getting SageMaker metric {config['MetricName']}: {e}")
                metrics[config['MetricName'].lower()] = {'error': str(e)}
        
        return metrics
    
    def _get_rds_metrics(self, db_identifier: str) -> Dict[str, Any]:
        """Get RDS metrics"""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        metrics = {}
        
        metric_names = [
            'CPUUtilization',
            'DatabaseConnections',
            'FreeStorageSpace',
            'ReadLatency',
            'WriteLatency',
            'ReadIOPS',
            'WriteIOPS'
        ]
        
        for metric_name in metric_names:
            try:
                if self.mock_mode:
                    response = self.cloudwatch.get_metric_statistics()
                else:
                    response = self.cloudwatch.get_metric_statistics(
                        Namespace='AWS/RDS',
                        MetricName=metric_name,
                        Dimensions=[
                            {'Name': 'DBInstanceIdentifier', 'Value': db_identifier}
                        ],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=300,
                        Statistics=['Average', 'Maximum']
                    )
                
                if response['Datapoints']:
                    latest_datapoint = max(response['Datapoints'], key=lambda x: x['Timestamp'])
                    metrics[metric_name.lower()] = {
                        'average': latest_datapoint.get('Average', 0),
                        'maximum': latest_datapoint.get('Maximum', 0),
                        'timestamp': latest_datapoint['Timestamp'].isoformat()
                    }
                else:
                    metrics[metric_name.lower()] = {'average': 0, 'maximum': 0, 'timestamp': None}
                    
            except Exception as e:
                self.logger.error(f"Error getting RDS metric {metric_name}: {e}")
                metrics[metric_name.lower()] = {'error': str(e)}
        
        return metrics
    
    def _assess_instance_health(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall instance health based on metrics"""
        
        health_score = 100
        issues = []
        
        # Check CPU utilization
        cpu_avg = metrics.get('cpuutilization', {}).get('average', 0)
        if cpu_avg > 90:
            health_score -= 30
            issues.append('high_cpu_utilization')
        elif cpu_avg > 80:
            health_score -= 15
            issues.append('elevated_cpu_utilization')
        
        # Check network metrics
        network_in = metrics.get('networkin', {}).get('average', 0)
        network_out = metrics.get('networkout', {}).get('average', 0)
        
        if network_in > 1000000000 or network_out > 1000000000:  # 1GB
            health_score -= 10
            issues.append('high_network_traffic')
        
        # Check disk operations
        disk_read_ops = metrics.get('diskreadops', {}).get('average', 0)
        disk_write_ops = metrics.get('diskwriteops', {}).get('average', 0)
        
        if disk_read_ops > 1000 or disk_write_ops > 1000:
            health_score -= 10
            issues.append('high_disk_operations')
        
        # Determine health status
        if health_score >= 90:
            status = 'healthy'
        elif health_score >= 70:
            status = 'warning'
        else:
            status = 'critical'
        
        return {
            'status': status,
            'score': health_score,
            'issues': issues
        }
    
    def _assess_endpoint_health(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Assess SageMaker endpoint health"""
        
        health_score = 100
        issues = []
        
        # Check latency
        model_latency = metrics.get('modellatency', {}).get('value', 0)
        if model_latency > 5000:  # 5 seconds
            health_score -= 30
            issues.append('high_latency')
        elif model_latency > 1000:  # 1 second
            health_score -= 15
            issues.append('elevated_latency')
        
        # Check error rate
        invocations = metrics.get('invocations', {}).get('value', 0)
        errors = metrics.get('invocationerrors', {}).get('value', 0)
        
        if invocations > 0:
            error_rate = (errors / invocations) * 100
            if error_rate > 5:
                health_score -= 25
                issues.append('high_error_rate')
            elif error_rate > 1:
                health_score -= 10
                issues.append('elevated_error_rate')
        
        # Check resource utilization
        cpu_util = metrics.get('cpuutilization', {}).get('value', 0)
        memory_util = metrics.get('memoryutilization', {}).get('value', 0)
        
        if cpu_util > 90 or memory_util > 90:
            health_score -= 20
            issues.append('high_resource_utilization')
        
        # Determine health status
        if health_score >= 90:
            status = 'healthy'
        elif health_score >= 70:
            status = 'warning'
        else:
            status = 'critical'
        
        return {
            'status': status,
            'score': health_score,
            'issues': issues
        }
    
    def _assess_rds_health(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Assess RDS instance health"""
        
        health_score = 100
        issues = []
        
        # Check CPU utilization
        cpu_util = metrics.get('cpuutilization', {}).get('average', 0)
        if cpu_util > 85:
            health_score -= 25
            issues.append('high_cpu_utilization')
        elif cpu_util > 70:
            health_score -= 10
            issues.append('elevated_cpu_utilization')
        
        # Check storage
        free_storage = metrics.get('freestoragespace', {}).get('average', 0)
        if free_storage < 1000000000:  # Less than 1GB
            health_score -= 30
            issues.append('low_storage_space')
        elif free_storage < 5000000000:  # Less than 5GB
            health_score -= 15
            issues.append('limited_storage_space')
        
        # Check latency
        read_latency = metrics.get('readlatency', {}).get('average', 0)
        write_latency = metrics.get('writelatency', {}).get('average', 0)
        
        if read_latency > 0.2 or write_latency > 0.2:  # 200ms
            health_score -= 20
            issues.append('high_latency')
        
        # Check connections
        connections = metrics.get('databaseconnections', {}).get('average', 0)
        if connections > 80:  # Assuming max connections around 100
            health_score -= 15
            issues.append('high_connection_count')
        
        # Determine health status
        if health_score >= 90:
            status = 'healthy'
        elif health_score >= 70:
            status = 'warning'
        else:
            status = 'critical'
        
        return {
            'status': status,
            'score': health_score,
            'issues': issues
        }
    
    def _publish_instance_metrics(self, instance_id: str, metrics: Dict[str, Any]) -> None:
        """Publish custom EC2 instance metrics"""
        
        # Overall health score
        health_score = self._assess_instance_health(metrics)['score']
        
        metric_data = [{
            'MetricName': 'InstanceHealthScore',
            'Dimensions': [
                {'Name': 'InstanceId', 'Value': instance_id}
            ],
            'Unit': 'Percent',
            'Value': health_score
        }]
        
        try:
            self.cloudwatch.put_metric_data(
                Namespace='ADPA/Infrastructure',
                MetricData=metric_data
            )
        except Exception as e:
            self.logger.error(f"Error publishing instance metrics: {e}")
    
    def _publish_endpoint_metrics(self, endpoint_name: str, metrics: Dict[str, Any]) -> None:
        """Publish custom SageMaker endpoint metrics"""
        
        # Overall health score
        health_score = self._assess_endpoint_health(metrics)['score']
        
        metric_data = [{
            'MetricName': 'EndpointHealthScore',
            'Dimensions': [
                {'Name': 'EndpointName', 'Value': endpoint_name}
            ],
            'Unit': 'Percent',
            'Value': health_score
        }]
        
        try:
            self.cloudwatch.put_metric_data(
                Namespace='ADPA/Infrastructure',
                MetricData=metric_data
            )
        except Exception as e:
            self.logger.error(f"Error publishing endpoint metrics: {e}")
    
    def _publish_rds_metrics(self, db_identifier: str, metrics: Dict[str, Any]) -> None:
        """Publish custom RDS metrics"""
        
        # Overall health score
        health_score = self._assess_rds_health(metrics)['score']
        
        metric_data = [{
            'MetricName': 'DatabaseHealthScore',
            'Dimensions': [
                {'Name': 'DBInstanceIdentifier', 'Value': db_identifier}
            ],
            'Unit': 'Percent',
            'Value': health_score
        }]
        
        try:
            self.cloudwatch.put_metric_data(
                Namespace='ADPA/Infrastructure',
                MetricData=metric_data
            )
        except Exception as e:
            self.logger.error(f"Error publishing RDS metrics: {e}")
    
    def generate_infrastructure_report(self) -> Dict[str, Any]:
        """Generate comprehensive infrastructure health report"""
        
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'ec2_instances': self.monitor_ec2_instances(),
            'sagemaker_endpoints': self.monitor_sagemaker_endpoints(),
            'rds_instances': self.monitor_rds_instances(),
            'overall_health': {},
            'recommendations': []
        }
        
        # Calculate overall health
        all_health_scores = []
        
        for instance in report['ec2_instances']:
            all_health_scores.append(instance['health_status']['score'])
        
        for endpoint in report['sagemaker_endpoints']:
            all_health_scores.append(endpoint['health_status']['score'])
        
        for db in report['rds_instances']:
            all_health_scores.append(db['health_status']['score'])
        
        if all_health_scores:
            overall_score = sum(all_health_scores) / len(all_health_scores)
            
            if overall_score >= 90:
                overall_status = 'healthy'
            elif overall_score >= 70:
                overall_status = 'warning'
            else:
                overall_status = 'critical'
            
            report['overall_health'] = {
                'status': overall_status,
                'score': overall_score,
                'total_components': len(all_health_scores)
            }
        
        # Generate recommendations
        self._generate_infrastructure_recommendations(report)
        
        return report
    
    def _generate_infrastructure_recommendations(self, report: Dict[str, Any]) -> None:
        """Generate infrastructure optimization recommendations"""
        
        recommendations = []
        
        # EC2 recommendations
        for instance in report['ec2_instances']:
            if 'high_cpu_utilization' in instance['health_status']['issues']:
                recommendations.append({
                    'component': 'EC2',
                    'resource': instance['instance_id'],
                    'issue': 'High CPU utilization',
                    'recommendation': 'Consider upgrading instance type or optimizing workload',
                    'priority': 'medium'
                })
        
        # SageMaker recommendations
        for endpoint in report['sagemaker_endpoints']:
            if 'high_latency' in endpoint['health_status']['issues']:
                recommendations.append({
                    'component': 'SageMaker',
                    'resource': endpoint['endpoint_name'],
                    'issue': 'High inference latency',
                    'recommendation': 'Optimize model or increase instance capacity',
                    'priority': 'high'
                })
        
        # RDS recommendations
        for db in report['rds_instances']:
            if 'low_storage_space' in db['health_status']['issues']:
                recommendations.append({
                    'component': 'RDS',
                    'resource': db['db_identifier'],
                    'issue': 'Low storage space',
                    'recommendation': 'Increase storage capacity immediately',
                    'priority': 'critical'
                })
        
        report['recommendations'] = recommendations
    
    def get_infrastructure_summary(self) -> Dict[str, Any]:
        """Get infrastructure summary statistics"""
        
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'ec2_instances': 0,
            'sagemaker_endpoints': 0,
            'rds_instances': 0,
            'healthy_components': 0,
            'warning_components': 0,
            'critical_components': 0
        }
        
        try:
            # Get counts
            ec2_instances = self.monitor_ec2_instances()
            sagemaker_endpoints = self.monitor_sagemaker_endpoints()
            rds_instances = self.monitor_rds_instances()
            
            summary['ec2_instances'] = len(ec2_instances)
            summary['sagemaker_endpoints'] = len(sagemaker_endpoints)
            summary['rds_instances'] = len(rds_instances)
            
            # Count health statuses
            all_components = ec2_instances + sagemaker_endpoints + rds_instances
            
            for component in all_components:
                status = component['health_status']['status']
                if status == 'healthy':
                    summary['healthy_components'] += 1
                elif status == 'warning':
                    summary['warning_components'] += 1
                elif status == 'critical':
                    summary['critical_components'] += 1
            
        except Exception as e:
            self.logger.error(f"Error getting infrastructure summary: {e}")
            summary['error'] = str(e)
        
        return summary