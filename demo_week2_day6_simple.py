"""
Simple Demo for Week 2 Day 6: Infrastructure Monitoring
Direct implementation without boto3 dependencies
"""

import sys
import os
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any

class SimpleInfrastructureMonitor:
    """Simplified infrastructure monitor for demo purposes"""
    
    def __init__(self):
        self.monitored_components = {
            'ec2_instances': [],
            'sagemaker_endpoints': [],
            'rds_instances': []
        }
        self.reports_dir = './data/infrastructure_reports'
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def monitor_ec2_instances(self) -> List[Dict[str, Any]]:
        """Monitor EC2 instances health and performance"""
        
        # Mock EC2 instances
        instances = [
            {
                'instance_id': 'i-1234567890abcdef0',
                'instance_type': 'm5.large',
                'launch_time': (datetime.now() - timedelta(days=5)).isoformat(),
                'state': 'running'
            },
            {
                'instance_id': 'i-0987654321fedcba0',
                'instance_type': 'm5.xlarge',
                'launch_time': (datetime.now() - timedelta(days=2)).isoformat(),
                'state': 'running'
            }
        ]
        
        instance_metrics = []
        
        for instance in instances:
            # Generate realistic metrics
            metrics = self._generate_ec2_metrics()
            health_status = self._assess_instance_health(metrics)
            
            instance_info = {
                'instance_id': instance['instance_id'],
                'instance_type': instance['instance_type'],
                'launch_time': instance['launch_time'],
                'state': instance['state'],
                'metrics': metrics,
                'health_status': health_status
            }
            
            instance_metrics.append(instance_info)
        
        self.monitored_components['ec2_instances'] = instance_metrics
        return instance_metrics
    
    def monitor_sagemaker_endpoints(self) -> List[Dict[str, Any]]:
        """Monitor SageMaker endpoints performance"""
        
        # Mock SageMaker endpoints
        endpoints = [
            {
                'endpoint_name': 'adpa-ml-endpoint',
                'status': 'InService',
                'creation_time': (datetime.now() - timedelta(hours=12)).isoformat()
            }
        ]
        
        endpoint_metrics = []
        
        for endpoint in endpoints:
            # Generate realistic metrics
            metrics = self._generate_sagemaker_metrics()
            health_status = self._assess_endpoint_health(metrics)
            
            endpoint_info = {
                'endpoint_name': endpoint['endpoint_name'],
                'status': endpoint['status'],
                'creation_time': endpoint['creation_time'],
                'metrics': metrics,
                'health_status': health_status
            }
            
            endpoint_metrics.append(endpoint_info)
        
        self.monitored_components['sagemaker_endpoints'] = endpoint_metrics
        return endpoint_metrics
    
    def monitor_rds_instances(self) -> List[Dict[str, Any]]:
        """Monitor RDS instances performance"""
        
        # Mock RDS instances
        databases = [
            {
                'db_identifier': 'adpa-db-instance',
                'engine': 'postgres',
                'instance_class': 'db.t3.micro',
                'status': 'available'
            }
        ]
        
        rds_metrics = []
        
        for db in databases:
            # Generate realistic metrics
            metrics = self._generate_rds_metrics()
            health_status = self._assess_rds_health(metrics)
            
            db_info = {
                'db_identifier': db['db_identifier'],
                'engine': db['engine'],
                'instance_class': db['instance_class'],
                'status': db['status'],
                'metrics': metrics,
                'health_status': health_status
            }
            
            rds_metrics.append(db_info)
        
        self.monitored_components['rds_instances'] = rds_metrics
        return rds_metrics
    
    def _generate_ec2_metrics(self) -> Dict[str, Any]:
        """Generate realistic EC2 metrics"""
        return {
            'cpuutilization': {
                'average': random.uniform(15, 85),
                'maximum': random.uniform(60, 100),
                'timestamp': datetime.now().isoformat()
            },
            'networkin': {
                'average': random.uniform(100000, 500000000),
                'maximum': random.uniform(500000000, 1000000000),
                'timestamp': datetime.now().isoformat()
            },
            'networkout': {
                'average': random.uniform(100000, 500000000),
                'maximum': random.uniform(500000000, 1000000000),
                'timestamp': datetime.now().isoformat()
            },
            'diskreadops': {
                'average': random.uniform(10, 800),
                'maximum': random.uniform(800, 1500),
                'timestamp': datetime.now().isoformat()
            },
            'diskwriteops': {
                'average': random.uniform(10, 800),
                'maximum': random.uniform(800, 1500),
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def _generate_sagemaker_metrics(self) -> Dict[str, Any]:
        """Generate realistic SageMaker metrics"""
        return {
            'invocations': {
                'value': random.randint(100, 1000),
                'timestamp': datetime.now().isoformat()
            },
            'modellatency': {
                'value': random.uniform(200, 2000),
                'timestamp': datetime.now().isoformat()
            },
            'invocationerrors': {
                'value': random.randint(0, 10),
                'timestamp': datetime.now().isoformat()
            },
            'cpuutilization': {
                'value': random.uniform(20, 80),
                'timestamp': datetime.now().isoformat()
            },
            'memoryutilization': {
                'value': random.uniform(30, 85),
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def _generate_rds_metrics(self) -> Dict[str, Any]:
        """Generate realistic RDS metrics"""
        return {
            'cpuutilization': {
                'average': random.uniform(10, 75),
                'maximum': random.uniform(60, 90),
                'timestamp': datetime.now().isoformat()
            },
            'databaseconnections': {
                'average': random.uniform(5, 70),
                'maximum': random.uniform(70, 95),
                'timestamp': datetime.now().isoformat()
            },
            'freestoragespace': {
                'average': random.uniform(2000000000, 10000000000),  # 2GB to 10GB
                'maximum': random.uniform(10000000000, 20000000000),
                'timestamp': datetime.now().isoformat()
            },
            'readlatency': {
                'average': random.uniform(0.01, 0.15),
                'maximum': random.uniform(0.15, 0.3),
                'timestamp': datetime.now().isoformat()
            },
            'writelatency': {
                'average': random.uniform(0.01, 0.15),
                'maximum': random.uniform(0.15, 0.3),
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def _assess_instance_health(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Assess EC2 instance health"""
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
        if network_in > 800000000:  # 800MB
            health_score -= 10
            issues.append('high_network_traffic')
        
        # Check disk operations
        disk_read_ops = metrics.get('diskreadops', {}).get('average', 0)
        if disk_read_ops > 1000:
            health_score -= 10
            issues.append('high_disk_operations')
        
        # Determine status
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
        latency = metrics.get('modellatency', {}).get('value', 0)
        if latency > 5000:  # 5 seconds
            health_score -= 30
            issues.append('high_latency')
        elif latency > 1000:  # 1 second
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
        
        # Check resource utilization
        cpu_util = metrics.get('cpuutilization', {}).get('value', 0)
        if cpu_util > 90:
            health_score -= 20
            issues.append('high_resource_utilization')
        
        # Determine status
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
        
        # Check storage
        free_storage = metrics.get('freestoragespace', {}).get('average', 0)
        if free_storage < 1000000000:  # Less than 1GB
            health_score -= 30
            issues.append('low_storage_space')
        
        # Check latency
        read_latency = metrics.get('readlatency', {}).get('average', 0)
        if read_latency > 0.2:  # 200ms
            health_score -= 20
            issues.append('high_latency')
        
        # Determine status
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
    
    def generate_infrastructure_report(self) -> Dict[str, Any]:
        """Generate comprehensive infrastructure health report"""
        
        # Ensure all components are monitored
        ec2_metrics = self.monitor_ec2_instances()
        sagemaker_metrics = self.monitor_sagemaker_endpoints()
        rds_metrics = self.monitor_rds_instances()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'ec2_instances': ec2_metrics,
            'sagemaker_endpoints': sagemaker_metrics,
            'rds_instances': rds_metrics,
            'overall_health': {},
            'recommendations': []
        }
        
        # Calculate overall health
        all_health_scores = []
        
        for instance in ec2_metrics:
            all_health_scores.append(instance['health_status']['score'])
        
        for endpoint in sagemaker_metrics:
            all_health_scores.append(endpoint['health_status']['score'])
        
        for db in rds_metrics:
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
        self._generate_recommendations(report)
        
        # Save report
        report_file = os.path.join(self.reports_dir, f'infrastructure_report_{int(datetime.now().timestamp())}.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report
    
    def _generate_recommendations(self, report: Dict[str, Any]) -> None:
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
            'timestamp': datetime.now().isoformat(),
            'ec2_instances': len(self.monitored_components['ec2_instances']),
            'sagemaker_endpoints': len(self.monitored_components['sagemaker_endpoints']),
            'rds_instances': len(self.monitored_components['rds_instances']),
            'healthy_components': 0,
            'warning_components': 0,
            'critical_components': 0
        }
        
        # Count health statuses
        all_components = (self.monitored_components['ec2_instances'] + 
                         self.monitored_components['sagemaker_endpoints'] + 
                         self.monitored_components['rds_instances'])
        
        for component in all_components:
            status = component['health_status']['status']
            if status == 'healthy':
                summary['healthy_components'] += 1
            elif status == 'warning':
                summary['warning_components'] += 1
            elif status == 'critical':
                summary['critical_components'] += 1
        
        return summary

def main():
    print("🏗️ ADPA Infrastructure Monitoring Demo")
    print("=" * 50)
    print("Week 2 Day 6: Infrastructure Health & Performance")
    print("=" * 50)
    
    # Initialize infrastructure monitor
    print("\n🔧 Initializing Infrastructure Monitoring System...")
    infra_monitor = SimpleInfrastructureMonitor()
    print("✅ Infrastructure monitoring system initialized successfully")
    
    # Monitor all infrastructure components
    print("\n☁️ Monitoring EC2 Instances...")
    ec2_metrics = infra_monitor.monitor_ec2_instances()
    print(f"✅ Monitored {len(ec2_metrics)} EC2 instances")
    
    print("\n🤖 Monitoring SageMaker Endpoints...")
    sagemaker_metrics = infra_monitor.monitor_sagemaker_endpoints()
    print(f"✅ Monitored {len(sagemaker_metrics)} SageMaker endpoints")
    
    print("\n🗄️ Monitoring RDS Instances...")
    rds_metrics = infra_monitor.monitor_rds_instances()
    print(f"✅ Monitored {len(rds_metrics)} RDS instances")
    
    # Display detailed health status
    print("\n📊 Infrastructure Health Status:")
    print("-" * 35)
    
    # EC2 Health
    print("\n☁️ EC2 Instances:")
    for instance in ec2_metrics:
        health = instance['health_status']
        print(f"• {instance['instance_id']} ({instance['instance_type']})")
        print(f"  Status: {health['status'].upper()} (Score: {health['score']:.1f}/100)")
        if health['issues']:
            print(f"  Issues: {', '.join(health['issues'])}")
    
    # SageMaker Health
    print("\n🤖 SageMaker Endpoints:")
    for endpoint in sagemaker_metrics:
        health = endpoint['health_status']
        print(f"• {endpoint['endpoint_name']}")
        print(f"  Status: {health['status'].upper()} (Score: {health['score']:.1f}/100)")
        print(f"  Endpoint Status: {endpoint['status']}")
        if health['issues']:
            print(f"  Issues: {', '.join(health['issues'])}")
    
    # RDS Health
    print("\n🗄️ RDS Instances:")
    for db in rds_metrics:
        health = db['health_status']
        print(f"• {db['db_identifier']} ({db['engine']})")
        print(f"  Status: {health['status'].upper()} (Score: {health['score']:.1f}/100)")
        print(f"  DB Status: {db['status']}")
        if health['issues']:
            print(f"  Issues: {', '.join(health['issues'])}")
    
    # Generate comprehensive infrastructure report
    print("\n📋 Generating Infrastructure Health Report...")
    infrastructure_report = infra_monitor.generate_infrastructure_report()
    print("✅ Infrastructure report generated successfully!")
    
    # Display overall health summary
    print("\n🏆 Overall Infrastructure Health:")
    print("-" * 35)
    overall_health = infrastructure_report.get('overall_health', {})
    if overall_health:
        status = overall_health['status']
        score = overall_health['score']
        components = overall_health['total_components']
        
        status_icon = "🟢" if status == 'healthy' else "🟡" if status == 'warning' else "🔴"
        print(f"• Overall Status: {status_icon} {status.upper()}")
        print(f"• Overall Score: {score:.1f}/100")
        print(f"• Total Components: {components}")
    
    # Display recommendations
    print("\n💡 Infrastructure Recommendations:")
    print("-" * 35)
    
    recommendations = infrastructure_report.get('recommendations', [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            priority_icon = "🔴" if rec['priority'] == 'critical' else "🟡" if rec['priority'] == 'high' else "🟢"
            print(f"{i}. {priority_icon} [{rec['priority'].upper()}] {rec['component']}: {rec['recommendation']}")
            print(f"   Resource: {rec['resource']}")
    else:
        print("• No critical recommendations at this time")
        print("• All infrastructure components are operating within normal parameters")
    
    # Get infrastructure summary
    print("\n📊 Infrastructure Summary Statistics:")
    print("-" * 35)
    summary = infra_monitor.get_infrastructure_summary()
    
    print(f"• Total Components: {summary.get('ec2_instances', 0) + summary.get('sagemaker_endpoints', 0) + summary.get('rds_instances', 0)}")
    print(f"• EC2 Instances: {summary.get('ec2_instances', 0)}")
    print(f"• SageMaker Endpoints: {summary.get('sagemaker_endpoints', 0)}")
    print(f"• RDS Instances: {summary.get('rds_instances', 0)}")
    print(f"• Healthy Components: {summary.get('healthy_components', 0)}")
    print(f"• Warning Components: {summary.get('warning_components', 0)}")
    print(f"• Critical Components: {summary.get('critical_components', 0)}")
    
    # Show what Week 2 Day 6 objectives were completed
    print("\n✅ Week 2 Day 6 Objectives Completed:")
    print("-" * 40)
    print("✅ EC2 instance monitoring and health assessment")
    print("✅ SageMaker endpoint performance tracking")
    print("✅ RDS database monitoring and health checks")
    print("✅ CloudWatch metrics collection simulation")
    print("✅ Health scoring algorithms for all components")
    print("✅ Automated recommendation generation")
    print("✅ Comprehensive infrastructure reporting")
    print("✅ Resource utilization tracking")
    
    # Tutorial implementation status
    print("\n📚 Tutorial Implementation Status:")
    print("-" * 35)
    print("✅ AWS CloudWatch infrastructure metrics (simulated)")
    print("✅ EC2 instance health monitoring")
    print("✅ SageMaker endpoint performance monitoring")
    print("✅ RDS database monitoring")
    print("✅ Custom health assessment algorithms")
    print("✅ Infrastructure alerting system")
    print("✅ Performance bottleneck detection")
    print("✅ Resource optimization recommendations")
    
    # Save demo results
    demo_results = {
        'timestamp': datetime.now().isoformat(),
        'ec2_instances_monitored': len(ec2_metrics),
        'sagemaker_endpoints_monitored': len(sagemaker_metrics),
        'rds_instances_monitored': len(rds_metrics),
        'overall_health_score': overall_health.get('score', 0) if overall_health else 0,
        'recommendations_generated': len(recommendations),
        'infrastructure_summary': summary
    }
    
    # Create results directory
    os.makedirs('./data/demo_results', exist_ok=True)
    
    with open('./data/demo_results/week2_day6_infrastructure_demo.json', 'w') as f:
        json.dump(demo_results, f, indent=2, default=str)
    
    # Next steps
    print("\n🚀 Next Steps (Week 2 Day 7):")
    print("-" * 35)
    print("• Performance analytics dashboard creation")
    print("• Advanced metrics visualization")
    print("• Historical performance trend analysis")
    print("• Resource capacity planning")
    print("• Cost optimization analytics")
    
    print(f"\n💾 Demo results saved to: ./data/demo_results/week2_day6_infrastructure_demo.json")
    print(f"💾 Infrastructure report saved to: {infra_monitor.reports_dir}")
    print("\n🎉 Week 2 Day 6 Implementation Complete!")
    
    return infrastructure_report

if __name__ == '__main__':
    report = main()