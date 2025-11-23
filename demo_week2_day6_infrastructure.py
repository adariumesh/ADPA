"""
Demo script for Week 2 Day 6: Infrastructure Monitoring
Demonstrates Adariprasad's infrastructure monitoring implementation
"""

import sys
import os
from datetime import datetime
import json

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), './'))

from src.monitoring.infrastructure_monitor import ADPAInfrastructureMonitor

def main():
    print("🏗️ ADPA Infrastructure Monitoring Demo")
    print("=" * 50)
    print("Week 2 Day 6: Infrastructure Health & Performance")
    print("=" * 50)
    
    # Initialize infrastructure monitor in mock mode
    print("\n🔧 Initializing Infrastructure Monitoring System...")
    infra_monitor = ADPAInfrastructureMonitor(mock_mode=True)
    print("✅ Infrastructure monitoring system initialized successfully")
    
    # Monitor EC2 instances
    print("\n☁️ Monitoring EC2 Instances...")
    ec2_metrics = infra_monitor.monitor_ec2_instances()
    print(f"✅ Monitored {len(ec2_metrics)} EC2 instances")
    
    # Display EC2 health status
    print("\n📊 EC2 Instance Health:")
    print("-" * 25)
    for instance in ec2_metrics:
        health = instance['health_status']
        print(f"• {instance['instance_id']} ({instance['instance_type']})")
        print(f"  Status: {health['status'].upper()} (Score: {health['score']}/100)")
        if health['issues']:
            print(f"  Issues: {', '.join(health['issues'])}")
        else:
            print("  Issues: None")
    
    # Monitor SageMaker endpoints
    print("\n🤖 Monitoring SageMaker Endpoints...")
    sagemaker_metrics = infra_monitor.monitor_sagemaker_endpoints()
    print(f"✅ Monitored {len(sagemaker_metrics)} SageMaker endpoints")
    
    # Display SageMaker health status
    print("\n📊 SageMaker Endpoint Health:")
    print("-" * 30)
    for endpoint in sagemaker_metrics:
        health = endpoint['health_status']
        print(f"• {endpoint['endpoint_name']}")
        print(f"  Status: {health['status'].upper()} (Score: {health['score']}/100)")
        print(f"  Endpoint Status: {endpoint['status']}")
        if health['issues']:
            print(f"  Issues: {', '.join(health['issues'])}")
        else:
            print("  Issues: None")
    
    # Monitor RDS instances
    print("\n🗄️ Monitoring RDS Instances...")
    rds_metrics = infra_monitor.monitor_rds_instances()
    print(f"✅ Monitored {len(rds_metrics)} RDS instances")
    
    # Display RDS health status
    print("\n📊 RDS Instance Health:")
    print("-" * 23)
    for db in rds_metrics:
        health = db['health_status']
        print(f"• {db['db_identifier']} ({db['engine']})")
        print(f"  Status: {health['status'].upper()} (Score: {health['score']}/100)")
        print(f"  DB Status: {db['status']}")
        if health['issues']:
            print(f"  Issues: {', '.join(health['issues'])}")
        else:
            print("  Issues: None")
    
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
        print(f"• Overall Status: {status.upper()}")
        print(f"• Overall Score: {score:.1f}/100")
        print(f"• Total Components: {components}")
    
    # Display key metrics
    print("\n📈 Key Infrastructure Metrics:")
    print("-" * 30)
    
    # Sample metrics from each component type
    if ec2_metrics:
        ec2_sample = ec2_metrics[0]
        cpu_util = ec2_sample['metrics'].get('cpuutilization', {}).get('average', 0)
        print(f"• EC2 CPU Utilization: {cpu_util:.1f}%")
    
    if sagemaker_metrics:
        sm_sample = sagemaker_metrics[0]
        latency = sm_sample['metrics'].get('modellatency', {}).get('value', 0)
        print(f"• SageMaker Model Latency: {latency:.1f}ms")
    
    if rds_metrics:
        rds_sample = rds_metrics[0]
        rds_cpu = rds_sample['metrics'].get('cpuutilization', {}).get('average', 0)
        print(f"• RDS CPU Utilization: {rds_cpu:.1f}%")
    
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
    print("✅ CloudWatch metrics collection for infrastructure")
    print("✅ Health scoring algorithms for all components")
    print("✅ Automated recommendation generation")
    print("✅ Comprehensive infrastructure reporting")
    print("✅ Resource utilization tracking")
    
    # Tutorial implementation status
    print("\n📚 Tutorial Implementation Status:")
    print("-" * 35)
    print("✅ AWS CloudWatch infrastructure metrics (mocked)")
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
    print("💾 Infrastructure report saved to: ./data/kpi_reports/")
    print("\n🎉 Week 2 Day 6 Implementation Complete!")
    
    return infrastructure_report

if __name__ == '__main__':
    report = main()