from __future__ import annotations

import argparse
import ast
import json
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "vm_server" / "tools"
CATALOG_JSON = REPO_ROOT / "memory" / "tool_catalog.json"
CATALOG_MD = REPO_ROOT / "memory" / "tool_catalog.md"


KEYWORD_TAGS = {
    "notion": "notion",
    "tool request": "backlog",
    "tool requests": "backlog",
    "backlog": "backlog",
    "health": "health",
    "mood": "mood",
    "serendipity": "serendipity",
    "system": "system",
    "hello": "hello",
    "greet": "hello",
    "calendar": "calendar",
    "task": "tasks",
    "tasks": "tasks",
}


def _infer_tags(filename: str, docstring: str) -> list[str]:
    haystack = f"{filename} {docstring}".lower()
    tags = set()
    for key, tag in KEYWORD_TAGS.items():
        if key in haystack:
            tags.add(tag)
    for token in filename.replace(".py", "").split("_"):
        if token and token not in {"tool", "tools"}:
            tags.add(token)
    return sorted(tags)


def _extract_tool_name(decorator: ast.expr, func_name: str) -> str | None:
    if isinstance(decorator, ast.Attribute):
        if decorator.attr == "tool":
            return func_name
    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
        if decorator.func.attr == "tool":
            for keyword in decorator.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                    if isinstance(keyword.value.value, str):
                        return keyword.value.value
            return func_name
    return None


def _extract_args(args_node: ast.arguments) -> list[dict]:
    arg_names = [arg.arg for arg in args_node.args]
    defaults = [None] * (len(arg_names) - len(args_node.defaults)) + list(
        args_node.defaults
    )
    items: list[dict] = []
    for name, default in zip(arg_names, defaults):
        if name in {"self", "mcp"}:
            continue
        default_repr = ast.unparse(default) if default is not None else None
        items.append({"name": name, "default": default_repr})
    for arg in args_node.kwonlyargs:
        items.append({"name": arg.arg, "default": None})
    return items


def _extract_docstring(node: ast.AST) -> str:
    docstring = ast.get_docstring(node) or ""
    docstring = docstring.strip()
    if not docstring:
        return ""
    return docstring.split("\n\n")[0].strip()


def _parse_tools_from_file(path: Path) -> list[dict]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    tools: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            tool_name = None
            for decorator in node.decorator_list:
                tool_name = _extract_tool_name(decorator, node.name)
                if tool_name:
                    break
            if tool_name:
                docstring = _extract_docstring(node)
                tools.append(
                    {
                        "name": tool_name,
                        "args": _extract_args(node.args),
                        "doc": docstring,
                    }
                )
    if not tools:
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "register":
                docstring = _extract_docstring(node)
                tools.append(
                    {
                        "name": f"{path.stem}.register",
                        "args": _extract_args(node.args),
                        "doc": docstring or "Registers MCP tools (no decorators found).",
                    }
                )
    for tool in tools:
        tool["module"] = path.stem
        tool["path"] = str(path.relative_to(REPO_ROOT))
        tool["tags"] = _infer_tags(path.name, tool.get("doc", ""))
    return tools


def build_catalog() -> dict:
    tools: list[dict] = []
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if path.name in {"__init__.py", "registry.py"}:
            continue
        tools.extend(_parse_tools_from_file(path))
    tools_sorted = sorted(tools, key=lambda item: item["name"])
    catalog = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool_count": len(tools_sorted),
        "tools": tools_sorted,
    }
    CATALOG_JSON.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_JSON.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    CATALOG_MD.write_text(_render_markdown(catalog), encoding="utf-8")
    return catalog


def _render_markdown(catalog: dict) -> str:
    lines = [
        "# MCP Tool Catalog",
        "",
        f"Generated: {catalog['generated_at']}",
        f"Total tools: {catalog['tool_count']}",
        "",
    ]
    for tool in catalog["tools"]:
        args = ", ".join(
            f"{arg['name']}={arg['default']}" if arg["default"] is not None else arg["name"]
            for arg in tool.get("args", [])
        )
        lines.extend(
            [
                f"## {tool['name']}",
                f"- Module: `{tool['module']}`",
                f"- Path: `{tool['path']}`",
                f"- Args: `{args or 'none'}`",
                f"- Tags: {', '.join(tool.get('tags', [])) or 'none'}",
                f"- Description: {tool.get('doc') or 'No description.'}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a catalog of VM MCP tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build", help="Scan vm_server/tools and write catalog files.")
    args = parser.parse_args()
    if args.command == "build":
        catalog = build_catalog()
        print(
            f"Wrote {catalog['tool_count']} tools to "
            f"{CATALOG_JSON.relative_to(REPO_ROOT)} and {CATALOG_MD.relative_to(REPO_ROOT)}"
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
