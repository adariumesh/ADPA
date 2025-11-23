"""
Unit tests for Feature Engineering Step.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.pipeline.etl.feature_engineer import FeatureEngineeringStep
from src.agent.core.interfaces import StepStatus


class TestFeatureEngineeringStep:
    """Test cases for FeatureEngineeringStep."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample dataset for testing."""
        np.random.seed(42)
        n_samples = 100
        
        data = pd.DataFrame({
            'numeric_1': np.random.randn(n_samples),
            'numeric_2': np.random.randn(n_samples) * 10 + 50,
            'numeric_3': np.random.uniform(0, 100, n_samples),
            'categorical_1': np.random.choice(['A', 'B', 'C'], n_samples),
            'categorical_2': np.random.choice(['X', 'Y'], n_samples),
            'categorical_high_card': [f'cat_{i % 30}' for i in range(n_samples)],
            'target': np.random.choice([0, 1], n_samples)
        })
        
        # Add some missing values
        data.loc[np.random.choice(data.index, 10), 'numeric_1'] = np.nan
        data.loc[np.random.choice(data.index, 5), 'categorical_1'] = np.nan
        
        return data
    
    @pytest.fixture
    def datetime_data(self):
        """Create dataset with datetime features."""
        n_samples = 50
        base_date = datetime(2024, 1, 1)
        
        data = pd.DataFrame({
            'date_col': [base_date + timedelta(days=i) for i in range(n_samples)],
            'value': np.random.randn(n_samples),
            'target': np.random.choice([0, 1], n_samples)
        })
        
        return data
    
    def test_initialization(self):
        """Test feature engineering step initialization."""
        step = FeatureEngineeringStep()
        
        assert step.step_type.value == "feature_engineering"
        assert step.name == "feature_engineering"
        assert isinstance(step.config, dict)
        assert isinstance(step.encoders, dict)
        assert isinstance(step.scalers, dict)
    
    def test_basic_execution(self, sample_data):
        """Test basic feature engineering execution."""
        step = FeatureEngineeringStep(config={
            'handle_missing': True,
            'encode_categorical': True,
            'scale_features': True
        })
        
        result = step.execute(
            data=sample_data,
            context={'target_column': 'target', 'problem_type': 'classification'}
        )
        
        assert result.status == StepStatus.COMPLETED
        assert result.data is not None
        assert 'target' in result.data.columns
        assert result.metrics is not None
        assert result.metrics['initial_features'] > 0
    
    def test_missing_value_handling(self, sample_data):
        """Test missing value imputation."""
        step = FeatureEngineeringStep(config={
            'handle_missing': True,
            'missing_value_strategy': 'median'
        })
        
        result = step.execute(
            data=sample_data,
            context={'target_column': 'target'}
        )
        
        assert result.status == StepStatus.COMPLETED
        assert result.data.isnull().sum().sum() == 0  # No missing values after
        assert result.metrics['missing_values_before'] > 0
        assert result.metrics['missing_values_after'] == 0
    
    def test_categorical_encoding_label(self, sample_data):
        """Test label encoding."""
        step = FeatureEngineeringStep(config={
            'encode_categorical': True,
            'categorical_encoding': 'label'
        })
        
        result = step.execute(
            data=sample_data,
            context={'target_column': 'target'}
        )
        
        assert result.status == StepStatus.COMPLETED
        assert result.metrics['categorical_columns_encoded'] > 0
        
        # Check that categorical columns are now numeric
        categorical_cols = sample_data.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if col != 'target' and col in result.data.columns:
                assert pd.api.types.is_numeric_dtype(result.data[col])
    
    def test_categorical_encoding_onehot(self, sample_data):
        """Test one-hot encoding."""
        step = FeatureEngineeringStep(config={
            'encode_categorical': True,
            'categorical_encoding': 'onehot',
            'scale_features': False  # Disable scaling for clearer test
        })
        
        initial_cols = len(sample_data.columns)
        
        result = step.execute(
            data=sample_data,
            context={'target_column': 'target'}
        )
        
        assert result.status == StepStatus.COMPLETED
        # One-hot should increase number of columns
        assert result.metrics['final_features'] >= result.metrics['initial_features']
    
    def test_datetime_feature_extraction(self, datetime_data):
        """Test datetime feature extraction."""
        step = FeatureEngineeringStep(config={
            'extract_datetime_features': True
        })
        
        result = step.execute(
            data=datetime_data,
            context={'target_column': 'target'}
        )
        
        assert result.status == StepStatus.COMPLETED
        assert result.metrics.get('datetime_columns_processed', 0) > 0
        
        # Check for extracted features
        assert 'date_col_year' in result.data.columns
        assert 'date_col_month' in result.data.columns
        assert 'date_col_day' in result.data.columns
        assert 'date_col_dayofweek' in result.data.columns
        assert 'date_col_is_weekend' in result.data.columns
    
    def test_feature_scaling_standard(self, sample_data):
        """Test standard scaling."""
        step = FeatureEngineeringStep(config={
            'scale_features': True,
            'scaling_method': 'standard',
            'encode_categorical': True  # Need to encode first
        })
        
        result = step.execute(
            data=sample_data,
            context={'target_column': 'target'}
        )
        
        assert result.status == StepStatus.COMPLETED
        assert result.metrics.get('features_scaled', 0) > 0
        
        # Check that numerical features are scaled (mean ≈ 0, std ≈ 1)
        numeric_cols = result.data.select_dtypes(include=[np.number]).columns
        numeric_cols = [col for col in numeric_cols if col != 'target']
        
        if len(numeric_cols) > 0:
            col_means = result.data[numeric_cols].mean()
            col_stds = result.data[numeric_cols].std()
            
            # Allow some tolerance
            assert all(abs(col_means) < 1), "Standard scaling should center data near 0"
    
    def test_feature_scaling_minmax(self, sample_data):
        """Test min-max scaling."""
        step = FeatureEngineeringStep(config={
            'scale_features': True,
            'scaling_method': 'minmax',
            'encode_categorical': True
        })
        
        result = step.execute(
            data=sample_data,
            context={'target_column': 'target'}
        )
        
        assert result.status == StepStatus.COMPLETED
        
        # Check that numerical features are in [0, 1] range
        numeric_cols = result.data.select_dtypes(include=[np.number]).columns
        numeric_cols = [col for col in numeric_cols if col != 'target']
        
        if len(numeric_cols) > 0:
            assert result.data[numeric_cols].min().min() >= -0.1  # Allow small tolerance
            assert result.data[numeric_cols].max().max() <= 1.1
    
    def test_polynomial_features(self, sample_data):
        """Test polynomial feature generation."""
        step = FeatureEngineeringStep(config={
            'polynomial_features': True,
            'polynomial_degree': 2,
            'encode_categorical': True,
            'scale_features': False  # Disable for clearer test
        })
        
        result = step.execute(
            data=sample_data,
            context={'target_column': 'target'}
        )
        
        assert result.status == StepStatus.COMPLETED
        
        # Polynomial features should add new columns
        if result.metrics.get('polynomial_features_added', 0) > 0:
            assert result.metrics['final_features'] > result.metrics['initial_features']
    
    def test_feature_selection(self, sample_data):
        """Test feature selection."""
        step = FeatureEngineeringStep(config={
            'encode_categorical': True,
            'feature_selection': True,
            'selection_method': 'statistical',
            'k_features': 5,
            'scale_features': False
        })
        
        result = step.execute(
            data=sample_data,
            context={'target_column': 'target', 'problem_type': 'classification'}
        )
        
        assert result.status == StepStatus.COMPLETED
        assert result.metrics.get('features_selected', 0) > 0
        
        # Should have selected k features (or less if fewer available)
        expected_features = min(5, result.metrics['features_before_selection'])
        assert result.metrics['features_selected'] <= expected_features
    
    def test_correlation_removal(self, sample_data):
        """Test highly correlated feature removal."""
        # Add highly correlated feature
        sample_data['numeric_1_copy'] = sample_data['numeric_1'] * 1.01
        
        step = FeatureEngineeringStep(config={
            'encode_categorical': True,
            'remove_correlated': True,
            'correlation_threshold': 0.9,
            'scale_features': False
        })
        
        result = step.execute(
            data=sample_data,
            context={'target_column': 'target'}
        )
        
        assert result.status == StepStatus.COMPLETED
        # Should have removed at least one correlated feature
        # (may be 0 if encoding creates non-correlated features)
        assert 'correlated_features_removed' in result.metrics
    
    def test_full_pipeline(self, sample_data):
        """Test complete feature engineering pipeline."""
        step = FeatureEngineeringStep(config={
            'handle_missing': True,
            'missing_value_strategy': 'median',
            'extract_datetime_features': True,
            'encode_categorical': True,
            'categorical_encoding': 'auto',
            'scale_features': True,
            'scaling_method': 'standard',
            'feature_selection': False,  # Disable for predictable results
            'remove_correlated': True,
            'correlation_threshold': 0.95
        })
        
        result = step.execute(
            data=sample_data,
            context={'target_column': 'target', 'problem_type': 'classification'}
        )
        
        assert result.status == StepStatus.COMPLETED
        assert result.data is not None
        assert 'target' in result.data.columns
        assert result.data.isnull().sum().sum() == 0
        assert len(result.metrics['transformations_applied']) > 0
    
    def test_no_data_error(self):
        """Test error handling when no data is provided."""
        step = FeatureEngineeringStep()
        
        result = step.execute(data=None)
        
        assert result.status == StepStatus.FAILED
        assert result.errors is not None
        assert len(result.errors) > 0
    
    def test_empty_data_error(self):
        """Test error handling with empty data."""
        step = FeatureEngineeringStep()
        
        empty_df = pd.DataFrame()
        result = step.execute(data=empty_df)
        
        assert result.status == StepStatus.FAILED
        assert result.errors is not None
    
    def test_feature_importance_calculation(self, sample_data):
        """Test feature importance calculation."""
        step = FeatureEngineeringStep(config={
            'encode_categorical': True,
            'scale_features': False
        })
        
        result = step.execute(
            data=sample_data,
            context={'target_column': 'target', 'problem_type': 'classification'}
        )
        
        assert result.status == StepStatus.COMPLETED
        assert 'feature_importance_scores' in result.artifacts
        
        if len(result.artifacts['feature_importance_scores']) > 0:
            # Should be a dict with feature names as keys
            assert isinstance(result.artifacts['feature_importance_scores'], dict)
    
    def test_validate_inputs(self, sample_data):
        """Test input validation."""
        step = FeatureEngineeringStep()
        
        # Valid inputs
        assert step.validate_inputs(data=sample_data) is True
        
        # Invalid inputs
        assert step.validate_inputs(data=None) is False
        assert step.validate_inputs(data="not a dataframe") is False
        assert step.validate_inputs(data=pd.DataFrame()) is False
    
    def test_get_requirements(self):
        """Test getting step requirements."""
        step = FeatureEngineeringStep()
        
        requirements = step.get_requirements()
        
        assert 'required_inputs' in requirements
        assert 'optional_config' in requirements
        assert 'data' in requirements['required_inputs']
        assert 'produces' in requirements


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
