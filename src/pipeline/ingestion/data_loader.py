"""
Data ingestion pipeline step.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd

from ...agent.core.interfaces import PipelineStep, PipelineStepType, ExecutionResult, StepStatus


class DataIngestionStep(PipelineStep):
    """
    Pipeline step for data ingestion and loading.
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
            data: Input data (if already loaded)
            config: Step configuration
            context: Execution context
            
        Returns:
            ExecutionResult with loaded data
        """
        try:
            self.logger.info("Starting data ingestion...")
            
            # If data is already provided, just validate and return it
            if data is not None:
                self.logger.info(f"Data already loaded: {data.shape}")
                return ExecutionResult(
                    status=StepStatus.COMPLETED,
                    data=data,
                    metrics={
                        "rows_loaded": len(data),
                        "columns_loaded": len(data.columns),
                        "memory_usage_mb": data.memory_usage(deep=True).sum() / 1024 / 1024
                    }
                )
            
            # Otherwise, load data from source
            source_path = config.get("source_path") if config else None
            if not source_path:
                return ExecutionResult(
                    status=StepStatus.FAILED,
                    errors=["No source path provided for data loading"]
                )
            
            # Load data based on file extension
            if source_path.endswith('.csv'):
                loaded_data = pd.read_csv(source_path)
            elif source_path.endswith('.json'):
                loaded_data = pd.read_json(source_path)
            elif source_path.endswith('.parquet'):
                loaded_data = pd.read_parquet(source_path)
            else:
                return ExecutionResult(
                    status=StepStatus.FAILED,
                    errors=[f"Unsupported file format: {source_path}"]
                )
            
            self.logger.info(f"Successfully loaded data: {loaded_data.shape}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=loaded_data,
                metrics={
                    "rows_loaded": len(loaded_data),
                    "columns_loaded": len(loaded_data.columns),
                    "memory_usage_mb": loaded_data.memory_usage(deep=True).sum() / 1024 / 1024,
                    "source_path": source_path
                }
            )
            
        except Exception as e:
            self.logger.error(f"Data ingestion failed: {str(e)}")
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[f"Data ingestion error: {str(e)}"]
            )
    
    def validate_inputs(self, 
                       data: Optional[pd.DataFrame] = None,
                       config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate inputs for data ingestion step.
        
        Args:
            data: Input data
            config: Step configuration
            
        Returns:
            True if inputs are valid
        """
        # If data is already provided, it's valid
        if data is not None:
            return True
        
        # Otherwise, check if source path is provided
        if config and "source_path" in config:
            return True
        
        self.logger.error("Data ingestion validation failed: no data or source path provided")
        return False