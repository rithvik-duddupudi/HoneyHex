# PLAN: HoneyHex — Full Project Implementation

## Phase -1: Context check (completed)

| Source | Summary |
|--------|---------|
| **OS** | macOS (darwin); use bash/zsh paths. No `CODEBASE.md` in repo; authoritative specs are `agent_docs/`. |
| **Product** | HoneyHex = **Distributed Ledger of Intelligence** for multi-agent systems: Agent-as-Repository (“Cell”), thought-commits, Hivemind mesh, Git-like DAG for LLM traces. |
| **Stack (design)** | Python 3.12+ (strict typing), uv/poetry, PostgreSQL (registry/PRs), Redis (pub/sub, Hive-Daemon), GitPython + local JSON/Markdown for `.honeyhex/`, LiteLLM, Pydantic v2, polars, Typer or Click, pyfilesystem2. |
| **Philosophy** | Immutable past state; LLMs behind Pydantic; virtual FS until merge; daemon-first sync. |
| **Patterns** | ThoughtCommit + CommitManager; CRDT blackboard for shared state; shadow-branch / async quorum; Proposer/Validator for `--quorum`. |

---

## Phase 0: Socratic gate — assumptions & open questions

**Assumptions (proceed unless you override):**

1. **MVP scope**: Deliver a **vertical slice**: local `.honeyhex/` DAG + `hex commit` + minimal CLI; then Hive-Daemon + Redis; then registry API + PostgreSQL + inter-agent PR flow; then swarm commands (`status`, `merge --quorum`, `rebase --global`) incrementally.
2. **Deployment**: Development uses Docker (or local services) for Postgres 18 and Redis; production topology is out of scope for first implementation pass unless specified.
3. **Agent runtime**: “Agents” are represented as **processes or SDK clients** using the same Python library—no separate mobile/web app in v1.

**Questions to resolve before or during implementation:**

- Target Postgres version in dev (design says v18 — confirm images/availability).
- Auth model for registry API (API keys, mTLS, or deferred for local-only MVP).
- Whether `hex checkout -b` uses **multiprocessing** vs **asyncio** as default (design allows both).

---

## Python environment (mandatory for all implementers)

Use the project virtualenv and **uv** for dependencies:

```bash
source .venv/bin/activate
uv pip install <dependency>
```

- Create the venv once if missing: `uv venv .venv` then activate as above.
- Pin versions in `pyproject.toml` / lockfile as the project adopts them.
- **Note:** Standard activation path is `.venv/bin/activate` (not `.venv/activate`).

---

## Project type

| Field | Value |
|-------|--------|
| **Type** | **BACKEND** — CLI + daemons + APIs + databases (no primary web UI in spec). |
| **Primary agents** | `backend-specialist`, `database-architect`; `security-auditor` before exposing network services; `test-engineer` for pytest/integration. |
| **Avoid for v1** | `frontend-specialist` / `mobile-developer` unless a separate dashboard is explicitly added. |

---

## Success criteria (measurable)

- [ ] `.honeyhex/` stores an immutable DAG (blobs/trees/commits) with parent links and hashes; no silent overwrite of history.
- [ ] `hex commit` snapshots prompt, RAG context, scratchpad, and tool outputs per design.
- [ ] Hive-Daemon subscribes to Redis and tracks agent HEADs; can signal global rebase events.
- [ ] Registry persists swarm topology + PR metadata in PostgreSQL; inter-agent PR workflow matches TECHNICAL_DESIGN §1.4.
- [ ] Pydantic validates LLM-facing structures; LiteLLM used behind a single gateway abstraction.
- [ ] CLI exposes commands from PRD §3 (staged: micro-level first, then macro-level).

---

## Proposed repository layout (initial target)

```
honeyhex/
  pyproject.toml          # uv, ruff, mypy, pytest
  src/honeyhex/
    cli/                  # Typer app: hex commands
    ledger/               # .honeyhex DAG, GitPython integration
    commit/               # ThoughtCommit, CommitManager, StateDiff
    daemon/               # Hive-Daemon (Redis listener)
    registry/             # DB models, PR repository, API (e.g. FastAPI if chosen)
    mesh/                 # CRDT / blackboard, quorum merge
    llm/                  # LiteLLM + Pydantic validators
    vfs/                  # pyfilesystem2 sandbox
  tests/
  docker-compose.yml      # postgres + redis (optional dev)
```

(Adjust names to match chosen package structure; keep boundaries: ledger vs registry vs daemon.)

---

## Implementation phases & functionality

### Phase 1 — Foundation & tooling

| Functionality | Notes |
|---------------|--------|
| Package layout, `pyproject.toml`, strict typing baseline | mypy/ruff/pytest wired. |
| Core models | `ThoughtCommit`, `StateDiff`, hashes — Pydantic v2. |
| Virtual FS sandbox | pyfilesystem2; isolate until `hex merge` to real disk. |

**Subagent guidelines:** `backend-specialist` + `python-patterns` skill; keep modules small; no I/O without interfaces for testing.

---

### Phase 2 — Local ledger & `hex commit`

| Functionality | Notes |
|---------------|--------|
| `.honeyhex/` layout | Blobs, trees, commits; GitPython + serialization per TECHNICAL_DESIGN. |
| `hex commit` | End-of-cycle snapshot: prompt, RAG, scratchpad, tool outputs. |
| Immutability | Append-only; corrections via new commits / rebase flows, not mutation. |

**Subagent guidelines:** `backend-specialist`; align with `CODE_PATTERNS` Thought-Commit pattern; `test-engineer` for golden-file or hash assertions on DAG shape.

