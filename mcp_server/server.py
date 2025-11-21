#!/usr/bin/env python3
"""
ADPA Project Manager MCP Server Implementation

This server helps manage the ADPA project completion by:
1. Tracking implementation status
2. Providing AWS credentials securely
3. Guiding feature implementation
4. Validating code against standards
5. Suggesting next tasks based on dependencies
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("adpa-mcp-server")


class ADPAProjectManager:
    """Manages ADPA project state and provides guidance."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.memory_file = project_root / ".claude" / "project_memory.md"
        self.plan_file = project_root / ".claude" / "implementation_plan.md"
        self.progress_file = project_root / ".claude" / "progress.json"
        self.credentials_file = project_root / ".claude" / "credentials.encrypted"

        # Load project state
        self.load_progress()

    def load_progress(self):
        """Load current project progress."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                self.progress = json.load(f)
        else:
            self.progress = {
                "tasks": {},
                "completed_features": [],
                "current_phase": 1,
                "last_updated": None
            }

    def save_progress(self):
        """Save current project progress."""
        self.progress["last_updated"] = datetime.now().isoformat()
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)

    def get_project_status(self, component: str = "all") -> Dict[str, Any]:
        """Get current implementation status."""
        status = {
            "overall_completion": self._calculate_completion(),
            "current_phase": self.progress.get("current_phase", 1),
            "completed_features": self.progress.get("completed_features", []),
            "last_updated": self.progress.get("last_updated")
        }

        if component != "all":
            status["component_details"] = self._get_component_status(component)

        return status

    def _calculate_completion(self) -> float:
        """Calculate overall project completion percentage."""
        total_tasks = len(self._get_all_tasks())
        completed_tasks = len([t for t in self.progress.get("tasks", {}).values()
                              if t.get("status") == "completed"])
        return (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0

    def _get_all_tasks(self) -> List[str]:
        """Get list of all tasks from implementation plan."""
        return [
            "feature_engineering_step",
            "model_evaluation_step",
            "reporting_step",
            "memory_system",
            "monitoring_cloudwatch",
            "monitoring_xray",
            "local_baseline",
            "api_endpoints",
            "authentication",
            "unit_tests",
            "integration_tests",
            "documentation"
        ]

    def _get_component_status(self, component: str) -> Dict[str, Any]:
        """Get detailed status for a specific component."""
        component_tasks = {
            "core_agent": ["feature_engineering_step", "model_evaluation_step", "reporting_step"],
            "pipeline": ["feature_engineering_step", "model_evaluation_step", "reporting_step"],
            "aws_integration": ["monitoring_cloudwatch", "monitoring_xray"],
            "memory_system": ["memory_system"],
            "monitoring": ["monitoring_cloudwatch", "monitoring_xray"],
            "api": ["api_endpoints", "authentication"],
            "testing": ["unit_tests", "integration_tests"]
        }

        tasks = component_tasks.get(component, [])
        task_status = {task: self.progress.get("tasks", {}).get(task, {"status": "not_started"})
                      for task in tasks}

        return {
            "component": component,
            "tasks": task_status,
            "completion": self._calculate_component_completion(tasks)
        }

    def _calculate_component_completion(self, tasks: List[str]) -> float:
        """Calculate completion percentage for a component."""
        if not tasks:
            return 0.0
        completed = len([t for t in tasks
                        if self.progress.get("tasks", {}).get(t, {}).get("status") == "completed"])
        return (completed / len(tasks)) * 100

    def get_next_task(self, current_context: Optional[str] = None) -> Dict[str, Any]:
        """Get the next recommended task based on dependencies."""
        # Define task dependencies
        dependencies = {
            "feature_engineering_step": [],
            "model_evaluation_step": ["feature_engineering_step"],
            "reporting_step": ["model_evaluation_step"],
            "memory_system": ["reporting_step"],
            "monitoring_cloudwatch": [],
            "monitoring_xray": ["monitoring_cloudwatch"],
            "local_baseline": ["reporting_step"],
            "api_endpoints": ["reporting_step", "memory_system"],
            "authentication": ["api_endpoints"],
            "unit_tests": ["feature_engineering_step", "model_evaluation_step", "reporting_step"],
            "integration_tests": ["unit_tests"],
            "documentation": ["integration_tests"]
        }

        # Find tasks that are not started and have all dependencies met
        available_tasks = []
        for task, deps in dependencies.items():
            task_status = self.progress.get("tasks", {}).get(task, {}).get("status", "not_started")

            if task_status not in ["completed", "in_progress"]:
                # Check if all dependencies are completed
                deps_met = all(
                    self.progress.get("tasks", {}).get(dep, {}).get("status") == "completed"
                    for dep in deps
                )

                if deps_met:
                    priority = self._get_task_priority(task)
                    available_tasks.append({
                        "task_id": task,
                        "priority": priority,
                        "dependencies_met": True,
                        "estimated_time": self._get_task_estimate(task)
                    })

        # Sort by priority
        available_tasks.sort(key=lambda x: x["priority"], reverse=True)

        if available_tasks:
            next_task = available_tasks[0]
            next_task["guidance"] = self._get_task_guidance(next_task["task_id"])
            return next_task
        else:
            return {"message": "All tasks completed or in progress!"}

    def _get_task_priority(self, task: str) -> int:
        """Get priority for a task (higher = more important)."""
        priority_map = {
            "feature_engineering_step": 10,
            "model_evaluation_step": 9,
            "reporting_step": 8,
            "memory_system": 7,
            "unit_tests": 6,
            "monitoring_cloudwatch": 5,
            "local_baseline": 4,
            "monitoring_xray": 3,
            "api_endpoints": 2,
            "authentication": 1,
            "integration_tests": 1,
            "documentation": 1
        }
        return priority_map.get(task, 0)

    def _get_task_estimate(self, task: str) -> str:
        """Get time estimate for a task."""
        estimates = {
            "feature_engineering_step": "2-3 days",
            "model_evaluation_step": "2-3 days",
            "reporting_step": "2-3 days",
            "memory_system": "3-4 days",
            "monitoring_cloudwatch": "2-3 days",
            "monitoring_xray": "1-2 days",
            "local_baseline": "4-5 days",
            "api_endpoints": "3-4 days",
            "authentication": "2 days",
            "unit_tests": "4-5 days",
            "integration_tests": "2-3 days",
            "documentation": "3-4 days"
        }
        return estimates.get(task, "Unknown")

    def _get_task_guidance(self, task: str) -> str:
        """Get implementation guidance for a task."""
        guidance_map = {
            "feature_engineering_step": "Implement categorical encoding, feature scaling, and selection. Follow the pattern in data_loader.py and cleaner.py.",
            "model_evaluation_step": "Calculate metrics based on problem type. Generate plots and extract feature importance.",
            "reporting_step": "Create HTML reports with data profiling, model performance, and recommendations.",
            "memory_system": "Implement SQLite storage for execution history and strategy learning.",
            "monitoring_cloudwatch": "Integrate CloudWatch for logs and custom metrics.",
            "local_baseline": "Implement local sklearn-based pipeline for comparison.",
            "api_endpoints": "Use FastAPI to create REST endpoints for pipeline management.",
            "unit_tests": "Create pytest tests for all core components with >80% coverage.",
        }
        return guidance_map.get(task, "No guidance available.")

    def update_task_status(self, task_id: str, status: str, notes: Optional[str] = None):
        """Update task status."""
        if "tasks" not in self.progress:
            self.progress["tasks"] = {}

        self.progress["tasks"][task_id] = {
            "status": status,
            "updated_at": datetime.now().isoformat(),
            "notes": notes
        }

        if status == "completed" and task_id not in self.progress.get("completed_features", []):
            if "completed_features" not in self.progress:
                self.progress["completed_features"] = []
            self.progress["completed_features"].append(task_id)

        self.save_progress()

    def get_aws_credentials(self, service: str = "all") -> Dict[str, str]:
        """Get AWS credentials (placeholder - implement secure storage)."""
        # In production, this would decrypt credentials from secure storage
        return {
            "message": "AWS credentials should be provided via environment variables or AWS credentials file",
            "required_env_vars": [
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_DEFAULT_REGION",
                "ADPA_S3_BUCKET",
                "ADPA_IAM_ROLE_ARN"
            ],
            "service": service
        }

    def get_implementation_guidance(self, feature: str) -> Dict[str, Any]:
        """Get detailed implementation guidance for a feature."""
        # Read from implementation plan
        if self.plan_file.exists():
            with open(self.plan_file, 'r') as f:
                plan_content = f.read()

            # Extract relevant section (simplified)
            return {
                "feature": feature,
                "guidance": f"See implementation plan for detailed guidance on {feature}",
                "plan_file": str(self.plan_file),
                "related_files": self._get_related_files(feature)
            }
        else:
            return {"error": "Implementation plan not found"}

    def _get_related_files(self, feature: str) -> List[str]:
        """Get list of related files for a feature."""
        file_map = {
            "feature_engineering": ["src/pipeline/etl/feature_engineer.py"],
            "model_evaluation": ["src/pipeline/evaluation/evaluator.py"],
            "reporting": ["src/pipeline/evaluation/reporter.py"],
            "memory_system": ["src/agent/memory/manager.py"],
            "monitoring": ["src/monitoring/metrics/", "src/monitoring/logging/"],
            "api": ["src/api/endpoints/", "src/api/main.py"]
        }
        return file_map.get(feature, [])

    def get_code_patterns(self, pattern_type: str) -> Dict[str, Any]:
        """Get code patterns used in the project."""
        patterns = {
            "pipeline_step": {
                "description": "Pattern for implementing a pipeline step",
                "example_file": "src/pipeline/training/trainer.py",
                "template": """
