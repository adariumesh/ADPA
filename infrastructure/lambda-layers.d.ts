import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
export interface LambdaLayersProps {
    environment: string;
    projectName: string;
}
export declare class ADPALambdaLayers extends Construct {
    readonly mlDependenciesLayer: lambda.LayerVersion;
    readonly commonUtilsLayer: lambda.LayerVersion;
    readonly monitoringLayer: lambda.LayerVersion;
    constructor(scope: Construct, id: string, props: LambdaLayersProps);
}
