#!/usr/bin/env python3
"""
Enhanced ADPA Deployment Script
Deploys the complete ADPA system including the new error handler
"""

import boto3
import json
import os
import sys
import zipfile
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
DEPLOYMENT_CONFIG = {
    "region": "us-east-2",
    "account_id": "083308938449",
    "environment": "development",
    "main_function": "adpa-data-processor-development",
    "error_function": "adpa-error-handler-development",
    "package_name": "enhanced-adpa-deployment.zip",
    "error_package_name": "adpa-error-handler.zip"
}

class EnhancedADPADeployer:
    """Deploy complete enhanced ADPA system"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name=DEPLOYMENT_CONFIG['region'])
        self.cf_client = boto3.client('cloudformation', region_name=DEPLOYMENT_CONFIG['region'])
        self.s3_client = boto3.client('s3', region_name=DEPLOYMENT_CONFIG['region'])
        
        print("🚀 Enhanced ADPA Deployment System")
        print("=" * 50)
        print(f"Region: {DEPLOYMENT_CONFIG['region']}")
        print(f"Environment: {DEPLOYMENT_CONFIG['environment']}")
    
    def deploy_complete_system(self):
        """Deploy the complete enhanced ADPA system"""
        
        print("\n📋 Starting Enhanced ADPA Deployment")
        print("=" * 50)
        
        # Step 1: Verify infrastructure exists
        if not self.verify_infrastructure():
            print("❌ Infrastructure verification failed")
            return False
        
        # Step 2: Package and deploy main function
        if not self.deploy_main_function():
            print("❌ Main function deployment failed")
            return False
        
        # Step 3: Package and deploy error handler
        if not self.deploy_error_handler():
            print("❌ Error handler deployment failed")
            return False
        
        # Step 4: Test deployment
        if not self.test_deployment():
            print("❌ Deployment testing failed")
            return False
        
        print("\n🎉 Enhanced ADPA Deployment Complete!")
        print("=" * 50)
        self.print_deployment_summary()
        
        return True
    
    def verify_infrastructure(self) -> bool:
        """Verify that required AWS infrastructure exists"""
        
        print("\n🔍 Verifying Infrastructure...")
        
        try:
            # Check CloudFormation stack
            stack_name = f"adpa-infrastructure-{DEPLOYMENT_CONFIG['environment']}"
            
            try:
                response = self.cf_client.describe_stacks(StackName=stack_name)
                stack_status = response['Stacks'][0]['StackStatus']
                
                if stack_status not in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                    print(f"❌ CloudFormation stack not ready: {stack_status}")
                    return False
                
                print(f"✅ CloudFormation stack: {stack_status}")
                
            except self.cf_client.exceptions.ClientError:
                print("❌ CloudFormation stack not found")
                print("   Please deploy infrastructure first")
                return False
            
            # Check Lambda functions exist
            try:
                self.lambda_client.get_function(FunctionName=DEPLOYMENT_CONFIG['main_function'])
                print(f"✅ Main Lambda function exists: {DEPLOYMENT_CONFIG['main_function']}")
            except self.lambda_client.exceptions.ResourceNotFoundException:
                print(f"❌ Main Lambda function not found: {DEPLOYMENT_CONFIG['main_function']}")
                return False
            
            try:
                self.lambda_client.get_function(FunctionName=DEPLOYMENT_CONFIG['error_function'])
                print(f"✅ Error Lambda function exists: {DEPLOYMENT_CONFIG['error_function']}")
            except self.lambda_client.exceptions.ResourceNotFoundException:
                print(f"❌ Error Lambda function not found: {DEPLOYMENT_CONFIG['error_function']}")
                return False
            
            # Check S3 buckets
            data_bucket = f"adpa-data-{DEPLOYMENT_CONFIG['account_id']}-{DEPLOYMENT_CONFIG['environment']}"
            try:
                self.s3_client.head_bucket(Bucket=data_bucket)
                print(f"✅ Data bucket exists: {data_bucket}")
            except:
                print(f"❌ Data bucket not accessible: {data_bucket}")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Infrastructure verification failed: {e}")
            return False
    
    def deploy_main_function(self) -> bool:
        """Deploy the main ADPA function with enhanced capabilities"""
        
        print("\n📦 Packaging Main ADPA Function...")
        
        try:
            # Create deployment package
            package_path = self.create_main_package()
            
            if not package_path:
                return False
            
            print(f"📤 Deploying main function: {DEPLOYMENT_CONFIG['main_function']}")
            
            # Update Lambda function code
            with open(package_path, 'rb') as f:
                zip_content = f.read()
            
            response = self.lambda_client.update_function_code(
                FunctionName=DEPLOYMENT_CONFIG['main_function'],
                ZipFile=zip_content
            )
            
            print(f"✅ Main function deployed successfully")
            print(f"   Function ARN: {response['FunctionArn']}")
            print(f"   Last Modified: {response['LastModified']}")
            
            # Update environment variables
            self.update_main_function_config()
            
            # Clean up package file
            os.unlink(package_path)
            
            return True
            
        except Exception as e:
            print(f"❌ Main function deployment failed: {e}")
            return False
    
    def deploy_error_handler(self) -> bool:
        """Deploy the enhanced error handler"""
        
        print("\n📦 Packaging Error Handler...")
        
        try:
            # Create error handler package
            package_path = self.create_error_handler_package()
            
            if not package_path:
                return False
            
            print(f"📤 Deploying error handler: {DEPLOYMENT_CONFIG['error_function']}")
            
            # Update Lambda function code
            with open(package_path, 'rb') as f:
                zip_content = f.read()
            
            response = self.lambda_client.update_function_code(
                FunctionName=DEPLOYMENT_CONFIG['error_function'],
                ZipFile=zip_content
            )
            
            print(f"✅ Error handler deployed successfully")
            print(f"   Function ARN: {response['FunctionArn']}")
            print(f"   Last Modified: {response['LastModified']}")
            
            # Clean up package file
            os.unlink(package_path)
            
            return True
            
        except Exception as e:
            print(f"❌ Error handler deployment failed: {e}")
            return False
    
    def create_main_package(self) -> Optional[str]:
        """Create deployment package for main ADPA function"""
        
        package_dir = "main_package_temp"
        zip_file = DEPLOYMENT_CONFIG["package_name"]
        
        try:
            # Clean existing files
            if os.path.exists(package_dir):
                shutil.rmtree(package_dir)
            if os.path.exists(zip_file):
                os.remove(zip_file)
            
            # Create package directory
            os.makedirs(package_dir)
            
            # Copy source files
            files_to_copy = [
                ("src", "src"),
                ("lambda_function.py", "lambda_function.py"),
                ("config", "config")
            ]
            
            for src, dst in files_to_copy:
                src_path = Path(src)
                dst_path = Path(package_dir) / dst
                
                if src_path.exists():
                    if src_path.is_dir():
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
                    print(f"   Copied {src}")
            
            # Create requirements for Lambda runtime
            requirements = """boto3>=1.34.0
