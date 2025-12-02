#!/usr/bin/env python3
"""
Manual deployment script for ADPA Lambda function
Handles shell environment issues by using Python subprocess
"""

import os
import sys
import json
import shutil
import zipfile
import subprocess
from pathlib import Path
from typing import Dict, Any

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

def run_command(cmd: list, cwd: str = None) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=cwd,
            timeout=300
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)

def check_aws_cli():
    """Check if AWS CLI is available and configured"""
    print_status("Checking AWS CLI availability...")
    
    # Try to find aws command
    exit_code, stdout, stderr = run_command(["which", "aws"])
    if exit_code != 0:
        print_error("AWS CLI not found in PATH")
        return False
    
    aws_path = stdout.strip()
    print_status(f"Found AWS CLI at: {aws_path}")
    
    # Check AWS credentials
    exit_code, stdout, stderr = run_command(["aws", "sts", "get-caller-identity"])
    if exit_code != 0:
        print_error(f"AWS credentials not configured: {stderr}")
        return False
    
    caller_identity = json.loads(stdout)
    print_status(f"AWS Identity: {caller_identity.get('Arn', 'Unknown')}")
    return True

def clean_previous_builds():
    """Clean previous deployment packages"""
    print_status("Cleaning previous deployment packages...")
    
    if os.path.exists(DEPLOYMENT_PACKAGE):
        os.remove(DEPLOYMENT_PACKAGE)
        print_status(f"Removed {DEPLOYMENT_PACKAGE}")
    
    if os.path.exists("lambda_package"):
        shutil.rmtree("lambda_package")
        print_status("Removed lambda_package directory")

def create_deployment_package():
    """Create Lambda deployment package"""
    print_status("Creating Lambda deployment package...")
    
    # Create package directory
    os.makedirs("lambda_package", exist_ok=True)
    
    # Copy source code
    print_status("Copying ADPA source code...")
    if os.path.exists("src"):
        shutil.copytree("src", "lambda_package/src")
    else:
        print_error("src directory not found!")
        return False
    
    # Copy lambda function handler
    if os.path.exists("lambda_function.py"):
        shutil.copy2("lambda_function.py", "lambda_package/")
    else:
        print_error("lambda_function.py not found!")
        return False
    
    # Copy config if exists
    if os.path.exists("config"):
        shutil.copytree("config", "lambda_package/config")
        print_status("Copied config directory")
    
    return True

def install_dependencies():
    """Install Python dependencies for Lambda"""
    print_status("Installing Python dependencies...")
    
    # Create requirements.txt for Lambda
    lambda_requirements = """boto3>=1.34.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
pydantic>=2.0.0
requests>=2.31.0
python-json-logger>=2.0.7
pyyaml>=6.0.0
python-dotenv>=1.0.0
"""
    
    with open("lambda_package/requirements.txt", "w") as f:
        f.write(lambda_requirements)
    
    # Install dependencies
    print_status("Installing packages to lambda_package...")
    exit_code, stdout, stderr = run_command([
        sys.executable, "-m", "pip", "install", 
        "-r", "requirements.txt", 
        "-t", "."
    ], cwd="lambda_package")
    
    if exit_code != 0:
        print_error(f"Failed to install dependencies: {stderr}")
        return False
    
    print_status("Dependencies installed successfully")
    return True

def optimize_package():
    """Remove unnecessary files to reduce package size"""
    print_status("Optimizing package size...")
    
    # Directories to remove
    dirs_to_remove = []
    files_to_remove = []
    
    # Walk through lambda_package and find files/dirs to remove
    for root, dirs, files in os.walk("lambda_package"):
        # Remove __pycache__ directories
        if "__pycache__" in dirs:
            dirs_to_remove.append(os.path.join(root, "__pycache__"))
        
        # Remove .dist-info directories
        for d in dirs:
            if d.endswith(".dist-info"):
                dirs_to_remove.append(os.path.join(root, d))
        
        # Remove test directories
        if "tests" in dirs:
            dirs_to_remove.append(os.path.join(root, "tests"))
        
        # Remove .pyc files
        for f in files:
            if f.endswith(".pyc"):
                files_to_remove.append(os.path.join(root, f))
    
    # Remove directories
    for dir_path in dirs_to_remove:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print_status(f"Removed {dir_path}")
            except Exception as e:
                print_warning(f"Could not remove {dir_path}: {e}")
    
    # Remove files
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print_warning(f"Could not remove {file_path}: {e}")

