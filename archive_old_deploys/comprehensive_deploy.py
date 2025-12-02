#!/usr/bin/env python3
"""
Comprehensive ADPA deployment script - executes all deployment steps
"""

import os
import sys
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

# Configuration
project_root = Path("/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa")
os.chdir(project_root)
sys.path.insert(0, str(project_root))

CONFIG = {
    "function_name": "adpa-data-processor-development",
    "region": "us-east-2", 
    "runtime": "python3.9",
    "handler": "lambda_function.lambda_handler",
    "timeout": 900,
    "memory_size": 512,
    "stack_name": "adpa-infrastructure-development",
    "package_name": "adpa-lambda-deployment.zip",
    "environment_vars": {
        "DATA_BUCKET": "adpa-data-276983626136-development",
        "MODEL_BUCKET": "adpa-models-276983626136-development", 
        "AWS_REGION": "us-east-2",
        "ENVIRONMENT": "development"
    }
}

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def check_environment():
    """Check basic environment setup"""
    log("🔍 Checking environment setup...")
    
    # Check Python version
    log(f"Python version: {sys.version}")
    
    # Check working directory
    log(f"Working directory: {os.getcwd()}")
    
    # Check critical files
    critical_files = [
        "src",
        "lambda_function.py",
        "config", 
        "deploy/cloudformation/adpa-infrastructure.yaml"
    ]
    
    all_present = True
    for file_path in critical_files:
        path = Path(file_path)
        if path.exists():
            log(f"✅ Found: {file_path}")
        else:
            log(f"❌ Missing: {file_path}", "ERROR")
            all_present = False
    
    return all_present

def check_boto3():
    """Check and import boto3"""
    log("🔍 Checking boto3 availability...")
    
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        log("✅ boto3 is available")
        return boto3, ClientError, NoCredentialsError
    except ImportError:
        log("❌ boto3 not available", "ERROR")
        return None, None, None

def check_aws_credentials(boto3, NoCredentialsError):
    """Check AWS credentials"""
    log("🔍 Checking AWS credentials...")
    
    try:
        sts = boto3.client('sts', region_name=CONFIG["region"])
        identity = sts.get_caller_identity()
        log(f"✅ AWS credentials valid: {identity.get('Arn', 'Unknown')}")
        return True
    except NoCredentialsError:
        log("❌ AWS credentials not configured", "ERROR")
        return False
    except Exception as e:
        log(f"❌ AWS credential check failed: {e}", "ERROR")
        return False

def check_existing_infrastructure(boto3):
    """Check existing AWS infrastructure"""
    log("🔍 Checking existing AWS infrastructure...")
    
    infrastructure_status = {
        "cloudformation": False,
        "lambda": False,
        "s3": False
    }
    
    # Check CloudFormation stacks
    try:
        cf = boto3.client('cloudformation', region_name=CONFIG["region"])
        stacks = cf.list_stacks()
        adpa_stacks = [s for s in stacks['StackSummaries'] if 'adpa' in s['StackName'].lower()]
        
        if adpa_stacks:
            log("✅ CloudFormation stacks found:")
            for stack in adpa_stacks:
                log(f"  - {stack['StackName']}: {stack['StackStatus']}")
                if stack['StackStatus'] in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                    infrastructure_status["cloudformation"] = True
        else:
            log("⚠️  No ADPA CloudFormation stacks found")
            
    except Exception as e:
        log(f"❌ CloudFormation check failed: {e}", "ERROR")
    
    # Check Lambda functions
    try:
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        functions = lambda_client.list_functions()
        adpa_functions = [f for f in functions['Functions'] if 'adpa' in f['FunctionName'].lower()]
        
        if adpa_functions:
            log("✅ Lambda functions found:")
            for func in adpa_functions:
                log(f"  - {func['FunctionName']}")
                infrastructure_status["lambda"] = True
        else:
            log("⚠️  No ADPA Lambda functions found")
                
    except Exception as e:
        log(f"❌ Lambda check failed: {e}", "ERROR")
    
    # Check S3 buckets
    try:
        s3 = boto3.client('s3', region_name=CONFIG["region"])
        buckets = s3.list_buckets()
        adpa_buckets = [b for b in buckets['Buckets'] if 'adpa' in b['Name'].lower()]
        
        if adpa_buckets:
            log("✅ S3 buckets found:")
            for bucket in adpa_buckets:
                log(f"  - {bucket['Name']}")
                infrastructure_status["s3"] = True
        else:
            log("⚠️  No ADPA S3 buckets found")
                
    except Exception as e:
        log(f"❌ S3 check failed: {e}", "ERROR")
    
    return infrastructure_status

