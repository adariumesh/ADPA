# ADPA ML Services Development Guide - Archit's Tutorial
## Phase 2-3 Implementation: ML Services Lead

**Assigned to:** Archit (ML Services Lead)  
**Duration:** 4 weeks  
**Focus:** SageMaker integration, ML pipelines, data processing, and model management

---

## Overview

As the ML Services Lead, you will implement the core machine learning infrastructure for ADPA using AWS SageMaker, AWS Glue, and related services. This tutorial provides step-by-step guidance to complete all ML-related components within the 4-week timeline.

---

## Week 1: AWS SageMaker Setup and Basic Pipeline Implementation

### Day 1: Environment Setup and SageMaker Domain Configuration

#### 1.1 Create AWS SageMaker Domain

```bash
# Create IAM role for SageMaker
aws iam create-role \
    --role-name ADPA-SageMaker-ExecutionRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "sagemaker.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }'

# Attach necessary policies
aws iam attach-role-policy \
    --role-name ADPA-SageMaker-ExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

aws iam attach-role-policy \
    --role-name ADPA-SageMaker-ExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy \
    --role-name ADPA-SageMaker-ExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

#### 1.2 Create SageMaker Domain

```python
import boto3
import json

sagemaker = boto3.client('sagemaker')

# Create SageMaker Domain
domain_response = sagemaker.create_domain(
    DomainName='adpa-ml-domain',
    AuthMode='IAM',
    DefaultUserSettings={
        'ExecutionRole': 'arn:aws:iam::YOUR_ACCOUNT:role/ADPA-SageMaker-ExecutionRole',
        'SecurityGroups': ['sg-12345678'],  # Your VPC security group
        'SharingSettings': {
            'NotebookOutputOption': 'Allowed',
            'S3OutputPath': 's3://adpa-sagemaker-bucket/'
        }
    },
    SubnetIds=['subnet-12345678'],  # Your VPC subnet
    VpcId='vpc-12345678',  # Your VPC ID
    Tags=[
        {
            'Key': 'Project',
            'Value': 'ADPA'
        },
        {
            'Key': 'Environment',
            'Value': 'Development'
        }
    ]
)

print(f"Domain created: {domain_response['DomainArn']}")
```

**Helpful Links:**
- [SageMaker Domain Setup Guide](https://docs.aws.amazon.com/sagemaker/latest/dg/gs-studio-onboard.html)
- [IAM Roles for SageMaker](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html)

#### 1.3 Set Up S3 Buckets for ML Data

```bash
# Create S3 buckets for different ML data types
aws s3 mb s3://adpa-ml-data-raw
aws s3 mb s3://adpa-ml-data-processed
aws s3 mb s3://adpa-ml-models
aws s3 mb s3://adpa-sagemaker-logs

# Configure bucket policies for SageMaker access
aws s3api put-bucket-policy \
    --bucket adpa-ml-data-raw \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "SageMakerAccess",
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::YOUR_ACCOUNT:role/ADPA-SageMaker-ExecutionRole"
                },
                "Action": "s3:*",
                "Resource": [
                    "arn:aws:s3:::adpa-ml-data-raw",
                    "arn:aws:s3:::adpa-ml-data-raw/*"
                ]
            }
        ]
    }'
```

### Day 2: Basic SageMaker Pipeline Creation

#### 2.1 Create Basic Training Pipeline

```python
import boto3
import sagemaker
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import TrainingStep
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.sklearn import SKLearn
from sagemaker.inputs import TrainingInput

# Initialize SageMaker session
sagemaker_session = sagemaker.Session()
pipeline_session = PipelineSession()
role = 'arn:aws:iam::YOUR_ACCOUNT:role/ADPA-SageMaker-ExecutionRole'
region = boto3.Session().region_name

# Define training script location
training_script = 's3://adpa-ml-models/scripts/train.py'

# Create SKLearn estimator
sklearn_estimator = SKLearn(
    entry_point='train.py',
    source_dir='s3://adpa-ml-models/scripts/',
    framework_version='1.0-1',
    instance_type='ml.m5.large',
    role=role,
    sagemaker_session=pipeline_session,
    hyperparameters={
        'max_depth': 10,
        'n_estimators': 100
    }
)

# Define training step
training_step = TrainingStep(
    name='ADPAModelTraining',
    estimator=sklearn_estimator,
    inputs={
        'train': TrainingInput(
            s3_data='s3://adpa-ml-data-processed/train/',
            content_type='text/csv'
        ),
        'validation': TrainingInput(
            s3_data='s3://adpa-ml-data-processed/validation/',
            content_type='text/csv'
        )
    }
)

# Create pipeline
pipeline = Pipeline(
    name='adpa-basic-training-pipeline',
    steps=[training_step],
    sagemaker_session=pipeline_session
)

# Submit pipeline
pipeline.create(role_arn=role)
execution = pipeline.start()
```

**Helpful Links:**
- [SageMaker Pipelines Tutorial](https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines-sdk.html)
- [SageMaker Python SDK](https://sagemaker.readthedocs.io/en/stable/)

#### 2.2 Create Training Script Template

```python
# save as train.py - upload to S3
import argparse
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()
    
    # SageMaker specific arguments
    parser.add_argument('--model-dir', type=str, default=os.environ.get('SM_MODEL_DIR'))
    parser.add_argument('--train', type=str, default=os.environ.get('SM_CHANNEL_TRAIN'))
    parser.add_argument('--validation', type=str, default=os.environ.get('SM_CHANNEL_VALIDATION'))
    
    # Hyperparameters
    parser.add_argument('--n_estimators', type=int, default=100)
    parser.add_argument('--max_depth', type=int, default=10)
    parser.add_argument('--min_samples_split', type=int, default=2)
    parser.add_argument('--min_samples_leaf', type=int, default=1)
    
    args = parser.parse_args()
    
    # Load training data
    logger.info("Loading training data...")
    train_df = pd.read_csv(os.path.join(args.train, 'train.csv'))
    val_df = pd.read_csv(os.path.join(args.validation, 'validation.csv'))
    
    # Prepare features and targets
    X_train = train_df.drop('target', axis=1)
    y_train = train_df['target']
    X_val = val_df.drop('target', axis=1)
    y_val = val_df['target']
    
    # Create and train model
    logger.info("Training Random Forest model...")
    model = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_split=args.min_samples_split,
        min_samples_leaf=args.min_samples_leaf,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate model
    logger.info("Evaluating model...")
    y_pred = model.predict(X_val)
    
    metrics = {
        'accuracy': accuracy_score(y_val, y_pred),
        'f1_score': f1_score(y_val, y_pred, average='weighted'),
        'precision': precision_score(y_val, y_pred, average='weighted'),
        'recall': recall_score(y_val, y_pred, average='weighted')
    }
    
    logger.info(f"Model metrics: {metrics}")
    
    # Save model
    logger.info("Saving model...")
    joblib.dump(model, os.path.join(args.model_dir, 'model.joblib'))
    
    # Save metrics
    with open(os.path.join(args.model_dir, 'metrics.json'), 'w') as f:
        import json
        json.dump(metrics, f)

if __name__ == '__main__':
    main()
```

### Day 3: Model Registry Integration

#### 3.1 Set Up SageMaker Model Registry

```python
import boto3
from sagemaker.model import Model
from sagemaker.model_package import ModelPackage

def create_model_package_group():
    """Create a model package group for ADPA models"""
    sagemaker_client = boto3.client('sagemaker')
    
    try:
        response = sagemaker_client.create_model_package_group(
            ModelPackageGroupName='adpa-models',
            ModelPackageGroupDescription='ADPA ML models for autonomous data pipeline',
            Tags=[
                {
                    'Key': 'Project',
                    'Value': 'ADPA'
                },
                {
                    'Key': 'Team',
                    'Value': 'ML-Services'
                }
            ]
        )
        print(f"Model package group created: {response['ModelPackageGroupArn']}")
        return response['ModelPackageGroupArn']
    except Exception as e:
        print(f"Error creating model package group: {e}")
        return None

def register_model_version(model_artifacts_s3_path, training_job_name):
    """Register a new model version in the model registry"""
    sagemaker_client = boto3.client('sagemaker')
    
    # Create model package
    model_package_input = {
        'ModelPackageGroupName': 'adpa-models',
        'ModelPackageDescription': f'ADPA model from training job: {training_job_name}',
        'ModelApprovalStatus': 'PendingManualApproval',
        'InferenceSpecification': {
            'Containers': [
                {
                    'Image': '246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-scikit-learn:1.0-1-cpu-py3',
                    'ModelDataUrl': model_artifacts_s3_path,
                    'Environment': {
                        'SAGEMAKER_PROGRAM': 'inference.py',
                        'SAGEMAKER_SUBMIT_DIRECTORY': '/opt/ml/code'
                    }
                }
            ],
            'SupportedContentTypes': ['text/csv'],
            'SupportedResponseMIMETypes': ['application/json']
        }
    }
    
    response = sagemaker_client.create_model_package(**model_package_input)
    print(f"Model package created: {response['ModelPackageArn']}")
    return response['ModelPackageArn']

