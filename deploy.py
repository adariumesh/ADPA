#!/usr/bin/env python3
"""
ADPA Final Deployment Script
Comprehensive deployment of ADPA to AWS Lambda with ML dependencies
"""

import boto3
import json
import os
import sys
import zipfile
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# ============================================================================
# DEPLOYMENT CONFIGURATION
# ============================================================================

# Import centralized AWS configuration
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config.aws_config import (
        AWS_ACCOUNT_ID, AWS_REGION, DATA_BUCKET, MODEL_BUCKET,
        LAMBDA_FUNCTION_NAME, LAMBDA_LAYER_NAME, get_credentials_from_csv
    )
except ImportError:
    # Fallback values if config module not available
    AWS_ACCOUNT_ID = "083308938449"
    AWS_REGION = "us-east-2"
    DATA_BUCKET = f"adpa-data-{AWS_ACCOUNT_ID}-development"
    MODEL_BUCKET = f"adpa-models-{AWS_ACCOUNT_ID}-development"
    LAMBDA_FUNCTION_NAME = "adpa-data-processor-development"
    LAMBDA_LAYER_NAME = "adpa-ml-dependencies-clean"

CONFIG = {
    # AWS Configuration - Using centralized config
    "region": AWS_REGION,
    "account_id": AWS_ACCOUNT_ID,
    
    # Lambda Function Configuration
    "function_name": LAMBDA_FUNCTION_NAME,
    "handler": "lambda_function.lambda_handler",
    "runtime": "python3.11",
    "memory": 3008,
    "timeout": 900,
    "architecture": "x86_64",
    
    # S3 Buckets - Using centralized config
    "data_bucket": DATA_BUCKET,
    "model_bucket": MODEL_BUCKET,
    
    # Lambda Layer Configuration
    "layer_name": LAMBDA_LAYER_NAME,
    "ml_libraries": {
        "pandas": "2.1.0",
        "numpy": "1.24.3",
        "scikit-learn": "1.3.0",
        "scipy": "1.11.0"
    },
    "skip_scipy": False,  # Include scipy for sklearn compatibility
    
    # IAM Role
    "role_name": f"adpa-lambda-execution-role-development",
    
    # Deployment Artifacts
    "code_package": "adpa-deployment-code.zip",
    "layer_package": "adpa-ml-layer.zip",
    "layer_dir": "python_layer_build",
}


