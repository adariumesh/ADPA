"""
Core ADPA Agent implementation.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
import pandas as pd

from .interfaces import (
    PipelineConfig, DatasetInfo, ExecutionResult, StepStatus,
    PipelineOrchestrator, AgentMemory, DataInspector, ErrorHandler
)
from ..planning.planner import PipelinePlanner
from ..execution.executor import StepExecutor
from ..memory.manager import MemoryManager


class ADPAAgent:
    """
    Autonomous Data Pipeline Agent - Main orchestrator for automated ML pipelines.
    """
    
    def __init__(self, 
                 config_path: Optional[str] = None,
                 aws_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the ADPA Agent.
        
        Args:
            config_path: Path to configuration file
            aws_config: AWS configuration dictionary
        """
        self.logger = self._setup_logging()
        self.agent_id = str(uuid.uuid4())
        
        # Initialize core components
        self.planner = PipelinePlanner()
        self.executor = StepExecutor(aws_config=aws_config)
        self.memory = MemoryManager()
        
        # Track active pipelines
        self.active_pipelines: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info(f"ADPA Agent initialized with ID: {self.agent_id}")
    
    def process_dataset(self, 
                       data: pd.DataFrame, 
                       objective: str,
                       target_column: Optional[str] = None,
                       config_overrides: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Process a dataset with the given objective.
        
        Args:
            data: Input dataset
            objective: ML objective (e.g., "predict churn")
            target_column: Target column name
            config_overrides: Override default configuration
            
        Returns:
            ExecutionResult with complete pipeline results
        """
        pipeline_id = str(uuid.uuid4())
        
        try:
            self.logger.info(f"Starting pipeline {pipeline_id} with objective: {objective}")
            
            # Step 1: Profile the dataset
            dataset_info = self._profile_dataset(data, target_column)
            self.logger.info(f"Dataset profiled: {dataset_info.shape[0]} rows, {dataset_info.shape[1]} columns")
            
            # Step 2: Create pipeline configuration
            config = self._create_pipeline_config(objective, target_column, config_overrides)
            
            # Step 3: Plan the pipeline
            pipeline_steps = self.planner.create_pipeline_plan(dataset_info, config)
            self.logger.info(f"Pipeline planned with {len(pipeline_steps)} steps")
            
            # Step 4: Execute the pipeline
            self.active_pipelines[pipeline_id] = {
                "status": "running",
                "steps": pipeline_steps,
                "config": config,
                "start_time": pd.Timestamp.now()
            }
            
            result = self.executor.execute_pipeline(pipeline_steps, data, config)
            
            # Step 5: Store results in memory
            self.memory.store_execution(pipeline_id, "complete_pipeline", result)
            
            # Update pipeline status
            self.active_pipelines[pipeline_id]["status"] = "completed"
            self.active_pipelines[pipeline_id]["end_time"] = pd.Timestamp.now()
            
            self.logger.info(f"Pipeline {pipeline_id} completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Pipeline {pipeline_id} failed: {str(e)}")
            self.active_pipelines[pipeline_id]["status"] = "failed"
            self.active_pipelines[pipeline_id]["error"] = str(e)
            
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[str(e)],
                step_output={"pipeline_id": pipeline_id}
            )
    
    def get_pipeline_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific pipeline."""
        return self.active_pipelines.get(pipeline_id)
    
    def list_active_pipelines(self) -> List[Dict[str, Any]]:
        """List all active pipelines."""
        return [
            {"id": pid, **info} 
            for pid, info in self.active_pipelines.items()
        ]
    
    def suggest_improvements(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """Suggest improvements for a completed pipeline."""
        if pipeline_id not in self.active_pipelines:
            return []
        
        pipeline_info = self.active_pipelines[pipeline_id]
        suggestions = []
        
        # Check execution time
        if "end_time" in pipeline_info and "start_time" in pipeline_info:
            duration = (pipeline_info["end_time"] - pipeline_info["start_time"]).total_seconds()
            if duration > 1800:  # 30 minutes
                suggestions.append({
                    "type": "performance",
                    "message": "Pipeline took longer than expected. Consider data sampling or feature selection.",
                    "priority": "medium"
                })
        
        # Check for failed steps
        if pipeline_info["status"] == "failed":
            suggestions.append({
                "type": "reliability",
                "message": "Pipeline failed. Review error logs and implement retry mechanisms.",
                "priority": "high"
            })
        
        return suggestions
    
    def _profile_dataset(self, data: pd.DataFrame, target_column: Optional[str]) -> DatasetInfo:
        """Create a profile of the input dataset."""
        numeric_columns = data.select_dtypes(include=['number']).columns.tolist()
        categorical_columns = data.select_dtypes(include=['object', 'category']).columns.tolist()
        
        missing_values = data.isnull().sum().to_dict()
        
        return DatasetInfo(
            shape=data.shape,
            columns=data.columns.tolist(),
            dtypes=data.dtypes.astype(str).to_dict(),
            missing_values=missing_values,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
            target_column=target_column
        )
    
    def _create_pipeline_config(self, 
                              objective: str, 
                              target_column: Optional[str],
                              overrides: Optional[Dict[str, Any]]) -> PipelineConfig:
        """Create pipeline configuration."""
        config = PipelineConfig(
            objective=objective,
            target_column=target_column,
            problem_type=self._infer_problem_type(objective),
            test_size=0.2,
            validation_strategy="train_test_split",
            max_execution_time=3600
        )
        
        # Apply overrides
        if overrides:
            for key, value in overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        return config
    
    def _infer_problem_type(self, objective: str) -> str:
        """Infer problem type from objective description."""
        objective_lower = objective.lower()
        
        if any(word in objective_lower for word in ['predict', 'regression', 'forecast']):
            if any(word in objective_lower for word in ['class', 'category', 'churn', 'sentiment']):
                return "classification"
            else:
                return "regression"
        elif any(word in objective_lower for word in ['classify', 'classification']):
            return "classification"
        else:
            # Default to classification for ambiguous cases
            return "classification"
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the agent."""
        logger = logging.getLogger(f"adpa.agent.{self.agent_id}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger