#!/usr/bin/env python3
"""
Simple ADPA deployment executor without subprocess dependencies
"""

import os
import sys
from pathlib import Path

# Add the project directory to Python path
project_dir = Path("/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa")
sys.path.insert(0, str(project_dir))

# Change to project directory  
os.chdir(project_dir)

print("🚀 ADPA DEPLOYMENT EXECUTION")
print("=" * 60)
print(f"Working directory: {os.getcwd()}")
print("=" * 60)

try:
    # Import and execute the boto3_deploy module directly
    print("STEP 1: Importing and executing boto3_deploy...")
    
    # Read and execute the boto3_deploy.py file
    boto3_script_path = project_dir / "boto3_deploy.py"
    
    if boto3_script_path.exists():
        print(f"✅ Found boto3_deploy.py at: {boto3_script_path}")
        
        # Execute the script by reading and running it
        with open(boto3_script_path, 'r') as f:
            script_content = f.read()
        
        # Execute in current namespace
        exec(script_content)
        
    else:
        print("❌ boto3_deploy.py not found")
        
        # Try step 2: CloudFormation deployment
        print("\\nSTEP 2: Attempting CloudFormation deployment...")
        
        try:
            import boto3
            from pathlib import Path
            
            # Check if template exists
            template_path = Path("deploy/cloudformation/adpa-infrastructure.yaml")
            if template_path.exists():
                print(f"✅ Found template: {template_path}")
                
                # Read the CloudFormation template
                with open(template_path, 'r') as f:
                    template_body = f.read()
                
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
                    
                except Exception as e:
                    if 'AlreadyExistsException' in str(e):
                        print('ℹ️  Stack already exists, checking status...')
                        try:
                            stack_info = cf_client.describe_stacks(StackName='adpa-infrastructure-development')
                            status = stack_info['Stacks'][0]['StackStatus']
                            print(f'Stack status: {status}')
                        except Exception as e2:
                            print(f'❌ Error checking stack status: {e2}')
                    else:
                        print(f'❌ Stack creation failed: {e}')
            else:
                print(f"❌ Template not found: {template_path}")
                
        except ImportError:
            print("❌ boto3 not available")
        except Exception as e:
            print(f"❌ CloudFormation deployment failed: {e}")
        
        # Step 3: Check AWS resources
        print("\\nSTEP 3: Checking AWS resources...")
        
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            
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
                
        except ImportError:
            print("❌ boto3 not available for resource checking")
        except Exception as e:
            print(f"❌ AWS resource check failed: {e}")

except Exception as e:
    print(f"❌ Deployment execution failed: {e}")
    import traceback
    traceback.print_exc()

print("\\n" + "=" * 60)
print("DEPLOYMENT EXECUTION COMPLETED")
print("=" * 60)