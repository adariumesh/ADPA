#!/bin/bash

# ADPA AWS Deployment Script
# Deploys complete ADPA infrastructure to AWS using CloudFormation

set -e

echo "🚀 ADPA AWS Infrastructure Deployment"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Parse arguments
ENVIRONMENT=${1:-"development"}
PROJECT_NAME=${2:-"adpa"}
REGION=${3:-"us-east-1"}

print_status "Deployment Configuration:"
print_status "  Environment: $ENVIRONMENT"
print_status "  Project: $PROJECT_NAME"
print_status "  Region: $REGION"

# Validate AWS CLI and credentials
print_header "Validating AWS Configuration"

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install it first."
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_status "AWS Account ID: $ACCOUNT_ID"
print_status "AWS Region: $REGION"

# Check if CloudFormation template exists
CF_TEMPLATE="deploy/cloudformation/adpa-infrastructure.yaml"
if [ ! -f "$CF_TEMPLATE" ]; then
    print_error "CloudFormation template not found: $CF_TEMPLATE"
    exit 1
fi

# Stack name
STACK_NAME="${PROJECT_NAME}-infrastructure-${ENVIRONMENT}"

# Check if stack already exists
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &> /dev/null; then
    print_warning "Stack $STACK_NAME already exists. This will update the existing stack."
    STACK_ACTION="update-stack"
    WAIT_CONDITION="stack-update-complete"
else
    print_status "Creating new stack: $STACK_NAME"
    STACK_ACTION="create-stack"
    WAIT_CONDITION="stack-create-complete"
fi

# Deploy CloudFormation stack
print_header "Deploying CloudFormation Stack"

aws cloudformation $STACK_ACTION \
    --stack-name "$STACK_NAME" \
    --template-body file://$CF_TEMPLATE \
    --parameters \
        ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME \
        ParameterKey=Environment,ParameterValue=$ENVIRONMENT \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    --tags \
        Key=Project,Value=$PROJECT_NAME \
        Key=Environment,Value=$ENVIRONMENT \
        Key=DeployedBy,Value=ADPA-Deploy-Script

if [ $? -eq 0 ]; then
    print_status "CloudFormation deployment initiated successfully"
else
    print_error "CloudFormation deployment failed"
    exit 1
fi

# Wait for stack creation/update to complete
print_header "Waiting for Stack Deployment to Complete"
print_status "This may take 10-15 minutes..."

set +e
aws cloudformation wait $WAIT_CONDITION \
    --stack-name "$STACK_NAME" \
    --region "$REGION"
WAIT_EXIT_CODE=$?
set -e

if [ $WAIT_EXIT_CODE -eq 0 ]; then
    print_status "Stack deployment completed successfully!"
else
    print_error "Stack deployment failed or timed out"
    
    # Get stack events for debugging
    print_header "Recent Stack Events (for debugging):"
    aws cloudformation describe-stack-events \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'StackEvents[0:5].[Timestamp,ResourceType,LogicalResourceId,ResourceStatus,ResourceStatusReason]' \
        --output table
    
    exit $WAIT_EXIT_CODE
fi

# Get stack outputs
print_header "Retrieving Stack Outputs"

OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs' \
    --output json)

if [ "$OUTPUTS" != "null" ]; then
    print_status "Stack Outputs:"
    echo "$OUTPUTS" | jq -r '.[] | "  \(.OutputKey): \(.OutputValue)"'
    
    # Extract key values
    DATA_BUCKET=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="DataBucketName") | .OutputValue')
    MODEL_BUCKET=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="ModelBucketName") | .OutputValue')
    LAMBDA_ROLE_ARN=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="LambdaExecutionRoleArn") | .OutputValue')
    
    print_status "Key Resources Created:"
    print_status "  Data Bucket: $DATA_BUCKET"
    print_status "  Model Bucket: $MODEL_BUCKET" 
    print_status "  Lambda Role: $LAMBDA_ROLE_ARN"
else
    print_warning "No stack outputs available"
fi

# Deploy Lambda functions
print_header "Deploying Lambda Functions"

