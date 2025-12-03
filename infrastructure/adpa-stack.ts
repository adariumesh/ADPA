import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as stepfunctions from 'aws-cdk-lib/aws-stepfunctions';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker';
import { Construct } from 'constructs';

export interface AdpaStackProps extends cdk.StackProps {
  environment: 'dev' | 'staging' | 'prod';
  projectName: string;
}

export class AdpaStack extends cdk.Stack {
  public readonly api: apigateway.RestApi;
  public readonly lambdaFunction: lambda.Function;
  public readonly pipelinesTable: dynamodb.Table;
  public readonly dataBucket: s3.Bucket;
  public readonly modelsBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: AdpaStackProps) {
    super(scope, id, props);

    const { environment, projectName } = props;
    const resourcePrefix = `${projectName}-${environment}`;

    // =================
    // S3 BUCKETS
    // =================
    this.dataBucket = new s3.Bucket(this, 'DataBucket', {
      bucketName: `${resourcePrefix}-data-${this.account}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      lifecycleRules: [
        {
          id: 'DeleteIncompleteMultipartUploads',
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(7),
        },
        {
          id: 'TransitionOldVersions',
          noncurrentVersionTransitions: [
            {
              storageClass: s3.StorageClass.INFREQUENT_ACCESS,
              transitionAfter: cdk.Duration.days(30),
            },
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(90),
            },
          ],
        },
      ],
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    this.modelsBucket = new s3.Bucket(this, 'ModelsBucket', {
      bucketName: `${resourcePrefix}-models-${this.account}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      lifecycleRules: [
        {
          id: 'ArchiveOldModels',
          transitions: [
            {
              storageClass: s3.StorageClass.INFREQUENT_ACCESS,
              transitionAfter: cdk.Duration.days(30),
            },
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(90),
            },
          ],
        },
      ],
      publicReadAccess: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    // =================
    // DYNAMODB TABLE
    // =================
    this.pipelinesTable = new dynamodb.Table(this, 'PipelinesTable', {
      tableName: `${resourcePrefix}-pipelines`,
      partitionKey: { name: 'pipeline_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.NUMBER },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: environment === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
    });

    // Add GSI for querying by status
    this.pipelinesTable.addGlobalSecondaryIndex({
      indexName: 'status-index',
      partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // =================
    // IAM ROLES
    // =================
    
    // Lambda Execution Role with least privilege
    const lambdaRole = new iam.Role(this, 'LambdaExecutionRole', {
      roleName: `${resourcePrefix}-lambda-execution-role`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
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
              resources: [
                this.pipelinesTable.tableArn,
                `${this.pipelinesTable.tableArn}/index/*`,
              ],
            }),
          ],
        }),
        S3Access: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                's3:GetObject',
                's3:PutObject',
                's3:DeleteObject',
                's3:ListBucket',
              ],
              resources: [
                this.dataBucket.bucketArn,
                `${this.dataBucket.bucketArn}/*`,
                this.modelsBucket.bucketArn,
                `${this.modelsBucket.bucketArn}/*`,
              ],
            }),
          ],
        }),
        StepFunctionsAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'states:StartExecution',
                'states:DescribeExecution',
                'states:StopExecution',
              ],
              resources: [`arn:aws:states:${this.region}:${this.account}:stateMachine:${resourcePrefix}-*`],
            }),
          ],
        }),
      },
    });

    // SageMaker Execution Role
    const sagemakerRole = new iam.Role(this, 'SageMakerExecutionRole', {
      roleName: `${resourcePrefix}-sagemaker-execution-role`,
      assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSageMakerFullAccess'),
      ],
      inlinePolicies: {
        S3ModelAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['s3:GetObject', 's3:PutObject'],
              resources: [
                `${this.dataBucket.bucketArn}/*`,
                `${this.modelsBucket.bucketArn}/*`,
              ],
            }),
          ],
        }),
      },
    });

    // Step Functions Execution Role
    const stepFunctionsRole = new iam.Role(this, 'StepFunctionsExecutionRole', {
      roleName: `${resourcePrefix}-stepfunctions-execution-role`,
      assumedBy: new iam.ServicePrincipal('states.amazonaws.com'),
      inlinePolicies: {
        LambdaInvoke: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['lambda:InvokeFunction'],
              resources: [`arn:aws:lambda:${this.region}:${this.account}:function:${resourcePrefix}-*`],
            }),
          ],
        }),
        SageMakerAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'sagemaker:CreateTrainingJob',
                'sagemaker:DescribeTrainingJob',
                'sagemaker:StopTrainingJob',
                'sagemaker:AddTags',
              ],
              resources: [`arn:aws:sagemaker:${this.region}:${this.account}:training-job/${resourcePrefix}-*`],
            }),
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['iam:PassRole'],
              resources: [sagemakerRole.roleArn],
            }),
          ],
        }),
        SNSPublish: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['sns:Publish'],
              resources: [`arn:aws:sns:${this.region}:${this.account}:${resourcePrefix}-*`],
            }),
          ],
        }),
      },
    });

    // =================
    // LAMBDA FUNCTION
    // =================
    this.lambdaFunction = new lambda.Function(this, 'ApiFunction', {
      functionName: `${resourcePrefix}-lambda-function`,
      runtime: lambda.Runtime.PYTHON_3_9,
      code: lambda.Code.fromAsset('../deploy'),
      handler: 'complete_api_handler.lambda_handler',
      role: lambdaRole,
      timeout: cdk.Duration.minutes(15),
      memorySize: 1024,
      environment: {
        DATA_BUCKET: this.dataBucket.bucketName,
        MODEL_BUCKET: this.modelsBucket.bucketName,
        PIPELINES_TABLE: this.pipelinesTable.tableName,
        ENVIRONMENT: environment,
        LOG_LEVEL: environment === 'prod' ? 'INFO' : 'DEBUG',
      },
      logRetention: logs.RetentionDays.TWO_WEEKS,
      tracing: lambda.Tracing.ACTIVE,
    });

    // =================
    // API GATEWAY
    // =================
    this.api = new apigateway.RestApi(this, 'AdpaApi', {
      restApiName: `${resourcePrefix}-api`,
      description: `ADPA Autonomous ML Pipeline API - ${environment}`,
      deployOptions: {
        stageName: environment,
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: environment === 'prod' ? ['https://yourdomain.com'] : apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'Authorization'],
      },
    });

    // Lambda Integration
    const lambdaIntegration = new apigateway.LambdaIntegration(this.lambdaFunction, {
      requestTemplates: { 'application/json': '{ "statusCode": "200" }' },
    });

    // Request Validator
    const requestValidator = new apigateway.RequestValidator(this, 'RequestValidator', {
      restApi: this.api,
      validateRequestBody: true,
      validateRequestParameters: true,
    });

    // API Gateway Resources and Methods
    const healthResource = this.api.root.addResource('health');
    healthResource.addMethod('GET', lambdaIntegration);

    const pipelinesResource = this.api.root.addResource('pipelines');
    
    // POST /pipelines with request validation
    pipelinesResource.addMethod('POST', lambdaIntegration, {
      requestValidator,
      requestModels: {
        'application/json': new apigateway.Model(this, 'CreatePipelineModel', {
          restApi: this.api,
          contentType: 'application/json',
          schema: {
            type: apigateway.JsonSchemaType.OBJECT,
            properties: {
              dataset_path: { type: apigateway.JsonSchemaType.STRING },
              objective: { type: apigateway.JsonSchemaType.STRING },
              config: { type: apigateway.JsonSchemaType.OBJECT },
            },
            required: ['dataset_path', 'objective'],
          },
        }),
      },
    });

    pipelinesResource.addMethod('GET', lambdaIntegration);

    const pipelineResource = pipelinesResource.addResource('{id}');
    pipelineResource.addMethod('GET', lambdaIntegration);

    const executeResource = pipelineResource.addResource('execute');
    executeResource.addMethod('POST', lambdaIntegration);

    const statusResource = pipelineResource.addResource('status');
    statusResource.addMethod('GET', lambdaIntegration);

    const dataResource = this.api.root.addResource('data');
    const uploadResource = dataResource.addResource('upload');
    uploadResource.addMethod('POST', lambdaIntegration);

    const uploadsResource = dataResource.addResource('uploads');
    uploadsResource.addMethod('GET', lambdaIntegration);

    // =================
    // SNS TOPIC
    // =================
    const notificationsTopic = new sns.Topic(this, 'NotificationsTopic', {
      topicName: `${resourcePrefix}-pipeline-notifications`,
      displayName: 'ADPA Pipeline Notifications',
    });

    // =================
    // CLOUDWATCH ALARMS
    // =================
    
    // Lambda Error Rate Alarm
    new cloudwatch.Alarm(this, 'LambdaErrorAlarm', {
      alarmName: `${resourcePrefix}-lambda-errors`,
      alarmDescription: 'Lambda function error rate is too high',
      metric: this.lambdaFunction.metricErrors({
        period: cdk.Duration.minutes(5),
      }),
      threshold: 5,
      evaluationPeriods: 2,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    // API Gateway 4XX Error Rate
    new cloudwatch.Alarm(this, 'ApiGateway4XXAlarm', {
      alarmName: `${resourcePrefix}-api-4xx-errors`,
      alarmDescription: 'API Gateway 4XX error rate is too high',
      metric: this.api.metricClientError({
        period: cdk.Duration.minutes(5),
      }),
      threshold: 20,
      evaluationPeriods: 2,
    });

    // DynamoDB Throttle Alarm
    new cloudwatch.Alarm(this, 'DynamoDBThrottleAlarm', {
      alarmName: `${resourcePrefix}-dynamodb-throttles`,
      alarmDescription: 'DynamoDB is being throttled',
      metric: this.pipelinesTable.metricThrottledRequests({
        period: cdk.Duration.minutes(5),
      }),
      threshold: 1,
      evaluationPeriods: 1,
    });

    // =================
    // OUTPUTS
    // =================
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: this.api.url,
      description: 'API Gateway URL',
    });

    new cdk.CfnOutput(this, 'DataBucketName', {
      value: this.dataBucket.bucketName,
      description: 'Data S3 Bucket Name',
    });

    new cdk.CfnOutput(this, 'ModelsBucketName', {
      value: this.modelsBucket.bucketName,
      description: 'Models S3 Bucket Name',
    });

    new cdk.CfnOutput(this, 'PipelinesTableName', {
      value: this.pipelinesTable.tableName,
      description: 'Pipelines DynamoDB Table Name',
    });

    new cdk.CfnOutput(this, 'LambdaFunctionName', {
      value: this.lambdaFunction.functionName,
      description: 'Lambda Function Name',
    });
  }
}