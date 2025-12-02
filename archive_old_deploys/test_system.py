#!/usr/bin/env python3
"""
Simple system test - verify ADPA is working
"""

import boto3
import json
import time

def test_adpa_system():
    print("🔬 Testing ADPA System...")
    
    lambda_client = boto3.client('lambda', region_name='us-east-2')
    
    tests = [
        {
            'name': 'Health Check',
            'payload': {'action': 'health_check'}
        },
        {
            'name': 'System Info',
            'payload': {'action': 'system_info'}
        }
    ]
    
    for test in tests:
        print(f"\n🧪 Running: {test['name']}")
        try:
            response = lambda_client.invoke(
                FunctionName='adpa-data-processor-development',
                Payload=json.dumps(test['payload'])
            )
            
            result = json.loads(response['Payload'].read().decode())
            
            if response['StatusCode'] == 200:
                print(f"✅ {test['name']} PASSED")
                if 'status' in result:
                    print(f"   Status: {result['status']}")
                if 'components' in result:
                    print(f"   Components: {result['components']}")
            else:
                print(f"❌ {test['name']} FAILED")
                print(f"   Status Code: {response['StatusCode']}")
            
            print(f"   Response: {json.dumps(result, indent=4)}")
            
        except Exception as e:
            print(f"❌ {test['name']} ERROR: {e}")
        
        time.sleep(1)  # Brief pause between tests

def check_logs():
    print("\n📝 Recent CloudWatch Logs:")
    try:
        logs_client = boto3.client('logs', region_name='us-east-2')
        
        # Get latest log stream
        streams = logs_client.describe_log_streams(
            logGroupName='/aws/lambda/adpa-data-processor-development',
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if streams['logStreams']:
            latest_stream = streams['logStreams'][0]['logStreamName']
            print(f"Latest log stream: {latest_stream}")
            
            # Get recent events
            events = logs_client.get_log_events(
                logGroupName='/aws/lambda/adpa-data-processor-development',
                logStreamName=latest_stream,
                limit=10
            )
            
            for event in events['events'][-5:]:  # Show last 5 events
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event['timestamp']/1000))
                print(f"[{timestamp}] {event['message']}")
        
    except Exception as e:
        print(f"❌ Could not fetch logs: {e}")

if __name__ == "__main__":
    test_adpa_system()
    check_logs()
    
    print(f"\n🎯 ADPA System Test Complete!")
    print(f"\n📊 AWS Console:")
    print(f"https://us-east-2.console.aws.amazon.com/lambda/home?region=us-east-2#/functions/adpa-data-processor-development")