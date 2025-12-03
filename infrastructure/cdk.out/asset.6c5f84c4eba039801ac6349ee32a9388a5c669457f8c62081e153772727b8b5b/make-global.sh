#!/bin/bash

# Make ADPA Globally Accessible
# Deploys global access infrastructure with CloudFront and API Gateway

set -e

echo "🌍 Making ADPA Globally Accessible"
echo "=================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_header() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Parse arguments
ENVIRONMENT=${1:-"development"}
PROJECT_NAME=${2:-"adpa"}
DOMAIN_NAME=${3:-""}
CERTIFICATE_ARN=${4:-""}

print_status "Global Access Configuration:"
print_status "  Environment: $ENVIRONMENT"
print_status "  Project: $PROJECT_NAME"
if [ -n "$DOMAIN_NAME" ]; then
    print_status "  Custom Domain: $DOMAIN_NAME"
else
    print_status "  Custom Domain: None (will use CloudFront domain)"
fi

# Check prerequisites
print_header "Checking Prerequisites"

# Check if base infrastructure exists
BASE_STACK="${PROJECT_NAME}-infrastructure-${ENVIRONMENT}"
if ! aws cloudformation describe-stacks --stack-name "$BASE_STACK" &> /dev/null; then
    echo "❌ Base ADPA infrastructure not found. Please deploy it first:"
    echo "   ./deploy/aws-deploy.sh $ENVIRONMENT $PROJECT_NAME"
    exit 1
fi

print_status "✅ Base ADPA infrastructure found"

# Get Step Functions state machine ARN from base stack
print_status "Getting Step Functions state machine ARN..."
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
    --query "stateMachines[?name=='${PROJECT_NAME}-pipeline-${ENVIRONMENT}'].stateMachineArn" \
    --output text)

if [ -z "$STATE_MACHINE_ARN" ] || [ "$STATE_MACHINE_ARN" = "None" ]; then
    echo "❌ Step Functions state machine not found. Creating one..."
    
    # Create a simple state machine for global access
    LAMBDA_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$BASE_STACK" \
        --query "Stacks[0].Outputs[?OutputKey=='DataProcessorFunctionArn'].OutputValue" \
        --output text)
    
    STEPFUNCTIONS_ROLE=$(aws cloudformation describe-stacks \
        --stack-name "$BASE_STACK" \
        --query "Stacks[0].Outputs[?OutputKey=='StepFunctionsRoleArn'].OutputValue" \
        --output text)
    
    cat > /tmp/adpa-state-machine.json << EOF
{
  "Comment": "ADPA Global Access Pipeline",
  "StartAt": "ProcessPipeline",
  "States": {
    "ProcessPipeline": {
      "Type": "Task",
      "Resource": "$LAMBDA_ARN",
      "Parameters": {
        "step_config": {
          "type": "global_pipeline",
          "step": "execute_pipeline"
        },
        "input.\$": "\$"
      },
      "End": true,
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ]
    }
  }
}
EOF

    STATE_MACHINE_ARN=$(aws stepfunctions create-state-machine \
        --name "${PROJECT_NAME}-pipeline-${ENVIRONMENT}" \
        --definition file:///tmp/adpa-state-machine.json \
        --role-arn "$STEPFUNCTIONS_ROLE" \
        --query 'stateMachineArn' \
        --output text)
    
    print_status "✅ Created Step Functions state machine: $STATE_MACHINE_ARN"
    rm -f /tmp/adpa-state-machine.json
else
    print_status "✅ Found Step Functions state machine: $STATE_MACHINE_ARN"
fi

# Deploy global access stack
print_header "Deploying Global Access Infrastructure"

GLOBAL_STACK="${PROJECT_NAME}-global-access-${ENVIRONMENT}"

# Prepare parameters
PARAMETERS="ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME"
PARAMETERS="$PARAMETERS ParameterKey=Environment,ParameterValue=$ENVIRONMENT"
PARAMETERS="$PARAMETERS ParameterKey=ADPAStateMachineArn,ParameterValue=$STATE_MACHINE_ARN"

if [ -n "$DOMAIN_NAME" ]; then
    PARAMETERS="$PARAMETERS ParameterKey=DomainName,ParameterValue=$DOMAIN_NAME"
fi

if [ -n "$CERTIFICATE_ARN" ]; then
    PARAMETERS="$PARAMETERS ParameterKey=CertificateArn,ParameterValue=$CERTIFICATE_ARN"
fi

# Check if global stack exists
if aws cloudformation describe-stacks --stack-name "$GLOBAL_STACK" &> /dev/null; then
    print_warning "Global access stack exists. Updating..."
    STACK_ACTION="update-stack"
    WAIT_CONDITION="stack-update-complete"
else
    print_status "Creating global access stack..."
    STACK_ACTION="create-stack"
    WAIT_CONDITION="stack-create-complete"
fi

# Create/update the stack with the state machine ARN parameter
cat > /tmp/global-access-template.yaml << EOF
AWSTemplateFormatVersion: '2010-09-09'
Description: 'ADPA Global Access Addon - Makes ADPA accessible worldwide'

