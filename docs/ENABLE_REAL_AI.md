# Enable 100% Real AI in Production

## Quick Answer: 3 Simple Steps (5-10 minutes)

### Step 1: Update Lambda Environment Variable (2 minutes)

```bash
# Set environment variable to force real AI usage
aws lambda update-function-configuration \
  --function-name adpa-lambda-function \
  --environment "Variables={
    USE_REAL_LLM=true,
    LLM_PROVIDER=bedrock,
    BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0,
    AWS_REGION=us-east-2,
    DATA_BUCKET=adpa-data-083308938449-production,
    MODEL_BUCKET=adpa-models-083308938449-production,
    ENVIRONMENT=production
  }" \
  --region us-east-2
```

### Step 2: Update LLM Integration Code (3 minutes)

Modify `src/agent/utils/llm_integration.py` to disable fallback:

```python
# Line 251 - Change from:
def _call_llm(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1) -> str:
    try:
        if self.provider == LLMProvider.BEDROCK and self.client:
            # ... real AI call ...
            return llm_response
    except Exception as e:
        # REMOVE THIS FALLBACK - Force real AI only
        return self._simulate_llm_response(prompt)

# Change to:
def _call_llm(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1) -> str:
    # Force real AI - no fallback to simulation
    force_real_ai = os.getenv('USE_REAL_LLM', 'false').lower() == 'true'
    
    try:
        if self.provider == LLMProvider.BEDROCK and self.client:
            # ... real AI call ...
            return llm_response
        elif self.provider == LLMProvider.OPENAI and self.client:
            # ... OpenAI call ...
            return llm_response
    except Exception as e:
        if force_real_ai:
            # FAIL HARD - Don't use simulation
            raise Exception(f"Real AI required but call failed: {e}")
        else:
            # Only fallback if not forced
            return self._simulate_llm_response(prompt)
```

### Step 3: Update Lambda Initialization (2 minutes)

Modify `lambda_function.py` to force real AI:

```python
# Around line 110-117, add environment check:
# Initialize master agent with REAL AI FORCED
self.agent = MasterAgenticController(
    aws_config=AWS_CONFIG,
    memory_dir="/tmp/experience_memory"
)

# Force real LLM usage
if os.getenv('USE_REAL_LLM', 'false').lower() == 'true':
    self.agent.reasoning_engine.provider = LLMProvider.BEDROCK
    self.agent.reasoning_engine._init_provider_client()
    logger.info("✅ REAL AI ENABLED - Using AWS Bedrock Claude 3.5 Sonnet")
else:
    logger.info("⚠️ Using intelligent simulation (set USE_REAL_LLM=true for real AI)")
```

---

## Alternative: Code-Only Solution (No Environment Variables)

If you want to **force real AI in the code** without environment variables:

### Option A: Modify `llm_integration.py` Directly

```python
# src/agent/utils/llm_integration.py
class LLMReasoningEngine:
    def __init__(self, 
                 provider: LLMProvider = LLMProvider.BEDROCK,
                 model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                 region: str = "us-east-2",
                 force_real_ai: bool = True):  # ADD THIS PARAMETER
        
        self.force_real_ai = force_real_ai  # ADD THIS LINE
        # ... rest of init ...
    
    def _call_llm(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1) -> str:
        try:
            # Always try real AI first
            if self.provider == LLMProvider.BEDROCK and self.client:
                response = self.client.invoke_model(...)
                return llm_response
        except Exception as e:
            if self.force_real_ai:
                # Don't fallback - fail with clear error
                raise Exception(f"Real AI required but failed: {e}")
            else:
                # Only use simulation if allowed
                return self._simulate_llm_response(prompt)
```

### Option B: Remove Simulation Code Entirely

```bash
# Backup the file first
cp src/agent/utils/llm_integration.py src/agent/utils/llm_integration.py.backup

# Edit the file and remove all _simulate_* methods
# Lines 340-600 approximately
```

Then modify `_call_llm` to:
```python
def _call_llm(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1) -> str:
    """Make ONLY real LLM calls - no simulation fallback."""
    
    if not self.client:
        raise Exception("LLM client not initialized - cannot proceed without real AI")
    
    start_time = time.time()
    
    if self.provider == LLMProvider.BEDROCK:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        })
        
        response = self.client.invoke_model(
            body=body,
            modelId=self.model_id,
            accept="application/json",
            contentType="application/json"
        )
        
        response_body = json.loads(response.get('body').read())
        content = response_body.get('content', [])
        return content[0].get('text', '') if content else ''
    
    elif self.provider == LLMProvider.OPENAI:
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=[
                {"role": "system", "content": "You are an expert ML engineer and data scientist."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content
    
    else:
        raise Exception(f"Unsupported LLM provider: {self.provider}")
```

