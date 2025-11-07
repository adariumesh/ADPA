#!/usr/bin/env python3
import argparse, io, gzip, json, random, string
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import boto3

rng = np.random.default_rng(42)

def rand_str(n=8):
    return ''.join(rng.choice(list(string.ascii_lowercase), n))

def make_sales(n=2000):
    days = [datetime.utcnow().date() - timedelta(days=int(i)) for i in rng.integers(0, 60, size=n)]
    df = pd.DataFrame({
        'order_id': rng.integers(10_000, 99_999, size=n),
        'customer_id': rng.integers(1_000, 1_999, size=n),
        'sku': [f"SKU-{rng.integers(100,999)}" for _ in range(n)],
        'quantity': rng.integers(1, 5, size=n),
        'unit_price': rng.normal(20, 5, size=n).round(2),
        'order_date': days,
        'region': rng.choice(['NA','EU','APAC'], size=n, p=[0.6,0.25,0.15])
    })
    df['revenue'] = (df['quantity'] * df['unit_price']).round(2)
    return df

def make_users(n=500):
    for i in range(n):
        yield {
            'user_id': int(1000+i),
            'email': f"{rand_str(5)}@example.com",
            'signup_ts': datetime.utcnow().isoformat(),
            'country': random.choice(['US','DE','IN','GB','CA'])
        }

def make_events(n=3000):
    ts0 = datetime.utcnow()
    df = pd.DataFrame({
        'event_id': rng.integers(1_000_000, 9_999_999, size=n),
        'ts': [ts0 - timedelta(seconds=int(x)) for x in rng.integers(0, 3600, size=n)],
        'user_id': rng.integers(1000, 1499, size=n),
        'event_type': rng.choice(['view','click','add_to_cart','purchase'], size=n, p=[0.6,0.25,0.1,0.05]),
        'device': rng.choice(['web','ios','android'], size=n)
    })
    return df

def make_logs(n=1000):
    for i in range(n):
        yield {
            'ts': datetime.utcnow().isoformat(),
            'level': random.choice(['INFO','WARN','ERROR']),
            'msg': random.choice(['ok','slow','timeout','retry'])
        }


def upload_bytes(s3, bucket, key, data_bytes):
    s3.put_object(Bucket=bucket, Key=key, Body=data_bytes)
    print(f"uploaded s3://{bucket}/{key}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bucket', required=True, help='RAW bucket name')
    ap.add_argument('--prefix', default='adpa/raw/', help='prefix under raw bucket')
    args = ap.parse_args()

    s3 = boto3.client('s3')

    # 1) sales CSV
    sales = make_sales()
    csv_bytes = sales.to_csv(index=False).encode('utf-8')
    upload_bytes(s3, args.bucket, f"{args.prefix}sales/sales.csv", csv_bytes)

    # 2) users JSONL
    bio = io.BytesIO()
    for rec in make_users():
        bio.write((json.dumps(rec) + "\n").encode('utf-8'))
    upload_bytes(s3, args.bucket, f"{args.prefix}users/users.jsonl", bio.getvalue())

    # 3) events Parquet
    events = make_events()
    pq_path = '/tmp/events.parquet'
    events.to_parquet(pq_path, engine='pyarrow', index=False)
    with open(pq_path, 'rb') as f:
        upload_bytes(s3, args.bucket, f"{args.prefix}events/events.parquet", f.read())

    # 4) logs gz CSV
    logs = list(make_logs())
    df_logs = pd.DataFrame(logs)
    gz = io.BytesIO()
    with gzip.GzipFile(fileobj=gz, mode='wb') as z:
        z.write(df_logs.to_csv(index=False).encode('utf-8'))
    upload_bytes(s3, args.bucket, f"{args.prefix}logs/logs.csv.gz", gz.getvalue())

    print("done.")

if __name__ == '__main__':
    main()