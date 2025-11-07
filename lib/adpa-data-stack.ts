import {
  Stack,
  StackProps,
  CfnOutput,
  RemovalPolicy,
  Duration,
  aws_s3 as s3,
  aws_iam as iam,
  aws_glue as glue,
  aws_lambda as lambda,
  aws_events as events,
  aws_events_targets as targets,
  aws_logs as logs,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';

export class AdpaDataStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // Buckets: raw, curated, artifacts
    const rawBucket = new s3.Bucket(this, 'RawBucket', {
      versioned: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const curatedBucket = new s3.Bucket(this, 'CuratedBucket', {
      versioned: false,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const artifactsBucket = new s3.Bucket(this, 'ArtifactsBucket', {
      versioned: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // Glue Database
    const db = new glue.CfnDatabase(this, 'GlueDatabase', {
      catalogId: this.account,
      databaseInput: { name: 'adpa_raw_db' },
    });

    // IAM Role for Glue Crawler
    const crawlerRole = new iam.Role(this, 'CrawlerRole', {
      assumedBy: new iam.ServicePrincipal('glue.amazonaws.com'),
    });
    rawBucket.grantRead(crawlerRole);
    crawlerRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSGlueServiceRole'));

    // Glue Crawler scanning the raw bucket
    const crawler = new glue.CfnCrawler(this, 'RawCrawler', {
      role: crawlerRole.roleArn,
      databaseName: db.ref,
      targets: { s3Targets: [{ path: `s3://${rawBucket.bucketName}/` }] },
      schemaChangePolicy: { deleteBehavior: 'DEPRECATE_IN_DATABASE', updateBehavior: 'UPDATE_IN_DATABASE' },
      name: 'adpa-raw-crawler',
    });

    // CloudWatch Logs group for Lambda (use logGroup instead of deprecated logRetention)
    const etlLogGroup = new logs.LogGroup(this, 'LightEtlLogGroup', {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    // Minimal ETL Lambda (placeholder): copies any new object from raw → curated
    const etlFn = new lambda.Function(this, 'LightEtlFn', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`import os
import json
import boto3
s3=boto3.client('s3')
RAW=os.environ['RAW']
CUR=os.environ['CUR']

def handler(event, context):
  # TODO: implement copy/transform raw → curated
  return { 'status':'ok' }`),
      environment: {
        RAW: rawBucket.bucketName,
        CUR: curatedBucket.bucketName,
      },
      logGroup: etlLogGroup,
    });
    rawBucket.grantRead(etlFn);
    curatedBucket.grantReadWrite(etlFn);

    // Optional: EventBridge rule for S3 create events (minimal placeholder)
    const rule = new events.Rule(this, 'RawToCuratedRule', {
      eventPattern: {
        source: ['aws.s3'],
        detailType: ['Object Created'],
      },
    });
    rule.addTarget(new targets.LambdaFunction(etlFn));

    // Outputs
    new CfnOutput(this, 'RawBucketName', { value: rawBucket.bucketName });
    new CfnOutput(this, 'CuratedBucketName', { value: curatedBucket.bucketName });
    new CfnOutput(this, 'ArtifactsBucketName', { value: artifactsBucket.bucketName });
    new CfnOutput(this, 'GlueDatabaseName', { value: 'adpa_raw_db' });
    new CfnOutput(this, 'GlueCrawlerName', { value: crawler.name! });
  }
}