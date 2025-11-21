"""
ADPA Agent Module - Agentic Architecture

This module contains the new agentic components for the Autonomous Data Pipeline Agent.
"""

# New agentic components
from .core.master_agent import MasterAgenticController
from .core.interfaces import PipelineStep, ExecutionResult, DatasetInfo, StepStatus
from .utils.llm_integration import LLMReasoningEngine, AgenticReasoningMixin
from .memory.experience_memory import ExperienceMemorySystem
from .reasoning.pipeline_reasoner import AgenticPipelineReasoner
from .data.intelligent_data_handler import IntelligentDataHandler
from .cloud.aws_intelligence import AWSCloudIntelligence
from .interface.natural_language import NaturalLanguageInterface

# Legacy components that still exist
from .execution.executor import StepExecutor
from .memory.manager import MemoryManager

__all__ = [
    # New agentic components
    'MasterAgenticController',
    'LLMReasoningEngine', 
    'AgenticReasoningMixin',
    'ExperienceMemorySystem',
    'AgenticPipelineReasoner',
    'IntelligentDataHandler',
    'AWSCloudIntelligence',
    'NaturalLanguageInterface',
    
    # Core interfaces
    'PipelineStep',
    'ExecutionResult', 
    'DatasetInfo',
    'StepStatus',
    
    # Legacy components
    'StepExecutor',
    'MemoryManager'
]