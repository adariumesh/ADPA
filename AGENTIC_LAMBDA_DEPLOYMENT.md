# ADPA Agentic Lambda Deployment Guide

## Problem Identified

The original `lambda_function_real_ml.py` was **NOT implementing the full agentic pipeline**. It was missing:

- ❌ Phase 5.1: Natural Language Understanding (Amazon Bedrock LLM)
- ❌ Phase 5.2: Intelligent Dataset Analysis (AI-powered)
- ❌ Phase 5.3: Experience-Based Recommendations
- ❌ Phase 5.4: AI Pipeline Planning
- ❌ Integration with `MasterAgenticController`, `LLMReasoningEngine`, `AgenticPipelineReasoner`

## Solution

Created `lambda_function_agentic.py` which implements the **complete Phase 4-8 flow**:

### Phase 4: Pipeline Creation & Execution ✅
- `handle_create_pipeline()` - Creates pipeline and starts agentic processing
- Pipeline stored in DynamoDB with AI insights

### Phase 5: Master Agentic Controller - AI-Powered Processing ✅

#### Step 5.1: Natural Language Understanding
```python
objective_understanding = ai_reasoner.understand_natural_language_objective(objective, config)
```
- Calls Amazon Bedrock Claude 3.5 Sonnet
- Extracts: problem_type, success_metrics, algorithm_hints, etc.

#### Step 5.2: Intelligent Dataset Analysis
```python
dataset_analysis = ai_reasoner.analyze_dataset_intelligently(data_result, objective_understanding)
```
- AI suggests target column
- Determines preprocessing requirements
- Assesses data quality score

#### Step 5.3: Experience-Based Recommendations
```python
recommendations = ai_reasoner.get_experience_recommendations(data_result, problem_type)
```
- Returns optimal algorithms based on similar past executions
- Hyperparameter suggestions

#### Step 5.4: Intelligent Pipeline Planning
```python
pipeline_plan = ai_reasoner.create_intelligent_pipeline_plan(dataset_analysis, objective_understanding, recommendations)
```
- AI creates optimized pipeline with reasoning
- Algorithm selection with justification

### Phase 6: Pipeline Execution Steps ✅
- Step 6.1: Data Ingestion (from S3)
- Step 6.2: Data Preprocessing (AI-configured missing value handling, scaling)
- Step 6.3: Model Training (AI-selected algorithm)
- Step 6.4: Model Evaluation (metrics, feature importance)

### Phase 7: Results Storage ✅
- Model artifacts saved to S3
- AI insights stored in DynamoDB

### Phase 8: Frontend Results Display ✅
- Pipeline status with AI insights
- Execution logs with progress

---

## Deployment Instructions

### Option 1: Update Existing Lambda

1. **Backup current Lambda code**
```bash
aws lambda get-function --function-name adpa-ml-pipeline --query 'Code.Location' --output text | xargs curl -o backup_lambda.zip
```

2. **Package new Lambda code**
```bash
cd /Users/architgolatkar/arc/Fall2025/Cloud\ Computing/DL_Project/ADPA/deploy

# Create deployment package
zip -r lambda_deployment.zip lambda_function_agentic.py

# Rename the function file for deployment
cd /tmp && mkdir lambda_package && cd lambda_package
unzip ../lambda_deployment.zip
mv lambda_function_agentic.py lambda_function.py
zip -r ../adpa_agentic_lambda.zip .
```

3. **Update Lambda function**
```bash
aws lambda update-function-code \
  --function-name adpa-ml-pipeline \
  --zip-file fileb:///tmp/adpa_agentic_lambda.zip \
  --region us-east-2
```

### Option 2: Create New Lambda

```bash
aws lambda create-function \
  --function-name adpa-agentic-pipeline \
  --runtime python3.11 \
  --handler lambda_function.lambda_handler \
  --role arn:aws:iam::083308938449:role/adpa-lambda-execution-role \
  --timeout 900 \
  --memory-size 512 \
  --environment "Variables={AWS_REGION=us-east-2,DATA_BUCKET=adpa-data-083308938449-production,MODEL_BUCKET=adpa-models-083308938449-production,PIPELINES_TABLE=adpa-pipelines,BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0}" \
  --zip-file fileb:///tmp/adpa_agentic_lambda.zip \
  --region us-east-2
```

