"""
ADPA Pipeline Planning Module

This module provides intelligent ML pipeline planning capabilities including:
- Automatic dataset profiling
- Intelligent pipeline step generation
- Resource estimation
- Alternative approach suggestions

Example usage:
    from src.agent.planning import PipelinePlanner, DataProfiler, StepFactory
    
    # Create a pipeline plan
    planner = PipelinePlanner()
    plan = planner.plan_pipeline(data, objective="classification", target_column="Churn")
    
    # Execute the plan
    steps = StepFactory.create_steps_from_plan(plan.steps)
"""

from .pipeline_planner import (
    PipelinePlanner,
    PipelinePlan,
    PlannerConfig,
    PipelineComplexity,
    DataProfiler
)

from .pipeline_steps import (
    BaseStep,
    DataValidationStep,
    MissingValueImputationStep,
    OutlierDetectionStep,
    CategoricalEncodingStep,
    FeatureScalingStep,
    FeatureEngineeringStep,
    FeatureSelectionStep,
    TrainTestSplitStep,
    ModelTrainingStep,
    ModelEvaluationStep,
    ReportGenerationStep,
    StepFactory
)

__all__ = [
    # Planner classes
    'PipelinePlanner',
    'PipelinePlan',
    'PlannerConfig',
    'PipelineComplexity',
    'DataProfiler',
    
    # Step implementations
    'BaseStep',
    'DataValidationStep',
    'MissingValueImputationStep',
    'OutlierDetectionStep',
    'CategoricalEncodingStep',
    'FeatureScalingStep',
    'FeatureEngineeringStep',
    'FeatureSelectionStep',
    'TrainTestSplitStep',
    'ModelTrainingStep',
    'ModelEvaluationStep',
    'ReportGenerationStep',
    'StepFactory'
]
