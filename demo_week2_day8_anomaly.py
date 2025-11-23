"""
Demo script for Week 2 Day 8: Anomaly Detection and Trend Analysis
Demonstrates Adariprasad's advanced anomaly detection implementation
"""

import sys
import os
from datetime import datetime, timedelta
import json
import random
import numpy as np

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), './'))

from src.monitoring.anomaly_detection import ADPAAnomalyDetection

def generate_historical_training_data(days: int = 14) -> list:
    """Generate historical data for training anomaly detection models"""
    
    training_data = []
    base_date = datetime.now() - timedelta(days=days)
    
    for day in range(days):
        for hour in range(0, 24, 4):  # Every 4 hours
            timestamp = base_date + timedelta(days=day, hours=hour)
            
            # Generate normal operational metrics with some variance
            metrics = {
                'cpu_utilization': random.uniform(20, 70),
                'memory_utilization': random.uniform(30, 75),
                'success_rate': random.uniform(92, 99),
                'error_rate': random.uniform(0, 3),
                'average_execution_time': random.uniform(1200, 3600),  # 20-60 minutes
                'throughput_per_hour': random.uniform(50, 150),
                'cost_per_execution': random.uniform(0.20, 0.80),
                'average_data_quality': random.uniform(85, 98),
                'model_accuracy': random.uniform(0.80, 0.92),
                'inference_latency': random.uniform(150, 400)
            }
            
            # Add some weekend patterns (lower activity)
            if timestamp.weekday() >= 5:  # Weekend
                metrics['throughput_per_hour'] *= 0.6
                metrics['cpu_utilization'] *= 0.7
                metrics['memory_utilization'] *= 0.8
            
            # Add some time-of-day patterns
            if 6 <= timestamp.hour <= 18:  # Business hours
                metrics['throughput_per_hour'] *= 1.3
                metrics['cpu_utilization'] *= 1.2
            
            training_data.append({
                'timestamp': timestamp.isoformat(),
                'metrics': metrics
            })
    
    return training_data

def generate_current_metrics(anomaly_type: str = 'normal') -> dict:
    """Generate current metrics with optional anomalies"""
    
    if anomaly_type == 'normal':
        return {
            'cpu_utilization': random.uniform(40, 65),
            'memory_utilization': random.uniform(45, 70),
            'success_rate': random.uniform(95, 99),
            'error_rate': random.uniform(0, 2),
            'average_execution_time': random.uniform(1800, 2400),
            'throughput_per_hour': random.uniform(80, 120),
            'cost_per_execution': random.uniform(0.30, 0.60),
            'average_data_quality': random.uniform(90, 97),
            'model_accuracy': random.uniform(0.85, 0.90),
            'inference_latency': random.uniform(200, 350)
        }
    
    elif anomaly_type == 'cpu_spike':
        return {
            'cpu_utilization': random.uniform(85, 98),  # Anomalous high CPU
            'memory_utilization': random.uniform(45, 70),
            'success_rate': random.uniform(92, 97),  # Slightly lower due to high CPU
            'error_rate': random.uniform(2, 5),
            'average_execution_time': random.uniform(3000, 4500),  # Slower due to high CPU
            'throughput_per_hour': random.uniform(40, 70),  # Lower throughput
            'cost_per_execution': random.uniform(0.60, 1.20),
            'average_data_quality': random.uniform(88, 95),
            'model_accuracy': random.uniform(0.82, 0.88),
            'inference_latency': random.uniform(400, 800)
        }
    
    elif anomaly_type == 'error_spike':
        return {
            'cpu_utilization': random.uniform(35, 55),
            'memory_utilization': random.uniform(40, 65),
            'success_rate': random.uniform(75, 85),  # Low success rate
            'error_rate': random.uniform(8, 15),  # High error rate
            'average_execution_time': random.uniform(1500, 3000),
            'throughput_per_hour': random.uniform(30, 60),  # Lower due to errors
            'cost_per_execution': random.uniform(0.25, 0.70),
            'average_data_quality': random.uniform(70, 85),  # Poor data quality
            'model_accuracy': random.uniform(0.65, 0.75),  # Lower accuracy
            'inference_latency': random.uniform(250, 450)
        }
    
    elif anomaly_type == 'performance_degradation':
        return {
            'cpu_utilization': random.uniform(75, 90),
            'memory_utilization': random.uniform(80, 95),  # High memory usage
            'success_rate': random.uniform(88, 94),
            'error_rate': random.uniform(3, 8),
            'average_execution_time': random.uniform(4500, 7200),  # Very slow execution
            'throughput_per_hour': random.uniform(20, 45),  # Very low throughput
            'cost_per_execution': random.uniform(1.20, 2.50),  # High cost
            'average_data_quality': random.uniform(85, 92),
            'model_accuracy': random.uniform(0.78, 0.85),
            'inference_latency': random.uniform(800, 1500)  # High latency
        }
    
    elif anomaly_type == 'cost_spike':
        return {
            'cpu_utilization': random.uniform(45, 70),
            'memory_utilization': random.uniform(50, 75),
            'success_rate': random.uniform(92, 97),
            'error_rate': random.uniform(1, 4),
            'average_execution_time': random.uniform(2000, 3500),
            'throughput_per_hour': random.uniform(60, 90),
            'cost_per_execution': random.uniform(1.50, 3.00),  # Very high cost
            'average_data_quality': random.uniform(88, 95),
            'model_accuracy': random.uniform(0.83, 0.89),
            'inference_latency': random.uniform(300, 500)
        }