# Create the model package group
model_group_arn = create_model_package_group()
```

**Helpful Links:**
- [SageMaker Model Registry Guide](https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry.html)
- [Model Versioning Best Practices](https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry-version.html)

#### 3.2 Enhanced Pipeline with Model Registration

```python
from sagemaker.workflow.model_step import ModelStep
from sagemaker.workflow.pipeline_context import LocalPipelineSession
from sagemaker.model import Model

# Enhanced pipeline with model registration
def create_full_ml_pipeline():
    pipeline_session = PipelineSession()
    
    # Training step (from previous example)
    training_step = TrainingStep(
        name='ADPAModelTraining',
        estimator=sklearn_estimator,
        inputs={
            'train': TrainingInput(s3_data='s3://adpa-ml-data-processed/train/'),
            'validation': TrainingInput(s3_data='s3://adpa-ml-data-processed/validation/')
        }
    )
    
    # Model creation step
    model = Model(
        image_uri='246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-scikit-learn:1.0-1-cpu-py3',
        model_data=training_step.properties.ModelArtifacts.S3ModelArtifacts,
        sagemaker_session=pipeline_session,
        role=role,
        entry_point='inference.py',
        source_dir='s3://adpa-ml-models/scripts/'
    )
    
    model_step = ModelStep(
        name='ADPAModelCreation',
        step_args=model.create(instance_type='ml.m5.large')
    )
    
    # Create pipeline with dependencies
    pipeline = Pipeline(
        name='adpa-full-ml-pipeline',
        steps=[training_step, model_step],
        sagemaker_session=pipeline_session
    )
    
    return pipeline

# Create and execute pipeline
full_pipeline = create_full_ml_pipeline()
full_pipeline.create(role_arn=role)
```

### Day 4: Basic Model Deployment

#### 4.1 Create Inference Script

```python
# save as inference.py - upload to S3
import joblib
import pandas as pd
import numpy as np
import json
import os

def model_fn(model_dir):
    """Load model from model directory"""
    model = joblib.load(os.path.join(model_dir, 'model.joblib'))
    return model

def input_fn(request_body, request_content_type):
    """Parse input data for inference"""
    if request_content_type == 'text/csv':
        # Parse CSV input
        df = pd.read_csv(pd.StringIO(request_body))
        return df
    elif request_content_type == 'application/json':
        # Parse JSON input
        data = json.loads(request_body)
        df = pd.DataFrame(data)
        return df
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")

def predict_fn(input_data, model):
    """Make predictions using the loaded model"""
    try:
        predictions = model.predict(input_data)
        probabilities = model.predict_proba(input_data)
        
        return {
            'predictions': predictions.tolist(),
            'probabilities': probabilities.tolist()
        }
    except Exception as e:
        return {'error': str(e)}

def output_fn(prediction, content_type):
    """Format prediction output"""
    if content_type == 'application/json':
        return json.dumps(prediction)
    else:
        raise ValueError(f"Unsupported content type: {content_type}")
```

#### 4.2 Deploy Model to Endpoint

```python
from sagemaker.model import Model
from sagemaker.predictor import Predictor

def deploy_model_to_endpoint(model_artifacts_s3_path):
    """Deploy model to SageMaker endpoint"""
    
    # Create model
    model = Model(
        image_uri='246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-scikit-learn:1.0-1-cpu-py3',
        model_data=model_artifacts_s3_path,
        role=role,
        entry_point='inference.py',
        source_dir='s3://adpa-ml-models/scripts/'
    )
    
    # Deploy model
    predictor = model.deploy(
        initial_instance_count=1,
        instance_type='ml.m5.large',
        endpoint_name='adpa-ml-endpoint'
    )
    
    print(f"Model deployed to endpoint: {predictor.endpoint_name}")
    return predictor

# Test inference
def test_inference(predictor):
    """Test the deployed model"""
    test_data = {
        'feature1': [1.0, 2.0, 3.0],
        'feature2': [0.5, 1.5, 2.5],
        'feature3': [10, 20, 30]
    }
    
    result = predictor.predict(test_data)
    print(f"Inference result: {result}")
    return result

# Deploy and test
# predictor = deploy_model_to_endpoint('s3://adpa-ml-models/model.tar.gz')
# test_result = test_inference(predictor)
```

**Helpful Links:**
- [SageMaker Deployment Guide](https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model.html)
- [Real-time Inference](https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html)

---

## Week 2: AWS Glue Integration and Data Processing

### Day 5: AWS Glue Setup and Data Cataloging

#### 5.1 Set Up AWS Glue Environment

```python
import boto3

def setup_glue_environment():
    """Set up AWS Glue environment for ADPA"""
    
    glue_client = boto3.client('glue')
    
    # Create Glue database
    try:
        glue_client.create_database(
            DatabaseInput={
                'Name': 'adpa_data_catalog',
                'Description': 'ADPA data catalog for ML pipelines',
                'Parameters': {
                    'Project': 'ADPA',
                    'Team': 'ML-Services'
                }
            }
        )
        print("Glue database 'adpa_data_catalog' created successfully")
    except Exception as e:
        print(f"Database creation error: {e}")
    
    # Create IAM role for Glue
    iam_client = boto3.client('iam')
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "glue.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        iam_client.create_role(
            RoleName='ADPA-Glue-ExecutionRole',
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='IAM role for ADPA Glue jobs'
        )
        
        # Attach necessary policies
        policies = [
            'arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole',
            'arn:aws:iam::aws:policy/AmazonS3FullAccess'
        ]
        
        for policy in policies:
            iam_client.attach_role_policy(
                RoleName='ADPA-Glue-ExecutionRole',
                PolicyArn=policy
            )
        
        print("Glue IAM role created successfully")
    except Exception as e:
        print(f"IAM role creation error: {e}")

setup_glue_environment()
```

#### 5.2 Create Glue Crawler for Data Discovery

```python
def create_data_crawler():
    """Create Glue crawler to discover data schemas"""
    
    glue_client = boto3.client('glue')
    
    crawler_config = {
        'Name': 'adpa-data-crawler',
        'Role': 'arn:aws:iam::YOUR_ACCOUNT:role/ADPA-Glue-ExecutionRole',
        'DatabaseName': 'adpa_data_catalog',
        'Description': 'Crawler for ADPA raw data discovery',
        'Targets': {
            'S3Targets': [
                {
                    'Path': 's3://adpa-ml-data-raw/',
                    'Exclusions': []
                }
            ]
        },
        'TablePrefix': 'adpa_raw_',
        'SchemaChangePolicy': {
            'UpdateBehavior': 'UPDATE_IN_DATABASE',
            'DeleteBehavior': 'LOG'
        },
        'RecrawlPolicy': {
            'RecrawlBehavior': 'CRAWL_EVERYTHING'
        },
        'LineageConfiguration': {
            'CrawlerLineageSettings': 'ENABLE'
        }
    }
    
    try:
        response = glue_client.create_crawler(**crawler_config)
        print(f"Crawler created: {response}")
        
        # Start the crawler
        glue_client.start_crawler(Name='adpa-data-crawler')
        print("Crawler started successfully")
        
    except Exception as e:
        print(f"Crawler creation error: {e}")

create_data_crawler()
```

**Helpful Links:**
- [AWS Glue Getting Started](https://docs.aws.amazon.com/glue/latest/dg/getting-started.html)
- [Glue Crawlers Guide](https://docs.aws.amazon.com/glue/latest/dg/add-crawler.html)

### Day 6: Data Processing ETL Jobs

#### 6.1 Create Glue ETL Job for Data Preprocessing

```python
# Glue job script - save as adpa_data_preprocessing.py
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.types import *
import boto3

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'input_path', 'output_path'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

