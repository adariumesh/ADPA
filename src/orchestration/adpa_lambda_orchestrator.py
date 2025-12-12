"""ADPA Lambda Orchestrator wrapper.

This module encapsulates the heavy orchestration logic that was previously
embedded directly inside the Lambda handler so that it can be reused by
multiple entrypoints (API handler and async worker).
"""

from __future__ import annotations

import logging
import os
import traceback
from datetime import datetime
from typing import Any, Dict

# Optional AWS X-Ray support -------------------------------------------------
try:  # pragma: no cover - optional dependency
    from aws_xray_sdk.core import xray_recorder
    from aws_xray_sdk.core import patch_all

    patch_all()
    XRAY_ENABLED = True
except ImportError:  # pragma: no cover - optional dependency degraded gracefully
    XRAY_ENABLED = False

    class DummyRecorder:  # pylint: disable=too-few-public-methods
        """Fallback recorder that behaves like aws_xray's capture decorator."""

        @staticmethod
        def capture(_name):
            def decorator(func):
                return func

            return decorator

    xray_recorder = DummyRecorder()  # type: ignore

import boto3  # noqa: E402  (import after optional xray setup)

from src.agent.core.master_agent import MasterAgenticController
from src.monitoring.cloudwatch_monitor import ADPACloudWatchMonitor
from src.monitoring.kpi_tracker import ADPABusinessMetrics as KPITracker
from src.orchestration.pipeline_executor import RealPipelineExecutor
from src.training.sagemaker_trainer import SageMakerTrainer
from src.aws.stepfunctions.orchestrator import StepFunctionsOrchestrator

logger = logging.getLogger(__name__)


