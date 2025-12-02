#!/usr/bin/env python3
"""
Simplified deployment script for ADPA Lambda function
Creates deployment package without shell dependencies
"""

import os
import sys
import json
import shutil
import zipfile
import boto3
from pathlib import Path
import tempfile

# Configuration
FUNCTION_NAME = "adpa-data-processor-development"
REGION = "us-east-2"
DEPLOYMENT_PACKAGE = "adpa-lambda-deployment.zip"

def print_status(message: str):
    print(f"[INFO] {message}")

def print_error(message: str):
    print(f"[ERROR] {message}")

def print_warning(message: str):
    print(f"[WARN] {message}")

def create_lambda_package():
    """Create Lambda deployment package"""
    print_status("Creating Lambda deployment package...")
    
    # Clean existing package
    if os.path.exists(DEPLOYMENT_PACKAGE):
        os.remove(DEPLOYMENT_PACKAGE)
        print_status(f"Removed existing {DEPLOYMENT_PACKAGE}")
    
    if os.path.exists("lambda_package"):
        shutil.rmtree("lambda_package")
        print_status("Removed existing lambda_package directory")
    
    # Create package directory
    os.makedirs("lambda_package", exist_ok=True)
    
    # Copy source code
    print_status("Copying ADPA source code...")
    
    # Copy src directory
    if os.path.exists("src"):
        shutil.copytree("src", "lambda_package/src")
        print_status("Copied src directory")
    else:
        print_error("src directory not found!")
        return False
    
    # Copy lambda function handler
    if os.path.exists("lambda_function.py"):
        shutil.copy2("lambda_function.py", "lambda_package/")
        print_status("Copied lambda_function.py")
    else:
        print_error("lambda_function.py not found!")
        return False
    
    # Copy config if exists
    if os.path.exists("config"):
        shutil.copytree("config", "lambda_package/config")
        print_status("Copied config directory")
    
    # Create lightweight requirements.txt for Lambda runtime
    lambda_requirements = """boto3>=1.34.0
pydantic>=2.0.0
requests>=2.31.0
python-json-logger>=2.0.7
pyyaml>=6.0.0
python-dotenv>=1.0.0
"""
    
    with open("lambda_package/requirements.txt", "w") as f:
        f.write(lambda_requirements)
    print_status("Created requirements.txt")
    
    return True

def optimize_package():
    """Remove unnecessary files to reduce package size"""
    print_status("Optimizing package size...")
    
    # Remove test directories and files
    for root, dirs, files in os.walk("lambda_package"):
        # Remove __pycache__ directories
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(pycache_path)
                print_status(f"Removed {pycache_path}")
            except Exception as e:
                print_warning(f"Could not remove {pycache_path}: {e}")
        
        # Remove test directories
        if "tests" in dirs:
            test_path = os.path.join(root, "tests")
            try:
                shutil.rmtree(test_path)
                print_status(f"Removed {test_path}")
            except Exception as e:
                print_warning(f"Could not remove {test_path}: {e}")
        
        # Remove .pyc files
        for file in files:
            if file.endswith(".pyc"):
                pyc_path = os.path.join(root, file)
                try:
                    os.remove(pyc_path)
                except Exception as e:
                    print_warning(f"Could not remove {pyc_path}: {e}")

def create_zip():
    """Create ZIP package"""
    print_status("Creating deployment ZIP...")
    
    with zipfile.ZipFile(DEPLOYMENT_PACKAGE, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("lambda_package"):
            for file in files:
                file_path = os.path.join(root, file)
                # Get relative path from lambda_package
                arcname = os.path.relpath(file_path, "lambda_package")
                zipf.write(file_path, arcname)
    
    # Check package size
    package_size = os.path.getsize(DEPLOYMENT_PACKAGE)
    package_size_mb = package_size / (1024 * 1024)
    print_status(f"Package created: {DEPLOYMENT_PACKAGE} ({package_size_mb:.2f} MB)")
    
    return True

def deploy_with_boto3():
    """Deploy using boto3 directly"""
    print_status(f"Deploying to AWS Lambda function: {FUNCTION_NAME}")
    
    try:
        # Initialize boto3 client
        lambda_client = boto3.client('lambda', region_name=REGION)
        
        # Check if function exists
        try:
            response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
            print_status("Lambda function exists, updating code...")
        except lambda_client.exceptions.ResourceNotFoundException:
            print_error(f"Lambda function {FUNCTION_NAME} not found!")
            print_error("Please deploy the infrastructure first")
            return False
        
        # Read deployment package
        with open(DEPLOYMENT_PACKAGE, 'rb') as f:
            zip_content = f.read()
        
        # Update function code
        print_status("Updating Lambda function code...")
        response = lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_content
        )
        print_status("✅ Function code updated successfully")
        
        # Update function configuration
        print_status("Updating function configuration...")
        try:
            config_response = lambda_client.update_function_configuration(
                FunctionName=FUNCTION_NAME,
                Timeout=900,
                MemorySize=512
            )
            print_status("✅ Function configuration updated")
        except Exception as e:
            print_warning(f"Configuration update failed: {e}")
        
        return True
        
    except Exception as e:
        print_error(f"Deployment failed: {e}")
        return False

