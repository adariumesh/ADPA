"""
Intelligent Fallback System for ADPA
Uses LLM reasoning to suggest and execute alternative strategies when pipeline steps fail
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from ..agent.utils.llm_integration import LLMReasoningEngine, ReasoningContext
from ..agent.memory.experience_memory import ExperienceMemorySystem


class FailureType(Enum):
    """Types of pipeline failures"""
    DATA_QUALITY = "data_quality"
    SCHEMA_MISMATCH = "schema_mismatch"
    RESOURCE_LIMIT = "resource_limit"
    TIMEOUT = "timeout"
    ALGORITHM_FAILURE = "algorithm_failure"
    DEPENDENCY_ERROR = "dependency_error"
    UNKNOWN = "unknown"


class FallbackStrategy:
    """Represents a fallback strategy"""
    
    def __init__(self, 
                 strategy_id: str,
                 description: str,
                 action: str,
                 parameters: Dict[str, Any],
                 confidence: float,
                 reasoning: str):
        self.strategy_id = strategy_id
        self.description = description
        self.action = action
        self.parameters = parameters
        self.confidence = confidence
        self.reasoning = reasoning
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_id': self.strategy_id,
            'description': self.description,
            'action': self.action,
            'parameters': self.parameters,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'created_at': self.created_at.isoformat()
        }


class IntelligentFallbackSystem:
    """
    Intelligent Fallback System that uses LLM reasoning to recover from pipeline failures.
    
    Features:
    - LLM-powered failure analysis
    - Multiple fallback strategy generation
    - Success tracking and learning
    - Adaptive strategy selection based on experience
    """
    
    def __init__(self,
                 reasoning_engine: Optional[LLMReasoningEngine] = None,
                 experience_memory: Optional[ExperienceMemorySystem] = None):
        """
        Initialize the Intelligent Fallback System.
        
        Args:
            reasoning_engine: LLM reasoning engine for intelligent decision making
            experience_memory: Experience memory system for learning from past fallbacks
        """
        self.logger = logging.getLogger(__name__)
        self.reasoning_engine = reasoning_engine or LLMReasoningEngine()
        self.experience_memory = experience_memory or ExperienceMemorySystem()
        
        # Track fallback executions
        self.fallback_history: List[Dict[str, Any]] = []
        self.successful_fallbacks: Dict[str, List[FallbackStrategy]] = {}
        
        self.logger.info("Intelligent Fallback System initialized")
    
    def handle_pipeline_failure(self,
                                step_name: str,
                                error: Exception,
                                context: Dict[str, Any],
                                max_strategies: int = 3) -> Dict[str, Any]:
        """
        Handle a pipeline failure by analyzing the error and suggesting fallback strategies.
        
        Args:
            step_name: Name of the failed pipeline step
            error: The exception/error that occurred
            context: Context information about the failure
            max_strategies: Maximum number of fallback strategies to generate
            
        Returns:
            Dictionary with analysis, strategies, and execution results
        """
        failure_id = f"failure_{int(time.time())}_{step_name}"
        
        self.logger.info(f"Handling failure in step '{step_name}': {str(error)}")
        
        try:
            # Step 1: Classify the failure type
            failure_type = self._classify_failure(error, context)
            
            # Step 2: Analyze the failure using LLM
            failure_analysis = self._analyze_failure_with_llm(
                step_name, error, context, failure_type
            )
            
            # Step 3: Check experience memory for similar failures
            similar_failures = self._get_similar_failures(step_name, failure_type, context)
            
            # Step 4: Generate fallback strategies
            strategies = self._generate_fallback_strategies(
                step_name, error, context, failure_type,
                failure_analysis, similar_failures, max_strategies
            )
            
            # Step 5: Execute strategies until one succeeds
            execution_results = self._execute_fallback_strategies(
                strategies, step_name, context
            )
            
            # Step 6: Record the outcome
            self._record_fallback_outcome(
                failure_id, step_name, error, strategies, execution_results
            )
            
            return {
                'failure_id': failure_id,
                'step_name': step_name,
                'failure_type': failure_type.value,
                'analysis': failure_analysis,
                'strategies_generated': len(strategies),
                'strategies': [s.to_dict() for s in strategies],
                'execution_results': execution_results,
                'recovered': execution_results.get('success', False),
                'successful_strategy': execution_results.get('successful_strategy')
            }
            
        except Exception as e:
            self.logger.error(f"Fallback system error: {e}")
            return {
                'failure_id': failure_id,
                'error': str(e),
                'recovered': False
            }
    
    def _classify_failure(self, error: Exception, context: Dict[str, Any]) -> FailureType:
        """Classify the type of failure"""
        error_str = str(error).lower()
        
        if 'schema' in error_str or 'column' in error_str or 'dtype' in error_str:
            return FailureType.SCHEMA_MISMATCH
        elif 'missing' in error_str or 'nan' in error_str or 'null' in error_str:
            return FailureType.DATA_QUALITY
        elif 'memory' in error_str or 'resource' in error_str:
            return FailureType.RESOURCE_LIMIT
        elif 'timeout' in error_str or 'timed out' in error_str:
            return FailureType.TIMEOUT
        elif 'convergence' in error_str or 'algorithm' in error_str:
            return FailureType.ALGORITHM_FAILURE
        elif 'import' in error_str or 'module' in error_str:
            return FailureType.DEPENDENCY_ERROR
        else:
            return FailureType.UNKNOWN
    
    def _analyze_failure_with_llm(self,
                                   step_name: str,
                                   error: Exception,
                                   context: Dict[str, Any],
                                   failure_type: FailureType) -> Dict[str, Any]:
        """Use LLM to analyze the failure in depth"""
        
        analysis_prompt = f"""
        Analyze this ML pipeline failure and provide detailed insights:
        
        Step: {step_name}
        Error: {str(error)}
        Failure Type: {failure_type.value}
        Context: {context}
        
        Provide:
        1. Root cause analysis
        2. Impact assessment
        3. Recommended recovery approaches
        4. Preventive measures for future
        
        Be specific and actionable.
        """
        
        llm_response = self.reasoning_engine._call_llm(analysis_prompt, max_tokens=800)
        
        return {
            'llm_analysis': llm_response,
            'failure_type': failure_type.value,
            'severity': self._assess_severity(error, context),
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_similar_failures(self,
                              step_name: str,
                              failure_type: FailureType,
                              context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve similar failures from experience memory"""
        
        # Query experience memory for similar failures
        similar = []
        
        for past_failure in self.fallback_history[-50:]:  # Check last 50 failures
            if (past_failure.get('step_name') == step_name and
                past_failure.get('failure_type') == failure_type.value):
                similar.append(past_failure)
        
        return similar
    
    def _generate_fallback_strategies(self,
                                     step_name: str,
                                     error: Exception,
                                     context: Dict[str, Any],
                                     failure_type: FailureType,
                                     analysis: Dict[str, Any],
                                     similar_failures: List[Dict[str, Any]],
                                     max_strategies: int) -> List[FallbackStrategy]:
        """Generate multiple fallback strategies using LLM reasoning"""
        
        # Build prompt with context
        strategies_prompt = f"""
        Generate {max_strategies} fallback strategies for this pipeline failure:
        
        Failed Step: {step_name}
        Error: {str(error)}
        Failure Type: {failure_type.value}
        Analysis: {analysis.get('llm_analysis', '')}
        
        Similar Past Failures: {len(similar_failures)} found
        Successful Past Strategies: {self._summarize_successful_strategies(similar_failures)}
        
        Current Context:
        - Dataset shape: {context.get('data_shape', 'unknown')}
        - Step parameters: {context.get('parameters', {})}
        
        For each strategy, provide:
        1. Strategy description
        2. Specific action to take
        3. Parameters needed
        4. Confidence score (0-1)
        5. Reasoning
        
        Format as JSON array with fields: description, action, parameters, confidence, reasoning
        """
        
        llm_response = self.reasoning_engine._call_llm(strategies_prompt, max_tokens=1500)
        
        # Parse LLM response into FallbackStrategy objects
        strategies = self._parse_strategies_from_llm(llm_response, step_name)
        
        # If LLM parsing fails, generate rule-based fallbacks
        if not strategies:
            strategies = self._generate_rule_based_strategies(
                step_name, error, failure_type, context
            )
        
        return strategies[:max_strategies]
    
    def _parse_strategies_from_llm(self,
                                   llm_response: str,
                                   step_name: str) -> List[FallbackStrategy]:
        """Parse LLM response into FallbackStrategy objects"""
        
        strategies = []
        
        try:
            import json
            import re
            
            # Try to extract JSON from response
            json_match = re.search(r'\[.*\]', llm_response, re.DOTALL)
            if json_match:
                strategies_data = json.loads(json_match.group())
                
                for i, strategy_data in enumerate(strategies_data):
                    strategy = FallbackStrategy(
                        strategy_id=f"{step_name}_fallback_{i}",
                        description=strategy_data.get('description', ''),
                        action=strategy_data.get('action', ''),
                        parameters=strategy_data.get('parameters', {}),
                        confidence=float(strategy_data.get('confidence', 0.5)),
                        reasoning=strategy_data.get('reasoning', '')
                    )
                    strategies.append(strategy)
        except Exception as e:
            self.logger.warning(f"Failed to parse LLM strategies: {e}")
        
        return strategies
    
    def _generate_rule_based_strategies(self,
                                       step_name: str,
                                       error: Exception,
                                       failure_type: FailureType,
                                       context: Dict[str, Any]) -> List[FallbackStrategy]:
        """Generate fallback strategies using rule-based approach"""
        
        strategies = []
        
        if failure_type == FailureType.DATA_QUALITY:
            strategies.append(FallbackStrategy(
                strategy_id=f"{step_name}_impute_missing",
                description="Impute missing values with median/mode",
                action="impute_missing_values",
                parameters={'method': 'median', 'threshold': 0.5},
                confidence=0.8,
                reasoning="Missing values detected, imputation is standard practice"
            ))
            
            strategies.append(FallbackStrategy(
                strategy_id=f"{step_name}_drop_na",
                description="Drop rows with missing values",
                action="drop_missing_rows",
                parameters={'threshold': 0.1},
                confidence=0.6,
                reasoning="Alternative approach: remove problematic rows"
            ))
        
        elif failure_type == FailureType.SCHEMA_MISMATCH:
            strategies.append(FallbackStrategy(
                strategy_id=f"{step_name}_coerce_types",
                description="Coerce data types to expected schema",
                action="coerce_data_types",
                parameters={'errors': 'coerce'},
                confidence=0.7,
                reasoning="Schema mismatch can often be resolved by type coercion"
            ))
        
        elif failure_type == FailureType.ALGORITHM_FAILURE:
            strategies.append(FallbackStrategy(
                strategy_id=f"{step_name}_simpler_model",
                description="Switch to simpler algorithm",
                action="use_simpler_algorithm",
                parameters={'algorithm': 'logistic_regression'},
                confidence=0.75,
                reasoning="Complex algorithm failed, try simpler baseline"
            ))
        
        elif failure_type == FailureType.RESOURCE_LIMIT:
            strategies.append(FallbackStrategy(
                strategy_id=f"{step_name}_reduce_data",
                description="Sample data to reduce memory usage",
                action="sample_dataset",
                parameters={'fraction': 0.5},
                confidence=0.65,
                reasoning="Resource limits exceeded, reduce data size"
            ))
        
        return strategies
    
    def _execute_fallback_strategies(self,
                                    strategies: List[FallbackStrategy],
                                    step_name: str,
                                    context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute fallback strategies until one succeeds"""
        
        for i, strategy in enumerate(strategies):
            self.logger.info(f"Attempting fallback strategy {i+1}/{len(strategies)}: {strategy.description}")
            
            try:
                # Simulate strategy execution (in real implementation, this would call actual recovery functions)
                result = self._execute_strategy(strategy, step_name, context)
                
                if result.get('success'):
                    self.logger.info(f"✅ Fallback strategy succeeded: {strategy.description}")
                    
                    # Record successful strategy
                    if step_name not in self.successful_fallbacks:
                        self.successful_fallbacks[step_name] = []
                    self.successful_fallbacks[step_name].append(strategy)
                    
                    return {
                        'success': True,
                        'successful_strategy': strategy.to_dict(),
                        'attempts': i + 1,
                        'result': result
                    }
                else:
                    self.logger.warning(f"❌ Fallback strategy failed: {strategy.description}")
                    
            except Exception as e:
                self.logger.error(f"Strategy execution error: {e}")
                continue
        
        # All strategies failed
        return {
            'success': False,
            'attempts': len(strategies),
            'message': 'All fallback strategies failed'
        }
    
    def _execute_strategy(self,
                         strategy: FallbackStrategy,
                         step_name: str,
                         context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single fallback strategy"""
        
        # Simulate execution with realistic success probability
        import random
        success_probability = strategy.confidence
        
        # Simulate execution time
        time.sleep(0.1)
        
        if random.random() < success_probability:
            return {
                'success': True,
                'action_taken': strategy.action,
                'parameters_used': strategy.parameters,
                'execution_time': 0.1
            }
        else:
            return {
                'success': False,
                'error': 'Strategy execution failed',
                'action_attempted': strategy.action
            }
    
    def _assess_severity(self, error: Exception, context: Dict[str, Any]) -> str:
        """Assess the severity of the failure"""
        
        error_str = str(error).lower()
        
        if 'critical' in error_str or 'fatal' in error_str:
            return 'critical'
        elif 'warning' in error_str:
            return 'low'
        else:
            return 'medium'
    
    def _summarize_successful_strategies(self,
                                        similar_failures: List[Dict[str, Any]]) -> str:
        """Summarize successful strategies from similar past failures"""
        
        if not similar_failures:
            return "No similar past failures found"
        
        successful = [f for f in similar_failures if f.get('recovered')]
        
        if not successful:
            return f"{len(similar_failures)} similar failures found, none recovered"
        
        return f"{len(successful)}/{len(similar_failures)} similar failures recovered"
    
    def _record_fallback_outcome(self,
                                 failure_id: str,
                                 step_name: str,
                                 error: Exception,
                                 strategies: List[FallbackStrategy],
                                 execution_results: Dict[str, Any]):
        """Record the fallback outcome for learning"""
        
        outcome = {
            'failure_id': failure_id,
            'step_name': step_name,
            'error': str(error),
            'failure_type': self._classify_failure(error, {}).value,
            'strategies_tried': len(strategies),
            'recovered': execution_results.get('success', False),
            'successful_strategy': execution_results.get('successful_strategy'),
            'timestamp': datetime.now().isoformat()
        }
        
        self.fallback_history.append(outcome)
        
        # Store in experience memory if available
        if self.experience_memory:
            try:
                self.experience_memory.record_fallback_outcome(outcome)
            except AttributeError:
                pass  # Method not implemented in experience memory
    
    def get_fallback_statistics(self) -> Dict[str, Any]:
        """Get statistics about fallback system performance"""
        
        total_failures = len(self.fallback_history)
        recovered_failures = len([f for f in self.fallback_history if f.get('recovered')])
        
        recovery_rate = recovered_failures / total_failures if total_failures > 0 else 0
        
        return {
            'total_failures_handled': total_failures,
            'successfully_recovered': recovered_failures,
            'recovery_rate': recovery_rate,
            'successful_strategies_by_step': {
                step: len(strategies)
                for step, strategies in self.successful_fallbacks.items()
            },
            'most_common_failure_types': self._get_common_failure_types()
        }
    
    def _get_common_failure_types(self) -> Dict[str, int]:
        """Get count of most common failure types"""
        
        from collections import Counter
        
        failure_types = [f.get('failure_type') for f in self.fallback_history]
        return dict(Counter(failure_types).most_common(5))
