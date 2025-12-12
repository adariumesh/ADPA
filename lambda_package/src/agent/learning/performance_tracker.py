"""
Advanced Performance Learning System for ADPA

This module implements sophisticated learning algorithms that continuously improve
pipeline performance by analyzing execution patterns, detecting regressions,
and providing adaptive optimization recommendations.
"""

import logging
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import sqlite3
from collections import defaultdict, deque
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, accuracy_score

# Make scipy optional - fallback to simple statistics if not available
try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    
import warnings
warnings.filterwarnings('ignore')

from ..utils.llm_integration import RealLLMReasoningEngine
from ..memory.experience_memory import ExperienceMemorySystem, PipelineExecution


@dataclass
class PerformanceMetric:
    """Individual performance metric tracking."""
    metric_name: str
    value: float
    timestamp: datetime
    execution_id: str
    context: Dict[str, Any]


@dataclass
class LearningCurve:
    """Learning curve analysis result."""
    metric_name: str
    trend: str  # "improving", "stable", "declining"
    slope: float
    confidence: float
    prediction_horizon: int  # days
    predicted_values: List[float]
    last_updated: datetime


@dataclass
class PerformanceRegression:
    """Detected performance regression."""
    regression_id: str
    metric_name: str
    severity: str  # "critical", "major", "minor"
    detection_time: datetime
    baseline_value: float
    current_value: float
    impact_percentage: float
    affected_executions: List[str]
    potential_causes: List[str]
    recommended_actions: List[str]


@dataclass
class AdaptiveRecommendation:
    """Adaptive recommendation based on learning."""
    recommendation_id: str
    category: str  # "algorithm", "hyperparameters", "preprocessing", "architecture"
    recommendation: str
    rationale: str
    confidence: float
    expected_improvement: float
    applicable_conditions: Dict[str, Any]
    success_evidence: List[str]
    created_at: datetime


