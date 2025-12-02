#!/usr/bin/env python3
"""
ADPA System Validation - Check if system is ready for deployment
Tests core components without requiring shell execution
"""

import os
import sys
import json
import importlib.util
from pathlib import Path

def validate_core_components():
    """Validate that all core ADPA components can be imported"""
    print("🔍 Validating Core Components...")
    
    # Add project root to path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    components_to_test = [
        ("src.agent.core.master_agent", "MasterAgenticController"),
        ("src.monitoring.cloudwatch_monitor", "ADPACloudWatchMonitor"), 
        ("src.monitoring.kpi_tracker", "KPITracker"),
        ("src.pipeline.ingestion.data_loader", "DataIngestionStep"),
        ("src.pipeline.etl.feature_engineer", "FeatureEngineeringStep"),
        ("src.pipeline.evaluation.evaluator", "ModelEvaluationStep")
    ]
    
    results = {}
    
    for module_name, class_name in components_to_test:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, class_name):
                results[f"{module_name}.{class_name}"] = "✅ AVAILABLE"
            else:
                results[f"{module_name}.{class_name}"] = "❌ CLASS NOT FOUND"
        except ImportError as e:
            results[f"{module_name}.{class_name}"] = f"❌ IMPORT ERROR: {e}"
        except Exception as e:
            results[f"{module_name}.{class_name}"] = f"❌ ERROR: {e}"
    
    # Print results
    for component, status in results.items():
        print(f"  {component}: {status}")
    
    success_count = sum(1 for status in results.values() if status.startswith("✅"))
    total_count = len(results)
    
    print(f"\n📊 Component Validation: {success_count}/{total_count} components available")
    return success_count == total_count

def validate_critical_fixes():
    """Validate that critical fixes have been applied"""
    print("🔧 Validating Critical Fixes...")
    
    fixes_status = {}
    
    # Check pandas compatibility fix
    cleaner_file = "src/pipeline/etl/cleaner.py"
    if os.path.exists(cleaner_file):
        with open(cleaner_file, 'r') as f:
            content = f.read()
        
        if "method='ffill'" not in content and "method='bfill'" not in content:
            fixes_status["Pandas Compatibility"] = "✅ FIXED"
        else:
            fixes_status["Pandas Compatibility"] = "❌ DEPRECATED METHODS STILL PRESENT"
    else:
        fixes_status["Pandas Compatibility"] = "❌ FILE NOT FOUND"
    
    # Check Bedrock permissions
    cf_file = "deploy/cloudformation/adpa-infrastructure.yaml"
    if os.path.exists(cf_file):
        with open(cf_file, 'r') as f:
            content = f.read()
        
        if "bedrock:InvokeModel" in content:
            fixes_status["Bedrock Permissions"] = "✅ ADDED"
        else:
            fixes_status["Bedrock Permissions"] = "❌ MISSING"
    else:
        fixes_status["Bedrock Permissions"] = "❌ FILE NOT FOUND"
    
    # Check region consistency
    config_file = "config/default_config.yaml"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            content = f.read()
        
        if "us-east-2" in content and "us-east-1" not in content:
            fixes_status["Region Consistency"] = "✅ STANDARDIZED"
        else:
            fixes_status["Region Consistency"] = "❌ INCONSISTENT"
    else:
        fixes_status["Region Consistency"] = "❌ FILE NOT FOUND"
    
    # Check database connection improvements
    memory_file = "src/agent/memory/experience_memory.py"
    if os.path.exists(memory_file):
        with open(memory_file, 'r') as f:
            content = f.read()
        
        if "finally:" in content and "conn.close()" in content:
            fixes_status["Database Connections"] = "✅ IMPROVED"
        else:
            fixes_status["Database Connections"] = "❌ NOT IMPROVED"
    else:
        fixes_status["Database Connections"] = "❌ FILE NOT FOUND"
    
    # Print results
    for fix, status in fixes_status.items():
        print(f"  {fix}: {status}")
    
    success_count = sum(1 for status in fixes_status.values() if status.startswith("✅"))
    total_count = len(fixes_status)
    
    print(f"\n📊 Critical Fixes: {success_count}/{total_count} applied successfully")
    return success_count == total_count

def validate_deployment_readiness():
    """Validate that system is ready for deployment"""
    print("🚀 Validating Deployment Readiness...")
    
    readiness_checks = {}
    
    # Check main Lambda handler
    if os.path.exists("lambda_function.py"):
        readiness_checks["Lambda Handler"] = "✅ PRESENT"
    else:
        readiness_checks["Lambda Handler"] = "❌ MISSING"
    
    # Check configuration
    if os.path.exists("config/default_config.yaml"):
        readiness_checks["Configuration"] = "✅ PRESENT"
    else:
        readiness_checks["Configuration"] = "❌ MISSING"
    
    # Check requirements
    if os.path.exists("requirements.txt"):
        readiness_checks["Requirements"] = "✅ PRESENT"
    else:
        readiness_checks["Requirements"] = "❌ MISSING"
    
    # Check deployment scripts
    deploy_scripts = [
        "deploy/deploy_lambda.sh",
        "boto3_deploy.py",
        "complete_manual_deployment.py"
    ]
    
    script_count = sum(1 for script in deploy_scripts if os.path.exists(script))
    if script_count >= 1:
        readiness_checks["Deployment Scripts"] = f"✅ {script_count} AVAILABLE"
    else:
        readiness_checks["Deployment Scripts"] = "❌ NONE AVAILABLE"
    
    # Check test files
    test_files = [
        "test_unified_adpa_system.py", 
        "complete_integration.sh"
    ]
    
    test_count = sum(1 for test_file in test_files if os.path.exists(test_file))
    if test_count >= 1:
        readiness_checks["Integration Tests"] = f"✅ {test_count} AVAILABLE"
    else:
        readiness_checks["Integration Tests"] = "❌ NONE AVAILABLE"
    
    # Print results
    for check, status in readiness_checks.items():
        print(f"  {check}: {status}")
    
    success_count = sum(1 for status in readiness_checks.values() if status.startswith("✅"))
    total_count = len(readiness_checks)
    
    print(f"\n📊 Deployment Readiness: {success_count}/{total_count} requirements met")
    return success_count == total_count

def main():
    """Main validation function"""
    print("🔥 ADPA System Validation")
    print("=" * 50)
    print("Validating system readiness for production deployment")
    print()
    
    # Run all validations
    components_ok = validate_core_components()
    print()
    
    fixes_ok = validate_critical_fixes()
    print()
    
    deployment_ok = validate_deployment_readiness()
    print()
    
    # Final assessment
    print("=" * 50)
    print("📋 FINAL ASSESSMENT")
    print("=" * 50)
    
    if components_ok and fixes_ok and deployment_ok:
        print("🎉 SYSTEM VALIDATION: PASSED")
        print("✅ All components available and fixes applied")
        print("✅ System ready for production deployment")
        print("🚀 Proceed with Lambda deployment")
        return True
    else:
        print("⚠️ SYSTEM VALIDATION: ISSUES FOUND")
        
        if not components_ok:
            print("❌ Component import issues detected")
        if not fixes_ok:
            print("❌ Critical fixes not fully applied")
        if not deployment_ok:
            print("❌ Deployment requirements not met")
            
        print("🔧 Address issues before deployment")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)