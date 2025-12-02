#!/usr/bin/env python3
"""
Deploy ADPA Code to Existing Lambda Functions
Bypasses CloudFormation and deploys code directly
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
    "main_function": "adpa-data-processor-development",
    "error_function": "adpa-error-handler-development",
    "package_name": "enhanced-adpa-deployment.zip",
    "error_package_name": "adpa-error-handler.zip"
}

class DirectADPADeployer:
    """Deploy ADPA code directly to existing Lambda functions"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name=DEPLOYMENT_CONFIG['region'])
        self.s3_client = boto3.client('s3', region_name=DEPLOYMENT_CONFIG['region'])
        
        print("🚀 Direct ADPA Code Deployment")
        print("=" * 50)
        print(f"Region: {DEPLOYMENT_CONFIG['region']}")
    
    def deploy_complete_system(self):
        """Deploy the complete ADPA code to existing functions"""
        
        print("\n📋 Starting Direct ADPA Code Deployment")
        print("=" * 50)
        
        # Step 1: Verify functions exist
        if not self.verify_functions_exist():
            print("❌ Function verification failed")
            return False
        
        # Step 2: Deploy main function code
        if not self.deploy_main_function():
            print("❌ Main function deployment failed")
            return False
        
        # Step 3: Deploy error handler code
        if not self.deploy_error_handler():
            print("❌ Error handler deployment failed")
            return False
        
        # Step 4: Test deployment
        if not self.test_deployment():
            print("❌ Deployment testing failed")
            return False
        
        print("\n🎉 ADPA Code Deployment Complete!")
        print("=" * 50)
        self.print_deployment_summary()
        
        return True
    
    def verify_functions_exist(self) -> bool:
        """Verify that Lambda functions exist"""
        
        print("\n🔍 Verifying Lambda Functions...")
        
        try:
            # Check main function
            try:
                response = self.lambda_client.get_function(FunctionName=DEPLOYMENT_CONFIG['main_function'])
                print(f"✅ Main function exists: {DEPLOYMENT_CONFIG['main_function']}")
                print(f"   Memory: {response['Configuration']['MemorySize']}MB")
                print(f"   Timeout: {response['Configuration']['Timeout']}s")
            except self.lambda_client.exceptions.ResourceNotFoundException:
                print(f"❌ Main function not found: {DEPLOYMENT_CONFIG['main_function']}")
                print("   Run: python3 create_lambda_functions.py")
                return False
            
            # Check error handler
            try:
                response = self.lambda_client.get_function(FunctionName=DEPLOYMENT_CONFIG['error_function'])
                print(f"✅ Error function exists: {DEPLOYMENT_CONFIG['error_function']}")
                print(f"   Memory: {response['Configuration']['MemorySize']}MB")
                print(f"   Timeout: {response['Configuration']['Timeout']}s")
            except self.lambda_client.exceptions.ResourceNotFoundException:
                print(f"❌ Error function not found: {DEPLOYMENT_CONFIG['error_function']}")
                print("   Run: python3 create_lambda_functions.py")
                return False
            
            # Check S3 buckets
            buckets_to_check = [
                'adpa-data-083308938449-development',
                'adpa-models-083308938449-development'
            ]
            
            for bucket in buckets_to_check:
                try:
                    self.s3_client.head_bucket(Bucket=bucket)
                    print(f"✅ S3 bucket accessible: {bucket}")
                except Exception as e:
                    print(f"❌ S3 bucket issue: {bucket} - {e}")
                    print("   Run: python3 create_s3_buckets.py")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Function verification failed: {e}")
            return False
    
    def deploy_main_function(self) -> bool:
        """Deploy the main ADPA function code"""
        
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
            print(f"   Last Modified: {response['LastModified']}")
            print(f"   Code Size: {response['CodeSize']} bytes")
            
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
            print(f"   Last Modified: {response['LastModified']}")
            print(f"   Code Size: {response['CodeSize']} bytes")
            
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
            
            copied_files = 0
            for src, dst in files_to_copy:
                src_path = Path(src)
                dst_path = Path(package_dir) / dst
                
                if src_path.exists():
                    if src_path.is_dir():
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
                    print(f"   ✅ Copied {src}")
                    copied_files += 1
                else:
                    print(f"   ⚠️  Missing {src}")
            
            if copied_files == 0:
                print("❌ No source files found to package")
                return None
            
            # Create requirements for Lambda runtime (minimal for deployment speed)
            requirements = """boto3>=1.34.0
pydantic>=2.0.0
requests>=2.31.0
python-json-logger>=2.0.7
pyyaml>=6.0.0
python-dotenv>=1.0.0"""
            
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
            
            # Copy error handler and minimal dependencies
            files_to_copy = [
                ("error_handler.py", "error_handler.py")
            ]
            
            # Copy selective source components for error handler
            if os.path.exists("src/agent/utils"):
                dst_path = Path(package_dir) / "src" / "agent" / "utils"
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree("src/agent/utils", dst_path)
                print(f"   ✅ Copied src/agent/utils")
            
            if os.path.exists("src/monitoring"):
                dst_path = Path(package_dir) / "src" / "monitoring"
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree("src/monitoring", dst_path)
                print(f"   ✅ Copied src/monitoring")
            
            # Copy main files
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
                    print(f"   ✅ Copied {src}")
            
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
                'DATA_BUCKET': 'adpa-data-083308938449-development',
                'MODEL_BUCKET': 'adpa-models-083308938449-development',
                'ENVIRONMENT': 'development'
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
            
            print(f"📊 Main Function Health Check:")
            print(f"   Status: {health_result.get('status', 'unknown')}")
            
            if health_result.get('status') == 'healthy':
                print("✅ Main function health check: PASSED")
                
                components = health_result.get('components', {})
                print(f"   Components loaded:")
                for component, status in components.items():
                    status_icon = "✅" if status else "❌"
                    print(f"     {status_icon} {component}: {status}")
                
            else:
                print("❌ Main function health check: FAILED")
                print(f"   Response: {health_result}")
                return False
            
            # Test error handler
            print(f"\n📊 Error Handler Test:")
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
                error_result = json.loads(error_response['Payload'].read())
                if error_result.get('statusCode') == 200:
                    print("✅ Error handler test: PASSED")
                else:
                    print("❌ Error handler test: FAILED")
                    print(f"   Response: {error_result}")
                    return False
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
    pipeline_response.json && cat pipeline_response.json""")
        
        print(f"\n📊 Monitoring:")
        cloudwatch_url = f"https://{DEPLOYMENT_CONFIG['region']}.console.aws.amazon.com/cloudwatch/home?region={DEPLOYMENT_CONFIG['region']}#logsV2:log-groups"
        print(f"CloudWatch Logs: {cloudwatch_url}")
        
        print(f"\n🎯 Next Steps:")
        print("1. Run comprehensive tests: python3 comprehensive_adpa_tests.py")
        print("2. Monitor CloudWatch logs for any issues")
        print("3. Test with real datasets")


def main():
    """Main deployment function"""
    
    print("🚀 Direct ADPA Code Deployment")
    print("Deploying sophisticated AI code to existing Lambda functions")
    print()
    
    # Initialize deployer
    deployer = DirectADPADeployer()
    
    # Deploy system
    success = deployer.deploy_complete_system()
    
    if success:
        print("\n🎉 Deployment completed successfully!")
        print("Your sophisticated ADPA AI system is now operational!")
    else:
        print("\n❌ Deployment failed!")
        print("Please check errors and retry.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)