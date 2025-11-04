"""
Pipeline execution module for ADPA.
"""

import logging
import time
from typing import List, Dict, Any, Optional
import pandas as pd

from ..core.interfaces import (
    PipelineStep, ExecutionResult, StepStatus, PipelineConfig,
    ErrorHandler
)


class StepExecutor:
    """
    Executes pipeline steps with error handling, retry logic, and monitoring.
    """
    
    def __init__(self, aws_config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(__name__)
        self.aws_config = aws_config or {}
        self.execution_history: List[Dict[str, Any]] = []
        
    def execute_pipeline(self, 
                        steps: List[PipelineStep], 
                        data: pd.DataFrame,
                        config: PipelineConfig) -> ExecutionResult:
        """
        Execute a complete pipeline with error handling and monitoring.
        
        Args:
            steps: List of pipeline steps to execute
            data: Input dataset
            config: Pipeline configuration
            
        Returns:
            ExecutionResult with final results
        """
        self.logger.info(f"Starting pipeline execution with {len(steps)} steps")
        
        current_data = data.copy()
        pipeline_artifacts = {}
        pipeline_metrics = {}
        execution_errors = []
        
        start_time = time.time()
        
        try:
            for i, step in enumerate(steps):
                self.logger.info(f"Executing step {i+1}/{len(steps)}: {step.name}")
                
                step_start = time.time()
                step.status = StepStatus.RUNNING
                
                # Execute step with retry logic
                step_result = self._execute_step_with_retry(
                    step, current_data, config, max_retries=3
                )
                
                step_duration = time.time() - step_start
                
                # Record execution
                self.execution_history.append({
                    "step_name": step.name,
                    "step_type": step.step_type.value,
                    "status": step_result.status.value,
                    "duration": step_duration,
                    "timestamp": pd.Timestamp.now()
                })
                
                if step_result.status == StepStatus.FAILED:
                    self.logger.error(f"Step {step.name} failed: {step_result.errors}")
                    execution_errors.extend(step_result.errors or [])
                    
                    # Try to continue with original data or fail completely
                    if self._is_critical_step(step):
                        return ExecutionResult(
                            status=StepStatus.FAILED,
                            errors=execution_errors,
                            execution_time=time.time() - start_time
                        )
                    else:
                        self.logger.warning(f"Non-critical step {step.name} failed, continuing...")
                        continue
                
                # Update data and collect artifacts
                if step_result.data is not None:
                    current_data = step_result.data
                
                if step_result.artifacts:
                    pipeline_artifacts.update(step_result.artifacts)
                
                if step_result.metrics:
                    pipeline_metrics.update(step_result.metrics)
                
                step.status = StepStatus.COMPLETED
                self.logger.info(f"Step {step.name} completed in {step_duration:.2f}s")
        
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[str(e)],
                execution_time=time.time() - start_time
            )
        
        total_time = time.time() - start_time
        
        self.logger.info(f"Pipeline execution completed in {total_time:.2f}s")
        
        return ExecutionResult(
            status=StepStatus.COMPLETED,
            data=current_data,
            artifacts=pipeline_artifacts,
            metrics=pipeline_metrics,
            execution_time=total_time,
            step_output={
                "execution_history": self.execution_history,
                "total_steps": len(steps),
                "successful_steps": len([h for h in self.execution_history if h["status"] == "completed"])
            }
        )
    
    def _execute_step_with_retry(self, 
                               step: PipelineStep, 
                               data: pd.DataFrame,
                               config: PipelineConfig,
                               max_retries: int = 3) -> ExecutionResult:
        """Execute a step with retry logic."""
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"Retrying step {step.name}, attempt {attempt + 1}")
                    step.status = StepStatus.RETRYING
                
                # Validate inputs
                if not step.validate_inputs(data, config.__dict__):
                    return ExecutionResult(
                        status=StepStatus.FAILED,
                        errors=[f"Input validation failed for step {step.name}"]
                    )
                
                # Execute the step
                result = step.execute(data, config.__dict__)
                
                if result.status == StepStatus.COMPLETED:
                    return result
                elif result.status == StepStatus.FAILED and attempt < max_retries:
                    last_error = result.errors[0] if result.errors else "Unknown error"
                    self.logger.warning(f"Step {step.name} failed on attempt {attempt + 1}: {last_error}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return result
                    
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Step {step.name} threw exception on attempt {attempt + 1}: {last_error}")
                
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    return ExecutionResult(
                        status=StepStatus.FAILED,
                        errors=[f"Step failed after {max_retries + 1} attempts: {last_error}"]
                    )
        
        return ExecutionResult(
            status=StepStatus.FAILED,
            errors=[f"Step failed after {max_retries + 1} attempts: {last_error}"]
        )
    
    def _is_critical_step(self, step: PipelineStep) -> bool:
        """Determine if a step is critical for pipeline success."""
        critical_steps = ["training", "data_loading", "target_preparation"]
        return step.step_type.value in critical_steps or "critical" in step.name.lower()
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get the execution history for the current pipeline."""
        return self.execution_history.copy()
    
    def clear_execution_history(self):
        """Clear the execution history."""
        self.execution_history.clear()
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution history."""
        if not self.execution_history:
            return {"message": "No executions recorded"}
        
        total_steps = len(self.execution_history)
        successful_steps = len([h for h in self.execution_history if h["status"] == "completed"])
        failed_steps = len([h for h in self.execution_history if h["status"] == "failed"])
        total_time = sum(h["duration"] for h in self.execution_history)
        
        return {
            "total_steps": total_steps,
            "successful_steps": successful_steps,
            "failed_steps": failed_steps,
            "success_rate": successful_steps / total_steps if total_steps > 0 else 0,
            "total_execution_time": total_time,
            "average_step_time": total_time / total_steps if total_steps > 0 else 0,
            "steps": self.execution_history
        }