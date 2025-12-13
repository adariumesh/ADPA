#!/bin/bash

# Deploy Adariprasad's ADPA Agent to Girik's Lambda Infrastructure
# This script packages and deploys the complete ADPA system

set -e

echo "🚀 Deploying ADPA Agent to AWS Lambda"
echo "====================================="

# Configuration
FUNCTION_NAME="adpa-data-processor-development"
REGION="us-east-2"
DEPLOYMENT_PACKAGE="adpa-lambda-deployment.zip"

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

# Step 1: Clean previous builds
print_status "Cleaning previous deployment packages..."
rm -f $DEPLOYMENT_PACKAGE
rm -rf lambda_package/

# Step 2: Create deployment package
print_status "Creating Lambda deployment package..."
mkdir -p lambda_package

# Copy Adariprasad's core ADPA components
print_status "Packaging ADPA source code..."
cp -r src/ lambda_package/
cp lambda_function.py lambda_package/

# Copy configuration files
if [ -f "config/default_config.yaml" ]; then
    cp -r config/ lambda_package/
fi

# Step 3: Install Python dependencies
print_status "Installing Python dependencies..."
cd lambda_package

# Create requirements file for Lambda
cat > requirements.txt << 'EOF'
boto3>=1.34.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
pydantic>=2.0.0
requests>=2.31.0
python-json-logger>=2.0.7
pyyaml>=6.0.0
python-dotenv>=1.0.0
EOF

# Install dependencies to package
pip install -r requirements.txt -t .

# Remove unnecessary files to reduce package size
print_status "Optimizing package size..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

cd ..

# Step 4: Create ZIP package
print_status "Creating deployment ZIP..."
cd lambda_package
zip -r ../$DEPLOYMENT_PACKAGE . -q
cd ..

package_size=$(du -h $DEPLOYMENT_PACKAGE | cut -f1)
print_status "Package created: $DEPLOYMENT_PACKAGE ($package_size)"

# Step 5: Deploy to AWS Lambda
print_status "Deploying to AWS Lambda function: $FUNCTION_NAME"

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1; then
    print_status "Updating existing Lambda function..."
    
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://$DEPLOYMENT_PACKAGE \
        --region $REGION
        
    print_status "Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout 900 \
        --memory-size 512 \
        --region $REGION
        
else
    print_error "Lambda function $FUNCTION_NAME not found!"
    print_error "Please deploy the infrastructure first using ./deploy/aws-deploy.sh"
    exit 1
fi

# Step 6: Test the deployment
print_status "Testing deployed Lambda function..."

# Test health check
print_status "Running health check..."
aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload '{"action": "health_check"}' \
    --region $REGION \
    lambda_test_response.json

if [ $? -eq 0 ]; then
    print_status "✅ Lambda invocation successful"
    echo "Response:"
    cat lambda_test_response.json | python -m json.tool
    echo
else
    print_error "❌ Lambda invocation failed"
    exit 1
fi

# Step 7: Cleanup
print_status "Cleaning up temporary files..."
rm -rf lambda_package/
rm -f lambda_test_response.json

# Step 8: Provide usage instructions
echo
echo "======================================"
echo "🎉 ADPA AGENT DEPLOYMENT SUCCESSFUL! 🎉"
echo "======================================"
echo
print_status "ADPA Agent is now running on AWS Lambda!"
print_status "Function: $FUNCTION_NAME"
print_status "Region: $REGION"
print_status "Package: $DEPLOYMENT_PACKAGE"
echo
print_status "Test the deployment:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME --payload '{\"action\": \"health_check\"}' response.json"
echo
print_status "Run a pipeline:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME --payload '{\"action\": \"run_pipeline\", \"dataset_path\": \"s3://your-bucket/data.csv\", \"objective\": \"classification\"}' response.json"
echo
print_status "Next steps:"
echo "  1. Test the Lambda function with real data"
echo "  2. Configure API Gateway endpoints"
echo "  3. Set up monitoring dashboards"
echo "  4. Deploy global access infrastructure"
echo

print_status "🚀 Adariprasad's sophisticated ADPA agent is now running on Girik's AWS infrastructure!"