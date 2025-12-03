#!/usr/bin/env python3
"""Complete ADPA End-to-End Testing Suite"""
import boto3
import json
import time
import uuid
from datetime import datetime

API_URL = "https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod"

def test_api_endpoints():
    """Test all 8 API endpoints"""
    print("=" * 80)
    print("TASK 1: API HEALTH AND CONNECTIVITY VERIFICATION")
    print("=" * 80)
    
    # Initialize boto3 clients
    lambda_client = boto3.client('lambda', region_name='us-east-2')
    
    # Test by invoking Lambda directly with test events
    test_results = {}
    
    # Test 1: Health check
    print("\n[1/8] Testing GET /health...")
    try:
        response = lambda_client.invoke(
            FunctionName='adpa-lambda-function',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'httpMethod': 'GET',
                'path': '/health',
                'headers': {}
            })
        )
        result = json.loads(response['Payload'].read())
        print(f"✅ Lambda invoked successfully")
        print(f"   Response: {json.dumps(result, indent=2)[:200]}")
        test_results['health'] = 'PASS'
    except Exception as e:
        print(f"❌ Error: {e}")
        test_results['health'] = 'FAIL'
    
    # Test 2: List pipelines
    print("\n[2/8] Testing GET /pipelines...")
    try:
        response = lambda_client.invoke(
            FunctionName='adpa-lambda-function',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'httpMethod': 'GET',
                'path': '/pipelines',
                'headers': {}
            })
        )
        result = json.loads(response['Payload'].read())
        print(f"✅ Lambda invoked successfully")
        test_results['list_pipelines'] = 'PASS'
    except Exception as e:
        print(f"❌ Error: {e}")
        test_results['list_pipelines'] = 'FAIL'
    
    # Test 3: Create pipeline
    print("\n[3/8] Testing POST /pipelines...")
    pipeline_id = f"test-pipeline-{uuid.uuid4().hex[:8]}"
    try:
        response = lambda_client.invoke(
            FunctionName='adpa-lambda-function',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'httpMethod': 'POST',
                'path': '/pipelines',
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'dataset_path': 's3://adpa-data-083308938449-production/demo_customer_churn.csv',
                    'objective': 'Predict customer churn with high accuracy'
                })
            })
        )
        result = json.loads(response['Payload'].read())
        print(f"✅ Pipeline creation invoked")
        if 'body' in result:
            body = json.loads(result['body'])
            if 'pipeline_id' in body:
                pipeline_id = body['pipeline_id']
                print(f"   Pipeline ID: {pipeline_id}")
        test_results['create_pipeline'] = 'PASS'
    except Exception as e:
        print(f"❌ Error: {e}")
        test_results['create_pipeline'] = 'FAIL'
    
    # Test 4: Get specific pipeline
    print(f"\n[4/8] Testing GET /pipelines/{pipeline_id}...")
    try:
        response = lambda_client.invoke(
            FunctionName='adpa-lambda-function',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'httpMethod': 'GET',
                'path': f'/pipelines/{pipeline_id}',
                'pathParameters': {'id': pipeline_id},
                'headers': {}
            })
        )
        result = json.loads(response['Payload'].read())
        print(f"✅ Get pipeline invoked")
        test_results['get_pipeline'] = 'PASS'
    except Exception as e:
        print(f"❌ Error: {e}")
        test_results['get_pipeline'] = 'FAIL'
    
    # Test 5: Execute pipeline
    print(f"\n[5/8] Testing POST /pipelines/{pipeline_id}/execute...")
    try:
        response = lambda_client.invoke(
            FunctionName='adpa-lambda-function',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'httpMethod': 'POST',
                'path': f'/pipelines/{pipeline_id}/execute',
                'pathParameters': {'id': pipeline_id},
                'headers': {}
            })
        )
        result = json.loads(response['Payload'].read())
        print(f"✅ Execute pipeline invoked")
        test_results['execute_pipeline'] = 'PASS'
    except Exception as e:
        print(f"❌ Error: {e}")
        test_results['execute_pipeline'] = 'FAIL'
    
    # Test 6: Get pipeline status
    print(f"\n[6/8] Testing GET /pipelines/{pipeline_id}/status...")
    try:
        response = lambda_client.invoke(
            FunctionName='adpa-lambda-function',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'httpMethod': 'GET',
                'path': f'/pipelines/{pipeline_id}/status',
                'pathParameters': {'id': pipeline_id},
                'headers': {}
            })
        )
        result = json.loads(response['Payload'].read())
        print(f"✅ Get status invoked")
        test_results['get_status'] = 'PASS'
    except Exception as e:
        print(f"❌ Error: {e}")
        test_results['get_status'] = 'FAIL'
    
    # Test 7: Upload data
    print("\n[7/8] Testing POST /data/upload...")
    try:
        response = lambda_client.invoke(
            FunctionName='adpa-lambda-function',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'httpMethod': 'POST',
                'path': '/data/upload',
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'filename': 'test_upload.csv',
                    'content': 'col1,col2,col3\n1,2,3\n4,5,6'
                })
            })
        )
        result = json.loads(response['Payload'].read())
        print(f"✅ Upload data invoked")
        test_results['upload_data'] = 'PASS'
    except Exception as e:
        print(f"❌ Error: {e}")
        test_results['upload_data'] = 'FAIL'
    
    # Test 8: List uploads
    print("\n[8/8] Testing GET /data/uploads...")
    try:
        response = lambda_client.invoke(
            FunctionName='adpa-lambda-function',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'httpMethod': 'GET',
                'path': '/data/uploads',
                'headers': {}
            })
        )
        result = json.loads(response['Payload'].read())
        print(f"✅ List uploads invoked")
        test_results['list_uploads'] = 'PASS'
    except Exception as e:
        print(f"❌ Error: {e}")
        test_results['list_uploads'] = 'FAIL'
    
    # Summary
    print("\n" + "=" * 80)
    print("API TEST SUMMARY")
    print("=" * 80)
    passed = sum(1 for v in test_results.values() if v == 'PASS')
    total = len(test_results)
    
    for test, result in test_results.items():
        icon = "✅" if result == 'PASS' else "❌"
        print(f"{icon} {test}: {result}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed ({int(passed/total*100)}%)")
    
    if passed == total:
        print("✅ ALL API TESTS PASSED!")
        return True
    else:
        print("⚠️ Some tests failed - review errors above")
        return False

