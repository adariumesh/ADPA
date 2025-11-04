#!/usr/bin/env python3
"""
ADPA AWS Integration Demo Script

This script demonstrates the key AWS integrations:
1. S3 data upload/download
2. Lambda function execution
3. Step Functions workflow orchestration
4. Real-time monitoring

Usage:
    python demo_aws_integration.py --dataset path/to/dataset.csv --bucket your-bucket-name
"""

import argparse
import logging
import os
import sys
import time
import pandas as pd
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.aws.s3.client import S3Client
from src.aws.stepfunctions.orchestrator import StepFunctionsOrchestrator
from src.agent.core.agent import ADPAAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ADPADemoRunner:
    """
    Demonstration runner for ADPA AWS integration.
    """
    
    def __init__(self, bucket_name: str, aws_region: str = "us-east-1"):
        """
        Initialize demo runner.
        
        Args:
            bucket_name: S3 bucket name for demo
            aws_region: AWS region to use
        """
        self.bucket_name = bucket_name
        self.aws_region = aws_region
        
        # Initialize AWS clients
        self.s3_client = S3Client(bucket_name=bucket_name, region=aws_region)
        self.sfn_orchestrator = StepFunctionsOrchestrator(region=aws_region)
        
        # Initialize ADPA agent
        self.agent = ADPAAgent()
        
        logger.info(f"ADPA Demo initialized for bucket: {bucket_name}")
    
    def run_complete_demo(self, dataset_path: str):
        """
        Run the complete ADPA demo showcasing all AWS integrations.
        
        Args:
            dataset_path: Path to the dataset file
        """
        print("\n" + "="*60)
        print("🤖 ADPA AWS Integration Demo")
        print("="*60)
        
        try:
            # Step 1: Validate and prepare environment
            print("\n📋 Step 1: Environment Setup")
            self._validate_environment()
            
            # Step 2: Load and analyze dataset locally
            print("\n📊 Step 2: Local Dataset Analysis")
            dataset = self._load_and_analyze_dataset(dataset_path)
            
            # Step 3: Upload dataset to S3
            print("\n☁️  Step 3: S3 Data Upload")
            s3_key = self._upload_to_s3(dataset, dataset_path)
            
            # Step 4: Create Step Functions workflow
            print("\n🔄 Step 4: Step Functions Workflow Creation")
            workflow_arn = self._create_workflow()
            
            # Step 5: Execute workflow
            print("\n🚀 Step 5: Execute AWS Pipeline")
            execution_result = self._execute_pipeline(s3_key, workflow_arn)
            
            # Step 6: Monitor execution
            print("\n📈 Step 6: Monitor Pipeline Execution")
            self._monitor_execution(execution_result)
            
            # Step 7: Retrieve and analyze results
            print("\n📋 Step 7: Results Analysis")
            self._analyze_results()
            
            # Step 8: Cost analysis
            print("\n💰 Step 8: Cost Analysis")
            self._analyze_costs()
            
            print("\n✅ Demo completed successfully!")
            self._print_aws_console_links()
            
        except Exception as e:
            logger.error(f"Demo failed: {str(e)}")
            print(f"\n❌ Demo failed: {str(e)}")
            raise
    
    def _validate_environment(self):
        """Validate AWS environment and credentials."""
        print("   Checking AWS credentials...")
        
        # Test S3 access
        try:
            bucket_info = self.s3_client.get_bucket_info()
            if bucket_info:
                print(f"   ✅ S3 access confirmed - Bucket: {self.bucket_name}")
            else:
                print(f"   ⚠️  Creating S3 bucket: {self.bucket_name}")
                self.s3_client.create_bucket_if_not_exists()
        except Exception as e:
            print(f"   ❌ S3 access failed: {str(e)}")
            raise
        
        # Test Step Functions access
        try:
            workflows = self.sfn_orchestrator.list_workflows()
            print(f"   ✅ Step Functions access confirmed - Found {len(workflows)} existing workflows")
        except Exception as e:
            print(f"   ❌ Step Functions access failed: {str(e)}")
            raise
        
        print("   ✅ Environment validation complete")
    
    def _load_and_analyze_dataset(self, dataset_path: str) -> pd.DataFrame:
        """Load and analyze dataset locally."""
        print(f"   Loading dataset: {dataset_path}")
        
        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")
        
        # Load dataset
        if dataset_path.endswith('.csv'):
            dataset = pd.read_csv(dataset_path)
        else:
            raise ValueError("Only CSV datasets are supported in this demo")
        
        # Basic analysis
        print(f"   ✅ Dataset loaded: {dataset.shape[0]} rows, {dataset.shape[1]} columns")
        print(f"   📊 Memory usage: {dataset.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
        
        # Show basic statistics
        missing_values = dataset.isnull().sum().sum()
        print(f"   📈 Missing values: {missing_values}")
        print(f"   📈 Numeric columns: {len(dataset.select_dtypes(include=['number']).columns)}")
        print(f"   📈 Text columns: {len(dataset.select_dtypes(include=['object']).columns)}")
        
        return dataset
    
    def _upload_to_s3(self, dataset: pd.DataFrame, original_path: str) -> str:
        """Upload dataset to S3."""
        print("   Uploading dataset to S3...")
        
        # Generate S3 key
        timestamp = int(time.time())
        filename = os.path.basename(original_path)
        s3_key = f"demo/{timestamp}/{filename}"
        
        # Upload with metadata
        metadata = {
            'upload-timestamp': str(timestamp),
            'original-path': original_path,
            'rows': str(len(dataset)),
            'columns': str(len(dataset.columns)),
            'demo-session': 'adpa-integration-demo'
        }
        
        result = self.s3_client.upload_dataset(dataset, s3_key, metadata=metadata)
        
        if result.status.value == "completed":
            print(f"   ✅ Upload successful: s3://{self.bucket_name}/{s3_key}")
            print(f"   📊 Size: {result.metrics['upload_size_bytes'] / 1024:.2f} KB")
            return s3_key
        else:
            raise Exception(f"S3 upload failed: {result.errors}")
    
    def _create_workflow(self) -> str:
        """Create Step Functions workflow."""
        print("   Creating Step Functions workflow...")
        
        workflow_name = f"adpa-demo-workflow-{int(time.time())}"
        
        # Note: In a real implementation, you would deploy the Lambda function first
        # For this demo, we'll use a placeholder ARN
        lambda_arn = f"arn:aws:lambda:{self.aws_region}:123456789012:function:adpa-data-processor"
        
        result = self.sfn_orchestrator.create_adpa_workflow(
            workflow_name=workflow_name,
            lambda_function_arn=lambda_arn,
            s3_bucket=self.bucket_name
        )
        
        if result.status.value == "completed":
            workflow_arn = result.metrics['state_machine_arn']
            print(f"   ✅ Workflow created: {workflow_name}")
            print(f"   🔗 Console URL: {result.artifacts.get('console_url', 'N/A')}")
            return workflow_arn
        else:
            raise Exception(f"Workflow creation failed: {result.errors}")
    
    def _execute_pipeline(self, s3_key: str, workflow_arn: str) -> dict:
        """Execute the AWS pipeline."""
        print("   Starting pipeline execution...")
        
        # Prepare execution input
        execution_input = {
            "input_key": s3_key,
            "output_prefix": f"results/{int(time.time())}",
            "pipeline_config": {
                "data_quality_threshold": 0.7,
                "enable_monitoring": True
            }
        }
        
        result = self.sfn_orchestrator.execute_workflow(
            state_machine_arn=workflow_arn,
            input_data=execution_input
        )
        
        if result.status.value == "completed":
            execution_arn = result.metrics['execution_arn']
            print(f"   ✅ Pipeline execution started")
            print(f"   🔗 Console URL: {result.artifacts.get('console_url', 'N/A')}")
            return {
                'execution_arn': execution_arn,
                'input_data': execution_input
            }
        else:
            raise Exception(f"Pipeline execution failed: {result.errors}")
    
    def _monitor_execution(self, execution_result: dict):
        """Monitor pipeline execution in real-time."""
        execution_arn = execution_result['execution_arn']
        print(f"   Monitoring execution: {execution_arn}")
        
        max_wait = 300  # 5 minutes max
        check_interval = 10  # Check every 10 seconds
        elapsed = 0
        
        while elapsed < max_wait:
            status_info = self.sfn_orchestrator.monitor_execution(execution_arn)
            
            if 'error' in status_info:
                print(f"   ❌ Monitoring error: {status_info['error']}")
                break
            
            status = status_info['status']
            print(f"   📊 Status: {status} (elapsed: {elapsed}s)")
            
            if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                print(f"   ✅ Execution completed with status: {status}")
                if 'duration_seconds' in status_info:
                    print(f"   ⏱️  Total duration: {status_info['duration_seconds']:.2f} seconds")
                break
            
            time.sleep(check_interval)
            elapsed += check_interval
        
        if elapsed >= max_wait:
            print(f"   ⚠️  Monitoring timeout after {max_wait} seconds")
    
    def _analyze_results(self):
        """Analyze pipeline results."""
        print("   Analyzing pipeline results...")
        
        # List processed files in S3
        datasets = self.s3_client.list_datasets(prefix="results/")
        
        if datasets:
            print(f"   ✅ Found {len(datasets)} result files:")
            for dataset in datasets[:5]:  # Show first 5
                print(f"      📄 {dataset['key']} ({dataset['size']} bytes)")
        else:
            print("   ⚠️  No result files found")
        
        # In a real implementation, you would download and analyze the results
        print("   📊 Results analysis would include:")
        print("      - Data quality improvements")
        print("      - Feature engineering results")
        print("      - Model performance metrics")
        print("      - Processing time breakdown")
    
    def _analyze_costs(self):
        """Analyze estimated AWS costs."""
        print("   Calculating estimated AWS costs...")
        
        # Simplified cost calculation (real implementation would use AWS Cost Explorer API)
        estimated_costs = {
            'S3 Storage': 0.023,  # $0.023 per GB
            'Lambda Executions': 0.05,  # Based on execution time
            'Step Functions': 0.025,  # Per state transition
            'Data Transfer': 0.01,  # Minimal for demo
            'Total': 0.108
        }
        
        print("   💰 Estimated costs for this demo session:")
        for service, cost in estimated_costs.items():
            print(f"      {service}: ${cost:.3f}")
        
        print(f"   💡 Cost efficiency insights:")
        print(f"      - Serverless architecture minimizes idle costs")
        print(f"      - Pay-per-use model scales with data volume")
        print(f"      - Managed services reduce operational overhead")
    
    def _print_aws_console_links(self):
        """Print useful AWS console links."""
        print("\n🔗 AWS Console Links:")
        print(f"   S3 Bucket: https://s3.console.aws.amazon.com/s3/buckets/{self.bucket_name}")
        print(f"   Step Functions: https://{self.aws_region}.console.aws.amazon.com/states/home?region={self.aws_region}")
        print(f"   CloudWatch Logs: https://{self.aws_region}.console.aws.amazon.com/cloudwatch/home?region={self.aws_region}#logsV2:")
        print(f"   Lambda Functions: https://{self.aws_region}.console.aws.amazon.com/lambda/home?region={self.aws_region}#/functions")


def create_sample_dataset(output_path: str = "sample_data.csv"):
    """Create a sample dataset for demonstration."""
    import numpy as np
    
    # Create sample data
    np.random.seed(42)
    n_samples = 1000
    
    data = {
        'age': np.random.randint(18, 80, n_samples),
        'income': np.random.normal(50000, 15000, n_samples),
        'education': np.random.choice(['High School', 'Bachelor', 'Master', 'PhD'], n_samples),
        'experience': np.random.randint(0, 40, n_samples),
        'score': np.random.normal(75, 15, n_samples),
        'category': np.random.choice(['A', 'B', 'C'], n_samples)
    }
    
    # Add some missing values
    missing_indices = np.random.choice(n_samples, size=int(n_samples * 0.05), replace=False)
    data['income'][missing_indices] = np.nan
    
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"Sample dataset created: {output_path}")
    return output_path


def main():
    """Main demo function."""
    parser = argparse.ArgumentParser(description='ADPA AWS Integration Demo')
    parser.add_argument('--dataset', type=str, help='Path to dataset CSV file')
    parser.add_argument('--bucket', type=str, required=True, help='S3 bucket name')
    parser.add_argument('--region', type=str, default='us-east-1', help='AWS region')
    parser.add_argument('--create-sample', action='store_true', help='Create sample dataset')
    
    args = parser.parse_args()
    
    # Create sample dataset if requested
    if args.create_sample:
        dataset_path = create_sample_dataset()
    elif args.dataset:
        dataset_path = args.dataset
    else:
        print("Error: Either provide --dataset or use --create-sample")
        return
    
    # Run demo
    try:
        demo_runner = ADPADemoRunner(bucket_name=args.bucket, aws_region=args.region)
        demo_runner.run_complete_demo(dataset_path)
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        print(f"\n❌ Demo failed. Check your AWS credentials and permissions.")
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())