#!/usr/bin/env python3
"""
Direct boto3 deployment script for ADPA Lambda function
Bypasses shell environment issues by using pure Python
"""

import os
import sys
import json
import zipfile
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

# Check if boto3 is available
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    print("❌ boto3 not available. Install with: pip install boto3")
    BOTO3_AVAILABLE = False

# Configuration
CONFIG = {
    "function_name": "adpa-data-processor-development",
    "region": "us-east-2",
    "runtime": "python3.9",
    "handler": "lambda_function.lambda_handler",
    "timeout": 900,
    "memory_size": 512,
    "package_name": "adpa-lambda-deployment.zip",
    "environment_vars": {
        "DATA_BUCKET": "adpa-data-276983626136-development",
        "MODEL_BUCKET": "adpa-models-276983626136-development",
        "AWS_REGION": "us-east-2",
        "ENVIRONMENT": "development"
    }
}

def print_status(message: str, prefix: str = "INFO"):
    """Print status message"""
    print(f"[{prefix}] {message}")

def create_deployment_package() -> bool:
    """Create the deployment ZIP package"""
    print_status("Creating deployment package...")
    
    package_dir = "lambda_package_temp"
    zip_file = CONFIG["package_name"]
    
    try:
        # Clean existing files
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir)
        if os.path.exists(zip_file):
            os.remove(zip_file)
        
        # Create temporary directory
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
                print_status(f"Copied {src}")
            else:
                print_status(f"Source {src} not found", "WARN")
        
        # Create minimal requirements.txt
        requirements = """# Lambda runtime dependencies
boto3>=1.34.0
pydantic>=2.0.0
requests>=2.31.0
python-json-logger>=2.0.7
pyyaml>=6.0.0
python-dotenv>=1.0.0
"""
        
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
        print_status(f"Created {zip_file} ({size_mb:.2f} MB)")
        
        # Cleanup temp directory
        shutil.rmtree(package_dir)
        
        return True
        
    except Exception as e:
        print_status(f"Failed to create package: {e}", "ERROR")
        return False

def check_aws_credentials() -> bool:
    """Check AWS credentials and permissions"""
    if not BOTO3_AVAILABLE:
        return False
        
    try:
        sts_client = boto3.client('sts', region_name=CONFIG["region"])
        identity = sts_client.get_caller_identity()
        print_status(f"AWS Identity: {identity.get('Arn', 'Unknown')}")
        return True
    except NoCredentialsError:
        print_status("AWS credentials not configured", "ERROR")
        return False
    except Exception as e:
        print_status(f"AWS credential check failed: {e}", "ERROR")
        return False

def check_lambda_function_exists() -> bool:
    """Check if target Lambda function exists"""
    try:
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        response = lambda_client.get_function(FunctionName=CONFIG["function_name"])
        print_status(f"Target function exists: {CONFIG['function_name']}")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print_status(f"Lambda function {CONFIG['function_name']} not found", "ERROR")
            print_status("Please deploy infrastructure first", "ERROR")
            return False
        else:
            print_status(f"Error checking function: {e}", "ERROR")
            return False

def deploy_lambda_code() -> bool:
    """Deploy code to Lambda function"""
    try:
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        
        # Read ZIP file
        with open(CONFIG["package_name"], 'rb') as f:
            zip_content = f.read()
        
        # Update function code
        print_status("Updating Lambda function code...")
        response = lambda_client.update_function_code(
            FunctionName=CONFIG["function_name"],
            ZipFile=zip_content
        )
        
        print_status("✅ Function code updated successfully")
        return True
        
    except Exception as e:
        print_status(f"Failed to update function code: {e}", "ERROR")
        return False

def update_lambda_configuration() -> bool:
    """Update Lambda function configuration"""
    try:
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        
        print_status("Updating function configuration...")
        response = lambda_client.update_function_configuration(
            FunctionName=CONFIG["function_name"],
            Runtime=CONFIG["runtime"],
            Handler=CONFIG["handler"],
            Timeout=CONFIG["timeout"],
            MemorySize=CONFIG["memory_size"],
            Environment={
                'Variables': CONFIG["environment_vars"]
            }
        )
        
        print_status("✅ Function configuration updated")
        return True
        
    except Exception as e:
        print_status(f"Configuration update failed: {e}", "WARN")
        return False

def test_lambda_function() -> Dict[str, Any]:
    """Test the deployed Lambda function"""
    try:
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        
        # Health check test
        print_status("Testing Lambda function with health check...")
        
        test_payload = json.dumps({"action": "health_check"})
        
        response = lambda_client.invoke(
            FunctionName=CONFIG["function_name"],
            Payload=test_payload
        )
        
        # Read response
        response_payload = response['Payload'].read().decode('utf-8')
        
        try:
            response_json = json.loads(response_payload)
        except json.JSONDecodeError:
            response_json = {"raw_response": response_payload}
        
        print_status("✅ Lambda invocation successful")
        
        # Check response status
        if isinstance(response_json, dict):
            status = response_json.get('status', 'unknown')
            if status == 'healthy':
                print_status("✅ Health check PASSED")
            elif status == 'unhealthy':
                print_status("⚠️  Health check returned unhealthy", "WARN")
            else:
                print_status(f"⚠️  Unknown health status: {status}", "WARN")
        
        return response_json
        
    except Exception as e:
        print_status(f"Lambda test failed: {e}", "ERROR")
        return {"error": str(e), "status": "test_failed"}

