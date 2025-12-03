import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as backup from 'aws-cdk-lib/aws-backup';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import { Construct } from 'constructs';

export interface DynamoDBConfigProps {
  environment: string;
  projectName: string;
  table: dynamodb.Table;
}

export class ADPADynamoDBConfig extends Construct {
  public readonly backupVault: backup.BackupVault;
  public readonly backupPlan: backup.BackupPlan;

  constructor(scope: Construct, id: string, props: DynamoDBConfigProps) {
    super(scope, id);

    const { environment, projectName, table } = props;
    const resourcePrefix = `${projectName}-${environment}`;

    // =================
    // AUTO-SCALING CONFIGURATION
    // =================

    // Read capacity auto-scaling
    const readScaling = table.autoScaleReadCapacity({
      minCapacity: environment === 'prod' ? 5 : 1,
      maxCapacity: environment === 'prod' ? 4000 : 100,
    });

    readScaling.scaleOnUtilization({
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.seconds(60),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    // Write capacity auto-scaling
    const writeScaling = table.autoScaleWriteCapacity({
      minCapacity: environment === 'prod' ? 5 : 1,
      maxCapacity: environment === 'prod' ? 4000 : 100,
    });

    writeScaling.scaleOnUtilization({
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.seconds(60),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    // Auto-scaling for Global Secondary Index  
    // Note: GSI auto-scaling configured separately per index
      const gsiReadScaling = table.autoScaleGlobalSecondaryIndexReadCapacity('status-index', {
        minCapacity: environment === 'prod' ? 5 : 1,
        maxCapacity: environment === 'prod' ? 1000 : 50,
      });

      gsiReadScaling.scaleOnUtilization({
        targetUtilizationPercent: 70,
      });

      const gsiWriteScaling = table.autoScaleGlobalSecondaryIndexWriteCapacity('status-index', {
        minCapacity: environment === 'prod' ? 5 : 1,
        maxCapacity: environment === 'prod' ? 1000 : 50,
      });

      gsiWriteScaling.scaleOnUtilization({
        targetUtilizationPercent: 70,
      });

    // =================
    // BACKUP CONFIGURATION
    // =================

    // Backup vault with KMS encryption
    this.backupVault = new backup.BackupVault(this, 'BackupVault', {
      backupVaultName: `${resourcePrefix}-dynamodb-backup-vault`,
      encryptionKey: undefined, // Uses AWS managed key
      accessPolicy: new iam.PolicyDocument({
        statements: [
          new iam.PolicyStatement({
            effect: iam.Effect.DENY,
            principals: [new iam.AnyPrincipal()],
            actions: ['backup:DeleteBackupVault', 'backup:DeleteBackupPlan', 'backup:DeleteRecoveryPoint'],
            resources: ['*'],
            conditions: {
              StringNotEquals: {
                'aws:PrincipalServiceName': 'backup.amazonaws.com',
              },
            },
          }),
        ],
      }),
    });

    // Backup service role
    const backupRole = new iam.Role(this, 'BackupServiceRole', {
      roleName: `${resourcePrefix}-backup-service-role`,
      assumedBy: new iam.ServicePrincipal('backup.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSBackupServiceRolePolicyForBackup'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSBackupServiceRolePolicyForRestores'),
      ],
    });

    // Backup plan with different schedules for different environments
    this.backupPlan = new backup.BackupPlan(this, 'BackupPlan', {
      backupPlanName: `${resourcePrefix}-dynamodb-backup-plan`,
      backupVault: this.backupVault,
    });

    // Production backup schedule (daily + monthly)
    if (environment === 'prod') {
      // Daily backups retained for 35 days
      this.backupPlan.addRule(backup.BackupPlanRule.daily(this.backupVault, {
        ruleName: 'DailyBackups',
        deleteAfter: cdk.Duration.days(35),
        moveToColdStorageAfter: cdk.Duration.days(7),
        scheduleExpression: events.Schedule.cron({ hour: '2', minute: '0' }), // 2 AM UTC
      }));

      // Monthly backups retained for 1 year
      this.backupPlan.addRule(backup.BackupPlanRule.monthly1Year(this.backupVault, {
        ruleName: 'MonthlyBackups',
        scheduleExpression: events.Schedule.cron({ 
          hour: '3', 
          minute: '0', 
          day: '1' 
        }), // 1st of month at 3 AM UTC
      }));
    } else {
      // Development/staging: weekly backups retained for 2 weeks
      this.backupPlan.addRule(backup.BackupPlanRule.weekly(this.backupVault, {
        ruleName: 'WeeklyBackups',
        deleteAfter: cdk.Duration.days(14),
        scheduleExpression: events.Schedule.cron({ 
          hour: '4', 
          minute: '0', 
          weekDay: 'SUN' 
        }), // Sunday at 4 AM UTC
      }));
    }

    // Add DynamoDB table to backup plan
    this.backupPlan.addSelection('DynamoDBSelection', {
      resources: [
        backup.BackupResource.fromArn(table.tableArn),
      ],
      role: backupRole,
    });

    // =================
    // CLOUDWATCH ALARMS FOR TABLE HEALTH
    // =================

    // High read throttle alarm
    new cloudwatch.Alarm(this, 'ReadThrottleAlarm', {
      alarmName: `${resourcePrefix}-dynamodb-read-throttles`,
      alarmDescription: 'DynamoDB table experiencing read throttling',
      metric: table.metricThrottledRequests({
        dimensionsMap: { TableName: table.tableName, Operation: 'Query' },
        period: cdk.Duration.minutes(5),
      }),
      threshold: 1,
      evaluationPeriods: 2,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    // High write throttle alarm
    new cloudwatch.Alarm(this, 'WriteThrottleAlarm', {
      alarmName: `${resourcePrefix}-dynamodb-write-throttles`,
      alarmDescription: 'DynamoDB table experiencing write throttling',
      metric: table.metricThrottledRequests({
        dimensionsMap: { TableName: table.tableName, Operation: 'PutItem' },
        period: cdk.Duration.minutes(5),
      }),
      threshold: 1,
      evaluationPeriods: 2,
    });

    // High consumed read capacity alarm (85% threshold)
    new cloudwatch.Alarm(this, 'HighReadCapacityAlarm', {
      alarmName: `${resourcePrefix}-dynamodb-high-read-capacity`,
      alarmDescription: 'DynamoDB read capacity utilization above 85%',
      metric: table.metricConsumedReadCapacityUnits({
        period: cdk.Duration.minutes(5),
      }),
      threshold: 0.85,
      evaluationPeriods: 3,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
    });

    // High consumed write capacity alarm (85% threshold)
    new cloudwatch.Alarm(this, 'HighWriteCapacityAlarm', {
      alarmName: `${resourcePrefix}-dynamodb-high-write-capacity`,
      alarmDescription: 'DynamoDB write capacity utilization above 85%',
      metric: table.metricConsumedWriteCapacityUnits({
        period: cdk.Duration.minutes(5),
      }),
      threshold: 0.85,
      evaluationPeriods: 3,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
    });

    // =================
    // DATA LIFECYCLE MANAGEMENT
    // =================

    // Lambda function for data cleanup (optional - for old pipeline data)
    const cleanupFunction = new cdk.aws_lambda.Function(this, 'DataCleanupFunction', {
      functionName: `${resourcePrefix}-dynamodb-cleanup`,
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_9,
      handler: 'cleanup.handler',
      code: cdk.aws_lambda.Code.fromInline(`
import boto3
import json
from datetime import datetime, timedelta

def handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('${table.tableName}')
    
    # Delete pipeline records older than 90 days (for non-prod)
    if '${environment}' != 'prod':
        cutoff_date = datetime.now() - timedelta(days=90)
        cutoff_timestamp = int(cutoff_date.timestamp())
        
        try:
            response = table.scan(
                FilterExpression='#ts < :cutoff',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={':cutoff': cutoff_timestamp},
                ProjectionExpression='pipeline_id, #ts'
            )
            
            deleted_count = 0
            for item in response['Items']:
                table.delete_item(
                    Key={
                        'pipeline_id': item['pipeline_id'],
                        'timestamp': item['timestamp']
                    }
                )
                deleted_count += 1
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Deleted {deleted_count} old pipeline records',
                    'cutoff_date': cutoff_date.isoformat()
                })
            }
            
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Cleanup skipped for production environment'})
    }
      `),
      timeout: cdk.Duration.minutes(5),
      environment: {
        TABLE_NAME: table.tableName,
        ENVIRONMENT: environment,
      },
    });

    // Grant cleanup function permissions
    table.grantReadWriteData(cleanupFunction);

    // Schedule cleanup function (weekly for non-prod environments)
    if (environment !== 'prod') {
      new events.Rule(this, 'CleanupSchedule', {
        ruleName: `${resourcePrefix}-dynamodb-cleanup-schedule`,
        description: 'Weekly cleanup of old pipeline data',
        schedule: events.Schedule.cron({ hour: '1', minute: '0', weekDay: 'MON' }),
        targets: [new targets.LambdaFunction(cleanupFunction)],
      });
    }

    // =================
    // OUTPUTS
    // =================
    new cdk.CfnOutput(this, 'BackupVaultArn', {
      value: this.backupVault.backupVaultArn,
      description: 'DynamoDB Backup Vault ARN',
    });

    new cdk.CfnOutput(this, 'BackupPlanArn', {
      value: this.backupPlan.backupPlanArn,
      description: 'DynamoDB Backup Plan ARN',
    });

    new cdk.CfnOutput(this, 'AutoScalingStatus', {
      value: `Read: ${environment === 'prod' ? '5-4000' : '1-100'} | Write: ${environment === 'prod' ? '5-4000' : '1-100'}`,
      description: 'DynamoDB Auto-scaling Configuration',
    });
  }
}