---

## Complete Deployment Script

Create and run this script to enable real AI:

```bash
#!/bin/bash
# File: enable_real_ai.sh

echo "🚀 Enabling 100% Real AI in Production..."

# 1. Update environment variable
echo "Step 1: Setting Lambda environment variable..."
aws lambda update-function-configuration \
  --function-name adpa-lambda-function \
  --environment "Variables={USE_REAL_LLM=true,LLM_PROVIDER=bedrock,BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0,AWS_REGION=us-east-2,DATA_BUCKET=adpa-data-083308938449-production,MODEL_BUCKET=adpa-models-083308938449-production,ENVIRONMENT=production}" \
  --region us-east-2

echo "✅ Environment variable set"

# 2. Update the code to force real AI
echo "Step 2: Updating code to force real AI..."

# Backup original file
cp src/agent/utils/llm_integration.py src/agent/utils/llm_integration.py.backup

# Add force_real_ai parameter (using Python to modify the file)
python3 << 'PYTHON_SCRIPT'
import re

with open('src/agent/utils/llm_integration.py', 'r') as f:
    content = f.read()

# Find the __init__ method and add force_real_ai parameter
content = re.sub(
    r'def __init__\(self,\s*provider:.*?region: str = "us-east-2"\)',
    'def __init__(self, provider: LLMProvider = LLMProvider.BEDROCK, model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0", region: str = "us-east-2", force_real_ai: bool = True)',
    content
)

# Add force_real_ai attribute
content = re.sub(
    r'(self\.region = region\s+self\.logger = logging\.getLogger\(__name__\))',
    r'\1\n        self.force_real_ai = force_real_ai',
    content
)

# Modify _call_llm to check force_real_ai
content = re.sub(
    r'(except Exception as e:.*?self\.logger\.error.*?# Return intelligent fallback\s+return self\._simulate_llm_response\(prompt\))',
    '''except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"LLM call failed after {execution_time:.2f}s: {e}")
            
            if self.force_real_ai or os.getenv('USE_REAL_LLM', 'false').lower() == 'true':
                # FAIL HARD - Real AI required
                raise Exception(f"Real AI required but call failed: {e}")
            
            # Track the failed call
            self.reasoning_calls.append({
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "error": str(e),
                "execution_time": execution_time,
                "timestamp": time.time(),
                "provider": self.provider.value,
                "success": False
            })
            
            # Only fallback if not forced
            return self._simulate_llm_response(prompt)''',
    content,
    flags=re.DOTALL
)

with open('src/agent/utils/llm_integration.py', 'w') as f:
    f.write(content)

print("✅ Code updated to force real AI")
PYTHON_SCRIPT

# 3. Redeploy Lambda
echo "Step 3: Redeploying Lambda with updated code..."

# Create deployment package
cd src
zip -r ../deployment.zip . -x "*.pyc" -x "__pycache__/*"
cd ..

# Update Lambda function code
aws lambda update-function-code \
  --function-name adpa-lambda-function \
  --zip-file fileb://deployment.zip \
  --region us-east-2

echo "✅ Lambda redeployed"

# 4. Test that real AI is working
echo "Step 4: Testing real AI..."
sleep 5  # Wait for Lambda to update

TEST_RESPONSE=$(curl -s -X POST https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/pipelines \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Real AI Test",
    "objective": "Predict customer lifetime value",
    "type": "regression"
  }')

echo "Test response:"
echo "$TEST_RESPONSE" | jq .

# Check if it succeeded
if echo "$TEST_RESPONSE" | jq -e '.pipeline_id' > /dev/null 2>&1; then
    echo "✅ Real AI is working!"
    
    # Check CloudWatch logs for confirmation
    echo "Checking Lambda logs for AI confirmation..."
    aws logs tail /aws/lambda/adpa-lambda-function \
      --follow \
      --region us-east-2 \
      --since 1m | grep -i "bedrock\|claude\|real ai"
else
    echo "❌ Test failed. Check logs:"
    aws logs tail /aws/lambda/adpa-lambda-function \
      --region us-east-2 \
      --since 5m
fi

echo ""
echo "================================================================"
echo "🎉 Real AI Enablement Complete!"
echo "================================================================"
echo ""
echo "Next steps:"
echo "1. Monitor costs at: https://console.aws.amazon.com/billing"
echo "2. Check Bedrock usage: https://console.aws.amazon.com/bedrock"
echo "3. View logs: aws logs tail /aws/lambda/adpa-lambda-function --follow"
echo ""
echo "Expected cost: ~\$0.018 per pipeline creation"
echo "Monthly estimate (100 pipelines): ~\$50"
echo ""
```