class ADPALambdaOrchestrator:
    """Unified orchestrator that wires the agent with Girik's AWS infra."""

    def __init__(self, aws_config: Dict[str, Any]):
        self.aws_config = aws_config
        self.monitoring = None
        self.kpi_tracker = None
        self.agent = None
        self.real_executor = None
        self.sagemaker_trainer = None
        self.stepfunctions = None
        self.initialized = False

        self._initialize_components()

    def _initialize_components(self) -> None:
        """Best-effort initialization of all ADPA building blocks."""

        try:
            # Monitoring + KPI systems -------------------------------------------------
            self.monitoring = ADPACloudWatchMonitor()
            self.kpi_tracker = KPITracker()

            # Agent -------------------------------------------------
            self.agent = MasterAgenticController(
                aws_config=self.aws_config,
                memory_dir="/tmp/experience_memory",
            )

            # Infrastructure integrations --------------------------------------------
            region = self.aws_config["region"]
            account_id = self.aws_config["account_id"]

            self.real_executor = RealPipelineExecutor(region=region, account_id=account_id)
            self.sagemaker_trainer = SageMakerTrainer(region=region)
            self.stepfunctions = StepFunctionsOrchestrator(region=region)

            self.initialized = True

            use_real_llm = os.getenv("USE_REAL_LLM", "false").lower() == "true"
            if use_real_llm:
                logger.info("🚀 ADPA Lambda initialized with REAL AI (Bedrock Claude 3.5 Sonnet)")
            else:
                logger.info("ADPA Lambda initialized with intelligent simulation")
            logger.info("ADPA Lambda orchestrator with real AWS integration initialized successfully")

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to initialize ADPA components: %s", exc)
            logger.error("Traceback: %s", traceback.format_exc())
            self.initialized = False

    # ------------------------------------------------------------------
    # Pipeline execution paths
    # ------------------------------------------------------------------
    @xray_recorder.capture("run_pipeline")
    def run_pipeline(self, event: Dict[str, Any]) -> Dict[str, Any]:
        if not self.initialized:
            return self._failure_response(f"ADPA not initialized", extra={"error": True})

        try:
            logger.info("Starting ADPA pipeline execution")

            dataset_path = event.get("dataset_path", "")
            objective = event.get("objective", "classification")
            pipeline_type = event.get("type", "classification")
            config = event.get("config", {})

            enhanced_config = {
                **config,
                "aws_config": self.aws_config,
                "execution_mode": "lambda",
                "infrastructure": "girik_aws",
                "problem_type": pipeline_type,
            }

            logger.info("🤖 Calling agent with real AI reasoning for objective: %s", objective)
            result = self.agent.process_natural_language_request(  # type: ignore[union-attr]
                request=objective,
                data=None,
                context=enhanced_config,
            )
            logger.info("✅ Agent AI reasoning completed successfully")

            execution_result = result.get("execution_result")
            metrics = {}
            if execution_result and hasattr(execution_result, "metrics"):
                metrics = execution_result.metrics or {}

            response_data = {
                "status": "completed",
                "pipeline_id": result.get("session_id", "unknown"),
                "execution_time": metrics.get("execution_time", 0),
                "performance_metrics": metrics,
                "model_performance": metrics,
                "understanding": result.get("understanding", {}),
                "pipeline_plan": result.get("pipeline_plan", {}),
                "summary": result.get("natural_language_summary", ""),
                "dashboard_url": self._get_dashboard_url(),
                "timestamp": datetime.utcnow().isoformat(),
            }

            self._publish_metrics(response_data)
            self._track_kpis(response_data)

            return response_data

        except Exception as exc:  # pragma: no cover - defensive logging
            error_msg = f"Pipeline execution failed: {exc}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())

            if self.monitoring:
                self.monitoring.send_alert(  # type: ignore[union-attr]
                    message=error_msg,
                    severity="HIGH",
                    source="ADPA Lambda",
                )

            return {
                "status": "failed",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat(),
            }

    @xray_recorder.capture("run_real_pipeline")
    def run_real_pipeline(self, event: Dict[str, Any]) -> Dict[str, Any]:
        if not self.initialized:
            return self._failure_response("ADPA not initialized")

        try:
            logger.info("Starting ADPA real pipeline execution with Step Functions + SageMaker")

            dataset_path = event.get("dataset_path", "")
            objective = event.get("objective", "binary_classification")
            config = event.get("config", {})

            pipeline_config = {
                "objective": objective,
                "dataset_type": "csv",
                "target_column": config.get("target_column", "target"),
                "steps": [
                    {"type": "data_validation", "timeout": 300},
                    {"type": "data_cleaning", "timeout": 600},
                    {"type": "feature_engineering", "timeout": 900},
                    {"type": "model_training", "timeout": 3600},
                    {"type": "model_evaluation", "timeout": 300},
                ],
            }

            state_machine_result = self.stepfunctions.create_state_machine_with_retries(  # type: ignore[union-attr]
                pipeline_config=pipeline_config,
                name=f"adpa-lambda-pipeline-{int(datetime.utcnow().timestamp())}",
            )

            if state_machine_result.get("status") == "FAILED":
                raise RuntimeError(state_machine_result.get("error", "Unknown error"))

            state_machine_arn = state_machine_result.get("state_machine_arn")
            logger.info("Created state machine: %s", state_machine_arn)

            execution_input = {
                "pipeline_id": f"lambda-{int(datetime.utcnow().timestamp())}",
                "dataset_path": dataset_path,
                "objective": objective,
                "target_column": config.get("target_column", "target"),
                "config": config,
            }

            execution_result = self.stepfunctions.execute_pipeline(  # type: ignore[union-attr]
                state_machine_arn=state_machine_arn,
                input_data=execution_input,
                execution_name=f"lambda-execution-{int(datetime.utcnow().timestamp())}",
            )

            self._publish_metrics(execution_result)
            self._track_kpis(execution_result)

            return {
                "status": "completed",
                "execution_mode": "real_aws",
                "state_machine_arn": state_machine_arn,
                "execution_arn": execution_result.get("execution_arn"),
                "execution_status": execution_result.get("status"),
                "pipeline_id": execution_input["pipeline_id"],
                "dashboard_url": self._get_dashboard_url(),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as exc:  # pragma: no cover - defensive logging
            error_msg = f"Real pipeline execution failed: {exc}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())

            if self.monitoring:
                self.monitoring.send_alert(  # type: ignore[union-attr]
                    message=error_msg,
                    severity="HIGH",
                    source="ADPA Real Pipeline",
                )

            return {
                "status": "failed",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat(),
            }

    # ------------------------------------------------------------------
    # Status + telemetry helpers
    # ------------------------------------------------------------------
    def get_pipeline_status(self, event: Dict[str, Any]) -> Dict[str, Any]:
        pipeline_id = event.get("pipeline_id", "")
        if not pipeline_id:
            return self._failure_response("Pipeline ID required")

        if not self.agent:
            return self._failure_response("ADPA agent not initialized")

        status = self.agent.get_agent_status()
        return {
            "status": "success",
            "agent_status": status,
            "pipeline_id": pipeline_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def health_check(self) -> Dict[str, Any]:
        health_status = {
            "status": "healthy" if self.initialized else "unhealthy",
            "components": {
                "imports": True,
                "monitoring": self.monitoring is not None,
                "kpi_tracker": self.kpi_tracker is not None,
                "agent": self.agent is not None,
                "xray_tracing": XRAY_ENABLED,
            },
            "aws_config": {
                "data_bucket": self.aws_config["data_bucket"],
                "model_bucket": self.aws_config["model_bucket"],
                "region": self.aws_config["region"],
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        return health_status

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _publish_metrics(self, result: Dict[str, Any]) -> None:
        if not self.monitoring:
            return

        try:
            self.monitoring.publish_custom_metric(  # type: ignore[union-attr]
                metric_name="PipelineSuccess",
                value=1,
                unit="Count",
                dimensions={"Environment": "development"},
            )

            if "execution_time" in result:
                self.monitoring.publish_custom_metric(  # type: ignore[union-attr]
                    metric_name="PipelineExecutionTime",
                    value=result["execution_time"],
                    unit="Seconds",
                    dimensions={"Environment": "development"},
                )

            performance = result.get("model_performance") or {}
            if isinstance(performance, dict):
                for metric_name, value in performance.items():
                    if isinstance(value, (int, float)):
                        self.monitoring.publish_custom_metric(  # type: ignore[union-attr]
                            metric_name=f"ModelPerformance_{metric_name}",
                            value=value,
                            unit="None",
                            dimensions={"Environment": "development"},
                        )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to publish metrics: %s", exc)

    def _track_kpis(self, result: Dict[str, Any]) -> None:
        if not self.kpi_tracker:
            return

        try:
            kpis = self.kpi_tracker.calculate_kpis(  # type: ignore[union-attr]
                execution_result=result,
                timestamp=datetime.utcnow(),
            )
            logger.info("KPIs tracked: %s", kpis)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to track KPIs: %s", exc)

    def _get_dashboard_url(self) -> str:
        region = self.aws_config["region"]
        return f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name=ADPA-PROD-Dashboard"

    @staticmethod
    def _failure_response(message: str, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = {
            "status": "failed",
            "error": message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if extra:
            payload.update(extra)
        return payload