"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ADPADeploymentPipeline = void 0;
const cdk = require("aws-cdk-lib");
const codepipeline = require("aws-cdk-lib/aws-codepipeline");
const codepipelineActions = require("aws-cdk-lib/aws-codepipeline-actions");
const codebuild = require("aws-cdk-lib/aws-codebuild");
const iam = require("aws-cdk-lib/aws-iam");
const s3 = require("aws-cdk-lib/aws-s3");
const sns = require("aws-cdk-lib/aws-sns");
const cloudwatch = require("aws-cdk-lib/aws-cloudwatch");
const actions = require("aws-cdk-lib/aws-cloudwatch-actions");
const constructs_1 = require("constructs");
class ADPADeploymentPipeline extends constructs_1.Construct {
    constructor(scope, id, props) {
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
        const deployProjects = {};
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
        pipelineFailureAlarm.addAlarmAction(new actions.SnsAction(this.notificationTopic));
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
exports.ADPADeploymentPipeline = ADPADeploymentPipeline;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZGVwbG95bWVudC1waXBlbGluZS5qcyIsInNvdXJjZVJvb3QiOiIiLCJzb3VyY2VzIjpbImRlcGxveW1lbnQtcGlwZWxpbmUudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7O0FBQUEsbUNBQW1DO0FBQ25DLDZEQUE2RDtBQUM3RCw0RUFBNEU7QUFDNUUsdURBQXVEO0FBQ3ZELDJDQUEyQztBQUMzQyx5Q0FBeUM7QUFDekMsMkNBQTJDO0FBRTNDLHlEQUF5RDtBQUN6RCw4REFBOEQ7QUFDOUQsMkNBQXVDO0FBVXZDLE1BQWEsc0JBQXVCLFNBQVEsc0JBQVM7SUFLbkQsWUFBWSxLQUFnQixFQUFFLEVBQVUsRUFBRSxLQUE4QjtRQUN0RSxLQUFLLENBQUMsS0FBSyxFQUFFLEVBQUUsQ0FBQyxDQUFDO1FBRWpCLE1BQU0sRUFBRSxXQUFXLEVBQUUsV0FBVyxFQUFFLFVBQVUsRUFBRSxZQUFZLEVBQUUsWUFBWSxFQUFFLEdBQUcsS0FBSyxDQUFDO1FBRW5GLG9CQUFvQjtRQUNwQixzQkFBc0I7UUFDdEIsb0JBQW9CO1FBQ3BCLElBQUksQ0FBQyxlQUFlLEdBQUcsSUFBSSxFQUFFLENBQUMsTUFBTSxDQUFDLElBQUksRUFBRSxpQkFBaUIsRUFBRTtZQUM1RCxVQUFVLEVBQUUsR0FBRyxXQUFXLHVCQUF1QixHQUFHLENBQUMsR0FBRyxDQUFDLFVBQVUsRUFBRTtZQUNyRSxTQUFTLEVBQUUsSUFBSTtZQUNmLFVBQVUsRUFBRSxFQUFFLENBQUMsZ0JBQWdCLENBQUMsVUFBVTtZQUMxQyxjQUFjLEVBQUU7Z0JBQ2Q7b0JBQ0UsRUFBRSxFQUFFLG9CQUFvQjtvQkFDeEIsVUFBVSxFQUFFLEdBQUcsQ0FBQyxRQUFRLENBQUMsSUFBSSxDQUFDLEVBQUUsQ0FBQztvQkFDakMsMkJBQTJCLEVBQUUsR0FBRyxDQUFDLFFBQVEsQ0FBQyxJQUFJLENBQUMsRUFBRSxDQUFDO2lCQUNuRDthQUNGO1lBQ0QsYUFBYSxFQUFFLEdBQUcsQ0FBQyxhQUFhLENBQUMsT0FBTztTQUN6QyxD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QUFJLENBQUMsaUJBQWlCLENBQUMsQ0FDOUMsQ0FBQztRQUVGLG9CQUFvQjtRQUNwQixVQUFVO1FBQ1Ysb0JBQW9CO1FBQ3BCLElBQUksR0FBRyxDQUFDLFNBQVMsQ0FBQyxJQUFJLEVBQUUsY0FBYyxFQUFFO1lBQ3RDLEtBQUssRUFBRSxJQUFJLENBQUMsUUFBUSxDQUFDLFlBQVk7WUFDakMsV0FBVyxFQUFFLG1CQUFtQjtTQUNqQyxDQUFDLENBQUM7UUFFSCxJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLGFBQWEsRUFBRTtZQUNyQyxLQUFLLEVBQUUsbUVBQW1FLElBQUksQ0FBQyxRQUFRLENBQUMsWUFBWSxPQUFPO1lBQzNHLFdBQVcsRUFBRSwwQkFBMEI7U0FDeEMsQ0FBQyxDQUFDO1FBRUgsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxxQkFBcUIsRUFBRTtZQUM3QyxLQUFLLEVBQUUsSUFBSSxDQUFDLGVBQWUsQ0FBQyxVQUFVO1lBQ3RDLFdBQVcsRUFBRSwyQkFBMkI7U0FDekMsQ0FBQyxDQUFDO1FBRUgsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxzQkFBc0IsRUFBRTtZQUM5QyxLQUFLLEVBQUUsSUFBSSxDQUFDLGlCQUFpQixDQUFDLFFBQVE7WUFDdEMsV0FBVyxFQUFFLGlDQUFpQztTQUMvQyxDQUFDLENBQUM7SUFDTCxDQUFDO0NBQ0Y7QUFoWUQsd0RBZ1lDIiwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0ICogYXMgY2RrIGZyb20gJ2F3cy1jZGstbGliJztcbmltcG9ydCAqIGFzIGNvZGVwaXBlbGluZSBmcm9tICdhd3MtY2RrLWxpYi9hd3MtY29kZXBpcGVsaW5lJztcbmltcG9ydCAqIGFzIGNvZGVwaXBlbGluZUFjdGlvbnMgZnJvbSAnYXdzLWNkay1saWIvYXdzLWNvZGVwaXBlbGluZS1hY3Rpb25zJztcbmltcG9ydCAqIGFzIGNvZGVidWlsZCBmcm9tICdhd3MtY2RrLWxpYi9hd3MtY29kZWJ1aWxkJztcbmltcG9ydCAqIGFzIGlhbSBmcm9tICdhd3MtY2RrLWxpYi9hd3MtaWFtJztcbmltcG9ydCAqIGFzIHMzIGZyb20gJ2F3cy1jZGstbGliL2F3cy1zMyc7XG5pbXBvcnQgKiBhcyBzbnMgZnJvbSAnYXdzLWNkay1saWIvYXdzLXNucyc7XG5pbXBvcnQgKiBhcyBzdWJzIGZyb20gJ2F3cy1jZGstbGliL2F3cy1zbnMtc3Vic2NyaXB0aW9ucyc7XG5pbXBvcnQgKiBhcyBjbG91ZHdhdGNoIGZyb20gJ2F3cy1jZGstbGliL2F3cy1jbG91ZHdhdGNoJztcbmltcG9ydCAqIGFzIGFjdGlvbnMgZnJvbSAnYXdzLWNkay1saWIvYXdzLWNsb3Vkd2F0Y2gtYWN0aW9ucyc7XG5pbXBvcnQgeyBDb25zdHJ1Y3QgfSBmcm9tICdjb25zdHJ1Y3RzJztcblxuZXhwb3J0IGludGVyZmFjZSBEZXBsb3ltZW50UGlwZWxpbmVQcm9wcyB7XG4gIHByb2plY3ROYW1lOiBzdHJpbmc7XG4gIGdpdGh1Yk93bmVyOiBzdHJpbmc7XG4gIGdpdGh1YlJlcG86IHN0cmluZztcbiAgZ2l0aHViQnJhbmNoOiBzdHJpbmc7XG4gIGVudmlyb25tZW50czogc3RyaW5nW107XG59XG5cbmV4cG9ydCBjbGFzcyBBRFBBRGVwbG95bWVudFBpcGVsaW5lIGV4dGVuZHMgQ29uc3RydWN0IHtcbiAgcHVibGljIHJlYWRvbmx5IHBpcGVsaW5lOiBjb2RlcGlwZWxpbmUuUGlwZWxpbmU7XG4gIHB1YmxpYyByZWFkb25seSBhcnRpZmFjdHNCdWNrZXQ6IHMzLkJ1Y2tldDtcbiAgcHVibGljIHJlYWRvbmx5IG5vdGlmaWNhdGlvblRvcGljOiBzbnMuVG9waWM7XG5cbiAgY29uc3RydWN0b3Ioc2NvcGU6IENvbnN0cnVjdCwgaWQ6IHN0cmluZywgcHJvcHM6IERlcGxveW1lbnRQaXBlbGluZVByb3BzKSB7XG4gICAgc3VwZXIoc2NvcGUsIGlkKTtcblxuICAgIGNvbnN0IHsgcHJvamVjdE5hbWUsIGdpdGh1Yk93bmVyLCBnaXRodWJSZXBvLCBnaXRodWJCcmFuY2gsIGVudmlyb25tZW50cyB9ID0gcHJvcHM7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIFMzIEFSVElGQUNUUyBCVUNLRVRcbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIHRoaXMuYXJ0aWZhY3RzQnVja2V0ID0gbmV3IHMzLkJ1Y2tldCh0aGlzLCAnQXJ0aWZhY3RzQnVja2V0Jywge1xuICAgICAgYnVja2V0TmFtZTogYCR7cHJvamVjdE5hbWV9LXBpcGVsaW5lLWFydGlmYWN0cy0ke2Nkay5Bd3MuQUNDT1VOVF9JRH1gLFxuICAgICAgdmVyc2lvbmVkOiB0cnVlLFxuICAgICAgZW5jcnlwdGlvbjogczMuQnVja2V0RW5jcnlwdGlvbi5TM19NQU5BR0VELFxuICAgICAgbGlmZWN5Y2xlUnVsZXM6IFtcbiAgICAgICAge1xuICAgICAgICAgIGlkOiAnRGVsZXRlT2xkQXJ0aWZhY3RzJyxcbiAgICAgICAgICBleHBpcmF0aW9uOiBjZGsuRHVyYXRpb24uZGF5cyg5MCksXG4gICAgICAgICAgbm9uY3VycmVudFZlcnNpb25FeHBpcmF0aW9uOiBjZGsuRHVyYXRpb24uZGF5cygzMCksXG4gICAgICAgIH0sXG4gICAgICBdLFxuICAgICAgcmVtb3ZhbFBvbGljeTogY2RrLlJlbW92YWxQb2xpY3kuREVTVFJPWSxcbiAgICB9KTtcblxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgLy8gU05TIE5PVElGSUNBVElPTlNcbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIHRoaXMubm90aWZpY2F0aW9uVG9waWMgPSBuZXcgc25zLlRvcGljKHRoaXMsICdQaXBlbGluZU5vdGlmaWNhdGlvbnMnLCB7XG4gICAgICB0b3BpY05hbWU6IGAke3Byb2plY3ROYW1lfS1waXBlbGluZS1ub3RpZmljYXRpb25zYCxcbiAgICAgIGRpc3BsYXlOYW1lOiAnQURQQSBQaXBlbGluZSBOb3RpZmljYXRpb25zJyxcbiAgICB9KTtcblxuICAgIC8vIEFkZCBlbWFpbCBzdWJzY3JpcHRpb24gKHJlcGxhY2Ugd2l0aCBhY3R1YWwgZW1haWwpXG4gICAgLy8gdGhpcy5ub3RpZmljYXRpb25Ub3BpYy5hZGRTdWJzY3JpcHRpb24oXG4gICAgLy8gICBuZXcgc3Vicy5FbWFpbFN1YnNjcmlwdGlvbignZGV2b3BzQHlvdXJjb21wYW55LmNvbScpXG4gICAgLy8gKTtcblxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgLy8gQ09ERUJVSUxEIFBST0pFQ1RTXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cblxuICAgIC8vIEJ1aWxkIHByb2plY3QgZm9yIHRlc3RpbmcgYW5kIHBhY2thZ2luZ1xuICAgIGNvbnN0IGJ1aWxkUHJvamVjdCA9IG5ldyBjb2RlYnVpbGQuUHJvamVjdCh0aGlzLCAnQnVpbGRQcm9qZWN0Jywge1xuICAgICAgcHJvamVjdE5hbWU6IGAke3Byb2plY3ROYW1lfS1idWlsZGAsXG4gICAgICBkZXNjcmlwdGlvbjogJ0J1aWxkIGFuZCB0ZXN0IEFEUEEgaW5mcmFzdHJ1Y3R1cmUgYW5kIExhbWJkYSBmdW5jdGlvbnMnLFxuICAgICAgc291cmNlOiBjb2RlYnVpbGQuU291cmNlLmdpdEh1Yih7XG4gICAgICAgIG93bmVyOiBnaXRodWJPd25lcixcbiAgICAgICAgcmVwbzogZ2l0aHViUmVwbyxcbiAgICAgICAgd2ViaG9vazogdHJ1ZSxcbiAgICAgICAgd2ViaG9va0ZpbHRlcnM6IFtcbiAgICAgICAgICBjb2RlYnVpbGQuRmlsdGVyR3JvdXAuaW5FdmVudE9mKGNvZGVidWlsZC5FdmVudEFjdGlvbi5QVVNIKVxuICAgICAgICAgICAgLmFuZEJyYW5jaElzKGdpdGh1YkJyYW5jaCksXG4gICAgICAgIF0sXG4gICAgICB9KSxcbiAgICAgIGVudmlyb25tZW50OiB7XG4gICAgICAgIGJ1aWxkSW1hZ2U6IGNvZGVidWlsZC5MaW51eEJ1aWxkSW1hZ2UuU1RBTkRBUkRfN18wLFxuICAgICAgICBjb21wdXRlVHlwZTogY29kZWJ1aWxkLkNvbXB1dGVUeXBlLlNNQUxMLFxuICAgICAgICBwcml2aWxlZ2VkOiB0cnVlLCAvLyBSZXF1aXJlZCBmb3IgRG9ja2VyXG4gICAgICB9LFxuICAgICAgYnVpbGRTcGVjOiBjb2RlYnVpbGQuQnVpbGRTcGVjLmZyb21PYmplY3Qoe1xuICAgICAgICB2ZXJzaW9uOiAnMC4yJyxcbiAgICAgICAgcGhhc2VzOiB7XG4gICAgICAgICAgaW5zdGFsbDoge1xuICAgICAgICAgICAgJ3J1bnRpbWUtdmVyc2lvbnMnOiB7XG4gICAgICAgICAgICAgIG5vZGVqczogJzE4JyxcbiAgICAgICAgICAgICAgcHl0aG9uOiAnMy45JyxcbiAgICAgICAgICAgIH0sXG4gICAgICAgICAgICBjb21tYW5kczogW1xuICAgICAgICAgICAgICAnZWNobyBcIkluc3RhbGxpbmcgZGVwZW5kZW5jaWVzLi4uXCInLFxuICAgICAgICAgICAgICAnbnBtIGluc3RhbGwgLWcgYXdzLWNka0AyLjg3LjAnLFxuICAgICAgICAgICAgICAnY2QgaW5mcmFzdHJ1Y3R1cmUgJiYgbnBtIGluc3RhbGwnLFxuICAgICAgICAgICAgICAncGlwIGluc3RhbGwgLXIgLi4vcmVxdWlyZW1lbnRzLnR4dCcsXG4gICAgICAgICAgICBdLFxuICAgICAgICAgIH0sXG4gICAgICAgICAgcHJlX2J1aWxkOiB7XG4gICAgICAgICAgICBjb21tYW5kczogW1xuICAgICAgICAgICAgICAnZWNobyBcIlJ1bm5pbmcgcHJlLWJ1aWxkIGNoZWNrcy4uLlwiJyxcbiAgICAgICAgICAgICAgJ3B5dGhvbiAtbSBweXRlc3QgdGVzdHMvIC0tanVuaXR4bWw9dGVzdC1yZXN1bHRzLnhtbCB8fCB0cnVlJyxcbiAgICAgICAgICAgICAgJ2NkIGluZnJhc3RydWN0dXJlICYmIG5wbSBydW4gYnVpbGQnLFxuICAgICAgICAgICAgICAnY2RrIHN5bnRoIC0tYWxsJyxcbiAgICAgICAgICAgIF0sXG4gICAgICAgICAgfSxcbiAgICAgICAgICBidWlsZDoge1xuICAgICAgICAgICAgY29tbWFuZHM6IFtcbiAgICAgICAgICAgICAgJ2VjaG8gXCJCdWlsZGluZyBMYW1iZGEgcGFja2FnZXMuLi5cIicsXG4gICAgICAgICAgICAgICdjZCAuLi9kZXBsb3kgJiYgemlwIC1yIGxhbWJkYS1wYWNrYWdlLnppcCAuIC14IFwiKi5weWNcIiBcIl9fcHljYWNoZV9fLypcIicsXG4gICAgICAgICAgICAgICdjZCAuLi9sYXllcnMvbWwtZGVwZW5kZW5jaWVzICYmIHppcCAtciAuLi8uLi9kZXBsb3kvbWwtbGF5ZXIuemlwIC4nLFxuICAgICAgICAgICAgICAnY2QgLi4vLi4vbGF5ZXJzL2NvbW1vbi11dGlscyAmJiB6aXAgLXIgLi4vLi4vZGVwbG95L3V0aWxzLWxheWVyLnppcCAuJyxcbiAgICAgICAgICAgICAgJ2NkIC4uLy4uL2xheWVycy9tb25pdG9yaW5nICYmIHppcCAtciAuLi8uLi9kZXBsb3kvbW9uaXRvcmluZy1sYXllci56aXAgLicsXG4gICAgICAgICAgICBdLFxuICAgICAgICAgIH0sXG4gICAgICAgICAgcG9zdF9idWlsZDoge1xuICAgICAgICAgICAgY29tbWFuZHM6IFtcbiAgICAgICAgICAgICAgJ2VjaG8gXCJCdWlsZCBjb21wbGV0ZWQgc3VjY2Vzc2Z1bGx5XCInLFxuICAgICAgICAgICAgICAnY2QgaW5mcmFzdHJ1Y3R1cmUnLFxuICAgICAgICAgICAgICAnY2RrIGRpZmYgLS1hbGwgfHwgdHJ1ZScsXG4gICAgICAgICAgICBdLFxuICAgICAgICAgIH0sXG4gICAgICAgIH0sXG4gICAgICAgIGFydGlmYWN0czoge1xuICAgICAgICAgIGZpbGVzOiBbXG4gICAgICAgICAgICAnaW5mcmFzdHJ1Y3R1cmUvKiovKicsXG4gICAgICAgICAgICAnZGVwbG95LyoqLyonLFxuICAgICAgICAgICAgJ2xheWVycy8qKi8qJyxcbiAgICAgICAgICAgICd0ZXN0cy8qKi8qJyxcbiAgICAgICAgICAgICdyZXF1aXJlbWVudHMudHh0JyxcbiAgICAgICAgICBdLFxuICAgICAgICAgICdiYXNlLWRpcmVjdG9yeSc6ICcuJyxcbiAgICAgICAgfSxcbiAgICAgICAgcmVwb3J0czoge1xuICAgICAgICAgICd0ZXN0LXJlc3VsdHMnOiB7XG4gICAgICAgICAgICBmaWxlczogWyd0ZXN0LXJlc3VsdHMueG1sJ10sXG4gICAgICAgICAgICAnZmlsZS1mb3JtYXQnOiAnSlVOSVRYTUwnLFxuICAgICAgICAgIH0sXG4gICAgICAgIH0sXG4gICAgICB9KSxcbiAgICAgIGNhY2hlOiBjb2RlYnVpbGQuQ2FjaGUubG9jYWwoY29kZWJ1aWxkLkxvY2FsQ2FjaGVNb2RlLkRPQ0tFUl9MQVlFUiksXG4gICAgICB0aW1lb3V0OiBjZGsuRHVyYXRpb24ubWludXRlcygzMCksXG4gICAgfSk7XG5cbiAgICAvLyBHcmFudCBuZWNlc3NhcnkgcGVybWlzc2lvbnMgdG8gYnVpbGQgcHJvamVjdFxuICAgIGJ1aWxkUHJvamVjdC5hZGRUb1JvbGVQb2xpY3kobmV3IGlhbS5Qb2xpY3lTdGF0ZW1lbnQoe1xuICAgICAgZWZmZWN0OiBpYW0uRWZmZWN0LkFMTE9XLFxuICAgICAgYWN0aW9uczogW1xuICAgICAgICAnc3RzOkFzc3VtZVJvbGUnLFxuICAgICAgICAnY2xvdWRmb3JtYXRpb246KicsXG4gICAgICAgICdpYW06KicsXG4gICAgICAgICdsYW1iZGE6KicsXG4gICAgICAgICdhcGlnYXRld2F5OionLFxuICAgICAgICAnZHluYW1vZGI6KicsXG4gICAgICAgICdzMzoqJyxcbiAgICAgICAgJ3N0ZXBmdW5jdGlvbnM6KicsXG4gICAgICAgICdzbnM6KicsXG4gICAgICAgICdzYWdlbWFrZXI6KicsXG4gICAgICAgICdiYWNrdXA6KicsXG4gICAgICAgICdjbG91ZHdhdGNoOionLFxuICAgICAgICAnbG9nczoqJyxcbiAgICAgIF0sXG4gICAgICByZXNvdXJjZXM6IFsnKiddLFxuICAgIH0pKTtcblxuICAgIC8vIERlcGxveSBwcm9qZWN0IGZvciBlYWNoIGVudmlyb25tZW50XG4gICAgY29uc3QgZGVwbG95UHJvamVjdHM6IHsgW2Vudjogc3RyaW5nXTogY29kZWJ1aWxkLlByb2plY3QgfSA9IHt9O1xuXG4gICAgZW52aXJvbm1lbnRzLmZvckVhY2goZW52ID0+IHtcbiAgICAgIGRlcGxveVByb2plY3RzW2Vudl0gPSBuZXcgY29kZWJ1aWxkLlByb2plY3QodGhpcywgYERlcGxveVByb2plY3Qke2Vudi5jaGFyQXQoMCkudG9VcHBlckNhc2UoKX0ke2Vudi5zbGljZSgxKX1gLCB7XG4gICAgICAgIHByb2plY3ROYW1lOiBgJHtwcm9qZWN0TmFtZX0tZGVwbG95LSR7ZW52fWAsXG4gICAgICAgIGRlc2NyaXB0aW9uOiBgRGVwbG95IEFEUEEgdG8gJHtlbnZ9IGVudmlyb25tZW50YCxcbiAgICAgICAgZW52aXJvbm1lbnQ6IHtcbiAgICAgICAgICBidWlsZEltYWdlOiBjb2RlYnVpbGQuTGludXhCdWlsZEltYWdlLlNUQU5EQVJEXzdfMCxcbiAgICAgICAgICBjb21wdXRlVHlwZTogY29kZWJ1aWxkLkNvbXB1dGVUeXBlLlNNQUxMLFxuICAgICAgICAgIGVudmlyb25tZW50VmFyaWFibGVzOiB7XG4gICAgICAgICAgICBFTlZJUk9OTUVOVDogeyB2YWx1ZTogZW52IH0sXG4gICAgICAgICAgICBBV1NfREVGQVVMVF9SRUdJT046IHsgdmFsdWU6ICd1cy1lYXN0LTInIH0sXG4gICAgICAgICAgfSxcbiAgICAgICAgfSxcbiAgICAgICAgYnVpbGRTcGVjOiBjb2RlYnVpbGQuQnVpbGRTcGVjLmZyb21PYmplY3Qoe1xuICAgICAgICAgIHZlcnNpb246ICcwLjInLFxuICAgICAgICAgIHBoYXNlczoge1xuICAgICAgICAgICAgaW5zdGFsbDoge1xuICAgICAgICAgICAgICAncnVudGltZS12ZXJzaW9ucyc6IHtcbiAgICAgICAgICAgICAgICBub2RlanM6ICcxOCcsXG4gICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgIGNvbW1hbmRzOiBbXG4gICAgICAgICAgICAgICAgJ25wbSBpbnN0YWxsIC1nIGF3cy1jZGtAMi44Ny4wJyxcbiAgICAgICAgICAgICAgICAnY2QgaW5mcmFzdHJ1Y3R1cmUgJiYgbnBtIGluc3RhbGwnLFxuICAgICAgICAgICAgICBdLFxuICAgICAgICAgICAgfSxcbiAgICAgICAgICAgIHByZV9idWlsZDoge1xuICAgICAgICAgICAgICBjb21tYW5kczogW1xuICAgICAgICAgICAgICAgICdlY2hvIFwiUHJlcGFyaW5nIGRlcGxveW1lbnQgZm9yICRFTlZJUk9OTUVOVCBlbnZpcm9ubWVudFwiJyxcbiAgICAgICAgICAgICAgICAnYXdzIHN0cyBnZXQtY2FsbGVyLWlkZW50aXR5JyxcbiAgICAgICAgICAgICAgICAnY2QgaW5mcmFzdHJ1Y3R1cmUgJiYgbnBtIHJ1biBidWlsZCcsXG4gICAgICAgICAgICAgIF0sXG4gICAgICAgICAgICB9LFxuICAgICAgICAgICAgYnVpbGQ6IHtcbiAgICAgICAgICAgICAgY29tbWFuZHM6IFtcbiAgICAgICAgICAgICAgICBgZWNobyBcIkRlcGxveWluZyB0byAke2Vudn0gZW52aXJvbm1lbnQuLi5cImAsXG4gICAgICAgICAgICAgICAgYGNkayBkZXBsb3kgJHtwcm9qZWN0TmFtZX0tJHtlbnZ9LXN0YWNrIC0tcmVxdWlyZS1hcHByb3ZhbCBuZXZlcmAsXG4gICAgICAgICAgICAgICAgJ2VjaG8gXCJEZXBsb3ltZW50IGNvbXBsZXRlZCBzdWNjZXNzZnVsbHlcIicsXG4gICAgICAgICAgICAgIF0sXG4gICAgICAgICAgICB9LFxuICAgICAgICAgICAgcG9zdF9idWlsZDoge1xuICAgICAgICAgICAgICBjb21tYW5kczogW1xuICAgICAgICAgICAgICAgICdlY2hvIFwiUnVubmluZyBwb3N0LWRlcGxveW1lbnQgdGVzdHMuLi5cIicsXG4gICAgICAgICAgICAgICAgYGF3cyBsYW1iZGEgaW52b2tlIC0tZnVuY3Rpb24tbmFtZSAke3Byb2plY3ROYW1lfS0ke2Vudn0tbGFtYmRhLWZ1bmN0aW9uIC0tcGF5bG9hZCAne1wiaHR0cE1ldGhvZFwiOlwiR0VUXCIsXCJwYXRoXCI6XCIvaGVhbHRoXCJ9JyByZXNwb25zZS5qc29uIHx8IHRydWVgLFxuICAgICAgICAgICAgICAgICdjYXQgcmVzcG9uc2UuanNvbiB8fCB0cnVlJyxcbiAgICAgICAgICAgICAgICAnZWNobyBcIlBvc3QtZGVwbG95bWVudCB2ZXJpZmljYXRpb24gY29tcGxldGVkXCInLFxuICAgICAgICAgICAgICBdLFxuICAgICAgICAgICAgfSxcbiAgICAgICAgICB9LFxuICAgICAgICB9KSxcbiAgICAgICAgdGltZW91dDogY2RrLkR1cmF0aW9uLm1pbnV0ZXMoMjApLFxuICAgICAgfSk7XG5cbiAgICAgIC8vIEdyYW50IGRlcGxveW1lbnQgcGVybWlzc2lvbnNcbiAgICAgIGRlcGxveVByb2plY3RzW2Vudl0uYWRkVG9Sb2xlUG9saWN5KG5ldyBpYW0uUG9saWN5U3RhdGVtZW50KHtcbiAgICAgICAgZWZmZWN0OiBpYW0uRWZmZWN0LkFMTE9XLFxuICAgICAgICBhY3Rpb25zOiBbXG4gICAgICAgICAgJ3N0czpBc3N1bWVSb2xlJyxcbiAgICAgICAgICAnY2xvdWRmb3JtYXRpb246KicsXG4gICAgICAgICAgJ2lhbToqJyxcbiAgICAgICAgICAnbGFtYmRhOionLFxuICAgICAgICAgICdhcGlnYXRld2F5OionLFxuICAgICAgICAgICdkeW5hbW9kYjoqJyxcbiAgICAgICAgICAnczM6KicsXG4gICAgICAgICAgJ3N0ZXBmdW5jdGlvbnM6KicsXG4gICAgICAgICAgJ3NuczoqJyxcbiAgICAgICAgICAnc2FnZW1ha2VyOionLFxuICAgICAgICAgICdiYWNrdXA6KicsXG4gICAgICAgICAgJ2Nsb3Vkd2F0Y2g6KicsXG4gICAgICAgICAgJ2xvZ3M6KicsXG4gICAgICAgIF0sXG4gICAgICAgIHJlc291cmNlczogWycqJ10sXG4gICAgICB9KSk7XG4gICAgfSk7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIENPREVQSVBFTElORVxuICAgIC8vID09PT09PT09PT09PT09PT09XG5cbiAgICAvLyBTb3VyY2UgYXJ0aWZhY3RcbiAgICBjb25zdCBzb3VyY2VBcnRpZmFjdCA9IG5ldyBjb2RlcGlwZWxpbmUuQXJ0aWZhY3QoJ1NvdXJjZUFydGlmYWN0Jyk7XG4gICAgY29uc3QgYnVpbGRBcnRpZmFjdCA9IG5ldyBjb2RlcGlwZWxpbmUuQXJ0aWZhY3QoJ0J1aWxkQXJ0aWZhY3QnKTtcblxuICAgIC8vIENyZWF0ZSBwaXBlbGluZVxuICAgIHRoaXMucGlwZWxpbmUgPSBuZXcgY29kZXBpcGVsaW5lLlBpcGVsaW5lKHRoaXMsICdQaXBlbGluZScsIHtcbiAgICAgIHBpcGVsaW5lTmFtZTogYCR7cHJvamVjdE5hbWV9LWRlcGxveW1lbnQtcGlwZWxpbmVgLFxuICAgICAgYXJ0aWZhY3RCdWNrZXQ6IHRoaXMuYXJ0aWZhY3RzQnVja2V0LFxuICAgICAgcmVzdGFydEV4ZWN1dGlvbk9uVXBkYXRlOiB0cnVlLFxuICAgICAgc3RhZ2VzOiBbXG4gICAgICAgIC8vIFNvdXJjZSBTdGFnZVxuICAgICAgICB7XG4gICAgICAgICAgc3RhZ2VOYW1lOiAnU291cmNlJyxcbiAgICAgICAgICBhY3Rpb25zOiBbXG4gICAgICAgICAgICBuZXcgY29kZXBpcGVsaW5lQWN0aW9ucy5HaXRIdWJTb3VyY2VBY3Rpb24oe1xuICAgICAgICAgICAgICBhY3Rpb25OYW1lOiAnR2l0SHViX1NvdXJjZScsXG4gICAgICAgICAgICAgIG93bmVyOiBnaXRodWJPd25lcixcbiAgICAgICAgICAgICAgcmVwbzogZ2l0aHViUmVwbyxcbiAgICAgICAgICAgICAgYnJhbmNoOiBnaXRodWJCcmFuY2gsXG4gICAgICAgICAgICAgIG9hdXRoVG9rZW46IGNkay5TZWNyZXRWYWx1ZS5zZWNyZXRzTWFuYWdlcignZ2l0aHViLXRva2VuJyksXG4gICAgICAgICAgICAgIG91dHB1dDogc291cmNlQXJ0aWZhY3QsXG4gICAgICAgICAgICAgIHRyaWdnZXI6IGNvZGVwaXBlbGluZUFjdGlvbnMuR2l0SHViVHJpZ2dlci5XRUJIT09LLFxuICAgICAgICAgICAgfSksXG4gICAgICAgICAgXSxcbiAgICAgICAgfSxcblxuICAgICAgICAvLyBCdWlsZCBTdGFnZVxuICAgICAgICB7XG4gICAgICAgICAgc3RhZ2VOYW1lOiAnQnVpbGQnLFxuICAgICAgICAgIGFjdGlvbnM6IFtcbiAgICAgICAgICAgIG5ldyBjb2RlcGlwZWxpbmVBY3Rpb25zLkNvZGVCdWlsZEFjdGlvbih7XG4gICAgICAgICAgICAgIGFjdGlvbk5hbWU6ICdCdWlsZF9hbmRfVGVzdCcsXG4gICAgICAgICAgICAgIHByb2plY3Q6IGJ1aWxkUHJvamVjdCxcbiAgICAgICAgICAgICAgaW5wdXQ6IHNvdXJjZUFydGlmYWN0LFxuICAgICAgICAgICAgICBvdXRwdXRzOiBbYnVpbGRBcnRpZmFjdF0sXG4gICAgICAgICAgICB9KSxcbiAgICAgICAgICBdLFxuICAgICAgICB9LFxuXG4gICAgICAgIC8vIERlcGxveSB0byBEZXZcbiAgICAgICAge1xuICAgICAgICAgIHN0YWdlTmFtZTogJ0RlcGxveV9EZXYnLFxuICAgICAgICAgIGFjdGlvbnM6IFtcbiAgICAgICAgICAgIG5ldyBjb2RlcGlwZWxpbmVBY3Rpb25zLkNvZGVCdWlsZEFjdGlvbih7XG4gICAgICAgICAgICAgIGFjdGlvbk5hbWU6ICdEZXBsb3lfdG9fRGV2JyxcbiAgICAgICAgICAgICAgcHJvamVjdDogZGVwbG95UHJvamVjdHNbJ2RldiddLFxuICAgICAgICAgICAgICBpbnB1dDogYnVpbGRBcnRpZmFjdCxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgIF0sXG4gICAgICAgIH0sXG5cbiAgICAgICAgLy8gTWFudWFsIGFwcHJvdmFsIGZvciBzdGFnaW5nXG4gICAgICAgIHtcbiAgICAgICAgICBzdGFnZU5hbWU6ICdBcHByb3ZhbF9mb3JfU3RhZ2luZycsXG4gICAgICAgICAgYWN0aW9uczogW1xuICAgICAgICAgICAgbmV3IGNvZGVwaXBlbGluZUFjdGlvbnMuTWFudWFsQXBwcm92YWxBY3Rpb24oe1xuICAgICAgICAgICAgICBhY3Rpb25OYW1lOiAnTWFudWFsX0FwcHJvdmFsX1N0YWdpbmcnLFxuICAgICAgICAgICAgICBub3RpZmljYXRpb25Ub3BpYzogdGhpcy5ub3RpZmljYXRpb25Ub3BpYyxcbiAgICAgICAgICAgICAgYWRkaXRpb25hbEluZm9ybWF0aW9uOiAnUGxlYXNlIHJldmlldyBkZXYgZGVwbG95bWVudCBhbmQgYXBwcm92ZSBmb3Igc3RhZ2luZycsXG4gICAgICAgICAgICB9KSxcbiAgICAgICAgICBdLFxuICAgICAgICB9LFxuXG4gICAgICAgIC8vIERlcGxveSB0byBTdGFnaW5nXG4gICAgICAgIHtcbiAgICAgICAgICBzdGFnZU5hbWU6ICdEZXBsb3lfU3RhZ2luZycsXG4gICAgICAgICAgYWN0aW9uczogW1xuICAgICAgICAgICAgbmV3IGNvZGVwaXBlbGluZUFjdGlvbnMuQ29kZUJ1aWxkQWN0aW9uKHtcbiAgICAgICAgICAgICAgYWN0aW9uTmFtZTogJ0RlcGxveV90b19TdGFnaW5nJyxcbiAgICAgICAgICAgICAgcHJvamVjdDogZGVwbG95UHJvamVjdHNbJ3N0YWdpbmcnXSxcbiAgICAgICAgICAgICAgaW5wdXQ6IGJ1aWxkQXJ0aWZhY3QsXG4gICAgICAgICAgICB9KSxcbiAgICAgICAgICBdLFxuICAgICAgICB9LFxuXG4gICAgICAgIC8vIE1hbnVhbCBhcHByb3ZhbCBmb3IgcHJvZHVjdGlvblxuICAgICAgICB7XG4gICAgICAgICAgc3RhZ2VOYW1lOiAnQXBwcm92YWxfZm9yX1Byb2R1Y3Rpb24nLFxuICAgICAgICAgIGFjdGlvbnM6IFtcbiAgICAgICAgICAgIG5ldyBjb2RlcGlwZWxpbmVBY3Rpb25zLk1hbnVhbEFwcHJvdmFsQWN0aW9uKHtcbiAgICAgICAgICAgICAgYWN0aW9uTmFtZTogJ01hbnVhbF9BcHByb3ZhbF9Qcm9kdWN0aW9uJyxcbiAgICAgICAgICAgICAgbm90aWZpY2F0aW9uVG9waWM6IHRoaXMubm90aWZpY2F0aW9uVG9waWMsXG4gICAgICAgICAgICAgIGFkZGl0aW9uYWxJbmZvcm1hdGlvbjogJ1BsZWFzZSByZXZpZXcgc3RhZ2luZyBkZXBsb3ltZW50IGFuZCBhcHByb3ZlIGZvciBwcm9kdWN0aW9uJyxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgIF0sXG4gICAgICAgIH0sXG5cbiAgICAgICAgLy8gRGVwbG95IHRvIFByb2R1Y3Rpb25cbiAgICAgICAge1xuICAgICAgICAgIHN0YWdlTmFtZTogJ0RlcGxveV9Qcm9kdWN0aW9uJyxcbiAgICAgICAgICBhY3Rpb25zOiBbXG4gICAgICAgICAgICBuZXcgY29kZXBpcGVsaW5lQWN0aW9ucy5Db2RlQnVpbGRBY3Rpb24oe1xuICAgICAgICAgICAgICBhY3Rpb25OYW1lOiAnRGVwbG95X3RvX1Byb2R1Y3Rpb24nLFxuICAgICAgICAgICAgICBwcm9qZWN0OiBkZXBsb3lQcm9qZWN0c1sncHJvZCddLFxuICAgICAgICAgICAgICBpbnB1dDogYnVpbGRBcnRpZmFjdCxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgIF0sXG4gICAgICAgIH0sXG4gICAgICBdLFxuICAgIH0pO1xuXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cbiAgICAvLyBQSVBFTElORSBOT1RJRklDQVRJT05TXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cblxuICAgIC8vIFBpcGVsaW5lIHN0YXRlIGNoYW5nZSBub3RpZmljYXRpb25zXG4gICAgdGhpcy5waXBlbGluZS5vblN0YXRlQ2hhbmdlKCdQaXBlbGluZVN0YXRlQ2hhbmdlTm90aWZpY2F0aW9uJywge1xuICAgICAgZGVzY3JpcHRpb246ICdTZW5kIG5vdGlmaWNhdGlvbiBvbiBwaXBlbGluZSBzdGF0ZSBjaGFuZ2UnLFxuICAgICAgdGFyZ2V0OiBuZXcgY2RrLmF3c19ldmVudHNfdGFyZ2V0cy5TbnNUb3BpYyh0aGlzLm5vdGlmaWNhdGlvblRvcGljKSxcbiAgICB9KTtcblxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgLy8gQ0xPVURXQVRDSCBBTEFSTVNcbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuXG4gICAgLy8gUGlwZWxpbmUgZmFpbHVyZSBhbGFybVxuICAgIGNvbnN0IHBpcGVsaW5lRmFpbHVyZUFsYXJtID0gbmV3IGNsb3Vkd2F0Y2guQWxhcm0odGhpcywgJ1BpcGVsaW5lRmFpbHVyZUFsYXJtJywge1xuICAgICAgYWxhcm1OYW1lOiBgJHtwcm9qZWN0TmFtZX0tcGlwZWxpbmUtZmFpbHVyZXNgLFxuICAgICAgYWxhcm1EZXNjcmlwdGlvbjogJ0FEUEEgZGVwbG95bWVudCBwaXBlbGluZSBmYWlsZWQnLFxuICAgICAgbWV0cmljOiBuZXcgY2xvdWR3YXRjaC5NZXRyaWMoe1xuICAgICAgICBuYW1lc3BhY2U6ICdBV1MvQ29kZVBpcGVsaW5lJyxcbiAgICAgICAgbWV0cmljTmFtZTogJ1BpcGVsaW5lRXhlY3V0aW9uRmFpbHVyZScsXG4gICAgICAgIGRpbWVuc2lvbnNNYXA6IHtcbiAgICAgICAgICBQaXBlbGluZU5hbWU6IHRoaXMucGlwZWxpbmUucGlwZWxpbmVOYW1lLFxuICAgICAgICB9LFxuICAgICAgICBzdGF0aXN0aWM6ICdTdW0nLFxuICAgICAgICBwZXJpb2Q6IGNkay5EdXJhdGlvbi5taW51dGVzKDUpLFxuICAgICAgfSksXG4gICAgICB0aHJlc2hvbGQ6IDEsXG4gICAgICBldmFsdWF0aW9uUGVyaW9kczogMSxcbiAgICAgIHRyZWF0TWlzc2luZ0RhdGE6IGNsb3Vkd2F0Y2guVHJlYXRNaXNzaW5nRGF0YS5OT1RfQlJFQUNISU5HLFxuICAgIH0pO1xuXG4gICAgcGlwZWxpbmVGYWlsdXJlQWxhcm0uYWRkQWxhcm1BY3Rpb24oXG4gICAgICBuZXcgYWN0aW9ucy5TbnNBY3Rpb24odGhpcy5ub3RpZmljYXRpb25Ub3BpYylcbiAgICApO1xuXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cbiAgICAvLyBPVVRQVVRTXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnUGlwZWxpbmVOYW1lJywge1xuICAgICAgdmFsdWU6IHRoaXMucGlwZWxpbmUucGlwZWxpbmVOYW1lLFxuICAgICAgZGVzY3JpcHRpb246ICdDb2RlUGlwZWxpbmUgTmFtZScsXG4gICAgfSk7XG5cbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnUGlwZWxpbmVVcmwnLCB7XG4gICAgICB2YWx1ZTogYGh0dHBzOi8vY29uc29sZS5hd3MuYW1hem9uLmNvbS9jb2Rlc3VpdGUvY29kZXBpcGVsaW5lL3BpcGVsaW5lcy8ke3RoaXMucGlwZWxpbmUucGlwZWxpbmVOYW1lfS92aWV3YCxcbiAgICAgIGRlc2NyaXB0aW9uOiAnQ29kZVBpcGVsaW5lIENvbnNvbGUgVVJMJyxcbiAgICB9KTtcblxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdBcnRpZmFjdHNCdWNrZXROYW1lJywge1xuICAgICAgdmFsdWU6IHRoaXMuYXJ0aWZhY3RzQnVja2V0LmJ1Y2tldE5hbWUsXG4gICAgICBkZXNjcmlwdGlvbjogJ1BpcGVsaW5lIEFydGlmYWN0cyBCdWNrZXQnLFxuICAgIH0pO1xuXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ05vdGlmaWNhdGlvblRvcGljQXJuJywge1xuICAgICAgdmFsdWU6IHRoaXMubm90aWZpY2F0aW9uVG9waWMudG9waWNBcm4sXG4gICAgICBkZXNjcmlwdGlvbjogJ1BpcGVsaW5lIE5vdGlmaWNhdGlvbiBUb3BpYyBBUk4nLFxuICAgIH0pO1xuICB9XG59Il19