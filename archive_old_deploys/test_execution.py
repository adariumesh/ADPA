import sys
import os

# Navigate to the project directory
project_dir = "/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa"
os.chdir(project_dir)
sys.path.insert(0, project_dir)

print("Current directory:", os.getcwd())
print("Python path includes project directory")

# Test basic functionality
try:
    import boto3
    print("✅ boto3 available")
    
    # Quick credential check
    sts = boto3.client('sts', region_name='us-east-2')
    identity = sts.get_caller_identity()
    print(f"✅ AWS credentials work: Account {identity.get('Account')}")
    
    # Check existing resources quickly
    cf = boto3.client('cloudformation', region_name='us-east-2')
    stacks = cf.list_stacks()
    adpa_stacks = [s for s in stacks['StackSummaries'] if 'adpa' in s['StackName'].lower()]
    print(f"Found {len(adpa_stacks)} ADPA stacks")
    
    lambda_client = boto3.client('lambda', region_name='us-east-2')
    functions = lambda_client.list_functions()
    adpa_functions = [f for f in functions['Functions'] if 'adpa' in f['FunctionName'].lower()]
    print(f"Found {len(adpa_functions)} ADPA Lambda functions")
    
    if adpa_functions:
        print("ADPA is already deployed - attempting code update...")
        # Try to run the boto3 deploy script which should update existing Lambda
        exec(open("boto3_deploy.py").read())
    else:
        print("No ADPA functions found - attempting full deployment...")
        exec(open("comprehensive_deploy.py").read())
        
except ImportError:
    print("❌ boto3 not available")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()