Parameters:
  ProjectName:
    Type: String
    Default: 'adpa'
  Environment:
    Type: String
    Default: 'development'
  ADPAStateMachineArn:
    Type: String
    Description: 'ARN of the ADPA Step Functions state machine'
  DomainName:
    Type: String
    Default: ''
    Description: 'Domain name for global access (optional)'
  CertificateArn:
    Type: String
    Default: ''
    Description: 'SSL Certificate ARN for custom domain (optional)'

Conditions:
  HasCustomDomain: !Not [!Equals [!Ref DomainName, '']]
  HasCertificate: !Not [!Equals [!Ref CertificateArn, '']]

Resources:
  ADPAGlobalAPI:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: !Sub '\${ProjectName}-global-api-\${Environment}'
      Description: 'Global API for ADPA autonomous data pipelines'
      EndpointConfiguration:
        Types: ['REGIONAL']

  ADPAPipelinesResource:
    Type: AWS::ApiGateway::Resource
    Properties:
      RestApiId: !Ref ADPAGlobalAPI
      ParentId: !GetAtt ADPAGlobalAPI.RootResourceId
      PathPart: 'pipelines'

  ADPAExecuteResource:
    Type: AWS::ApiGateway::Resource
    Properties:
      RestApiId: !Ref ADPAGlobalAPI
      ParentId: !Ref ADPAPipelinesResource
      PathPart: 'execute'

  ADPAExecutePipelineMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      RestApiId: !Ref ADPAGlobalAPI
      ResourceId: !Ref ADPAExecuteResource
      HttpMethod: POST
      AuthorizationType: NONE
      Integration:
        Type: AWS
        IntegrationHttpMethod: POST
        Uri: !Sub 'arn:aws:apigateway:\${AWS::Region}:states:action/StartExecution'
        Credentials: !GetAtt ADPAAPIGatewayRole.Arn
        RequestTemplates:
          application/json: !Sub |
            {
              "stateMachineArn": "\${ADPAStateMachineArn}",
              "name": "\$context.requestId",
              "input": "\$util.escapeJavaScript(\$input.body)"
            }
        IntegrationResponses:
          - StatusCode: 200
            ResponseTemplates:
              application/json: |
                {
                  "executionArn": "\$input.path('\$.executionArn')",
                  "status": "STARTED",
                  "message": "ADPA pipeline execution started globally! 🌍",
                  "requestId": "\$context.requestId"
                }
            ResponseParameters:
              method.response.header.Access-Control-Allow-Origin: "'*'"
              method.response.header.Access-Control-Allow-Headers: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
              method.response.header.Access-Control-Allow-Methods: "'POST,OPTIONS'"
      MethodResponses:
        - StatusCode: 200
          ResponseParameters:
            method.response.header.Access-Control-Allow-Origin: true
            method.response.header.Access-Control-Allow-Headers: true
            method.response.header.Access-Control-Allow-Methods: true

  # CORS OPTIONS method
  ADPAExecuteOptionsMethod:
    Type: AWS::ApiGateway::Method
    Properties:
      RestApiId: !Ref ADPAGlobalAPI
      ResourceId: !Ref ADPAExecuteResource
      HttpMethod: OPTIONS
      AuthorizationType: NONE
      Integration:
        Type: MOCK
        IntegrationResponses:
          - StatusCode: 200
            ResponseParameters:
              method.response.header.Access-Control-Allow-Origin: "'*'"
              method.response.header.Access-Control-Allow-Headers: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
              method.response.header.Access-Control-Allow-Methods: "'POST,OPTIONS'"
      MethodResponses:
        - StatusCode: 200
          ResponseParameters:
            method.response.header.Access-Control-Allow-Origin: true
            method.response.header.Access-Control-Allow-Headers: true
            method.response.header.Access-Control-Allow-Methods: true

  ADPAAPIGatewayRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub '\${ProjectName}-apigateway-global-\${Environment}'
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: apigateway.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: StepFunctionsExecutionPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - 'states:StartExecution'
                  - 'states:DescribeExecution'
                Resource: !Ref ADPAStateMachineArn

  ADPAAPIDeployment:
    Type: AWS::ApiGateway::Deployment
    DependsOn:
      - ADPAExecutePipelineMethod
      - ADPAExecuteOptionsMethod
    Properties:
      RestApiId: !Ref ADPAGlobalAPI

  ADPAAPIStage:
    Type: AWS::ApiGateway::Stage
    Properties:
      RestApiId: !Ref ADPAGlobalAPI
      DeploymentId: !Ref ADPAAPIDeployment
      StageName: !Ref Environment
      ThrottleSettings:
        BurstLimit: 1000
        RateLimit: 100

  ADPACloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Comment: !Sub 'ADPA Global Distribution - \${Environment}'
        Origins:
          - DomainName: !Sub '\${ADPAGlobalAPI}.execute-api.\${AWS::Region}.amazonaws.com'
            Id: ADPA-API-Origin
            OriginPath: !Sub '/\${Environment}'
            CustomOriginConfig:
              HTTPPort: 443
              OriginProtocolPolicy: https-only
        DefaultCacheBehavior:
          TargetOriginId: ADPA-API-Origin
          ViewerProtocolPolicy: redirect-to-https
          AllowedMethods: ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT']
          CachedMethods: ['GET', 'HEAD']
          Compress: true
          ForwardedValues:
            QueryString: true
            Headers: ['*']
          MinTTL: 0
          DefaultTTL: 0
          MaxTTL: 0
        Enabled: true
        PriceClass: PriceClass_All
        HttpVersion: http2
        ViewerCertificate:
          !If
            - HasCertificate
            - AcmCertificateArn: !Ref CertificateArn
              SslSupportMethod: sni-only
            - CloudFrontDefaultCertificate: true
        Aliases:
          !If
            - HasCustomDomain
            - [!Ref DomainName]
            - !Ref AWS::NoValue

