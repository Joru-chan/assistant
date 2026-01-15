from __future__ import annotations

import argparse
import importlib.util
import json
import re
import secrets
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "memory" / "tool_catalog.json"
JOB_LOCK = threading.Lock()
JOBS: dict[str, dict] = {}
ALLOWLIST = {
    ("./vm/status.sh",),
    ("./vm/deploy.sh",),
    ("./vm/pull_server_from_vm.sh",),
    ("./vm/health_check.sh",),
    ("./vm/ssh.sh",),
}
ADMIN_TOKEN_PATH = REPO_ROOT / "memory" / "admin_token.txt"
SAFE_MCP_TOOLS = {
    "hello",
    "health_check",
    "tool_requests_latest",
    "tool_requests_search",
    "notion_search",
    "notion_get_page",
}
MCP_TOOL_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
_ADMIN_TOKEN: str | None = None


TEMPLATE_PATH = REPO_ROOT / "templates" / "index.html"
STATIC_DIR = REPO_ROOT / "static"


def _load_html() -> str:
    if not TEMPLATE_PATH.exists():
        return "<h1>Missing templates/index.html</h1>"
    return TEMPLATE_PATH.read_text(encoding="utf-8")





def _load_tool_catalog() -> dict:
    if not CATALOG_PATH.exists():
        _build_catalog()
    try:
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        _build_catalog()
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _build_catalog() -> dict:
    tool_catalog_path = REPO_ROOT / "scripts" / "tool_catalog.py"
    spec = importlib.util.spec_from_file_location("tool_catalog", tool_catalog_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to import tool_catalog.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_catalog()


def _ensure_admin_token() -> str:
    global _ADMIN_TOKEN
    if _ADMIN_TOKEN:
        return _ADMIN_TOKEN
    ADMIN_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ADMIN_TOKEN_PATH.exists():
        token = ADMIN_TOKEN_PATH.read_text(encoding="utf-8").strip()
        if token:
            _ADMIN_TOKEN = token
            return token
    token = secrets.token_urlsafe(24)
    ADMIN_TOKEN_PATH.write_text(token, encoding="utf-8")
    _ADMIN_TOKEN = token
    return token


def _is_authorized(token: str | None) -> bool:
    expected = _ensure_admin_token()
    if not token:
        return False
    return secrets.compare_digest(token, expected)


def _is_localhost(host: str | None) -> bool:
    return host in {"127.0.0.1", "::1"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_job(cmd: list[str]) -> dict:
    job_id = uuid.uuid4().hex
    now = _now_iso()
    job = {
        "id": job_id,
        "cmd": cmd,
        "stdout": [],
        "stderr": [],
        "done": False,
        "exit_code": None,
        "started_at": now,
        "updated_at": now,
    }
    with JOB_LOCK:
        JOBS[job_id] = job
    return job


def _append_job(job_id: str, stream: str, line: str) -> None:
    with JOB_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        if stream == "stderr":
            job["stderr"].append(line)
        else:
            job["stdout"].append(line)
        job["updated_at"] = _now_iso()


def _finish_job(job_id: str, exit_code: int | None) -> None:
    with JOB_LOCK:
        job = JOBS.get(job_id)
        if job:
            job["done"] = True
            job["exit_code"] = exit_code
            job["updated_at"] = _now_iso()


def _get_job(job_id: str) -> dict | None:
    with JOB_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return None
        return {
            "done": job["done"],
            "exit_code": job["exit_code"],
            "stdout": "\n".join(job["stdout"]),
            "stderr": "\n".join(job["stderr"]),
            "started_at": job["started_at"],
            "updated_at": job["updated_at"],
        }


def _is_allowed_command(cmd: list[str], advanced: bool) -> tuple[bool, str]:
    if not cmd or not isinstance(cmd, list):
        return False, "cmd must be a non-empty list"
    if any(not isinstance(item, str) for item in cmd):
        return False, "cmd must be a list of strings"
    if tuple(cmd) in ALLOWLIST:
        return True, ""
    if cmd[0] == "./vm/deploy.sh":
        if len(cmd) == 1:
            return True, ""
        if len(cmd) == 2 and cmd[1] in {"--restart-only", "--restart"}:
            return True, ""
        return False, "deploy accepts --restart-only"
    if cmd[0] == "./vm/logs.sh":
        if len(cmd) == 1:
            return True, ""
        if len(cmd) == 2 and cmd[1].isdigit():
            return True, ""
        if len(cmd) == 3 and cmd[1] == "--lines" and cmd[2].isdigit():
            return True, ""
        return False, "logs accepts --lines N or a numeric line count"
    if cmd[0] == "./vm/mcp_curl.sh":
        if len(cmd) == 2 and cmd[1] == "--list":
            return True, ""
        if len(cmd) == 3 and cmd[1] == "--list" and cmd[2] == "--local":
            return True, ""
        if len(cmd) != 3:
            return False, "mcp_curl requires tool name and JSON args"
        tool = cmd[1].strip()
        if not tool:
            return False, "tool name is required"
        if not MCP_TOOL_PATTERN.match(tool):
            return False, "tool name must match ^[a-zA-Z0-9_-]+$"
        try:
            args_obj = json.loads(cmd[2])
        except json.JSONDecodeError:
            return False, "JSON args are invalid"
        if not isinstance(args_obj, dict):
            return False, "JSON args must be an object"
        if not advanced and tool not in SAFE_MCP_TOOLS:
            return False, "tool not allowed without advanced mode"
        return True, ""
    return False, "command not allowed"


def _run_job(job_id: str, cmd: list[str]) -> None:
    process = None
    exit_code = None
    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        def _reader(stream_name: str, pipe) -> None:
            if pipe is None:
                return
            for line in pipe:
                _append_job(job_id, stream_name, line.rstrip())
            pipe.close()

        stdout_thread = threading.Thread(
            target=_reader, args=("stdout", process.stdout), daemon=True
        )
        stderr_thread = threading.Thread(
            target=_reader, args=("stderr", process.stderr), daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()
        exit_code = process.wait()
        stdout_thread.join()
        stderr_thread.join()
    except Exception as exc:  # noqa: BLE001
        _append_job(job_id, "stderr", f"Job failed: {exc}")
    finally:
        _finish_job(job_id, exit_code)


class ToolboxHandler(BaseHTTPRequestHandler):
    def log_message(self, *_: object) -> None:
        return

    def _send(self, status: int, body: str, content_type: str = "text/html") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, _load_html())
            return
        if path.startswith("/static/"):
            relative = path.replace("/static/", "", 1)
            static_path = (STATIC_DIR / relative).resolve()
            if STATIC_DIR not in static_path.parents or not static_path.exists():
                self._send(404, "Not found")
                return
            content_type = "text/plain"
            if static_path.suffix == ".css":
                content_type = "text/css"
            elif static_path.suffix == ".js":
                content_type = "application/javascript"
            self._send(200, static_path.read_text(encoding="utf-8"), content_type)
            return
        if path == "/api/token":
            if not _is_localhost(self.client_address[0]):
                self._send(403, json.dumps({"error": "forbidden"}), "application/json")
                return
            token = _ensure_admin_token()
            self._send(200, json.dumps({"token": token}), "application/json")
            return
        if path == "/catalog":
            try:
                catalog = _load_tool_catalog()
                self._send(200, json.dumps(catalog), "application/json")
            except Exception as exc:  # pragma: no cover - UI fallback
                payload = {"error": str(exc)}
                self._send(500, json.dumps(payload), "application/json")
            return
        if path == "/refresh":
            try:
                catalog = _build_catalog()
                self._send(200, json.dumps(catalog), "application/json")
            except Exception as exc:  # pragma: no cover - UI fallback
                payload = {"error": str(exc)}
                self._send(500, json.dumps(payload), "application/json")
            return
        if path.startswith("/api/jobs/"):
            token = self.headers.get("X-Admin-Token")
            if not _is_authorized(token):
                self._send(401, json.dumps({"error": "unauthorized"}), "application/json")
                return
            job_id = path.split("/api/jobs/")[-1]
            job = _get_job(job_id)
            if not job:
                self._send(404, json.dumps({"error": "job not found"}), "application/json")
                return
            self._send(200, json.dumps(job), "application/json")
            return
        self._send(404, "Not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {}
        if path == "/api/jobs/run":
            token = self.headers.get("X-Admin-Token")
            if not _is_authorized(token):
                self._send(401, json.dumps({"error": "unauthorized"}), "application/json")
                return
            cmd = payload.get("cmd")
            confirm = bool(payload.get("confirm"))
            advanced = bool(payload.get("advanced"))
            ok, message = (
                _is_allowed_command(cmd, advanced) if isinstance(cmd, list) else (False, "")
            )
            if not ok:
                self._send(400, json.dumps({"error": message or "command not allowed"}), "application/json")
                return
            if cmd in (["./vm/deploy.sh"], ["./vm/pull_server_from_vm.sh"]) and not confirm:
                self._send(
                    400,
                    json.dumps({"error": "confirmation required"}),
                    "application/json",
                )
                return
            job = _new_job(cmd)
            thread = threading.Thread(target=_run_job, args=(job["id"], cmd), daemon=True)
            thread.start()
            self._send(200, json.dumps({"job_id": job["id"]}), "application/json")
            return

        self._send(404, json.dumps({"error": "Not found"}), "application/json")


def _maybe_open_browser(url: str) -> None:
    if subprocess.run(["which", "open"], capture_output=True, text=True).returncode != 0:
        return
    subprocess.Popen(
        ["open", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the Toolbox UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    catalog = _load_tool_catalog()
    host = args.host
    port = args.port
    url = f"http://{host}:{port}"
    _ensure_admin_token()
    tool_names = [tool["name"] for tool in catalog["tools"]][:5]
    print(f"Serving on {url}", flush=True)
    if tool_names:
        print(f"Loaded tools: {', '.join(tool_names)}", flush=True)
    print(
        "Admin routes: /api/jobs/run /api/jobs/<id>",
        flush=True,
    )
    _maybe_open_browser(url)
    server = HTTPServer((host, port), ToolboxHandler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
