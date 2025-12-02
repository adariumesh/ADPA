#!/usr/bin/env python3
"""
Manual deployment steps - broken down for individual execution
"""

# Step 1: Create deployment package manually
import zipfile
import os
from pathlib import Path

def create_deployment_package():
    """Create the deployment ZIP package manually"""
    package_name = "adpa-manual-deploy.zip"
    
    # Remove existing package
    if os.path.exists(package_name):
        os.remove(package_name)
    
    print("Creating deployment package...")
    
    with zipfile.ZipFile(package_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add main handler
        if os.path.exists("lambda_function.py"):
            zipf.write("lambda_function.py", "lambda_function.py")
            print("✅ Added lambda_function.py")
        
        # Add src directory
        if os.path.exists("src"):
            for root, dirs, files in os.walk("src"):
                dirs[:] = [d for d in dirs if d != '__pycache__']
                for file in files:
                    if not file.endswith(('.pyc', '.pyo')):
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, ".")
                        zipf.write(file_path, arc_name)
            print("✅ Added src/ directory")
        
        # Add config directory  
        if os.path.exists("config"):
            for root, dirs, files in os.walk("config"):
                dirs[:] = [d for d in dirs if d != '__pycache__']
                for file in files:
                    if not file.endswith(('.pyc', '.pyo')):
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, ".")
                        zipf.write(file_path, arc_name)
            print("✅ Added config/ directory")
    
    # Get file size
    size_mb = os.path.getsize(package_name) / (1024 * 1024)
    print(f"✅ Package created: {package_name} ({size_mb:.2f} MB)")
    
    return package_name

if __name__ == "__main__":
    # Change to correct directory
    os.chdir("/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa")
    
    # Create package
    package = create_deployment_package()
    print(f"\n📦 Deployment package ready: {package}")
    print("\nNext steps:")
    print("1. Use AWS CLI or boto3 to upload this package")
    print("2. Update Lambda function code") 
    print("3. Test the function")