"""
Rebuild Lambda Layer with clean, single version of each library.
"""

import boto3
import subprocess
import os
import shutil
import zipfile
from pathlib import Path

def main():
    print("🔧 Rebuilding Clean Lambda Layer")
    print("Fixing numpy version conflict")
    print("=" * 60)
    
    # Clean up old layer directory
    layer_dir = Path("python_layer_clean")
    if layer_dir.exists():
        print(f"   🗑️  Removing old {layer_dir}...")
        shutil.rmtree(layer_dir)
    
    layer_dir.mkdir()
    python_dir = layer_dir / "python"
    python_dir.mkdir()
    
    print("\n📦 Installing ML libraries with pip...")
    print("   Installing pandas, numpy, scikit-learn...")
    
    # Install with --upgrade to ensure single versions
    # Install numpy first (this is the base)
    print("   Installing numpy...")
    result = subprocess.run([
        "pip3", "install",
        "--platform", "manylinux2014_x86_64",
        "--implementation", "cp",
        "--python-version", "3.11",
        "--only-binary=:all:",
        "--target", str(python_dir),
        "numpy==1.24.3"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ numpy install failed: {result.stderr}")
        return
    
    # Then pandas with dependencies
    print("   Installing pandas...")
    result = subprocess.run([
        "pip3", "install",
        "--platform", "manylinux2014_x86_64",
        "--implementation", "cp",
        "--python-version", "3.11",
        "--only-binary=:all:",
        "--no-deps",
        "--target", str(python_dir),
        "pandas==2.1.0",
        "pytz",
        "python-dateutil",
        "tzdata"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ pandas install failed: {result.stderr}")
        return
    
    # Install scipy (needed by performance_tracker)
    print("   Installing scipy...")
    result = subprocess.run([
        "pip3", "install",
        "--platform", "manylinux2014_x86_64",
        "--implementation", "cp",
        "--python-version", "3.11",
        "--only-binary=:all:",
        "--no-deps",
        "--target", str(python_dir),
        "scipy==1.11.4"  # Compatible with numpy 1.24.3
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ scipy install failed: {result.stderr}")
        return
    
    # Finally scikit-learn with minimal deps
    print("   Installing scikit-learn...")
    result = subprocess.run([
        "pip3", "install",
        "--platform", "manylinux2014_x86_64",
        "--implementation", "cp",
        "--python-version", "3.11",
        "--only-binary=:all:",
        "--no-deps",
        "--target", str(python_dir),
        "scikit-learn==1.3.0",
        "joblib",
        "threadpoolctl"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ pip install failed: {result.stderr}")
        return
    
    print("   ✅ Libraries installed")
    
    # Check for duplicate numpy
    print("\n🔍 Verifying no duplicate versions...")
    numpy_dirs = list(python_dir.glob("numpy*"))
    print(f"   Found {len(numpy_dirs)} numpy-related items:")
    for item in numpy_dirs:
        print(f"      - {item.name}")
    
    # Remove any numpy 2.x if present
    for item in python_dir.glob("numpy-2*.dist-info"):
        print(f"   🗑️  Removing duplicate: {item.name}")
        shutil.rmtree(item)
    
    # Check final state
    print("\n✅ Final package contents:")
    dist_infos = sorted([d.name for d in python_dir.glob("*.dist-info")])
    for dist in dist_infos:
        print(f"      {dist}")
    
    # Create ZIP
    print("\n📦 Creating layer ZIP...")
    zip_path = "adpa-ml-layer-clean.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(layer_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, layer_dir)
                zipf.write(file_path, arcname)
    
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"   ✅ Layer created: {zip_path} ({size_mb:.2f} MB)")
    
    # Upload to S3
    print("\n📤 Uploading to S3...")
    s3_client = boto3.client('s3', region_name='us-east-2')
    bucket = 'adpa-data-083308938449-development'
    key = f'lambda-layers/{zip_path}'
    
    s3_client.upload_file(zip_path, bucket, key)
    print(f"   ✅ Uploaded to s3://{bucket}/{key}")
    
    # Publish new layer version
    print("\n🚀 Publishing Lambda Layer...")
    lambda_client = boto3.client('lambda', region_name='us-east-2')
    
    response = lambda_client.publish_layer_version(
        LayerName='adpa-ml-dependencies-clean',
        Description='Clean ML dependencies: pandas 2.1.0, numpy 1.24.3, scipy 1.11.4, scikit-learn 1.3.0',
        Content={
            'S3Bucket': bucket,
            'S3Key': key
        },
        CompatibleRuntimes=['python3.11'],
        CompatibleArchitectures=['x86_64']
    )
    
    layer_arn = response['LayerVersionArn']
    print(f"   ✅ Layer published: {layer_arn}")
    
    # Update Lambda function
    print("\n🔗 Updating Lambda function...")
    lambda_client.update_function_configuration(
        FunctionName='adpa-data-processor-development',
        Layers=[layer_arn]
    )
    print("   ✅ Function updated with clean layer")
    
    # Wait and test
    print("\n⏳ Waiting for update to complete...")
    import time
    time.sleep(10)
    
    print("\n🧪 Testing import...")
    test_response = lambda_client.invoke(
        FunctionName='adpa-data-processor-development',
        Payload='{"action": "diagnostic", "test": "import_trace"}'
    )
    
    import json
    result = json.loads(test_response['Payload'].read())
    
    if result.get('success'):
        print(f"   ✅ SUCCESS! numpy imported from: {result['numpy_file']}")
    else:
        print(f"   ❌ Still failing: {result.get('error', 'Unknown error')}")
        if 'traceback' in result:
            print(f"\n{result['traceback']}")
    
    print("\n" + "=" * 60)
    print("🎯 Clean Layer Rebuild Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
