#!/usr/bin/env python3
"""
Create S3 buckets for ADPA manually
"""

import boto3
import sys
from botocore.exceptions import ClientError

def create_s3_buckets():
    """Create S3 buckets for ADPA"""
    
    s3_client = boto3.client('s3', region_name='us-east-2')
    
    buckets_to_create = [
        'adpa-data-083308938449-development',
        'adpa-models-083308938449-development'
    ]
    
    print("🪣 Creating S3 Buckets...")
    
    for bucket_name in buckets_to_create:
        try:
            # Check if bucket already exists
            try:
                s3_client.head_bucket(Bucket=bucket_name)
                print(f"✅ Bucket already exists: {bucket_name}")
                continue
            except ClientError:
                pass
            
            # Create bucket
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': 'us-east-2'
                }
            )
            
            # Block public access
            s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            
            print(f"✅ Created bucket: {bucket_name}")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'BucketAlreadyOwnedByYou':
                print(f"✅ Bucket already owned: {bucket_name}")
            elif error_code == 'BucketAlreadyExists':
                print(f"❌ Bucket name taken by someone else: {bucket_name}")
                return False
            else:
                print(f"❌ Error creating bucket {bucket_name}: {e}")
                return False
    
    print("🎉 All S3 buckets ready!")
    return True

if __name__ == "__main__":
    success = create_s3_buckets()
    sys.exit(0 if success else 1)