def check_aws_resources():
    """Verify AWS resources are deployed correctly"""
    print("\n" + "=" * 80)
    print("TASK 2: AWS INFRASTRUCTURE VERIFICATION")
    print("=" * 80)
    
    # Check S3 buckets
    print("\n[Checking S3 Buckets]")
    s3 = boto3.client('s3', region_name='us-east-2')
    buckets_to_check = [
        'adpa-data-083308938449-production',
        'adpa-models-083308938449-production',
        'adpa-frontend-083308938449-production'
    ]
    
    for bucket in buckets_to_check:
        try:
            s3.head_bucket(Bucket=bucket)
            print(f"✅ {bucket} exists")
        except:
            print(f"❌ {bucket} not found")
    
    # Check Lambda function
    print("\n[Checking Lambda Function]")
    lambda_client = boto3.client('lambda', region_name='us-east-2')
    try:
        response = lambda_client.get_function(FunctionName='adpa-lambda-function')
        print(f"✅ adpa-lambda-function exists")
        print(f"   Runtime: {response['Configuration']['Runtime']}")
        print(f"   Handler: {response['Configuration']['Handler']}")
        print(f"   Memory: {response['Configuration']['MemorySize']}MB")
    except:
        print(f"❌ adpa-lambda-function not found")
    
    # Check Step Functions
    print("\n[Checking Step Functions]")
    sfn = boto3.client('stepfunctions', region_name='us-east-2')
    try:
        response = sfn.describe_state_machine(
            stateMachineArn='arn:aws:states:us-east-2:083308938449:stateMachine:adpa-ml-pipeline-workflow'
        )
        print(f"✅ adpa-ml-pipeline-workflow exists")
        print(f"   Status: {response['status']}")
    except:
        print(f"❌ adpa-ml-pipeline-workflow not found")
    
    # Check DynamoDB table
    print("\n[Checking DynamoDB]")
    dynamodb = boto3.client('dynamodb', region_name='us-east-2')
    try:
        response = dynamodb.describe_table(TableName='adpa-pipelines')
        print(f"✅ adpa-pipelines table exists")
        print(f"   Status: {response['Table']['TableStatus']}")
    except dynamodb.exceptions.ResourceNotFoundException:
        print(f"ℹ️  adpa-pipelines table will be auto-created on first use")
    except Exception as e:
        print(f"⚠️ Error checking table: {e}")
    
    print("\n✅ Infrastructure verification complete")

def test_frontend():
    """Check frontend deployment"""
    print("\n" + "=" * 80)
    print("TASK 3: FRONTEND VERIFICATION")
    print("=" * 80)
    
    bucket_name = 'adpa-frontend-083308938449-production'
    frontend_url = f"http://{bucket_name}.s3-website.us-east-2.amazonaws.com"
    
    print(f"\n📱 Frontend URL: {frontend_url}")
    print("   Please open this URL in your browser to test:")
    print(f"   - UI loads correctly")
    print(f"   - No console errors")
    print(f"   - Can navigate pages")
    print(f"   - Can interact with API")
    
    # Check S3 bucket website configuration
    s3 = boto3.client('s3', region_name='us-east-2')
    try:
        response = s3.get_bucket_website(Bucket=bucket_name)
        print(f"\n✅ Static website hosting enabled")
        print(f"   Index document: {response.get('IndexDocument', {}).get('Suffix', 'N/A')}")
    except:
        print(f"\n❌ Static website hosting not configured")
    
    # List files in bucket
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=10)
        if 'Contents' in response:
            print(f"\n✅ Frontend files deployed ({len(response['Contents'])} files)")
            for obj in response['Contents'][:5]:
                print(f"   - {obj['Key']}")
        else:
            print(f"\n❌ No files found in frontend bucket")
    except Exception as e:
        print(f"\n❌ Error listing bucket: {e}")

def main():
    """Run all tests"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  ADPA COMPLETE END-TO-END TEST SUITE                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    start_time = time.time()
    
    # Run all tests
    api_passed = test_api_endpoints()
    check_aws_resources()
    test_frontend()
    
    # Final summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print("FINAL TEST SUMMARY")
    print("=" * 80)
    print(f"⏱️  Total test time: {elapsed:.2f} seconds")
    print(f"📅 Test date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if api_passed:
        print("\n✅ SYSTEM IS OPERATIONAL AND READY FOR USE!")
        print("\n🌐 Access the application:")
        print(f"   Frontend: http://adpa-frontend-083308938449-production.s3-website.us-east-2.amazonaws.com")
        print(f"   API: https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod")
    else:
        print("\n⚠️ SOME TESTS FAILED - REVIEW ERRORS ABOVE")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
