#!/usr/bin/env python3
"""End-to-end verification for the deployed ADPA pipeline."""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from botocore.exceptions import ClientError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.aws_config import AWS_REGION, get_boto3_session  # noqa: E402  pylint: disable=wrong-import-position

DEFAULT_API_URL = "https://cr1kkj7213.execute-api.us-east-2.amazonaws.com/prod"


class VerificationError(RuntimeError):
    """Raised when the verification flow fails."""


def encode_dataset(dataset_path: Path) -> Tuple[str, bytes]:
    data = dataset_path.read_bytes()
    return base64.b64encode(data).decode("utf-8"), data


def upload_dataset(api_url: str, dataset_path: Path, filename: Optional[str] = None) -> Dict[str, Any]:
    encoded_content, raw_bytes = encode_dataset(dataset_path)
    payload = {
        "filename": filename or dataset_path.name,
        "content": encoded_content,
        "encoding": "base64",
    }
    response = requests.post(f"{api_url}/data/upload", json=payload, timeout=60)
    response.raise_for_status()
    body = response.json()
    body["s3_uri"] = f"s3://{body['bucket']}/{body['s3_key']}"
    body["size_readable"] = len(raw_bytes)
    return body


def create_pipeline(
    api_url: str,
    dataset_s3_uri: str,
    objective: str,
    pipeline_name: str,
    pipeline_type: str,
) -> Dict[str, Any]:
    payload = {
        "dataset_path": dataset_s3_uri,
        "objective": objective,
        "name": pipeline_name,
        "type": pipeline_type,
        "config": {
            "use_real_aws": True,
            "type": pipeline_type,
            "name": pipeline_name,
        },
    }
    response = requests.post(f"{api_url}/pipelines", json=payload, timeout=60)
    response.raise_for_status()
    body = response.json()
    if not body.get("pipeline_id"):
        raise VerificationError(f"Pipeline creation response missing pipeline_id: {body}")
    return body


def execute_pipeline(api_url: str, pipeline_id: str) -> Dict[str, Any]:
    response = requests.post(f"{api_url}/pipelines/{pipeline_id}/execute", timeout=60)
    response.raise_for_status()
    return response.json()


def extract_execution_arn(payload: Dict[str, Any]) -> Optional[str]:
    result = payload.get("result")
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            result = None
    if isinstance(result, dict):
        if result.get("execution_arn"):
            return result["execution_arn"]
        if isinstance(result.get("execution_result"), dict):
            candidate = result["execution_result"].get("execution_arn") or result["execution_result"].get("executionArn")
            if candidate:
                return candidate
    return payload.get("execution_arn")


def poll_pipeline_status(
    api_url: str,
    pipeline_id: str,
    attempts: int,
    interval_seconds: int,
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    statuses: List[Dict[str, Any]] = []
    execution_arn: Optional[str] = None

    for attempt in range(1, attempts + 1):
        response = requests.get(f"{api_url}/pipelines/{pipeline_id}", timeout=30)
        response.raise_for_status()
        body = response.json()
        body["attempt"] = attempt
        statuses.append(body)
        execution_arn = extract_execution_arn(body)
        if execution_arn:
            break
        time.sleep(interval_seconds)

    return execution_arn, statuses


def describe_execution(execution_arn: str, region: str, max_history: int) -> Dict[str, Any]:
    session = get_boto3_session()
    client = session.client("stepfunctions", region_name=region)
    description = client.describe_execution(executionArn=execution_arn)

    history_events: List[Dict[str, Any]] = []
    paginator = client.get_paginator("get_execution_history")
    for page in paginator.paginate(executionArn=execution_arn, reverseOrder=False):
        for event in page.get("events", []):
            history_events.append(event)
            if len(history_events) >= max_history:
                break
        if len(history_events) >= max_history:
            break

    state_entries = []
    for event in history_events:
        details = event.get("stateEnteredEventDetails")
        if details and details.get("name"):
            entry = {
                "event_id": event.get("id"),
                "timestamp": event.get("timestamp").isoformat() if event.get("timestamp") else None,
                "name": details["name"],
            }
            state_entries.append(entry)

    return {
        "description": description,
        "state_entries": state_entries,
        "total_events_scanned": len(history_events),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify ADPA upload → pipeline → execute flow")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API Gateway base URL")
    parser.add_argument(
        "--dataset-path",
        default="demo_datasets/customer_churn.csv",
        help="Local dataset CSV to upload",
    )
    parser.add_argument(
        "--objective",
        default="Predict customer churn with high accuracy",
        help="Objective text for the pipeline request",
    )
    parser.add_argument("--pipeline-name", default="Verification Run", help="Logical pipeline name")
    parser.add_argument("--pipeline-type", default="classification", help="Pipeline type field")
    parser.add_argument("--poll-attempts", type=int, default=18, help="Number of GET polls for pipeline status")
    parser.add_argument("--poll-interval", type=int, default=10, help="Seconds between polls")
    parser.add_argument("--region", default=AWS_REGION, help="AWS region for Step Functions describe calls")
    parser.add_argument("--max-history", type=int, default=180, help="Maximum Step Functions events to scan")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_path = Path(args.dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")

    print("🚀 Starting ADPA verification flow")
    print(f"API URL: {args.api_url}")
    print(f"Dataset: {dataset_path}")

    upload_info = upload_dataset(args.api_url, dataset_path)
    dataset_uri = upload_info["s3_uri"]
    print(f"📤 Uploaded dataset to {dataset_uri}")

    pipeline_resp = create_pipeline(
        api_url=args.api_url,
        dataset_s3_uri=dataset_uri,
        objective=args.objective,
        pipeline_name=args.pipeline_name,
        pipeline_type=args.pipeline_type,
    )
    pipeline_id = pipeline_resp["pipeline_id"]
    print(f"🆔 Created pipeline: {pipeline_id}")

    execute_resp = execute_pipeline(args.api_url, pipeline_id)
    print(f"▶️ Execute response: {execute_resp}")

    execution_arn, status_history = poll_pipeline_status(
        api_url=args.api_url,
        pipeline_id=pipeline_id,
        attempts=args.poll_attempts,
        interval_seconds=args.poll_interval,
    )
    if not execution_arn:
        raise VerificationError("Timed out waiting for execution ARN to appear in pipeline status")

    print(f"✅ Execution ARN detected: {execution_arn}")

    step_func_data: Dict[str, Any] = {}
    try:
        step_func_data = describe_execution(execution_arn, args.region, args.max_history)
    except ClientError as exc:
        print(f"⚠️ Failed to describe Step Functions execution: {exc}")
        step_func_data = {"error": str(exc)}

    summary = {
        "upload": upload_info,
        "pipeline": pipeline_resp,
        "execute_response": execute_resp,
        "execution_arn": execution_arn,
        "step_functions": step_func_data,
        "status_history": status_history,
    }

    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover - CLI usage
        print(f"❌ Verification failed: {exc}", file=sys.stderr)
        sys.exit(1)
