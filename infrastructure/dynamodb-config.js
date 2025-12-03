"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ADPADynamoDBConfig = void 0;
const cdk = require("aws-cdk-lib");
const backup = require("aws-cdk-lib/aws-backup");
const iam = require("aws-cdk-lib/aws-iam");
const events = require("aws-cdk-lib/aws-events");
const targets = require("aws-cdk-lib/aws-events-targets");
const cloudwatch = require("aws-cdk-lib/aws-cloudwatch");
const constructs_1 = require("constructs");
class ADPADynamoDBConfig extends constructs_1.Construct {
    constructor(scope, id, props) {
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
        if (table.globalSecondaryIndexes) {
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
        }
        // =================
        // BACKUP CONFIGURATION
        // =================
        // Backup vault with KMS encryption
        this.backupVault = new backup.BackupVault(this, 'BackupVault', {
            backupVaultName: `${resourcePrefix}-dynamodb-backup-vault`,
            encryptionKey: undefined,
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
        }
        else {
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
            selectionName: `${resourcePrefix}-dynamodb-selection`,
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
                dimensions: { TableName: table.tableName, Operation: 'Query' },
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
                dimensions: { TableName: table.tableName, Operation: 'PutItem' },
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
exports.ADPADynamoDBConfig = ADPADynamoDBConfig;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZHluYW1vZGItY29uZmlnLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiZHluYW1vZGItY29uZmlnLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7OztBQUFBLG1DQUFtQztBQUVuQyxpREFBaUQ7QUFDakQsMkNBQTJDO0FBQzNDLGlEQUFpRDtBQUNqRCwwREFBMEQ7QUFDMUQseURBQXlEO0FBQ3pELDJDQUF1QztBQVF2QyxNQUFhLGtCQUFtQixTQUFRLHNCQUFTO0lBSS9DLFlBQVksS0FBZ0IsRUFBRSxFQUFVLEVBQUUsS0FBMEI7UUFDbEUsS0FBSyxDQUFDLEtBQUssRUFBRSxFQUFFLENBQUMsQ0FBQztRQUVqQixNQUFNLEVBQUUsV0FBVyxFQUFFLFdBQVcsRUFBRSxLQUFLLEVBQUUsR0FBRyxLQUFLLENBQUM7UUFDbEQsTUFBTSxjQUFjLEdBQUcsR0FBRyxXQUFXLElBQUksV0FBVyxFQUFFLENBQUM7UUFFdkQsb0JBQW9CO1FBQ3BCLDZCQUE2QjtRQUM3QixvQkFBb0I7UUFFcEIsNkJBQTZCO1FBQzdCLE1BQU0sV0FBVyxHQUFHLEtBQUssQ0FBQyxxQkFBcUIsQ0FBQztZQUM5QyxXQUFXLEVBQUUsV0FBVyxLQUFLLE1BQU0sQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDO1lBQzNDLFdBQVcsRUFBRSxXQUFXLEtBQUssTUFBTSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLEdBQUc7U0FDakQsQ0FBQyxDQUFDO1FBRUgsV0FBVyxDQUFDLGtCQUFrQixDQUFDO1lBQzdCLHdCQUF3QixFQUFFLEVBQUU7WUFDNUIsZUFBZSxFQUFFLEdBQUcsQ0FBQyxRQUFRLENBQUMsT0FBTyxDQUFDLEVBQUUsQ0FBQztZQUN6QyxnQkFBZ0IsRUFBRSxHQUFHLENBQUMsUUFBUSxDQUFDLE9BQU8sQ0FBQyxFQUFFLENBQUM7U0FDM0MsQ0FBQyxDQUFDO1FBRUgsOEJBQThCO1FBQzlCLE1BQU0sWUFBWSxHQUFHLEtBQUssQ0FB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QUUsR0FBRyxjQUFjLDRCQUE0QjtnQkFDdkQsV0FBVyxFQUFFLHFDQUFxQztnQkFDbEQsUUFBUSxFQUFFLE1BQU0sQ0FBQyxRQUFRLENBQUMsSUFBSSxDQUFDLEVBQUUsSUFBSSxFQUFFLEdBQUcsRUFBRSxNQUFNLEVBQUUsR0FBRyxFQUFFLE9BQU8sRUFBRSxLQUFLLEVBQUUsQ0FBQztnQkFDMUUsT0FBTyxFQUFFLENBQUMsSUFBSSxPQUFPLENBQUMsY0FBYyxDQUFDLGVBQWUsQ0FBQyxDQUFDO2FBQ3ZELENBQUMsQ0FBQztTQUNKO1FBRUQsb0JBQW9CO1FBQ3BCLFVBQVU7UUFDVixvQkFBb0I7UUFDcEIsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxnQkFBZ0IsRUFBRTtZQUN4QyxLQUFLLEVBQUUsSUFBSSxDQUFDLFdBQVcsQ0FBQyxjQUFjO1lBQ3RDLFdBQVcsRUFBRSwyQkFBMkI7U0FDekMsQ0FBQyxDQUFDO1FBRUgsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxlQUFlLEVBQUU7WUFDdkMsS0FBSyxFQUFFLElBQUksQ0FBQyxVQUFVLENBQUMsYUFBYTtZQUNwQyxXQUFXLEVBQUUsMEJBQTBCO1NBQ3hDLENBQUMsQ0FBQztRQUVILElBQUksR0FBRyxDQUFDLFNBQVMsQ0FBQyxJQUFJLEVBQUUsbUJBQW1CLEVBQUU7WUFDM0MsS0FBSyxFQUFFLFNBQVMsV0FBVyxLQUFLLE1BQU0sQ0FBQyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsQ0FBQyxPQUFPLGFBQWEsV0FBVyxLQUFLLE1BQU0sQ0FBQyxDQUFDLENBQUMsUUFBUSxDQUFDLENBQUMsQ0FBQyxPQUFPLEVBQUU7WUFDckgsV0FBVyxFQUFFLHFDQUFxQztTQUNuRCxDQUFDLENBQUM7SUFDTCxDQUFDO0NBQ0Y7QUFwU0QsZ0RBb1NDIiwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0ICogYXMgY2RrIGZyb20gJ2F3cy1jZGstbGliJztcbmltcG9ydCAqIGFzIGR5bmFtb2RiIGZyb20gJ2F3cy1jZGstbGliL2F3cy1keW5hbW9kYic7XG5pbXBvcnQgKiBhcyBiYWNrdXAgZnJvbSAnYXdzLWNkay1saWIvYXdzLWJhY2t1cCc7XG5pbXBvcnQgKiBhcyBpYW0gZnJvbSAnYXdzLWNkay1saWIvYXdzLWlhbSc7XG5pbXBvcnQgKiBhcyBldmVudHMgZnJvbSAnYXdzLWNkay1saWIvYXdzLWV2ZW50cyc7XG5pbXBvcnQgKiBhcyB0YXJnZXRzIGZyb20gJ2F3cy1jZGstbGliL2F3cy1ldmVudHMtdGFyZ2V0cyc7XG5pbXBvcnQgKiBhcyBjbG91ZHdhdGNoIGZyb20gJ2F3cy1jZGstbGliL2F3cy1jbG91ZHdhdGNoJztcbmltcG9ydCB7IENvbnN0cnVjdCB9IGZyb20gJ2NvbnN0cnVjdHMnO1xuXG5leHBvcnQgaW50ZXJmYWNlIER5bmFtb0RCQ29uZmlnUHJvcHMge1xuICBlbnZpcm9ubWVudDogc3RyaW5nO1xuICBwcm9qZWN0TmFtZTogc3RyaW5nO1xuICB0YWJsZTogZHluYW1vZGIuVGFibGU7XG59XG5cbmV4cG9ydCBjbGFzcyBBRFBBRHluYW1vREJDb25maWcgZXh0ZW5kcyBDb25zdHJ1Y3Qge1xuICBwdWJsaWMgcmVhZG9ubHkgYmFja3VwVmF1bHQ6IGJhY2t1cC5CYWNrdXBWYXVsdDtcbiAgcHVibGljIHJlYWRvbmx5IGJhY2t1cFBsYW46IGJhY2t1cC5CYWNrdXBQbGFuO1xuXG4gIGNvbnN0cnVjdG9yKHNjb3BlOiBDb25zdHJ1Y3QsIGlkOiBzdHJpbmcsIHByb3BzOiBEeW5hbW9EQkNvbmZpZ1Byb3BzKSB7XG4gICAgc3VwZXIoc2NvcGUsIGlkKTtcblxuICAgIGNvbnN0IHsgZW52aXJvbm1lbnQsIHByb2plY3ROYW1lLCB0YWJsZSB9ID0gcHJvcHM7XG4gICAgY29uc3QgcmVzb3VyY2VQcmVmaXggPSBgJHtwcm9qZWN0TmFtZX0tJHtlbnZpcm9ubWVudH1gO1xuXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cbiAgICAvLyBBVVRPLVNDQUxJTkcgQ09ORklHVVJBVElPTlxuICAgIC8vID09PT09PT09PT09PT09PT09XG5cbiAgICAvLyBSZWFkIGNhcGFjaXR5IGF1dG8tc2NhbGluZ1xuICAgIGNvbnN0IHJlYWRTY2FsaW5nID0gdGFibGUuYXV0b1NjYWxlUmVhZENhcGFjaXR5KHtcbiAgICAgIG1pbkNhcGFjaXR5OiBlbnZpcm9ubWVudCA9PT0gJ3Byb2QnID8gNSA6IDEsXG4gICAgICBtYXhDYXBhY2l0eTogZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/IDQwMDAgOiAxMDAsXG4gICAgfSk7XG5cbiAgICByZWFkU2NhbGluZy5zY2FsZU9uVXRpbGl6YXRpb24oe1xuICAgICAgdGFyZ2V0VXRpbGl6YXRpb25QZXJjZW50OiA3MCxcbiAgICAgIHNjYWxlSW5Db29sZG93bjogY2RrLkR1cmF0aW9uLnNlY29uZHMoNjApLFxuICAgICAgc2NhbGVPdXRDb29sZG93bjogY2RrLkR1cmF0aW9uLnNlY29uZHMoNjApLFxuICAgIH0pO1xuXG4gICAgLy8gV3JpdGUgY2FwYWNpdHkgYXV0by1zY2FsaW5nXG4gICAgY29uc3Qgd3JpdGVTY2FsaW5nID0gdGFibGUuYXV0b1NjYWxlV3JpdGVDYXBhY2l0eSh7XG4gICAgICBtaW5DYXBhY2l0eTogZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/IDUgOiAxLFxuICAgICAgbWF4Q2FwYWNpdHk6IGVudmlyb25tZW50ID09PSAncHJvZCcgPyA0MDAwIDogMTAwLFxuICAgIH0pO1xuXG4gICAgd3JpdGVTY2FsaW5nLnNjYWxlT25VdGlsaXphdGlvbih7XG4gICAgICB0YXJnZXRVdGlsaXphdGlvblBlcmNlbnQ6IDcwLFxuICAgICAgc2NhbGVJbkNvb2xkb3duOiBjZGsuRHVyYXRpb24uc2Vjb25kcyg2MCksXG4gICAgICBzY2FsZU91dENvb2xkb3duOiBjZGsuRHVyYXRpb24uc2Vjb25kcyg2MCksXG4gICAgfSk7XG5cbiAgICAvLyBBdXRvLXNjYWxpbmcgZm9yIEdsb2JhbCBTZWNvbmRhcnkgSW5kZXhcbiAgICBpZiAodGFibGUuZ2xvYmFsU2Vjb25kYXJ5SW5kZXhlcykge1xuICAgICAgY29uc3QgZ3NpUmVhZFNjYWxpbmcgPSB0YWJsZS5hdXRvU2NhbGVHbG9iYWxTZWNvbmRhcnlJbmRleFJlYWRDYXBhY2l0eSgnc3RhdHVzLWluZGV4Jywge1xuICAgICAgICBtaW5DYXBhY2l0eTogZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/IDUgOiAxLFxuICAgICAgICBtYXhDYXBhY2l0eTogZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/IDEwMDAgOiA1MCxcbiAgICAgIH0pO1xuXG4gICAgICBnc2lSZWFkU2NhbGluZy5zY2FsZU9uVXRpbGl6YXRpb24oe1xuICAgICAgICB0YXJnZXRVdGlsaXphdGlvblBlcmNlbnQ6IDcwLFxuICAgICAgfSk7XG5cbiAgICAgIGNvbnN0IGdzaVdyaXRlU2NhbGluZyA9IHRhYmxlLmF1dG9TY2FsZUdsb2JhbFNlY29uZGFyeUluZGV4V3JpdGVDYXBhY2l0eSgnc3RhdHVzLWluZGV4Jywge1xuICAgICAgICBtaW5DYXBhY2l0eTogZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/IDUgOiAxLFxuICAgICAgICBtYXhDYXBhY2l0eTogZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/IDEwMDAgOiA1MCxcbiAgICAgIH0pO1xuXG4gICAgICBnc2lXcml0ZVNjYWxpbmcuc2NhbGVPblV0aWxpemF0aW9uKHtcbiAgICAgICAgdGFyZ2V0VXRpbGl6YXRpb25QZXJjZW50OiA3MCxcbiAgICAgIH0pO1xuICAgIH1cblxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgLy8gQkFDS1VQIENPTkZJR1VSQVRJT05cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuXG4gICAgLy8gQmFja3VwIHZhdWx0IHdpdGggS01TIGVuY3J5cHRpb25cbiAgICB0aGlzLmJhY2t1cFZhdWx0ID0gbmV3IGJhY2t1cC5CYWNrdXBWYXVsdCh0aGlzLCAnQmFja3VwVmF1bHQnLCB7XG4gICAgICBiYWNrdXBWYXVsdE5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1keW5hbW9kYi1iYWNrdXAtdmF1bHRgLFxuICAgICAgZW5jcnlwdGlvbktleTogdW5kZWZpbmVkLCAvLyBVc2VzIEFXUyBtYW5hZ2VkIGtleVxuICAgICAgYWNjZXNzUG9saWN5OiBuZXcgaWFtLlBvbGljeURvY3VtZW50KHtcbiAgICAgICAgc3RhdGVtZW50czogW1xuICAgICAgICAgIG5ldyBpYW0uUG9saWN5U3RhdGVtZW50KHtcbiAgICAgICAgICAgIGVmZmVjdDogaWFtLkVmZmVjdC5ERU5ZLFxuICAgICAgICAgICAgcHJpbmNpcGFsczogW25ldyBpYW0uQW55UHJpbmNpcGFsKCldLFxuICAgICAgICAgICAgYWN0aW9uczogWydiYWNrdXA6RGVsZXRlQmFja3VwVmF1bHQnLCAnYmFja3VwOkRlbGV0ZUJhY2t1cFBsYW4nLCAnYmFja3VwOkRlbGV0ZVJlY292ZXJ5UG9pbnQnXSxcbiAgICAgICAgICAgIHJlc291cmNlczogWycqJ10sXG4gICAgICAgICAgICBjb25kaXRpb25zOiB7XG4gICAgICAgICAgICAgIFN0cmluZ05vdEVxdWFsczoge1xuICAgICAgICAgICAgICAgICdhd3M6UHJpbmNpcGFsU2VydmljZU5hbWUnOiAnYmFja3VwLmFtYXpvbmF3cy5jb20nLFxuICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgfSxcbiAgICAgICAgICB9KSxcbiAgICAgICAgXSxcbiAgICAgIH0pLFxuICAgIH0pO1xuXG4gICAgLy8gQmFja3VwIHNlcnZpY2Ugcm9sZVxuICAgIGNvbnN0IGJhY2t1cFJvbGUgPSBuZXcgaWFtLlJvbGUodGhpcywgJ0JhY2t1cFNlcnZpY2VSb2xlJywge1xuICAgICAgcm9sZU5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1iYWNrdXAtc2VydmljZS1yb2xlYCxcbiAgICAgIGFzc3VtZWRCeTogbmV3IGlhbS5TZXJ2aWNlUHJpbmNpcGFsKCdiYWNrdXAuYW1hem9uYXdzLmNvbScpLFxuICAgICAgbWFuYWdlZFBvbGljaWVzOiBbXG4gICAgICAgIGlhbS5NYW5hZ2VkUG9saWN5LmZyb21Bd3NNYW5hZ2VkUG9saWN5TmFtZSgnc2VydmljZS1yb2xlL0FXU0JhY2t1cFNlcnZpY2VSb2xlUG9saWN5Rm9yQmFja3VwJyksXG4gICAgICAgIGlhbS5NYW5hZ2VkUG9saWN5LmZyb21Bd3NNYW5hZ2VkUG9saWN5TmFtZSgnc2VydmljZS1yb2xlL0FXU0JhY2t1cFNlcnZpY2VSb2xlUG9saWN5Rm9yUmVzdG9yZXMnKSxcbiAgICAgIF0sXG4gICAgfSk7XG5cbiAgICAvLyBCYWNrdXAgcGxhbiB3aXRoIGRpZmZlcmVudCBzY2hlZHVsZXMgZm9yIGRpZmZlcmVudCBlbnZpcm9ubWVudHNcbiAgICB0aGlzLmJhY2t1cFBsYW4gPSBuZXcgYmFja3VwLkJhY2t1cFBsYW4odGhpcywgJ0JhY2t1cFBsYW4nLCB7XG4gICAgICBiYWNrdXBQbGFuTmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LWR5bmFtb2RiLWJhY2t1cC1wbGFuYCxcbiAgICAgIGJhY2t1cFZhdWx0OiB0aGlzLmJhY2t1cFZhdWx0LFxuICAgIH0pO1xuXG4gICAgLy8gUHJvZHVjdGlvbiBiYWNrdXAgc2NoZWR1bGUgKGRhaWx5ICsgbW9udGhseSlcbiAgICBpZiAoZW52aXJvbm1lbnQgPT09ICdwcm9kJykge1xuICAgICAgLy8gRGFpbHkgYmFja3VwcyByZXRhaW5lZCBmb3IgMzUgZGF5c1xuICAgICAgdGhpcy5iYWNrdXBQbGFuLmFkZFJ1bGUoYmFja3VwLkJhY2t1cFBsYW5SdWxlLmRhaWx5KHRoaXMuYmFja3VwVmF1bHQsIHtcbiAgICAgICAgcnVsZU5hbWU6ICdEYWlseUJhY2t1cHMnLFxuICAgICAgICBkZWxldGVBZnRlcjogY2RrLkR1cmF0aW9uLmRheXMoMzUpLFxuICAgICAgICBtb3ZlVG9Db2xkU3RvcmFnZUFmdGVyOiBjZGsuRHVyYXRpb24uZGF5cyg3KSxcbiAgICAgICAgc2NoZWR1bGVFeHByZXNzaW9uOiBldmVudHMuU2NoZWR1bGUuY3Jvbih7IGhvdXI6ICcyJywgbWludXRlOiAnMCcgfSksIC8vIDIgQU0gVVRDXG4gICAgICB9KSk7XG5cbiAgICAgIC8vIE1vbnRobHkgYmFja3VwcyByZXRhaW5lZCBmb3IgMSB5ZWFyXG4gICAgICB0aGlzLmJhY2t1cFBsYW4uYWRkUnVsZShiYWNrdXAuQmFja3VwUGxhblJ1bGUubW9udGhseTFZZWFyKHRoaXMuYmFja3VwVmF1bHQsIHtcbiAgICAgICAgcnVsZU5hbWU6ICdNb250aGx5QmFja3VwcycsXG4gICAgICAgIHNjaGVkdWxlRXhwcmVzc2lvbjogZXZlbnRzLlNjaGVkdWxlLmNyb24oeyBcbiAgICAgICAgICBob3VyOiAnMycsIFxuICAgICAgICAgIG1pbnV0ZTogJzAnLCBcbiAgICAgICAgICBkYXk6ICcxJyBcbiAgICAgICAgfSksIC8vIDFzdCBvZiBtb250aCBhdCAzIEFNIFVUQ1xuICAgICAgfSkpO1xuICAgIH0gZWxzZSB7XG4gICAgICAvLyBEZXZlbG9wbWVudC9zdGFnaW5nOiB3ZWVrbHkgYmFja3VwcyByZXRhaW5lZCBmb3IgMiB3ZWVrc1xuICAgICAgdGhpcy5iYWNrdXBQbGFuLmFkZFJ1bGUoYmFja3VwLkJhY2t1cFBsYW5SdWxlLndlZWtseSh0aGlzLmJhY2t1cFZhdWx0LCB7XG4gICAgICAgIHJ1bGVOYW1lOiAnV2Vla2x5QmFja3VwcycsXG4gICAgICAgIGRlbGV0ZUFmdGVyOiBjZGsuRHVyYXRpb24uZGF5cygxNCksXG4gICAgICAgIHNjaGVkdWxlRXhwcmVzc2lvbjogZXZlbnRzLlNjaGVkdWxlLmNyb24oeyBcbiAgICAgICAgICBob3VyOiAnNCcsIFxuICAgICAgICAgIG1pbnV0ZTogJzAnLCBcbiAgICAgICAgICB3ZWVrRGF5OiAnU1VOJyBcbiAgICAgICAgfSksIC8vIFN1bmRheSBhdCA0IEFNIFVUQ1xuICAgICAgfSkpO1xuICAgIH1cblxuICAgIC8vIEFkZCBEeW5hbW9EQiB0YWJsZSB0byBiYWNrdXAgcGxhblxuICAgIHRoaXMuYmFja3VwUGxhbi5hZGRTZWxlY3Rpb24oJ0R5bmFtb0RCU2VsZWN0aW9uJywge1xuICAgICAgc2VsZWN0aW9uTmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LWR5bmFtb2RiLXNlbGVjdGlvbmAsXG4gICAgICByZXNvdXJjZXM6IFtcbiAgICAgICAgYmFja3VwLkJhY2t1cFJlc291cmNlLmZyb21Bcm4odGFibGUudGFibGVBcm4pLFxuICAgICAgXSxcbiAgICAgIHJvbGU6IGJhY2t1cFJvbGUsXG4gICAgfSk7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIENMT1VEV0FUQ0ggQUxBUk1TIEZPUiBUQUJMRSBIRUFMVEhcbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuXG4gICAgLy8gSGlnaCByZWFkIHRocm90dGxlIGFsYXJtXG4gICAgbmV3IGNsb3Vkd2F0Y2guQWxhcm0odGhpcywgJ1JlYWRUaHJvdHRsZUFsYXJtJywge1xuICAgICAgYWxhcm1OYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tZHluYW1vZGItcmVhZC10aHJvdHRsZXNgLFxuICAgICAgYWxhcm1EZXNjcmlwdGlvbjogJ0R5bmFtb0RCIHRhYmxlIGV4cGVyaWVuY2luZyByZWFkIHRocm90dGxpbmcnLFxuICAgICAgbWV0cmljOiB0YWJsZS5tZXRyaWNUaHJvdHRsZWRSZXF1ZXN0cyh7XG4gICAgICAgIGRpbWVuc2lvbnM6IHsgVGFibGVOYW1lOiB0YWJsZS50YWJsZU5hbWUsIE9wZXJhdGlvbjogJ1F1ZXJ5JyB9LFxuICAgICAgICBwZXJpb2Q6IGNkay5EdXJhdGlvbi5taW51dGVzKDUpLFxuICAgICAgfSksXG4gICAgICB0aHJlc2hvbGQ6IDEsXG4gICAgICBldmFsdWF0aW9uUGVyaW9kczogMixcbiAgICAgIHRyZWF0TWlzc2luZ0RhdGE6IGNsb3Vkd2F0Y2guVHJlYXRNaXNzaW5nRGF0YS5OT1RfQlJFQUNISU5HLFxuICAgIH0pO1xuXG4gICAgLy8gSGlnaCB3cml0ZSB0aHJvdHRsZSBhbGFybVxuICAgIG5ldyBjbG91ZHdhdGNoLkFsYXJtKHRoaXMsICdXcml0ZVRocm90dGxlQWxhcm0nLCB7XG4gICAgICBhbGFybU5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1keW5hbW9kYi13cml0ZS10aHJvdHRsZXNgLFxuICAgICAgYWxhcm1EZXNjcmlwdGlvbjogJ0R5bmFtb0RCIHRhYmxlIGV4cGVyaWVuY2luZyB3cml0ZSB0aHJvdHRsaW5nJyxcbiAgICAgIG1ldHJpYzogdGFibGUubWV0cmljVGhyb3R0bGVkUmVxdWVzdHMoe1xuICAgICAgICBkaW1lbnNpb25zOiB7IFRhYmxlTmFtZTogdGFibGUudGFibGVOYW1lLCBPcGVyYXRpb246ICdQdXRJdGVtJyB9LFxuICAgICAgICBwZXJpb2Q6IGNkay5EdXJhdGlvbi5taW51dGVzKDUpLFxuICAgICAgfSksXG4gICAgICB0aHJlc2hvbGQ6IDEsXG4gICAgICBldmFsdWF0aW9uUGVyaW9kczogMixcbiAgICB9KTtcblxuICAgIC8vIEhpZ2ggY29uc3VtZWQgcmVhZCBjYXBhY2l0eSBhbGFybSAoODUlIHRocmVzaG9sZClcbiAgICBuZXcgY2xvdWR3YXRjaC5BbGFybSh0aGlzLCAnSGlnaFJlYWRDYXBhY2l0eUFsYXJtJywge1xuICAgICAgYWxhcm1OYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tZHluYW1vZGItaGlnaC1yZWFkLWNhcGFjaXR5YCxcbiAgICAgIGFsYXJtRGVzY3JpcHRpb246ICdEeW5hbW9EQiByZWFkIGNhcGFjaXR5IHV0aWxpemF0aW9uIGFib3ZlIDg1JScsXG4gICAgICBtZXRyaWM6IHRhYmxlLm1ldHJpY0NvbnN1bWVkUmVhZENhcGFjaXR5VW5pdHMoe1xuICAgICAgICBwZXJpb2Q6IGNkay5EdXJhdGlvbi5taW51dGVzKDUpLFxuICAgICAgfSksXG4gICAgICB0aHJlc2hvbGQ6IDAuODUsXG4gICAgICBldmFsdWF0aW9uUGVyaW9kczogMyxcbiAgICAgIGNvbXBhcmlzb25PcGVyYXRvcjogY2xvdWR3YXRjaC5Db21wYXJpc29uT3BlcmF0b3IuR1JFQVRFUl9USEFOX1RIUkVTSE9MRCxcbiAgICB9KTtcblxuICAgIC8vIEhpZ2ggY29uc3VtZWQgd3JpdGUgY2FwYWNpdHkgYWxhcm0gKDg1JSB0aHJlc2hvbGQpXG4gICAgbmV3IGNsb3Vkd2F0Y2guQWxhcm0odGhpcywgJ0hpZ2hXcml0ZUNhcGFjaXR5QWxhcm0nLCB7XG4gICAgICBhbGFybU5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1keW5hbW9kYi1oaWdoLXdyaXRlLWNhcGFjaXR5YCxcbiAgICAgIGFsYXJtRGVzY3JpcHRpb246ICdEeW5hbW9EQiB3cml0ZSBjYXBhY2l0eSB1dGlsaXphdGlvbiBhYm92ZSA4NSUnLFxuICAgICAgbWV0cmljOiB0YWJsZS5tZXRyaWNDb25zdW1lZFdyaXRlQ2FwYWNpdHlVbml0cyh7XG4gICAgICAgIHBlcmlvZDogY2RrLkR1cmF0aW9uLm1pbnV0ZXMoNSksXG4gICAgICB9KSxcbiAgICAgIHRocmVzaG9sZDogMC44NSxcbiAgICAgIGV2YWx1YXRpb25QZXJpb2RzOiAzLFxuICAgICAgY29tcGFyaXNvbk9wZXJhdG9yOiBjbG91ZHdhdGNoLkNvbXBhcmlzb25PcGVyYXRvci5HUkVBVEVSX1RIQU5fVEhSRVNIT0xELFxuICAgIH0pO1xuXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cbiAgICAvLyBEQVRBIExJRkVDWUNMRSBNQU5BR0VNRU5UXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cblxuICAgIC8vIExhbWJkYSBmdW5jdGlvbiBmb3IgZGF0YSBjbGVhbnVwIChvcHRpb25hbCAtIGZvciBvbGQgcGlwZWxpbmUgZGF0YSlcbiAgICBjb25zdCBjbGVhbnVwRnVuY3Rpb24gPSBuZXcgY2RrLmF3c19sYW1iZGEuRnVuY3Rpb24odGhpcywgJ0RhdGFDbGVhbnVwRnVuY3Rpb24nLCB7XG4gICAgICBmdW5jdGlvbk5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1keW5hbW9kYi1jbGVhbnVwYCxcbiAgICAgIHJ1bnRpbWU6IGNkay5hd3NfbGFtYmRhLlJ1bnRpbWUuUFlUSE9OXzNfOSxcbiAgICAgIGhhbmRsZXI6ICdjbGVhbnVwLmhhbmRsZXInLFxuICAgICAgY29kZTogY2RrLmF3c19sYW1iZGEuQ29kZS5mcm9tSW5saW5lKGBcbmltcG9ydCBib3RvM1xuaW1wb3J0IGpzb25cbmZyb20gZGF0ZXRpbWUgaW1wb3J0IGRhdGV0aW1lLCB0aW1lZGVsdGFcblxuZGVmIGhhbmRsZXIoZXZlbnQsIGNvbnRleHQpOlxuICAgIGR5bmFtb2RiID0gYm90bzMucmVzb3VyY2UoJ2R5bmFtb2RiJylcbiAgICB0YWJsZSA9IGR5bmFtb2RiLlRhYmxlKCcke3RhYmxlLnRhYmxlTmFtZX0nKVxuICAgIFxuICAgICMgRGVsZXRlIHBpcGVsaW5lIHJlY29yZHMgb2xkZXIgdGhhbiA5MCBkYXlzIChmb3Igbm9uLXByb2QpXG4gICAgaWYgJyR7ZW52aXJvbm1lbnR9JyAhPSAncHJvZCc6XG4gICAgICAgIGN1dG9mZl9kYXRlID0gZGF0ZXRpbWUubm93KCkgLSB0aW1lZGVsdGEoZGF5cz05MClcbiAgICAgICAgY3V0b2ZmX3RpbWVzdGFtcCA9IGludChjdXRvZmZfZGF0ZS50aW1lc3RhbXAoKSlcbiAgICAgICAgXG4gICAgICAgIHRyeTpcbiAgICAgICAgICAgIHJlc3BvbnNlID0gdGFibGUuc2NhbihcbiAgICAgICAgICAgICAgICBGaWx0ZXJFeHByZXNzaW9uPScjdHMgPCA6Y3V0b2ZmJyxcbiAgICAgICAgICAgICAgICBFeHByZXNzaW9uQXR0cmlidXRlTmFtZXM9eycjdHMnOiAndGltZXN0YW1wJ30sXG4gICAgICAgICAgICAgICAgRXhwcmVzc2lvbkF0dHJpYnV0ZVZhbHVlcz17JzpjdXRvZmYnOiBjdXRvZmZfdGltZXN0YW1wfSxcbiAgICAgICAgICAgICAgICBQcm9qZWN0aW9uRXhwcmVzc2lvbj0ncGlwZWxpbmVfaWQsICN0cydcbiAgICAgICAgICAgIClcbiAgICAgICAgICAgIFxuICAgICAgICAgICAgZGVsZXRlZF9jb3VudCA9IDBcbiAgICAgICAgICAgIGZvciBpdGVtIGluIHJlc3BvbnNlWydJdGVtcyddOlxuICAgICAgICAgICAgICAgIHRhYmxlLmRlbGV0ZV9pdGVtKFxuICAgICAgICAgICAgICAgICAgICBLZXk9e1xuICAgICAgICAgICAgICAgICAgICAgICAgJ3BpcGVsaW5lX2lkJzogaXRlbVsncGlwZWxpbmVfaWQnXSxcbiAgICAgICAgICAgICAgICAgICAgICAgICd0aW1lc3RhbXAnOiBpdGVtWyd0aW1lc3RhbXAnXVxuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgKVxuICAgICAgICAgICAgICAgIGRlbGV0ZWRfY291bnQgKz0gMVxuICAgICAgICAgICAgXG4gICAgICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgICAgICdzdGF0dXNDb2RlJzogMjAwLFxuICAgICAgICAgICAgICAgICdib2R5JzoganNvbi5kdW1wcyh7XG4gICAgICAgICAgICAgICAgICAgICdtZXNzYWdlJzogZidEZWxldGVkIHtkZWxldGVkX2NvdW50fSBvbGQgcGlwZWxpbmUgcmVjb3JkcycsXG4gICAgICAgICAgICAgICAgICAgICdjdXRvZmZfZGF0ZSc6IGN1dG9mZl9kYXRlLmlzb2Zvcm1hdCgpXG4gICAgICAgICAgICAgICAgfSlcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIFxuICAgICAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6XG4gICAgICAgICAgICByZXR1cm4ge1xuICAgICAgICAgICAgICAgICdzdGF0dXNDb2RlJzogNTAwLFxuICAgICAgICAgICAgICAgICdib2R5JzoganNvbi5kdW1wcyh7J2Vycm9yJzogc3RyKGUpfSlcbiAgICAgICAgICAgIH1cbiAgICBcbiAgICByZXR1cm4ge1xuICAgICAgICAnc3RhdHVzQ29kZSc6IDIwMCxcbiAgICAgICAgJ2JvZHknOiBqc29uLmR1bXBzKHsnbWVzc2FnZSc6ICdDbGVhbnVwIHNraXBwZWQgZm9yIHByb2R1Y3Rpb24gZW52aXJvbm1lbnQnfSlcbiAgICB9XG4gICAgICBgKSxcbiAgICAgIHRpbWVvdXQ6IGNkay5EdXJhdGlvbi5taW51dGVzKDUpLFxuICAgICAgZW52aXJvbm1lbnQ6IHtcbiAgICAgICAgVEFCTEVfTkFNRTogdGFibGUudGFibGVOYW1lLFxuICAgICAgICBFTlZJUk9OTUVOVDogZW52aXJvbm1lbnQsXG4gICAgICB9LFxuICAgIH0pO1xuXG4gICAgLy8gR3JhbnQgY2xlYW51cCBmdW5jdGlvbiBwZXJtaXNzaW9uc1xuICAgIHRhYmxlLmdyYW50UmVhZFdyaXRlRGF0YShjbGVhbnVwRnVuY3Rpb24pO1xuXG4gICAgLy8gU2NoZWR1bGUgY2xlYW51cCBmdW5jdGlvbiAod2Vla2x5IGZvciBub24tcHJvZCBlbnZpcm9ubWVudHMpXG4gICAgaWYgKGVudmlyb25tZW50ICE9PSAncHJvZCcpIHtcbiAgICAgIG5ldyBldmVudHMuUnVsZSh0aGlzLCAnQ2xlYW51cFNjaGVkdWxlJywge1xuICAgICAgICBydWxlTmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LWR5bmFtb2RiLWNsZWFudXAtc2NoZWR1bGVgLFxuICAgICAgICBkZXNjcmlwdGlvbjogJ1dlZWtseSBjbGVhbnVwIG9mIG9sZCBwaXBlbGluZSBkYXRhJyxcbiAgICAgICAgc2NoZWR1bGU6IGV2ZW50cy5TY2hlZHVsZS5jcm9uKHsgaG91cjogJzEnLCBtaW51dGU6ICcwJywgd2Vla0RheTogJ01PTicgfSksXG4gICAgICAgIHRhcmdldHM6IFtuZXcgdGFyZ2V0cy5MYW1iZGFGdW5jdGlvbihjbGVhbnVwRnVuY3Rpb24pXSxcbiAgICAgIH0pO1xuICAgIH1cblxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgLy8gT1VUUFVUU1xuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0JhY2t1cFZhdWx0QXJuJywge1xuICAgICAgdmFsdWU6IHRoaXMuYmFja3VwVmF1bHQuYmFja3VwVmF1bHRBcm4sXG4gICAgICBkZXNjcmlwdGlvbjogJ0R5bmFtb0RCIEJhY2t1cCBWYXVsdCBBUk4nLFxuICAgIH0pO1xuXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0JhY2t1cFBsYW5Bcm4nLCB7XG4gICAgICB2YWx1ZTogdGhpcy5iYWNrdXBQbGFuLmJhY2t1cFBsYW5Bcm4sXG4gICAgICBkZXNjcmlwdGlvbjogJ0R5bmFtb0RCIEJhY2t1cCBQbGFuIEFSTicsXG4gICAgfSk7XG5cbiAgICBuZXcgY2RrLkNmbk91dHB1dCh0aGlzLCAnQXV0b1NjYWxpbmdTdGF0dXMnLCB7XG4gICAgICB2YWx1ZTogYFJlYWQ6ICR7ZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/ICc1LTQwMDAnIDogJzEtMTAwJ30gfCBXcml0ZTogJHtlbnZpcm9ubWVudCA9PT0gJ3Byb2QnID8gJzUtNDAwMCcgOiAnMS0xMDAnfWAsXG4gICAgICBkZXNjcmlwdGlvbjogJ0R5bmFtb0RCIEF1dG8tc2NhbGluZyBDb25maWd1cmF0aW9uJyxcbiAgICB9KTtcbiAgfVxufSJdfQ==