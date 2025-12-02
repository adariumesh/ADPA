#!/bin/bash

# Create AWS Lambda Layer with pandas, scikit-learn, and other ML dependencies
# This resolves the "No module named 'pandas'" error

set -e

echo "════════════════════════════════════════════════════════════════"
echo "Creating Lambda Layer with ML Dependencies"
echo "════════════════════════════════════════════════════════════════"

# Configuration
LAYER_NAME="adpa-ml-dependencies"
REGION="us-east-2"
PYTHON_VERSION="python3.9"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
LAYER_DIR="$TEMP_DIR/python"

echo "📁 Creating layer directory: $LAYER_DIR"
mkdir -p "$LAYER_DIR"

# Install dependencies
echo "📦 Installing dependencies..."
pip install \
    pandas \
    scikit-learn \
    numpy \
    scipy \
    joblib \
    -t "$LAYER_DIR" \
    --platform manylinux2014_x86_64 \
    --python-version 3.9 \
    --only-binary=:all:

# Create ZIP file
echo "🗜️  Creating layer package..."
cd "$TEMP_DIR"
zip -r9 layer.zip python/

# Upload to Lambda
echo "☁️  Uploading layer to AWS Lambda..."
aws lambda publish-layer-version \
    --layer-name "$LAYER_NAME" \
    --description "ML dependencies: pandas, scikit-learn, numpy, scipy" \
    --zip-file "fileb://layer.zip" \
    --compatible-runtimes "$PYTHON_VERSION" \
    --region "$REGION"

# Get layer ARN
LAYER_ARN=$(aws lambda list-layer-versions \
    --layer-name "$LAYER_NAME" \
    --region "$REGION" \
    --query 'LayerVersions[0].LayerVersionArn' \
    --output text)

echo "✅ Layer created successfully!"
echo "Layer ARN: $LAYER_ARN"

# Update all Lambda functions to use the layer
echo ""
echo "🔗 Updating Lambda functions to use the layer..."

LAMBDA_FUNCTIONS=(
    "adpa-data-ingestion"
    "adpa-data-cleaning"
    "adpa-feature-engineering"
    "adpa-model-training"
    "adpa-model-evaluation"
)

for FUNCTION_NAME in "${LAMBDA_FUNCTIONS[@]}"; do
    echo "  Updating $FUNCTION_NAME..."
    
    # Check if function exists
    if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
        aws lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --layers "$LAYER_ARN" \
            --region "$REGION" &>/dev/null
        
        echo "    ✅ $FUNCTION_NAME updated"
    else
        echo "    ⚠️  $FUNCTION_NAME not found, skipping"
    fi
done

# Update API Gateway health check Lambda
echo "  Updating adpa-api-health-check..."
if aws lambda get-function --function-name "adpa-api-health-check" --region "$REGION" &>/dev/null; then
    aws lambda update-function-configuration \
        --function-name "adpa-api-health-check" \
        --layers "$LAYER_ARN" \
        --region "$REGION" &>/dev/null
    echo "    ✅ adpa-api-health-check updated"
fi

# Cleanup
echo ""
echo "🧹 Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Lambda Layer Created and Applied Successfully!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Layer Details:"
echo "  Name: $LAYER_NAME"
echo "  ARN: $LAYER_ARN"
echo "  Region: $REGION"
echo "  Python: $PYTHON_VERSION"
echo ""
echo "Dependencies included:"
echo "  - pandas (latest compatible)"
echo "  - scikit-learn (latest compatible)"
echo "  - numpy (latest compatible)"
echo "  - scipy (latest compatible)"
echo "  - joblib (latest compatible)"
echo ""
echo "Next steps:"
echo "  1. Test Lambda functions: aws lambda invoke --function-name adpa-data-ingestion /tmp/response.json"
echo "  2. Verify health endpoint: curl https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/health"
echo ""
