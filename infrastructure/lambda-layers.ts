import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import { Construct } from 'constructs';

export interface LambdaLayersProps {
  environment: string;
  projectName: string;
}

export class ADPALambdaLayers extends Construct {
  public readonly mlDependenciesLayer: lambda.LayerVersion;
  public readonly commonUtilsLayer: lambda.LayerVersion;
  public readonly monitoringLayer: lambda.LayerVersion;

  constructor(scope: Construct, id: string, props: LambdaLayersProps) {
    super(scope, id);

    const { environment, projectName } = props;
    const resourcePrefix = `${projectName}-${environment}`;

    // =================
    // S3 BUCKET FOR LAYER STORAGE
    // =================
    const layersBucket = new s3.Bucket(this, 'LayersBucket', {
      bucketName: `${resourcePrefix}-lambda-layers-${cdk.Aws.ACCOUNT_ID}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      lifecycleRules: [
        {
          id: 'DeleteOldVersions',
          noncurrentVersionExpiration: cdk.Duration.days(30),
        },
      ],
      removalPolicy: environment === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // =================
    // ML DEPENDENCIES LAYER
    // =================
    this.mlDependenciesLayer = new lambda.LayerVersion(this, 'MLDependenciesLayer', {
      layerVersionName: `${resourcePrefix}-ml-dependencies`,
      code: lambda.Code.fromAsset('../layers/ml-dependencies', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_9.bundlingImage,
          command: [
            'bash', '-c', 
            'pip install -r requirements.txt -t /asset-output/python && ' +
            'find /asset-output -name "*.pyc" -delete && ' +
            'find /asset-output -name "__pycache__" -type d -exec rm -rf {} + || true'
          ],
        },
      }),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_9],
      description: `ML dependencies layer for ADPA ${environment} - pandas, numpy, scikit-learn, boto3`,
      removalPolicy: environment === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // =================
    // COMMON UTILITIES LAYER
    // =================
    this.commonUtilsLayer = new lambda.LayerVersion(this, 'CommonUtilsLayer', {
      layerVersionName: `${resourcePrefix}-common-utils`,
      code: lambda.Code.fromAsset('../layers/common-utils'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_9],
      description: `Common utilities layer for ADPA ${environment} - logging, validation, metrics`,
      removalPolicy: environment === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // =================
    // MONITORING LAYER
    // =================
    this.monitoringLayer = new lambda.LayerVersion(this, 'MonitoringLayer', {
      layerVersionName: `${resourcePrefix}-monitoring`,
      code: lambda.Code.fromAsset('../layers/monitoring'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_9],
      description: `Monitoring and observability layer for ADPA ${environment} - CloudWatch, X-Ray, custom metrics`,
      removalPolicy: environment === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // =================
    // LAYER DEPLOYMENT AUTOMATION
    // =================
    new s3deploy.BucketDeployment(this, 'LayerArtifacts', {
      sources: [s3deploy.Source.asset('../layers')],
      destinationBucket: layersBucket,
      destinationKeyPrefix: 'layer-sources/',
      retainOnDelete: environment === 'prod',
    });

    // =================
    // OUTPUTS
    // =================
    new cdk.CfnOutput(this, 'MLDependenciesLayerArn', {
      value: this.mlDependenciesLayer.layerVersionArn,
      description: 'ML Dependencies Layer ARN',
      exportName: `${resourcePrefix}-ml-layer-arn`,
    });

    new cdk.CfnOutput(this, 'CommonUtilsLayerArn', {
      value: this.commonUtilsLayer.layerVersionArn,
      description: 'Common Utils Layer ARN',
      exportName: `${resourcePrefix}-utils-layer-arn`,
    });

    new cdk.CfnOutput(this, 'MonitoringLayerArn', {
      value: this.monitoringLayer.layerVersionArn,
      description: 'Monitoring Layer ARN',
      exportName: `${resourcePrefix}-monitoring-layer-arn`,
    });
  }
}