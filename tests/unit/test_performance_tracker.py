"""
Unit tests for Performance Learning System.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.agent.learning.performance_tracker import (
    PerformanceLearningSystem,
    PerformanceMetric,
    LearningCurve,
    PerformanceRegression,
    AdaptiveRecommendation
)
from src.agent.memory.experience_memory import ExperienceMemorySystem, PipelineExecution


class TestPerformanceLearningSystem:
    """Test cases for PerformanceLearningSystem."""
    
    @pytest.fixture
    def mock_memory_system(self):
        """Create mock memory system."""
        mock_memory = Mock(spec=ExperienceMemorySystem)
        mock_memory._get_recent_executions.return_value = []
        return mock_memory
    
    @pytest.fixture
    def performance_tracker(self, mock_memory_system):
        """Create performance tracker with mocked dependencies."""
        with patch('src.agent.learning.performance_tracker.RealLLMReasoningEngine'):
            tracker = PerformanceLearningSystem(
                memory_system=mock_memory_system,
                learning_window_days=30,
                min_samples_for_learning=5
            )
            return tracker
    
    def test_initialization(self, performance_tracker):
        """Test system initialization."""
        assert performance_tracker.learning_window_days == 30
        assert performance_tracker.min_samples_for_learning == 5
        assert performance_tracker.regression_threshold == 0.1
        assert isinstance(performance_tracker.performance_history, dict)
    
    def test_record_performance_metrics(self, performance_tracker):
        """Test recording performance metrics."""
        metrics = {
            "accuracy": 0.85,
            "f1_score": 0.82,
            "training_time": 300.5
        }
        context = {
            "algorithm": "random_forest",
            "dataset_size": 1000
        }
        
        performance_tracker.record_performance_metrics(
            execution_id="test_exec_1",
            metrics=metrics,
            context=context
        )
        
        # Check metrics were recorded
        assert len(performance_tracker.performance_history["accuracy"]) == 1
        assert len(performance_tracker.performance_history["f1_score"]) == 1
        assert len(performance_tracker.performance_history["training_time"]) == 1
        
        # Check metric values
        recorded_metric = performance_tracker.performance_history["accuracy"][0]
        assert recorded_metric.value == 0.85
        assert recorded_metric.execution_id == "test_exec_1"
        assert recorded_metric.context["algorithm"] == "random_forest"
    
    def test_record_invalid_metrics(self, performance_tracker):
        """Test handling of invalid metric values."""
        metrics = {
            "accuracy": float('nan'),
            "f1_score": 0.82,
            "invalid_metric": "not_a_number"
        }
        context = {"algorithm": "test"}
        
        performance_tracker.record_performance_metrics(
            execution_id="test_exec_2",
            metrics=metrics,
            context=context
        )
        
        # Only valid metric should be recorded
        assert "accuracy" not in performance_tracker.performance_history
        assert len(performance_tracker.performance_history["f1_score"]) == 1
        assert "invalid_metric" not in performance_tracker.performance_history
    
    def test_is_higher_better_metric(self, performance_tracker):
        """Test metric direction detection."""
        # Higher is better metrics
        assert performance_tracker._is_higher_better_metric("accuracy")
        assert performance_tracker._is_higher_better_metric("f1_score")
        assert performance_tracker._is_higher_better_metric("roc_auc")
        assert performance_tracker._is_higher_better_metric("primary_metric")
        
        # Lower is better metrics
        assert not performance_tracker._is_higher_better_metric("mean_squared_error")
        assert not performance_tracker._is_higher_better_metric("training_time")
        assert not performance_tracker._is_higher_better_metric("error_rate")
        
        # Unknown metrics default to higher is better
        assert performance_tracker._is_higher_better_metric("unknown_metric")
    
    def test_learning_curve_analysis(self, performance_tracker):
        """Test learning curve analysis."""
        # Create mock performance history with trend
        base_time = datetime.now()
        for i in range(10):
            metric = PerformanceMetric(
                metric_name="accuracy",
                value=0.7 + i * 0.02,  # Improving trend
                timestamp=base_time + timedelta(days=i),
                execution_id=f"exec_{i}",
                context={"algorithm": "test"}
            )
            performance_tracker.performance_history["accuracy"].append(metric)
        
        learning_curves = performance_tracker.analyze_learning_curves()
        
        assert "accuracy" in learning_curves
        curve = learning_curves["accuracy"]
        assert isinstance(curve, LearningCurve)
        assert curve.trend == "improving"
        assert curve.slope > 0
        assert len(curve.predicted_values) == 7  # prediction_horizon
    
    def test_regression_detection(self, performance_tracker):
        """Test performance regression detection."""
        base_time = datetime.now()
        
        # Create baseline metrics (good performance)
        for i in range(10):
            metric = PerformanceMetric(
                metric_name="accuracy",
                value=0.85 + np.random.normal(0, 0.01),
                timestamp=base_time - timedelta(days=20-i),
                execution_id=f"baseline_{i}",
                context={"algorithm": "test"}
            )
            performance_tracker.performance_history["accuracy"].append(metric)
        
        # Create recent metrics (degraded performance)
        for i in range(5):
            metric = PerformanceMetric(
                metric_name="accuracy",
                value=0.70 + np.random.normal(0, 0.01),  # 15% regression
                timestamp=base_time - timedelta(days=5-i),
                execution_id=f"recent_{i}",
                context={"algorithm": "test"}
            )
            performance_tracker.performance_history["accuracy"].append(metric)
        
        regressions = performance_tracker.detect_performance_regressions()
        
        assert len(regressions) > 0
        regression = regressions[0]
        assert isinstance(regression, PerformanceRegression)
        assert regression.metric_name == "accuracy"
        assert regression.severity in ["critical", "major", "minor"]
        assert regression.impact_percentage < -0.1  # Negative impact
    
    def test_determine_regression_severity(self, performance_tracker):
        """Test regression severity classification."""
        assert performance_tracker._determine_regression_severity(0.35) == "critical"
        assert performance_tracker._determine_regression_severity(0.20) == "major"
        assert performance_tracker._determine_regression_severity(0.10) == "minor"
    
    def test_adaptive_recommendations_with_no_data(self, performance_tracker):
        """Test adaptive recommendations with insufficient data."""
        recommendations = performance_tracker.generate_adaptive_recommendations()
        assert recommendations == []
    
    def test_adaptive_recommendations_with_data(self, performance_tracker):
        """Test adaptive recommendations with sufficient data."""
        # Create mock recent executions
        successful_executions = []
        for i in range(10):
            execution = Mock(spec=PipelineExecution)
            execution.success = True
            execution.pipeline_steps = [{"algorithm": "random_forest", "parameters": {"n_estimators": 100}}]
            execution.performance_metrics = {"primary_metric": 0.85}
            execution.execution_id = f"success_{i}"
            successful_executions.append(execution)
        
        failed_executions = []
        for i in range(3):
            execution = Mock(spec=PipelineExecution)
            execution.success = False
            execution.pipeline_steps = [{"algorithm": "linear_regression"}]
            execution.execution_id = f"failed_{i}"
            failed_executions.append(execution)
        
        # Mock memory system to return these executions
        all_executions = successful_executions + failed_executions
        performance_tracker.memory_system._get_recent_executions.return_value = all_executions
        
        recommendations = performance_tracker.generate_adaptive_recommendations()
        
        # Should generate some recommendations
        assert len(recommendations) > 0
        
        # Check recommendation structure
        for rec in recommendations:
            assert isinstance(rec, AdaptiveRecommendation)
            assert rec.category in ["algorithm", "hyperparameters", "preprocessing", "architecture", "optimization"]
            assert 0 <= rec.confidence <= 1
            assert rec.recommendation_id is not None
    
    def test_performance_prediction_no_similar_executions(self, performance_tracker):
        """Test performance prediction with no similar executions."""
        pipeline_config = {"algorithm": "unknown_algo"}
        dataset_info = {"row_count": 1000}
        
        # Mock empty similar executions
        performance_tracker._find_similar_executions = Mock(return_value=[])
        
        predictions = performance_tracker.predict_pipeline_performance(pipeline_config, dataset_info)
        
        assert "message" in predictions
        assert "No similar executions found" in predictions["message"]
    
    def test_performance_prediction_with_similar_executions(self, performance_tracker):
        """Test performance prediction with similar executions."""
        pipeline_config = {"algorithm": "random_forest"}
        dataset_info = {"row_count": 1000}
        
        # Create mock similar executions
        similar_executions = []
        for i in range(5):
            execution = Mock(spec=PipelineExecution)
            execution.success = True
            execution.performance_metrics = {
                "accuracy": 0.8 + i * 0.01,
                "f1_score": 0.75 + i * 0.01
            }
            similar_executions.append(execution)
        
        performance_tracker._find_similar_executions = Mock(return_value=similar_executions)
        
        predictions = performance_tracker.predict_pipeline_performance(pipeline_config, dataset_info)
        
        assert "accuracy" in predictions
        assert "f1_score" in predictions
        assert "success_probability" in predictions
        
        # Check prediction structure
        accuracy_pred = predictions["accuracy"]
        assert "expected_value" in accuracy_pred
        assert "confidence" in accuracy_pred
        assert "sample_size" in accuracy_pred
        assert accuracy_pred["sample_size"] == 5
    
    def test_get_performance_insights(self, performance_tracker):
        """Test performance insights generation."""
        # Add some mock data
        performance_tracker.learning_curves = {
            "accuracy": Mock(trend="improving", confidence=0.8, slope=0.01, predicted_values=[0.8, 0.81])
        }
        performance_tracker.active_regressions = {}
        
        insights = performance_tracker.get_performance_insights()
        
        assert "timestamp" in insights
        assert "learning_curves" in insights
        assert "active_regressions" in insights
        assert "adaptive_recommendations" in insights
        assert "performance_summary" in insights
    
    def test_size_bucket_classification(self, performance_tracker):
        """Test dataset size bucket classification."""
        assert performance_tracker._get_size_bucket(500) == "small"
        assert performance_tracker._get_size_bucket(5000) == "medium"
        assert performance_tracker._get_size_bucket(50000) == "large"
        assert performance_tracker._get_size_bucket(500000) == "very_large"
    
    def test_error_handling_in_record_metrics(self, performance_tracker):
        """Test error handling in metric recording."""
        # Should not raise exception with invalid input
        performance_tracker.record_performance_metrics(
            execution_id=None,  # Invalid input
            metrics=None,  # Invalid input
            context={}
        )
        
        # Performance history should remain empty
        assert len(performance_tracker.performance_history) == 0
    
    def test_error_handling_in_regression_detection(self, performance_tracker):
        """Test error handling in regression detection."""
        # Should not raise exception with empty data
        regressions = performance_tracker.detect_performance_regressions()
        assert regressions == []
    
    def test_error_handling_in_learning_curve_analysis(self, performance_tracker):
        """Test error handling in learning curve analysis."""
        # Should not raise exception with empty data
        curves = performance_tracker.analyze_learning_curves()
        assert curves == {}


class TestPerformanceMetric:
    """Test cases for PerformanceMetric dataclass."""
    
    def test_performance_metric_creation(self):
        """Test PerformanceMetric creation."""
        timestamp = datetime.now()
        metric = PerformanceMetric(
            metric_name="accuracy",
            value=0.85,
            timestamp=timestamp,
            execution_id="test_exec",
            context={"algorithm": "test"}
        )
        
        assert metric.metric_name == "accuracy"
        assert metric.value == 0.85
        assert metric.timestamp == timestamp
        assert metric.execution_id == "test_exec"
        assert metric.context["algorithm"] == "test"


class TestLearningCurve:
    """Test cases for LearningCurve dataclass."""
    
    def test_learning_curve_creation(self):
        """Test LearningCurve creation."""
        timestamp = datetime.now()
        curve = LearningCurve(
            metric_name="accuracy",
            trend="improving",
            slope=0.01,
            confidence=0.85,
            prediction_horizon=7,
            predicted_values=[0.8, 0.81, 0.82],
            last_updated=timestamp
        )
        
        assert curve.metric_name == "accuracy"
        assert curve.trend == "improving"
        assert curve.slope == 0.01
        assert curve.confidence == 0.85
        assert curve.prediction_horizon == 7
        assert len(curve.predicted_values) == 3
        assert curve.last_updated == timestamp


class TestPerformanceRegression:
    """Test cases for PerformanceRegression dataclass."""
    
    def test_performance_regression_creation(self):
        """Test PerformanceRegression creation."""
        timestamp = datetime.now()
        regression = PerformanceRegression(
            regression_id="reg_test",
            metric_name="accuracy",
            severity="major",
            detection_time=timestamp,
            baseline_value=0.85,
            current_value=0.70,
            impact_percentage=-0.176,
            affected_executions=["exec1", "exec2"],
            potential_causes=["algorithm change"],
            recommended_actions=["investigate parameters"]
        )
        
        assert regression.regression_id == "reg_test"
        assert regression.metric_name == "accuracy"
        assert regression.severity == "major"
        assert regression.impact_percentage == -0.176
        assert len(regression.affected_executions) == 2
        assert len(regression.potential_causes) == 1
        assert len(regression.recommended_actions) == 1


class TestAdaptiveRecommendation:
    """Test cases for AdaptiveRecommendation dataclass."""
    
    def test_adaptive_recommendation_creation(self):
        """Test AdaptiveRecommendation creation."""
        timestamp = datetime.now()
        recommendation = AdaptiveRecommendation(
            recommendation_id="rec_test",
            category="algorithm",
            recommendation="Use random_forest",
            rationale="Shows good performance",
            confidence=0.8,
            expected_improvement=0.05,
            applicable_conditions={"algorithm_selection": True},
            success_evidence=["exec1", "exec2"],
            created_at=timestamp
        )
        
        assert recommendation.recommendation_id == "rec_test"
        assert recommendation.category == "algorithm"
        assert recommendation.recommendation == "Use random_forest"
        assert recommendation.confidence == 0.8
        assert recommendation.expected_improvement == 0.05
        assert len(recommendation.success_evidence) == 2
        assert recommendation.created_at == timestamp