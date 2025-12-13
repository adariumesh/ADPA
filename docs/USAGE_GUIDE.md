# ADPA AWS Deployment - Usage Guide

## 🔐 Current Deployment Details

**AWS Account:** `083308938449`  
**Credentials Used:** `umeshka` (IAM User: AIDARGZMZQTIUYBS6TANP)  
**Region:** `us-east-2` (Ohio)

## 📍 Where is ADPA in AWS?

### 1. Lambda Function
- **Console URL:** https://us-east-2.console.aws.amazon.com/lambda/home?region=us-east-2#/functions/adpa-data-processor-development
- **Function Name:** `adpa-data-processor-development`
- **Type:** Container Image (Docker)
- **Memory:** 3008 MB (3 GB)
- **Timeout:** 900 seconds (15 minutes)
- **ARN:** `arn:aws:lambda:us-east-2:083308938449:function:adpa-data-processor-development`

### 2. Container Image (ECR)
- **Console URL:** https://us-east-2.console.aws.amazon.com/ecr/repositories/private/083308938449/adpa?region=us-east-2
- **Repository:** `adpa`
- **Image URI:** `083308938449.dkr.ecr.us-east-2.amazonaws.com/adpa:latest`
- **Size:** ~1.04 GB (includes all ML libraries)

### 3. S3 Buckets
- **Data Bucket:** `adpa-data-083308938449-development`
  - URL: https://s3.console.aws.amazon.com/s3/buckets/adpa-data-083308938449-development?region=us-east-2
- **Model Bucket:** `adpa-models-083308938449-development`
  - URL: https://s3.console.aws.amazon.com/s3/buckets/adpa-models-083308938449-development?region=us-east-2

### 4. IAM Role
- **Role Name:** `adpa-lambda-execution-role-development`
- **Console URL:** https://console.aws.amazon.com/iam/home#/roles/adpa-lambda-execution-role-development
- **Permissions:** S3 access, CloudWatch Logs, Lambda execution

#### ✅ Required Step Functions permissions for real metrics
To let `use_real_aws=true` create dynamic Step Functions workflows and stream real SageMaker metrics back into DynamoDB, the Lambda execution role now needs full pipeline management permissions. Apply the bundled policy once per environment:

```bash
aws iam put-role-policy \
  --region us-east-2 \
  --role-name adpa-lambda-execution-role-development \
  --policy-name adpa-stepfunctions-full-access \
  --policy-document file://infrastructure/policies/lambda-stepfunctions-access.json
```

After attaching the policy, run `aws stepfunctions list-state-machines --region us-east-2` from the same credentials to confirm the Lambda role can see the `adpa-*` workflows. The Lambda logs will now show `simulation_mode=False`, and end-to-end executions will publish live metrics instead of zeros.

### 5. CloudWatch Logs
- **Log Group:** `/aws/lambda/adpa-data-processor-development`
- **Console URL:** https://us-east-2.console.aws.amazon.com/cloudwatch/home?region=us-east-2#logsV2:log-groups/log-group/$252Faws$252Flambda$252Fadpa-data-processor-development

---

## 🚀 How to Use ADPA

### Method 1: AWS CLI (Recommended)

#### Health Check
```bash
aws lambda invoke \
  --function-name adpa-data-processor-development \
  --payload '{"action": "health_check"}' \
  --region us-east-2 \
  response.json && cat response.json
```

**Expected Response:**
```json
{
  "status": "healthy",
  "components": {
    "imports": true,
    "monitoring": true,
    "kpi_tracker": true,
    "agent": true
  },
  "timestamp": "2025-12-02T19:15:21.592900"
}
```

#### Run ML Pipeline
```bash
aws lambda invoke \
  --function-name adpa-data-processor-development \
  --payload '{
    "action": "run_pipeline",
    "objective": "Build a classification model to predict customer churn",
    "dataset_path": "s3://adpa-data-083308938449-development/datasets/customer_data.csv"
  }' \
  --region us-east-2 \
  pipeline_result.json && cat pipeline_result.json
```

