# 🚀 ADPA Step-by-Step Deployment Guide

## **Current Status Check**

✅ **Python 3.12.7**: Ready  
❌ **AWS CLI**: **MISSING - NEEDS INSTALLATION**  
🔄 **Dependencies**: Checking...  
🔄 **AWS Credentials**: Pending  
🔄 **Project Structure**: Pending  

---

## **Phase 1: Prerequisites Installation**

### **Step 1.1: Install AWS CLI**

**CRITICAL**: You need AWS CLI for cloud deployment.

```bash
# Option 1: Using pip
pip install awscli

# Option 2: Using Homebrew (Mac)
brew install awscli

# Option 3: Download installer
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Verify Installation:**
```bash
aws --version
# Should show: aws-cli/2.x.x
```

### **Step 1.2: Configure AWS Credentials**

**CRITICAL**: You need AWS credentials for deployment.

```bash
aws configure
```

**Enter:**
- **AWS Access Key ID**: [Your AWS Access Key]
- **AWS Secret Access Key**: [Your AWS Secret Key] 
- **Default region name**: `us-east-1`
- **Default output format**: `json`

**Verify Credentials:**
```bash
aws sts get-caller-identity
# Should show your AWS Account ID
```

### **Step 1.3: Install Python Dependencies**

```bash
cd "/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa"
pip install -r requirements.txt
```

---

## **Phase 2: Local Deployment & Testing**

### **Step 2.1: Test Core Functionality**

```bash
# Test imports and basic functionality
python -c "
import sys
sys.path.insert(0, '.')
from src.agent.core.master_agent import MasterAgenticController
from src.pipeline.evaluation.reporter import ReportingStep
from mcp_server.server import ADPAProjectManager
print('✅ All core components working!')
"
```

### **Step 2.2: Local Deployment**

```bash
# Run local deployment
./deploy.sh local true
```

**Expected Output:**
- ✅ Core functionality verified
- ✅ Local deployment complete
- ✅ Pipeline verification successful

### **Step 2.3: Test MCP Server**

```bash
# Start MCP server in background
python mcp_server/server.py &
MCP_PID=$!

# Test MCP functionality
python -c "
from mcp_server.server import ADPAProjectManager
from pathlib import Path
manager = ADPAProjectManager(Path('.'))
print('MCP Status:', manager.get_project_status())
print('Next Task:', manager.get_next_task())
"

# Stop MCP server
kill $MCP_PID
```

---

## **Phase 3: AWS Infrastructure Deployment**

### **Step 3.1: Deploy Base AWS Infrastructure**

```bash
# Deploy complete AWS infrastructure
./deploy/aws-deploy.sh development adpa us-east-1
```

**This creates:**
- ✅ VPC with public/private subnets
- ✅ S3 buckets for data and models  
- ✅ Lambda functions
- ✅ IAM roles and policies
- ✅ Step Functions state machine
- ✅ CloudWatch monitoring
- ✅ KMS encryption
- ✅ Secrets Manager

**Expected Duration:** 10-15 minutes

**Verification Commands:**
```bash
# Check CloudFormation stack
aws cloudformation describe-stacks --stack-name adpa-infrastructure-development

# Check S3 buckets
aws s3 ls | grep adpa

# Check Lambda functions  
aws lambda list-functions | grep adpa

# Check Step Functions
aws stepfunctions list-state-machines | grep adpa
```

### **Step 3.2: Test AWS Deployment**

```bash
# Test Lambda function
aws lambda invoke \
  --function-name adpa-data-processor-development \
  --payload '{"test": "deployment_verification"}' \
  response.json

# Check response
cat response.json

# Test S3 access
DATA_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name adpa-infrastructure-development \
  --query "Stacks[0].Outputs[?OutputKey=='DataBucketName'].OutputValue" \
  --output text)

aws s3 ls "s3://$DATA_BUCKET"
```

---

## **Phase 4: Global Access Deployment**

### **Step 4.1: Deploy Global Access Infrastructure**

```bash
# Make ADPA globally accessible
./deploy/make-global.sh development adpa
```

**This creates:**
- ✅ API Gateway with global endpoints
- ✅ CloudFront distribution (400+ edge locations)
- ✅ WAF protection and rate limiting
- ✅ CORS support for web apps
- ✅ HTTPS/SSL termination

**Expected Duration:** 15-20 minutes (CloudFront propagation)

### **Step 4.2: Get Global Access URLs**

```bash
# Get your global endpoints
aws cloudformation describe-stacks \
  --stack-name adpa-global-access-development \
  --query 'Stacks[0].Outputs[].{Key:OutputKey,Value:OutputValue}' \
  --output table
