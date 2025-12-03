import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sns from 'aws-cdk-lib/aws-sns';
import { Construct } from 'constructs';
export interface DeploymentPipelineProps {
    projectName: string;
    githubOwner: string;
    githubRepo: string;
    githubBranch: string;
    environments: string[];
}
export declare class ADPADeploymentPipeline extends Construct {
    readonly pipeline: codepipeline.Pipeline;
    readonly artifactsBucket: s3.Bucket;
    readonly notificationTopic: sns.Topic;
    constructor(scope: Construct, id: string, props: DeploymentPipelineProps);
}
