# ADPA Presentation - Screenshot Capture Guide

## Screenshots Needed for Presentation

### 1. Frontend Dashboard (Slide 6)
**URL:** http://adpa-frontend-083308938449-production.s3-website.us-east-2.amazonaws.com

Capture:
- [ ] Main dashboard showing pipeline list
- [ ] Pipeline creation dialog/form
- [ ] Results viewer with charts

### 2. Classification Pipeline Results (Slide 7)
**URL:** http://adpa-frontend-083308938449-production.s3-website.us-east-2.amazonaws.com

Click on "ADPA Customer Churn Prediction Pipeline" and capture:
- [ ] Overview tab with metrics
- [ ] AI Summary tab showing Bedrock insights
- [ ] Feature importance chart
- [ ] Confusion matrix visualization

### 3. Regression Pipeline Results (Slide 8)
**URL:** http://adpa-frontend-083308938449-production.s3-website.us-east-2.amazonaws.com

Click on "ADPA Sales Revenue Forecasting Pipeline" and capture:
- [ ] Overview tab with R², RMSE, MAE metrics
- [ ] AI Summary tab with trend analysis
- [ ] Predictions chart

### 4. AWS Console Screenshots (Slide 9)

#### CloudWatch Dashboard
**URL:** https://us-east-2.console.aws.amazon.com/cloudwatch/home?region=us-east-2#dashboards:name=ADPA-PROD-Dashboard
- [ ] Full dashboard view

#### Lambda Function
**URL:** https://us-east-2.console.aws.amazon.com/lambda/home?region=us-east-2#/functions/adpa-lambda-function
- [ ] Function overview
- [ ] Monitoring tab with invocation metrics

#### API Gateway
**URL:** https://us-east-2.console.aws.amazon.com/apigateway/home?region=us-east-2
- [ ] API endpoint configuration
- [ ] Resource structure

#### DynamoDB
**URL:** https://us-east-2.console.aws.amazon.com/dynamodbv2/home?region=us-east-2#table?name=adpa-pipelines
- [ ] Table with pipeline items

#### S3 Buckets
**URL:** https://s3.console.aws.amazon.com/s3/buckets?region=us-east-2
- [ ] List of ADPA buckets
- [ ] Frontend bucket contents

### 5. Architecture Diagram (Slide 3)
- [ ] Create visual diagram using draw.io or Lucidchart
- [ ] Show data flow between components

---

## Quick Links for Demo

1. **Frontend Dashboard:**
   http://adpa-frontend-083308938449-production.s3-website.us-east-2.amazonaws.com

2. **API Health Check:**
   https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/health

3. **List Pipelines:**
   https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/pipelines

4. **Classification Pipeline:**
   https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/pipelines/c918d785-b403-4869-be01-2f499472827f

5. **Regression Pipeline:**
   https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/pipelines/578818bc-029a-48ac-83a2-d3e0b5e87987

6. **CloudWatch Dashboard:**
   https://us-east-2.console.aws.amazon.com/cloudwatch/home?region=us-east-2#dashboards:name=ADPA-PROD-Dashboard

---

## API Demo Commands (for live demo)

```bash
# Health check
curl https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/health

# List all pipelines
curl https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/pipelines | python3 -m json.tool

# Get classification pipeline details
curl https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/pipelines/c918d785-b403-4869-be01-2f499472827f | python3 -m json.tool

# Get regression pipeline details
curl https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/pipelines/578818bc-029a-48ac-83a2-d3e0b5e87987 | python3 -m json.tool
```