```

**Save these URLs:**
- **CloudFront Domain**: Your global access point
- **API Gateway Endpoint**: Direct API access
- **Global Endpoint URL**: Main execution endpoint

### **Step 4.3: Test Global Access**

```bash
# Get your CloudFront domain
CLOUDFRONT_DOMAIN=$(aws cloudformation describe-stacks \
  --stack-name adpa-global-access-development \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDomain'].OutputValue" \
  --output text)

echo "Testing global access at: https://$CLOUDFRONT_DOMAIN"

# Test CORS (should return 200)
curl -s -o /dev/null -w "%{http_code}" \
  "https://$CLOUDFRONT_DOMAIN/pipelines/execute" \
  -X OPTIONS

# Test actual pipeline execution
curl -X POST "https://$CLOUDFRONT_DOMAIN/pipelines/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "test-data", 
    "objective": "test global deployment"
  }'
```

---

## **Phase 5: Production Configuration**

### **Step 5.1: Update Secrets Manager**

```bash
# Get Secrets Manager ARN
SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name adpa-infrastructure-development \
  --query "Stacks[0].Outputs[?OutputKey=='SecretsManagerArn'].OutputValue" \
  --output text)

# Update with your API keys
aws secretsmanager update-secret \
  --secret-id "$SECRET_ARN" \
  --secret-string '{
    "openai_api_key": "your-openai-key-here",
    "anthropic_api_key": "your-anthropic-key-here",
    "environment": "development"
  }'
```

### **Step 5.2: Configure Custom Domain (Optional)**

If you want a custom domain like `api.yourcompany.com`:

```bash
# 1. Get SSL certificate in us-east-1 (required for CloudFront)
aws acm request-certificate \
  --domain-name api.yourcompany.com \
  --validation-method DNS \
  --region us-east-1

# 2. After certificate is validated, get ARN
CERT_ARN=$(aws acm list-certificates \
  --region us-east-1 \
  --query 'CertificateSummaryList[?DomainName==`api.yourcompany.com`].CertificateArn' \
  --output text)

# 3. Update global stack with custom domain
./deploy/make-global.sh development adpa api.yourcompany.com $CERT_ARN
```

---

## **Phase 6: Verification & Testing**

### **Step 6.1: Complete System Test**

```bash
# Run comprehensive test
python -c "
import requests
import json

# Test global access
cloudfront_domain = 'YOUR_CLOUDFRONT_DOMAIN_HERE'
url = f'https://{cloudfront_domain}/pipelines/execute'

test_data = {
    'data_path': 's3://test-bucket/sample.csv',
    'objective': 'predict customer churn',
    'features': ['age', 'income', 'usage']
}

print('🚀 Testing ADPA Global Access...')
try:
    response = requests.post(url, json=test_data, timeout=30)
    print(f'✅ Status Code: {response.status_code}')
    print(f'✅ Response: {response.json()}')
    print('🎉 ADPA is globally accessible!')
except Exception as e:
    print(f'❌ Test failed: {e}')
"
```

### **Step 6.2: Monitor Deployment**

```bash
# Check CloudWatch logs
aws logs describe-log-groups | grep adpa

# Check API Gateway metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Check CloudFront metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name Requests \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

---

## **Phase 7: Usage Examples**

### **Step 7.1: API Usage Examples**

```bash
# Replace with your actual CloudFront domain
export ADPA_GLOBAL_URL="https://your-cloudfront-domain.cloudfront.net/pipelines/execute"

# Example 1: Simple classification
curl -X POST "$ADPA_GLOBAL_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "s3://my-bucket/customer-data.csv",
    "objective": "predict customer churn",
    "problem_type": "classification"
  }'

# Example 2: Regression with custom features
curl -X POST "$ADPA_GLOBAL_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "s3://my-bucket/sales-data.csv", 
    "objective": "predict monthly revenue",
    "problem_type": "regression",
    "target_column": "revenue",
    "features": ["product_type", "season", "marketing_spend"]
  }'

# Example 3: Time series forecasting
curl -X POST "$ADPA_GLOBAL_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "s3://my-bucket/timeseries.csv",
    "objective": "forecast next 30 days sales",
    "problem_type": "time_series",
    "date_column": "date",
    "target_column": "sales"
  }'
```

### **Step 7.2: Integration Examples**