#### Get Pipeline Status
```bash
aws lambda invoke \
  --function-name adpa-data-processor-development \
  --payload '{
    "action": "get_status",
    "pipeline_id": "your-pipeline-id"
  }' \
  --region us-east-2 \
  status.json && cat status.json
```

### Method 2: AWS Console

1. **Go to Lambda Console:**
   - Navigate to: https://us-east-2.console.aws.amazon.com/lambda/home?region=us-east-2#/functions/adpa-data-processor-development

2. **Click "Test" tab**

3. **Create Test Event:**
   ```json
   {
     "action": "health_check"
   }
   ```

4. **Click "Test" button**

5. **View Results** in the Execution Results panel

### Method 3: Python SDK (boto3)

```python
import boto3
import json

# Initialize Lambda client
lambda_client = boto3.client('lambda', region_name='us-east-2')

# Health check
response = lambda_client.invoke(
    FunctionName='adpa-data-processor-development',
    Payload=json.dumps({"action": "health_check"})
)

result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))

# Run pipeline
response = lambda_client.invoke(
    FunctionName='adpa-data-processor-development',
    Payload=json.dumps({
        "action": "run_pipeline",
        "objective": "Predict sales forecast",
        "dataset_path": "s3://adpa-data-083308938449-development/sales_data.csv"
    })
)

result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))
```

---

## 📊 Available Actions

### 1. `health_check`
**Purpose:** Verify all ADPA components are working

**Payload:**
```json
{"action": "health_check"}
```

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "imports": true,
    "monitoring": true,
    "kpi_tracker": true,
    "agent": true
  }
}
```

### 2. `run_pipeline`
**Purpose:** Execute a complete ML pipeline

**Payload:**
```json
{
  "action": "run_pipeline",
  "objective": "Build a classification model",
  "dataset_path": "s3://bucket/data.csv",
  "config": {
    "max_execution_time": 600,
    "optimization_metric": "accuracy"
  }
}
```

**Response:**
```json
{
  "status": "completed",
  "pipeline_id": "uuid",
  "execution_time": 45.2,
  "performance_metrics": {...},
  "model_performance": {...}
}
```

### 3. `get_status`
**Purpose:** Check pipeline execution status

**Payload:**
```json
{
  "action": "get_status",
  "pipeline_id": "your-pipeline-id"
}
```

---

## 🔑 Credentials & Authentication

### Current Setup
- **User:** `umeshka` (you're currently using these credentials)
- **Account ID:** `083308938449`
- **Access:** Full access to Lambda, S3, ECR, IAM

### Where Credentials Are Stored

1. **Local Machine:** 
   ```bash
   cat ~/.aws/credentials
   cat ~/.aws/config
   ```

2. **Lambda Execution Role:**
   - ADPA uses: `adpa-lambda-execution-role-development`
   - This role has permissions to:
     - Read/Write S3 buckets
     - Write CloudWatch Logs
     - Execute Lambda functions

### To Use Different Credentials

**Option 1: Use AWS_PROFILE**
```bash
export AWS_PROFILE=your-profile-name
aws lambda invoke ...
```

**Option 2: Use Different User**
```bash
aws configure --profile adpa-user
# Enter new credentials
export AWS_PROFILE=adpa-user
```

**Option 3: Temporary Credentials**
```bash
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_SESSION_TOKEN=your-token  # if using temporary creds
```

---

## 📝 View Logs

### Real-time Logs (Follow)
```bash
aws logs tail /aws/lambda/adpa-data-processor-development \
  --follow \
  --region us-east-2
```

### Recent Logs (Last 5 minutes)
```bash
aws logs tail /aws/lambda/adpa-data-processor-development \
  --since 5m \
  --region us-east-2
```

### Filter Logs
```bash
aws logs tail /aws/lambda/adpa-data-processor-development \
  --filter-pattern "ERROR" \
  --since 1h \
  --region us-east-2
```

---

## 🔄 Update/Redeploy

### To Deploy Code Changes

```bash
cd /Users/adariprasad/weapon/UMD/DATA650/Group\ Presentation/adpa
python3 deploy_docker.py
```

This will:
1. ✅ Build new Docker image with your changes
2. ✅ Push to ECR
3. ✅ Update Lambda function
4. ✅ Run health check

**Time:** ~5-8 minutes (build) + ~2-3 minutes (push/deploy)

### To View Current Deployment

```bash
# Function details
aws lambda get-function \
  --function-name adpa-data-processor-development \
  --region us-east-2

