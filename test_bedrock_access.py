#!/usr/bin/env python3
"""
Test script to verify AWS Bedrock access with your credentials.
"""

import csv
import os
import sys

# Load credentials from rootkey.csv
def load_credentials():
    csv_path = os.path.join(os.path.dirname(__file__), 'rootkey.csv')
    try:
        with open(csv_path, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 2:
                # Parse CSV manually - header on line 1, values on line 2
                values = lines[1].strip().split(',')
                if len(values) >= 2:
                    return values[0], values[1]
        print(f"❌ Invalid rootkey.csv format")
        return None, None
    except Exception as e:
        print(f"❌ Failed to load credentials from rootkey.csv: {e}")
        return None, None

def test_bedrock():
    print("=" * 60)
    print("AWS BEDROCK ACCESS TEST")
    print("=" * 60)
    
    # Load credentials
    access_key, secret_key = load_credentials()
    if not access_key:
        return False
    
    print(f"✅ Loaded credentials: {access_key[:8]}...{access_key[-4:]}")
    
    # Configure boto3 with credentials
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    
    region = "us-east-2"
    
    # Create session with explicit credentials
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )
    
    print(f"\n📍 Testing in region: {region}")
    
    # Test 1: Check Bedrock service access
    print("\n--- Test 1: Bedrock Service Access ---")
    try:
        bedrock = session.client('bedrock', region_name=region)
        models = bedrock.list_foundation_models()
        model_count = len(models.get('modelSummaries', []))
        print(f"✅ Bedrock service accessible! Found {model_count} foundation models")
        
        # List available Claude models
        claude_models = [m for m in models['modelSummaries'] if 'claude' in m['modelId'].lower()]
        if claude_models:
            print(f"\n📋 Available Claude models:")
            for m in claude_models[:5]:
                print(f"   - {m['modelId']}")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"❌ Bedrock service error: {error_code}")
        print(f"   Message: {error_msg}")
        if 'AccessDenied' in error_code:
            print("\n⚠️  Your IAM user doesn't have Bedrock permissions.")
            print("   See instructions below to enable Bedrock access.")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Check Bedrock Runtime (for inference)
    print("\n--- Test 2: Bedrock Runtime Access ---")
    try:
        bedrock_runtime = session.client('bedrock-runtime', region_name=region)
        print("✅ Bedrock Runtime client created successfully")
    except Exception as e:
        print(f"❌ Bedrock Runtime error: {e}")
        return False
    
    # Test 3: Try a simple inference call
    print("\n--- Test 3: Model Invocation Test ---")
    try:
        import json
        
        # Use Claude 3.5 Sonnet via inference profile (works with your account)
        model_id = "us.anthropic.claude-3-5-sonnet-20240620-v1:0"
        
        # Use Messages API format for Claude 3+ models
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [
                {"role": "user", "content": "Say 'Hello from Bedrock!' in exactly those words."}
            ],
            "temperature": 0,
        })
        
        print(f"   Testing model: {model_id}")
        response = bedrock_runtime.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
        
        response_body = json.loads(response.get('body').read())
        completion = response_body.get('content', [{}])[0].get('text', '')
        
        print(f"✅ Model invocation successful!")
        print(f"   Response: {completion.strip()}")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"❌ Model invocation failed: {error_code}")
        print(f"   Message: {error_msg}")
        
        if 'AccessDenied' in str(e):
            print("\n⚠️  You need to request model access in the AWS Console.")
            print("   The IAM permissions are OK, but you haven't enabled the Claude model.")
        elif 'ValidationException' in error_code:
            print("\n⚠️  Model not available. Try requesting access in AWS Console.")
        
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def print_setup_instructions():
    print("\n" + "=" * 60)
    print("HOW TO ENABLE BEDROCK ACCESS")
    print("=" * 60)
    print("""
1. GO TO AWS CONSOLE:
   https://us-east-2.console.aws.amazon.com/bedrock/home?region=us-east-2

2. ADD IAM PERMISSIONS (if needed):
   Go to IAM → Users → your user → Add permissions
   Add these policies:
   - AmazonBedrockFullAccess (managed policy)
   
   Or create inline policy with:
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Action": [
                   "bedrock:*"
               ],
               "Resource": "*"
           }
       ]
   }

3. REQUEST MODEL ACCESS (required even with IAM permissions):
   - Go to Bedrock Console → Model access (left sidebar)
   - Click "Manage model access"
   - Select "Anthropic" → "Claude" models
   - Click "Request model access"
   - Wait for approval (usually instant for Claude)

4. VERIFY REGION:
   Make sure you're in us-east-2 (Ohio) region
""")

if __name__ == "__main__":
    print("\n")
    success = test_bedrock()
    
    if not success:
        print_setup_instructions()
    else:
        print("\n" + "=" * 60)
        print("🎉 SUCCESS! Bedrock is fully configured and working!")
        print("=" * 60)
        print("\nYour ADPA system can now use AWS Bedrock for LLM reasoning.")
    
    sys.exit(0 if success else 1)
