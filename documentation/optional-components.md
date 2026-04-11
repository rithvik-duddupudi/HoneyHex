# Optional components and extras

Core **`pip install honeyhex`** includes the ledger, porcelain, branching, bundles, and local outbox enqueue/list. Everything below is **optional** and shipped as **extras**.

## Extra matrix

| Extra | Install | Brings in |
|-------|---------|-----------|
| **`redis`** | `pip install 'honeyhex[redis]'` | `redis` — Hive-Daemon, `hex publish-head`, `hex rebase-global`, mesh announcements |
| **`registry`** | `pip install 'honeyhex[registry]'` | FastAPI, Uvicorn, SQLAlchemy, httpx — **`honeyhex-api`**, `hex push` / `status` / `vote` / merge, outbox sync |
| **`llm`** | `pip install 'honeyhex[llm]'` | LiteLLM, Polars — LLM validator, `summarize_tabular_rows`, `/llm-evaluate` endpoint |
| **`dev`** | `pip install -e ".[dev]"` | All of the above plus pytest, ruff, mypy (contributors) |

If a command needs an extra you have not installed, the CLI prints a one-line **`pip install 'honeyhex[…]'`** hint and exits cleanly.

## Hive-Daemon and Redis

1. Install **`[redis]`**.
2. Set **`HONEYHEX_REDIS_URL`** and optionally **`HONEYHEX_CHANNEL`**.
3. Run **`hex daemon run`** on a host that can reach Redis.

Agents publish HEAD updates with **`hex publish-head --agent <id>`** after local commits.

## Central registry (HTTP API)

1. Install **`[registry]`**.
2. Set **`HONEYHEX_DATABASE_URL`** (PostgreSQL in production; SQLite is fine for local dev).
3. Run **`honeyhex-api`** (bind via **`HONEYHEX_REGISTRY_HOST`** / **`HONEYHEX_REGISTRY_PORT`**).
4. Point clients with **`HONEYHEX_REGISTRY_URL`** (default `http://127.0.0.1:8765`).

Use **`hex push`**, **`hex status`**, **`hex vote`**, **`hex merge-quorum`**, and **`hex outbox sync`** / **`hex sync`** against that service.

## LLM validators

1. Install **`[llm]`** (and usually **`[registry]`** for the HTTP API).
2. Configure provider environment variables (e.g. **`OPENAI_API_KEY`**).
3. Call **`POST /api/v1/prs/{id}/llm-evaluate`** or **`hex llm-vote`**.

## Docker Compose (development only)

The repository may include **`docker-compose.yml`** with Redis and Postgres for local integration testing. It is **not** required for core `hex` usage—only for optional services.
