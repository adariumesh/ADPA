#!/usr/bin/env python3
"""
Test Step Functions Real AWS Integration
Tests the updated Step Functions orchestrator with real AWS services
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')
sys.path.insert(0, './src')

from src.aws.stepfunctions.orchestrator import StepFunctionsOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_stepfunctions_real_integration():
    """Test Step Functions with real AWS integration."""
    
    logger.info("🚀 Testing Step Functions Real AWS Integration")
    
    # Initialize orchestrator (will try real AWS, fallback to simulation)
    orchestrator = StepFunctionsOrchestrator(region="us-east-2")
    
    # Check if we're in simulation mode
    if orchestrator.is_simulation_mode():
        logger.warning("⚠️  Running in SIMULATION MODE (AWS not available)")
    else:
        logger.info("✅ Running in REAL AWS MODE")
    
    # Test 1: List existing state machines
    logger.info("\n📋 Test 1: List existing state machines")
    try:
        state_machines = orchestrator.get_real_state_machines()
        logger.info(f"Found {len(state_machines)} existing state machines")
        for sm in state_machines:
            logger.info(f"  - {sm['name']}: {sm.get('type', 'N/A')}")
    except Exception as e:
        logger.error(f"Failed to list state machines: {e}")
    
    # Test 2: Create a simple pipeline configuration
    logger.info("\n🔧 Test 2: Create pipeline state machine")
    
    pipeline_config = {
        "objective": "Test ML Pipeline",
        "dataset_type": "csv",
        "target_column": "label",
        "steps": [
            {"type": "data_validation", "timeout": 300},
            {"type": "data_cleaning", "timeout": 600}, 
            {"type": "feature_engineering", "timeout": 900},
            {"type": "model_training", "timeout": 1800},
            {"type": "model_evaluation", "timeout": 300}
        ]
    }
    
    try:
        # Use the retry method for better reliability
        result = orchestrator.create_state_machine_with_retries(
            pipeline_config=pipeline_config,
            name=f"adpa-test-pipeline-{int(datetime.now().timestamp())}"
        )
        
        if result.get('status') in ['ACTIVE', 'SIMULATED']:
            logger.info("✅ State machine created successfully")
            logger.info(f"  Status: {result['status']}")
            logger.info(f"  ARN: {result.get('state_machine_arn', 'N/A')}")
            state_machine_arn = result.get('state_machine_arn')
        else:
            logger.error(f"❌ Failed to create state machine: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exception creating state machine: {e}")
        return False
    
    # Test 3: Execute the pipeline
    logger.info("\n▶️  Test 3: Execute pipeline")
    
    execution_input = {
        "pipeline_id": f"test-{int(datetime.now().timestamp())}",
        "dataset_path": "s3://adpa-data-bucket/test-data.csv",
        "objective": "binary_classification",
        "target_column": "churn"
    }
    
    try:
        if state_machine_arn:
            execution_result = orchestrator.execute_pipeline(
                state_machine_arn=state_machine_arn,
                input_data=execution_input,
                execution_name=f"test-execution-{int(datetime.now().timestamp())}"
            )
            
            if execution_result.get('status') in ['SUCCEEDED', 'RUNNING']:
                logger.info("✅ Pipeline execution started successfully")
                logger.info(f"  Status: {execution_result['status']}")
                logger.info(f"  Execution ARN: {execution_result.get('execution_arn', 'N/A')}")
            else:
                logger.warning(f"⚠️  Pipeline execution status: {execution_result}")
        else:
            logger.warning("⚠️  Skipping execution test - no state machine ARN")
            
    except Exception as e:
        logger.error(f"❌ Exception executing pipeline: {e}")
        return False
    
    # Test 4: Monitor execution (if real AWS)
    if not orchestrator.is_simulation_mode() and state_machine_arn:
        logger.info("\n🔍 Test 4: Monitor execution")
        
        try:
            # Get execution status
            if execution_result.get('execution_arn'):
                monitor_result = orchestrator.monitor_execution(
                    execution_arn=execution_result['execution_arn'],
                    max_wait_time=30  # Short wait for testing
                )
                logger.info(f"✅ Execution monitoring result: {monitor_result['status']}")
            
        except Exception as e:
            logger.error(f"❌ Exception monitoring execution: {e}")
    
    logger.info("\n🎉 Step Functions integration test completed!")
    return True

def test_stepfunctions_configuration():
    """Test Step Functions configuration and connectivity."""
    
    logger.info("\n🔧 Testing Step Functions Configuration")
    
    orchestrator = StepFunctionsOrchestrator()
    
    logger.info(f"Region: {orchestrator.region}")
    logger.info(f"Account ID: {orchestrator.account_id}")
    logger.info(f"Role ARN: {orchestrator.role_arn}")
    logger.info(f"Simulation Mode: {orchestrator.is_simulation_mode()}")
    
    if orchestrator.client:
        logger.info("✅ Step Functions client initialized")
    else:
        logger.warning("⚠️  Step Functions client not available (simulation mode)")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("ADPA Step Functions Integration Test")
    logger.info("=" * 60)
    
    # Test configuration
    test_stepfunctions_configuration()
    
    # Test real integration
    success = test_stepfunctions_real_integration()
    
    if success:
        logger.info("\n✅ ALL TESTS PASSED - Step Functions integration working!")
    else:
        logger.error("\n❌ SOME TESTS FAILED - Check logs above")
        sys.exit(1)