# Current image
aws lambda get-function-configuration \
  --function-name adpa-data-processor-development \
  --region us-east-2 \
  --query 'CodeSha256'
```

---

## 🧪 Testing

### Quick Test Script
Create `test_adpa.sh`:
```bash
#!/bin/bash

echo "🧪 Testing ADPA Lambda Function"
echo "================================"

echo -e "\n1️⃣ Health Check..."
aws lambda invoke \
  --function-name adpa-data-processor-development \
  --payload '{"action": "health_check"}' \
  --region us-east-2 \
  health.json

cat health.json | python3 -m json.tool

echo -e "\n✅ Test Complete!"
```

Run:
```bash
chmod +x test_adpa.sh
./test_adpa.sh
```

---

## 💰 Cost Considerations

**Lambda Costs:**
- **Memory:** 3008 MB
- **Duration:** Up to 900 seconds (15 min)
- **Cost:** ~$0.000050 per second (~$0.75 per full execution)
- **Free Tier:** 1M requests/month, 400,000 GB-seconds

**ECR Costs:**
- **Storage:** ~$0.10/GB per month (1.04 GB = ~$0.10/month)

**S3 Costs:**
- **Storage:** ~$0.023/GB per month
- **Requests:** Minimal

**Estimated Monthly Cost:** <$5 for development usage

---

## 🛠️ Troubleshooting

### Function Not Working?
```bash
# Check function status
aws lambda get-function-configuration \
  --function-name adpa-data-processor-development \
  --region us-east-2 \
  --query 'State'

# Check recent errors in logs
aws logs tail /aws/lambda/adpa-data-processor-development \
  --filter-pattern "ERROR" \
  --since 1h \
  --region us-east-2
```

### Timeout Issues?
```bash
# Increase timeout (max 900 seconds)
aws lambda update-function-configuration \
  --function-name adpa-data-processor-development \
  --timeout 900 \
  --region us-east-2
```

### Memory Issues?
```bash
# Increase memory (max 10240 MB)
aws lambda update-function-configuration \
  --function-name adpa-data-processor-development \
  --memory-size 4096 \
  --region us-east-2
```

---

## 🔗 Quick Links

| Resource | URL |
|----------|-----|
| Lambda Console | https://us-east-2.console.aws.amazon.com/lambda/home?region=us-east-2#/functions/adpa-data-processor-development |
| ECR Repository | https://us-east-2.console.aws.amazon.com/ecr/repositories/private/083308938449/adpa?region=us-east-2 |
| CloudWatch Logs | https://us-east-2.console.aws.amazon.com/cloudwatch/home?region=us-east-2#logsV2:log-groups/log-group/$252Faws$252Flambda$252Fadpa-data-processor-development |
| S3 Data Bucket | https://s3.console.aws.amazon.com/s3/buckets/adpa-data-083308938449-development?region=us-east-2 |
| S3 Model Bucket | https://s3.console.aws.amazon.com/s3/buckets/adpa-models-083308938449-development?region=us-east-2 |
| IAM Role | https://console.aws.amazon.com/iam/home#/roles/adpa-lambda-execution-role-development |

---

## 📚 Next Steps

1. **Upload Data to S3:**
   ```bash
   aws s3 cp your_data.csv s3://adpa-data-083308938449-development/datasets/
   ```

2. **Run Your First Pipeline:**
   ```bash
   aws lambda invoke \
     --function-name adpa-data-processor-development \
     --payload '{"action": "run_pipeline", "objective": "test", "dataset_path": "s3://adpa-data-083308938449-development/datasets/your_data.csv"}' \
     --region us-east-2 \
     result.json
   ```

3. **Monitor Execution:**
   ```bash
   aws logs tail /aws/lambda/adpa-data-processor-development --follow --region us-east-2
   ```

---

**Need help?** Check the logs or run health check to diagnose issues.