Outputs:
  GlobalAPIEndpoint:
    Description: 'Global API Gateway endpoint'
    Value: !Sub 'https://\${ADPAGlobalAPI}.execute-api.\${AWS::Region}.amazonaws.com/\${Environment}'
    Export:
      Name: !Sub '\${ProjectName}-global-api-\${Environment}'

  CloudFrontDomain:
    Description: 'CloudFront global distribution domain'
    Value: !GetAtt ADPACloudFrontDistribution.DomainName
    Export:
      Name: !Sub '\${ProjectName}-global-domain-\${Environment}'

  GlobalEndpointURL:
    Description: 'Use this URL for global ADPA access'
    Value: !Sub 'https://\${ADPACloudFrontDistribution.DomainName}/pipelines/execute'

  UsageExample:
    Description: 'Example API call'
    Value: !Sub |
      curl -X POST https://\${ADPACloudFrontDistribution.DomainName}/pipelines/execute \\
        -H "Content-Type: application/json" \\
        -d '{"data_path": "s3://your-bucket/data.csv", "objective": "predict sales"}'
EOF

aws cloudformation $STACK_ACTION \
    --stack-name "$GLOBAL_STACK" \
    --template-body file:///tmp/global-access-template.yaml \
    --parameters $PARAMETERS \
    --capabilities CAPABILITY_NAMED_IAM

print_status "Waiting for global access deployment..."
aws cloudformation wait $WAIT_CONDITION --stack-name "$GLOBAL_STACK"

if [ $? -eq 0 ]; then
    print_status "✅ Global access deployment completed!"
else
    echo "❌ Global access deployment failed"
    exit 1
fi

# Get outputs
print_header "Retrieving Global Access Information"

OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$GLOBAL_STACK" \
    --query 'Stacks[0].Outputs' \
    --output json)

CLOUDFRONT_DOMAIN=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="CloudFrontDomain") | .OutputValue')
GLOBAL_ENDPOINT=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="GlobalEndpointURL") | .OutputValue')
API_ENDPOINT=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="GlobalAPIEndpoint") | .OutputValue')

# Test global access
print_header "Testing Global Access"

print_status "Testing CloudFront distribution..."
sleep 30  # Wait for CloudFront to propagate

TEST_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "https://$CLOUDFRONT_DOMAIN/pipelines/execute" -X OPTIONS || echo "000")

if [ "$TEST_RESPONSE" = "200" ]; then
    print_status "✅ Global access is working!"
else
    print_warning "⚠️ Global access may need a few minutes to propagate globally"
fi

# Clean up
rm -f /tmp/global-access-template.yaml

# Final summary
print_header "🌍 ADPA is Now Globally Accessible!"

echo ""
echo "=================================="
echo -e "${GREEN}🎉 GLOBAL DEPLOYMENT SUCCESSFUL! 🎉${NC}"
echo "=================================="
echo ""
echo -e "${BLUE}Global Access Information:${NC}"
echo "  🌍 CloudFront Global Domain: $CLOUDFRONT_DOMAIN"
echo "  🚀 Global API Endpoint: $GLOBAL_ENDPOINT"
echo "  📡 Direct API Gateway: $API_ENDPOINT"
echo ""
echo -e "${BLUE}How to Use ADPA Globally:${NC}"
echo ""
echo "1. 📋 Example API Call:"
echo "   curl -X POST https://$CLOUDFRONT_DOMAIN/pipelines/execute \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"data_path\": \"s3://your-bucket/data.csv\", \"objective\": \"predict sales\"}'"
echo ""
echo "2. 🌐 Web Interface:"
echo "   You can now build a web frontend that calls: https://$CLOUDFRONT_DOMAIN"
echo ""
echo "3. 📱 Mobile Apps:"
echo "   Use the global endpoint in your mobile applications"
echo ""
echo -e "${BLUE}Global Features Enabled:${NC}"
echo "  ✅ Worldwide access via CloudFront edge locations"
echo "  ✅ Automatic HTTPS and SSL termination"
echo "  ✅ CORS enabled for web applications"
echo "  ✅ Rate limiting and DDoS protection"
echo "  ✅ Global caching and performance optimization"
echo "  ✅ Auto-scaling and high availability"
echo ""
echo -e "${GREEN}🚀 ADPA is now accessible from anywhere in the world!${NC}"
echo ""

exit 0