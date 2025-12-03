#!/bin/bash

# Add EventBridge Logging Rules
# Completes the EventBridge integration that Girik mentioned

set -e

echo "📡 Adding EventBridge Logging Rules"
echo "=================================="

# Configuration
STACK_NAME="adpa-eventbridge-rules"
ENVIRONMENT="development"
REGION="us-east-2"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Create EventBridge rules configuration
print_status "Creating EventBridge rules for ADPA logging..."

cat > eventbridge_rules.yaml << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Description: 'ADPA EventBridge Rules for Logging and Monitoring'

Parameters:
  Environment:
    Type: String
    Default: 'development'

Resources:
  # Custom Event Bus for ADPA
  ADPAEventBus:
    Type: AWS::Events::EventBus
    Properties:
      Name: !Sub 'adpa-events-${Environment}'
      Description: 'Custom event bus for ADPA pipeline events'
      Tags:
        - Key: Project
          Value: ADPA
        - Key: Environment
          Value: !Ref Environment

  # SNS Topic for EventBridge notifications
  ADPAEventTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: !Sub 'adpa-events-${Environment}'
      DisplayName: 'ADPA EventBridge Notifications'

  # Rule for Pipeline Success Events
  PipelineSuccessRule:
    Type: AWS::Events::Rule
    Properties:
      Name: !Sub 'adpa-pipeline-success-${Environment}'
      Description: 'Capture ADPA pipeline success events'
      EventBusName: !Ref ADPAEventBus
      EventPattern:
        source: ['adpa.pipeline']
        detail-type: ['Pipeline Execution']
        detail:
          status: ['completed', 'success']
      Targets:
        - Arn: !Ref ADPAEventTopic
          Id: 'PipelineSuccessSNS'
        - Arn: !GetAtt PipelineSuccessLogGroup.Arn
          Id: 'PipelineSuccessLogs'

  # Rule for Pipeline Failure Events
  PipelineFailureRule:
    Type: AWS::Events::Rule
    Properties:
      Name: !Sub 'adpa-pipeline-failure-${Environment}'
      Description: 'Capture ADPA pipeline failure events'
      EventBusName: !Ref ADPAEventBus
      EventPattern:
        source: ['adpa.pipeline']
        detail-type: ['Pipeline Execution']
        detail:
          status: ['failed', 'error']
      Targets:
        - Arn: !Ref ADPAEventTopic
          Id: 'PipelineFailureSNS'
        - Arn: !GetAtt PipelineFailureLogGroup.Arn
          Id: 'PipelineFailureLogs'

  # Rule for Lambda Function Events
  LambdaEventsRule:
    Type: AWS::Events::Rule
    Properties:
      Name: !Sub 'adpa-lambda-events-${Environment}'
      Description: 'Capture Lambda function events'
      EventPattern:
        source: ['aws.lambda']
        detail-type: ['Lambda Function Invocation Result']
        detail:
          responseElements:
            functionName:
              - prefix: 'adpa'
      Targets:
        - Arn: !GetAtt LambdaEventsLogGroup.Arn
          Id: 'LambdaEventsLogs'

  # Rule for API Gateway Events  
  APIGatewayRule:
    Type: AWS::Events::Rule
    Properties:
      Name: !Sub 'adpa-api-events-${Environment}'
      Description: 'Capture API Gateway events'
      EventPattern:
        source: ['aws.apigateway']
        detail-type: ['API Gateway Execution Logs']
        detail:
          responseElements:
            restApiId:
              - exists: true
      Targets:
        - Arn: !GetAtt APIGatewayLogGroup.Arn
          Id: 'APIGatewayLogs'

  # CloudWatch Log Groups for EventBridge rules
  PipelineSuccessLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub '/aws/events/adpa/pipeline-success-${Environment}'
      RetentionInDays: 30

  PipelineFailureLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub '/aws/events/adpa/pipeline-failure-${Environment}'
      RetentionInDays: 90

  LambdaEventsLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub '/aws/events/adpa/lambda-events-${Environment}'
      RetentionInDays: 30

  APIGatewayLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub '/aws/events/adpa/api-gateway-${Environment}'
      RetentionInDays: 30

  # IAM Role for EventBridge to CloudWatch Logs
  EventBridgeLogsRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub 'adpa-eventbridge-logs-role-${Environment}'
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: events.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: CloudWatchLogsPolicy
          PolicyDocument:
            Statement:
              - Effect: Allow
                Action:
                  - logs:CreateLogStream
                  - logs:PutLogEvents
                Resource: 
                  - !GetAtt PipelineSuccessLogGroup.Arn
                  - !GetAtt PipelineFailureLogGroup.Arn
                  - !GetAtt LambdaEventsLogGroup.Arn
                  - !GetAtt APIGatewayLogGroup.Arn

  # CloudWatch Alarm for High Failure Rate
  HighFailureRateAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub 'ADPA-High-Failure-Rate-${Environment}'
      AlarmDescription: 'Alarm when ADPA pipeline failure rate is high'
      MetricName: 'FailureCount'
      Namespace: 'AWS/Events'
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 2
      Threshold: 5
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref ADPAEventTopic

