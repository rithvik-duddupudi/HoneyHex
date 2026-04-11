# HTTP API (`honeyhex-api`)

The registry service is a **FastAPI** app mounted at **`/api/v1`**.

**Run:** `honeyhex-api` (requires **`pip install 'honeyhex[registry]'`**).  
**Bind:** **`HONEYHEX_REGISTRY_HOST`** (default `127.0.0.1`), **`HONEYHEX_REGISTRY_PORT`** (default `8765`).  
**Database:** **`HONEYHEX_DATABASE_URL`** (SQLAlchemy URL; defaults to a local SQLite file if unset).

## Endpoints (prefix `/api/v1`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/status` | Swarm status, agents, open PRs (`swarm_id` query, default `default`) |
| GET | `/prs/{pr_id}` | Single pull request |
| POST | `/prs` | Create pull request (body: swarm, source/target agents, `head_sha`, title) |
| POST | `/prs/{pr_id}/votes` | Validator vote (`validator_id`, `approved`) |
| POST | `/prs/{pr_id}/merge` | Merge if quorum satisfied |
| POST | `/prs/{pr_id}/reject` | Reject PR (optional `reason` query) |
| POST | `/prs/{pr_id}/llm-evaluate` | LLM validator vote (needs **`[llm]`**; body: `model`, `validator_id`) |
| POST | `/agents/{agent_id}/head` | Upsert agent HEAD (`head_sha` query, optional `swarm_id`, `branch`) |
| POST | `/blackboard/append` | Append blackboard entry |
| GET | `/blackboard` | List blackboard (`swarm_id` query) |

Detailed request/response models live in **`honeyhex.registry.schemas`** and OpenAPI at **`/docs`** when the server runs.

## Redis side effects

If **`HONEYHEX_REDIS_URL`** is set on the API process, creating a PR may publish a **`pr_created`** event to **`HONEYHEX_CHANNEL`** for mesh subscribers.
