#!/bin/bash

# ADPA Container Deployment Script
# Deploys ADPA as containerized application on AWS ECS with Application Load Balancer

set -e

echo "🐳 ADPA Container Deployment to AWS"
echo "==================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ENVIRONMENT="${1:-development}"
PROJECT_NAME="${2:-adpa}"
REGION="${3:-us-east-1}"
REPOSITORY_NAME="${PROJECT_NAME}-ecr"
IMAGE_TAG="${4:-latest}"

echo -e "${BLUE}Configuration:${NC}"
echo "  Environment: $ENVIRONMENT"
echo "  Project: $PROJECT_NAME"
echo "  Region: $REGION"
echo "  Image Tag: $IMAGE_TAG"
echo ""

# Validation
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found${NC}"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    exit 1
fi

# Check if infrastructure stack exists
echo -e "${BLUE}📋 Phase 1: Infrastructure Check${NC}"
echo "──────────────────────────────────────"

INFRA_STACK_NAME="${PROJECT_NAME}-infrastructure-${ENVIRONMENT}"
if aws cloudformation describe-stacks --stack-name "$INFRA_STACK_NAME" --region "$REGION" &> /dev/null; then
    STACK_STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$INFRA_STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].StackStatus' \
        --output text)
    
    if [ "$STACK_STATUS" = "CREATE_COMPLETE" ] || [ "$STACK_STATUS" = "UPDATE_COMPLETE" ]; then
        echo -e "${GREEN}✅ Infrastructure stack exists and ready${NC}"
    else
        echo -e "${RED}❌ Infrastructure stack in invalid state: $STACK_STATUS${NC}"
        echo "Please fix infrastructure before deploying containers"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Infrastructure stack not found${NC}"
    echo "Creating infrastructure stack first..."
    
    ./aws-deploy.sh "$ENVIRONMENT" "$PROJECT_NAME" "$REGION"
    
    echo -e "${GREEN}✅ Infrastructure stack created${NC}"
fi

# Create ECR repository if it doesn't exist
echo ""
echo -e "${BLUE}📋 Phase 2: Container Registry${NC}"
echo "─────────────────────────────────"

if aws ecr describe-repositories --repository-names "$REPOSITORY_NAME" --region "$REGION" &> /dev/null; then
    echo -e "${GREEN}✅ ECR repository exists: $REPOSITORY_NAME${NC}"
else
    echo -e "${YELLOW}Creating ECR repository: $REPOSITORY_NAME${NC}"
    
    aws ecr create-repository \
        --repository-name "$REPOSITORY_NAME" \
        --region "$REGION" \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 \
        --tags Key=Project,Value="$PROJECT_NAME" Key=Environment,Value="$ENVIRONMENT"
    
    echo -e "${GREEN}✅ ECR repository created${NC}"
fi

# Get ECR login and repository URI
ECR_URI=$(aws ecr describe-repositories \
    --repository-names "$REPOSITORY_NAME" \
    --region "$REGION" \
    --query 'repositories[0].repositoryUri' \
    --output text)

echo "ECR Repository URI: $ECR_URI"

# Build and push Docker image
echo ""
echo -e "${BLUE}📋 Phase 3: Build and Push Container${NC}"
echo "────────────────────────────────────────"

echo -e "${YELLOW}Building Docker image...${NC}"

