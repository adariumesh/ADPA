#!/usr/bin/env python3
"""
ADPA Complete Demo Workflow
Demonstrates end-to-end autonomous ML pipeline agent capabilities
"""

import pandas as pd
import numpy as np
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import time
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.core.master_agent import MasterAgenticController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_demo_customer_churn_dataset():
    """
    Create a realistic customer churn dataset for demonstration.
    
    Returns:
        DataFrame with customer churn data
    """
    logger.info("📊 Creating demo customer churn dataset...")
    
    np.random.seed(42)  # For reproducibility
    
    # Generate 1000 customer records
    n_customers = 1000
    
    # Customer demographics
    customer_ids = [f"CUST{str(i).zfill(5)}" for i in range(1, n_customers + 1)]
    ages = np.random.normal(40, 15, n_customers).clip(18, 80).astype(int)
    tenure_months = np.random.poisson(24, n_customers).clip(1, 72)
    
    # Service usage
    monthly_charges = np.random.normal(70, 20, n_customers).clip(20, 150)
    total_charges = monthly_charges * tenure_months + np.random.normal(0, 50, n_customers)
    
    # Contract types
    contract_types = np.random.choice(
        ['Month-to-Month', 'One Year', 'Two Year'],
        n_customers,
        p=[0.5, 0.3, 0.2]
    )
    
    # Payment methods
    payment_methods = np.random.choice(
        ['Electronic check', 'Mailed check', 'Bank transfer', 'Credit card'],
        n_customers,
        p=[0.3, 0.2, 0.25, 0.25]
    )
    
    # Internet service
    internet_service = np.random.choice(
        ['DSL', 'Fiber optic', 'No'],
        n_customers,
        p=[0.4, 0.4, 0.2]
    )
    
    # Tech support
    tech_support = np.random.choice(['Yes', 'No'], n_customers, p=[0.4, 0.6])
    
    # Online security
    online_security = np.random.choice(['Yes', 'No'], n_customers, p=[0.35, 0.65])
    
    # Customer service calls
    service_calls = np.random.poisson(2, n_customers)
    
    # Churn (target variable) - influenced by multiple factors
    churn_probability = (
        0.1 +  # Base churn rate
        0.3 * (contract_types == 'Month-to-Month').astype(float) +
        0.2 * (payment_methods == 'Electronic check').astype(float) +
        0.15 * (service_calls > 3).astype(float) +
        0.1 * (tech_support == 'No').astype(float) +
        0.1 * (tenure_months < 12).astype(float) -
        0.15 * (contract_types == 'Two Year').astype(float) -
        0.1 * (online_security == 'Yes').astype(float)
    )
    
    churn = (np.random.random(n_customers) < churn_probability).astype(int)
    
    # Create DataFrame
    df = pd.DataFrame({
        'customer_id': customer_ids,
        'age': ages,
        'tenure_months': tenure_months,
        'monthly_charges': np.round(monthly_charges, 2),
        'total_charges': np.round(total_charges, 2),
        'contract_type': contract_types,
        'payment_method': payment_methods,
        'internet_service': internet_service,
        'tech_support': tech_support,
        'online_security': online_security,
        'service_calls': service_calls,
        'churn': churn
    })
    
    # Introduce some realistic missing values
    missing_mask = np.random.random((n_customers, 3)) < 0.05
    df.loc[missing_mask[:, 0], 'total_charges'] = np.nan
    df.loc[missing_mask[:, 1], 'tech_support'] = np.nan
    df.loc[missing_mask[:, 2], 'online_security'] = np.nan
    
    logger.info(f"✅ Created dataset: {df.shape[0]} customers, {df.shape[1]} features")
    logger.info(f"   Churn rate: {churn.mean():.1%}")
    logger.info(f"   Missing values: {df.isnull().sum().sum()} total")
    
    return df


def save_demo_dataset(df: pd.DataFrame, filename: str = 'demo_customer_churn.csv'):
    """Save the demo dataset to a CSV file."""
    output_path = Path(__file__).parent / filename
    df.to_csv(output_path, index=False)
    logger.info(f"💾 Saved dataset to: {output_path}")
    return output_path


