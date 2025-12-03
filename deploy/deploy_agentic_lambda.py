#!/usr/bin/env python3
"""
Deploy the ADPA Agentic Lambda Function
This script packages and deploys the new AI-powered Lambda
"""

import os
import sys
import json
import shutil
import zipfile
import subprocess
from datetime import datetime

# Configuration
AWS_REGION = "us-east-2"
AWS_ACCOUNT_ID = "083308938449"
LAMBDA_FUNCTION_NAME = "adpa-lambda-function"  # Main ADPA Lambda
LAMBDA_TIMEOUT = 900  # 15 minutes
LAMBDA_MEMORY = 512

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILE = os.path.join(SCRIPT_DIR, "lambda_function_agentic.py")
TEMP_DIR = "/tmp/adpa_lambda_deploy"
PACKAGE_FILE = os.path.join(TEMP_DIR, "adpa_agentic_lambda.zip")


def run_command(cmd, capture=False):
    """Run a shell command"""
    print(f"Running: {cmd}")
    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.returncode
    else:
        result = subprocess.run(cmd, shell=True)
        return None, result.returncode


def create_package():
    """Create Lambda deployment package"""
    print("\n=== Creating Lambda Deployment Package ===")
    
    # Clean up temp directory
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)
    
    package_dir = os.path.join(TEMP_DIR, "package")
    os.makedirs(package_dir)
    
    # Copy source file and rename to lambda_function.py
    dest_file = os.path.join(package_dir, "lambda_function.py")
    shutil.copy(SOURCE_FILE, dest_file)
    print(f"Copied {SOURCE_FILE} to {dest_file}")
    
    # Create zip file
    with zipfile.ZipFile(PACKAGE_FILE, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, package_dir)
                zf.write(file_path, arc_name)
    
    print(f"Created package: {PACKAGE_FILE}")
    print(f"Package size: {os.path.getsize(PACKAGE_FILE) / 1024:.1f} KB")
    return PACKAGE_FILE


def check_lambda_exists():
    """Check if Lambda function exists"""
    stdout, returncode = run_command(
        f"aws lambda get-function --function-name {LAMBDA_FUNCTION_NAME} --region {AWS_REGION} 2>/dev/null",
        capture=True
    )
    return returncode == 0


