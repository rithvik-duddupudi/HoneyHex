# src/honeytrail/server.py
from __future__ import annotations

import os
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from honeytrail.db.store import TrailStore

app = Server("honey-trail")


def _db() -> TrailStore:
    default_db = str(Path.home() / ".honeytrail" / "default.db")
    raw = os.environ.get("HONEYTRAIL_DB_PATH", default_db)
    return TrailStore(Path(raw))


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="trail_session_open",
            description="Open or create a reasoning session.",
            inputSchema={
                "type": "object",
                "properties": {"label": {"type": "string"}},
                "required": [],
            },
        ),
        Tool(
            name="trail_append_thought",
            description="Append a thought node to the session; moves the head forward.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "monologue": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["session_id", "monologue"],
            },
        ),
        Tool(
            name="trail_append_tool",
            description=(
                "Append a tool-call node with name, input JSON, and output summary."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "tool_name": {"type": "string"},
                    "tool_input_json": {"type": "string"},
                    "tool_output_summary": {"type": "string"},
                },
                "required": ["session_id", "tool_name"],
            },
        ),
        Tool(
            name="trail_get_branch",
            description=(
                "Return the linear path from root to head with summaries "
                "(get-last-logic-branch)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "branch": {"type": "string"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="trail_rollback",
            description=(
                "Move the session head to the parent of the node matching "
                "before_substring."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "before_substring": {"type": "string"},
                },
                "required": ["session_id", "before_substring"],
            },
        ),
        Tool(
            name="trail_fork",
            description=(
                "Create a fork node from from_node_id and register a named branch."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "branch_name": {"type": "string"},
                    "from_node_id": {"type": "string"},
                },
                "required": ["session_id", "branch_name", "from_node_id"],
            },
        ),
        Tool(
            name="trail_merge",
            description=(
                "Create a merge node: current head (A) + named other_branch tip (B)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "other_branch": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["session_id", "other_branch"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:  # type: ignore[type-arg]
    store = _db()
    try:
        if name == "trail_session_open":
            sid = store.session_open(arguments.get("label") or "")
            return [TextContent(type="text", text=sid)]

        if name == "trail_append_thought":
            node_id = store.append_thought(
                session_id=arguments["session_id"],
                monologue=arguments["monologue"],
                summary=arguments.get("summary", ""),
            )
            return [TextContent(type="text", text=node_id)]

        if name == "trail_append_tool":
            node_id = store.append_tool(
                session_id=arguments["session_id"],
                tool_name=arguments["tool_name"],
                tool_input_json=arguments.get("tool_input_json", "{}"),
                tool_output_summary=arguments.get("tool_output_summary", ""),
            )
            return [TextContent(type="text", text=node_id)]

        if name == "trail_get_branch":
            sid = arguments["session_id"]
            branch = arguments.get("branch")
            if branch:
                store.checkout_branch(sid, branch)
            path = store.linear_path_to_head(sid)
            lines = [
                f"{n.id}\t{n.kind}\t{n.summary}\t{n.monologue[:200]}"
                for n in path
            ]
            return [TextContent(type="text", text="\n".join(lines))]

        if name == "trail_rollback":
            result = store.rollback_to_parent_of_match(
                arguments["session_id"], arguments["before_substring"]
            )
            msg = (
                f"rolled back: {result.previous_head_id} → {result.new_head_id}"
            )
            return [TextContent(type="text", text=msg)]

        if name == "trail_fork":
            fork_id = store.fork(
                session_id=arguments["session_id"],
                branch_name=arguments["branch_name"],
                from_node_id=arguments["from_node_id"],
            )
            return [TextContent(type="text", text=fork_id)]

        if name == "trail_merge":
            merge_id = store.merge_into_current(
                session_id=arguments["session_id"],
                other_branch=arguments["other_branch"],
                summary=arguments.get("summary", ""),
            )
            return [TextContent(type="text", text=merge_id)]

        return [TextContent(type="text", text=f"unknown tool: {name}")]
    finally:
        store.close()


async def run() -> None:
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())
