# Tool Development Guide

**Last updated:** 2026-01-20

This guide documents the complete workflow for developing tools in this personal assistant repository.

---

## Table of Contents
1. [Overview](#overview)
2. [Workflow: Friction → Tool](#workflow-friction--tool)
3. [Development Setup](#development-setup)
4. [Creating a New Tool](#creating-a-new-tool)
5. [Testing](#testing)
6. [Deployment](#deployment)
7. [Common Patterns](#common-patterns)

---

## Overview

### Philosophy
- **Capture friction immediately** - Don't let pain points slip away
- **v0 bias** - Ship the smallest useful version first
- **Iterate quickly** - Use auto-deployment to test in production
- **Safety by default** - Prefer read-only operations unless explicitly confirmed

### Tool Types
1. **VM MCP Tools** (`vm_server/tools/`) - Deployed to remote VM, called via MCP
2. **Local Scripts** (`scripts/`) - Run locally for analysis, capture, orchestration
3. **Calendar Hygiene** (`tools/`) - Special category for calendar management

---

## Workflow: Friction → Tool

### 1. Capture Friction

When you encounter something annoying or repetitive:

```bash
# Quick capture
python3 scripts/tool_requests.py capture "Annoyed by duplicating calendar invites"

# With details
python3 scripts/tool_requests.py capture "Annoyed by duplicating calendar invites" \
  --desired-outcome "Auto-detect and merge duplicates" \
  --frequency daily \
  --impact high \
  --domain "calendar,planning"
```

**Tip:** Lower the barrier - capture now, elaborate later.

### 2. Weekly Triage

Review and prioritize captured friction:

```bash
# Read-only triage (review + score)
python3 scripts/triage.py

# Apply triage (updates Status from 'new' → 'triaging')
python3 scripts/triage.py --apply
```

The triage script:
- Fetches all 'new' tool requests
- Scores based on impact × frequency × recency
- Recommends top candidates
- Saves report to `memory/triage/YYYY-MM-DD.md`

### 3. Generate Spec

For promising candidates, generate a detailed spec:

```bash
# From complaint string
python3 scripts/generate_tool_spec.py "Annoyed by calendar invite spam"

# From Notion page ID
python3 scripts/generate_tool_spec.py --notion-id <page_id>

# Output JSON + Markdown
python3 scripts/generate_tool_spec.py "..." --format both
```

The spec includes:
- Tool name and description
- Input parameters
- Expected output
- Success criteria
- Implementation notes

### 4. Scaffold Tool

Create the tool structure:

**For VM MCP tools:**
```bash
# Create new tool module
touch vm_server/tools/my_new_tool.py
```

**For local scripts:**
```bash
# Create new script
touch scripts/my_new_script.py
chmod +x scripts/my_new_script.py
```

### 5. Implement

Follow the patterns in existing tools (see [Common Patterns](#common-patterns) below).

**VM MCP Tool Template:**
```python
#!/usr/bin/env python3
"""
Tool: my_new_tool

Description: What this tool does

Usage:
  ./vm/mcp_curl.sh my_new_tool '{"param":"value"}'
"""

from datetime import datetime, timezone
from typing import Any, Dict

def my_new_tool(param: str) -> Dict[str, Any]:
    """
    Main tool function.
    
    Args:
        param: Description of parameter
    
    Returns:
        Standard response contract with summary, result, next_actions, errors
    """
    # Implementation here
    return {
        "summary": "Brief description of what happened",
        "result": {"key": "value"},
        "next_actions": [],
        "errors": []
    }
```

**Register in `vm_server/tools/registry.py`:**
```python
from .my_new_tool import my_new_tool

TOOLS = {
    # ... existing tools
    "my_new_tool": my_new_tool,
}
```

### 6. Test Locally (Optional)

For local testing without deploying:

```bash
# Run VM server locally
cd vm_server
python3 server.py

# In another terminal, test the tool
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"my_new_tool","arguments":{"param":"value"}}}'
```

### 7. Deploy

**Automatic deployment:**
```bash
git add vm_server/tools/my_new_tool.py vm_server/tools/registry.py
git commit -m "Add my_new_tool for X"
git push origin main
# 🚀 Auto-deploys to VM!
```

**Manual deployment:**
```bash
./vm/deploy.sh
```

### 8. Verify

```bash
# Check health
./vm/health_check.sh

# Test the tool
./vm/mcp_curl.sh my_new_tool '{"param":"value"}'

# View logs if needed
./vm/logs.sh
```

### 9. Update Status

Mark the tool request as shipped:

```bash
# Via agent
python3 scripts/agent.py "In Notion, set status shipped for 'my new tool'"  --execute

# Or manually in Notion
```

---

## Development Setup

### Prerequisites

```bash
# Verify setup
python3 scripts/verify_setup.py

# Install dependencies
pip install -r requirements.txt

# VM config (for deployment)
cp vm/config.example.sh vm/config.sh
# Edit vm/config.sh with your VM details
```

### Directory Structure

```
claude-code-personal-assistant/
├── vm_server/              # MCP server code (deployed to VM)
│   ├── server.py          # FastMCP server
│   ├── tools/             # Tool modules
│   │   ├── __init__.py
│   │   ├── registry.py    # Tool registration
│   │   ├── basic.py       # Basic tools (hello, health_check)
│   │   ├── tool_requests.py  # Tool request management
│   │   └── your_tool.py   # Your new tool
│   └── requirements.txt   # VM dependencies
├── scripts/               # Local utility scripts
│   ├── tool_requests.py   # Capture/manage friction
│   ├── triage.py          # Weekly triage
│   ├── generate_tool_spec.py  # Spec generation
│   └── agent.py           # Universal router
├── tools/                 # Special tools (calendar hygiene)
└── vm/                    # VM deployment scripts
    ├── deploy.sh          # Deploy to VM
    ├── mcp_curl.sh        # Test MCP tools
    └── health_check.sh    # Health check
```

---

## Creating a New Tool

### VM MCP Tool (Recommended for most tools)

**1. Create tool module:**

```python
# vm_server/tools/example_tool.py
#!/usr/bin/env python3
"""
Example tool that demonstrates the standard pattern.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

def example_tool(
    required_param: str,
    optional_param: str = "default"
) -> Dict[str, Any]:
    """
    Brief description of what this tool does.
    
    Args:
        required_param: Description
        optional_param: Description (default: "default")
    
    Returns:
        Standard response with summary, result, next_actions, errors
    """
    try:
        # Your implementation here
        result_data = {
            "processed": required_param,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return {
            "summary": f"Successfully processed {required_param}",
            "result": result_data,
            "next_actions": [
                "Check the result",
                "Update related systems"
            ],
            "errors": []
        }
    
    except Exception as exc:
        return {
            "summary": f"Failed to process {required_param}",
            "result": {},
            "next_actions": ["Check error details", "Retry with different parameters"],
            "errors": [str(exc)]
        }
```

**2. Register in registry:**

```python
# vm_server/tools/registry.py
from .example_tool import example_tool

TOOLS = {
    # ... existing tools
    "example_tool": example_tool,
}
```

**3. Test locally:**

```bash
# Deploy
git add vm_server/tools/example_tool.py vm_server/tools/registry.py
git commit -m "Add example_tool"
git push origin main

# Test
./vm/mcp_curl.sh example_tool '{"required_param":"test"}'
```

### Local Script

**1. Create script:**

```python
#!/usr/bin/env python3
"""
Example local script.

Usage:
    python3 scripts/example_script.py --input value
"""

import argparse
import sys
from common import print_ok, print_warn

def main() -> int:
    parser = argparse.ArgumentParser(description="Example script")
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    
    # Your logic here
    print_ok(f"Processed: {args.input}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

**2. Make executable:**

```bash
chmod +x scripts/example_script.py
```

---

## Testing

### Unit Tests (Future)

```bash
# Run tests (when implemented)
pytest tests/
```

### Manual Testing

**VM Tools:**
```bash
# Test via MCP
./vm/mcp_curl.sh tool_name '{"param":"value"}'

# Test with verbose output
./vm/mcp_curl.sh tool_name '{"param":"value"}' | jq .
```

**Local Scripts:**
```bash
# Test directly
python3 scripts/your_script.py --args

# Test with verification
python3 scripts/verify_setup.py
```

### Integration Testing

```bash
# Full workflow test
python3 scripts/tool_requests.py capture "Test entry"
python3 scripts/tool_requests.py fetch --limit 1
python3 scripts/tool_requests.py flush
```

---

## Deployment

### Automatic (Recommended)

```bash
git add .
git commit -m "Description of changes"
git push origin main
# 🚀 Deploys automatically via post-push hook
```

### Manual

```bash
# Full deployment
./vm/deploy.sh

# Restart only (no rsync)
./vm/deploy.sh --restart
```

### Verification

```bash
# Check health
./vm/health_check.sh

# View logs
./vm/logs.sh

# Check service status
./vm/status.sh

# SSH to VM (if needed)
./vm/ssh.sh
```

---

## Common Patterns

### Standard Response Contract

All tools should return:

```python
{
    "summary": "Brief human-readable summary",
    "result": {
        # Structured data
    },
    "next_actions": [
        "Suggested next step 1",
        "Suggested next step 2"
    ],
    "errors": [
        # Any error messages
    ]
}
```

### Error Handling

```python
try:
    # Main logic
    result = do_something()
    return {
        "summary": "Success message",
        "result": result,
        "next_actions": [],
        "errors": []
    }
except ValueError as exc:
    return {
        "summary": "Failed due to invalid input",
        "result": {},
        "next_actions": ["Check input format", "Retry"],
        "errors": [f"ValueError: {exc}"]
    }
except Exception as exc:
    return {
        "summary": "Unexpected error occurred",
        "result": {},
        "next_actions": ["Check logs", "Report issue"],
        "errors": [f"{type(exc).__name__}: {exc}"]
    }
```

### Environment Variables

```python
import os

# Read from environment
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable required")

# Optional with default
TIMEOUT = int(os.getenv("TIMEOUT", "30"))
```

### Configuration

```python
# Read from PERSONAL_CONTEXT.md
from pathlib import Path
import re

def read_db_id() -> str | None:
    context = Path("PERSONAL_CONTEXT.md")
    if not context.exists():
        return None
    content = context.read_text()
    match = re.search(r"Database ID.*?`([^`]+)`", content)
    return match.group(1) if match else None
```

### Webhooks (for events)

```python
import os
import requests

def send_webhook(event_type: str, data: dict) -> None:
    """Send event to webhook if configured"""
    webhook_url = os.getenv("EVENT_WEBHOOK_URL")
    if not webhook_url:
        return  # Webhook not configured, skip
    
    payload = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data
    }
    
    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception:
        pass  # Don't fail if webhook fails
```

---

## Troubleshooting

### Tool Not Found

```bash
# Check if tool is registered
./vm/mcp_curl.sh --list

# Check VM logs
./vm/logs.sh

# Re-deploy
./vm/deploy.sh
```

### Import Errors

```bash
# Check dependencies on VM
./vm/ssh.sh
source venv/bin/activate
pip list

# Update dependencies
./vm/deploy.sh  # Automatically syncs requirements.txt
```

### Auto-Deployment Not Working

```bash
# Check if vm/config.sh exists
ls -la vm/config.sh

# Check hook is executable
ls -la .git/hooks/post-push

# Test hook manually
./vm/test_hook.sh
```

### Tool Returning Errors

```bash
# View detailed logs
./vm/logs.sh --lines 100

# Test with verbose output
./vm/mcp_curl.sh tool_name '{"param":"value"}' | jq .

# SSH and debug
./vm/ssh.sh
cd /home/ubuntu/mcp-server-template/src
source venv/bin/activate
python3 -c "from tools.your_tool import your_tool; print(your_tool('test'))"
```

---

## Best Practices

1. **Start Simple** - Build the minimum viable tool first
2. **Follow Patterns** - Use existing tools as templates
3. **Document As You Go** - Add docstrings and comments
4. **Test Locally First** - When possible, test before deploying
5. **Use Auto-Deploy** - Push to main triggers deployment
6. **Monitor Logs** - Check logs after deployment
7. **Handle Errors Gracefully** - Always return structured responses
8. **Keep Secrets Safe** - Use environment variables, never commit secrets
9. **Update Tool Requests** - Mark items as shipped when done
10. **Iterate Quickly** - Ship v0, gather feedback, improve

---

## Examples

### Example 1: Simple Tool

```python
# vm_server/tools/greet.py
def greet(name: str = "friend") -> dict:
    """Simple greeting tool"""
    return {
        "summary": f"Greeted {name}",
        "result": {"greeting": f"Hello, {name}!"},
        "next_actions": [],
        "errors": []
    }
```

### Example 2: API Integration

```python
# vm_server/tools/weather.py
import os
import requests

def get_weather(city: str) -> dict:
    """Fetch weather for a city"""
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return {
            "summary": "API key not configured",
            "result": {},
            "next_actions": ["Set WEATHER_API_KEY"],
            "errors": ["Missing API key"]
        }
    
    try:
        url = f"https://api.weather.com/v1/weather?city={city}&key={api_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "summary": f"Weather in {city}: {data['temp']}°C",
            "result": data,
            "next_actions": [],
            "errors": []
        }
    except Exception as exc:
        return {
            "summary": f"Failed to fetch weather for {city}",
            "result": {},
            "next_actions": ["Check city name", "Verify API key"],
            "errors": [str(exc)]
        }
```

### Example 3: Database Query

```python
# vm_server/tools/query_notion.py
import os
from notion_client import Client

def query_tasks(status: str = "Not started") -> dict:
    """Query tasks from Notion"""
    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("TASKS_DB_ID")
    
    if not token or not db_id:
        return {
            "summary": "Configuration missing",
            "result": {},
            "next_actions": ["Set NOTION_TOKEN", "Set TASKS_DB_ID"],
            "errors": ["Missing credentials"]
        }
    
    try:
        notion = Client(auth=token)
        results = notion.databases.query(
            database_id=db_id,
            filter={
                "property": "Status",
                "select": {"equals": status}
            }
        )
        
        tasks = [
            {
                "title": page["properties"]["Name"]["title"][0]["plain_text"],
                "id": page["id"]
            }
            for page in results["results"]
        ]
        
        return {
            "summary": f"Found {len(tasks)} tasks with status '{status}'",
            "result": {"tasks": tasks, "count": len(tasks)},
            "next_actions": [],
            "errors": []
        }
    except Exception as exc:
        return {
            "summary": "Failed to query Notion",
            "result": {},
            "next_actions": ["Check credentials", "Verify database ID"],
            "errors": [str(exc)]
        }
```

---

## Resources

- **AGENT_GUIDE.md** - Agent instructions and workflows
- **PERSONAL_CONTEXT.md** - Database IDs and configuration
- **vm/README.md** - VM deployment documentation
- **SETUP_CODEX.md** - Setup instructions

---

**Happy building! 🛠️**