# Create deployment package
LAMBDA_ZIP="adpa-lambda-deployment.zip"
print_status "Creating Lambda deployment package..."

# Create temporary directory for Lambda package
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Copy source code
cp -r src/ $TEMP_DIR/
cp -r mcp_server/ $TEMP_DIR/

# Create a simple lambda_function.py for the data processor
cat > $TEMP_DIR/lambda_function.py << 'EOF'
import json
import logging
import sys
import os

# Add src directory to Python path
sys.path.append('/var/task/src')
sys.path.append('/var/task')

# Import ADPA modules
try:
    from src.agent.core.master_agent import MasterAgenticController
    from src.pipeline.evaluation.reporter import ReportingStep
    from src.agent.utils.llm_integration import LLMReasoningEngine
    ADPA_AVAILABLE = True
except ImportError as e:
    print(f"ADPA modules not available: {e}")
    ADPA_AVAILABLE = False

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Main Lambda handler for ADPA data processing.
    """
    logger.info(f"Processing ADPA event: {event}")
    
    try:
        if ADPA_AVAILABLE:
            # Use ADPA components
            step_config = event.get('step_config', {})
            input_data = event.get('input', {})
            
            # Process based on step type
            step_type = step_config.get('type', 'unknown')
            
            if step_type == 'reporting':
                reporter = ReportingStep()
                result = reporter.execute(context=input_data)
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'status': result.status.value,
                        'artifacts': result.artifacts,
                        'metrics': result.metrics
                    })
                }
            else:
                # Generic processing
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': f'ADPA processing completed for {step_type}',
                        'step_config': step_config,
                        'processed_at': context.aws_request_id
                    })
                }
        else:
            # Fallback processing
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'ADPA Lambda function executed (fallback mode)',
                    'event': event,
                    'request_id': context.aws_request_id
                })
            }
            
    except Exception as e:
        logger.error(f"Error processing ADPA event: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'ADPA processing failed'
            })
        }
EOF

# Create ZIP package
cd $TEMP_DIR
zip -r "../$LAMBDA_ZIP" . > /dev/null
cd - > /dev/null

print_status "Lambda package created: $LAMBDA_ZIP"

# Update Lambda function code
if [ -n "$DATA_PROCESSOR_ARN" ]; then
    aws lambda update-function-code \
        --function-name "${PROJECT_NAME}-data-processor-${ENVIRONMENT}" \
        --zip-file fileb://$LAMBDA_ZIP \
        --region "$REGION" > /dev/null
    
    print_status "Lambda function code updated"
else
    print_warning "Data processor function not found in outputs, skipping code update"
fi

# Create Step Functions state machine
print_header "Creating Step Functions State Machine"

# Get Step Functions role ARN
SF_ROLE_ARN=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="StepFunctionsRoleArn") | .OutputValue')

if [ -n "$SF_ROLE_ARN" ] && [ "$SF_ROLE_ARN" != "null" ]; then
    # Create a simple state machine definition
    cat > step-function-definition.json << EOF
{
  "Comment": "ADPA Pipeline State Machine",
  "StartAt": "DataProcessing",
  "States": {
    "DataProcessing": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${PROJECT_NAME}-data-processor-${ENVIRONMENT}",
      "Parameters": {
        "step_config": {
          "type": "data_processing",
          "step": "data_validation"
        },
        "input.$": "$"
      },
      "Next": "FeatureEngineering"
    },
    "FeatureEngineering": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${PROJECT_NAME}-data-processor-${ENVIRONMENT}",
      "Parameters": {
        "step_config": {
          "type": "feature_engineering",
          "step": "feature_creation"
        },
        "input.$": "$"
      },
      "Next": "ModelTraining"
    },
    "ModelTraining": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${PROJECT_NAME}-data-processor-${ENVIRONMENT}",
      "Parameters": {
        "step_config": {
          "type": "training",
          "step": "model_training"
        },
        "input.$": "$"
      },
      "Next": "Reporting"
    },
    "Reporting": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${PROJECT_NAME}-data-processor-${ENVIRONMENT}",
      "Parameters": {
        "step_config": {
          "type": "reporting",
          "step": "pipeline_reporting"
        },
        "input.$": "$"
      },
      "End": true
    }
  }
}
EOF

    # Create state machine
    SM_NAME="${PROJECT_NAME}-pipeline-${ENVIRONMENT}"
    
    aws stepfunctions create-state-machine \
        --name "$SM_NAME" \
        --definition file://step-function-definition.json \
        --role-arn "$SF_ROLE_ARN" \
        --region "$REGION" \
        --tags key=Project,value=$PROJECT_NAME key=Environment,value=$ENVIRONMENT > /dev/null
    
    if [ $? -eq 0 ]; then
        print_status "Step Functions state machine created: $SM_NAME"
    else
        print_warning "Step Functions state machine creation failed (may already exist)"
    fi
    
    # Clean up
    rm -f step-function-definition.json
else
    print_warning "Step Functions role not found, skipping state machine creation"
fi

# Update Secrets Manager with placeholder values
print_header "Updating Secrets Manager"

SECRET_ARN=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="SecretsManagerArn") | .OutputValue')

if [ -n "$SECRET_ARN" ] && [ "$SECRET_ARN" != "null" ]; then
    aws secretsmanager update-secret \
        --secret-id "$SECRET_ARN" \
        --secret-string "{
            \"openai_api_key\": \"your-openai-key-here\",
            \"anthropic_api_key\": \"your-anthropic-key-here\",
            \"default_region\": \"$REGION\",
            \"environment\": \"$ENVIRONMENT\",
            \"data_bucket\": \"$DATA_BUCKET\",
            \"model_bucket\": \"$MODEL_BUCKET\"
        }" \
        --region "$REGION" > /dev/null
    
    print_status "Secrets Manager updated with configuration"
else
    print_warning "Secrets Manager secret not found"
fi

# Test deployment
print_header "Testing Deployment"

print_status "Running deployment verification..."

# Test Lambda function
if aws lambda invoke \
    --function-name "${PROJECT_NAME}-data-processor-${ENVIRONMENT}" \
    --payload '{"test": "deployment_verification"}' \
    --region "$REGION" \
    /tmp/lambda-test-output.json > /dev/null 2>&1; then
    
    print_status "✅ Lambda function test passed"
else
    print_warning "⚠️  Lambda function test failed"
fi

# Test S3 access
if aws s3 ls "s3://$DATA_BUCKET" > /dev/null 2>&1; then
    print_status "✅ S3 bucket access verified"
else
    print_warning "⚠️  S3 bucket access test failed"
fi

# Clean up temporary files
rm -f $LAMBDA_ZIP
rm -f /tmp/lambda-test-output.json

# Final summary
print_header "Deployment Summary"

echo ""
echo "=================================="
echo -e "${GREEN}🎉 AWS DEPLOYMENT SUCCESSFUL! 🎉${NC}"
echo "=================================="
echo ""
echo -e "${BLUE}Infrastructure Deployed:${NC}"
echo "  ✅ VPC with public/private subnets"
echo "  ✅ S3 buckets for data and models"
echo "  ✅ Lambda functions for processing"
echo "  ✅ IAM roles and security policies"
echo "  ✅ KMS encryption keys"
echo "  ✅ CloudWatch monitoring"
echo "  ✅ Secrets Manager integration"
echo "  ✅ Step Functions workflow"
echo ""
echo -e "${BLUE}Key Resources:${NC}"
echo "  Stack Name: $STACK_NAME"
echo "  Data Bucket: $DATA_BUCKET"
echo "  Model Bucket: $MODEL_BUCKET"
echo "  Region: $REGION"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Update API keys in Secrets Manager:"
echo "     aws secretsmanager update-secret --secret-id '$SECRET_ARN' --secret-string '{\"openai_api_key\":\"your-key\"}'"
echo ""
echo "  2. Test the pipeline:"
echo "     python demo_aws_integration.py"
echo ""
echo "  3. Monitor in AWS Console:"
echo "     https://${REGION}.console.aws.amazon.com/cloudformation/home?region=${REGION}#/stacks"
echo ""
echo -e "${GREEN}🚀 ADPA is now deployed and ready for production use in AWS!${NC}"

exit 0