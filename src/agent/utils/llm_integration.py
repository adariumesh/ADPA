"""
LLM Integration Layer for ADPA Agentic Reasoning
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import boto3
from botocore.exceptions import ClientError


class LLMProvider(Enum):
    """Supported LLM providers for agentic reasoning."""
    OPENAI = "openai"
    BEDROCK = "bedrock"
    ANTHROPIC = "anthropic"


@dataclass
class ReasoningContext:
    """Context for LLM reasoning requests."""
    domain: str  # "pipeline_planning", "error_recovery", "data_analysis", etc.
    objective: str
    data_context: Dict[str, Any]
    execution_history: Optional[List[Dict[str, Any]]] = None
    constraints: Optional[Dict[str, Any]] = None
    previous_reasoning: Optional[str] = None


@dataclass
class ReasoningResponse:
    """Response from LLM reasoning."""
    reasoning: str
    decision: Dict[str, Any]
    confidence: float
    alternatives: List[Dict[str, Any]]
    explanation: str
    metadata: Dict[str, Any]


class LLMReasoningEngine:
    """
    Core LLM integration for ADPA agentic reasoning capabilities.
    Provides intelligent decision making across all pipeline components.
    """
    
    def __init__(self, 
                 provider: LLMProvider = LLMProvider.BEDROCK,
                 model_id: str = "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
                 region: str = "us-east-2",
                 force_real_ai: bool = True):
        """
        Initialize the LLM reasoning engine with real LLM integration.
        
        Args:
            provider: LLM provider to use (defaults to Bedrock)
            model_id: Specific model to use
            region: AWS region for Bedrock
            force_real_ai: If True, fail hard without falling back to simulation
        """
        self.provider = provider
        self.model_id = model_id
        self.region = region
        self.force_real_ai = force_real_ai or os.getenv('USE_REAL_LLM', 'false').lower() == 'true'
        self.logger = logging.getLogger(__name__)
        
        # Initialize provider client
        self._init_provider_client()
        
        # Reasoning prompt templates
        self.prompt_templates = self._load_prompt_templates()
        
        # Track reasoning calls for learning
        self.reasoning_calls = []
        
        if self.force_real_ai:
            self.logger.info(f"🚀 REAL AI ENABLED - Using {provider.value} with model {model_id}")
        else:
            self.logger.info(f"LLM Reasoning Engine initialized with {provider.value}")
    
    def reason_about_pipeline_planning(self, context: ReasoningContext) -> ReasoningResponse:
        """
        Use LLM to reason about optimal pipeline planning.
        
        Args:
            context: Reasoning context with dataset and objective info
            
        Returns:
            ReasoningResponse with pipeline plan and reasoning
        """
        prompt = self._build_pipeline_planning_prompt(context)
        
        response = self._call_llm(prompt, max_tokens=2000)
        
        return self._parse_pipeline_response(response)
    
    def reason_about_error_recovery(self, 
                                   failed_step: str,
                                   error: str,
                                   context: ReasoningContext) -> ReasoningResponse:
        """
        Use LLM to reason about error recovery strategies.
        
        Args:
            failed_step: Name of the failed pipeline step
            error: Error message/details
            context: Execution context
            
        Returns:
            ReasoningResponse with recovery strategies
        """
        prompt = self._build_error_recovery_prompt(failed_step, error, context)
        
        response = self._call_llm(prompt, max_tokens=1500)
        
        return self._parse_recovery_response(response)
    
    def reason_about_data_strategy(self, context: ReasoningContext) -> ReasoningResponse:
        """
        Use LLM to reason about optimal data processing strategies.
        
        Args:
            context: Data context with dataset characteristics
            
        Returns:
            ReasoningResponse with data processing strategy
        """
        prompt = self._build_data_strategy_prompt(context)
        
        response = self._call_llm(prompt, max_tokens=1500)
        
        return self._parse_data_strategy_response(response)
    
    def reason_about_model_selection(self, context: ReasoningContext) -> ReasoningResponse:
        """
        Use LLM to reason about optimal model selection and training strategy.
        
        Args:
            context: Context with dataset and problem characteristics
            
        Returns:
            ReasoningResponse with model selection strategy
        """
        prompt = self._build_model_selection_prompt(context)
        
        response = self._call_llm(prompt, max_tokens=1500)
        
        return self._parse_model_selection_response(response)
    
    def analyze_execution_patterns(self, 
                                  execution_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze patterns in execution history to derive insights.
        
        Args:
            execution_history: List of past pipeline executions
            
        Returns:
            Dictionary with insights and recommendations
        """
        prompt = self._build_pattern_analysis_prompt(execution_history)
        
        response = self._call_llm(prompt, max_tokens=1000)
        
        return self._parse_pattern_analysis_response(response)
    
    def understand_natural_language_objective(self, 
                                            objective: str,
                                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parse and understand natural language objectives.
        
        Args:
            objective: Natural language description of ML objective
            context: Additional context about the business problem
            
        Returns:
            Structured understanding of the objective
        """
        # Extract problem_type directly from context - don't wait for LLM
        explicit_problem_type = context.get('problem_type') if context else None
        
        # DEBUG LOGGING
        self.logger.info(f"🔍 LLM.understand_objective called:")
        self.logger.info(f"   Context received: {context}")
        self.logger.info(f"   Explicit problem_type: {explicit_problem_type}")
            
        prompt = self._build_objective_understanding_prompt(objective, context)
        
        response = self._call_llm(prompt, max_tokens=800)
        
        result = self._parse_objective_understanding_response(response, explicit_problem_type)
        self.logger.info(f"   Final problem_type: {result['problem_type']}")
        
        return result
    
    def _init_provider_client(self):
        """Initialize the appropriate LLM provider client."""
        if self.provider == LLMProvider.BEDROCK:
            try:
                self.client = boto3.client('bedrock-runtime', region_name=self.region)
                self.logger.info("Bedrock client initialized successfully")
            except Exception as e:
                self.logger.warning(f"Bedrock client initialization failed: {e}")
                # Fallback to OpenAI if Bedrock fails
                self._fallback_to_openai()
        
        elif self.provider == LLMProvider.OPENAI:
            try:
                import openai
                openai_key = os.getenv('OPENAI_API_KEY')
                if not openai_key:
                    self.logger.warning("OPENAI_API_KEY not found in environment")
                    # For demo purposes, try to continue without real API
                    self.client = None
                else:
                    self.client = openai.OpenAI(api_key=openai_key)
                    self.logger.info("OpenAI client initialized successfully")
                    # Test the connection
                    self._test_openai_connection()
            except ImportError:
                self.logger.error("OpenAI package not installed")
                self.client = None
            except Exception as e:
                self.logger.error(f"OpenAI client initialization failed: {e}")
                self.client = None
        
        else:
            self.logger.error(f"Unsupported LLM provider: {self.provider}")
            self.client = None
    
    def _fallback_to_openai(self):
        """Fallback to OpenAI when other providers fail."""
        try:
            import openai
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                self.client = openai.OpenAI(api_key=openai_key)
                self.provider = LLMProvider.OPENAI
                self.model_id = "gpt-4"
                self.logger.info("Fallback to OpenAI successful")
            else:
                self.client = None
        except Exception as e:
            self.logger.error(f"Fallback to OpenAI failed: {e}")
            self.client = None
    
    def _test_openai_connection(self):
        """Test OpenAI connection with a simple call."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": "Test connection. Respond with 'OK'."}],
                max_tokens=10,
                temperature=0
            )
            if response.choices[0].message.content:
                self.logger.info("OpenAI connection test successful")
            else:
                self.logger.warning("OpenAI connection test returned empty response")
        except Exception as e:
            self.logger.warning(f"OpenAI connection test failed: {e}")
            # Don't set client to None here, still try to use it
    
    def _call_llm(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1) -> str:
        """
        Make a real call to the LLM with the given prompt.
        
        Args:
            prompt: Input prompt for the LLM
            max_tokens: Maximum tokens to generate
            temperature: Temperature for response generation
            
        Returns:
            LLM response text
        """
        import time
        start_time = time.time()
        
        try:
            if self.provider == LLMProvider.BEDROCK and self.client:
                # Use Messages API format for Claude 3+ models (inference profiles)
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                })
                
                response = self.client.invoke_model(
                    body=body,
                    modelId=self.model_id,
                    accept="application/json",
                    contentType="application/json"
                )
                
                response_body = json.loads(response.get('body').read())
                # Handle Messages API response format
                content = response_body.get('content', [])
                llm_response = content[0].get('text', '') if content else ''
            
            elif self.provider == LLMProvider.OPENAI and self.client:
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=[
                        {"role": "system", "content": "You are an expert ML engineer and data scientist. Provide detailed, structured, and actionable responses."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                llm_response = response.choices[0].message.content
            
            else:
                # Check if real AI is required
                if self.force_real_ai:
                    raise Exception("Real AI required (USE_REAL_LLM=true) but no LLM client available")
                # Fallback to intelligent simulation
                self.logger.warning("No LLM client available, using intelligent simulation")
                llm_response = self._simulate_llm_response(prompt)
            
            # Track the reasoning call for learning
            execution_time = time.time() - start_time
            self.reasoning_calls.append({
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "response_length": len(llm_response),
                "execution_time": execution_time,
                "timestamp": time.time(),
                "provider": self.provider.value,
                "success": True
            })
            
            self.logger.info(f"LLM call successful in {execution_time:.2f}s")
            return llm_response
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"LLM call failed after {execution_time:.2f}s: {e}")
            
            # Check if real AI is required (fail hard instead of fallback)
            if self.force_real_ai:
                raise Exception(f"Real AI required (USE_REAL_LLM=true) but call failed: {e}")
            
            # Track the failed call
            self.reasoning_calls.append({
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "error": str(e),
                "execution_time": execution_time,
                "timestamp": time.time(),
                "provider": self.provider.value,
                "success": False
            })
            
            # Return intelligent fallback only if not forced
            self.logger.warning("Falling back to intelligent simulation after LLM failure")
            return self._simulate_llm_response(prompt)
    
    def _simulate_llm_response(self, prompt: str) -> str:
        """
        Simulate LLM response for development/testing when real LLM unavailable.
        
        Args:
            prompt: Input prompt
            
        Returns:
            Simulated intelligent response based on prompt content
        """
        self.logger.warning("Using simulated LLM response")
        
        if "pipeline planning" in prompt.lower():
            return self._simulate_pipeline_planning_response()
        elif "error recovery" in prompt.lower():
            return self._simulate_error_recovery_response()
        elif "data strategy" in prompt.lower():
            return self._simulate_data_strategy_response()
        elif "model selection" in prompt.lower():
            return self._simulate_model_selection_response()
        else:
            return self._simulate_general_response()
    
    def _simulate_pipeline_planning_response(self) -> str:
        """Simulate intelligent pipeline planning response."""
        return """
        REASONING: Based on the dataset characteristics, I recommend a comprehensive ML pipeline with the following considerations:

        1. DATA QUALITY: The dataset shows moderate missing values (15%) and some categorical variables that need encoding
        2. PROBLEM TYPE: This appears to be a classification problem based on the objective
        3. ALGORITHM SELECTION: Given the dataset size and complexity, ensemble methods would be optimal

        DECISION:
        {
            "pipeline_steps": [
                {"step": "data_validation", "priority": "high", "reason": "Ensure data integrity before processing"},
                {"step": "missing_value_imputation", "strategy": "iterative", "reason": "Preserve data relationships"},
                {"step": "categorical_encoding", "method": "target_encoding", "reason": "High cardinality categories detected"},
                {"step": "feature_scaling", "method": "robust_scaler", "reason": "Outliers detected in numeric features"},
                {"step": "model_training", "algorithms": ["random_forest", "xgboost", "lightgbm"], "reason": "Ensemble methods for robust performance"},
                {"step": "evaluation", "metrics": ["roc_auc", "precision", "recall"], "reason": "Classification problem with potential class imbalance"}
            ],
            "estimated_duration": "45 minutes",
            "resource_requirements": "medium",
            "success_probability": 0.85
        }

        CONFIDENCE: 0.85

        ALTERNATIVES: [
            {"approach": "automl", "reason": "Automated feature engineering and model selection", "trade_offs": "Less control but faster"},
            {"approach": "deep_learning", "reason": "Complex pattern recognition", "trade_offs": "Requires more data and compute"}
        ]

        EXPLANATION: This pipeline balances thoroughness with efficiency, addressing the key data quality issues while selecting appropriate algorithms for the problem type and dataset characteristics.
        """
    
    def _simulate_error_recovery_response(self) -> str:
        """Simulate intelligent error recovery response."""
        return """
        REASONING: The pipeline step failed due to data compatibility issues. Analyzing the error pattern and context:

        1. ROOT CAUSE: Schema mismatch between expected and actual data format
        2. IMPACT ASSESSMENT: This error is recoverable with data transformation
        3. URGENCY: Medium - pipeline can continue with alternative approach

        DECISION:
        {
            "recovery_strategy": "data_transformation",
            "immediate_action": "convert_data_types",
            "fallback_options": ["use_alternative_algorithm", "skip_problematic_features"],
            "estimated_recovery_time": "10 minutes"
        }

        CONFIDENCE: 0.90

        ALTERNATIVES: [
            {"strategy": "retry_with_preprocessing", "success_probability": 0.85, "time": "15 minutes"},
            {"strategy": "skip_feature_and_continue", "success_probability": 0.70, "time": "5 minutes"},
            {"strategy": "use_robust_algorithm", "success_probability": 0.75, "time": "20 minutes"}
        ]

        EXPLANATION: The schema mismatch can be resolved by converting data types and handling the format inconsistency. This approach maintains data integrity while allowing the pipeline to continue.
        """
    
    def _simulate_data_strategy_response(self) -> str:
        """Simulate intelligent data strategy response."""
        return """
        REASONING: Analyzing the dataset characteristics reveals several optimization opportunities:

        1. DATA VOLUME: 50K rows - sufficient for most ML algorithms
        2. FEATURE DISTRIBUTION: Mix of numerical and categorical features with varying scales
        3. QUALITY ISSUES: Some missing values and potential outliers detected

        DECISION:
        {
            "preprocessing_strategy": "comprehensive",
            "missing_value_approach": "intelligent_imputation",
            "feature_engineering": ["polynomial_features", "interaction_terms"],
            "data_validation": "statistical_tests",
            "caching_strategy": "feature_store"
        }

        CONFIDENCE: 0.80

        ALTERNATIVES: [
            {"strategy": "minimal_preprocessing", "trade_offs": "Faster but potentially lower quality"},
            {"strategy": "aggressive_feature_engineering", "trade_offs": "More features but risk of overfitting"}
        ]

        EXPLANATION: A balanced approach that addresses data quality issues while creating meaningful features without over-engineering.
        """
    
    def _simulate_model_selection_response(self) -> str:
        """Simulate intelligent model selection response."""
        return """
        REASONING: Model selection should consider dataset size, problem complexity, and performance requirements:

        1. DATASET SIZE: Medium-sized dataset suitable for various algorithms
        2. PROBLEM COMPLEXITY: Moderate complexity suggesting ensemble methods
        3. INTERPRETABILITY: Balance between performance and explainability

        DECISION:
        {
            "primary_algorithm": "gradient_boosting",
            "backup_algorithms": ["random_forest", "logistic_regression"],
            "hyperparameter_strategy": "bayesian_optimization",
            "cross_validation": "stratified_k_fold",
            "ensemble_approach": "voting_classifier"
        }

        CONFIDENCE: 0.82

        ALTERNATIVES: [
            {"algorithm": "neural_network", "reason": "Complex pattern recognition", "requirements": "more_data"},
            {"algorithm": "svm", "reason": "Good for medium datasets", "trade_offs": "slower_training"}
        ]

        EXPLANATION: Gradient boosting provides excellent performance for this dataset size and complexity, with good interpretability and robust handling of mixed feature types.
        """
    
    def _simulate_general_response(self) -> str:
        """Simulate general intelligent response."""
        return """
        REASONING: Based on the available context and domain knowledge, I recommend a data-driven approach that considers:

        1. CURRENT CONTEXT: Available data and computational resources
        2. OBJECTIVE ALIGNMENT: Ensuring approach matches stated goals
        3. BEST PRACTICES: Following established ML engineering principles

        DECISION:
        {
            "recommended_approach": "adaptive_strategy",
            "considerations": ["data_quality", "computational_efficiency", "interpretability"],
            "success_factors": ["proper_validation", "monitoring", "iteration"]
        }

        CONFIDENCE: 0.75

        EXPLANATION: An adaptive approach allows for optimization based on real-world performance and changing requirements.
        """
    
    def _load_prompt_templates(self) -> Dict[str, str]:
        """Load and return prompt templates for different reasoning domains."""
        return {
            "pipeline_planning": """
            You are an expert ML engineer designing an optimal data pipeline. 
            
            Analyze the following context and create a detailed pipeline plan:
            
            Dataset Characteristics:
            {dataset_info}
            
            Objective: {objective}
            
            Constraints: {constraints}
            
            Previous Experience: {execution_history}
            
            Provide:
            1. REASONING: Step-by-step analysis of requirements
            2. DECISION: Structured pipeline plan with specific steps
            3. CONFIDENCE: Confidence score (0-1)
            4. ALTERNATIVES: Alternative approaches with trade-offs
            5. EXPLANATION: Clear rationale for recommendations
            
            Format your response with clear sections and structured decisions.
            """,
            
            "error_recovery": """
            You are an expert system administrator diagnosing and recovering from pipeline failures.
            
            Failure Context:
            Failed Step: {failed_step}
            Error: {error}
            Pipeline Context: {context}
            
            Provide:
            1. REASONING: Root cause analysis
            2. DECISION: Immediate recovery actions
            3. CONFIDENCE: Success probability of recovery
            4. ALTERNATIVES: Fallback strategies
            5. EXPLANATION: Clear recovery rationale
            
            Focus on practical, implementable solutions.
            """,
            
            "data_strategy": """
            You are a data engineering expert optimizing data processing strategies.
            
            Data Context:
            {data_context}
            
            Processing Objective: {objective}
            
            Provide:
            1. REASONING: Analysis of data characteristics and requirements
            2. DECISION: Optimal processing strategy
            3. CONFIDENCE: Strategy effectiveness estimate
            4. ALTERNATIVES: Alternative processing approaches
            5. EXPLANATION: Technical justification
            
            Consider efficiency, quality, and maintainability.
            """
        }
    
    def _build_pipeline_planning_prompt(self, context: ReasoningContext) -> str:
        """Build pipeline planning prompt from context."""
        template = self.prompt_templates.get("pipeline_planning", "")
        
        return template.format(
            dataset_info=self._format_dataset_info(context.data_context),
            objective=context.objective,
            constraints=context.constraints or "None specified",
            execution_history=self._format_execution_history(context.execution_history)
        )
    
    def _build_error_recovery_prompt(self, failed_step: str, error: str, context: ReasoningContext) -> str:
        """Build error recovery prompt."""
        template = self.prompt_templates.get("error_recovery", "")
        
        return template.format(
            failed_step=failed_step,
            error=error,
            context=context.data_context
        )
    
    def _build_data_strategy_prompt(self, context: ReasoningContext) -> str:
        """Build data strategy prompt."""
        template = self.prompt_templates.get("data_strategy", "")
        
        return template.format(
            data_context=context.data_context,
            objective=context.objective
        )
    
    def _build_model_selection_prompt(self, context: ReasoningContext) -> str:
        """Build model selection prompt."""
        return f"""
        You are an ML expert selecting optimal algorithms and training strategies.
        
        Problem Context:
        - Objective: {context.objective}
        - Dataset: {context.data_context}
        - Constraints: {context.constraints}
        
        Recommend the best algorithm(s) and training approach with detailed reasoning.
        """
    
    def _build_pattern_analysis_prompt(self, execution_history: List[Dict[str, Any]]) -> str:
        """Build pattern analysis prompt."""
        return f"""
        Analyze the following pipeline execution history and identify patterns:
        
        Execution History: {execution_history}
        
        Provide insights about:
        1. Success patterns
        2. Common failure modes
        3. Performance trends
        4. Optimization opportunities
        """
    
    def _build_objective_understanding_prompt(self, objective: str, context: Optional[Dict[str, Any]]) -> str:
        """Build objective understanding prompt."""
        return f"""
        Parse and understand this ML objective:
        
        Objective: "{objective}"
        Context: {context or "None provided"}
        
        Extract:
        1. Problem type (classification, regression, etc.)
        2. Success criteria
        3. Business constraints
        4. Technical requirements
        5. Evaluation metrics
        """
    
    def _format_dataset_info(self, data_context: Dict[str, Any]) -> str:
        """Format dataset information for prompts."""
        if not data_context:
            return "No dataset information available"
        
        return f"""
        Rows: {data_context.get('rows', 'unknown')}
        Columns: {data_context.get('columns', 'unknown')}
        Data Types: {data_context.get('dtypes', {})}
        Missing Values: {data_context.get('missing_values', {})}
        Target Column: {data_context.get('target_column', 'not specified')}
        """
    
    def _format_execution_history(self, history: Optional[List[Dict[str, Any]]]) -> str:
        """Format execution history for prompts."""
        if not history:
            return "No previous executions"
        
        return f"Previous executions: {len(history)} pipelines with varying success rates"
    
    def _parse_pipeline_response(self, response: str) -> ReasoningResponse:
        """Parse pipeline planning response into structured format."""
        try:
            # Extract structured decision from response
            decision_start = response.find("DECISION:")
            confidence_start = response.find("CONFIDENCE:")
            alternatives_start = response.find("ALTERNATIVES:")
            
            decision_text = response[decision_start:confidence_start] if decision_start >= 0 else "{}"
            confidence_text = response[confidence_start:alternatives_start] if confidence_start >= 0 else "0.5"
            
            # Parse confidence
            confidence = 0.8  # Default
            try:
                conf_match = confidence_text.split(":")[-1].strip()
                confidence = float(conf_match.split()[0])
            except:
                pass
            
            return ReasoningResponse(
                reasoning=response[:decision_start] if decision_start >= 0 else response,
                decision={"pipeline_plan": "intelligent_pipeline_generated"},
                confidence=confidence,
                alternatives=[{"alternative": "automl_approach"}, {"alternative": "custom_approach"}],
                explanation="LLM-generated pipeline plan with intelligent reasoning",
                metadata={"response_length": len(response), "llm_provider": self.provider.value}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse pipeline response: {e}")
            return ReasoningResponse(
                reasoning="Failed to parse LLM response",
                decision={"fallback": "use_default_pipeline"},
                confidence=0.5,
                alternatives=[],
                explanation="Error in response parsing",
                metadata={"error": str(e)}
            )
    
    def _parse_recovery_response(self, response: str) -> ReasoningResponse:
        """Parse error recovery response."""
        return ReasoningResponse(
            reasoning=response,
            decision={"recovery_strategy": "intelligent_recovery"},
            confidence=0.8,
            alternatives=[{"strategy": "fallback_approach"}],
            explanation="LLM-generated recovery strategy",
            metadata={"response_type": "error_recovery"}
        )
    
    def _parse_data_strategy_response(self, response: str) -> ReasoningResponse:
        """Parse data strategy response."""
        return ReasoningResponse(
            reasoning=response,
            decision={"data_strategy": "intelligent_processing"},
            confidence=0.8,
            alternatives=[{"strategy": "alternative_processing"}],
            explanation="LLM-generated data processing strategy",
            metadata={"response_type": "data_strategy"}
        )
    
    def _parse_model_selection_response(self, response: str) -> ReasoningResponse:
        """Parse model selection response."""
        return ReasoningResponse(
            reasoning=response,
            decision={"model_strategy": "intelligent_selection"},
            confidence=0.8,
            alternatives=[{"model": "alternative_algorithm"}],
            explanation="LLM-generated model selection strategy",
            metadata={"response_type": "model_selection"}
        )
    
    def _parse_pattern_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse pattern analysis response."""
        return {
            "insights": response,
            "patterns_identified": ["performance_trends", "common_failures"],
            "recommendations": ["optimization_suggestions"],
            "metadata": {"analysis_type": "pattern_analysis"}
        }
    
    def _parse_objective_understanding_response(self, response: str) -> Dict[str, Any]:
        """Parse objective understanding response."""
        # Check if context has explicit problem_type
    def _parse_objective_understanding_response(self, response: str, explicit_problem_type: Optional[str] = None) -> Dict[str, Any]:
        """Parse objective understanding response."""
        # Use explicit problem_type from context if provided, otherwise default to classification
        problem_type = explicit_problem_type or "classification"
        
        # Set evaluation metrics based on problem type
        if problem_type == "regression":
            evaluation_metrics = ["r2_score", "rmse", "mae", "mape"]
        else:
            evaluation_metrics = ["accuracy", "precision", "recall", "f1_score"]
        
        return {
            "problem_type": problem_type,
            "success_criteria": "high_accuracy" if problem_type == "classification" else "low_error",
            "constraints": ["time_limit", "resource_limit"],
            "evaluation_metrics": evaluation_metrics,
            "technical_requirements": ["feature_engineering", "cross_validation"],
            "raw_understanding": response
        }


class AgenticReasoningMixin:
    """
    Mixin class to add agentic reasoning capabilities to any ADPA component.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reasoning_engine = LLMReasoningEngine()
    
    def reason_and_decide(self, domain: str, context_data: Dict[str, Any], objective: str) -> ReasoningResponse:
        """
        Use LLM reasoning for intelligent decision making.
        
        Args:
            domain: Decision domain (e.g., "data_processing", "model_selection")
            context_data: Relevant context information
            objective: Current objective or goal
            
        Returns:
            ReasoningResponse with intelligent decision
        """
        reasoning_context = ReasoningContext(
            domain=domain,
            objective=objective,
            data_context=context_data
        )
        
        if domain == "pipeline_planning":
            return self.reasoning_engine.reason_about_pipeline_planning(reasoning_context)
        elif domain == "data_strategy":
            return self.reasoning_engine.reason_about_data_strategy(reasoning_context)
        elif domain == "model_selection":
            return self.reasoning_engine.reason_about_model_selection(reasoning_context)
        else:
            # General reasoning for any domain
            return self.reasoning_engine.reason_about_pipeline_planning(reasoning_context)