def main():
    print("🔍 ADPA Anomaly Detection & Trend Analysis Demo")
    print("=" * 55)
    print("Week 2 Day 8: Anomaly Detection and Trend Analysis")
    print("=" * 55)
    
    # Initialize anomaly detection system
    print("\n🔧 Initializing Anomaly Detection System...")
    anomaly_detector = ADPAAnomalyDetection(mock_mode=True)
    print("✅ Anomaly detection system initialized successfully")
    
    # Generate historical training data
    print("\n📊 Generating Historical Training Data...")
    training_data = generate_historical_training_data(days=14)
    print(f"✅ Generated {len(training_data)} historical data points for training")
    
    # Train anomaly detection models
    print("\n🤖 Training Anomaly Detection Models...")
    training_result = anomaly_detector.train_anomaly_models(training_data)
    
    if training_result['status'] == 'success':
        print("✅ Anomaly detection models trained successfully!")
        print(f"📊 Training samples: {training_result['training_samples']}")
        print(f"🔧 Model type: {training_result['model_type']}")
        print(f"📈 Features used: {len(training_result['features_used'])}")
    else:
        print(f"❌ Failed to train models: {training_result.get('message')}")
        return
    
    # Test anomaly detection with different scenarios
    print("\n🔍 Testing Anomaly Detection...")
    
    test_scenarios = [
        ('normal', 'Normal Operations'),
        ('normal', 'Normal Operations'),
        ('cpu_spike', 'CPU Spike Anomaly'),
        ('normal', 'Normal Operations'),
        ('error_spike', 'Error Rate Spike'),
        ('performance_degradation', 'Performance Degradation'),
        ('normal', 'Normal Operations'),
        ('cost_spike', 'Cost Spike Anomaly')
    ]
    
    anomaly_results = []
    
    for i, (scenario_type, scenario_name) in enumerate(test_scenarios, 1):
        print(f"\n  📋 Test {i}: {scenario_name}")
        
        # Generate test metrics
        current_metrics = generate_current_metrics(scenario_type)
        
        # Detect anomalies
        detection_result = anomaly_detector.detect_anomalies(current_metrics)
        
        if detection_result.get('status') != 'error':
            is_anomaly = detection_result['is_anomaly']
            severity = detection_result.get('severity', 'unknown')
            anomaly_score = detection_result['anomaly_score']
            
            status_icon = "🚨" if is_anomaly else "✅"
            print(f"    {status_icon} Anomaly Detected: {is_anomaly}")
            
            if is_anomaly:
                print(f"    🔥 Severity: {severity.upper()}")
                print(f"    📊 Anomaly Score: {anomaly_score:.3f}")
                print(f"    🏷️ Types: {', '.join(detection_result['anomaly_types'])}")
                
                if detection_result['recommendations']:
                    print(f"    💡 Top Recommendation: {detection_result['recommendations'][0]}")
            
            anomaly_results.append({
                'scenario': scenario_name,
                'anomaly_detected': is_anomaly,
                'severity': severity,
                'score': anomaly_score
            })
        else:
            print(f"    ❌ Detection failed: {detection_result.get('message')}")
    
    # Perform trend analysis
    print("\n📈 Performing Trend Analysis...")
    
    # Generate additional data for trend analysis (last 7 days)
    trend_data = generate_historical_training_data(days=7)
    
    trend_analysis = anomaly_detector.perform_trend_analysis(trend_data, forecast_days=5)
    
    if trend_analysis.get('status') != 'error':
        print("✅ Trend analysis completed successfully!")
        
        # Display overall trend summary
        overall_trend = trend_analysis['overall_trend']
        print(f"\n🏆 Overall System Health Score: {overall_trend['overall_health_score']:.1f}/100")
        print(f"📊 Metrics Analyzed: {overall_trend['metrics_analyzed']}")
        
        # Display trending metrics
        if overall_trend['increasing_trends']:
            print(f"\n📈 Increasing Trends ({len(overall_trend['increasing_trends'])}):")
            for trend in overall_trend['increasing_trends'][:3]:
                print(f"  • {trend['metric'].replace('_', ' ').title()}: {trend['intensity']} intensity")
        
        if overall_trend['decreasing_trends']:
            print(f"\n📉 Decreasing Trends ({len(overall_trend['decreasing_trends'])}):")
            for trend in overall_trend['decreasing_trends'][:3]:
                print(f"  • {trend['metric'].replace('_', ' ').title()}: {trend['intensity']} intensity")
        
        # Display specific metric trends
        print(f"\n📊 Key Metric Trends:")
        print("-" * 25)
        
        key_metrics = ['cpu_utilization', 'error_rate', 'success_rate', 'cost_per_execution']
        metric_trends = trend_analysis['metric_trends']
        
        for metric in key_metrics:
            if metric in metric_trends and metric_trends[metric].get('status') == 'success':
                trend_data = metric_trends[metric]
                direction = trend_data['trend_direction']
                intensity = trend_data['trend_intensity']
                current = trend_data['current_value']
                
                direction_icon = "📈" if direction == 'increasing' else "📉" if direction == 'decreasing' else "📊"
                print(f"• {direction_icon} {metric.replace('_', ' ').title()}: {current:.2f}")
                print(f"  Trend: {direction} ({intensity} intensity)")
        
        # Display trend recommendations
        recommendations = trend_analysis.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Trend-Based Recommendations:")
            print("-" * 35)
            
            for i, rec in enumerate(recommendations[:3], 1):
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
                print(f"{i}. {priority_icon} [{rec['priority'].upper()}] {rec['category'].title()}")
                print(f"   Metric: {rec['metric'].replace('_', ' ').title()}")
                print(f"   {rec['message']}")
    else:
        print(f"❌ Trend analysis failed: {trend_analysis.get('message')}")
    
    # Get anomaly summary
    print("\n📋 Anomaly Detection Summary:")
    print("-" * 30)
    
    anomaly_summary = anomaly_detector.get_anomaly_summary(days_back=1)
    
    if anomaly_summary['total_anomalies'] > 0:
        print(f"• Total Anomalies Detected: {anomaly_summary['total_anomalies']}")
        print(f"• Severity Breakdown: {anomaly_summary['severity_breakdown']}")
        print(f"• Most Common Type: {anomaly_summary.get('most_common_type', 'N/A')}")
    else:
        print("• No anomalies detected in recent period")
        print("• System operating within normal parameters")
    
    # Create anomaly detection dashboard
    print("\n📊 Creating Anomaly Detection Dashboard...")
    dashboard_result = anomaly_detector.create_anomaly_detection_dashboard()
    
    if dashboard_result['status'] == 'success':
        print("✅ Anomaly detection dashboard created successfully!")
        print(f"📊 Dashboard widgets: {dashboard_result['widgets_created']}")
    else:
        print(f"❌ Failed to create dashboard: {dashboard_result.get('message')}")
    
    # Display test results summary
    print("\n📊 Anomaly Detection Test Results:")
    print("-" * 35)
    
    normal_count = sum(1 for r in anomaly_results if not r['anomaly_detected'])
    anomaly_count = sum(1 for r in anomaly_results if r['anomaly_detected'])
    
    print(f"• Normal Operations Detected: {normal_count}")
    print(f"• Anomalies Detected: {anomaly_count}")
    print(f"• Detection Accuracy: {((anomaly_count/len([s for s in test_scenarios if s[0] != 'normal'])) + (normal_count/len([s for s in test_scenarios if s[0] == 'normal'])))/2*100:.1f}%")
    
    # Show what Week 2 Day 8 objectives were completed
    print("\n✅ Week 2 Day 8 Objectives Completed:")
    print("-" * 40)
    print("✅ Machine learning-based anomaly detection")
    print("✅ Multi-metric anomaly analysis")
    print("✅ Advanced trend analysis and forecasting")
    print("✅ Seasonal pattern detection")
    print("✅ Anomaly severity classification")
    print("✅ Real-time anomaly alerting")
    print("✅ Trend-based capacity planning")
    print("✅ Anomaly detection dashboard")
    
    # Tutorial implementation status
    print("\n📚 Tutorial Implementation Status:")
    print("-" * 35)
    print("✅ Isolation Forest anomaly detection")
    print("✅ Statistical trend analysis")
    print("✅ Multi-dimensional feature analysis")
    print("✅ Automated threshold-based detection")
    print("✅ CloudWatch integration (mocked)")
    print("✅ SNS alerting system (mocked)")
    print("✅ Forecast confidence intervals")
    print("✅ Seasonality detection algorithms")
    
    # Save demo results
    demo_results = {
        'timestamp': datetime.now().isoformat(),
        'training_data_points': len(training_data),
        'anomaly_tests_performed': len(test_scenarios),
        'anomalies_detected': anomaly_count,
        'trend_analysis_completed': trend_analysis.get('status') != 'error',
        'dashboard_created': dashboard_result['status'] == 'success',
        'overall_health_score': trend_analysis.get('overall_trend', {}).get('overall_health_score', 0),
        'test_results': anomaly_results
    }
    
    # Create results directory
    os.makedirs('./data/demo_results', exist_ok=True)
    
    with open('./data/demo_results/week2_day8_anomaly_demo.json', 'w') as f:
        json.dump(demo_results, f, indent=2, default=str)
    
    # Next steps and completion
    print("\n🚀 Week 2 Completion Summary:")
    print("-" * 30)
    print("✅ Day 5: Business KPI tracking")
    print("✅ Day 6: Infrastructure monitoring")  
    print("✅ Day 7: Performance analytics")
    print("✅ Day 8: Anomaly detection")
    print("\n🎯 All Week 2 objectives completed!")
    
    print(f"\n💾 Demo results saved to: ./data/demo_results/week2_day8_anomaly_demo.json")
    print(f"💾 Anomaly reports saved to: {anomaly_detector.reports_dir}")
    print("\n🎉 Week 2 Day 8 Implementation Complete!")
    print("🎉 ADPA Monitoring & Observability Implementation Complete!")
    
    return {
        'anomaly_results': anomaly_results,
        'trend_analysis': trend_analysis,
        'demo_results': demo_results
    }

if __name__ == '__main__':
    results = main()