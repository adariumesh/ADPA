#!/usr/bin/env python3
"""
Create our own Lambda Layer with real ML dependencies
This gives us full control without relying on external layers
"""

import boto3
import subprocess
import zipfile
import shutil
import os
import sys
from pathlib import Path

# Configuration
DEPLOYMENT_CONFIG = {
    "region": "us-east-2",
    "layer_name": "adpa-ml-dependencies",
    "description": "ADPA ML Dependencies - pandas, numpy, scikit-learn",
    "compatible_runtimes": ["python3.11"],
    "main_function": "adpa-data-processor-development",
}

class ADPALayerCreator:
    """Create Lambda Layer with real ML dependencies"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name=DEPLOYMENT_CONFIG['region'])
        self.s3_client = boto3.client('s3', region_name=DEPLOYMENT_CONFIG['region'])
        self.s3_bucket = 'adpa-data-083308938449-development'
        print("🚀 Creating ADPA Lambda Layer with Real Dependencies")
        print("=" * 60)
    
    def create_complete_layer(self):
        """Create and publish Lambda Layer with ML dependencies"""
        
        print("\n📋 Starting Layer Creation Process")
        print("=" * 60)
        
        layer_zip = self.build_layer_package()
        if not layer_zip:
            print("❌ Layer package creation failed")
            return False
        
        layer_arn = self.publish_layer(layer_zip)
        if not layer_arn:
            print("❌ Layer publishing failed")
            return False
        
        if not self.attach_layer_to_function(layer_arn):
            print("❌ Layer attachment failed")
            return False
        
        print("\n🎉 Lambda Layer Created and Attached Successfully!")
        print(f"   Layer ARN: {layer_arn}")
        return True
    
    def build_layer_package(self) -> str:
        """Build Lambda Layer package with essential ML libraries"""
        
        print("\n📦 Building Lambda Layer Package...")
        
        # Create layer directory structure
        layer_dir = Path("lambda_layer_build")
        python_dir = layer_dir / "python"
        
        # Clean up old builds
        if layer_dir.exists():
            shutil.rmtree(layer_dir)
        python_dir.mkdir(parents=True)
        
        try:
            # Install packages using pip with target directory
            print("   📥 Installing lightweight ML packages...")
            print("      (This may take 2-3 minutes...)")
            
            # Use slim versions and essential packages only
            packages = [
                "pandas==2.1.0",
                "numpy==1.24.3",
                "scikit-learn==1.3.0",
            ]
            
            for package in packages:
                print(f"      Installing {package}...")
                result = subprocess.run(
                    [
                        sys.executable, "-m", "pip", "install",
                        package,
                        "--target", str(python_dir),
                        "--platform", "manylinux2014_x86_64",
                        "--implementation", "cp",
                        "--python-version", "3.11",
                        "--only-binary=:all:",
                        "--upgrade"
                    ],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print(f"      ⚠️  Warning: {package} installation had issues")
                    print(f"         {result.stderr[:200]}")
                else:
                    print(f"      ✅ {package}")
            
            # Create zip file
            print("   🗜️  Creating layer ZIP package...")
            layer_zip_path = "adpa-ml-layer.zip"
            
            with zipfile.ZipFile(layer_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(layer_dir):
                    # Skip unnecessary files to reduce size
                    dirs[:] = [d for d in dirs if not d.startswith(('.', '__pycache__'))]
                    
                    for file in files:
                        if file.endswith(('.pyc', '.pyo', '.dist-info')):
                            continue
                        
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(layer_dir)
                        zipf.write(file_path, arcname)
            
            # Check size
            size_mb = os.path.getsize(layer_zip_path) / (1024 * 1024)
            print(f"   ✅ Layer package created: {layer_zip_path} ({size_mb:.2f} MB)")
            
            if size_mb > 50:
                print(f"   ⚠️  Warning: Layer size is {size_mb:.2f}MB (Lambda limit: 50MB compressed)")
                print("      Attempting to reduce size...")
                self.optimize_layer_size(layer_dir, layer_zip_path)
                size_mb = os.path.getsize(layer_zip_path) / (1024 * 1024)
                print(f"   ✅ Optimized to: {size_mb:.2f} MB")
            
            # Clean up build directory
            shutil.rmtree(layer_dir)
            
            return layer_zip_path
            
        except Exception as e:
            print(f"   ❌ Layer build failed: {e}")
            if layer_dir.exists():
                shutil.rmtree(layer_dir)
            return None
    
    def optimize_layer_size(self, layer_dir: Path, zip_path: str):
        """Optimize layer size by removing unnecessary files"""
        
        # Remove test files
        for root, dirs, files in os.walk(layer_dir):
            for file in files:
                file_path = Path(root) / file
                # Remove tests, examples, docs
                if any(x in str(file_path) for x in ['test', 'tests', 'examples', 'docs', '.so.debug']):
                    file_path.unlink(missing_ok=True)
        
        # Recreate zip
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(layer_dir):
                dirs[:] = [d for d in dirs if not d.startswith(('.', '__pycache__'))]
                for file in files:
                    if file.endswith(('.pyc', '.pyo')):
                        continue
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(layer_dir)
                    zipf.write(file_path, arcname)
    
    def publish_layer(self, layer_zip_path: str) -> str:
        """Publish Lambda Layer via S3 (for large packages)"""
        
        print("\n📤 Publishing Lambda Layer...")
        
        try:
            # Check size
            size_mb = os.path.getsize(layer_zip_path) / (1024 * 1024)
            
            if size_mb > 50:
                # Upload to S3 first for large packages
                print(f"   📦 Layer size: {size_mb:.2f}MB - Uploading to S3...")
                s3_key = f"lambda-layers/{DEPLOYMENT_CONFIG['layer_name']}.zip"
                
                self.s3_client.upload_file(
                    layer_zip_path,
                    self.s3_bucket,
                    s3_key
                )
                print(f"   ✅ Uploaded to S3: s3://{self.s3_bucket}/{s3_key}")
                
                # Publish layer from S3
                response = self.lambda_client.publish_layer_version(
                    LayerName=DEPLOYMENT_CONFIG['layer_name'],
                    Description=DEPLOYMENT_CONFIG['description'],
                    Content={
                        'S3Bucket': self.s3_bucket,
                        'S3Key': s3_key
                    },
                    CompatibleRuntimes=DEPLOYMENT_CONFIG['compatible_runtimes']
                )
            else:
                # Direct upload for smaller packages
                print(f"   📦 Layer size: {size_mb:.2f}MB - Direct upload...")
                with open(layer_zip_path, 'rb') as f:
                    layer_content = f.read()
                
                response = self.lambda_client.publish_layer_version(
                    LayerName=DEPLOYMENT_CONFIG['layer_name'],
                    Description=DEPLOYMENT_CONFIG['description'],
                    Content={'ZipFile': layer_content},
                    CompatibleRuntimes=DEPLOYMENT_CONFIG['compatible_runtimes']
                )
            
            layer_arn = response['LayerVersionArn']
            print(f"   ✅ Layer published successfully")
            print(f"      Layer Name: {DEPLOYMENT_CONFIG['layer_name']}")
            print(f"      Version: {response['Version']}")
            print(f"      ARN: {layer_arn}")
            
            return layer_arn
            
        except Exception as e:
            print(f"   ❌ Layer publishing failed: {e}")
            return None
    
    def attach_layer_to_function(self, layer_arn: str) -> bool:
        """Attach layer to Lambda function"""
        
        print("\n🔗 Attaching Layer to Lambda Function...")
        
        try:
            # Wait for any pending updates
            print("   ⏳ Waiting for function to be ready...")
            waiter = self.lambda_client.get_waiter('function_updated')
            waiter.wait(FunctionName=DEPLOYMENT_CONFIG['main_function'])
            
            # Update function configuration with layer
            response = self.lambda_client.update_function_configuration(
                FunctionName=DEPLOYMENT_CONFIG['main_function'],
                Layers=[layer_arn],
                MemorySize=3008,
                Timeout=900,
                Environment={
                    'Variables': {
                        'ENVIRONMENT': 'development',
                        'DATA_BUCKET': 'adpa-data-083308938449-development',
                        'MODEL_BUCKET': 'adpa-models-083308938449-development'
                    }
                }
            )
            
            print("   ✅ Layer attached successfully")
            print(f"      Function: {DEPLOYMENT_CONFIG['main_function']}")
            print(f"      Memory: {response['MemorySize']}MB")
            print(f"      Timeout: {response['Timeout']}s")
            print(f"      Layers: {len(response.get('Layers', []))} layer(s)")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Layer attachment failed: {e}")
            return False

def main():
    """Main function"""
    
    print("🔧 ADPA ML Dependencies Layer Setup")
    print("This will create a Lambda Layer with pandas, numpy, scikit-learn")
    print()
    
    creator = ADPALayerCreator()
    success = creator.create_complete_layer()
    
    if success:
        print("\n" + "=" * 60)
        print("🎯 Lambda Layer Setup Complete!")
        print("=" * 60)
        print("\n📊 Next Steps:")
        print("\n1. Test the function with real ML libraries:")
        print("   aws lambda invoke \\")
        print("       --function-name adpa-data-processor-development \\")
        print("       --payload '{\"action\": \"health_check\"}' \\")
        print("       --region us-east-2 \\")
        print("       response.json && cat response.json")
        print("\n2. The health check should now show:")
        print("   ✅ imports: True")
        print("   ✅ agent: True")
        print("   ✅ monitoring: True")
        print("\n🎉 Your ADPA system now has REAL ML capabilities!")
        
        sys.exit(0)
    else:
        print("\n❌ Layer setup failed")
        print("\nTroubleshooting:")
        print("- Ensure you have internet connection for pip")
        print("- Check AWS permissions for lambda:PublishLayerVersion")
        print("- Verify sufficient disk space for downloads")
        sys.exit(1)

if __name__ == "__main__":
    main()
