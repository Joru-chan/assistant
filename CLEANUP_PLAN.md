# Repository Cleanup Plan

## Overview

This cleanup simplifies the repository by removing the Notion integration and natural language agent interface, keeping only the core VM deployment system.

## Changes Made

### Removed Components

1. **Natural Language Agent Interface**
   - `scripts/agent.py` - Main agent router (101KB file)
   - `scripts/agent/` - Agent-related modules directory
   - `scripts/llm_decider.py` - LLM decision logic
   - `scripts/personal_task_analyzer.py` - Notion task analysis
   - `scripts/personal_project_analyzer.py` - Notion project analysis
   - `scripts/sync_tool_requests.py` - Tool request syncing
   - `scripts/tool_catalog.py` - Tool catalog builder
   - `scripts/tool_request_scoring.py` - Tool request scoring
   - `scripts/tool_requests.py` - Tool request management
   - `scripts/toolbox_ui.py` - Toolbox web UI
   - `scripts/verify_setup.py` - Setup verification
   - `scripts/common/` - Common utilities directory

2. **Notion-Specific Documentation**
   - `AGENT_GUIDE.md` - Agent instructions and workflows (12KB)
   - `PERSONAL_CONTEXT.md` - Personal Notion database details (9.5KB)
   - `SETUP_CODEX.md` - MCP setup instructions (9.5KB)
   - `docs/` - Additional documentation directory

3. **Test and Template Files**
   - `test_one_item.json` - Test data
   - `test_receipt.json` - Test receipt data
   - `templates/` - Template files directory
   - `static/` - Static assets directory
   - `tests/` - Test files directory

4. **Notion/Agent-Related Directories**
   - `tools/` - Tool integrations directory
   - `utils/` - Utility modules directory
   - `legacy/` - Legacy code directory
   - `.claude/` - Claude-specific configuration

5. **Other Files**
   - `Makefile` - Build automation (for agent system)
   - `requirements.txt` - Python dependencies for agent

### Kept Components

1. **VM Deployment System** (Complete)
   - `vm/` directory with all deployment scripts
   - `vm/README.md` - VM deployment documentation
   - `vm/deploy.sh` - Main deployment script
   - All VM management scripts (ssh, status, logs, health_check, etc.)
   - `vm_server/` - VM server components directory

2. **Repository Basics**
   - `README.md` - Updated and simplified
   - `LICENSE` - Repository license
   - `.gitignore` - Git ignore rules

## Rationale

The cleanup focuses the repository on its core purpose: VM deployment and management. By removing the Notion integration and complex agent system, we:

- Reduce repository complexity
- Remove personal/private context from the codebase
- Create a more maintainable and focused project
- Keep deployment infrastructure intact

## Next Steps

After this cleanup is merged:

1. Consider creating separate repositories for:
   - Notion integration tools (if still needed)
   - Personal assistant agent (if desired to continue development)

2. Archive removed components if needed for future reference

3. Update any external documentation or links pointing to removed components

## Rollback Plan

If needed, all removed code is preserved in git history and can be restored by:
```bash
git checkout <previous-commit> -- <file-or-directory>
```

Original state is at commit: `395dfab12036d9cce6298461280c1dfab818ec00`
