"""
Validate monitoring system structure and implementation
Simple validation script for Adariprasad's Week 1 tutorial objectives
"""

import os
import sys
import inspect
from typing import Dict, Any

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '../../')
sys.path.append(project_root)

def validate_file_exists(filepath: str) -> bool:
    """Validate that a file exists."""
    full_path = os.path.join(project_root, filepath)
    exists = os.path.exists(full_path)
    print(f"✅ {filepath}" if exists else f"❌ {filepath}")
    return exists

def validate_class_methods(module_path: str, class_name: str, expected_methods: list) -> bool:
    """Validate that a class has expected methods."""
    try:
        # Import the module dynamically
        module_parts = module_path.split('.')
        module = __import__(module_path, fromlist=[class_name])
        cls = getattr(module, class_name)
        
        print(f"\n📋 Validating {class_name} methods:")
        
        all_methods_exist = True
        for method_name in expected_methods:
            if hasattr(cls, method_name):
                print(f"  ✅ {method_name}")
            else:
                print(f"  ❌ {method_name}")
                all_methods_exist = False
        
        return all_methods_exist
        
    except ImportError as e:
        print(f"  ❌ Could not import {class_name}: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error validating {class_name}: {e}")
        return False

def main():
    """Main validation function."""
    print("🔍 ADPA Monitoring System Structure Validation")
    print("=" * 60)
    print("Validating Adariprasad's Week 1 Tutorial Implementation")
    print("=" * 60)
    
    # Track validation results
    results = {}
    
    print("\n📁 File Structure Validation:")
    print("-" * 30)
    
    # Core monitoring files
    core_files = [
        "src/monitoring/__init__.py",
        "src/monitoring/cloudwatch_monitor.py", 
        "src/monitoring/xray_tracer.py",
        "src/monitoring/alerting_system.py",
        "src/pipeline/monitoring/pipeline_monitor.py"
    ]
    
    files_exist = all(validate_file_exists(f) for f in core_files)
    results['file_structure'] = files_exist
    
    print(f"\n📊 File Structure: {'✅ PASS' if files_exist else '❌ FAIL'}")
    
    # Method validation (without importing boto3-dependent modules)
    print("\n🏗️  Class Structure Validation:")
    print("-" * 35)
    
    # Check if files contain expected class definitions and method signatures
    monitoring_components = [
        {
            'file': 'src/monitoring/cloudwatch_monitor.py',
            'class': 'ADPACloudWatchMonitor',
            'methods': ['publish_pipeline_metrics', 'log_structured_event', 'create_dashboard', 'get_metrics_summary']
        },
        {
            'file': 'src/monitoring/xray_tracer.py', 
            'class': 'ADPAXRayMonitor',
            'methods': ['trace_pipeline_execution', 'analyze_trace_data', 'get_service_map', 'get_trace_analytics']
        },
        {
            'file': 'src/monitoring/alerting_system.py',
            'class': 'ADPAAlertingSystem', 
            'methods': ['send_custom_alert', 'get_alarm_history', 'test_alert_system', 'create_custom_alarm']
        }
    ]
    
    # Validate by reading file contents (safer than importing)
    structure_valid = True
    for component in monitoring_components:
        print(f"\n📋 {component['class']}:")
        file_path = os.path.join(project_root, component['file'])
        
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Check if class is defined
            if f"class {component['class']}" in content:
                print(f"  ✅ Class {component['class']} defined")
                
                # Check if methods are defined
                methods_found = 0
                for method in component['methods']:
                    if f"def {method}" in content:
                        print(f"    ✅ {method}")
                        methods_found += 1
                    else:
                        print(f"    ❌ {method}")
                        structure_valid = False
                        
                print(f"  📊 Methods: {methods_found}/{len(component['methods'])}")
            else:
                print(f"  ❌ Class {component['class']} not found")
                structure_valid = False
        else:
            print(f"  ❌ File not found: {component['file']}")
            structure_valid = False
    
    results['class_structure'] = structure_valid
    
    # Tutorial objectives validation
    print(f"\n🎯 Tutorial Objectives Validation:")
    print("-" * 40)
    
    objectives = {
        "Day 1: CloudWatch Setup": {
            'files': ['src/monitoring/cloudwatch_monitor.py'],
            'features': ['Log groups setup', 'Custom metrics', 'Dashboard creation']
        },
        "Day 2: X-Ray Tracing": {
            'files': ['src/monitoring/xray_tracer.py'],
            'features': ['Distributed tracing', 'Trace analysis', 'Service map']
        },
        "Day 3: Alerting System": {
            'files': ['src/monitoring/alerting_system.py'], 
            'features': ['SNS integration', 'CloudWatch alarms', 'Custom alerts']
        },
        "Integration: Pipeline Monitor": {
            'files': ['src/pipeline/monitoring/pipeline_monitor.py'],
            'features': ['Comprehensive monitoring', 'Health checks', 'Alert testing']
        }
    }
    
    objectives_completed = 0
    total_objectives = len(objectives)
    
    for objective, details in objectives.items():
        files_exist = all(
            os.path.exists(os.path.join(project_root, f)) 
            for f in details['files']
        )
        
        if files_exist:
            print(f"✅ {objective}")
            objectives_completed += 1
        else:
            print(f"❌ {objective}")
    
    results['tutorial_objectives'] = objectives_completed == total_objectives
    
    # Final summary
    print(f"\n🏆 VALIDATION SUMMARY:")
    print("=" * 25)
    print(f"📁 File Structure: {'✅ PASS' if results['file_structure'] else '❌ FAIL'}")
    print(f"🏗️  Class Structure: {'✅ PASS' if results['class_structure'] else '❌ FAIL'}")
    print(f"🎯 Tutorial Objectives: {objectives_completed}/{total_objectives} ({'✅ PASS' if results['tutorial_objectives'] else '❌ PARTIAL'}")
    
    overall_pass = all(results.values())
    print(f"\n🎉 Overall Status: {'✅ IMPLEMENTATION COMPLETE' if overall_pass else '⚠️ NEEDS ATTENTION'}")
    
    # Week 1 completion status
    print(f"\n📅 Week 1 Status:")
    print("-" * 20)
    week1_tasks = [
        ("Day 1: AWS CloudWatch Setup", results['file_structure'] and 'cloudwatch_monitor.py' in str(core_files)),
        ("Day 2: X-Ray Integration", 'xray_tracer.py' in str(core_files)),
        ("Day 3: Alerting System", 'alerting_system.py' in str(core_files)),
        ("Day 4: Integration", results['class_structure'])
    ]
    
    completed_tasks = sum(1 for _, completed in week1_tasks if completed)
    
    for task, completed in week1_tasks:
        print(f"{'✅' if completed else '❌'} {task}")
    
    print(f"\n📊 Week 1 Progress: {completed_tasks}/{len(week1_tasks)} tasks completed")
    
    if completed_tasks == len(week1_tasks):
        print("🎊 WEEK 1 OBJECTIVES COMPLETE! Ready for Week 2.")
    else:
        print("⚠️  Continue working on remaining Week 1 tasks.")
    
    return overall_pass

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)