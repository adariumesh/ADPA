"""
Anomaly Detection and Advanced Trend Analysis for ADPA
Implementation based on Adariprasad's monitoring tutorial Week 2 Day 8
"""

import json
import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

# Mock AWS functionality for development
class MockCloudWatchClient:
    def put_metric_data(self, **kwargs):
        pass
    
    def put_metric_alarm(self, **kwargs):
        pass

class MockSNSClient:
    def publish(self, **kwargs):
        pass

class ADPAAnomalyDetection:
    """Advanced anomaly detection and trend analysis system"""
    
    def __init__(self, mock_mode: bool = True):
        self.logger = logging.getLogger(__name__)
        self.mock_mode = mock_mode
        
        if mock_mode:
            self.cloudwatch = MockCloudWatchClient()
            self.sns = MockSNSClient()
        else:
            import boto3
            self.cloudwatch = boto3.client('cloudwatch')
            self.sns = boto3.client('sns')
        
        self.namespace = 'ADPA/AnomalyDetection'
        self.reports_dir = Path('./data/anomaly_reports')
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Anomaly detection models
        self.isolation_forest = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Data storage
        self.historical_data = []
        self.anomalies = []
        self.trend_forecasts = {}
        
        # Thresholds for different metrics
        self.thresholds = {
            'cpu_utilization': {'warning': 70, 'critical': 90},
            'memory_utilization': {'warning': 75, 'critical': 90},
            'error_rate': {'warning': 5, 'critical': 10},
            'response_time': {'warning': 2000, 'critical': 5000},
            'cost_per_execution': {'warning': 1.0, 'critical': 2.0}
        }
    
    def train_anomaly_models(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Train anomaly detection models on historical data"""
        
        if len(historical_data) < 10:
            return {'status': 'error', 'message': 'Insufficient data for training (minimum 10 records required)'}
        
        try:
            # Prepare training data
            training_features = self._extract_features_for_training(historical_data)
            
            if training_features.empty:
                return {'status': 'error', 'message': 'No valid features for training'}
            
            # Scale features
            scaled_features = self.scaler.fit_transform(training_features)
            
            # Train isolation forest
            self.isolation_forest.fit(scaled_features)
            self.is_trained = True
            
            # Store historical data
            self.historical_data = historical_data
            
            training_result = {
                'status': 'success',
                'training_samples': len(historical_data),
                'features_used': list(training_features.columns),
                'model_type': 'IsolationForest',
                'contamination_rate': 0.1,
                'trained_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Anomaly detection models trained successfully with {len(historical_data)} samples")
            return training_result
            
        except Exception as e:
            self.logger.error(f"Error training anomaly models: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _extract_features_for_training(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Extract features for anomaly detection training"""
        
        features = []
        
        for record in data:
            metrics = record.get('metrics', {})
            feature_row = {
                'cpu_utilization': metrics.get('cpu_utilization', 0),
                'memory_utilization': metrics.get('memory_utilization', 0),
                'success_rate': metrics.get('success_rate', 100),
                'error_rate': metrics.get('error_rate', 0),
                'average_execution_time': metrics.get('average_execution_time', 0),
                'throughput_per_hour': metrics.get('throughput_per_hour', 0),
                'cost_per_execution': metrics.get('cost_per_execution', 0),
                'data_quality_score': metrics.get('average_data_quality', 95),
                'model_accuracy': metrics.get('model_accuracy', 0.85),
                'inference_latency': metrics.get('inference_latency', 200)
            }
            features.append(feature_row)
        
        df = pd.DataFrame(features)
        
        # Remove columns with all zeros or NaN
        df = df.loc[:, (df != 0).any(axis=0)]
        df = df.dropna(axis=1, how='all')
        
        return df
    
    def detect_anomalies(self, current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Detect anomalies in current metrics"""
        
        if not self.is_trained:
            return {'status': 'error', 'message': 'Models not trained. Call train_anomaly_models() first.'}
        
        try:
            # Prepare features
            feature_row = self._extract_single_feature_row(current_metrics)
            
            if not feature_row:
                return {'status': 'error', 'message': 'Unable to extract features from metrics'}
            
            # Scale features
            feature_df = pd.DataFrame([feature_row])
            
            # Ensure all training columns are present
            training_columns = self.scaler.feature_names_in_ if hasattr(self.scaler, 'feature_names_in_') else range(self.scaler.n_features_in_)
            
            # Reorder and fill missing columns
            for col in training_columns:
                if col not in feature_df.columns:
                    feature_df[col] = 0
            
            feature_df = feature_df[training_columns]
            scaled_features = self.scaler.transform(feature_df)
            
            # Predict anomaly
            anomaly_score = self.isolation_forest.decision_function(scaled_features)[0]
            is_anomaly = self.isolation_forest.predict(scaled_features)[0] == -1
            
            # Detect specific anomaly types
            anomaly_details = self._analyze_specific_anomalies(current_metrics)
            
            # Create anomaly record
            anomaly_result = {
                'timestamp': datetime.now().isoformat(),
                'is_anomaly': bool(is_anomaly),
                'anomaly_score': float(anomaly_score),
                'confidence': abs(float(anomaly_score)),
                'severity': self._calculate_anomaly_severity(anomaly_score, anomaly_details),
                'anomaly_types': anomaly_details['types'],
                'affected_metrics': anomaly_details['affected_metrics'],
                'recommendations': self._generate_anomaly_recommendations(anomaly_details)
            }
            
            # Store anomaly if detected
            if is_anomaly:
                self.anomalies.append({
                    'detection_time': anomaly_result['timestamp'],
                    'metrics': current_metrics,
                    'anomaly_details': anomaly_result
                })
                
                # Send alert
                self._send_anomaly_alert(anomaly_result, current_metrics)
            
            # Publish metrics to CloudWatch
            self._publish_anomaly_metrics(anomaly_result)
            
            return anomaly_result
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _extract_single_feature_row(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from a single metrics record"""
        
        return {
            'cpu_utilization': float(metrics.get('cpu_utilization', 0)),
            'memory_utilization': float(metrics.get('memory_utilization', 0)),
            'success_rate': float(metrics.get('success_rate', 100)),
            'error_rate': float(metrics.get('error_rate', 0)),
            'average_execution_time': float(metrics.get('average_execution_time', 0)),
            'throughput_per_hour': float(metrics.get('throughput_per_hour', 0)),
            'cost_per_execution': float(metrics.get('cost_per_execution', 0)),
            'data_quality_score': float(metrics.get('average_data_quality', 95)),
            'model_accuracy': float(metrics.get('model_accuracy', 0.85)),
            'inference_latency': float(metrics.get('inference_latency', 200))
        }
    
    def _analyze_specific_anomalies(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze specific types of anomalies"""
        
        anomaly_types = []
        affected_metrics = []
        
        # CPU anomaly
        cpu_util = metrics.get('cpu_utilization', 0)
        if cpu_util > self.thresholds['cpu_utilization']['critical']:
            anomaly_types.append('critical_cpu_spike')
            affected_metrics.append('cpu_utilization')
        elif cpu_util > self.thresholds['cpu_utilization']['warning']:
            anomaly_types.append('high_cpu_usage')
            affected_metrics.append('cpu_utilization')
        
        # Memory anomaly
        memory_util = metrics.get('memory_utilization', 0)
        if memory_util > self.thresholds['memory_utilization']['critical']:
            anomaly_types.append('critical_memory_spike')
            affected_metrics.append('memory_utilization')
        elif memory_util > self.thresholds['memory_utilization']['warning']:
            anomaly_types.append('high_memory_usage')
            affected_metrics.append('memory_utilization')
        
        # Error rate anomaly
        error_rate = metrics.get('error_rate', 0)
        if error_rate > self.thresholds['error_rate']['critical']:
            anomaly_types.append('critical_error_rate')
            affected_metrics.append('error_rate')
        elif error_rate > self.thresholds['error_rate']['warning']:
            anomaly_types.append('elevated_error_rate')
            affected_metrics.append('error_rate')
        
        # Performance anomaly
        response_time = metrics.get('average_execution_time', 0) * 1000  # Convert to ms
        if response_time > self.thresholds['response_time']['critical']:
            anomaly_types.append('critical_performance_degradation')
            affected_metrics.append('response_time')
        elif response_time > self.thresholds['response_time']['warning']:
            anomaly_types.append('performance_degradation')
            affected_metrics.append('response_time')
        
        # Cost anomaly
        cost = metrics.get('cost_per_execution', 0)
        if cost > self.thresholds['cost_per_execution']['critical']:
            anomaly_types.append('critical_cost_spike')
            affected_metrics.append('cost_per_execution')
        elif cost > self.thresholds['cost_per_execution']['warning']:
            anomaly_types.append('cost_increase')
            affected_metrics.append('cost_per_execution')
        
        # Success rate anomaly
        success_rate = metrics.get('success_rate', 100)
        if success_rate < 80:
            anomaly_types.append('low_success_rate')
            affected_metrics.append('success_rate')
        
        # Model accuracy anomaly
        model_accuracy = metrics.get('model_accuracy', 0.85)
        if model_accuracy < 0.7:
            anomaly_types.append('model_accuracy_degradation')
            affected_metrics.append('model_accuracy')
        
        return {
            'types': anomaly_types,
            'affected_metrics': affected_metrics
        }
    
    def _calculate_anomaly_severity(self, anomaly_score: float, anomaly_details: Dict[str, Any]) -> str:
        """Calculate the severity of detected anomaly"""
        
        # Severity based on anomaly score
        if abs(anomaly_score) > 0.5:
            base_severity = 'high'
        elif abs(anomaly_score) > 0.3:
            base_severity = 'medium'
        else:
            base_severity = 'low'
        
        # Adjust based on specific anomaly types
        critical_types = ['critical_cpu_spike', 'critical_memory_spike', 'critical_error_rate', 
                         'critical_performance_degradation', 'critical_cost_spike']
        
        if any(atype in critical_types for atype in anomaly_details['types']):
            return 'critical'
        elif len(anomaly_details['types']) > 2:
            return 'high'
        else:
            return base_severity
    
    def _generate_anomaly_recommendations(self, anomaly_details: Dict[str, Any]) -> List[str]:
        """Generate recommendations for detected anomalies"""
        
        recommendations = []
        
        for anomaly_type in anomaly_details['types']:
            if 'cpu' in anomaly_type:
                recommendations.extend([
                    'Scale up instance types or add more instances',
                    'Optimize CPU-intensive operations',
                    'Enable auto-scaling based on CPU metrics'
                ])
            elif 'memory' in anomaly_type:
                recommendations.extend([
                    'Increase memory allocation',
                    'Optimize memory usage patterns',
                    'Implement memory caching strategies'
                ])
            elif 'error' in anomaly_type:
                recommendations.extend([
                    'Review error logs for root cause analysis',
                    'Implement additional error handling',
                    'Check data quality and validation'
                ])
            elif 'performance' in anomaly_type:
                recommendations.extend([
                    'Optimize algorithms and database queries',
                    'Review system bottlenecks',
                    'Consider performance profiling'
                ])
            elif 'cost' in anomaly_type:
                recommendations.extend([
                    'Review resource utilization efficiency',
                    'Consider spot instances or reserved capacity',
                    'Optimize processing schedules'
                ])
            elif 'success_rate' in anomaly_type:
                recommendations.extend([
                    'Investigate recent failures',
                    'Implement retry mechanisms',
                    'Review system dependencies'
                ])
            elif 'model_accuracy' in anomaly_type:
                recommendations.extend([
                    'Retrain model with recent data',
                    'Check for data drift',
                    'Review feature engineering'
                ])
        
        # Remove duplicates and limit recommendations
        return list(set(recommendations))[:5]
    
    def _send_anomaly_alert(self, anomaly_result: Dict[str, Any], metrics: Dict[str, Any]) -> None:
        """Send anomaly alert via SNS"""
        
        severity = anomaly_result['severity']
        anomaly_types = ', '.join(anomaly_result['anomaly_types'])
        
        message = f"""
ADPA Anomaly Alert - {severity.upper()} Severity

Timestamp: {anomaly_result['timestamp']}
Anomaly Score: {anomaly_result['anomaly_score']:.3f}
Confidence: {anomaly_result['confidence']:.3f}

Anomaly Types: {anomaly_types}
Affected Metrics: {', '.join(anomaly_result['affected_metrics'])}

Current Metrics:
- CPU Utilization: {metrics.get('cpu_utilization', 0):.1f}%
- Memory Utilization: {metrics.get('memory_utilization', 0):.1f}%
- Error Rate: {metrics.get('error_rate', 0):.2f}%
- Success Rate: {metrics.get('success_rate', 100):.1f}%

Recommendations:
{chr(10).join(f"- {rec}" for rec in anomaly_result['recommendations'][:3])}

Please investigate immediately.
"""
        
        try:
            if self.mock_mode:
                self.logger.info(f"Mock anomaly alert sent: {severity} severity")
            else:
                self.sns.publish(
                    TopicArn=f'arn:aws:sns:us-west-2:account:ADPA-{severity.title()}-Alerts',
                    Message=message,
                    Subject=f'ADPA Anomaly Alert - {severity.upper()}'
                )
                self.logger.info(f"Anomaly alert sent via SNS: {severity} severity")
                
        except Exception as e:
            self.logger.error(f"Error sending anomaly alert: {e}")
    
    def _publish_anomaly_metrics(self, anomaly_result: Dict[str, Any]) -> None:
        """Publish anomaly detection metrics to CloudWatch"""
        
        metric_data = [
            {
                'MetricName': 'AnomalyDetected',
                'Dimensions': [
                    {'Name': 'Environment', 'Value': 'Production'},
                    {'Name': 'System', 'Value': 'ADPA'}
                ],
                'Unit': 'Count',
                'Value': 1 if anomaly_result['is_anomaly'] else 0
            },
            {
                'MetricName': 'AnomalyScore',
                'Dimensions': [
                    {'Name': 'Environment', 'Value': 'Production'},
                    {'Name': 'System', 'Value': 'ADPA'}
                ],
                'Unit': 'None',
                'Value': abs(anomaly_result['anomaly_score'])
            },
            {
                'MetricName': 'AnomalyConfidence',
                'Dimensions': [
                    {'Name': 'Environment', 'Value': 'Production'},
                    {'Name': 'System', 'Value': 'ADPA'}
                ],
                'Unit': 'Percent',
                'Value': anomaly_result['confidence'] * 100
            }
        ]
        
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data
            )
            self.logger.info("Anomaly detection metrics published to CloudWatch")
        except Exception as e:
            self.logger.error(f"Error publishing anomaly metrics: {e}")
    
    def perform_trend_analysis(self, historical_data: List[Dict[str, Any]], forecast_days: int = 7) -> Dict[str, Any]:
        """Perform advanced trend analysis and forecasting"""
        
        if len(historical_data) < 5:
            return {'status': 'error', 'message': 'Insufficient data for trend analysis (minimum 5 records required)'}
        
        try:
            # Prepare time series data
            df = self._prepare_trend_data(historical_data)
            
            # Perform trend analysis for each metric
            trend_results = {}
            
            for metric in df.columns:
                if metric != 'timestamp':
                    trend_analysis = self._analyze_metric_trend(df, metric, forecast_days)
                    trend_results[metric] = trend_analysis
            
            # Generate overall trend summary
            overall_trend = self._generate_overall_trend_summary(trend_results)
            
            # Create forecast visualizations (metadata)
            forecast_metadata = self._create_forecast_metadata(trend_results)
            
            trend_report = {
                'analysis_timestamp': datetime.now().isoformat(),
                'data_points_analyzed': len(historical_data),
                'forecast_horizon_days': forecast_days,
                'overall_trend': overall_trend,
                'metric_trends': trend_results,
                'forecast_metadata': forecast_metadata,
                'recommendations': self._generate_trend_recommendations(trend_results)
            }
            
            # Save trend analysis
            self._save_trend_analysis(trend_report)
            
            return trend_report
            
        except Exception as e:
            self.logger.error(f"Error performing trend analysis: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _prepare_trend_data(self, historical_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare data for trend analysis"""
        
        trend_data = []
        
        for record in historical_data:
            timestamp = pd.to_datetime(record['timestamp'])
            metrics = record.get('metrics', {})
            
            row = {'timestamp': timestamp}
            row.update({
                'cpu_utilization': metrics.get('cpu_utilization', 0),
                'memory_utilization': metrics.get('memory_utilization', 0),
                'success_rate': metrics.get('success_rate', 100),
                'error_rate': metrics.get('error_rate', 0),
                'throughput_per_hour': metrics.get('throughput_per_hour', 0),
                'cost_per_execution': metrics.get('cost_per_execution', 0),
                'model_accuracy': metrics.get('model_accuracy', 0.85),
                'response_time': metrics.get('average_execution_time', 0)
            })
            
            trend_data.append(row)
        
        df = pd.DataFrame(trend_data)
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    def _analyze_metric_trend(self, df: pd.DataFrame, metric: str, forecast_days: int) -> Dict[str, Any]:
        """Analyze trend for a specific metric"""
        
        values = df[metric].dropna()
        
        if len(values) < 3:
            return {'status': 'insufficient_data', 'message': f'Not enough data points for {metric}'}
        
        # Calculate basic statistics
        current_value = float(values.iloc[-1])
        mean_value = float(values.mean())
        std_value = float(values.std())
        
        # Linear trend analysis
        x = np.arange(len(values))
        trend_slope, trend_intercept = np.polyfit(x, values, 1)
        
        # Determine trend direction and strength
        trend_direction = 'increasing' if trend_slope > 0 else 'decreasing' if trend_slope < 0 else 'stable'
        trend_strength = abs(trend_slope) / (std_value + 1e-8)  # Avoid division by zero
        
        if trend_strength > 0.5:
            trend_intensity = 'strong'
        elif trend_strength > 0.2:
            trend_intensity = 'moderate'
        else:
            trend_intensity = 'weak'
        
        # Simple linear forecast
        future_x = np.arange(len(values), len(values) + forecast_days)
        forecast_values = trend_slope * future_x + trend_intercept
        
        # Calculate forecast confidence (simplified)
        forecast_std = std_value * np.sqrt(1 + (future_x - len(values)) / len(values))
        
        # Detect seasonal patterns (simplified)
        seasonality = self._detect_seasonality(values)
        
        return {
            'metric_name': metric,
            'current_value': current_value,
            'mean_value': mean_value,
            'std_value': std_value,
            'trend_direction': trend_direction,
            'trend_intensity': trend_intensity,
            'trend_slope': float(trend_slope),
            'forecast_values': forecast_values.tolist(),
            'forecast_std': forecast_std.tolist(),
            'seasonality': seasonality,
            'status': 'success'
        }
    
    def _detect_seasonality(self, values: pd.Series) -> Dict[str, Any]:
        """Simple seasonality detection"""
        
        if len(values) < 7:
            return {'detected': False, 'message': 'Insufficient data for seasonality detection'}
        
        # Simple autocorrelation check for daily patterns
        if len(values) >= 7:
            autocorr_7 = values.autocorr(lag=7) if hasattr(values, 'autocorr') else 0
            if abs(autocorr_7) > 0.3:
                return {
                    'detected': True,
                    'pattern': 'weekly',
                    'strength': abs(autocorr_7)
                }
        
        return {'detected': False, 'pattern': None, 'strength': 0}
    
    def _generate_overall_trend_summary(self, trend_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall trend summary across all metrics"""
        
        increasing_trends = []
        decreasing_trends = []
        stable_trends = []
        
        for metric, analysis in trend_results.items():
            if analysis.get('status') == 'success':
                direction = analysis['trend_direction']
                intensity = analysis['trend_intensity']
                
                if direction == 'increasing':
                    increasing_trends.append({'metric': metric, 'intensity': intensity})
                elif direction == 'decreasing':
                    decreasing_trends.append({'metric': metric, 'intensity': intensity})
                else:
                    stable_trends.append({'metric': metric, 'intensity': intensity})
        
        # Overall system health trend
        critical_metrics = ['cpu_utilization', 'memory_utilization', 'error_rate']
        positive_metrics = ['success_rate', 'throughput_per_hour', 'model_accuracy']
        
        health_score = 100
        
        for metric in critical_metrics:
            if metric in trend_results and trend_results[metric].get('trend_direction') == 'increasing':
                intensity = trend_results[metric].get('trend_intensity', 'weak')
                if intensity == 'strong':
                    health_score -= 15
                elif intensity == 'moderate':
                    health_score -= 10
                else:
                    health_score -= 5
        
        for metric in positive_metrics:
            if metric in trend_results and trend_results[metric].get('trend_direction') == 'decreasing':
                intensity = trend_results[metric].get('trend_intensity', 'weak')
                if intensity == 'strong':
                    health_score -= 15
                elif intensity == 'moderate':
                    health_score -= 10
                else:
                    health_score -= 5
        
        return {
            'increasing_trends': increasing_trends,
            'decreasing_trends': decreasing_trends,
            'stable_trends': stable_trends,
            'overall_health_score': max(0, health_score),
            'metrics_analyzed': len(trend_results)
        }
    
    def _create_forecast_metadata(self, trend_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata for forecast visualizations"""
        
        forecast_metadata = {
            'chart_configs': {},
            'alert_thresholds': {},
            'data_quality': {}
        }
        
        for metric, analysis in trend_results.items():
            if analysis.get('status') == 'success':
                forecast_metadata['chart_configs'][metric] = {
                    'chart_type': 'time_series',
                    'y_axis_label': metric.replace('_', ' ').title(),
                    'trend_line': True,
                    'confidence_bands': True
                }
                
                # Set alert thresholds based on forecasted values
                forecast_values = analysis.get('forecast_values', [])
                if forecast_values:
                    max_forecast = max(forecast_values)
                    if metric in self.thresholds:
                        forecast_metadata['alert_thresholds'][metric] = {
                            'warning': self.thresholds[metric]['warning'],
                            'critical': self.thresholds[metric]['critical'],
                            'forecast_breach': max_forecast > self.thresholds[metric]['warning']
                        }
        
        return forecast_metadata
    
    def _generate_trend_recommendations(self, trend_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate recommendations based on trend analysis"""
        
        recommendations = []
        
        for metric, analysis in trend_results.items():
            if analysis.get('status') == 'success':
                direction = analysis['trend_direction']
                intensity = analysis['trend_intensity']
                current_value = analysis['current_value']
                
                if metric == 'cpu_utilization' and direction == 'increasing' and intensity in ['strong', 'moderate']:
                    recommendations.append({
                        'category': 'capacity_planning',
                        'priority': 'high' if intensity == 'strong' else 'medium',
                        'metric': metric,
                        'message': f'CPU utilization trending {direction} ({intensity}). Consider scaling resources.',
                        'suggested_actions': [
                            'Plan for additional compute capacity',
                            'Optimize CPU-intensive processes',
                            'Consider auto-scaling policies'
                        ]
                    })
                
                elif metric == 'error_rate' and direction == 'increasing':
                    recommendations.append({
                        'category': 'reliability',
                        'priority': 'high',
                        'metric': metric,
                        'message': f'Error rate trending {direction}. Investigate root causes.',
                        'suggested_actions': [
                            'Review recent code changes',
                            'Analyze error patterns',
                            'Implement additional monitoring'
                        ]
                    })
                
                elif metric == 'cost_per_execution' and direction == 'increasing':
                    recommendations.append({
                        'category': 'cost_optimization',
                        'priority': 'medium',
                        'metric': metric,
                        'message': f'Costs trending {direction}. Review resource efficiency.',
                        'suggested_actions': [
                            'Optimize resource utilization',
                            'Consider reserved instances',
                            'Review processing efficiency'
                        ]
                    })
                
                elif metric == 'model_accuracy' and direction == 'decreasing':
                    recommendations.append({
                        'category': 'model_performance',
                        'priority': 'high',
                        'metric': metric,
                        'message': f'Model accuracy trending {direction}. Plan for retraining.',
                        'suggested_actions': [
                            'Schedule model retraining',
                            'Check for data drift',
                            'Review feature quality'
                        ]
                    })
        
        return recommendations
    
    def _save_trend_analysis(self, trend_report: Dict[str, Any]) -> None:
        """Save trend analysis report"""
        
        try:
            report_file = self.reports_dir / f'trend_analysis_{int(time.time())}.json'
            with open(report_file, 'w') as f:
                json.dump(trend_report, f, indent=2, default=str)
            
            self.logger.info(f"Trend analysis saved: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving trend analysis: {e}")
    
    def get_anomaly_summary(self, days_back: int = 7) -> Dict[str, Any]:
        """Get summary of detected anomalies"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        recent_anomalies = [
            anomaly for anomaly in self.anomalies
            if start_time <= datetime.fromisoformat(anomaly['detection_time'].replace('Z', '+00:00')) <= end_time
        ]
        
        if not recent_anomalies:
            return {
                'period': f'{days_back} days',
                'total_anomalies': 0,
                'message': 'No anomalies detected in the specified period'
            }
        
        # Analyze anomaly patterns
        severity_counts = {}
        type_counts = {}
        
        for anomaly in recent_anomalies:
            details = anomaly['anomaly_details']
            severity = details['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            for atype in details['anomaly_types']:
                type_counts[atype] = type_counts.get(atype, 0) + 1
        
        return {
            'period': f'{days_back} days',
            'total_anomalies': len(recent_anomalies),
            'severity_breakdown': severity_counts,
            'anomaly_types': type_counts,
            'most_recent': recent_anomalies[-1]['detection_time'] if recent_anomalies else None,
            'most_common_type': max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None
        }
    
    def create_anomaly_detection_dashboard(self) -> Dict[str, Any]:
        """Create CloudWatch dashboard for anomaly detection"""
        
        dashboard_widgets = [
            {
                "type": "metric",
                "properties": {
                    "title": "Anomaly Detection Overview",
                    "metrics": [
                        [self.namespace, "AnomalyDetected", {"stat": "Sum"}],
                        [self.namespace, "AnomalyScore", {"stat": "Average"}],
                        [self.namespace, "AnomalyConfidence", {"stat": "Average"}]
                    ],
                    "period": 300,
                    "view": "timeSeries"
                }
            },
            {
                "type": "log",
                "properties": {
                    "title": "Recent Anomaly Alerts",
                    "query": "SOURCE '/aws/lambda/adpa-anomaly-detection' | fields @timestamp, @message | filter @message like /ANOMALY/ | sort @timestamp desc | limit 20",
                    "region": "us-west-2",
                    "view": "table"
                }
            }
        ]
        
        try:
            if self.mock_mode:
                dashboard_file = self.reports_dir / 'anomaly_dashboard_config.json'
                with open(dashboard_file, 'w') as f:
                    json.dump({"widgets": dashboard_widgets}, f, indent=2)
                
                return {
                    'status': 'success',
                    'dashboard_name': 'ADPA-Anomaly-Detection',
                    'widgets_created': len(dashboard_widgets),
                    'config_saved': str(dashboard_file)
                }
            else:
                self.cloudwatch.put_dashboard(
                    DashboardName='ADPA-Anomaly-Detection',
                    DashboardBody=json.dumps({"widgets": dashboard_widgets})
                )
                
                return {
                    'status': 'success',
                    'dashboard_name': 'ADPA-Anomaly-Detection',
                    'widgets_created': len(dashboard_widgets)
                }
                
        except Exception as e:
            self.logger.error(f"Error creating anomaly detection dashboard: {e}")
            return {'status': 'error', 'message': str(e)}