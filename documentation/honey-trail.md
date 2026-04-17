# Honey-Trail MCP

Honey-Trail is a **reasoning debugger** for AI agents. It records every internal monologue and tool call in a structured SQLite database, exposes a `trail_get_branch` tool so an agent can inspect its full reasoning history, and supports rollback, named branches, and merge nodes — conceptually "Git for agent thought."

Honey-Trail runs as a **stdio MCP server** using the official Python `mcp` package and integrates alongside HoneyHex's Git ledger under `.honeyhex/`.

---

## Installation

```bash
pip install honeyhex[honeytrail]
```

Or from source in the repo:

```bash
pip install -e ".[honeytrail]"
```

**Requirements:** Python 3.12+, `mcp>=1.2.0` (installed automatically with the extra).

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `HONEYTRAIL_DB_PATH` | `~/.honeytrail/default.db` | Path to the SQLite database file |
| `HONEYTRAIL_SESSION_ID` | _(unset)_ | UUID for the active agent session; set by the MCP client before each tool batch |
| `HONEYTRAIL_HEX_CELL` | _(unset)_ | Absolute path to a HoneyHex cell root for optional export/sync |

---

## Running the server

```bash
# Default DB location
honeytrail-mcp

# Custom DB path
HONEYTRAIL_DB_PATH=/path/to/project.db honeytrail-mcp
```

The server reads from stdin and writes to stdout using the MCP stdio transport.

---

## MCP client configuration

### Cursor

Add to `~/.cursor/mcp.json` (or the project-level `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "honey-trail": {
      "command": "honeytrail-mcp",
      "env": {
        "HONEYTRAIL_DB_PATH": "/path/to/trail.db"
      }
    }
  }
}
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "honey-trail": {
      "command": "honeytrail-mcp",
      "env": {
        "HONEYTRAIL_DB_PATH": "~/.honeytrail/default.db"
      }
    }
  }
}
```

### Generic stdio client

```bash
honeytrail-mcp
# server speaks MCP over stdin/stdout
```

---

## MCP tools reference

| Tool | Required args | Returns | Description |
|------|---------------|---------|-------------|
| `trail_session_open` | _(none)_ | `session_id` | Open or create a reasoning session |
| `trail_append_thought` | `session_id`, `monologue` | `node_id` | Append a thought node; moves the head forward |
| `trail_append_tool` | `session_id`, `tool_name` | `node_id` | Append a tool-call node with input JSON + output summary |
| `trail_get_branch` | `session_id` | newline-separated path | Return linear path from root → head with summaries |
| `trail_rollback` | `session_id`, `before_substring` | confirmation string | Move head to parent of node matching the substring |
| `trail_fork` | `session_id`, `branch_name`, `from_node_id` | `node_id` | Create a fork node and register a named branch |
| `trail_merge` | `session_id`, `other_branch` | `node_id` | Merge another branch's tip into the current head |

### Optional args

- `trail_session_open`: `label` (string) — human-readable session name
- `trail_append_thought`: `summary` (string) — short description of the thought
- `trail_append_tool`: `tool_input_json`, `tool_output_summary` (strings)
- `trail_get_branch`: `branch` (string) — check out a named branch before returning the path
- `trail_merge`: `summary` (string) — description of the merge decision

---

## Typical agent session

```
1. trail_session_open(label="fix auth bug")
   → "a1b2c3d4..."

2. trail_append_thought(session_id, monologue="I'll start by reading the auth module")
3. trail_append_tool(session_id, tool_name="read_file", tool_input_json='{"path":"src/auth.py"}')
4. trail_append_thought(session_id, monologue="I think I should drop the users table to reset")

5. # Realize step 4 is wrong — roll back before it
   trail_rollback(session_id, before_substring="drop the users table")

6. # Resume from the safe point
   trail_append_thought(session_id, monologue="Better to add a migration instead")

7. # Review the current clean reasoning path
   trail_get_branch(session_id)
```

---

## Branching and merging

```
trail_fork(session_id, branch_name="approach-b", from_node_id=<node_id>)

# switch to the new branch
trail_append_thought(session_id, ...)   # builds on approach-b

# merge approach-b result back
trail_merge(session_id, other_branch="main", summary="approach-b was faster")
```

---

## Database

Honey-Trail writes to a single SQLite file (default `~/.honeytrail/default.db`). The schema is append-only: rollback moves the session head pointer without deleting history.

Tables: `sessions`, `nodes`, `branches`.

The `state_json` column on each node can store arbitrary structured state in a HoneyHex-compatible `StateDiff` shape (`prompt`, `rag_context`, `scratchpad`, `tool_outputs`, `session_id`, `task`, `model`) for optional export via `hex commit`.

---

## Operator runbook

### Check server is reachable

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}' \
  | HONEYTRAIL_DB_PATH=/tmp/test.db honeytrail-mcp
```

Expect a JSON `result` response with `serverInfo.name: "honey-trail"`.

### Inspect the database directly

```bash
sqlite3 ~/.honeytrail/default.db \
  "SELECT id, kind, summary, created_at FROM nodes ORDER BY created_at DESC LIMIT 20;"
```

### Reset a session head manually

```bash
sqlite3 ~/.honeytrail/default.db \
  "UPDATE sessions SET head_node_id = '<node_id>' WHERE id = '<session_id>';"
```

### Rotate / archive the DB

```bash
mv ~/.honeytrail/default.db ~/.honeytrail/archive-$(date +%Y%m%d).db
# Next honeytrail-mcp invocation auto-creates a fresh default.db
```
