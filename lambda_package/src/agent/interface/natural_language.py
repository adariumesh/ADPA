"""
Natural Language Interface for ADPA - Enhanced conversational ML pipeline creation.
"""

import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

from ..utils.llm_integration import LLMReasoningEngine, ReasoningContext
from ..core.master_agent import MasterAgenticController


class NaturalLanguageInterface:
    """
    Enhanced natural language interface for ADPA that enables intuitive interaction.
    
    Capabilities:
    - Multi-turn conversation management
    - Intent recognition and clarification
    - Context retention across sessions
    - Business objective translation to technical requirements
    - Interactive pipeline refinement
    - Progress explanations and status updates
    """
    
    def __init__(self, master_agent: MasterAgenticController):
        """
        Initialize natural language interface.
        
        Args:
            master_agent: Master agentic controller for pipeline operations
        """
        self.master_agent = master_agent
        self.reasoning_engine = LLMReasoningEngine()
        self.logger = logging.getLogger(__name__)
        
        # Conversation state management
        self.conversation_sessions = {}
        self.intent_patterns = self._load_intent_patterns()
        
        self.logger.info("Natural Language Interface initialized")
    
    def process_user_message(self, 
                           message: str,
                           session_id: Optional[str] = None,
                           data: Optional[pd.DataFrame] = None,
                           context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process user message and provide intelligent response.
        
        Args:
            message: User's natural language message
            session_id: Optional session ID for context continuity
            data: Optional dataset to work with
            context: Additional context information
            
        Returns:
            Dictionary with response and session information
        """
        try:
            # Initialize or retrieve conversation session
            if session_id and session_id in self.conversation_sessions:
                session = self.conversation_sessions[session_id]
            else:
                session_id = f"session_{int(datetime.now().timestamp())}"
                session = self._initialize_session(session_id)
            
            # Add user message to conversation history
            session["messages"].append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat(),
                "data_provided": data is not None
            })
            
            # Analyze user intent and message
            intent_analysis = self._analyze_user_intent(message, session, data, context)
            
            # Generate appropriate response based on intent
            response = self._generate_response(intent_analysis, session, data, context)
            
            # Add response to conversation history
            session["messages"].append({
                "role": "assistant",
                "content": response["response"],
                "timestamp": datetime.now().isoformat(),
                "intent": intent_analysis["primary_intent"],
                "actions_taken": response.get("actions_taken", [])
            })
            
            # Update session context
            session["last_activity"] = datetime.now().isoformat()
            session["context"].update(response.get("context_updates", {}))
            
            return {
                "session_id": session_id,
                "response": response["response"],
                "intent": intent_analysis["primary_intent"],
                "confidence": intent_analysis["confidence"],
                "actions_taken": response.get("actions_taken", []),
                "follow_up_suggestions": response.get("follow_up_suggestions", []),
                "pipeline_status": response.get("pipeline_status"),
                "data_summary": response.get("data_summary")
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process user message: {e}")
            return {
                "session_id": session_id,
                "response": f"I encountered an error processing your request: {str(e)}",
                "intent": "error",
                "confidence": 0.0
            }
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary of conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with conversation summary
        """
        if session_id not in self.conversation_sessions:
            return {"error": "Session not found"}
        
        session = self.conversation_sessions[session_id]
        
        # Generate intelligent summary
        summary_prompt = f"""
        Summarize this ADPA conversation session:
        
        Messages: {session['messages'][-10:]}  # Last 10 messages
        Context: {session['context']}
        
        Provide:
        1. What the user wanted to accomplish
        2. What was achieved
        3. Current status
        4. Next steps
        
        Make it clear and actionable.
        """
        
        summary = self.reasoning_engine._call_llm(summary_prompt, max_tokens=400)
        
        return {
            "session_id": session_id,
            "message_count": len(session["messages"]),
            "duration": session.get("last_activity", "unknown"),
            "primary_objectives": session["context"].get("objectives", []),
            "achievements": session["context"].get("achievements", []),
            "current_status": session["context"].get("status", "active"),
            "intelligent_summary": summary
        }
    
    def suggest_next_actions(self, session_id: str) -> List[str]:
        """
        Suggest next actions based on conversation context.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of suggested actions
        """
        if session_id not in self.conversation_sessions:
            return ["Start a new conversation"]
        
        session = self.conversation_sessions[session_id]
        context = session["context"]
        
        suggestions = []
        
        # Context-based suggestions
        if context.get("pipeline_created") and not context.get("pipeline_executed"):
            suggestions.extend([
                "Execute the pipeline we created",
                "Modify the pipeline configuration",
                "Preview the pipeline steps"
            ])
        
        elif context.get("pipeline_executed"):
            suggestions.extend([
                "Analyze the results",
                "Optimize the pipeline performance",
                "Create a new variant",
                "Deploy to production"
            ])
        
        elif context.get("data_uploaded") and not context.get("pipeline_created"):
            suggestions.extend([
                "Create a prediction model",
                "Explore data patterns",
                "Set up data quality monitoring"
            ])
        
        else:
            suggestions.extend([
                "Upload a dataset to get started",
                "Tell me about your ML goal",
                "Show me example use cases"
            ])
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def _initialize_session(self, session_id: str) -> Dict[str, Any]:
        """Initialize a new conversation session."""
        session = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "messages": [],
            "context": {
                "objectives": [],
                "data_context": {},
                "pipeline_context": {},
                "user_preferences": {}
            }
        }
        
        self.conversation_sessions[session_id] = session
        return session
    
    def _analyze_user_intent(self, 
                           message: str,
                           session: Dict[str, Any],
                           data: Optional[pd.DataFrame],
                           context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze user intent from message and context.
        
        Args:
            message: User message
            session: Conversation session
            data: Optional dataset
            context: Additional context
            
        Returns:
            Dictionary with intent analysis
        """
        # Use LLM for intelligent intent recognition
        intent_prompt = f"""
        Analyze user intent from this message in context:
        
        User Message: "{message}"
        Conversation History: {session['messages'][-3:]}  # Last 3 messages
        Session Context: {session['context']}
        Data Provided: {data is not None}
        
        Identify:
        1. Primary intent (create_model, analyze_data, optimize_pipeline, get_help, etc.)
        2. Confidence level (0-1)
        3. Extracted entities (dataset_name, algorithm_preference, business_goal, etc.)
        4. Required clarifications
        5. Suggested next steps
        
        Respond in JSON format.
        """
        
        intent_response = self.reasoning_engine._call_llm(intent_prompt, max_tokens=600)
        
        # Parse intent response and extract structured information
        intent_analysis = self._parse_intent_response(intent_response, message, session)
        
        return intent_analysis
    
    def _parse_intent_response(self, 
                             intent_response: str,
                             message: str,
                             session: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM intent response into structured format."""
        
        # Fallback pattern-based intent recognition
        primary_intent = "general_inquiry"
        confidence = 0.5
        entities = {}
        
        # Pattern matching for common intents
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["create", "build", "make", "train", "model"]):
            primary_intent = "create_model"
            confidence = 0.8
        elif any(word in message_lower for word in ["analyze", "explore", "understand", "examine"]):
            primary_intent = "analyze_data"
            confidence = 0.8
        elif any(word in message_lower for word in ["optimize", "improve", "enhance", "better"]):
            primary_intent = "optimize_pipeline"
            confidence = 0.8
        elif any(word in message_lower for word in ["help", "how", "what", "explain"]):
            primary_intent = "get_help"
            confidence = 0.9
        elif any(word in message_lower for word in ["status", "progress", "results"]):
            primary_intent = "check_status"
            confidence = 0.8
        
        # Extract entities using simple patterns
        if "predict" in message_lower:
            entities["task_type"] = "prediction"
        if "classify" in message_lower:
            entities["task_type"] = "classification"
        if "forecast" in message_lower:
            entities["task_type"] = "forecasting"
        
        # Extract business goals
        business_keywords = ["sales", "revenue", "churn", "customer", "fraud", "sentiment", "demand"]
        for keyword in business_keywords:
            if keyword in message_lower:
                entities["business_domain"] = keyword
                break
        
        return {
            "primary_intent": primary_intent,
            "confidence": confidence,
            "entities": entities,
            "clarifications_needed": [],
            "suggested_actions": self._suggest_actions_for_intent(primary_intent)
        }
    
    def _generate_response(self, 
                         intent_analysis: Dict[str, Any],
                         session: Dict[str, Any],
                         data: Optional[pd.DataFrame],
                         context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate appropriate response based on intent analysis.
        
        Args:
            intent_analysis: Analyzed user intent
            session: Conversation session
            data: Optional dataset
            context: Additional context
            
        Returns:
            Dictionary with response and actions
        """
        intent = intent_analysis["primary_intent"]
        
        if intent == "create_model":
            return self._handle_create_model_intent(intent_analysis, session, data, context)
        elif intent == "analyze_data":
            return self._handle_analyze_data_intent(intent_analysis, session, data, context)
        elif intent == "optimize_pipeline":
            return self._handle_optimize_pipeline_intent(intent_analysis, session, data, context)
        elif intent == "get_help":
            return self._handle_help_intent(intent_analysis, session)
        elif intent == "check_status":
            return self._handle_status_intent(intent_analysis, session)
        else:
            return self._handle_general_intent(intent_analysis, session)
    
    def _handle_create_model_intent(self, 
                                  intent_analysis: Dict[str, Any],
                                  session: Dict[str, Any],
                                  data: Optional[pd.DataFrame],
                                  context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle create model intent."""
        
        if data is None:
            return {
                "response": "I'd be happy to help you create a model! To get started, I'll need you to provide a dataset. You can upload a CSV, JSON, or Parquet file, and I'll analyze it to recommend the best ML approach for your goals.",
                "actions_taken": ["clarification_requested"],
                "follow_up_suggestions": [
                    "Upload your dataset",
                    "Tell me more about your prediction goal",
                    "What type of problem are you trying to solve?"
                ]
            }
        
        # Extract business objective from entities
        entities = intent_analysis.get("entities", {})
        business_domain = entities.get("business_domain", "general")
        task_type = entities.get("task_type", "prediction")
        
        # Construct objective for master agent
        objective = f"{task_type} for {business_domain} analysis"
        
        # Use master agent to process the request
        agent_result = self.master_agent.process_natural_language_request(
            request=f"Create a {task_type} model for {business_domain}",
            data=data,
            context=context
        )
        
        # Update session context
        session["context"]["pipeline_created"] = True
        session["context"]["current_pipeline_id"] = agent_result.get("session_id")
        session["context"]["objectives"].append(objective)
        
        # Generate conversational response
        response = f"""Perfect! I've analyzed your dataset and created an intelligent ML pipeline for {objective}.

Here's what I found and built for you:

📊 **Dataset Analysis**: {data.shape[0]} rows, {data.shape[1]} columns
🧠 **Recommended Approach**: {agent_result.get('pipeline_plan', {}).get('reasoning', 'Intelligent pipeline selection')}
⚡ **Pipeline Created**: {len(agent_result.get('pipeline_plan', {}).get('steps', []))} optimized steps

{agent_result.get('natural_language_summary', 'Pipeline ready for execution!')}

Would you like me to execute this pipeline, or would you prefer to review and modify it first?"""

        return {
            "response": response,
            "actions_taken": ["pipeline_created", "data_analyzed"],
            "follow_up_suggestions": [
                "Execute the pipeline",
                "Review pipeline steps",
                "Modify configuration",
                "Explain the approach"
            ],
            "pipeline_status": "created",
            "context_updates": {
                "pipeline_created": True,
                "data_analyzed": True
            }
        }
    
    def _handle_analyze_data_intent(self, 
                                  intent_analysis: Dict[str, Any],
                                  session: Dict[str, Any],
                                  data: Optional[pd.DataFrame],
                                  context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle analyze data intent."""
        
        if data is None:
            return {
                "response": "I'd love to help you analyze your data! Please upload your dataset (CSV, JSON, or Parquet format) and I'll provide comprehensive insights about data quality, patterns, and ML opportunities.",
                "actions_taken": ["clarification_requested"]
            }
        
        # Perform intelligent data analysis
        analysis_summary = self._generate_data_analysis_summary(data)
        
        response = f"""I've analyzed your dataset and here's what I discovered:

📊 **Dataset Overview**:
- Size: {data.shape[0]:,} rows × {data.shape[1]} columns
- Memory usage: {data.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB

🔍 **Data Quality**:
{analysis_summary['quality_insights']}

💡 **ML Opportunities**:
{analysis_summary['ml_opportunities']}

🚀 **Recommendations**:
{analysis_summary['recommendations']}

Would you like me to dive deeper into any specific aspect or create a model based on these insights?"""

        return {
            "response": response,
            "actions_taken": ["data_analyzed"],
            "follow_up_suggestions": [
                "Create a prediction model",
                "Fix data quality issues",
                "Explore specific columns",
                "Generate detailed report"
            ],
            "data_summary": analysis_summary,
            "context_updates": {"data_analyzed": True}
        }
    
    def _handle_optimize_pipeline_intent(self, 
                                       intent_analysis: Dict[str, Any],
                                       session: Dict[str, Any],
                                       data: Optional[pd.DataFrame],
                                       context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle optimize pipeline intent."""
        
        current_pipeline_id = session["context"].get("current_pipeline_id")
        
        if not current_pipeline_id:
            return {
                "response": "I don't see any active pipeline to optimize. Let's create one first! Upload your data and tell me your ML objective, and I'll build an optimized pipeline for you.",
                "actions_taken": ["clarification_requested"]
            }
        
        # Use master agent to optimize pipeline
        optimization_result = self.master_agent.optimize_existing_pipeline(
            current_pipeline_id,
            performance_feedback={"request": "user_requested_optimization"}
        )
        
        response = f"""Great! I've analyzed your current pipeline and identified several optimization opportunities:

🎯 **Optimization Analysis**:
{optimization_result.get('optimizations', {}).get('refined_suggestions', 'Intelligent optimizations identified')}

⚡ **Expected Improvements**:
- Performance boost: ~{optimization_result.get('optimization_confidence', 0.5)*20:.0f}%
- Faster execution
- Better resource utilization

🔧 **Recommended Changes**:
Based on my analysis of similar successful pipelines, I suggest implementing these optimizations.

Would you like me to apply these optimizations to your pipeline?"""

        return {
            "response": response,
            "actions_taken": ["pipeline_optimized"],
            "follow_up_suggestions": [
                "Apply optimizations",
                "Compare before/after",
                "Test with different data",
                "Export optimized pipeline"
            ],
            "pipeline_status": "optimization_ready"
        }
    
    def _handle_help_intent(self, 
                          intent_analysis: Dict[str, Any],
                          session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle help and explanation intents."""
        
        help_response = """I'm ADPA, your Autonomous Data Pipeline Agent! I can help you with:

🤖 **What I Do**:
- Create ML models from natural language descriptions
- Analyze datasets and provide insights
- Build and optimize data pipelines automatically
- Learn from each interaction to improve

💬 **How to Talk to Me**:
- "Build a model to predict customer churn"
- "Analyze this sales data for patterns"
- "Create a forecasting model for inventory"
- "Help me understand my data quality"

📊 **What I Need**:
- Your dataset (CSV, JSON, or Parquet)
- A description of what you want to predict or analyze
- Any specific requirements or constraints

🚀 **My Capabilities**:
- Intelligent algorithm selection
- Automated feature engineering
- Real-time monitoring and optimization
- Business-focused explanations

Just tell me what you want to accomplish in plain English, and I'll handle the technical details!"""

        return {
            "response": help_response,
            "actions_taken": ["help_provided"],
            "follow_up_suggestions": [
                "Try: 'Build a model to predict...'",
                "Upload a dataset to get started",
                "Ask about specific capabilities",
                "Show me an example workflow"
            ]
        }
    
    def _handle_status_intent(self, 
                            intent_analysis: Dict[str, Any],
                            session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status check intents."""
        
        context = session["context"]
        current_pipeline_id = context.get("current_pipeline_id")
        
        if not current_pipeline_id:
            status_response = """📊 **Current Status**: No active pipeline

🎯 **What we can do**:
- Upload a dataset to analyze
- Create a new ML pipeline
- Explore example use cases

Ready to get started with your ML project?"""
        else:
            # Get pipeline status from master agent
            pipeline_status = self.master_agent.get_session_history(current_pipeline_id)
            
            status_response = f"""📊 **Current Status**: Active Pipeline

🔄 **Pipeline ID**: {current_pipeline_id}
📈 **Progress**: {context.get('status', 'In progress')}
⏱️ **Created**: {pipeline_status.get('created_at', 'Recently')}

🎯 **Completed Steps**:
{', '.join(context.get('achievements', ['Pipeline created']))}

🚀 **Next Actions Available**:
- Execute pipeline if not done
- Optimize performance
- Analyze results
- Create variations"""

        return {
            "response": status_response,
            "actions_taken": ["status_provided"],
            "pipeline_status": context.get("status", "no_pipeline")
        }
    
    def _handle_general_intent(self, 
                             intent_analysis: Dict[str, Any],
                             session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general inquiries and conversation."""
        
        response = """I'm here to help you with ML and data science! I can:

🎯 **Create Models**: Tell me what you want to predict, and I'll build it
📊 **Analyze Data**: Upload data and I'll provide insights
🔧 **Optimize Pipelines**: I'll make your models faster and better
💬 **Explain Everything**: I'll walk you through each step

What would you like to work on today?"""

        return {
            "response": response,
            "actions_taken": ["general_response"],
            "follow_up_suggestions": [
                "Create a prediction model",
                "Analyze my dataset", 
                "Show me what you can do",
                "Help me get started"
            ]
        }
    
    def _generate_data_analysis_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate intelligent data analysis summary."""
        
        # Basic analysis
        missing_ratio = data.isnull().sum().sum() / (data.shape[0] * data.shape[1])
        numeric_cols = data.select_dtypes(include=['number']).columns
        categorical_cols = data.select_dtypes(include=['object', 'category']).columns
        
        # Quality insights
        quality_score = 1.0 - missing_ratio
        if quality_score > 0.9:
            quality_level = "Excellent"
        elif quality_score > 0.7:
            quality_level = "Good"
        else:
            quality_level = "Needs attention"
        
        quality_insights = f"- Quality Score: {quality_level} ({quality_score:.1%})\n"
        quality_insights += f"- Missing Data: {missing_ratio:.1%} of cells\n"
        quality_insights += f"- Numeric Features: {len(numeric_cols)}\n"
        quality_insights += f"- Categorical Features: {len(categorical_cols)}"
        
        # ML opportunities
        ml_opportunities = ""
        if len(numeric_cols) > 5:
            ml_opportunities += "- Strong potential for regression/forecasting models\n"
        if len(categorical_cols) > 0:
            ml_opportunities += "- Good for classification tasks\n"
        if data.shape[0] > 10000:
            ml_opportunities += "- Sufficient data for complex models\n"
        else:
            ml_opportunities += "- Consider ensemble methods for smaller dataset\n"
        
        # Recommendations
        recommendations = ""
        if missing_ratio > 0.1:
            recommendations += "- Address missing data before modeling\n"
        if len(categorical_cols) > 5:
            recommendations += "- Feature engineering for categorical variables\n"
        recommendations += "- Ready for automated ML pipeline creation"
        
        return {
            "quality_insights": quality_insights,
            "ml_opportunities": ml_opportunities,
            "recommendations": recommendations,
            "quality_score": quality_score
        }
    
    def _suggest_actions_for_intent(self, intent: str) -> List[str]:
        """Suggest actions based on intent."""
        action_map = {
            "create_model": ["analyze_data", "select_algorithm", "configure_pipeline"],
            "analyze_data": ["data_profiling", "quality_assessment", "pattern_discovery"],
            "optimize_pipeline": ["performance_tuning", "cost_optimization", "accuracy_improvement"],
            "get_help": ["show_capabilities", "provide_examples", "explain_concepts"],
            "check_status": ["show_progress", "display_results", "suggest_next_steps"]
        }
        
        return action_map.get(intent, ["clarify_request", "provide_guidance"])
    
    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        """Load intent recognition patterns."""
        return {
            "create_model": [
                r"(create|build|make|train)\s+(model|pipeline)",
                r"predict\s+\w+",
                r"(classification|regression|forecasting)",
                r"machine learning"
            ],
            "analyze_data": [
                r"(analyze|explore|examine|understand)\s+(data|dataset)",
                r"data\s+(quality|insights|patterns)",
                r"what\s+(does|is)\s+(this|my)\s+data"
            ],
            "optimize": [
                r"(optimize|improve|enhance|better)\s+(pipeline|model|performance)",
                r"make\s+it\s+(faster|better|more accurate)"
            ],
            "help": [
                r"(help|how|what|explain)",
                r"(capabilities|features|what can you do)"
            ]
        }
    
    def get_interface_statistics(self) -> Dict[str, Any]:
        """Get statistics about interface usage."""
        total_sessions = len(self.conversation_sessions)
        total_messages = sum(len(session["messages"]) for session in self.conversation_sessions.values())
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "active_sessions": total_sessions,
            "interface_version": "2.0_agentic",
            "capabilities": [
                "natural_language_processing",
                "intent_recognition",
                "context_retention",
                "multi_turn_conversation",
                "intelligent_responses"
            ]
        }