def deploy_cloudformation(boto3, ClientError):
    """Deploy CloudFormation infrastructure"""
    log("🚀 Deploying CloudFormation infrastructure...")
    
    template_path = Path("deploy/cloudformation/adpa-infrastructure.yaml")
    if not template_path.exists():
        log(f"❌ Template not found: {template_path}", "ERROR")
        return False
    
    try:
        with open(template_path, 'r') as f:
            template_body = f.read()
        
        log(f"✅ Read template: {template_path}")
        log(f"Template size: {len(template_body)} characters")
        
        cf = boto3.client('cloudformation', region_name=CONFIG["region"])
        
        try:
            response = cf.create_stack(
                StackName=CONFIG["stack_name"],
                TemplateBody=template_body,
                Parameters=[
                    {'ParameterKey': 'Environment', 'ParameterValue': 'development'},
                    {'ParameterKey': 'AccountId', 'ParameterValue': '083308938449'}
                ],
                Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
            )
            log(f"✅ CloudFormation stack creation initiated: {response['StackId']}")
            return True
            
        except ClientError as e:
            if 'AlreadyExistsException' in str(e):
                log("ℹ️  Stack already exists, checking status...")
                try:
                    stack_info = cf.describe_stacks(StackName=CONFIG["stack_name"])
                    status = stack_info['Stacks'][0]['StackStatus']
                    log(f"Stack status: {status}")
                    return status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']
                except Exception as e2:
                    log(f"❌ Error checking stack status: {e2}", "ERROR")
                    return False
            else:
                log(f"❌ Stack creation failed: {e}", "ERROR")
                return False
                
    except Exception as e:
        log(f"❌ CloudFormation deployment failed: {e}", "ERROR")
        return False

def create_deployment_package():
    """Create Lambda deployment package"""
    log("📦 Creating Lambda deployment package...")
    
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
                log(f"✅ Copied {src}")
            else:
                log(f"⚠️  Source {src} not found", "WARN")
        
        # Create minimal requirements.txt
        requirements = """boto3>=1.34.0
pydantic>=2.0.0
requests>=2.31.0
python-json-logger>=2.0.7
pyyaml>=6.0.0
python-dotenv>=1.0.0
"""
        
        with open(Path(package_dir) / "requirements.txt", "w") as f:
            f.write(requirements)
        
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
        log(f"✅ Created {zip_file} ({size_mb:.2f} MB)")
        
        # Cleanup temp directory
        shutil.rmtree(package_dir)
        return True
        
    except Exception as e:
        log(f"❌ Failed to create package: {e}", "ERROR")
        return False