# Ensure we're in the project root
if [ ! -f "Dockerfile" ] || [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Not in project root directory${NC}"
    exit 1
fi

# Build the image
docker build -t "${PROJECT_NAME}:${IMAGE_TAG}" .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
else
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

# Tag for ECR
docker tag "${PROJECT_NAME}:${IMAGE_TAG}" "${ECR_URI}:${IMAGE_TAG}"

# Login to ECR
echo -e "${YELLOW}Logging into ECR...${NC}"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_URI"

# Push to ECR
echo -e "${YELLOW}Pushing to ECR...${NC}"
docker push "${ECR_URI}:${IMAGE_TAG}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Image pushed to ECR successfully${NC}"
else
    echo -e "${RED}❌ Failed to push image to ECR${NC}"
    exit 1
fi

# Deploy container stack
echo ""
echo -e "${BLUE}📋 Phase 4: Deploy Container Infrastructure${NC}"
echo "─────────────────────────────────────────────"

CONTAINER_STACK_NAME="${PROJECT_NAME}-containers-${ENVIRONMENT}"

echo -e "${YELLOW}Deploying ECS infrastructure...${NC}"

aws cloudformation deploy \
    --template-file "deploy/cloudformation/adpa-container-stack.yaml" \
    --stack-name "$CONTAINER_STACK_NAME" \
    --region "$REGION" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        ProjectName="$PROJECT_NAME" \
        Environment="$ENVIRONMENT" \
        ContainerImage="${ECR_URI}:${IMAGE_TAG}" \
        DesiredCapacity=2 \
    --tags \
        Project="$PROJECT_NAME" \
        Environment="$ENVIRONMENT" \
        DeployedBy="container-deploy-script"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Container infrastructure deployed successfully${NC}"
else
    echo -e "${RED}❌ Container infrastructure deployment failed${NC}"
    exit 1
fi

# Wait for service to become stable
echo ""
echo -e "${BLUE}📋 Phase 5: Service Health Check${NC}"
echo "───────────────────────────────────"

CLUSTER_NAME="${PROJECT_NAME}-cluster-${ENVIRONMENT}"
SERVICE_NAME="${PROJECT_NAME}-service-${ENVIRONMENT}"

echo -e "${YELLOW}Waiting for service to become stable...${NC}"

aws ecs wait services-stable \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --region "$REGION"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Service is stable and running${NC}"
else
    echo -e "${YELLOW}⚠️  Service may still be starting up${NC}"
fi

# Get the load balancer URL
echo ""
echo -e "${BLUE}📋 Phase 6: Access Information${NC}"
echo "─────────────────────────────────"

ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name "$CONTAINER_STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
    --output text)

WEB_URL="http://${ALB_DNS}"

echo -e "${GREEN}🎉 ADPA Container Deployment Complete!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}🌐 Access Information${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}🔗 ADPA Web Interface:${NC} $WEB_URL"
echo -e "${GREEN}🔗 API Base URL:${NC} $WEB_URL/api"
echo -e "${GREEN}🔗 Health Check:${NC} $WEB_URL/health"
echo ""
echo "Container Details:"
echo "  • ECS Cluster: $CLUSTER_NAME"
echo "  • Service: $SERVICE_NAME"
echo "  • Load Balancer: $ALB_DNS"
echo "  • Container Image: ${ECR_URI}:${IMAGE_TAG}"
echo ""
echo -e "${BLUE}📊 Management Commands:${NC}"
echo "  • View logs: aws logs tail /aws/ecs/${PROJECT_NAME}-${ENVIRONMENT} --region $REGION"
echo "  • Service status: aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION"
echo "  • Scale service: aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 3 --region $REGION"
echo ""

# Test the deployment
echo -e "${BLUE}📋 Phase 7: Deployment Test${NC}"
echo "──────────────────────────────"

echo -e "${YELLOW}Testing health endpoint...${NC}"
sleep 10  # Give load balancer time to register targets

for i in {1..5}; do
    if curl -f -s "$WEB_URL/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Health check passed${NC}"
        break
    else
        if [ $i -eq 5 ]; then
            echo -e "${YELLOW}⚠️  Health check failed, but deployment may still be starting${NC}"
            echo "   Check the ECS service status and logs"
        else
            echo -e "${YELLOW}⏳ Waiting for service to start (attempt $i/5)...${NC}"
            sleep 30
        fi
    fi
done

echo ""
echo -e "${GREEN}🚀 ADPA is now running in the cloud!${NC}"
echo ""
echo "Next steps:"
echo "1. Visit $WEB_URL to access the ADPA web interface"
echo "2. Use the API at $WEB_URL/api for programmatic access"
echo "3. Monitor the service in the AWS ECS console"
echo "4. Set up custom domain and HTTPS certificate if needed"

# Optional: Open browser (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    read -p "Open ADPA web interface in browser? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open "$WEB_URL"
    fi
fi