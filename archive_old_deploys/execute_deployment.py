#!/usr/bin/env python3
"""
Execute ADPA deployment bypassing shell environment issues
"""

import os
import subprocess
import sys
from pathlib import Path

def execute_step1():
    """Execute Step 1: Run existing boto3_deploy.py"""
    print("=" * 60)
    print("STEP 1: Executing existing boto3_deploy.py")
    print("=" * 60)
    
    project_dir = Path("/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa")
    os.chdir(project_dir)
    
    try:
        # Execute the boto3_deploy.py script
        result = subprocess.run(
            [sys.executable, "boto3_deploy.py"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"Return code: {result.returncode}")
        return result.returncode == 0, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print("❌ Script execution timed out (10 minutes)")
        return False, "", "Timeout expired"
    except Exception as e:
        print(f"❌ Script execution failed: {e}")
        return False, "", str(e)

def execute_step2():
    """Execute Step 2: CloudFormation deployment via boto3"""
    print("=" * 60)
    print("STEP 2: CloudFormation deployment via boto3")
    print("=" * 60)
    
    script_content = '''
import boto3
import json
from pathlib import Path
import sys

def deploy_cloudformation():
    try:
        # Check if template exists
        template_path = Path("deploy/cloudformation/adpa-infrastructure.yaml")
        if not template_path.exists():
            print(f"❌ Template not found: {template_path}")
            return False
        
        # Read the CloudFormation template
        with open(template_path, 'r') as f:
            template_body = f.read()
        
        print(f"✅ Read template: {template_path}")
        print(f"Template size: {len(template_body)} characters")
        
        # Deploy via boto3
        cf_client = boto3.client('cloudformation', region_name='us-east-2')
        
        try:
            response = cf_client.create_stack(
                StackName='adpa-infrastructure-development',
                TemplateBody=template_body,
                Parameters=[
                    {'ParameterKey': 'Environment', 'ParameterValue': 'development'},
                    {'ParameterKey': 'AccountId', 'ParameterValue': '083308938449'}
                ],
                Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
            )
            print('✅ CloudFormation stack creation initiated:', response['StackId'])
            return True
        except Exception as e:
            if 'AlreadyExistsException' in str(e):
                print('ℹ️  Stack already exists, checking status...')
                try:
                    stack_info = cf_client.describe_stacks(StackName='adpa-infrastructure-development')
                    status = stack_info['Stacks'][0]['StackStatus']
                    print(f'Stack status: {status}')
                    return status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']
                except Exception as e2:
                    print(f'❌ Error checking stack status: {e2}')
                    return False
            else:
                print(f'❌ Stack creation failed: {e}')
                return False
            
    except ImportError:
        print("❌ boto3 not available")
        return False
    except Exception as e:
        print(f'❌ CloudFormation deployment failed: {e}')
        return False

if __name__ == "__main__":
    success = deploy_cloudformation()
    sys.exit(0 if success else 1)
'''
    
    project_dir = Path("/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa")
    script_file = project_dir / "cf_deploy_temp.py"
    
    try:
        # Write the script
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        # Execute it
        result = subprocess.run(
            [sys.executable, str(script_file)],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"Return code: {result.returncode}")
        
        # Cleanup
        if script_file.exists():
            script_file.unlink()
        
        return result.returncode == 0, result.stdout, result.stderr
        
    except Exception as e:
        print(f"❌ CloudFormation deployment failed: {e}")
        if script_file.exists():
            script_file.unlink()
        return False, "", str(e)

def execute_step3():
    """Execute Step 3: Check status of AWS resources"""
    print("=" * 60)
    print("STEP 3: Checking AWS resource status")
    print("=" * 60)
    
    check_script = '''
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import json

def check_aws_resources():
    try:
        # Check CloudFormation stacks
        print("Checking CloudFormation stacks...")
        cf_client = boto3.client('cloudformation', region_name='us-east-2')
        
        try:
            stacks = cf_client.list_stacks(
                StackStatusFilter=[
                    'CREATE_IN_PROGRESS', 'CREATE_COMPLETE', 'UPDATE_IN_PROGRESS', 
                    'UPDATE_COMPLETE', 'ROLLBACK_IN_PROGRESS', 'ROLLBACK_COMPLETE'
                ]
            )
            
            adpa_stacks = [s for s in stacks['StackSummaries'] if 'adpa' in s['StackName'].lower()]
            
            if adpa_stacks:
                print("✅ ADPA CloudFormation stacks found:")
                for stack in adpa_stacks:
                    print(f"  - {stack['StackName']}: {stack['StackStatus']}")
            else:
                print("⚠️  No ADPA CloudFormation stacks found")
                
        except Exception as e:
            print(f"❌ Error checking CloudFormation: {e}")
        
        # Check Lambda functions
        print("\\nChecking Lambda functions...")
        lambda_client = boto3.client('lambda', region_name='us-east-2')
        
        try:
            functions = lambda_client.list_functions()
            adpa_functions = [f for f in functions['Functions'] if 'adpa' in f['FunctionName'].lower()]
            
            if adpa_functions:
                print("✅ ADPA Lambda functions found:")
                for func in adpa_functions:
                    print(f"  - {func['FunctionName']}: {func['Runtime']}")
            else:
                print("⚠️  No ADPA Lambda functions found")
                
        except Exception as e:
            print(f"❌ Error checking Lambda: {e}")
        
        # Check S3 buckets
        print("\\nChecking S3 buckets...")
        s3_client = boto3.client('s3', region_name='us-east-2')
        
        try:
            buckets = s3_client.list_buckets()
            adpa_buckets = [b for b in buckets['Buckets'] if 'adpa' in b['Name'].lower()]
            
            if adpa_buckets:
                print("✅ ADPA S3 buckets found:")
                for bucket in adpa_buckets:
                    print(f"  - {bucket['Name']}")
            else:
                print("⚠️  No ADPA S3 buckets found")
                
        except Exception as e:
            print(f"❌ Error checking S3: {e}")
            
        print("\\n" + "="*50)
        print("RESOURCE CHECK COMPLETED")
        print("="*50)
        
    except NoCredentialsError:
        print("❌ AWS credentials not configured")
    except Exception as e:
        print(f"❌ AWS resource check failed: {e}")

if __name__ == "__main__":
    check_aws_resources()
'''
    
    project_dir = Path("/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa")
    script_file = project_dir / "aws_check_temp.py"
    
    try:
        # Write the script
        with open(script_file, 'w') as f:
            f.write(check_script)
        
        # Execute it
        result = subprocess.run(
            [sys.executable, str(script_file)],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        # Cleanup
        if script_file.exists():
            script_file.unlink()
        
        return result.returncode == 0, result.stdout, result.stderr
        
    except Exception as e:
        print(f"❌ AWS resource check failed: {e}")
        if script_file.exists():
            script_file.unlink()
        return False, "", str(e)

def execute_step4():
    """Execute Step 4: Run complete_manual_deployment.py if infrastructure succeeds"""
    print("=" * 60)
    print("STEP 4: Executing complete_manual_deployment.py")
    print("=" * 60)
    
    project_dir = Path("/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa")
    
    # Check if the file exists
    deployment_script = project_dir / "complete_manual_deployment.py"
    if not deployment_script.exists():
        print(f"❌ Script not found: {deployment_script}")
        return False, "", "Script not found"
    
    try:
        result = subprocess.run(
            [sys.executable, str(deployment_script)],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=900  # 15 minutes timeout
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"Return code: {result.returncode}")
        return result.returncode == 0, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print("❌ Script execution timed out (15 minutes)")
        return False, "", "Timeout expired"
    except Exception as e:
        print(f"❌ Script execution failed: {e}")
        return False, "", str(e)

def main():
    """Main execution function"""
    print("🚀 ADPA DEPLOYMENT EXECUTION")
    print("=" * 60)
    print("Executing deployment steps in sequence...")
    print("=" * 60)
    
    results = {}
    
    # Step 1: Try existing boto3_deploy.py
    success_1, stdout_1, stderr_1 = execute_step1()
    results["step1"] = {"success": success_1, "stdout": stdout_1, "stderr": stderr_1}
    
    if success_1:
        print("✅ Step 1 completed successfully")
    else:
        print("❌ Step 1 failed, proceeding to Step 2...")
    
    # Step 2: CloudFormation deployment (always run to check infrastructure)
    success_2, stdout_2, stderr_2 = execute_step2()
    results["step2"] = {"success": success_2, "stdout": stdout_2, "stderr": stderr_2}
    
    # Step 3: Check AWS resources
    success_3, stdout_3, stderr_3 = execute_step3()
    results["step3"] = {"success": success_3, "stdout": stdout_3, "stderr": stderr_3}
    
    # Step 4: Run complete deployment if infrastructure is ready
    if success_2 or success_1:  # Run if either step 1 or step 2 succeeded
        success_4, stdout_4, stderr_4 = execute_step4()
        results["step4"] = {"success": success_4, "stdout": stdout_4, "stderr": stderr_4}
    else:
        print("⚠️ Skipping Step 4 due to infrastructure issues")
        results["step4"] = {"success": False, "stdout": "", "stderr": "Skipped due to infrastructure issues"}
    
    # Summary
    print("\\n" + "=" * 60)
    print("DEPLOYMENT EXECUTION SUMMARY")
    print("=" * 60)
    
    for step, result in results.items():
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
        print(f"{step.upper()}: {status}")
    
    # Provide next steps
    print("\\n" + "=" * 60)
    print("NEXT STEPS AND RECOMMENDATIONS")
    print("=" * 60)
    
    if results["step1"]["success"]:
        print("✅ Direct Lambda deployment succeeded - system ready for testing")
    elif results["step2"]["success"] and results.get("step4", {}).get("success"):
        print("✅ Infrastructure and code deployment completed - system ready")
    elif results["step2"]["success"]:
        print("⚠️ Infrastructure deployed, but code deployment needs manual intervention")
    else:
        print("❌ Infrastructure deployment failed - check AWS credentials and permissions")
    
    return results

if __name__ == "__main__":
    main()