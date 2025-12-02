import os
import sys
sys.path.insert(0, '/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa')
os.chdir('/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa')

try:
    import boto3
    print("✅ boto3 available")
    
    # Test AWS connection
    sts = boto3.client('sts', region_name='us-east-2')
    identity = sts.get_caller_identity()
    print(f"✅ AWS connected: {identity.get('Arn')}")
    
    # Test Lambda function exists
    lambda_client = boto3.client('lambda', region_name='us-east-2')
    response = lambda_client.get_function(FunctionName='adpa-data-processor-development')
    print("✅ Lambda function exists")
    
    print("Ready for deployment!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("Check AWS credentials or function name")