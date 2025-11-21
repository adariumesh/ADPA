"""
Experience Memory System for ADPA Agentic Learning
Replaces the rule-based memory manager with intelligent learning capabilities.
"""

import json
import logging
import os
import pickle
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

from ..utils.llm_integration import LLMReasoningEngine, ReasoningContext
from ..core.interfaces import ExecutionResult, DatasetInfo


@dataclass
class PipelineExecution:
    """Record of a complete pipeline execution for learning."""
    execution_id: str
    timestamp: datetime
    dataset_fingerprint: Dict[str, Any]  # Unique characteristics of the dataset
    objective: str
    pipeline_steps: List[Dict[str, Any]]
    execution_results: Dict[str, Any]
    performance_metrics: Dict[str, float]
    resource_usage: Dict[str, Any]
    success: bool
    failure_reasons: Optional[List[str]] = None
    user_feedback: Optional[Dict[str, Any]] = None
    learned_insights: Optional[Dict[str, Any]] = None


@dataclass
class DatasetPattern:
    """Learned patterns about dataset characteristics and optimal approaches."""
    pattern_id: str
    dataset_characteristics: Dict[str, Any]
    successful_approaches: List[Dict[str, Any]]
    failed_approaches: List[Dict[str, Any]]
    performance_insights: Dict[str, Any]
    confidence_score: float
    last_updated: datetime


@dataclass
class LearningInsight:
    """Specific insight learned from experience."""
    insight_id: str
    domain: str  # "preprocessing", "model_selection", "feature_engineering", etc.
    condition: Dict[str, Any]  # When this insight applies
    recommendation: Dict[str, Any]  # What to do
    evidence: List[str]  # Execution IDs that support this insight
    confidence: float
    impact_score: float  # How much this insight improves outcomes


