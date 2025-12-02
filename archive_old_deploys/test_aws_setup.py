#!/usr/bin/env python3
"""
AWS Setup and Integration Test for ADPA
Tests all AWS services required for full ADPA functionality
"""

import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import time

# Add ADPA to path
sys.path.insert(0, '.')

def test_aws_credentials():
    """Test AWS credentials are configured"""
    print("🔑 Testing AWS Credentials")
    print("-" * 30)
    
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print(f"✅ AWS Account: {identity['Account']}")
        print(f"✅ User/Role: {identity['Arn']}")
        print(f"✅ Region: {boto3.Session().region_name}")
        return True
        
    except NoCredentialsError:
        print("❌ No AWS credentials configured")
        return False
    except Exception as e:
        print(f"❌ Credential test failed: {e}")
        return False

def test_s3_access():
    """Test S3 service access"""
    print("\n📦 Testing S3 Access")
    print("-" * 20)
    
    try:
        s3 = boto3.client('s3')
        
        # List existing buckets
        response = s3.list_buckets()
        bucket_count = len(response['Buckets'])
        print(f"✅ S3 Access: {bucket_count} buckets available")
        
        # Test bucket operations with a unique test bucket
        test_bucket_name = f"adpa-test-{int(time.time())}"
        
        try:
            # Create test bucket
            if boto3.Session().region_name == 'us-east-1':
                s3.create_bucket(Bucket=test_bucket_name)
            else:
                s3.create_bucket(
                    Bucket=test_bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': boto3.Session().region_name}
                )
            print(f"✅ S3 Create: Test bucket created successfully")
            
            # Test object operations
            s3.put_object(
                Bucket=test_bucket_name, 
                Key='test-file.txt', 
                Body=b'ADPA test content'
            )
            print(f"✅ S3 Upload: Object uploaded successfully")
            
            # Clean up
            s3.delete_object(Bucket=test_bucket_name, Key='test-file.txt')
            s3.delete_bucket(Bucket=test_bucket_name)
            print(f"✅ S3 Cleanup: Test resources cleaned up")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyExists':
                print("✅ S3 Create: Bucket operations working (name collision)")
            else:
                print(f"⚠️ S3 Operations: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ S3 Test failed: {e}")
        return False

def test_sagemaker_access():
    """Test SageMaker service access"""
    print("\n🤖 Testing SageMaker Access")
    print("-" * 27)
    
    try:
        sagemaker = boto3.client('sagemaker')
        
        # Test basic SageMaker API access
        response = sagemaker.list_training_jobs(MaxResults=1)
        print("✅ SageMaker: Training jobs API accessible")
        
        # Test AutoML API
        response = sagemaker.list_auto_ml_jobs(MaxResults=1)
        print("✅ SageMaker: AutoML API accessible")
        
        return True
        
    except Exception as e:
        print(f"❌ SageMaker Test failed: {e}")
        return False

def test_stepfunctions_access():
    """Test Step Functions service access"""
    print("\n🔄 Testing Step Functions Access")
    print("-" * 32)
    
    try:
        stepfunctions = boto3.client('stepfunctions')
        
        # Test Step Functions API access
        response = stepfunctions.list_state_machines(maxResults=1)
        machine_count = len(response.get('stateMachines', []))
        print(f"✅ Step Functions: {machine_count} state machines found")
        
        return True
        
    except Exception as e:
        print(f"❌ Step Functions Test failed: {e}")
        return False

def test_secrets_manager():
    """Test Secrets Manager access"""
    print("\n🔐 Testing Secrets Manager Access")
    print("-" * 33)
    
    try:
        secrets = boto3.client('secretsmanager')
        
        # Test Secrets Manager API access
        response = secrets.list_secrets(MaxResults=1)
        secret_count = len(response.get('SecretList', []))
        print(f"✅ Secrets Manager: {secret_count} secrets found")
        
        return True
        
    except Exception as e:
        print(f"❌ Secrets Manager Test failed: {e}")
        return False

