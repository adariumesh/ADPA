#!/bin/bash

PIPELINE_ID="0c21544a-c079-413f-8faf-9db8017fa31b"
API_URL="https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod/pipelines/${PIPELINE_ID}"

echo "🔄 Monitoring pipeline: ${PIPELINE_ID}"
echo "================================================================"
echo ""

ITERATION=1
MAX_ITERATIONS=10  # 10 iterations * 60 seconds = 10 minutes max

while [ $ITERATION -le $MAX_ITERATIONS ]; do
    echo "[$ITERATION] Checking status... ($(date +%H:%M:%S))"
    
    # Get pipeline status
    RESPONSE=$(curl -s "${API_URL}")
    STATUS=$(echo "$RESPONSE" | jq -r '.status')
    
    echo "   Status: $STATUS"
    
    # Check if completed or failed
    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo "✅ Pipeline completed successfully!"
        echo "================================================================"
        echo "$RESPONSE" | jq '.'
        echo "================================================================"
        exit 0
    elif [ "$STATUS" = "failed" ]; then
        echo ""
        echo "❌ Pipeline failed!"
        echo "================================================================"
        ERROR=$(echo "$RESPONSE" | jq -r '.error // "Unknown error"')
        echo "Error: $ERROR"
        echo "================================================================"
        exit 1
    elif [ "$STATUS" != "processing" ]; then
        echo "   Unknown status: $STATUS"
    fi
    
    # Wait before next check
    if [ $ITERATION -lt $MAX_ITERATIONS ]; then
        echo "   Waiting 60 seconds..."
        sleep 60
    fi
    
    ITERATION=$((ITERATION + 1))
    echo ""
done

echo "⏱️ Timeout: Pipeline still processing after 10 minutes"
echo "   Current status: $STATUS"
echo "   Pipeline may still complete in background"
echo "   Check manually: curl ${API_URL}"