class ExperienceMemorySystem:
    """
    Intelligent memory system that learns from pipeline executions to improve future decisions.
    Combines traditional storage with LLM-powered insight extraction.
    """
    
    def __init__(self, 
                 memory_dir: str = "./data/experience_memory",
                 max_executions: int = 10000,
                 similarity_threshold: float = 0.8):
        """
        Initialize the experience memory system.
        
        Args:
            memory_dir: Directory to store memory data
            max_executions: Maximum number of executions to keep
            similarity_threshold: Threshold for considering datasets similar
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_executions = max_executions
        self.similarity_threshold = similarity_threshold
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.reasoning_engine = LLMReasoningEngine()
        self.vectorizer = TfidfVectorizer()
        
        # Storage
        self.db_path = self.memory_dir / "executions.db"
        self.insights_path = self.memory_dir / "insights.json"
        self.patterns_path = self.memory_dir / "patterns.json"
        
        # Initialize storage
        self._init_database()
        self._load_insights()
        self._load_patterns()
        
        self.logger.info("Experience Memory System initialized")
    
    def record_execution(self, 
                        pipeline_id: str,
                        dataset_info: DatasetInfo,
                        objective: str,
                        pipeline_steps: List[Dict[str, Any]],
                        execution_result: ExecutionResult,
                        resource_usage: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a complete pipeline execution for learning.
        
        Args:
            pipeline_id: Unique pipeline execution ID
            dataset_info: Information about the dataset used
            objective: ML objective for this execution
            pipeline_steps: Steps that were executed
            execution_result: Final execution result
            resource_usage: Resource consumption data
        """
        try:
            # Create dataset fingerprint for similarity matching
            dataset_fingerprint = self._create_dataset_fingerprint(dataset_info)
            
            # Extract performance metrics
            performance_metrics = execution_result.metrics or {}
            
            # Determine success
            success = execution_result.status.value == "completed"
            failure_reasons = execution_result.errors if not success else None
            
            # Create execution record
            execution = PipelineExecution(
                execution_id=pipeline_id,
                timestamp=datetime.now(),
                dataset_fingerprint=dataset_fingerprint,
                objective=objective,
                pipeline_steps=pipeline_steps,
                execution_results=asdict(execution_result),
                performance_metrics=performance_metrics,
                resource_usage=resource_usage or {},
                success=success,
                failure_reasons=failure_reasons
            )
            
            # Store in database
            self._store_execution(execution)
            
            # Trigger learning from this execution
            self._learn_from_execution(execution)
            
            self.logger.info(f"Recorded execution {pipeline_id} with success={success}")
            
        except Exception as e:
            self.logger.error(f"Failed to record execution {pipeline_id}: {e}")
    
    def get_recommendations_for_dataset(self, 
                                      dataset_info: DatasetInfo,
                                      objective: str) -> Dict[str, Any]:
        """
        Get intelligent recommendations based on past experience with similar datasets.
        
        Args:
            dataset_info: Current dataset characteristics
            objective: Current ML objective
            
        Returns:
            Dictionary with recommendations and reasoning
        """
        try:
            # Find similar past executions
            similar_executions = self._find_similar_executions(dataset_info, objective)
            
            if not similar_executions:
                return self._get_default_recommendations(dataset_info, objective)
            
            # Use LLM to analyze patterns and generate recommendations
            recommendations = self._generate_intelligent_recommendations(
                dataset_info, objective, similar_executions
            )
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to get recommendations: {e}")
            return self._get_default_recommendations(dataset_info, objective)
    
    def learn_from_feedback(self, 
                           execution_id: str,
                           feedback: Dict[str, Any]) -> None:
        """
        Learn from user feedback about pipeline performance.
        
        Args:
            execution_id: ID of the execution to provide feedback on
            feedback: User feedback dictionary
        """
        try:
            # Update execution record with feedback
            self._update_execution_feedback(execution_id, feedback)
            
            # Use feedback to refine insights
            self._refine_insights_from_feedback(execution_id, feedback)
            
            self.logger.info(f"Recorded feedback for execution {execution_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to record feedback: {e}")
    
    def get_performance_insights(self, 
                               time_window_days: int = 30) -> Dict[str, Any]:
        """
        Get insights about recent pipeline performance patterns.
        
        Args:
            time_window_days: Time window for analysis
            
        Returns:
            Dictionary with performance insights
        """
        try:
            # Get recent executions
            recent_executions = self._get_recent_executions(time_window_days)
            
            if not recent_executions:
                return {"message": "No recent executions to analyze"}
            
            # Analyze patterns using LLM
            insights = self._analyze_performance_patterns(recent_executions)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to get performance insights: {e}")
            return {"error": str(e)}
    
    def optimize_pipeline_for_dataset(self, 
                                    dataset_info: DatasetInfo,
                                    objective: str,
                                    current_pipeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Suggest optimizations for a pipeline based on learned experience.
        
        Args:
            dataset_info: Dataset characteristics
            objective: ML objective
            current_pipeline: Current pipeline configuration
            
        Returns:
            Dictionary with optimization suggestions
        """
        try:
            # Find similar successful executions
            similar_successes = self._find_similar_successful_executions(dataset_info, objective)
            
            # Use LLM to suggest optimizations
            optimizations = self._generate_optimization_suggestions(
                dataset_info, objective, current_pipeline, similar_successes
            )
            
            return optimizations
            
        except Exception as e:
            self.logger.error(f"Failed to generate optimizations: {e}")
            return {"error": str(e)}
    
    def predict_pipeline_success(self, 
                                dataset_info: DatasetInfo,
                                objective: str,
                                planned_pipeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Predict the likelihood of success for a planned pipeline.
        
        Args:
            dataset_info: Dataset characteristics
            objective: ML objective
            planned_pipeline: Planned pipeline steps
            
        Returns:
            Dictionary with success prediction and reasoning
        """
        try:
            # Find similar past attempts
            similar_attempts = self._find_similar_executions(dataset_info, objective)
            
            # Analyze success patterns
            prediction = self._predict_success_probability(
                dataset_info, objective, planned_pipeline, similar_attempts
            )
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Failed to predict pipeline success: {e}")
            return {"success_probability": 0.5, "confidence": 0.0, "error": str(e)}
    
    def _create_dataset_fingerprint(self, dataset_info: DatasetInfo) -> Dict[str, Any]:
        """Create a unique fingerprint for dataset similarity matching."""
        fingerprint = {
            "rows": dataset_info.shape[0],
            "columns": dataset_info.shape[1],
            "numeric_ratio": len(dataset_info.numeric_columns) / len(dataset_info.columns),
            "categorical_ratio": len(dataset_info.categorical_columns) / len(dataset_info.columns),
            "missing_ratio": sum(dataset_info.missing_values.values()) / (dataset_info.shape[0] * dataset_info.shape[1]),
            "target_type": "categorical" if dataset_info.target_column in dataset_info.categorical_columns else "numeric",
            "feature_count_bucket": self._get_feature_bucket(len(dataset_info.columns)),
            "size_bucket": self._get_size_bucket(dataset_info.shape[0])
        }
        
        return fingerprint
    
    def _get_feature_bucket(self, feature_count: int) -> str:
        """Bucket feature count into categories."""
        if feature_count < 10:
            return "low"
        elif feature_count < 50:
            return "medium"
        elif feature_count < 200:
            return "high"
        else:
            return "very_high"
    
    def _get_size_bucket(self, row_count: int) -> str:
        """Bucket dataset size into categories."""
        if row_count < 1000:
            return "small"
        elif row_count < 10000:
            return "medium"
        elif row_count < 100000:
            return "large"
        else:
            return "very_large"
    
    def _init_database(self):
        """Initialize SQLite database for execution storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS executions (
                execution_id TEXT PRIMARY KEY,
                timestamp TEXT,
                dataset_fingerprint TEXT,
                objective TEXT,
                pipeline_steps TEXT,
                execution_results TEXT,
                performance_metrics TEXT,
                resource_usage TEXT,
                success INTEGER,
                failure_reasons TEXT,
                user_feedback TEXT,
                learned_insights TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON executions(timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_success ON executions(success)
        ''')
        
        conn.commit()
        conn.close()
    
    def _store_execution(self, execution: PipelineExecution):
        """Store execution record in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO executions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            execution.execution_id,
            execution.timestamp.isoformat(),
            json.dumps(execution.dataset_fingerprint),
            execution.objective,
            json.dumps(execution.pipeline_steps),
            json.dumps(execution.execution_results),
            json.dumps(execution.performance_metrics),
            json.dumps(execution.resource_usage),
            1 if execution.success else 0,
            json.dumps(execution.failure_reasons) if execution.failure_reasons else None,
            json.dumps(execution.user_feedback) if execution.user_feedback else None,
            json.dumps(execution.learned_insights) if execution.learned_insights else None
        ))
        
        conn.commit()
        conn.close()
    
    def _find_similar_executions(self, 
                                dataset_info: DatasetInfo,
                                objective: str,
                                limit: int = 10) -> List[PipelineExecution]:
        """Find similar past executions based on dataset characteristics and objective."""
        target_fingerprint = self._create_dataset_fingerprint(dataset_info)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM executions 
            WHERE objective LIKE ? 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''', (f"%{objective.lower()}%",))
        
        rows = cursor.fetchall()
        conn.close()
        
        similar_executions = []
        
        for row in rows:
            stored_fingerprint = json.loads(row[2])
            similarity = self._calculate_fingerprint_similarity(target_fingerprint, stored_fingerprint)
            
            if similarity >= self.similarity_threshold:
                execution = PipelineExecution(
                    execution_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    dataset_fingerprint=stored_fingerprint,
                    objective=row[3],
                    pipeline_steps=json.loads(row[4]),
                    execution_results=json.loads(row[5]),
                    performance_metrics=json.loads(row[6]),
                    resource_usage=json.loads(row[7]),
                    success=bool(row[8]),
                    failure_reasons=json.loads(row[9]) if row[9] else None,
                    user_feedback=json.loads(row[10]) if row[10] else None,
                    learned_insights=json.loads(row[11]) if row[11] else None
                )
                similar_executions.append(execution)
        
        return similar_executions[:limit]
    
    def _calculate_fingerprint_similarity(self, fp1: Dict[str, Any], fp2: Dict[str, Any]) -> float:
        """Calculate similarity between two dataset fingerprints."""
        # Numerical similarity for continuous features
        numerical_features = ['rows', 'columns', 'numeric_ratio', 'categorical_ratio', 'missing_ratio']
        numerical_sim = 0.0
        
        for feature in numerical_features:
            if feature in fp1 and feature in fp2:
                val1, val2 = fp1[feature], fp2[feature]
                if val1 == 0 and val2 == 0:
                    sim = 1.0
                else:
                    sim = 1.0 - abs(val1 - val2) / max(abs(val1), abs(val2), 1.0)
                numerical_sim += sim
        
        numerical_sim /= len(numerical_features)
        
        # Categorical similarity
        categorical_features = ['target_type', 'feature_count_bucket', 'size_bucket']
        categorical_sim = 0.0
        
        for feature in categorical_features:
            if feature in fp1 and feature in fp2:
                categorical_sim += 1.0 if fp1[feature] == fp2[feature] else 0.0
        
        categorical_sim /= len(categorical_features)
        
        # Weighted average
        return 0.7 * numerical_sim + 0.3 * categorical_sim
    
    def _learn_from_execution(self, execution: PipelineExecution):
        """Extract learning insights from a completed execution."""
        try:
            # Use LLM to extract insights
            learning_context = ReasoningContext(
                domain="learning_extraction",
                objective=execution.objective,
                data_context={
                    "dataset_fingerprint": execution.dataset_fingerprint,
                    "pipeline_steps": execution.pipeline_steps,
                    "performance_metrics": execution.performance_metrics,
                    "success": execution.success,
                    "failure_reasons": execution.failure_reasons
                }
            )
            
            # Generate insights using LLM
            insights_prompt = f"""
            Analyze this pipeline execution and extract key learnings:
            
            Dataset: {execution.dataset_fingerprint}
            Objective: {execution.objective}
            Pipeline: {execution.pipeline_steps}
            Success: {execution.success}
            Performance: {execution.performance_metrics}
            Failures: {execution.failure_reasons}
            
            What insights can we learn for future similar datasets and objectives?
            What worked well? What could be improved?
            What patterns emerge?
            """
            
            insights_response = self.reasoning_engine._call_llm(insights_prompt, max_tokens=800)
            
            # Store insights
            execution.learned_insights = {
                "insights": insights_response,
                "extracted_at": datetime.now().isoformat(),
                "key_learnings": self._extract_key_learnings(insights_response)
            }
            
            # Update database
            self._update_execution_insights(execution.execution_id, execution.learned_insights)
            
        except Exception as e:
            self.logger.error(f"Failed to learn from execution {execution.execution_id}: {e}")
    
    def _extract_key_learnings(self, insights_text: str) -> List[str]:
        """Extract key learnings from LLM insights text."""
        # Simple extraction - could be enhanced with NLP
        learnings = []
        
        if "successful" in insights_text.lower():
            learnings.append("successful_approach_identified")
        if "failed" in insights_text.lower():
            learnings.append("failure_pattern_identified")
        if "optimize" in insights_text.lower():
            learnings.append("optimization_opportunity")
        if "feature" in insights_text.lower():
            learnings.append("feature_engineering_insight")
        if "model" in insights_text.lower():
            learnings.append("model_selection_insight")
        
        return learnings
    
    def _generate_intelligent_recommendations(self, 
                                            dataset_info: DatasetInfo,
                                            objective: str,
                                            similar_executions: List[PipelineExecution]) -> Dict[str, Any]:
        """Generate intelligent recommendations based on similar executions."""
        
        # Prepare context for LLM
        successful_patterns = [ex for ex in similar_executions if ex.success]
        failed_patterns = [ex for ex in similar_executions if not ex.success]
        
        recommendation_prompt = f"""
        Based on past experience with similar datasets, provide recommendations:
        
        Current Dataset: {self._create_dataset_fingerprint(dataset_info)}
        Objective: {objective}
        
        Successful Past Approaches ({len(successful_patterns)} examples):
        {self._format_execution_summaries(successful_patterns[:3])}
        
        Failed Past Approaches ({len(failed_patterns)} examples):
        {self._format_execution_summaries(failed_patterns[:2])}
        
        Provide specific recommendations for:
        1. Pipeline steps and order
        2. Algorithm selection
        3. Feature engineering approach
        4. Potential pitfalls to avoid
        5. Expected performance range
        
        Be specific and actionable.
        """
        
        recommendations_response = self.reasoning_engine._call_llm(recommendation_prompt, max_tokens=1000)
        
        return {
            "recommendations": recommendations_response,
            "based_on_executions": len(similar_executions),
            "success_rate": len(successful_patterns) / len(similar_executions) if similar_executions else 0,
            "confidence": min(0.9, len(similar_executions) * 0.1),
            "generated_at": datetime.now().isoformat()
        }
    
    def _format_execution_summaries(self, executions: List[PipelineExecution]) -> str:
        """Format execution summaries for LLM prompts."""
        summaries = []
        
        for exec in executions:
            summary = f"""
            - Pipeline: {[step.get('step', 'unknown') for step in exec.pipeline_steps]}
            - Performance: {exec.performance_metrics}
            - Success: {exec.success}
            """
            summaries.append(summary)
        
        return "\n".join(summaries)
    
    def _get_default_recommendations(self, dataset_info: DatasetInfo, objective: str) -> Dict[str, Any]:
        """Get default recommendations when no similar executions found."""
        return {
            "recommendations": "No similar past executions found. Using general best practices.",
            "suggested_pipeline": [
                {"step": "data_validation", "reason": "Always validate data first"},
                {"step": "preprocessing", "reason": "Handle missing values and outliers"},
                {"step": "feature_engineering", "reason": "Improve feature quality"},
                {"step": "model_training", "reason": "Train appropriate model"},
                {"step": "evaluation", "reason": "Assess model performance"}
            ],
            "confidence": 0.3,
            "based_on_executions": 0,
            "note": "Consider running similar experiments to build experience base"
        }
    
    def _load_insights(self):
        """Load stored insights from file."""
        self.insights = {}
        if self.insights_path.exists():
            try:
                with open(self.insights_path, 'r') as f:
                    self.insights = json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load insights: {e}")
    
    def _load_patterns(self):
        """Load stored patterns from file."""
        self.patterns = {}
        if self.patterns_path.exists():
            try:
                with open(self.patterns_path, 'r') as f:
                    self.patterns = json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load patterns: {e}")
    
    def _save_insights(self):
        """Save insights to file."""
        try:
            with open(self.insights_path, 'w') as f:
                json.dump(self.insights, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save insights: {e}")
    
    def _save_patterns(self):
        """Save patterns to file."""
        try:
            with open(self.patterns_path, 'w') as f:
                json.dump(self.patterns, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save patterns: {e}")
    
    def _update_execution_feedback(self, execution_id: str, feedback: Dict[str, Any]):
        """Update execution record with user feedback."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE executions 
            SET user_feedback = ? 
            WHERE execution_id = ?
        ''', (json.dumps(feedback), execution_id))
        
        conn.commit()
        conn.close()
    
    def _update_execution_insights(self, execution_id: str, insights: Dict[str, Any]):
        """Update execution record with learned insights."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE executions 
            SET learned_insights = ? 
            WHERE execution_id = ?
        ''', (json.dumps(insights), execution_id))
        
        conn.commit()
        conn.close()
    
    def _get_recent_executions(self, days: int) -> List[PipelineExecution]:
        """Get executions from the last N days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM executions 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC
        ''', (cutoff_date.isoformat(),))
        
        rows = cursor.fetchall()
        conn.close()
        
        executions = []
        for row in rows:
            execution = PipelineExecution(
                execution_id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                dataset_fingerprint=json.loads(row[2]),
                objective=row[3],
                pipeline_steps=json.loads(row[4]),
                execution_results=json.loads(row[5]),
                performance_metrics=json.loads(row[6]),
                resource_usage=json.loads(row[7]),
                success=bool(row[8]),
                failure_reasons=json.loads(row[9]) if row[9] else None,
                user_feedback=json.loads(row[10]) if row[10] else None,
                learned_insights=json.loads(row[11]) if row[11] else None
            )
            executions.append(execution)
        
        return executions
    
    def _find_similar_successful_executions(self, 
                                          dataset_info: DatasetInfo,
                                          objective: str) -> List[PipelineExecution]:
        """Find similar successful executions."""
        similar_executions = self._find_similar_executions(dataset_info, objective)
        return [ex for ex in similar_executions if ex.success]
    
    def _analyze_performance_patterns(self, executions: List[PipelineExecution]) -> Dict[str, Any]:
        """Analyze performance patterns in recent executions."""
        analysis_prompt = f"""
        Analyze these recent pipeline executions and identify patterns:
        
        Total Executions: {len(executions)}
        Success Rate: {sum(1 for ex in executions if ex.success) / len(executions):.2%}
        
        Performance Metrics Summary:
        {self._summarize_performance_metrics(executions)}
        
        Common Objectives: {self._get_common_objectives(executions)}
        
        Identify:
        1. Performance trends
        2. Success factors
        3. Common failure modes
        4. Optimization opportunities
        5. Resource utilization patterns
        """
        
        analysis_response = self.reasoning_engine._call_llm(analysis_prompt, max_tokens=1000)
        
        return {
            "analysis": analysis_response,
            "execution_count": len(executions),
            "success_rate": sum(1 for ex in executions if ex.success) / len(executions) if executions else 0,
            "analyzed_at": datetime.now().isoformat()
        }
    
    def _summarize_performance_metrics(self, executions: List[PipelineExecution]) -> str:
        """Summarize performance metrics across executions."""
        all_metrics = []
        for ex in executions:
            all_metrics.extend(list(ex.performance_metrics.keys()))
        
        unique_metrics = list(set(all_metrics))
        return f"Common metrics: {unique_metrics[:5]}"
    
    def _get_common_objectives(self, executions: List[PipelineExecution]) -> List[str]:
        """Get most common objectives from executions."""
        objectives = [ex.objective for ex in executions]
        return list(set(objectives))[:3]
    
    def _generate_optimization_suggestions(self, 
                                         dataset_info: DatasetInfo,
                                         objective: str,
                                         current_pipeline: List[Dict[str, Any]],
                                         similar_successes: List[PipelineExecution]) -> Dict[str, Any]:
        """Generate optimization suggestions based on successful similar executions."""
        
        optimization_prompt = f"""
        Suggest optimizations for this pipeline based on successful similar executions:
        
        Current Pipeline: {current_pipeline}
        Dataset: {self._create_dataset_fingerprint(dataset_info)}
        Objective: {objective}
        
        Successful Similar Approaches:
        {self._format_execution_summaries(similar_successes[:3])}
        
        Suggest specific optimizations:
        1. Step modifications
        2. Parameter tuning
        3. Algorithm alternatives
        4. Performance improvements
        5. Resource optimization
        """
        
        optimization_response = self.reasoning_engine._call_llm(optimization_prompt, max_tokens=1000)
        
        return {
            "optimizations": optimization_response,
            "based_on_successes": len(similar_successes),
            "confidence": min(0.9, len(similar_successes) * 0.15),
            "generated_at": datetime.now().isoformat()
        }
    
    def _predict_success_probability(self, 
                                   dataset_info: DatasetInfo,
                                   objective: str,
                                   planned_pipeline: List[Dict[str, Any]],
                                   similar_attempts: List[PipelineExecution]) -> Dict[str, Any]:
        """Predict success probability for a planned pipeline."""
        
        if not similar_attempts:
            return {
                "success_probability": 0.5,
                "confidence": 0.1,
                "reasoning": "No similar attempts found for comparison"
            }
        
        successful_attempts = [ex for ex in similar_attempts if ex.success]
        success_rate = len(successful_attempts) / len(similar_attempts)
        
        prediction_prompt = f"""
        Predict the success probability of this planned pipeline:
        
        Planned Pipeline: {planned_pipeline}
        Dataset: {self._create_dataset_fingerprint(dataset_info)}
        Objective: {objective}
        
        Historical Success Rate for Similar Cases: {success_rate:.2%}
        Similar Attempts: {len(similar_attempts)}
        
        Consider:
        - Pipeline similarity to successful approaches
        - Dataset compatibility
        - Known risk factors
        
        Provide success probability (0-1) and reasoning.
        """
        
        prediction_response = self.reasoning_engine._call_llm(prediction_prompt, max_tokens=600)
        
        # Extract probability from response (simplified)
        base_probability = success_rate
        confidence = min(0.8, len(similar_attempts) * 0.1)
        
        return {
            "success_probability": base_probability,
            "confidence": confidence,
            "reasoning": prediction_response,
            "based_on_attempts": len(similar_attempts),
            "historical_success_rate": success_rate
        }
    
    def _refine_insights_from_feedback(self, execution_id: str, feedback: Dict[str, Any]):
        """Refine learning insights based on user feedback."""
        try:
            # This would implement feedback-based learning refinement
            # For now, just log the feedback for future processing
            self.logger.info(f"Received feedback for {execution_id}: {feedback}")
            
            # Future enhancement: Use feedback to adjust confidence scores,
            # update pattern recognition, and improve recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to refine insights from feedback: {e}")
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get statistics about the memory system."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM executions')
        total_executions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM executions WHERE success = 1')
        successful_executions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT objective) FROM executions')
        unique_objectives = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "unique_objectives": unique_objectives,
            "memory_size_mb": self.db_path.stat().st_size / 1024 / 1024 if self.db_path.exists() else 0,
            "insights_count": len(self.insights),
            "patterns_count": len(self.patterns)
        }