def deploy_lambda_code(boto3, ClientError):
    """Deploy code to Lambda function"""
    log("🚀 Deploying Lambda code...")
    
    try:
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=CONFIG["function_name"])
            function_exists = True
            log(f"✅ Target function exists: {CONFIG['function_name']}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                log(f"❌ Lambda function {CONFIG['function_name']} not found", "ERROR")
                return False
            else:
                raise e
        
        # Read ZIP file
        with open(CONFIG["package_name"], 'rb') as f:
            zip_content = f.read()
        
        # Update function code
        log("Updating Lambda function code...")
        response = lambda_client.update_function_code(
            FunctionName=CONFIG["function_name"],
            ZipFile=zip_content
        )
        
        log("✅ Function code updated successfully")
        
        # Update configuration
        log("Updating function configuration...")
        try:
            lambda_client.update_function_configuration(
                FunctionName=CONFIG["function_name"],
                Runtime=CONFIG["runtime"],
                Handler=CONFIG["handler"],
                Timeout=CONFIG["timeout"],
                MemorySize=CONFIG["memory_size"],
                Environment={
                    'Variables': CONFIG["environment_vars"]
                }
            )
            log("✅ Function configuration updated")
        except Exception as e:
            log(f"⚠️  Configuration update failed: {e}", "WARN")
        
        return True
        
    except Exception as e:
        log(f"❌ Failed to deploy Lambda code: {e}", "ERROR")
        return False

def test_deployment(boto3):
    """Test the deployed Lambda function"""
    log("🧪 Testing deployment...")
    
    try:
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        
        # Health check test
        log("Running health check...")
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
        
        log("✅ Lambda invocation successful")
        
        if isinstance(response_json, dict):
            status = response_json.get('status', 'unknown')
            if status == 'healthy':
                log("✅ Health check PASSED")
            else:
                log(f"⚠️  Health check status: {status}", "WARN")
        
        return response_json
        
    except Exception as e:
        log(f"❌ Lambda test failed: {e}", "ERROR")
        return {"error": str(e), "status": "test_failed"}

def cleanup():
    """Clean up temporary files"""
    temp_files = [
        "lambda_package_temp",
        CONFIG["package_name"]
    ]
    
    for file_path in temp_files:
        if os.path.exists(file_path):
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                log(f"🧹 Cleaned up: {file_path}")
            except Exception as e:
                log(f"⚠️  Could not remove {file_path}: {e}", "WARN")

def main():
    """Main deployment function"""
    log("🚀 COMPREHENSIVE ADPA DEPLOYMENT STARTED")
    log("=" * 80)
    
    try:
        # Step 1: Environment check
        if not check_environment():
            log("❌ Environment check failed", "ERROR")
            return 1
        
        # Step 2: Check boto3
        boto3, ClientError, NoCredentialsError = check_boto3()
        if not boto3:
            log("❌ boto3 not available", "ERROR")
            return 1
        
        # Step 3: Check AWS credentials
        if not check_aws_credentials(boto3, NoCredentialsError):
            log("❌ AWS credentials check failed", "ERROR")  
            return 1
        
        # Step 4: Check existing infrastructure
        infrastructure = check_existing_infrastructure(boto3)
        
        # Step 5: Deploy infrastructure if needed
        if not infrastructure["cloudformation"]:
            log("Deploying CloudFormation infrastructure...")
            if not deploy_cloudformation(boto3, ClientError):
                log("❌ Infrastructure deployment failed", "ERROR")
                return 1
        else:
            log("✅ Infrastructure already exists")
        
        # Step 6: Create deployment package
        if not create_deployment_package():
            log("❌ Package creation failed", "ERROR")
            return 1
        
        # Step 7: Deploy Lambda code
        if not deploy_lambda_code(boto3, ClientError):
            log("❌ Lambda deployment failed", "ERROR")
            return 1
        
        # Step 8: Test deployment
        test_result = test_deployment(boto3)
        
        # Step 9: Report results
        log("=" * 80)
        log("🎉 DEPLOYMENT COMPLETED SUCCESSFULLY")
        log("=" * 80)
        
        log(f"✅ Function: {CONFIG['function_name']}")
        log(f"✅ Region: {CONFIG['region']}")
        log(f"✅ Stack: {CONFIG['stack_name']}")
        log(f"✅ Test Result: {json.dumps(test_result, indent=2)}")
        
        # Dashboard URLs
        log("📊 AWS Console URLs:")
        log(f"Lambda: https://{CONFIG['region']}.console.aws.amazon.com/lambda/home?region={CONFIG['region']}#/functions/{CONFIG['function_name']}")
        log(f"CloudFormation: https://{CONFIG['region']}.console.aws.amazon.com/cloudformation/home?region={CONFIG['region']}#/stacks")
        
        # Cleanup
        cleanup()
        
        return 0
        
    except KeyboardInterrupt:
        log("⚠️  Deployment cancelled by user", "WARN")
        cleanup()
        return 1
    except Exception as e:
        log(f"❌ Deployment failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        cleanup()
        return 1

if __name__ == "__main__":
    exit_code = main()
    print(f"\n{'='*80}")
    print(f"DEPLOYMENT FINISHED WITH EXIT CODE: {exit_code}")
    print(f"{'='*80}")
    sys.exit(exit_code)