pydantic>=2.0.0
requests>=2.31.0
python-json-logger>=2.0.7
pyyaml>=6.0.0
python-dotenv>=1.0.0
pandas>=2.0.0,<2.3.0
numpy>=1.24.0,<2.0.0
scikit-learn>=1.3.0,<1.6.0"""
            
            with open(Path(package_dir) / "requirements.txt", "w") as f:
                f.write(requirements)
            
            # Create ZIP file
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(package_dir):
                    # Skip __pycache__ directories
                    dirs[:] = [d for d in dirs if d != '__pycache__']
                    
                    for file in files:
                        if file.endswith(('.pyc', '.pyo')):
                            continue
                        
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, package_dir)
                        zipf.write(file_path, arcname)
            
            # Get package size
            size_mb = os.path.getsize(zip_file) / (1024 * 1024)
            print(f"✅ Main package created: {zip_file} ({size_mb:.2f} MB)")
            
            # Cleanup temp directory
            shutil.rmtree(package_dir)
            
            return zip_file
            
        except Exception as e:
            print(f"❌ Failed to create main package: {e}")
            if os.path.exists(package_dir):
                shutil.rmtree(package_dir)
            return None
    
    def create_error_handler_package(self) -> Optional[str]:
        """Create deployment package for error handler"""
        
        package_dir = "error_package_temp"
        zip_file = DEPLOYMENT_CONFIG["error_package_name"]
        
        try:
            # Clean existing files
            if os.path.exists(package_dir):
                shutil.rmtree(package_dir)
            if os.path.exists(zip_file):
                os.remove(zip_file)
            
            # Create package directory
            os.makedirs(package_dir)
            
            # Copy error handler and dependencies
            files_to_copy = [
                ("error_handler.py", "error_handler.py"),
                ("src/agent/utils", "src/agent/utils"),
                ("src/monitoring", "src/monitoring"),
                ("config", "config")
            ]
            
            for src, dst in files_to_copy:
                src_path = Path(src)
                dst_path = Path(package_dir) / dst
                
                if src_path.exists():
                    if src_path.is_dir():
                        # Create parent directories if needed
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(src_path, dst_path)
                    else:
                        # Create parent directories if needed
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_path, dst_path)
                    print(f"   Copied {src}")
            
            # Create minimal requirements for error handler
            error_requirements = """boto3>=1.34.0
