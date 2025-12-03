import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import { Construct } from 'constructs';

export class SimpleAdpaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const environment = 'prod';
    const resourcePrefix = `adpa-${environment}`;

    // S3 Buckets
    const dataBucket = new s3.Bucket(this, 'DataBucket', {
      bucketName: `${resourcePrefix}-data-${this.account}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    const modelsBucket = new s3.Bucket(this, 'ModelsBucket', {
      bucketName: `${resourcePrefix}-models-${this.account}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    // DynamoDB Table
    const pipelinesTable = new dynamodb.Table(this, 'PipelinesTable', {
      tableName: `${resourcePrefix}-pipelines`,
      partitionKey: { name: 'pipeline_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.NUMBER },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // IAM Role for Lambda
    const lambdaRole = new iam.Role(this, 'LambdaExecutionRole', {
      roleName: `${resourcePrefix}-lambda-execution-role`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess'),
      ],
      inlinePolicies: {
        DynamoDBAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'dynamodb:GetItem',
                'dynamodb:PutItem', 
                'dynamodb:UpdateItem',
                'dynamodb:DeleteItem',
                'dynamodb:Query',
                'dynamodb:Scan',
              ],
              resources: [pipelinesTable.tableArn, `${pipelinesTable.tableArn}/index/*`],
            }),
          ],
        }),
        S3Access: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['s3:GetObject', 's3:PutObject', 's3:DeleteObject', 's3:ListBucket'],
              resources: [
                dataBucket.bucketArn, `${dataBucket.bucketArn}/*`,
                modelsBucket.bucketArn, `${modelsBucket.bucketArn}/*`,
              ],
            }),
          ],
        }),
        StepFunctionsAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['states:StartExecution', 'states:DescribeExecution'],
              resources: [`arn:aws:states:${this.region}:${this.account}:stateMachine:${resourcePrefix}-*`],
            }),
          ],
        }),
      },
    });

    // Lambda Function
    const apiFunction = new lambda.Function(this, 'ApiFunction', {
      functionName: `${resourcePrefix}-lambda-function-v2`,
      runtime: lambda.Runtime.PYTHON_3_9,
      code: lambda.Code.fromAsset('../deploy', {
        exclude: ['local-baseline/**/*', '*.log', '**/*.log', '**/latest'],
      }),
      handler: 'complete_api_handler.lambda_handler',
      role: lambdaRole,
      timeout: cdk.Duration.minutes(15),
      memorySize: 1024,
      environment: {
        DATA_BUCKET: dataBucket.bucketName,
        MODEL_BUCKET: modelsBucket.bucketName,
        PIPELINES_TABLE: pipelinesTable.tableName,
        ENVIRONMENT: environment,
        STATE_MACHINE_ARN: `arn:aws:states:${this.region}:${this.account}:stateMachine:${resourcePrefix}-ml-pipeline-workflow`,
      },
      tracing: lambda.Tracing.ACTIVE,
    });

    // API Gateway
    const api = new apigateway.RestApi(this, 'AdpaApi', {
      restApiName: `${resourcePrefix}-api-v2`,
      description: 'ADPA Production API v2 - Enterprise Grade',
      deployOptions: {
        stageName: 'prod',
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'Authorization'],
      },
    });

    // Lambda Integration
    const lambdaIntegration = new apigateway.LambdaIntegration(apiFunction);

    // API Resources
    const healthResource = api.root.addResource('health');
    healthResource.addMethod('GET', lambdaIntegration);

    const pipelinesResource = api.root.addResource('pipelines');
    pipelinesResource.addMethod('GET', lambdaIntegration);
    pipelinesResource.addMethod('POST', lambdaIntegration);

    const pipelineResource = pipelinesResource.addResource('{id}');
    pipelineResource.addMethod('GET', lambdaIntegration);

    const executeResource = pipelineResource.addResource('execute');
    executeResource.addMethod('POST', lambdaIntegration);

    const statusResource = pipelineResource.addResource('status');
    statusResource.addMethod('GET', lambdaIntegration);

    const dataResource = api.root.addResource('data');
    const uploadResource = dataResource.addResource('upload');
    uploadResource.addMethod('POST', lambdaIntegration);

    const uploadsResource = dataResource.addResource('uploads');
    uploadsResource.addMethod('GET', lambdaIntegration);

    // CloudWatch Alarms
    new cloudwatch.Alarm(this, 'LambdaErrorAlarm', {
      alarmName: `${resourcePrefix}-lambda-errors`,
      alarmDescription: 'Lambda function error rate is too high',
      metric: apiFunction.metricErrors({
        period: cdk.Duration.minutes(5),
      }),
      threshold: 5,
      evaluationPeriods: 2,
    });

    new cloudwatch.Alarm(this, 'ApiGateway4XXAlarm', {
      alarmName: `${resourcePrefix}-api-4xx-errors`,
      alarmDescription: 'API Gateway 4XX error rate is too high',
      metric: api.metricClientError({
        period: cdk.Duration.minutes(5),
      }),
      threshold: 20,
      evaluationPeriods: 2,
    });

    // Outputs
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: api.url,
      description: 'Production API Gateway URL',
    });

    new cdk.CfnOutput(this, 'DataBucketName', {
      value: dataBucket.bucketName,
      description: 'Data S3 Bucket Name',
    });

    new cdk.CfnOutput(this, 'ModelsBucketName', {
      value: modelsBucket.bucketName,
      description: 'Models S3 Bucket Name', 
    });

    new cdk.CfnOutput(this, 'PipelinesTableName', {
      value: pipelinesTable.tableName,
      description: 'Pipelines DynamoDB Table Name',
    });

    new cdk.CfnOutput(this, 'LambdaFunctionName', {
      value: apiFunction.functionName,
      description: 'Lambda Function Name',
    });
  }
}