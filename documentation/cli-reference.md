# CLI reference (`hex`)

Unless noted, commands accept **`--cell <path>`** to use a cell other than the current working directory.

Global: **`hex --help`**, **`hex <command> --help`**.

---

## Core ledger

### `hex cell init`

Initialize `.honeyhex/` and default config. Optional **`--hook-stubs`** installs sample hook scripts and enables hooks in config.

```bash
hex cell init
hex cell init --hook-stubs
```

### `hex commit`

Record a thought-commit. **`-m` / `--message`** is required (internal monologue title).

| Option | Meaning |
|--------|---------|
| `--prompt` | Prompt snapshot |
| `--rag-context` | RAG context text |
| `--scratchpad` | Scratchpad text |
| `--tools-json` | JSON array of tool output objects |
| `--payload-file` | JSON file with `prompt`, `rag_context`, `scratchpad`, `tool_outputs` (replaces individual flags) |

Runs **`pre-thought`** / **`post-thought`** hooks when hooks are enabled.

### `hex checkout`

Create and switch to a branch in `.honeyhex`. Requires **`-b` / `--branch`** (new branch name).

### `hex cherry-pick`

Cherry-pick a commit SHA onto the current branch.

### `hex rebase-interactive`

Interactive-style rebase: **`--onto`**, optional **`--drop`** (comma-separated SHAs), optional **`--fix-message`**.

### `hex shadow`

Run two shell commands concurrently; first successful exit wins (shadow-branch race). **`--left-cmd`**, **`--right-cmd`**.

---

## Inspection (porcelain)

### `hex log`

List thought-commits. Options: **`-n` / `--max-count`**, **`--oneline`**, **`--graph`**, **`--json`**.

### `hex show`

Show one revision (default **HEAD**). Optional **`--json`**.

### `hex diff`

Diff `thoughts/snapshot.json` between revisions (default **HEAD~1** vs **HEAD**). Optional **`--json`**.

### `hex blame`

Git blame on `thoughts/snapshot.json`. **`--rev`**, **`--json`**.

### `hex reflog`

**`.honeyhex`** reflog. **`-n` / `--max-count`**.

### `hex tag`

Create a lightweight tag at HEAD: **`hex tag <name>`**.

---

## Swarm remotes (local peers)

### `hex remote`

- **`hex remote list`** — JSON map of remotes  
- **`hex remote add <name> <path-or-url>`** — peer cell path or Git URL  
- **`hex remote remove <name>`**

### `hex fetch` / `hex pull`

**`hex fetch <remote>`** — fetch from configured remote.  
**`hex pull <remote>`** — fetch and merge; optional second argument for branch ref.

---

## Merge and hooks

### `hex merge`

**`hex merge <branch>`** — Git merge inside `.honeyhex`. Runs **`post-merge`** when hooks allow.

### `hex hook`

**`hex hook run <name>`** — run a hook manually (e.g. `pre-thought`).

---

## Bundles and signing

### `hex bundle create` / `hex bundle replay`

- **`hex bundle create <output.zip>`** — export manifest + thoughts. Optional **`-n` / `--max-count`**.
- **`hex bundle replay <bundle.zip>`** — import as new commits into the cell.

### `hex sign` / `hex verify`

HMAC-SHA256 sidecar for a commit (default **HEAD**). Requires **`HONEYHEX_SIGNING_KEY`**.

---

## Git passthrough

### `hex git …`

Forwards to **`git -C .honeyhex`** with any extra arguments:

```bash
hex git status
hex git log -1
```

---

## Hive-Daemon and mesh (needs **`[redis]`**)

### `hex daemon run`

Long-running subscriber on Redis Pub/Sub. Optional **`--redis-url`**, **`--channel`**.

### `hex publish-head`

Publish this cell’s `.honeyhex` HEAD to the mesh. **`--agent`** (required), optional **`--redis-url`**, **`--channel`**.

---

## Registry and swarm CLI (needs **`[registry]`** for HTTP; optional running API)

Commands talk to **`HONEYHEX_REGISTRY_URL`**.

| Command | Purpose |
|---------|---------|
| **`hex status`** | GET aggregated swarm status (`--swarm`). |
| **`hex push`** | POST a PR (`--source`, `--target`, optional `--cell`, `--swarm`, `--title`). Runs **`pre-push`** when hooks allow. |
| **`hex vote`** | POST validator vote (`--pr`, `--validator`, `--approve` / `--reject`). |
| **`hex merge-quorum`** | POST merge if quorum satisfied (`--pr`). |
| **`hex rebase-global`** | Publish truth commit on Redis (`--commit`; mesh / daemon). Needs **`[redis]`** for Redis client. |
| **`hex db-url`** | Print resolved **`HONEYHEX_DATABASE_URL`** (registry / API debugging). |

If the **`[registry]`** or **`[redis]`** extra is missing, these commands exit with an install hint (no import-time failure for `hex --help`).

---

## Outbox (offline PR queue)

Local queue under **`.honeyhex/outbox/`**.

| Command | Purpose |
|---------|---------|
| **`hex outbox enqueue`** | Queue a PR intent (`--source`, `--target`, optional `--cell`, `--swarm`, `--title`). |
| **`hex outbox list`** | List pending JSON items. |
| **`hex outbox sync`** | POST pending items to the registry (`--refresh-head` optional). |
| **`hex sync`** | Alias for **`hex outbox sync`**. |

Enqueue/list work with core install; sync needs registry HTTP client (**`[registry]`**).

---

## LLM (needs **`[llm]`** + registry for HTTP)

### `hex llm-vote`

POST LLM evaluation + vote to **`/api/v1/prs/{id}/llm-evaluate`**. Options: **`--pr`**, **`--validator-id`**, **`--model`**.

---

## Python API (tabular summaries)

With **`[llm]`** installed: **`honeyhex.eval.tables.summarize_tabular_rows`** summarizes list-of-dicts using Polars (see package docstrings).
