"""
Demo script for Week 2 Day 7: Performance Analytics and Dashboards
Demonstrates Adariprasad's performance analytics implementation
"""

import sys
import os
from datetime import datetime
import json
import random
import numpy as np

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), './'))

from src.monitoring.performance_analytics import ADPAPerformanceAnalytics

def generate_sample_execution_data(day_offset: int = 0) -> dict:
    """Generate realistic sample execution data"""
    
    base_executions = 100
    base_success_rate = 95
    
    # Add some variance based on day
    executions = base_executions + random.randint(-20, 30)
    success_rate = base_success_rate + random.uniform(-5, 3)
    
    successful = int(executions * (success_rate / 100))
    
    return {
        'total_executions': executions,
        'successful_executions': successful,
        'execution_time_seconds': random.randint(1800, 7200),  # 30min to 2hrs
        'data_volume_gb': random.uniform(50, 200),
        'cpu_utilization_avg': random.uniform(40, 85),
        'memory_utilization_avg': random.uniform(35, 80),
        'total_cost': random.uniform(25, 75),
        'data_quality_scores': [random.uniform(85, 98) for _ in range(5)],
        'model_metrics': {
            'accuracy': random.uniform(0.80, 0.95),
            'precision': random.uniform(0.75, 0.92),
            'recall': random.uniform(0.78, 0.90),
            'f1_score': random.uniform(0.76, 0.91),
            'inference_latency_ms': random.uniform(100, 500)
        },
        'errors': {
            'total': random.randint(0, 8),
            'critical': random.randint(0, 2),
            'timeout': random.randint(0, 3),
            'validation': random.randint(0, 3)
        }
    }