class YourStep(PipelineStep):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(PipelineStepType.YOUR_TYPE, "step_name")
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

    def execute(self, data: pd.DataFrame, config: Dict[str, Any]) -> ExecutionResult:
        try:
            # Your implementation
            return ExecutionResult(
                status=StepStatus.COMPLETED,
                data=processed_data,
                metrics={...},
                artifacts={...}
            )
        except Exception as e:
            return ExecutionResult(
                status=StepStatus.FAILED,
                errors=[str(e)]
            )

    def validate_inputs(self, data: pd.DataFrame, config: Dict[str, Any]) -> bool:
        # Validation logic
        return True
"""
            },
            "aws_client": {
                "description": "Pattern for AWS service client",
                "example_file": "src/aws/sagemaker/client.py",
                "key_points": [
                    "Use boto3 client",
                    "Handle ClientError specifically",
                    "Return ExecutionResult with status",
                    "Include console URLs in artifacts",
                    "Log all operations"
                ]
            },
            "error_handling": {
                "description": "Error handling pattern",
                "pattern": """
try:
    result = operation()
    return ExecutionResult(status=StepStatus.COMPLETED, ...)
except ClientError as e:
    error_msg = f"AWS Error: {e.response['Error']['Message']}"
    logger.error(error_msg)
    return ExecutionResult(status=StepStatus.FAILED, errors=[error_msg])
