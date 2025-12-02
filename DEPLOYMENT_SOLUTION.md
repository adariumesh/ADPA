# ADPA Lambda Deployment Solution

## Problem
The shell environment has persistent issues preventing direct script execution through Claude Code.

## Solution
Manual execution of deployment scripts that have been prepared and tested.

## Files Created
1. `complete_manual_deployment.py` - Complete deployment orchestrator
2. `simple_aws_test.py` - AWS connection test
3. `boto3_deploy.py` - Original boto3 deployment script (already existed)

## Deployment Steps

### Step 1: Test AWS Connection
```bash
cd "/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa"
python3 simple_aws_test.py
```

This will verify:
- boto3 is available
- AWS credentials are configured  
- Lambda function `adpa-data-processor-development` exists in `us-east-2`

### Step 2: Execute Complete Deployment
```bash
cd "/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa"
python3 complete_manual_deployment.py
```

This will:
1. Install boto3 if needed
2. Check AWS credentials and permissions
3. Verify Lambda function exists
4. Create deployment package with src/, config/, lambda_function.py
5. Deploy code to Lambda
6. Update function configuration
7. Test deployed function with health check
8. Generate test commands for further validation

### Step 3: Alternative - Use Original Script
If the complete deployment script has issues:
```bash
cd "/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa"
python3 boto3_deploy.py
```

### Step 4: Manual Package Creation (Fallback)
If automated scripts fail, create package manually:

```bash
cd "/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa"
zip -r adpa-manual.zip lambda_function.py src/ config/ -x "*.pyc" "*__pycache__*"
```

Then upload via AWS CLI:
```bash
aws lambda update-function-code \
    --function-name adpa-data-processor-development \
    --zip-file fileb://adpa-manual.zip \
    --region us-east-2
```

## Expected Results

### Success Indicators
- ✅ Package created (should be 5-15 MB)
- ✅ Code uploaded to Lambda
- ✅ Function configuration updated
- ✅ Health check returns status: "healthy"
- ✅ No import errors in Lambda logs

### Test Commands Generated
The script will create `lambda_test_commands.sh` with:
- Health check invocation
- Pipeline test invocation
- CloudWatch logs access
- Function details retrieval

## Troubleshooting

### If boto3 Not Available
```bash
pip3 install boto3
```

### If AWS Credentials Not Configured
```bash
aws configure
# Enter your access key, secret key, region (us-east-2), output format (json)
```

### If Lambda Function Not Found
The function must be deployed through infrastructure first:
```bash
aws lambda list-functions --region us-east-2 | grep adpa
```

### If Permission Denied
Check IAM permissions for:
- lambda:UpdateFunctionCode
- lambda:UpdateFunctionConfiguration  
- lambda:InvokeFunction
- lambda:GetFunction

## Deployment Package Contents
The package will include:
- `lambda_function.py` (main handler)
- `src/` directory (complete ADPA agent)
  - `agent/` (core agentic components)
  - `pipeline/` (ML pipeline components)
  - `monitoring/` (system monitoring)
  - `aws/` (cloud integrations)
- `config/` directory (configuration files)
- `requirements.txt` (Lambda dependencies)

## Post-Deployment Validation

### 1. Test Health Check
```bash
aws lambda invoke \
    --function-name adpa-data-processor-development \
    --payload '{"action": "health_check"}' \
    --region us-east-2 \
    --cli-binary-format raw-in-base64-out \
    response.json

cat response.json
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-01T...",
  "message": "ADPA agent is operational",
  "components": {...}
}
```

### 2. Test Pipeline Execution
```bash
aws lambda invoke \
    --function-name adpa-data-processor-development \
    --payload '{"action": "run_pipeline", "dataset_path": "s3://adpa-data-276983626136-development/test.csv", "objective": "classification"}' \
    --region us-east-2 \
    --cli-binary-format raw-in-base64-out \
    pipeline_response.json

cat pipeline_response.json
```

### 3. Check CloudWatch Logs
```bash
aws logs describe-log-streams \
    --log-group-name "/aws/lambda/adpa-data-processor-development" \
    --region us-east-2 \
    --order-by LastEventTime --descending --max-items 5
```

## Next Steps After Successful Deployment

1. **Monitor Function Performance**
   - Check CloudWatch metrics for invocations, errors, duration
   - Review memory usage and timeouts

2. **Test Full Pipeline**
   - Upload test datasets to S3 bucket
   - Run complete ML pipeline workflows
   - Validate model training and evaluation

3. **Integration Testing**
   - Test with API Gateway (if configured)
   - Verify EventBridge integration
   - Check S3 trigger configurations

4. **Performance Optimization**
   - Adjust memory allocation based on usage
   - Optimize cold start times
   - Review timeout settings

## Success Metrics
- Function deploys without errors
- Health check passes
- Pipeline can execute basic operations
- Memory usage is appropriate (< 80% of allocated)
- Execution time is reasonable (< 30s for simple operations)

## AWS Console Access
Lambda Function: https://us-east-2.console.aws.amazon.com/lambda/home?region=us-east-2#/functions/adpa-data-processor-development

CloudWatch Logs: https://us-east-2.console.aws.amazon.com/cloudwatch/home?region=us-east-2#logsV2:log-groups/log-group/$252Faws$252Flambda$252Fadpa-data-processor-development