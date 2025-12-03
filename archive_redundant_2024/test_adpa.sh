#!/bin/bash

echo "🧪 Testing ADPA Lambda Function"
echo "================================"

echo -e "\n1️⃣ Health Check..."
aws lambda invoke \
  --function-name adpa-data-processor-development \
  --payload '{"action": "health_check"}' \
  --region us-east-2 \
  health.json

echo -e "\n📊 Result:"
cat health.json | python3 -m json.tool

echo -e "\n2️⃣ Checking Lambda Configuration..."
aws lambda get-function-configuration \
  --function-name adpa-data-processor-development \
  --region us-east-2 \
  --query '{Memory:MemorySize,Timeout:Timeout,State:State,LastModified:LastModified}' \
  --output json | python3 -m json.tool

echo -e "\n✅ Test Complete!"
echo -e "\n📍 Quick Links:"
echo "   Lambda: https://us-east-2.console.aws.amazon.com/lambda/home?region=us-east-2#/functions/adpa-data-processor-development"
echo "   Logs: https://us-east-2.console.aws.amazon.com/cloudwatch/home?region=us-east-2#logsV2:log-groups/log-group/\$252Faws\$252Flambda\$252Fadpa-data-processor-development"