---

## Cost Implications

### Before (Simulation):
- Cost per pipeline: **$0**
- Monthly cost: **$0**

### After (Real AI):
- Cost per pipeline: **~$0.018**
- Monthly cost (100 pipelines): **~$54**
- Monthly cost (1000 pipelines): **~$540**

### Bedrock Pricing (Claude 3.5 Sonnet):
- Input: $0.003 per 1000 tokens
- Output: $0.015 per 1000 tokens

### Typical Pipeline Creation:
- Prompt: ~500 tokens input
- Response: ~1000 tokens output
- Cost: (500 × $0.003/1000) + (1000 × $0.015/1000) = **$0.0015 + $0.015 = $0.0165**

---

## Verification Steps

### 1. Check Environment Variable
```bash
aws lambda get-function-configuration \
  --function-name adpa-lambda-function \
  --region us-east-2 \
  --query 'Environment.Variables.USE_REAL_LLM'
```
Should return: `"true"`

### 2. Check CloudWatch Logs
```bash
aws logs tail /aws/lambda/adpa-lambda-function \
  --follow \
  --region us-east-2 | grep -i "bedrock\|claude\|llm"
```
Should see: `"✅ REAL AI ENABLED - Using AWS Bedrock Claude 3.5 Sonnet"`

### 3. Test Real AI Call
```bash
curl -X POST https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/pipelines \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Real AI Test",
    "objective": "Build a model to predict customer churn using advanced ML techniques",
    "type": "classification"
  }' | jq '.ai_insights'
```

Look for **unique, contextual responses** instead of templated ones.

### 4. Monitor Bedrock Usage
```bash
# Check Bedrock invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=ModelId,Value=us.anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --region us-east-2
```

### 5. Compare Responses

**Before (Simulation):**
```json
{
  "ai_insights": {
    "pipeline_plan": {
      "selected_algorithm": "xgboost",
      "optimization_opportunities": [
        "Feature selection to reduce dimensionality",
        "Implement SMOTE for handling class imbalance"
      ]
    }
  }
}
```

**After (Real AI):**
```json
{
  "ai_insights": {
    "reasoning": "After analyzing the customer churn prediction objective with advanced ML techniques requirement, I recommend a multi-model ensemble approach. Given the business-critical nature of churn prediction, we should prioritize both accuracy and interpretability...",
    "pipeline_plan": {
      "selected_algorithm": "gradient_boosting_ensemble",
      "specific_recommendations": [
        "Start with XGBoost as primary model due to its proven performance on tabular data",
        "Add LightGBM as secondary model for faster inference in production",
        "Include a logistic regression model for interpretability and baseline comparison",
        "Use SHAP values for model explainability to business stakeholders"
      ],
      "confidence": 0.87
    }
  }
}
```

---

## Rollback Plan

If you need to disable real AI and go back to simulation:

```bash
# Revert environment variable
aws lambda update-function-configuration \
  --function-name adpa-lambda-function \
  --environment "Variables={USE_REAL_LLM=false}" \
  --region us-east-2

# Or restore backup code
cp src/agent/utils/llm_integration.py.backup src/agent/utils/llm_integration.py

# Redeploy
cd src && zip -r ../deployment.zip . && cd ..
aws lambda update-function-code \
  --function-name adpa-lambda-function \
  --zip-file fileb://deployment.zip \
  --region us-east-2
```

---

## Summary

**To enable 100% real AI production usage:**

1. ✅ **Set environment variable**: `USE_REAL_LLM=true`
2. ✅ **Modify code**: Force real AI, remove fallback to simulation
3. ✅ **Redeploy Lambda**: Update function code
4. ✅ **Test**: Verify Bedrock is being called
5. ✅ **Monitor**: Track costs and usage

**Total time**: 10-15 minutes  
**Cost**: ~$50/month for moderate usage  
**Benefit**: True AI-powered pipeline generation with unique, contextual responses

**Run the script**: `./enable_real_ai.sh` (create the file above and run it)
