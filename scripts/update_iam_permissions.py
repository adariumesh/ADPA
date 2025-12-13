#!/usr/bin/env python3
"""Utility to patch the ADPA Lambda execution role with Step Functions and CloudWatch Logs permissions.

This script ensures that the Lambda execution role can pass the Step Functions
execution role and has the logging permissions required by the orchestrator.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

from botocore.exceptions import ClientError


def _ensure_project_root_on_path() -> None:
    """Add the repository root to sys.path so `config` is importable."""
    project_root = Path(__file__).resolve().parents[1]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)


_ensure_project_root_on_path()

from config.aws_config import (  # noqa: E402  pylint: disable=wrong-import-position
    AWS_ACCOUNT_ID,
    AWS_REGION,
    STEP_FUNCTIONS_ROLE,
    get_boto3_session,
)

PASS_ROLE_POLICY_NAME = "ADPAAllowPassStepFunctionsRole"
LOGS_POLICY_NAME = "ADPAOrchestratorLogsAccess"

def build_passrole_policy(step_role_arn: str) -> Dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowPassStepFunctionsRole",
                "Effect": "Allow",
                "Action": "iam:PassRole",
                "Resource": step_role_arn,
            }
        ],
    }

def build_logs_policy(region: str, account: str) -> Dict:
    log_group_arn = f"arn:aws:logs:{region}:{account}:log-group:*"
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowLogGroupManagement",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:TagResource",
                    "logs:PutRetentionPolicy",
                ],
                "Resource": log_group_arn,
            },
            {
                "Sid": "AllowLogStreamWrites",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": f"{log_group_arn}:*",
            },
        ],
    }

def ensure_inline_policy(iam_client, role_name: str, policy_name: str, document: Dict) -> None:
    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(document),
    )

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patch IAM permissions for the ADPA Lambda execution role.")
    parser.add_argument(
        "--role-name",
        default="adpa-lambda-execution-role",
        help="IAM role name to patch (default: adpa-lambda-execution-role)",
    )
    parser.add_argument(
        "--step-role-arn",
        default=STEP_FUNCTIONS_ROLE,
        help=f"Step Functions execution role ARN to allow via PassRole (default: {STEP_FUNCTIONS_ROLE})",
    )
    parser.add_argument(
        "--region",
        default=AWS_REGION,
        help=f"AWS region for CloudWatch Logs resources (default: {AWS_REGION})",
    )
    parser.add_argument(
        "--account-id",
        default=AWS_ACCOUNT_ID,
        help=f"AWS account ID for resource ARNs (default: {AWS_ACCOUNT_ID})",
    )
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    session = get_boto3_session()
    iam_client = session.client("iam", region_name=args.region)

    try:
        ensure_inline_policy(
            iam_client,
            args.role_name,
            PASS_ROLE_POLICY_NAME,
            build_passrole_policy(args.step_role_arn),
        )
        print(
            f"✅ Attached iam:PassRole permissions for {args.step_role_arn} to role {args.role_name}."
        )

        ensure_inline_policy(
            iam_client,
            args.role_name,
            LOGS_POLICY_NAME,
            build_logs_policy(args.region, args.account_id),
        )
        print(
            "✅ Granted CloudWatch Logs permissions (CreateLogGroup/CreateLogStream/PutLogEvents/TagResource)."
        )
        return 0
    except ClientError as exc:
        print(f"❌ Failed to update IAM role: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
