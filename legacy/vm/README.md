# Legacy VM Scripts (Deprecated)

These scripts were moved out of `vm/` during the VM MCP admin cleanup.
They are kept for reference and emergency use, but they are **deprecated**.

Use the canonical scripts under `vm/` instead:
- `deploy.sh`
- `status.sh`
- `logs.sh`
- `pull_server_from_vm.sh`
- `mcp_curl.sh`
- `health_check.sh`
- `ssh.sh`

If you need any of these legacy scripts re-enabled, move them back into `vm/`
and update `scripts/toolbox_ui.py` allowlist accordingly.