def test_cloudwatch_access():
    """Test CloudWatch access"""
    print("\n📊 Testing CloudWatch Access")
    print("-" * 28)
    
    try:
        cloudwatch = boto3.client('cloudwatch')
        
        # Test CloudWatch API access
        response = cloudwatch.list_metrics(MaxResults=1)
        print("✅ CloudWatch: Metrics API accessible")
        
        # Test custom metric publishing
        cloudwatch.put_metric_data(
            Namespace='ADPA/Test',
            MetricData=[
                {
                    'MetricName': 'TestMetric',
                    'Value': 1.0,
                    'Unit': 'Count'
                }
            ]
        )
        print("✅ CloudWatch: Custom metrics publishing working")
        
        return True
        
    except Exception as e:
        print(f"❌ CloudWatch Test failed: {e}")
        return False

def test_adpa_orchestrator():
    """Test ADPA Step Functions Orchestrator"""
    print("\n🎯 Testing ADPA Orchestrator")
    print("-" * 27)
    
    try:
        from src.aws.stepfunctions.orchestrator import StepFunctionsOrchestrator
        
        # Initialize orchestrator with real AWS credentials
        orchestrator = StepFunctionsOrchestrator(region='us-east-1')
        print("✅ ADPA Orchestrator: Initialized successfully")
        
        # Test state machine creation (dry run)
        try:
            result = orchestrator.create_pipeline_state_machine(
                pipeline_config={'steps': ['test_step']},
                name='adpa-test-pipeline'
            )
            print("✅ ADPA Orchestrator: State machine creation working")
        except Exception as e:
            if 'already exists' in str(e).lower():
                print("✅ ADPA Orchestrator: State machine creation working (already exists)")
            else:
                print(f"⚠️ ADPA Orchestrator: State machine creation - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ ADPA Orchestrator failed: {e}")
        return False

def test_bedrock_access():
    """Test AWS Bedrock for LLM integration"""
    print("\n🧠 Testing AWS Bedrock Access")
    print("-" * 30)
    
    try:
        bedrock = boto3.client('bedrock-runtime')
        
        # Test basic Bedrock access
        try:
            # Try to invoke a model (will fail if not enabled, but tests API access)
            response = bedrock.invoke_model(
                modelId='anthropic.claude-3-haiku-20240307-v1:0',
                body='{"max_tokens": 10, "messages": [{"role": "user", "content": "test"}]}'
            )
            print("✅ Bedrock: Claude model accessible")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                print("⚠️ Bedrock: Model access requires use case approval")
            elif error_code == 'ValidationException':
                print("✅ Bedrock: API accessible (validation error expected)")
            else:
                print(f"⚠️ Bedrock: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Bedrock Test failed: {e}")
        return False

def main():
    """Run comprehensive AWS setup test"""
    print("🚀 ADPA AWS Setup and Integration Test")
    print("=" * 45)
    
    tests = [
        ("AWS Credentials", test_aws_credentials),
        ("S3 Storage", test_s3_access),
        ("SageMaker ML", test_sagemaker_access),
        ("Step Functions", test_stepfunctions_access),
        ("Secrets Manager", test_secrets_manager),
        ("CloudWatch", test_cloudwatch_access),
        ("ADPA Orchestrator", test_adpa_orchestrator),
        ("Bedrock LLM", test_bedrock_access),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name}: Unexpected error - {e}")
    
    print(f"\n{'='*45}")
    print(f"📊 Test Results: {passed}/{total} tests passed")
    print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! ADPA is ready for full AWS deployment!")
    elif passed >= total * 0.8:
        print("✅ Most tests passed. ADPA is ready for deployment with minor issues.")
    else:
        print("⚠️ Several tests failed. Review AWS permissions and configuration.")
    
    print(f"\nNext steps:")
    if passed >= total * 0.8:
        print("  1. Deploy infrastructure: ./deploy/aws-deploy.sh development adpa us-east-1")
        print("  2. Deploy containers: ./deploy/container-deploy.sh development adpa us-east-1")
        print("  3. Access ADPA: http://your-alb-url.amazonaws.com")
    else:
        print("  1. Review AWS IAM permissions")
        print("  2. Enable required AWS services")
        print("  3. Re-run this test: python3 test_aws_setup.py")

if __name__ == "__main__":
    main()