def create_zip_package():
    """Create ZIP package for deployment"""
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
    
    # Check if package is too large
    if package_size_mb > 50:
        print_warning(f"Package size ({package_size_mb:.2f} MB) is quite large for Lambda")
    
    return True

def deploy_to_lambda():
    """Deploy package to AWS Lambda"""
    print_status(f"Deploying to AWS Lambda function: {FUNCTION_NAME}")
    
    # Check if function exists
    exit_code, stdout, stderr = run_command([
        "aws", "lambda", "get-function",
        "--function-name", FUNCTION_NAME,
        "--region", REGION
    ])
    
    if exit_code != 0:
        print_error(f"Lambda function {FUNCTION_NAME} not found!")
        print_error("Please deploy the infrastructure first")
        return False
    
    print_status("Lambda function exists, updating code...")
    
    # Update function code
    exit_code, stdout, stderr = run_command([
        "aws", "lambda", "update-function-code",
        "--function-name", FUNCTION_NAME,
        "--zip-file", f"fileb://{DEPLOYMENT_PACKAGE}",
        "--region", REGION
    ])
    
    if exit_code != 0:
        print_error(f"Failed to update function code: {stderr}")
        return False
    
    print_status("Function code updated successfully")
    
    # Update function configuration
    print_status("Updating function configuration...")
    exit_code, stdout, stderr = run_command([
        "aws", "lambda", "update-function-configuration",
        "--function-name", FUNCTION_NAME,
        "--timeout", "900",
        "--memory-size", "512",
        "--region", REGION
    ])
    
    if exit_code != 0:
        print_warning(f"Failed to update function configuration: {stderr}")
    else:
        print_status("Function configuration updated")
    
    return True

def test_deployment():
    """Test the deployed Lambda function"""
    print_status("Testing deployed Lambda function...")
    
    # Create test payload
    test_payload = json.dumps({"action": "health_check"})
    
    # Invoke function
    exit_code, stdout, stderr = run_command([
        "aws", "lambda", "invoke",
        "--function-name", FUNCTION_NAME,
        "--payload", test_payload,
        "--region", REGION,
        "lambda_test_response.json"
    ])
    
    if exit_code != 0:
        print_error(f"Lambda invocation failed: {stderr}")
        return False
    
    print_status("✅ Lambda invocation successful")
    
    # Read and display response
    try:
        with open("lambda_test_response.json", "r") as f:
            response = json.load(f)
        print("Response:")
        print(json.dumps(response, indent=2))
        
        # Clean up test file
        os.remove("lambda_test_response.json")
        
    except Exception as e:
        print_warning(f"Could not read response file: {e}")
    
    return True

def cleanup():
    """Clean up temporary files"""
    print_status("Cleaning up temporary files...")
    
    if os.path.exists("lambda_package"):
        shutil.rmtree("lambda_package")
    
    if os.path.exists("lambda_test_response.json"):
        os.remove("lambda_test_response.json")

def main():
    """Main deployment function"""
    print("🚀 Deploying ADPA Agent to AWS Lambda")
    print("=" * 40)
    
    try:
        # Step 1: Check prerequisites
        if not check_aws_cli():
            print_error("AWS CLI check failed")
            return False
        
        # Step 2: Clean previous builds
        clean_previous_builds()
        
        # Step 3: Create deployment package
        if not create_deployment_package():
            print_error("Failed to create deployment package")
            return False
        
        # Step 4: Install dependencies
        if not install_dependencies():
            print_error("Failed to install dependencies")
            return False
        
        # Step 5: Optimize package
        optimize_package()
        
        # Step 6: Create ZIP
        if not create_zip_package():
            print_error("Failed to create ZIP package")
            return False
        
        # Step 7: Deploy to Lambda
        if not deploy_to_lambda():
            print_error("Failed to deploy to Lambda")
            return False
        
        # Step 8: Test deployment
        if not test_deployment():
            print_warning("Deployment test failed, but deployment may still be successful")
        
        # Step 9: Cleanup
        cleanup()
        
        print()
        print("=" * 40)
        print("🎉 ADPA AGENT DEPLOYMENT SUCCESSFUL! 🎉")
        print("=" * 40)
        print()
        print(f"✅ Function: {FUNCTION_NAME}")
        print(f"✅ Region: {REGION}")
        print(f"✅ Package: {DEPLOYMENT_PACKAGE}")
        print()
        print("Test commands:")
        print(f'  aws lambda invoke --function-name {FUNCTION_NAME} --payload \'{{"action": "health_check"}}\' response.json')
        print()
        
        return True
        
    except Exception as e:
        print_error(f"Deployment failed with exception: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)