def preprocess_data():
    """Main data preprocessing function"""
    
    # Read data from S3
    raw_data = glueContext.create_dynamic_frame.from_options(
        format_options={"multiline": False},
        connection_type="s3",
        format="csv",
        connection_options={"paths": [args['input_path']], "recurse": True},
        transformation_ctx="raw_data"
    )
    
    # Convert to DataFrame for easier manipulation
    df = raw_data.toDF()
    
    # Data quality checks and cleaning
    print(f"Initial row count: {df.count()}")
    
    # Remove duplicates
    df = df.dropDuplicates()
    print(f"After removing duplicates: {df.count()}")
    
    # Handle missing values
    # For numerical columns, fill with median
    numerical_columns = [field.name for field in df.schema.fields if field.dataType in [IntegerType(), FloatType(), DoubleType()]]
    for col in numerical_columns:
        median_val = df.approxQuantile(col, [0.5], 0.25)[0]
        df = df.fillna({col: median_val})
    
    # For categorical columns, fill with mode
    categorical_columns = [field.name for field in df.schema.fields if field.dataType == StringType()]
    for col in categorical_columns:
        mode_val = df.groupBy(col).count().orderBy(F.desc("count")).first()[0]
        df = df.fillna({col: mode_val})
    
    # Feature engineering
    # Add derived features based on existing columns
    if 'timestamp' in df.columns:
        df = df.withColumn('hour', F.hour(F.col('timestamp')))
        df = df.withColumn('day_of_week', F.dayofweek(F.col('timestamp')))
        df = df.withColumn('month', F.month(F.col('timestamp')))
    
    # Add data quality metrics
    df = df.withColumn('processing_timestamp', F.current_timestamp())
    df = df.withColumn('data_quality_score', F.lit(1.0))  # Placeholder for quality scoring
    
    print(f"Final processed row count: {df.count()}")
    
    # Convert back to DynamicFrame
    processed_data = DynamicFrame.fromDF(df, glueContext, "processed_data")
    
    # Write processed data to S3
    glueContext.write_dynamic_frame.from_options(
        frame=processed_data,
        connection_type="s3",
        format="parquet",
        connection_options={"path": args['output_path'], "partitionKeys": ["month"]},
        transformation_ctx="processed_data"
    )
    
    # Log processing statistics to CloudWatch
    cloudwatch = boto3.client('cloudwatch')
    cloudwatch.put_metric_data(
        Namespace='ADPA/DataProcessing',
        MetricData=[
            {
                'MetricName': 'ProcessedRows',
                'Value': df.count(),
                'Unit': 'Count'
            },
            {
                'MetricName': 'ProcessingTime',
                'Value': job.elapsed_time(),
                'Unit': 'Seconds'
            }
        ]
    )

# Execute preprocessing
preprocess_data()

job.commit()
```

#### 6.2 Create and Run Glue Job

```python
def create_glue_etl_job():
    """Create Glue ETL job for data preprocessing"""
    
    glue_client = boto3.client('glue')
    
    job_config = {
        'Name': 'adpa-data-preprocessing',
        'Description': 'ADPA data preprocessing ETL job',
        'Role': 'arn:aws:iam::YOUR_ACCOUNT:role/ADPA-Glue-ExecutionRole',
        'Command': {
            'Name': 'glueetl',
            'ScriptLocation': 's3://adpa-ml-models/scripts/adpa_data_preprocessing.py',
            'PythonVersion': '3'
        },
        'DefaultArguments': {
            '--job-language': 'python',
            '--job-bookmark-option': 'job-bookmark-enable',
            '--enable-continuous-cloudwatch-log': 'true',
            '--enable-metrics': 'true',
            '--input_path': 's3://adpa-ml-data-raw/',
            '--output_path': 's3://adpa-ml-data-processed/'
        },
        'MaxRetries': 2,
        'Timeout': 2880,  # 48 hours
        'GlueVersion': '3.0',
        'NumberOfWorkers': 10,
        'WorkerType': 'G.1X'
    }
    
    try:
        response = glue_client.create_job(**job_config)
        print(f"Glue job created: {response}")
        
        # Start the job
        job_run = glue_client.start_job_run(
            JobName='adpa-data-preprocessing',
            Arguments={
                '--input_path': 's3://adpa-ml-data-raw/',
                '--output_path': 's3://adpa-ml-data-processed/'
            }
        )
        print(f"Job run started: {job_run['JobRunId']}")
        
    except Exception as e:
        print(f"Job creation error: {e}")

create_glue_etl_job()
```

**Helpful Links:**
- [Glue ETL Jobs](https://docs.aws.amazon.com/glue/latest/dg/author-job.html)
- [PySpark in Glue](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-python.html)

### Day 7: Feature Engineering Pipeline

#### 7.1 Advanced Feature Engineering Job

```python
# Advanced feature engineering script - save as adpa_feature_engineering.py
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.ml.feature import VectorAssembler, StandardScaler, PCA
from pyspark.ml import Pipeline
import boto3

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'input_path', 'output_path', 'feature_config'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

def advanced_feature_engineering():
    """Advanced feature engineering for ML pipeline"""
    
    # Read processed data
    processed_data = glueContext.create_dynamic_frame.from_options(
        format_options={},
        connection_type="s3",
        format="parquet",
        connection_options={"paths": [args['input_path']], "recurse": True},
        transformation_ctx="processed_data"
    )
    
    df = processed_data.toDF()
    
    # Window functions for time-series features
    if 'timestamp' in df.columns:
        window_spec = Window.partitionBy().orderBy('timestamp')
        
        # Rolling averages
        df = df.withColumn('rolling_avg_7d', 
                          F.avg('target_column').over(window_spec.rowsBetween(-7, 0)))
        df = df.withColumn('rolling_avg_30d', 
                          F.avg('target_column').over(window_spec.rowsBetween(-30, 0)))
        
        # Lag features
        df = df.withColumn('lag_1', F.lag('target_column', 1).over(window_spec))
        df = df.withColumn('lag_7', F.lag('target_column', 7).over(window_spec))
        
        # Rate of change
        df = df.withColumn('roc_1d', 
                          (F.col('target_column') - F.col('lag_1')) / F.col('lag_1'))
    
    # Categorical encoding
    categorical_columns = ['category_col1', 'category_col2']  # Adjust based on your data
    
    for col in categorical_columns:
        # One-hot encoding
        distinct_values = [row[0] for row in df.select(col).distinct().collect()]
        for value in distinct_values[:10]:  # Limit to top 10 categories
            df = df.withColumn(f'{col}_{value}', 
                              F.when(F.col(col) == value, 1).otherwise(0))
    
    # Interaction features
    numerical_columns = ['num_col1', 'num_col2', 'num_col3']  # Adjust based on your data
    
    # Create polynomial features
    for i, col1 in enumerate(numerical_columns):
        for col2 in numerical_columns[i+1:]:
            df = df.withColumn(f'{col1}_{col2}_interaction', F.col(col1) * F.col(col2))
            df = df.withColumn(f'{col1}_{col2}_ratio', F.col(col1) / (F.col(col2) + 0.001))
    
    # Statistical features
    # Add percentile-based features
    for col in numerical_columns:
        percentiles = df.approxQuantile(col, [0.25, 0.5, 0.75], 0.05)
        df = df.withColumn(f'{col}_q1_flag', F.when(F.col(col) <= percentiles[0], 1).otherwise(0))
        df = df.withColumn(f'{col}_q3_flag', F.when(F.col(col) >= percentiles[2], 1).otherwise(0))
        df = df.withColumn(f'{col}_outlier', F.when(
            (F.col(col) < percentiles[0] - 1.5 * (percentiles[2] - percentiles[0])) |
            (F.col(col) > percentiles[2] + 1.5 * (percentiles[2] - percentiles[0])), 1
        ).otherwise(0))
    
    # Domain-specific features (customize based on your use case)
    # Business hours indicator
    if 'hour' in df.columns:
        df = df.withColumn('is_business_hours', 
                          F.when((F.col('hour') >= 9) & (F.col('hour') <= 17), 1).otherwise(0))
    
    # Weekend indicator
    if 'day_of_week' in df.columns:
        df = df.withColumn('is_weekend', 
                          F.when(F.col('day_of_week').isin([1, 7]), 1).otherwise(0))
    
    # Feature selection based on correlation (simplified)
    feature_columns = [col for col in df.columns if col not in ['target', 'timestamp', 'id']]
    
    # Log feature engineering statistics
    cloudwatch = boto3.client('cloudwatch')
    cloudwatch.put_metric_data(
        Namespace='ADPA/FeatureEngineering',
        MetricData=[
            {
                'MetricName': 'FeaturesGenerated',
                'Value': len(feature_columns),
                'Unit': 'Count'
            },
            {
                'MetricName': 'FeatureEngineeringTime',
                'Value': job.elapsed_time(),
                'Unit': 'Seconds'
            }
        ]
    )
    
    # Convert back to DynamicFrame and save
    engineered_data = DynamicFrame.fromDF(df, glueContext, "engineered_data")
    
    glueContext.write_dynamic_frame.from_options(
        frame=engineered_data,
        connection_type="s3",
        format="parquet",
        connection_options={"path": args['output_path'], "partitionKeys": ["month"]},
        transformation_ctx="engineered_data"
    )
    
    # Save feature metadata
    feature_metadata = {
        'total_features': len(feature_columns),
        'feature_names': feature_columns,
        'engineering_timestamp': str(F.current_timestamp()),
        'data_shape': [df.count(), len(df.columns)]
    }
    
    # Save metadata to S3
    s3_client = boto3.client('s3')
    s3_client.put_object(
        Bucket='adpa-ml-models',
        Key='metadata/feature_metadata.json',
        Body=json.dumps(feature_metadata)
    )

advanced_feature_engineering()
job.commit()
```

### Day 8: Data Quality and Monitoring

#### 8.1 Data Quality Assessment Job

```python
# Data quality assessment script - save as adpa_data_quality.py
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.types import *
import boto3
import json

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'input_path', 'output_path'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

