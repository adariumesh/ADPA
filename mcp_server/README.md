# ADPA Project Manager MCP Server

An intelligent MCP server that guides ADPA project completion by providing context, credentials, and implementation guidance.

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure in Claude:
```json
{
  "mcpServers": {
    "adpa-project-manager": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/home/user/ADPA"
    }
  }
}
```

3. Start using with Claude:
```
"What's the current project status?"
"What should I work on next?"
"Show me the pattern for implementing a pipeline step"
```

## Features

- **Progress Tracking**: Knows what's done and what's remaining
- **Dependency Management**: Suggests tasks in the right order
- **Code Patterns**: Provides templates and conventions
- **Implementation Guidance**: Detailed help for each feature
- **AWS Configuration**: Manages credential requirements
- **Completion Estimation**: Tracks progress toward 100%

## Available Tools

- `get_project_status`: Check implementation status
- `get_next_task`: Get recommended next task
- `update_task_status`: Mark tasks complete
- `get_aws_credentials`: AWS credential info
- `get_implementation_guidance`: Feature implementation help
- `get_code_patterns`: Code templates and patterns

## Documentation

See [.claude/MCP_SETUP.md](../.claude/MCP_SETUP.md) for complete setup and usage guide.

## Architecture

```
mcp_server/
├── server.py          # MCP server implementation
├── __init__.py        # Package init
└── requirements.txt   # Dependencies

.claude/
├── project_memory.md       # Project context and status
├── implementation_plan.md  # Detailed roadmap
├── progress.json          # Task tracking (auto-generated)
└── MCP_SETUP.md          # Setup guide
```

## How It Works

1. **Context Awareness**: Reads project_memory.md and implementation_plan.md
2. **State Tracking**: Maintains progress.json with task status
3. **Smart Recommendations**: Analyzes dependencies to suggest next steps
4. **Pattern Matching**: Provides code patterns from existing files
5. **Guided Implementation**: Offers step-by-step guidance for each feature

## Example Session

```
User: "What should I work on next?"

MCP Server → get_next_task()
→ Returns: "feature_engineering_step" (Priority: 10, Time: 2-3 days)
→ Guidance: "Implement categorical encoding, feature scaling, and selection"

User: "Show me the pattern for a pipeline step"

MCP Server → get_code_patterns(pattern_type="pipeline_step")
→ Returns: Template with PipelineStep interface
→ Example: src/pipeline/training/trainer.py

User: [implements feature]

User: "I've completed feature engineering"

MCP Server → update_task_status(task_id="feature_engineering_step", status="completed")
→ Progress updated: 65% → 70%
→ Next task available: "model_evaluation_step"
```

## Benefits

1. **Never Lose Context**: Resume work anytime without forgetting where you were
2. **Avoid Wrong Order**: Dependencies prevent implementing features too early
3. **Consistent Code**: Patterns ensure all code follows same style
4. **Faster Development**: Guidance and templates speed up implementation
5. **Track Progress**: Always know how close you are to 100%

## Extending

Add custom tools by modifying `server.py`:

```python
@app.call_tool()
async def call_tool(name: str, arguments: Any):
    if name == "your_custom_tool":
        # Your logic
        return [TextContent(type="text", text=result)]
```

## License

MIT License - Part of the ADPA project
