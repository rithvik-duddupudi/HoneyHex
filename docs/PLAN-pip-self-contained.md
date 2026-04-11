# PLAN: Maximum local functionality, pip-only (no mandatory outside services)

## Phase -1: Context check

| Item | Notes |
|------|--------|
| **Goal** | HoneyHex should be **fully usable after `pip install honeyhex`** (or `pip install -e .`) with **no** required Redis, Postgres, HTTP registry, or Docker. Optional features stay behind **extras** and clearly separated. |
| **“Maximum functionality”** | Preserve everything that can run **offline / local-only**: thought ledger (`.honeyhex/`), Git-backed history, inspection (`log`/`show`/`diff`), branching, hooks, bundle/replay, signing, local swarm remotes (`file:` / paths), `hex git`, outbox **as a local queue** if registry sync is not installed. |
| **Non-goals** | Removing Git from the host machine (GitPython still shells to `git`). Removing optional value for users who *do* want registry/Redis (keep as extras). |

---

## Phase 0: Socratic gate — assumptions

1. **Single wheel / sdist** still ships **one** package; “removal” means **not importing** registry/redis code on default code paths and **not documenting** those flows as required setup.
2. **Extras** remain valid: `pip install honeyhex[registry,redis,llm]` for teams that want them.
3. **Outbox `hex sync`** today POSTs to an HTTP registry. For self-containment, either **document as optional** only, or **plan a follow-up** to no-op / warn when `httpx`/registry extra absent (implementation phase, not this doc).
4. **Docker Compose** is **dev convenience only**, never a prerequisite for end users.

**Open question (resolve in implementation):** Should the default `pip install honeyhex` **exclude** `fastapi`, `sqlalchemy`, `redis`, `httpx` from core dependencies entirely (strict), or keep them as unused deps (not recommended)? **Recommendation:** strict — core `pyproject` dependencies = pydantic, typer, GitPython, fs (and stdlib); everything else = extras.

---

## Recommended implementation order

| Order | Theme |
|-------|--------|
| **1** | Inventory & dependency split (`pyproject.toml` core vs extras). |
| **2** | Import boundaries: lazy/optional imports for registry, redis, llm, httpx. |
| **3** | CLI: hide or soft-fail commands that need missing extras with a clear one-liner install hint. |
| **4** | Docs & README: “pip only” quickstart first; registry/redis/LLM in an “Optional services” section. |
| **5** | Tests: default CI runs **core** tests only; optional job with extras for integration. |

---

## A. What to remove from the *default* user experience (not necessarily delete code)

| Item | Action |
|------|--------|
| **Implied requirement for Postgres / `honeyhex-api`** | README and CLI help must not read as “step 1: start API.” Move to **Optional: central registry**. |
| **Implied requirement for Redis / daemon** | Same: **Optional: Hive-Daemon** for mesh pub/sub. |
| **`docker-compose.yml` as setup path** | Keep in repo for contributors; label **development only** in README. |
| **Default env vars** pointing at localhost services | OK to keep as *defaults for extras*, but core docs should not tell users to set `HONEYHEX_REGISTRY_URL` to use basic `hex commit`. |
| **LLM / Polars as core** | Already extra; ensure `hex llm-vote` fails with install hint, not import error at startup. |

---

## B. What to remove or relocate in *packaging* (dependencies)

| Dependency group | Suggested location |
|-------------------|-------------------|
| `fastapi`, `uvicorn`, `sqlalchemy`, `httpx` | **`[registry]`** extra only (registry API client + any CLI that calls HTTP registry). |
| `redis` | **`[redis]`** extra (daemon, `publish-head`, mesh Redis). |
| `litellm`, `polars` | **`[llm]`** extra (unchanged). |
| **Core** | `pydantic`, `typer`, `GitPython`, `fs` — sufficient for local ledger + CLI porcelain. |

**Note:** After split, `import honeyhex` and `hex --help` must not execute imports that **require** missing extras (use lazy imports inside command functions).

---

## C. CLI commands vs extras (behavior matrix)

| Command / area | Core (no extras) | Needs extra |
|----------------|------------------|-------------|
| `hex commit`, `log`, `show`, `diff`, `checkout`, `cherry-pick`, `rebase-interactive`, `shadow`, `merge`, `blame`, `reflog`, `tag`, `remote`, `fetch`, `pull`, `hook`, `cell init`, `bundle`, `sign`, `verify`, `git` | Yes | — |
| `hex outbox enqueue`, `hex outbox list` | Yes (local JSON queue) | — |
| `hex outbox sync`, `hex sync`, `hex push`, `hex status`, `hex vote`, `hex merge-quorum` | No | **`[registry]`** (+ running API if calling live service) |
| `hex daemon run`, `hex publish-head`, `hex rebase-global` | No | **`[redis]`** |
| `hex llm-vote` | No | **`[llm]`** + registry for HTTP |

---

## D. What to remove or slim in *documentation*

| Document / section | Action |
|--------------------|--------|
| `README.md` top | **Quickstart: pip install + `hex commit`** only. |
| Registry / Redis / LLM | Single subsection **“Optional: central registry & mesh”** with extras + compose pointer. |
| `docs/MANUAL-RUNBOOK.md` | Reorder so **sections 1–3** (local-only) come first; registry steps last and labeled optional. |

---

## E. Tests & CI

| Action |
|--------|
| Tag or mark tests: `registry`, `redis`, `llm`, `integration` where they need extras or services. |
| Default `pytest` (or CI matrix job) runs **core** tests without registry/redis. |
| Optional job: `pip install -e ".[dev]"` with all extras + docker services for full suite. |

---

## F. Optional follow-ups (not required for “plan complete”)

- **Outbox without registry:** export queued PRs to a file, or **no-op sync** with message when `[registry]` not installed.
- **Typer groups:** e.g. `hex registry …` subcommand group so `hex --help` lists fewer commands for minimal installs (UX polish).

---

## Subagent / owner hints

| Concern | Owner |
|---------|--------|
| Dependency graph & extras | backend packaging |
| Lazy imports & CLI guards | backend |
| Docs structure | documentation (if requested) |
| Test splitting | test engineer |

---

## Phase X: Verification (definition of done)

| Step | Check |
|------|--------|
| 1 | Fresh venv: `pip install .` (no extras) succeeds. |
| 2 | `hex commit` / `hex log` / `hex show` work with no env vars. |
| 3 | `hex push` or `hex sync` prints clear **install honeyhex[registry]** (or equivalent) message, not a traceback from missing `httpx`/SQLAlchemy at import time. |
| 4 | `pytest` (default selection) passes without Docker. |
| 5 | README “first 5 minutes” uses **only** pip + `hex` commands. |

**Phase X completion block:**

```markdown
## PHASE X COMPLETE
- Core-only install verified: Pass/Fail
- Docs reviewed: Pass/Fail
- Date: YYYY-MM-DD
```

---

## File delivered

| Artifact | Path |
|----------|------|
| This plan | `docs/PLAN-pip-self-contained.md` |

---

*Planning mode: no application code was written; this file is the sole deliverable for `/plan`.*
