#!/usr/bin/env python3
"""Add OPTIONS integration to /pipelines"""
import boto3

client = boto3.client('apigateway', region_name='us-east-2')
api_id = 'cr1kkj7213'

# Add MOCK integration for OPTIONS on /pipelines (oi471y)
response = client.put_integration_response(
    restApiId=api_id,
    resourceId='oi471y',
    httpMethod='OPTIONS',
    statusCode='200',
    responseParameters={
        'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
        'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
        'method.response.header.Access-Control-Allow-Origin': "'*'"
    }
)

print("✅ OPTIONS integration response added for /pipelines")

# Add MOCK integration
integration_response = client.put_integration(
    restApiId=api_id,
    resourceId='oi471y',
    httpMethod='OPTIONS',
    type='MOCK',
    requestTemplates={
        'application/json': '{"statusCode": 200}'
    }
)

print("✅ OPTIONS MOCK integration added for /pipelines")

# Add method response
method_response = client.put_method_response(
    restApiId=api_id,
    resourceId='oi471y',
    httpMethod='OPTIONS',
    statusCode='200',
    responseParameters={
        'method.response.header.Access-Control-Allow-Headers': False,
        'method.response.header.Access-Control-Allow-Methods': False,
        'method.response.header.Access-Control-Allow-Origin': False
    }
)

print("✅ OPTIONS method response added for /pipelines")