def test_lambda_function():
    """Test the deployed Lambda function"""
    print_status("Testing deployed Lambda function...")
    
    try:
        lambda_client = boto3.client('lambda', region_name=REGION)
        
        # Create test payload
        test_payload = json.dumps({"action": "health_check"})
        
        # Invoke function
        response = lambda_client.invoke(
            FunctionName=FUNCTION_NAME,
            Payload=test_payload
        )
        
        # Read response
        response_payload = response['Payload'].read().decode('utf-8')
        response_json = json.loads(response_payload)
        
        print_status("✅ Lambda invocation successful")
        print("Response:")
        print(json.dumps(response_json, indent=2))
        
        # Check if response indicates success
        if response_json.get('status') == 'healthy':
            print_status("✅ Health check passed")
            return True
        else:
            print_warning("⚠️  Health check returned unhealthy status")
            return False
        
    except Exception as e:
        print_error(f"Lambda test failed: {e}")
        return False

def cleanup():
    """Clean up temporary files"""
    print_status("Cleaning up temporary files...")
    
    if os.path.exists("lambda_package"):
        shutil.rmtree("lambda_package")
        print_status("Removed lambda_package directory")

def main():
    """Main deployment function"""
    print("🚀 Deploying ADPA Agent to AWS Lambda (Simplified)")
    print("=" * 50)
    
    try:
        # Check AWS credentials by trying to create client
        try:
            sts_client = boto3.client('sts', region_name=REGION)
            caller_identity = sts_client.get_caller_identity()
            print_status(f"AWS Identity: {caller_identity.get('Arn', 'Unknown')}")
        except Exception as e:
            print_error(f"AWS credentials not configured: {e}")
            return False
        
        # Step 1: Create deployment package
        if not create_lambda_package():
            print_error("Failed to create deployment package")
            return False
        
        # Step 2: Optimize package
        optimize_package()
        
        # Step 3: Create ZIP
        if not create_zip():
            print_error("Failed to create ZIP package")
            return False
        
        # Step 4: Deploy to Lambda
        if not deploy_with_boto3():
            print_error("Failed to deploy to Lambda")
            return False
        
        # Step 5: Test deployment
        test_success = test_lambda_function()
        
        # Step 6: Cleanup
        cleanup()
        
        print()
        print("=" * 50)
        print("🎉 ADPA AGENT DEPLOYMENT COMPLETED! 🎉")
        print("=" * 50)
        print()
        print(f"✅ Function: {FUNCTION_NAME}")
        print(f"✅ Region: {REGION}")
        print(f"✅ Package: {DEPLOYMENT_PACKAGE}")
        
        if test_success:
            print("✅ Health check: PASSED")
        else:
            print("⚠️  Health check: FAILED (check CloudWatch logs)")
        
        print()
        print("Manual test command:")
        print(f'aws lambda invoke --function-name {FUNCTION_NAME} --payload \'{{"action": "health_check"}}\' response.json')
        print()
        print("Dashboard URL:")
        print(f"https://{REGION}.console.aws.amazon.com/lambda/home?region={REGION}#/functions/{FUNCTION_NAME}")
        print()
        
        return True
        
    except Exception as e:
        print_error(f"Deployment failed with exception: {e}")
        import traceback
        print(traceback.format_exc())
        return False
    finally:
        # Always cleanup
        if os.path.exists("lambda_package"):
            shutil.rmtree("lambda_package")

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ Deployment completed successfully!")
    else:
        print("❌ Deployment failed!")
    sys.exit(0 if success else 1)