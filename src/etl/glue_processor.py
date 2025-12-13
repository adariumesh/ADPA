"""
AWS Glue ETL Integration for ADPA

This module provides serverless ETL capabilities for processing large datasets
that exceed Lambda's limitations (>1GB, >15 minutes processing time).
"""

import json
import os
import logging
import boto3
from datetime import datetime
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

# Import centralized AWS configuration
try:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from config.aws_config import (
        AWS_ACCOUNT_ID, AWS_REGION, DATA_BUCKET,
        GLUE_EXECUTION_ROLE, get_credentials_from_csv
    )
except ImportError:
    # Fallback values
    AWS_ACCOUNT_ID = "083308938449"
    AWS_REGION = "us-east-2"
    DATA_BUCKET = f"adpa-data-{AWS_ACCOUNT_ID}-development"
    GLUE_EXECUTION_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/adpa-glue-execution-role"
    get_credentials_from_csv = None


class GlueETLProcessor:
    """Process large datasets using AWS Glue"""
    
    def __init__(self, region: str = None):
        """
        Initialize Glue ETL processor
        
        Args:
            region: AWS region name (defaults to centralized config)
        """
        self.logger = logging.getLogger(__name__)
        self.region = region or AWS_REGION

        session_kwargs = self._resolve_session_kwargs()
        self.glue = boto3.client('glue', **session_kwargs)
        self.s3 = boto3.client('s3', **session_kwargs)
        
        # Configuration from centralized config
        self.role_arn = GLUE_EXECUTION_ROLE
        self.script_bucket = DATA_BUCKET
        self.script_prefix = "glue-scripts/"
        self.output_bucket = DATA_BUCKET
        self.output_prefix = "processed-data/"

    def _resolve_session_kwargs(self) -> Dict[str, Any]:
        """Determine how to authenticate with AWS for Glue/S3 clients."""
        session_kwargs: Dict[str, Any] = {"region_name": self.region}

        if self._should_use_instance_credentials():
            self.logger.info("GlueETLProcessor using IAM role credentials (instance profile)")
            return session_kwargs

        creds = self._load_static_credentials()
        if creds:
            self.logger.info("GlueETLProcessor using static credentials from rootkey.csv")
            session_kwargs.update(
                aws_access_key_id=creds["access_key_id"],
                aws_secret_access_key=creds["secret_access_key"],
            )
            if creds.get("session_token"):
                session_kwargs["aws_session_token"] = creds["session_token"]
        else:
            self.logger.info("GlueETLProcessor falling back to default credential chain")

        return session_kwargs

    @staticmethod
    def _should_use_instance_credentials() -> bool:
        """Prefer Lambda/EC2 role credentials unless explicitly overridden."""
        force_rootkey = os.getenv("FORCE_GLUE_ROOTKEY", "false").lower() == "true"
        if force_rootkey:
            return False

        lambda_env = bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
        exec_env = bool(os.getenv("AWS_EXECUTION_ENV"))
        force_instance = os.getenv("FORCE_INSTANCE_CREDENTIALS", "false").lower() == "true"
        return lambda_env or exec_env or force_instance

    @staticmethod
    def _load_static_credentials() -> Dict[str, str]:
        if not get_credentials_from_csv:
            return {}

        try:
            creds = get_credentials_from_csv()
            if creds.get('access_key_id') and creds.get('secret_access_key'):
                return creds
        except Exception:
            return {}
        return {}
    
    def create_crawler(
        self,
        crawler_name: str,
        s3_path: str,
        database_name: str = 'adpa-data-catalog'
    ) -> Dict[str, Any]:
        """
        Create a Glue crawler to automatically detect schema
        
        Args:
            crawler_name: Name for the crawler
            s3_path: S3 path to crawl
            database_name: Glue database name
            
        Returns:
            Dict containing crawler creation status
        """
        try:
            # Create database if it doesn't exist
            try:
                self.glue.create_database(
                    DatabaseInput={
                        'Name': database_name,
                        'Description': 'ADPA data catalog for ML datasets'
                    }
                )
            except self.glue.exceptions.AlreadyExistsException:
                pass  # Database already exists
            
            # Create crawler
            response = self.glue.create_crawler(
                Name=crawler_name,
                Role=self.role_arn,
                DatabaseName=database_name,
                Targets={
                    'S3Targets': [
                        {
                            'Path': s3_path
                        }
                    ]
                },
                SchemaChangePolicy={
                    'UpdateBehavior': 'UPDATE_IN_DATABASE',
                    'DeleteBehavior': 'LOG'
                },
                Tags={
                    'Project': 'ADPA',
                    'ManagedBy': 'ADPA-Agent'
                }
            )
            
            return {
                "status": "created",
                "crawler_name": crawler_name,
                "database": database_name
            }
            
        except ClientError as e:
            return {
                "status": "failed",
                "error": str(e),
                "error_code": e.response['Error']['Code']
            }
    
    def start_crawler(self, crawler_name: str) -> Dict[str, Any]:
        """
        Start a Glue crawler to detect schema
        
        Args:
            crawler_name: Name of the crawler
            
        Returns:
            Dict containing crawler start status
        """
        try:
            self.glue.start_crawler(Name=crawler_name)
            
            return {
                "status": "started",
                "crawler_name": crawler_name
            }
            
        except ClientError as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def get_crawler_status(self, crawler_name: str) -> Dict[str, Any]:
        """
        Get crawler status and metrics
        
        Args:
            crawler_name: Name of the crawler
            
        Returns:
            Dict containing crawler status
        """
        try:
            response = self.glue.get_crawler(Name=crawler_name)
            crawler = response['Crawler']
            
            return {
                "crawler_name": crawler_name,
                "state": crawler['State'],  # READY, RUNNING, STOPPING
                "last_crawl": crawler.get('LastCrawl', {}),
                "database": crawler['DatabaseName']
            }
            
        except ClientError as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def create_etl_job(
        self,
        job_name: str,
        script_location: str,
        worker_type: str = 'G.1X',
        number_of_workers: int = 2,
        max_retries: int = 1,
        timeout_minutes: int = 120
    ) -> Dict[str, Any]:
        """
        Create a Glue ETL job for data processing
        
        Args:
            job_name: Name for the ETL job
            script_location: S3 path to PySpark script
            worker_type: Worker instance type (G.1X, G.2X, G.025X)
            number_of_workers: Number of workers
            max_retries: Maximum retry attempts
            timeout_minutes: Job timeout in minutes
            
        Returns:
            Dict containing job creation status
        """
        try:
            response = self.glue.create_job(
                Name=job_name,
                Role=self.role_arn,
                Command={
                    'Name': 'glueetl',
                    'ScriptLocation': script_location,
                    'PythonVersion': '3'
                },
                DefaultArguments={
                    '--TempDir': f's3://{self.output_bucket}/temp/',
                    '--job-bookmark-option': 'job-bookmark-enable',
                    '--enable-metrics': '',
                    '--enable-spark-ui': 'true',
                    '--spark-event-logs-path': f's3://{self.output_bucket}/spark-logs/',
                    '--enable-job-insights': 'true'
                },
                MaxRetries=max_retries,
                Timeout=timeout_minutes,
                GlueVersion='4.0',
                WorkerType=worker_type,
                NumberOfWorkers=number_of_workers,
                Tags={
                    'Project': 'ADPA',
                    'Environment': 'development'
                }
            )
            
            return {
                "status": "created",
                "job_name": job_name
            }
            
        except ClientError as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def start_job_run(
        self,
        job_name: str,
        arguments: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Start a Glue ETL job run
        
        Args:
            job_name: Name of the job to run
            arguments: Job arguments (input/output paths, etc.)
            
        Returns:
            Dict containing job run ID and status
        """
        try:
            params = {'JobName': job_name}
            if arguments:
                params['Arguments'] = arguments
            
            response = self.glue.start_job_run(**params)
            
            return {
                "status": "started",
                "job_name": job_name,
                "job_run_id": response['JobRunId']
            }
            
        except ClientError as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def get_job_run_status(
        self,
        job_name: str,
        job_run_id: str
    ) -> Dict[str, Any]:
        """
        Get the status of a Glue job run
        
        Args:
            job_name: Name of the job
            job_run_id: Job run ID
            
        Returns:
            Dict containing job run status and metrics
        """
        try:
            response = self.glue.get_job_run(
                JobName=job_name,
                RunId=job_run_id
            )
            
            job_run = response['JobRun']
            
            return {
                "job_name": job_name,
                "job_run_id": job_run_id,
                "status": job_run['JobRunState'],  # STARTING, RUNNING, STOPPING, STOPPED, SUCCEEDED, FAILED, TIMEOUT
                "started_on": job_run.get('StartedOn', datetime.utcnow()).isoformat() if job_run.get('StartedOn') else None,
                "completed_on": job_run.get('CompletedOn', datetime.utcnow()).isoformat() if job_run.get('CompletedOn') else None,
                "execution_time_seconds": job_run.get('ExecutionTime', 0),
                "worker_type": job_run.get('WorkerType'),
                "number_of_workers": job_run.get('NumberOfWorkers'),
                "error_message": job_run.get('ErrorMessage', '')
            }
            
        except ClientError as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_table_schema(
        self,
        database_name: str,
        table_name: str
    ) -> Dict[str, Any]:
        """
        Get schema information for a Glue catalog table
        
        Args:
            database_name: Database name
            table_name: Table name
            
        Returns:
            Dict containing table schema
        """
        try:
            response = self.glue.get_table(
                DatabaseName=database_name,
                Name=table_name
            )
            
            table = response['Table']
            
            return {
                "database": database_name,
                "table": table_name,
                "columns": [
                    {
                        "name": col['Name'],
                        "type": col['Type'],
                        "comment": col.get('Comment', '')
                    }
                    for col in table['StorageDescriptor']['Columns']
                ],
                "location": table['StorageDescriptor']['Location'],
                "row_count": table.get('Parameters', {}).get('recordCount', 'unknown')
            }
            
        except ClientError as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def ensure_standard_jobs_exist(self) -> Dict[str, Any]:
        """Ensure standard ADPA Glue jobs exist for pipeline execution."""
        
        standard_jobs = {
            'adpa-step0_data_validation': 's3://adpa-glue-scripts-{}/data_validation.py'.format(AWS_ACCOUNT_ID),
            'adpa-step1_data_cleaning': 's3://adpa-glue-scripts-{}/data_cleaning.py'.format(AWS_ACCOUNT_ID), 
            'adpa-step2_feature_engineering': 's3://adpa-glue-scripts-{}/feature_engineering.py'.format(AWS_ACCOUNT_ID),
            'adpa-data_preprocessing': 's3://adpa-glue-scripts-{}/preprocessing.py'.format(AWS_ACCOUNT_ID)
        }
        
        results = {}
        
        for job_name, script_location in standard_jobs.items():
            try:
                # Check if job exists
                try:
                    self.glue.get_job(JobName=job_name)
                    results[job_name] = {'status': 'exists', 'action': 'none'}
                    print(f"✅ Glue job {job_name} already exists")
                    continue
                except ClientError as e:
                    if e.response['Error']['Code'] != 'EntityNotFoundException':
                        raise e
                
                # Create job if it doesn't exist (with mock script for now)
                mock_script_location = f's3://{DATA_BUCKET}/glue-scripts/mock_etl.py'
                result = self.create_etl_job(
                    job_name=job_name,
                    script_location=mock_script_location,
                    worker_type='G.1X',
                    number_of_workers=2
                )
                
                if result.get('success'):
                    results[job_name] = {'status': 'created', 'action': 'created'}
                    print(f"✅ Created Glue job {job_name}")
                else:
                    results[job_name] = {'status': 'failed', 'error': result.get('error')}
                    print(f"❌ Failed to create Glue job {job_name}: {result.get('error')}")
                    
            except Exception as e:
                results[job_name] = {'status': 'error', 'error': str(e)}
                print(f"❌ Error with Glue job {job_name}: {str(e)}")
        
        return results
    
    def create_mock_script_in_s3(self) -> str:
        """Create a mock Glue ETL script in S3 for testing."""
        
        mock_script = '''
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

# Mock Glue ETL script for ADPA testing
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

try:
    # Mock ETL processing
    print("ADPA Mock ETL job executed successfully")
    # In a real implementation, this would process data
finally:
    job.commit()
'''
        
        try:
            s3 = boto3.client('s3', region_name=self.region)
            script_key = 'glue-scripts/mock_etl.py'
            
            s3.put_object(
                Bucket=DATA_BUCKET,
                Key=script_key,
                Body=mock_script.encode('utf-8'),
                ContentType='text/plain'
            )
            
            return f's3://{DATA_BUCKET}/{script_key}'
            
        except Exception as e:
            print(f"Failed to create mock script: {str(e)}")
            return f's3://{DATA_BUCKET}/glue-scripts/mock_etl.py'  # Return path anyway


# Lambda handler for Glue integration
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to interact with AWS Glue
    
    Args:
        event: Contains action and parameters
        context: Lambda context
        
    Returns:
        Dict containing operation results
    """
    action = event.get('action', 'start_job_run')
    processor = GlueETLProcessor()
    
    if action == 'create_crawler':
        return processor.create_crawler(
            crawler_name=event['crawler_name'],
            s3_path=event['s3_path'],
            database_name=event.get('database_name', 'adpa-data-catalog')
        )
    
    elif action == 'start_crawler':
        return processor.start_crawler(event['crawler_name'])
    
    elif action == 'get_crawler_status':
        return processor.get_crawler_status(event['crawler_name'])
    
    elif action == 'create_etl_job':
        return processor.create_etl_job(
            job_name=event['job_name'],
            script_location=event['script_location'],
            worker_type=event.get('worker_type', 'G.1X'),
            number_of_workers=event.get('number_of_workers', 2)
        )
    
    elif action == 'start_job_run':
        return processor.start_job_run(
            job_name=event['job_name'],
            arguments=event.get('arguments')
        )
    
    elif action == 'get_job_run_status':
        return processor.get_job_run_status(
            job_name=event['job_name'],
            job_run_id=event['job_run_id']
        )
    
    elif action == 'get_table_schema':
        return processor.get_table_schema(
            database_name=event['database_name'],
            table_name=event['table_name']
        )
    
    else:
        return {
            "status": "error",
            "message": f"Unknown action: {action}"
        }
