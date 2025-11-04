"""
AWS Glue client for ADPA ETL job management and execution.
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError

from ...agent.core.interfaces import ExecutionResult, StepStatus


class GlueClient:
    """
    AWS Glue client for managing ETL jobs and data catalog operations.
    """
    
    def __init__(self, 
                 region: str = "us-east-1",
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None):
        """
        Initialize Glue client.
        
        Args:
            region: AWS region
            aws_access_key_id: AWS access key (optional)
            aws_secret_access_key: AWS secret key (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.region = region
        
        # Initialize boto3 client
        session_kwargs = {'region_name': region}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs.update({
                'aws_access_key_id': aws_access_key_id,
                'aws_secret_access_key': aws_secret_access_key
            })
        
        self.glue_client = boto3.client('glue', **session_kwargs)
        self.s3_client = boto3.client('s3', **session_kwargs)
        
        self.logger.info("AWS Glue client initialized")
    
    def create_etl_job(self, 
                      job_name: str,
                      script_location: str,
                      role_arn: str,
                      job_type: str = "data_profiling") -> ExecutionResult:
        """
        Create an AWS Glue ETL job.
        
        Args:
            job_name: Name of the Glue job
            script_location: S3 location of the ETL script
            role_arn: IAM role ARN for Glue job execution
            job_type: Type of job (data_profiling, data_cleaning, feature_engineering)
            
        Returns:
            ExecutionResult with job creation details
        """
        try:
            self.logger.info(f"Creating Glue job: {job_name}")
            
            # Job configuration based on type
            job_config = self._get_job_config(job_type)
            
            # Create job
            response = self.glue_client.create_job(
                Name=job_name,
                Description=f"ADPA {job_type} ETL job",
                Role=role_arn,
                Command={
                    'Name': 'glueetl',
                    'ScriptLocation': script_location,
                    'PythonVersion': '3'
                },
                DefaultArguments={
                    '--TempDir': 's3://adpa-data-bucket/temp/',
                    '--job-bookmark-option': 'job-bookmark-enable',
                    '--enable-metrics': '',
                    '--enable-continuous-cloudwatch-log': 'true',
                    '--job-language': 'python'
                },
                MaxRetries=3,
                Timeout=job_config['timeout'],
                MaxCapacity=job_config['max_capacity'],
                Tags={
                    'Project': 'ADPA',
                    'JobType': job_type,
                    'Environment': 'Development'
                }
            )
            
            self.logger.info(f"Successfully created Glue job: {job_name}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                metrics={
                    'job_name': job_name,
                    'job_type': job_type,
                    'max_capacity': job_config['max_capacity'],
                    'timeout': job_config['timeout']
                },
                artifacts={
                    'script_location': script_location,
                    'role_arn': role_arn,
                    'console_url': f"https://{self.region}.console.aws.amazon.com/glue/home?region={self.region}#etl:tab=jobs"
                }
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'AlreadyExistsException':
                self.logger.info(f"Glue job {job_name} already exists")
                return ExecutionResult(
                    status=StepStatus.COMPLETED,
                    metrics={'job_name': job_name, 'status': 'already_exists'}
                )
            
            error_msg = f"Failed to create Glue job: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
        except Exception as e:
            error_msg = f"Unexpected error creating Glue job: {str(e)}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
    
    def run_etl_job(self, 
                   job_name: str,
                   job_arguments: Dict[str, str]) -> ExecutionResult:
        """
        Run an AWS Glue ETL job.
        
        Args:
            job_name: Name of the Glue job to run
            job_arguments: Arguments to pass to the job
            
        Returns:
            ExecutionResult with job run details
        """
        try:
            self.logger.info(f"Starting Glue job run: {job_name}")
            
            # Start job run
            response = self.glue_client.start_job_run(
                JobName=job_name,
                Arguments=job_arguments
            )
            
            job_run_id = response['JobRunId']
            
            self.logger.info(f"Glue job run started: {job_run_id}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                metrics={
                    'job_name': job_name,
                    'job_run_id': job_run_id
                },
                artifacts={
                    'arguments': job_arguments,
                    'console_url': f"https://{self.region}.console.aws.amazon.com/glue/home?region={self.region}#etl:tab=jobRuns"
                }
            )
            
        except ClientError as e:
            error_msg = f"Failed to start Glue job run: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
        except Exception as e:
            error_msg = f"Unexpected error starting Glue job run: {str(e)}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
    
    def monitor_job_run(self, job_name: str, job_run_id: str) -> Dict[str, Any]:
        """
        Monitor a Glue job run.
        
        Args:
            job_name: Name of the Glue job
            job_run_id: ID of the job run
            
        Returns:
            Dictionary with job run status and details
        """
        try:
            response = self.glue_client.get_job_run(
                JobName=job_name,
                RunId=job_run_id
            )
            
            job_run = response['JobRun']
            
            status_info = {
                'job_name': job_name,
                'job_run_id': job_run_id,
                'job_run_state': job_run['JobRunState'],
                'started_on': job_run.get('StartedOn', '').isoformat() if job_run.get('StartedOn') else None,
                'execution_time': job_run.get('ExecutionTime', 0),
                'max_capacity': job_run.get('MaxCapacity', 0)
            }
            
            if 'CompletedOn' in job_run:
                status_info['completed_on'] = job_run['CompletedOn'].isoformat()
                if job_run.get('StartedOn'):
                    duration = (job_run['CompletedOn'] - job_run['StartedOn']).total_seconds()
                    status_info['duration_seconds'] = duration
            
            if 'ErrorMessage' in job_run:
                status_info['error_message'] = job_run['ErrorMessage']
            
            if 'Arguments' in job_run:
                status_info['arguments'] = job_run['Arguments']
            
            return status_info
            
        except ClientError as e:
            self.logger.error(f"Failed to get job run status: {e.response['Error']['Message']}")
            return {'error': e.response['Error']['Message']}
        except Exception as e:
            self.logger.error(f"Unexpected error monitoring job run: {str(e)}")
            return {'error': str(e)}
    
    def wait_for_job_completion(self, 
                               job_name: str, 
                               job_run_id: str, 
                               max_wait_time: int = 3600) -> Dict[str, Any]:
        """
        Wait for a Glue job to complete.
        
        Args:
            job_name: Name of the Glue job
            job_run_id: ID of the job run
            max_wait_time: Maximum time to wait in seconds
            
        Returns:
            Final job status
        """
        start_time = time.time()
        check_interval = 30  # Check every 30 seconds
        
        while (time.time() - start_time) < max_wait_time:
            status = self.monitor_job_run(job_name, job_run_id)
            
            if 'error' in status:
                return status
            
            job_state = status.get('job_run_state')
            self.logger.info(f"Job {job_name} status: {job_state}")
            
            if job_state in ['SUCCEEDED', 'FAILED', 'STOPPED', 'TIMEOUT']:
                return status
            
            time.sleep(check_interval)
        
        return {
            'error': f'Job monitoring timeout after {max_wait_time} seconds',
            'job_run_state': 'TIMEOUT'
        }
    
    def create_data_catalog_table(self, 
                                 database_name: str,
                                 table_name: str,
                                 s3_location: str,
                                 columns: List[Dict[str, str]]) -> ExecutionResult:
        """
        Create a table in the Glue Data Catalog.
        
        Args:
            database_name: Name of the Glue database
            table_name: Name of the table
            s3_location: S3 location of the data
            columns: List of column definitions
            
        Returns:
            ExecutionResult with catalog operation details
        """
        try:
            # Ensure database exists
            self._create_database_if_not_exists(database_name)
            
            # Create table
            table_input = {
                'Name': table_name,
                'Description': f'ADPA data table: {table_name}',
                'StorageDescriptor': {
                    'Columns': columns,
                    'Location': s3_location,
                    'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                    'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                    'SerdeInfo': {
                        'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe',
                        'Parameters': {
                            'field.delim': ',',
                            'skip.header.line.count': '1'
                        }
                    }
                },
                'PartitionKeys': [],
                'TableType': 'EXTERNAL_TABLE'
            }
            
            self.glue_client.create_table(
                DatabaseName=database_name,
                TableInput=table_input
            )
            
            self.logger.info(f"Created catalog table: {database_name}.{table_name}")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                metrics={
                    'database_name': database_name,
                    'table_name': table_name,
                    'columns_count': len(columns)
                },
                artifacts={
                    's3_location': s3_location,
                    'console_url': f"https://{self.region}.console.aws.amazon.com/glue/home?region={self.region}#catalog:tab=tables"
                }
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'AlreadyExistsException':
                self.logger.info(f"Table {database_name}.{table_name} already exists")
                return ExecutionResult(
                    status=StepStatus.COMPLETED,
                    metrics={'table_name': table_name, 'status': 'already_exists'}
                )
            
            error_msg = f"Failed to create catalog table: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
    
    def upload_etl_script(self, script_content: str, script_name: str, bucket: str) -> str:
        """
        Upload ETL script to S3 for Glue job usage.
        
        Args:
            script_content: Content of the ETL script
            script_name: Name of the script file
            bucket: S3 bucket for script storage
            
        Returns:
            S3 URI of the uploaded script
        """
        try:
            key = f"glue-scripts/{script_name}"
            
            self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=script_content,
                ContentType='text/x-python-script'
            )
            
            script_uri = f"s3://{bucket}/{key}"
            self.logger.info(f"Uploaded ETL script: {script_uri}")
            
            return script_uri
            
        except ClientError as e:
            self.logger.error(f"Failed to upload ETL script: {e.response['Error']['Message']}")
            raise
    
    def _get_job_config(self, job_type: str) -> Dict[str, Any]:
        """Get job configuration based on job type."""
        configs = {
            'data_profiling': {
                'max_capacity': 2,
                'timeout': 60
            },
            'data_cleaning': {
                'max_capacity': 5,
                'timeout': 120
            },
            'feature_engineering': {
                'max_capacity': 10,
                'timeout': 180
            }
        }
        
        return configs.get(job_type, configs['data_profiling'])
    
    def _create_database_if_not_exists(self, database_name: str):
        """Create Glue database if it doesn't exist."""
        try:
            self.glue_client.get_database(Name=database_name)
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                self.glue_client.create_database(
                    DatabaseInput={
                        'Name': database_name,
                        'Description': 'ADPA data processing database'
                    }
                )
                self.logger.info(f"Created database: {database_name}")
            else:
                raise
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all ADPA Glue jobs."""
        try:
            response = self.glue_client.get_jobs()
            
            adpa_jobs = []
            for job in response.get('Jobs', []):
                if 'adpa' in job['Name'].lower():
                    adpa_jobs.append({
                        'name': job['Name'],
                        'description': job.get('Description', ''),
                        'role': job['Role'],
                        'created_on': job.get('CreatedOn', '').isoformat() if job.get('CreatedOn') else None,
                        'max_capacity': job.get('MaxCapacity', 0)
                    })
            
            return adpa_jobs
            
        except ClientError as e:
            self.logger.error(f"Failed to list Glue jobs: {e.response['Error']['Message']}")
            return []
    
    def get_job_runs(self, job_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get recent job runs for a specific job."""
        try:
            response = self.glue_client.get_job_runs(
                JobName=job_name,
                MaxResults=max_results
            )
            
            job_runs = []
            for run in response.get('JobRuns', []):
                job_runs.append({
                    'job_run_id': run['Id'],
                    'job_run_state': run['JobRunState'],
                    'started_on': run.get('StartedOn', '').isoformat() if run.get('StartedOn') else None,
                    'completed_on': run.get('CompletedOn', '').isoformat() if run.get('CompletedOn') else None,
                    'execution_time': run.get('ExecutionTime', 0),
                    'error_message': run.get('ErrorMessage', '')
                })
            
            return job_runs
            
        except ClientError as e:
            self.logger.error(f"Failed to get job runs: {e.response['Error']['Message']}")
            return []