#!/usr/bin/env python3
"""
Simple ADPA Status Check
"""

import boto3
import json
import sys

def test_adpa_status():
    """Test current ADPA deployment status"""
    
    print("🧪 Testing ADPA System Status")
    print("=" * 50)
    
    try:
        # Initialize Lambda client
        lambda_client = boto3.client('lambda', region_name='us-east-2')
        
        # Test main function
        print("\n📡 Testing Main Function...")
        response = lambda_client.invoke(
            FunctionName='adpa-data-processor-development',
            InvocationType='RequestResponse',
            Payload=json.dumps({"action": "health_check"})
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Status: {result.get('status', 'unknown')}")
        
        # Check if dependencies are working
        print("\n🧠 Testing AI Pipeline...")
        pipeline_response = lambda_client.invoke(
            FunctionName='adpa-data-processor-development',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                "action": "run_pipeline",
                "objective": "Test ML pipeline with mock data",
                "dataset_path": "mock://test-data",
                "config": {"test_mode": True}
            })
        )
        
        pipeline_result = json.loads(pipeline_response['Payload'].read())
        print(f"Pipeline Status: {pipeline_result.get('status', 'unknown')}")
        
        if 'error' in pipeline_result:
            print(f"Pipeline Error: {pipeline_result['error']}")
            return False
        
        print("\n✅ ADPA System Status: OPERATIONAL")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_adpa_status()
    sys.exit(0 if success else 1)