def backup_current_lambda():
    """Backup the current Lambda function code"""
    print("\n=== Backing Up Current Lambda ===")
    backup_file = os.path.join(TEMP_DIR, f"backup_{LAMBDA_FUNCTION_NAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
    
    stdout, _ = run_command(
        f"aws lambda get-function --function-name {LAMBDA_FUNCTION_NAME} --region {AWS_REGION} --query 'Code.Location' --output text",
        capture=True
    )
    
    if stdout and stdout.strip():
        download_url = stdout.strip()
        run_command(f"curl -s -o {backup_file} '{download_url}'")
        print(f"Backup saved to: {backup_file}")
        return backup_file
    else:
        print("Could not get current Lambda code URL")
        return None


def update_lambda_code():
    """Update Lambda function code"""
    print("\n=== Updating Lambda Function Code ===")
    
    cmd = f"""aws lambda update-function-code \
        --function-name {LAMBDA_FUNCTION_NAME} \
        --zip-file fileb://{PACKAGE_FILE} \
        --region {AWS_REGION}"""
    
    _, returncode = run_command(cmd)
    
    if returncode == 0:
        print("✅ Lambda code updated successfully!")
        return True
    else:
        print("❌ Failed to update Lambda code")
        return False


def update_lambda_configuration():
    """Update Lambda configuration"""
    print("\n=== Updating Lambda Configuration ===")
    
    env_vars = {
        "Variables": {
            "AWS_REGION": AWS_REGION,
            "DATA_BUCKET": f"adpa-data-{AWS_ACCOUNT_ID}-production",
            "MODEL_BUCKET": f"adpa-models-{AWS_ACCOUNT_ID}-production",
            "PIPELINES_TABLE": "adpa-pipelines",
            "BEDROCK_MODEL_ID": "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        }
    }
    
    cmd = f"""aws lambda update-function-configuration \
        --function-name {LAMBDA_FUNCTION_NAME} \
        --timeout {LAMBDA_TIMEOUT} \
        --memory-size {LAMBDA_MEMORY} \
        --environment '{json.dumps(env_vars)}' \
        --region {AWS_REGION}"""
    
    _, returncode = run_command(cmd)
    
    if returncode == 0:
        print("✅ Lambda configuration updated successfully!")
        return True
    else:
        print("❌ Failed to update Lambda configuration")
        return False


def test_lambda():
    """Test the Lambda function"""
    print("\n=== Testing Lambda Function ===")
    
    test_event = json.dumps({
        "httpMethod": "GET",
        "path": "/health"
    })
    
    cmd = f"""aws lambda invoke \
        --function-name {LAMBDA_FUNCTION_NAME} \
        --payload '{test_event}' \
        --cli-binary-format raw-in-base64-out \
        --region {AWS_REGION} \
        /tmp/lambda_response.json"""
    
    _, returncode = run_command(cmd)
    
    if returncode == 0:
        with open("/tmp/lambda_response.json", "r") as f:
            response = json.load(f)
        
        if isinstance(response, dict) and "body" in response:
            body = json.loads(response["body"])
            print("\n📊 Lambda Health Check Response:")
            print(json.dumps(body, indent=2))
            
            if body.get("version") == "4.0.0-agentic":
                print("\n✅ Agentic Lambda is deployed and working!")
                return True
            else:
                print(f"\n⚠️ Version mismatch: {body.get('version')}")
                return False
        else:
            print(f"Response: {response}")
            return True
    else:
        print("❌ Lambda test failed")
        return False


def main():
    """Main deployment process"""
    print("=" * 60)
    print("ADPA Agentic Lambda Deployment")
    print("=" * 60)
    
    # Check if source file exists
    if not os.path.exists(SOURCE_FILE):
        print(f"❌ Source file not found: {SOURCE_FILE}")
        sys.exit(1)
    
    # Check if Lambda exists
    if not check_lambda_exists():
        print(f"❌ Lambda function '{LAMBDA_FUNCTION_NAME}' not found in {AWS_REGION}")
        print("Please create the Lambda function first or update LAMBDA_FUNCTION_NAME")
        sys.exit(1)
    
    print(f"✅ Lambda function '{LAMBDA_FUNCTION_NAME}' found")
    
    # Create package
    package = create_package()
    
    # Backup current Lambda
    backup = backup_current_lambda()
    if backup:
        print(f"✅ Backup created: {backup}")
    
    # Update Lambda code
    if not update_lambda_code():
        print("\n❌ Deployment failed!")
        sys.exit(1)
    
    # Wait for update to propagate
    print("\nWaiting for Lambda update to propagate...")
    import time
    time.sleep(5)
    
    # Update configuration
    update_lambda_configuration()
    
    # Wait again
    print("\nWaiting for configuration update...")
    time.sleep(5)
    
    # Test Lambda
    test_lambda()
    
    print("\n" + "=" * 60)
    print("Deployment Complete!")
    print("=" * 60)
    print(f"""
Next Steps:
1. Test the health endpoint:
   curl https://YOUR_API_GATEWAY_URL/health
   
2. Create a test pipeline:
   curl -X POST https://YOUR_API_GATEWAY_URL/pipelines \\
     -H "Content-Type: application/json" \\
     -d '{{"dataset_path": "your_dataset.csv", "objective": "predict target"}}'

3. Check CloudWatch logs:
   aws logs tail /aws/lambda/{LAMBDA_FUNCTION_NAME} --follow

Backup location: {backup if backup else 'Not created'}
""")


if __name__ == "__main__":
    main()