class ADPADeployer:
    """Complete ADPA deployment orchestrator"""
    
    def __init__(self, rebuild_layer: bool = False):
        """
        Initialize deployer
        
        Args:
            rebuild_layer: Whether to rebuild the Lambda Layer (default: False, use existing)
        """
        self.rebuild_layer = rebuild_layer
        
        # Load credentials from rootkey.csv
        try:
            from config.aws_config import get_credentials_from_csv
            creds = get_credentials_from_csv()
            if creds['access_key_id'] and creds['secret_access_key']:
                self.lambda_client = boto3.client(
                    'lambda', 
                    region_name=CONFIG['region'],
                    aws_access_key_id=creds['access_key_id'],
                    aws_secret_access_key=creds['secret_access_key']
                )
                self.s3_client = boto3.client(
                    's3', 
                    region_name=CONFIG['region'],
                    aws_access_key_id=creds['access_key_id'],
                    aws_secret_access_key=creds['secret_access_key']
                )
                self.iam_client = boto3.client(
                    'iam', 
                    region_name=CONFIG['region'],
                    aws_access_key_id=creds['access_key_id'],
                    aws_secret_access_key=creds['secret_access_key']
                )
                print("✅ Loaded credentials from rootkey.csv")
            else:
                raise ValueError("No credentials found")
        except Exception as e:
            print(f"⚠️  Could not load credentials from rootkey.csv: {e}")
            print("   Falling back to default AWS credential chain")
            self.lambda_client = boto3.client('lambda', region_name=CONFIG['region'])
            self.s3_client = boto3.client('s3', region_name=CONFIG['region'])
            self.iam_client = boto3.client('iam', region_name=CONFIG['region'])
        
        self.layer_arn: Optional[str] = None
        self.function_arn: Optional[str] = None
        
        print("=" * 70)
        print("🚀 ADPA AWS Lambda Deployment")
        print("=" * 70)
        print(f"Account: {CONFIG['account_id']}")
        print(f"Region: {CONFIG['region']}")
        print(f"Function: {CONFIG['function_name']}")
        print(f"Runtime: {CONFIG['runtime']}")
        print(f"Rebuild Layer: {rebuild_layer}")
        print("=" * 70)
    
    def deploy(self) -> bool:
        """Execute complete deployment"""
        
        try:
            # Step 1: Verify AWS resources
            if not self._verify_aws_resources():
                return False
            
            # Step 2: Build or verify Lambda Layer
            if self.rebuild_layer:
                if not self._build_lambda_layer():
                    return False
                if not self._publish_lambda_layer():
                    return False
            else:
                if not self._get_existing_layer():
                    return False
            
            # Step 3: Package ADPA code
            if not self._package_adpa_code():
                return False
            
            # Step 4: Deploy Lambda function
            if not self._deploy_lambda_function():
                return False
            
            # Step 5: Test deployment
            if not self._test_deployment():
                print("\n⚠️  Deployment succeeded but tests failed")
                print("Check CloudWatch logs for details")
                return True  # Still consider deployment successful
            
            print("\n" + "=" * 70)
            print("✅ DEPLOYMENT SUCCESSFUL")
            print("=" * 70)
            self._print_success_info()
            return True
            
        except Exception as e:
            print(f"\n❌ Deployment failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self._cleanup()
    
    def _verify_aws_resources(self) -> bool:
        """Verify required AWS resources exist"""
        
        print("\n📋 Step 1: Verifying AWS Resources")
        print("-" * 70)
        
        # Check S3 buckets
        try:
            print(f"   Checking S3 bucket: {CONFIG['data_bucket']}...", end=" ")
            self.s3_client.head_bucket(Bucket=CONFIG['data_bucket'])
            print("✅")
        except Exception as e:
            print(f"❌\n   Error: {e}")
            return False
        
        try:
            print(f"   Checking S3 bucket: {CONFIG['model_bucket']}...", end=" ")
            self.s3_client.head_bucket(Bucket=CONFIG['model_bucket'])
            print("✅")
        except Exception as e:
            print(f"❌\n   Error: {e}")
            return False
        
        # Check IAM role
        try:
            print(f"   Checking IAM role: {CONFIG['role_name']}...", end=" ")
            response = self.iam_client.get_role(RoleName=CONFIG['role_name'])
            role_arn = response['Role']['Arn']
            print("✅")
            print(f"   Role ARN: {role_arn}")
        except Exception as e:
            print(f"❌\n   Error: {e}")
            return False
        
        print("   ✅ All AWS resources verified")
        return True
    
    def _get_existing_layer(self) -> bool:
        """Get existing Lambda Layer ARN"""
        
        print("\n📦 Step 2: Using Existing Lambda Layer")
        print("-" * 70)
        
        try:
            # List layer versions
            response = self.lambda_client.list_layer_versions(
                LayerName=CONFIG['layer_name']
            )
            
            if not response.get('LayerVersions'):
                print(f"   ❌ No versions found for layer: {CONFIG['layer_name']}")
                print("   Run with --rebuild-layer flag to create the layer")
                return False
            
            # Get the latest version
            latest = response['LayerVersions'][0]
            self.layer_arn = latest['LayerVersionArn']
            
            print(f"   ✅ Found layer: {CONFIG['layer_name']}")
            print(f"   Version: {latest['Version']}")
            print(f"   ARN: {self.layer_arn}")
            print(f"   Description: {latest.get('Description', 'N/A')}")
            
            return True
            
        except self.lambda_client.exceptions.ResourceNotFoundException:
            print(f"   ❌ Layer not found: {CONFIG['layer_name']}")
            print("   Run with --rebuild-layer flag to create the layer")
            return False
        except Exception as e:
            print(f"   ❌ Error getting layer: {e}")
            return False
    
    def _build_lambda_layer(self) -> bool:
        """Build Lambda Layer with ML dependencies"""
        
        print("\n📦 Step 2a: Building Lambda Layer")
        print("-" * 70)
        
        layer_dir = Path(CONFIG['layer_dir'])
        if layer_dir.exists():
            print(f"   Removing old layer directory...")
            shutil.rmtree(layer_dir)
        
        python_dir = layer_dir / "python"
        python_dir.mkdir(parents=True)
        
        print(f"   Installing ML libraries...")
        
        # Install each library separately to avoid dependency conflicts
        for lib, version in CONFIG['ml_libraries'].items():
            print(f"      Installing {lib}=={version}...", end=" ")
            
            # For sklearn, use --no-deps to avoid pulling in scipy
            extra_args = []
            if lib == "scikit-learn" and CONFIG.get('skip_scipy'):
                extra_args = ["--no-deps"]
            
            result = subprocess.run([
                "pip3", "install",
                "--platform", "manylinux2014_x86_64",
                "--implementation", "cp",
                "--python-version", "3.11",
                "--only-binary=:all:",
                "--upgrade",
                "--target", str(python_dir),
                f"{lib}=={version}",
                *extra_args
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌\n   Error: {result.stderr}")
                return False
            
            print("✅")
        
        # Install minimal required dependencies
        print(f"      Installing dependencies...", end=" ")
        deps = ["pytz", "python-dateutil", "tzdata", "joblib", "threadpoolctl"]
        
        result = subprocess.run([
            "pip3", "install",
            "--platform", "manylinux2014_x86_64",
            "--implementation", "cp",
            "--python-version", "3.11",
            "--only-binary=:all:",
            "--target", str(python_dir),
            *deps
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌\n   Error: {result.stderr}")
            return False
        
        print("✅")
        
        # Check for duplicate numpy versions
        numpy_versions = list(python_dir.glob("numpy-*.dist-info"))
        if len(numpy_versions) > 1:
            print(f"   ⚠️  Found {len(numpy_versions)} numpy versions, cleaning...")
            # Keep only the target version
            for ver_dir in numpy_versions:
                if CONFIG['ml_libraries']['numpy'] not in ver_dir.name:
                    print(f"      Removing {ver_dir.name}...")
                    shutil.rmtree(ver_dir)

        # Remove large, non-runtime directories to keep layer under AWS limits
        print(f"   Trimming optional files from layer...", end=" ")
        removed_bytes = self._cleanup_layer_directory(python_dir)
        print(f"removed {removed_bytes / (1024 * 1024):.2f} MB")

        total_size = self._get_directory_size(layer_dir)
        print(f"   Layer size after cleanup: {total_size / (1024 * 1024):.2f} MB (limit 250 MB)")
        if total_size > 262_144_000:
            print("   ⚠️  Layer still exceeds Lambda limit; consider reducing dependencies")
        
        # Create ZIP
        print(f"   Creating layer package...")
        with zipfile.ZipFile(CONFIG['layer_package'], 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(layer_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, layer_dir)
                    zipf.write(file_path, arcname)
        
        size_mb = os.path.getsize(CONFIG['layer_package']) / (1024 * 1024)
        print(f"   ✅ Layer package created: {CONFIG['layer_package']} ({size_mb:.2f} MB)")
        
        if size_mb > 50:
            print(f"   ℹ️  Package > 50MB, will upload via S3")
        
        return True

    def _cleanup_layer_directory(self, python_dir: Path) -> int:
        """Remove tests, examples, and caches to reduce dependency size"""
        patterns = [
            "**/tests", "**/Tests", "**/testing", "**/benchmarks",
            "**/__pycache__", "**/*.pyc", "**/*.pyo",
            "**/dist-info/INSTALLER", "**/dist-info/RECORD", "**/dist-info/REQUESTED"
        ]
        removed_bytes = 0
        protected_prefixes = {
            "numpy/testing",
        }

        for pattern in patterns:
            for path in python_dir.glob(pattern):
                try:
                    if not path.exists():
                        continue
                    rel_path = path.relative_to(python_dir).as_posix()
                    if any(rel_path.startswith(prefix) for prefix in protected_prefixes):
                        continue
                    if path.is_dir():
                        removed_bytes += self._get_directory_size(path)
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        removed_bytes += path.stat().st_size
                        path.unlink()
                except Exception as cleanup_error:
                    print(f"\n   ⚠️  Could not remove {path}: {cleanup_error}")

        return removed_bytes

    @staticmethod
    def _get_directory_size(path: Path) -> int:
        total = 0
        for root, _, files in os.walk(path):
            for name in files:
                try:
                    total += os.path.getsize(os.path.join(root, name))
                except OSError:
                    continue
        return total
    
    def _publish_lambda_layer(self) -> bool:
        """Publish Lambda Layer"""
        
        print("\n📦 Step 2b: Publishing Lambda Layer")
        print("-" * 70)
        
        layer_file = Path(CONFIG['layer_package'])
        size_mb = layer_file.stat().st_size / (1024 * 1024)
        
        try:
            if size_mb > 50:
                # Upload to S3 first
                print(f"   Uploading layer to S3...")
                s3_key = f"lambda-layers/{CONFIG['layer_package']}"
                
                self.s3_client.upload_file(
                    str(layer_file),
                    CONFIG['data_bucket'],
                    s3_key
                )
                print(f"   ✅ Uploaded to s3://{CONFIG['data_bucket']}/{s3_key}")
                
                # Publish from S3
                print(f"   Publishing layer from S3...")
                response = self.lambda_client.publish_layer_version(
                    LayerName=CONFIG['layer_name'],
                    Description=f"ML dependencies: {', '.join([f'{k} {v}' for k, v in CONFIG['ml_libraries'].items()])}",
                    Content={
                        'S3Bucket': CONFIG['data_bucket'],
                        'S3Key': s3_key
                    },
                    CompatibleRuntimes=[CONFIG['runtime']],
                    CompatibleArchitectures=[CONFIG['architecture']]
                )
            else:
                # Direct upload
                print(f"   Publishing layer directly...")
                with open(layer_file, 'rb') as f:
                    response = self.lambda_client.publish_layer_version(
                        LayerName=CONFIG['layer_name'],
                        Description=f"ML dependencies: {', '.join([f'{k} {v}' for k, v in CONFIG['ml_libraries'].items()])}",
                        Content={'ZipFile': f.read()},
                        CompatibleRuntimes=[CONFIG['runtime']],
                        CompatibleArchitectures=[CONFIG['architecture']]
                    )
            
            self.layer_arn = response['LayerVersionArn']
            print(f"   ✅ Layer published successfully")
            print(f"   ARN: {self.layer_arn}")
            print(f"   Version: {response['Version']}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error publishing layer: {e}")
            return False
    
    def _package_adpa_code(self) -> bool:
        """Package ADPA source code"""
        
        print("\n📦 Step 3: Packaging ADPA Code")
        print("-" * 70)
        
        temp_dir = Path("lambda_code_temp")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()
        
        try:
            # Copy source code
            print("   Copying ADPA source code...")
            shutil.copytree("src", temp_dir / "src",
                          ignore=shutil.ignore_patterns(
                              '*.pyc', '__pycache__', '.DS_Store',
                              'numpy', 'pandas', 'sklearn', 'scipy'  # Exclude ML libs
                          ))
            print("      ✅ src/")
            
            # Copy Lambda handler
            shutil.copy("lambda_function.py", temp_dir / "lambda_function.py")
            print("      ✅ lambda_function.py")
            
            # Copy config if exists
            if Path("config").exists():
                shutil.copytree("config", temp_dir / "config",
                              ignore=shutil.ignore_patterns('*.pyc', '__pycache__'))
                print("      ✅ config/")
            
            # Create deployment package
            print("   Creating deployment package...")
            with zipfile.ZipFile(CONFIG['code_package'], 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    # Exclude ML library directories and cache
                    dirs[:] = [d for d in dirs if d not in ['numpy', 'pandas', 'sklearn', 'scipy', '__pycache__']]
                    
                    for file in files:
                        if file.endswith('.pyc') or file == '.DS_Store':
                            continue
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(temp_dir)
                        zipf.write(file_path, arcname)
            
            size_mb = os.path.getsize(CONFIG['code_package']) / (1024 * 1024)
            print(f"   ✅ Package created: {CONFIG['code_package']} ({size_mb:.2f} MB)")
            
            # Verify no ML libraries in package
            print("   Verifying package contents...")
            with zipfile.ZipFile(CONFIG['code_package'], 'r') as zipf:
                files = zipf.namelist()
                ml_files = [f for f in files if any(lib in f for lib in ['numpy/', 'pandas/', 'sklearn/', 'scipy/'])]
                if ml_files:
                    print(f"   ⚠️  Warning: Found ML library files in package:")
                    for f in ml_files[:5]:
                        print(f"      {f}")
                else:
                    print(f"   ✅ Clean package (no ML libraries)")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error packaging code: {e}")
            return False
    
    def _deploy_lambda_function(self) -> bool:
        """Deploy or update Lambda function"""
        
        print("\n🚀 Step 4: Deploying Lambda Function")
        print("-" * 70)
        
        # Get role ARN
        role_response = self.iam_client.get_role(RoleName=CONFIG['role_name'])
        role_arn = role_response['Role']['Arn']
        
        # Read code package
        with open(CONFIG['code_package'], 'rb') as f:
            code_bytes = f.read()
        
        try:
            # Try to get existing function
            print(f"   Checking if function exists...")
            self.lambda_client.get_function(FunctionName=CONFIG['function_name'])
            
            # Function exists, update it
            print(f"   Updating existing function code...")
            response = self.lambda_client.update_function_code(
                FunctionName=CONFIG['function_name'],
                ZipFile=code_bytes
            )
            print(f"   ✅ Code updated")
            
            # Wait for update to complete
            print(f"   Waiting for update to complete...", end=" ")
            waiter = self.lambda_client.get_waiter('function_updated')
            waiter.wait(FunctionName=CONFIG['function_name'])
            print("✅")
            
            # Update configuration
            print(f"   Updating function configuration...")
            response = self.lambda_client.update_function_configuration(
                FunctionName=CONFIG['function_name'],
                Runtime=CONFIG['runtime'],
                Handler=CONFIG['handler'],
                Role=role_arn,
                Timeout=CONFIG['timeout'],
                MemorySize=CONFIG['memory'],
                Layers=[self.layer_arn],
                Environment={
                    'Variables': {
                        'DATA_BUCKET': CONFIG['data_bucket'],
                        'MODEL_BUCKET': CONFIG['model_bucket']
                    }
                }
            )
            print(f"   ✅ Configuration updated")
            
        except self.lambda_client.exceptions.ResourceNotFoundException:
            # Function doesn't exist, create it
            print(f"   Creating new function...")
            response = self.lambda_client.create_function(
                FunctionName=CONFIG['function_name'],
                Runtime=CONFIG['runtime'],
                Role=role_arn,
                Handler=CONFIG['handler'],
                Code={'ZipFile': code_bytes},
                Timeout=CONFIG['timeout'],
                MemorySize=CONFIG['memory'],
                Layers=[self.layer_arn],
                Environment={
                    'Variables': {
                        'DATA_BUCKET': CONFIG['data_bucket'],
                        'MODEL_BUCKET': CONFIG['model_bucket']
                    }
                },
                Architectures=[CONFIG['architecture']]
            )
            print(f"   ✅ Function created")
        
        self.function_arn = response['FunctionArn']
        
        # Wait for function to be ready
        print(f"   Waiting for function to be active...", end=" ")
        time.sleep(5)
        print("✅")
        
        print(f"   ✅ Lambda function deployed")
        print(f"   ARN: {self.function_arn}")
        
        return True
    
    def _test_deployment(self) -> bool:
        """Test the deployed Lambda function"""
        
        print("\n🧪 Step 5: Testing Deployment")
        print("-" * 70)
        
        # Test 1: Health check
        print("   Running health check...", end=" ")
        try:
            response = self.lambda_client.invoke(
                FunctionName=CONFIG['function_name'],
                Payload=json.dumps({"action": "health_check"})
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] != 200:
                print(f"❌ (Status: {response['StatusCode']})")
                return False
            
            status = result.get('status', 'unknown')
            if status == 'healthy':
                print("✅")
                print(f"      All components initialized successfully")
                
                # Show component status
                components = result.get('components', {})
                for comp, status in components.items():
                    icon = "✅" if status else "❌"
                    print(f"      {icon} {comp}: {status}")
                
                return True
            else:
                print(f"⚠️  (Status: {status})")
                print(f"      Components: {result.get('components', {})}")
                
                if 'import_error' in result:
                    print(f"      Import Error: {result['import_error']}")
                
                return False
                
        except Exception as e:
            print(f"❌\n   Error: {e}")
            return False
    
    def _cleanup(self):
        """Clean up temporary files"""
        
        print("\n🧹 Cleaning up temporary files...")
        
        for path in [Path("lambda_code_temp"), Path(CONFIG['layer_dir'])]:
            if path.exists():
                shutil.rmtree(path)
                print(f"   Removed {path}/")
    
    def _print_success_info(self):
        """Print success information and next steps"""
        
        print("\n📊 Deployment Summary:")
        print(f"   Function: {CONFIG['function_name']}")
        print(f"   ARN: {self.function_arn}")
        print(f"   Runtime: {CONFIG['runtime']}")
        print(f"   Memory: {CONFIG['memory']} MB")
        print(f"   Timeout: {CONFIG['timeout']} seconds")
        print(f"   Layer: {self.layer_arn}")
        
        print("\n🧪 Test your function:")
        print(f"\naws lambda invoke \\")
        print(f"  --function-name {CONFIG['function_name']} \\")
        print(f"  --payload '{{\"action\": \"health_check\"}}' \\")
        print(f"  --region {CONFIG['region']} \\")
        print(f"  response.json && cat response.json")
        
        print("\n📊 View logs:")
        print(f"\naws logs tail /aws/lambda/{CONFIG['function_name']} \\")
        print(f"  --follow \\")
        print(f"  --region {CONFIG['region']}")
        
        print("\n🎉 ADPA is now deployed and ready to use!")


def main():
    """Main entry point"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy ADPA to AWS Lambda')
    parser.add_argument('--rebuild-layer', action='store_true',
                       help='Rebuild the Lambda Layer (default: use existing)')
    parser.add_argument('--clean', action='store_true',
                       help='Clean up deployment artifacts before deploying')
    
    args = parser.parse_args()
    
    # Clean up old artifacts if requested
    if args.clean:
        print("🧹 Cleaning up old deployment artifacts...")
        for f in [CONFIG['code_package'], CONFIG['layer_package']]:
            if Path(f).exists():
                os.remove(f)
                print(f"   Removed {f}")
    
    # Deploy
    deployer = ADPADeployer(rebuild_layer=args.rebuild_layer)
    success = deployer.deploy()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