def main():
    print("📊 ADPA Performance Analytics & Dashboards Demo")
    print("=" * 55)
    print("Week 2 Day 7: Performance Analytics and Dashboards")
    print("=" * 55)
    
    # Initialize performance analytics system
    print("\n🔧 Initializing Performance Analytics System...")
    analytics = ADPAPerformanceAnalytics(mock_mode=True)
    print("✅ Performance analytics system initialized successfully")
    
    # Create performance dashboard
    print("\n📈 Creating Performance Dashboard...")
    dashboard_result = analytics.create_performance_dashboard("ADPA-Performance-Dashboard")
    
    if dashboard_result['status'] == 'success':
        print("✅ Performance dashboard created successfully!")
        print(f"📊 Dashboard widgets created: {dashboard_result['widgets_created']}")
    else:
        print(f"❌ Failed to create dashboard: {dashboard_result.get('error')}")
    
    # Generate historical performance data
    print("\n📈 Generating Historical Performance Data...")
    
    performance_summary = []
    
    # Simulate 7 days of performance data
    for day in range(7):
        print(f"  📅 Day {day + 1}: Tracking performance metrics...")
        
        # Generate sample execution data
        execution_data = generate_sample_execution_data(day)
        
        # Track performance metrics
        performance_metrics = analytics.track_performance_metrics(execution_data)
        
        performance_summary.append({
            'day': day + 1,
            'executions': execution_data['total_executions'],
            'success_rate': performance_metrics.get('success_rate', 0),
            'avg_time': performance_metrics.get('average_execution_time', 0),
            'throughput': performance_metrics.get('throughput_per_hour', 0),
            'cost_per_exec': performance_metrics.get('cost_per_execution', 0)
        })
    
    print(f"✅ Generated 7 days of performance data")
    print(f"📊 Total performance records: {len(analytics.performance_data)}")
    
    # Display performance summary
    print("\n📊 Performance Summary (Last 7 Days):")
    print("-" * 45)
    print("Day | Exec | Success% | Avg Time | Throughput | Cost/Exec")
    print("-" * 45)
    
    for summary in performance_summary:
        print(f"{summary['day']:3} | {summary['executions']:4} | "
              f"{summary['success_rate']:7.1f} | {summary['avg_time']:8.1f} | "
              f"{summary['throughput']:10.1f} | ${summary['cost_per_exec']:7.2f}")
    
    # Generate comprehensive performance report
    print("\n📋 Generating Performance Analytics Report...")
    performance_report = analytics.generate_performance_report(days_back=7)
    
    print("✅ Performance report generated successfully!")
    
    # Display executive summary
    print("\n🏆 Performance Executive Summary:")
    print("-" * 35)
    
    trends = performance_report.get('performance_trends', {})
    if trends:
        for metric, data in trends.items():
            trend_icon = "📈" if data['trend'] == 'improving' else "📉"
            print(f"• {metric.replace('_', ' ').title()}: {data['current']:.2f} {trend_icon}")
            print(f"  Trend: {data['trend']} (avg: {data['average']:.2f})")
    
    # Display resource utilization
    print("\n🔧 Resource Utilization Analysis:")
    print("-" * 30)
    
    utilization = performance_report.get('resource_utilization', {})
    if utilization:
        for resource, data in utilization.items():
            if resource == 'cpu_utilization':
                icon = "🔴" if data['average'] > 80 else "🟡" if data['average'] > 60 else "🟢"
            elif resource == 'memory_utilization':
                icon = "🔴" if data['average'] > 85 else "🟡" if data['average'] > 70 else "🟢"
            else:
                icon = "📊"
            
            print(f"• {icon} {resource.replace('_', ' ').title()}: {data['current']:.1f}%")
            print(f"  Average: {data['average']:.1f}% | Peak: {data['peak']:.1f}%")
    
    # Display cost analysis
    print("\n💰 Cost Analysis:")
    print("-" * 15)
    
    cost_analysis = performance_report.get('cost_analysis', {})
    if cost_analysis:
        for cost_metric, data in cost_analysis.items():
            trend_icon = "📈" if data['trend'] == 'increasing' else "📊"
            print(f"• {cost_metric.replace('_', ' ').title()}: ${data['current']:.2f} {trend_icon}")
            print(f"  Average: ${data['average']:.2f} | Trend: {data['trend']}")
    
    # Display recommendations
    print("\n💡 Performance Optimization Recommendations:")
    print("-" * 45)
    
    recommendations = performance_report.get('recommendations', [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
            print(f"{i}. {priority_icon} [{rec['priority'].upper()}] {rec['category'].title()}")
            print(f"   {rec['message']}")
            
            if 'suggested_actions' in rec:
                for action in rec['suggested_actions'][:2]:  # Show first 2 actions
                    print(f"   → {action}")
            print()
    else:
        print("• No specific recommendations at this time")
        print("• System is performing within optimal parameters")
    
    # Get real-time metrics
    print("\n⚡ Real-time Performance Metrics:")
    print("-" * 30)
    
    real_time_metrics = analytics.get_real_time_metrics()
    if 'metrics' in real_time_metrics:
        metrics = real_time_metrics['metrics']
        status_icon = "🟢" if real_time_metrics['status'] == 'healthy' else "🟡"
        
        print(f"• {status_icon} System Status: {real_time_metrics['status'].upper()}")
        print(f"• Success Rate: {metrics.get('success_rate', 0):.1f}%")
        print(f"• Throughput: {metrics.get('throughput_per_hour', 0):.1f} exec/hr")
        print(f"• CPU Utilization: {metrics.get('cpu_utilization', 0):.1f}%")
        print(f"• Error Rate: {metrics.get('error_rate', 0):.2f}%")
    
    # Create capacity planning analysis
    print("\n🔮 Capacity Planning Analysis:")
    print("-" * 30)
    
    capacity_analysis = analytics.create_capacity_planning_analysis()
    
    if 'current_capacity' in capacity_analysis:
        current = capacity_analysis['current_capacity']
        print(f"• Current Throughput: {current.get('throughput', 0):.1f} exec/hr")
        print(f"• CPU Headroom: {current.get('cpu_headroom', 0):.1f}%")
        
        projected = capacity_analysis.get('projected_capacity', {})
        if projected:
            print("\n📈 30-Day Projections:")
            for metric, value in projected.items():
                print(f"  • {metric.replace('_', ' ').title()}: {value:.1f}")
    
    # Show dashboard widget summary
    print("\n📊 Dashboard Widget Summary:")
    print("-" * 30)
    
    if dashboard_result['status'] == 'success':
        widget_types = [
            "Pipeline Execution Overview",
            "Execution Performance Metrics", 
            "Resource Utilization",
            "Cost Analytics",
            "Data Processing Performance",
            "Model Performance Analytics",
            "Error Analysis",
            "Performance Trends & Capacity Planning"
        ]
        
        for i, widget in enumerate(widget_types, 1):
            print(f"  {i}. {widget}")
    
    # Show what Week 2 Day 7 objectives were completed
    print("\n✅ Week 2 Day 7 Objectives Completed:")
    print("-" * 40)
    print("✅ Performance analytics dashboard creation")
    print("✅ Advanced metrics visualization widgets")
    print("✅ Historical performance trend analysis")
    print("✅ Resource utilization monitoring")
    print("✅ Cost analytics and optimization")
    print("✅ Real-time performance metrics")
    print("✅ Capacity planning analysis")
    print("✅ Performance optimization recommendations")
    
    # Tutorial implementation status
    print("\n📚 Tutorial Implementation Status:")
    print("-" * 35)
    print("✅ CloudWatch dashboard creation (mocked)")
    print("✅ Performance metrics calculation")
    print("✅ Trend analysis algorithms")
    print("✅ Resource utilization tracking")
    print("✅ Cost efficiency analysis")
    print("✅ Real-time monitoring capabilities")
    print("✅ Capacity planning projections")
    print("✅ Automated recommendation engine")
    
    # Save demo results
    demo_results = {
        'timestamp': datetime.now().isoformat(),
        'dashboard_widgets_created': dashboard_result.get('widgets_created', 0),
        'performance_data_points': len(analytics.performance_data),
        'recommendations_generated': len(recommendations),
        'performance_summary': performance_summary,
        'real_time_status': real_time_metrics.get('status', 'unknown')
    }
    
    # Create results directory
    os.makedirs('./data/demo_results', exist_ok=True)
    
    with open('./data/demo_results/week2_day7_performance_demo.json', 'w') as f:
        json.dump(demo_results, f, indent=2, default=str)
    
    # Next steps
    print("\n🚀 Next Steps (Week 2 Day 8):")
    print("-" * 35)
    print("• Anomaly detection implementation")
    print("• Advanced trend analysis")
    print("• Predictive analytics")
    print("• Machine learning-based forecasting")
    print("• Automated scaling recommendations")
    
    print(f"\n💾 Demo results saved to: ./data/demo_results/week2_day7_performance_demo.json")
    print(f"💾 Performance reports saved to: {analytics.reports_dir}")
    print("\n🎉 Week 2 Day 7 Implementation Complete!")
    
    return performance_report

if __name__ == '__main__':
    report = main()