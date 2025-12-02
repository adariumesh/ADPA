#!/usr/bin/env python3
"""
Simple infrastructure creation - creates Lambda function if it doesn't exist
"""

import boto3
import json

def create_lambda_function():
    print("🏗️  Creating ADPA Lambda Infrastructure...")
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-2')
        iam_client = boto3.client('iam', region_name='us-east-2')
        
        # Check if function already exists
        try:
            lambda_client.get_function(FunctionName='adpa-data-processor-development')
            print("✅ Lambda function already exists")
            return True
        except lambda_client.exceptions.ResourceNotFoundException:
            print("Creating new Lambda function...")
        
        # Create basic Lambda execution role
        role_name = 'adpa-lambda-execution-role'
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            # Create role
            iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy)
            )
            print(f"✅ Created IAM role: {role_name}")
        except iam_client.exceptions.EntityAlreadyExistsException:
            print(f"✅ IAM role already exists: {role_name}")
        
        # Attach basic Lambda execution policy
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        # Get role ARN
        role_response = iam_client.get_role(RoleName=role_name)
        role_arn = role_response['Role']['Arn']
        
        # Simple Lambda function code
        simple_code = '''
def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': {
            'status': 'healthy',
            'message': 'ADPA Lambda function ready for deployment'
        }
    }
'''
        
        import zipfile
        import tempfile
        import os
        
        # Create minimal ZIP
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip.name, 'w') as zf:
                zf.writestr('lambda_function.py', simple_code)
            
            with open(tmp_zip.name, 'rb') as f:
                zip_content = f.read()
            
            os.unlink(tmp_zip.name)
        
        # Create Lambda function
        response = lambda_client.create_function(
            FunctionName='adpa-data-processor-development',
            Runtime='python3.9',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_content},
            Description='ADPA Data Processing Agent',
            Timeout=900,
            MemorySize=512,
            Environment={
                'Variables': {
                    'AWS_REGION': 'us-east-2',
                    'ENVIRONMENT': 'development'
                }
            }
        )
        
        print("✅ Created Lambda function: adpa-data-processor-development")
        print(f"   Function ARN: {response['FunctionArn']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Infrastructure creation failed: {e}")
        return False

if __name__ == "__main__":
    success = create_lambda_function()
    if success:
        print("\n🎉 Infrastructure ready! Now run deployment.")
    else:
        print("\n❌ Infrastructure creation failed.")