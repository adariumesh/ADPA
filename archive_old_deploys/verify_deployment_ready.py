#!/usr/bin/env python3
"""
Verify ADPA deployment readiness
Checks all required files and configurations
"""

import os
import sys
from pathlib import Path

def check_file(path, description):
    """Check if file exists and report"""
    if Path(path).exists():
        if Path(path).is_file():
            size = Path(path).stat().st_size
            print(f"✅ {description}: {path} ({size} bytes)")
        else:
            print(f"✅ {description}: {path} (directory)")
        return True
    else:
        print(f"❌ {description}: {path} (missing)")
        return False

def main():
    """Check deployment readiness"""
    print("🔍 ADPA Deployment Readiness Check")
    print("=" * 50)
    
    # Change to project directory
    project_dir = "/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa"
    os.chdir(project_dir)
    print(f"📁 Project directory: {project_dir}")
    
    # Critical files check
    critical_files = [
        ("lambda_function.py", "Lambda handler"),
        ("src", "Source code directory"),
        ("src/agent", "Agent core"),
        ("src/pipeline", "Pipeline components"),
        ("src/monitoring", "Monitoring system"),
        ("config", "Configuration directory"),
        ("config/default_config.yaml", "Default configuration"),
    ]
    
    print("\\n📋 Critical Files:")
    critical_passed = 0
    for path, desc in critical_files:
        if check_file(path, desc):
            critical_passed += 1
    
    # Deployment scripts check
    deployment_scripts = [
        ("complete_manual_deployment.py", "Complete deployment script"),
        ("boto3_deploy.py", "Boto3 deployment script"), 
        ("simple_aws_test.py", "AWS connection test"),
        ("DEPLOYMENT_SOLUTION.md", "Deployment instructions"),
    ]
    
    print("\\n🚀 Deployment Scripts:")
    script_passed = 0
    for path, desc in deployment_scripts:
        if check_file(path, desc):
            script_passed += 1
    
    # Optional files check
    optional_files = [
        ("requirements.txt", "Requirements file"),
        ("README.md", "Documentation"),
        ("deploy", "Deploy directory"),
    ]
    
    print("\\n📄 Optional Files:")
    for path, desc in optional_files:
        check_file(path, desc)
    
    # Python environment check
    print("\\n🐍 Python Environment:")
    try:
        import boto3
        print(f"✅ boto3: {boto3.__version__}")
    except ImportError:
        print("❌ boto3: Not installed (pip install boto3)")
    
    try:
        import yaml
        print("✅ pyyaml: Available")
    except ImportError:
        print("⚠️  pyyaml: Not available (optional)")
    
    try:
        import requests
        print("✅ requests: Available")
    except ImportError:
        print("⚠️  requests: Not available (may be needed)")
    
    # Summary
    print("\\n📊 Readiness Summary:")
    print(f"Critical files: {critical_passed}/{len(critical_files)}")
    print(f"Deployment scripts: {script_passed}/{len(deployment_scripts)}")
    
    if critical_passed == len(critical_files) and script_passed >= 2:
        print("\\n✅ DEPLOYMENT READY!")
        print("\\nNext step:")
        print("python3 complete_manual_deployment.py")
    elif critical_passed < len(critical_files):
        print("\\n❌ MISSING CRITICAL FILES")
        print("Cannot proceed with deployment")
    else:
        print("\\n⚠️  PARTIALLY READY")
        print("At least one deployment script is available")
    
    # Instructions
    print("\\n📖 Available deployment methods:")
    if Path("complete_manual_deployment.py").exists():
        print("1. python3 complete_manual_deployment.py (recommended)")
    if Path("boto3_deploy.py").exists():
        print("2. python3 boto3_deploy.py (alternative)")
    if Path("simple_aws_test.py").exists():
        print("3. python3 simple_aws_test.py (test only)")
    
    print("\\n📚 See DEPLOYMENT_SOLUTION.md for complete instructions")

if __name__ == "__main__":
    main()