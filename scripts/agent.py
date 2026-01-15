#!/usr/bin/env python3
"""
Universal router entrypoint for natural language requests.

Usage:
  python scripts/agent.py "what should we build next?"
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from prefs import load_prefs, save_prefs

ROUTE_LIST = ("list wishes", "show tool requests", "list tool requests", "show wishes")
ROUTE_PICK = ("pick", "choose", "what to build", "next tool", "triage", "what should we build")
ROUTE_SCAFFOLD = ("scaffold", "start project", "start a project", "create tool", "implement")
ROUTE_DEPLOY = ("deploy", "ship", "push to vm")
ROUTE_SEARCH = ("search", "find", "lookup")
MUTATING_TOOL_RE = re.compile(r"(apply|deploy|write|create|set|update|delete)")
EDIT_NOTION_KEYWORDS = (
    "edit",
    "update",
    "change",
    "fix",
    "correct",
    "rename",
    "set",
    "add tag",
    "remove tag",
)
PREFS_KEYWORDS = ("auto apply", "auto-apply")
LAST_PREVIEW_PATH = Path("memory/last_preview.json")
PREVIEW_TTL_HOURS = 24
STOPWORDS = {
    "the",
    "and",
    "or",
    "to",
    "a",
    "an",
    "of",
    "in",
    "for",
    "with",
    "is",
    "are",
    "be",
    "it",
    "this",
    "that",
    "my",
    "your",
    "from",
    "on",
    "by",
    "as",
    "at",
    "like",
}


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "new-tool"


def _truncate(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...<truncated>"


def _run_command(cmd: List[str]) -> Dict[str, Any]:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {
        "cmd": " ".join(cmd),
        "returncode": result.returncode,
        "stdout": _truncate(result.stdout.strip()),
        "stderr": _truncate(result.stderr.strip()),
    }


def _extract_quoted_phrases(text: str) -> List[str]:
    matches = re.finditer(r"(?:^|\s|:)[\"']([^\"']+)[\"']", text)
    return [match.group(1).strip() for match in matches if match.group(1).strip()]


def _extract_search_query(text: str) -> str:
    quoted = _extract_quoted_phrases(text)
    if quoted:
        return quoted[0]
    match = re.search(
        r"(?:search|find|lookup)\s+(?:wishes|tool requests|requests|for|about)?\s*(.+)",
        text,
        flags=re.IGNORECASE,
    )
    if match and match.group(1).strip():
        return match.group(1).strip()
    return text


def _extract_page_id(text: str) -> str | None:
    match = re.search(
        r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1)
    match = re.search(r"([0-9a-f]{32})", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _should_set_prefs(request: str) -> bool:
    lower = request.lower()
    return any(keyword in lower for keyword in PREFS_KEYWORDS)


def _should_correct_tool_request(request: str) -> bool:
    lower = request.lower()
    if "tool request" in lower or "tool requests" in lower or "friction log" in lower:
        return any(word in lower for word in ("fix", "correct", "change", "update", "edit"))
    return False


def _should_edit_notion(request: str) -> bool:
    lower = request.lower()
    if "notion" not in lower:
        return False
    return any(keyword in lower for keyword in EDIT_NOTION_KEYWORDS)


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if token and token not in STOPWORDS]


def _save_last_preview(payload: Dict[str, Any]) -> None:
    LAST_PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_PREVIEW_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_last_preview() -> Dict[str, Any] | None:
    if not LAST_PREVIEW_PATH.exists():
        return None
    return json.loads(LAST_PREVIEW_PATH.read_text(encoding="utf-8"))


def _preview_is_fresh(timestamp: str) -> bool:
    try:
        dt = datetime.fromisoformat(timestamp)
    except ValueError:
        return False
    age = datetime.now(timezone.utc) - dt
    return age.total_seconds() <= PREVIEW_TTL_HOURS * 3600


def _parse_correction_request(request: str) -> Tuple[str | None, str | None]:
    quoted = _extract_quoted_phrases(request)
    if len(quoted) >= 2:
        return quoted[0], quoted[1]
    match = re.search(
        r"(?:change|correct|fix|update)\s+(.+?)\s+to\s+(.+)",
        request,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, None


def _replace_case_insensitive(text: str, old: str, new: str) -> str:
    pattern = re.compile(re.escape(old), flags=re.IGNORECASE)
    if not pattern.search(text):
        return new
    return pattern.sub(new, text, count=1)


def _simplify_query(text: str) -> str:
    tokens = _tokenize(text)
    if "physical" in tokens and "items" in tokens:
        return "physical items"
    if len(tokens) >= 2:
        return " ".join(tokens[:2])
    return tokens[0] if tokens else ""


def _compute_confidence(
    request: str,
    candidate: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    old_phrase: str | None,
) -> Tuple[float, List[Dict[str, Any]]]:
    score = 0.0
    breakdown: List[Dict[str, Any]] = []
    title = str(candidate.get("title") or "")
    lower = request.lower()

    if old_phrase and old_phrase.lower() in title.lower():
        score += 0.45
        breakdown.append(
            {
                "rule": "quoted_phrase_match",
                "score": 0.45,
                "details": f"Matched '{old_phrase}' in title.",
            }
        )

    candidate_index = next(
        (idx for idx, item in enumerate(candidates) if item is candidate),
        None,
    )
    if candidate_index is not None and candidate_index <= 1:
        score += 0.20
        breakdown.append(
            {
                "rule": "recency_bonus",
                "score": 0.20,
                "details": "Candidate is among the two newest results.",
            }
        )

    if ("not " in lower and " but " in lower) or ("instead of" in lower) or ("misinterpreted" in lower):
        score += 0.20
        breakdown.append(
            {
                "rule": "negation_pattern",
                "score": 0.20,
                "details": "Detected correction/negation phrasing.",
            }
        )

    request_tokens = set(_tokenize(request))
    candidate_tokens = set(_tokenize(title))
    overlap = request_tokens.intersection(candidate_tokens)
    if len(overlap) >= 2:
        score += 0.15
        breakdown.append(
            {
                "rule": "keyword_overlap",
                "score": 0.15,
                "details": f"Overlapping tokens: {', '.join(sorted(overlap))}.",
            }
        )

    score = max(0.0, min(score, 1.0))
    return score, breakdown


def _route(request: str, force_scaffold: bool) -> Tuple[str, Dict[str, Any]]:
    lower = request.lower()
    if force_scaffold:
        return "scaffold", {}
    if lower.strip() in ("apply that", "apply last preview", "apply last correction"):
        return "apply_last", {}
    if _should_set_prefs(request):
        return "prefs", {}
    if _should_correct_tool_request(request):
        return "correct_tool_request", {}
    call_match = re.match(
        r"^\s*call\s+([a-z0-9_-]+)\s*(\{.*\})?\s*$",
        request,
        flags=re.IGNORECASE,
    )
    if call_match:
        return "call", {
            "tool": call_match.group(1).lower(),
            "args": call_match.group(2),
        }
    if any(word in lower for word in ROUTE_DEPLOY):
        return "deploy", {}
    if _should_edit_notion(request):
        return "edit_notion", {}
    if any(word in lower for word in ROUTE_SCAFFOLD):
        return "scaffold", {}
    if any(word in lower for word in ROUTE_PICK):
        return "triage", {}
    if any(word in lower for word in ROUTE_SEARCH):
        return "search", {"query": _extract_search_query(request)}
    if any(word in lower for word in ROUTE_LIST):
        return "list", {}
    return "unknown", {}


def _run_triage(dry_run: bool) -> Dict[str, Any]:
    cmd = [sys.executable, "scripts/triage.py"]
    if dry_run:
        cmd.append("--dry-run")
    else:
        cmd.append("--execute")
    result = _run_command(cmd)
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or "triage failed")
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError:
        payload = {"raw_output": result["stdout"]}
    payload["command"] = result["cmd"]
    return payload


def _parse_mcp_response(raw: str) -> Dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid MCP JSON output: {exc}") from exc
    result = payload.get("result") or {}
    structured = result.get("structuredContent")
    if structured:
        return structured
    content = result.get("content") or []
    for block in content:
        text = block.get("text")
        if isinstance(text, str):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue
    raise RuntimeError("Missing structuredContent in MCP response")


def _run_mcp_tool(tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    cmd = ["./vm/mcp_curl.sh", tool, json.dumps(args)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "MCP tool call failed")
    return _parse_mcp_response(result.stdout)


def _extract_edit_query(request: str) -> str:
    query = _extract_search_query(request)
    query = re.sub(r"\b(in\s+notion|notion)\b", "", query, flags=re.IGNORECASE).strip()
    return query


def _strip_quotes(text: str) -> str:
    return text.strip().strip("\"'").strip()


def _parse_edit_intent(request: str) -> Tuple[Dict[str, Any], List[str]]:
    updates: Dict[str, Any] = {"properties": {}}
    notes: List[str] = []
    lower = request.lower()

    title_match = re.search(
        r"(?:rename|change|update|set)\s+title(?:\s+from)?\s+(.+?)\s+to\s+(.+)",
        request,
        flags=re.IGNORECASE,
    )
    if title_match:
        updates["title"] = _strip_quotes(title_match.group(2))

    status_match = re.search(r"set\s+status\s+(.+)", request, flags=re.IGNORECASE)
    if status_match:
        updates["properties"]["Status"] = _strip_quotes(status_match.group(1))

    desc_match = re.search(r"set\s+description\s+(.+)", request, flags=re.IGNORECASE)
    if desc_match:
        updates["properties"]["Description"] = _strip_quotes(desc_match.group(1))

    tag_match = re.search(
        r"(?:add|set)\s+tag[s]?\s+(.+)",
        request,
        flags=re.IGNORECASE,
    )
    if tag_match:
        raw_tags = _strip_quotes(tag_match.group(1))
        tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
        if tags:
            updates["properties"]["Domain"] = tags

    if not updates.get("title") and not updates["properties"]:
        notes.append("No update intent detected; specify title/status/description/tag.")

    return updates, notes


def _parse_prefs_request(request: str, prefs: Dict[str, object]) -> Dict[str, object]:
    lower = request.lower()
    updated = dict(prefs)
    if "enable auto apply" in lower or "enable auto-apply" in lower:
        updated["auto_apply_enabled"] = True
    if "disable auto apply" in lower or "disable auto-apply" in lower:
        updated["auto_apply_enabled"] = False
    match = re.search(r"auto apply threshold to\s*([0-9.]+)", lower)
    if match:
        try:
            value = float(match.group(1))
        except ValueError:
            value = prefs.get("auto_apply_threshold", 0.92)
        updated["auto_apply_threshold"] = max(0.0, min(value, 1.0))
    return updated


def _build_correction_updates(
    candidate: Dict[str, Any], old_text: str | None, new_text: str | None
) -> Dict[str, Any]:
    title = str(candidate.get("title") or "")
    if new_text:
        if old_text:
            new_title = _replace_case_insensitive(title, old_text, new_text)
        else:
            new_title = new_text
        return {"title": new_title, "properties": {}}
    return {"properties": {}}


def _extract_triage_title(triage_payload: Dict[str, Any]) -> str | None:
    triage_result = triage_payload.get("result") or {}
    selected = triage_result.get("selected") or {}
    title = selected.get("title")
    return title if isinstance(title, str) and title.strip() else None


def _update_registry(slug: str, registry_path: Path) -> bool:
    lines = registry_path.read_text(encoding="utf-8").splitlines()
    updated = False

    def insert_in_block(start_predicate, end_predicate) -> None:
        nonlocal updated
        start = next((i for i, line in enumerate(lines) if start_predicate(line)), None)
        if start is None:
            raise RuntimeError("Registry import block not found.")
        end = next((i for i in range(start + 1, len(lines)) if end_predicate(lines[i])), None)
        if end is None:
            raise RuntimeError("Registry block end not found.")
        if any(re.search(rf"\\b{re.escape(slug)}\\b", line) for line in lines[start + 1 : end]):
            return
        lines.insert(end, f"    {slug},")
        updated = True

    insert_in_block(lambda line: line.strip() == "from tools import (", lambda line: line.strip() == ")")
    insert_in_block(lambda line: line.strip() == "for module in (", lambda line: line.strip() == "):")

    if updated:
        registry_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return updated


def _scaffold_tool(request: str) -> Dict[str, Any]:
    slug = _slugify(request)
    tools_dir = Path("vm_server/tools")
    module_path = tools_dir / f"{slug}.py"
    registry_path = tools_dir / "registry.py"
    created: List[str] = []

    if module_path.exists():
        raise RuntimeError(f"Tool already exists: {module_path}")

    tools_dir.mkdir(parents=True, exist_ok=True)
    module_content = f"""from __future__ import annotations

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def {slug}(request: str | None = None) -> dict:
        \"\"\"Stub tool generated by scripts/agent.py.\"\"\"
        return {{
            "summary": "Stub tool created. Implementation pending.",
            "result": {{"request": request}},
            "next_actions": ["Implement tool logic in vm_server/tools/{slug}.py"],
            "errors": [],
        }}
