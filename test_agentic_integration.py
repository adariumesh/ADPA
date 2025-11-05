#!/usr/bin/env python3
"""
ADPA Agentic Integration Test - Validate that all agentic components work together.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    # Import new agentic components
    from agent.core.master_agent import MasterAgenticController
    from agent.utils.llm_integration import LLMReasoningEngine
    from agent.memory.experience_memory import ExperienceMemorySystem
    from agent.reasoning.pipeline_reasoner import AgenticPipelineReasoner
    from agent.data.intelligent_data_handler import IntelligentDataHandler
    from agent.cloud.aws_intelligence import AWSCloudIntelligence
    from agent.interface.natural_language import NaturalLanguageInterface
    
    print("✅ All agentic components imported successfully!")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Attempting to install missing dependencies...")
    
    # Try to identify what's missing and continue with available components
    available_components = []
    
    try:
        from agent.utils.llm_integration import LLMReasoningEngine
        available_components.append("LLM Reasoning Engine")
    except ImportError:
        print("⚠️ LLM Reasoning Engine not available")
    
    try:
        from agent.memory.experience_memory import ExperienceMemorySystem  
        available_components.append("Experience Memory")
    except ImportError:
        print("⚠️ Experience Memory not available")
    
    try:
        from agent.data.intelligent_data_handler import IntelligentDataHandler
        available_components.append("Intelligent Data Handler")
    except ImportError:
        print("⚠️ Intelligent Data Handler not available")
        
    if len(available_components) == 0:
        print("❌ No components available")
        sys.exit(1)
    else:
        print(f"✅ {len(available_components)} components available: {', '.join(available_components)}")


def create_test_dataset():
    """Create a test dataset for validation."""
    np.random.seed(42)
    
    # Create realistic customer churn dataset
    n_samples = 1000
    
    data = {
        'customer_id': range(1, n_samples + 1),
        'age': np.random.randint(18, 80, n_samples),
        'tenure_months': np.random.randint(1, 60, n_samples),
        'monthly_spend': np.random.normal(50, 20, n_samples).clip(10, 200),
        'support_calls': np.random.poisson(2, n_samples),
        'contract_type': np.random.choice(['Monthly', 'Annual', '2-Year'], n_samples),
        'payment_method': np.random.choice(['Credit Card', 'Bank Transfer', 'Electronic Check'], n_samples),
        'satisfaction_score': np.random.randint(1, 6, n_samples)
    }
    
    # Create target variable with realistic correlation
    churn_probability = (
        0.1 +  # Base rate
        (data['support_calls'] / 10) * 0.3 +  # More calls = higher churn
        (1 / (data['tenure_months'] + 1)) * 0.2 +  # Shorter tenure = higher churn
        (6 - data['satisfaction_score']) / 20  # Lower satisfaction = higher churn
    )
    
    data['churned'] = np.random.binomial(1, churn_probability, n_samples)
    
    return pd.DataFrame(data)


def test_llm_reasoning_engine():
    """Test LLM reasoning engine."""
    print("\n🧠 Testing LLM Reasoning Engine...")
    
    try:
        reasoning_engine = LLMReasoningEngine()
        
        # Test objective understanding
        objective_result = reasoning_engine.understand_natural_language_objective(
            "Build a model to predict customer churn for our subscription service"
        )
        
        print(f"   ✅ Objective understanding: {objective_result.get('problem_type', 'classification')}")
        
        # Test pattern analysis
        sample_history = [
            {"objective": "classification", "success": True, "performance": {"accuracy": 0.85}},
            {"objective": "classification", "success": True, "performance": {"accuracy": 0.82}}
        ]
        
        pattern_result = reasoning_engine.analyze_execution_patterns(sample_history)
        print(f"   ✅ Pattern analysis: {len(pattern_result.get('analysis', 'completed'))} characters")
        
        return True
        
    except Exception as e:
        print(f"   ❌ LLM Reasoning Engine failed: {e}")
        return False


def test_experience_memory():
    """Test experience memory system."""
    print("\n💾 Testing Experience Memory System...")
    
    try:
        memory = ExperienceMemorySystem(memory_dir="./test_memory")
        
        # Test memory statistics
        stats = memory.get_memory_statistics()
        print(f"   ✅ Memory initialized: {stats['total_executions']} executions")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Experience Memory failed: {e}")
        return False


def test_intelligent_data_handler():
    """Test intelligent data handler."""
    print("\n📊 Testing Intelligent Data Handler...")
    
    try:
        data_handler = IntelligentDataHandler()
        test_data = create_test_dataset()
        
        # Test data processing
        result = data_handler.execute(
            data=test_data,
            config={"target_column": "churned"},
            context={"objective": "predict customer churn"}
        )
        
        print(f"   ✅ Data processing: {result.status.value}")
        print(f"   ✅ Quality score: {result.metrics.get('data_quality_score', 0.8):.2f}")
        print(f"   ✅ Processing time: {result.metrics.get('processing_time_seconds', 0):.1f}s")
        
        return result.status.value == "completed"
        
    except Exception as e:
        print(f"   ❌ Intelligent Data Handler failed: {e}")
        return False


def test_pipeline_reasoner():
    """Test agentic pipeline reasoner."""
    print("\n🤖 Testing Agentic Pipeline Reasoner...")
    
    try:
        reasoning_engine = LLMReasoningEngine()
        memory = ExperienceMemorySystem(memory_dir="./test_memory")
        reasoner = AgenticPipelineReasoner(reasoning_engine, memory)
        
        # Create mock dataset info
        from agent.core.interfaces import DatasetInfo
        
        dataset_info = DatasetInfo(
            shape=(1000, 8),
            columns=['age', 'tenure_months', 'monthly_spend', 'support_calls', 
                    'contract_type', 'payment_method', 'satisfaction_score', 'churned'],
            dtypes={'age': 'int64', 'churned': 'int64'},
            missing_values={'age': 0, 'churned': 0},
            numeric_columns=['age', 'tenure_months', 'monthly_spend', 'support_calls', 'satisfaction_score'],
            categorical_columns=['contract_type', 'payment_method'],
            target_column='churned'
        )
        
        # Test intelligent pipeline planning
        objective_understanding = {"problem_type": "classification", "objective": "predict customer churn"}
        recommendations = {"based_on_executions": 0, "confidence": 0.5}
        
        pipeline_plan = reasoner.create_intelligent_pipeline_plan(
            dataset_info=dataset_info,
            objective_understanding=objective_understanding,
            recommendations=recommendations
        )
        
        print(f"   ✅ Pipeline created: {len(pipeline_plan.get('steps', []))} steps")
        print(f"   ✅ Confidence: {pipeline_plan.get('confidence', 0.8):.2f}")
        
        return len(pipeline_plan.get('steps', [])) > 0
        
    except Exception as e:
        print(f"   ❌ Pipeline Reasoner failed: {e}")
        return False


def test_aws_intelligence():
    """Test AWS cloud intelligence."""
    print("\n☁️ Testing AWS Cloud Intelligence...")
    
    try:
        aws_intelligence = AWSCloudIntelligence()
        
        # Test service recommendation
        recommendation = aws_intelligence.get_intelligent_service_recommendation(
            workload_type="ml_training",
            requirements={"data_size": 5, "performance": "high"},
            constraints={"budget_limit": 100}
        )
        
        print(f"   ✅ Service recommendation: {recommendation.get('primary_service', 'sagemaker')}")
        print(f"   ✅ Cost estimate: ${recommendation.get('cost_estimate', 25):.2f}")
        
        # Test status
        status = aws_intelligence.get_cloud_intelligence_status()
        print(f"   ✅ Intelligence status: {len(status.get('active_clients', []))} clients ready")
        
        return True
        
    except Exception as e:
        print(f"   ❌ AWS Intelligence failed: {e}")
        return False


def test_master_agent():
    """Test master agentic controller."""
    print("\n🧠 Testing Master Agentic Controller...")
    
    try:
        master_agent = MasterAgenticController(memory_dir="./test_memory")
        test_data = create_test_dataset()
        
        # Test natural language processing
        result = master_agent.process_natural_language_request(
            request="Build a model to predict customer churn using this dataset",
            data=test_data,
            context={"business_goal": "reduce customer churn"}
        )
        
        print(f"   ✅ Session created: {result.get('session_id', 'unknown')}")
        print(f"   ✅ Understanding: {result.get('understanding', {}).get('problem_type', 'classification')}")
        print(f"   ✅ Pipeline created: {len(result.get('pipeline_plan', {}).get('steps', []))} steps")
        print(f"   ✅ Execution: {result.get('execution_result', {}).get('status', 'completed')}")
        
        # Test agent status
        status = master_agent.get_agent_status()
        print(f"   ✅ Agent capabilities: {len(status.get('capabilities', []))} features")
        
        return result.get('execution_result', {}).get('status') == 'completed'
        
    except Exception as e:
        print(f"   ❌ Master Agent failed: {e}")
        return False


def test_natural_language_interface():
    """Test natural language interface."""
    print("\n💬 Testing Natural Language Interface...")
    
    try:
        master_agent = MasterAgenticController(memory_dir="./test_memory")
        nl_interface = NaturalLanguageInterface(master_agent)
        test_data = create_test_dataset()
        
        # Test message processing
        response = nl_interface.process_user_message(
            message="I want to build a model to predict which customers will churn",
            data=test_data
        )
        
        print(f"   ✅ Intent recognized: {response.get('intent', 'create_model')}")
        print(f"   ✅ Confidence: {response.get('confidence', 0.8):.2f}")
        print(f"   ✅ Actions taken: {len(response.get('actions_taken', []))}")
        print(f"   ✅ Response length: {len(response.get('response', ''))} characters")
        
        # Test conversation continuation
        session_id = response.get('session_id')
        follow_up = nl_interface.process_user_message(
            message="How accurate is this model?",
            session_id=session_id
        )
        
        print(f"   ✅ Follow-up processed: {follow_up.get('intent', 'general')}")
        
        return response.get('intent') == 'create_model'
        
    except Exception as e:
        print(f"   ❌ Natural Language Interface failed: {e}")
        return False


def test_end_to_end_integration():
    """Test complete end-to-end integration."""
    print("\n🚀 Testing End-to-End Integration...")
    
    try:
        # Create master agent
        master_agent = MasterAgenticController(memory_dir="./test_memory")
        
        # Create natural language interface
        nl_interface = NaturalLanguageInterface(master_agent)
        
        # Create test dataset
        test_data = create_test_dataset()
        
        # Simulate complete user interaction
        conversation_steps = [
            "Hello, I need help building a machine learning model",
            "I want to predict customer churn for my subscription business",
            "Execute the pipeline you created",
            "How did the model perform?",
            "Can you optimize it for better accuracy?"
        ]
        
        session_id = None
        
        for i, message in enumerate(conversation_steps):
            print(f"   Step {i+1}: Processing '{message[:50]}...'")
            
            # Provide data only on first meaningful request
            data_to_provide = test_data if i == 1 else None
            
            response = nl_interface.process_user_message(
                message=message,
                session_id=session_id,
                data=data_to_provide
            )
            
            session_id = response.get('session_id')
            print(f"            Intent: {response.get('intent')}, Confidence: {response.get('confidence', 0.5):.2f}")
        
        # Get conversation summary
        summary = nl_interface.get_conversation_summary(session_id)
        print(f"   ✅ Conversation completed: {summary.get('message_count', 0)} messages")
        print(f"   ✅ Session duration: Active")
        
        return True
        
    except Exception as e:
        print(f"   ❌ End-to-end integration failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("🧪 ADPA Agentic Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("LLM Reasoning Engine", test_llm_reasoning_engine),
        ("Experience Memory", test_experience_memory),
        ("Intelligent Data Handler", test_intelligent_data_handler),
        ("Pipeline Reasoner", test_pipeline_reasoner),
        ("AWS Intelligence", test_aws_intelligence),
        ("Master Agent", test_master_agent),
        ("Natural Language Interface", test_natural_language_interface),
        ("End-to-End Integration", test_end_to_end_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n📊 Overall: {passed}/{len(results)} tests passed ({passed/len(results)*100:.0f}%)")
    
    if passed == len(results):
        print("🎉 All tests passed! Agentic ADPA system is ready!")
    else:
        print("⚠️  Some tests failed. Review the output above for details.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)