"""
AWS S3 client for ADPA data storage and retrieval.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Union
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import pandas as pd
from io import BytesIO

from ...agent.core.interfaces import ExecutionResult, StepStatus


class S3Client:
    """
    AWS S3 client for handling data upload, download, and management.
    """
    
    def __init__(self, 
                 bucket_name: Optional[str] = None,
                 region: str = "us-east-1",
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None):
        """
        Initialize S3 client.
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region
            aws_access_key_id: AWS access key (optional, can use env vars)
            aws_secret_access_key: AWS secret key (optional, can use env vars)
        """
        self.logger = logging.getLogger(__name__)
        self.bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME', 'adpa-data-bucket')
        self.region = region
        
        # Initialize boto3 client
        try:
            session_kwargs = {'region_name': region}
            if aws_access_key_id and aws_secret_access_key:
                session_kwargs.update({
                    'aws_access_key_id': aws_access_key_id,
                    'aws_secret_access_key': aws_secret_access_key
                })
            
            self.s3_client = boto3.client('s3', **session_kwargs)
            self.s3_resource = boto3.resource('s3', **session_kwargs)
            
            # Test connection
            self._test_connection()
            self.logger.info(f"S3 client initialized for bucket: {self.bucket_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise
    
    def upload_dataset(self, 
                      data: Union[pd.DataFrame, str], 
                      key: str,
                      metadata: Optional[Dict[str, str]] = None) -> ExecutionResult:
        """
        Upload a dataset to S3.
        
        Args:
            data: DataFrame or file path to upload
            key: S3 object key (path within bucket)
            metadata: Optional metadata to attach
            
        Returns:
            ExecutionResult with upload details
        """
        try:
            self.logger.info(f"Uploading dataset to s3://{self.bucket_name}/{key}")
            
            if isinstance(data, pd.DataFrame):
                # Upload DataFrame as CSV
                csv_buffer = BytesIO()
                data.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                
                extra_args = {'ContentType': 'text/csv'}
                if metadata:
                    extra_args['Metadata'] = metadata
                
                self.s3_client.upload_fileobj(
                    csv_buffer, 
                    self.bucket_name, 
                    key,
                    ExtraArgs=extra_args
                )
                
                upload_size = len(csv_buffer.getvalue())
                
            elif isinstance(data, str) and os.path.exists(data):
                # Upload file
                extra_args = {}
                if metadata:
                    extra_args['Metadata'] = metadata
                
                self.s3_client.upload_file(
                    data, 
                    self.bucket_name, 
                    key,
                    ExtraArgs=extra_args if extra_args else None
                )
                
                upload_size = os.path.getsize(data)
                
            else:
                return ExecutionResult(
                    status=StepStatus.FAILED,
                    errors=["Invalid data input for upload"]
                )
            
            # Get object details
            obj_info = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            
            self.logger.info(f"Successfully uploaded {upload_size} bytes to S3")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                metrics={
                    "upload_size_bytes": upload_size,
                    "s3_key": key,
                    "bucket": self.bucket_name,
                    "last_modified": obj_info['LastModified'].isoformat()
                },
                artifacts={
                    "s3_uri": f"s3://{self.bucket_name}/{key}",
                    "object_metadata": obj_info.get('Metadata', {}),
                    "content_type": obj_info.get('ContentType', '')
                }
            )
            
        except ClientError as e:
            error_msg = f"S3 upload failed: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
        except Exception as e:
            error_msg = f"Unexpected error during S3 upload: {str(e)}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
    
    def download_dataset(self, key: str) -> ExecutionResult:
        """
        Download a dataset from S3.
        
        Args:
            key: S3 object key
            
        Returns:
            ExecutionResult with downloaded DataFrame
        """
        try:
            self.logger.info(f"Downloading dataset from s3://{self.bucket_name}/{key}")
            
            # Get object
            obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            
            # Read data based on file type
            if key.endswith('.csv'):
                data = pd.read_csv(obj['Body'])
            elif key.endswith('.json'):
                data = pd.read_json(obj['Body'])
            elif key.endswith('.parquet'):
                data = pd.read_parquet(obj['Body'])
            else:
                return ExecutionResult(
                    status=StepStatus.FAILED,
                    errors=[f"Unsupported file format for key: {key}"]
                )
            
            download_size = obj['ContentLength']
            
            self.logger.info(f"Successfully downloaded {data.shape[0]} rows, {data.shape[1]} columns")
            
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=data,
                metrics={
                    "download_size_bytes": download_size,
                    "rows": len(data),
                    "columns": len(data.columns),
                    "s3_key": key
                },
                artifacts={
                    "s3_uri": f"s3://{self.bucket_name}/{key}",
                    "last_modified": obj['LastModified'].isoformat(),
                    "content_type": obj.get('ContentType', '')
                }
            )
            
        except ClientError as e:
            error_msg = f"S3 download failed: {e.response['Error']['Message']}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
        except Exception as e:
            error_msg = f"Unexpected error during S3 download: {str(e)}"
            self.logger.error(error_msg)
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[error_msg]
            )
    
    def list_datasets(self, prefix: str = "") -> List[Dict[str, Any]]:
        """
        List datasets in the S3 bucket.
        
        Args:
            prefix: Optional prefix to filter objects
            
        Returns:
            List of dataset information
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            datasets = []
            for obj in response.get('Contents', []):
                datasets.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    's3_uri': f"s3://{self.bucket_name}/{obj['Key']}"
                })
            
            return datasets
            
        except ClientError as e:
            self.logger.error(f"Failed to list S3 objects: {e.response['Error']['Message']}")
            return []
    
    def create_bucket_if_not_exists(self) -> bool:
        """
        Create the S3 bucket if it doesn't exist.
        
        Returns:
            True if bucket exists or was created successfully
        """
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self.logger.info(f"Bucket {self.bucket_name} already exists")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Bucket doesn't exist, create it
                try:
                    if self.region == 'us-east-1':
                        # us-east-1 doesn't need LocationConstraint
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    
                    self.logger.info(f"Created bucket {self.bucket_name}")
                    return True
                    
                except ClientError as create_error:
                    self.logger.error(f"Failed to create bucket: {create_error.response['Error']['Message']}")
                    return False
            else:
                self.logger.error(f"Error checking bucket: {e.response['Error']['Message']}")
                return False
    
    def _test_connection(self):
        """Test S3 connection and credentials."""
        try:
            # Try to list buckets to test credentials
            self.s3_client.list_buckets()
            self.logger.info("S3 connection test successful")
        except NoCredentialsError:
            raise Exception("AWS credentials not found. Please configure credentials.")
        except ClientError as e:
            raise Exception(f"S3 connection test failed: {e.response['Error']['Message']}")
    
    def get_bucket_info(self) -> Dict[str, Any]:
        """Get information about the current bucket."""
        try:
            # Get bucket location
            location = self.s3_client.get_bucket_location(Bucket=self.bucket_name)
            
            # Get bucket size (approximate)
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            
            total_size = 0
            object_count = 0
            for obj in response.get('Contents', []):
                total_size += obj['Size']
                object_count += 1
            
            return {
                'bucket_name': self.bucket_name,
                'region': location['LocationConstraint'] or 'us-east-1',
                'object_count': object_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2)
            }
            
        except ClientError as e:
            self.logger.error(f"Failed to get bucket info: {e.response['Error']['Message']}")
            return {}
    
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for S3 object access.
        
        Args:
            key: S3 object key
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL or None if error
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            self.logger.error(f"Failed to generate presigned URL: {e.response['Error']['Message']}")
            return None