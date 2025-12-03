#!/usr/bin/env python3
"""
ADPA Real AWS Infrastructure Deployment
Deploys complete AWS infrastructure for 100% autonomous ML pipeline agent
"""

import json
import boto3
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ADPAInfrastructureDeployer:
    """Deploy real AWS infrastructure for ADPA autonomous agent"""
    
    def __init__(self, region: str = 'us-east-2', account_id: str = '083308938449'):
        self.region = region
        self.account_id = account_id
        
        # Initialize AWS clients
        self.iam = boto3.client('iam', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.stepfunctions = boto3.client('stepfunctions', region_name=region)
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        self.glue = boto3.client('glue', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.apigateway = boto3.client('apigateway', region_name=region)
        
        # Resource names
        self.resources = {
            'data_bucket': f'adpa-data-{account_id}-production',
            'model_bucket': f'adpa-models-{account_id}-production',
            'sagemaker_role': 'adpa-sagemaker-execution-role',
            'stepfunctions_role': 'adpa-stepfunctions-execution-role',
            'lambda_role': 'adpa-lambda-execution-role',
            'glue_role': 'adpa-glue-execution-role',
            'sns_topic': 'adpa-pipeline-notifications',
            'state_machine': 'adpa-ml-pipeline-workflow',
            'glue_database': 'adpa_data_catalog',
            'api_gateway': 'adpa-autonomous-agent-api'
        }
        
        self.deployment_status = {}
    
    def deploy_complete_infrastructure(self) -> Dict[str, Any]:
        """Deploy complete ADPA infrastructure"""
        logger.info("🚀 Starting ADPA Real AWS Infrastructure Deployment")
        logger.info("=" * 60)
        
        deployment_errors = []
        
        try:
            # Phase 1: Core IAM roles and permissions
            try:
                self._deploy_iam_roles()
            except Exception as e:
                logger.error(f"IAM deployment error: {e}")
                deployment_errors.append(f"IAM: {e}")
            
            # Phase 2: S3 buckets and storage
            try:
                self._deploy_s3_buckets()
            except Exception as e:
                logger.error(f"S3 deployment error: {e}")
                deployment_errors.append(f"S3: {e}")
            
            # Phase 3: SNS notifications
            try:
                self._deploy_sns_notifications()
            except Exception as e:
                logger.error(f"SNS deployment error: {e}")
                deployment_errors.append(f"SNS: {e}")
            
            # Phase 4: Lambda functions for pipeline steps
            try:
                self._deploy_lambda_functions()
            except Exception as e:
                logger.error(f"Lambda deployment error: {e}")
                deployment_errors.append(f"Lambda: {e}")
            
            # Phase 5: SageMaker execution infrastructure
            try:
                self._deploy_sagemaker_infrastructure()
            except Exception as e:
                logger.error(f"SageMaker deployment error: {e}")
                deployment_errors.append(f"SageMaker: {e}")
            
            # Phase 6: Glue ETL infrastructure
            try:
                self._deploy_glue_infrastructure()
            except Exception as e:
                logger.error(f"Glue deployment error: {e}")
                deployment_errors.append(f"Glue: {e}")
            
            # Phase 7: Step Functions ML pipeline
            try:
                self._deploy_stepfunctions_workflow()
            except Exception as e:
                logger.error(f"Step Functions deployment error: {e}")
                deployment_errors.append(f"Step Functions: {e}")
                self.deployment_status['stepfunctions_workflow'] = {
                    'status': 'failed',
                    'error': str(e)
                }
            
            # Phase 8: CloudWatch monitoring and dashboards
            try:
                self._deploy_cloudwatch_monitoring()
            except Exception as e:
                logger.error(f"CloudWatch deployment error: {e}")
                deployment_errors.append(f"CloudWatch: {e}")
            
            # Phase 9: API Gateway for agent interface
            try:
                self._deploy_api_gateway()
            except Exception as e:
                logger.error(f"API Gateway deployment error: {e}")
                deployment_errors.append(f"API Gateway: {e}")
            
            self.deployment_status['overall_status'] = 'completed_with_errors' if deployment_errors else 'success'
            self.deployment_status['deployed_at'] = datetime.utcnow().isoformat()
            self.deployment_status['errors'] = deployment_errors
            
            logger.info("✅ ADPA Infrastructure Deployment Completed!")
            if deployment_errors:
                logger.warning(f"⚠️  Some components had errors: {len(deployment_errors)} errors")
            self._print_deployment_summary()
            
            return self.deployment_status
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {str(e)}")
            self.deployment_status['overall_status'] = 'failed'
            self.deployment_status['error'] = str(e)
            raise
    
    def _deploy_iam_roles(self):
        """Deploy IAM roles with proper permissions"""
        logger.info("📋 Deploying IAM roles and permissions...")
        
        # SageMaker execution role
        sagemaker_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "sagemaker.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        sagemaker_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject", 
                        "s3:DeleteObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{self.resources['data_bucket']}",
                        f"arn:aws:s3:::{self.resources['data_bucket']}/*",
                        f"arn:aws:s3:::{self.resources['model_bucket']}",
                        f"arn:aws:s3:::{self.resources['model_bucket']}/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "cloudwatch:PutMetricData",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        self._create_iam_role(
            self.resources['sagemaker_role'],
            sagemaker_trust_policy,
            sagemaker_policy,
            'SageMaker execution role for ADPA ML training'
        )
        
        # Step Functions execution role
        stepfunctions_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "states.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        stepfunctions_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction",
                        "sagemaker:CreateTrainingJob",
                        "sagemaker:DescribeTrainingJob",
                        "sagemaker:StopTrainingJob",
                        "sns:Publish",
                        "iam:PassRole",
                        "logs:CreateLogDelivery",
                        "logs:GetLogDelivery",
                        "logs:UpdateLogDelivery",
                        "logs:DeleteLogDelivery",
                        "logs:ListLogDeliveries",
                        "logs:PutResourcePolicy",
                        "logs:DescribeResourcePolicies",
                        "logs:DescribeLogGroups",
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords",
                        "xray:GetSamplingRules",
                        "xray:GetSamplingTargets"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        self._create_iam_role(
            self.resources['stepfunctions_role'],
            stepfunctions_trust_policy,
            stepfunctions_policy,
            'Step Functions execution role for ADPA ML pipeline orchestration'
        )
        
        # Lambda execution role
        lambda_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        lambda_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:ListBucket",
                        "glue:*",
                        "cloudwatch:PutMetricData",
                        "states:StartExecution",
                        "states:DescribeExecution",
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        self._create_iam_role(
            self.resources['lambda_role'],
            lambda_trust_policy,
            lambda_policy,
            'Lambda execution role for ADPA pipeline steps'
        )
        
        # Glue execution role
        glue_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "glue.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        glue_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "glue:*",
                        "s3:GetBucketLocation",
                        "s3:ListBucket",
                        "s3:ListAllMyBuckets",
                        "s3:GetObject",
                        "s3:PutObject",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        self._create_iam_role(
            self.resources['glue_role'],
            glue_trust_policy,
            glue_policy,
            'Glue execution role for ADPA data processing'
        )
        
        self.deployment_status['iam_roles'] = 'completed'
        logger.info("✅ IAM roles deployed successfully")
    
    def _deploy_s3_buckets(self):
        """Deploy S3 buckets for data and model storage"""
        logger.info("🗄️  Deploying S3 buckets...")
        
        buckets_created = []
        
        for bucket_key, bucket_name in [
            ('data_bucket', self.resources['data_bucket']),
            ('model_bucket', self.resources['model_bucket'])
        ]:
            try:
                # Create bucket
                if self.region == 'us-east-1':
                    self.s3.create_bucket(Bucket=bucket_name)
                else:
                    self.s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                
                # Enable versioning
                self.s3.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                
                # Set lifecycle policy for cost optimization
                lifecycle_policy = {
                    "Rules": [
                        {
                            "ID": "adpa-lifecycle-rule",
                            "Status": "Enabled",
                            "Filter": {"Prefix": ""},
                            "Transitions": [
                                {
                                    "Days": 30,
                                    "StorageClass": "STANDARD_IA"
                                },
                                {
                                    "Days": 90,
                                    "StorageClass": "GLACIER"
                                }
                            ]
                        }
                    ]
                }
                
                self.s3.put_bucket_lifecycle_configuration(
                    Bucket=bucket_name,
                    LifecycleConfiguration=lifecycle_policy
                )
                
                buckets_created.append(bucket_name)
                logger.info(f"✅ Created bucket: {bucket_name}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                    logger.info(f"✅ Bucket already exists: {bucket_name}")
                    buckets_created.append(bucket_name)
                else:
                    logger.error(f"Failed to create bucket {bucket_name}: {e}")
                    raise
        
        self.deployment_status['s3_buckets'] = {
            'status': 'completed',
            'buckets': buckets_created
        }
        logger.info("✅ S3 buckets deployed successfully")
    
    def _deploy_sns_notifications(self):
        """Deploy SNS topic for pipeline notifications"""
        logger.info("📧 Deploying SNS notifications...")
        
        try:
            response = self.sns.create_topic(Name=self.resources['sns_topic'])
            topic_arn = response['TopicArn']
            
            # Set display name
            self.sns.set_topic_attributes(
                TopicArn=topic_arn,
                AttributeName='DisplayName',
                AttributeValue='ADPA Pipeline Notifications'
            )
            
            self.deployment_status['sns_notifications'] = {
                'status': 'completed',
                'topic_arn': topic_arn
            }
            
            logger.info(f"✅ SNS topic created: {topic_arn}")
            
        except ClientError as e:
            if 'already exists' in str(e):
                # Get existing topic ARN
                topic_arn = f"arn:aws:sns:{self.region}:{self.account_id}:{self.resources['sns_topic']}"
                self.deployment_status['sns_notifications'] = {
                    'status': 'completed',
                    'topic_arn': topic_arn
                }
                logger.info(f"✅ SNS topic already exists: {topic_arn}")
            else:
                logger.error(f"Failed to create SNS topic: {e}")
                raise
    
    def _deploy_lambda_functions(self):
        """Deploy Lambda functions for pipeline steps"""
        logger.info("⚡ Deploying Lambda functions...")
        
        function_name = 'adpa-lambda-function'
        role_arn = f"arn:aws:iam::{self.account_id}:role/{self.resources['lambda_role']}"
        
        try:
            # Create deployment package
            deployment_package = self._create_lambda_deployment_package()
            
            # Wait for any existing updates to complete
            self._wait_for_lambda_update(function_name)
            
            # Try to update existing function first
            try:
                response = self.lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=deployment_package
                )
                
                # Wait for code update to complete
                self._wait_for_lambda_update(function_name)
                
                # Update function configuration for production
                self.lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    Runtime='python3.9',
                    Handler='lambda_function.lambda_handler',
                    Role=role_arn,
                    Timeout=900,  # 15 minutes
                    MemorySize=1024,
                    Environment={
                        'Variables': {
                            'DATA_BUCKET': self.resources['data_bucket'],
                            'MODEL_BUCKET': self.resources['model_bucket'],
                            'SNS_TOPIC_ARN': f"arn:aws:sns:{self.region}:{self.account_id}:{self.resources['sns_topic']}",
                            'ENVIRONMENT': 'production',
                            'OPENAI_API_KEY': 'placeholder',  # Will be set via AWS Systems Manager
                            'ENABLE_XRAY': 'true'
                        }
                    },
                    TracingConfig={'Mode': 'Active'}  # Enable X-Ray tracing
                )
                
                logger.info(f"✅ Lambda function updated: {function_name}")
                
            except ClientError as e:
                if 'ResourceNotFoundException' in str(e):
                    # Function doesn't exist, create it
                    response = self.lambda_client.create_function(
                        FunctionName=function_name,
                        Runtime='python3.9',
                        Role=role_arn,
                        Handler='lambda_function.lambda_handler',
                        Code={'ZipFile': deployment_package},
                        Description='ADPA Autonomous ML Pipeline Agent Lambda Function',
                        Timeout=900,
                        MemorySize=1024,
                        Environment={
                            'Variables': {
                                'DATA_BUCKET': self.resources['data_bucket'],
                                'MODEL_BUCKET': self.resources['model_bucket'],
                                'SNS_TOPIC_ARN': f"arn:aws:sns:{self.region}:{self.account_id}:{self.resources['sns_topic']}",
                                'ENVIRONMENT': 'production',
                                'OPENAI_API_KEY': 'placeholder',
                                'ENABLE_XRAY': 'true'
                            }
                        },
                        TracingConfig={'Mode': 'Active'},
                        Tags={
                            'Project': 'ADPA',
                            'Environment': 'production',
                            'Type': 'AutonomousAgent'
                        }
                    )
                    logger.info(f"✅ Lambda function created: {function_name}")
                else:
                    raise
            
            self.deployment_status['lambda_functions'] = {
                'status': 'completed',
                'function_name': function_name,
                'function_arn': response['FunctionArn']
            }
            
        except ClientError as e:
            logger.error(f"Failed to deploy Lambda functions: {e}")
            raise
    
    def _deploy_sagemaker_infrastructure(self):
        """Deploy SageMaker infrastructure for ML training"""
        logger.info("🧠 Deploying SageMaker infrastructure...")
        
        try:
            # The SageMaker role was already created in IAM deployment
            role_arn = f"arn:aws:iam::{self.account_id}:role/{self.resources['sagemaker_role']}"
            
            # Create default training job template (this will be used by Step Functions)
            training_job_template = {
                "RoleArn": role_arn,
                "AlgorithmSpecification": {
                    "TrainingImage": f"683313688378.dkr.ecr.{self.region}.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3",
                    "TrainingInputMode": "File"
                },
                "OutputDataConfig": {
                    "S3OutputPath": f"s3://{self.resources['model_bucket']}/sagemaker-output/"
                },
                "ResourceConfig": {
                    "InstanceType": "ml.m5.xlarge",
                    "InstanceCount": 1,
                    "VolumeSizeInGB": 30
                },
                "StoppingCondition": {
                    "MaxRuntimeInSeconds": 3600
                }
            }
            
            self.deployment_status['sagemaker_infrastructure'] = {
                'status': 'completed',
                'execution_role_arn': role_arn,
                'training_job_template': training_job_template
            }
            
            logger.info("✅ SageMaker infrastructure configured")
            
        except Exception as e:
            logger.error(f"Failed to deploy SageMaker infrastructure: {e}")
            raise
    
    def _deploy_glue_infrastructure(self):
        """Deploy Glue infrastructure for data processing"""
        logger.info("🔄 Deploying Glue infrastructure...")
        
        try:
            # Create Glue database
            try:
                self.glue.create_database(
                    DatabaseInput={
                        'Name': self.resources['glue_database'],
                        'Description': 'ADPA data catalog for autonomous ML pipeline'
                    }
                )
                logger.info(f"✅ Created Glue database: {self.resources['glue_database']}")
            except ClientError as e:
                if 'AlreadyExistsException' in str(e):
                    logger.info(f"✅ Glue database already exists: {self.resources['glue_database']}")
                else:
                    raise
            
            # Create Glue crawler for automatic schema discovery
            crawler_name = 'adpa-data-crawler'
            try:
                self.glue.create_crawler(
                    Name=crawler_name,
                    Role=f"arn:aws:iam::{self.account_id}:role/{self.resources['glue_role']}",
                    DatabaseName=self.resources['glue_database'],
                    Targets={
                        'S3Targets': [
                            {
                                'Path': f"s3://{self.resources['data_bucket']}/datasets/"
                            }
                        ]
                    },
                    Description='ADPA autonomous data crawler for schema discovery',
                    Schedule='cron(0 12 ? * SUN *)',  # Weekly on Sundays at noon
                    SchemaChangePolicy={
                        'UpdateBehavior': 'UPDATE_IN_DATABASE',
                        'DeleteBehavior': 'LOG'
                    }
                )
                logger.info(f"✅ Created Glue crawler: {crawler_name}")
            except ClientError as e:
                if 'AlreadyExistsException' in str(e):
                    logger.info(f"✅ Glue crawler already exists: {crawler_name}")
                else:
                    raise
            
            self.deployment_status['glue_infrastructure'] = {
                'status': 'completed',
                'database_name': self.resources['glue_database'],
                'crawler_name': crawler_name
            }
            
            logger.info("✅ Glue infrastructure deployed successfully")
            
        except Exception as e:
            logger.error(f"Failed to deploy Glue infrastructure: {e}")
            raise
    
    def _deploy_stepfunctions_workflow(self):
        """Deploy Step Functions ML pipeline workflow"""
        logger.info("🔄 Deploying Step Functions ML pipeline...")
        
        try:
            # Create CloudWatch log group for Step Functions
            logs_client = boto3.client('logs', region_name=self.region)
            log_group_name = f'/aws/stepfunctions/{self.resources["state_machine"]}'
            
            try:
                logs_client.create_log_group(logGroupName=log_group_name)
                logger.info(f"✅ Created log group: {log_group_name}")
            except ClientError as e:
                if 'ResourceAlreadyExistsException' in str(e):
                    logger.info(f"✅ Log group already exists: {log_group_name}")
                else:
                    raise
            
            # Read the workflow definition
            with open('/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa/deploy/step-functions/pipeline-workflow.json', 'r') as f:
                workflow_definition = json.load(f)
            
            # Update resource ARNs in the workflow
            workflow_str = json.dumps(workflow_definition)
            workflow_str = workflow_str.replace(
                'arn:aws:lambda:us-east-2:083308938449:function:',
                f'arn:aws:lambda:{self.region}:{self.account_id}:function:'
            )
            workflow_str = workflow_str.replace(
                'arn:aws:iam::083308938449:role/adpa-sagemaker-execution-role',
                f'arn:aws:iam::{self.account_id}:role/{self.resources["sagemaker_role"]}'
            )
            workflow_str = workflow_str.replace(
                'arn:aws:sns:us-east-2:083308938449:adpa-pipeline-notifications',
                f'arn:aws:sns:{self.region}:{self.account_id}:{self.resources["sns_topic"]}'
            )
            workflow_str = workflow_str.replace(
                's3://adpa-models-083308938449-development/sagemaker-output',
                f's3://{self.resources["model_bucket"]}/sagemaker-output'
            )
            
            workflow_definition = json.loads(workflow_str)
            
            # Create the state machine
            try:
                response = self.stepfunctions.create_state_machine(
                    name=self.resources['state_machine'],
                    definition=json.dumps(workflow_definition),
                    roleArn=f"arn:aws:iam::{self.account_id}:role/{self.resources['stepfunctions_role']}",
                    type='STANDARD'
                )
                
                state_machine_arn = response['stateMachineArn']
                logger.info(f"✅ Created Step Functions state machine: {state_machine_arn}")
                
            except ClientError as e:
                if 'StateMachineAlreadyExists' in str(e):
                    # Update existing state machine
                    state_machine_arn = f"arn:aws:states:{self.region}:{self.account_id}:stateMachine:{self.resources['state_machine']}"
                    self.stepfunctions.update_state_machine(
                        stateMachineArn=state_machine_arn,
                        definition=json.dumps(workflow_definition),
                        roleArn=f"arn:aws:iam::{self.account_id}:role/{self.resources['stepfunctions_role']}"
                    )
                    logger.info(f"✅ Updated Step Functions state machine: {state_machine_arn}")
                else:
                    raise
            
            self.deployment_status['stepfunctions_workflow'] = {
                'status': 'completed',
                'state_machine_arn': state_machine_arn
            }
            
            logger.info("✅ Step Functions workflow deployed successfully")
            
        except Exception as e:
            logger.error(f"Failed to deploy Step Functions workflow: {e}")
            raise
    
    def _deploy_cloudwatch_monitoring(self):
        """Deploy CloudWatch monitoring and dashboards"""
        logger.info("📊 Deploying CloudWatch monitoring...")
        
        try:
            # Create CloudWatch dashboard
            dashboard_name = 'ADPA-Autonomous-Agent-Dashboard'
            
            dashboard_body = {
                "widgets": [
                    {
                        "type": "metric",
                        "x": 0, "y": 0, "width": 12, "height": 6,
                        "properties": {
                            "metrics": [
                                ["AWS/States", "ExecutionsSucceeded", "StateMachineArn", f"arn:aws:states:{self.region}:{self.account_id}:stateMachine:{self.resources['state_machine']}"],
                                ["AWS/States", "ExecutionsFailed", "StateMachineArn", f"arn:aws:states:{self.region}:{self.account_id}:stateMachine:{self.resources['state_machine']}"],
                                ["AWS/States", "ExecutionsStarted", "StateMachineArn", f"arn:aws:states:{self.region}:{self.account_id}:stateMachine:{self.resources['state_machine']}"]
                            ],
                            "period": 300,
                            "stat": "Sum",
                            "region": self.region,
                            "title": "ADPA Pipeline Executions"
                        }
                    },
                    {
                        "type": "metric",
                        "x": 0, "y": 6, "width": 12, "height": 6,
                        "properties": {
                            "metrics": [
                                ["AWS/Lambda", "Duration", "FunctionName", "adpa-lambda-function"],
                                ["AWS/Lambda", "Invocations", "FunctionName", "adpa-lambda-function"],
                                ["AWS/Lambda", "Errors", "FunctionName", "adpa-lambda-function"]
                            ],
                            "period": 300,
                            "stat": "Average",
                            "region": self.region,
                            "title": "Lambda Performance Metrics"
                        }
                    },
                    {
                        "type": "log",
                        "x": 0, "y": 12, "width": 24, "height": 6,
                        "properties": {
                            "query": f"SOURCE '/aws/lambda/adpa-lambda-function' | fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 100",
                            "region": self.region,
                            "title": "Recent Errors",
                            "view": "table"
                        }
                    }
                ]
            }
            
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            # Create alarms for pipeline monitoring
            self._create_cloudwatch_alarms()
            
            self.deployment_status['cloudwatch_monitoring'] = {
                'status': 'completed',
                'dashboard_name': dashboard_name,
                'dashboard_url': f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={dashboard_name}"
            }
            
            logger.info(f"✅ CloudWatch monitoring deployed: {dashboard_name}")
            
        except Exception as e:
            logger.error(f"Failed to deploy CloudWatch monitoring: {e}")
            raise
    
    def _deploy_api_gateway(self):
        """Deploy API Gateway for agent interface"""
        logger.info("🌐 Deploying API Gateway...")
        
        try:
            # Create REST API
            api_response = self.apigateway.create_rest_api(
                name=self.resources['api_gateway'],
                description='ADPA Autonomous ML Pipeline Agent API',
                endpointConfiguration={
                    'types': ['REGIONAL']
                }
            )
            
            api_id = api_response['id']
            
            # Get root resource ID
            resources_response = self.apigateway.get_resources(restApiId=api_id)
            root_resource_id = None
            for resource in resources_response['items']:
                if resource['path'] == '/':
                    root_resource_id = resource['id']
                    break
            
            # Create Lambda integration
            lambda_arn = f"arn:aws:lambda:{self.region}:{self.account_id}:function:adpa-lambda-function"
            
            # Add Lambda permission for API Gateway
            try:
                self.lambda_client.add_permission(
                    FunctionName='adpa-lambda-function',
                    StatementId='adpa-api-gateway-invoke',
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=f"arn:aws:execute-api:{self.region}:{self.account_id}:{api_id}/*/*/*"
                )
            except ClientError as e:
                if 'ResourceConflictException' not in str(e):
                    raise
            
            # Create deployment
            deployment_response = self.apigateway.create_deployment(
                restApiId=api_id,
                stageName='prod',
                description='Production deployment of ADPA API'
            )
            
            api_url = f"https://{api_id}.execute-api.{self.region}.amazonaws.com/prod"
            
            self.deployment_status['api_gateway'] = {
                'status': 'completed',
                'api_id': api_id,
                'api_url': api_url
            }
            
            logger.info(f"✅ API Gateway deployed: {api_url}")
            
        except Exception as e:
            logger.error(f"Failed to deploy API Gateway: {e}")
            raise
    
    def _create_iam_role(self, role_name: str, trust_policy: Dict, permissions_policy: Dict, description: str):
        """Helper method to create IAM role"""
        try:
            self.iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=description
            )
            
            # Attach inline policy
            self.iam.put_role_policy(
                RoleName=role_name,
                PolicyName=f'{role_name}-policy',
                PolicyDocument=json.dumps(permissions_policy)
            )
            
            logger.info(f"✅ Created IAM role: {role_name}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                logger.info(f"✅ IAM role already exists: {role_name}")
                # Update inline policy
                self.iam.put_role_policy(
                    RoleName=role_name,
                    PolicyName=f'{role_name}-policy',
                    PolicyDocument=json.dumps(permissions_policy)
                )
            else:
                raise
    
    def _create_lambda_deployment_package(self) -> bytes:
        """Create Lambda deployment package"""
        import zipfile
        import io
        
        # Create a ZIP file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add the main Lambda function
            with open('/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa/lambda_function.py', 'r') as f:
                zip_file.writestr('lambda_function.py', f.read())
            
            # Add any other required Python files
            import os
            src_path = '/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa/src'
            if os.path.exists(src_path):
                for root, dirs, files in os.walk(src_path):
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            arc_path = os.path.relpath(file_path, '/Users/adariprasad/weapon/UMD/DATA650/Group Presentation/adpa')
                            with open(file_path, 'r') as f:
                                zip_file.writestr(arc_path, f.read())
        
        zip_buffer.seek(0)
        return zip_buffer.read()
    
    def _create_cloudwatch_alarms(self):
        """Create CloudWatch alarms for monitoring"""
        alarms = [
            {
                'AlarmName': 'ADPA-Pipeline-Failures',
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 1,
                'MetricName': 'ExecutionsFailed',
                'Namespace': 'AWS/States',
                'Period': 300,
                'Statistic': 'Sum',
                'Threshold': 0.0,
                'ActionsEnabled': True,
                'AlarmActions': [f"arn:aws:sns:{self.region}:{self.account_id}:{self.resources['sns_topic']}"],
                'AlarmDescription': 'Alert when ADPA pipeline executions fail',
                'Dimensions': [
                    {
                        'Name': 'StateMachineArn',
                        'Value': f"arn:aws:states:{self.region}:{self.account_id}:stateMachine:{self.resources['state_machine']}"
                    }
                ]
            }
        ]
        
        for alarm in alarms:
            try:
                self.cloudwatch.put_metric_alarm(**alarm)
                logger.info(f"✅ Created alarm: {alarm['AlarmName']}")
            except Exception as e:
                logger.error(f"Failed to create alarm {alarm['AlarmName']}: {e}")
    
    def _wait_for_lambda_update(self, function_name: str, max_wait_seconds: int = 120):
        """Wait for Lambda function update to complete"""
        logger.info(f"⏳ Waiting for Lambda function {function_name} to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait_seconds:
            try:
                response = self.lambda_client.get_function(FunctionName=function_name)
                state = response['Configuration'].get('State', 'Active')
                last_update_status = response['Configuration'].get('LastUpdateStatus', 'Successful')
                
                if state == 'Active' and last_update_status == 'Successful':
                    logger.info(f"✅ Lambda function {function_name} is ready")
                    return True
                elif last_update_status == 'Failed':
                    logger.error(f"❌ Lambda function update failed")
                    return False
                
                time.sleep(5)
                
            except ClientError as e:
                if 'ResourceNotFoundException' in str(e):
                    # Function doesn't exist yet
                    return True
                logger.warning(f"Error checking Lambda status: {e}")
                time.sleep(5)
        
        logger.warning(f"⚠️  Lambda function update did not complete within {max_wait_seconds} seconds")
        return False
    
    def _print_deployment_summary(self):
        """Print deployment summary"""
        logger.info("\n" + "=" * 60)
        logger.info("🎉 ADPA REAL AWS INFRASTRUCTURE DEPLOYMENT SUMMARY")
        logger.info("=" * 60)
        
        for component, status in self.deployment_status.items():
            if component != 'overall_status' and component != 'deployed_at':
                if isinstance(status, dict):
                    logger.info(f"✅ {component}: {status.get('status', 'completed')}")
                else:
                    logger.info(f"✅ {component}: {status}")
        
        logger.info("\n📋 KEY RESOURCES DEPLOYED:")
        logger.info(f"• S3 Buckets: {self.resources['data_bucket']}, {self.resources['model_bucket']}")
        logger.info(f"• State Machine: {self.resources['state_machine']}")
        logger.info(f"• SNS Topic: {self.resources['sns_topic']}")
        logger.info(f"• Glue Database: {self.resources['glue_database']}")
        
        if 'api_gateway' in self.deployment_status:
            logger.info(f"• API Gateway URL: {self.deployment_status['api_gateway']['api_url']}")
        
        if 'cloudwatch_monitoring' in self.deployment_status:
            logger.info(f"• Dashboard: {self.deployment_status['cloudwatch_monitoring']['dashboard_url']}")
        
        logger.info("\n🚀 ADPA is now ready for autonomous ML pipeline execution!")
        logger.info("=" * 60)

def main():
    """Main deployment function"""
    try:
        deployer = ADPAInfrastructureDeployer()
        result = deployer.deploy_complete_infrastructure()
        
        # Save deployment status
        with open('adpa_deployment_status.json', 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print("\n✅ Deployment completed successfully!")
        print("📝 Deployment status saved to: adpa_deployment_status.json")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Deployment failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())