#!/usr/bin/env python3
"""Basic environment and AWS checks"""

import sys
import os
from pathlib import Path

print("=" * 60)
print("BASIC ENVIRONMENT CHECK")
print("=" * 60)

# Set working directory
project_dir = Path("/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa")
os.chdir(project_dir)
print(f"Working directory: {os.getcwd()}")

# Check Python version
print(f"Python version: {sys.version}")

# Check if critical files exist
critical_files = [
    "src",
    "lambda_function.py", 
    "config",
    "deploy/cloudformation/adpa-infrastructure.yaml"
]

print("\nFile checks:")
for file_path in critical_files:
    path = Path(file_path)
    exists = "✅" if path.exists() else "❌"
    print(f"{exists} {file_path}")

# Check boto3 availability
try:
    import boto3
    print("\n✅ boto3 is available")
    
    # Quick AWS credential test
    try:
        sts = boto3.client('sts', region_name='us-east-2')
        identity = sts.get_caller_identity()
        print(f"✅ AWS credentials work: {identity.get('Arn', 'Unknown')}")
        
        # Check existing resources
        print("\n" + "=" * 60)
        print("CHECKING EXISTING AWS RESOURCES")
        print("=" * 60)
        
        # CloudFormation stacks
        try:
            cf = boto3.client('cloudformation', region_name='us-east-2')
            stacks = cf.list_stacks()
            adpa_stacks = [s for s in stacks['StackSummaries'] if 'adpa' in s['StackName'].lower()]
            
            if adpa_stacks:
                print("CloudFormation stacks:")
                for stack in adpa_stacks:
                    print(f"  - {stack['StackName']}: {stack['StackStatus']}")
            else:
                print("❌ No ADPA CloudFormation stacks found")
                
        except Exception as e:
            print(f"❌ CloudFormation check failed: {e}")
        
        # Lambda functions  
        try:
            lambda_client = boto3.client('lambda', region_name='us-east-2')
            functions = lambda_client.list_functions()
            adpa_functions = [f for f in functions['Functions'] if 'adpa' in f['FunctionName'].lower()]
            
            if adpa_functions:
                print("Lambda functions:")
                for func in adpa_functions:
                    print(f"  - {func['FunctionName']}")
            else:
                print("❌ No ADPA Lambda functions found")
                    
        except Exception as e:
            print(f"❌ Lambda check failed: {e}")
            
        # S3 buckets
        try:
            s3 = boto3.client('s3', region_name='us-east-2')
            buckets = s3.list_buckets()
            adpa_buckets = [b for b in buckets['Buckets'] if 'adpa' in b['Name'].lower()]
            
            if adpa_buckets:
                print("S3 buckets:")
                for bucket in adpa_buckets:
                    print(f"  - {bucket['Name']}")
            else:
                print("❌ No ADPA S3 buckets found")
                    
        except Exception as e:
            print(f"❌ S3 check failed: {e}")
        
    except Exception as e:
        print(f"❌ AWS credential test failed: {e}")
        
except ImportError:
    print("❌ boto3 is not available")

print("\n" + "=" * 60)
print("ENVIRONMENT CHECK COMPLETED")
print("=" * 60)