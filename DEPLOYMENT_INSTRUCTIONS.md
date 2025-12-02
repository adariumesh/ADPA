# ADPA Lambda Deployment Instructions

## Overview
This document provides step-by-step instructions to deploy the ADPA agent to AWS Lambda function `adpa-data-processor-development` in the `us-east-2` region.

## Prerequisites
- AWS CLI installed and configured with appropriate credentials
- Target Lambda function `adpa-data-processor-development` already exists
- Python 3.9+ environment
- Access to us-east-2 region

## Shell Environment Issue
**IMPORTANT**: The shell environment has persistent issues preventing direct bash execution. All commands must be run manually or through alternative execution methods.

## Manual Deployment Steps

### Step 1: Create Deployment Package

Create a directory called `lambda_package` and copy the following files:

```bash
mkdir lambda_package

# Copy source code
cp -r src/ lambda_package/src/

# Copy lambda handler
cp lambda_function.py lambda_package/

# Copy configuration  
cp -r config/ lambda_package/config/

# Create requirements.txt for Lambda
cat > lambda_package/requirements.txt << 'EOF'
boto3>=1.34.0
pydantic>=2.0.0
requests>=2.31.0
python-json-logger>=2.0.7
pyyaml>=6.0.0
python-dotenv>=1.0.0
EOF
```

### Step 2: Install Dependencies (Optional)

For full deployment with dependencies:

```bash
cd lambda_package
pip install -r requirements.txt -t .
cd ..
```

**Note**: Many packages like boto3, pandas, numpy are pre-installed in AWS Lambda Python runtime.

### Step 3: Create ZIP Package

```bash
cd lambda_package
zip -r ../adpa-lambda-deployment.zip . -x "__pycache__/*" "*.pyc" "tests/*"
cd ..
```

### Step 4: Deploy to AWS Lambda

```bash
# Update function code
aws lambda update-function-code \
    --function-name adpa-data-processor-development \
    --zip-file fileb://adpa-lambda-deployment.zip \
    --region us-east-2

# Update function configuration
aws lambda update-function-configuration \
    --function-name adpa-data-processor-development \
    --timeout 900 \
    --memory-size 512 \
    --region us-east-2 \
    --environment Variables='{
        "DATA_BUCKET":"adpa-data-276983626136-development",
        "MODEL_BUCKET":"adpa-models-276983626136-development",
        "AWS_REGION":"us-east-2", 
        "ENVIRONMENT":"development"
    }'
```

### Step 5: Test Deployment

```bash
# Health check
aws lambda invoke \
    --function-name adpa-data-processor-development \
    --payload '{"action": "health_check"}' \
    --region us-east-2 \
    health_check_response.json

# View response
cat health_check_response.json | python -m json.tool

# Test pipeline execution
aws lambda invoke \
    --function-name adpa-data-processor-development \
    --payload '{"action": "run_pipeline", "dataset_path": "s3://adpa-data-276983626136-development/sample.csv", "objective": "classification"}' \
    --region us-east-2 \
    pipeline_response.json

# View pipeline response  
cat pipeline_response.json | python -m json.tool
```

## Package Contents

The deployment package should contain:

### Core Files
- `lambda_function.py` - Main Lambda handler
- `src/` - Complete ADPA source code
- `config/` - Configuration files
- `requirements.txt` - Python dependencies

### Source Structure
```
lambda_package/
├── lambda_function.py
├── requirements.txt
├── config/
│   └── default_config.yaml
└── src/
    ├── __init__.py
    ├── agent/
    │   ├── core/
    │   │   └── master_agent.py
    │   ├── memory/
    │   ├── learning/
    │   └── ...
    ├── monitoring/
    │   ├── cloudwatch_monitor.py
    │   ├── kpi_tracker.py
    │   └── ...
    ├── pipeline/
    │   ├── ingestion/
    │   ├── etl/
    │   ├── evaluation/
    │   └── ...
    └── aws/
        ├── lambda/
        ├── s3/
        └── ...
```

## Environment Variables

The Lambda function should have these environment variables:

```json
{
  "DATA_BUCKET": "adpa-data-276983626136-development",
  "MODEL_BUCKET": "adpa-models-276983626136-development", 
  "AWS_REGION": "us-east-2",
  "ENVIRONMENT": "development"
}
```

## Function Configuration

- **Runtime**: Python 3.9
- **Handler**: lambda_function.lambda_handler
- **Timeout**: 900 seconds (15 minutes)
- **Memory**: 512 MB
- **Region**: us-east-2

## Testing

### Health Check Test
```json
{
  "action": "health_check"
}
```

Expected response:
```json
{
  "status": "healthy",
  "components": {
    "imports": true,
    "monitoring": true,
    "kpi_tracker": true,
    "agent": true
  },
  "aws_config": {
    "data_bucket": "adpa-data-276983626136-development",
    "model_bucket": "adpa-models-276983626136-development",
    "region": "us-east-2"
  },
  "timestamp": "2025-12-01T00:00:00.000Z"
}
```

### Pipeline Execution Test
```json
{
  "action": "run_pipeline",
  "dataset_path": "s3://adpa-data-276983626136-development/test.csv",
  "objective": "classification",
  "config": {}
}
```

## Monitoring

After deployment, monitor:

1. **CloudWatch Logs**: `/aws/lambda/adpa-data-processor-development`
2. **CloudWatch Metrics**: Lambda function metrics
3. **Custom Metrics**: ADPA performance metrics
4. **Dashboard**: https://us-east-2.console.aws.amazon.com/cloudwatch/home?region=us-east-2#dashboards:name=ADPA-Dashboard

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are included in the package
2. **Permission Errors**: Verify Lambda execution role has required permissions
3. **Timeout Errors**: Increase timeout for complex pipelines
4. **Memory Errors**: Increase memory allocation for large datasets

### Debug Commands

```bash
# View function details
aws lambda get-function --function-name adpa-data-processor-development --region us-east-2

# View recent logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/adpa-data-processor" --region us-east-2

# Get latest log stream
aws logs describe-log-streams --log-group-name "/aws/lambda/adpa-data-processor-development" --region us-east-2 --order-by LastEventTime --descending --max-items 1
```

## Deployment Status

- **Package Ready**: ✅ All source files available
- **Shell Issues**: ⚠️  Shell environment has persistent issues
- **Manual Deploy Required**: 🔧 Execute steps manually using AWS CLI
- **Function Target**: `adpa-data-processor-development`
- **Region**: `us-east-2`

## Next Steps

1. Execute manual deployment steps above
2. Run health check test
3. Execute pipeline test with sample data
4. Monitor CloudWatch logs for any issues
5. Set up continuous deployment pipeline if needed

## Support

For deployment issues:
1. Check CloudWatch logs
2. Verify AWS credentials and permissions
3. Ensure target Lambda function exists
4. Validate package contents and structure