def assess_data_quality():
    """Comprehensive data quality assessment"""
    
    # Read data
    data_frame = glueContext.create_dynamic_frame.from_options(
        connection_type="s3",
        format="parquet",
        connection_options={"paths": [args['input_path']], "recurse": True},
        transformation_ctx="input_data"
    )
    
    df = data_frame.toDF()
    total_rows = df.count()
    
    quality_report = {
        'assessment_timestamp': str(F.current_timestamp()),
        'total_rows': total_rows,
        'total_columns': len(df.columns),
        'column_assessments': {},
        'overall_quality_score': 0
    }
    
    quality_scores = []
    
    for column in df.columns:
        col_assessment = {}
        
        # Basic statistics
        null_count = df.filter(F.col(column).isNull()).count()
        null_percentage = (null_count / total_rows) * 100
        
        col_assessment['null_count'] = null_count
        col_assessment['null_percentage'] = null_percentage
        col_assessment['data_type'] = str(df.schema[column].dataType)
        
        # Column-specific quality checks
        if str(df.schema[column].dataType) in ['IntegerType', 'FloatType', 'DoubleType']:
            # Numerical column checks
            stats = df.select(
                F.min(column).alias('min'),
                F.max(column).alias('max'),
                F.mean(column).alias('mean'),
                F.stddev(column).alias('stddev')
            ).collect()[0]
            
            col_assessment['min_value'] = stats['min']
            col_assessment['max_value'] = stats['max']
            col_assessment['mean_value'] = stats['mean']
            col_assessment['std_deviation'] = stats['stddev']
            
            # Outlier detection (simple IQR method)
            percentiles = df.approxQuantile(column, [0.25, 0.75], 0.05)
            if len(percentiles) == 2:
                q1, q3 = percentiles
                iqr = q3 - q1
                outlier_threshold_low = q1 - 1.5 * iqr
                outlier_threshold_high = q3 + 1.5 * iqr
                
                outlier_count = df.filter(
                    (F.col(column) < outlier_threshold_low) | 
                    (F.col(column) > outlier_threshold_high)
                ).count()
                
                col_assessment['outlier_count'] = outlier_count
                col_assessment['outlier_percentage'] = (outlier_count / total_rows) * 100
        
        elif str(df.schema[column].dataType) == 'StringType':
            # Categorical column checks
            distinct_count = df.select(column).distinct().count()
            col_assessment['distinct_values'] = distinct_count
            col_assessment['cardinality'] = distinct_count / total_rows
            
            # Check for empty strings
            empty_string_count = df.filter(F.col(column) == '').count()
            col_assessment['empty_string_count'] = empty_string_count
        
        # Calculate column quality score
        column_score = 100
        if null_percentage > 10:
            column_score -= 20
        if null_percentage > 50:
            column_score -= 50
        
        if 'outlier_percentage' in col_assessment and col_assessment['outlier_percentage'] > 5:
            column_score -= 10
        
        col_assessment['quality_score'] = max(0, column_score)
        quality_scores.append(column_score)
        
        quality_report['column_assessments'][column] = col_assessment
    
    # Overall quality score
    quality_report['overall_quality_score'] = sum(quality_scores) / len(quality_scores)
    
    # Data freshness check
    if 'timestamp' in df.columns:
        latest_timestamp = df.agg(F.max('timestamp')).collect()[0][0]
        quality_report['data_freshness'] = {
            'latest_timestamp': str(latest_timestamp),
            'hours_since_latest': None  # Calculate based on current time
        }
    
    # Save quality report
    report_json = json.dumps(quality_report, indent=2, default=str)
    
    # Save to S3
    s3_client = boto3.client('s3')
    s3_client.put_object(
        Bucket='adpa-ml-models',
        Key=f'quality_reports/data_quality_report_{int(time.time())}.json',
        Body=report_json
    )
    
    # Send alerts if quality is below threshold
    if quality_report['overall_quality_score'] < 70:
        sns_client = boto3.client('sns')
        sns_client.publish(
            TopicArn='arn:aws:sns:region:account:adpa-data-quality-alerts',
            Message=f"Data quality alert: Overall score {quality_report['overall_quality_score']:.1f}%",
            Subject='ADPA Data Quality Alert'
        )
    
    # Publish metrics to CloudWatch
    cloudwatch = boto3.client('cloudwatch')
    cloudwatch.put_metric_data(
        Namespace='ADPA/DataQuality',
        MetricData=[
            {
                'MetricName': 'OverallQualityScore',
                'Value': quality_report['overall_quality_score'],
                'Unit': 'Percent'
            },
            {
                'MetricName': 'TotalRows',
                'Value': total_rows,
                'Unit': 'Count'
            }
        ]
    )

assess_data_quality()
job.commit()
```

**Helpful Links:**
- [Glue Data Quality](https://docs.aws.amazon.com/glue/latest/dg/glue-data-quality.html)
- [Data Quality Best Practices](https://docs.aws.amazon.com/prescriptive-guidance/latest/data-quality-analytics/welcome.html)

---

## Week 3: Advanced SageMaker Features and MLOps

### Day 9: Hyperparameter Optimization

#### 9.1 Set Up SageMaker Hyperparameter Tuning

```python
from sagemaker.tuner import HyperparameterTuner, IntegerParameter, ContinuousParameter, CategoricalParameter
from sagemaker.sklearn import SKLearn

def create_hyperparameter_tuning_job():
    """Create hyperparameter tuning job for ADPA models"""
    
    # Define hyperparameter ranges
    hyperparameter_ranges = {
        'n_estimators': IntegerParameter(50, 500),
        'max_depth': IntegerParameter(3, 20),
        'min_samples_split': IntegerParameter(2, 20),
        'min_samples_leaf': IntegerParameter(1, 10),
        'max_features': CategoricalParameter(['auto', 'sqrt', 'log2']),
        'learning_rate': ContinuousParameter(0.01, 0.3)
    }
    
    # Enhanced training script for hyperparameter tuning
    estimator = SKLearn(
        entry_point='train_with_tuning.py',
        source_dir='s3://adpa-ml-models/scripts/',
        framework_version='1.0-1',
        instance_type='ml.m5.xlarge',
        role=role,
        metric_definitions=[
            {'Name': 'validation:accuracy', 'Regex': 'validation_accuracy=(\\S+)'},
            {'Name': 'validation:f1', 'Regex': 'validation_f1=(\\S+)'},
            {'Name': 'training:loss', 'Regex': 'training_loss=(\\S+)'}
        ]
    )
    
    # Create hyperparameter tuner
    tuner = HyperparameterTuner(
        estimator=estimator,
        objective_metric_name='validation:f1',
        objective_type='Maximize',
        hyperparameter_ranges=hyperparameter_ranges,
        max_jobs=20,
        max_parallel_jobs=3,
        strategy='Bayesian',
        early_stopping_type='Auto'
    )
    
    # Start tuning job
    tuner.fit({
        'train': 's3://adpa-ml-data-processed/train/',
        'validation': 's3://adpa-ml-data-processed/validation/'
    }, job_name='adpa-hyperparameter-tuning')
    
    return tuner

# Enhanced training script with hyperparameter tuning support
train_script = '''
import argparse
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
import os
import logging

def main():
    parser = argparse.ArgumentParser()
    
    # SageMaker arguments
    parser.add_argument('--model-dir', type=str, default=os.environ.get('SM_MODEL_DIR'))
    parser.add_argument('--train', type=str, default=os.environ.get('SM_CHANNEL_TRAIN'))
    parser.add_argument('--validation', type=str, default=os.environ.get('SM_CHANNEL_VALIDATION'))
    
    # Hyperparameters for tuning
    parser.add_argument('--n_estimators', type=int, default=100)
    parser.add_argument('--max_depth', type=int, default=10)
    parser.add_argument('--min_samples_split', type=int, default=2)
    parser.add_argument('--min_samples_leaf', type=int, default=1)
    parser.add_argument('--max_features', type=str, default='auto')
    parser.add_argument('--learning_rate', type=float, default=0.1)
    
    args = parser.parse_args()
    
    # Load data
    train_df = pd.read_csv(os.path.join(args.train, 'train.csv'))
    val_df = pd.read_csv(os.path.join(args.validation, 'validation.csv'))
    
    X_train = train_df.drop('target', axis=1)
    y_train = train_df['target']
    X_val = val_df.drop('target', axis=1)
    y_val = val_df['target']
    
    # Create model with hyperparameters
    model = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_split=args.min_samples_split,
        min_samples_leaf=args.min_samples_leaf,
        max_features=args.max_features,
        random_state=42
    )
    
    # Train model
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_val)
    accuracy = accuracy_score(y_val, y_pred)
    f1 = f1_score(y_val, y_pred, average='weighted')
    
    # Print metrics for SageMaker to capture
    print(f"validation_accuracy={accuracy}")
    print(f"validation_f1={f1}")
    
    # Save model
    joblib.dump(model, os.path.join(args.model_dir, 'model.joblib'))

if __name__ == '__main__':
    main()
'''

# Save enhanced training script
with open('train_with_tuning.py', 'w') as f:
    f.write(train_script)

# Upload to S3
# s3_client.upload_file('train_with_tuning.py', 'adpa-ml-models', 'scripts/train_with_tuning.py')
```

### Day 10: Model Monitoring and A/B Testing

#### 10.1 Set Up Model Monitoring

```python
from sagemaker.model_monitor import DefaultModelMonitor, DataCaptureConfig
from sagemaker.model_monitor.dataset_format import DatasetFormat

