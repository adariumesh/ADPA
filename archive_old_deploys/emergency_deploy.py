#!/usr/bin/env python3
"""
Emergency deployment script for ADPA Lambda - shell environment workaround
"""

import os
import sys
import json
import zipfile
import shutil
from pathlib import Path

# Add current directory to path
current_dir = "/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa"
os.chdir(current_dir)
sys.path.insert(0, current_dir)

# Import boto3 directly
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    print("✅ boto3 available")
except ImportError as e:
    print(f"❌ boto3 import failed: {e}")
    print("Installing boto3...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "boto3"])
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

# Configuration
CONFIG = {
    "function_name": "adpa-data-processor-development",
    "region": "us-east-2",
    "runtime": "python3.9",
    "handler": "lambda_function.lambda_handler",
    "timeout": 900,
    "memory_size": 512,
    "package_name": "adpa-emergency-deploy.zip",
}

def print_status(message, prefix="INFO"):
    print(f"[{prefix}] {message}")

def create_package():
    """Create deployment package"""
    print_status("Creating deployment package...")
    
    # Clean up existing files
    if os.path.exists(CONFIG["package_name"]):
        os.remove(CONFIG["package_name"])
    
    # Create ZIP directly
    with zipfile.ZipFile(CONFIG["package_name"], 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add lambda_function.py
        if os.path.exists("lambda_function.py"):
            zipf.write("lambda_function.py", "lambda_function.py")
            print_status("Added lambda_function.py")
        
        # Add src directory recursively
        if os.path.exists("src"):
            for root, dirs, files in os.walk("src"):
                # Skip __pycache__ 
                dirs[:] = [d for d in dirs if d != '__pycache__']
                for file in files:
                    if not file.endswith(('.pyc', '.pyo')):
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, ".")
                        zipf.write(file_path, arc_path)
        
        # Add config directory
        if os.path.exists("config"):
            for root, dirs, files in os.walk("config"):
                dirs[:] = [d for d in dirs if d != '__pycache__']
                for file in files:
                    if not file.endswith(('.pyc', '.pyo')):
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, ".")
                        zipf.write(file_path, arc_path)
    
    size_mb = os.path.getsize(CONFIG["package_name"]) / (1024 * 1024)
    print_status(f"Package created: {CONFIG['package_name']} ({size_mb:.2f} MB)")
    return True

def check_aws_access():
    """Check AWS credentials"""
    try:
        sts = boto3.client('sts', region_name=CONFIG["region"])
        identity = sts.get_caller_identity()
        print_status(f"AWS Identity: {identity.get('Arn', 'Unknown')}")
        return True
    except Exception as e:
        print_status(f"AWS access check failed: {e}", "ERROR")
        return False

def check_function_exists():
    """Check if Lambda function exists"""
    try:
        client = boto3.client('lambda', region_name=CONFIG["region"])
        response = client.get_function(FunctionName=CONFIG["function_name"])
        print_status(f"Target function found: {CONFIG['function_name']}")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print_status(f"Function {CONFIG['function_name']} not found", "ERROR")
            return False
        else:
            print_status(f"Function check error: {e}", "ERROR")
            return False

def deploy_code():
    """Deploy code to Lambda"""
    try:
        client = boto3.client('lambda', region_name=CONFIG["region"])
        
        with open(CONFIG["package_name"], 'rb') as f:
            zip_data = f.read()
        
        print_status("Uploading code to Lambda...")
        response = client.update_function_code(
            FunctionName=CONFIG["function_name"],
            ZipFile=zip_data
        )
        
        print_status("✅ Code deployment successful")
        return True
        
    except Exception as e:
        print_status(f"Code deployment failed: {e}", "ERROR")
        return False

def test_function():
    """Test the Lambda function"""
    try:
        client = boto3.client('lambda', region_name=CONFIG["region"])
        
        print_status("Testing Lambda function...")
        test_payload = json.dumps({"action": "health_check"})
        
        response = client.invoke(
            FunctionName=CONFIG["function_name"],
            Payload=test_payload
        )
        
        response_data = response['Payload'].read().decode('utf-8')
        
        try:
            result = json.loads(response_data)
        except:
            result = {"raw_response": response_data}
        
        print_status("✅ Function invocation successful")
        
        # Check health status
        if isinstance(result, dict) and result.get('status') == 'healthy':
            print_status("✅ Health check PASSED")
        else:
            print_status(f"⚠️  Health check result: {result}", "WARN")
        
        return result
        
    except Exception as e:
        print_status(f"Function test failed: {e}", "ERROR")
        return {"error": str(e)}

def main():
    """Main deployment process"""
    print("🚀 ADPA Emergency Lambda Deployment")
    print("=" * 40)
    
    # Check prerequisites
    if not os.path.exists("lambda_function.py"):
        print_status("lambda_function.py not found", "ERROR")
        return False
    
    if not os.path.exists("src"):
        print_status("src directory not found", "ERROR")
        return False
    
    # Execute deployment steps
    steps = [
        ("AWS Access Check", check_aws_access),
        ("Function Existence Check", check_function_exists),
        ("Create Package", create_package),
        ("Deploy Code", deploy_code),
    ]
    
    for step_name, step_func in steps:
        print_status(f"Executing: {step_name}")
        if not step_func():
            print_status(f"Step failed: {step_name}", "ERROR")
            return False
    
    # Test deployment
    print_status("Testing deployment...")
    test_result = test_function()
    
    # Results summary
    print("\n" + "=" * 40)
    print("🎉 DEPLOYMENT COMPLETED")
    print("=" * 40)
    print(f"✅ Function: {CONFIG['function_name']}")
    print(f"✅ Region: {CONFIG['region']}")
    print(f"✅ Package: {CONFIG['package_name']}")
    
    print(f"\n📋 Test Result:")
    print(json.dumps(test_result, indent=2))
    
    print(f"\n📊 AWS Console URL:")
    print(f"https://{CONFIG['region']}.console.aws.amazon.com/lambda/home?region={CONFIG['region']}#/functions/{CONFIG['function_name']}")
    
    # Clean up
    if os.path.exists(CONFIG["package_name"]):
        os.remove(CONFIG["package_name"])
        print_status("Cleaned up package file")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Emergency deployment completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Emergency deployment failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Deployment error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)