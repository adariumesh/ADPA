"""
ADPA AWS Configuration Module
Centralized AWS configuration that reads credentials from rootkey.csv
All hardcoded AWS values should be imported from this module.
"""

import os
import csv
from pathlib import Path
from typing import Dict, Optional
import boto3


# ============================================================================
# AWS ACCOUNT CONFIGURATION - SINGLE SOURCE OF TRUTH
# ============================================================================

AWS_ACCOUNT_ID = "083308938449"
AWS_REGION = "us-east-2"
ENVIRONMENT = os.getenv("ADPA_ENVIRONMENT", "development")

# ============================================================================
# S3 BUCKET NAMES
# ============================================================================

DATA_BUCKET = f"adpa-data-{AWS_ACCOUNT_ID}-{ENVIRONMENT}"
MODEL_BUCKET = f"adpa-models-{AWS_ACCOUNT_ID}-{ENVIRONMENT}"
FRONTEND_BUCKET = f"adpa-frontend-{AWS_ACCOUNT_ID}"

# ============================================================================
# IAM ROLE ARNS
# ============================================================================

LAMBDA_EXECUTION_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/adpa-lambda-execution-role-{ENVIRONMENT}"
SAGEMAKER_EXECUTION_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/adpa-sagemaker-execution-role"
GLUE_EXECUTION_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/adpa-glue-execution-role"
STEP_FUNCTIONS_ROLE = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/adpa-stepfunctions-role"

# ============================================================================
# STEP FUNCTIONS
# ============================================================================

STEP_FUNCTION_ARN = f"arn:aws:states:{AWS_REGION}:{AWS_ACCOUNT_ID}:stateMachine:adpa-ml-pipeline"

# ============================================================================
# SNS TOPICS
# ============================================================================

PIPELINE_NOTIFICATIONS_TOPIC = f"arn:aws:sns:{AWS_REGION}:{AWS_ACCOUNT_ID}:adpa-pipeline-notifications"

# ============================================================================
# LAMBDA FUNCTIONS
# ============================================================================

LAMBDA_FUNCTION_NAME = f"adpa-data-processor-{ENVIRONMENT}"
LAMBDA_LAYER_NAME = "adpa-ml-dependencies-clean"

# ============================================================================
# CREDENTIALS MANAGEMENT
# ============================================================================

def get_credentials_from_csv(csv_path: Optional[str] = None) -> Dict[str, str]:
    """
    Read AWS credentials from rootkey.csv file.
    
    Args:
        csv_path: Path to the CSV file. If None, searches in common locations.
        
    Returns:
        Dictionary with 'access_key_id' and 'secret_access_key'
    """
    # Search paths for credentials file
    search_paths = []
    
    if csv_path:
        search_paths.append(Path(csv_path))
    
    # Add common locations
    project_root = Path(__file__).parent.parent
    search_paths.extend([
        project_root / "rootkey.csv",
        Path.home() / ".aws" / "rootkey.csv",
        Path.cwd() / "rootkey.csv",
    ])
    
    for path in search_paths:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        return {
                            'access_key_id': row.get('Access key ID', ''),
                            'secret_access_key': row.get('Secret access key', '')
                        }
            except Exception as e:
                print(f"Warning: Could not read credentials from {path}: {e}")
                continue
    
    # Fallback to environment variables
    return {
        'access_key_id': os.getenv('AWS_ACCESS_KEY_ID', ''),
        'secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', '')
    }


def get_boto3_session(csv_path: Optional[str] = None) -> boto3.Session:
    """
    Create a boto3 session using credentials from rootkey.csv.
    
    Args:
        csv_path: Optional path to credentials CSV file
        
    Returns:
        Configured boto3 Session
    """
    creds = get_credentials_from_csv(csv_path)
    
    if creds['access_key_id'] and creds['secret_access_key']:
        return boto3.Session(
            aws_access_key_id=creds['access_key_id'],
            aws_secret_access_key=creds['secret_access_key'],
            region_name=AWS_REGION
        )
    else:
        # Fall back to default credential chain
        return boto3.Session(region_name=AWS_REGION)


def get_boto3_client(service_name: str, csv_path: Optional[str] = None):
    """
    Get a boto3 client for a specific AWS service using rootkey.csv credentials.
    
    Args:
        service_name: AWS service name (e.g., 's3', 'lambda', 'sagemaker')
        csv_path: Optional path to credentials CSV file
        
    Returns:
        Configured boto3 client
    """
    session = get_boto3_session(csv_path)
    return session.client(service_name)


def get_boto3_resource(service_name: str, csv_path: Optional[str] = None):
    """
    Get a boto3 resource for a specific AWS service using rootkey.csv credentials.
    
    Args:
        service_name: AWS service name (e.g., 's3', 'dynamodb')
        csv_path: Optional path to credentials CSV file
        
    Returns:
        Configured boto3 resource
    """
    session = get_boto3_session(csv_path)
    return session.resource(service_name)


# ============================================================================
# CONFIGURATION DICTIONARY (for backward compatibility)
# ============================================================================

AWS_CONFIG = {
    'account_id': AWS_ACCOUNT_ID,
    'region': AWS_REGION,
    'environment': ENVIRONMENT,
    
    # S3 Buckets
    'data_bucket': DATA_BUCKET,
    'model_bucket': MODEL_BUCKET,
    'frontend_bucket': FRONTEND_BUCKET,
    
    # IAM Roles
    'lambda_role': LAMBDA_EXECUTION_ROLE,
    'sagemaker_role': SAGEMAKER_EXECUTION_ROLE,
    'glue_role': GLUE_EXECUTION_ROLE,
    'stepfunctions_role': STEP_FUNCTIONS_ROLE,
    
    # Step Functions
    'step_function_arn': STEP_FUNCTION_ARN,
    
    # SNS
    'notifications_topic': PIPELINE_NOTIFICATIONS_TOPIC,
    
    # Lambda
    'lambda_function_name': LAMBDA_FUNCTION_NAME,
    'lambda_layer_name': LAMBDA_LAYER_NAME,
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_s3_uri(bucket: str, key: str) -> str:
    """Generate S3 URI from bucket and key"""
    return f"s3://{bucket}/{key}"


def get_cloudwatch_dashboard_url(dashboard_name: str = "ADPA-Dashboard") -> str:
    """Generate CloudWatch dashboard URL"""
    return f"https://{AWS_REGION}.console.aws.amazon.com/cloudwatch/home?region={AWS_REGION}#dashboards:name={dashboard_name}"


def get_lambda_console_url() -> str:
    """Generate Lambda console URL"""
    return f"https://{AWS_REGION}.console.aws.amazon.com/lambda/home?region={AWS_REGION}#/functions/{LAMBDA_FUNCTION_NAME}"


def get_step_functions_console_url() -> str:
    """Generate Step Functions console URL"""
    return f"https://{AWS_REGION}.console.aws.amazon.com/states/home?region={AWS_REGION}#/statemachines/view/{STEP_FUNCTION_ARN}"


def validate_config():
    """Validate that all required configuration is present"""
    required = [
        ('AWS_ACCOUNT_ID', AWS_ACCOUNT_ID),
        ('AWS_REGION', AWS_REGION),
        ('DATA_BUCKET', DATA_BUCKET),
        ('MODEL_BUCKET', MODEL_BUCKET),
    ]
    
    missing = [name for name, value in required if not value]
    
    if missing:
        raise ValueError(f"Missing required AWS configuration: {', '.join(missing)}")
    
    return True


# Validate on import
try:
    validate_config()
except ValueError as e:
    print(f"Warning: {e}")
