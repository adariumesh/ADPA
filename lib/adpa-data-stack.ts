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
  aws_sns as sns,
  aws_sns_subscriptions as subs,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import { CfnParameter } from 'aws-cdk-lib';

export class AdpaDataStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // === S3 BUCKETS ===
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

    // === GLUE CATALOG ===
    const db = new glue.CfnDatabase(this, 'GlueDatabase', {
      catalogId: this.account,
      databaseInput: { name: 'adpa_raw_db' },
    });

    // IAM Role for Glue Crawler
    const crawlerRole = new iam.Role(this, 'CrawlerRole', {
      assumedBy: new iam.ServicePrincipal('glue.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSGlueServiceRole'),
      ],
    });
    rawBucket.grantRead(crawlerRole);
    curatedBucket.grantRead(crawlerRole);

    // Crawlers: raw + curated
    const rawCrawler = new glue.CfnCrawler(this, 'RawCrawler', {
      role: crawlerRole.roleArn,
      databaseName: db.ref,
      targets: { s3Targets: [{ path: `s3://${rawBucket.bucketName}/` }] },
      schemaChangePolicy: { deleteBehavior: 'DEPRECATE_IN_DATABASE', updateBehavior: 'UPDATE_IN_DATABASE' },
      name: 'adpa-raw-crawler',
    });

    const curatedCrawler = new glue.CfnCrawler(this, 'CuratedCrawler', {
      role: crawlerRole.roleArn,
      databaseName: db.ref,
      targets: { s3Targets: [{ path: `s3://${curatedBucket.bucketName}/` }] },
      schemaChangePolicy: { deleteBehavior: 'DEPRECATE_IN_DATABASE', updateBehavior: 'UPDATE_IN_DATABASE' },
      name: 'adpa-curated-crawler',
    });

    // === LAMBDA (placeholder) + LOG GROUP ===
    const etlLogGroup = new logs.LogGroup(this, 'LightEtlLogGroup', {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    const etlFn = new lambda.Function(this, 'LightEtlFn', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`def handler(event, context):
  return {'status':'ok'}`),
      logGroup: etlLogGroup,
      environment: {
        RAW: rawBucket.bucketName,
        CUR: curatedBucket.bucketName,
      },
    });
    rawBucket.grantRead(etlFn);
    curatedBucket.grantReadWrite(etlFn);

    new events.Rule(this, 'RawToCuratedRule', {
      eventPattern: { source: ['aws.s3'], detailType: ['Object Created'] },
      targets: [new targets.LambdaFunction(etlFn)],
    });

    // === GLUE JOBS ===
    // Upload PySpark scripts to artifacts bucket
    const scriptsPrefix = 'glue-scripts';
    new s3deploy.BucketDeployment(this, 'UploadGlueScripts', {
      destinationBucket: artifactsBucket,
      destinationKeyPrefix: scriptsPrefix,
      sources: [s3deploy.Source.asset('glue-scripts')],
      prune: false,
    });

    // Role for Glue Jobs
    const glueJobRole = new iam.Role(this, 'GlueJobRole', {
      assumedBy: new iam.ServicePrincipal('glue.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSGlueServiceRole'),
      ],
    });
    rawBucket.grantRead(glueJobRole);
    curatedBucket.grantReadWrite(glueJobRole);
    artifactsBucket.grantRead(glueJobRole);

    const defaultArgs = {
      '--job-language': 'python',
      '--enable-glue-datacatalog': 'true',
      '--RAW_BUCKET': rawBucket.bucketName,
      '--CURATED_BUCKET': curatedBucket.bucketName,
    } as any;

    const cleaningJob = new glue.CfnJob(this, 'CleaningJob', {
      name: 'adpa-cleaning-job',
      role: glueJobRole.roleArn,
      glueVersion: '4.0',
      command: {
        name: 'glueetl',
        pythonVersion: '3',
        scriptLocation: `s3://${artifactsBucket.bucketName}/${scriptsPrefix}/cleaning.py`,
      },
      defaultArguments: defaultArgs,
      executionProperty: { maxConcurrentRuns: 1 },
      maxRetries: 1,
      numberOfWorkers: 2,
      workerType: 'G.1X',
      timeout: 30,
    });

    const featuresJob = new glue.CfnJob(this, 'FeaturesJob', {
      name: 'adpa-features-job',
      role: glueJobRole.roleArn,
      glueVersion: '4.0',
      command: {
        name: 'glueetl',
        pythonVersion: '3',
        scriptLocation: `s3://${artifactsBucket.bucketName}/${scriptsPrefix}/features.py`,
      },
      defaultArguments: defaultArgs,
      executionProperty: { maxConcurrentRuns: 1 },
      maxRetries: 1,
      numberOfWorkers: 2,
      workerType: 'G.1X',
      timeout: 30,
    });

    // === TRIGGERS (schedule + after-success chain) ===
    new glue.CfnTrigger(this, 'NightlyCleaningTrigger', {
      name: 'adpa-nightly-cleaning',
      type: 'SCHEDULED',
      schedule: 'cron(0 2 * * ? *)', // 2:00 UTC nightly
      actions: [{ jobName: cleaningJob.name! }],
    });

    new glue.CfnTrigger(this, 'OnCleaningSuccessRunFeatures', {
      name: 'adpa-cleaning-then-features',
      type: 'CONDITIONAL',
      startOnCreation: true,
      predicate: {
        logical: 'AND',
        conditions: [{
          jobName: cleaningJob.name!,
          state: 'SUCCEEDED',
          logicalOperator: 'EQUALS',
        }],
      },
      actions: [{ jobName: featuresJob.name! }],
    });

    // === (Optional) RDS JDBC Connection (parametrized) ===
    const rdsJdbcUrl = new CfnParameter(this, 'RdsJdbcUrl', {
      type: 'String',
      default: 'jdbc:mysql://your-host:3306/yourdb',
    });
    const rdsSecretArn = new CfnParameter(this, 'RdsSecretArn', { type: 'String', default: '' });
    const rdsSubnetId = new CfnParameter(this, 'RdsSubnetId', { type: 'String', default: '' });
    const rdsSgId = new CfnParameter(this, 'RdsSecurityGroupId', { type: 'String', default: '' });

    new glue.CfnConnection(this, 'RdsGlueConnection', {
      catalogId: this.account,
      connectionInput: {
        name: 'adpa-rds-connection',
        connectionType: 'JDBC',
        description: 'JDBC connection from Glue to RDS',
        connectionProperties: {
          JDBC_CONNECTION_URL: rdsJdbcUrl.valueAsString,
          SECRET_ID: rdsSecretArn.valueAsString,
        },
        physicalConnectionRequirements: {
          subnetId: rdsSubnetId.valueAsString || undefined,
          securityGroupIdList: rdsSgId.valueAsString ? [rdsSgId.valueAsString] : undefined,
        },
      },
    });

    // === Alerts: notify on FAILED job runs (EventBridge → SNS) ===
    const topic = new sns.Topic(this, 'GlueAlertsTopic');
    // Optional: add an email subscription via context/env if you want
    const email = this.node.tryGetContext('alertEmail');
    if (email) topic.addSubscription(new subs.EmailSubscription(email));

    new events.Rule(this, 'GlueJobFailedRule', {
      eventPattern: {
        source: ['aws.glue'],
        detailType: ['Glue Job State Change'],
        detail: { state: ['FAILED'] },
      },
      targets: [new targets.SnsTopic(topic)],
    });

    // === Outputs ===
    new CfnOutput(this, 'RawBucketName', { value: rawBucket.bucketName });
    new CfnOutput(this, 'CuratedBucketName', { value: curatedBucket.bucketName });
    new CfnOutput(this, 'ArtifactsBucketName', { value: artifactsBucket.bucketName });
    new CfnOutput(this, 'GlueDatabaseName', { value: 'adpa_raw_db' });
    new CfnOutput(this, 'RawCrawlerName', { value: rawCrawler.name! });
    new CfnOutput(this, 'CuratedCrawlerName', { value: curatedCrawler.name! });
    new CfnOutput(this, 'CleaningJobName', { value: cleaningJob.name! });
    new CfnOutput(this, 'FeaturesJobName', { value: featuresJob.name! });
  }
}