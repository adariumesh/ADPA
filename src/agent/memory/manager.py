"""
Memory management module for ADPA.
"""

import logging
import json
import pickle
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

from ..core.interfaces import (
    AgentMemory, ExecutionResult, DatasetInfo, PipelineStepType
)


class MemoryManager(AgentMemory):
    """
    Manages agent memory including execution history, best practices,
    and learned patterns from previous runs.
    """
    
    def __init__(self, memory_size: int = 1000):
        self.logger = logging.getLogger(__name__)
        self.memory_size = memory_size
        
        # In-memory storage (in production, this would be persistent)
        self.execution_memory: List[Dict[str, Any]] = []
        self.dataset_profiles: Dict[str, DatasetInfo] = {}
        self.best_practices: Dict[str, Dict[str, Any]] = {}
        self.pattern_library: Dict[str, List[Dict[str, Any]]] = {}
        
        # Initialize default best practices
        self._initialize_best_practices()
    
    def store_execution(self, pipeline_id: str, step_name: str, result: ExecutionResult):
        """Store execution result in memory."""
        execution_record = {
            "pipeline_id": pipeline_id,
            "step_name": step_name,
            "status": result.status.value,
            "execution_time": result.execution_time,
            "timestamp": datetime.now(),
            "metrics": result.metrics,
            "errors": result.errors,
            "artifacts_summary": self._summarize_artifacts(result.artifacts)
        }
        
        self.execution_memory.append(execution_record)
        
        # Maintain memory size limit
        if len(self.execution_memory) > self.memory_size:
            self.execution_memory = self.execution_memory[-self.memory_size:]
        
        self.logger.info(f"Stored execution record for {pipeline_id}:{step_name}")
        
        # Learn from successful executions
        if result.status.value == "completed":
            self._learn_from_execution(execution_record)
    
    def get_similar_executions(self, dataset_info: DatasetInfo, objective: str) -> List[Dict[str, Any]]:
        """Retrieve similar past executions."""
        similar_executions = []
        
        for execution in self.execution_memory:
            if execution["status"] == "completed":
                similarity_score = self._calculate_similarity(dataset_info, objective, execution)
                if similarity_score > 0.7:  # Threshold for similarity
                    execution_copy = execution.copy()
                    execution_copy["similarity_score"] = similarity_score
                    similar_executions.append(execution_copy)
        
        # Sort by similarity score
        similar_executions.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        self.logger.info(f"Found {len(similar_executions)} similar executions")
        return similar_executions[:10]  # Return top 10
    
    def store_dataset_profile(self, dataset_id: str, profile: DatasetInfo):
        """Store dataset profiling information."""
        self.dataset_profiles[dataset_id] = profile
        self.logger.info(f"Stored dataset profile for {dataset_id}")
    
    def get_best_practices(self, step_type: PipelineStepType, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get best practices for a specific step type and context."""
        step_type_str = step_type.value
        
        if step_type_str not in self.best_practices:
            return {}
        
        practices = self.best_practices[step_type_str].copy()
        
        # Contextualize based on dataset characteristics
        if "dataset_size" in context:
            dataset_size = context["dataset_size"]
            if dataset_size < 1000:
                practices["recommendations"].append("Consider using simpler models for small datasets")
            elif dataset_size > 100000:
                practices["recommendations"].append("Consider sampling or distributed processing for large datasets")
        
        if "missing_data_ratio" in context:
            missing_ratio = context["missing_data_ratio"]
            if missing_ratio > 0.3:
                practices["recommendations"].append("High missing data detected - consider advanced imputation techniques")
        
        return practices
    
    def learn_from_feedback(self, pipeline_id: str, feedback: Dict[str, Any]):
        """Learn from user feedback about pipeline performance."""
        # Find the execution record
        for execution in self.execution_memory:
            if execution["pipeline_id"] == pipeline_id:
                execution["user_feedback"] = feedback
                
                # Update best practices based on feedback
                if feedback.get("rating", 0) >= 4:  # Good rating
                    self._promote_successful_pattern(execution)
                elif feedback.get("rating", 0) <= 2:  # Poor rating
                    self._record_failed_pattern(execution)
                
                break
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about memory usage and performance."""
        total_executions = len(self.execution_memory)
        successful_executions = len([e for e in self.execution_memory if e["status"] == "completed"])
        recent_executions = len([
            e for e in self.execution_memory 
            if e["timestamp"] > datetime.now() - timedelta(days=7)
        ])
        
        avg_execution_time = 0
        if self.execution_memory:
            valid_times = [e["execution_time"] for e in self.execution_memory if e["execution_time"]]
            if valid_times:
                avg_execution_time = sum(valid_times) / len(valid_times)
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "recent_executions_7days": recent_executions,
            "average_execution_time": avg_execution_time,
            "dataset_profiles_stored": len(self.dataset_profiles),
            "best_practices_categories": len(self.best_practices),
            "memory_utilization": len(self.execution_memory) / self.memory_size
        }
    
    def _initialize_best_practices(self):
        """Initialize default best practices."""
        self.best_practices = {
            "cleaning": {
                "description": "Data cleaning best practices",
                "recommendations": [
                    "Always profile data before cleaning",
                    "Handle missing values based on data type and distribution",
                    "Remove or correct obvious outliers",
                    "Validate data types and formats"
                ],
                "common_issues": [
                    "Missing values in critical columns",
                    "Outliers skewing distributions",
                    "Inconsistent data formats"
                ]
            },
            "feature_engineering": {
                "description": "Feature engineering best practices",
                "recommendations": [
                    "Encode categorical variables appropriately",
                    "Scale numerical features when necessary",
                    "Create meaningful derived features",
                    "Remove highly correlated features"
                ],
                "common_issues": [
                    "High cardinality categorical variables",
                    "Skewed feature distributions",
                    "Feature leakage"
                ]
            },
            "training": {
                "description": "Model training best practices",
                "recommendations": [
                    "Use appropriate validation strategies",
                    "Try multiple algorithms",
                    "Tune hyperparameters systematically",
                    "Monitor for overfitting"
                ],
                "common_issues": [
                    "Overfitting on small datasets",
                    "Class imbalance",
                    "Insufficient validation"
                ]
            }
        }
    
    def _summarize_artifacts(self, artifacts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a summary of artifacts for storage."""
        if not artifacts:
            return {}
        
        summary = {}
        for key, value in artifacts.items():
            if isinstance(value, (int, float, str, bool)):
                summary[key] = value
            elif isinstance(value, dict):
                summary[key] = f"Dict with {len(value)} keys"
            elif isinstance(value, list):
                summary[key] = f"List with {len(value)} items"
            else:
                summary[key] = str(type(value).__name__)
        
        return summary
    
    def _calculate_similarity(self, dataset_info: DatasetInfo, objective: str, execution: Dict[str, Any]) -> float:
        """Calculate similarity between current context and past execution."""
        # This is a simplified similarity calculation
        # In practice, this would be more sophisticated
        
        similarity_score = 0.0
        
        # Check if objectives are similar (simple keyword matching)
        if any(word in objective.lower() for word in ["predict", "classify", "regression"]):
            similarity_score += 0.3
        
        # Add more sophisticated similarity measures here
        # - Dataset size similarity
        # - Feature type similarity  
        # - Problem type similarity
        
        return min(similarity_score, 1.0)
    
    def _learn_from_execution(self, execution_record: Dict[str, Any]):
        """Learn patterns from successful executions."""
        if execution_record["metrics"]:
            pattern_key = f"{execution_record['step_name']}_success"
            
            if pattern_key not in self.pattern_library:
                self.pattern_library[pattern_key] = []
            
            pattern = {
                "metrics": execution_record["metrics"],
                "execution_time": execution_record["execution_time"],
                "timestamp": execution_record["timestamp"]
            }
            
            self.pattern_library[pattern_key].append(pattern)
    
    def _promote_successful_pattern(self, execution: Dict[str, Any]):
        """Promote a pattern as a best practice based on positive feedback."""
        # Implementation would add the pattern to best practices
        pass
    
    def _record_failed_pattern(self, execution: Dict[str, Any]):
        """Record a pattern to avoid based on negative feedback."""
        # Implementation would add anti-patterns to avoid
        pass