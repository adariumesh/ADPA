"""
AWS X-Ray integration for distributed tracing
Implementation based on Adariprasad's monitoring tutorial
"""

import boto3
import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from aws_xray_sdk.core import xray_recorder
    from aws_xray_sdk.core import patch_all
    # Patch AWS SDK calls for automatic tracing
    patch_all()
    XRAY_AVAILABLE = True
except ImportError:
    # Fallback for development environments without X-Ray SDK
    XRAY_AVAILABLE = False
    xray_recorder = None

class ADPAXRayMonitor:
    """AWS X-Ray integration for distributed tracing"""
    
    def __init__(self):
        self.xray_client = boto3.client('xray')
        self.logger = logging.getLogger(__name__)
        
        if not XRAY_AVAILABLE:
            self.logger.warning("X-Ray SDK not available. Tracing will be disabled.")
    
    def trace_pipeline_execution(self, execution_id: str, pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
        """Trace complete pipeline execution with detailed segments"""
        
        if not XRAY_AVAILABLE or not xray_recorder:
            self.logger.warning("X-Ray not available, skipping tracing")
            return {
                'status': 'success',
                'execution_id': execution_id,
                'trace_id': 'xray_not_available'
            }
        
        @xray_recorder.capture('adpa_pipeline_execution')
        def _trace_execution():
            # Add metadata to trace
            xray_recorder.put_metadata('execution_id', execution_id)
            xray_recorder.put_metadata('pipeline_config', pipeline_config)
            
            try:
                # Trace data preprocessing
                with xray_recorder.in_subsegment('data_preprocessing') as subsegment:
                    start_time = time.time()
                    
                    subsegment.put_annotation('stage', 'preprocessing')
                    subsegment.put_annotation('execution_id', execution_id)
                    
                    # Simulate data preprocessing
                    preprocessing_result = self._trace_data_preprocessing(execution_id)
                    
                    processing_time = time.time() - start_time
                    subsegment.put_metadata('processing_time', processing_time)
                    subsegment.put_metadata('result', preprocessing_result)
                
                # Trace model training
                with xray_recorder.in_subsegment('model_training') as subsegment:
                    start_time = time.time()
                    
                    subsegment.put_annotation('stage', 'training')
                    subsegment.put_annotation('execution_id', execution_id)
                    
                    # Simulate model training
                    training_result = self._trace_model_training(execution_id)
                    
                    training_time = time.time() - start_time
                    subsegment.put_metadata('training_time', training_time)
                    subsegment.put_metadata('result', training_result)
                
                # Trace model evaluation
                with xray_recorder.in_subsegment('model_evaluation') as subsegment:
                    start_time = time.time()
                    
                    subsegment.put_annotation('stage', 'evaluation')
                    subsegment.put_annotation('execution_id', execution_id)
                    
                    # Simulate model evaluation
                    evaluation_result = self._trace_model_evaluation(execution_id)
                    
                    evaluation_time = time.time() - start_time
                    subsegment.put_metadata('evaluation_time', evaluation_time)
                    subsegment.put_metadata('evaluation_result', evaluation_result)
                
                return {
                    'status': 'success',
                    'execution_id': execution_id,
                    'trace_id': xray_recorder.current_segment().trace_id if xray_recorder.current_segment() else 'unknown'
                }
                
            except Exception as e:
                if xray_recorder.current_segment():
                    xray_recorder.current_segment().add_exception(e)
                return {
                    'status': 'error',
                    'error': str(e),
                    'execution_id': execution_id
                }
        
        return _trace_execution()
    
    def _trace_data_preprocessing(self, execution_id: str) -> Dict[str, Any]:
        """Trace data preprocessing with detailed metrics"""
        
        if not XRAY_AVAILABLE or not xray_recorder:
            return {'status': 'completed', 'rows_processed': 50000}
        
        # Simulate data loading
        with xray_recorder.in_subsegment('data_loading') as subsegment:
            time.sleep(0.1)  # Simulate processing time
            subsegment.put_annotation('data_source', 's3://adpa-data-raw')
            subsegment.put_metadata('rows_processed', 50000)
        
        # Simulate data validation
        with xray_recorder.in_subsegment('data_validation') as subsegment:
            time.sleep(0.05)
            subsegment.put_metadata('validation_score', 95.5)
            subsegment.put_annotation('validation_status', 'passed')
        
        # Simulate feature engineering
        with xray_recorder.in_subsegment('feature_engineering') as subsegment:
            time.sleep(0.08)
            subsegment.put_metadata('features_created', 25)
            subsegment.put_annotation('feature_selection', 'automated')
        
        return {
            'status': 'completed',
            'rows_processed': 50000,
            'validation_score': 95.5,
            'features_created': 25
        }
    
    def _trace_model_training(self, execution_id: str) -> Dict[str, Any]:
        """Trace model training process"""
        
        if not XRAY_AVAILABLE or not xray_recorder:
            return {'status': 'completed', 'algorithm': 'random_forest'}
        
        # Simulate hyperparameter tuning
        with xray_recorder.in_subsegment('hyperparameter_tuning') as subsegment:
            time.sleep(0.2)
            subsegment.put_metadata('tuning_trials', 50)
            subsegment.put_annotation('optimization_metric', 'f1_score')
        
        # Simulate model training
        with xray_recorder.in_subsegment('training_execution') as subsegment:
            time.sleep(0.3)
            subsegment.put_metadata('training_samples', 40000)
            subsegment.put_annotation('algorithm', 'random_forest')
        
        return {
            'status': 'completed',
            'algorithm': 'random_forest',
            'training_samples': 40000,
            'tuning_trials': 50
        }
    
    def _trace_model_evaluation(self, execution_id: str) -> Dict[str, Any]:
        """Trace model evaluation process"""
        
        if not XRAY_AVAILABLE or not xray_recorder:
            return {
                'accuracy': 0.87,
                'precision': 0.85,
                'recall': 0.89,
                'f1_score': 0.87
            }
        
        # Simulate model evaluation
        with xray_recorder.in_subsegment('performance_evaluation') as subsegment:
            time.sleep(0.1)
            
            evaluation_metrics = {
                'accuracy': 0.87,
                'precision': 0.85,
                'recall': 0.89,
                'f1_score': 0.87
            }
            
            subsegment.put_metadata('evaluation_metrics', evaluation_metrics)
            subsegment.put_annotation('test_samples', 10000)
            
            return evaluation_metrics
    
    def analyze_trace_data(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Analyze X-Ray trace data for performance insights"""
        
        if not trace_id or trace_id == 'xray_not_available':
            return None
        
        try:
            # Get trace summary
            trace_summaries = self.xray_client.get_trace_summaries(
                TimeRangeType='TraceId',
                TraceIds=[trace_id]
            )
            
            if trace_summaries['TraceSummaries']:
                summary = trace_summaries['TraceSummaries'][0]
                
                # Get detailed trace
                trace_details = self.xray_client.batch_get_traces(
                    TraceIds=[trace_id]
                )
                
                analysis = {
                    'trace_id': trace_id,
                    'duration': summary.get('Duration', 0),
                    'response_time': summary.get('ResponseTime', 0),
                    'service_count': len(summary.get('ServiceIds', [])),
                    'error_count': summary.get('ErrorCount', 0),
                    'fault_count': summary.get('FaultCount', 0),
                    'throttle_count': summary.get('ThrottleCount', 0)
                }
                
                return analysis
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error analyzing trace data: {e}")
            return None
    
    def get_service_map(self, start_time: datetime, end_time: datetime) -> Optional[Dict[str, Any]]:
        """Get X-Ray service map for the specified time period"""
        
        try:
            response = self.xray_client.get_service_graph(
                StartTime=start_time,
                EndTime=end_time
            )
            
            service_map = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'services': response.get('Services', []),
                'total_count': len(response.get('Services', [])),
                'contains_old_group_versions': response.get('ContainsOldGroupVersions', False)
            }
            
            return service_map
            
        except Exception as e:
            self.logger.error(f"Error getting service map: {e}")
            return None
    
    def get_trace_analytics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get analytics for traces in the specified time period"""
        
        analytics = {
            'time_period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'trace_summary': {},
            'performance_insights': [],
            'error_analysis': []
        }
        
        try:
            # Get trace summaries
            trace_summaries = self.xray_client.get_trace_summaries(
                TimeRangeType='TimeRange',
                StartTime=start_time,
                EndTime=end_time
            )
            
            summaries = trace_summaries.get('TraceSummaries', [])
            
            if summaries:
                total_traces = len(summaries)
                total_duration = sum(trace.get('Duration', 0) for trace in summaries)
                error_traces = [trace for trace in summaries if trace.get('HasError', False)]
                fault_traces = [trace for trace in summaries if trace.get('HasFault', False)]
                
                analytics['trace_summary'] = {
                    'total_traces': total_traces,
                    'average_duration': total_duration / total_traces if total_traces > 0 else 0,
                    'error_count': len(error_traces),
                    'fault_count': len(fault_traces),
                    'error_rate': len(error_traces) / total_traces if total_traces > 0 else 0
                }
                
                # Identify slow traces
                slow_traces = [trace for trace in summaries if trace.get('Duration', 0) > 5.0]
                if slow_traces:
                    analytics['performance_insights'].append({
                        'type': 'slow_traces',
                        'count': len(slow_traces),
                        'percentage': len(slow_traces) / total_traces * 100
                    })
                
                # Analyze error patterns
                if error_traces:
                    analytics['error_analysis'].append({
                        'type': 'error_rate',
                        'error_rate': len(error_traces) / total_traces * 100,
                        'total_errors': len(error_traces)
                    })
            
        except Exception as e:
            self.logger.error(f"Error getting trace analytics: {e}")
            analytics['error'] = str(e)
        
        return analytics
    
    def start_tracing_segment(self, segment_name: str) -> Optional[Any]:
        """Start a new X-Ray tracing segment"""
        
        if not XRAY_AVAILABLE or not xray_recorder:
            return None
        
        return xray_recorder.begin_segment(segment_name)
    
    def end_tracing_segment(self) -> None:
        """End the current X-Ray tracing segment"""
        
        if XRAY_AVAILABLE and xray_recorder:
            xray_recorder.end_segment()
    
    def add_annotation(self, key: str, value: str) -> None:
        """Add annotation to current trace segment"""
        
        if XRAY_AVAILABLE and xray_recorder and xray_recorder.current_segment():
            xray_recorder.put_annotation(key, value)
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to current trace segment"""
        
        if XRAY_AVAILABLE and xray_recorder and xray_recorder.current_segment():
            xray_recorder.put_metadata(key, value)