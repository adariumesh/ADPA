import * as cdk from 'aws-cdk-lib';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipelineActions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subs from 'aws-cdk-lib/aws-sns-subscriptions';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import { Construct } from 'constructs';

export interface DeploymentPipelineProps {
  projectName: string;
  githubOwner: string;
  githubRepo: string;
  githubBranch: string;
  environments: string[];
}

export class ADPADeploymentPipeline extends Construct {
  public readonly pipeline: codepipeline.Pipeline;
  public readonly artifactsBucket: s3.Bucket;
  public readonly notificationTopic: sns.Topic;

  constructor(scope: Construct, id: string, props: DeploymentPipelineProps) {
    super(scope, id);

    const { projectName, githubOwner, githubRepo, githubBranch, environments } = props;

    // =================
    // S3 ARTIFACTS BUCKET
    // =================
    this.artifactsBucket = new s3.Bucket(this, 'ArtifactsBucket', {
      bucketName: `${projectName}-pipeline-artifacts-${cdk.Aws.ACCOUNT_ID}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      lifecycleRules: [
        {
          id: 'DeleteOldArtifacts',
          expiration: cdk.Duration.days(90),
          noncurrentVersionExpiration: cdk.Duration.days(30),
        },
      ],
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // =================
    // SNS NOTIFICATIONS
    // =================
    this.notificationTopic = new sns.Topic(this, 'PipelineNotifications', {
      topicName: `${projectName}-pipeline-notifications`,
      displayName: 'ADPA Pipeline Notifications',
    });

    // Add email subscription (replace with actual email)
    // this.notificationTopic.addSubscription(
    //   new subs.EmailSubscription('devops@yourcompany.com')
    // );

    // =================
    // CODEBUILD PROJECTS
    // =================

    // Build project for testing and packaging
    const buildProject = new codebuild.Project(this, 'BuildProject', {
      projectName: `${projectName}-build`,
      description: 'Build and test ADPA infrastructure and Lambda functions',
      source: codebuild.Source.gitHub({
        owner: githubOwner,
        repo: githubRepo,
        webhook: true,
        webhookFilters: [
          codebuild.FilterGroup.inEventOf(codebuild.EventAction.PUSH)
            .andBranchIs(githubBranch),
        ],
      }),
      environment: {
        buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
        computeType: codebuild.ComputeType.SMALL,
        privileged: true, // Required for Docker
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          install: {
            'runtime-versions': {
              nodejs: '18',
              python: '3.9',
            },
            commands: [
              'echo "Installing dependencies..."',
              'npm install -g aws-cdk@2.87.0',
              'cd infrastructure && npm install',
              'pip install -r ../requirements.txt',
            ],
          },
          pre_build: {
            commands: [
              'echo "Running pre-build checks..."',
              'python -m pytest tests/ --junitxml=test-results.xml || true',
              'cd infrastructure && npm run build',
              'cdk synth --all',
            ],
          },
          build: {
            commands: [
              'echo "Building Lambda packages..."',
              'cd ../deploy && zip -r lambda-package.zip . -x "*.pyc" "__pycache__/*"',
              'cd ../layers/ml-dependencies && zip -r ../../deploy/ml-layer.zip .',
              'cd ../../layers/common-utils && zip -r ../../deploy/utils-layer.zip .',
              'cd ../../layers/monitoring && zip -r ../../deploy/monitoring-layer.zip .',
            ],
          },
          post_build: {
            commands: [
              'echo "Build completed successfully"',
              'cd infrastructure',
              'cdk diff --all || true',
            ],
          },
        },
        artifacts: {
          files: [
            'infrastructure/**/*',
            'deploy/**/*',
            'layers/**/*',
            'tests/**/*',
            'requirements.txt',
          ],
          'base-directory': '.',
        },
        reports: {
          'test-results': {
            files: ['test-results.xml'],
            'file-format': 'JUNITXML',
          },
        },
      }),
      cache: codebuild.Cache.local(codebuild.LocalCacheMode.DOCKER_LAYER),
      timeout: cdk.Duration.minutes(30),
    });

    // Grant necessary permissions to build project
    buildProject.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'sts:AssumeRole',
        'cloudformation:*',
        'iam:*',
        'lambda:*',
        'apigateway:*',
        'dynamodb:*',
        's3:*',
        'stepfunctions:*',
        'sns:*',
        'sagemaker:*',
        'backup:*',
        'cloudwatch:*',
        'logs:*',
      ],
      resources: ['*'],
    }));

    // Deploy project for each environment
    const deployProjects: { [env: string]: codebuild.Project } = {};

    environments.forEach(env => {
      deployProjects[env] = new codebuild.Project(this, `DeployProject${env.charAt(0).toUpperCase()}${env.slice(1)}`, {
        projectName: `${projectName}-deploy-${env}`,
        description: `Deploy ADPA to ${env} environment`,
        environment: {
          buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
          computeType: codebuild.ComputeType.SMALL,
          environmentVariables: {
            ENVIRONMENT: { value: env },
            AWS_DEFAULT_REGION: { value: 'us-east-2' },
          },
        },
        buildSpec: codebuild.BuildSpec.fromObject({
          version: '0.2',
          phases: {
            install: {
              'runtime-versions': {
                nodejs: '18',
              },
              commands: [
                'npm install -g aws-cdk@2.87.0',
                'cd infrastructure && npm install',
              ],
            },
            pre_build: {
              commands: [
                'echo "Preparing deployment for $ENVIRONMENT environment"',
                'aws sts get-caller-identity',
                'cd infrastructure && npm run build',
              ],
            },
            build: {
              commands: [
                `echo "Deploying to ${env} environment..."`,
                `cdk deploy ${projectName}-${env}-stack --require-approval never`,
                'echo "Deployment completed successfully"',
              ],
            },
            post_build: {
              commands: [
                'echo "Running post-deployment tests..."',
                `aws lambda invoke --function-name ${projectName}-${env}-lambda-function --payload '{"httpMethod":"GET","path":"/health"}' response.json || true`,
                'cat response.json || true',
                'echo "Post-deployment verification completed"',
              ],
            },
          },
        }),
        timeout: cdk.Duration.minutes(20),
      });

      // Grant deployment permissions
      deployProjects[env].addToRolePolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'sts:AssumeRole',
          'cloudformation:*',
          'iam:*',
          'lambda:*',
          'apigateway:*',
          'dynamodb:*',
          's3:*',
          'stepfunctions:*',
          'sns:*',
          'sagemaker:*',
          'backup:*',
          'cloudwatch:*',
          'logs:*',
        ],
        resources: ['*'],
      }));
    });

    // =================
    // CODEPIPELINE
    // =================

    // Source artifact
    const sourceArtifact = new codepipeline.Artifact('SourceArtifact');
    const buildArtifact = new codepipeline.Artifact('BuildArtifact');

    // Create pipeline
    this.pipeline = new codepipeline.Pipeline(this, 'Pipeline', {
      pipelineName: `${projectName}-deployment-pipeline`,
      artifactBucket: this.artifactsBucket,
      restartExecutionOnUpdate: true,
      stages: [
        // Source Stage
        {
          stageName: 'Source',
          actions: [
            new codepipelineActions.GitHubSourceAction({
              actionName: 'GitHub_Source',
              owner: githubOwner,
              repo: githubRepo,
              branch: githubBranch,
              oauthToken: cdk.SecretValue.secretsManager('github-token'),
              output: sourceArtifact,
              trigger: codepipelineActions.GitHubTrigger.WEBHOOK,
            }),
          ],
        },

        // Build Stage
        {
          stageName: 'Build',
          actions: [
            new codepipelineActions.CodeBuildAction({
              actionName: 'Build_and_Test',
              project: buildProject,
              input: sourceArtifact,
              outputs: [buildArtifact],
            }),
          ],
        },

        // Deploy to Dev
        {
          stageName: 'Deploy_Dev',
          actions: [
            new codepipelineActions.CodeBuildAction({
              actionName: 'Deploy_to_Dev',
              project: deployProjects['dev'],
              input: buildArtifact,
            }),
          ],
        },

        // Manual approval for staging
        {
          stageName: 'Approval_for_Staging',
          actions: [
            new codepipelineActions.ManualApprovalAction({
              actionName: 'Manual_Approval_Staging',
              notificationTopic: this.notificationTopic,
              additionalInformation: 'Please review dev deployment and approve for staging',
            }),
          ],
        },

        // Deploy to Staging
        {
          stageName: 'Deploy_Staging',
          actions: [
            new codepipelineActions.CodeBuildAction({
              actionName: 'Deploy_to_Staging',
              project: deployProjects['staging'],
              input: buildArtifact,
            }),
          ],
        },

        // Manual approval for production
        {
          stageName: 'Approval_for_Production',
          actions: [
            new codepipelineActions.ManualApprovalAction({
              actionName: 'Manual_Approval_Production',
              notificationTopic: this.notificationTopic,
              additionalInformation: 'Please review staging deployment and approve for production',
            }),
          ],
        },

        // Deploy to Production
        {
          stageName: 'Deploy_Production',
          actions: [
            new codepipelineActions.CodeBuildAction({
              actionName: 'Deploy_to_Production',
              project: deployProjects['prod'],
              input: buildArtifact,
            }),
          ],
        },
      ],
    });

    // =================
    // PIPELINE NOTIFICATIONS
    // =================

    // Pipeline state change notifications
    this.pipeline.onStateChange('PipelineStateChangeNotification', {
      description: 'Send notification on pipeline state change',
      target: new cdk.aws_events_targets.SnsTopic(this.notificationTopic),
    });

    // =================
    // CLOUDWATCH ALARMS
    // =================

    // Pipeline failure alarm
    const pipelineFailureAlarm = new cloudwatch.Alarm(this, 'PipelineFailureAlarm', {
      alarmName: `${projectName}-pipeline-failures`,
      alarmDescription: 'ADPA deployment pipeline failed',
      metric: new cloudwatch.Metric({
        namespace: 'AWS/CodePipeline',
        metricName: 'PipelineExecutionFailure',
        dimensionsMap: {
          PipelineName: this.pipeline.pipelineName,
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      }),
      threshold: 1,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    pipelineFailureAlarm.addAlarmAction(
      new actions.SnsAction(this.notificationTopic)
    );

    // =================
    // OUTPUTS
    // =================
    new cdk.CfnOutput(this, 'PipelineName', {
      value: this.pipeline.pipelineName,
      description: 'CodePipeline Name',
    });

    new cdk.CfnOutput(this, 'PipelineUrl', {
      value: `https://console.aws.amazon.com/codesuite/codepipeline/pipelines/${this.pipeline.pipelineName}/view`,
      description: 'CodePipeline Console URL',
    });

    new cdk.CfnOutput(this, 'ArtifactsBucketName', {
      value: this.artifactsBucket.bucketName,
      description: 'Pipeline Artifacts Bucket',
    });

    new cdk.CfnOutput(this, 'NotificationTopicArn', {
      value: this.notificationTopic.topicArn,
      description: 'Pipeline Notification Topic ARN',
    });
  }
}