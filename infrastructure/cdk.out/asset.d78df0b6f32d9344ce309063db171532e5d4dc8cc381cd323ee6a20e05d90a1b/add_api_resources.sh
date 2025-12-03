#!/bin/bash

# Add all API Gateway resources for ADPA
set -e

API_ID="cr1kkj7213"
REGION="us-east-2"
LAMBDA_ARN="arn:aws:lambda:us-east-2:083308938449:function:adpa-lambda-function"

echo "Adding API Gateway resources..."

# Get root resource ID
ROOT_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?path==`/`].id' --output text)

echo "Root ID: $ROOT_ID"

# Create /pipelines resource
PIPELINES_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part pipelines \
  --region $REGION \
  --query 'id' --output text 2>/dev/null || \
  aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?pathPart==`pipelines`].id' --output text)

echo "Created /pipelines: $PIPELINES_ID"

# Add GET method to /pipelines
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $PIPELINES_ID \
  --http-method GET \
  --authorization-type NONE \
  --region $REGION 2>/dev/null || echo "GET method exists"

# Add POST method to /pipelines
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $PIPELINES_ID \
  --http-method POST \
  --authorization-type NONE \
  --region $REGION 2>/dev/null || echo "POST method exists"

# Add OPTIONS for CORS
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $PIPELINES_ID \
  --http-method OPTIONS \
  --authorization-type NONE \
  --region $REGION 2>/dev/null || echo "OPTIONS method exists"

# Add Lambda integrations for GET
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $PIPELINES_ID \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" \
  --region $REGION 2>/dev/null || echo "GET integration exists"

# Add Lambda integrations for POST
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $PIPELINES_ID \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" \
  --region $REGION 2>/dev/null || echo "POST integration exists"

# Create /pipelines/{id} resource
PIPELINE_ID_RESOURCE=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $PIPELINES_ID \
  --path-part '{id}' \
  --region $REGION \
  --query 'id' --output text 2>/dev/null || \
  aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?pathPart==`{id}`].id' --output text | head -1)

echo "Created /pipelines/{id}: $PIPELINE_ID_RESOURCE"

# Add GET to /pipelines/{id}
aws apigateway put-method --rest-api-id $API_ID --resource-id $PIPELINE_ID_RESOURCE --http-method GET --authorization-type NONE --region $REGION 2>/dev/null || echo "GET exists"
aws apigateway put-integration --rest-api-id $API_ID --resource-id $PIPELINE_ID_RESOURCE --http-method GET --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" --region $REGION 2>/dev/null || echo "Integration exists"

# Create /pipelines/{id}/execute
EXECUTE_RESOURCE=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $PIPELINE_ID_RESOURCE \
  --path-part execute \
  --region $REGION \
  --query 'id' --output text 2>/dev/null || \
  aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?pathPart==`execute`].id' --output text | head -1)

echo "Created /pipelines/{id}/execute: $EXECUTE_RESOURCE"

aws apigateway put-method --rest-api-id $API_ID --resource-id $EXECUTE_RESOURCE --http-method POST --authorization-type NONE --region $REGION 2>/dev/null || echo "POST exists"
aws apigateway put-integration --rest-api-id $API_ID --resource-id $EXECUTE_RESOURCE --http-method POST --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" --region $REGION 2>/dev/null || echo "Integration exists"

# Create /pipelines/{id}/status
STATUS_RESOURCE=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $PIPELINE_ID_RESOURCE \
  --path-part status \
  --region $REGION \
  --query 'id' --output text 2>/dev/null || \
  aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?pathPart==`status`].id' --output text | head -1)

echo "Created /pipelines/{id}/status: $STATUS_RESOURCE"

aws apigateway put-method --rest-api-id $API_ID --resource-id $STATUS_RESOURCE --http-method GET --authorization-type NONE --region $REGION 2>/dev/null || echo "GET exists"
aws apigateway put-integration --rest-api-id $API_ID --resource-id $STATUS_RESOURCE --http-method GET --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" --region $REGION 2>/dev/null || echo "Integration exists"

# Create /data resource
DATA_RESOURCE=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part data \
  --region $REGION \
  --query 'id' --output text 2>/dev/null || \
  aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?pathPart==`data`].id' --output text)

echo "Created /data: $DATA_RESOURCE"

# Create /data/upload
UPLOAD_RESOURCE=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $DATA_RESOURCE \
  --path-part upload \
  --region $REGION \
  --query 'id' --output text 2>/dev/null || \
  aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?pathPart==`upload`].id' --output text | head -1)

echo "Created /data/upload: $UPLOAD_RESOURCE"

aws apigateway put-method --rest-api-id $API_ID --resource-id $UPLOAD_RESOURCE --http-method POST --authorization-type NONE --region $REGION 2>/dev/null || echo "POST exists"
aws apigateway put-integration --rest-api-id $API_ID --resource-id $UPLOAD_RESOURCE --http-method POST --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" --region $REGION 2>/dev/null || echo "Integration exists"

# Create /data/uploads
UPLOADS_RESOURCE=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $DATA_RESOURCE \
  --path-part uploads \
  --region $REGION \
  --query 'id' --output text 2>/dev/null || \
  aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?pathPart==`uploads`].id' --output text | head -1)

echo "Created /data/uploads: $UPLOADS_RESOURCE"

aws apigateway put-method --rest-api-id $API_ID --resource-id $UPLOADS_RESOURCE --http-method GET --authorization-type NONE --region $REGION 2>/dev/null || echo "GET exists"
aws apigateway put-integration --rest-api-id $API_ID --resource-id $UPLOADS_RESOURCE --http-method GET --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" --region $REGION 2>/dev/null || echo "Integration exists"

# Deploy API
echo "Deploying API..."
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region $REGION

echo "✅ API Gateway updated successfully!"
echo "API URL: https://$API_ID.execute-api.$REGION.amazonaws.com/prod"
