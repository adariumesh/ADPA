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
            this.backupPlan.addRule(new backup.BackupPlanRule({
                ruleName: 'DailyBackups',
                deleteAfter: cdk.Duration.days(35),
                moveToColdStorageAfter: cdk.Duration.days(7),
                backupVault: this.backupVault,
                scheduleExpression: events.Schedule.cron({ hour: '2', minute: '0' }), // 2 AM UTC
            }));
            // Monthly backups retained for 1 year
            this.backupPlan.addRule(new backup.BackupPlanRule({
                ruleName: 'MonthlyBackups',
                backupVault: this.backupVault,
                scheduleExpression: events.Schedule.cron({
                    hour: '3',
                    minute: '0',
                    day: '1'
                }), // 1st of month at 3 AM UTC
            }));
        }
        else {
            // Development/staging: weekly backups retained for 2 weeks
            this.backupPlan.addRule(new backup.BackupPlanRule({
                ruleName: 'WeeklyBackups',
                deleteAfter: cdk.Duration.days(14),
                backupVault: this.backupVault,
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
exports.ADPADynamoDBConfig = ADPADynamoDBConfig;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZHluYW1vZGItY29uZmlnLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiZHluYW1vZGItY29uZmlnLnRzIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7OztBQUFBLG1DQUFtQztBQUVuQyxpREFBaUQ7QUFDakQsMkNBQTJDO0FBQzNDLGlEQUFpRDtBQUNqRCwwREFBMEQ7QUFDMUQseURBQXlEO0FBQ3pELDJDQUF1QztBQVF2QyxNQUFhLGtCQUFtQixTQUFRLHNCQUFTO0lBSS9DLFlBQVksS0FBZ0IsRUFBRSxFQUFVLEVBQUUsS0FBMEI7UUFDbEUsS0FBSyxDQUFDLEtBQUssRUFBRSxFQUFFLENBQUMsQ0FBQztRQUVqQixNQUFNLEVBQUUsV0FBVyxFQUFFLFdBQVcsRUFBRSxLQUFLLEVBQUUsR0FBRyxLQUFLLENBQUM7UUFDbEQsTUFBTSxjQUFjLEdBQUcsR0FBRyxXQUFXLElBQUksV0FBVyxFQUFFLENBQUM7UUFFdkQsb0JBQW9CO1FBQ3BCLDZCQUE2QjtRQUM3QixvQkFBb0I7UUFFcEIsNkJBQTZCO1FBQzdCLE1BQU0sV0FBVyxHQUFHLEtBQUssQ0FBQyxxQkFBcUIsQ0FBQztZQUM5QyxXQUFXLEVBQUUsV0FBVyxLQUFLLE1BQU0sQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDLENBQUMsQ0FBQyxDQUFDO1lBQzNDLFdBQVcsRUFBRSxXQUFXLEtBQUssTUFBTSxDQUFDLENBQUMsQ0FBQyxJQUFJLENBQUMsQ0FBQyxDQUFDLEdBQUc7U0FDakQsQ0FBQyxDQUFDO1FBRUgsV0FBVyxDQUFDLGtCQUFrQixDQUFDO1lBQzdCLHdCQUF3QixFQUFFLEVBQUU7WUFDNUIsZUFBZSxFQUFFLEdBQUcsQ0FBQyxRQUFRLENBQUMsT0FBTyxDQUFDLEVBQUUsQ0FBQztZQUN6QyxnQkFBZ0IsRUFBRSxHQUFHLENBQUMsUUFBUSxDQUFDLE9BQU8sQ0FBQyxFQUFFLENBQUM7U0FDM0MsQ0FBQyxDQUFDO1FBRUgsOEJBQThCO1FBQzlCLE1BQU0sWUFBWSxHQUFHLEtBQUssQ0FB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O2dCQUNsRCxRQUFRLEVBQUUsTUFBTSxDQUFDLFFBQVEsQ0FBQyxJQUFJLENBQUMsRUFBRSxJQUFJLEVBQUUsR0FBRyxFQUFFLE1BQU0sRUFBRSxHQUFHLEVBQUUsT0FBTyxFQUFFLEtBQUssRUFBRSxDQUFDO2dCQUMxRSxPQUFPLEVBQUUsQ0FBQyxJQUFJLE9BQU8sQ0FBQyxjQUFjLENBQUMsZUFBZSxDQUFDLENBQUM7YUFDdkQsQ0FBQyxDQUFDO1NBQ0o7UUFFRCxvQkFBb0I7UUFDcEIsVUFBVTtRQUNWLG9CQUFvQjtRQUNwQixJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLGdCQUFnQixFQUFFO1lBQ3hDLEtBQUssRUFBRSxJQUFJLENBQUMsV0FBVyxDQUFDLGNBQWM7WUFDdEMsV0FBVyxFQUFFLDJCQUEyQjtTQUN6QyxDQUFDLENBQUM7UUFFSCxJQUFJLEdBQUcsQ0FBQyxTQUFTLENBQUMsSUFBSSxFQUFFLGVBQWUsRUFBRTtZQUN2QyxLQUFLLEVBQUUsSUFBSSxDQUFDLFVBQVUsQ0FBQyxhQUFhO1lBQ3BDLFdBQVcsRUFBRSwwQkFBMEI7U0FDeEMsQ0FBQyxDQUFDO1FBRUgsSUFBSSxHQUFHLENBQUMsU0FBUyxDQUFDLElBQUksRUFBRSxtQkFBbUIsRUFBRTtZQUMzQyxLQUFLLEVBQUUsU0FBUyxXQUFXLEtBQUssTUFBTSxDQUFDLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxDQUFDLE9BQU8sYUFBYSxXQUFXLEtBQUssTUFBTSxDQUFDLENBQUMsQ0FBQyxRQUFRLENBQUMsQ0FBQyxDQUFDLE9BQU8sRUFBRTtZQUNySCxXQUFXLEVBQUUscUNBQXFDO1NBQ25ELENBQUMsQ0FBQztJQUNMLENBQUM7Q0FDRjtBQXJTRCxnREFxU0MiLCJzb3VyY2VzQ29udGVudCI6WyJpbXBvcnQgKiBhcyBjZGsgZnJvbSAnYXdzLWNkay1saWInO1xuaW1wb3J0ICogYXMgZHluYW1vZGIgZnJvbSAnYXdzLWNkay1saWIvYXdzLWR5bmFtb2RiJztcbmltcG9ydCAqIGFzIGJhY2t1cCBmcm9tICdhd3MtY2RrLWxpYi9hd3MtYmFja3VwJztcbmltcG9ydCAqIGFzIGlhbSBmcm9tICdhd3MtY2RrLWxpYi9hd3MtaWFtJztcbmltcG9ydCAqIGFzIGV2ZW50cyBmcm9tICdhd3MtY2RrLWxpYi9hd3MtZXZlbnRzJztcbmltcG9ydCAqIGFzIHRhcmdldHMgZnJvbSAnYXdzLWNkay1saWIvYXdzLWV2ZW50cy10YXJnZXRzJztcbmltcG9ydCAqIGFzIGNsb3Vkd2F0Y2ggZnJvbSAnYXdzLWNkay1saWIvYXdzLWNsb3Vkd2F0Y2gnO1xuaW1wb3J0IHsgQ29uc3RydWN0IH0gZnJvbSAnY29uc3RydWN0cyc7XG5cbmV4cG9ydCBpbnRlcmZhY2UgRHluYW1vREJDb25maWdQcm9wcyB7XG4gIGVudmlyb25tZW50OiBzdHJpbmc7XG4gIHByb2plY3ROYW1lOiBzdHJpbmc7XG4gIHRhYmxlOiBkeW5hbW9kYi5UYWJsZTtcbn1cblxuZXhwb3J0IGNsYXNzIEFEUEFEeW5hbW9EQkNvbmZpZyBleHRlbmRzIENvbnN0cnVjdCB7XG4gIHB1YmxpYyByZWFkb25seSBiYWNrdXBWYXVsdDogYmFja3VwLkJhY2t1cFZhdWx0O1xuICBwdWJsaWMgcmVhZG9ubHkgYmFja3VwUGxhbjogYmFja3VwLkJhY2t1cFBsYW47XG5cbiAgY29uc3RydWN0b3Ioc2NvcGU6IENvbnN0cnVjdCwgaWQ6IHN0cmluZywgcHJvcHM6IER5bmFtb0RCQ29uZmlnUHJvcHMpIHtcbiAgICBzdXBlcihzY29wZSwgaWQpO1xuXG4gICAgY29uc3QgeyBlbnZpcm9ubWVudCwgcHJvamVjdE5hbWUsIHRhYmxlIH0gPSBwcm9wcztcbiAgICBjb25zdCByZXNvdXJjZVByZWZpeCA9IGAke3Byb2plY3ROYW1lfS0ke2Vudmlyb25tZW50fWA7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIEFVVE8tU0NBTElORyBDT05GSUdVUkFUSU9OXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cblxuICAgIC8vIFJlYWQgY2FwYWNpdHkgYXV0by1zY2FsaW5nXG4gICAgY29uc3QgcmVhZFNjYWxpbmcgPSB0YWJsZS5hdXRvU2NhbGVSZWFkQ2FwYWNpdHkoe1xuICAgICAgbWluQ2FwYWNpdHk6IGVudmlyb25tZW50ID09PSAncHJvZCcgPyA1IDogMSxcbiAgICAgIG1heENhcGFjaXR5OiBlbnZpcm9ubWVudCA9PT0gJ3Byb2QnID8gNDAwMCA6IDEwMCxcbiAgICB9KTtcblxuICAgIHJlYWRTY2FsaW5nLnNjYWxlT25VdGlsaXphdGlvbih7XG4gICAgICB0YXJnZXRVdGlsaXphdGlvblBlcmNlbnQ6IDcwLFxuICAgICAgc2NhbGVJbkNvb2xkb3duOiBjZGsuRHVyYXRpb24uc2Vjb25kcyg2MCksXG4gICAgICBzY2FsZU91dENvb2xkb3duOiBjZGsuRHVyYXRpb24uc2Vjb25kcyg2MCksXG4gICAgfSk7XG5cbiAgICAvLyBXcml0ZSBjYXBhY2l0eSBhdXRvLXNjYWxpbmdcbiAgICBjb25zdCB3cml0ZVNjYWxpbmcgPSB0YWJsZS5hdXRvU2NhbGVXcml0ZUNhcGFjaXR5KHtcbiAgICAgIG1pbkNhcGFjaXR5OiBlbnZpcm9ubWVudCA9PT0gJ3Byb2QnID8gNSA6IDEsXG4gICAgICBtYXhDYXBhY2l0eTogZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/IDQwMDAgOiAxMDAsXG4gICAgfSk7XG5cbiAgICB3cml0ZVNjYWxpbmcuc2NhbGVPblV0aWxpemF0aW9uKHtcbiAgICAgIHRhcmdldFV0aWxpemF0aW9uUGVyY2VudDogNzAsXG4gICAgICBzY2FsZUluQ29vbGRvd246IGNkay5EdXJhdGlvbi5zZWNvbmRzKDYwKSxcbiAgICAgIHNjYWxlT3V0Q29vbGRvd246IGNkay5EdXJhdGlvbi5zZWNvbmRzKDYwKSxcbiAgICB9KTtcblxuICAgIC8vIEF1dG8tc2NhbGluZyBmb3IgR2xvYmFsIFNlY29uZGFyeSBJbmRleCAgXG4gICAgLy8gTm90ZTogR1NJIGF1dG8tc2NhbGluZyBjb25maWd1cmVkIHNlcGFyYXRlbHkgcGVyIGluZGV4XG4gICAgICBjb25zdCBnc2lSZWFkU2NhbGluZyA9IHRhYmxlLmF1dG9TY2FsZUdsb2JhbFNlY29uZGFyeUluZGV4UmVhZENhcGFjaXR5KCdzdGF0dXMtaW5kZXgnLCB7XG4gICAgICAgIG1pbkNhcGFjaXR5OiBlbnZpcm9ubWVudCA9PT0gJ3Byb2QnID8gNSA6IDEsXG4gICAgICAgIG1heENhcGFjaXR5OiBlbnZpcm9ubWVudCA9PT0gJ3Byb2QnID8gMTAwMCA6IDUwLFxuICAgICAgfSk7XG5cbiAgICAgIGdzaVJlYWRTY2FsaW5nLnNjYWxlT25VdGlsaXphdGlvbih7XG4gICAgICAgIHRhcmdldFV0aWxpemF0aW9uUGVyY2VudDogNzAsXG4gICAgICB9KTtcblxuICAgICAgY29uc3QgZ3NpV3JpdGVTY2FsaW5nID0gdGFibGUuYXV0b1NjYWxlR2xvYmFsU2Vjb25kYXJ5SW5kZXhXcml0ZUNhcGFjaXR5KCdzdGF0dXMtaW5kZXgnLCB7XG4gICAgICAgIG1pbkNhcGFjaXR5OiBlbnZpcm9ubWVudCA9PT0gJ3Byb2QnID8gNSA6IDEsXG4gICAgICAgIG1heENhcGFjaXR5OiBlbnZpcm9ubWVudCA9PT0gJ3Byb2QnID8gMTAwMCA6IDUwLFxuICAgICAgfSk7XG5cbiAgICAgIGdzaVdyaXRlU2NhbGluZy5zY2FsZU9uVXRpbGl6YXRpb24oe1xuICAgICAgICB0YXJnZXRVdGlsaXphdGlvblBlcmNlbnQ6IDcwLFxuICAgICAgfSk7XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIEJBQ0tVUCBDT05GSUdVUkFUSU9OXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cblxuICAgIC8vIEJhY2t1cCB2YXVsdCB3aXRoIEtNUyBlbmNyeXB0aW9uXG4gICAgdGhpcy5iYWNrdXBWYXVsdCA9IG5ldyBiYWNrdXAuQmFja3VwVmF1bHQodGhpcywgJ0JhY2t1cFZhdWx0Jywge1xuICAgICAgYmFja3VwVmF1bHROYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tZHluYW1vZGItYmFja3VwLXZhdWx0YCxcbiAgICAgIGVuY3J5cHRpb25LZXk6IHVuZGVmaW5lZCwgLy8gVXNlcyBBV1MgbWFuYWdlZCBrZXlcbiAgICAgIGFjY2Vzc1BvbGljeTogbmV3IGlhbS5Qb2xpY3lEb2N1bWVudCh7XG4gICAgICAgIHN0YXRlbWVudHM6IFtcbiAgICAgICAgICBuZXcgaWFtLlBvbGljeVN0YXRlbWVudCh7XG4gICAgICAgICAgICBlZmZlY3Q6IGlhbS5FZmZlY3QuREVOWSxcbiAgICAgICAgICAgIHByaW5jaXBhbHM6IFtuZXcgaWFtLkFueVByaW5jaXBhbCgpXSxcbiAgICAgICAgICAgIGFjdGlvbnM6IFsnYmFja3VwOkRlbGV0ZUJhY2t1cFZhdWx0JywgJ2JhY2t1cDpEZWxldGVCYWNrdXBQbGFuJywgJ2JhY2t1cDpEZWxldGVSZWNvdmVyeVBvaW50J10sXG4gICAgICAgICAgICByZXNvdXJjZXM6IFsnKiddLFxuICAgICAgICAgICAgY29uZGl0aW9uczoge1xuICAgICAgICAgICAgICBTdHJpbmdOb3RFcXVhbHM6IHtcbiAgICAgICAgICAgICAgICAnYXdzOlByaW5jaXBhbFNlcnZpY2VOYW1lJzogJ2JhY2t1cC5hbWF6b25hd3MuY29tJyxcbiAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgIH0sXG4gICAgICAgICAgfSksXG4gICAgICAgIF0sXG4gICAgICB9KSxcbiAgICB9KTtcblxuICAgIC8vIEJhY2t1cCBzZXJ2aWNlIHJvbGVcbiAgICBjb25zdCBiYWNrdXBSb2xlID0gbmV3IGlhbS5Sb2xlKHRoaXMsICdCYWNrdXBTZXJ2aWNlUm9sZScsIHtcbiAgICAgIHJvbGVOYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tYmFja3VwLXNlcnZpY2Utcm9sZWAsXG4gICAgICBhc3N1bWVkQnk6IG5ldyBpYW0uU2VydmljZVByaW5jaXBhbCgnYmFja3VwLmFtYXpvbmF3cy5jb20nKSxcbiAgICAgIG1hbmFnZWRQb2xpY2llczogW1xuICAgICAgICBpYW0uTWFuYWdlZFBvbGljeS5mcm9tQXdzTWFuYWdlZFBvbGljeU5hbWUoJ3NlcnZpY2Utcm9sZS9BV1NCYWNrdXBTZXJ2aWNlUm9sZVBvbGljeUZvckJhY2t1cCcpLFxuICAgICAgICBpYW0uTWFuYWdlZFBvbGljeS5mcm9tQXdzTWFuYWdlZFBvbGljeU5hbWUoJ3NlcnZpY2Utcm9sZS9BV1NCYWNrdXBTZXJ2aWNlUm9sZVBvbGljeUZvclJlc3RvcmVzJyksXG4gICAgICBdLFxuICAgIH0pO1xuXG4gICAgLy8gQmFja3VwIHBsYW4gd2l0aCBkaWZmZXJlbnQgc2NoZWR1bGVzIGZvciBkaWZmZXJlbnQgZW52aXJvbm1lbnRzXG4gICAgdGhpcy5iYWNrdXBQbGFuID0gbmV3IGJhY2t1cC5CYWNrdXBQbGFuKHRoaXMsICdCYWNrdXBQbGFuJywge1xuICAgICAgYmFja3VwUGxhbk5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1keW5hbW9kYi1iYWNrdXAtcGxhbmAsXG4gICAgICBiYWNrdXBWYXVsdDogdGhpcy5iYWNrdXBWYXVsdCxcbiAgICB9KTtcblxuICAgIC8vIFByb2R1Y3Rpb24gYmFja3VwIHNjaGVkdWxlIChkYWlseSArIG1vbnRobHkpXG4gICAgaWYgKGVudmlyb25tZW50ID09PSAncHJvZCcpIHtcbiAgICAgIC8vIERhaWx5IGJhY2t1cHMgcmV0YWluZWQgZm9yIDM1IGRheXNcbiAgICAgICAgdGhpcy5iYWNrdXBQbGFuLmFkZFJ1bGUobmV3IGJhY2t1cC5CYWNrdXBQbGFuUnVsZSh7XG4gICAgICAgICAgcnVsZU5hbWU6ICdEYWlseUJhY2t1cHMnLFxuICAgICAgICAgIGRlbGV0ZUFmdGVyOiBjZGsuRHVyYXRpb24uZGF5cygzNSksXG4gICAgICAgICAgbW92ZVRvQ29sZFN0b3JhZ2VBZnRlcjogY2RrLkR1cmF0aW9uLmRheXMoNyksXG4gICAgICAgICAgYmFja3VwVmF1bHQ6IHRoaXMuYmFja3VwVmF1bHQsXG4gICAgICAgICAgc2NoZWR1bGVFeHByZXNzaW9uOiBldmVudHMuU2NoZWR1bGUuY3Jvbih7IGhvdXI6ICcyJywgbWludXRlOiAnMCcgfSksIC8vIDIgQU0gVVRDXG4gICAgICAgIH0pKTtcblxuICAgICAgLy8gTW9udGhseSBiYWNrdXBzIHJldGFpbmVkIGZvciAxIHllYXJcbiAgICAgICAgdGhpcy5iYWNrdXBQbGFuLmFkZFJ1bGUobmV3IGJhY2t1cC5CYWNrdXBQbGFuUnVsZSh7XG4gICAgICAgICAgcnVsZU5hbWU6ICdNb250aGx5QmFja3VwcycsXG4gICAgICAgICAgYmFja3VwVmF1bHQ6IHRoaXMuYmFja3VwVmF1bHQsXG4gICAgICAgICAgc2NoZWR1bGVFeHByZXNzaW9uOiBldmVudHMuU2NoZWR1bGUuY3Jvbih7IFxuICAgICAgICAgICAgaG91cjogJzMnLCBcbiAgICAgICAgICAgIG1pbnV0ZTogJzAnLCBcbiAgICAgICAgICAgIGRheTogJzEnIFxuICAgICAgICAgIH0pLCAvLyAxc3Qgb2YgbW9udGggYXQgMyBBTSBVVENcbiAgICAgICAgfSkpO1xuICAgIH0gZWxzZSB7XG4gICAgICAvLyBEZXZlbG9wbWVudC9zdGFnaW5nOiB3ZWVrbHkgYmFja3VwcyByZXRhaW5lZCBmb3IgMiB3ZWVrc1xuICAgICAgICB0aGlzLmJhY2t1cFBsYW4uYWRkUnVsZShuZXcgYmFja3VwLkJhY2t1cFBsYW5SdWxlKHtcbiAgICAgICAgICBydWxlTmFtZTogJ1dlZWtseUJhY2t1cHMnLFxuICAgICAgICAgIGRlbGV0ZUFmdGVyOiBjZGsuRHVyYXRpb24uZGF5cygxNCksXG4gICAgICAgICAgYmFja3VwVmF1bHQ6IHRoaXMuYmFja3VwVmF1bHQsXG4gICAgICAgICAgc2NoZWR1bGVFeHByZXNzaW9uOiBldmVudHMuU2NoZWR1bGUuY3Jvbih7IFxuICAgICAgICAgICAgaG91cjogJzQnLCBcbiAgICAgICAgICAgIG1pbnV0ZTogJzAnLCBcbiAgICAgICAgICAgIHdlZWtEYXk6ICdTVU4nIFxuICAgICAgICAgIH0pLCAvLyBTdW5kYXkgYXQgNCBBTSBVVENcbiAgICAgICAgfSkpO1xuICAgIH1cblxuICAgIC8vIEFkZCBEeW5hbW9EQiB0YWJsZSB0byBiYWNrdXAgcGxhblxuICAgIHRoaXMuYmFja3VwUGxhbi5hZGRTZWxlY3Rpb24oJ0R5bmFtb0RCU2VsZWN0aW9uJywge1xuICAgICAgcmVzb3VyY2VzOiBbXG4gICAgICAgIGJhY2t1cC5CYWNrdXBSZXNvdXJjZS5mcm9tQXJuKHRhYmxlLnRhYmxlQXJuKSxcbiAgICAgIF0sXG4gICAgICByb2xlOiBiYWNrdXBSb2xlLFxuICAgIH0pO1xuXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cbiAgICAvLyBDTE9VRFdBVENIIEFMQVJNUyBGT1IgVEFCTEUgSEVBTFRIXG4gICAgLy8gPT09PT09PT09PT09PT09PT1cblxuICAgIC8vIEhpZ2ggcmVhZCB0aHJvdHRsZSBhbGFybVxuICAgIG5ldyBjbG91ZHdhdGNoLkFsYXJtKHRoaXMsICdSZWFkVGhyb3R0bGVBbGFybScsIHtcbiAgICAgIGFsYXJtTmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LWR5bmFtb2RiLXJlYWQtdGhyb3R0bGVzYCxcbiAgICAgIGFsYXJtRGVzY3JpcHRpb246ICdEeW5hbW9EQiB0YWJsZSBleHBlcmllbmNpbmcgcmVhZCB0aHJvdHRsaW5nJyxcbiAgICAgIG1ldHJpYzogdGFibGUubWV0cmljVGhyb3R0bGVkUmVxdWVzdHMoe1xuICAgICAgICBkaW1lbnNpb25zTWFwOiB7IFRhYmxlTmFtZTogdGFibGUudGFibGVOYW1lLCBPcGVyYXRpb246ICdRdWVyeScgfSxcbiAgICAgICAgcGVyaW9kOiBjZGsuRHVyYXRpb24ubWludXRlcyg1KSxcbiAgICAgIH0pLFxuICAgICAgdGhyZXNob2xkOiAxLFxuICAgICAgZXZhbHVhdGlvblBlcmlvZHM6IDIsXG4gICAgICB0cmVhdE1pc3NpbmdEYXRhOiBjbG91ZHdhdGNoLlRyZWF0TWlzc2luZ0RhdGEuTk9UX0JSRUFDSElORyxcbiAgICB9KTtcblxuICAgIC8vIEhpZ2ggd3JpdGUgdGhyb3R0bGUgYWxhcm1cbiAgICBuZXcgY2xvdWR3YXRjaC5BbGFybSh0aGlzLCAnV3JpdGVUaHJvdHRsZUFsYXJtJywge1xuICAgICAgYWxhcm1OYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tZHluYW1vZGItd3JpdGUtdGhyb3R0bGVzYCxcbiAgICAgIGFsYXJtRGVzY3JpcHRpb246ICdEeW5hbW9EQiB0YWJsZSBleHBlcmllbmNpbmcgd3JpdGUgdGhyb3R0bGluZycsXG4gICAgICBtZXRyaWM6IHRhYmxlLm1ldHJpY1Rocm90dGxlZFJlcXVlc3RzKHtcbiAgICAgICAgZGltZW5zaW9uc01hcDogeyBUYWJsZU5hbWU6IHRhYmxlLnRhYmxlTmFtZSwgT3BlcmF0aW9uOiAnUHV0SXRlbScgfSxcbiAgICAgICAgcGVyaW9kOiBjZGsuRHVyYXRpb24ubWludXRlcyg1KSxcbiAgICAgIH0pLFxuICAgICAgdGhyZXNob2xkOiAxLFxuICAgICAgZXZhbHVhdGlvblBlcmlvZHM6IDIsXG4gICAgfSk7XG5cbiAgICAvLyBIaWdoIGNvbnN1bWVkIHJlYWQgY2FwYWNpdHkgYWxhcm0gKDg1JSB0aHJlc2hvbGQpXG4gICAgbmV3IGNsb3Vkd2F0Y2guQWxhcm0odGhpcywgJ0hpZ2hSZWFkQ2FwYWNpdHlBbGFybScsIHtcbiAgICAgIGFsYXJtTmFtZTogYCR7cmVzb3VyY2VQcmVmaXh9LWR5bmFtb2RiLWhpZ2gtcmVhZC1jYXBhY2l0eWAsXG4gICAgICBhbGFybURlc2NyaXB0aW9uOiAnRHluYW1vREIgcmVhZCBjYXBhY2l0eSB1dGlsaXphdGlvbiBhYm92ZSA4NSUnLFxuICAgICAgbWV0cmljOiB0YWJsZS5tZXRyaWNDb25zdW1lZFJlYWRDYXBhY2l0eVVuaXRzKHtcbiAgICAgICAgcGVyaW9kOiBjZGsuRHVyYXRpb24ubWludXRlcyg1KSxcbiAgICAgIH0pLFxuICAgICAgdGhyZXNob2xkOiAwLjg1LFxuICAgICAgZXZhbHVhdGlvblBlcmlvZHM6IDMsXG4gICAgICBjb21wYXJpc29uT3BlcmF0b3I6IGNsb3Vkd2F0Y2guQ29tcGFyaXNvbk9wZXJhdG9yLkdSRUFURVJfVEhBTl9USFJFU0hPTEQsXG4gICAgfSk7XG5cbiAgICAvLyBIaWdoIGNvbnN1bWVkIHdyaXRlIGNhcGFjaXR5IGFsYXJtICg4NSUgdGhyZXNob2xkKVxuICAgIG5ldyBjbG91ZHdhdGNoLkFsYXJtKHRoaXMsICdIaWdoV3JpdGVDYXBhY2l0eUFsYXJtJywge1xuICAgICAgYWxhcm1OYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tZHluYW1vZGItaGlnaC13cml0ZS1jYXBhY2l0eWAsXG4gICAgICBhbGFybURlc2NyaXB0aW9uOiAnRHluYW1vREIgd3JpdGUgY2FwYWNpdHkgdXRpbGl6YXRpb24gYWJvdmUgODUlJyxcbiAgICAgIG1ldHJpYzogdGFibGUubWV0cmljQ29uc3VtZWRXcml0ZUNhcGFjaXR5VW5pdHMoe1xuICAgICAgICBwZXJpb2Q6IGNkay5EdXJhdGlvbi5taW51dGVzKDUpLFxuICAgICAgfSksXG4gICAgICB0aHJlc2hvbGQ6IDAuODUsXG4gICAgICBldmFsdWF0aW9uUGVyaW9kczogMyxcbiAgICAgIGNvbXBhcmlzb25PcGVyYXRvcjogY2xvdWR3YXRjaC5Db21wYXJpc29uT3BlcmF0b3IuR1JFQVRFUl9USEFOX1RIUkVTSE9MRCxcbiAgICB9KTtcblxuICAgIC8vID09PT09PT09PT09PT09PT09XG4gICAgLy8gREFUQSBMSUZFQ1lDTEUgTUFOQUdFTUVOVFxuICAgIC8vID09PT09PT09PT09PT09PT09XG5cbiAgICAvLyBMYW1iZGEgZnVuY3Rpb24gZm9yIGRhdGEgY2xlYW51cCAob3B0aW9uYWwgLSBmb3Igb2xkIHBpcGVsaW5lIGRhdGEpXG4gICAgY29uc3QgY2xlYW51cEZ1bmN0aW9uID0gbmV3IGNkay5hd3NfbGFtYmRhLkZ1bmN0aW9uKHRoaXMsICdEYXRhQ2xlYW51cEZ1bmN0aW9uJywge1xuICAgICAgZnVuY3Rpb25OYW1lOiBgJHtyZXNvdXJjZVByZWZpeH0tZHluYW1vZGItY2xlYW51cGAsXG4gICAgICBydW50aW1lOiBjZGsuYXdzX2xhbWJkYS5SdW50aW1lLlBZVEhPTl8zXzksXG4gICAgICBoYW5kbGVyOiAnY2xlYW51cC5oYW5kbGVyJyxcbiAgICAgIGNvZGU6IGNkay5hd3NfbGFtYmRhLkNvZGUuZnJvbUlubGluZShgXG5pbXBvcnQgYm90bzNcbmltcG9ydCBqc29uXG5mcm9tIGRhdGV0aW1lIGltcG9ydCBkYXRldGltZSwgdGltZWRlbHRhXG5cbmRlZiBoYW5kbGVyKGV2ZW50LCBjb250ZXh0KTpcbiAgICBkeW5hbW9kYiA9IGJvdG8zLnJlc291cmNlKCdkeW5hbW9kYicpXG4gICAgdGFibGUgPSBkeW5hbW9kYi5UYWJsZSgnJHt0YWJsZS50YWJsZU5hbWV9JylcbiAgICBcbiAgICAjIERlbGV0ZSBwaXBlbGluZSByZWNvcmRzIG9sZGVyIHRoYW4gOTAgZGF5cyAoZm9yIG5vbi1wcm9kKVxuICAgIGlmICcke2Vudmlyb25tZW50fScgIT0gJ3Byb2QnOlxuICAgICAgICBjdXRvZmZfZGF0ZSA9IGRhdGV0aW1lLm5vdygpIC0gdGltZWRlbHRhKGRheXM9OTApXG4gICAgICAgIGN1dG9mZl90aW1lc3RhbXAgPSBpbnQoY3V0b2ZmX2RhdGUudGltZXN0YW1wKCkpXG4gICAgICAgIFxuICAgICAgICB0cnk6XG4gICAgICAgICAgICByZXNwb25zZSA9IHRhYmxlLnNjYW4oXG4gICAgICAgICAgICAgICAgRmlsdGVyRXhwcmVzc2lvbj0nI3RzIDwgOmN1dG9mZicsXG4gICAgICAgICAgICAgICAgRXhwcmVzc2lvbkF0dHJpYnV0ZU5hbWVzPXsnI3RzJzogJ3RpbWVzdGFtcCd9LFxuICAgICAgICAgICAgICAgIEV4cHJlc3Npb25BdHRyaWJ1dGVWYWx1ZXM9eyc6Y3V0b2ZmJzogY3V0b2ZmX3RpbWVzdGFtcH0sXG4gICAgICAgICAgICAgICAgUHJvamVjdGlvbkV4cHJlc3Npb249J3BpcGVsaW5lX2lkLCAjdHMnXG4gICAgICAgICAgICApXG4gICAgICAgICAgICBcbiAgICAgICAgICAgIGRlbGV0ZWRfY291bnQgPSAwXG4gICAgICAgICAgICBmb3IgaXRlbSBpbiByZXNwb25zZVsnSXRlbXMnXTpcbiAgICAgICAgICAgICAgICB0YWJsZS5kZWxldGVfaXRlbShcbiAgICAgICAgICAgICAgICAgICAgS2V5PXtcbiAgICAgICAgICAgICAgICAgICAgICAgICdwaXBlbGluZV9pZCc6IGl0ZW1bJ3BpcGVsaW5lX2lkJ10sXG4gICAgICAgICAgICAgICAgICAgICAgICAndGltZXN0YW1wJzogaXRlbVsndGltZXN0YW1wJ11cbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgIClcbiAgICAgICAgICAgICAgICBkZWxldGVkX2NvdW50ICs9IDFcbiAgICAgICAgICAgIFxuICAgICAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgICAgICAnc3RhdHVzQ29kZSc6IDIwMCxcbiAgICAgICAgICAgICAgICAnYm9keSc6IGpzb24uZHVtcHMoe1xuICAgICAgICAgICAgICAgICAgICAnbWVzc2FnZSc6IGYnRGVsZXRlZCB7ZGVsZXRlZF9jb3VudH0gb2xkIHBpcGVsaW5lIHJlY29yZHMnLFxuICAgICAgICAgICAgICAgICAgICAnY3V0b2ZmX2RhdGUnOiBjdXRvZmZfZGF0ZS5pc29mb3JtYXQoKVxuICAgICAgICAgICAgICAgIH0pXG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBcbiAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOlxuICAgICAgICAgICAgcmV0dXJuIHtcbiAgICAgICAgICAgICAgICAnc3RhdHVzQ29kZSc6IDUwMCxcbiAgICAgICAgICAgICAgICAnYm9keSc6IGpzb24uZHVtcHMoeydlcnJvcic6IHN0cihlKX0pXG4gICAgICAgICAgICB9XG4gICAgXG4gICAgcmV0dXJuIHtcbiAgICAgICAgJ3N0YXR1c0NvZGUnOiAyMDAsXG4gICAgICAgICdib2R5JzoganNvbi5kdW1wcyh7J21lc3NhZ2UnOiAnQ2xlYW51cCBza2lwcGVkIGZvciBwcm9kdWN0aW9uIGVudmlyb25tZW50J30pXG4gICAgfVxuICAgICAgYCksXG4gICAgICB0aW1lb3V0OiBjZGsuRHVyYXRpb24ubWludXRlcyg1KSxcbiAgICAgIGVudmlyb25tZW50OiB7XG4gICAgICAgIFRBQkxFX05BTUU6IHRhYmxlLnRhYmxlTmFtZSxcbiAgICAgICAgRU5WSVJPTk1FTlQ6IGVudmlyb25tZW50LFxuICAgICAgfSxcbiAgICB9KTtcblxuICAgIC8vIEdyYW50IGNsZWFudXAgZnVuY3Rpb24gcGVybWlzc2lvbnNcbiAgICB0YWJsZS5ncmFudFJlYWRXcml0ZURhdGEoY2xlYW51cEZ1bmN0aW9uKTtcblxuICAgIC8vIFNjaGVkdWxlIGNsZWFudXAgZnVuY3Rpb24gKHdlZWtseSBmb3Igbm9uLXByb2QgZW52aXJvbm1lbnRzKVxuICAgIGlmIChlbnZpcm9ubWVudCAhPT0gJ3Byb2QnKSB7XG4gICAgICBuZXcgZXZlbnRzLlJ1bGUodGhpcywgJ0NsZWFudXBTY2hlZHVsZScsIHtcbiAgICAgICAgcnVsZU5hbWU6IGAke3Jlc291cmNlUHJlZml4fS1keW5hbW9kYi1jbGVhbnVwLXNjaGVkdWxlYCxcbiAgICAgICAgZGVzY3JpcHRpb246ICdXZWVrbHkgY2xlYW51cCBvZiBvbGQgcGlwZWxpbmUgZGF0YScsXG4gICAgICAgIHNjaGVkdWxlOiBldmVudHMuU2NoZWR1bGUuY3Jvbih7IGhvdXI6ICcxJywgbWludXRlOiAnMCcsIHdlZWtEYXk6ICdNT04nIH0pLFxuICAgICAgICB0YXJnZXRzOiBbbmV3IHRhcmdldHMuTGFtYmRhRnVuY3Rpb24oY2xlYW51cEZ1bmN0aW9uKV0sXG4gICAgICB9KTtcbiAgICB9XG5cbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIC8vIE9VVFBVVFNcbiAgICAvLyA9PT09PT09PT09PT09PT09PVxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdCYWNrdXBWYXVsdEFybicsIHtcbiAgICAgIHZhbHVlOiB0aGlzLmJhY2t1cFZhdWx0LmJhY2t1cFZhdWx0QXJuLFxuICAgICAgZGVzY3JpcHRpb246ICdEeW5hbW9EQiBCYWNrdXAgVmF1bHQgQVJOJyxcbiAgICB9KTtcblxuICAgIG5ldyBjZGsuQ2ZuT3V0cHV0KHRoaXMsICdCYWNrdXBQbGFuQXJuJywge1xuICAgICAgdmFsdWU6IHRoaXMuYmFja3VwUGxhbi5iYWNrdXBQbGFuQXJuLFxuICAgICAgZGVzY3JpcHRpb246ICdEeW5hbW9EQiBCYWNrdXAgUGxhbiBBUk4nLFxuICAgIH0pO1xuXG4gICAgbmV3IGNkay5DZm5PdXRwdXQodGhpcywgJ0F1dG9TY2FsaW5nU3RhdHVzJywge1xuICAgICAgdmFsdWU6IGBSZWFkOiAke2Vudmlyb25tZW50ID09PSAncHJvZCcgPyAnNS00MDAwJyA6ICcxLTEwMCd9IHwgV3JpdGU6ICR7ZW52aXJvbm1lbnQgPT09ICdwcm9kJyA/ICc1LTQwMDAnIDogJzEtMTAwJ31gLFxuICAgICAgZGVzY3JpcHRpb246ICdEeW5hbW9EQiBBdXRvLXNjYWxpbmcgQ29uZmlndXJhdGlvbicsXG4gICAgfSk7XG4gIH1cbn0iXX0=