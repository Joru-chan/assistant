from __future__ import annotations

"""Deprecated admin tools (kept for backward compatibility)."""

import os
import socket
import subprocess
from datetime import datetime, timezone
from typing import List

from fastmcp import FastMCP


def _authorize(token: str | None) -> list[str]:
    errors: list[str] = []
    expected = os.getenv("ADMIN_TOKEN")
    if not expected:
        errors.append("ADMIN_TOKEN is not set on the server.")
        return errors
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
        if errors:
            return {
                "summary": "Admin token required.",
                "result": {},
                "next_actions": ["Provide a valid admin token."],
                "errors": errors,
            }

        service = os.getenv("MCP_SERVICE_NAME", "mcp-server.service")
        port = os.getenv("PORT", "8000")
        server_time = datetime.now(timezone.utc).isoformat()
        hostname = socket.gethostname()
        uptime_seconds = None
        try:
            with open("/proc/uptime", "r", encoding="utf-8") as handle:
                uptime_seconds = float(handle.read().split()[0])
        except Exception:  # noqa: BLE001
            uptime_seconds = None

        status_code, status_out = _run_command(["systemctl", "is-active", service])

        return {
            "summary": f"Service {service} status: {status_out or 'unknown'}.",
            "result": {
                "service": service,
                "status": status_out or "unknown",
                "status_code": status_code,
                "server_time": server_time,
                "hostname": hostname,
                "uptime_seconds": uptime_seconds,
                "health_url": f"http://127.0.0.1:{port}/health",
            },
            "next_actions": ["Run admin_logs to inspect recent logs."],
            "errors": [],
        }

    @mcp.tool
    def admin_logs(token: str | None = None, lines: int = 200) -> dict:
        """
        Return recent systemd logs for the MCP service.
        """
        errors = _authorize(token)
        if errors:
            return {
                "summary": "Admin token required.",
                "result": {},
                "next_actions": ["Provide a valid admin token."],
                "errors": errors,
            }

        service = os.getenv("MCP_SERVICE_NAME", "mcp-server.service")
        lines = max(1, min(lines, 1000))
        code, output = _run_command(
            ["sudo", "journalctl", "-u", service, "-n", str(lines), "--no-pager"]
        )
        if code != 0:
            return {
                "summary": "Failed to read logs.",
                "result": {"lines": []},
                "next_actions": ["Check journalctl permissions."],
                "errors": [output or "journalctl returned a non-zero exit code."],
            }
        log_lines = output.splitlines()
        return {
            "summary": f"Fetched {len(log_lines)} log line(s).",
            "result": {"lines": log_lines},
            "next_actions": [],
            "errors": [],
        }

    @mcp.tool
    def admin_restart(token: str | None = None, confirm: bool = False) -> dict:
        """
        Restart the MCP systemd service (explicit confirmation required).
        """
        errors = _authorize(token)
        if errors:
            return {
                "summary": "Admin token required.",
                "result": {},
                "next_actions": ["Provide a valid admin token."],
                "errors": errors,
            }

        service = os.getenv("MCP_SERVICE_NAME", "mcp-server.service")
        if not confirm:
            return {
                "summary": "Restart requires confirmation.",
                "result": {"service": service},
                "next_actions": ["Re-run with confirm=true to restart."],
                "errors": [],
            }

        code, output = _run_command(["sudo", "systemctl", "restart", service])
        if code != 0:
            return {
                "summary": "Restart failed.",
                "result": {"service": service},
                "next_actions": ["Inspect admin_logs for details."],
                "errors": [output or "systemctl restart failed."],
            }
        return {
            "summary": f"Restart triggered for {service}.",
            "result": {"service": service},
            "next_actions": ["Run health_check to confirm readiness."],
            "errors": [],
        }
