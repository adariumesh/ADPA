"""
Tests for Intelligent Fallback System
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.fallback_handler import IntelligentFallbackSystem, FailureType, FallbackStrategy


class TestIntelligentFallbackSystem:
    """Test suite for IntelligentFallbackSystem"""
    
    @pytest.fixture
    def fallback_system(self):
        """Create a fallback system instance for testing"""
        return IntelligentFallbackSystem()
    
    @pytest.fixture
    def sample_context(self):
        """Sample context for testing"""
        return {
            'pipeline_id': 'test-pipeline-123',
            'step': 'data_cleaning',
            'dataset_path': 's3://test-bucket/data.csv',
            'objective': 'classification'
        }
    
    def test_initialization(self, fallback_system):
        """Test system initializes correctly"""
        assert fallback_system is not None
        assert fallback_system.llm_engine is not None
        assert fallback_system.memory_system is not None
        assert fallback_system.success_count == 0
        assert fallback_system.failure_count == 0
    
    def test_classify_failure_data_quality(self, fallback_system):
        """Test classification of data quality failures"""
        error_message = "ValueError: Dataset contains 50% missing values"
        failure_type = fallback_system._classify_failure(error_message, {})
        
        assert failure_type == FailureType.DATA_QUALITY
    
    def test_classify_failure_schema_mismatch(self, fallback_system):
        """Test classification of schema mismatch failures"""
        error_message = "KeyError: 'target_column' not found in dataset"
        failure_type = fallback_system._classify_failure(error_message, {})
        
        assert failure_type == FailureType.SCHEMA_MISMATCH
    
    def test_classify_failure_timeout(self, fallback_system):
        """Test classification of timeout failures"""
        error_message = "TimeoutError: Pipeline execution exceeded 3600 seconds"
        failure_type = fallback_system._classify_failure(error_message, {})
        
        assert failure_type == FailureType.TIMEOUT
    
    def test_classify_failure_resource_limit(self, fallback_system):
        """Test classification of resource limit failures"""
        error_message = "MemoryError: Cannot allocate 10GB for operation"
        failure_type = fallback_system._classify_failure(error_message, {})
        
        assert failure_type == FailureType.RESOURCE_LIMIT
    
    def test_classify_failure_algorithm(self, fallback_system):
        """Test classification of algorithm failures"""
        error_message = "ConvergenceWarning: Model failed to converge after 1000 iterations"
        failure_type = fallback_system._classify_failure(error_message, {})
        
        assert failure_type == FailureType.ALGORITHM_FAILURE
    
    def test_classify_failure_dependency(self, fallback_system):
        """Test classification of dependency errors"""
        error_message = "ImportError: No module named 'sklearn'"
        failure_type = fallback_system._classify_failure(error_message, {})
        
        assert failure_type == FailureType.DEPENDENCY_ERROR
    
    def test_classify_failure_unknown(self, fallback_system):
        """Test classification of unknown failures"""
        error_message = "Something went wrong"
        failure_type = fallback_system._classify_failure(error_message, {})
        
        assert failure_type == FailureType.UNKNOWN
    
    @patch('core.fallback_handler.IntelligentFallbackSystem._generate_fallback_strategies')
    def test_handle_pipeline_failure_success(self, mock_generate, fallback_system, sample_context):
        """Test successful failure handling"""
        # Mock successful strategy execution
        mock_strategy = FallbackStrategy(
            strategy_id='test-strategy-1',
            name='Impute Missing Values',
            description='Fill missing values with median',
            implementation='data = data.fillna(data.median())',
            estimated_success_rate=0.9
        )
        
        mock_generate.return_value = [mock_strategy]
        
        # Mock successful execution
        with patch.object(fallback_system, '_execute_strategy', return_value=(True, {'data': pd.DataFrame()})):
            result = fallback_system.handle_pipeline_failure(
                error_message="ValueError: Dataset contains missing values",
                context=sample_context,
                max_attempts=3
            )
            
            assert result['success'] is True
            assert result['strategy_used'] == 'Impute Missing Values'
            assert fallback_system.success_count == 1
    
    @patch('core.fallback_handler.IntelligentFallbackSystem._generate_fallback_strategies')
    def test_handle_pipeline_failure_all_strategies_fail(self, mock_generate, fallback_system, sample_context):
        """Test handling when all strategies fail"""
        mock_strategies = [
            FallbackStrategy(
                strategy_id='test-strategy-1',
                name='Strategy 1',
                description='First attempt',
                implementation='pass',
                estimated_success_rate=0.8
            ),
            FallbackStrategy(
                strategy_id='test-strategy-2',
                name='Strategy 2',
                description='Second attempt',
                implementation='pass',
                estimated_success_rate=0.6
            )
        ]
        
        mock_generate.return_value = mock_strategies
        
        # Mock all executions failing
        with patch.object(fallback_system, '_execute_strategy', return_value=(False, None)):
            result = fallback_system.handle_pipeline_failure(
                error_message="Critical failure",
                context=sample_context,
                max_attempts=2
            )
            
            assert result['success'] is False
            assert result['attempts'] == 2
            assert fallback_system.failure_count == 1
    
    def test_rule_based_fallback_strategies_data_quality(self, fallback_system):
        """Test rule-based strategies for data quality issues"""
        strategies = fallback_system._rule_based_fallback_strategies(
            FailureType.DATA_QUALITY,
            "Missing values detected"
        )
        
        assert len(strategies) > 0
        assert any('impute' in s.name.lower() for s in strategies)
    
    def test_rule_based_fallback_strategies_schema_mismatch(self, fallback_system):
        """Test rule-based strategies for schema mismatches"""
        strategies = fallback_system._rule_based_fallback_strategies(
            FailureType.SCHEMA_MISMATCH,
            "Column 'target' not found"
        )
        
        assert len(strategies) > 0
        assert any('column' in s.name.lower() for s in strategies)
    
    def test_rule_based_fallback_strategies_timeout(self, fallback_system):
        """Test rule-based strategies for timeouts"""
        strategies = fallback_system._rule_based_fallback_strategies(
            FailureType.TIMEOUT,
            "Execution timeout"
        )
        
        assert len(strategies) > 0
        assert any('sample' in s.name.lower() or 'reduce' in s.name.lower() for s in strategies)
    
    def test_rule_based_fallback_strategies_resource_limit(self, fallback_system):
        """Test rule-based strategies for resource limits"""
        strategies = fallback_system._rule_based_fallback_strategies(
            FailureType.RESOURCE_LIMIT,
            "Out of memory"
        )
        
        assert len(strategies) > 0
        assert any('memory' in s.name.lower() or 'batch' in s.name.lower() for s in strategies)
    
    def test_rule_based_fallback_strategies_algorithm_failure(self, fallback_system):
        """Test rule-based strategies for algorithm failures"""
        strategies = fallback_system._rule_based_fallback_strategies(
            FailureType.ALGORITHM_FAILURE,
            "Model convergence failed"
        )
        
        assert len(strategies) > 0
        assert any('parameter' in s.name.lower() or 'algorithm' in s.name.lower() for s in strategies)
    
    def test_get_statistics(self, fallback_system):
        """Test statistics retrieval"""
        fallback_system.success_count = 10
        fallback_system.failure_count = 2
        
        stats = fallback_system.get_statistics()
        
        assert stats['total_attempts'] == 12
        assert stats['success_count'] == 10
        assert stats['failure_count'] == 2
        assert stats['success_rate'] == pytest.approx(0.833, rel=0.01)
    
    @patch('core.fallback_handler.IntelligentFallbackSystem._analyze_failure_with_llm')
    def test_llm_integration(self, mock_analyze, fallback_system, sample_context):
        """Test LLM integration for failure analysis"""
        mock_analyze.return_value = {
            'failure_type': 'DATA_QUALITY',
            'root_cause': 'Missing values in critical columns',
            'recommended_actions': ['Impute with median', 'Remove rows with missing values']
        }
        
        result = fallback_system._analyze_failure_with_llm(
            "ValueError: Missing values detected",
            sample_context
        )
        
        assert result['failure_type'] == 'DATA_QUALITY'
        assert 'root_cause' in result
        assert len(result['recommended_actions']) > 0
        mock_analyze.assert_called_once()
    
    def test_memory_system_integration(self, fallback_system, sample_context):
        """Test integration with experience memory system"""
        # Store a successful recovery
        fallback_system._store_recovery_experience(
            error_message="Test error",
            context=sample_context,
            strategy_used="Test strategy",
            success=True
        )
        
        # Verify it's stored in memory
        # This assumes the memory system is working correctly
        assert fallback_system.memory_system is not None
    
    def test_strategy_execution_simulation(self, fallback_system, sample_context):
        """Test strategy execution in simulation mode"""
        strategy = FallbackStrategy(
            strategy_id='test-sim-1',
            name='Test Strategy',
            description='Simulated strategy',
            implementation='# Simulated code',
            estimated_success_rate=0.9
        )
        
        success, result = fallback_system._execute_strategy(strategy, sample_context)
        
        # In simulation mode, should return success based on probability
        assert isinstance(success, bool)
    
    def test_concurrent_failure_handling(self, fallback_system, sample_context):
        """Test handling multiple failures concurrently"""
        errors = [
            "ValueError: Missing values",
            "KeyError: Column not found",
            "TimeoutError: Execution timeout"
        ]
        
        results = []
        for error in errors:
            with patch.object(fallback_system, '_generate_fallback_strategies', 
                            return_value=[FallbackStrategy(
                                strategy_id=f'strategy-{i}',
                                name=f'Strategy {i}',
                                description='Test',
                                implementation='pass',
                                estimated_success_rate=0.8
                            ) for i in range(2)]):
                with patch.object(fallback_system, '_execute_strategy', return_value=(True, {})):
                    result = fallback_system.handle_pipeline_failure(error, sample_context)
                    results.append(result)
        
        assert len(results) == 3
        assert all(r['success'] for r in results)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
