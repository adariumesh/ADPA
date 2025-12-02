#!/usr/bin/env python3
"""
ADPA Intelligent Error Handler
Implements sophisticated error analysis and recovery strategies
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
import traceback

# Add project paths for imports
sys.path.append('/opt/python')
sys.path.append('./src')
sys.path.append('.')

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    # Import ADPA components for intelligent error analysis
    from src.agent.utils.llm_integration import LLMReasoningEngine, ReasoningContext
    from src.monitoring.cloudwatch_monitor import ADPACloudWatchMonitor
    IMPORTS_SUCCESS = True
except ImportError as e:
    IMPORTS_SUCCESS = False
    IMPORT_ERROR = str(e)
    logger.warning(f"Could not import ADPA components: {e}")


class ADPAErrorAnalyzer:
    """
    Intelligent error analysis and recovery system for ADPA pipelines
    """
    
    def __init__(self):
        self.monitoring = None
        self.llm_engine = None
        
        if IMPORTS_SUCCESS:
            try:
                self.monitoring = ADPACloudWatchMonitor()
                self.llm_engine = LLMReasoningEngine()
                logger.info("ADPA Error Analyzer initialized with AI capabilities")
            except Exception as e:
                logger.warning(f"Partial initialization: {e}")
        
        # Error pattern database
        self.common_patterns = self._load_error_patterns()
        
    def _load_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load common error patterns and their solutions"""
        return {
            "memory_error": {
                "patterns": ["MemoryError", "OutOfMemoryError", "memory limit"],
                "severity": "high",
                "category": "resource",
                "solutions": [
                    "reduce_batch_size",
                    "increase_lambda_memory",
                    "implement_chunking",
                    "use_streaming_processing"
                ]
            },
            "timeout_error": {
                "patterns": ["TimeoutError", "timed out", "timeout exceeded"],
                "severity": "high", 
                "category": "performance",
                "solutions": [
                    "increase_timeout",
                    "optimize_processing",
                    "implement_checkpointing",
                    "parallelize_operations"
                ]
            },
            "data_quality": {
                "patterns": ["missing values", "invalid data", "schema mismatch"],
                "severity": "medium",
                "category": "data",
                "solutions": [
                    "improve_data_validation",
                    "implement_robust_preprocessing",
                    "add_data_quality_checks",
                    "use_adaptive_schemas"
                ]
            },
            "model_performance": {
                "patterns": ["poor accuracy", "overfitting", "underfitting"],
                "severity": "medium",
                "category": "model",
                "solutions": [
                    "adjust_hyperparameters",
                    "feature_engineering",
                    "regularization",
                    "ensemble_methods"
                ]
            },
            "aws_service": {
                "patterns": ["AccessDenied", "ServiceException", "ThrottlingException"],
                "severity": "high",
                "category": "infrastructure",
                "solutions": [
                    "check_iam_permissions",
                    "implement_exponential_backoff",
                    "request_service_limits_increase",
                    "use_alternative_regions"
                ]
            },
            "import_error": {
                "patterns": ["ImportError", "ModuleNotFoundError", "No module named"],
                "severity": "critical",
                "category": "dependencies",
                "solutions": [
                    "check_deployment_package",
                    "verify_dependencies",
                    "rebuild_lambda_layer",
                    "update_requirements"
                ]
            }
        }
    
    def analyze_error(self, error_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive error analysis
        
        Args:
            error_event: Error event containing failure details
            
        Returns:
            Comprehensive error analysis with recovery recommendations
        """
        logger.info("Starting intelligent error analysis...")
        
        # Extract error details
        error_message = str(error_event.get('errorMessage', ''))
        error_type = error_event.get('errorType', 'Unknown')
        stack_trace = error_event.get('stackTrace', [])
        
        # Pattern matching analysis
        pattern_analysis = self._analyze_error_patterns(error_message, error_type)
        
        # Context analysis
        context_analysis = self._analyze_error_context(error_event)
        
        # LLM-powered analysis (if available)
        llm_analysis = self._llm_error_analysis(error_event) if self.llm_engine else None
        
        # Generate recovery strategy
        recovery_strategy = self._generate_recovery_strategy(
            pattern_analysis, context_analysis, llm_analysis
        )
        
        analysis_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_summary": {
                "type": error_type,
                "message": error_message,
                "severity": pattern_analysis.get("severity", "medium")
            },
            "pattern_analysis": pattern_analysis,
            "context_analysis": context_analysis,
            "llm_analysis": llm_analysis,
            "recovery_strategy": recovery_strategy,
            "confidence_score": self._calculate_confidence(
                pattern_analysis, context_analysis, llm_analysis
            )
        }
        
        # Log comprehensive analysis
        logger.info(f"Error analysis complete. Confidence: {analysis_result['confidence_score']}")
        
        return analysis_result
    
    def _analyze_error_patterns(self, error_message: str, error_type: str) -> Dict[str, Any]:
        """Analyze error against known patterns"""
        
        matched_patterns = []
        
        for pattern_name, pattern_info in self.common_patterns.items():
            for pattern in pattern_info["patterns"]:
                if pattern.lower() in error_message.lower() or pattern.lower() in error_type.lower():
                    matched_patterns.append({
                        "pattern": pattern_name,
                        "confidence": 0.9,
                        "category": pattern_info["category"],
                        "severity": pattern_info["severity"],
                        "solutions": pattern_info["solutions"]
                    })
                    break
        
        if not matched_patterns:
            # Generic analysis
            matched_patterns.append({
                "pattern": "unknown",
                "confidence": 0.3,
                "category": "general",
                "severity": "medium",
                "solutions": ["investigate_logs", "check_configuration", "retry_operation"]
            })
        
        return {
            "matched_patterns": matched_patterns,
            "primary_pattern": matched_patterns[0] if matched_patterns else None,
            "pattern_count": len(matched_patterns)
        }
    
    def _analyze_error_context(self, error_event: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error context and environment"""
        
        context = {}
        
        # Extract execution context
        if 'requestContext' in error_event:
            context['execution_context'] = error_event['requestContext']
        
        # Analyze resource usage patterns
        if 'logs' in error_event:
            context['resource_usage'] = self._extract_resource_metrics(error_event['logs'])
        
        # Check for related errors
        if 'related_errors' in error_event:
            context['error_frequency'] = len(error_event['related_errors'])
            context['error_trend'] = self._analyze_error_trend(error_event['related_errors'])
        
        # Environment analysis
        context['environment'] = {
            'lambda_memory': os.environ.get('AWS_LAMBDA_FUNCTION_MEMORY_SIZE', 'unknown'),
            'lambda_timeout': os.environ.get('AWS_LAMBDA_FUNCTION_TIMEOUT', 'unknown'),
            'region': os.environ.get('AWS_REGION', 'unknown')
        }
        
        return context
    
    def _llm_error_analysis(self, error_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use LLM for sophisticated error analysis"""
        
        if not self.llm_engine:
            return None
        
        try:
            # Prepare reasoning context
            context = ReasoningContext(
                domain="error_recovery",
                objective="Analyze ML pipeline failure and recommend recovery strategy",
                data_context={
                    "error_details": error_event,
                    "system": "ADPA ML Pipeline",
                    "environment": "AWS Lambda"
                },
                constraints={
                    "focus": "actionable recovery strategies",
                    "priority": "minimize downtime"
                }
            )
            
            # Get LLM analysis
            reasoning_response = self.llm_engine.reason_about_error_recovery(
                failed_step="pipeline_execution",
                error=str(error_event.get('errorMessage', '')),
                context=context
            )
            
            return {
                "reasoning": reasoning_response.reasoning,
                "recommended_action": reasoning_response.decision,
                "confidence": reasoning_response.confidence,
                "alternatives": reasoning_response.alternatives[:3],  # Top 3 alternatives
                "explanation": reasoning_response.explanation
            }
            
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
            return None
    
    def _generate_recovery_strategy(self, 
                                  pattern_analysis: Dict[str, Any],
                                  context_analysis: Dict[str, Any],
                                  llm_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive recovery strategy"""
        
        strategy = {
            "immediate_actions": [],
            "configuration_changes": {},
            "monitoring_adjustments": [],
            "retry_strategy": {},
            "long_term_improvements": []
        }
        
        # Extract solutions from pattern analysis
        primary_pattern = pattern_analysis.get("primary_pattern")
        if primary_pattern:
            solutions = primary_pattern.get("solutions", [])
            
            for solution in solutions:
                if solution == "reduce_batch_size":
                    strategy["configuration_changes"]["batch_size"] = "50% of current"
                    strategy["immediate_actions"].append("Reduce processing batch size")
                
                elif solution == "increase_lambda_memory":
                    current_memory = context_analysis.get("environment", {}).get("lambda_memory", "512")
                    try:
                        new_memory = min(int(current_memory) * 2, 10240)  # Max 10GB
                        strategy["configuration_changes"]["lambda_memory"] = f"{new_memory}MB"
                        strategy["immediate_actions"].append(f"Increase Lambda memory to {new_memory}MB")
                    except:
                        strategy["immediate_actions"].append("Increase Lambda memory allocation")
                
                elif solution == "increase_timeout":
                    strategy["configuration_changes"]["lambda_timeout"] = "900 seconds"
                    strategy["immediate_actions"].append("Increase Lambda timeout")
                
                elif solution == "implement_exponential_backoff":
                    strategy["retry_strategy"] = {
                        "max_attempts": 5,
                        "backoff_base": 2,
                        "jitter": True
                    }
                    strategy["immediate_actions"].append("Implement exponential backoff retry")
        
        # Incorporate LLM recommendations
        if llm_analysis and llm_analysis.get("confidence", 0) > 0.7:
            llm_action = llm_analysis.get("recommended_action", {})
            if llm_action:
                strategy["llm_recommendations"] = {
                    "primary_action": llm_action.get("action", ""),
                    "reasoning": llm_analysis.get("reasoning", ""),
                    "confidence": llm_analysis.get("confidence", 0)
                }
                
                # Add specific LLM recommendations
                if "parameters" in llm_action:
                    strategy["configuration_changes"].update(llm_action["parameters"])
        
        # Default retry strategy if none specified
        if not strategy["retry_strategy"]:
            strategy["retry_strategy"] = {
                "max_attempts": 3,
                "backoff_base": 1.5,
                "jitter": False
            }
        
        # Add monitoring improvements
        strategy["monitoring_adjustments"] = [
            "Increase log verbosity for error tracking",
            "Add custom metrics for failure detection",
            "Enable detailed CloudWatch tracing"
        ]
        
        return strategy
    
    def _extract_resource_metrics(self, logs: List[str]) -> Dict[str, Any]:
        """Extract resource usage metrics from logs"""
        
        metrics = {
            "memory_usage": "unknown",
            "duration": "unknown",
            "cpu_usage": "unknown"
        }
        
        for log_line in logs:
            # Extract Lambda metrics from CloudWatch logs
            if "REPORT RequestId:" in log_line:
                # Parse Lambda execution report
                try:
                    if "Duration:" in log_line:
                        duration = log_line.split("Duration: ")[1].split(" ms")[0]
                        metrics["duration"] = f"{duration}ms"
                    
                    if "Max Memory Used:" in log_line:
                        memory = log_line.split("Max Memory Used: ")[1].split(" MB")[0]
                        metrics["memory_usage"] = f"{memory}MB"
                        
                except Exception:
                    pass
        
        return metrics
    
    def _analyze_error_trend(self, related_errors: List[Dict[str, Any]]) -> str:
        """Analyze error frequency trends"""
        
        if len(related_errors) == 0:
            return "isolated"
        elif len(related_errors) < 3:
            return "occasional"
        elif len(related_errors) < 10:
            return "frequent"
        else:
            return "critical_pattern"
    
    def _calculate_confidence(self, 
                            pattern_analysis: Dict[str, Any],
                            context_analysis: Dict[str, Any], 
                            llm_analysis: Optional[Dict[str, Any]]) -> float:
        """Calculate confidence score for the analysis"""
        
        confidence_factors = []
        
        # Pattern matching confidence
        primary_pattern = pattern_analysis.get("primary_pattern")
        if primary_pattern:
            confidence_factors.append(primary_pattern.get("confidence", 0.5))
        
        # Context richness
        context_score = min(len(context_analysis.keys()) * 0.1, 0.8)
        confidence_factors.append(context_score)
        
        # LLM analysis confidence
        if llm_analysis:
            confidence_factors.append(llm_analysis.get("confidence", 0.5))
        
        # Calculate weighted average
        if confidence_factors:
            return round(sum(confidence_factors) / len(confidence_factors), 2)
        else:
            return 0.3


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Intelligent error handler for ADPA pipeline failures
    
    Args:
        event: Error event containing failure details
        context: Lambda execution context
        
    Returns:
        Comprehensive error analysis and recovery strategy
    """
    
    logger.info(f"ADPA Error Handler invoked: {json.dumps(event, default=str)}")
    
    try:
        # Initialize error analyzer
        analyzer = ADPAErrorAnalyzer()
        
        # Perform comprehensive analysis
        analysis = analyzer.analyze_error(event)
        
        # Publish error metrics (if monitoring available)
        if analyzer.monitoring:
            try:
                analyzer.monitoring.publish_custom_metric(
                    metric_name="PipelineErrors",
                    value=1,
                    unit="Count",
                    dimensions={
                        "ErrorType": analysis["error_summary"]["type"],
                        "Severity": analysis["error_summary"]["severity"]
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to publish error metrics: {e}")
        
        # Return comprehensive response
        response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "status": "analyzed",
                "analysis": analysis,
                "recovery_recommended": True,
                "next_steps": analysis["recovery_strategy"]["immediate_actions"],
                "timestamp": datetime.utcnow().isoformat()
            }, default=str)
        }
        
        logger.info(f"Error analysis complete. Confidence: {analysis['confidence_score']}")
        return response
        
    except Exception as e:
        # Fallback error handling
        logger.error(f"Error handler failed: {str(e)}")
        logger.error(traceback.format_exc())
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "status": "error_handler_failed",
                "error": str(e),
                "fallback_action": "manual_investigation_required",
                "timestamp": datetime.utcnow().isoformat()
            })
        }