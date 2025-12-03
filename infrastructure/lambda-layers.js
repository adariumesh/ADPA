"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ADPALambdaLayers = void 0;
const cdk = require("aws-cdk-lib");
const lambda = require("aws-cdk-lib/aws-lambda");
const s3 = require("aws-cdk-lib/aws-s3");
const s3deploy = require("aws-cdk-lib/aws-s3-deployment");
const constructs_1 = require("constructs");
class ADPALambdaLayers extends constructs_1.Construct {
    constructor(scope, id, props) {
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
exports.ADPALambdaLayers = ADPALambdaLayers;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoibGFtYmRhLWxheWVycy5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbImxhbWJkYS1sYXllcnMudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7O0FBQUEsbUNBQW1DO0FBQ25DLGlEQUFpRDtBQUNqRCx5Q0FBeUM7QUFDekMsMERBQTBEO0FBQzFELDJDQUF1QztBQU92QyxNQUFhLGdCQUFpQixTQUFRLHNCQUFTO0lBSzdDLFlBQVksS0FBZ0IsRUFBRSxFQUFVLEVBQUUsS0FBd0I7UUFDaEUsS0FBSyxDQUFDLEtBQUssRUFBRSxFQUFFLENBQUMsQ0FBQztRQUVqQixNQUFNLEVBQUUsV0FBVyxFQUFFLFdBQVcsRUFBRSxHQUFHLEtBQUssQ0FBQztRQUMzQyxNQUFNLGNBQWMsR0FBRyxHQUFHLFdBQVcsSUFBSSxXQUFXLEVBQUUsQ0FBQztRQUV2RCxvQkFBb0I7UUFDcEIsOEJBQThCO1FBQzlCLG9CQUFvQjtRQUNwQixNQUFNLFlBQVksR0FBRyxJQUFJLEVBQUUsQ0FBQyxNQUFNLENBQUMsSUFBSSxFQUFFLGNBQWMsRUFBRTtZQUN2RCxVQUFVLEVBQUUsR0FBRyxjQUFjLGtCQUFrQixHQUFHLENBQUMsR0FBRyxDQUFDLFVBQVUsRUFBRTtZQUNuRSxTQUFTLEVBQUUsSUFBSTtZQUNmLFVBQVUsRUFBRSxFQUFFLENBQUMsZ0JBQWdCLENBQUMsVUFBVTtZQUMxQyxjQUFjLEVBQUU7Z0JBQ2Q7b0JBQ0UsRUFBRSxFQUFFLG1CQUFtQjtvQkFDdkIsMkJBQTJCLEVBQUUsR0FBRyxDQUFDLFFBQVEsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDO2lCQUNuRDthQUNGO1lBQ0QsYUFBYSxFQUFFLFdBQVcsS0FBSyxNQUFNLENBQUMsQ0FBQyxDQUFDLEdBQUcsQ0FBQyxhQUFhLENBQUMsTUFBTSxDQUFDLENBQUMsQ0FBQyxHQUFHLENBQUMsYUFBYSxDQUFDLE9BQU87U0FDN0YsQ0FBQyxDQUFDO1FBRUgsb0JBQW9CO1FBQ3BCLHdCQUF3QjtRQUN4QixvQkFBb0I7UUFD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QUFVLEVBQUUsR0FBRyxjQUFjLGVBQWU7U0FDN0MsQ0FBQyxDQUFDO1FBRUgsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxxQkFBcUIsRUFBRTtZQUM3QyxLQUFLLEVBQUUsSUFBSSxDQUFDLGdCQUFnQixDQUFDLGVBQWU7WUFDNUMsV0FBVyxFQUFFLHdCQUF3QjtZQUNyQyxVQUFVLEVBQUUsR0FBRyxjQUFjLGtCQUFrQjtTQUNoRCxDQUFDLENBQUM7UUFFSCxJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLG9CQUFvQixFQUFFO1lBQzVDLEtBQUssRUFBRSxJQUFJLENBQUMsZUFBZSxDQUFDLGVBQWU7WUFDM0MsV0FBVyxFQUFFLHNCQUFzQjtZQUNuQyxVQUFVLEVBQUUsR0FBRyxjQUFjLHVCQUF1QjtTQUNyRCxDQUFDLENBQUM7SUFDTCxDQUFDO0NBQ0Y7QUFyR0QsNENBcUdDIiwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0ICogYXMgY2RrIGZyb20gJ2F3cy1jZGstbGliJztcbmltcG9ydCAqIGFzIGxhbWJkYSBmcm9tICdhd3MtY2RrLWxpYi9hd3MtbGFtYmRhJztcbmltcG9ydCAqIGFzIHMzIGZyb20gJ2F3cy1jZGstbGliL2F3cy1zMyc7XG5pbXBvcnQgKiBhcyBzM2RlcGxveSBmcm9tICdhd3MtY2RrLWxpYi9hd3MtczMtZGVwbG95bWVudCc7XG5pbXBvcnQgeyBDb25zdHJ1Y3QgfSBmcm9tICdjb25zdHJ1Y3RzJztcblxuZXhwb3J0IGludGVyZmFjZSBMYW1iZGFMYXllcnNQcm9wcyB7XG4gIGVudmlyb25tZW50OiBzdHJpbmc7XG4gIHByb2plY3ROYW1lOiBzdHJpbmc7XG59XG5cbmV4cG9ydCBjbGFzcyBBRFBBTGFtYmRhTGF5ZXJzIGV4dGVuZHMgQ29uc3RydWN0IHtcbiAgcHVibGljIHJlYWRvbmx5IG1sRGVwZW5kZW5jaWVzTGF5ZXI6IGxhbWJkYS5MYXllclZlcnNpb247XG4gIHB1YmxpYyByZWFkb25seSBjb21tb25VdGlsc0xheWVyOiBsYW1iZGEuTGF5ZXJWZXJzaW9uO1xuICBwdWJsaWMgcmVhZG9ubHkgbW9uaXRvcmluZ0xheWVyOiBsYW1iZGEuTGF5ZXJWZXJzaW9uO1xuXG4gIGNvbnN0cnVjdG9yKHNjb3BlOiBDb25zdHJ1Y3QsIGlkOiBzdHJpbmcsIHByb3BzOiBMYW1iZGFMYXllcnNQcm9wcykge1xuICAgIHN1cGVyKHNjb3BlLCBpZCk7XG5cbiAgICBjb25zdCB7IGVudmlyb25tZW50LCBwcm9qZWN0TmFtZSB9ID0gcHJvcHM7XG4gICAgY29uc3QgcmVzb3VyY2VQcmVmaXggPSBgJHtwcm9qZWN0TmFtZX0tJHtlbnZpcm9ubWVudH1gO1xuXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cbiAgICAvLyBTMyBCVUNLRVQgRk9SIExBWUVSIFNUT1JBR0VcbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIGNvbnN0IGxheWVyc0J1Y2tldCA9IG5ldyBzMy5CdWNrZXQodGhpcywgJ0xheWVyc0J1Y2tldCcsIHtcbiAgICAgIGJ1Y2tldE5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1sYW1iZGEtbGF5ZXJzLSR7Y2RrLkF3cy5BQ0NPVU5UX0lEfWAsXG4gICAgICB2ZXJzaW9uZWQ6IHRydWUsXG4gICAgICBlbmNyeXB0aW9uOiBzMy5CdWNrZXRFbmNyeXB0aW9uLlMzX01BTkFHRUQsXG4gICAgICBsaWZlY3ljbGVSdWxlczogW1xuICAgICAgICB7XG4gICAgICAgICAgaWQ6ICdEZWxldGVPbGRWZXJzaW9ucycsXG4gICAgICAgICAgbm9uY3VycmVudFZlcnNpb25FeHBpcmF0aW9uOiBjZGsuRHVyYXRpb24uZGF5cygzMCksXG4gICAgICAgIH0sXG4gICAgICBdLFxuICAgICAgcmVtb3ZhbFBvbGljeTogZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/IGNkay5SZW1vdmFsUG9saWN5LlJFVEFJTiA6IGNkay5SZW1vdmFsUG9saWN5LkRFU1RST1ksXG4gICAgfSk7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIE1MIERFUEVOREVOQ0lFUyBMQVlFUlxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgdGhpcy5tbERlcGVuZGVuY2llc0xheWVyID0gbmV3IGxhbWJkYS5MYXllclZlcnNpb24odGhpcywgJ01MRGVwZW5kZW5jaWVzTGF5ZXInLCB7XG4gICAgICBsYXllclZlcnNpb25OYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tbWwtZGVwZW5kZW5jaWVzYCxcbiAgICAgIGNvZGU6IGxhbWJkYS5Db2RlLmZyb21Bc3NldCgnLi4vbGF5ZXJzL21sLWRlcGVuZGVuY2llcycsIHtcbiAgICAgICAgYnVuZGxpbmc6IHtcbiAgICAgICAgICBpbWFnZTogbGFtYmRhLlJ1bnRpbWUuUFlUSE9OXzNfOS5idW5kbGluZ0ltYWdlLFxuICAgICAgICAgIGNvbW1hbmQ6IFtcbiAgICAgICAgICAgICdiYXNoJywgJy1jJywgXG4gICAgICAgICAgICAncGlwIGluc3RhbGwgLXIgcmVxdWlyZW1lbnRzLnR4dCAtdCAvYXNzZXQtb3V0cHV0L3B5dGhvbiAmJiAnICtcbiAgICAgICAgICAgICdmaW5kIC9hc3NldC1vdXRwdXQgLW5hbWUgXCIqLnB5Y1wiIC1kZWxldGUgJiYgJyArXG4gICAgICAgICAgICAnZmluZCAvYXNzZXQtb3V0cHV0IC1uYW1lIFwiX19weWNhY2hlX19cIiAtdHlwZSBkIC1leGVjIHJtIC1yZiB7fSArIHx8IHRydWUnXG4gICAgICAgICAgXSxcbiAgICAgICAgfSxcbiAgICAgIH0pLFxuICAgICAgY29tcGF0aWJsZVJ1bnRpbWVzOiBbbGFtYmRhLlJ1bnRpbWUuUFlUSE9OXzNfOV0sXG4gICAgICBkZXNjcmlwdGlvbjogYE1MIGRlcGVuZGVuY2llcyBsYXllciBmb3IgQURQQSAke2Vudmlyb25tZW50fSAtIHBhbmRhcywgbnVtcHksIHNjaWtpdC1sZWFybiwgYm90bzNgLFxuICAgICAgcmVtb3ZhbFBvbGljeTogZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/IGNkay5SZW1vdmFsUG9saWN5LlJFVEFJTiA6IGNkay5SZW1vdmFsUG9saWN5LkRFU1RST1ksXG4gICAgfSk7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIENPTU1PTiBVVElMSVRJRVMgTEFZRVJcbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIHRoaXMuY29tbW9uVXRpbHNMYXllciA9IG5ldyBsYW1iZGEuTGF5ZXJWZXJzaW9uKHRoaXMsICdDb21tb25VdGlsc0xheWVyJywge1xuICAgICAgbGF5ZXJWZXJzaW9uTmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LWNvbW1vbi11dGlsc2AsXG4gICAgICBjb2RlOiBsYW1iZGEuQ29kZS5mcm9tQXNzZXQoJy4uL2xheWVycy9jb21tb24tdXRpbHMnKSxcbiAgICAgIGNvbXBhdGlibGVSdW50aW1lczogW2xhbWJkYS5SdW50aW1lLlBZVEhPTl8zXzldLFxuICAgICAgZGVzY3JpcHRpb246IGBDb21tb24gdXRpbGl0aWVzIGxheWVyIGZvciBBRFBBICR7ZW52aXJvbm1lbnR9IC0gbG9nZ2luZywgdmFsaWRhdGlvbiwgbWV0cmljc2AsXG4gICAgICByZW1vdmFsUG9saWN5OiBlbnZpcm9ubWVudCA9PT0gJ3Byb2QnID8gY2RrLlJlbW92YWxQb2xpY3kuUkVUQUlOIDogY2RrLlJlbW92YWxQb2xpY3kuREVTVFJPWSxcbiAgICB9KTtcblxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgLy8gTU9OSVRPUklORyBMQVlFUlxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgdGhpcy5tb25pdG9yaW5nTGF5ZXIgPSBuZXcgbGFtYmRhLkxheWVyVmVyc2lvbih0aGlzLCAnTW9uaXRvcmluZ0xheWVyJywge1xuICAgICAgbGF5ZXJWZXJzaW9uTmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LW1vbml0b3JpbmdgLFxuICAgICAgY29kZTogbGFtYmRhLkNvZGUuZnJvbUFzc2V0KCcuLi9sYXllcnMvbW9uaXRvcmluZycpLFxuICAgICAgY29tcGF0aWJsZVJ1bnRpbWVzOiBbbGFtYmRhLlJ1bnRpbWUuUFlUSE9OXzNfOV0sXG4gICAgICBkZXNjcmlwdGlvbjogYE1vbml0b3JpbmcgYW5kIG9ic2VydmFiaWxpdHkgbGF5ZXIgZm9yIEFEUEEgJHtlbnZpcm9ubWVudH0gLSBDbG91ZFdhdGNoLCBYLVJheSwgY3VzdG9tIG1ldHJpY3NgLFxuICAgICAgcmVtb3ZhbFBvbGljeTogZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/IGNkay5SZW1vdmFsUG9saWN5LlJFVEFJTiA6IGNkay5SZW1vdmFsUG9saWN5LkRFU1RST1ksXG4gICAgfSk7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIExBWUVSIERFUExPWU1FTlQgQVVUT01BVElPTlxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgbmV3IHMzZGVwbG95LkJ1Y2tldERlcGxveW1lbnQodGhpcywgJ0xheWVyQXJ0aWZhY3RzJywge1xuICAgICAgc291cmNlczogW3MzZGVwbG95LlNvdXJjZS5hc3NldCgnLi4vbGF5ZXJzJyldLFxuICAgICAgZGVzdGluYXRpb25CdWNrZXQ6IGxheWVyc0J1Y2tldCxcbiAgICAgIGRlc3RpbmF0aW9uS2V5UHJlZml4OiAnbGF5ZXItc291cmNlcy8nLFxuICAgICAgcmV0YWluT25EZWxldGU6IGVudmlyb25tZW50ID09PSAncHJvZCcsXG4gICAgfSk7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIE9VVFBVVFNcbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdNTERlcGVuZGVuY2llc0xheWVyQXJuJywge1xuICAgICAgdmFsdWU6IHRoaXMubWxEZXBlbmRlbmNpZXNMYXllci5sYXllclZlcnNpb25Bcm4sXG4gICAgICBkZXNjcmlwdGlvbjogJ01MIERlcGVuZGVuY2llcyBMYXllciBBUk4nLFxuICAgICAgZXhwb3J0TmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LW1sLWxheWVyLWFybmAsXG4gICAgfSk7XG5cbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnQ29tbW9uVXRpbHNMYXllckFybicsIHtcbiAgICAgIHZhbHVlOiB0aGlzLmNvbW1vblV0aWxzTGF5ZXIubGF5ZXJWZXJzaW9uQXJuLFxuICAgICAgZGVzY3JpcHRpb246ICdDb21tb24gVXRpbHMgTGF5ZXIgQVJOJyxcbiAgICAgIGV4cG9ydE5hbWU6IGAke3Jlc291cmNlUHJlZml4fS11dGlscy1sYXllci1hcm5gLFxuICAgIH0pO1xuXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ01vbml0b3JpbmdMYXllckFybicsIHtcbiAgICAgIHZhbHVlOiB0aGlzLm1vbml0b3JpbmdMYXllci5sYXllclZlcnNpb25Bcm4sXG4gICAgICBkZXNjcmlwdGlvbjogJ01vbml0b3JpbmcgTGF5ZXIgQVJOJyxcbiAgICAgIGV4cG9ydE5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1tb25pdG9yaW5nLWxheWVyLWFybmAsXG4gICAgfSk7XG4gIH1cbn0iXX0=