#!/usr/bin/env python3
"""
Setup complete API Gateway for ADPA
"""

import boto3
import json
import time
import os
import sys

# Import centralized AWS configuration
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config.aws_config import (
        AWS_ACCOUNT_ID, AWS_REGION, LAMBDA_FUNCTION_NAME,
        get_credentials_from_csv
    )
    REGION = AWS_REGION
    ACCOUNT_ID = AWS_ACCOUNT_ID
    LAMBDA_FUNCTION = LAMBDA_FUNCTION_NAME
except ImportError:
    # Fallback values
    REGION = "us-east-2"
    ACCOUNT_ID = "083308938449"
    LAMBDA_FUNCTION = "adpa-data-processor-development"
    get_credentials_from_csv = None

API_NAME = "adpa-api"
STAGE_NAME = "prod"

def create_api_gateway():
    print("🚀 Setting up ADPA API Gateway...")
    print(f"   Account: {ACCOUNT_ID}")
    print(f"   Region: {REGION}")
    
    # Get clients with credentials from rootkey.csv if available
    try:
        if get_credentials_from_csv:
            creds = get_credentials_from_csv()
            if creds['access_key_id'] and creds['secret_access_key']:
                apigateway = boto3.client(
                    'apigateway', 
                    region_name=REGION,
                    aws_access_key_id=creds['access_key_id'],
                    aws_secret_access_key=creds['secret_access_key']
                )
                lambda_client = boto3.client(
                    'lambda', 
                    region_name=REGION,
                    aws_access_key_id=creds['access_key_id'],
                    aws_secret_access_key=creds['secret_access_key']
                )
                print("   ✅ Using credentials from rootkey.csv")
            else:
                raise ValueError("No credentials found")
        else:
            raise ValueError("Config module not available")
    except Exception:
        apigateway = boto3.client('apigateway', region_name=REGION)
        lambda_client = boto3.client('lambda', region_name=REGION)
        print("   ⚠️  Using default AWS credential chain")
    
    # Create REST API
    print("📋 Creating REST API...")
    api_response = apigateway.create_rest_api(
        name=API_NAME,
        description='ADPA - Autonomous Data Pipeline Agent API',
        endpointConfiguration={'types': ['REGIONAL']}
    )
    api_id = api_response['id']
    print(f"   ✅ API created: {api_id}")
    
    # Get root resource
    resources = apigateway.get_resources(restApiId=api_id)
    root_id = [r for r in resources['items'] if r['path'] == '/'][0]['id']
    
    # Define endpoints
    endpoints = [
        {'path': 'health', 'methods': ['GET']},
        {'path': 'pipelines', 'methods': ['GET', 'POST', 'OPTIONS']},
        {'path': 'data', 'methods': []},
    ]
    
    # Create resources
    print("📝 Creating API resources...")
    
    # /health
    health_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='health'
    )
    create_method(apigateway, api_id, health_resource['id'], 'GET', LAMBDA_FUNCTION, REGION, ACCOUNT_ID)
    create_method(apigateway, api_id, health_resource['id'], 'OPTIONS', LAMBDA_FUNCTION, REGION, ACCOUNT_ID, cors=True)
    print("   ✅ /health")
    
    # /pipelines
    pipelines_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='pipelines'
    )
    create_method(apigateway, api_id, pipelines_resource['id'], 'GET', LAMBDA_FUNCTION, REGION, ACCOUNT_ID)
    create_method(apigateway, api_id, pipelines_resource['id'], 'POST', LAMBDA_FUNCTION, REGION, ACCOUNT_ID)
    create_method(apigateway, api_id, pipelines_resource['id'], 'OPTIONS', LAMBDA_FUNCTION, REGION, ACCOUNT_ID, cors=True)
    print("   ✅ /pipelines")
    
    # /pipelines/{id}
    pipeline_id_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=pipelines_resource['id'],
        pathPart='{id}'
    )
    create_method(apigateway, api_id, pipeline_id_resource['id'], 'GET', LAMBDA_FUNCTION, REGION, ACCOUNT_ID)
    create_method(apigateway, api_id, pipeline_id_resource['id'], 'OPTIONS', LAMBDA_FUNCTION, REGION, ACCOUNT_ID, cors=True)
    print("   ✅ /pipelines/{id}")
    
    # /pipelines/{id}/execution
    execution_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=pipeline_id_resource['id'],
        pathPart='execution'
    )
    create_method(apigateway, api_id, execution_resource['id'], 'GET', LAMBDA_FUNCTION, REGION, ACCOUNT_ID)
    create_method(apigateway, api_id, execution_resource['id'], 'OPTIONS', LAMBDA_FUNCTION, REGION, ACCOUNT_ID, cors=True)
    print("   ✅ /pipelines/{id}/execution")
    
    # /pipelines/{id}/results
    results_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=pipeline_id_resource['id'],
        pathPart='results'
    )
    create_method(apigateway, api_id, results_resource['id'], 'GET', LAMBDA_FUNCTION, REGION, ACCOUNT_ID)
    create_method(apigateway, api_id, results_resource['id'], 'OPTIONS', LAMBDA_FUNCTION, REGION, ACCOUNT_ID, cors=True)
    print("   ✅ /pipelines/{id}/results")
    
    # /pipelines/{id}/logs
    logs_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=pipeline_id_resource['id'],
        pathPart='logs'
    )
    create_method(apigateway, api_id, logs_resource['id'], 'GET', LAMBDA_FUNCTION, REGION, ACCOUNT_ID)
    create_method(apigateway, api_id, logs_resource['id'], 'OPTIONS', LAMBDA_FUNCTION, REGION, ACCOUNT_ID, cors=True)
    print("   ✅ /pipelines/{id}/logs")
    
    # /data
    data_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='data'
    )
    
    # /data/upload
    upload_resource = apigateway.create_resource(
        restApiId=api_id,
        parentId=data_resource['id'],
        pathPart='upload'
    )
    create_method(apigateway, api_id, upload_resource['id'], 'POST', LAMBDA_FUNCTION, REGION, ACCOUNT_ID)
    create_method(apigateway, api_id, upload_resource['id'], 'OPTIONS', LAMBDA_FUNCTION, REGION, ACCOUNT_ID, cors=True)
    print("   ✅ /data/upload")
    
    # Add Lambda permission
    print("🔒 Setting up Lambda permissions...")
    lambda_arn = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{LAMBDA_FUNCTION}"
    
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION,
            StatementId=f'apigateway-{api_id}',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*'
        )
        print("   ✅ Lambda permission added")
    except lambda_client.exceptions.ResourceConflictException:
        print("   ℹ️  Lambda permission already exists")
    
    # Deploy API
    print("🚀 Deploying API...")
    deployment = apigateway.create_deployment(
        restApiId=api_id,
        stageName=STAGE_NAME,
        description='ADPA API Production Deployment'
    )
    print(f"   ✅ Deployed to stage: {STAGE_NAME}")
    
    # Get API URL
    api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/{STAGE_NAME}"
    
    print("\n" + "=" * 60)
    print("✅ API GATEWAY SETUP COMPLETE")
    print("=" * 60)
    print(f"API ID: {api_id}")
    print(f"API URL: {api_url}")
    print("\nEndpoints:")
    print(f"  GET  {api_url}/health")
    print(f"  GET  {api_url}/pipelines")
    print(f"  POST {api_url}/pipelines")
    print(f"  GET  {api_url}/pipelines/{{id}}")
    print(f"  GET  {api_url}/pipelines/{{id}}/execution")
    print(f"  GET  {api_url}/pipelines/{{id}}/results")
    print(f"  GET  {api_url}/pipelines/{{id}}/logs")
    print(f"  POST {api_url}/data/upload")
    print("=" * 60)
    
    return api_id, api_url


def create_method(apigateway, api_id, resource_id, method, lambda_function, region, account_id, cors=False):
    """Create a method with Lambda integration"""
    
    lambda_uri = f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/arn:aws:lambda:{region}:{account_id}:function:{lambda_function}/invocations"
    
    # Create method
    apigateway.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod=method,
        authorizationType='NONE',
        requestParameters={
            'method.request.path.id': True
        } if '{id}' in str(resource_id) else {}
    )
    
    if cors:
        # CORS mock integration
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=method,
            type='MOCK',
            requestTemplates={'application/json': '{"statusCode": 200}'}
        )
        
        apigateway.put_method_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=method,
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True
            }
        )
        
        apigateway.put_integration_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=method,
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'",
                'method.response.header.Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            },
            responseTemplates={'application/json': ''}
        )
    else:
        # Lambda proxy integration
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=method,
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=lambda_uri
        )


if __name__ == "__main__":
    create_api_gateway()
