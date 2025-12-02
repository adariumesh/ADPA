"""
Diagnostic script to understand the numpy import issue in Lambda.
"""

import boto3
import json

def main():
    lambda_client = boto3.client('lambda', region_name='us-east-2')
    
    # Test 1: Check sys.path
    print("🔍 Test 1: Checking Python sys.path...")
    payload = {
        "action": "diagnostic",
        "test": "sys_path"
    }
    
    response = lambda_client.invoke(
        FunctionName='adpa-data-processor-development',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    print(json.dumps(result, indent=2))
    
    # Test 2: List current directory contents
    print("\n🔍 Test 2: Checking current directory...")
    payload = {
        "action": "diagnostic", 
        "test": "list_cwd"
    }
    
    response = lambda_client.invoke(
        FunctionName='adpa-data-processor-development',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    print(json.dumps(result, indent=2))
    
    # Test 3: Check if numpy exists as directory
    print("\n🔍 Test 3: Looking for numpy directories...")
    payload = {
        "action": "diagnostic",
        "test": "find_numpy"
    }
    
    response = lambda_client.invoke(
        FunctionName='adpa-data-processor-development',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
