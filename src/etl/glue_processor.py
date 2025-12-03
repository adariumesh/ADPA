"""
AWS Glue ETL Integration for ADPA

This module provides serverless ETL capabilities for processing large datasets
that exceed Lambda's limitations (>1GB, >15 minutes processing time).
"""

import json
import os
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
        self.region = region or AWS_REGION
        
        # Try to load credentials from rootkey.csv
        try:
            if get_credentials_from_csv:
                creds = get_credentials_from_csv()
                if creds['access_key_id'] and creds['secret_access_key']:
                    self.glue = boto3.client(
                        'glue', 
                        region_name=self.region,
                        aws_access_key_id=creds['access_key_id'],
                        aws_secret_access_key=creds['secret_access_key']
                    )
                    self.s3 = boto3.client(
                        's3', 
                        region_name=self.region,
                        aws_access_key_id=creds['access_key_id'],
                        aws_secret_access_key=creds['secret_access_key']
                    )
                else:
                    raise ValueError("No credentials in CSV")
            else:
                raise ValueError("Config module not available")
        except Exception:
            # Fallback to default credential chain
            self.glue = boto3.client('glue', region_name=self.region)
            self.s3 = boto3.client('s3', region_name=self.region)
        
        # Configuration from centralized config
        self.role_arn = GLUE_EXECUTION_ROLE
        self.script_bucket = DATA_BUCKET
        self.script_prefix = "glue-scripts/"
        self.output_bucket = DATA_BUCKET
        self.output_prefix = "processed-data/"
    
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