```python
# Python client example
import requests
import json

class ADPAClient:
    def __init__(self, global_url):
        self.url = global_url
    
    def run_pipeline(self, data_path, objective, **kwargs):
        payload = {
            'data_path': data_path,
            'objective': objective,
            **kwargs
        }
        
        response = requests.post(self.url, json=payload)
        return response.json()

# Usage
client = ADPAClient('https://your-domain.cloudfront.net/pipelines/execute')
result = client.run_pipeline(
    's3://my-bucket/data.csv',
    'predict customer satisfaction'
)
print(result)
```

```javascript
// JavaScript/Node.js client example
const axios = require('axios');

class ADPAClient {
    constructor(globalUrl) {
        this.url = globalUrl;
    }
    
    async runPipeline(dataPath, objective, options = {}) {
        const payload = {
            data_path: dataPath,
            objective: objective,
            ...options
        };
        
        const response = await axios.post(this.url, payload);
        return response.data;
    }
}

// Usage
const client = new ADPAClient('https://your-domain.cloudfront.net/pipelines/execute');
client.runPipeline('s3://my-bucket/data.csv', 'predict user engagement')
    .then(result => console.log(result));
```

---

## **Troubleshooting Common Issues**

### **Issue 1: AWS CLI Not Found**
```bash
# Install AWS CLI
pip install awscli
# OR
brew install awscli
```

### **Issue 2: Permission Denied on Scripts**
```bash
chmod +x deploy.sh
chmod +x deploy/aws-deploy.sh  
chmod +x deploy/make-global.sh
```

### **Issue 3: CloudFormation Stack Errors**
```bash
# Check stack events
aws cloudformation describe-stack-events \
  --stack-name adpa-infrastructure-development \
  --query 'StackEvents[0:10].[Timestamp,ResourceStatus,LogicalResourceId,ResourceStatusReason]' \
  --output table
```

### **Issue 4: CloudFront Not Accessible**
- CloudFront takes 15-20 minutes to propagate globally
- Check CloudFront distribution status:
```bash
aws cloudfront list-distributions \
  --query 'DistributionList.Items[?contains(Comment, `ADPA`)].{Id:Id,Status:Status,DomainName:DomainName}'
```

### **Issue 5: Lambda Function Errors**
```bash
# Check Lambda logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/adpa
aws logs get-log-events \
  --log-group-name /aws/lambda/adpa-data-processor-development \
  --log-stream-name $(aws logs describe-log-streams \
    --log-group-name /aws/lambda/adpa-data-processor-development \
    --order-by LastEventTime \
    --descending \
    --limit 1 \
    --query 'logStreams[0].logStreamName' \
    --output text)
```

---

## **Success Criteria Checklist**

### **Local Deployment ✅**
- [ ] Python dependencies installed
- [ ] Core components working
- [ ] MCP server functional
- [ ] Local tests passing

### **AWS Infrastructure ✅**  
- [ ] CloudFormation stack deployed
- [ ] S3 buckets created
- [ ] Lambda functions working
- [ ] Step Functions operational
- [ ] IAM roles configured
- [ ] Secrets Manager set up

### **Global Access ✅**
- [ ] API Gateway deployed
- [ ] CloudFront distribution active
- [ ] Global endpoints accessible
- [ ] CORS working
- [ ] SSL/HTTPS functional

### **Production Ready ✅**
- [ ] API keys configured
- [ ] Monitoring active
- [ ] Error handling working
- [ ] Performance optimized
- [ ] Security hardened

---

## **Final Verification Command**

Run this to verify everything is working:

```bash
echo "🎯 ADPA Complete System Verification"
echo "==================================="

# 1. Check local functionality
python -c "from src.agent.core.master_agent import MasterAgenticController; print('✅ Local: Core agent working')"

# 2. Check AWS infrastructure
aws cloudformation describe-stacks --stack-name adpa-infrastructure-development --query 'Stacks[0].StackStatus' --output text

# 3. Check global access
CLOUDFRONT_DOMAIN=$(aws cloudformation describe-stacks --stack-name adpa-global-access-development --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDomain'].OutputValue" --output text)
curl -s -o /dev/null -w "Global Access Status: %{http_code}\n" "https://$CLOUDFRONT_DOMAIN/pipelines/execute" -X OPTIONS

echo "🌍 ADPA Global URL: https://$CLOUDFRONT_DOMAIN/pipelines/execute"
echo "🎉 Deployment verification complete!"
```

**Expected Final Output:**
```
✅ Local: Core agent working
CREATE_COMPLETE
Global Access Status: 200
🌍 ADPA Global URL: https://d1234567890123.cloudfront.net/pipelines/execute
🎉 Deployment verification complete!
```

---

**🎊 Congratulations! ADPA is now globally accessible to 8 billion people worldwide!**