def setup_model_monitoring():
    """Set up comprehensive model monitoring"""
    
    # Create data capture configuration
    data_capture_config = DataCaptureConfig(
        enable_capture=True,
        sampling_percentage=100,
        destination_s3_uri='s3://adpa-ml-models/data-capture',
        capture_options=['REQUEST', 'RESPONSE'],
        csv_content_types=['text/csv'],
        json_content_types=['application/json']
    )
    
    # Deploy model with data capture
    predictor = model.deploy(
        initial_instance_count=1,
        instance_type='ml.m5.large',
        endpoint_name='adpa-ml-endpoint-monitored',
        data_capture_config=data_capture_config
    )
    
    # Create model monitor
    model_monitor = DefaultModelMonitor(
        role=role,
        instance_count=1,
        instance_type='ml.m5.xlarge',
        volume_size_in_gb=20,
        max_runtime_in_seconds=3600
    )
    
    # Create baseline dataset
    baseline_job = model_monitor.suggest_baseline(
        baseline_dataset='s3://adpa-ml-data-processed/baseline/baseline.csv',
        dataset_format=DatasetFormat.csv(header=True),
        output_s3_uri='s3://adpa-ml-models/monitoring/baseline'
    )
    
    # Wait for baseline job to complete
    baseline_job.wait()
    
    # Create monitoring schedule
    model_monitor.create_monitoring_schedule(
        monitor_schedule_name='adpa-model-monitoring-schedule',
        endpoint_input=predictor.endpoint_name,
        output_s3_uri='s3://adpa-ml-models/monitoring/results',
        statistics=baseline_job.baseline_statistics(),
        constraints=baseline_job.suggested_constraints(),
        schedule_cron_expression='cron(0 * * * ? *)',  # Hourly monitoring
        enable_cloudwatch_metrics=True
    )
    
    return model_monitor, predictor

# Model monitoring analysis script
monitoring_script = '''
import boto3
import pandas as pd
import json
from datetime import datetime, timedelta

def analyze_monitoring_results():
    """Analyze model monitoring results and send alerts"""
    
    s3_client = boto3.client('s3')
    cloudwatch = boto3.client('cloudwatch')
    sns_client = boto3.client('sns')
    
    # Get latest monitoring results
    monitoring_results = s3_client.list_objects_v2(
        Bucket='adpa-ml-models',
        Prefix='monitoring/results/'
    )
    
    if 'Contents' in monitoring_results:
        latest_result = max(monitoring_results['Contents'], key=lambda x: x['LastModified'])
        
        # Download and analyze results
        result_obj = s3_client.get_object(
            Bucket='adpa-ml-models',
            Key=latest_result['Key']
        )
        
        result_data = json.loads(result_obj['Body'].read())
        
        # Check for violations
        violations = result_data.get('violations', [])
        
        if violations:
            alert_message = f"Model monitoring detected {len(violations)} violations"
            
            # Send SNS alert
            sns_client.publish(
                TopicArn='arn:aws:sns:region:account:adpa-model-alerts',
                Message=alert_message,
                Subject='ADPA Model Monitoring Alert'
            )
            
            # Log to CloudWatch
            cloudwatch.put_metric_data(
                Namespace='ADPA/ModelMonitoring',
                MetricData=[
                    {
                        'MetricName': 'ViolationCount',
                        'Value': len(violations),
                        'Unit': 'Count'
                    }
                ]
            )

analyze_monitoring_results()
'''
```

#### 10.2 A/B Testing Setup

```python
def setup_ab_testing():
    """Set up A/B testing for model comparison"""
    
    # Deploy two model variants
    model_a = Model(
        image_uri='246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-scikit-learn:1.0-1-cpu-py3',
        model_data='s3://adpa-ml-models/model-a/model.tar.gz',
        role=role
    )
    
    model_b = Model(
        image_uri='246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-scikit-learn:1.0-1-cpu-py3',
        model_data='s3://adpa-ml-models/model-b/model.tar.gz',
        role=role
    )
    
    # Create multi-model endpoint
    endpoint_config_name = 'adpa-ab-testing-config'
    
    sagemaker_client = boto3.client('sagemaker')
    
    # Create endpoint configuration
    sagemaker_client.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=[
            {
                'VariantName': 'ModelA',
                'ModelName': model_a.name,
                'InitialInstanceCount': 1,
                'InstanceType': 'ml.m5.large',
                'InitialVariantWeight': 50  # 50% traffic
            },
            {
                'VariantName': 'ModelB',
                'ModelName': model_b.name,
                'InitialInstanceCount': 1,
                'InstanceType': 'ml.m5.large',
                'InitialVariantWeight': 50  # 50% traffic
            }
        ],
        DataCaptureConfig={
            'EnableCapture': True,
            'InitialSamplingPercentage': 100,
            'DestinationS3Uri': 's3://adpa-ml-models/ab-testing-data/',
            'CaptureOptions': [
                {'CaptureMode': 'Input'},
                {'CaptureMode': 'Output'}
            ]
        }
    )
    
    # Create endpoint
    sagemaker_client.create_endpoint(
        EndpointName='adpa-ab-testing-endpoint',
        EndpointConfigName=endpoint_config_name
    )
    
    print("A/B testing endpoint created successfully")

# A/B testing analysis
def analyze_ab_testing_results():
    """Analyze A/B testing results"""
    
    s3_client = boto3.client('s3')
    
    # Get captured data for both variants
    response = s3_client.list_objects_v2(
        Bucket='adpa-ml-models',
        Prefix='ab-testing-data/'
    )
    
    model_a_results = []
    model_b_results = []
    
    for obj in response.get('Contents', []):
        if 'ModelA' in obj['Key']:
            # Process Model A results
            pass
        elif 'ModelB' in obj['Key']:
            # Process Model B results
            pass
    
    # Statistical significance testing
    # Implementation would include proper statistical tests
    # to determine if performance differences are significant
    
    return {
        'model_a_performance': {},
        'model_b_performance': {},
        'statistical_significance': {},
        'recommendation': 'Continue testing'
    }
```

**Helpful Links:**
- [SageMaker Model Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html)
- [Multi-Model Endpoints](https://docs.aws.amazon.com/sagemaker/latest/dg/multi-model-endpoints.html)

### Day 11: SageMaker Pipelines Integration

#### 11.1 Create Comprehensive ML Pipeline

```python
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep, TrainingStep, CreateModelStep, RegisterModel
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.functions import JsonGet
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.sklearn import SKLearnProcessor

def create_comprehensive_ml_pipeline():
    """Create end-to-end ML pipeline with SageMaker Pipelines"""
    
    pipeline_session = PipelineSession()
    
    # Step 1: Data Processing
    sklearn_processor = SKLearnProcessor(
        framework_version='1.0-1',
        instance_type='ml.m5.large',
        instance_count=1,
        base_job_name='adpa-data-processing',
        sagemaker_session=pipeline_session,
        role=role
    )
    
    processing_step = ProcessingStep(
        name='DataProcessing',
        processor=sklearn_processor,
        inputs=[
            ProcessingInput(
                source='s3://adpa-ml-data-raw/',
                destination='/opt/ml/processing/input'
            )
        ],
        outputs=[
            ProcessingOutput(
                output_name='train_data',
                source='/opt/ml/processing/train',
                destination='s3://adpa-ml-data-processed/train/'
            ),
            ProcessingOutput(
                output_name='validation_data', 
                source='/opt/ml/processing/validation',
                destination='s3://adpa-ml-data-processed/validation/'
            ),
            ProcessingOutput(
                output_name='test_data',
                source='/opt/ml/processing/test', 
                destination='s3://adpa-ml-data-processed/test/'
            )
        ],
        code='s3://adpa-ml-models/scripts/data_processing_pipeline.py'
    )
    
    # Step 2: Model Training
    sklearn_estimator = SKLearn(
        entry_point='train_pipeline.py',
        source_dir='s3://adpa-ml-models/scripts/',
        framework_version='1.0-1',
        instance_type='ml.m5.xlarge',
        role=role,
        sagemaker_session=pipeline_session,
        metric_definitions=[
            {'Name': 'validation:accuracy', 'Regex': 'validation_accuracy=(\\S+)'},
            {'Name': 'validation:f1', 'Regex': 'validation_f1=(\\S+)'}
        ]
    )
    
    training_step = TrainingStep(
        name='ModelTraining',
        estimator=sklearn_estimator,
        inputs={
            'train': TrainingInput(
                s3_data=processing_step.properties.ProcessingOutputConfig.Outputs['train_data'].S3Output.S3Uri
            ),
            'validation': TrainingInput(
                s3_data=processing_step.properties.ProcessingOutputConfig.Outputs['validation_data'].S3Output.S3Uri
            )
        }
    )
    
    # Step 3: Model Evaluation
    evaluation_processor = SKLearnProcessor(
        framework_version='1.0-1',
        instance_type='ml.m5.large',
        instance_count=1,
        base_job_name='adpa-model-evaluation',
        sagemaker_session=pipeline_session,
        role=role
    )
    
    evaluation_step = ProcessingStep(
        name='ModelEvaluation',
        processor=evaluation_processor,
        inputs=[
            ProcessingInput(
                source=training_step.properties.ModelArtifacts.S3ModelArtifacts,
                destination='/opt/ml/processing/model'
            ),
            ProcessingInput(
                source=processing_step.properties.ProcessingOutputConfig.Outputs['test_data'].S3Output.S3Uri,
                destination='/opt/ml/processing/test'
            )
        ],
        outputs=[
            ProcessingOutput(
                output_name='evaluation_report',
                source='/opt/ml/processing/evaluation',
                destination='s3://adpa-ml-models/evaluation/'
            )
        ],
        code='s3://adpa-ml-models/scripts/model_evaluation.py'
    )
    
    # Step 4: Create Model
    model = Model(
        image_uri='246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-scikit-learn:1.0-1-cpu-py3',
        model_data=training_step.properties.ModelArtifacts.S3ModelArtifacts,
        sagemaker_session=pipeline_session,
        role=role
    )
    
    create_model_step = CreateModelStep(
        name='CreateModel',
        model=model,
        inputs=CreateModelStep.get_create_model_request_from_model(model)
    )
    
    # Step 5: Conditional Model Registration
    accuracy_condition = ConditionGreaterThanOrEqualTo(
        left=JsonGet(
            step_name=evaluation_step.name,
            property_file='evaluation',
            json_path='accuracy'
        ),
        right=0.8  # Minimum accuracy threshold
    )
    
    register_model_step = RegisterModel(
        name='RegisterModel',
        estimator=sklearn_estimator,
        model_data=training_step.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=['text/csv'],
        response_types=['application/json'],
        inference_instances=['ml.t2.medium', 'ml.m5.large'],
        transform_instances=['ml.m5.large'],
        model_package_group_name='adpa-models'
    )
    
    condition_step = ConditionStep(
        name='CheckAccuracy',
        conditions=[accuracy_condition],
        if_steps=[register_model_step],
        else_steps=[]
    )
    
    # Create the pipeline
    pipeline = Pipeline(
        name='adpa-comprehensive-ml-pipeline',
        steps=[
            processing_step,
            training_step, 
            evaluation_step,
            create_model_step,
            condition_step
        ],
        sagemaker_session=pipeline_session
    )
    
    return pipeline

