#!/usr/bin/env python3
"""Deploy API Gateway configuration"""
import boto3
import sys

def main():
    client = boto3.client('apigateway', region_name='us-east-2')
    api_id = 'cr1kkj7213'
    
    try:
        # Deploy to prod stage
        response = client.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Complete API with all 8 endpoints configured'
        )
        print(f"✅ Deployment successful!")
        print(f"Deployment ID: {response['id']}")
        print(f"\nAPI URL: https://{api_id}.execute-api.us-east-2.amazonaws.com/prod")
        return 0
    except client.exceptions.BadRequestException as e:
        print(f"❌ Deployment failed: {e}")
        print("\nChecking for methods without integrations...")
        
        # Get all resources
        resources = client.get_resources(restApiId=api_id)
        
        for resource in resources['items']:
            res_id = resource['id']
            path = resource.get('path', 'unknown')
            methods = resource.get('resourceMethods', {})
            
            for method in methods:
                try:
                    client.get_integration(
                        restApiId=api_id,
                        resourceId=res_id,
                        httpMethod=method
                    )
                except client.exceptions.NotFoundException:
                    print(f"❌ MISSING INTEGRATION: {path} {method}")
        
        return 1

if __name__ == '__main__':
    sys.exit(main())
