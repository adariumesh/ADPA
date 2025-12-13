"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SimpleAdpaStack = void 0;
const cdk = require("aws-cdk-lib");
const lambda = require("aws-cdk-lib/aws-lambda");
const apigateway = require("aws-cdk-lib/aws-apigateway");
const dynamodb = require("aws-cdk-lib/aws-dynamodb");
const s3 = require("aws-cdk-lib/aws-s3");
const iam = require("aws-cdk-lib/aws-iam");
const cloudwatch = require("aws-cdk-lib/aws-cloudwatch");
class SimpleAdpaStack extends cdk.Stack {
    constructor(scope, id, props) {
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
exports.SimpleAdpaStack = SimpleAdpaStack;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoic2ltcGxlLXN0YWNrLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsic2ltcGxlLXN0YWNrLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7OztBQUFBLG1DQUFtQztBQUNuQyxpREFBaUQ7QUFDakQseURBQXlEO0FBQ3pELHFEQUFxRDtBQUNyRCx5Q0FBeUM7QUFDekMsMkNBQTJDO0FBQzNDLHlEQUF5RDtBQUd6RCxNQUFhLGVBQWdCLFNBQVEsR0FBRyxDQUFDLEtBQUs7SUFDNUMsWUFBWSxLQUFnQixFQUFFLEVBQVUsRUFBRSxLQUFzQjtRQUM5RCxLQUFLLENBQUMsS0FBSyxFQUFFLEVBQUUsRUFBRSxLQUFLLENBQUMsQ0FBQztRQUV4QixNQUFNLFdBQVcsR0FBRyxNQUFNLENBQUM7UUFDM0IsTUFBTSxjQUFjLEdBQUcsUUFBUSxXQUFXLEVBQUUsQ0FBQztRQUU3QyxhQUFhO1FBQ2IsTUFBTSxVQUFVLEdBQUcsSUFBSSxFQUFFLENBQUMsTUFBTSxDQUFDLElBQUksRUFBRSxZQUFZLEVBQUU7WUFDbkQsVUFBVSxFQUFFLEdBQUcsY0FBYyxTQUFTLElBQUksQ0FBQyxPQUFPLEVBQUU7WUFDcEQsU0FBUyxFQUFFLElBQUk7WUFDZixVQUFVLEVBQUUsRUFBRSxDQUFDLGdCQUFnQixDQUFDLFVBQVU7WUFDMUMsZ0JBQWdCLEVBQUUsS0FBSztZQUN2QixpQkFBaUIsRUFBRSxFQUFFLENBQUMsaUJBQWlCLENBQUMsU0FBUztTQUNsRCxDQUFDLENBQUM7UUFFSCxNQUFNLFlBQVksR0FBRyxJQUFJLEVBQUUsQ0FBQyxNQUFNLENBQUMsSUFBSSxFQUFFLGNBQWMsRUFBRTtZQUN2RCxVQUFVLEVBQUUsR0FBRyxjQUFjLFdBQVcsSUFBSSxDQUFDLE9BQU8sRUFBRTtZQUN0RCxTQUFTLEVBQUUsSUFBSTtZQUNmLFVBQVUsRUFBRSxFQUFFLENBQUMsZ0JBQWdCLENBQUMsVUFBVTtZQUMxQyxnQkFBZ0IsRUFBRSxLQUFLO1lBQ3ZCLGlCQUFpQixFQUFFLEVBQUUsQ0FB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QVEsRUFBRTtZQUNoQyxLQUFLLEVBQUUsR0FBRyxDQUFDLEdBQUc7WUFDZCxXQUFXLEVBQUUsNEJBQTRCO1NBQzFDLENBQUMsQ0FBQztRQUVILElBQUksR0FBRyxDQUFDLFNBQVMsQ0FBQyxJQUFJLEVBQUUsZ0JBQWdCLEVBQUU7WUFDeEMsS0FBSyxFQUFFLFVBQVUsQ0FBQyxVQUFVO1lBQzVCLFdBQVcsRUFBRSxxQkFBcUI7U0FDbkMsQ0FBQyxDQUFDO1FBRUgsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxrQkFBa0IsRUFBRTtZQUMxQyxLQUFLLEVBQUUsWUFBWSxDQUFDLFVBQVU7WUFDOUIsV0FBVyxFQUFFLHVCQUF1QjtTQUNyQyxDQUFDLENBQUM7UUFFSCxJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLG9CQUFvQixFQUFFO1lBQzVDLEtBQUssRUFBRSxjQUFjLENBQUMsU0FBUztZQUMvQixXQUFXLEVBQUUsK0JBQStCO1NBQzdDLENBQUMsQ0FBQztRQUVILElBQUksR0FBRyxDQUFDLFNBQVMsQ0FBQyxJQUFJLEVBQUUsb0JBQW9CLEVBQUU7WUFDNUMsS0FBSyxFQUFFLFdBQVcsQ0FBQyxZQUFZO1lBQy9CLFdBQVcsRUFBRSxzQkFBc0I7U0FDcEMsQ0FBQyxDQUFDO0lBQ0wsQ0FBQztDQUNGO0FBcE1ELDBDQW9NQyIsInNvdXJjZXNDb250ZW50IjpbImltcG9ydCAqIGFzIGNkayBmcm9tICdhd3MtY2RrLWxpYic7XG5pbXBvcnQgKiBhcyBsYW1iZGEgZnJvbSAnYXdzLWNkay1saWIvYXdzLWxhbWJkYSc7XG5pbXBvcnQgKiBhcyBhcGlnYXRld2F5IGZyb20gJ2F3cy1jZGstbGliL2F3cy1hcGlnYXRld2F5JztcbmltcG9ydCAqIGFzIGR5bmFtb2RiIGZyb20gJ2F3cy1jZGstbGliL2F3cy1keW5hbW9kYic7XG5pbXBvcnQgKiBhcyBzMyBmcm9tICdhd3MtY2RrLWxpYi9hd3MtczMnO1xuaW1wb3J0ICogYXMgaWFtIGZyb20gJ2F3cy1jZGstbGliL2F3cy1pYW0nO1xuaW1wb3J0ICogYXMgY2xvdWR3YXRjaCBmcm9tICdhd3MtY2RrLWxpYi9hd3MtY2xvdWR3YXRjaCc7XG5pbXBvcnQgeyBDb25zdHJ1Y3QgfSBmcm9tICdjb25zdHJ1Y3RzJztcblxuZXhwb3J0IGNsYXNzIFNpbXBsZUFkcGFTdGFjayBleHRlbmRzIGNkay5TdGFjayB7XG4gIGNvbnN0cnVjdG9yKHNjb3BlOiBDb25zdHJ1Y3QsIGlkOiBzdHJpbmcsIHByb3BzPzogY2RrLlN0YWNrUHJvcHMpIHtcbiAgICBzdXBlcihzY29wZSwgaWQsIHByb3BzKTtcblxuICAgIGNvbnN0IGVudmlyb25tZW50ID0gJ3Byb2QnO1xuICAgIGNvbnN0IHJlc291cmNlUHJlZml4ID0gYGFkcGEtJHtlbnZpcm9ubWVudH1gO1xuXG4gICAgLy8gUzMgQnVja2V0c1xuICAgIGNvbnN0IGRhdGFCdWNrZXQgPSBuZXcgczMuQnVja2V0KHRoaXMsICdEYXRhQnVja2V0Jywge1xuICAgICAgYnVja2V0TmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LWRhdGEtJHt0aGlzLmFjY291bnR9YCxcbiAgICAgIHZlcnNpb25lZDogdHJ1ZSxcbiAgICAgIGVuY3J5cHRpb246IHMzLkJ1Y2tldEVuY3J5cHRpb24uUzNfTUFOQUdFRCxcbiAgICAgIHB1YmxpY1JlYWRBY2Nlc3M6IGZhbHNlLFxuICAgICAgYmxvY2tQdWJsaWNBY2Nlc3M6IHMzLkJsb2NrUHVibGljQWNjZXNzLkJMT0NLX0FMTCxcbiAgICB9KTtcblxuICAgIGNvbnN0IG1vZGVsc0J1Y2tldCA9IG5ldyBzMy5CdWNrZXQodGhpcywgJ01vZGVsc0J1Y2tldCcsIHtcbiAgICAgIGJ1Y2tldE5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1tb2RlbHMtJHt0aGlzLmFjY291bnR9YCxcbiAgICAgIHZlcnNpb25lZDogdHJ1ZSxcbiAgICAgIGVuY3J5cHRpb246IHMzLkJ1Y2tldEVuY3J5cHRpb24uUzNfTUFOQUdFRCxcbiAgICAgIHB1YmxpY1JlYWRBY2Nlc3M6IGZhbHNlLFxuICAgICAgYmxvY2tQdWJsaWNBY2Nlc3M6IHMzLkJsb2NrUHVibGljQWNjZXNzLkJMT0NLX0FMTCxcbiAgICB9KTtcblxuICAgIC8vIER5bmFtb0RCIFRhYmxlXG4gICAgY29uc3QgcGlwZWxpbmVzVGFibGUgPSBuZXcgZHluYW1vZGIuVGFibGUodGhpcywgJ1BpcGVsaW5lc1RhYmxlJywge1xuICAgICAgdGFibGVOYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tcGlwZWxpbmVzYCxcbiAgICAgIHBhcnRpdGlvbktleTogeyBuYW1lOiAncGlwZWxpbmVfaWQnLCB0eXBlOiBkeW5hbW9kYi5BdHRyaWJ1dGVUeXBlLlNUUklORyB9LFxuICAgICAgc29ydEtleTogeyBuYW1lOiAndGltZXN0YW1wJywgdHlwZTogZHluYW1vZGIuQXR0cmlidXRlVHlwZS5OVU1CRVIgfSxcbiAgICAgIGJpbGxpbmdNb2RlOiBkeW5hbW9kYi5CaWxsaW5nTW9kZS5QQVlfUEVSX1JFUVVFU1QsXG4gICAgICBlbmNyeXB0aW9uOiBkeW5hbW9kYi5UYWJsZUVuY3J5cHRpb24uQVdTX01BTkFHRUQsXG4gICAgICBwb2ludEluVGltZVJlY292ZXJ5OiB0cnVlLFxuICAgICAgcmVtb3ZhbFBvbGljeTogY2RrLlJlbW92YWxQb2xpY3kuREVTVFJPWSxcbiAgICB9KTtcblxuICAgIC8vIElBTSBSb2xlIGZvciBMYW1iZGFcbiAgICBjb25zdCBsYW1iZGFSb2xlID0gbmV3IGlhbS5Sb2xlKHRoaXMsICdMYW1iZGFFeGVjdXRpb25Sb2xlJywge1xuICAgICAgcm9sZU5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1sYW1iZGEtZXhlY3V0aW9uLXJvbGVgLFxuICAgICAgYXNzdW1lZEJ5OiBuZXcgaWFtLlNlcnZpY2VQcmluY2lwYWwoJ2xhbWJkYS5hbWF6b25hd3MuY29tJyksXG4gICAgICBtYW5hZ2VkUG9saWNpZXM6IFtcbiAgICAgICAgaWFtLk1hbmFnZWRQb2xpY3kuZnJvbUF3c01hbmFnZWRQb2xpY3lOYW1lKCdzZXJ2aWNlLXJvbGUvQVdTTGFtYmRhQmFzaWNFeGVjdXRpb25Sb2xlJyksXG4gICAgICAgIGlhbS5NYW5hZ2VkUG9saWN5LmZyb21Bd3NNYW5hZ2VkUG9saWN5TmFtZSgnQVdTWFJheURhZW1vbldyaXRlQWNjZXNzJyksXG4gICAgICBdLFxuICAgICAgaW5saW5lUG9saWNpZXM6IHtcbiAgICAgICAgRHluYW1vREJBY2Nlc3M6IG5ldyBpYW0uUG9saWN5RG9jdW1lbnQoe1xuICAgICAgICAgIHN0YXRlbWVudHM6IFtcbiAgICAgICAgICAgIG5ldyBpYW0uUG9saWN5U3RhdGVtZW50KHtcbiAgICAgICAgICAgICAgZWZmZWN0OiBpYW0uRWZmZWN0LkFMTE9XLFxuICAgICAgICAgICAgICBhY3Rpb25zOiBbXG4gICAgICAgICAgICAgICAgJ2R5bmFtb2RiOkdldEl0ZW0nLFxuICAgICAgICAgICAgICAgICdkeW5hbW9kYjpQdXRJdGVtJywgXG4gICAgICAgICAgICAgICAgJ2R5bmFtb2RiOlVwZGF0ZUl0ZW0nLFxuICAgICAgICAgICAgICAgICdkeW5hbW9kYjpEZWxldGVJdGVtJyxcbiAgICAgICAgICAgICAgICAnZHluYW1vZGI6UXVlcnknLFxuICAgICAgICAgICAgICAgICdkeW5hbW9kYjpTY2FuJyxcbiAgICAgICAgICAgICAgXSxcbiAgICAgICAgICAgICAgcmVzb3VyY2VzOiBbcGlwZWxpbmVzVGFibGUudGFibGVBcm4sIGAke3BpcGVsaW5lc1RhYmxlLnRhYmxlQXJufS9pbmRleC8qYF0sXG4gICAgICAgICAgICB9KSxcbiAgICAgICAgICBdLFxuICAgICAgICB9KSxcbiAgICAgICAgUzNBY2Nlc3M6IG5ldyBpYW0uUG9saWN5RG9jdW1lbnQoe1xuICAgICAgICAgIHN0YXRlbWVudHM6IFtcbiAgICAgICAgICAgIG5ldyBpYW0uUG9saWN5U3RhdGVtZW50KHtcbiAgICAgICAgICAgICAgZWZmZWN0OiBpYW0uRWZmZWN0LkFMTE9XLFxuICAgICAgICAgICAgICBhY3Rpb25zOiBbJ3MzOkdldE9iamVjdCcsICdzMzpQdXRPYmplY3QnLCAnczM6RGVsZXRlT2JqZWN0JywgJ3MzOkxpc3RCdWNrZXQnXSxcbiAgICAgICAgICAgICAgcmVzb3VyY2VzOiBbXG4gICAgICAgICAgICAgICAgZGF0YUJ1Y2tldC5idWNrZXRBcm4sIGAke2RhdGFCdWNrZXQuYnVja2V0QXJufS8qYCxcbiAgICAgICAgICAgICAgICBtb2RlbHNCdWNrZXQuYnVja2V0QXJuLCBgJHttb2RlbHNCdWNrZXQuYnVja2V0QXJufS8qYCxcbiAgICAgICAgICAgICAgXSxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgIF0sXG4gICAgICAgIH0pLFxuICAgICAgICBTdGVwRnVuY3Rpb25zQWNjZXNzOiBuZXcgaWFtLlBvbGljeURvY3VtZW50KHtcbiAgICAgICAgICBzdGF0ZW1lbnRzOiBbXG4gICAgICAgICAgICBuZXcgaWFtLlBvbGljeVN0YXRlbWVudCh7XG4gICAgICAgICAgICAgIGVmZmVjdDogaWFtLkVmZmVjdC5BTExPVyxcbiAgICAgICAgICAgICAgYWN0aW9uczogWydzdGF0ZXM6U3RhcnRFeGVjdXRpb24nLCAnc3RhdGVzOkRlc2NyaWJlRXhlY3V0aW9uJ10sXG4gICAgICAgICAgICAgIHJlc291cmNlczogW2Bhcm46YXdzOnN0YXRlczoke3RoaXMucmVnaW9ufToke3RoaXMuYWNjb3VudH06c3RhdGVNYWNoaW5lOiR7cmVzb3VyY2VQcmVmaXh9LSpgXSxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgIF0sXG4gICAgICAgIH0pLFxuICAgICAgfSxcbiAgICB9KTtcblxuICAgIC8vIExhbWJkYSBGdW5jdGlvblxuICAgIGNvbnN0IGFwaUZ1bmN0aW9uID0gbmV3IGxhbWJkYS5GdW5jdGlvbih0aGlzLCAnQXBpRnVuY3Rpb24nLCB7XG4gICAgICBmdW5jdGlvbk5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1sYW1iZGEtZnVuY3Rpb24tdjJgLFxuICAgICAgcnVudGltZTogbGFtYmRhLlJ1bnRpbWUuUFlUSE9OXzNfOSxcbiAgICAgIGNvZGU6IGxhbWJkYS5Db2RlLmZyb21Bc3NldCgnLi4vZGVwbG95Jywge1xuICAgICAgICBleGNsdWRlOiBbJ2xvY2FsLWJhc2VsaW5lLyoqLyonLCAnKi5sb2cnLCAnKiovKi5sb2cnLCAnKiovbGF0ZXN0J10sXG4gICAgICB9KSxcbiAgICAgIGhhbmRsZXI6ICdjb21wbGV0ZV9hcGlfaGFuZGxlci5sYW1iZGFfaGFuZGxlcicsXG4gICAgICByb2xlOiBsYW1iZGFSb2xlLFxuICAgICAgdGltZW91dDogY2RrLkR1cmF0aW9uLm1pbnV0ZXMoMTUpLFxuICAgICAgbWVtb3J5U2l6ZTogMTAyNCxcbiAgICAgIGVudmlyb25tZW50OiB7XG4gICAgICAgIERBVEFfQlVDS0VUOiBkYXRhQnVja2V0LmJ1Y2tldE5hbWUsXG4gICAgICAgIE1PREVMX0JVQ0tFVDogbW9kZWxzQnVja2V0LmJ1Y2tldE5hbWUsXG4gICAgICAgIFBJUEVMSU5FU19UQUJMRTogcGlwZWxpbmVzVGFibGUudGFibGVOYW1lLFxuICAgICAgICBFTlZJUk9OTUVOVDogZW52aXJvbm1lbnQsXG4gICAgICAgIFNUQVRFX01BQ0hJTkVfQVJOOiBgYXJuOmF3czpzdGF0ZXM6JHt0aGlzLnJlZ2lvbn06JHt0aGlzLmFjY291bnR9OnN0YXRlTWFjaGluZToke3Jlc291cmNlUHJlZml4fS1tbC1waXBlbGluZS13b3JrZmxvd2AsXG4gICAgICB9LFxuICAgICAgdHJhY2luZzogbGFtYmRhLlRyYWNpbmcuQUNUSVZFLFxuICAgIH0pO1xuXG4gICAgLy8gQVBJIEdhdGV3YXlcbiAgICBjb25zdCBhcGkgPSBuZXcgYXBpZ2F0ZXdheS5SZXN0QXBpKHRoaXMsICdBZHBhQXBpJywge1xuICAgICAgcmVzdEFwaU5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1hcGktdjJgLFxuICAgICAgZGVzY3JpcHRpb246ICdBRFBBIFByb2R1Y3Rpb24gQVBJIHYyIC0gRW50ZXJwcmlzZSBHcmFkZScsXG4gICAgICBkZXBsb3lPcHRpb25zOiB7XG4gICAgICAgIHN0YWdlTmFtZTogJ3Byb2QnLFxuICAgICAgICBsb2dnaW5nTGV2ZWw6IGFwaWdhdGV3YXkuTWV0aG9kTG9nZ2luZ0xldmVsLklORk8sXG4gICAgICAgIGRhdGFUcmFjZUVuYWJsZWQ6IHRydWUsXG4gICAgICAgIG1ldHJpY3NFbmFibGVkOiB0cnVlLFxuICAgICAgfSxcbiAgICAgIGRlZmF1bHRDb3JzUHJlZmxpZ2h0T3B0aW9uczoge1xuICAgICAgICBhbGxvd09yaWdpbnM6IGFwaWdhdGV3YXkuQ29ycy5BTExfT1JJR0lOUyxcbiAgICAgICAgYWxsb3dNZXRob2RzOiBhcGlnYXRld2F5LkNvcnMuQUxMX01FVEhPRFMsXG4gICAgICAgIGFsbG93SGVhZGVyczogWydDb250ZW50LVR5cGUnLCAnQXV0aG9yaXphdGlvbiddLFxuICAgICAgfSxcbiAgICB9KTtcblxuICAgIC8vIExhbWJkYSBJbnRlZ3JhdGlvblxuICAgIGNvbnN0IGxhbWJkYUludGVncmF0aW9uID0gbmV3IGFwaWdhdGV3YXkuTGFtYmRhSW50ZWdyYXRpb24oYXBpRnVuY3Rpb24pO1xuXG4gICAgLy8gQVBJIFJlc291cmNlc1xuICAgIGNvbnN0IGhlYWx0aFJlc291cmNlID0gYXBpLnJvb3QuYWRkUmVzb3VyY2UoJ2hlYWx0aCcpO1xuICAgIGhlYWx0aFJlc291cmNlLmFkZE1ldGhvZCgnR0VUJywgbGFtYmRhSW50ZWdyYXRpb24pO1xuXG4gICAgY29uc3QgcGlwZWxpbmVzUmVzb3VyY2UgPSBhcGkucm9vdC5hZGRSZXNvdXJjZSgncGlwZWxpbmVzJyk7XG4gICAgcGlwZWxpbmVzUmVzb3VyY2UuYWRkTWV0aG9kKCdHRVQnLCBsYW1iZGFJbnRlZ3JhdGlvbik7XG4gICAgcGlwZWxpbmVzUmVzb3VyY2UuYWRkTWV0aG9kKCdQT1NUJywgbGFtYmRhSW50ZWdyYXRpb24pO1xuXG4gICAgY29uc3QgcGlwZWxpbmVSZXNvdXJjZSA9IHBpcGVsaW5lc1Jlc291cmNlLmFkZFJlc291cmNlKCd7aWR9Jyk7XG4gICAgcGlwZWxpbmVSZXNvdXJjZS5hZGRNZXRob2QoJ0dFVCcsIGxhbWJkYUludGVncmF0aW9uKTtcblxuICAgIGNvbnN0IGV4ZWN1dGVSZXNvdXJjZSA9IHBpcGVsaW5lUmVzb3VyY2UuYWRkUmVzb3VyY2UoJ2V4ZWN1dGUnKTtcbiAgICBleGVjdXRlUmVzb3VyY2UuYWRkTWV0aG9kKCdQT1NUJywgbGFtYmRhSW50ZWdyYXRpb24pO1xuXG4gICAgY29uc3Qgc3RhdHVzUmVzb3VyY2UgPSBwaXBlbGluZVJlc291cmNlLmFkZFJlc291cmNlKCdzdGF0dXMnKTtcbiAgICBzdGF0dXNSZXNvdXJjZS5hZGRNZXRob2QoJ0dFVCcsIGxhbWJkYUludGVncmF0aW9uKTtcblxuICAgIGNvbnN0IGRhdGFSZXNvdXJjZSA9IGFwaS5yb290LmFkZFJlc291cmNlKCdkYXRhJyk7XG4gICAgY29uc3QgdXBsb2FkUmVzb3VyY2UgPSBkYXRhUmVzb3VyY2UuYWRkUmVzb3VyY2UoJ3VwbG9hZCcpO1xuICAgIHVwbG9hZFJlc291cmNlLmFkZE1ldGhvZCgnUE9TVCcsIGxhbWJkYUludGVncmF0aW9uKTtcblxuICAgIGNvbnN0IHVwbG9hZHNSZXNvdXJjZSA9IGRhdGFSZXNvdXJjZS5hZGRSZXNvdXJjZSgndXBsb2FkcycpO1xuICAgIHVwbG9hZHNSZXNvdXJjZS5hZGRNZXRob2QoJ0dFVCcsIGxhbWJkYUludGVncmF0aW9uKTtcblxuICAgIC8vIENsb3VkV2F0Y2ggQWxhcm1zXG4gICAgbmV3IGNsb3Vkd2F0Y2guQWxhcm0odGhpcywgJ0xhbWJkYUVycm9yQWxhcm0nLCB7XG4gICAgICBhbGFybU5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1sYW1iZGEtZXJyb3JzYCxcbiAgICAgIGFsYXJtRGVzY3JpcHRpb246ICdMYW1iZGEgZnVuY3Rpb24gZXJyb3IgcmF0ZSBpcyB0b28gaGlnaCcsXG4gICAgICBtZXRyaWM6IGFwaUZ1bmN0aW9uLm1ldHJpY0Vycm9ycyh7XG4gICAgICAgIHBlcmlvZDogY2RrLkR1cmF0aW9uLm1pbnV0ZXMoNSksXG4gICAgICB9KSxcbiAgICAgIHRocmVzaG9sZDogNSxcbiAgICAgIGV2YWx1YXRpb25QZXJpb2RzOiAyLFxuICAgIH0pO1xuXG4gICAgbmV3IGNsb3Vkd2F0Y2guQWxhcm0odGhpcywgJ0FwaUdhdGV3YXk0WFhBbGFybScsIHtcbiAgICAgIGFsYXJtTmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LWFwaS00eHgtZXJyb3JzYCxcbiAgICAgIGFsYXJtRGVzY3JpcHRpb246ICdBUEkgR2F0ZXdheSA0WFggZXJyb3IgcmF0ZSBpcyB0b28gaGlnaCcsXG4gICAgICBtZXRyaWM6IGFwaS5tZXRyaWNDbGllbnRFcnJvcih7XG4gICAgICAgIHBlcmlvZDogY2RrLkR1cmF0aW9uLm1pbnV0ZXMoNSksXG4gICAgICB9KSxcbiAgICAgIHRocmVzaG9sZDogMjAsXG4gICAgICBldmFsdWF0aW9uUGVyaW9kczogMixcbiAgICB9KTtcblxuICAgIC8vIE91dHB1dHNcbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnQXBpVXJsJywge1xuICAgICAgdmFsdWU6IGFwaS51cmwsXG4gICAgICBkZXNjcmlwdGlvbjogJ1Byb2R1Y3Rpb24gQVBJIEdhdGV3YXkgVVJMJyxcbiAgICB9KTtcblxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdEYXRhQnVja2V0TmFtZScsIHtcbiAgICAgIHZhbHVlOiBkYXRhQnVja2V0LmJ1Y2tldE5hbWUsXG4gICAgICBkZXNjcmlwdGlvbjogJ0RhdGEgUzMgQnVja2V0IE5hbWUnLFxuICAgIH0pO1xuXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ01vZGVsc0J1Y2tldE5hbWUnLCB7XG4gICAgICB2YWx1ZTogbW9kZWxzQnVja2V0LmJ1Y2tldE5hbWUsXG4gICAgICBkZXNjcmlwdGlvbjogJ01vZGVscyBTMyBCdWNrZXQgTmFtZScsIFxuICAgIH0pO1xuXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ1BpcGVsaW5lc1RhYmxlTmFtZScsIHtcbiAgICAgIHZhbHVlOiBwaXBlbGluZXNUYWJsZS50YWJsZU5hbWUsXG4gICAgICBkZXNjcmlwdGlvbjogJ1BpcGVsaW5lcyBEeW5hbW9EQiBUYWJsZSBOYW1lJyxcbiAgICB9KTtcblxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdMYW1iZGFGdW5jdGlvbk5hbWUnLCB7XG4gICAgICB2YWx1ZTogYXBpRnVuY3Rpb24uZnVuY3Rpb25OYW1lLFxuICAgICAgZGVzY3JpcHRpb246ICdMYW1iZGEgRnVuY3Rpb24gTmFtZScsXG4gICAgfSk7XG4gIH1cbn0iXX0=