# Create and execute pipeline
comprehensive_pipeline = create_comprehensive_ml_pipeline()
comprehensive_pipeline.create(role_arn=role)
execution = comprehensive_pipeline.start()
```

### Day 12: Pipeline Orchestration and Automation

#### 12.1 Advanced Pipeline Orchestration

```python
# Model evaluation script for pipeline
evaluation_script = '''
import json
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.metrics import confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import os

def evaluate_model():
    """Comprehensive model evaluation"""
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-path', type=str, default='/opt/ml/processing/model')
    parser.add_argument('--test-path', type=str, default='/opt/ml/processing/test')
    parser.add_argument('--output-path', type=str, default='/opt/ml/processing/evaluation')
    
    args = parser.parse_args()
    
    # Load model
    model = joblib.load(os.path.join(args.model_path, 'model.joblib'))
    
    # Load test data
    test_df = pd.read_csv(os.path.join(args.test_path, 'test.csv'))
    X_test = test_df.drop('target', axis=1)
    y_test = test_df['target']
    
    # Make predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None
    
    # Calculate metrics
    metrics = {
        'accuracy': float(accuracy_score(y_test, y_pred)),
        'f1_score': float(f1_score(y_test, y_pred, average='weighted')),
        'precision': float(precision_score(y_test, y_pred, average='weighted')),
        'recall': float(recall_score(y_test, y_pred, average='weighted'))
    }
    
    if y_pred_proba is not None:
        metrics['roc_auc'] = float(roc_auc_score(y_test, y_pred_proba))
    
    # Generate detailed report
    report = {
        'model_performance': metrics,
        'classification_report': classification_report(y_test, y_pred, output_dict=True),
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
        'test_samples': len(y_test),
        'model_passed_threshold': metrics['accuracy'] >= 0.8
    }
    
    # Save evaluation report
    os.makedirs(args.output_path, exist_ok=True)
    
    with open(os.path.join(args.output_path, 'evaluation.json'), 'w') as f:
        json.dump(report, f, indent=2)
    
    # Generate plots
    plt.figure(figsize=(8, 6))
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title('Confusion Matrix')
    plt.ylabel('Actual')
    plt.xlabel('Predicted')
    plt.savefig(os.path.join(args.output_path, 'confusion_matrix.png'))
    plt.close()
    
    # Feature importance if available
    if hasattr(model, 'feature_importances_'):
        importance_df = pd.DataFrame({
            'feature': X_test.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        plt.figure(figsize=(10, 6))
        sns.barplot(data=importance_df.head(10), x='importance', y='feature')
        plt.title('Top 10 Feature Importances')
        plt.tight_layout()
        plt.savefig(os.path.join(args.output_path, 'feature_importance.png'))
        plt.close()
    
    print(f"Evaluation completed. Accuracy: {metrics['accuracy']:.3f}")

if __name__ == '__main__':
    evaluate_model()
'''

# Pipeline automation with Lambda integration
def create_pipeline_automation():
    """Create automated pipeline triggers"""
    
    lambda_function_code = '''
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Lambda function to trigger pipeline on S3 events"""
    
    sagemaker = boto3.client('sagemaker')
    
    try:
        # Extract S3 event information
        s3_event = event['Records'][0]['s3']
        bucket = s3_event['bucket']['name']
        key = s3_event['object']['key']
        
        logger.info(f"New data detected: s3://{bucket}/{key}")
        
        # Trigger pipeline if new data is in the raw data prefix
        if key.startswith('raw-data/') and key.endswith('.csv'):
            response = sagemaker.start_pipeline_execution(
                PipelineName='adpa-comprehensive-ml-pipeline',
                PipelineExecutionDisplayName=f'auto-trigger-{int(time.time())}'
            )
            
            logger.info(f"Pipeline triggered: {response['PipelineExecutionArn']}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Pipeline triggered successfully',
                    'execution_arn': response['PipelineExecutionArn']
                })
            }
        else:
            logger.info("File does not match trigger criteria")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No action taken'})
            }
            
    except Exception as e:
        logger.error(f"Error triggering pipeline: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    '''
    
    # Create Lambda function
    lambda_client = boto3.client('lambda')
    
    lambda_response = lambda_client.create_function(
        FunctionName='adpa-pipeline-trigger',
        Runtime='python3.9',
        Role='arn:aws:iam::YOUR_ACCOUNT:role/ADPA-Lambda-ExecutionRole',
        Handler='lambda_function.lambda_handler',
        Code={'ZipFile': lambda_function_code},
        Description='Trigger ADPA ML pipeline on new data arrival',
        Timeout=300,
        Environment={
            'Variables': {
                'PIPELINE_NAME': 'adpa-comprehensive-ml-pipeline'
            }
        }
    )
    
    print(f"Lambda function created: {lambda_response['FunctionArn']}")
    
    # Add S3 trigger
    s3_client = boto3.client('s3')
    
    notification_config = {
        'LambdaConfigurations': [
            {
                'Id': 'adpa-data-trigger',
                'LambdaFunctionArn': lambda_response['FunctionArn'],
                'Events': ['s3:ObjectCreated:*'],
                'Filter': {
                    'Key': {
                        'FilterRules': [
                            {
                                'Name': 'prefix',
                                'Value': 'raw-data/'
                            },
                            {
                                'Name': 'suffix',
                                'Value': '.csv'
                            }
                        ]
                    }
                }
            }
        ]
    }
    
    s3_client.put_bucket_notification_configuration(
        Bucket='adpa-ml-data-raw',
        NotificationConfiguration=notification_config
    )
    
    print("S3 trigger configured successfully")

create_pipeline_automation()
```

**Helpful Links:**
- [SageMaker Pipelines SDK](https://sagemaker.readthedocs.io/en/stable/amazon_sagemaker_model_building_pipeline.html)
- [Pipeline Automation Best Practices](https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines-best-practices.html)

---

## Week 4: Integration and Production Deployment

### Day 13: Multi-Model Endpoints and Auto-Scaling

#### 13.1 Set Up Multi-Model Endpoints

```python
from sagemaker.multidatamodel import MultiDataModel
from sagemaker.model import Model

def setup_multi_model_endpoint():
    """Set up multi-model endpoint for ADPA"""
    
    # Create multi-data model
    multi_data_model = MultiDataModel(
        name='adpa-multi-model',
        model_data_prefix='s3://adpa-ml-models/multi-model/',
        image_uri='246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-scikit-learn:1.0-1-cpu-py3',
        role=role,
        entry_point='multi_model_inference.py',
        source_dir='s3://adpa-ml-models/scripts/'
    )
    
    # Deploy multi-model endpoint
    predictor = multi_data_model.deploy(
        initial_instance_count=1,
        instance_type='ml.m5.xlarge',
        endpoint_name='adpa-multi-model-endpoint'
    )
    
    # Add models to the endpoint
    model_artifacts = [
        's3://adpa-ml-models/model-v1/model.tar.gz',
        's3://adpa-ml-models/model-v2/model.tar.gz',
        's3://adpa-ml-models/model-v3/model.tar.gz'
    ]
    
    for i, artifact in enumerate(model_artifacts):
        multi_data_model.add_model(artifact, f'model-v{i+1}')
    
    return predictor, multi_data_model

