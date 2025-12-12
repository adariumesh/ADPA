"""Lightweight entrypoint for the ADPA Lambda.

All heavy orchestration, HTTP routing, and async processing live inside
`src/api/routes/pipeline_router.py` and `src/orchestration/adpa_lambda_orchestrator.py`.
This module wires those building blocks together and keeps the Lambda handler
focused on delegation and basic error handling.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Ensure AWS Lambda can import modules from src/
# ---------------------------------------------------------------------------
LAMBDA_TASK_ROOT = os.environ.get("LAMBDA_TASK_ROOT", os.path.dirname(os.path.abspath(__file__)))
SEARCH_PATHS = [
    LAMBDA_TASK_ROOT,
    "/var/task",
    "/opt/python",
    "./src",
    ".",
]
for path in SEARCH_PATHS:
    if path and path not in sys.path:
        sys.path.insert(0, path)

# Attempt to load optional compatibility helpers (safe to ignore)
try:  # pragma: no cover - optional
    from src import compat as _compat  # noqa: F401
except ImportError:  # pragma: no cover - optional dependency missing
    pass

from src.api.routes.pipeline_router import PipelineRouter
from src.orchestration.adpa_lambda_orchestrator import ADPALambdaOrchestrator

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# AWS + environment configuration
# ---------------------------------------------------------------------------
AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID", "083308938449")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")

AWS_CONFIG: Dict[str, Any] = {
    "data_bucket": os.getenv("DATA_BUCKET", f"adpa-data-{AWS_ACCOUNT_ID}-{ENVIRONMENT}"),
    "model_bucket": os.getenv("MODEL_BUCKET", f"adpa-models-{AWS_ACCOUNT_ID}-{ENVIRONMENT}"),
    "secrets_arn": os.getenv("SECRETS_ARN", ""),
    "region": AWS_REGION,
    "account_id": AWS_ACCOUNT_ID,
}

LAMBDA_FUNCTION_NAME = os.getenv("AWS_LAMBDA_FUNCTION_NAME", "adpa-lambda-handler")


def _build_router() -> PipelineRouter:
    orchestrator = ADPALambdaOrchestrator(AWS_CONFIG)
    return PipelineRouter(
        aws_config=AWS_CONFIG,
        orchestrator=orchestrator,
        lambda_function_name=LAMBDA_FUNCTION_NAME,
    )


try:  # pragma: no cover - initialization occurs at import time in Lambda
    PIPELINE_ROUTER = _build_router()
except Exception as exc:  # pragma: no cover - defensive fallback
    logger.exception("Failed to initialize ADPA router: %s", exc)
    PIPELINE_ROUTER = None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Delegate incoming events to HTTP, async, or legacy handlers."""

    logger.info("ADPA Lambda invoked with event: %s", json.dumps(event, default=str))

    if PIPELINE_ROUTER is None:
        return _json_response(
            status_code=500,
            payload={
                "status": "error",
                "error": "ADPA router failed to initialize",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    try:
        if event.get("action") == "process_pipeline_async":
            return PIPELINE_ROUTER.process_pipeline_async(event)

        if "httpMethod" in event and "path" in event:
            return PIPELINE_ROUTER.handle_http(event)

        return PIPELINE_ROUTER.handle_legacy_action(event)

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Lambda handler error: %s", exc)
        return _json_response(
            status_code=500,
            payload={
                "status": "error",
                "error": f"Lambda handler error: {exc}",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


def _json_response(status_code: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS, PUT, DELETE",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token, x-filename, X-Filename",
    }
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(payload),
    }


if __name__ == "__main__":  # pragma: no cover - manual local check
    print(json.dumps(lambda_handler({"action": "health_check"}, None), indent=2))
