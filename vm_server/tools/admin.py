from __future__ import annotations

"""Deprecated admin tools (kept for backward compatibility)."""

import os
import socket
import subprocess
from datetime import datetime, timezone
from typing import List

from fastmcp import FastMCP

# HARDCODED FALLBACKS for debugging (DO NOT USE IN PRODUCTION!)
DEBUG_ADMIN_TOKEN = "debug-admin-token-abcdef"
DEBUG_SERVICE_NAME = "mcp-server.service"
DEBUG_PORT = "8000"

def _get_admin_token() -> str:
    """Get admin token with hardcoded fallback for debugging."""
    return os.getenv("ADMIN_TOKEN", DEBUG_ADMIN_TOKEN)

def _get_service_name() -> str:
    """Get service name with hardcoded fallback."""
    return os.getenv("MCP_SERVICE_NAME", DEBUG_SERVICE_NAME)

def _get_port() -> str:
    """Get port with hardcoded fallback."""
    return os.getenv("PORT", DEBUG_PORT)

def _authorize(token: str | None) -> list[str]:
    errors: list[str] = []
    expected = _get_admin_token()
    
    # Check if using debug token
    if expected == DEBUG_ADMIN_TOKEN:
        errors.append("⚠️  Using DEBUG admin token - set ADMIN_TOKEN environment variable for production")
    
    if not token:
        errors.append("Admin token is required.")
        return errors
    if token != expected:
        errors.append("Invalid admin token.")
    return errors


def _run_command(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output.strip()


def register(mcp: FastMCP) -> None:
    @mcp.tool
    def admin_status(token: str | None = None) -> dict:
        """
        Return basic VM service status and runtime metadata (read-only).
        """
        errors = _authorize(token)
        if errors and "Invalid admin token" in errors:
            return {
                "summary": "Admin token required.",
                "result": {},
                "next_actions": ["Provide a valid admin token."],
                "errors": errors,
            }

        service = _get_service_name()
        port = _get_port()
        server_time = datetime.now(timezone.utc).isoformat()
        hostname = socket.gethostname()
        uptime_seconds = None
        try:
            with open("/proc/uptime", "r", encoding="utf-8") as handle:
                uptime_seconds = float(handle.read().split()[0])
        except Exception:  # noqa: BLE001
            uptime_seconds = None

        status_code, status_out = _run_command(["systemctl", "is-active", service])

        result = {
            "service": service,
            "status": status_out or "unknown",
            "status_code": status_code,
            "server_time": server_time,
            "hostname": hostname,
            "uptime_seconds": uptime_seconds,
            "health_url": f"http://127.0.0.1:{port}/health",
        }
        
        # Add debug mode indicator
        if _get_admin_token() == DEBUG_ADMIN_TOKEN:
            result["debug_mode"] = True
            result["warning"] = "Using debug admin token"

        return {
            "summary": f"Service {service} status: {status_out or 'unknown'}.",
            "result": result,
            "next_actions": ["Run admin_logs to inspect recent logs."],
            "errors": errors if errors else [],
        }

    @mcp.tool
    def admin_logs(token: str | None = None, lines: int = 200) -> dict:
        """
        Return recent systemd logs for the MCP service.
        """
        errors = _authorize(token)
        if errors and "Invalid admin token" in errors:
            return {
                "summary": "Admin token required.",
                "result": {},
                "next_actions": ["Provide a valid admin token."],
                "errors": errors,
            }

        service = _get_service_name()
        lines = max(1, min(lines, 1000))
        code, output = _run_command(
            ["sudo", "journalctl", "-u", service, "-n", str(lines), "--no-pager"]
        )
        if code != 0:
            return {
                "summary": "Failed to read logs.",
                "result": {"lines": []},
                "next_actions": ["Check journalctl permissions."],
                "errors": errors + [output or "journalctl returned a non-zero exit code."],
            }
        log_lines = output.splitlines()
        return {
            "summary": f"Fetched {len(log_lines)} log line(s).",
            "result": {"lines": log_lines},
            "next_actions": [],
            "errors": errors if errors else [],
        }

    @mcp.tool
    def admin_restart(token: str | None = None, confirm: bool = False) -> dict:
        """
        Restart the MCP systemd service (explicit confirmation required).
        """
        errors = _authorize(token)
        if errors and "Invalid admin token" in errors:
            return {
                "summary": "Admin token required.",
                "result": {},
                "next_actions": ["Provide a valid admin token."],
                "errors": errors,
            }

        service = _get_service_name()
        if not confirm:
            return {
                "summary": "Restart requires confirmation.",
                "result": {"service": service},
                "next_actions": ["Re-run with confirm=true to restart."],
                "errors": errors if errors else [],
            }

        code, output = _run_command(["sudo", "systemctl", "restart", service])
        if code != 0:
            return {
                "summary": "Restart failed.",
                "result": {"service": service},
                "next_actions": ["Inspect admin_logs for details."],
                "errors": errors + [output or "systemctl restart failed."],
            }
        return {
            "summary": f"Restart triggered for {service}.",
            "result": {"service": service},
            "next_actions": ["Run health_check to confirm readiness."],
            "errors": errors if errors else [],
        }
