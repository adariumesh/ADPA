#!/usr/bin/env python3
"""
Lambda Package Creator for ADPA deployment
Creates the deployment package without external shell dependencies
"""

import os
import sys
import json
import shutil
import zipfile
from pathlib import Path

def create_deployment_package():
    """Create the lambda deployment package"""
    print("🚀 Creating ADPA Lambda deployment package...")
    
    # Configuration
    package_dir = "lambda_package"
    zip_file = "adpa-lambda-deployment.zip"
    
    # Clean existing package
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
        print(f"✅ Cleaned existing {package_dir}")
    
    if os.path.exists(zip_file):
        os.remove(zip_file)
        print(f"✅ Removed existing {zip_file}")
    
    # Create package directory
    os.makedirs(package_dir, exist_ok=True)
    print(f"✅ Created {package_dir} directory")
    
    # Copy source code
    src_path = Path("src")
    if src_path.exists():
        shutil.copytree(src_path, Path(package_dir) / "src")
        print("✅ Copied src directory")
    else:
        print("❌ src directory not found")
        return False
    
    # Copy lambda function
    lambda_file = Path("lambda_function.py")
    if lambda_file.exists():
        shutil.copy2(lambda_file, Path(package_dir) / "lambda_function.py")
        print("✅ Copied lambda_function.py")
    else:
        print("❌ lambda_function.py not found")
        return False
    
    # Copy config
    config_path = Path("config")
    if config_path.exists():
        shutil.copytree(config_path, Path(package_dir) / "config")
        print("✅ Copied config directory")
    
    # Create minimal requirements for Lambda runtime (since some packages are pre-installed)
    requirements_content = """# Minimal requirements for Lambda runtime
# Note: Some packages like boto3 are pre-installed in Lambda
boto3>=1.34.0
pydantic>=2.0.0
requests>=2.31.0
python-json-logger>=2.0.7
pyyaml>=6.0.0
python-dotenv>=1.0.0
"""
    
    with open(Path(package_dir) / "requirements.txt", "w") as f:
        f.write(requirements_content)
    print("✅ Created requirements.txt")
    
    # Add a simple __init__.py to make it a proper Python package
    with open(Path(package_dir) / "__init__.py", "w") as f:
        f.write('"""ADPA Lambda Package"""')
    
    # Create the ZIP file
    print("📦 Creating ZIP archive...")
    
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                if file.endswith('.pyc'):
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, package_dir)
                zipf.write(file_path, arcname)
                
    # Get file size
    zip_size = os.path.getsize(zip_file)
    zip_size_mb = zip_size / (1024 * 1024)
    print(f"✅ Created {zip_file} ({zip_size_mb:.2f} MB)")
    
    # Clean up temporary directory
    shutil.rmtree(package_dir)
    print(f"✅ Cleaned up {package_dir}")
    
    return True

def create_deployment_info():
    """Create deployment information file"""
    deployment_info = {
        "function_name": "adpa-data-processor-development",
        "region": "us-east-2",
        "runtime": "python3.9",
        "timeout": 900,
        "memory_size": 512,
        "environment_variables": {
            "DATA_BUCKET": "adpa-data-276983626136-development",
            "MODEL_BUCKET": "adpa-models-276983626136-development",
            "AWS_REGION": "us-east-2",
            "ENVIRONMENT": "development"
        },
        "package_file": "adpa-lambda-deployment.zip",
        "handler": "lambda_function.lambda_handler",
        "description": "ADPA intelligent data processing agent",
        "tags": {
            "Project": "ADPA",
            "Environment": "Development",
            "Owner": "Adariprasad",
            "Infrastructure": "Girik"
        }
    }
    
    with open("deployment_info.json", "w") as f:
        json.dump(deployment_info, f, indent=2)
    
    print("✅ Created deployment_info.json")
    return deployment_info

def generate_deployment_commands():
    """Generate AWS CLI commands for deployment"""
    
    commands = """
# ADPA Lambda Deployment Commands
# Execute these commands to deploy the ADPA agent to AWS Lambda

# 1. Update Lambda function code
aws lambda update-function-code \\
    --function-name adpa-data-processor-development \\
    --zip-file fileb://adpa-lambda-deployment.zip \\
    --region us-east-2

# 2. Update Lambda function configuration  
aws lambda update-function-configuration \\
    --function-name adpa-data-processor-development \\
    --timeout 900 \\
    --memory-size 512 \\
    --region us-east-2 \\
    --environment Variables='{
        "DATA_BUCKET":"adpa-data-276983626136-development",
        "MODEL_BUCKET":"adpa-models-276983626136-development", 
        "AWS_REGION":"us-east-2",
        "ENVIRONMENT":"development"
    }'

# 3. Test the deployment
aws lambda invoke \\
    --function-name adpa-data-processor-development \\
    --payload '{"action": "health_check"}' \\
    --region us-east-2 \\
    health_check_response.json

# 4. View the response
cat health_check_response.json | python -m json.tool

# 5. Test pipeline execution
aws lambda invoke \\
    --function-name adpa-data-processor-development \\
    --payload '{"action": "run_pipeline", "dataset_path": "s3://adpa-data-276983626136-development/test.csv", "objective": "classification"}' \\
    --region us-east-2 \\
    pipeline_response.json

# 6. View pipeline response
cat pipeline_response.json | python -m json.tool
"""
    
    with open("deployment_commands.sh", "w") as f:
        f.write(commands)
    
    print("✅ Created deployment_commands.sh")

def main():
    """Main function"""
    print("ADPA Lambda Package Creator")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists("src") or not os.path.exists("lambda_function.py"):
        print("❌ Please run this script from the ADPA project root directory")
        print("   (should contain 'src' and 'lambda_function.py')")
        return 1
    
    try:
        # Create deployment package
        if not create_deployment_package():
            print("❌ Failed to create deployment package")
            return 1
        
        # Create deployment info
        deployment_info = create_deployment_info()
        
        # Generate deployment commands
        generate_deployment_commands()
        
        print("\n🎉 DEPLOYMENT PACKAGE CREATED SUCCESSFULLY!")
        print("=" * 50)
        print()
        print("📦 Files created:")
        print("   - adpa-lambda-deployment.zip (deployment package)")
        print("   - deployment_info.json (deployment configuration)")
        print("   - deployment_commands.sh (AWS CLI commands)")
        print()
        print("📋 Next steps:")
        print("   1. Ensure AWS CLI is configured with proper credentials")
        print("   2. Verify the target Lambda function exists:")
        print(f"      aws lambda get-function --function-name {deployment_info['function_name']} --region {deployment_info['region']}")
        print("   3. Execute the deployment commands:")
        print("      chmod +x deployment_commands.sh")
        print("      ./deployment_commands.sh")
        print()
        print(f"🎯 Target Function: {deployment_info['function_name']}")
        print(f"🌍 Region: {deployment_info['region']}")
        print(f"📦 Package Size: {os.path.getsize('adpa-lambda-deployment.zip') / (1024*1024):.2f} MB")
        print()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())