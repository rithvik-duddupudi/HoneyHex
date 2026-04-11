# Configuration

## Cell layout

After `hex cell init`, the cell contains:

- **`.honeyhex/`** — Git repo for the thought ledger (commits, branches, tags).
- **`.honeyhex/config.json`** — created if missing; can be replaced or supplemented by **`config.toml`** in the same directory.

## Config files

HoneyHex reads **`config.toml`** or **`config.json`** under `.honeyhex/` (TOML preferred for readability). Use them for default branch, hook paths, and hook mode.

Typical keys include:

- **`default_branch`** — Git branch name for the ledger.
- **`hooks_mode`** — `off` (default), `safe`, or `full` (see [Security](security.md)).
- **`hooks`** — map of hook names to script paths **under `.honeyhex/`** (e.g. `pre-thought` → `hooks/pre-thought.sh`).

## Environment variables

| Variable | Purpose |
|----------|---------|
| **`HONEYHEX_HOOKS`** | Override hook mode: `off`, `safe`, or `full`. |
| **`HONEYHEX_SIGNING_KEY`** | UTF-8 secret for `hex sign` / `hex verify` (HMAC). |
| **`HONEYHEX_REDIS_URL`** | Redis URL for daemon / `publish-head` / `rebase-global` (default `redis://127.0.0.1:6379/0`). |
| **`HONEYHEX_CHANNEL`** | Pub/Sub channel (default `honeyhex:mesh`). |
| **`HONEYHEX_REGISTRY_URL`** | Base URL of the registry HTTP API for `hex push`, `hex status`, outbox sync (default `http://127.0.0.1:8765`). |
| **`HONEYHEX_DATABASE_URL`** | SQLAlchemy URL for the registry database (used by **`honeyhex-api`**; default SQLite file). |
| **`HONEYHEX_REGISTRY_HOST`** / **`HONEYHEX_REGISTRY_PORT`** | Bind address for **`honeyhex-api`** (defaults `127.0.0.1:8765`). |
| **`HONEYHEX_DEFAULT_MODEL`** | Optional default LLM model name for LLM features. |
| **`OPENAI_API_KEY`** (and other provider vars) | Used when **`[llm]`** extra is installed for validator calls. |

## Hooks (summary)

- **`off`** — no hooks run.
- **`safe`** — `pre-thought` and `post-thought` around `hex commit`.
- **`full`** — also **`pre-push`** (before registry PR POST / outbox sync) and **`post-merge`** (after `hex merge`).

Details: [Security](security.md).