class PerformanceLearningSystem:
    """
    Advanced learning system that continuously analyzes pipeline performance,
    detects patterns and regressions, and provides adaptive recommendations.
    
    This system implements:
    1. Automated performance pattern recognition
    2. Regression detection with anomaly detection
    3. Learning curve analysis and prediction
    4. Adaptive optimization recommendations
    5. Success pattern extraction and application
    """
    
    def __init__(self, 
                 memory_system: ExperienceMemorySystem,
                 learning_window_days: int = 30,
                 min_samples_for_learning: int = 10):
        """
        Initialize the performance learning system.
        
        Args:
            memory_system: Experience memory system for data access
            learning_window_days: Days of history to consider for learning
            min_samples_for_learning: Minimum samples needed for reliable learning
        """
        self.memory_system = memory_system
        self.learning_window_days = learning_window_days
        self.min_samples_for_learning = min_samples_for_learning
        self.logger = logging.getLogger(__name__)
        
        # Initialize LLM reasoning for insights
        try:
            self.llm_engine = RealLLMReasoningEngine()
            self.llm_available = True
        except Exception as e:
            self.logger.warning(f"LLM engine not available for learning insights: {e}")
            self.llm_available = False
        
        # Learning state
        self.performance_history = defaultdict(list)  # metric_name -> [PerformanceMetric]
        self.learning_curves = {}  # metric_name -> LearningCurve
        self.active_regressions = {}  # regression_id -> PerformanceRegression
        self.adaptive_recommendations = {}  # recommendation_id -> AdaptiveRecommendation
        
        # Analysis parameters
        self.regression_threshold = 0.1  # 10% degradation triggers regression detection
        self.confidence_threshold = 0.7  # Minimum confidence for recommendations
        self.outlier_contamination = 0.1  # Expected outlier ratio for anomaly detection
        
        # Initialize learning history
        self._load_performance_history()
        
        self.logger.info("Performance Learning System initialized")
    
    def record_performance_metrics(self, 
                                 execution_id: str,
                                 metrics: Dict[str, float],
                                 context: Dict[str, Any]) -> None:
        """
        Record performance metrics from a pipeline execution.
        
        Args:
            execution_id: Unique execution identifier
            metrics: Dictionary of metric name -> value
            context: Execution context (algorithm, dataset info, etc.)
        """
        try:
            timestamp = datetime.now()
            
            # Record each metric
            for metric_name, value in metrics.items():
                if isinstance(value, (int, float)) and not np.isnan(value):
                    perf_metric = PerformanceMetric(
                        metric_name=metric_name,
                        value=float(value),
                        timestamp=timestamp,
                        execution_id=execution_id,
                        context=context.copy()
                    )
                    
                    self.performance_history[metric_name].append(perf_metric)
            
            # Trigger learning analysis
            self._trigger_learning_analysis()
            
            self.logger.info(f"Recorded {len(metrics)} performance metrics for execution {execution_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to record performance metrics: {e}")
    
    def detect_performance_regressions(self) -> List[PerformanceRegression]:
        """
        Detect performance regressions using statistical analysis and anomaly detection.
        
        Returns:
            List of detected regressions
        """
        try:
            detected_regressions = []
            
            for metric_name, metric_history in self.performance_history.items():
                if len(metric_history) < self.min_samples_for_learning:
                    continue
                
                # Get recent metrics (last 7 days) vs baseline (previous period)
                cutoff_date = datetime.now() - timedelta(days=7)
                recent_metrics = [m for m in metric_history if m.timestamp >= cutoff_date]
                baseline_metrics = [m for m in metric_history if m.timestamp < cutoff_date]
                
                if len(recent_metrics) < 3 or len(baseline_metrics) < 3:
                    continue
                
                # Calculate statistical comparison
                recent_values = [m.value for m in recent_metrics]
                baseline_values = [m.value for m in baseline_metrics]
                
                recent_mean = np.mean(recent_values)
                baseline_mean = np.mean(baseline_values)
                
                # Determine if this is a "higher is better" metric
                higher_is_better = self._is_higher_better_metric(metric_name)
                
                # Calculate impact
                if baseline_mean != 0:
                    impact_percentage = (recent_mean - baseline_mean) / baseline_mean
                else:
                    impact_percentage = 0
                
                # Check for significant regression
                is_regression = False
                if higher_is_better and impact_percentage < -self.regression_threshold:
                    is_regression = True
                elif not higher_is_better and impact_percentage > self.regression_threshold:
                    is_regression = True
                
                # Statistical significance test
                if is_regression:
                    try:
                        if HAS_SCIPY:
                            statistic, p_value = stats.ttest_ind(recent_values, baseline_values)
                        else:
                            # Fallback: use simple threshold without statistical test
                            p_value = 0.01  # Assume significant if we don't have scipy
                            
                        if p_value < 0.05:  # Statistically significant
                            
                            # Determine severity
                            severity = self._determine_regression_severity(abs(impact_percentage))
                            
                            # Analyze potential causes
                            potential_causes = self._analyze_regression_causes(
                                metric_name, recent_metrics, baseline_metrics
                            )
                            
                            # Generate recommendations
                            recommendations = self._generate_regression_recommendations(
                                metric_name, impact_percentage, potential_causes
                            )
                            
                            regression = PerformanceRegression(
                                regression_id=f"reg_{metric_name}_{int(time.time())}",
                                metric_name=metric_name,
                                severity=severity,
                                detection_time=datetime.now(),
                                baseline_value=baseline_mean,
                                current_value=recent_mean,
                                impact_percentage=impact_percentage,
                                affected_executions=[m.execution_id for m in recent_metrics],
                                potential_causes=potential_causes,
                                recommended_actions=recommendations
                            )
                            
                            detected_regressions.append(regression)
                            self.active_regressions[regression.regression_id] = regression
                            
                    except Exception as e:
                        self.logger.warning(f"Statistical test failed for {metric_name}: {e}")
            
            if detected_regressions:
                self.logger.warning(f"Detected {len(detected_regressions)} performance regressions")
            
            return detected_regressions
            
        except Exception as e:
            self.logger.error(f"Regression detection failed: {e}")
            return []
    
    def analyze_learning_curves(self) -> Dict[str, LearningCurve]:
        """
        Analyze learning curves for all performance metrics.
        
        Returns:
            Dictionary of metric_name -> LearningCurve
        """
        try:
            learning_curves = {}
            
            for metric_name, metric_history in self.performance_history.items():
                if len(metric_history) < self.min_samples_for_learning:
                    continue
                
                # Sort by timestamp
                sorted_metrics = sorted(metric_history, key=lambda x: x.timestamp)
                
                # Prepare data for trend analysis
                timestamps = [(m.timestamp - sorted_metrics[0].timestamp).days for m in sorted_metrics]
                values = [m.value for m in sorted_metrics]
                
                if len(set(timestamps)) < 3:  # Need at least 3 different days
                    continue
                
                # Fit linear regression for trend
                X = np.array(timestamps).reshape(-1, 1)
                y = np.array(values)
                
                lr = LinearRegression()
                lr.fit(X, y)
                
                slope = lr.coef_[0]
                r_squared = lr.score(X, y)
                
                # Determine trend direction
                higher_is_better = self._is_higher_better_metric(metric_name)
                
                if abs(slope) < 0.001:  # Very small slope
                    trend = "stable"
                elif (slope > 0 and higher_is_better) or (slope < 0 and not higher_is_better):
                    trend = "improving"
                else:
                    trend = "declining"
                
                # Predict future values
                prediction_horizon = 7  # 7 days
                future_timestamps = np.array(range(max(timestamps) + 1, max(timestamps) + prediction_horizon + 1)).reshape(-1, 1)
                predicted_values = lr.predict(future_timestamps).tolist()
                
                learning_curve = LearningCurve(
                    metric_name=metric_name,
                    trend=trend,
                    slope=slope,
                    confidence=r_squared,
                    prediction_horizon=prediction_horizon,
                    predicted_values=predicted_values,
                    last_updated=datetime.now()
                )
                
                learning_curves[metric_name] = learning_curve
                self.learning_curves[metric_name] = learning_curve
            
            self.logger.info(f"Analyzed learning curves for {len(learning_curves)} metrics")
            return learning_curves
            
        except Exception as e:
            self.logger.error(f"Learning curve analysis failed: {e}")
            return {}
    
    def generate_adaptive_recommendations(self) -> List[AdaptiveRecommendation]:
        """
        Generate adaptive recommendations based on learned patterns.
        
        Returns:
            List of adaptive recommendations
        """
        try:
            recommendations = []
            
            # Get recent executions for pattern analysis
            cutoff_date = datetime.now() - timedelta(days=self.learning_window_days)
            recent_executions = []
            
            # Access recent executions from memory system
            try:
                recent_executions = self.memory_system._get_recent_executions(self.learning_window_days)
            except Exception as e:
                self.logger.warning(f"Could not access recent executions: {e}")
                return recommendations
            
            if len(recent_executions) < self.min_samples_for_learning:
                return recommendations
            
            # Analyze success patterns
            successful_executions = [ex for ex in recent_executions if ex.success]
            failed_executions = [ex for ex in recent_executions if not ex.success]
            
            # Algorithm recommendations
            algo_recommendations = self._generate_algorithm_recommendations(
                successful_executions, failed_executions
            )
            recommendations.extend(algo_recommendations)
            
            # Hyperparameter recommendations
            hp_recommendations = self._generate_hyperparameter_recommendations(
                successful_executions
            )
            recommendations.extend(hp_recommendations)
            
            # Preprocessing recommendations
            prep_recommendations = self._generate_preprocessing_recommendations(
                successful_executions, failed_executions
            )
            recommendations.extend(prep_recommendations)
            
            # Architecture recommendations
            arch_recommendations = self._generate_architecture_recommendations(
                recent_executions
            )
            recommendations.extend(arch_recommendations)
            
            # Use LLM for additional insights if available
            if self.llm_available and recommendations:
                llm_recommendations = self._enhance_recommendations_with_llm(
                    recommendations, recent_executions
                )
                recommendations.extend(llm_recommendations)
            
            # Store recommendations
            for rec in recommendations:
                self.adaptive_recommendations[rec.recommendation_id] = rec
            
            self.logger.info(f"Generated {len(recommendations)} adaptive recommendations")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Adaptive recommendation generation failed: {e}")
            return []
    
    def predict_pipeline_performance(self, 
                                   pipeline_config: Dict[str, Any],
                                   dataset_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict expected performance for a given pipeline configuration.
        
        Args:
            pipeline_config: Pipeline configuration
            dataset_info: Dataset characteristics
            
        Returns:
            Performance predictions
        """
        try:
            predictions = {}
            
            # Find similar historical executions
            similar_executions = self._find_similar_executions(pipeline_config, dataset_info)
            
            if not similar_executions:
                return {"message": "No similar executions found for prediction"}
            
            # Extract performance metrics from similar executions
            for metric_name in self.performance_history.keys():
                metric_values = []
                for execution in similar_executions:
                    if metric_name in execution.performance_metrics:
                        metric_values.append(execution.performance_metrics[metric_name])
                
                if metric_values:
                    predictions[metric_name] = {
                        "expected_value": np.mean(metric_values),
                        "std_deviation": np.std(metric_values),
                        "min_value": np.min(metric_values),
                        "max_value": np.max(metric_values),
                        "confidence": min(0.9, len(metric_values) * 0.1),
                        "sample_size": len(metric_values)
                    }
            
            # Overall success prediction
            success_rate = sum(1 for ex in similar_executions if ex.success) / len(similar_executions)
            predictions["success_probability"] = {
                "probability": success_rate,
                "confidence": min(0.9, len(similar_executions) * 0.1),
                "based_on_executions": len(similar_executions)
            }
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"Performance prediction failed: {e}")
            return {"error": str(e)}
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """
        Get comprehensive performance insights and recommendations.
        
        Returns:
            Dictionary with insights, trends, and recommendations
        """
        try:
            insights = {
                "timestamp": datetime.now().isoformat(),
                "analysis_window_days": self.learning_window_days,
                "learning_curves": {},
                "active_regressions": [],
                "adaptive_recommendations": [],
                "performance_summary": {},
                "key_insights": []
            }
            
            # Learning curves
            learning_curves = self.analyze_learning_curves()
            insights["learning_curves"] = {
                name: {
                    "trend": curve.trend,
                    "confidence": curve.confidence,
                    "slope": curve.slope,
                    "predicted_improvement": curve.predicted_values[-1] - curve.predicted_values[0] if curve.predicted_values else 0
                }
                for name, curve in learning_curves.items()
            }
            
            # Active regressions
            regressions = self.detect_performance_regressions()
            insights["active_regressions"] = [
                {
                    "metric": reg.metric_name,
                    "severity": reg.severity,
                    "impact": f"{reg.impact_percentage:.1%}",
                    "potential_causes": reg.potential_causes[:3],
                    "recommendations": reg.recommended_actions[:3]
                }
                for reg in regressions
            ]
            
            # Adaptive recommendations
            recommendations = self.generate_adaptive_recommendations()
            insights["adaptive_recommendations"] = [
                {
                    "category": rec.category,
                    "recommendation": rec.recommendation,
                    "confidence": rec.confidence,
                    "expected_improvement": rec.expected_improvement
                }
                for rec in recommendations[:5]  # Top 5 recommendations
            ]
            
            # Performance summary
            insights["performance_summary"] = self._generate_performance_summary()
            
            # Key insights using LLM if available
            if self.llm_available:
                key_insights = self._generate_key_insights_with_llm(insights)
                insights["key_insights"] = key_insights
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Performance insights generation failed: {e}")
            return {"error": str(e)}
    
    # Helper methods
    
    def _load_performance_history(self):
        """Load performance history from memory system."""
        try:
            # Access recent executions from memory system
            recent_executions = self.memory_system._get_recent_executions(self.learning_window_days)
            
            for execution in recent_executions:
                context = {
                    "algorithm": execution.pipeline_steps[0].get("algorithm", "unknown") if execution.pipeline_steps else "unknown",
                    "dataset_fingerprint": execution.dataset_fingerprint,
                    "objective": execution.objective
                }
                
                for metric_name, value in execution.performance_metrics.items():
                    if isinstance(value, (int, float)) and not np.isnan(value):
                        perf_metric = PerformanceMetric(
                            metric_name=metric_name,
                            value=float(value),
                            timestamp=execution.timestamp,
                            execution_id=execution.execution_id,
                            context=context
                        )
                        self.performance_history[metric_name].append(perf_metric)
            
            self.logger.info(f"Loaded performance history for {len(self.performance_history)} metrics")
            
        except Exception as e:
            self.logger.warning(f"Failed to load performance history: {e}")
    
    def _trigger_learning_analysis(self):
        """Trigger periodic learning analysis."""
        # Limit frequency of analysis to avoid performance impact
        if hasattr(self, '_last_analysis_time'):
            if (datetime.now() - self._last_analysis_time).seconds < 300:  # 5 minutes
                return
        
        self._last_analysis_time = datetime.now()
        
        # Run analysis in background
        try:
            self.analyze_learning_curves()
            self.detect_performance_regressions()
        except Exception as e:
            self.logger.warning(f"Background learning analysis failed: {e}")
    
    def _is_higher_better_metric(self, metric_name: str) -> bool:
        """Determine if higher values are better for a metric."""
        higher_better_metrics = [
            "accuracy", "precision", "recall", "f1_score", "roc_auc",
            "r2_score", "primary_metric", "performance_score"
        ]
        lower_better_metrics = [
            "mean_squared_error", "mean_absolute_error", "root_mean_squared_error",
            "training_time", "error_rate", "loss"
        ]
        
        metric_lower = metric_name.lower()
        
        if any(better in metric_lower for better in higher_better_metrics):
            return True
        elif any(better in metric_lower for better in lower_better_metrics):
            return False
        else:
            # Default assumption for unknown metrics
            return True
    
    def _determine_regression_severity(self, impact_percentage: float) -> str:
        """Determine regression severity based on impact percentage."""
        if impact_percentage >= 0.3:  # 30%+ degradation
            return "critical"
        elif impact_percentage >= 0.15:  # 15%+ degradation
            return "major"
        else:
            return "minor"
    
    def _analyze_regression_causes(self, 
                                 metric_name: str,
                                 recent_metrics: List[PerformanceMetric],
                                 baseline_metrics: List[PerformanceMetric]) -> List[str]:
        """Analyze potential causes of performance regression."""
        causes = []
        
        # Compare algorithm distributions
        recent_algos = [m.context.get("algorithm", "unknown") for m in recent_metrics]
        baseline_algos = [m.context.get("algorithm", "unknown") for m in baseline_metrics]
        
        if set(recent_algos) != set(baseline_algos):
            causes.append("Algorithm change detected")
        
        # Compare dataset characteristics (simplified)
        try:
            recent_datasets = [m.context.get("dataset_fingerprint", {}) for m in recent_metrics]
            baseline_datasets = [m.context.get("dataset_fingerprint", {}) for m in baseline_metrics]
            
            if len(recent_datasets) > 0 and len(baseline_datasets) > 0:
                recent_sizes = [d.get("rows", 0) for d in recent_datasets if isinstance(d, dict)]
                baseline_sizes = [d.get("rows", 0) for d in baseline_datasets if isinstance(d, dict)]
                
                if recent_sizes and baseline_sizes:
                    if np.mean(recent_sizes) > np.mean(baseline_sizes) * 1.5:
                        causes.append("Dataset size increased significantly")
                    elif np.mean(recent_sizes) < np.mean(baseline_sizes) * 0.5:
                        causes.append("Dataset size decreased significantly")
        except Exception:
            pass
        
        # Time-based causes
        execution_times = [(datetime.now() - m.timestamp).days for m in recent_metrics]
        if max(execution_times) - min(execution_times) > 7:
            causes.append("Performance degradation over time")
        
        if not causes:
            causes.append("Unknown cause - requires investigation")
        
        return causes
    
    def _generate_regression_recommendations(self, 
                                           metric_name: str,
                                           impact_percentage: float,
                                           potential_causes: List[str]) -> List[str]:
        """Generate recommendations for addressing regression."""
        recommendations = []
        
        # General recommendations based on metric type
        if "accuracy" in metric_name.lower() or "f1" in metric_name.lower():
            recommendations.extend([
                "Review recent model training parameters",
                "Check for data quality issues",
                "Consider ensemble methods or different algorithms"
            ])
        elif "time" in metric_name.lower():
            recommendations.extend([
                "Profile code for performance bottlenecks",
                "Check resource allocation and scaling",
                "Consider optimization techniques"
            ])
        
        # Recommendations based on causes
        for cause in potential_causes:
            if "algorithm change" in cause.lower():
                recommendations.append("Revert to previous algorithm or optimize new one")
            elif "dataset size" in cause.lower():
                recommendations.append("Adjust model complexity for dataset size")
            elif "time" in cause.lower():
                recommendations.append("Investigate recent system or code changes")
        
        # Severity-based recommendations
        if abs(impact_percentage) > 0.3:
            recommendations.insert(0, "URGENT: Immediate investigation required")
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _generate_algorithm_recommendations(self, 
                                          successful_executions: List[PipelineExecution],
                                          failed_executions: List[PipelineExecution]) -> List[AdaptiveRecommendation]:
        """Generate algorithm-based recommendations."""
        recommendations = []
        
        try:
            # Analyze algorithm success rates
            algo_success = defaultdict(list)
            algo_performance = defaultdict(list)
            
            for execution in successful_executions:
                if execution.pipeline_steps:
                    algo = execution.pipeline_steps[0].get("algorithm", "unknown")
                    algo_success[algo].append(True)
                    
                    primary_metric = execution.performance_metrics.get("primary_metric", 0)
                    algo_performance[algo].append(primary_metric)
            
            for execution in failed_executions:
                if execution.pipeline_steps:
                    algo = execution.pipeline_steps[0].get("algorithm", "unknown")
                    algo_success[algo].append(False)
            
            # Find best performing algorithms
            algo_stats = {}
            for algo, successes in algo_success.items():
                if len(successes) >= 3:  # Minimum samples
                    success_rate = sum(successes) / len(successes)
                    avg_performance = np.mean(algo_performance.get(algo, [0]))
                    
                    algo_stats[algo] = {
                        "success_rate": success_rate,
                        "avg_performance": avg_performance,
                        "sample_size": len(successes)
                    }
            
            # Generate recommendations for top algorithms
            sorted_algos = sorted(algo_stats.items(), 
                                key=lambda x: (x[1]["success_rate"], x[1]["avg_performance"]), 
                                reverse=True)
            
            for i, (algo, stats) in enumerate(sorted_algos[:3]):
                if stats["success_rate"] > 0.7 and stats["avg_performance"] > 0.6:
                    rec = AdaptiveRecommendation(
                        recommendation_id=f"algo_rec_{algo}_{int(time.time())}",
                        category="algorithm",
                        recommendation=f"Consider using {algo} algorithm",
                        rationale=f"Shows {stats['success_rate']:.1%} success rate with {stats['avg_performance']:.3f} avg performance",
                        confidence=min(0.9, stats["sample_size"] * 0.1),
                        expected_improvement=stats["avg_performance"] - 0.5,
                        applicable_conditions={"algorithm_selection": True},
                        success_evidence=[ex.execution_id for ex in successful_executions 
                                        if ex.pipeline_steps and ex.pipeline_steps[0].get("algorithm") == algo],
                        created_at=datetime.now()
                    )
                    recommendations.append(rec)
        
        except Exception as e:
            self.logger.warning(f"Algorithm recommendation generation failed: {e}")
        
        return recommendations
    
    def _generate_hyperparameter_recommendations(self, 
                                               successful_executions: List[PipelineExecution]) -> List[AdaptiveRecommendation]:
        """Generate hyperparameter-based recommendations."""
        recommendations = []
        
        try:
            # Analyze hyperparameter patterns in successful executions
            hp_patterns = defaultdict(list)
            
            for execution in successful_executions:
                if execution.pipeline_steps:
                    step = execution.pipeline_steps[0]
                    params = step.get("parameters", {})
                    
                    for param_name, param_value in params.items():
                        if isinstance(param_value, (int, float)):
                            hp_patterns[param_name].append({
                                "value": param_value,
                                "performance": execution.performance_metrics.get("primary_metric", 0),
                                "execution_id": execution.execution_id
                            })
            
            # Find optimal hyperparameter ranges
            for param_name, values in hp_patterns.items():
                if len(values) >= 5:  # Minimum samples for analysis
                    # Sort by performance
                    sorted_values = sorted(values, key=lambda x: x["performance"], reverse=True)
                    top_performers = sorted_values[:len(sorted_values)//3]  # Top third
                    
                    if top_performers:
                        top_values = [v["value"] for v in top_performers]
                        optimal_range = (min(top_values), max(top_values))
                        avg_performance = np.mean([v["performance"] for v in top_performers])
                        
                        if avg_performance > 0.7:  # Good performance threshold
                            rec = AdaptiveRecommendation(
                                recommendation_id=f"hp_rec_{param_name}_{int(time.time())}",
                                category="hyperparameters",
                                recommendation=f"Use {param_name} in range {optimal_range[0]:.3f} - {optimal_range[1]:.3f}",
                                rationale=f"Top performers use this range with {avg_performance:.3f} avg performance",
                                confidence=min(0.8, len(top_performers) * 0.1),
                                expected_improvement=avg_performance - 0.5,
                                applicable_conditions={"parameter_tuning": True, param_name: True},
                                success_evidence=[v["execution_id"] for v in top_performers],
                                created_at=datetime.now()
                            )
                            recommendations.append(rec)
        
        except Exception as e:
            self.logger.warning(f"Hyperparameter recommendation generation failed: {e}")
        
        return recommendations
    
    def _generate_preprocessing_recommendations(self, 
                                             successful_executions: List[PipelineExecution],
                                             failed_executions: List[PipelineExecution]) -> List[AdaptiveRecommendation]:
        """Generate preprocessing-based recommendations."""
        recommendations = []
        
        try:
            # Analyze preprocessing steps in successful vs failed executions
            successful_steps = set()
            failed_steps = set()
            
            for execution in successful_executions:
                for step in execution.pipeline_steps:
                    step_name = step.get("step", "unknown")
                    successful_steps.add(step_name)
            
            for execution in failed_executions:
                for step in execution.pipeline_steps:
                    step_name = step.get("step", "unknown")
                    failed_steps.add(step_name)
            
            # Find steps that appear more in successful executions
            beneficial_steps = successful_steps - failed_steps
            
            for step in beneficial_steps:
                if step not in ["unknown", "training", "evaluation"]:  # Skip generic steps
                    rec = AdaptiveRecommendation(
                        recommendation_id=f"prep_rec_{step}_{int(time.time())}",
                        category="preprocessing",
                        recommendation=f"Include {step} step in pipeline",
                        rationale=f"Step appears in successful executions but not failed ones",
                        confidence=0.6,  # Moderate confidence for preprocessing
                        expected_improvement=0.05,  # Conservative estimate
                        applicable_conditions={"preprocessing": True},
                        success_evidence=[ex.execution_id for ex in successful_executions 
                                        if any(s.get("step") == step for s in ex.pipeline_steps)],
                        created_at=datetime.now()
                    )
                    recommendations.append(rec)
        
        except Exception as e:
            self.logger.warning(f"Preprocessing recommendation generation failed: {e}")
        
        return recommendations
    
    def _generate_architecture_recommendations(self, 
                                             recent_executions: List[PipelineExecution]) -> List[AdaptiveRecommendation]:
        """Generate architecture-based recommendations."""
        recommendations = []
        
        try:
            # Analyze execution patterns for architecture insights
            training_approaches = defaultdict(list)
            
            for execution in recent_executions:
                # Look for training approach indicators
                training_approach = "standard"
                
                for step in execution.pipeline_steps:
                    if "ensemble" in str(step).lower():
                        training_approach = "ensemble"
                    elif "automl" in str(step).lower():
                        training_approach = "automl"
                    elif "optimization" in str(step).lower():
                        training_approach = "optimized"
                
                training_approaches[training_approach].append(execution)
            
            # Find best performing approach
            approach_performance = {}
            for approach, executions in training_approaches.items():
                if len(executions) >= 3:
                    success_rate = sum(1 for ex in executions if ex.success) / len(executions)
                    avg_performance = np.mean([
                        ex.performance_metrics.get("primary_metric", 0) 
                        for ex in executions if ex.success
                    ])
                    
                    approach_performance[approach] = {
                        "success_rate": success_rate,
                        "avg_performance": avg_performance,
                        "sample_size": len(executions)
                    }
            
            # Generate recommendation for best approach
            if approach_performance:
                best_approach = max(approach_performance.items(), 
                                  key=lambda x: (x[1]["success_rate"], x[1]["avg_performance"]))
                
                approach_name, stats = best_approach
                if stats["success_rate"] > 0.7:
                    rec = AdaptiveRecommendation(
                        recommendation_id=f"arch_rec_{approach_name}_{int(time.time())}",
                        category="architecture",
                        recommendation=f"Use {approach_name} training approach",
                        rationale=f"Shows {stats['success_rate']:.1%} success rate in recent executions",
                        confidence=min(0.8, stats["sample_size"] * 0.1),
                        expected_improvement=stats["avg_performance"] - 0.5,
                        applicable_conditions={"architecture_choice": True},
                        success_evidence=[ex.execution_id for ex in training_approaches[approach_name] if ex.success],
                        created_at=datetime.now()
                    )
                    recommendations.append(rec)
        
        except Exception as e:
            self.logger.warning(f"Architecture recommendation generation failed: {e}")
        
        return recommendations
    
    def _enhance_recommendations_with_llm(self, 
                                        recommendations: List[AdaptiveRecommendation],
                                        recent_executions: List[PipelineExecution]) -> List[AdaptiveRecommendation]:
        """Enhance recommendations using LLM analysis."""
        enhanced_recommendations = []
        
        try:
            if not self.llm_available or not recommendations:
                return enhanced_recommendations
            
            # Prepare context for LLM
            llm_context = {
                "recent_executions_count": len(recent_executions),
                "success_rate": sum(1 for ex in recent_executions if ex.success) / len(recent_executions),
                "current_recommendations": [
                    {"category": rec.category, "recommendation": rec.recommendation, "confidence": rec.confidence}
                    for rec in recommendations[:5]
                ],
                "performance_trends": list(self.learning_curves.keys())
            }
            
            enhancement_prompt = f"""
            Analyze these ML pipeline performance patterns and recommendations:
            
            Recent Performance: {llm_context['success_rate']:.1%} success rate
            Current Recommendations: {llm_context['current_recommendations']}
            
            Based on this analysis, suggest 1-2 additional high-impact recommendations
            that could further improve pipeline performance. Focus on:
            1. Cross-cutting optimizations
            2. Integration improvements
            3. Performance bottleneck elimination
            
            Provide specific, actionable recommendations.
            """
            
            llm_response = self.llm_engine._call_anthropic(enhancement_prompt)
            
            # Parse LLM response and create recommendation
            if "recommendation" in llm_response.lower() or "suggest" in llm_response.lower():
                rec = AdaptiveRecommendation(
                    recommendation_id=f"llm_rec_{int(time.time())}",
                    category="optimization",
                    recommendation=llm_response[:200] + "..." if len(llm_response) > 200 else llm_response,
                    rationale="Generated by LLM analysis of execution patterns",
                    confidence=0.7,
                    expected_improvement=0.05,
                    applicable_conditions={"llm_enhancement": True},
                    success_evidence=[],
                    created_at=datetime.now()
                )
                enhanced_recommendations.append(rec)
        
        except Exception as e:
            self.logger.warning(f"LLM enhancement failed: {e}")
        
        return enhanced_recommendations
    
    def _find_similar_executions(self, 
                               pipeline_config: Dict[str, Any],
                               dataset_info: Dict[str, Any]) -> List[PipelineExecution]:
        """Find similar historical executions."""
        try:
            # Get recent executions
            recent_executions = self.memory_system._get_recent_executions(self.learning_window_days)
            
            # Simple similarity matching (could be enhanced)
            similar_executions = []
            target_algo = pipeline_config.get("algorithm", "unknown")
            target_size_bucket = self._get_size_bucket(dataset_info.get("row_count", 0))
            
            for execution in recent_executions:
                if execution.pipeline_steps:
                    exec_algo = execution.pipeline_steps[0].get("algorithm", "unknown")
                    exec_size_bucket = execution.dataset_fingerprint.get("size_bucket", "unknown")
                    
                    if exec_algo == target_algo or exec_size_bucket == target_size_bucket:
                        similar_executions.append(execution)
            
            return similar_executions[:20]  # Limit to most recent similar executions
        
        except Exception as e:
            self.logger.warning(f"Similar execution search failed: {e}")
            return []
    
    def _get_size_bucket(self, row_count: int) -> str:
        """Get size bucket for dataset."""
        if row_count < 1000:
            return "small"
        elif row_count < 10000:
            return "medium"
        elif row_count < 100000:
            return "large"
        else:
            return "very_large"
    
    def _generate_performance_summary(self) -> Dict[str, Any]:
        """Generate performance summary statistics."""
        summary = {
            "total_metrics_tracked": len(self.performance_history),
            "total_data_points": sum(len(metrics) for metrics in self.performance_history.values()),
            "active_regressions_count": len(self.active_regressions),
            "learning_curves_analyzed": len(self.learning_curves),
            "recommendations_generated": len(self.adaptive_recommendations)
        }
        
        # Recent performance trends
        for metric_name, curve in self.learning_curves.items():
            if curve.trend != "stable":
                summary[f"{metric_name}_trend"] = curve.trend
        
        return summary
    
    def _generate_key_insights_with_llm(self, insights: Dict[str, Any]) -> List[str]:
        """Generate key insights using LLM analysis."""
        try:
            insight_prompt = f"""
            Analyze these ML pipeline performance insights and provide 3-5 key takeaways:
            
            Performance Summary: {insights['performance_summary']}
            Learning Trends: {list(insights['learning_curves'].keys())}
            Active Issues: {len(insights['active_regressions'])} regressions detected
            Recommendations: {len(insights['adaptive_recommendations'])} generated
            
            Provide concise, actionable insights about:
            1. Overall performance health
            2. Key improvement opportunities
            3. Risk areas requiring attention
            4. Success patterns to replicate
            """
            
            llm_response = self.llm_engine._call_anthropic(insight_prompt)
            
            # Parse response into key insights
            insights_list = []
            if llm_response:
                # Split by numbered items or bullet points
                lines = llm_response.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                        # Clean up formatting
                        clean_line = line.lstrip('0123456789.-• ')
                        if clean_line:
                            insights_list.append(clean_line)
            
            return insights_list[:5]  # Top 5 insights
        
        except Exception as e:
            self.logger.warning(f"LLM key insights generation failed: {e}")
            return ["Performance learning system is active and collecting data"]