### Required IAM Permissions

The Lambda execution role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-3-5-sonnet-*",
        "arn:aws:bedrock:us-east-2::foundation-model/us.anthropic.claude-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:HeadBucket"
      ],
      "Resource": [
        "arn:aws:s3:::adpa-data-*",
        "arn:aws:s3:::adpa-data-*/*",
        "arn:aws:s3:::adpa-models-*",
        "arn:aws:s3:::adpa-models-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:us-east-2:083308938449:table/adpa-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

### Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `AWS_REGION` | `us-east-2` | AWS region |
| `DATA_BUCKET` | `adpa-data-083308938449-production` | S3 bucket for datasets |
| `MODEL_BUCKET` | `adpa-models-083308938449-production` | S3 bucket for models |
| `PIPELINES_TABLE` | `adpa-pipelines` | DynamoDB table for pipelines |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-3-5-sonnet-20241022-v2:0` | Bedrock model ID |

---

## Testing After Deployment

### 1. Test Health Endpoint
```bash
curl https://YOUR_API_GATEWAY_URL/health
```

Expected response shows `bedrock: true` and `version: 4.0.0-agentic`:
```json
{
  "status": "healthy",
  "components": {
    "api": true,
    "s3_access": true,
    "dynamodb": true,
    "bedrock": true,
    "lambda": true
  },
  "ai_capabilities": {
    "bedrock_enabled": true,
    "model_id": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "agentic_features": [
      "natural_language_understanding",
      "intelligent_dataset_analysis",
      "experience_based_recommendations", 
      "ai_pipeline_planning"
    ]
  },
  "version": "4.0.0-agentic"
}
```

### 2. Test Pipeline Creation
```bash
curl -X POST https://YOUR_API_GATEWAY_URL/pipelines \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_path": "s3://adpa-data-083308938449-production/datasets/your_file.csv",
    "objective": "Predict customer churn based on usage patterns",
    "config": {}
  }'
```

### 3. Check Pipeline Status (with AI Insights)
```bash
curl https://YOUR_API_GATEWAY_URL/pipelines/YOUR_PIPELINE_ID
```

The response should include `ai_insights`:
```json
{
  "data": {
    "pipeline_id": "...",
    "status": "completed",
    "ai_insights": {
      "objective_understanding": {
        "problem_type": "classification",
        "success_metrics": ["accuracy", "f1_score"]
      },
      "dataset_analysis": {
        "suggested_target_column": "churn",
        "data_quality_score": 0.85
      },
      "pipeline_plan": {
        "selected_algorithm": "xgboost",
        "algorithm_reasoning": "..."
      }
    }
  }
}
```

---

## Key Differences: Old vs New Lambda

| Feature | Old (`lambda_function_real_ml.py`) | New (`lambda_function_agentic.py`) |
|---------|-----------------------------------|-------------------------------------|
| LLM Integration | ❌ None | ✅ Amazon Bedrock Claude |
| NL Understanding | ❌ Manual rules | ✅ AI-powered parsing |
| Dataset Analysis | ❌ Basic profiling | ✅ Intelligent analysis |
| Algorithm Selection | ❌ Hardcoded linear | ✅ AI-selected |
| Pipeline Planning | ❌ Fixed steps | ✅ Intelligent planning |
| Experience Learning | ❌ None | ✅ Recommendation system |
| Version | 3.0.0-real-ml | 4.0.0-agentic |

---

## Troubleshooting

### Bedrock Not Available
If `bedrock: false` in health check:
1. Check IAM role has Bedrock permissions
2. Verify Bedrock is enabled in your AWS account
3. Check model ID is valid for your region

### Pipeline Stuck at "running"
1. Check CloudWatch logs for Lambda
2. Increase Lambda timeout (max 15 min)
3. Check S3/DynamoDB permissions

### Low Model Performance
The current implementation uses a linear approximation for fast execution. For production:
1. Consider using SageMaker for training
2. Implement proper sklearn/xgboost in a Lambda layer
