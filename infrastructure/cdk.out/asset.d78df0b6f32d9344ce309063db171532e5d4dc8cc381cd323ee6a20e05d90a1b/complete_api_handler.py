"""
Complete ADPA API Lambda Handler
Handles all API endpoints for pipeline management
"""

import json
import boto3
import base64
import time
import uuid
from datetime import datetime
from typing import Dict, Any
import os
from boto3.dynamodb.conditions import Key

# AWS clients
s3 = boto3.client('s3', region_name='us-east-2')
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
sfn = boto3.client('stepfunctions', region_name='us-east-2')

# Configuration from environment variables
DATA_BUCKET = os.environ.get('DATA_BUCKET', 'adpa-prod-data-083308938449')
MODEL_BUCKET = os.environ.get('MODEL_BUCKET', 'adpa-prod-models-083308938449')
PIPELINES_TABLE = os.environ.get('PIPELINES_TABLE', 'adpa-prod-pipelines')
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN', 'arn:aws:states:us-east-2:083308938449:stateMachine:adpa-prod-ml-pipeline-workflow')


def cors_headers():
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization'
    }


def response(data: Any, status: int = 200):
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json', **cors_headers()},
        'body': json.dumps(data, default=str)
    }


def error(msg: str, status: int = 500):
    return response({'error': msg, 'timestamp': datetime.utcnow().isoformat() + 'Z'}, status)


def get_table():
    """Get DynamoDB table"""
    table = dynamodb.Table(PIPELINES_TABLE)
    return table


def handle_step_function_action(event, context):
    """Handle Step Functions action calls"""
    action = event.get('action')
    
    try:
        if action == 'ingest_data':
            data_path = event.get('data_path')
            objective = event.get('objective')
            
            # Simulate data ingestion - return S3 path
            return {
                'status': 'success',
                'data': f"{data_path}",
                'objective': objective,
                'ingested_at': datetime.utcnow().isoformat()
            }
            
        elif action == 'clean_data':
            data = event.get('data')
            strategy = event.get('strategy', 'intelligent')
            
            # Simulate data cleaning
            return {
                'status': 'success',
                'data': data,
                'strategy': strategy,
                'cleaned_at': datetime.utcnow().isoformat()
            }
            
        elif action == 'engineer_features':
            data = event.get('data')
            objective = event.get('objective')
            
            # Simulate feature engineering
            training_data_s3 = f"s3://{DATA_BUCKET}/processed/training_{int(time.time())}.csv"
            test_data_s3 = f"s3://{DATA_BUCKET}/processed/test_{int(time.time())}.csv"
            
            return {
                'status': 'success',
                'training_data_s3': training_data_s3,
                'test_data_s3': test_data_s3,
                'features_engineered': ['feature1', 'feature2', 'target'],
                'objective': objective
            }
            
        elif action == 'evaluate_model':
            model_artifacts = event.get('model_artifacts')
            test_data = event.get('test_data')
            
            # Simulate model evaluation
            return {
                'status': 'success',
                'accuracy': 0.85,
                'f1_score': 0.82,
                'precision': 0.87,
                'recall': 0.78,
                'model_artifacts': model_artifacts,
                'evaluated_at': datetime.utcnow().isoformat()
            }
            
        else:
            return {
                'status': 'error',
                'error': f'Unknown action: {action}'
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'action': action
        }


