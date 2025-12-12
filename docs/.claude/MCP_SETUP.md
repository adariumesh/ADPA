# ADPA MCP Server Setup Guide

This guide explains how to set up and use the ADPA Project Manager MCP server to help complete the project to 100%.

## What is the MCP Server?

The ADPA MCP (Model Context Protocol) server acts as an intelligent project manager that:
- **Maintains context** about what's completed and what's missing
- **Provides guidance** on what to implement next
- **Tracks dependencies** to ensure features are built in the right order
- **Offers code patterns** to maintain consistency
- **Manages credentials** (AWS configuration) securely
- **Monitors progress** and estimates completion

## Installation

### 1. Install MCP SDK

```bash
pip install mcp
```

### 2. Install MCP Server Dependencies

```bash
cd /home/user/ADPA
pip install -r mcp_server/requirements.txt
```

### 3. Configure Claude Desktop (or Claude Code)

Add the MCP server to your Claude configuration file:

**For Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json` on Mac):

```json
{
  "mcpServers": {
    "adpa-project-manager": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/home/user/ADPA",
      "env": {
        "PYTHONPATH": "/home/user/ADPA"
      }
    }
  }
}
```

**For Claude Code** (`.claude/config.json` in your project):

```json
{
  "mcp": {
    "servers": {
      "adpa-project-manager": {
        "command": "python",
        "args": ["-m", "mcp_server.server"],
        "env": {
          "PYTHONPATH": "${workspaceFolder}"
        }
      }
    }
  }
}
```

### 4. Set Up AWS Credentials

Create a `.env` file in the project root:

```bash
# /home/user/ADPA/.env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
ADPA_S3_BUCKET=your-bucket-name
ADPA_IAM_ROLE_ARN=arn:aws:iam::123456789012:role/ADPASageMakerRole
```

**Important:** Add `.env` to `.gitignore` to keep credentials secure!

## Using the MCP Server

### Available Tools

The MCP server provides these tools that Claude can use:

#### 1. `get_project_status`
Get current implementation status

```
Example: "What's the current status of the project?"
Claude will call: get_project_status(component="all")
```

#### 2. `get_next_task`
Get the next recommended task based on dependencies

```
Example: "What should I work on next?"
Claude will call: get_next_task()
Returns: The highest priority task with unmet dependencies
```

#### 3. `update_task_status`
Update task completion status

```
Example: "Mark feature_engineering_step as completed"
Claude will call: update_task_status(task_id="feature_engineering_step", status="completed")
```

#### 4. `get_aws_credentials`
Get information about AWS credential requirements

```
Example: "What AWS credentials do I need?"
Claude will call: get_aws_credentials(service="all")
```

#### 5. `get_implementation_guidance`
Get detailed implementation guidance for a feature

```
Example: "How should I implement the memory system?"
Claude will call: get_implementation_guidance(feature="memory_system")
```

#### 6. `get_code_patterns`
Get code patterns and conventions used in the project

```
Example: "Show me the pattern for creating a pipeline step"
Claude will call: get_code_patterns(pattern_type="pipeline_step")
```

### Available Resources

The MCP server provides access to these resources:

- **Project Memory** (`adpa://project/memory`): Complete project context
- **Implementation Plan** (`adpa://project/implementation-plan`): Detailed roadmap
- **Current Status** (`adpa://project/status`): Real-time progress tracking

### Workflow Examples

#### Example 1: Starting Fresh

```
You: "I want to continue working on ADPA. What's the status?"

Claude (using MCP):
- Calls get_project_status()
- Shows you that you're at 60% completion
- Lists completed and remaining features

You: "What should I work on next?"

Claude (using MCP):
- Calls get_next_task()
- Recommends: "feature_engineering_step" (highest priority, no dependencies)
- Provides estimated time: 2-3 days
- Shows guidance: "Implement categorical encoding, feature scaling, and selection"

You: "Show me how to implement a pipeline step"

Claude (using MCP):
- Calls get_code_patterns(pattern_type="pipeline_step")
- Shows you the template and example files
- Helps you implement following the existing pattern
```

#### Example 2: Completing a Feature

```
You: "I've finished implementing the feature engineering step. Here's my code..."

Claude (using MCP):
- Reviews your code against project standards
- Validates it follows the pattern
- Calls update_task_status(task_id="feature_engineering_step", status="completed")
- Calls get_next_task() to suggest what's next
- Recommends: "model_evaluation_step" (dependencies now met)
```