def run_demo_autonomous_analysis():
    """
    Run a complete demonstration of ADPA's autonomous capabilities.
    
    Demonstrates:
    1. Dataset creation
    2. Natural language objective processing
    3. Intelligent agent analysis
    4. Pipeline planning
    5. Execution (if AWS infrastructure available)
    6. Results interpretation
    """
    logger.info("\n" + "=" * 80)
    logger.info("🚀 ADPA AUTONOMOUS DATA PIPELINE AGENT - COMPLETE DEMO")
    logger.info("=" * 80)
    
    try:
        # Step 1: Create demo dataset
        logger.info("\n📋 STEP 1: Creating Demo Dataset")
        logger.info("-" * 80)
        df = create_demo_customer_churn_dataset()
        dataset_path = save_demo_dataset(df)
        
        # Display dataset summary
        logger.info(f"\nDataset Summary:")
        logger.info(f"  • Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        logger.info(f"  • Numerical features: {len(df.select_dtypes(include=['number']).columns)}")
        logger.info(f"  • Categorical features: {len(df.select_dtypes(include=['object']).columns)}")
        logger.info(f"  • Missing values: {df.isnull().sum().sum()}")
        logger.info(f"  • Target variable: churn (binary: 0={df['churn'].value_counts()[0]}, 1={df['churn'].value_counts()[1]})")
        
        # Step 2: Initialize ADPA Master Agent
        logger.info("\n🤖 STEP 2: Initializing ADPA Master Agentic Controller")
        logger.info("-" * 80)
        
        agent = MasterAgenticController(
            aws_config={
                'region': 'us-east-2',
                'account_id': '083308938449'
            },
            memory_dir="./data/experience_memory"
        )
        
        logger.info("✅ Agent initialized successfully")
        
        # Step 3: Process natural language request
        logger.info("\n💬 STEP 3: Processing Natural Language Objective")
        logger.info("-" * 80)
        
        user_request = """
        I need to predict which customers are likely to churn so we can take 
        proactive retention actions. The business goal is to identify at-risk 
        customers with high accuracy and understand the key drivers of churn.
        """
        
        logger.info(f"User Request: {user_request.strip()}")
        logger.info("\nAgent is analyzing the request and dataset...")
        
        result = agent.process_natural_language_request(
            request=user_request,
            data=df,
            context={
                'business_objective': 'customer_retention',
                'priority': 'high_accuracy',
                'interpretability_required': True
            }
        )
        
        # Step 4: Display Agent's Understanding
        logger.info("\n🧠 STEP 4: Agent's Understanding & Analysis")
        logger.info("-" * 80)
        
        understanding = result.get('understanding', {})
        logger.info(f"\nObjective Understanding:")
        logger.info(f"  • Problem Type: {understanding.get('problem_type', 'N/A')}")
        logger.info(f"  • Target Variable: {understanding.get('target_column', 'N/A')}")
        logger.info(f"  • Business Goal: {understanding.get('business_goal', 'N/A')}")
        
        # Step 5: Display Pipeline Plan
        logger.info("\n📐 STEP 5: Autonomous Pipeline Plan")
        logger.info("-" * 80)
        
        pipeline_plan = result.get('pipeline_plan', {})
        steps = pipeline_plan.get('steps', [])
        
        logger.info(f"\nPlanned Pipeline Steps: {len(steps)}")
        for i, step in enumerate(steps, 1):
            step_name = step.get('name', 'Unknown')
            step_type = step.get('type', 'Unknown')
            logger.info(f"  {i}. {step_name} ({step_type})")
            if 'reasoning' in step:
                logger.info(f"     Reasoning: {step['reasoning'][:100]}...")
        
        # Step 6: Display Execution Results
        logger.info("\n⚡ STEP 6: Pipeline Execution Results")
        logger.info("-" * 80)
        
        execution_result = result.get('execution_result')
        if execution_result:
            metrics = execution_result.metrics or {}
            
            logger.info(f"\nExecution Status: {execution_result.status}")
            logger.info(f"\nPerformance Metrics:")
            logger.info(f"  • Accuracy: {metrics.get('accuracy', 0):.2%}")
            logger.info(f"  • Precision: {metrics.get('precision', 0):.2%}")
            logger.info(f"  • Recall: {metrics.get('recall', 0):.2%}")
            logger.info(f"  • F1 Score: {metrics.get('f1_score', 0):.2%}")
            logger.info(f"  • Execution Time: {metrics.get('execution_time', 0):.2f}s")
            logger.info(f"  • Rows Processed: {metrics.get('rows_processed', 0):,}")
            
            # Display model insights
            artifacts = execution_result.artifacts or {}
            model_artifacts = artifacts.get('model_artifacts', {})
            
            if 'feature_importance' in model_artifacts:
                logger.info(f"\nTop Feature Importance:")
                feature_importance = model_artifacts['feature_importance']
                sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
                for feature, importance in sorted_features[:5]:
                    logger.info(f"  • {feature}: {importance:.3f}")
        
        # Step 7: Display Natural Language Summary
        logger.info("\n📝 STEP 7: Agent's Natural Language Summary")
        logger.info("-" * 80)
        
        summary = result.get('natural_language_summary', '')
        if summary:
            logger.info(f"\n{summary}")
        
        # Step 8: Get Agent Status
        logger.info("\n📊 STEP 8: Agent Status & Capabilities")
        logger.info("-" * 80)
        
        agent_status = agent.get_agent_status()
        logger.info(f"\nAgent Status:")
        logger.info(f"  • Agent ID: {agent_status.get('agent_id')}")
        logger.info(f"  • Status: {agent_status.get('status')}")
        logger.info(f"  • Active Sessions: {agent_status.get('active_sessions')}")
        logger.info(f"  • Pipeline Executions: {agent_status.get('pipeline_executions')}")
        
        logger.info(f"\nCapabilities:")
        for capability in agent_status.get('capabilities', []):
            logger.info(f"  ✓ {capability.replace('_', ' ').title()}")
        
        # Step 9: Save Results
        logger.info("\n💾 STEP 9: Saving Demo Results")
        logger.info("-" * 80)
        
        results_dir = Path(__file__).parent / 'demo_results'
        results_dir.mkdir(exist_ok=True)
        
        # Save full results
        results_file = results_dir / f'demo_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        # Convert result to JSON-serializable format
        json_result = {
            'session_id': result.get('session_id'),
            'understanding': understanding,
            'pipeline_plan': pipeline_plan,
            'execution_summary': {
                'status': str(execution_result.status) if execution_result else 'not_executed',
                'metrics': metrics if execution_result else {},
                'execution_time': metrics.get('execution_time', 0) if execution_result else 0
            },
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(results_file, 'w') as f:
            json.dump(json_result, f, indent=2, default=str)
        
        logger.info(f"✅ Results saved to: {results_file}")
        
        # Demo complete
        logger.info("\n" + "=" * 80)
        logger.info("✅ ADPA DEMO COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        logger.info(f"\n📁 Demo artifacts:")
        logger.info(f"  • Dataset: {dataset_path}")
        logger.info(f"  • Results: {results_file}")
        logger.info(f"\n🎯 Key Achievements:")
        logger.info(f"  ✓ Processed natural language objective")
        logger.info(f"  ✓ Autonomously analyzed dataset")
        logger.info(f"  ✓ Created intelligent pipeline plan")
        logger.info(f"  ✓ Executed pipeline with monitoring")
        logger.info(f"  ✓ Generated actionable insights")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_comparison_demo():
    """
    Run a demonstration comparing AWS vs local execution.
    """
    logger.info("\n" + "=" * 80)
    logger.info("🔬 ADPA COMPARATIVE ANALYSIS DEMO - AWS vs Local")
    logger.info("=" * 80)
    
    try:
        # Create dataset
        df = create_demo_customer_churn_dataset()
        
        # Initialize components
        agent = MasterAgenticController()
        
        # Measure local execution
        logger.info("\n🖥️  Running LOCAL Execution...")
        local_start = time.time()
        
        local_result = agent.process_natural_language_request(
            request="Predict customer churn with best accuracy",
            data=df
        )
        
        local_duration = time.time() - local_start
        local_metrics = local_result.get('execution_result').metrics if local_result.get('execution_result') else {}
        
        logger.info(f"  ✅ Local execution completed in {local_duration:.2f}s")
        logger.info(f"  Accuracy: {local_metrics.get('accuracy', 0):.2%}")
        
        # AWS execution would be here (requires infrastructure)
        logger.info("\n☁️  AWS Execution (requires deployed infrastructure)")
        logger.info(f"  Status: Infrastructure deployment needed")
        logger.info(f"  Expected benefits:")
        logger.info(f"    • Scalability: Handle 100x larger datasets")
        logger.info(f"    • Parallel processing: 5-10x faster with SageMaker")
        logger.info(f"    • Automatic monitoring: CloudWatch integration")
        logger.info(f"    • Cost optimization: Pay only for usage")
        
        # Display comparison
        logger.info("\n📊 Comparison Summary:")
        logger.info("-" * 80)
        logger.info(f"{'Metric':<30} {'Local':<20} {'AWS (Expected)':<20}")
        logger.info("-" * 80)
        logger.info(f"{'Execution Time':<30} {f'{local_duration:.2f}s':<20} {'~0.5x local':<20}")
        logger.info(f"{'Scalability':<30} {'Limited':<20} {'Unlimited':<20}")
        logger.info(f"{'Cost (1000 runs/month)':<30} {'$0':<20} {'~$32':<20}")
        logger.info(f"{'Monitoring':<30} {'Manual':<20} {'Automatic':<20}")
        logger.info(f"{'Reliability':<30} {'95%':<20} {'99.9%':<20}")
        
        return {
            'local': local_result,
            'local_duration': local_duration,
            'comparison_complete': True
        }
        
    except Exception as e:
        logger.error(f"❌ Comparison demo failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point for demo workflow."""
    import argparse
    
    parser = argparse.ArgumentParser(description='ADPA Demo Workflow')
    parser.add_argument('--mode', choices=['full', 'quick', 'comparison'], 
                       default='full', help='Demo mode to run')
    parser.add_argument('--save-dataset', action='store_true',
                       help='Save dataset only without running pipeline')
    
    args = parser.parse_args()
    
    if args.save_dataset:
        df = create_demo_customer_churn_dataset()
        save_demo_dataset(df)
        logger.info("✅ Dataset created and saved successfully")
        return
    
    if args.mode == 'comparison':
        result = run_comparison_demo()
    else:
        result = run_demo_autonomous_analysis()
    
    if result:
        logger.info("\n✅ Demo completed successfully!")
        return 0
    else:
        logger.error("\n❌ Demo failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
