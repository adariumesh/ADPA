#!/usr/bin/env python3
"""
Direct ADPA deployment without shell dependencies
"""

import os
import sys
import json
import zipfile
import shutil
import tempfile
from pathlib import Path

# Add the project directory to Python path
project_dir = Path("/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa")
sys.path.insert(0, str(project_dir))
os.chdir(project_dir)

print("🚀 DIRECT ADPA DEPLOYMENT")
print("=" * 60)
print(f"Working directory: {os.getcwd()}")

# Check dependencies
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    print("✅ boto3 available")
    BOTO3_AVAILABLE = True
except ImportError as e:
    print(f"❌ boto3 not available: {e}")
    BOTO3_AVAILABLE = False

if not BOTO3_AVAILABLE:
    print("❌ Cannot proceed without boto3")
    sys.exit(1)

# Configuration
CONFIG = {
    "function_name": "adpa-data-processor-development",
    "region": "us-east-2",
    "runtime": "python3.9",
    "handler": "lambda_function.lambda_handler",
    "timeout": 900,
    "memory_size": 512,
    "package_name": "adpa-lambda-deployment.zip",
    "environment_vars": {
        "DATA_BUCKET": "adpa-data-276983626136-development",
        "MODEL_BUCKET": "adpa-models-276983626136-development",
        "AWS_REGION": "us-east-2",
        "ENVIRONMENT": "development"
    }
}

def print_status(message, prefix="INFO"):
    print(f"[{prefix}] {message}")

def check_aws_credentials():
    """Check AWS credentials"""
    try:
        sts_client = boto3.client('sts', region_name=CONFIG["region"])
        identity = sts_client.get_caller_identity()
        print_status(f"AWS Identity: {identity.get('Arn', 'Unknown')}")
        return True
    except NoCredentialsError:
        print_status("AWS credentials not configured", "ERROR")
        return False
    except Exception as e:
        print_status(f"AWS credential check failed: {e}", "ERROR")
        return False

def check_cloudformation_stacks():
    """Check CloudFormation stacks"""
    try:
        cf_client = boto3.client('cloudformation', region_name=CONFIG["region"])
        stacks = cf_client.list_stacks(
            StackStatusFilter=[
                'CREATE_IN_PROGRESS', 'CREATE_COMPLETE', 'UPDATE_IN_PROGRESS', 
                'UPDATE_COMPLETE', 'ROLLBACK_IN_PROGRESS', 'ROLLBACK_COMPLETE'
            ]
        )
        
        adpa_stacks = [s for s in stacks['StackSummaries'] if 'adpa' in s['StackName'].lower()]
        
        if adpa_stacks:
            print_status("ADPA CloudFormation stacks found:")
            for stack in adpa_stacks:
                print_status(f"  - {stack['StackName']}: {stack['StackStatus']}")
            return True
        else:
            print_status("No ADPA CloudFormation stacks found", "WARN")
            return False
            
    except Exception as e:
        print_status(f"Error checking CloudFormation: {e}", "ERROR")
        return False

def deploy_cloudformation():
    """Deploy CloudFormation infrastructure"""
    try:
        template_path = Path("deploy/cloudformation/adpa-infrastructure.yaml")
        if not template_path.exists():
            print_status(f"Template not found: {template_path}", "ERROR")
            return False
        
        with open(template_path, 'r') as f:
            template_body = f.read()
        
        print_status(f"Read template: {template_path}")
        print_status(f"Template size: {len(template_body)} characters")
        
        cf_client = boto3.client('cloudformation', region_name=CONFIG["region"])
        
        try:
            response = cf_client.create_stack(
                StackName='adpa-infrastructure-development',
                TemplateBody=template_body,
                Parameters=[
                    {'ParameterKey': 'Environment', 'ParameterValue': 'development'},
                    {'ParameterKey': 'AccountId', 'ParameterValue': '083308938449'}
                ],
                Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
            )
            print_status(f'CloudFormation stack creation initiated: {response["StackId"]}')
            return True
            
        except ClientError as e:
            if 'AlreadyExistsException' in str(e):
                print_status('Stack already exists, checking status...', "WARN")
                try:
                    stack_info = cf_client.describe_stacks(StackName='adpa-infrastructure-development')
                    status = stack_info['Stacks'][0]['StackStatus']
                    print_status(f'Stack status: {status}')
                    return status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']
                except Exception as e2:
                    print_status(f'Error checking stack status: {e2}', "ERROR")
                    return False
            else:
                print_status(f'Stack creation failed: {e}', "ERROR")
                return False
            
    except Exception as e:
        print_status(f'CloudFormation deployment failed: {e}', "ERROR")
        return False

def check_lambda_functions():
    """Check Lambda functions"""
    try:
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        functions = lambda_client.list_functions()
        adpa_functions = [f for f in functions['Functions'] if 'adpa' in f['FunctionName'].lower()]
        
        if adpa_functions:
            print_status("ADPA Lambda functions found:")
            for func in adpa_functions:
                print_status(f"  - {func['FunctionName']}: {func['Runtime']}")
            return True
        else:
            print_status("No ADPA Lambda functions found", "WARN")
            return False
            
    except Exception as e:
        print_status(f"Error checking Lambda: {e}", "ERROR")
        return False

