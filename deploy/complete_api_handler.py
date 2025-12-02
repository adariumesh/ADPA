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

# AWS clients
s3 = boto3.client('s3', region_name='us-east-2')
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
sfn = boto3.client('stepfunctions', region_name='us-east-2')

# Configuration
DATA_BUCKET = 'adpa-data-083308938449-production'
MODEL_BUCKET = 'adpa-models-083308938449-production'
PIPELINES_TABLE = 'adpa-pipelines'
STATE_MACHINE_ARN = 'arn:aws:states:us-east-2:083308938449:stateMachine:adpa-ml-pipeline-workflow'


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
    """Get or create DynamoDB table"""
    try:
        table = dynamodb.Table(PIPELINES_TABLE)
        table.load()
        return table
    except:
        table = dynamodb.create_table(
            TableName=PIPELINES_TABLE,
            KeySchema=[{'AttributeName': 'pipeline_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'pipeline_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        return table


def lambda_handler(event, context):
    """Main handler"""
    
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
            now = datetime.utcnow().isoformat() + 'Z'
            
            pipeline = {
                'pipeline_id': pipeline_id,
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
            item = get_table().get_item(Key={'pipeline_id': pipeline_id}).get('Item')
            
            if not item:
                return error(f'Pipeline not found: {pipeline_id}', 404)
            
            return response(item)
        
        # POST /pipelines/{id}/execute
        if path.endswith('/execute') and method == 'POST':
            pipeline_id = path.split('/')[-2]
            item = get_table().get_item(Key={'pipeline_id': pipeline_id}).get('Item')
            
            if not item:
                return error(f'Pipeline not found: {pipeline_id}', 404)
            
            exec_name = f"{pipeline_id}-{int(time.time())}"
            exec_input = json.dumps({
                'pipeline_id': pipeline_id,
                'dataset_path': item['dataset_path'],
                'objective': item['objective']
            })
            
            sfn_resp = sfn.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=exec_name,
                input=exec_input
            )
            
            get_table().update_item(
                Key={'pipeline_id': pipeline_id},
                UpdateExpression='SET #s = :s, execution_arn = :arn',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':s': 'running', ':arn': sfn_resp['executionArn']}
            )
            
            return response({'pipeline_id': pipeline_id, 'status': 'running', 'execution_arn': sfn_resp['executionArn']})
        
        # GET /pipelines/{id}/status
        if path.endswith('/status') and method == 'GET':
            pipeline_id = path.split('/')[-2]
            item = get_table().get_item(Key={'pipeline_id': pipeline_id}).get('Item')
            
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
