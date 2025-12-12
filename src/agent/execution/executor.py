"""Step execution engine for ADPA pipelines.

This module provides the `StepExecutor`, a lightweight orchestration layer that
can transform planner outputs (step definitions) into executable pipeline runs
with intelligent retry logic, critical-step enforcement, and execution history
tracking. It is intentionally framework-agnostic so it can be reused by the
Lambda handler, local demos, and automated tests alike.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import pandas as pd

from ..core.interfaces import ExecutionResult, PipelineConfig, PipelineStep, StepStatus
from ..planning.pipeline_steps import StepFactory

StepDefinition = Dict[str, Any]
StepsInput = Sequence[Union[PipelineStep, StepDefinition]]


@dataclass
class _StepEntry:
    """Internal representation of a pipeline step to execute."""

    instance: PipelineStep
    critical: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return getattr(self.instance, "name", self.metadata.get("name", "unknown_step"))


class StepExecutor:
    """Executes planner-produced pipeline steps with retries and tracking."""

    def __init__(
        self,
        *,
        max_retries: int = 2,
        retry_backoff_seconds: float = 2.0,
        retry_backoff_multiplier: float = 2.0,
        retry_non_critical: bool = False,
        important_artifact_keys: Optional[Iterable[str]] = None,
    ) -> None:
        """Initialize the executor.

        Args:
            max_retries: Maximum retry attempts per step (in addition to the first try).
            retry_backoff_seconds: Initial backoff wait between retries.
            retry_backoff_multiplier: Multiplier applied to the backoff after each retry.
            retry_non_critical: Whether to retry non-critical steps as well.
            important_artifact_keys: Keys that should be lifted into the shared context
                whenever a step returns them in its artifacts or step_output. If not
                provided, a sensible default list is used.
        """

        self.logger = logging.getLogger(__name__)
        self.max_retries = max(0, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.retry_backoff_multiplier = max(1.0, retry_backoff_multiplier)
        self.retry_non_critical = retry_non_critical
        self.important_artifact_keys = list(
            important_artifact_keys
            or (
                "model",
                "test_data",
                "train_data",
                "feature_columns",
                "transformers",
                "encoders",
                "scaler",
                "selected_features",
            )
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def execute_pipeline(
        self,
        steps: StepsInput,
        data: pd.DataFrame,
        config: Optional[Union[PipelineConfig, Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Execute a list of pipeline steps and return an aggregated result."""

        if data is None:
            raise ValueError("Pipeline data is required")
        if not steps:
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=data,
                artifacts={"execution_history": [], "context": context or {}},
                metrics={"total_steps": 0, "successful_steps": 0, "failed_steps": 0},
                execution_time=0.0,
            )

        normalized_steps = self._normalize_steps(steps)
        config_dict = self._config_to_dict(config)
        shared_context: Dict[str, Any] = {**(context or {})}
        shared_context.setdefault("config", config_dict)
        shared_context.setdefault("target_column", config_dict.get("target_column"))

        current_data = data.copy() if isinstance(data, pd.DataFrame) else data
        execution_history: List[Dict[str, Any]] = []
        pipeline_start = time.time()
        successful_steps = 0
        failed_steps = 0
        aggregate_errors: List[str] = []

        for order, step_entry in enumerate(normalized_steps, start=1):
            step_start = time.time()
            result, attempts = self._execute_step_with_retry(
                step_entry=step_entry,
                data=current_data,
                config=config_dict,
                context=shared_context,
            )
            duration = time.time() - step_start

            history_entry = {
                "order": order,
                "name": step_entry.name,
                "critical": step_entry.critical,
                "attempts": attempts,
                "status": result.status.value if result else StepStatus.FAILED.value,
                "execution_time": result.execution_time if result else None,
                "wall_clock_time": duration,
                "metrics": result.metrics if result else None,
                "errors": result.errors if result else None,
            }
            execution_history.append(history_entry)

            if result.status == StepStatus.COMPLETED:
                successful_steps += 1
                current_data = result.data if result.data is not None else current_data
                self._update_context_from_result(shared_context, result)
                continue

            failed_steps += 1
            self.logger.warning(
                "Step '%s' ended with status %s (critical=%s)",
                step_entry.name,
                result.status.value,
                step_entry.critical,
            )
            if result.errors:
                aggregate_errors.extend(result.errors)

            if step_entry.critical:
                overall_duration = time.time() - pipeline_start
                return ExecutionResult(
                    status=StepStatus.FAILED,
                    data=current_data if isinstance(current_data, pd.DataFrame) else None,
                    artifacts={
                        "execution_history": execution_history,
                        "context": shared_context,
                        "failed_step": step_entry.name,
                    },
                    metrics={
                        "total_steps": len(normalized_steps),
                        "successful_steps": successful_steps,
                        "failed_steps": failed_steps,
                        "execution_time": overall_duration,
                    },
                    errors=aggregate_errors or result.errors,
                    execution_time=overall_duration,
                )

            # Non-critical failure -> continue pipeline while keeping data/context
            self.logger.info("Continuing despite non-critical failure in %s", step_entry.name)

        overall_duration = time.time() - pipeline_start
        overall_status = StepStatus.COMPLETED if failed_steps == 0 else StepStatus.FAILED
        errors = aggregate_errors or None

        return ExecutionResult(
            status=overall_status,
            data=current_data if isinstance(current_data, pd.DataFrame) else None,
            artifacts={
                "execution_history": execution_history,
                "context": shared_context,
            },
            metrics={
                "total_steps": len(normalized_steps),
                "successful_steps": successful_steps,
                "failed_steps": failed_steps,
                "execution_time": overall_duration,
            },
            errors=errors,
            execution_time=overall_duration,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _normalize_steps(self, steps: StepsInput) -> List[_StepEntry]:
        normalized: List[_StepEntry] = []
        for raw_step in steps:
            if isinstance(raw_step, PipelineStep):
                metadata = getattr(raw_step, "metadata", {})
                critical = bool(getattr(raw_step, "critical", metadata.get("critical", True)))
                normalized.append(_StepEntry(instance=raw_step, critical=critical, metadata=metadata))
                continue

            if isinstance(raw_step, dict):
                instance = StepFactory.create_step(raw_step)
                normalized.append(
                    _StepEntry(
                        instance=instance,
                        critical=bool(raw_step.get("critical", True)),
                        metadata=raw_step,
                    )
                )
                continue

            raise TypeError(
                "Steps must be PipelineStep instances or step definition dictionaries"
            )
        return normalized

    def _config_to_dict(self, config: Optional[Union[PipelineConfig, Dict[str, Any]]]) -> Dict[str, Any]:
        if config is None:
            return {}
        if isinstance(config, dict):
            return dict(config)
        if is_dataclass(config):
            return asdict(config)  # type: ignore[arg-type]
        raise TypeError("config must be a PipelineConfig dataclass or a dict")

    def _execute_step_with_retry(
        self,
        *,
        step_entry: _StepEntry,
        data: Any,
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[ExecutionResult, int]:
        attempts = 0
        backoff = self.retry_backoff_seconds
        last_result: Optional[ExecutionResult] = None

        while True:
            attempts += 1
            try:
                result = step_entry.instance.execute(data=data, config=config, context=context)
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("Step '%s' raised an exception", step_entry.name)
                result = ExecutionResult(status=StepStatus.FAILED, errors=[str(exc)])

            last_result = result

            if result.status == StepStatus.COMPLETED or not self._should_retry(
                step_entry, attempts, result
            ):
                return result, attempts

            self.logger.info(
                "Retrying step '%s' (attempt %s of %s)",
                step_entry.name,
                attempts,
                self.max_retries + 1,
            )
            if backoff > 0:
                time.sleep(backoff)
                backoff *= self.retry_backoff_multiplier

        # Should never reach here
        assert last_result is not None
        return last_result, attempts

    def _should_retry(
        self,
        step_entry: _StepEntry,
        attempts: int,
        result: ExecutionResult,
    ) -> bool:
        if attempts > self.max_retries + 1:
            return False
        if result.status == StepStatus.COMPLETED:
            return False
        if not step_entry.critical and not self.retry_non_critical:
            return False
        return True

    def _update_context_from_result(self, context: Dict[str, Any], result: ExecutionResult) -> None:
        if result.artifacts:
            for key in self.important_artifact_keys:
                if key in result.artifacts:
                    context[key] = result.artifacts[key]
        if result.step_output:
            for key, value in result.step_output.items():
                if key in self.important_artifact_keys or key.endswith("_data"):
                    context[key] = value
        # Metrics like target_column shouldn't change automatically, but if a
        # step explicitly provides one we respect it.
        if result.metrics and "target_column" in result.metrics:
            context["target_column"] = result.metrics["target_column"]
