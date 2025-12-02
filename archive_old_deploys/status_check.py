#!/usr/bin/env python3
"""
ADPA Status Check and Manual Deployment
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

print("🔍 ADPA DEPLOYMENT STATUS CHECK")
print("=" * 60)
print(f"Timestamp: {datetime.now()}")
print(f"Working Directory: {os.getcwd()}")
print(f"Python Version: {sys.version}")

# Check boto3
print("\n📦 Checking boto3...")
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
        
        aws_available = True
    except Exception as e:
        print(f"❌ AWS credentials failed: {e}")
        aws_available = False
        
except ImportError:
    print("❌ boto3 not available")
    aws_available = False

# Check file structure
print("\n📁 Checking file structure...")
critical_files = {
    "src": "Source code directory",
    "lambda_function.py": "Lambda handler",
    "config": "Configuration directory", 
    "deploy/cloudformation/adpa-infrastructure.yaml": "CloudFormation template",
    "boto3_deploy.py": "Direct deployment script",
    "complete_manual_deployment.py": "Manual deployment script"
}

file_status = {}
for file_path, description in critical_files.items():
    path = Path(file_path)
    exists = path.exists()
    file_status[file_path] = exists
    status = "✅" if exists else "❌"
    print(f"{status} {file_path} - {description}")

if aws_available:
    print("\n☁️  Checking AWS resources...")
    
    # Check CloudFormation stacks
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
            print("✅ CloudFormation stacks:")
            for stack in adpa_stacks:
                print(f"   - {stack['StackName']}: {stack['StackStatus']}")
                if stack['StackStatus'] == 'CREATE_COMPLETE':
                    print(f"     ✅ Stack is ready for use")
                elif 'PROGRESS' in stack['StackStatus']:
                    print(f"     🔄 Stack is still being processed")
                elif 'FAILED' in stack['StackStatus']:
                    print(f"     ❌ Stack has failed")
        else:
            print("❌ No ADPA CloudFormation stacks found")
            
    except Exception as e:
        print(f"❌ CloudFormation check failed: {e}")
    
    # Check Lambda functions
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-2')
        functions = lambda_client.list_functions()
        adpa_functions = [f for f in functions['Functions'] if 'adpa' in f['FunctionName'].lower()]
        
        if adpa_functions:
            print("✅ Lambda functions:")
            for func in adpa_functions:
                print(f"   - {func['FunctionName']}: {func['Runtime']}")
                # Try to get function details
                try:
                    details = lambda_client.get_function(FunctionName=func['FunctionName'])
                    code_size = details['Configuration']['CodeSize']
                    last_modified = details['Configuration']['LastModified']
                    print(f"     Size: {code_size} bytes, Modified: {last_modified}")
                except Exception as e:
                    print(f"     Error getting details: {e}")
        else:
            print("❌ No ADPA Lambda functions found")
            
    except Exception as e:
        print(f"❌ Lambda check failed: {e}")
    
    # Check S3 buckets
    try:
        s3 = boto3.client('s3', region_name='us-east-2')
        buckets = s3.list_buckets()
        adpa_buckets = [b for b in buckets['Buckets'] if 'adpa' in b['Name'].lower()]
        
        if adpa_buckets:
            print("✅ S3 buckets:")
            for bucket in adpa_buckets:
                print(f"   - {bucket['Name']}")
                # Check bucket contents
                try:
                    objects = s3.list_objects_v2(Bucket=bucket['Name'], MaxKeys=5)
                    if 'Contents' in objects:
                        print(f"     Contains {len(objects['Contents'])} objects (showing first 5)")
                    else:
                        print(f"     Empty bucket")
                except Exception as e:
                    print(f"     Error accessing bucket: {e}")
        else:
            print("❌ No ADPA S3 buckets found")
            
    except Exception as e:
        print(f"❌ S3 check failed: {e}")

# Summary and recommendations
print("\n" + "=" * 60)
print("📋 SUMMARY AND RECOMMENDATIONS")
print("=" * 60)

if not aws_available:
    print("❌ CRITICAL: AWS/boto3 not available")
    print("   Install boto3: pip install boto3")
    print("   Configure AWS credentials: aws configure")

elif not all(file_status[f] for f in ["src", "lambda_function.py"]):
    print("❌ CRITICAL: Missing core application files")
    print("   Ensure you're in the correct ADPA project directory")

else:
    print("✅ Environment looks ready for deployment")
    
    # Try to run one of the deployment scripts
    print("\n🚀 ATTEMPTING AUTOMATIC DEPLOYMENT...")
    
    # Try the comprehensive deployment
    try:
        print("Running comprehensive deployment...")
        exec(open("comprehensive_deploy.py").read())
        
    except Exception as e:
        print(f"❌ Comprehensive deployment failed: {e}")
        
        # Try the boto3 deployment
        try:
            print("\\nTrying boto3 deployment...")
            exec(open("boto3_deploy.py").read())
            
        except Exception as e2:
            print(f"❌ boto3 deployment failed: {e2}")
            
            # Try the manual deployment
            try:
                print("\\nTrying manual deployment...")
                exec(open("complete_manual_deployment.py").read())
                
            except Exception as e3:
                print(f"❌ Manual deployment failed: {e3}")
                print("\\n⚠️  All automatic deployment attempts failed")
                print("Manual intervention may be required")

print(f"\\n{'='*60}")
print("STATUS CHECK COMPLETED")
print(f"{'='*60}")