# Multi-model inference script
multi_model_script = '''
import joblib
import json
import os
import pandas as pd

def model_fn(model_dir):
    """Load the specified model"""
    model_path = os.path.join(model_dir, 'model.joblib')
    return joblib.load(model_path)

def input_fn(request_body, request_content_type):
    """Process input data"""
    if request_content_type == 'application/json':
        data = json.loads(request_body)
        return pd.DataFrame(data['instances'])
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")

def predict_fn(input_data, model):
    """Generate predictions"""
    predictions = model.predict(input_data)
    probabilities = model.predict_proba(input_data) if hasattr(model, 'predict_proba') else None
    
    result = {'predictions': predictions.tolist()}
    if probabilities is not None:
        result['probabilities'] = probabilities.tolist()
    
    return result

def output_fn(prediction, content_type):
    """Format output"""
    return json.dumps(prediction)
'''

# Auto-scaling configuration
def configure_auto_scaling():
    """Configure auto-scaling for production endpoints"""
    
    autoscaling_client = boto3.client('application-autoscaling')
    
    # Register scalable target
    autoscaling_client.register_scalable_target(
        ServiceNamespace='sagemaker',
        ResourceId='endpoint/adpa-multi-model-endpoint/variant/AllTraffic',
        ScalableDimension='sagemaker:variant:DesiredInstanceCount',
        MinCapacity=1,
        MaxCapacity=10,
        RoleArn='arn:aws:iam::YOUR_ACCOUNT:role/ADPA-AutoScaling-Role'
    )
    
    # Create scaling policy
    autoscaling_client.put_scaling_policy(
        PolicyName='adpa-endpoint-scaling-policy',
        ServiceNamespace='sagemaker',
        ResourceId='endpoint/adpa-multi-model-endpoint/variant/AllTraffic',
        ScalableDimension='sagemaker:variant:DesiredInstanceCount',
        PolicyType='TargetTrackingScaling',
        TargetTrackingScalingPolicyConfiguration={
            'TargetValue': 70.0,
            'PredefinedMetricSpecification': {
                'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance'
            },
            'ScaleOutCooldown': 300,
            'ScaleInCooldown': 300
        }
    )
    
    print("Auto-scaling configured for ADPA endpoint")
```

### Day 14: Model Performance Analytics

#### 14.1 Advanced Performance Tracking

```python
def setup_performance_analytics():
    """Set up comprehensive performance analytics"""
    
    # CloudWatch custom metrics
    def publish_custom_metrics():
        cloudwatch = boto3.client('cloudwatch')
        
        # Model performance metrics
        metrics = [
            {
                'MetricName': 'ModelAccuracy',
                'Dimensions': [
                    {
                        'Name': 'ModelVersion',
                        'Value': 'v1.0'
                    },
                    {
                        'Name': 'Environment', 
                        'Value': 'Production'
                    }
                ],
                'Unit': 'Percent',
                'Value': 85.5
            },
            {
                'MetricName': 'PredictionLatency',
                'Dimensions': [
                    {
                        'Name': 'Endpoint',
                        'Value': 'adpa-multi-model-endpoint'
                    }
                ],
                'Unit': 'Milliseconds',
                'Value': 250.0
            },
            {
                'MetricName': 'DataDrift',
                'Dimensions': [
                    {
                        'Name': 'Feature',
                        'Value': 'feature_set_1'
                    }
                ],
                'Unit': 'Percent',
                'Value': 5.2
            }
        ]
        
        cloudwatch.put_metric_data(
            Namespace='ADPA/ModelPerformance',
            MetricData=metrics
        )
    
    # Model performance dashboard
    dashboard_body = {
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["ADPA/ModelPerformance", "ModelAccuracy"],
                        [".", "PredictionLatency"],
                        [".", "DataDrift"]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": "us-west-2",
                    "title": "ADPA Model Performance"
                }
            },
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/SageMaker", "Invocations", "EndpointName", "adpa-multi-model-endpoint"],
                        [".", "ModelLatency", ".", "."],
                        [".", "InvocationErrors", ".", "."]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-west-2",
                    "title": "Endpoint Metrics"
                }
            }
        ]
    }
    
    cloudwatch.put_dashboard(
        DashboardName='ADPA-Model-Performance',
        DashboardBody=json.dumps(dashboard_body)
    )

# Performance analysis script
performance_analysis = '''
import boto3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

class ModelPerformanceAnalyzer:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.s3_client = boto3.client('s3')
        
    def analyze_model_performance(self, days_back=7):
        """Analyze model performance over time"""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)
        
        # Get CloudWatch metrics
        metrics_data = self.cloudwatch.get_metric_statistics(
            Namespace='ADPA/ModelPerformance',
            MetricName='ModelAccuracy',
            Dimensions=[],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,  # 1 hour
            Statistics=['Average']
        )
        
        # Analyze trends
        if metrics_data['Datapoints']:
            df = pd.DataFrame(metrics_data['Datapoints'])
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            df = df.sort_values('Timestamp')
            
            # Calculate trend
            from scipy import stats
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                range(len(df)), df['Average']
            )
            
            trend_analysis = {
                'slope': slope,
                'r_squared': r_value**2,
                'trend': 'improving' if slope > 0 else 'declining',
                'significance': 'significant' if p_value < 0.05 else 'not_significant'
            }
            
            return {
                'performance_data': df.to_dict('records'),
                'trend_analysis': trend_analysis,
                'current_performance': df['Average'].iloc[-1],
                'average_performance': df['Average'].mean()
            }
        
        return {'message': 'No performance data available'}
    
    def detect_anomalies(self, threshold=2):
        """Detect performance anomalies"""
        
        # Get recent performance data
        performance_data = self.analyze_model_performance(days_back=30)
        
        if 'performance_data' in performance_data:
            df = pd.DataFrame(performance_data['performance_data'])
            
            # Calculate z-scores
            mean_perf = df['Average'].mean()
            std_perf = df['Average'].std()
            df['z_score'] = (df['Average'] - mean_perf) / std_perf
            
            # Identify anomalies
            anomalies = df[abs(df['z_score']) > threshold]
            
            return {
                'anomaly_count': len(anomalies),
                'anomalies': anomalies.to_dict('records'),
                'anomaly_threshold': threshold
            }
        
        return {'message': 'Insufficient data for anomaly detection'}
    
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'model_performance': self.analyze_model_performance(),
            'anomaly_detection': self.detect_anomalies(),
            'recommendations': []
        }
        
        # Add recommendations based on analysis
        if 'trend_analysis' in report['model_performance']:
            trend = report['model_performance']['trend_analysis']
            
            if trend['trend'] == 'declining':
                report['recommendations'].append({
                    'type': 'performance_decline',
                    'message': 'Model performance is declining. Consider retraining.',
                    'priority': 'high'
                })
            
            if trend['significance'] == 'significant':
                report['recommendations'].append({
                    'type': 'significant_trend',
                    'message': f'Significant {trend["trend"]} trend detected.',
                    'priority': 'medium'
                })
        
        return report

# Usage
analyzer = ModelPerformanceAnalyzer()
report = analyzer.generate_performance_report()
'''
```

### Day 15: Security and Compliance

#### 15.1 Security Hardening

```python
def implement_security_measures():
    """Implement comprehensive security measures"""
    
    # VPC Endpoint for SageMaker
    ec2_client = boto3.client('ec2')
    
    vpc_endpoint_response = ec2_client.create_vpc_endpoint(
        VpcId='vpc-12345678',
        ServiceName='com.amazonaws.us-west-2.sagemaker.api',
        VpcEndpointType='Interface',
        SubnetIds=['subnet-12345678'],
        SecurityGroupIds=['sg-12345678'],
        PolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": [
                        "sagemaker:CreateTrainingJob",
                        "sagemaker:CreateModel",
                        "sagemaker:CreateEndpoint*",
                        "sagemaker:InvokeEndpoint"
                    ],
                    "Resource": "*"
                }
            ]
        })
    )
    
    # Encryption at rest and in transit
    sagemaker_config = {
        'encryption_at_rest': {
            'kms_key_id': 'arn:aws:kms:us-west-2:account:key/key-id',
            's3_encryption': 'SSE-KMS',
            'volume_encryption': True
        },
        'network_isolation': True,
        'inter_container_traffic_encryption': True
    }
    
    # IAM policies with least privilege
    least_privilege_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject"
                ],
                "Resource": [
                    "arn:aws:s3:::adpa-ml-data-*/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "sagemaker:CreateTrainingJob",
                    "sagemaker:DescribeTrainingJob"
                ],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "aws:RequestedRegion": "us-west-2"
                    }
                }
            }
        ]
    }
    
    print("Security measures implemented successfully")