def cleanup() -> None:
    """Clean up temporary files"""
    temp_files = [
        "lambda_package_temp",
        CONFIG["package_name"]
    ]
    
    for file_path in temp_files:
        if os.path.exists(file_path):
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
            except Exception as e:
                print_status(f"Could not remove {file_path}: {e}", "WARN")

def generate_test_commands() -> None:
    """Generate test commands for manual execution"""
    commands = f"""
# ADPA Lambda Test Commands

# Health check
aws lambda invoke \\
    --function-name {CONFIG["function_name"]} \\
    --payload '{{"action": "health_check"}}' \\
    --region {CONFIG["region"]} \\
    health_check_response.json

# View health check response
cat health_check_response.json | python -m json.tool

# Pipeline test
aws lambda invoke \\
    --function-name {CONFIG["function_name"]} \\
    --payload '{{"action": "run_pipeline", "dataset_path": "s3://adpa-data-276983626136-development/test.csv", "objective": "classification"}}' \\
    --region {CONFIG["region"]} \\
    pipeline_response.json

# View pipeline response  
cat pipeline_response.json | python -m json.tool

# Function details
aws lambda get-function --function-name {CONFIG["function_name"]} --region {CONFIG["region"]}

# CloudWatch logs
aws logs describe-log-streams \\
    --log-group-name "/aws/lambda/{CONFIG["function_name"]}" \\
    --region {CONFIG["region"]} \\
    --order-by LastEventTime --descending --max-items 5
"""
    
    with open("test_commands.sh", "w") as f:
        f.write(commands)
    
    print_status("Created test_commands.sh")

def main() -> int:
    """Main deployment function"""
    print("🚀 ADPA Lambda Direct Deployment (boto3)")
    print("=" * 50)
    
    # Check prerequisites
    if not BOTO3_AVAILABLE:
        print_status("boto3 library required for deployment", "ERROR")
        return 1
    
    if not os.path.exists("src") or not os.path.exists("lambda_function.py"):
        print_status("Required files not found. Run from ADPA project root.", "ERROR")
        return 1
    
    try:
        # Step 1: Check AWS credentials
        if not check_aws_credentials():
            print_status("AWS credentials check failed", "ERROR")
            return 1
        
        # Step 2: Check if target function exists
        if not check_lambda_function_exists():
            print_status("Target Lambda function check failed", "ERROR")
            return 1
        
        # Step 3: Create deployment package
        if not create_deployment_package():
            print_status("Package creation failed", "ERROR")
            return 1
        
        # Step 4: Deploy to Lambda
        if not deploy_lambda_code():
            print_status("Code deployment failed", "ERROR")
            return 1
        
        # Step 5: Update configuration
        config_success = update_lambda_configuration()
        
        # Step 6: Test deployment
        print_status("Testing deployment...")
        test_result = test_lambda_function()
        
        # Step 7: Generate test commands
        generate_test_commands()
        
        # Step 8: Report results
        print("\n" + "=" * 50)
        print("🎉 ADPA LAMBDA DEPLOYMENT COMPLETED")
        print("=" * 50)
        
        print(f"\n✅ Function: {CONFIG['function_name']}")
        print(f"✅ Region: {CONFIG['region']}")
        print(f"✅ Package: {CONFIG['package_name']}")
        
        if config_success:
            print("✅ Configuration: Updated")
        else:
            print("⚠️  Configuration: Warning (check manually)")
        
        # Test results
        if isinstance(test_result, dict):
            test_status = test_result.get('status', 'unknown')
            if test_status == 'healthy':
                print("✅ Health Check: PASSED")
            else:
                print(f"⚠️  Health Check: {test_status}")
                print("   Check CloudWatch logs for details")
        
        print(f"\n📋 Test Response:")
        print(json.dumps(test_result, indent=2))
        
        print(f"\n📊 Dashboard URL:")
        print(f"https://{CONFIG['region']}.console.aws.amazon.com/lambda/home?region={CONFIG['region']}#/functions/{CONFIG['function_name']}")
        
        print(f"\n📝 Manual test commands saved to: test_commands.sh")
        
        # Cleanup
        cleanup()
        
        return 0
        
    except KeyboardInterrupt:
        print_status("Deployment cancelled by user", "WARN")
        cleanup()
        return 1
    except Exception as e:
        print_status(f"Deployment failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        cleanup()
        return 1

if __name__ == "__main__":
    sys.exit(main())