pydantic>=2.0.0
python-json-logger>=2.0.7
pyyaml>=6.0.0"""
            
            with open(Path(package_dir) / "requirements.txt", "w") as f:
                f.write(error_requirements)
            
            # Create ZIP file
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(package_dir):
                    # Skip __pycache__ directories
                    dirs[:] = [d for d in dirs if d != '__pycache__']
                    
                    for file in files:
                        if file.endswith(('.pyc', '.pyo')):
                            continue
                        
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, package_dir)
                        zipf.write(file_path, arcname)
            
            # Get package size
            size_mb = os.path.getsize(zip_file) / (1024 * 1024)
            print(f"✅ Error handler package created: {zip_file} ({size_mb:.2f} MB)")
            
            # Cleanup temp directory
            shutil.rmtree(package_dir)
            
            return zip_file
            
        except Exception as e:
            print(f"❌ Failed to create error handler package: {e}")
            if os.path.exists(package_dir):
                shutil.rmtree(package_dir)
            return None
    
    def update_main_function_config(self):
        """Update main function configuration"""
        
        try:
            # Environment variables
            environment_vars = {
                'DATA_BUCKET': f"adpa-data-{DEPLOYMENT_CONFIG['account_id']}-{DEPLOYMENT_CONFIG['environment']}",
                'MODEL_BUCKET': f"adpa-models-{DEPLOYMENT_CONFIG['account_id']}-{DEPLOYMENT_CONFIG['environment']}",
                'AWS_REGION': DEPLOYMENT_CONFIG['region'],
                'ENVIRONMENT': DEPLOYMENT_CONFIG['environment'],
                'ERROR_HANDLER_FUNCTION': DEPLOYMENT_CONFIG['error_function']
            }
            
            self.lambda_client.update_function_configuration(
                FunctionName=DEPLOYMENT_CONFIG['main_function'],
                Environment={'Variables': environment_vars},
                Timeout=900,  # 15 minutes
                MemorySize=1024  # 1GB
            )
            
            print("✅ Main function configuration updated")
            
        except Exception as e:
            print(f"⚠️  Configuration update warning: {e}")
    
    def test_deployment(self) -> bool:
        """Test the deployed functions"""
        
        print("\n🧪 Testing Deployment...")
        
        try:
            # Test main function health check
            health_response = self.lambda_client.invoke(
                FunctionName=DEPLOYMENT_CONFIG['main_function'],
                InvocationType='RequestResponse',
                Payload=json.dumps({"action": "health_check"})
            )
            
            health_result = json.loads(health_response['Payload'].read())
            
            if health_result.get('status') == 'healthy':
                print("✅ Main function health check: PASSED")
                
                components = health_result.get('components', {})
                print(f"   Components loaded: {list(components.keys())}")
                
            else:
                print("❌ Main function health check: FAILED")
                print(f"   Response: {health_result}")
                return False
            
            # Test error handler
            error_test_event = {
                "errorMessage": "Test deployment validation",
                "errorType": "DeploymentTest",
                "stackTrace": ["test"]
            }
            
            error_response = self.lambda_client.invoke(
                FunctionName=DEPLOYMENT_CONFIG['error_function'],
                InvocationType='RequestResponse',
                Payload=json.dumps(error_test_event)
            )
            
            if error_response['StatusCode'] == 200:
                print("✅ Error handler test: PASSED")
            else:
                print("❌ Error handler test: FAILED")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Deployment testing failed: {e}")
            return False
    
    def print_deployment_summary(self):
        """Print deployment summary and next steps"""
        
        print("\n📋 Deployment Summary:")
        print("=" * 50)
        
        main_url = f"https://console.aws.amazon.com/lambda/home?region={DEPLOYMENT_CONFIG['region']}#/functions/{DEPLOYMENT_CONFIG['main_function']}"
        error_url = f"https://console.aws.amazon.com/lambda/home?region={DEPLOYMENT_CONFIG['region']}#/functions/{DEPLOYMENT_CONFIG['error_function']}"
        
        print(f"✅ Main Function: {DEPLOYMENT_CONFIG['main_function']}")
        print(f"   URL: {main_url}")
        print(f"✅ Error Handler: {DEPLOYMENT_CONFIG['error_function']}")
        print(f"   URL: {error_url}")
        
        print(f"\n🧪 Testing Commands:")
        print("Health Check:")
        print(f"""aws lambda invoke \\
    --function-name {DEPLOYMENT_CONFIG['main_function']} \\
    --payload '{{"action": "health_check"}}' \\
    --region {DEPLOYMENT_CONFIG['region']} \\
    response.json && cat response.json""")
        
        print("\nPipeline Test:")
        print(f"""aws lambda invoke \\
    --function-name {DEPLOYMENT_CONFIG['main_function']} \\
    --payload '{{"action": "run_pipeline", "objective": "Test classification", "dataset_path": "mock://test"}}' \\
    --region {DEPLOYMENT_CONFIG['region']} \\
    pipeline_response.json""")
        
        print(f"\n📊 Monitoring:")
        cloudwatch_url = f"https://{DEPLOYMENT_CONFIG['region']}.console.aws.amazon.com/cloudwatch/home?region={DEPLOYMENT_CONFIG['region']}#logsV2:log-groups"
        print(f"CloudWatch Logs: {cloudwatch_url}")
        
        print(f"\n🎯 Next Steps:")
        print("1. Run comprehensive tests: python3 comprehensive_adpa_tests.py")
        print("2. Monitor CloudWatch logs for any issues")
        print("3. Test with real datasets")
        print("4. Set up monitoring alerts")


def main():
    """Main deployment function"""
    
    print("🚀 Enhanced ADPA Deployment")
    print("Deploying complete system with error handler")
    print()
    
    # Initialize deployer
    deployer = EnhancedADPADeployer()
    
    # Deploy system
    success = deployer.deploy_complete_system()
    
    if success:
        print("\n🎉 Deployment completed successfully!")
        print("System is ready for comprehensive testing.")
    else:
        print("\n❌ Deployment failed!")
        print("Please check errors and retry.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)