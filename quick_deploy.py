#!/usr/bin/env python3
"""
Quick ADPA API Deployment Script - No ML layer needed
"""

import boto3
import json
import os
import sys
import zipfile
from pathlib import Path

# Import centralized AWS configuration
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config.aws_config import (
        AWS_ACCOUNT_ID, AWS_REGION, DATA_BUCKET, MODEL_BUCKET,
        LAMBDA_FUNCTION_NAME, get_credentials_from_csv
    )
    REGION = AWS_REGION
    FUNCTION_NAME = LAMBDA_FUNCTION_NAME
except ImportError:
    # Fallback values
    AWS_ACCOUNT_ID = "083308938449"
    REGION = "us-east-2"
    FUNCTION_NAME = "adpa-data-processor-development"
    DATA_BUCKET = f"adpa-data-{AWS_ACCOUNT_ID}-development"
    MODEL_BUCKET = f"adpa-models-{AWS_ACCOUNT_ID}-development"
    get_credentials_from_csv = None

ROLE_NAME = "adpa-lambda-execution-role-development"

def deploy():
    print("🚀 Deploying ADPA API Lambda...")
    print(f"   Account: {AWS_ACCOUNT_ID}")
    print(f"   Region: {REGION}")
    
    # Create deployment package
    print("📦 Creating deployment package...")
    zip_path = "adpa-simple-deployment.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Use the simple lambda function
        zipf.write("lambda_function_simple.py", "lambda_function.py")
    
    size_kb = os.path.getsize(zip_path) / 1024
    print(f"   ✅ Package created: {zip_path} ({size_kb:.1f} KB)")
    
    # Get clients with credentials from rootkey.csv if available
    try:
        if get_credentials_from_csv:
            creds = get_credentials_from_csv()
            if creds['access_key_id'] and creds['secret_access_key']:
                lambda_client = boto3.client(
                    'lambda', 
                    region_name=REGION,
                    aws_access_key_id=creds['access_key_id'],
                    aws_secret_access_key=creds['secret_access_key']
                )
                iam_client = boto3.client(
                    'iam',
                    aws_access_key_id=creds['access_key_id'],
                    aws_secret_access_key=creds['secret_access_key']
                )
                print("   ✅ Using credentials from rootkey.csv")
            else:
                raise ValueError("No credentials found")
        else:
            raise ValueError("Config module not available")
    except Exception:
        lambda_client = boto3.client('lambda', region_name=REGION)
        iam_client = boto3.client('iam')
        print("   ⚠️  Using default AWS credential chain")
    
    # Get role ARN
    role_response = iam_client.get_role(RoleName=ROLE_NAME)
    role_arn = role_response['Role']['Arn']
    print(f"   ✅ IAM Role: {ROLE_NAME}")
    
    # Read zip file
    with open(zip_path, 'rb') as f:
        code_bytes = f.read()
    
    # Deploy Lambda
    print("🚀 Deploying to AWS Lambda...")
    try:
        # Try to update existing function
        lambda_client.get_function(FunctionName=FUNCTION_NAME)
        
        response = lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=code_bytes
        )
        print("   ✅ Updated existing function")
        
        # Wait for update
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(FunctionName=FUNCTION_NAME)
        
        # Update configuration (remove layer requirement)
        lambda_client.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Runtime='python3.11',
            Handler='lambda_function.lambda_handler',
            Role=role_arn,
            Timeout=60,
            MemorySize=512,
            Layers=[],  # No layers needed
            Environment={
                'Variables': {
                    'DATA_BUCKET': DATA_BUCKET,
                    'MODEL_BUCKET': MODEL_BUCKET
                }
            }
        )
        print("   ✅ Configuration updated")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        # Create new function
        response = lambda_client.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime='python3.11',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': code_bytes},
            Timeout=60,
            MemorySize=512,
            Environment={
                'Variables': {
                    'DATA_BUCKET': DATA_BUCKET,
                    'MODEL_BUCKET': MODEL_BUCKET
                }
            }
        )
        print("   ✅ Created new function")
    
    # Test the function
    print("🧪 Testing deployment...")
    import time
    time.sleep(3)
    
    test_response = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        Payload=json.dumps({"action": "health_check"})
    )
    
    result = json.loads(test_response['Payload'].read())
    body = json.loads(result.get('body', '{}'))
    
    if body.get('status') == 'healthy':
        print("   ✅ Health check passed!")
    else:
        print(f"   ⚠️  Health check: {body.get('status', 'unknown')}")
    
    # Clean up
    os.remove(zip_path)
    
    print("\n" + "=" * 60)
    print("✅ DEPLOYMENT SUCCESSFUL")
    print("=" * 60)
    print(f"Function: {FUNCTION_NAME}")
    print(f"Region: {REGION}")
    
    return True


if __name__ == "__main__":
    deploy()