#### Example 3: Getting Unstuck

```
You: "I'm stuck on the AWS SageMaker integration"

Claude (using MCP):
- Calls get_implementation_guidance(feature="training")
- Shows you related files (src/aws/sagemaker/client.py)
- Calls get_code_patterns(pattern_type="aws_client")
- Shows AWS client pattern
- Helps you debug based on existing working examples
```

#### Example 4: AWS Credential Setup

```
You: "What AWS credentials do I need to set up?"

Claude (using MCP):
- Calls get_aws_credentials(service="all")
- Lists required environment variables
- Shows you where to put them (.env file)
- Helps you configure IAM roles and permissions
```

## How It Helps Achieve 100% Completion

### 1. Dependency Management
The MCP server tracks dependencies between tasks. It won't suggest implementing the API before the core pipeline is done. This prevents wasted effort and ensures a solid foundation.

### 2. Context Persistence
Even if you stop working for days, the MCP server remembers:
- What you've completed
- What you were working on
- What needs to be done next
- Patterns and conventions used

### 3. Consistent Code Quality
By providing code patterns and templates, the MCP server ensures all new code:
- Follows existing conventions
- Uses the same error handling patterns
- Implements proper logging
- Returns consistent result types

### 4. Guided Implementation
For each feature, the MCP server provides:
- Detailed requirements
- Implementation approach
- Related files to reference
- Testing strategy
- Estimated time

### 5. Progress Tracking
The MCP server automatically:
- Tracks completion percentage
- Updates when features are done
- Suggests next steps
- Estimates remaining work

## Project Phases (Tracked by MCP)

The MCP server organizes work into phases:

### Phase 1: Core Pipeline (Week 1-2)
- Feature Engineering
- Model Evaluation
- Reporting

### Phase 2: Learning & Optimization (Week 3)
- Memory System
- Monitoring Infrastructure

### Phase 3: Baseline & Comparison (Week 4)
- Local Pipeline Implementation
- Performance Comparison

### Phase 4: API & Interface (Week 5)
- REST API
- Authentication

### Phase 5: Testing & Documentation (Week 6)
- Comprehensive Tests
- Documentation

## Best Practices

### 1. Always Start Sessions with Status Check
```
"What's the current project status?"
```
This reminds you and Claude where things stand.

### 2. Follow Recommended Task Order
The MCP server suggests tasks based on dependencies. Following this order prevents issues.

### 3. Update Status After Completing Work
```
"I've completed the feature engineering step"
```
This keeps the MCP server's tracking accurate.

### 4. Ask for Patterns Before Implementing
```
"Show me the pattern for implementing X"
```
This ensures consistency with existing code.

### 5. Check Guidance Before Starting
```
"What's the implementation guidance for X?"
```
This gives you a clear roadmap before coding.

## Troubleshooting

### MCP Server Not Responding
1. Check that Python path is correct in config
2. Verify mcp package is installed: `pip list | grep mcp`
3. Check server logs for errors

### "Tool Not Found" Errors
1. Restart Claude Desktop/Code
2. Verify config file syntax
3. Check that server.py is executable

### Progress Not Saving
1. Check .claude/progress.json file permissions
2. Ensure directory exists: `mkdir -p .claude`
3. Verify no file lock issues

## Advanced Usage

### Custom Credential Management

For production use, implement encrypted credential storage in the MCP server:

```python
# mcp_server/credentials.py
from cryptography.fernet import Fernet
import json

class CredentialManager:
    def __init__(self, key_file: str):
        self.cipher = Fernet(self.load_key(key_file))

    def store_credentials(self, creds: dict):
        encrypted = self.cipher.encrypt(json.dumps(creds).encode())
        # Store encrypted credentials

    def retrieve_credentials(self, service: str):
        # Decrypt and return credentials
        pass
```

### Extending the MCP Server

Add custom tools for your workflow:

```python
@app.call_tool()
async def call_tool(name: str, arguments: Any):
    if name == "your_custom_tool":
        # Your custom logic
        return [TextContent(type="text", text=result)]
```

## Summary

The ADPA MCP server transforms Claude from a helpful assistant into a **project-aware development partner** that:
- Remembers everything about your project
- Guides you through completion systematically
- Provides credentials and configuration when needed
- Ensures code quality and consistency
- Tracks progress toward 100% completion

Just ask Claude "What should I work on next?" and let the MCP server guide you to completion!
