"""
Data ingestion pipeline step.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import boto3
from io import StringIO

from ...agent.core.interfaces import PipelineStep, PipelineStepType, ExecutionResult, StepStatus


class DataIngestionStep(PipelineStep):
    """
    Pipeline step for data ingestion from various sources.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.INGESTION, "data_ingestion")
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    def execute(self, 
                data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Execute data ingestion step.
        
        Args:
            data: Input data (optional if loading from source)
            config: Step configuration
            context: Execution context
            
        Returns:
            ExecutionResult with loaded data
        """
        try:
            self.logger.info("Starting data ingestion...")
            
            # Merge configurations
            ingestion_config = {**self.config, **(config or {})}
            
            # Determine data source
            source_type = ingestion_config.get('source_type', 'dataframe')
            
            if source_type == 'dataframe' and data is not None:
                loaded_data = data
                source_info = "dataframe_input"
            elif source_type == 's3':
                loaded_data = self._load_from_s3(ingestion_config)
                source_info = ingestion_config.get('s3_path', 'unknown')
            elif source_type == 'file':
                loaded_data = self._load_from_file(ingestion_config)
                source_info = ingestion_config.get('file_path', 'unknown')
            else:
                return ExecutionResult(
                    status=StepStatus.FAILED,
                    errors=[f"Unsupported source type: {source_type}"]
                )
            
            # Basic validation
            if loaded_data.empty:
                return ExecutionResult(
                    status=StepStatus.FAILED,
                    errors=["Loaded data is empty"]
                )
            
            ingestion_stats = {
                'source_type': source_type,
                'source_info': source_info,
                'rows_loaded': len(loaded_data),
                'columns_loaded': len(loaded_data.columns),
                'data_types': loaded_data.dtypes.value_counts().to_dict(),
                'memory_usage_mb': loaded_data.memory_usage(deep=True).sum() / 1024 / 1024
            }
            
            self.logger.info(f"Data ingestion completed. Loaded {len(loaded_data)} rows, {len(loaded_data.columns)} columns")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=loaded_data,
                metrics=ingestion_stats,
                step_output={
                    'data_loaded': True,
                    'dataset_shape': loaded_data.shape,
                    'source': source_info
                }
            )
            
        except Exception as e:
            self.logger.error(f"Data ingestion failed: {str(e)}")
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[f"Data ingestion error: {str(e)}"]
            )
    
    def _load_from_s3(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Load data from S3."""
        s3_path = config['s3_path']
        bucket, key = s3_path.replace('s3://', '').split('/', 1)
        
        s3 = boto3.client('s3')
        obj = s3.get_object(Bucket=bucket, Key=key)
        
        if key.endswith('.csv'):
            return pd.read_csv(StringIO(obj['Body'].read().decode('utf-8')))
        elif key.endswith('.json'):
            return pd.read_json(StringIO(obj['Body'].read().decode('utf-8')))
        else:
            raise ValueError(f"Unsupported file format: {key}")
    
    def _load_from_file(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Load data from local file."""
        file_path = config['file_path']
        
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        elif file_path.endswith('.json'):
            return pd.read_json(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")
    
    def validate_inputs(self, 
                       data: Optional[pd.DataFrame] = None,
                       config: Optional[Dict[str, Any]] = None,
                       context: Optional[Dict[str, Any]] = None) -> bool:
        """Validate inputs for data ingestion step."""
        ingestion_config = {**self.config, **(config or {})}
        source_type = ingestion_config.get('source_type', 'dataframe')
        
        if source_type == 'dataframe' and data is None:
            self.logger.error("No data provided for dataframe source type")
            return False
        
        if source_type == 's3' and not ingestion_config.get('s3_path'):
            self.logger.error("No S3 path provided for S3 source type")
            return False
        
        if source_type == 'file' and not ingestion_config.get('file_path'):
            self.logger.error("No file path provided for file source type")
            return False
        
        return True
    
    def get_requirements(self) -> Dict[str, Any]:
        """Get step requirements."""
        return {
            "required_inputs": [],
            "optional_inputs": ["data", "config", "context"],
            "required_config": ["source_type"],
            "optional_config": ["s3_path", "file_path"],
            "produces": ["loaded_data", "ingestion_stats"]
        }