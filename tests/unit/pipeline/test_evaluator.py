"""
Unit tests for Model Evaluation Step.
"""

import pytest
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.datasets import make_classification, make_regression
from sklearn.model_selection import train_test_split

from src.pipeline.evaluation.evaluator import ModelEvaluationStep
from src.agent.core.interfaces import StepStatus


class TestModelEvaluationStep:
    """Test suite for ModelEvaluationStep."""
    
    @pytest.fixture
    def classification_data(self):
        """Create sample classification dataset with trained model."""
        # Generate synthetic classification data
        X, y = make_classification(
            n_samples=200,
            n_features=10,
            n_informative=7,
            n_redundant=2,
            n_classes=2,
            random_state=42
        )
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42
        )
        
        # Train a simple model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        
        # Generate predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)
        
        return {
            'model': model,
            'X_train': X_train,
            'y_train': y_train,
            'X_test': X_test,
            'y_test': y_test,
            'y_pred': y_pred,
            'y_pred_proba': y_pred_proba,
            'problem_type': 'classification',
            'num_features': X.shape[1],
            'feature_names': [f'feature_{i}' for i in range(X.shape[1])]
        }
    
    @pytest.fixture
    def regression_data(self):
        """Create sample regression dataset with trained model."""
        # Generate synthetic regression data
        X, y = make_regression(
            n_samples=200,
            n_features=10,
            n_informative=7,
            noise=10,
            random_state=42
        )
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42
        )
        
        # Train a simple model
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        
        # Generate predictions
        y_pred = model.predict(X_test)
        
        return {
            'model': model,
            'X_train': X_train,
            'y_train': y_train,
            'X_test': X_test,
            'y_test': y_test,
            'y_pred': y_pred,
            'problem_type': 'regression',
            'num_features': X.shape[1],
            'feature_names': [f'feature_{i}' for i in range(X.shape[1])]
        }
    
    def test_initialization(self):
        """Test model evaluation step initialization."""
        step = ModelEvaluationStep()
        
        assert step.step_type.value == "evaluation"
        assert step.name == "model_evaluation"
        assert isinstance(step.config, dict)
    
    def test_classification_evaluation_with_predictions(self, classification_data):
        """Test classification evaluation with pre-computed predictions."""
        step = ModelEvaluationStep(config={
            'problem_type': 'classification',
            'detailed_metrics': True
        })
        
        context = {
            'model': classification_data['model'],
            'y_true': classification_data['y_test'],
            'y_pred': classification_data['y_pred'],
            'y_pred_proba': classification_data['y_pred_proba'],
            'problem_type': 'classification',
            'num_features': classification_data['num_features'],
            'feature_names': classification_data['feature_names']
        }
        
        result = step.execute(context=context)
        
        assert result.status == StepStatus.COMPLETED
        assert result.metrics is not None
        assert 'accuracy' in result.metrics
        assert 'precision' in result.metrics
        assert 'recall' in result.metrics
        assert 'f1_score' in result.metrics
        assert 'roc_auc' in result.metrics
        
        # Check that metrics are in valid range
        assert 0 <= result.metrics['accuracy'] <= 1
        assert 0 <= result.metrics['precision'] <= 1
        assert 0 <= result.metrics['recall'] <= 1
        assert 0 <= result.metrics['f1_score'] <= 1
        assert 0 <= result.metrics['roc_auc'] <= 1
    
    def test_classification_evaluation_with_test_data(self, classification_data):
        """Test classification evaluation with test data (no predictions)."""
        step = ModelEvaluationStep(config={
            'problem_type': 'classification'
        })
        
        context = {
            'model': classification_data['model'],
            'X_test': classification_data['X_test'],
            'y_test': classification_data['y_test'],
            'problem_type': 'classification',
            'num_features': classification_data['num_features']
        }
        
        result = step.execute(context=context)
        
        assert result.status == StepStatus.COMPLETED
        assert 'accuracy' in result.metrics
        assert result.metrics['num_samples'] == len(classification_data['y_test'])
    
    def test_classification_artifacts(self, classification_data):
        """Test classification evaluation artifacts."""
        step = ModelEvaluationStep(config={
            'problem_type': 'classification',
            'detailed_metrics': True
        })
        
        context = {
            'model': classification_data['model'],
            'y_true': classification_data['y_test'],
            'y_pred': classification_data['y_pred'],
            'y_pred_proba': classification_data['y_pred_proba'],
            'problem_type': 'classification',
            'feature_names': classification_data['feature_names']
        }
        
        result = step.execute(context=context)
        
        assert result.artifacts is not None
        assert 'confusion_matrix' in result.artifacts
        assert 'roc_curve' in result.artifacts
        assert 'precision_recall_curve' in result.artifacts
        assert 'classification_report' in result.artifacts
        
        # Check confusion matrix shape
        cm = result.artifacts['confusion_matrix']
        assert len(cm) == 2  # Binary classification
        assert len(cm[0]) == 2
    
    def test_regression_evaluation(self, regression_data):
        """Test regression evaluation."""
        step = ModelEvaluationStep(config={
            'problem_type': 'regression'
        })
        
        context = {
            'model': regression_data['model'],
            'y_true': regression_data['y_test'],
            'y_pred': regression_data['y_pred'],
            'problem_type': 'regression',
            'num_features': regression_data['num_features'],
            'feature_names': regression_data['feature_names']
        }
        
        result = step.execute(context=context)
        
        assert result.status == StepStatus.COMPLETED
        assert result.metrics is not None
        assert 'mse' in result.metrics
        assert 'rmse' in result.metrics
        assert 'mae' in result.metrics
        assert 'r2' in result.metrics
        assert 'median_ae' in result.metrics
        
        # RMSE should be square root of MSE
        assert abs(result.metrics['rmse'] - np.sqrt(result.metrics['mse'])) < 1e-6
    
    def test_regression_artifacts(self, regression_data):
        """Test regression evaluation artifacts."""
        step = ModelEvaluationStep(config={
            'problem_type': 'regression',
            'residuals_analysis': True,
            'create_plots': True
        })
        
        context = {
            'model': regression_data['model'],
            'y_true': regression_data['y_test'],
            'y_pred': regression_data['y_pred'],
            'problem_type': 'regression'
        }
        
        result = step.execute(context=context)
        
        assert result.artifacts is not None
        assert 'residuals' in result.artifacts
        assert 'residuals_sample' in result.artifacts
        assert 'scatter_plot_data' in result.artifacts
        
        # Check residuals statistics
        residuals = result.artifacts['residuals']
        assert 'mean' in residuals
        assert 'std' in residuals
        assert 'median' in residuals
    
    def test_feature_importance(self, classification_data):
        """Test feature importance calculation."""
        step = ModelEvaluationStep(config={
            'feature_importance': True
        })
        
        context = {
            'model': classification_data['model'],
            'y_true': classification_data['y_test'],
            'y_pred': classification_data['y_pred'],
            'y_pred_proba': classification_data['y_pred_proba'],
            'problem_type': 'classification',
            'feature_names': classification_data['feature_names']
        }
        
        result = step.execute(context=context)
        
        assert result.artifacts is not None
        assert 'feature_importance' in result.artifacts
        
        importance = result.artifacts['feature_importance']
        assert len(importance) == len(classification_data['feature_names'])
        
        # Check that importances sum to approximately 1
        total_importance = sum(importance.values())
        assert abs(total_importance - 1.0) < 1e-6
        
        # Check that all importances are non-negative
        assert all(v >= 0 for v in importance.values())
    
    def test_cross_validation(self, classification_data):
        """Test cross-validation."""
        step = ModelEvaluationStep(config={
            'cross_validation': True,
            'cv_folds': 5
        })
        
        context = {
            'model': classification_data['model'],
            'X_train': classification_data['X_train'],
            'y_train': classification_data['y_train'],
            'y_true': classification_data['y_test'],
            'y_pred': classification_data['y_pred'],
            'y_pred_proba': classification_data['y_pred_proba'],
            'problem_type': 'classification'
        }
        
        result = step.execute(context=context)
        
        assert result.status == StepStatus.COMPLETED
        assert 'cross_validation' in result.metrics
        
        cv_results = result.metrics['cross_validation']
        assert 'cv_mean' in cv_results
        assert 'cv_std' in cv_results
        assert 'cv_scores' in cv_results
        assert len(cv_results['cv_scores']) == 5
    
    def test_error_analysis_classification(self, classification_data):
        """Test error analysis for classification."""
        step = ModelEvaluationStep(config={
            'error_analysis': True
        })
        
        context = {
            'model': classification_data['model'],
            'y_true': classification_data['y_test'],
            'y_pred': classification_data['y_pred'],
            'problem_type': 'classification'
        }
        
        result = step.execute(context=context)
        
        assert 'error_analysis' in result.metrics
        error_stats = result.metrics['error_analysis']
        
        assert 'num_misclassified' in error_stats
        assert 'misclassification_rate' in error_stats
        assert error_stats['misclassification_rate'] >= 0
        assert error_stats['misclassification_rate'] <= 1
    
    def test_error_analysis_regression(self, regression_data):
        """Test error analysis for regression."""
        step = ModelEvaluationStep(config={
            'error_analysis': True
        })
        
        context = {
            'model': regression_data['model'],
            'y_true': regression_data['y_test'],
            'y_pred': regression_data['y_pred'],
            'problem_type': 'regression'
        }
        
        result = step.execute(context=context)
        
        assert 'error_analysis' in result.metrics
        error_stats = result.metrics['error_analysis']
        
        assert 'mean_error' in error_stats
        assert 'std_error' in error_stats
        assert 'median_error' in error_stats
    
    def test_no_model_error(self):
        """Test error when no model is provided."""
        step = ModelEvaluationStep()
        
        result = step.execute(context={})
        
        assert result.status == StepStatus.FAILED
        assert result.errors is not None
        assert len(result.errors) > 0
    
    def test_no_predictions_or_test_data_error(self, classification_data):
        """Test error when neither predictions nor test data are provided."""
        step = ModelEvaluationStep()
        
        context = {
            'model': classification_data['model'],
            'problem_type': 'classification'
        }
        
        result = step.execute(context=context)
        
        assert result.status == StepStatus.FAILED
        assert result.errors is not None
    
    def test_validate_inputs(self):
        """Test input validation."""
        step = ModelEvaluationStep()
        
        # Evaluation step should always return True
        # as it can work with just context
        assert step.validate_inputs() == True
        assert step.validate_inputs(data=None, config={}) == True
    
    def test_performance_summary_classification(self, classification_data):
        """Test performance summary generation for classification."""
        step = ModelEvaluationStep()
        
        context = {
            'model': classification_data['model'],
            'y_true': classification_data['y_test'],
            'y_pred': classification_data['y_pred'],
            'y_pred_proba': classification_data['y_pred_proba'],
            'problem_type': 'classification'
        }
        
        result = step.execute(context=context)
        
        assert result.step_output is not None
        assert 'model_performance' in result.step_output
        
        summary = result.step_output['model_performance']
        assert 'Accuracy' in summary
        assert 'Precision' in summary
        assert 'Recall' in summary
        assert 'F1 Score' in summary
    
    def test_performance_summary_regression(self, regression_data):
        """Test performance summary generation for regression."""
        step = ModelEvaluationStep()
        
        context = {
            'model': regression_data['model'],
            'y_true': regression_data['y_test'],
            'y_pred': regression_data['y_pred'],
            'problem_type': 'regression'
        }
        
        result = step.execute(context=context)
        
        assert result.step_output is not None
        assert 'model_performance' in result.step_output
        
        summary = result.step_output['model_performance']
        assert 'R² Score' in summary
        assert 'RMSE' in summary
        assert 'MAE' in summary
    
    def test_multiclass_classification(self):
        """Test evaluation with multiclass classification."""
        # Generate multiclass data
        X, y = make_classification(
            n_samples=200,
            n_features=10,
            n_informative=7,
            n_classes=3,
            n_clusters_per_class=1,
            random_state=42
        )
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42
        )
        
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)
        
        step = ModelEvaluationStep()
        
        context = {
            'model': model,
            'y_true': y_test,
            'y_pred': y_pred,
            'y_pred_proba': y_pred_proba,
            'problem_type': 'classification'
        }
        
        result = step.execute(context=context)
        
        assert result.status == StepStatus.COMPLETED
        assert result.metrics['num_classes'] == 3
        assert result.metrics['is_binary'] == False
        assert 'roc_auc' in result.metrics  # Should still calculate multiclass ROC-AUC
    
    def test_model_without_feature_importance(self, classification_data):
        """Test evaluation with model that doesn't have feature importances."""
        # Use logistic regression which doesn't have feature_importances_
        X_train = classification_data['X_train']
        y_train = classification_data['y_train']
        X_test = classification_data['X_test']
        y_test = classification_data['y_test']
        
        model = LogisticRegression(random_state=42, max_iter=200)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)
        
        step = ModelEvaluationStep(config={'feature_importance': True})
        
        context = {
            'model': model,
            'y_true': y_test,
            'y_pred': y_pred,
            'y_pred_proba': y_pred_proba,
            'problem_type': 'classification'
        }
        
        result = step.execute(context=context)
        
        # Should complete successfully even without feature importances
        assert result.status == StepStatus.COMPLETED
        assert 'feature_importance_calculated' not in result.metrics