def check_s3_buckets():
    """Check S3 buckets"""
    try:
        s3_client = boto3.client('s3', region_name=CONFIG["region"])
        buckets = s3_client.list_buckets()
        adpa_buckets = [b for b in buckets['Buckets'] if 'adpa' in b['Name'].lower()]
        
        if adpa_buckets:
            print_status("ADPA S3 buckets found:")
            for bucket in adpa_buckets:
                print_status(f"  - {bucket['Name']}")
            return True
        else:
            print_status("No ADPA S3 buckets found", "WARN")
            return False
            
    except Exception as e:
        print_status(f"Error checking S3: {e}", "ERROR")
        return False

def create_deployment_package():
    """Create Lambda deployment package"""
    print_status("Creating deployment package...")
    
    package_dir = "lambda_package_temp"
    zip_file = CONFIG["package_name"]
    
    try:
        # Clean existing files
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir)
        if os.path.exists(zip_file):
            os.remove(zip_file)
        
        # Create temporary directory
        os.makedirs(package_dir)
        
        # Copy source files
        files_to_copy = [
            ("src", "src"),
            ("lambda_function.py", "lambda_function.py"),
            ("config", "config")
        ]
        
        for src, dst in files_to_copy:
            src_path = Path(src)
            dst_path = Path(package_dir) / dst
            
            if src_path.exists():
                if src_path.is_dir():
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
                print_status(f"Copied {src}")
            else:
                print_status(f"Source {src} not found", "WARN")
        
        # Create ZIP file
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                # Skip __pycache__ directories
                dirs[:] = [d for d in dirs if d != '__pycache__']
                
                for file in files:
                    if file.endswith(('.pyc', '.pyo')):
                        continue
                        
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arcname)
        
        # Get package size
        size_mb = os.path.getsize(zip_file) / (1024 * 1024)
        print_status(f"Created {zip_file} ({size_mb:.2f} MB)")
        
        # Cleanup temp directory
        shutil.rmtree(package_dir)
        return True
        
    except Exception as e:
        print_status(f"Failed to create package: {e}", "ERROR")
        return False

def deploy_lambda_code():
    """Deploy code to Lambda"""
    try:
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=CONFIG["function_name"])
            function_exists = True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                function_exists = False
            else:
                raise e
        
        if not function_exists:
            print_status(f"Lambda function {CONFIG['function_name']} not found", "ERROR")
            print_status("Infrastructure deployment may be incomplete", "ERROR")
            return False
        
        # Read ZIP file
        with open(CONFIG["package_name"], 'rb') as f:
            zip_content = f.read()
        
        # Update function code
        print_status("Updating Lambda function code...")
        response = lambda_client.update_function_code(
            FunctionName=CONFIG["function_name"],
            ZipFile=zip_content
        )
        
        print_status("Function code updated successfully")
        return True
        
    except Exception as e:
        print_status(f"Failed to update function code: {e}", "ERROR")
        return False

def test_lambda_function():
    """Test Lambda function"""
    try:
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        
        print_status("Testing Lambda function with health check...")
        test_payload = json.dumps({"action": "health_check"})
        
        response = lambda_client.invoke(
            FunctionName=CONFIG["function_name"],
            Payload=test_payload
        )
        
        response_payload = response['Payload'].read().decode('utf-8')
        
        try:
            response_json = json.loads(response_payload)
        except json.JSONDecodeError:
            response_json = {"raw_response": response_payload}
        
        print_status("Lambda invocation successful")
        
        if isinstance(response_json, dict):
            status = response_json.get('status', 'unknown')
            if status == 'healthy':
                print_status("Health check PASSED")
            else:
                print_status(f"Health check status: {status}", "WARN")
        
        return response_json
        
    except Exception as e:
        print_status(f"Lambda test failed: {e}", "ERROR")
        return {"error": str(e), "status": "test_failed"}

def main():
    """Main deployment function"""
    print("=" * 60)
    
    # Step 1: Check AWS credentials
    print_status("Step 1: Checking AWS credentials...")
    if not check_aws_credentials():
        print_status("AWS credentials check failed", "ERROR")
        return 1
    
    # Step 2: Check existing infrastructure
    print_status("Step 2: Checking existing infrastructure...")
    cf_exists = check_cloudformation_stacks()
    lambda_exists = check_lambda_functions()
    s3_exists = check_s3_buckets()
    
    # Step 3: Deploy infrastructure if needed
    if not cf_exists:
        print_status("Step 3: Deploying CloudFormation infrastructure...")
        cf_deployed = deploy_cloudformation()
        if not cf_deployed:
            print_status("CloudFormation deployment failed", "ERROR")
            return 1
    else:
        print_status("Step 3: Infrastructure already exists")
    
    # Step 4: Create and deploy Lambda code
    if lambda_exists or cf_exists:
        print_status("Step 4: Creating deployment package...")
        if not create_deployment_package():
            return 1
        
        print_status("Step 5: Deploying Lambda code...")
        if not deploy_lambda_code():
            return 1
        
        print_status("Step 6: Testing deployment...")
        test_result = test_lambda_function()
        
        print("=" * 60)
        print("✅ DEPLOYMENT COMPLETED")
        print("=" * 60)
        print(f"Function: {CONFIG['function_name']}")
        print(f"Region: {CONFIG['region']}")
        print(f"Test Result: {json.dumps(test_result, indent=2)}")
        
        # Cleanup
        if os.path.exists(CONFIG["package_name"]):
            os.remove(CONFIG["package_name"])
    else:
        print_status("Cannot deploy Lambda - infrastructure not ready", "ERROR")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())