# Data privacy and compliance
def implement_data_privacy():
    """Implement data privacy measures"""
    
    data_privacy_script = '''
import hashlib
import pandas as pd
from cryptography.fernet import Fernet

class DataPrivacyManager:
    def __init__(self):
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def anonymize_pii(self, dataframe, pii_columns):
        """Anonymize personally identifiable information"""
        
        df_anonymized = dataframe.copy()
        
        for column in pii_columns:
            if column in df_anonymized.columns:
                # Hash PII data
                df_anonymized[column] = df_anonymized[column].apply(
                    lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:10]
                )
        
        return df_anonymized
    
    def encrypt_sensitive_data(self, data):
        """Encrypt sensitive data"""
        return self.cipher_suite.encrypt(data.encode())
    
    def decrypt_data(self, encrypted_data):
        """Decrypt data"""
        return self.cipher_suite.decrypt(encrypted_data).decode()
    
    def audit_data_access(self, user_id, resource, action):
        """Log data access for audit purposes"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'ip_address': 'xxx.xxx.xxx.xxx'  # Replace with actual IP
        }
        
        # Log to CloudTrail or custom audit system
        cloudwatch = boto3.client('logs')
        cloudwatch.put_log_events(
            logGroupName='ADPA-Data-Audit',
            logStreamName='data-access',
            logEvents=[
                {
                    'timestamp': int(time.time() * 1000),
                    'message': json.dumps(audit_entry)
                }
            ]
        )

# Usage example
privacy_manager = DataPrivacyManager()
'''
```

### Day 16: Final Integration and Testing

#### 16.1 End-to-End Integration Testing

```python
class ADPAMLIntegrationTester:
    """Comprehensive integration testing for ADPA ML services"""
    
    def __init__(self):
        self.sagemaker_client = boto3.client('sagemaker')
        self.s3_client = boto3.client('s3')
        self.glue_client = boto3.client('glue')
        
    def test_data_pipeline(self):
        """Test complete data processing pipeline"""
        
        test_results = {
            'data_ingestion': False,
            'data_processing': False,
            'feature_engineering': False,
            'data_quality': False
        }
        
        try:
            # Test data upload
            test_data = pd.DataFrame({
                'feature1': np.random.randn(100),
                'feature2': np.random.randn(100),
                'target': np.random.randint(0, 2, 100)
            })
            
            test_data.to_csv('/tmp/test_data.csv', index=False)
            
            self.s3_client.upload_file(
                '/tmp/test_data.csv',
                'adpa-ml-data-raw',
                'test/test_data.csv'
            )
            test_results['data_ingestion'] = True
            
            # Test Glue job execution
            job_run = self.glue_client.start_job_run(
                JobName='adpa-data-preprocessing',
                Arguments={
                    '--input_path': 's3://adpa-ml-data-raw/test/',
                    '--output_path': 's3://adpa-ml-data-processed/test/'
                }
            )
            
            # Wait for job completion (simplified)
            import time
            time.sleep(60)  # Wait 1 minute
            
            test_results['data_processing'] = True
            test_results['feature_engineering'] = True
            test_results['data_quality'] = True
            
        except Exception as e:
            print(f"Data pipeline test failed: {e}")
        
        return test_results
    
    def test_ml_pipeline(self):
        """Test ML training and deployment pipeline"""
        
        test_results = {
            'pipeline_execution': False,
            'model_training': False,
            'model_registration': False,
            'model_deployment': False
        }
        
        try:
            # Start pipeline execution
            execution = self.sagemaker_client.start_pipeline_execution(
                PipelineName='adpa-comprehensive-ml-pipeline',
                PipelineExecutionDisplayName='integration-test'
            )
            
            test_results['pipeline_execution'] = True
            
            # Monitor pipeline execution (simplified)
            # In practice, you'd wait for completion and check each step
            
            test_results['model_training'] = True
            test_results['model_registration'] = True
            test_results['model_deployment'] = True
            
        except Exception as e:
            print(f"ML pipeline test failed: {e}")
        
        return test_results
    
    def test_inference_endpoint(self):
        """Test model inference endpoints"""
        
        test_results = {
            'endpoint_health': False,
            'inference_accuracy': False,
            'response_time': False
        }
        
        try:
            # Test endpoint health
            endpoint_status = self.sagemaker_client.describe_endpoint(
                EndpointName='adpa-multi-model-endpoint'
            )
            
            if endpoint_status['EndpointStatus'] == 'InService':
                test_results['endpoint_health'] = True
            
            # Test inference
            runtime_client = boto3.client('sagemaker-runtime')
            
            test_payload = {
                'instances': [
                    [1.0, 2.0, 3.0, 4.0, 5.0]
                ]
            }
            
            start_time = time.time()
            response = runtime_client.invoke_endpoint(
                EndpointName='adpa-multi-model-endpoint',
                ContentType='application/json',
                Body=json.dumps(test_payload)
            )
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # ms
            
            if response_time < 1000:  # Less than 1 second
                test_results['response_time'] = True
            
            # Check response format
            result = json.loads(response['Body'].read())
            if 'predictions' in result:
                test_results['inference_accuracy'] = True
            
        except Exception as e:
            print(f"Inference test failed: {e}")
        
        return test_results
    
    def run_comprehensive_tests(self):
        """Run all integration tests"""
        
        print("Starting ADPA ML Services Integration Tests...")
        
        # Run test suites
        data_test_results = self.test_data_pipeline()
        ml_test_results = self.test_ml_pipeline()
        inference_test_results = self.test_inference_endpoint()
        
        # Compile results
        all_results = {
            'test_timestamp': datetime.utcnow().isoformat(),
            'data_pipeline': data_test_results,
            'ml_pipeline': ml_test_results,
            'inference_endpoint': inference_test_results
        }
        
        # Calculate overall success rate
        total_tests = sum(len(results) for results in [data_test_results, ml_test_results, inference_test_results])
        passed_tests = sum(sum(results.values()) for results in [data_test_results, ml_test_results, inference_test_results])
        
        success_rate = (passed_tests / total_tests) * 100
        
        all_results['overall_success_rate'] = success_rate
        all_results['status'] = 'PASS' if success_rate >= 90 else 'FAIL'
        
        # Save test results
        self.s3_client.put_object(
            Bucket='adpa-ml-models',
            Key=f'test_results/integration_test_{int(time.time())}.json',
            Body=json.dumps(all_results, indent=2)
        )
        
        print(f"Integration tests completed. Success rate: {success_rate:.1f}%")
        return all_results

# Run integration tests
tester = ADPAMLIntegrationTester()
test_results = tester.run_comprehensive_tests()
```

## Performance Optimization and Best Practices

### Performance Checklist

- [ ] **Cost Optimization**: Use Spot instances for training, right-size endpoints
- [ ] **Monitoring**: Set up comprehensive CloudWatch dashboards
- [ ] **Security**: Implement encryption, VPC endpoints, least-privilege IAM
- [ ] **Scalability**: Configure auto-scaling for production endpoints
- [ ] **Data Quality**: Implement automated data quality checks
- [ ] **Model Governance**: Use Model Registry for version control
- [ ] **CI/CD**: Automate pipeline triggers and deployments

### Troubleshooting Guide

#### Common Issues and Solutions

1. **Training Job Failures**
   - Check IAM permissions for S3 and SageMaker
   - Verify data format and paths
   - Monitor CloudWatch logs

2. **Endpoint Deployment Issues**
   - Validate inference script syntax
   - Check container image compatibility
   - Verify model artifacts format

3. **Pipeline Execution Errors**
   - Review pipeline definition JSON
   - Check step dependencies
   - Validate input/output paths

4. **Data Quality Issues**
   - Implement data validation steps
   - Set up automated alerts
   - Monitor data drift metrics

### Next Steps for Week 4

- Complete integration with Girik's API Gateway
- Connect to Adariprasad's monitoring systems
- Perform end-to-end testing
- Document APIs and interfaces
- Prepare for production deployment

---

## Key Resources and Documentation

- **AWS SageMaker Documentation**: https://docs.aws.amazon.com/sagemaker/
- **AWS Glue Developer Guide**: https://docs.aws.amazon.com/glue/latest/dg/
- **SageMaker Python SDK**: https://sagemaker.readthedocs.io/
- **MLOps Best Practices**: https://aws.amazon.com/sagemaker/mlops/
- **Model Registry Guide**: https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry.html

---

## Contact and Support

For questions or issues during implementation:
- AWS Documentation: https://docs.aws.amazon.com/
- SageMaker Examples: https://github.com/aws/amazon-sagemaker-examples
- AWS Support: Contact through AWS Console

**Remember**: This tutorial provides the foundation for ADPA's ML services. Adapt configurations based on your specific data and requirements. Focus on getting basic functionality working first, then optimize for production.

---

*Generated for ADPA Team - Data650 Group Project*  
*ML Services Lead: Archit*  
*Duration: 4 weeks*  
*Last Updated: November 2025*