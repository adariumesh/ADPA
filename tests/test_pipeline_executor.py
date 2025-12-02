"""
Tests for Real Pipeline Executor
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from orchestration.pipeline_executor import RealPipelineExecutor


class TestRealPipelineExecutor:
    """Test suite for RealPipelineExecutor"""
    
    @pytest.fixture
    def executor(self):
        """Create a pipeline executor instance for testing"""
        with patch('boto3.client'):
            return RealPipelineExecutor(region='us-east-2')
    
    @pytest.fixture
    def sample_dataset(self):
        """Sample dataset for testing"""
        return pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': ['A', 'B', 'C', 'D', 'E'],
            'target': [0, 1, 0, 1, 0]
        })
    
    @pytest.fixture
    def sample_config(self):
        """Sample pipeline configuration"""
        return {
            'objective': 'classification',
            'target_column': 'target',
            'feature_columns': ['feature1', 'feature2'],
            'model_type': 'random_forest',
            'hyperparameters': {
                'n_estimators': 100,
                'max_depth': 10
            }
        }
    
    def test_initialization(self, executor):
        """Test executor initializes correctly"""
        assert executor is not None
        assert executor.region == 'us-east-2'
        assert executor.s3_client is not None
        assert executor.sfn_client is not None
        assert executor.sagemaker_client is not None
    
    @patch('boto3.client')
    def test_upload_to_s3_success(self, mock_boto, executor, sample_dataset):
        """Test successful S3 upload"""
        mock_s3 = MagicMock()
        executor.s3_client = mock_s3
        
        s3_path = executor._upload_to_s3(
            sample_dataset,
            bucket='test-bucket',
            key='test-data.csv'
        )
        
        assert s3_path == 's3://test-bucket/test-data.csv'
        mock_s3.upload_file.assert_called_once()
    
    @patch('boto3.client')
    def test_upload_to_s3_error(self, mock_boto, executor, sample_dataset):
        """Test S3 upload error handling"""
        mock_s3 = MagicMock()
        mock_s3.upload_file.side_effect = Exception("Upload failed")
        executor.s3_client = mock_s3
        
        with pytest.raises(Exception, match="Upload failed"):
            executor._upload_to_s3(
                sample_dataset,
                bucket='test-bucket',
                key='test-data.csv'
            )
    
    @patch('boto3.client')
    def test_start_stepfunctions_execution(self, mock_boto, executor, sample_config):
        """Test Step Functions execution start"""
        mock_sfn = MagicMock()
        mock_sfn.start_execution.return_value = {
            'executionArn': 'arn:aws:states:us-east-2:123456789012:execution:test-state-machine:test-execution'
        }
        executor.sfn_client = mock_sfn
        
        execution_arn = executor._start_stepfunctions_execution(
            state_machine_arn='arn:aws:states:us-east-2:123456789012:stateMachine:test-state-machine',
            execution_input={
                'dataset_path': 's3://test-bucket/data.csv',
                'config': sample_config
            }
        )
        
        assert 'execution:test-state-machine' in execution_arn
        mock_sfn.start_execution.assert_called_once()
    
    @patch('boto3.client')
    def test_monitor_execution_success(self, mock_boto, executor):
        """Test successful execution monitoring"""
        mock_sfn = MagicMock()
        
        # Simulate execution completing after 2 polls
        mock_sfn.describe_execution.side_effect = [
            {'status': 'RUNNING', 'output': None},
            {'status': 'SUCCEEDED', 'output': json.dumps({'result': 'success'})}
        ]
        executor.sfn_client = mock_sfn
        
        status, output = executor._monitor_execution(
            execution_arn='test-arn',
            poll_interval=0.1  # Fast polling for tests
        )
        
        assert status == 'SUCCEEDED'
        assert output == {'result': 'success'}
    
    @patch('boto3.client')
    def test_monitor_execution_failure(self, mock_boto, executor):
        """Test failed execution monitoring"""
        mock_sfn = MagicMock()
        mock_sfn.describe_execution.return_value = {
            'status': 'FAILED',
            'output': json.dumps({'error': 'Pipeline failed'})
        }
        executor.sfn_client = mock_sfn
        
        status, output = executor._monitor_execution(
            execution_arn='test-arn',
            poll_interval=0.1
        )
        
        assert status == 'FAILED'
        assert 'error' in output
    
    @patch('boto3.client')
    def test_monitor_execution_timeout(self, mock_boto, executor):
        """Test execution timeout handling"""
        mock_sfn = MagicMock()
        mock_sfn.describe_execution.return_value = {
            'status': 'RUNNING',
            'output': None
        }
        executor.sfn_client = mock_sfn
        
        # Should timeout quickly
        status, output = executor._monitor_execution(
            execution_arn='test-arn',
            poll_interval=0.1,
            max_wait_time=0.5  # 0.5 seconds timeout
        )
        
        assert status == 'TIMEOUT'
    
    @patch('boto3.client')
    def test_execute_pipeline_full_flow(self, mock_boto, executor, sample_dataset, sample_config):
        """Test complete pipeline execution flow"""
        # Mock S3 upload
        mock_s3 = MagicMock()
        executor.s3_client = mock_s3
        
        # Mock Step Functions
        mock_sfn = MagicMock()
        mock_sfn.start_execution.return_value = {
            'executionArn': 'test-execution-arn'
        }
        mock_sfn.describe_execution.return_value = {
            'status': 'SUCCEEDED',
            'output': json.dumps({
                'model_path': 's3://test-bucket/model.tar.gz',
                'metrics': {'accuracy': 0.95}
            })
        }
        executor.sfn_client = mock_sfn
        
        # Mock CloudWatch
        mock_cw = MagicMock()
        executor.cloudwatch = mock_cw
        
        result = executor.execute_pipeline(
            dataset=sample_dataset,
            config=sample_config,
            state_machine_arn='test-state-machine-arn',
            s3_bucket='test-bucket'
        )
        
        assert result['status'] == 'SUCCEEDED'
        assert 'model_path' in result['output']
        assert result['output']['metrics']['accuracy'] == 0.95
        
        # Verify all clients were called
        mock_s3.upload_file.assert_called()
        mock_sfn.start_execution.assert_called_once()
        mock_cw.put_metric_data.assert_called()
    
    @patch('boto3.client')
    def test_train_sagemaker_model(self, mock_boto, executor, sample_config):
        """Test SageMaker training job creation"""
        mock_sagemaker = MagicMock()
        mock_sagemaker.create_training_job.return_value = {
            'TrainingJobArn': 'test-training-job-arn'
        }
        mock_sagemaker.describe_training_job.return_value = {
            'TrainingJobStatus': 'Completed',
            'ModelArtifacts': {
                'S3ModelArtifacts': 's3://test-bucket/model.tar.gz'
            }
        }
        executor.sagemaker_client = mock_sagemaker
        
        result = executor.train_sagemaker_model(
            training_data_path='s3://test-bucket/train.csv',
            output_path='s3://test-bucket/output',
            role_arn='test-role-arn',
            config=sample_config
        )
        
        assert result['status'] == 'Completed'
        assert 's3://test-bucket/model.tar.gz' in result['model_path']
        mock_sagemaker.create_training_job.assert_called_once()
    
    @patch('boto3.client')
    def test_send_cloudwatch_metrics(self, mock_boto, executor):
        """Test CloudWatch metrics submission"""
        mock_cw = MagicMock()
        executor.cloudwatch = mock_cw
        
        executor._send_cloudwatch_metrics(
            metric_name='PipelineExecutions',
            value=1,
            unit='Count'
        )
        
        mock_cw.put_metric_data.assert_called_once()
        call_args = mock_cw.put_metric_data.call_args
        assert call_args[1]['Namespace'] == 'ADPA/Pipelines'
        assert call_args[1]['MetricData'][0]['MetricName'] == 'PipelineExecutions'
        assert call_args[1]['MetricData'][0]['Value'] == 1
    
    @patch('boto3.client')
    def test_error_handling_in_execution(self, mock_boto, executor, sample_dataset, sample_config):
        """Test error handling during pipeline execution"""
        # Mock S3 to fail
        mock_s3 = MagicMock()
        mock_s3.upload_file.side_effect = Exception("S3 upload failed")
        executor.s3_client = mock_s3
        
        with pytest.raises(Exception):
            executor.execute_pipeline(
                dataset=sample_dataset,
                config=sample_config,
                state_machine_arn='test-state-machine-arn',
                s3_bucket='test-bucket'
            )
    
    @patch('boto3.client')
    def test_parallel_executions(self, mock_boto, executor, sample_dataset, sample_config):
        """Test handling multiple parallel pipeline executions"""
        # Mock successful execution
        mock_s3 = MagicMock()
        mock_sfn = MagicMock()
        mock_sfn.start_execution.return_value = {'executionArn': 'test-arn'}
        mock_sfn.describe_execution.return_value = {
            'status': 'SUCCEEDED',
            'output': json.dumps({'result': 'success'})
        }
        
        executor.s3_client = mock_s3
        executor.sfn_client = mock_sfn
        executor.cloudwatch = MagicMock()
        
        # Execute multiple pipelines
        results = []
        for i in range(3):
            config = sample_config.copy()
            config['pipeline_id'] = f'pipeline-{i}'
            
            result = executor.execute_pipeline(
                dataset=sample_dataset,
                config=config,
                state_machine_arn='test-state-machine',
                s3_bucket='test-bucket'
            )
            results.append(result)
        
        assert len(results) == 3
        assert all(r['status'] == 'SUCCEEDED' for r in results)
    
    @patch('boto3.client')
    def test_execution_with_custom_timeout(self, mock_boto, executor, sample_dataset, sample_config):
        """Test execution with custom timeout settings"""
        mock_s3 = MagicMock()
        mock_sfn = MagicMock()
        mock_sfn.start_execution.return_value = {'executionArn': 'test-arn'}
        mock_sfn.describe_execution.return_value = {
            'status': 'RUNNING',
            'output': None
        }
        
        executor.s3_client = mock_s3
        executor.sfn_client = mock_sfn
        executor.cloudwatch = MagicMock()
        
        result = executor.execute_pipeline(
            dataset=sample_dataset,
            config=sample_config,
            state_machine_arn='test-state-machine',
            s3_bucket='test-bucket',
            max_wait_time=1  # 1 second timeout
        )
        
        assert result['status'] == 'TIMEOUT'
    
    def test_configuration_validation(self, executor, sample_dataset):
        """Test pipeline configuration validation"""
        invalid_config = {
            # Missing required fields
            'objective': 'classification'
        }
        
        # Should handle missing configuration gracefully
        with pytest.raises((KeyError, ValueError)):
            executor.execute_pipeline(
                dataset=sample_dataset,
                config=invalid_config,
                state_machine_arn='test-state-machine',
                s3_bucket='test-bucket'
            )
    
    @patch('boto3.client')
    def test_execution_metrics_tracking(self, mock_boto, executor, sample_dataset, sample_config):
        """Test that execution metrics are properly tracked"""
        mock_s3 = MagicMock()
        mock_sfn = MagicMock()
        mock_sfn.start_execution.return_value = {'executionArn': 'test-arn'}
        mock_sfn.describe_execution.return_value = {
            'status': 'SUCCEEDED',
            'output': json.dumps({'metrics': {'accuracy': 0.92}})
        }
        mock_cw = MagicMock()
        
        executor.s3_client = mock_s3
        executor.sfn_client = mock_sfn
        executor.cloudwatch = mock_cw
        
        executor.execute_pipeline(
            dataset=sample_dataset,
            config=sample_config,
            state_machine_arn='test-state-machine',
            s3_bucket='test-bucket'
        )
        
        # Verify metrics were sent
        assert mock_cw.put_metric_data.called
        
        # Check that success metrics were sent
        calls = mock_cw.put_metric_data.call_args_list
        metric_names = [call[1]['MetricData'][0]['MetricName'] for call in calls]
        
        assert 'PipelineExecutions' in metric_names
        assert 'ExecutionsSucceeded' in metric_names


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
