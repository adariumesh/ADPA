#!/usr/bin/env python3
"""
Final ADPA Deployment Report and Execution
Provides comprehensive status and attempts deployment
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Setup
project_root = Path("/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa")
os.chdir(project_root)
sys.path.insert(0, str(project_root))

def print_header(title):
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}")

def print_section(title):
    print(f"\n{'-'*60}")
    print(f" {title}")
    print(f"{'-'*60}")

def check_aws_and_deploy():
    """Check AWS status and attempt deployment"""
    
    print_header("FINAL ADPA DEPLOYMENT EXECUTION")
    print(f"Timestamp: {datetime.now()}")
    print(f"Working Directory: {os.getcwd()}")
    
    # Check boto3
    print_section("Checking Dependencies")
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        print("✅ boto3 is available")
        
        # Test AWS credentials
        try:
            sts = boto3.client('sts', region_name='us-east-2')
            identity = sts.get_caller_identity()
            print(f"✅ AWS credentials valid")
            print(f"   Account: {identity.get('Account', 'Unknown')}")
            print(f"   User: {identity.get('Arn', 'Unknown')}")
            aws_ready = True
            
        except NoCredentialsError:
            print("❌ AWS credentials not configured")
            print("   Run: aws configure")
            return False
        except Exception as e:
            print(f"❌ AWS credentials error: {e}")
            return False
            
    except ImportError:
        print("❌ boto3 not available")
        print("   Run: pip install boto3")
        return False
    
    # Check infrastructure
    print_section("Current Infrastructure Status")
    
    infrastructure_ready = True
    
    # CloudFormation
    try:
        cf = boto3.client('cloudformation', region_name='us-east-2')
        stacks = cf.list_stacks(
            StackStatusFilter=[
                'CREATE_IN_PROGRESS', 'CREATE_COMPLETE', 'UPDATE_IN_PROGRESS', 
                'UPDATE_COMPLETE', 'ROLLBACK_IN_PROGRESS', 'ROLLBACK_COMPLETE'
            ]
        )
        adpa_stacks = [s for s in stacks['StackSummaries'] if 'adpa' in s['StackName'].lower()]
        
        if adpa_stacks:
            print("CloudFormation Stacks:")
            for stack in adpa_stacks:
                status = stack['StackStatus']
                print(f"   - {stack['StackName']}: {status}")
                if status not in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                    infrastructure_ready = False
        else:
            print("⚠️  No ADPA CloudFormation stacks found")
            infrastructure_ready = False
            
    except Exception as e:
        print(f"❌ CloudFormation check failed: {e}")
        infrastructure_ready = False
    
    # Lambda Functions
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-2')
        functions = lambda_client.list_functions()
        adpa_functions = [f for f in functions['Functions'] if 'adpa' in f['FunctionName'].lower()]
        
        if adpa_functions:
            print("Lambda Functions:")
            for func in adpa_functions:
                print(f"   - {func['FunctionName']}: {func['Runtime']}")
                print(f"     Last Modified: {func['LastModified']}")
                print(f"     Code Size: {func['CodeSize']} bytes")
        else:
            print("⚠️  No ADPA Lambda functions found")
            
    except Exception as e:
        print(f"❌ Lambda check failed: {e}")
    
    # S3 Buckets
    try:
        s3 = boto3.client('s3', region_name='us-east-2')
        buckets = s3.list_buckets()
        adpa_buckets = [b for b in buckets['Buckets'] if 'adpa' in b['Name'].lower()]
        
        if adpa_buckets:
            print("S3 Buckets:")
            for bucket in adpa_buckets:
                print(f"   - {bucket['Name']}")
        else:
            print("⚠️  No ADPA S3 buckets found")
            
    except Exception as e:
        print(f"❌ S3 check failed: {e}")
    
    # Attempt deployment
    print_section("Deployment Execution")
    
    deployment_attempts = [
        ("boto3_deploy.py", "Direct Lambda code update"),
        ("comprehensive_deploy.py", "Full infrastructure + code deployment"),
        ("complete_manual_deployment.py", "Manual step-by-step deployment")
    ]
    
    success = False
    
    for script, description in deployment_attempts:
        print(f"\\nAttempting: {description}")
        print(f"Script: {script}")
        
        try:
            if Path(script).exists():
                print(f"✅ Found {script}")
                
                # Execute the script
                with open(script, 'r') as f:
                    script_content = f.read()
                
                # Create a new namespace for execution
                exec_globals = {
                    '__name__': '__main__',
                    '__file__': str(Path(script).absolute())
                }
                
                exec(script_content, exec_globals)
                print(f"✅ {script} completed successfully")
                success = True
                break
                
            else:
                print(f"❌ {script} not found")
                
        except SystemExit as e:
            if e.code == 0:
                print(f"✅ {script} completed with exit code 0")
                success = True
                break
            else:
                print(f"❌ {script} failed with exit code {e.code}")
        except Exception as e:
            print(f"❌ {script} failed with error: {e}")
            import traceback
            traceback.print_exc()
    
    # Final status
    print_header("DEPLOYMENT SUMMARY")
    
    if success:
        print("✅ DEPLOYMENT SUCCESSFUL")
        print("\\nNext Steps:")
        print("1. Test the Lambda function:")
        print('   aws lambda invoke --function-name adpa-data-processor-development --payload \\')
        print('   \'{"action": "health_check"}\' --region us-east-2 response.json')
        print("\\n2. View the response:")
        print("   cat response.json | python -m json.tool")
        print("\\n3. Check CloudWatch logs:")
        print("   aws logs describe-log-groups --log-group-name-prefix /aws/lambda/adpa")
        
    else:
        print("❌ DEPLOYMENT FAILED")
        print("\\nTroubleshooting:")
        print("1. Check AWS credentials: aws sts get-caller-identity")
        print("2. Ensure you have necessary permissions")
        print("3. Check for existing resources that may conflict")
        print("4. Review CloudFormation console for stack status")
        
    return success

def create_manual_commands():
    """Create manual deployment commands"""
    commands = '''#!/bin/bash
# Manual ADPA Deployment Commands

echo "Manual ADPA Deployment"
echo "======================"

# Check AWS credentials
echo "Checking AWS credentials..."
aws sts get-caller-identity

# Check existing infrastructure
echo "Checking existing stacks..."
aws cloudformation list-stacks --region us-east-2 --query "StackSummaries[?contains(StackName, 'adpa')]"

# Deploy infrastructure if needed
echo "Deploying infrastructure..."
aws cloudformation create-stack \\
    --stack-name adpa-infrastructure-development \\
    --template-body file://deploy/cloudformation/adpa-infrastructure.yaml \\
    --parameters ParameterKey=Environment,ParameterValue=development ParameterKey=AccountId,ParameterValue=083308938449 \\
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \\
    --region us-east-2

# Wait for stack to complete
echo "Waiting for stack completion..."
aws cloudformation wait stack-create-complete --stack-name adpa-infrastructure-development --region us-east-2

# Create deployment package
echo "Creating deployment package..."
python3 boto3_deploy.py

# Test deployment
echo "Testing deployment..."
aws lambda invoke \\
    --function-name adpa-data-processor-development \\
    --payload '{"action": "health_check"}' \\
    --region us-east-2 \\
    test_response.json

cat test_response.json | python -m json.tool
'''
    
    with open("manual_deployment_commands.sh", "w") as f:
        f.write(commands)
    
    print(f"\\n📝 Created manual_deployment_commands.sh")
    print("   Make executable: chmod +x manual_deployment_commands.sh")
    print("   Run: ./manual_deployment_commands.sh")

if __name__ == "__main__":
    try:
        success = check_aws_and_deploy()
        
        if not success:
            print("\\nCreating manual deployment commands...")
            create_manual_commands()
        
        print(f"\\n{'='*80}")
        print(f"EXECUTION COMPLETED AT: {datetime.now()}")
        print(f"{'='*80}")
        
    except KeyboardInterrupt:
        print("\\n⚠️  Execution cancelled by user")
    except Exception as e:
        print(f"\\n❌ Execution failed: {e}")
        import traceback
        traceback.print_exc()