"""
Demo script for Week 2 Day 5: KPI Tracking System
Demonstrates Adariprasad's business metrics implementation
"""

import sys
import os
from datetime import datetime
import json

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), './'))

from src.monitoring.kpi_tracker import ADPABusinessMetrics

def main():
    print("🎯 ADPA Business KPI Tracking Demo")
    print("=" * 50)
    print("Week 2 Day 5: Custom Metrics and KPI Tracking")
    print("=" * 50)
    
    # Initialize KPI tracker in mock mode
    print("\n📊 Initializing KPI Tracking System...")
    kpi_tracker = ADPABusinessMetrics(mock_mode=True)
    print("✅ KPI tracking system initialized successfully")
    
    # Sample execution data for tracking
    print("\n📈 Tracking Sample Business KPIs...")
    
    sample_execution_data = {
        'total_executions': 150,
        'successful_executions': 143,
        'average_execution_time': 240,  # seconds
        'data_quality_scores': [95.5, 96.2, 94.8, 97.1, 95.9],
        'model_accuracies': [87.3, 86.9, 88.1, 87.7, 88.5],
        'total_compute_cost': 450.75,
        'total_processing_volume_gb': 2500,
        'uptime_percentage': 99.8,
        'mean_time_to_recovery_minutes': 15,
        'user_satisfaction_scores': [4.2, 4.5, 4.3, 4.1, 4.4],
        'features_released': 3,
        'experiments_completed': 12,
        'metadata': {
            'environment': 'production',
            'version': '2.1.0'
        }
    }
    
    # Track KPIs
    tracked_kpis = kpi_tracker.track_business_kpis(sample_execution_data)
    
    print("✅ Business KPIs tracked successfully!")
    print(f"📊 Tracked {len(tracked_kpis)} KPI metrics")
    
    # Display tracked KPIs
    print("\n📋 Tracked KPIs:")
    print("-" * 30)
    
    for kpi_name, kpi_value in tracked_kpis.items():
        if isinstance(kpi_value, float):
            print(f"• {kpi_name}: {kpi_value:.2f}")
        else:
            print(f"• {kpi_name}: {kpi_value}")
    
    # Generate additional sample data for trend analysis
    print("\n📈 Generating Sample Historical Data...")
    
    # Simulate data for the past 7 days
    import random
    for day in range(7):
        daily_data = {
            'total_executions': random.randint(140, 160),
            'successful_executions': random.randint(130, 155),
            'average_execution_time': random.randint(200, 300),
            'data_quality_scores': [random.uniform(90, 100) for _ in range(5)],
            'model_accuracies': [random.uniform(0.80, 0.90) for _ in range(5)],
            'total_compute_cost': random.uniform(400, 500),
            'total_processing_volume_gb': random.randint(2000, 3000),
            'uptime_percentage': random.uniform(99, 100),
            'metadata': {
                'day': day + 1,
                'environment': 'production'
            }
        }
        
        daily_kpis = kpi_tracker.track_business_kpis(daily_data)
    
    print(f"✅ Generated 7 days of historical KPI data")
    
    # Generate KPI report
    print("\n📊 Generating KPI Report...")
    kpi_report = kpi_tracker.generate_kpi_report(days_back=7)
    
    print("✅ KPI report generated successfully!")
    
    # Display executive summary
    print("\n🏆 Executive Summary:")
    print("-" * 25)
    
    exec_summary = kpi_report.get('executive_summary', {})
    for metric, value in exec_summary.items():
        print(f"• {metric.replace('_', ' ').title()}: {value}")
    
    # Display recommendations
    print("\n💡 Recommendations:")
    print("-" * 20)
    
    recommendations = kpi_report.get('recommendations', [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. [{rec['priority'].upper()}] {rec['category'].title()}: {rec['message']}")
            if 'suggested_actions' in rec:
                for action in rec['suggested_actions'][:2]:  # Show first 2 actions
                    print(f"   → {action}")
    else:
        print("• No specific recommendations at this time")
        print("• All metrics are within acceptable ranges")
    
    # Display KPI summary
    print("\n📈 Current KPI Summary:")
    print("-" * 25)
    
    kpi_summary = kpi_tracker.get_kpi_summary()
    
    if 'kpis' in kpi_summary:
        for kpi_name, stats in kpi_summary['kpis'].items():
            current = stats.get('current')
            if current is not None:
                print(f"• {kpi_name.replace('_', ' ').title()}: {current:.2f}")
    
    # Create KPI alarms (mock mode)
    print("\n⚠️ Setting up KPI Alarms...")
    kpi_tracker.create_kpi_alarms()
    print("✅ KPI alarms configured successfully")
    
    # Show what Week 2 Day 5 objectives were completed
    print("\n✅ Week 2 Day 5 Objectives Completed:")
    print("-" * 40)
    print("✅ Business KPI calculation system")
    print("✅ DynamoDB KPI storage (mocked)")
    print("✅ CloudWatch metrics publishing (mocked)")
    print("✅ KPI trend analysis and reporting")
    print("✅ Automated recommendations generation")
    print("✅ KPI alarm setup (mocked)")
    
    # Next steps
    print("\n🚀 Next Steps (Week 2 Day 6):")
    print("-" * 35)
    print("• Infrastructure monitoring setup")
    print("• EC2, SageMaker, RDS health monitoring")
    print("• Resource utilization tracking")
    print("• Performance bottleneck detection")
    
    # Save demo results
    demo_results = {
        'timestamp': datetime.now().isoformat(),
        'kpis_tracked': len(tracked_kpis),
        'sample_kpis': {k: v for k, v in list(tracked_kpis.items())[:5]},
        'report_summary': kpi_report.get('executive_summary', {}),
        'recommendations_count': len(recommendations)
    }
    
    # Create results directory
    os.makedirs('./data/demo_results', exist_ok=True)
    
    with open('./data/demo_results/week2_day5_kpi_demo.json', 'w') as f:
        json.dump(demo_results, f, indent=2, default=str)
    
    print(f"\n💾 Demo results saved to: ./data/demo_results/week2_day5_kpi_demo.json")
    print("\n🎉 Week 2 Day 5 Implementation Complete!")

if __name__ == '__main__':
    main()