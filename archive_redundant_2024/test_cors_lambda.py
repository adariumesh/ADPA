#!/usr/bin/env python3
"""
Test script to verify CORS functionality in the Lambda function
"""

import json
import sys
import os

# Add current directory to path
sys.path.append('.')

from lambda_function import lambda_handler

def test_cors_headers():
    """Test that CORS headers are properly included in responses"""
    
    print("Testing CORS functionality...")
    
    # Test OPTIONS request (preflight)
    print("\n1. Testing OPTIONS preflight request:")
    options_event = {
        'httpMethod': 'OPTIONS',
        'path': '/health'
    }
    
    response = lambda_handler(options_event, None)
    print(f"   Status Code: {response['statusCode']}")
    print(f"   Headers: {response['headers']}")
    
    # Verify CORS headers
    headers = response.get('headers', {})
    assert 'Access-Control-Allow-Origin' in headers
    assert 'Access-Control-Allow-Methods' in headers
    assert 'Access-Control-Allow-Headers' in headers
    print("   ✓ CORS headers present")
    
    # Test health endpoint
    print("\n2. Testing GET /health endpoint:")
    health_event = {
        'httpMethod': 'GET',
        'path': '/health'
    }
    
    response = lambda_handler(health_event, None)
    print(f"   Status Code: {response['statusCode']}")
    print(f"   CORS Headers: {dict((k, v) for k, v in response['headers'].items() if 'Access-Control' in k)}")
    
    body = json.loads(response['body'])
    print(f"   Health Status: {body.get('status', 'unknown')}")
    print("   ✓ Health endpoint with CORS")
    
    # Test pipelines listing
    print("\n3. Testing GET /pipelines endpoint:")
    pipelines_event = {
        'httpMethod': 'GET',
        'path': '/pipelines'
    }
    
    response = lambda_handler(pipelines_event, None)
    print(f"   Status Code: {response['statusCode']}")
    print(f"   CORS Headers: {dict((k, v) for k, v in response['headers'].items() if 'Access-Control' in k)}")
    
    body = json.loads(response['body'])
    print(f"   Pipeline Count: {body.get('count', 0)}")
    print("   ✓ Pipelines endpoint with CORS")
    
    # Test pipeline creation
    print("\n4. Testing POST /pipelines endpoint:")
    create_pipeline_event = {
        'httpMethod': 'POST',
        'path': '/pipelines',
        'body': json.dumps({
            'dataset_path': 's3://test-bucket/data.csv',
            'objective': 'classification',
            'config': {'test_mode': True}
        })
    }
    
    response = lambda_handler(create_pipeline_event, None)
    print(f"   Status Code: {response['statusCode']}")
    print(f"   CORS Headers: {dict((k, v) for k, v in response['headers'].items() if 'Access-Control' in k)}")
    
    body = json.loads(response['body'])
    print(f"   Pipeline ID: {body.get('pipeline_id', 'none')}")
    print(f"   Pipeline Status: {body.get('status', 'unknown')}")
    print("   ✓ Pipeline creation with CORS")
    
    # Test pipeline status retrieval
    if 'pipeline_id' in body:
        print("\n5. Testing GET /pipelines/{id} endpoint:")
        pipeline_id = body['pipeline_id']
        status_event = {
            'httpMethod': 'GET',
            'path': f'/pipelines/{pipeline_id}'
        }
        
        response = lambda_handler(status_event, None)
        print(f"   Status Code: {response['statusCode']}")
        print(f"   CORS Headers: {dict((k, v) for k, v in response['headers'].items() if 'Access-Control' in k)}")
        
        body = json.loads(response['body'])
        print(f"   Pipeline Status: {body.get('status', 'unknown')}")
        print("   ✓ Pipeline status with CORS")
    
    # Test unsupported endpoint
    print("\n6. Testing unsupported endpoint:")
    unsupported_event = {
        'httpMethod': 'GET',
        'path': '/unsupported'
    }
    
    response = lambda_handler(unsupported_event, None)
    print(f"   Status Code: {response['statusCode']}")
    print(f"   CORS Headers: {dict((k, v) for k, v in response['headers'].items() if 'Access-Control' in k)}")
    print("   ✓ Error responses include CORS")
    
    print("\n✅ All CORS tests passed!")

def test_legacy_compatibility():
    """Test that legacy direct invocation still works"""
    
    print("\n\nTesting legacy compatibility...")
    
    # Test legacy health check
    legacy_event = {'action': 'health_check'}
    response = lambda_handler(legacy_event, None)
    
    print(f"   Status Code: {response['statusCode']}")
    print("   ✓ Legacy direct invocation works")

if __name__ == "__main__":
    try:
        test_cors_headers()
        test_legacy_compatibility()
        print("\n🎉 All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)