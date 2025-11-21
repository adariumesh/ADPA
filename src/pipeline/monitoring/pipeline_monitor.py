"""
Pipeline monitoring integration step that tracks execution across all pipeline components.
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd

from ...agent.core.interfaces import PipelineStep, PipelineStepType, ExecutionResult, StepStatus
from ...aws.cloudwatch.monitor import CloudWatchMonitor


class PipelineMonitoringStep(PipelineStep):
    """
    Pipeline step for comprehensive monitoring and observability.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.MONITORING, "pipeline_monitoring")
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize CloudWatch monitor
        self.cloudwatch_monitor = CloudWatchMonitor()
    
    def execute(self, 
                data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Execute pipeline monitoring step.
        
        Args:
            data: Pipeline data (optional)
            config: Step configuration
            context: Execution context with pipeline metrics
            
        Returns:
            ExecutionResult with monitoring setup results
        """
        try:
            self.logger.info("Starting pipeline monitoring setup...")
            
            # Merge configurations
            monitor_config = {**self.config, **(config or {})}
            
            # Generate pipeline ID
            pipeline_id = context.get('pipeline_id') or f"adpa-{int(time.time())}"
            
            # Create CloudWatch dashboard
            dashboard_result = self._setup_monitoring_dashboard(pipeline_id, monitor_config)
            
            # Create monitoring alarms
            alarms_result = self._setup_monitoring_alarms(pipeline_id, monitor_config)
            
            # Track pipeline execution metrics
            self._track_pipeline_metrics(pipeline_id, context)
            
            # Log pipeline monitoring event
            self._log_monitoring_event(pipeline_id, context, monitor_config)
            
            # Generate monitoring report
            monitoring_report = self._generate_monitoring_report(pipeline_id, context, monitor_config)
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                metrics={
                    'pipeline_id': pipeline_id,
                    'dashboard_created': dashboard_result.status == StepStatus.COMPLETED,
                    'alarms_created': alarms_result.status == StepStatus.COMPLETED,
                    'monitoring_active': True,
                    'metrics_tracked': len(self._get_tracked_metrics(context))
                },
                artifacts={
                    'dashboard_url': dashboard_result.artifacts.get('dashboard_url') if dashboard_result.artifacts else None,
                    'monitoring_report': monitoring_report,
                    'cloudwatch_namespace': 'ADPA/Pipeline',
                    'log_group': '/aws/adpa/pipeline'
                },
                step_output={
                    'monitoring_enabled': True,
                    'pipeline_id': pipeline_id,
                    'observability_score': self._calculate_observability_score(context)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Pipeline monitoring setup failed: {str(e)}")
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[f"Pipeline monitoring error: {str(e)}"]
            )
    
    def validate_inputs(self, 
                       data: Optional[pd.DataFrame] = None,
                       config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate inputs for monitoring step.
        
        Args:
            data: Input data
            config: Step configuration
            
        Returns:
            True if inputs are valid
        """
        # Monitoring step can work with minimal inputs
        return True
    
    def _setup_monitoring_dashboard(self, 
                                  pipeline_id: str,
                                  config: Dict[str, Any]) -> ExecutionResult:
        """
        Set up CloudWatch dashboard for pipeline monitoring.
        
        Args:
            pipeline_id: Pipeline execution ID
            config: Monitoring configuration
            
        Returns:
            ExecutionResult from dashboard creation
        """
        try:
            dashboard_name = config.get('dashboard_name', f"ADPA-Pipeline-{pipeline_id}")
            
            # Define pipeline resources for dashboard
            pipeline_resources = {
                'glue_jobs': config.get('glue_jobs', ['data-profiling', 'data-cleaning', 'feature-engineering']),
                'sagemaker_jobs': config.get('sagemaker_jobs', True),
                'step_functions': config.get('step_functions', True)
            }
            
            result = self.cloudwatch_monitor.create_dashboard(
                dashboard_name=dashboard_name,
                pipeline_resources=pipeline_resources
            )
            
            self.logger.info(f"Dashboard setup result: {result.status}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to setup monitoring dashboard: {str(e)}")
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[f"Dashboard setup error: {str(e)}"]
            )
    
    def _setup_monitoring_alarms(self, 
                               pipeline_id: str,
                               config: Dict[str, Any]) -> ExecutionResult:
        """
        Set up CloudWatch alarms for pipeline monitoring.
        
        Args:
            pipeline_id: Pipeline execution ID
            config: Monitoring configuration
            
        Returns:
            ExecutionResult from alarm creation
        """
        try:
            pipeline_name = config.get('pipeline_name', 'default')
            notification_topic = config.get('sns_topic_arn')
            
            result = self.cloudwatch_monitor.create_pipeline_alarms(
                pipeline_name=pipeline_name,
                notification_topic_arn=notification_topic
            )
            
            self.logger.info(f"Alarms setup result: {result.status}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to setup monitoring alarms: {str(e)}")
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[f"Alarms setup error: {str(e)}"]
            )
    
    def _track_pipeline_metrics(self, 
                              pipeline_id: str,
                              context: Optional[Dict[str, Any]]) -> None:
        """
        Track comprehensive pipeline execution metrics.
        
        Args:
            pipeline_id: Pipeline execution ID
            context: Execution context with metrics
        """
        if not context:
            return
        
        try:
            # Prepare execution data for tracking
            execution_data = {
                'pipeline_id': pipeline_id,
                'status': 'success' if context.get('pipeline_success', False) else 'failure'
            }
            
            # Add duration if available
            if 'total_duration' in context:
                execution_data['duration_seconds'] = context['total_duration']
            
            # Add data processing metrics
            profiling_results = context.get('profiling_results', {})
            if 'rows' in profiling_results:
                execution_data['rows_processed'] = profiling_results['rows']
            
            # Add model performance metrics
            ml_results = context.get('ml_results', {})
            if 'primary_metric' in ml_results:
                execution_data['model_accuracy'] = ml_results['primary_metric'] * 100  # Convert to percentage
            
            # Add cost metrics
            aws_info = context.get('aws_infrastructure', {})
            if 'estimated_cost' in aws_info:
                execution_data['estimated_cost'] = float(aws_info['estimated_cost'])
            
            # Track metrics in CloudWatch
            self.cloudwatch_monitor.track_pipeline_execution(pipeline_id, execution_data)
            
            self.logger.info(f"Pipeline metrics tracked for {pipeline_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to track pipeline metrics: {str(e)}")
    
    def _log_monitoring_event(self, 
                            pipeline_id: str,
                            context: Optional[Dict[str, Any]],
                            config: Dict[str, Any]) -> None:
        """
        Log monitoring event to CloudWatch Logs.
        
        Args:
            pipeline_id: Pipeline execution ID
            context: Execution context
            config: Monitoring configuration
        """
        try:
            event_data = {
                'monitoring_setup': True,
                'dashboard_enabled': True,
                'alarms_enabled': True,
                'pipeline_summary': self._create_pipeline_summary(context),
                'config': config
            }
            
            self.cloudwatch_monitor.log_pipeline_event(
                event_type='MONITORING_SETUP',
                pipeline_id=pipeline_id,
                event_data=event_data
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log monitoring event: {str(e)}")
    
    def _generate_monitoring_report(self, 
                                  pipeline_id: str,
                                  context: Optional[Dict[str, Any]],
                                  config: Dict[str, Any]) -> str:
        """
        Generate comprehensive monitoring report.
        
        Args:
            pipeline_id: Pipeline execution ID
            context: Execution context
            config: Monitoring configuration
            
        Returns:
            Formatted monitoring report
        """
        try:
            report = f"""# ADPA Pipeline Monitoring Report

**Pipeline ID:** {pipeline_id}  
**Monitoring Setup:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Status:** Active

## Monitoring Components Enabled

### CloudWatch Dashboard
- **Dashboard Name:** ADPA-Pipeline-{pipeline_id}
- **Metrics Tracked:** Pipeline execution, model performance, costs, data volume
- **Refresh Interval:** 5 minutes
- **Access:** AWS Console → CloudWatch → Dashboards

### CloudWatch Alarms
- **Pipeline Failure Alarm:** Triggers on execution failures
- **Execution Duration Alarm:** Triggers on executions > 2 hours
- **Model Performance Alarm:** Triggers on accuracy < 70%
- **Cost Threshold Alarm:** Triggers on costs > $50/hour

### Custom Metrics
"""
            
            # Add tracked metrics details
            tracked_metrics = self._get_tracked_metrics(context)
            for metric in tracked_metrics:
                report += f"- **{metric['name']}:** {metric['description']} (Unit: {metric['unit']})\n"
            
            report += f"""
### CloudWatch Logs
- **Log Group:** /aws/adpa/pipeline
- **Log Stream:** pipeline-{pipeline_id}
- **Retention:** 30 days (configurable)

## Pipeline Execution Summary
"""
            
            # Add pipeline summary
            if context:
                summary = self._create_pipeline_summary(context)
                for key, value in summary.items():
                    report += f"- **{key.replace('_', ' ').title()}:** {value}\n"
            
            report += f"""
## Monitoring Best Practices

### Real-time Monitoring
1. Monitor dashboard during pipeline execution
2. Set up mobile notifications for critical alarms
3. Review logs for detailed execution traces

### Performance Optimization
1. Track execution duration trends
2. Monitor resource utilization patterns
3. Analyze cost optimization opportunities

### Alerting Strategy
1. Critical: Pipeline failures, cost overruns
2. Warning: Performance degradation, long executions
3. Info: Successful completions, metric updates

## Next Steps

1. **Configure SNS Topic:** Set up email/SMS notifications for alarms
2. **Custom Dashboards:** Create team-specific monitoring views
3. **Log Analysis:** Set up log insights queries for deeper analysis
4. **Automated Responses:** Configure auto-scaling based on metrics

---
*Generated by ADPA Pipeline Monitoring System*
"""
            
            return report.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to generate monitoring report: {str(e)}")
            return f"Monitoring report generation failed: {str(e)}"
    
    def _get_tracked_metrics(self, context: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Get list of metrics being tracked."""
        metrics = [
            {
                'name': 'PipelineSuccess',
                'description': 'Pipeline execution success/failure indicator',
                'unit': 'Count'
            },
            {
                'name': 'ExecutionDuration',
                'description': 'Total pipeline execution time',
                'unit': 'Seconds'
            },
            {
                'name': 'RowsProcessed',
                'description': 'Number of data rows processed',
                'unit': 'Count'
            },
            {
                'name': 'ModelAccuracy',
                'description': 'Model performance accuracy percentage',
                'unit': 'Percent'
            },
            {
                'name': 'EstimatedCost',
                'description': 'Estimated AWS service costs',
                'unit': 'USD'
            }
        ]
        
        return metrics
    
    def _create_pipeline_summary(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create pipeline execution summary."""
        if not context:
            return {'status': 'No context provided'}
        
        summary = {}
        
        # Basic execution info
        summary['execution_status'] = 'Success' if context.get('pipeline_success', False) else 'Failure'
        summary['total_duration'] = f"{context.get('total_duration', 0):.1f} seconds"
        
        # Data processing info
        profiling_results = context.get('profiling_results', {})
        if profiling_results:
            summary['rows_processed'] = profiling_results.get('rows', 'N/A')
            summary['data_quality_score'] = profiling_results.get('quality_score', 'N/A')
        
        # ML results info
        ml_results = context.get('ml_results', {})
        if ml_results:
            summary['model_algorithm'] = ml_results.get('algorithm', 'AutoML')
            summary['model_performance'] = f"{ml_results.get('primary_metric', 0):.3f}"
        
        # Infrastructure info
        aws_info = context.get('aws_infrastructure', {})
        if aws_info:
            summary['estimated_cost'] = f"${aws_info.get('estimated_cost', '0.00')}"
        
        return summary
    
    def _calculate_observability_score(self, context: Optional[Dict[str, Any]]) -> float:
        """Calculate overall observability score for the pipeline."""
        score = 0.0
        max_score = 100.0
        
        # Base score for monitoring setup
        score += 30.0  # Dashboard and alarms
        
        # Score for metrics availability
        if context:
            if context.get('profiling_results'):
                score += 20.0
            if context.get('ml_results'):
                score += 20.0
            if context.get('aws_infrastructure'):
                score += 15.0
            if context.get('total_duration'):
                score += 10.0
            if context.get('pipeline_success') is not None:
                score += 5.0
        
        return min(score, max_score)
    
    def get_current_metrics(self, pipeline_id: str) -> Dict[str, Any]:
        """
        Get current pipeline metrics from CloudWatch.
        
        Args:
            pipeline_id: Pipeline execution ID
            
        Returns:
            Current metrics dictionary
        """
        try:
            return self.cloudwatch_monitor.get_pipeline_metrics(pipeline_id=pipeline_id)
        except Exception as e:
            self.logger.error(f"Failed to get current metrics: {str(e)}")
            return {}
    
    def create_monitoring_summary(self, pipeline_ids: List[str]) -> str:
        """
        Create monitoring summary for multiple pipeline executions.
        
        Args:
            pipeline_ids: List of pipeline execution IDs
            
        Returns:
            Formatted monitoring summary
        """
        try:
            summary = "# ADPA Pipeline Monitoring Summary\n\n"
            
            for pipeline_id in pipeline_ids:
                metrics = self.get_current_metrics(pipeline_id)
                
                summary += f"## Pipeline: {pipeline_id}\n"
                
                if metrics:
                    if 'execution_duration' in metrics:
                        duration_data = metrics['execution_duration']
                        summary += f"- **Avg Duration:** {duration_data.get('latest_value', {}).get('Average', 'N/A')} seconds\n"
                    
                    if 'success_rate' in metrics:
                        success_data = metrics['success_rate']
                        summary += f"- **Success Rate:** {success_data.get('latest_value', {}).get('Sum', 'N/A')}\n"
                    
                    if 'cost_metrics' in metrics:
                        cost_data = metrics['cost_metrics']
                        summary += f"- **Total Cost:** ${cost_data.get('latest_value', {}).get('Sum', 'N/A')}\n"
                else:
                    summary += "- No metrics available\n"
                
                summary += "\n"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to create monitoring summary: {str(e)}")
            return f"Monitoring summary generation failed: {str(e)}"