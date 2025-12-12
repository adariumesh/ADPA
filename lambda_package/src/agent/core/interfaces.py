"""
Core interfaces for the ADPA agent system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import pandas as pd


class StepStatus(Enum):
    """Status of a pipeline step execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class PipelineStepType(Enum):
    """Types of pipeline steps."""
    INGESTION = "ingestion"
    CLEANING = "cleaning"
    FEATURE_ENGINEERING = "feature_engineering"
    TRAINING = "training"
    EVALUATION = "evaluation"
    REPORTING = "reporting"
    MONITORING = "monitoring"


@dataclass
class ExecutionResult:
    """Result of a pipeline step execution."""
    status: StepStatus
    data: Optional[pd.DataFrame] = None
    artifacts: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, float]] = None
    errors: Optional[List[str]] = None
    execution_time: Optional[float] = None
    step_output: Optional[Dict[str, Any]] = None


@dataclass
class DatasetInfo:
    """Information about a dataset."""
    shape: tuple
    columns: List[str]
    dtypes: Dict[str, str]
    missing_values: Dict[str, int]
    numeric_columns: List[str]
    categorical_columns: List[str]
    target_column: Optional[str] = None


@dataclass
class PipelineConfig:
    """Configuration for a pipeline execution."""
    objective: str  # e.g., "predict churn", "classify sentiment"
    target_column: Optional[str] = None
    problem_type: Optional[str] = None  # "classification", "regression"
    test_size: float = 0.2
    validation_strategy: str = "train_test_split"
    max_execution_time: int = 3600  # seconds
    quality_thresholds: Optional[Dict[str, float]] = None


class PipelineStep(ABC):
    """Abstract base class for all pipeline steps."""
    
    def __init__(self, step_type: PipelineStepType, name: str):
        self.step_type = step_type
        self.name = name
        self.status = StepStatus.PENDING
        
    @abstractmethod
    def execute(self, 
                data: Optional[pd.DataFrame] = None,
                config: Optional[Dict[str, Any]] = None,
                context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute the pipeline step."""
        pass
    
    @abstractmethod
    def validate_inputs(self, 
                       data: Optional[pd.DataFrame] = None,
                       config: Optional[Dict[str, Any]] = None) -> bool:
        """Validate inputs before execution."""
        pass
    
    def get_step_info(self) -> Dict[str, Any]:
        """Get information about this step."""
        return {
            "name": self.name,
            "type": self.step_type.value,
            "status": self.status.value
        }


class AgentMemory(ABC):
    """Abstract interface for agent memory management."""
    
    @abstractmethod
    def store_execution(self, pipeline_id: str, step_name: str, result: ExecutionResult):
        """Store execution result in memory."""
        pass
    
    @abstractmethod
    def get_similar_executions(self, dataset_info: DatasetInfo, objective: str) -> List[Dict[str, Any]]:
        """Retrieve similar past executions."""
        pass
    
    @abstractmethod
    def store_dataset_profile(self, dataset_id: str, profile: DatasetInfo):
        """Store dataset profiling information."""
        pass
    
    @abstractmethod
    def get_best_practices(self, step_type: PipelineStepType, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get best practices for a specific step type and context."""
        pass


class DataInspector(ABC):
    """Abstract interface for dataset inspection and profiling."""
    
    @abstractmethod
    def profile_dataset(self, data: pd.DataFrame, target_column: Optional[str] = None) -> DatasetInfo:
        """Create a comprehensive profile of the dataset."""
        pass
    
    @abstractmethod
    def detect_data_issues(self, data: pd.DataFrame) -> Dict[str, List[str]]:
        """Detect potential data quality issues."""
        pass
    
    @abstractmethod
    def suggest_transformations(self, profile: DatasetInfo, objective: str) -> List[Dict[str, Any]]:
        """Suggest appropriate transformations based on data profile."""
        pass


class ErrorHandler(ABC):
    """Abstract interface for error handling and recovery."""
    
    @abstractmethod
    def handle_step_failure(self, 
                          step: PipelineStep, 
                          error: Exception, 
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a step failure and suggest recovery actions."""
        pass
    
    @abstractmethod
    def suggest_fallback_strategy(self, 
                                step_type: PipelineStepType, 
                                error_type: str,
                                context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Suggest a fallback strategy for a failed step."""
        pass


class PipelineOrchestrator(ABC):
    """Abstract interface for pipeline orchestration."""
    
    @abstractmethod
    def create_pipeline_plan(self, 
                           dataset_info: DatasetInfo, 
                           config: PipelineConfig) -> List[PipelineStep]:
        """Create a complete pipeline plan."""
        pass
    
    @abstractmethod
    def execute_pipeline(self, 
                        steps: List[PipelineStep], 
                        data: pd.DataFrame,
                        config: PipelineConfig) -> ExecutionResult:
        """Execute a complete pipeline."""
        pass
    
    @abstractmethod
    def monitor_execution(self, pipeline_id: str) -> Dict[str, Any]:
        """Monitor pipeline execution status."""
        pass