Outputs:
  EventBusArn:
    Description: 'ADPA EventBus ARN'
    Value: !GetAtt ADPAEventBus.Arn
    Export:
      Name: !Sub 'adpa-eventbus-arn-${Environment}'

  EventTopicArn:
    Description: 'ADPA Events SNS Topic ARN'
    Value: !Ref ADPAEventTopic
    Export:
      Name: !Sub 'adpa-events-topic-arn-${Environment}'

  PipelineSuccessLogGroup:
    Description: 'Pipeline Success Log Group'
    Value: !Ref PipelineSuccessLogGroup
    Export:
      Name: !Sub 'adpa-success-logs-${Environment}'

  PipelineFailureLogGroup:
    Description: 'Pipeline Failure Log Group'
    Value: !Ref PipelineFailureLogGroup
    Export:
      Name: !Sub 'adpa-failure-logs-${Environment}'
EOF

# Deploy EventBridge rules
print_status "Deploying EventBridge rules..."
aws cloudformation deploy \
    --template-file eventbridge_rules.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $REGION

if [ $? -eq 0 ]; then
    print_status "✅ EventBridge rules deployed successfully!"
    
    # Get outputs
    EVENT_BUS_ARN=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query "Stacks[0].Outputs[?OutputKey=='EventBusArn'].OutputValue" \
        --output text)
    
    print_status "EventBus ARN: $EVENT_BUS_ARN"
    
    # Test by sending a sample event
    print_status "Testing EventBridge integration..."
    
    aws events put-events \
        --entries Source=adpa.pipeline,DetailType="Pipeline Execution",Detail='{"status":"completed","pipeline_id":"test-123"}' \
        --event-bus-name "adpa-events-$ENVIRONMENT" \
        --region $REGION
    
    print_status "Test event sent successfully!"
    
else
    print_error "❌ EventBridge deployment failed"
    exit 1
fi

# Cleanup
rm -f eventbridge_rules.yaml

echo
echo "======================================"
echo "🎉 EVENTBRIDGE RULES COMPLETE! 🎉"
echo "======================================"
echo
print_status "EventBridge features implemented:"
echo "  ✅ Custom event bus for ADPA events"
echo "  ✅ Pipeline success/failure event capture"
echo "  ✅ Lambda function event monitoring"
echo "  ✅ API Gateway event logging"
echo "  ✅ Automated CloudWatch log routing"
echo "  ✅ SNS notifications for events"
echo "  ✅ CloudWatch alarms for failure rates"
echo
print_status "Event Bus: $EVENT_BUS_ARN"
echo
print_status "Your EventBridge logging rules are now active!"
echo