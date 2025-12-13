"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AdpaStack = void 0;
const cdk = require("aws-cdk-lib");
const lambda = require("aws-cdk-lib/aws-lambda");
const apigateway = require("aws-cdk-lib/aws-apigateway");
const dynamodb = require("aws-cdk-lib/aws-dynamodb");
const s3 = require("aws-cdk-lib/aws-s3");
const iam = require("aws-cdk-lib/aws-iam");
const logs = require("aws-cdk-lib/aws-logs");
const cloudwatch = require("aws-cdk-lib/aws-cloudwatch");
const sns = require("aws-cdk-lib/aws-sns");
class AdpaStack extends cdk.Stack {
    constructor(scope, id, props) {
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
                                'states:CreateStateMachine',
                                'states:DeleteStateMachine',
                                'states:UpdateStateMachine',
                                'states:ListStateMachines',
                                'states:TagResource',
                                'states:UntagResource',
                                'states:ListActivities',
                            ],
                            resources: ['*'],
                        }),
                        new iam.PolicyStatement({
                            effect: iam.Effect.ALLOW,
                            actions: [
                                'states:StartExecution',
                                'states:StopExecution',
                                'states:DescribeExecution',
                                'states:GetExecutionHistory',
                                'states:ListExecutions',
                                'states:DescribeStateMachine',
                                'states:DescribeStateMachineForExecution',
                            ],
                            resources: [
                                `arn:aws:states:${this.region}:${this.account}:stateMachine:${resourcePrefix}-*`,
                                `arn:aws:states:${this.region}:${this.account}:stateMachine:adpa-*`,
                                `arn:aws:states:${this.region}:${this.account}:execution:${resourcePrefix}-*:*`,
                                `arn:aws:states:${this.region}:${this.account}:execution:adpa-*:*`,
                            ],
                        }),
                    ],
                }),
                CloudWatchLogsTagging: new iam.PolicyDocument({
                    statements: [
                        new iam.PolicyStatement({
                            effect: iam.Effect.ALLOW,
                            actions: [
                                'logs:CreateLogGroup',
                                'logs:TagResource',
                                'logs:PutRetentionPolicy',
                            ],
                            resources: [
                                `arn:aws:logs:${this.region}:${this.account}:log-group:*`,
                            ],
                        }),
                    ],
                }),
                GlueAccess: new iam.PolicyDocument({
                    statements: [
                        new iam.PolicyStatement({
                            effect: iam.Effect.ALLOW,
                            actions: [
                                'glue:CreateDatabase',
                                'glue:GetDatabase',
                                'glue:GetDatabases',
                                'glue:CreateTable',
                                'glue:GetTable',
                                'glue:GetTables',
                                'glue:CreateCrawler',
                                'glue:UpdateCrawler',
                                'glue:GetCrawler',
                                'glue:GetCrawlers',
                                'glue:StartCrawler',
                                'glue:DeleteCrawler',
                                'glue:CreateJob',
                                'glue:UpdateJob',
                                'glue:GetJob',
                                'glue:GetJobs',
                                'glue:StartJobRun',
                                'glue:GetJobRun',
                                'glue:GetJobRuns',
                                'glue:BatchStopJobRun',
                            ],
                            resources: ['*'],
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
        lambdaRole.addToPrincipalPolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['iam:PassRole'],
            resources: [stepFunctionsRole.roleArn],
        }));
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
exports.AdpaStack = AdpaStack;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiYWRwYS1zdGFjay5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbImFkcGEtc3RhY2sudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7O0FBQUEsbUNBQW1DO0FBQ25DLGlEQUFpRDtBQUNqRCx5REFBeUQ7QUFDekQscURBQXFEO0FBQ3JELHlDQUF5QztBQUN6QywyQ0FBMkM7QUFFM0MsNkNBQTZDO0FBQzdDLHlEQUF5RDtBQUN6RCwyQ0FBMkM7QUFTM0MsTUFBYSxTQUFVLFNBQVEsR0FBRyxDQUFDLEtBQUs7SUFPdEMsWUFBWSxLQUFnQixFQUFFLEVBQVUsRUFBRSxLQUFxQjtRQUM3RCxLQUFLLENBQUMsS0FBSyxFQUFFLEVBQUUsRUFBRSxLQUFLLENBQUMsQ0FBQztRQUV4QixNQUFNLEVBQUUsV0FBVyxFQUFFLFdBQVcsRUFBRSxHQUFHLEtBQUssQ0FBQztRQUMzQyxNQUFNLGNBQWMsR0FBRyxHQUFHLFdBQVcsSUFBSSxXQUFXLEVBQUUsQ0FBQztRQUV2RCxvQkFBb0I7UUFDcEIsYUFBYTtRQUNiLG9CQUFvQjtRQUNwQixJQUFJLENBQUMsVUFBVSxHQUFHLElBQUksRUFBRSxDQUFDLE1BQU0sQ0FBQyxJQUFJLEVBQUUsWUFBWSxFQUFFO1lBQ2xELFVBQVUsRUFBRSxHQUFHLGNBQWMsU0FBUyxJQUFJLENBQUMsT0FBTyxFQUFFO1lBQ3BELFNBQVMsRUFBRSxJQUFJO1lBQ2YsVUFBVSxFQUFFLEVBQUUsQ0FBQyxnQkFBZ0IsQ0FBQyxVQUFVO1lBQzFDLGNBQWMsRUFBRTtnQkFDZDtvQkFDRSxFQUFFLEVBQUUsa0NBQWtDO29CQUN0QyxtQ0FBbUMsRUFBRSxHQUFHLENBQUMsUUFBUSxDQUFDLElBQUksQ0FBQyxDQUFDLENBQUM7aUJBQzFEO2dCQUNEO29CQUNFLEVBQUUsRUFBRSx1QkFBdUI7b0JBQzNCLDRCQUE0QixFQUFFO3dCQUM1Qjs0QkFDRSxZQUFZLEVBQUUsRUFBRSxDQUFDLFlBQVksQ0FBQyxpQkFBaUI7NEJBQy9DLGVBQWUsRUFBRSxHQUFH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QyxDQUFDO1FBRUgsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxrQkFBa0IsRUFBRTtZQUMxQyxLQUFLLEVBQUUsSUFBSSxDQUFDLFlBQVksQ0FBQyxVQUFVO1lBQ25DLFdBQVcsRUFBRSx1QkFBdUI7U0FDckMsQ0FBQyxDQUFDO1FBRUgsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxvQkFBb0IsRUFBRTtZQUM1QyxLQUFLLEVBQUUsSUFBSSxDQUFDLGNBQWMsQ0FBQyxTQUFTO1lBQ3BDLFdBQVcsRUFBRSwrQkFBK0I7U0FDN0MsQ0FBQyxDQUFDO1FBRUgsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxvQkFBb0IsRUFBRTtZQUM1QyxLQUFLLEVBQUUsSUFBSSxDQUFDLGNBQWMsQ0FBQyxZQUFZO1lBQ3ZDLFdBQVcsRUFBRSxzQkFBc0I7U0FDcEMsQ0FBQyxDQUFDO0lBQ0wsQ0FBQztDQUNGO0FBbGRELDhCQWtkQyIsInNvdXJjZXNDb250ZW50IjpbImltcG9ydCAqIGFzIGNkayBmcm9tICdhd3MtY2RrLWxpYic7XG5pbXBvcnQgKiBhcyBsYW1iZGEgZnJvbSAnYXdzLWNkay1saWIvYXdzLWxhbWJkYSc7XG5pbXBvcnQgKiBhcyBhcGlnYXRld2F5IGZyb20gJ2F3cy1jZGstbGliL2F3cy1hcGlnYXRld2F5JztcbmltcG9ydCAqIGFzIGR5bmFtb2RiIGZyb20gJ2F3cy1jZGstbGliL2F3cy1keW5hbW9kYic7XG5pbXBvcnQgKiBhcyBzMyBmcm9tICdhd3MtY2RrLWxpYi9hd3MtczMnO1xuaW1wb3J0ICogYXMgaWFtIGZyb20gJ2F3cy1jZGstbGliL2F3cy1pYW0nO1xuaW1wb3J0ICogYXMgc3RlcGZ1bmN0aW9ucyBmcm9tICdhd3MtY2RrLWxpYi9hd3Mtc3RlcGZ1bmN0aW9ucyc7XG5pbXBvcnQgKiBhcyBsb2dzIGZyb20gJ2F3cy1jZGstbGliL2F3cy1sb2dzJztcbmltcG9ydCAqIGFzIGNsb3Vkd2F0Y2ggZnJvbSAnYXdzLWNkay1saWIvYXdzLWNsb3Vkd2F0Y2gnO1xuaW1wb3J0ICogYXMgc25zIGZyb20gJ2F3cy1jZGstbGliL2F3cy1zbnMnO1xuaW1wb3J0ICogYXMgc2FnZW1ha2VyIGZyb20gJ2F3cy1jZGstbGliL2F3cy1zYWdlbWFrZXInO1xuaW1wb3J0IHsgQ29uc3RydWN0IH0gZnJvbSAnY29uc3RydWN0cyc7XG5cbmV4cG9ydCBpbnRlcmZhY2UgQWRwYVN0YWNrUHJvcHMgZXh0ZW5kcyBjZGsuU3RhY2tQcm9wcyB7XG4gIGVudmlyb25tZW50OiAnZGV2JyB8ICdzdGFnaW5nJyB8ICdwcm9kJztcbiAgcHJvamVjdE5hbWU6IHN0cmluZztcbn1cblxuZXhwb3J0IGNsYXNzIEFkcGFTdGFjayBleHRlbmRzIGNkay5TdGFjayB7XG4gIHB1YmxpYyByZWFkb25seSBhcGk6IGFwaWdhdGV3YXkuUmVzdEFwaTtcbiAgcHVibGljIHJlYWRvbmx5IGxhbWJkYUZ1bmN0aW9uOiBsYW1iZGEuRnVuY3Rpb247XG4gIHB1YmxpYyByZWFkb25seSBwaXBlbGluZXNUYWJsZTogZHluYW1vZGIuVGFibGU7XG4gIHB1YmxpYyByZWFkb25seSBkYXRhQnVja2V0OiBzMy5CdWNrZXQ7XG4gIHB1YmxpYyByZWFkb25seSBtb2RlbHNCdWNrZXQ6IHMzLkJ1Y2tldDtcblxuICBjb25zdHJ1Y3RvcihzY29wZTogQ29uc3RydWN0LCBpZDogc3RyaW5nLCBwcm9wczogQWRwYVN0YWNrUHJvcHMpIHtcbiAgICBzdXBlcihzY29wZSwgaWQsIHByb3BzKTtcblxuICAgIGNvbnN0IHsgZW52aXJvbm1lbnQsIHByb2plY3ROYW1lIH0gPSBwcm9wcztcbiAgICBjb25zdCByZXNvdXJjZVByZWZpeCA9IGAke3Byb2plY3ROYW1lfS0ke2Vudmlyb25tZW50fWA7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIFMzIEJVQ0tFVFNcbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIHRoaXMuZGF0YUJ1Y2tldCA9IG5ldyBzMy5CdWNrZXQodGhpcywgJ0RhdGFCdWNrZXQnLCB7XG4gICAgICBidWNrZXROYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tZGF0YS0ke3RoaXMuYWNjb3VudH1gLFxuICAgICAgdmVyc2lvbmVkOiB0cnVlLFxuICAgICAgZW5jcnlwdGlvbjogczMuQnVja2V0RW5jcnlwdGlvbi5TM19NQU5BR0VELFxuICAgICAgbGlmZWN5Y2xlUnVsZXM6IFtcbiAgICAgICAge1xuICAgICAgICAgIGlkOiAnRGVsZXRlSW5jb21wbGV0ZU11bHRpcGFydFVwbG9hZHMnLFxuICAgICAgICAgIGFib3J0SW5jb21wbGV0ZU11bHRpcGFydFVwbG9hZEFmdGVyOiBjZGsuRHVyYXRpb24uZGF5cyg3KSxcbiAgICAgICAgfSxcbiAgICAgICAge1xuICAgICAgICAgIGlkOiAnVHJhbnNpdGlvbk9sZFZlcnNpb25zJyxcbiAgICAgICAgICBub25jdXJyZW50VmVyc2lvblRyYW5zaXRpb25zOiBbXG4gICAgICAgICAgICB7XG4gICAgICAgICAgICAgIHN0b3JhZ2VDbGFzczogczMuU3RvcmFnZUNsYXNzLklORlJFUVVFTlRfQUNDRVNTLFxuICAgICAgICAgICAgICB0cmFuc2l0aW9uQWZ0ZXI6IGNkay5EdXJhdGlvbi5kYXlzKDMwKSxcbiAgICAgICAgICAgIH0sXG4gICAgICAgICAgICB7XG4gICAgICAgICAgICAgIHN0b3JhZ2VDbGFzczogczMuU3RvcmFnZUNsYXNzLkdMQUNJRVIsXG4gICAgICAgICAgICAgIHRyYW5zaXRpb25BZnRlcjogY2RrLkR1cmF0aW9uLmRheXMoOTApLFxuICAgICAgICAgICAgfSxcbiAgICAgICAgICBdLFxuICAgICAgICB9LFxuICAgICAgXSxcbiAgICAgIHB1YmxpY1JlYWRBY2Nlc3M6IGZhbHNlLFxuICAgICAgYmxvY2tQdWJsaWNBY2Nlc3M6IHMzLkJsb2NrUHVibGljQWNjZXNzLkJMT0NLX0FMTCxcbiAgICB9KTtcblxuICAgIHRoaXMubW9kZWxzQnVja2V0ID0gbmV3IHMzLkJ1Y2tldCh0aGlzLCAnTW9kZWxzQnVja2V0Jywge1xuICAgICAgYnVja2V0TmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LW1vZGVscy0ke3RoaXMuYWNjb3VudH1gLFxuICAgICAgdmVyc2lvbmVkOiB0cnVlLFxuICAgICAgZW5jcnlwdGlvbjogczMuQnVja2V0RW5jcnlwdGlvbi5TM19NQU5BR0VELFxuICAgICAgbGlmZWN5Y2xlUnVsZXM6IFtcbiAgICAgICAge1xuICAgICAgICAgIGlkOiAnQXJjaGl2ZU9sZE1vZGVscycsXG4gICAgICAgICAgdHJhbnNpdGlvbnM6IFtcbiAgICAgICAgICAgIHtcbiAgICAgICAgICAgICAgc3RvcmFnZUNsYXNzOiBzMy5TdG9yYWdlQ2xhc3MuSU5GUkVRVUVOVF9BQ0NFU1MsXG4gICAgICAgICAgICAgIHRyYW5zaXRpb25BZnRlcjogY2RrLkR1cmF0aW9uLmRheXMoMzApLFxuICAgICAgICAgICAgfSxcbiAgICAgICAgICAgIHtcbiAgICAgICAgICAgICAgc3RvcmFnZUNsYXNzOiBzMy5TdG9yYWdlQ2xhc3MuR0xBQ0lFUixcbiAgICAgICAgICAgICAgdHJhbnNpdGlvbkFmdGVyOiBjZGsuRHVyYXRpb24uZGF5cyg5MCksXG4gICAgICAgICAgICB9LFxuICAgICAgICAgIF0sXG4gICAgICAgIH0sXG4gICAgICBdLFxuICAgICAgcHVibGljUmVhZEFjY2VzczogZmFsc2UsXG4gICAgICBibG9ja1B1YmxpY0FjY2VzczogczMuQmxvY2tQdWJsaWNBY2Nlc3MuQkxPQ0tfQUxMLFxuICAgIH0pO1xuXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cbiAgICAvLyBEWU5BTU9EQiBUQUJMRVxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgdGhpcy5waXBlbGluZXNUYWJsZSA9IG5ldyBkeW5hbW9kYi5UYWJsZSh0aGlzLCAnUGlwZWxpbmVzVGFibGUnLCB7XG4gICAgICB0YWJsZU5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1waXBlbGluZXNgLFxuICAgICAgcGFydGl0aW9uS2V5OiB7IG5hbWU6ICdwaXBlbGluZV9pZCcsIHR5cGU6IGR5bmFtb2RiLkF0dHJpYnV0ZVR5cGUuU1RSSU5HIH0sXG4gICAgICBzb3J0S2V5OiB7IG5hbWU6ICd0aW1lc3RhbXAnLCB0eXBlOiBkeW5hbW9kYi5BdHRyaWJ1dGVUeXBlLk5VTUJFUiB9LFxuICAgICAgYmlsbGluZ01vZGU6IGR5bmFtb2RiLkJpbGxpbmdNb2RlLlBBWV9QRVJfUkVRVUVTVCxcbiAgICAgIGVuY3J5cHRpb246IGR5bmFtb2RiLlRhYmxlRW5jcnlwdGlvbi5BV1NfTUFOQUdFRCxcbiAgICAgIHBvaW50SW5UaW1lUmVjb3Zlcnk6IHRydWUsXG4gICAgICByZW1vdmFsUG9saWN5OiBlbnZpcm9ubWVudCA9PT0gJ3Byb2QnID8gY2RrLlJlbW92YWxQb2xpY3kuUkVUQUlOIDogY2RrLlJlbW92YWxQb2xpY3kuREVTVFJPWSxcbiAgICAgIHN0cmVhbTogZHluYW1vZGIuU3RyZWFtVmlld1R5cGUuTkVXX0FORF9PTERfSU1BR0VTLFxuICAgIH0pO1xuXG4gICAgLy8gQWRkIEdTSSBmb3IgcXVlcnlpbmcgYnkgc3RhdHVzXG4gICAgdGhpcy5waXBlbGluZXNUYWJsZS5hZGRHbG9iYWxTZWNvbmRhcnlJbmRleCh7XG4gICAgICBpbmRleE5hbWU6ICdzdGF0dXMtaW5kZXgnLFxuICAgICAgcGFydGl0aW9uS2V5OiB7IG5hbWU6ICdzdGF0dXMnLCB0eXBlOiBkeW5hbW9kYi5BdHRyaWJ1dGVUeXBlLlNUUklORyB9LFxuICAgICAgc29ydEtleTogeyBuYW1lOiAnY3JlYXRlZF9hdCcsIHR5cGU6IGR5bmFtb2RiLkF0dHJpYnV0ZVR5cGUuU1RSSU5HIH0sXG4gICAgICBwcm9qZWN0aW9uVHlwZTogZHluYW1vZGIuUHJvamVjdGlvblR5cGUuQUxMLFxuICAgIH0pO1xuXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cbiAgICAvLyBJQU0gUk9MRVNcbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIFxuICAgIC8vIExhbWJkYSBFeGVjdXRpb24gUm9sZSB3aXRoIGxlYXN0IHByaXZpbGVnZVxuICAgIGNvbnN0IGxhbWJkYVJvbGUgPSBuZXcgaWFtLlJvbGUodGhpcywgJ0xhbWJkYUV4ZWN1dGlvblJvbGUnLCB7XG4gICAgICByb2xlTmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LWxhbWJkYS1leGVjdXRpb24tcm9sZWAsXG4gICAgICBhc3N1bWVkQnk6IG5ldyBpYW0uU2VydmljZVByaW5jaXBhbCgnbGFtYmRhLmFtYXpvbmF3cy5jb20nKSxcbiAgICAgIG1hbmFnZWRQb2xpY2llczogW1xuICAgICAgICBpYW0uTWFuYWdlZFBvbGljeS5mcm9tQXdzTWFuYWdlZFBvbGljeU5hbWUoJ3NlcnZpY2Utcm9sZS9BV1NMYW1iZGFCYXNpY0V4ZWN1dGlvblJvbGUnKSxcbiAgICAgIF0sXG4gICAgICBpbmxpbmVQb2xpY2llczoge1xuICAgICAgICBEeW5hbW9EQkFjY2VzczogbmV3IGlhbS5Qb2xpY3lEb2N1bWVudCh7XG4gICAgICAgICAgc3RhdGVtZW50czogW1xuICAgICAgICAgICAgbmV3IGlhbS5Qb2xpY3lTdGF0ZW1lbnQoe1xuICAgICAgICAgICAgICBlZmZlY3Q6IGlhbS5FZmZlY3QuQUxMT1csXG4gICAgICAgICAgICAgIGFjdGlvbnM6IFtcbiAgICAgICAgICAgICAgICAnZHluYW1vZGI6R2V0SXRlbScsXG4gICAgICAgICAgICAgICAgJ2R5bmFtb2RiOlB1dEl0ZW0nLFxuICAgICAgICAgICAgICAgICdkeW5hbW9kYjpVcGRhdGVJdGVtJyxcbiAgICAgICAgICAgICAgICAnZHluYW1vZGI6RGVsZXRlSXRlbScsXG4gICAgICAgICAgICAgICAgJ2R5bmFtb2RiOlF1ZXJ5JyxcbiAgICAgICAgICAgICAgICAnZHluYW1vZGI6U2NhbicsXG4gICAgICAgICAgICAgIF0sXG4gICAgICAgICAgICAgIHJlc291cmNlczogW1xuICAgICAgICAgICAgICAgIHRoaXMucGlwZWxpbmVzVGFibGUudGFibGVBcm4sXG4gICAgICAgICAgICAgICAgYCR7dGhpcy5waXBlbGluZXNUYWJsZS50YWJsZUFybn0vaW5kZXgvKmAsXG4gICAgICAgICAgICAgIF0sXG4gICAgICAgICAgICB9KSxcbiAgICAgICAgICBdLFxuICAgICAgICB9KSxcbiAgICAgICAgUzNBY2Nlc3M6IG5ldyBpYW0uUG9saWN5RG9jdW1lbnQoe1xuICAgICAgICAgIHN0YXRlbWVudHM6IFtcbiAgICAgICAgICAgIG5ldyBpYW0uUG9saWN5U3RhdGVtZW50KHtcbiAgICAgICAgICAgICAgZWZmZWN0OiBpYW0uRWZmZWN0LkFMTE9XLFxuICAgICAgICAgICAgICBhY3Rpb25zOiBbXG4gICAgICAgICAgICAgICAgJ3MzOkdldE9iamVjdCcsXG4gICAgICAgICAgICAgICAgJ3MzOlB1dE9iamVjdCcsXG4gICAgICAgICAgICAgICAgJ3MzOkRlbGV0ZU9iamVjdCcsXG4gICAgICAgICAgICAgICAgJ3MzOkxpc3RCdWNrZXQnLFxuICAgICAgICAgICAgICBdLFxuICAgICAgICAgICAgICByZXNvdXJjZXM6IFtcbiAgICAgICAgICAgICAgICB0aGlzLmRhdGFCdWNrZXQuYnVja2V0QXJuLFxuICAgICAgICAgICAgICAgIGAke3RoaXMuZGF0YUJ1Y2tldC5idWNrZXRBcm59LypgLFxuICAgICAgICAgICAgICAgIHRoaXMubW9kZWxzQnVja2V0LmJ1Y2tldEFybixcbiAgICAgICAgICAgICAgICBgJHt0aGlzLm1vZGVsc0J1Y2tldC5idWNrZXRBcm59LypgLFxuICAgICAgICAgICAgICBdLFxuICAgICAgICAgICAgfSksXG4gICAgICAgICAgXSxcbiAgICAgICAgfSksXG4gICAgICAgIFN0ZXBGdW5jdGlvbnNBY2Nlc3M6IG5ldyBpYW0uUG9saWN5RG9jdW1lbnQoe1xuICAgICAgICAgIHN0YXRlbWVudHM6IFtcbiAgICAgICAgICAgIG5ldyBpYW0uUG9saWN5U3RhdGVtZW50KHtcbiAgICAgICAgICAgICAgZWZmZWN0OiBpYW0uRWZmZWN0LkFMTE9XLFxuICAgICAgICAgICAgICBhY3Rpb25zOiBbXG4gICAgICAgICAgICAgICAgJ3N0YXRlczpDcmVhdGVTdGF0ZU1hY2hpbmUnLFxuICAgICAgICAgICAgICAgICdzdGF0ZXM6RGVsZXRlU3RhdGVNYWNoaW5lJyxcbiAgICAgICAgICAgICAgICAnc3RhdGVzOlVwZGF0ZVN0YXRlTWFjaGluZScsXG4gICAgICAgICAgICAgICAgJ3N0YXRlczpMaXN0U3RhdGVNYWNoaW5lcycsXG4gICAgICAgICAgICAgICAgJ3N0YXRlczpUYWdSZXNvdXJjZScsXG4gICAgICAgICAgICAgICAgJ3N0YXRlczpVbnRhZ1Jlc291cmNlJyxcbiAgICAgICAgICAgICAgICAnc3RhdGVzOkxpc3RBY3Rpdml0aWVzJyxcbiAgICAgICAgICAgICAgXSxcbiAgICAgICAgICAgICAgcmVzb3VyY2VzOiBbJyonXSxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgICAgbmV3IGlhbS5Qb2xpY3lTdGF0ZW1lbnQoe1xuICAgICAgICAgICAgICBlZmZlY3Q6IGlhbS5FZmZlY3QuQUxMT1csXG4gICAgICAgICAgICAgIGFjdGlvbnM6IFtcbiAgICAgICAgICAgICAgICAnc3RhdGVzOlN0YXJ0RXhlY3V0aW9uJyxcbiAgICAgICAgICAgICAgICAnc3RhdGVzOlN0b3BFeGVjdXRpb24nLFxuICAgICAgICAgICAgICAgICdzdGF0ZXM6RGVzY3JpYmVFeGVjdXRpb24nLFxuICAgICAgICAgICAgICAgICdzdGF0ZXM6R2V0RXhlY3V0aW9uSGlzdG9yeScsXG4gICAgICAgICAgICAgICAgJ3N0YXRlczpMaXN0RXhlY3V0aW9ucycsXG4gICAgICAgICAgICAgICAgJ3N0YXRlczpEZXNjcmliZVN0YXRlTWFjaGluZScsXG4gICAgICAgICAgICAgICAgJ3N0YXRlczpEZXNjcmliZVN0YXRlTWFjaGluZUZvckV4ZWN1dGlvbicsXG4gICAgICAgICAgICAgIF0sXG4gICAgICAgICAgICAgIHJlc291cmNlczogW1xuICAgICAgICAgICAgICAgIGBhcm46YXdzOnN0YXRlczoke3RoaXMucmVnaW9ufToke3RoaXMuYWNjb3VudH06c3RhdGVNYWNoaW5lOiR7cmVzb3VyY2VQcmVmaXh9LSpgLFxuICAgICAgICAgICAgICAgIGBhcm46YXdzOnN0YXRlczoke3RoaXMucmVnaW9ufToke3RoaXMuYWNjb3VudH06c3RhdGVNYWNoaW5lOmFkcGEtKmAsXG4gICAgICAgICAgICAgICAgYGFybjphd3M6c3RhdGVzOiR7dGhpcy5yZWdpb259OiR7dGhpcy5hY2NvdW50fTpleGVjdXRpb246JHtyZXNvdXJjZVByZWZpeH0tKjoqYCxcbiAgICAgICAgICAgICAgICBgYXJuOmF3czpzdGF0ZXM6JHt0aGlzLnJlZ2lvbn06JHt0aGlzLmFjY291bnR9OmV4ZWN1dGlvbjphZHBhLSo6KmAsXG4gICAgICAgICAgICAgIF0sXG4gICAgICAgICAgICB9KSxcbiAgICAgICAgICBdLFxuICAgICAgICB9KSxcbiAgICAgICAgQ2xvdWRXYXRjaExvZ3NUYWdnaW5nOiBuZXcgaWFtLlBvbGljeURvY3VtZW50KHtcbiAgICAgICAgICBzdGF0ZW1lbnRzOiBbXG4gICAgICAgICAgICBuZXcgaWFtLlBvbGljeVN0YXRlbWVudCh7XG4gICAgICAgICAgICAgIGVmZmVjdDogaWFtLkVmZmVjdC5BTExPVyxcbiAgICAgICAgICAgICAgYWN0aW9uczogW1xuICAgICAgICAgICAgICAgICdsb2dzOkNyZWF0ZUxvZ0dyb3VwJyxcbiAgICAgICAgICAgICAgICAnbG9nczpUYWdSZXNvdXJjZScsXG4gICAgICAgICAgICAgICAgJ2xvZ3M6UHV0UmV0ZW50aW9uUG9saWN5JyxcbiAgICAgICAgICAgICAgXSxcbiAgICAgICAgICAgICAgcmVzb3VyY2VzOiBbXG4gICAgICAgICAgICAgICAgYGFybjphd3M6bG9nczoke3RoaXMucmVnaW9ufToke3RoaXMuYWNjb3VudH06bG9nLWdyb3VwOipgLFxuICAgICAgICAgICAgICBdLFxuICAgICAgICAgICAgfSksXG4gICAgICAgICAgXSxcbiAgICAgICAgfSksXG4gICAgICAgIEdsdWVBY2Nlc3M6IG5ldyBpYW0uUG9saWN5RG9jdW1lbnQoe1xuICAgICAgICAgIHN0YXRlbWVudHM6IFtcbiAgICAgICAgICAgIG5ldyBpYW0uUG9saWN5U3RhdGVtZW50KHtcbiAgICAgICAgICAgICAgZWZmZWN0OiBpYW0uRWZmZWN0LkFMTE9XLFxuICAgICAgICAgICAgICBhY3Rpb25zOiBbXG4gICAgICAgICAgICAgICAgJ2dsdWU6Q3JlYXRlRGF0YWJhc2UnLFxuICAgICAgICAgICAgICAgICdnbHVlOkdldERhdGFiYXNlJyxcbiAgICAgICAgICAgICAgICAnZ2x1ZTpHZXREYXRhYmFzZXMnLFxuICAgICAgICAgICAgICAgICdnbHVlOkNyZWF0ZVRhYmxlJyxcbiAgICAgICAgICAgICAgICAnZ2x1ZTpHZXRUYWJsZScsXG4gICAgICAgICAgICAgICAgJ2dsdWU6R2V0VGFibGVzJyxcbiAgICAgICAgICAgICAgICAnZ2x1ZTpDcmVhdGVDcmF3bGVyJyxcbiAgICAgICAgICAgICAgICAnZ2x1ZTpVcGRhdGVDcmF3bGVyJyxcbiAgICAgICAgICAgICAgICAnZ2x1ZTpHZXRDcmF3bGVyJyxcbiAgICAgICAgICAgICAgICAnZ2x1ZTpHZXRDcmF3bGVycycsXG4gICAgICAgICAgICAgICAgJ2dsdWU6U3RhcnRDcmF3bGVyJyxcbiAgICAgICAgICAgICAgICAnZ2x1ZTpEZWxldGVDcmF3bGVyJyxcbiAgICAgICAgICAgICAgICAnZ2x1ZTpDcmVhdGVKb2InLFxuICAgICAgICAgICAgICAgICdnbHVlOlVwZGF0ZUpvYicsXG4gICAgICAgICAgICAgICAgJ2dsdWU6R2V0Sm9iJyxcbiAgICAgICAgICAgICAgICAnZ2x1ZTpHZXRKb2JzJyxcbiAgICAgICAgICAgICAgICAnZ2x1ZTpTdGFydEpvYlJ1bicsXG4gICAgICAgICAgICAgICAgJ2dsdWU6R2V0Sm9iUnVuJyxcbiAgICAgICAgICAgICAgICAnZ2x1ZTpHZXRKb2JSdW5zJyxcbiAgICAgICAgICAgICAgICAnZ2x1ZTpCYXRjaFN0b3BKb2JSdW4nLFxuICAgICAgICAgICAgICBdLFxuICAgICAgICAgICAgICByZXNvdXJjZXM6IFsnKiddLFxuICAgICAgICAgICAgfSksXG4gICAgICAgICAgXSxcbiAgICAgICAgfSksXG4gICAgICB9LFxuICAgIH0pO1xuXG4gICAgLy8gU2FnZU1ha2VyIEV4ZWN1dGlvbiBSb2xlXG4gICAgY29uc3Qgc2FnZW1ha2VyUm9sZSA9IG5ldyBpYW0uUm9sZSh0aGlzLCAnU2FnZU1ha2VyRXhlY3V0aW9uUm9sZScsIHtcbiAgICAgIHJvbGVOYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tc2FnZW1ha2VyLWV4ZWN1dGlvbi1yb2xlYCxcbiAgICAgIGFzc3VtZWRCeTogbmV3IGlhbS5TZXJ2aWNlUHJpbmNpcGFsKCdzYWdlbWFrZXIuYW1hem9uYXdzLmNvbScpLFxuICAgICAgbWFuYWdlZFBvbGljaWVzOiBbXG4gICAgICAgIGlhbS5NYW5hZ2VkUG9saWN5LmZyb21Bd3NNYW5hZ2VkUG9saWN5TmFtZSgnQW1hem9uU2FnZU1ha2VyRnVsbEFjY2VzcycpLFxuICAgICAgXSxcbiAgICAgIGlubGluZVBvbGljaWVzOiB7XG4gICAgICAgIFMzTW9kZWxBY2Nlc3M6IG5ldyBpYW0uUG9saWN5RG9jdW1lbnQoe1xuICAgICAgICAgIHN0YXRlbWVudHM6IFtcbiAgICAgICAgICAgIG5ldyBpYW0uUG9saWN5U3RhdGVtZW50KHtcbiAgICAgICAgICAgICAgZWZmZWN0OiBpYW0uRWZmZWN0LkFMTE9XLFxuICAgICAgICAgICAgICBhY3Rpb25zOiBbJ3MzOkdldE9iamVjdCcsICdzMzpQdXRPYmplY3QnXSxcbiAgICAgICAgICAgICAgcmVzb3VyY2VzOiBbXG4gICAgICAgICAgICAgICAgYCR7dGhpcy5kYXRhQnVja2V0LmJ1Y2tldEFybn0vKmAsXG4gICAgICAgICAgICAgICAgYCR7dGhpcy5tb2RlbHNCdWNrZXQuYnVja2V0QXJufS8qYCxcbiAgICAgICAgICAgICAgXSxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgIF0sXG4gICAgICAgIH0pLFxuICAgICAgfSxcbiAgICB9KTtcblxuICAgIC8vIFN0ZXAgRnVuY3Rpb25zIEV4ZWN1dGlvbiBSb2xlXG4gICAgY29uc3Qgc3RlcEZ1bmN0aW9uc1JvbGUgPSBuZXcgaWFtLlJvbGUodGhpcywgJ1N0ZXBGdW5jdGlvbnNFeGVjdXRpb25Sb2xlJywge1xuICAgICAgcm9sZU5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1zdGVwZnVuY3Rpb25zLWV4ZWN1dGlvbi1yb2xlYCxcbiAgICAgIGFzc3VtZWRCeTogbmV3IGlhbS5TZXJ2aWNlUHJpbmNpcGFsKCdzdGF0ZXMuYW1hem9uYXdzLmNvbScpLFxuICAgICAgaW5saW5lUG9saWNpZXM6IHtcbiAgICAgICAgTGFtYmRhSW52b2tlOiBuZXcgaWFtLlBvbGljeURvY3VtZW50KHtcbiAgICAgICAgICBzdGF0ZW1lbnRzOiBbXG4gICAgICAgICAgICBuZXcgaWFtLlBvbGljeVN0YXRlbWVudCh7XG4gICAgICAgICAgICAgIGVmZmVjdDogaWFtLkVmZmVjdC5BTExPVyxcbiAgICAgICAgICAgICAgYWN0aW9uczogWydsYW1iZGE6SW52b2tlRnVuY3Rpb24nXSxcbiAgICAgICAgICAgICAgcmVzb3VyY2VzOiBbYGFybjphd3M6bGFtYmRhOiR7dGhpcy5yZWdpb259OiR7dGhpcy5hY2NvdW50fTpmdW5jdGlvbjoke3Jlc291cmNlUHJlZml4fS0qYF0sXG4gICAgICAgICAgICB9KSxcbiAgICAgICAgICBdLFxuICAgICAgICB9KSxcbiAgICAgICAgU2FnZU1ha2VyQWNjZXNzOiBuZXcgaWFtLlBvbGljeURvY3VtZW50KHtcbiAgICAgICAgICBzdGF0ZW1lbnRzOiBbXG4gICAgICAgICAgICBuZXcgaWFtLlBvbGljeVN0YXRlbWVudCh7XG4gICAgICAgICAgICAgIGVmZmVjdDogaWFtLkVmZmVjdC5BTExPVyxcbiAgICAgICAgICAgICAgYWN0aW9uczogW1xuICAgICAgICAgICAgICAgICdzYWdlbWFrZXI6Q3JlYXRlVHJhaW5pbmdKb2InLFxuICAgICAgICAgICAgICAgICdzYWdlbWFrZXI6RGVzY3JpYmVUcmFpbmluZ0pvYicsXG4gICAgICAgICAgICAgICAgJ3NhZ2VtYWtlcjpTdG9wVHJhaW5pbmdKb2InLFxuICAgICAgICAgICAgICAgICdzYWdlbWFrZXI6QWRkVGFncycsXG4gICAgICAgICAgICAgIF0sXG4gICAgICAgICAgICAgIHJlc291cmNlczogW2Bhcm46YXdzOnNhZ2VtYWtlcjoke3RoaXMucmVnaW9ufToke3RoaXMuYWNjb3VudH06dHJhaW5pbmctam9iLyR7cmVzb3VyY2VQcmVmaXh9LSpgXSxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgICAgbmV3IGlhbS5Qb2xpY3lTdGF0ZW1lbnQoe1xuICAgICAgICAgICAgICBlZmZlY3Q6IGlhbS5FZmZlY3QuQUxMT1csXG4gICAgICAgICAgICAgIGFjdGlvbnM6IFsnaWFtOlBhc3NSb2xlJ10sXG4gICAgICAgICAgICAgIHJlc291cmNlczogW3NhZ2VtYWtlclJvbGUucm9sZUFybl0sXG4gICAgICAgICAgICB9KSxcbiAgICAgICAgICBdLFxuICAgICAgICB9KSxcbiAgICAgICAgU05TUHVibGlzaDogbmV3IGlhbS5Qb2xpY3lEb2N1bWVudCh7XG4gICAgICAgICAgc3RhdGVtZW50czogW1xuICAgICAgICAgICAgbmV3IGlhbS5Qb2xpY3lTdGF0ZW1lbnQoe1xuICAgICAgICAgICAgICBlZmZlY3Q6IGlhbS5FZmZlY3QuQUxMT1csXG4gICAgICAgICAgICAgIGFjdGlvbnM6IFsnc25zOlB1Ymxpc2gnXSxcbiAgICAgICAgICAgICAgcmVzb3VyY2VzOiBbYGFybjphd3M6c25zOiR7dGhpcy5yZWdpb259OiR7dGhpcy5hY2NvdW50fToke3Jlc291cmNlUHJlZml4fS0qYF0sXG4gICAgICAgICAgICB9KSxcbiAgICAgICAgICBdLFxuICAgICAgICB9KSxcbiAgICAgIH0sXG4gICAgfSk7XG5cbiAgICBsYW1iZGFSb2xlLmFkZFRvUHJpbmNpcGFsUG9saWN5KG5ldyBpYW0uUG9saWN5U3RhdGVtZW50KHtcbiAgICAgIGVmZmVjdDogaWFtLkVmZmVjdC5BTExPVyxcbiAgICAgIGFjdGlvbnM6IFsnaWFtOlBhc3NSb2xlJ10sXG4gICAgICByZXNvdXJjZXM6IFtzdGVwRnVuY3Rpb25zUm9sZS5yb2xlQXJuXSxcbiAgICB9KSk7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIExBTUJEQSBGVU5DVElPTlxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgdGhpcy5sYW1iZGFGdW5jdGlvbiA9IG5ldyBsYW1iZGEuRnVuY3Rpb24odGhpcywgJ0FwaUZ1bmN0aW9uJywge1xuICAgICAgZnVuY3Rpb25OYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tbGFtYmRhLWZ1bmN0aW9uYCxcbiAgICAgIHJ1bnRpbWU6IGxhbWJkYS5SdW50aW1lLlBZVEhPTl8zXzksXG4gICAgICBjb2RlOiBsYW1iZGEuQ29kZS5mcm9tQXNzZXQoJy4uL2RlcGxveScpLFxuICAgICAgaGFuZGxlcjogJ2NvbXBsZXRlX2FwaV9oYW5kbGVyLmxhbWJkYV9oYW5kbGVyJyxcbiAgICAgIHJvbGU6IGxhbWJkYVJvbGUsXG4gICAgICB0aW1lb3V0OiBjZGsuRHVyYXRpb24ubWludXRlcygxNSksXG4gICAgICBtZW1vcnlTaXplOiAxMDI0LFxuICAgICAgZW52aXJvbm1lbnQ6IHtcbiAgICAgICAgREFUQV9CVUNLRVQ6IHRoaXMuZGF0YUJ1Y2tldC5idWNrZXROYW1lLFxuICAgICAgICBNT0RFTF9CVUNLRVQ6IHRoaXMubW9kZWxzQnVja2V0LmJ1Y2tldE5hbWUsXG4gICAgICAgIFBJUEVMSU5FU19UQUJMRTogdGhpcy5waXBlbGluZXNUYWJsZS50YWJsZU5hbWUsXG4gICAgICAgIEVOVklST05NRU5UOiBlbnZpcm9ubWVudCxcbiAgICAgICAgTE9HX0xFVkVMOiBlbnZpcm9ubWVudCA9PT0gJ3Byb2QnID8gJ0lORk8nIDogJ0RFQlVHJyxcbiAgICAgIH0sXG4gICAgICBsb2dSZXRlbnRpb246IGxvZ3MuUmV0ZW50aW9uRGF5cy5UV09fV0VFS1MsXG4gICAgICB0cmFjaW5nOiBsYW1iZGEuVHJhY2luZy5BQ1RJVkUsXG4gICAgfSk7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIEFQSSBHQVRFV0FZXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cbiAgICB0aGlzLmFwaSA9IG5ldyBhcGlnYXRld2F5LlJlc3RBcGkodGhpcywgJ0FkcGFBcGknLCB7XG4gICAgICByZXN0QXBpTmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LWFwaWAsXG4gICAgICBkZXNjcmlwdGlvbjogYEFEUEEgQXV0b25vbW91cyBNTCBQaXBlbGluZSBBUEkgLSAke2Vudmlyb25tZW50fWAsXG4gICAgICBkZXBsb3lPcHRpb25zOiB7XG4gICAgICAgIHN0YWdlTmFtZTogZW52aXJvbm1lbnQsXG4gICAgICAgIGxvZ2dpbmdMZXZlbDogYXBpZ2F0ZXdheS5NZXRob2RMb2dnaW5nTGV2ZWwuSU5GTyxcbiAgICAgICAgZGF0YVRyYWNlRW5hYmxlZDogdHJ1ZSxcbiAgICAgICAgbWV0cmljc0VuYWJsZWQ6IHRydWUsXG4gICAgICB9LFxuICAgICAgZGVmYXVsdENvcnNQcmVmbGlnaHRPcHRpb25zOiB7XG4gICAgICAgIGFsbG93T3JpZ2luczogZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/IFsnaHR0cHM6Ly95b3VyZG9tYWluLmNvbSddIDogYXBpZ2F0ZXdheS5Db3JzLkFMTF9PUklHSU5TLFxuICAgICAgICBhbGxvd01ldGhvZHM6IGFwaWdhdGV3YXkuQ29ycy5BTExfTUVUSE9EUyxcbiAgICAgICAgYWxsb3dIZWFkZXJzOiBbJ0NvbnRlbnQtVHlwZScsICdBdXRob3JpemF0aW9uJ10sXG4gICAgICB9LFxuICAgIH0pO1xuXG4gICAgLy8gTGFtYmRhIEludGVncmF0aW9uXG4gICAgY29uc3QgbGFtYmRhSW50ZWdyYXRpb24gPSBuZXcgYXBpZ2F0ZXdheS5MYW1iZGFJbnRlZ3JhdGlvbih0aGlzLmxhbWJkYUZ1bmN0aW9uLCB7XG4gICAgICByZXF1ZXN0VGVtcGxhdGVzOiB7ICdhcHBsaWNhdGlvbi9qc29uJzogJ3sgXCJzdGF0dXNDb2RlXCI6IFwiMjAwXCIgfScgfSxcbiAgICB9KTtcblxuICAgIC8vIFJlcXVlc3QgVmFsaWRhdG9yXG4gICAgY29uc3QgcmVxdWVzdFZhbGlkYXRvciA9IG5ldyBhcGlnYXRld2F5LlJlcXVlc3RWYWxpZGF0b3IodGhpcywgJ1JlcXVlc3RWYWxpZGF0b3InLCB7XG4gICAgICByZXN0QXBpOiB0aGlzLmFwaSxcbiAgICAgIHZhbGlkYXRlUmVxdWVzdEJvZHk6IHRydWUsXG4gICAgICB2YWxpZGF0ZVJlcXVlc3RQYXJhbWV0ZXJzOiB0cnVlLFxuICAgIH0pO1xuXG4gICAgLy8gQVBJIEdhdGV3YXkgUmVzb3VyY2VzIGFuZCBNZXRob2RzXG4gICAgY29uc3QgaGVhbHRoUmVzb3VyY2UgPSB0aGlzLmFwaS5yb290LmFkZFJlc291cmNlKCdoZWFsdGgnKTtcbiAgICBoZWFsdGhSZXNvdXJjZS5hZGRNZXRob2QoJ0dFVCcsIGxhbWJkYUludGVncmF0aW9uKTtcblxuICAgIGNvbnN0IHBpcGVsaW5lc1Jlc291cmNlID0gdGhpcy5hcGkucm9vdC5hZGRSZXNvdXJjZSgncGlwZWxpbmVzJyk7XG4gICAgXG4gICAgLy8gUE9TVCAvcGlwZWxpbmVzIHdpdGggcmVxdWVzdCB2YWxpZGF0aW9uXG4gICAgcGlwZWxpbmVzUmVzb3VyY2UuYWRkTWV0aG9kKCdQT1NUJywgbGFtYmRhSW50ZWdyYXRpb24sIHtcbiAgICAgIHJlcXVlc3RWYWxpZGF0b3IsXG4gICAgICByZXF1ZXN0TW9kZWxzOiB7XG4gICAgICAgICdhcHBsaWNhdGlvbi9qc29uJzogbmV3IGFwaWdhdGV3YXkuTW9kZWwodGhpcywgJ0NyZWF0ZVBpcGVsaW5lTW9kZWwnLCB7XG4gICAgICAgICAgcmVzdEFwaTogdGhpcy5hcGksXG4gICAgICAgICAgY29udGVudFR5cGU6ICdhcHBsaWNhdGlvbi9qc29uJyxcbiAgICAgICAgICBzY2hlbWE6IHtcbiAgICAgICAgICAgIHR5cGU6IGFwaWdhdGV3YXkuSnNvblNjaGVtYVR5cGUuT0JKRUNULFxuICAgICAgICAgICAgcHJvcGVydGllczoge1xuICAgICAgICAgICAgICBkYXRhc2V0X3BhdGg6IHsgdHlwZTogYXBpZ2F0ZXdheS5Kc29uU2NoZW1hVHlwZS5TVFJJTkcgfSxcbiAgICAgICAgICAgICAgb2JqZWN0aXZlOiB7IHR5cGU6IGFwaWdhdGV3YXkuSnNvblNjaGVtYVR5cGUuU1RSSU5HIH0sXG4gICAgICAgICAgICAgIGNvbmZpZzogeyB0eXBlOiBhcGlnYXRld2F5Lkpzb25TY2hlbWFUeXBlLk9CSkVDVCB9LFxuICAgICAgICAgICAgfSxcbiAgICAgICAgICAgIHJlcXVpcmVkOiBbJ2RhdGFzZXRfcGF0aCcsICdvYmplY3RpdmUnXSxcbiAgICAgICAgICB9LFxuICAgICAgICB9KSxcbiAgICAgIH0sXG4gICAgfSk7XG5cbiAgICBwaXBlbGluZXNSZXNvdXJjZS5hZGRNZXRob2QoJ0dFVCcsIGxhbWJkYUludGVncmF0aW9uKTtcblxuICAgIGNvbnN0IHBpcGVsaW5lUmVzb3VyY2UgPSBwaXBlbGluZXNSZXNvdXJjZS5hZGRSZXNvdXJjZSgne2lkfScpO1xuICAgIHBpcGVsaW5lUmVzb3VyY2UuYWRkTWV0aG9kKCdHRVQnLCBsYW1iZGFJbnRlZ3JhdGlvbik7XG5cbiAgICBjb25zdCBleGVjdXRlUmVzb3VyY2UgPSBwaXBlbGluZVJlc291cmNlLmFkZFJlc291cmNlKCdleGVjdXRlJyk7XG4gICAgZXhlY3V0ZVJlc291cmNlLmFkZE1ldGhvZCgnUE9TVCcsIGxhbWJkYUludGVncmF0aW9uKTtcblxuICAgIGNvbnN0IHN0YXR1c1Jlc291cmNlID0gcGlwZWxpbmVSZXNvdXJjZS5hZGRSZXNvdXJjZSgnc3RhdHVzJyk7XG4gICAgc3RhdHVzUmVzb3VyY2UuYWRkTWV0aG9kKCdHRVQnLCBsYW1iZGFJbnRlZ3JhdGlvbik7XG5cbiAgICBjb25zdCBkYXRhUmVzb3VyY2UgPSB0aGlzLmFwaS5yb290LmFkZFJlc291cmNlKCdkYXRhJyk7XG4gICAgY29uc3QgdXBsb2FkUmVzb3VyY2UgPSBkYXRhUmVzb3VyY2UuYWRkUmVzb3VyY2UoJ3VwbG9hZCcpO1xuICAgIHVwbG9hZFJlc291cmNlLmFkZE1ldGhvZCgnUE9TVCcsIGxhbWJkYUludGVncmF0aW9uKTtcblxuICAgIGNvbnN0IHVwbG9hZHNSZXNvdXJjZSA9IGRhdGFSZXNvdXJjZS5hZGRSZXNvdXJjZSgndXBsb2FkcycpO1xuICAgIHVwbG9hZHNSZXNvdXJjZS5hZGRNZXRob2QoJ0dFVCcsIGxhbWJkYUludGVncmF0aW9uKTtcblxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgLy8gU05TIFRPUElDXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cbiAgICBjb25zdCBub3RpZmljYXRpb25zVG9waWMgPSBuZXcgc25zLlRvcGljKHRoaXMsICdOb3RpZmljYXRpb25zVG9waWMnLCB7XG4gICAgICB0b3BpY05hbWU6IGAke3Jlc291cmNlUHJlZml4fS1waXBlbGluZS1ub3RpZmljYXRpb25zYCxcbiAgICAgIGRpc3BsYXlOYW1lOiAnQURQQSBQaXBlbGluZSBOb3RpZmljYXRpb25zJyxcbiAgICB9KTtcblxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgLy8gQ0xPVURXQVRDSCBBTEFSTVNcbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIFxuICAgIC8vIExhbWJkYSBFcnJvciBSYXRlIEFsYXJtXG4gICAgbmV3IGNsb3Vkd2F0Y2guQWxhcm0odGhpcywgJ0xhbWJkYUVycm9yQWxhcm0nLCB7XG4gICAgICBhbGFybU5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1sYW1iZGEtZXJyb3JzYCxcbiAgICAgIGFsYXJtRGVzY3JpcHRpb246ICdMYW1iZGEgZnVuY3Rpb24gZXJyb3IgcmF0ZSBpcyB0b28gaGlnaCcsXG4gICAgICBtZXRyaWM6IHRoaXMubGFtYmRhRnVuY3Rpb24ubWV0cmljRXJyb3JzKHtcbiAgICAgICAgcGVyaW9kOiBjZGsuRHVyYXRpb24ubWludXRlcyg1KSxcbiAgICAgIH0pLFxuICAgICAgdGhyZXNob2xkOiA1LFxuICAgICAgZXZhbHVhdGlvblBlcmlvZHM6IDIsXG4gICAgICB0cmVhdE1pc3NpbmdEYXRhOiBjbG91ZHdhdGNoLlRyZWF0TWlzc2luZ0RhdGEuTk9UX0JSRUFDSElORyxcbiAgICB9KTtcblxuICAgIC8vIEFQSSBHYXRld2F5IDRYWCBFcnJvciBSYXRlXG4gICAgbmV3IGNsb3Vkd2F0Y2guQWxhcm0odGhpcywgJ0FwaUdhdGV3YXk0WFhBbGFybScsIHtcbiAgICAgIGFsYXJtTmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LWFwaS00eHgtZXJyb3JzYCxcbiAgICAgIGFsYXJtRGVzY3JpcHRpb246ICdBUEkgR2F0ZXdheSA0WFggZXJyb3IgcmF0ZSBpcyB0b28gaGlnaCcsXG4gICAgICBtZXRyaWM6IHRoaXMuYXBpLm1ldHJpY0NsaWVudEVycm9yKHtcbiAgICAgICAgcGVyaW9kOiBjZGsuRHVyYXRpb24ubWludXRlcyg1KSxcbiAgICAgIH0pLFxuICAgICAgdGhyZXNob2xkOiAyMCxcbiAgICAgIGV2YWx1YXRpb25QZXJpb2RzOiAyLFxuICAgIH0pO1xuXG4gICAgLy8gRHluYW1vREIgVGhyb3R0bGUgQWxhcm1cbiAgICBuZXcgY2xvdWR3YXRjaC5BbGFybSh0aGlzLCAnRHluYW1vREJUaHJvdHRsZUFsYXJtJywge1xuICAgICAgYWxhcm1OYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tZHluYW1vZGItdGhyb3R0bGVzYCxcbiAgICAgIGFsYXJtRGVzY3JpcHRpb246ICdEeW5hbW9EQiBpcyBiZWluZyB0aHJvdHRsZWQnLFxuICAgICAgbWV0cmljOiB0aGlzLnBpcGVsaW5lc1RhYmxlLm1ldHJpY1Rocm90dGxlZFJlcXVlc3RzKHtcbiAgICAgICAgcGVyaW9kOiBjZGsuRHVyYXRpb24ubWludXRlcyg1KSxcbiAgICAgIH0pLFxuICAgICAgdGhyZXNob2xkOiAxLFxuICAgICAgZXZhbHVhdGlvblBlcmlvZHM6IDEsXG4gICAgfSk7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIE9VVFBVVFNcbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdBcGlVcmwnLCB7XG4gICAgICB2YWx1ZTogdGhpcy5hcGkudXJsLFxuICAgICAgZGVzY3JpcHRpb246ICdBUEkgR2F0ZXdheSBVUkwnLFxuICAgIH0pO1xuXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0RhdGFCdWNrZXROYW1lJywge1xuICAgICAgdmFsdWU6IHRoaXMuZGF0YUJ1Y2tldC5idWNrZXROYW1lLFxuICAgICAgZGVzY3JpcHRpb246ICdEYXRhIFMzIEJ1Y2tldCBOYW1lJyxcbiAgICB9KTtcblxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdNb2RlbHNCdWNrZXROYW1lJywge1xuICAgICAgdmFsdWU6IHRoaXMubW9kZWxzQnVja2V0LmJ1Y2tldE5hbWUsXG4gICAgICBkZXNjcmlwdGlvbjogJ01vZGVscyBTMyBCdWNrZXQgTmFtZScsXG4gICAgfSk7XG5cbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnUGlwZWxpbmVzVGFibGVOYW1lJywge1xuICAgICAgdmFsdWU6IHRoaXMucGlwZWxpbmVzVGFibGUudGFibGVOYW1lLFxuICAgICAgZGVzY3JpcHRpb246ICdQaXBlbGluZXMgRHluYW1vREIgVGFibGUgTmFtZScsXG4gICAgfSk7XG5cbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnTGFtYmRhRnVuY3Rpb25OYW1lJywge1xuICAgICAgdmFsdWU6IHRoaXMubGFtYmRhRnVuY3Rpb24uZnVuY3Rpb25OYW1lLFxuICAgICAgZGVzY3JpcHRpb246ICdMYW1iZGEgRnVuY3Rpb24gTmFtZScsXG4gICAgfSk7XG4gIH1cbn0iXX0=