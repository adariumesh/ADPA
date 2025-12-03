#!/usr/bin/env python3
"""
ADPA Docker Lambda Deployment
Deploy ADPA as a container image to AWS Lambda
"""

import boto3
import subprocess
import json
import sys
import time
from pathlib import Path

# Configuration
CONFIG = {
    "region": "us-east-2",
    "account_id": "083308938449",
    "function_name": "adpa-data-processor-development",
    "ecr_repo_name": "adpa",
    "image_tag": "latest",
    "memory": 3008,
    "timeout": 900,
    "data_bucket": "adpa-data-083308938449-development",
    "model_bucket": "adpa-models-083308938449-development",
    "role_name": "adpa-lambda-execution-role-development"
}


class DockerLambdaDeployer:
    """Deploy ADPA as Docker container to Lambda"""
    
    def __init__(self):
        self.ecr_client = boto3.client('ecr', region_name=CONFIG['region'])
        self.lambda_client = boto3.client('lambda', region_name=CONFIG['region'])
        self.iam_client = boto3.client('iam', region_name=CONFIG['region'])
        self.ecr_uri = None
        self.image_uri = None
        
        print("=" * 70)
        print("🐳 ADPA Docker Lambda Deployment")
        print("=" * 70)
        print(f"Region: {CONFIG['region']}")
        print(f"Function: {CONFIG['function_name']}")
        print(f"ECR Repo: {CONFIG['ecr_repo_name']}")
        print("=" * 70)
    
    def deploy(self) -> bool:
        """Execute full Docker deployment"""
        
        try:
            # Step 1: Create ECR repository
            if not self._create_ecr_repository():
                return False
            
            # Step 2: Build Docker image
            if not self._build_docker_image():
                return False
            
            # Step 3: Push to ECR
            if not self._push_to_ecr():
                return False
            
            # Step 4: Deploy Lambda function
            if not self._deploy_lambda_function():
                return False
            
            # Step 5: Test deployment
            if not self._test_deployment():
                print("\n⚠️  Deployment succeeded but tests failed")
                return True
            
            print("\n" + "=" * 70)
            print("✅ DOCKER DEPLOYMENT SUCCESSFUL")
            print("=" * 70)
            self._print_success_info()
            return True
            
        except Exception as e:
            print(f"\n❌ Deployment failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_ecr_repository(self) -> bool:
        """Create ECR repository if it doesn't exist"""
        
        print("\n📦 Step 1: Setting up ECR Repository")
        print("-" * 70)
        
        try:
            # Try to describe the repository
            response = self.ecr_client.describe_repositories(
                repositoryNames=[CONFIG['ecr_repo_name']]
            )
            repo = response['repositories'][0]
            self.ecr_uri = repo['repositoryUri']
            print(f"   ✅ Repository exists: {self.ecr_uri}")
            
        except self.ecr_client.exceptions.RepositoryNotFoundException:
            # Create repository
            print(f"   Creating new ECR repository: {CONFIG['ecr_repo_name']}...")
            
            response = self.ecr_client.create_repository(
                repositoryName=CONFIG['ecr_repo_name'],
                imageScanningConfiguration={'scanOnPush': True},
                encryptionConfiguration={'encryptionType': 'AES256'}
            )
            
            self.ecr_uri = response['repository']['repositoryUri']
            print(f"   ✅ Repository created: {self.ecr_uri}")
        
        self.image_uri = f"{self.ecr_uri}:{CONFIG['image_tag']}"
        return True
    
    def _build_docker_image(self) -> bool:
        """Build Docker image"""
        
        print("\n🔨 Step 2: Building Docker Image")
        print("-" * 70)
        print("   This may take 5-8 minutes...")
        
        try:
            # Build image
            print(f"   Building image: {self.image_uri}")
            
            result = subprocess.run([
                "docker", "build",
                "--platform", "linux/amd64",
                "-t", self.image_uri,
                "-f", "Dockerfile",
                "."
            ], capture_output=True, text=True, cwd=".")
            
            if result.returncode != 0:
                print(f"   ❌ Build failed:")
                print(result.stderr)
                return False
            
            print("   ✅ Image built successfully")
            
            # Show image size
            result = subprocess.run([
                "docker", "images", self.image_uri,
                "--format", "{{.Size}}"
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                print(f"   Image size: {result.stdout.strip()}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error building image: {e}")
            return False
    
    def _push_to_ecr(self) -> bool:
        """Push Docker image to ECR"""
        
        print("\n📤 Step 3: Pushing Image to ECR")
        print("-" * 70)
        print("   This may take 3-5 minutes...")
        
        try:
            # Get ECR login token
            print("   Authenticating with ECR...")
            
            response = self.ecr_client.get_authorization_token()
            auth_data = response['authorizationData'][0]
            token = auth_data['authorizationToken']
            endpoint = auth_data['proxyEndpoint']
            
            # Decode token (format is "AWS:password")
            import base64
            decoded = base64.b64decode(token).decode('utf-8')
            password = decoded.split(':')[1]
            
            # Docker login
            result = subprocess.run([
                "docker", "login",
                "--username", "AWS",
                "--password-stdin",
                endpoint
            ], input=password, text=True, capture_output=True)
            
            if result.returncode != 0:
                print(f"   ❌ ECR login failed: {result.stderr}")
                return False
            
            print("   ✅ Authenticated")
            
            # Push image
            print(f"   Pushing {self.image_uri}...")
            
            result = subprocess.run([
                "docker", "push", self.image_uri
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"   ❌ Push failed: {result.stderr}")
                return False
            
            print("   ✅ Image pushed successfully")
            return True
            
        except Exception as e:
            print(f"   ❌ Error pushing image: {e}")
            return False
    
    def _deploy_lambda_function(self) -> bool:
        """Deploy or update Lambda function with container image"""
        
        print("\n🚀 Step 4: Deploying Lambda Function")
        print("-" * 70)
        
        # Get role ARN
        role_response = self.iam_client.get_role(RoleName=CONFIG['role_name'])
        role_arn = role_response['Role']['Arn']
        
        try:
            # Check if function exists
            print(f"   Checking if function exists...")
            existing = self.lambda_client.get_function(FunctionName=CONFIG['function_name'])
            
            # Check package type
            package_type = existing['Configuration'].get('PackageType', 'Zip')
            
            if package_type == 'Zip':
                # Need to delete and recreate as Image type
                print(f"   Function exists as Zip package, converting to Image...")
                print(f"   Deleting existing function...")
                
                self.lambda_client.delete_function(FunctionName=CONFIG['function_name'])
                
                # Wait a moment for deletion
                time.sleep(3)
                print(f"   ✅ Old function deleted")
                
                # Create new function with Image
                print(f"   Creating new function from container image...")
                
                response = self.lambda_client.create_function(
                    FunctionName=CONFIG['function_name'],
                    Role=role_arn,
                    Code={'ImageUri': self.image_uri},
                    PackageType='Image',
                    Timeout=CONFIG['timeout'],
                    MemorySize=CONFIG['memory'],
                    Environment={
                        'Variables': {
                            'DATA_BUCKET': CONFIG['data_bucket'],
                            'MODEL_BUCKET': CONFIG['model_bucket']
                        }
                    },
                    Architectures=['x86_64']
                )
                print(f"   ✅ Function created")
            else:
                # Function exists as Image, update it
                print(f"   Updating function with new image...")
                
                response = self.lambda_client.update_function_code(
                    FunctionName=CONFIG['function_name'],
                    ImageUri=self.image_uri
                )
                print(f"   ✅ Code updated")
                
                # Wait for update
                print(f"   Waiting for update to complete...", end=" ")
                waiter = self.lambda_client.get_waiter('function_updated')
                waiter.wait(FunctionName=CONFIG['function_name'])
                print("✅")
                
                # Update configuration
                print(f"   Updating configuration...")
                response = self.lambda_client.update_function_configuration(
                    FunctionName=CONFIG['function_name'],
                    Role=role_arn,
                    Timeout=CONFIG['timeout'],
                    MemorySize=CONFIG['memory'],
                    Environment={
                        'Variables': {
                            'DATA_BUCKET': CONFIG['data_bucket'],
                            'MODEL_BUCKET': CONFIG['model_bucket']
                        }
                    }
                )
                print(f"   ✅ Configuration updated")
            
        except self.lambda_client.exceptions.ResourceNotFoundException:
            # Create new function
            print(f"   Creating new function from container image...")
            
            response = self.lambda_client.create_function(
                FunctionName=CONFIG['function_name'],
                Role=role_arn,
                Code={'ImageUri': self.image_uri},
                PackageType='Image',
                Timeout=CONFIG['timeout'],
                MemorySize=CONFIG['memory'],
                Environment={
                    'Variables': {
                        'DATA_BUCKET': CONFIG['data_bucket'],
                        'MODEL_BUCKET': CONFIG['model_bucket']
                    }
                },
                Architectures=['x86_64']
            )
            print(f"   ✅ Function created")
        
        # Wait for function to be ready
        print(f"   Waiting for function to be active...", end=" ")
        time.sleep(5)
        print("✅")
        
        function_arn = response['FunctionArn']
        print(f"   ✅ Lambda function deployed")
        print(f"   ARN: {function_arn}")
        
        return True
    
    def _test_deployment(self) -> bool:
        """Test the deployed function"""
        
        print("\n🧪 Step 5: Testing Deployment")
        print("-" * 70)
        
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
                
                components = result.get('components', {})
                for comp, comp_status in components.items():
                    icon = "✅" if comp_status else "❌"
                    print(f"      {icon} {comp}: {comp_status}")
                
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
    
    def _print_success_info(self):
        """Print success info"""
        
        print("\n📊 Deployment Summary:")
        print(f"   Function: {CONFIG['function_name']}")
        print(f"   Image: {self.image_uri}")
        print(f"   Memory: {CONFIG['memory']} MB")
        print(f"   Timeout: {CONFIG['timeout']} seconds")
        print(f"   Package Type: Container Image")
        
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
        
        print("\n🎉 ADPA is now deployed with full ML dependencies!")


def main():
    """Main entry point"""
    
    deployer = DockerLambdaDeployer()
    success = deployer.deploy()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