except Exception as e:
    error_msg = f"Unexpected error: {str(e)}"
    logger.error(error_msg)
    return ExecutionResult(status=StepStatus.FAILED, errors=[error_msg])
"""
            }
        }

        return patterns.get(pattern_type, {"error": "Pattern type not found"})


# Create MCP server instance
app = Server("adpa-project-manager")
project_manager = ADPAProjectManager(Path(__file__).parent.parent)


@app.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="adpa://project/memory",
            name="Project Memory",
            mimeType="text/markdown",
            description="Complete project context and status"
        ),
        Resource(
            uri="adpa://project/implementation-plan",
            name="Implementation Plan",
            mimeType="text/markdown",
            description="Detailed implementation plan"
        ),
        Resource(
            uri="adpa://project/status",
            name="Current Status",
            mimeType="application/json",
            description="Current project status and progress"
        )
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource."""
    if uri == "adpa://project/memory":
        if project_manager.memory_file.exists():
            return project_manager.memory_file.read_text()
        return "Project memory file not found"

    elif uri == "adpa://project/implementation-plan":
        if project_manager.plan_file.exists():
            return project_manager.plan_file.read_text()
        return "Implementation plan not found"

    elif uri == "adpa://project/status":
        status = project_manager.get_project_status()
        return json.dumps(status, indent=2)

    return "Resource not found"


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_project_status",
            description="Get current implementation status of ADPA project",
            inputSchema={
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "description": "Specific component to check",
                        "enum": ["all", "core_agent", "pipeline", "aws_integration", "memory_system", "monitoring", "api", "testing"]
                    }
                }
            }
        ),
        Tool(
            name="get_next_task",
            description="Get the next recommended task",
            inputSchema={
                "type": "object",
                "properties": {
                    "current_context": {
                        "type": "string",
                        "description": "Current work context"
                    }
                }
            }
        ),
        Tool(
            name="update_task_status",
            description="Update task status",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["not_started", "in_progress", "completed", "blocked"]},
                    "notes": {"type": "string"}
                },
                "required": ["task_id", "status"]
            }
        ),
        Tool(
            name="get_aws_credentials",
            description="Get AWS credentials information",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {"type": "string"}
                },
                "required": ["service"]
            }
        ),
        Tool(
            name="get_implementation_guidance",
            description="Get implementation guidance for a feature",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature": {"type": "string"}
                },
                "required": ["feature"]
            }
        ),
        Tool(
            name="get_code_patterns",
            description="Get code patterns and conventions",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern_type": {
                        "type": "string",
                        "enum": ["pipeline_step", "aws_client", "error_handling", "testing", "interfaces"]
                    }
                },
                "required": ["pattern_type"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_project_status":
            component = arguments.get("component", "all")
            status = project_manager.get_project_status(component)
            return [TextContent(
                type="text",
                text=json.dumps(status, indent=2)
            )]

        elif name == "get_next_task":
            current_context = arguments.get("current_context")
            next_task = project_manager.get_next_task(current_context)
            return [TextContent(
                type="text",
                text=json.dumps(next_task, indent=2)
            )]

        elif name == "update_task_status":
            task_id = arguments["task_id"]
            status = arguments["status"]
            notes = arguments.get("notes")
            project_manager.update_task_status(task_id, status, notes)
            return [TextContent(
                type="text",
                text=f"Task {task_id} updated to {status}"
            )]

        elif name == "get_aws_credentials":
            service = arguments["service"]
            creds = project_manager.get_aws_credentials(service)
            return [TextContent(
                type="text",
                text=json.dumps(creds, indent=2)
            )]

        elif name == "get_implementation_guidance":
            feature = arguments["feature"]
            guidance = project_manager.get_implementation_guidance(feature)
            return [TextContent(
                type="text",
                text=json.dumps(guidance, indent=2)
            )]

        elif name == "get_code_patterns":
            pattern_type = arguments["pattern_type"]
            patterns = project_manager.get_code_patterns(pattern_type)
            return [TextContent(
                type="text",
                text=json.dumps(patterns, indent=2)
            )]

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
