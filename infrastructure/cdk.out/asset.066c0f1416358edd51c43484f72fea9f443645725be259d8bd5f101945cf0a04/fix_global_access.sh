#!/bin/bash

# Fix Global Access Stack Issues
# Debug and fix the CloudFormation global access deployment

set -e

echo "🔧 Debugging ADPA Global Access Issues"
echo "======================================"

# Configuration
STACK_NAME="adpa-global-access-development"
REGION="us-east-2"
PROJECT_NAME="adpa"
ENVIRONMENT="development"

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

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Check if stack exists and get failure details
print_status "Checking global access stack status..."

if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION >/dev/null 2>&1; then
    print_warning "Stack exists, checking status..."
    
    STACK_STATUS=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query "Stacks[0].StackStatus" \
        --output text)
    
    print_status "Current stack status: $STACK_STATUS"
    
    if [[ "$STACK_STATUS" == "ROLLBACK_COMPLETE" || "$STACK_STATUS" == "CREATE_FAILED" ]]; then
        print_status "Getting failure events..."
        aws cloudformation describe-stack-events \
            --stack-name $STACK_NAME \
            --region $REGION \
            --query "StackEvents[?ResourceStatus=='CREATE_FAILED'].{Resource:LogicalResourceId,Reason:ResourceStatusReason}" \
            --output table
        
        print_status "Deleting failed stack..."
        aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION
        
        print_status "Waiting for stack deletion..."
        aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION
        print_status "Stack deleted successfully"
    fi
else
    print_status "No existing stack found"
fi

# Step 2: Create a simplified global access stack
print_status "Creating simplified global access configuration..."

cat > simplified_global_access.yaml << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Description: 'ADPA Simplified Global Access - Basic API Gateway'

Parameters:
  ProjectName:
    Type: String
    Default: 'adpa'
  Environment:
    Type: String
    Default: 'development'
  DataProcessorFunctionArn:
    Type: String
    Description: 'ARN of the ADPA data processor Lambda function'

Resources:
  # Simple API Gateway
  ADPASimpleAPI:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: !Sub '${ProjectName}-api-${Environment}'
      Description: 'Simple API for ADPA'
      EndpointConfiguration:
        Types: ['REGIONAL']

  # Pipeline resource
  PipelineResource:
    Type: AWS::ApiGateway::Resource
    Properties:
      RestApiId: !Ref ADPASimpleAPI
      ParentId: !GetAtt ADPASimpleAPI.RootResourceId
      PathPart: 'pipeline'

  # POST method for pipeline
  PipelinePostMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      RestApiId: !Ref ADPASimpleAPI
      ResourceId: !Ref PipelineResource
      HttpMethod: POST
      AuthorizationType: NONE
      Integration:
        Type: AWS_PROXY
        IntegrationHttpMethod: POST
        Uri: !Sub 'arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${DataProcessorFunctionArn}/invocations'
      MethodResponses:
        - StatusCode: 200
          ResponseModels:
            application/json: Empty

  # Health check resource
  HealthResource:
    Type: AWS::ApiGateway::Resource
    Properties:
      RestApiId: !Ref ADPASimpleAPI
      ParentId: !GetAtt ADPASimpleAPI.RootResourceId
      PathPart: 'health'

  # GET method for health check
  HealthGetMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      RestApiId: !Ref ADPASimpleAPI
      ResourceId: !Ref HealthResource
      HttpMethod: GET
      AuthorizationType: NONE
      Integration:
        Type: AWS_PROXY
        IntegrationHttpMethod: POST
        Uri: !Sub 'arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${DataProcessorFunctionArn}/invocations'
      MethodResponses:
        - StatusCode: 200
          ResponseModels:
            application/json: Empty

  # Lambda permission for API Gateway
  LambdaApiPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref DataProcessorFunctionArn
      Action: lambda:InvokeFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub 'arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${ADPASimpleAPI}/*'

  # API Deployment
  APIDeployment:
    Type: AWS::ApiGateway::Deployment
    DependsOn: 
      - PipelinePostMethod
      - HealthGetMethod
    Properties:
      RestApiId: !Ref ADPASimpleAPI
      StageName: 'v1'

Outputs:
  APIEndpoint:
    Description: 'ADPA API Gateway endpoint'
    Value: !Sub 'https://${ADPASimpleAPI}.execute-api.${AWS::Region}.amazonaws.com/v1'
    Export:
      Name: !Sub '${ProjectName}-api-endpoint-${Environment}'
  
  APIId:
    Description: 'API Gateway ID'
    Value: !Ref ADPASimpleAPI
    Export:
      Name: !Sub '${ProjectName}-api-id-${Environment}'
EOF

# Step 3: Get the Lambda function ARN
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

# Step 4: Deploy simplified global access stack
print_status "Deploying simplified global access stack..."
aws cloudformation deploy \
    --template-file simplified_global_access.yaml \
    --stack-name adpa-simple-global-access-development \
    --parameter-overrides \
        ProjectName=$PROJECT_NAME \
        Environment=$ENVIRONMENT \
        DataProcessorFunctionArn=$LAMBDA_ARN \
    --capabilities CAPABILITY_IAM \
    --region $REGION

if [ $? -eq 0 ]; then
    print_status "✅ Global access stack deployed successfully!"
    
    # Get API endpoint
    API_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name adpa-simple-global-access-development \
        --region $REGION \
        --query "Stacks[0].Outputs[?OutputKey=='APIEndpoint'].OutputValue" \
        --output text)
    
    print_status "API Endpoint: $API_ENDPOINT"
    
    # Test the API
    print_status "Testing API endpoint..."
    sleep 10  # Wait for deployment to propagate
    
    curl -s "$API_ENDPOINT/health" || print_warning "API not ready yet, may need a few minutes"
    
else
    print_error "❌ Global access deployment failed"
    exit 1
fi

# Step 5: Cleanup
rm -f simplified_global_access.yaml

echo
echo "======================================"
echo "🎉 GLOBAL ACCESS FIXED! 🎉"
echo "======================================"
echo
print_status "ADPA is now globally accessible via API Gateway!"
print_status "API Endpoint: $API_ENDPOINT"
echo
print_status "Test endpoints:"
echo "  Health Check: $API_ENDPOINT/health"
echo "  Pipeline:     $API_ENDPOINT/pipeline (POST)"
echo
print_status "Example usage:"
echo "  curl '$API_ENDPOINT/health'"
echo "  curl -X POST '$API_ENDPOINT/pipeline' -d '{\"action\":\"run_pipeline\",\"dataset_path\":\"s3://bucket/data.csv\"}'"
echo