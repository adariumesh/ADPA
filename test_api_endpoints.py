#!/usr/bin/env python3
"""Test all ADPA API endpoints"""
import requests
import json
import time

API_URL = "https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod"

def test_endpoints():
    """Test all 8 API endpoints"""
    
    print("=" * 60)
    print("ADPA API Endpoint Tests")
    print("=" * 60)
    print(f"API URL: {API_URL}\n")
    
    # Test 1: Health check
    print("1️⃣ Testing GET /health")
    try:
        resp = requests.get(f"{API_URL}/health", timeout=10)
        print(f"   ✅ Status: {resp.status_code}")
        print(f"   Response: {resp.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 2: Create pipeline
    print("2️⃣ Testing POST /pipelines")
    pipeline_data = {
        "dataset_path": "s3://adpa-data-083308938449-production/demo_customer_churn.csv",
        "objective": "Predict customer churn with high accuracy"
    }
    try:
        resp = requests.post(f"{API_URL}/pipelines", json=pipeline_data, timeout=15)
        print(f"   ✅ Status: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"   Response: {json.dumps(result, indent=2)}")
            pipeline_id = result.get('pipeline_id', 'test-123')
        else:
            print(f"   Response: {resp.text[:300]}")
            pipeline_id = "test-123"
    except Exception as e:
        print(f"   ❌ Error: {e}")
        pipeline_id = "test-123"
    print()
    
    # Test 3: List pipelines
    print("3️⃣ Testing GET /pipelines")
    try:
        resp = requests.get(f"{API_URL}/pipelines", timeout=10)
        print(f"   ✅ Status: {resp.status_code}")
        print(f"   Response: {resp.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 4: Get specific pipeline
    print(f"4️⃣ Testing GET /pipelines/{pipeline_id}")
    try:
        resp = requests.get(f"{API_URL}/pipelines/{pipeline_id}", timeout=10)
        print(f"   ✅ Status: {resp.status_code}")
        print(f"   Response: {resp.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 5: Execute pipeline
    print(f"5️⃣ Testing POST /pipelines/{pipeline_id}/execute")
    try:
        resp = requests.post(f"{API_URL}/pipelines/{pipeline_id}/execute", timeout=10)
        print(f"   ✅ Status: {resp.status_code}")
        print(f"   Response: {resp.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 6: Get pipeline status
    print(f"6️⃣ Testing GET /pipelines/{pipeline_id}/status")
    try:
        resp = requests.get(f"{API_URL}/pipelines/{pipeline_id}/status", timeout=10)
        print(f"   ✅ Status: {resp.status_code}")
        print(f"   Response: {resp.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 7: List uploads
    print("7️⃣ Testing GET /data/uploads")
    try:
        resp = requests.get(f"{API_URL}/data/uploads", timeout=10)
        print(f"   ✅ Status: {resp.status_code}")
        print(f"   Response: {resp.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 8: Upload data
    print("8️⃣ Testing POST /data/upload")
    upload_data = {
        "filename": "test_upload.csv",
        "content": "col1,col2,col3\n1,2,3\n4,5,6"
    }
    try:
        resp = requests.post(f"{API_URL}/data/upload", json=upload_data, timeout=15)
        print(f"   ✅ Status: {resp.status_code}")
        print(f"   Response: {resp.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    print("=" * 60)
    print("✅ All endpoint tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_endpoints()
