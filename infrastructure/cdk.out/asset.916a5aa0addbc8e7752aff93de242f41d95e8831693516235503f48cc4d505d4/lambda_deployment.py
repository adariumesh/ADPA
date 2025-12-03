#!/usr/bin/env python3
"""
AWS Lambda deployment script for ADPA data processor.
"""

import os
import sys
import boto3
import zipfile
import json
from pathlib import Path
import tempfile
import shutil

def create_lambda_package():
    """Create deployment package for Lambda function."""
    print("Creating Lambda deployment package...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Copy Lambda function code
        src_path = Path(__file__).parent.parent / "src" / "aws" / "lambda" / "data_processor.py"
        shutil.copy2(src_path, temp_path / "lambda_function.py")
        
        # Install dependencies
        requirements = [
            "pandas>=2.0.0",
            "numpy>=1.24.0",
            "boto3>=1.34.0"
        ]
        
        # For simplicity, we'll assume pandas and numpy are available in Lambda runtime
        # In production, you'd include them in the package or use Lambda layers
        
        # Create ZIP file
        zip_path = Path(__file__).parent / "adpa_lambda_function.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(temp_path / "lambda_function.py", "lambda_function.py")
        
        print(f"✅ Lambda package created: {zip_path}")
        return zip_path

def deploy_lambda_function(function_name: str, zip_path: Path, region: str = "us-east-1"):
    """Deploy Lambda function to AWS."""
    print(f"Deploying Lambda function: {function_name}")
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Read the ZIP file
    with open(zip_path, 'rb') as zip_file:
        zip_content = zip_file.read()
    
    try:
        # Try to update existing function
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        print(f"✅ Updated existing Lambda function: {function_name}")
        return response['FunctionArn']
        
    except lambda_client.exceptions.ResourceNotFoundException:
        # Function doesn't exist, create it
        print(f"Function doesn't exist, creating new one...")
        
        # Create IAM role for Lambda (simplified)
        iam_role_arn = create_lambda_execution_role(region)
        
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role=iam_role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_content},
            Description='ADPA data processing function',
            Timeout=300,  # 5 minutes
            MemorySize=512,
            Environment={
                'Variables': {
                    'ENVIRONMENT': 'development',
                    'LOG_LEVEL': 'INFO'
                }
            },
            Tags={
                'Project': 'ADPA',
                'Environment': 'Development'
            }
        )
        
        print(f"✅ Created new Lambda function: {function_name}")
        return response['FunctionArn']

def create_lambda_execution_role(region: str) -> str:
    """Create IAM role for Lambda execution."""
    iam_client = boto3.client('iam', region_name=region)
    role_name = 'ADPALambdaExecutionRole'
    
    # Trust policy for Lambda
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
    
    try:
        # Try to get existing role
        response = iam_client.get_role(RoleName=role_name)
        print(f"✅ Using existing IAM role: {role_name}")
        return response['Role']['Arn']
        
    except iam_client.exceptions.NoSuchEntityException:
        # Create new role
        print(f"Creating IAM role: {role_name}")
        
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Execution role for ADPA Lambda functions'
        )
        
        role_arn = response['Role']['Arn']
        
        # Attach basic Lambda execution policy
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        
        # Attach S3 access policy
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess'
        )
        
        print(f"✅ Created IAM role: {role_name}")
        return role_arn

def create_cloudformation_template():
    """Create CloudFormation template for ADPA infrastructure."""
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "ADPA Infrastructure Template",
        "Parameters": {
            "BucketName": {
                "Type": "String",
                "Description": "S3 bucket name for ADPA data storage",
                "Default": "adpa-data-bucket"
            }
        },
        "Resources": {
            "ADPADataBucket": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": {"Ref": "BucketName"},
                    "VersioningConfiguration": {
                        "Status": "Enabled"
                    },
                    "PublicAccessBlockConfiguration": {
                        "BlockPublicAcls": True,
                        "BlockPublicPolicy": True,
                        "IgnorePublicAcls": True,
                        "RestrictPublicBuckets": True
                    },
                    "Tags": [
                        {"Key": "Project", "Value": "ADPA"},
                        {"Key": "Environment", "Value": "Development"}
                    ]
                }
            },
            "ADPALambdaExecutionRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "RoleName": "ADPALambdaExecutionRole",
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "lambda.amazonaws.com"},
                                "Action": "sts:AssumeRole"
                            }
                        ]
                    },
                    "ManagedPolicyArns": [
                        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                        "arn:aws:iam::aws:policy/AmazonS3FullAccess"
                    ],
                    "Tags": [
                        {"Key": "Project", "Value": "ADPA"}
                    ]
                }
            },
            "ADPAStepFunctionsRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "RoleName": "ADPAStepFunctionsRole",
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "states.amazonaws.com"},
                                "Action": "sts:AssumeRole"
                            }
                        ]
                    },
                    "Policies": [
                        {
                            "PolicyName": "ADPAStepFunctionsPolicy",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": [
                                            "lambda:InvokeFunction"
                                        ],
                                        "Resource": "*"
                                    }
                                ]
                            }
                        }
                    ],
                    "Tags": [
                        {"Key": "Project", "Value": "ADPA"}
                    ]
                }
            }
        },
        "Outputs": {
            "BucketName": {
                "Description": "Name of the S3 bucket",
                "Value": {"Ref": "ADPADataBucket"},
                "Export": {"Name": "ADPA-S3-Bucket"}
            },
            "LambdaRoleArn": {
                "Description": "ARN of the Lambda execution role",
                "Value": {"Fn::GetAtt": ["ADPALambdaExecutionRole", "Arn"]},
                "Export": {"Name": "ADPA-Lambda-Role-ARN"}
            },
            "StepFunctionsRoleArn": {
                "Description": "ARN of the Step Functions execution role",
                "Value": {"Fn::GetAtt": ["ADPAStepFunctionsRole", "Arn"]},
                "Export": {"Name": "ADPA-StepFunctions-Role-ARN"}
            }
        }
    }
    
    template_path = Path(__file__).parent / "adpa_infrastructure.yaml"
    
    # Convert to YAML format (simplified JSON for now)
    with open(template_path, 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"✅ CloudFormation template created: {template_path}")
    return template_path

def main():
    """Main deployment function."""
    print("🚀 ADPA AWS Lambda Deployment")
    print("=" * 40)
    
    function_name = "adpa-data-processor"
    region = "us-east-1"
    
    try:
        # Step 1: Create deployment package
        zip_path = create_lambda_package()
        
        # Step 2: Deploy Lambda function
        function_arn = deploy_lambda_function(function_name, zip_path, region)
        
        # Step 3: Create CloudFormation template
        template_path = create_cloudformation_template()
        
        print("\n✅ Deployment completed successfully!")
        print(f"Lambda Function ARN: {function_arn}")
        print(f"CloudFormation Template: {template_path}")
        
        print("\nNext steps:")
        print("1. Deploy the CloudFormation template to create S3 bucket and IAM roles")
        print("2. Update the demo script with the actual Lambda function ARN")
        print("3. Run the integration demo")
        
    except Exception as e:
        print(f"❌ Deployment failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())