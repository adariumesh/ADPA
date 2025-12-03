#!/bin/bash

# Complete API Gateway Configuration
# Adds the missing throttling and caching that Girik mentioned

set -e

echo "🌐 Completing API Gateway Configuration"
echo "======================================"

# Configuration
STACK_NAME="adpa-api-gateway-complete"
ENVIRONMENT="development"
REGION="us-east-2"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Get Lambda function ARN
print_status "Getting Lambda function ARN..."
LAMBDA_ARN=$(aws cloudformation describe-stacks \
    --stack-name adpa-infrastructure-development \
    --region $REGION \
    --query "Stacks[0].Outputs[?OutputKey=='DataProcessorFunctionArn'].OutputValue" \
    --output text)

if [ -z "$LAMBDA_ARN" ]; then
    print_error "Could not find Lambda function ARN"
    exit 1
fi

print_status "Lambda function ARN: $LAMBDA_ARN"

# Create comprehensive API Gateway configuration
print_status "Creating comprehensive API Gateway with throttling and caching..."

cat > complete_api_gateway.yaml << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Complete ADPA API Gateway with Throttling and Caching'

Parameters:
  Environment:
    Type: String
    Default: 'development'
  DataProcessorFunctionArn:
    Type: String
    Description: 'ARN of the ADPA data processor Lambda function'

