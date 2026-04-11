# HoneyHex

Distributed Ledger of Intelligence for multi-agent systems. See `agent_docs/` and `docs/PLAN-honeyhex-implementation.md`.

## Quickstart (pip only)

The core package is enough for local thought ledgers, Git-backed history, inspection, branching, bundles, and signing—no Redis, HTTP registry, or Docker required.

```bash
pip install honeyhex
cd your-agent-cell
hex cell init
hex commit -m "why I acted" --prompt "..." --scratchpad "..."
```

Run from an agent **cell root** (defaults to current directory). The ledger lives in `.honeyhex/`.

## Development setup

Contributors typically use an editable install with all optional stacks for tests and API work:

```bash
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## CLI (core)

```bash
hex commit -m "why I acted" --prompt "..." --scratchpad "..."
hex checkout -b my-hypothesis --cell .
hex cherry-pick <sha>
hex rebase-interactive --onto <ancestor-sha> --drop <sha1>,<sha2>
hex shadow --left-cmd "true" --right-cmd "sleep 9"
```

**Porcelain (local `.honeyhex/`):** `hex log` / `show` / `diff` (add `--json` for scripting), `hex remote` / `fetch` / `pull`, `hex merge` (runs **`post-merge`** when hooks enabled), `hex bundle create|replay`, `hex sign` / `hex verify` (set `HONEYHEX_SIGNING_KEY`), `hex git …` (passthrough `git -C .honeyhex`). Config: `.honeyhex/config.json` or **`config.toml`**. See `docs/SECURITY.md`, `docs/MANUAL-RUNBOOK.md`, and `docs/MERGE_POLICY.md`.

## Optional: mesh and central registry

These features install additional dependencies via extras; commands print a one-line `pip install 'honeyhex[…]'` hint if the extra is missing.

**Hive-Daemon (`pip install 'honeyhex[redis]'`):** set `HONEYHEX_REDIS_URL` / `HONEYHEX_CHANNEL`, then `hex daemon run`. Agents can `hex publish-head --agent <id>` after commits. For local development, `docker compose` in this repo is optional convenience only.

**Registry API (`pip install 'honeyhex[registry]'`):** set `HONEYHEX_DATABASE_URL` (PostgreSQL in production, e.g. `postgresql+psycopg://honeyhex:honeyhex@localhost:5432/honeyhex`), run `honeyhex-api`, then use `hex status`, `hex push --source … --target …` (runs **`pre-push`** when hooks are enabled), **`hex outbox enqueue` / `hex sync`** to queue PRs offline then flush, `hex vote --pr …`, `hex merge-quorum --pr …`, `hex rebase-global --commit …`.

**LLM validators (`pip install 'honeyhex[llm]'`):** configure provider keys (e.g. `OPENAI_API_KEY`), set `HONEYHEX_DEFAULT_MODEL` if needed, then `POST /api/v1/prs/{id}/llm-evaluate` or `hex llm-vote --pr <id>`. Tabular summaries: `honeyhex.eval.tables.summarize_tabular_rows`.

## Tests

Default `pytest` runs **core** tests only (no registry/LLM markers). Install `[dev]` and run the full suite when you have all extras:

```bash
pytest
pytest -o addopts=   # run all tests including registry + LLM markers
ruff check src tests
mypy src
```
