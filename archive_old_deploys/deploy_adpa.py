#!/usr/bin/env python3
"""
Simple ADPA deployment - no complex commands
"""

import boto3
import zipfile
import os
import shutil
import json

def deploy_adpa():
    print("🚀 Deploying ADPA System...")
    
    # Clean previous package
    if os.path.exists('adpa-deployment.zip'):
        os.remove('adpa-deployment.zip')
    
    # Create deployment package
    print("📦 Creating deployment package...")
    with zipfile.ZipFile('adpa-deployment.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
        
        # Add main Lambda handler
        if os.path.exists('lambda_function.py'):
            zf.write('lambda_function.py')
            print("   ✅ Added lambda_function.py")
        else:
            print("   ❌ lambda_function.py not found")
            return False
        
        # Add source code
        if os.path.exists('src'):
            for root, dirs, files in os.walk('src'):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path)
                        zf.write(file_path, arcname)
            print("   ✅ Added src/ directory")
        
        # Add config
        if os.path.exists('config'):
            for root, dirs, files in os.walk('config'):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path)
                    zf.write(file_path, arcname)
            print("   ✅ Added config/ directory")
    
    # Get package size
    size_mb = os.path.getsize('adpa-deployment.zip') / (1024 * 1024)
    print(f"📦 Package created: {size_mb:.2f} MB")
    
    # Deploy to Lambda
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-2')
        
        print("🚀 Uploading to Lambda...")
        with open('adpa-deployment.zip', 'rb') as f:
            zip_content = f.read()
        
        response = lambda_client.update_function_code(
            FunctionName='adpa-data-processor-development',
            ZipFile=zip_content
        )
        
        print("✅ Code uploaded successfully")
        
        # Update configuration
        print("⚙️  Updating configuration...")
        lambda_client.update_function_configuration(
            FunctionName='adpa-data-processor-development',
            Timeout=900,
            MemorySize=512,
            Environment={
                'Variables': {
                    'DATA_BUCKET': 'adpa-data-083308938449-development',
                    'MODEL_BUCKET': 'adpa-models-083308938449-development',
                    'AWS_REGION': 'us-east-2',
                    'ENVIRONMENT': 'development'
                }
            }
        )
        
        print("✅ Configuration updated")
        
        return True
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return False

def test_deployment():
    print("🧪 Testing deployment...")
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-2')
        
        # Test health check
        response = lambda_client.invoke(
            FunctionName='adpa-data-processor-development',
            Payload=json.dumps({'action': 'health_check'})
        )
        
        result = json.loads(response['Payload'].read().decode())
        print("✅ Test successful!")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    if deploy_adpa():
        print("\n🎉 ADPA Deployment Complete!")
        test_deployment()
        print(f"\n📊 View function at:")
        print(f"https://us-east-2.console.aws.amazon.com/lambda/home?region=us-east-2#/functions/adpa-data-processor-development")
    else:
        print("\n❌ Deployment failed")