"""
    module_path.write_text(module_content, encoding="utf-8")
    created.append(str(module_path))

    if not registry_path.exists():
        raise RuntimeError(f"Missing registry: {registry_path}")
    _update_registry(slug, registry_path)
    created.append(str(registry_path))

    today = datetime.now().strftime("%Y-%m-%d")
    spec_path = Path("memory/specs") / f"{today}_{slug}.md"
    plan_path = Path("memory/plans") / f"{today}_{slug}.md"
    spec_content = (
        f"# Tool Spec: {request}\n\n"
        "## Problem\n"
        f"{request}\n\n"
        "## v0 proposal\n"
        "- Create a minimal read-only tool.\n"
        "- Add an explicit apply/confirm step before any writes.\n"
    )
    plan_content = (
        f"# Plan: {request}\n\n"
        "1) Confirm inputs/outputs contract.\n"
        "2) Implement read-only path first.\n"
        "3) Add tests + apply path with confirmation.\n"
    )
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(spec_content, encoding="utf-8")
    plan_path.write_text(plan_content, encoding="utf-8")
    created.append(str(spec_path))
    created.append(str(plan_path))

    return {
        "slug": slug,
        "module": str(module_path),
        "spec_path": str(spec_path),
        "plan_path": str(plan_path),
        "files_created": created,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Route natural language requests.")
    parser.add_argument("request", nargs="+")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--scaffold", action="store_true")
    parser.add_argument("--auto-apply", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    request_text = " ".join(args.request).strip()
    dry_run = True
    if args.execute:
        dry_run = False
    if args.dry_run:
        dry_run = True

    prefs = load_prefs()

    route, route_meta = _route(request_text, args.scaffold)
    errors: List[str] = []
    next_actions: List[str] = []
    result: Dict[str, Any] = {
        "route": route,
        "request": request_text,
        "commands": [],
        "files_created": [],
    }

    try:
        if route == "list":
            cmd = [
                "./vm/mcp_curl.sh",
                "tool_requests_latest",
                json.dumps({"limit": 10, "statuses": ["new", "triaging"]}),
            ]
            result["commands"].append(" ".join(cmd))
            result["output"] = _run_command(cmd)
        elif route == "search":
            query = route_meta.get("query") or request_text
            cmd = ["./vm/mcp_curl.sh", "tool_requests_search", json.dumps({"query": query, "limit": 10})]
            result["commands"].append(" ".join(cmd))
            result["output"] = _run_command(cmd)
        elif route == "triage":
            result["triage"] = _run_triage(dry_run=dry_run)
            if dry_run:
                next_actions.append("Re-run with --execute to write spec/plan files.")
        elif route == "prefs":
            updated_prefs = _parse_prefs_request(request_text, prefs)
            save_prefs(updated_prefs)
            result["prefs"] = updated_prefs
            next_actions.append("Prefs saved. Re-run with your request.")
        elif route == "apply_last":
            if dry_run:
                next_actions.append("Re-run with --execute to apply the last preview.")
            else:
                preview = _load_last_preview()
                if not preview:
                    raise RuntimeError("No last preview found.")
                if preview.get("type") != "notion_correction":
                    raise RuntimeError("Last preview is not a Notion correction.")
                timestamp = str(preview.get("timestamp") or "")
                if not _preview_is_fresh(timestamp) and not args.force:
                    raise RuntimeError("Last preview is older than 24h. Re-run with --force.")
                payload = {
                    "page_id": preview.get("page_id"),
                    "updates": preview.get("updates"),
                    "dry_run": False,
                }
                result["commands"].append(
                    "./vm/mcp_curl.sh notion_update_page " + json.dumps(payload)
                )
                result["notion_update"] = _run_mcp_tool("notion_update_page", payload)
        elif route == "correct_tool_request":
            old_text, new_text = _parse_correction_request(request_text)
            if not new_text:
                raise RuntimeError("No correction target found. Use: change 'X' to 'Y'.")

            page_id = _extract_page_id(request_text)
            items: List[Dict[str, Any]] = []
            if page_id:
                result["commands"].append(
                    "./vm/mcp_curl.sh notion_get_page " + json.dumps({"page_id": page_id})
                )
                page = _run_mcp_tool("notion_get_page", {"page_id": page_id})
                summary = page.get("result", {}).get("page", {})
                items = [
                    {
                        "id": summary.get("id"),
                        "title": summary.get("title"),
                        "url": summary.get("url"),
                        "created_time": "",
                    }
                ]
            else:
                query = old_text or _extract_search_query(request_text)
                search = _run_mcp_tool("tool_requests_search", {"query": query, "limit": 10})
                result["commands"].append(
                    "./vm/mcp_curl.sh tool_requests_search " + json.dumps({"query": query, "limit": 10})
                )
                items = search.get("result", {}).get("items", [])
                if not items and new_text:
                    fallback_query = new_text
                    search = _run_mcp_tool(
                        "tool_requests_search", {"query": fallback_query, "limit": 10}
                    )
                    result["commands"].append(
                        "./vm/mcp_curl.sh tool_requests_search "
                        + json.dumps({"query": fallback_query, "limit": 10})
                    )
                    items = search.get("result", {}).get("items", [])
                if not items and new_text:
                    simplified = _simplify_query(new_text)
                    if simplified and simplified != new_text:
                        search = _run_mcp_tool(
                            "tool_requests_search", {"query": simplified, "limit": 10}
                        )
                        result["commands"].append(
                            "./vm/mcp_curl.sh tool_requests_search "
                            + json.dumps({"query": simplified, "limit": 10})
                        )
                        items = search.get("result", {}).get("items", [])
            if not items:
                result["candidates"] = []
                next_actions.append("No matches. Try quoting the exact title.")
            elif len(items) > 1 and not page_id:
                candidates = []
                for item in items:
                    confidence, breakdown = _compute_confidence(
                        request_text, item, items, old_text
                    )
                    candidates.append(
                        {
                            "id": item.get("id"),
                            "title": item.get("title"),
                            "url": item.get("url"),
                            "confidence": confidence,
                        }
                    )
                result["candidates"] = candidates
                next_actions.append("Multiple matches found. Re-run with a page URL or id.")
            else:
                candidate = items[0]
                confidence, breakdown = _compute_confidence(
                    request_text, candidate, items, old_text
                )
                updates = _build_correction_updates(candidate, old_text, new_text)
                correction_payload = {
                    "page_id": candidate.get("id"),
                    "updates": updates,
                }
                result["correction"] = {
                    "target": {
                        "id": candidate.get("id"),
                        "title": candidate.get("title"),
                        "url": candidate.get("url"),
                    },
                    "confidence": confidence,
                    "confidence_breakdown": breakdown,
                }
                result["confidence"] = confidence
                result["confidence_breakdown"] = breakdown

                auto_apply_enabled = bool(prefs.get("auto_apply_enabled"))
                threshold = float(prefs.get("auto_apply_threshold") or 0.92)
                scope = prefs.get("auto_apply_scope") or []
                allow_auto = (
                    auto_apply_enabled
                    and args.auto_apply
                    and "notion_corrections" in scope
                )

                if dry_run:
                    payload = dict(correction_payload, dry_run=True)
                    result["commands"].append(
                        "./vm/mcp_curl.sh notion_update_page " + json.dumps(payload)
                    )
                    result["notion_update"] = _run_mcp_tool("notion_update_page", payload)
                    _save_last_preview(
                        {
                            "type": "notion_correction",
                            "page_id": candidate.get("id"),
                            "updates": updates,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "confidence": confidence,
                        }
                    )
                    if confidence >= threshold:
                        next_actions.append(
                            f"High confidence ({confidence:.2f}). To apply: "
                            "python scripts/agent.py \"apply that\" --execute"
                        )
                        next_actions.append(
                            "Or rerun with --execute --auto-apply."
                        )
                    else:
                        next_actions.append(
                            f"Confidence ({confidence:.2f}) below threshold. "
                            "Re-run with --execute --force to apply."
                        )
                else:
                    payload = dict(correction_payload, dry_run=False)
                    if allow_auto and confidence < threshold and not args.force:
                        preview_payload = dict(correction_payload, dry_run=True)
                        result["commands"].append(
                            "./vm/mcp_curl.sh notion_update_page " + json.dumps(preview_payload)
                        )
                        result["notion_update"] = _run_mcp_tool(
                            "notion_update_page", preview_payload
                        )
                        next_actions.append(
                            f"Confidence ({confidence:.2f}) below threshold. "
                            "Re-run with --execute --force to apply."
                        )
                    else:
                        result["commands"].append(
                            "./vm/mcp_curl.sh notion_update_page " + json.dumps(payload)
                        )
                        result["notion_update"] = _run_mcp_tool("notion_update_page", payload)
        elif route == "edit_notion":
            page_id = _extract_page_id(request_text)
            updates, intent_notes = _parse_edit_intent(request_text)

            if not page_id:
                query = _extract_edit_query(request_text)
                if not query:
                    raise RuntimeError("No Notion target found. Provide a page title or URL.")
                search = _run_mcp_tool("notion_search", {"query": query, "limit": 5})
                result["commands"].append(
                    "./vm/mcp_curl.sh notion_search "
                    + json.dumps({"query": query, "limit": 5})
                )
                items = search.get("result", {}).get("items", [])
                if not items:
                    result["candidates"] = []
                    next_actions.append("No matches. Try quoting the page title or paste the URL.")
                elif len(items) > 1:
                    result["candidates"] = items
                    next_actions.append("Multiple matches found. Re-run with a page URL or id.")
                else:
                    page_id = items[0].get("id")

            if not page_id:
                result["intent_notes"] = intent_notes
            else:
                if intent_notes:
                    result["intent_notes"] = intent_notes
                if intent_notes and dry_run:
                    result["commands"].append(
                        "./vm/mcp_curl.sh notion_get_page "
                        + json.dumps({"page_id": page_id})
                    )
                    page = _run_mcp_tool("notion_get_page", {"page_id": page_id})
                    result["preview"] = page
                    next_actions.append("Specify a target field (title/status/description/tag) to update.")
                else:
                    payload = {"page_id": page_id, "updates": updates, "dry_run": dry_run}
                    result["commands"].append(
                        "./vm/mcp_curl.sh notion_update_page "
                        + json.dumps(payload)
                    )
                    result["notion_update"] = _run_mcp_tool("notion_update_page", payload)
                    if dry_run:
                        next_actions.append("Re-run with --execute to apply the update.")
        elif route == "deploy":
            cmd = ["./vm/deploy.sh"]
            result["commands"].append(" ".join(cmd))
            if dry_run:
                next_actions.append("Re-run with --execute to deploy.")
            else:
                result["output"] = _run_command(cmd)
        elif route == "scaffold":
            result["triage"] = _run_triage(dry_run=True)
            title = _extract_triage_title(result["triage"])
            if not title:
                raise RuntimeError("No triage selection available for scaffolding.")
            result["scaffold_source"] = title
            if dry_run:
                next_actions.append("Re-run with --execute to scaffold the tool.")
            else:
                scaffold = _scaffold_tool(title)
                result["files_created"] = scaffold.pop("files_created", [])
                result["scaffold"] = scaffold
        elif route == "call":
            tool = route_meta.get("tool")
            args_json = route_meta.get("args") or "{}"
            if not tool:
                raise RuntimeError("Missing tool name for call route.")
            cmd = ["./vm/mcp_curl.sh", tool, args_json]
            result["commands"].append(" ".join(cmd))
            if MUTATING_TOOL_RE.search(tool):
                if dry_run:
                    next_actions.append("Re-run with --execute to call mutating tool.")
                else:
                    result["output"] = _run_command(cmd)
            else:
                result["output"] = _run_command(cmd)
        else:
            next_actions.append("Try: python scripts/agent.py \"what should we build next?\"")
            next_actions.append("Or: python scripts/agent.py \"show tool requests\"")
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))

    if result.get("commands"):
        last_cmd = result["commands"][-1]
        next_actions.append(f"Reproduce: {last_cmd}")
    if "triage" in result and isinstance(result["triage"], dict):
        triage_cmd = result["triage"].get("command")
        if triage_cmd:
            next_actions.append(f"Reproduce: {triage_cmd}")

    summary = f"Route: {route}. Dry-run: {dry_run}."
    output = {
        "summary": summary,
        "result": result,
        "next_actions": next_actions,
        "errors": errors,
    }
    print(json.dumps(output, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
