import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as backup from 'aws-cdk-lib/aws-backup';
import { Construct } from 'constructs';
export interface DynamoDBConfigProps {
    environment: string;
    projectName: string;
    table: dynamodb.Table;
}
export declare class ADPADynamoDBConfig extends Construct {
    readonly backupVault: backup.BackupVault;
    readonly backupPlan: backup.BackupPlan;
    constructor(scope: Construct, id: string, props: DynamoDBConfigProps);
}
