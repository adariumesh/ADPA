#!/usr/bin/env python3
"""
Complete manual deployment script for ADPA Lambda
Run this script manually to complete the deployment
"""

import os
import sys
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

# Ensure we're in the correct directory
project_root = "/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa"
os.chdir(project_root)
sys.path.insert(0, project_root)

# Configuration
CONFIG = {
    "function_name": "adpa-data-processor-development",
    "region": "us-east-2",
    "runtime": "python3.9",
    "handler": "lambda_function.lambda_handler",
    "timeout": 900,
    "memory_size": 512,
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

def install_boto3_if_needed():
    """Install boto3 if not available"""
    try:
        import boto3
        log("boto3 is available")
        return True
    except ImportError:
        log("Installing boto3...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "boto3"])
            log("boto3 installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            log(f"Failed to install boto3: {e}", "ERROR")
            return False

def create_deployment_package():
    """Create deployment ZIP package"""
    log("Creating deployment package...")
    
    package_name = f"adpa-deployment-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    
    # Remove any existing package
    for existing in Path(".").glob("adpa-deployment-*.zip"):
        existing.unlink()
        log(f"Removed existing package: {existing}")
    
    try:
        with zipfile.ZipFile(package_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add lambda_function.py (main handler)
            if Path("lambda_function.py").exists():
                zipf.write("lambda_function.py", "lambda_function.py")
                log("✅ Added lambda_function.py")
            else:
                log("❌ lambda_function.py not found", "ERROR")
                return None
            
            # Add src directory (core ADPA code)
            if Path("src").exists():
                file_count = 0
                for root, dirs, files in os.walk("src"):
                    # Skip __pycache__ directories
                    dirs[:] = [d for d in dirs if d != '__pycache__']
                    
                    for file in files:
                        if file.endswith(('.pyc', '.pyo', '.DS_Store')):
                            continue
                        
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, ".")
                        zipf.write(file_path, arc_name)
                        file_count += 1
                
                log(f"✅ Added src/ directory ({file_count} files)")
            else:
                log("❌ src directory not found", "ERROR")
                return None
            
            # Add config directory
            if Path("config").exists():
                config_files = 0
                for root, dirs, files in os.walk("config"):
                    dirs[:] = [d for d in dirs if d != '__pycache__']
                    
                    for file in files:
                        if file.endswith(('.pyc', '.pyo', '.DS_Store')):
                            continue
                        
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, ".")
                        zipf.write(file_path, arc_name)
                        config_files += 1
                
                log(f"✅ Added config/ directory ({config_files} files)")
            
            # Add minimal requirements.txt
            requirements_content = """boto3>=1.34.0
pydantic>=2.0.0
requests>=2.31.0
python-json-logger>=2.0.7
pyyaml>=6.0.0
python-dotenv>=1.0.0
"""
            zipf.writestr("requirements.txt", requirements_content)
            log("✅ Added requirements.txt")
        
        # Check package size
        size_mb = Path(package_name).stat().st_size / (1024 * 1024)
        log(f"📦 Package created: {package_name} ({size_mb:.2f} MB)")
        
        if size_mb > 50:
            log("⚠️  Package is quite large (>50MB)", "WARN")
        
        return package_name
        
    except Exception as e:
        log(f"Failed to create package: {e}", "ERROR")
        return None

def check_aws_credentials():
    """Check AWS credentials"""
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError
        
        sts_client = boto3.client('sts', region_name=CONFIG["region"])
        identity = sts_client.get_caller_identity()
        
        log(f"✅ AWS Identity: {identity.get('Arn', 'Unknown')}")
        log(f"✅ Account ID: {identity.get('Account', 'Unknown')}")
        return True
        
    except NoCredentialsError:
        log("❌ AWS credentials not configured", "ERROR")
        log("Please run: aws configure", "ERROR")
        return False
    except Exception as e:
        log(f"AWS credential check failed: {e}", "ERROR")
        return False

def check_lambda_function():
    """Check if Lambda function exists"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        response = lambda_client.get_function(FunctionName=CONFIG["function_name"])
        
        log(f"✅ Lambda function exists: {CONFIG['function_name']}")
        
        # Show current function details
        func_config = response['Configuration']
        log(f"   Runtime: {func_config.get('Runtime')}")
        log(f"   Handler: {func_config.get('Handler')}")
        log(f"   Memory: {func_config.get('MemorySize')} MB")
        log(f"   Timeout: {func_config.get('Timeout')} seconds")
        
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            log(f"❌ Lambda function not found: {CONFIG['function_name']}", "ERROR")
            log("Please deploy infrastructure first", "ERROR")
        else:
            log(f"Error checking function: {e}", "ERROR")
        return False

def deploy_lambda_code(package_name):
    """Deploy code to Lambda function"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        
        log("Uploading code to Lambda function...")
        
        # Read the ZIP file
        with open(package_name, 'rb') as f:
            zip_content = f.read()
        
        # Update function code
        response = lambda_client.update_function_code(
            FunctionName=CONFIG["function_name"],
            ZipFile=zip_content
        )
        
        log("✅ Function code updated successfully")
        log(f"   Code SHA256: {response.get('CodeSha256', 'Unknown')[:16]}...")
        log(f"   Code Size: {response.get('CodeSize', 0) / (1024*1024):.2f} MB")
        
        return True
        
    except ClientError as e:
        log(f"Code deployment failed: {e}", "ERROR")
        return False
    except Exception as e:
        log(f"Unexpected error during deployment: {e}", "ERROR")
        return False

def update_lambda_configuration():
    """Update Lambda function configuration"""
    try:
        import boto3
        
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        
        log("Updating function configuration...")
        
        response = lambda_client.update_function_configuration(
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
        return True
        
    except Exception as e:
        log(f"Configuration update failed: {e}", "WARN")
        log("Function may still work with previous configuration", "WARN")
        return False

def test_lambda_function():
    """Test the deployed Lambda function"""
    try:
        import boto3
        
        lambda_client = boto3.client('lambda', region_name=CONFIG["region"])
        
        log("Testing Lambda function with health check...")
        
        # Test payload
        test_payload = json.dumps({"action": "health_check"})
        
        # Invoke function
        response = lambda_client.invoke(
            FunctionName=CONFIG["function_name"],
            Payload=test_payload,
            LogType='Tail'
        )
        
        # Read response
        response_payload = response['Payload'].read().decode('utf-8')
        
        # Parse response
        try:
            result = json.loads(response_payload)
        except json.JSONDecodeError:
            result = {"raw_response": response_payload}
        
        log("✅ Lambda invocation successful")
        
        # Check response status
        if isinstance(result, dict):
            status = result.get('status', 'unknown')
            if status == 'healthy':
                log("✅ Health check PASSED")
            elif status == 'unhealthy':
                log("⚠️  Health check returned unhealthy", "WARN")
                log("Check function logs for details", "WARN")
            else:
                log(f"⚠️  Unknown health status: {status}", "WARN")
        
        # Show logs if available
        if 'LogResult' in response:
            import base64
            log_data = base64.b64decode(response['LogResult']).decode('utf-8')
            log("Function logs:")
            for line in log_data.strip().split('\\n'):
                if line.strip():
                    log(f"  {line}")
        
        return result
        
    except Exception as e:
        log(f"Function test failed: {e}", "ERROR")
        return {"error": str(e), "status": "test_failed"}

def generate_aws_cli_commands():
    """Generate AWS CLI commands for manual testing"""
    commands = f"""
# ADPA Lambda Test Commands (AWS CLI)

# Health check test
aws lambda invoke \\
    --function-name {CONFIG["function_name"]} \\
    --payload '{{"action": "health_check"}}' \\
    --region {CONFIG["region"]} \\
    --cli-binary-format raw-in-base64-out \\
    health_response.json

# View response
cat health_response.json | python3 -m json.tool

# Pipeline test  
aws lambda invoke \\
    --function-name {CONFIG["function_name"]} \\
    --payload '{{"action": "run_pipeline", "dataset_path": "s3://adpa-data-276983626136-development/test.csv", "objective": "classification"}}' \\
    --region {CONFIG["region"]} \\
    --cli-binary-format raw-in-base64-out \\
    pipeline_response.json

# Function info
aws lambda get-function --function-name {CONFIG["function_name"]} --region {CONFIG["region"]}

# CloudWatch logs
aws logs describe-log-streams \\
    --log-group-name "/aws/lambda/{CONFIG["function_name"]}" \\
    --region {CONFIG["region"]} \\
    --order-by LastEventTime --descending
"""
    
    with open("lambda_test_commands.sh", "w") as f:
        f.write(commands)
    
    log("✅ Created lambda_test_commands.sh")

def cleanup_packages():
    """Clean up deployment packages"""
    packages = list(Path(".").glob("adpa-deployment-*.zip"))
    for package in packages:
        try:
            package.unlink()
            log(f"Cleaned up: {package}")
        except Exception as e:
            log(f"Could not remove {package}: {e}", "WARN")

def main():
    """Main deployment orchestrator"""
    print("🚀 ADPA Lambda Manual Deployment")
    print("=" * 60)
    
    # Step 1: Prerequisites
    log("Step 1: Checking prerequisites...")
    if not install_boto3_if_needed():
        log("Cannot proceed without boto3", "ERROR")
        return False
    
    # Check if we're in the right directory
    required_files = ["lambda_function.py", "src"]
    missing_files = [f for f in required_files if not Path(f).exists()]
    if missing_files:
        log(f"Missing required files: {missing_files}", "ERROR")
        log(f"Current directory: {os.getcwd()}")
        return False
    
    # Step 2: AWS Credentials
    log("Step 2: Checking AWS credentials...")
    if not check_aws_credentials():
        return False
    
    # Step 3: Lambda Function Check
    log("Step 3: Checking Lambda function...")
    if not check_lambda_function():
        return False
    
    # Step 4: Create Package
    log("Step 4: Creating deployment package...")
    package_name = create_deployment_package()
    if not package_name:
        return False
    
    # Step 5: Deploy Code
    log("Step 5: Deploying code to Lambda...")
    if not deploy_lambda_code(package_name):
        return False
    
    # Step 6: Update Configuration  
    log("Step 6: Updating function configuration...")
    config_updated = update_lambda_configuration()
    
    # Step 7: Test Function
    log("Step 7: Testing deployed function...")
    test_result = test_lambda_function()
    
    # Step 8: Generate test commands
    log("Step 8: Generating test commands...")
    generate_aws_cli_commands()
    
    # Step 9: Final Report
    print("\\n" + "=" * 60)
    print("🎉 ADPA LAMBDA DEPLOYMENT COMPLETED")
    print("=" * 60)
    
    log(f"✅ Function Name: {CONFIG['function_name']}")
    log(f"✅ Region: {CONFIG['region']}")
    log(f"✅ Package: {package_name}")
    
    if config_updated:
        log("✅ Configuration: Updated")
    else:
        log("⚠️  Configuration: Warning (check manually)")
    
    # Test results
    if isinstance(test_result, dict):
        status = test_result.get('status', 'unknown')
        if status == 'healthy':
            log("✅ Health Check: PASSED")
        else:
            log(f"⚠️  Health Check: {status}")
    
    print("\\n📋 Test Response:")
    print(json.dumps(test_result, indent=2))
    
    print(f"\\n📊 AWS Console:")
    print(f"https://{CONFIG['region']}.console.aws.amazon.com/lambda/home?region={CONFIG['region']}#/functions/{CONFIG['function_name']}")
    
    print(f"\\n📝 Test commands saved to: lambda_test_commands.sh")
    
    # Cleanup
    log("Cleaning up deployment packages...")
    cleanup_packages()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\\n🎉 Deployment completed successfully!")
            print("\\nNext steps:")
            print("1. Run manual tests using lambda_test_commands.sh")
            print("2. Check CloudWatch logs for any issues")
            print("3. Monitor function performance")
        else:
            print("\\n❌ Deployment failed!")
            print("\\nTroubleshooting:")
            print("1. Check AWS credentials (aws configure)")
            print("2. Verify Lambda function exists in us-east-2")
            print("3. Check IAM permissions for Lambda")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\\n⚠️  Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)