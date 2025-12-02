#!/usr/bin/env python3
"""
Simple infrastructure check - no heredocs, pure Python
"""

import boto3

def check_infrastructure():
    print("🔍 Checking ADPA Infrastructure...")
    
    try:
        # Check AWS credentials
        sts = boto3.client('sts', region_name='us-east-2')
        identity = sts.get_caller_identity()
        print(f"✅ AWS Credentials OK")
        print(f"   Account: {identity.get('Account', 'Unknown')}")
        print(f"   User: {identity.get('Arn', 'Unknown').split('/')[-1] if identity.get('Arn') else 'Unknown'}")
        
        # Check Lambda function
        lambda_client = boto3.client('lambda', region_name='us-east-2')
        try:
            response = lambda_client.get_function(FunctionName='adpa-data-processor-development')
            print("✅ Lambda function 'adpa-data-processor-development' exists")
            print(f"   Runtime: {response['Configuration'].get('Runtime', 'Unknown')}")
            print(f"   Memory: {response['Configuration'].get('MemorySize', 'Unknown')} MB")
            return True
        except lambda_client.exceptions.ResourceNotFoundException:
            print("❌ Lambda function 'adpa-data-processor-development' NOT found")
            print("   Need to create infrastructure first")
            return False
            
    except Exception as e:
        print(f"❌ Infrastructure check failed: {e}")
        return False

if __name__ == "__main__":
    check_infrastructure()