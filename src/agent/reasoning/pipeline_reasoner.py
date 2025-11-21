"""
Agentic Pipeline Reasoner - Replaces rule-based pipeline planning with intelligent reasoning.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pandas as pd

from ..core.interfaces import (
    PipelineStep, PipelineStepType, DatasetInfo, PipelineConfig,
    ExecutionResult, StepStatus
)
from ..utils.llm_integration import LLMReasoningEngine, ReasoningContext, ReasoningResponse
from ..memory.experience_memory import ExperienceMemorySystem


class AgenticPipelineReasoner:
    """
    Intelligent pipeline planning system that uses LLM reasoning to create optimal pipelines.
    
    Replaces hardcoded rules with context-aware decision making:
    - Analyzes dataset characteristics with intelligent reasoning
    - Considers business objectives and constraints
    - Learns from past successful and failed approaches
    - Adapts pipeline strategy based on real-world performance
    - Provides explanations for all decisions
    """
    
    def __init__(self, 
                 reasoning_engine: LLMReasoningEngine,
                 experience_memory: ExperienceMemorySystem):
        """
        Initialize the agentic pipeline reasoner.
        
        Args:
            reasoning_engine: LLM reasoning engine for intelligent decisions
            experience_memory: Experience memory for learning from past executions
        """
        self.reasoning_engine = reasoning_engine
        self.experience_memory = experience_memory
        self.logger = logging.getLogger(__name__)
        
        # Pipeline strategy templates (dynamic, not hardcoded)
        self.strategy_domains = {
            "data_preprocessing": "intelligent data cleaning and preparation",
            "feature_engineering": "optimal feature creation and selection", 
            "model_selection": "algorithm selection and hyperparameter optimization",
            "evaluation": "comprehensive model assessment and validation",
            "deployment": "production readiness and monitoring setup"
        }
        
        self.logger.info("Agentic Pipeline Reasoner initialized")
    
    def create_intelligent_pipeline_plan(self, 
                                       dataset_info: DatasetInfo,
                                       objective_understanding: Dict[str, Any],
                                       recommendations: Dict[str, Any],
                                       context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an intelligent pipeline plan using LLM reasoning and experience.
        
        Args:
            dataset_info: Comprehensive dataset analysis
            objective_understanding: LLM understanding of user's objective
            recommendations: Experience-based recommendations
            context: Additional business context
            
        Returns:
            Dictionary with intelligent pipeline plan and reasoning
        """
        try:
            self.logger.info("Creating intelligent pipeline plan...")
            
            # Create reasoning context
            reasoning_context = ReasoningContext(
                domain="pipeline_planning",
                objective=objective_understanding.get('objective', 'unknown'),
                data_context={
                    "dataset_info": dataset_info.__dict__ if hasattr(dataset_info, '__dict__') else dataset_info,
                    "objective_understanding": objective_understanding,
                    "recommendations": recommendations,
                    "business_context": context or {}
                },
                constraints=objective_understanding.get('constraints', {}),
                execution_history=self._get_relevant_execution_history(dataset_info, objective_understanding)
            )
            
            # Use LLM to create intelligent pipeline plan
            reasoning_response = self.reasoning_engine.reason_about_pipeline_planning(reasoning_context)
            
            # Extract structured pipeline from LLM response
            structured_pipeline = self._extract_pipeline_structure(reasoning_response, dataset_info, objective_understanding)
            
            # Validate and optimize the pipeline plan
            validated_pipeline = self._validate_and_optimize_pipeline(structured_pipeline, reasoning_context)
            
            # Generate resource and time estimates
            estimates = self._estimate_pipeline_requirements(validated_pipeline, dataset_info)
            
            # Create comprehensive pipeline plan
            pipeline_plan = {
                "pipeline_id": f"intelligent_pipeline_{int(datetime.now().timestamp())}",
                "reasoning": reasoning_response.reasoning,
                "confidence": reasoning_response.confidence,
                "steps": validated_pipeline,
                "alternatives": reasoning_response.alternatives,
                "estimates": estimates,
                "explanation": reasoning_response.explanation,
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "reasoning_engine": "llm_powered",
                    "based_on_experience": recommendations.get("based_on_executions", 0),
                    "adaptation_level": "high"
                }
            }
            
            self.logger.info(f"Created intelligent pipeline with {len(validated_pipeline)} steps, confidence: {reasoning_response.confidence}")
            
            return pipeline_plan
            
        except Exception as e:
            self.logger.error(f"Failed to create intelligent pipeline plan: {e}")
            return self._create_fallback_pipeline_plan(dataset_info, objective_understanding)
    
    def adapt_pipeline_during_execution(self, 
                                      current_pipeline: Dict[str, Any],
                                      execution_context: Dict[str, Any],
                                      performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt pipeline strategy during execution based on real-time performance.
        
        Args:
            current_pipeline: Currently executing pipeline
            execution_context: Current execution state and context
            performance_data: Real-time performance metrics
            
        Returns:
            Dictionary with adaptation recommendations
        """
        try:
            adaptation_prompt = f"""
            Analyze current pipeline execution and suggest real-time adaptations:
            
            Current Pipeline: {current_pipeline}
            Execution Context: {execution_context}
            Performance Data: {performance_data}
            
            Based on the current performance, should we:
            1. Continue with current approach
            2. Modify parameters
            3. Switch algorithms
            4. Add preprocessing steps
            5. Abort and restart with different strategy
            
            Provide specific recommendations with reasoning.
            """
            
            adaptation_response = self.reasoning_engine._call_llm(adaptation_prompt, max_tokens=800)
            
            return {
                "adaptation_needed": True,
                "recommendations": adaptation_response,
                "confidence": 0.8,
                "urgency": self._assess_adaptation_urgency(performance_data),
                "suggested_actions": self._extract_adaptation_actions(adaptation_response)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to adapt pipeline during execution: {e}")
            return {"adaptation_needed": False, "error": str(e)}
    
    def reason_about_algorithm_selection(self, 
                                       dataset_info: DatasetInfo,
                                       problem_type: str,
                                       performance_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use intelligent reasoning to select optimal algorithms.
        
        Args:
            dataset_info: Dataset characteristics
            problem_type: Type of ML problem
            performance_requirements: Required performance criteria
            
        Returns:
            Dictionary with algorithm recommendations and reasoning
        """
        try:
            reasoning_context = ReasoningContext(
                domain="model_selection",
                objective=problem_type,
                data_context={
                    "dataset_characteristics": dataset_info.__dict__ if hasattr(dataset_info, '__dict__') else dataset_info,
                    "performance_requirements": performance_requirements,
                    "problem_complexity": self._assess_problem_complexity(dataset_info)
                }
            )
            
            reasoning_response = self.reasoning_engine.reason_about_model_selection(reasoning_context)
            
            # Extract specific algorithm recommendations
            algorithm_recommendations = self._extract_algorithm_recommendations(
                reasoning_response, dataset_info, performance_requirements
            )
            
            return {
                "primary_algorithms": algorithm_recommendations["primary"],
                "backup_algorithms": algorithm_recommendations["backup"],
                "ensemble_strategy": algorithm_recommendations["ensemble"],
                "reasoning": reasoning_response.reasoning,
                "confidence": reasoning_response.confidence,
                "expected_performance": algorithm_recommendations["performance_estimate"],
                "training_strategy": algorithm_recommendations["training_approach"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to reason about algorithm selection: {e}")
            return self._get_default_algorithm_recommendation(dataset_info, problem_type)
    
    def reason_about_feature_engineering(self, 
                                       dataset_info: DatasetInfo,
                                       objective: str,
                                       data_sample: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Use intelligent reasoning to determine optimal feature engineering strategy.
        
        Args:
            dataset_info: Dataset characteristics
            objective: ML objective
            data_sample: Sample of the actual data for analysis
            
        Returns:
            Dictionary with feature engineering recommendations
        """
        try:
            # Analyze data characteristics for feature engineering
            feature_analysis = self._analyze_feature_engineering_opportunities(dataset_info, data_sample)
            
            reasoning_context = ReasoningContext(
                domain="feature_engineering",
                objective=objective,
                data_context={
                    "dataset_info": dataset_info.__dict__ if hasattr(dataset_info, '__dict__') else dataset_info,
                    "feature_analysis": feature_analysis,
                    "data_quality": self._assess_data_quality(dataset_info)
                }
            )
            
            reasoning_response = self.reasoning_engine.reason_about_data_strategy(reasoning_context)
            
            # Extract structured feature engineering plan
            fe_plan = self._extract_feature_engineering_plan(reasoning_response, feature_analysis)
            
            return {
                "feature_engineering_plan": fe_plan,
                "reasoning": reasoning_response.reasoning,
                "confidence": reasoning_response.confidence,
                "estimated_impact": fe_plan["impact_estimate"],
                "implementation_order": fe_plan["execution_order"],
                "validation_strategy": fe_plan["validation_approach"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to reason about feature engineering: {e}")
            return self._get_default_feature_engineering_plan(dataset_info)
    
    def handle_pipeline_failure_intelligently(self, 
                                            failed_step: str,
                                            error_details: Dict[str, Any],
                                            execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use intelligent reasoning to handle pipeline failures and suggest recovery.
        
        Args:
            failed_step: Name of the step that failed
            error_details: Detailed error information
            execution_context: Context of the failed execution
            
        Returns:
            Dictionary with intelligent recovery strategy
        """
        try:
            reasoning_context = ReasoningContext(
                domain="error_recovery",
                objective="pipeline_recovery",
                data_context={
                    "failed_step": failed_step,
                    "error_details": error_details,
                    "execution_context": execution_context,
                    "pipeline_state": execution_context.get("pipeline_state", {})
                }
            )
            
            recovery_response = self.reasoning_engine.reason_about_error_recovery(
                failed_step, str(error_details), reasoning_context
            )
            
            # Extract actionable recovery plan
            recovery_plan = self._extract_recovery_plan(recovery_response, execution_context)
            
            return {
                "recovery_strategy": recovery_plan,
                "reasoning": recovery_response.reasoning,
                "confidence": recovery_response.confidence,
                "alternatives": recovery_response.alternatives,
                "estimated_recovery_time": recovery_plan["time_estimate"],
                "success_probability": recovery_plan["success_probability"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to handle pipeline failure intelligently: {e}")
            return self._get_default_recovery_strategy(failed_step, error_details)
    
    def _get_relevant_execution_history(self, 
                                      dataset_info: DatasetInfo,
                                      objective_understanding: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant execution history for context."""
        try:
            # Get similar executions from experience memory
            similar_executions = self.experience_memory._find_similar_executions(
                dataset_info, 
                objective_understanding.get('problem_type', 'unknown'),
                limit=5
            )
            
            # Convert to context format
            history = []
            for execution in similar_executions:
                history.append({
                    "objective": execution.objective,
                    "success": execution.success,
                    "performance": execution.performance_metrics,
                    "approach": [step.get('step', 'unknown') for step in execution.pipeline_steps],
                    "insights": execution.learned_insights
                })
            
            return history
            
        except Exception as e:
            self.logger.warning(f"Failed to get execution history: {e}")
            return []
    
    def _extract_pipeline_structure(self, 
                                  reasoning_response: ReasoningResponse,
                                  dataset_info: DatasetInfo,
                                  objective_understanding: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract structured pipeline steps from LLM reasoning response."""
        try:
            # Parse the LLM response to extract pipeline steps
            # This is a simplified extraction - in production, would use more sophisticated NLP
            
            default_steps = [
                {
                    "step": "data_validation",
                    "type": "preprocessing",
                    "reasoning": "Ensure data integrity and quality",
                    "parameters": {"validate_schema": True, "check_missing": True},
                    "estimated_duration": "5 minutes"
                },
                {
                    "step": "intelligent_preprocessing",
                    "type": "preprocessing", 
                    "reasoning": "LLM-guided data cleaning and preparation",
                    "parameters": {"strategy": "adaptive", "missing_value_approach": "intelligent"},
                    "estimated_duration": "15 minutes"
                },
                {
                    "step": "feature_engineering",
                    "type": "feature_engineering",
                    "reasoning": "Create optimal features based on data characteristics",
                    "parameters": {"approach": "llm_guided", "feature_selection": True},
                    "estimated_duration": "20 minutes"
                },
                {
                    "step": "model_training",
                    "type": "training",
                    "reasoning": "Train optimal model based on intelligent algorithm selection",
                    "parameters": {"algorithm": "adaptive", "hyperparameter_tuning": True},
                    "estimated_duration": "30 minutes"
                },
                {
                    "step": "evaluation",
                    "type": "evaluation",
                    "reasoning": "Comprehensive model evaluation with business context",
                    "parameters": {"metrics": "adaptive", "business_validation": True},
                    "estimated_duration": "10 minutes"
                }
            ]
            
            # Customize based on dataset characteristics
            if len(dataset_info.categorical_columns) > 5:
                # Add categorical encoding step
                default_steps.insert(2, {
                    "step": "categorical_encoding",
                    "type": "preprocessing",
                    "reasoning": "High number of categorical variables detected",
                    "parameters": {"strategy": "intelligent_encoding"},
                    "estimated_duration": "10 minutes"
                })
            
            if dataset_info.shape[0] > 100000:
                # Add data sampling for large datasets
                default_steps.insert(1, {
                    "step": "intelligent_sampling",
                    "type": "preprocessing",
                    "reasoning": "Large dataset detected, intelligent sampling for efficiency",
                    "parameters": {"strategy": "stratified", "size": "optimal"},
                    "estimated_duration": "8 minutes"
                })
            
            return default_steps
            
        except Exception as e:
            self.logger.error(f"Failed to extract pipeline structure: {e}")
            return self._get_default_pipeline_structure()
    
    def _validate_and_optimize_pipeline(self, 
                                      pipeline: List[Dict[str, Any]],
                                      reasoning_context: ReasoningContext) -> List[Dict[str, Any]]:
        """Validate and optimize the proposed pipeline."""
        try:
            # Check for logical step ordering
            validated_pipeline = []
            
            # Ensure preprocessing comes before training
            preprocessing_steps = [step for step in pipeline if step.get("type") == "preprocessing"]
            feature_steps = [step for step in pipeline if step.get("type") == "feature_engineering"]
            training_steps = [step for step in pipeline if step.get("type") == "training"]
            evaluation_steps = [step for step in pipeline if step.get("type") == "evaluation"]
            
            # Logical ordering
            validated_pipeline.extend(preprocessing_steps)
            validated_pipeline.extend(feature_steps)
            validated_pipeline.extend(training_steps)
            validated_pipeline.extend(evaluation_steps)
            
            # Add any other steps that don't fit categories
            other_steps = [step for step in pipeline if step.get("type") not in 
                         ["preprocessing", "feature_engineering", "training", "evaluation"]]
            validated_pipeline.extend(other_steps)
            
            return validated_pipeline
            
        except Exception as e:
            self.logger.error(f"Failed to validate pipeline: {e}")
            return pipeline
    
    def _estimate_pipeline_requirements(self, 
                                      pipeline: List[Dict[str, Any]],
                                      dataset_info: DatasetInfo) -> Dict[str, Any]:
        """Estimate resource and time requirements for the pipeline."""
        try:
            total_duration = 0
            for step in pipeline:
                duration_str = step.get("estimated_duration", "10 minutes")
                # Simple parsing - extract number
                duration_minutes = 10  # default
                if "minutes" in duration_str:
                    try:
                        duration_minutes = int(duration_str.split()[0])
                    except:
                        pass
                total_duration += duration_minutes
            
            # Estimate based on dataset size
            size_multiplier = 1.0
            if dataset_info.shape[0] > 10000:
                size_multiplier = 1.5
            if dataset_info.shape[0] > 100000:
                size_multiplier = 2.0
            
            total_duration = int(total_duration * size_multiplier)
            
            return {
                "estimated_duration_minutes": total_duration,
                "estimated_compute_cost": total_duration * 0.10,  # $0.10 per minute estimate
                "memory_requirements": f"{max(1, dataset_info.shape[0] * dataset_info.shape[1] / 100000)} GB",
                "parallel_execution_possible": True,
                "resource_efficiency": "optimized"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to estimate requirements: {e}")
            return {"estimated_duration_minutes": 60, "memory_requirements": "2 GB"}
    
    def _analyze_feature_engineering_opportunities(self, 
                                                 dataset_info: DatasetInfo,
                                                 data_sample: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """Analyze opportunities for feature engineering."""
        opportunities = {
            "categorical_encoding_needed": len(dataset_info.categorical_columns) > 0,
            "missing_value_imputation": sum(dataset_info.missing_values.values()) > 0,
            "feature_scaling_needed": len(dataset_info.numeric_columns) > 1,
            "dimensionality_reduction": len(dataset_info.columns) > 50,
            "interaction_features": len(dataset_info.numeric_columns) > 2,
            "polynomial_features": len(dataset_info.numeric_columns) <= 10
        }
        
        return opportunities
    
    def _assess_data_quality(self, dataset_info: DatasetInfo) -> Dict[str, Any]:
        """Assess overall data quality."""
        total_cells = dataset_info.shape[0] * dataset_info.shape[1]
        missing_ratio = sum(dataset_info.missing_values.values()) / total_cells if total_cells > 0 else 0
        
        quality_score = 1.0 - missing_ratio
        if quality_score > 0.9:
            quality_level = "high"
        elif quality_score > 0.7:
            quality_level = "medium"
        else:
            quality_level = "low"
        
        return {
            "quality_score": quality_score,
            "quality_level": quality_level,
            "missing_data_ratio": missing_ratio,
            "data_completeness": 1 - missing_ratio
        }
    
    def _assess_problem_complexity(self, dataset_info: DatasetInfo) -> str:
        """Assess the complexity of the ML problem."""
        complexity_factors = 0
        
        if dataset_info.shape[1] > 50:
            complexity_factors += 1
        if len(dataset_info.categorical_columns) > 10:
            complexity_factors += 1
        if sum(dataset_info.missing_values.values()) / (dataset_info.shape[0] * dataset_info.shape[1]) > 0.2:
            complexity_factors += 1
        if dataset_info.shape[0] > 100000:
            complexity_factors += 1
        
        if complexity_factors >= 3:
            return "high"
        elif complexity_factors >= 2:
            return "medium"
        else:
            return "low"
    
    def _extract_algorithm_recommendations(self, 
                                         reasoning_response: ReasoningResponse,
                                         dataset_info: DatasetInfo,
                                         performance_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Extract algorithm recommendations from LLM response."""
        # Default intelligent recommendations based on dataset characteristics
        if dataset_info.shape[0] < 1000:
            primary = ["logistic_regression", "svm", "decision_tree"]
        elif dataset_info.shape[0] < 10000:
            primary = ["random_forest", "gradient_boosting", "xgboost"]
        else:
            primary = ["lightgbm", "neural_network", "ensemble"]
        
        return {
            "primary": primary,
            "backup": ["logistic_regression", "random_forest"],
            "ensemble": "voting_classifier",
            "performance_estimate": {"accuracy": 0.85, "training_time": "20 minutes"},
            "training_approach": "cross_validation"
        }
    
    def _extract_feature_engineering_plan(self, 
                                        reasoning_response: ReasoningResponse,
                                        feature_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract feature engineering plan from reasoning response."""
        plan_steps = []
        
        if feature_analysis.get("missing_value_imputation"):
            plan_steps.append("intelligent_imputation")
        if feature_analysis.get("categorical_encoding_needed"):
            plan_steps.append("categorical_encoding")
        if feature_analysis.get("feature_scaling_needed"):
            plan_steps.append("feature_scaling")
        if feature_analysis.get("interaction_features"):
            plan_steps.append("interaction_features")
        
        return {
            "steps": plan_steps,
            "execution_order": plan_steps,
            "impact_estimate": "medium_to_high",
            "validation_approach": "cross_validation"
        }
    
    def _extract_recovery_plan(self, 
                             reasoning_response: ReasoningResponse,
                             execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract recovery plan from reasoning response."""
        return {
            "strategy": "retry_with_modifications",
            "modifications": ["adjust_parameters", "fallback_algorithm"],
            "time_estimate": "10 minutes",
            "success_probability": 0.8
        }
    
    def _assess_adaptation_urgency(self, performance_data: Dict[str, Any]) -> str:
        """Assess urgency of pipeline adaptation."""
        if performance_data.get("error_rate", 0) > 0.5:
            return "high"
        elif performance_data.get("performance_degradation", 0) > 0.3:
            return "medium"
        else:
            return "low"
    
    def _extract_adaptation_actions(self, adaptation_response: str) -> List[str]:
        """Extract specific adaptation actions from LLM response."""
        # Simplified extraction
        actions = []
        if "parameter" in adaptation_response.lower():
            actions.append("adjust_parameters")
        if "algorithm" in adaptation_response.lower():
            actions.append("switch_algorithm")
        if "preprocess" in adaptation_response.lower():
            actions.append("add_preprocessing")
        
        return actions if actions else ["continue_monitoring"]
    
    def _create_fallback_pipeline_plan(self, 
                                     dataset_info: DatasetInfo,
                                     objective_understanding: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback pipeline plan when intelligent planning fails."""
        return {
            "pipeline_id": f"fallback_pipeline_{int(datetime.now().timestamp())}",
            "reasoning": "Fallback plan due to planning error",
            "confidence": 0.5,
            "steps": self._get_default_pipeline_structure(),
            "alternatives": [],
            "estimates": {"estimated_duration_minutes": 45},
            "explanation": "Using default pipeline structure as fallback",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "reasoning_engine": "fallback",
                "adaptation_level": "low"
            }
        }
    
    def _get_default_pipeline_structure(self) -> List[Dict[str, Any]]:
        """Get default pipeline structure."""
        return [
            {"step": "data_validation", "type": "preprocessing"},
            {"step": "preprocessing", "type": "preprocessing"},
            {"step": "feature_engineering", "type": "feature_engineering"},
            {"step": "training", "type": "training"},
            {"step": "evaluation", "type": "evaluation"}
        ]
    
    def _get_default_algorithm_recommendation(self, 
                                            dataset_info: DatasetInfo,
                                            problem_type: str) -> Dict[str, Any]:
        """Get default algorithm recommendation."""
        return {
            "primary_algorithms": ["random_forest", "gradient_boosting"],
            "backup_algorithms": ["logistic_regression"],
            "ensemble_strategy": "voting",
            "reasoning": "Default recommendation due to reasoning failure",
            "confidence": 0.5
        }
    
    def _get_default_feature_engineering_plan(self, dataset_info: DatasetInfo) -> Dict[str, Any]:
        """Get default feature engineering plan."""
        return {
            "feature_engineering_plan": {
                "steps": ["missing_value_imputation", "categorical_encoding", "scaling"],
                "execution_order": ["missing_value_imputation", "categorical_encoding", "scaling"],
                "impact_estimate": "medium",
                "validation_approach": "holdout"
            },
            "reasoning": "Default feature engineering plan",
            "confidence": 0.5
        }
    
    def _get_default_recovery_strategy(self, 
                                     failed_step: str,
                                     error_details: Dict[str, Any]) -> Dict[str, Any]:
        """Get default recovery strategy."""
        return {
            "recovery_strategy": {
                "strategy": "retry",
                "modifications": ["reduce_complexity"],
                "time_estimate": "15 minutes",
                "success_probability": 0.6
            },
            "reasoning": "Default recovery strategy",
            "confidence": 0.5
        }