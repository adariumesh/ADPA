#!/usr/bin/env python3
"""
Create Lambda functions directly using boto3
"""

import boto3
import json
import sys
import zipfile
import io
from botocore.exceptions import ClientError

def create_lambda_functions():
    """Create Lambda functions directly"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-2')
    iam_client = boto3.client('iam', region_name='us-east-2')
    
    print("⚡ Creating Lambda Functions Directly...")
    
    # Step 1: Create IAM role
    role_arn = create_lambda_role(iam_client)
    if not role_arn:
        return False
    
    # Step 2: Create main Lambda function
    main_success = create_main_function(lambda_client, role_arn)
    if not main_success:
        return False
    
    # Step 3: Create error handler function
    error_success = create_error_function(lambda_client, role_arn)
    if not error_success:
        return False
    
    print("🎉 Lambda functions created successfully!")
    return True

def create_lambda_role(iam_client):
    """Create IAM role for Lambda functions"""
    
    role_name = 'adpa-lambda-execution-role-development'
    
    try:
        # Check if role exists
        try:
            response = iam_client.get_role(RoleName=role_name)
            print(f"✅ IAM role already exists: {role_name}")
            return response['Role']['Arn']
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchEntity':
                raise
        
        # Create trust policy
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        # Create role
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Execution role for ADPA Lambda functions'
        )
        
        role_arn = response['Role']['Arn']
        print(f"✅ Created IAM role: {role_name}")
        
        # Attach managed policies
        policies_to_attach = [
            'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
            'arn:aws:iam::aws:policy/AmazonS3FullAccess',
            'arn:aws:iam::aws:policy/AmazonBedrockFullAccess',
            'arn:aws:iam::aws:policy/CloudWatchFullAccess'
        ]
        
        for policy_arn in policies_to_attach:
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
        
        print("✅ Attached managed policies to role")
        
        # Wait a moment for role propagation
        import time
        time.sleep(10)
        
        return role_arn
        
    except Exception as e:
        print(f"❌ Failed to create IAM role: {e}")
        return None

def create_main_function(lambda_client, role_arn):
    """Create main ADPA Lambda function"""
    
    function_name = 'adpa-data-processor-development'
    
    try:
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=function_name)
            print(f"✅ Main function already exists: {function_name}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        # Create function code
        lambda_code = '''
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Processing event: {event}")
    
    action = event.get('action', 'health_check')
    
    if action == 'health_check':
        return {
            'status': 'healthy',
            'message': 'ADPA Lambda function is operational',
            'components': {
                'imports': False,
                'agent': False,
                'monitoring': False
            },
            'aws_config': {
                'region': 'us-east-2',
                'data_bucket': 'adpa-data-083308938449-development'
            }
        }
    
    return {
        'status': 'placeholder',
        'message': 'ADPA code will be deployed here',
        'action': action
    }
'''
        
        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('lambda_function.py', lambda_code)
        
        zip_content = zip_buffer.getvalue()
        
        # Create function
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.11',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_content},
            Description='ADPA Main Data Processing Function',
            Timeout=900,
            MemorySize=1024,
            Environment={
                'Variables': {
                    'ENVIRONMENT': 'development',
                    'DATA_BUCKET': 'adpa-data-083308938449-development',
                    'MODEL_BUCKET': 'adpa-models-083308938449-development'
                }
            }
        )
        
        print(f"✅ Created main function: {function_name}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create main function: {e}")
        return False

def create_error_function(lambda_client, role_arn):
    """Create error handler Lambda function"""
    
    function_name = 'adpa-error-handler-development'
    
    try:
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=function_name)
            print(f"✅ Error function already exists: {function_name}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        # Create function code
        lambda_code = '''
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.error(f"Pipeline error occurred: {event}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'analyzed',
            'message': 'Error handler operational',
            'recovery_recommended': True,
            'next_steps': ['investigate_logs', 'retry_operation']
        })
    }
'''
        
        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('error_handler.py', lambda_code)
        
        zip_content = zip_buffer.getvalue()
        
        # Create function
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.11',
            Role=role_arn,
            Handler='error_handler.lambda_handler',
            Code={'ZipFile': zip_content},
            Description='ADPA Error Handler Function',
            Timeout=300,
            MemorySize=512,
            Environment={
                'Variables': {
                    'ENVIRONMENT': 'development'
                }
            }
        )
        
        print(f"✅ Created error function: {function_name}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create error function: {e}")
        return False

if __name__ == "__main__":
    success = create_lambda_functions()
    sys.exit(0 if success else 1)