def lambda_handler(event, context):
    """Main handler - supports both API Gateway and Step Functions"""
    
    # Handle Step Functions action calls
    if 'action' in event:
        return handle_step_function_action(event, context)
    
    # CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers(), 'body': ''}
    
    path = event.get('path', '').replace('/prod', '')
    method = event.get('httpMethod', 'GET')
    
    try:
        # Health check
        if path == '/health':
            try:
                s3.head_bucket(Bucket=DATA_BUCKET)
                s3_ok = True
            except:
                s3_ok = False
            
            return response({
                'status': 'healthy' if s3_ok else 'degraded',
                'components': {'s3': s3_ok, 'lambda': True},
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        
        # POST /pipelines - Create
        if path == '/pipelines' and method == 'POST':
            body = json.loads(event.get('body', '{}'))
            
            pipeline_id = f"pipeline-{uuid.uuid4().hex[:12]}"
            timestamp = int(time.time())  # Unix timestamp for sort key
            now = datetime.utcnow().isoformat() + 'Z'
            
            pipeline = {
                'pipeline_id': pipeline_id,
                'timestamp': timestamp,  # Sort key required by table schema
                'dataset_path': body.get('dataset_path') or body.get('dataset'),
                'objective': body.get('objective'),
                'config': body.get('config', {}),
                'status': 'created',
                'created_at': now,
                'updated_at': now
            }
            
            get_table().put_item(Item=pipeline)
            
            return response({'pipeline_id': pipeline_id, 'status': 'created', 'pipeline': pipeline}, 201)
        
        # GET /pipelines - List
        if path == '/pipelines' and method == 'GET':
            items = get_table().scan().get('Items', [])
            items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return response({'pipelines': items, 'count': len(items)})
        
        # GET /pipelines/{id}
        if '/pipelines/' in path and method == 'GET' and not path.endswith('/status'):
            pipeline_id = path.split('/')[-1]
            # Get the most recent item for this pipeline_id
            result = get_table().query(
                KeyConditionExpression=Key('pipeline_id').eq(pipeline_id),
                ScanIndexForward=False,  # Sort by timestamp descending
                Limit=1
            )
            items = result.get('Items', [])
            item = items[0] if items else None
            
            if not item:
                return error(f'Pipeline not found: {pipeline_id}', 404)
            
            return response(item)
        
        # POST /pipelines/{id}/execute
        if path.endswith('/execute') and method == 'POST':
            pipeline_id = path.split('/')[-2]
            # Get the most recent item for this pipeline_id
            result = get_table().query(
                KeyConditionExpression=Key('pipeline_id').eq(pipeline_id),
                ScanIndexForward=False,  # Sort by timestamp descending
                Limit=1
            )
            items = result.get('Items', [])
            item = items[0] if items else None
            
            if not item:
                return error(f'Pipeline not found: {pipeline_id}', 404)
            
            exec_name = f"{pipeline_id}-{int(time.time())}"
            exec_input = json.dumps({
                'pipeline_id': pipeline_id,
                'data_path': item['dataset_path'],
                'objective': item['objective'],
                'training_job_name': f"adpa-training-{pipeline_id}-{int(time.time())}"
            })
            
            sfn_resp = sfn.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=exec_name,
                input=exec_input
            )
            
            # Update the most recent item for this pipeline_id
            get_table().update_item(
                Key={'pipeline_id': pipeline_id, 'timestamp': item['timestamp']},
                UpdateExpression='SET #s = :s, execution_arn = :arn',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':s': 'running', ':arn': sfn_resp['executionArn']}
            )
            
            return response({'pipeline_id': pipeline_id, 'status': 'running', 'execution_arn': sfn_resp['executionArn']})
        
        # GET /pipelines/{id}/status
        if path.endswith('/status') and method == 'GET':
            pipeline_id = path.split('/')[-2]
            # Get the most recent item for this pipeline_id
            result = get_table().query(
                KeyConditionExpression=Key('pipeline_id').eq(pipeline_id),
                ScanIndexForward=False,  # Sort by timestamp descending
                Limit=1
            )
            items = result.get('Items', [])
            item = items[0] if items else None
            
            if not item:
                return error(f'Pipeline not found: {pipeline_id}', 404)
            
            exec_arn = item.get('execution_arn')
            if not exec_arn:
                return response({'pipeline_id': pipeline_id, 'status': item.get('status', 'created')})
            
            sfn_resp = sfn.describe_execution(executionArn=exec_arn)
            status = sfn_resp['status'].lower()
            
            return response({
                'pipeline_id': pipeline_id,
                'status': status,
                'start_date': sfn_resp.get('startDate'),
                'stop_date': sfn_resp.get('stopDate')
            })
        
        # POST /data/upload
        if path == '/data/upload' and method == 'POST':
            upload_id = f"upload-{uuid.uuid4().hex[:12]}"
            s3_key = f"uploads/{upload_id}-{int(time.time())}.csv"
            
            body = event['body']
            if event.get('isBase64Encoded'):
                body = base64.b64decode(body)
            
            s3.put_object(Bucket=DATA_BUCKET, Key=s3_key, Body=body)
            
            return response({
                'upload_id': upload_id,
                's3_path': f"s3://{DATA_BUCKET}/{s3_key}",
                'message': 'Upload successful'
            }, 201)
        
        # GET /data/uploads
        if path == '/data/uploads' and method == 'GET':
            objs = s3.list_objects_v2(Bucket=DATA_BUCKET, Prefix='uploads/').get('Contents', [])
            uploads = [{
                'key': o['Key'],
                's3_path': f"s3://{DATA_BUCKET}/{o['Key']}",
                'size': o['Size'],
                'last_modified': o['LastModified']
            } for o in objs]
            
            return response({'uploads': uploads, 'count': len(uploads)})
        
        return error(f'Not found: {method} {path}', 404)
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return error(str(e), 500)