---

### Phase 3 — Branching, rebase, cherry-pick (micro-CLI)

| Command | Behavior |
|---------|----------|
| `hex checkout -b <hypothesis>` | Shadow-branch: two parallel executions; first valid result wins; cancel sibling (asyncio or multiprocessing per decision). |
| `hex rebase --interactive` | Rewind, drop bad commits, re-apply with fix prompt. |
| `hex cherry-pick <commit-hash>` | Apply a thought-pattern from another branch/agent context. |

**Subagent guidelines:** `backend-specialist` + `systematic-debugging` if concurrency bugs; document cancellation and resource cleanup.

---

### Phase 4 — Hive-Daemon & Redis

| Functionality | Notes |
|---------------|--------|
| Background process | Listens on Redis Pub/Sub; tracks HEAD per agent. |
| Events | Triggers for global rebase when “truth” commits publish. |
| Config | Connection URLs, channel names, graceful shutdown. |

**Subagent guidelines:** `backend-specialist`; `redis-development` skill for channels, timeouts, avoid blocking commands in production; `devops-engineer` for compose and healthchecks.

---

### Phase 5 — Central registry (PostgreSQL) & inter-agent PRs

| Functionality | Notes |
|---------------|--------|
| Schema | Swarms, agents, PRs, relationships; migrations (e.g. Alembic). |
| Flow | Agent A → `hex push --target=AgentB` → registry row → daemon notifies B → validation → merge/reject. |
| API layer | REST or minimal RPC — versioned, Pydantic request/response models. |

**Subagent guidelines:** `database-architect` for schema/indexes; `backend-specialist` for API; `security-auditor` for injection, authz, and secrets handling before any expose beyond localhost.

---

### Phase 6 — Swarm operations (macro-CLI)

| Command | Behavior |
|---------|----------|
| `hex status` | Hive tree: HEAD per agent, branches. |
| `hex merge --quorum` | Proposer/Validator; background CI for “thought tests”; weighted/quorum approval. |
| `hex rebase --global` | Coordinate pause/pull/rebase across agents (with daemon). |
| CRDT blackboard | Shared ordered updates without global locks (CODE_PATTERNS §2). |

**Subagent guidelines:** `backend-specialist` + `architecture` skill for consensus trade-offs; `test-engineer` for multi-agent integration tests (containers or mocked Redis/Postgres).

---

### Phase 7 — LLM gateway & validators

| Functionality | Notes |
|---------------|--------|
| LiteLLM | Single entry for models; structured outputs validated by Pydantic. |
| Validator agents | Lightweight approve/reject for quorum (`LLM-Raft` pattern). |
| polars | Large tabular evaluations in validator/CI path when needed. |

**Subagent guidelines:** `backend-specialist`; strict schemas; no raw dict passes across module boundaries.

---

## Task dependency graph (high level)

```
Phase 1 (tooling/models/VFS)
    → Phase 2 (ledger + hex commit)
        → Phase 3 (checkout/rebase/cherry-pick)
            → Phase 4 (daemon + Redis)
                → Phase 5 (Postgres + PR pipeline)
                    → Phase 6 (swarm CLI + CRDT + quorum)
                        → Phase 7 (LLM + validators + polars)
                            → Phase X (verification)
```

Parallelism: Phase 7 LiteLLM adapter can start after Phase 2 models stabilize; do not block Phase 2 on Phase 7 beyond interface types.

---

## Subagent assignment matrix (quick reference)

| Concern | Subagent | Skill |
|---------|----------|--------|
| CLI & services | `backend-specialist` | `python-patterns`, `nodejs-best-practices` N/A — use Python |
| Postgres schema/migrations | `database-architect` | `database-design` |
| Redis pub/sub, performance | `backend-specialist` | `redis-development` |
| Consensus / merge design | `backend-specialist` or orchestration | `architecture` |
| Security before network expose | `security-auditor` | `vulnerability-scanner` |
| Tests | `test-engineer` | `testing-patterns`, `tdd-workflow` |
| Infra compose/deploy | `devops-engineer` | `deployment-procedures` |

---

## Phase X: Verification (definition of done)

Run **after** each milestone and fully before declaring release-ready:

| Step | Verify |
|------|--------|
| 1 | `source .venv/bin/activate` — all commands use this env. |
| 2 | `uv pip sync` or equivalent — reproducible deps. |
| 3 | `ruff check`, `mypy` (if enabled), `pytest` — green. |
| 4 | Local integration: Redis + Postgres up (e.g. `docker compose up -d`); daemon + one agent client smoke test. |
| 5 | CLI smoke: `hex commit` creates readable DAG; `hex status` reflects seeded data. |
| 6 | Security pass: no secrets in repo; `security-auditor` checklist for API/registry. |

**Manual:**

- [ ] AGENT.md rules respected: no mutation of historical commits; virtualization until merge.
- [ ] Socratic assumptions reviewed — update Phase 0 if product scope changed.

**Phase X completion block (fill when done):**

```markdown
## PHASE X COMPLETE
- Lint/type/tests: [Pass/Fail]
- Integration (Redis/Postgres): [Pass/Fail]
- CLI smoke: [Pass/Fail]
- Date: YYYY-MM-DD
```

---

## File delivered

| Deliverable | Path |
|-------------|------|
| This plan | `docs/PLAN-honeyhex-implementation.md` |

---

*Plan mode: no application code was written; this document is the sole planning artifact for the requested location.*
