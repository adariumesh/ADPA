import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
export interface AdpaStackProps extends cdk.StackProps {
    environment: 'dev' | 'staging' | 'prod';
    projectName: string;
}
export declare class AdpaStack extends cdk.Stack {
    readonly api: apigateway.RestApi;
    readonly lambdaFunction: lambda.Function;
    readonly pipelinesTable: dynamodb.Table;
    readonly dataBucket: s3.Bucket;
    readonly modelsBucket: s3.Bucket;
    constructor(scope: Construct, id: string, props: AdpaStackProps);
}