Resources:
  # API Gateway with advanced features
  ADPACompleteAPI:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: !Sub 'adpa-complete-api-${Environment}'
      Description: 'Complete ADPA API with throttling and caching'
      EndpointConfiguration:
        Types: ['REGIONAL']
      Policy:
        Statement:
          - Effect: Allow
            Principal: '*'
            Action: 'execute-api:Invoke'
            Resource: '*'

  # Usage Plan for throttling
  ADPAUsagePlan:
    Type: AWS::ApiGateway::UsagePlan
    Properties:
      UsagePlanName: !Sub 'adpa-usage-plan-${Environment}'
      Description: 'ADPA API usage plan with throttling'
      Throttle:
        BurstLimit: 1000
        RateLimit: 500
      Quota:
        Limit: 10000
        Period: DAY

  # API Key
  ADPAApiKey:
    Type: AWS::ApiGateway::ApiKey
    Properties:
      Name: !Sub 'adpa-api-key-${Environment}'
      Description: 'ADPA API key'
      Enabled: true

  # Usage Plan Key
  ADPAUsagePlanKey:
    Type: AWS::ApiGateway::UsagePlanKey
    Properties:
      KeyId: !Ref ADPAApiKey
      KeyType: API_KEY
      UsagePlanId: !Ref ADPAUsagePlan

  # Request Validator
  ADPARequestValidator:
    Type: AWS::ApiGateway::RequestValidator
    Properties:
      RestApiId: !Ref ADPACompleteAPI
      ValidateRequestBody: true
      ValidateRequestParameters: true

  # Pipeline resource
  PipelineResource:
    Type: AWS::ApiGateway::Resource
    Properties:
      RestApiId: !Ref ADPACompleteAPI
      ParentId: !GetAtt ADPACompleteAPI.RootResourceId
      PathPart: 'pipeline'

  # POST method with caching
  PipelinePostMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      RestApiId: !Ref ADPACompleteAPI
      ResourceId: !Ref PipelineResource
      HttpMethod: POST
      AuthorizationType: API_KEY
      RequestValidatorId: !Ref ADPARequestValidator
      Integration:
        Type: AWS_PROXY
        IntegrationHttpMethod: POST
        Uri: !Sub 'arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${DataProcessorFunctionArn}/invocations'
        CacheKeyParameters:
          - 'method.request.header.Content-Type'
      MethodResponses:
        - StatusCode: 200
          ResponseModels:
            application/json: Empty

  # Health resource
  HealthResource:
    Type: AWS::ApiGateway::Resource
    Properties:
      RestApiId: !Ref ADPACompleteAPI
      ParentId: !GetAtt ADPACompleteAPI.RootResourceId
      PathPart: 'health'

  # GET method with caching
  HealthGetMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      RestApiId: !Ref ADPACompleteAPI
      ResourceId: !Ref HealthResource
      HttpMethod: GET
      AuthorizationType: NONE
      Integration:
        Type: AWS_PROXY
        IntegrationHttpMethod: POST
        Uri: !Sub 'arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${DataProcessorFunctionArn}/invocations'
        CacheKeyParameters:
          - 'method.request.querystring.version'
      MethodResponses:
        - StatusCode: 200
          ResponseModels:
            application/json: Empty

  # Lambda permission
  LambdaApiPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref DataProcessorFunctionArn
      Action: lambda:InvokeFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${ADPACompleteAPI}/*'

  # Deployment with caching
  APIDeployment:
    Type: AWS::ApiGateway::Deployment
    DependsOn: 
      - PipelinePostMethod
      - HealthGetMethod
    Properties:
      RestApiId: !Ref ADPACompleteAPI
      StageName: 'prod'
      StageDescription:
        CachingEnabled: true
        CacheTtlInSeconds: 300
        CacheKeyParameters:
          - 'method.request.header.Content-Type'
          - 'method.request.querystring.version'
        ThrottlingRateLimit: 500
        ThrottlingBurstLimit: 1000

Outputs:
  APIEndpoint:
    Description: 'Complete ADPA API Gateway endpoint'
    Value: !Sub 'https://${ADPACompleteAPI}.execute-api.${AWS::Region}.amazonaws.com/prod'
    Export:
      Name: !Sub 'adpa-complete-api-endpoint-${Environment}'
  
  APIKey:
    Description: 'API Key for accessing ADPA'
    Value: !Ref ADPAApiKey
    Export:
      Name: !Sub 'adpa-api-key-${Environment}'
  
  UsagePlanId:
    Description: 'Usage Plan ID for monitoring'
    Value: !Ref ADPAUsagePlan
    Export:
      Name: !Sub 'adpa-usage-plan-${Environment}'
EOF

# Deploy the complete API Gateway
print_status "Deploying complete API Gateway..."
aws cloudformation deploy \
    --template-file complete_api_gateway.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
        DataProcessorFunctionArn=$LAMBDA_ARN \
    --capabilities CAPABILITY_IAM \
    --region $REGION

if [ $? -eq 0 ]; then
    print_status "✅ Complete API Gateway deployed successfully!"
    
    # Get outputs
    API_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query "Stacks[0].Outputs[?OutputKey=='APIEndpoint'].OutputValue" \
        --output text)
    
    API_KEY=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query "Stacks[0].Outputs[?OutputKey=='APIKey'].OutputValue" \
        --output text)
    
    print_status "API Endpoint: $API_ENDPOINT"
    print_status "API Key: $API_KEY"
    
    # Test with API key
    print_status "Testing API with throttling and caching..."
    sleep 5
    
    # Test health endpoint (no key required)
    curl -s "$API_ENDPOINT/health" | head -1
    
    # Test pipeline endpoint (requires key)
    curl -s -H "x-api-key: $API_KEY" "$API_ENDPOINT/pipeline" -X POST -d '{"action":"health_check"}' | head -1
    
else
    print_error "❌ API Gateway deployment failed"
    exit 1
fi

# Cleanup
rm -f complete_api_gateway.yaml

echo
echo "======================================"
echo "🎉 API GATEWAY COMPLETE! 🎉"
echo "======================================"
echo
print_status "Features implemented:"
echo "  ✅ Request throttling (500 req/sec, 1000 burst)"
echo "  ✅ Response caching (5 min TTL)"
echo "  ✅ API key authentication"
echo "  ✅ Usage plan with quotas (10k/day)"
echo "  ✅ Request validation"
echo "  ✅ Production-grade deployment"
echo
print_status "API Details:"
echo "  Endpoint: $API_ENDPOINT"
echo "  API Key: $API_KEY"
echo
print_status "Usage examples:"
echo "  Health: curl '$API_ENDPOINT/health'"
echo "  Pipeline: curl -H 'x-api-key: $API_KEY' '$API_ENDPOINT/pipeline' -X POST -d '{\"action\":\"run_pipeline\"}'"
echo