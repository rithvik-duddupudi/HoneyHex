# PLAN: CLI waves A + B + C (“Git for agentic swarms”)

## Phase -1: Context check

| Item | Notes |
|------|--------|
| **Product** | HoneyHex pip package + CLI; local `.honeyhex/` Git ledger; optional registry/Redis from prior phases—not required for this plan’s core paths. |
| **Goal** | Implement **A** (Git-like inspection & parity), **B** (swarm remotes / peer cells), **C** (hooks, config, porcelain)—in **recommended delivery order** (not A→B→C alphabetically). |
| **OS** | macOS/Linux primary; shell examples use `source .venv/bin/activate`. |

---

## Phase 0: Socratic gate — assumptions

1. **Scope**: All features are **CLI + library**; no new hosted product requirement.
2. **Compatibility**: New commands **extend** existing `hex` Typer app; breaking changes avoided unless versioned (`hex --version` / semver).
3. **Storage**: Remotes/outbox (B) may use **files under `.honeyhex/`** plus optional refs in Git (e.g. `refs/remotes/<name>/HEAD`).
4. **Hooks (C)**: Default **off** or **prompt** for arbitrary shell execution; document security model before 1.0.
5. **Order rationale**: Ship **inspectability first** (A-lite), then **multi-cell story** (B), then **extensibility** (C), then **deep Git parity** (A-deep) that depends on stable patterns.

**Open questions (resolve during implementation):**

- Should `hex fetch` support **only local paths** in v1, or also **SSH/Git URLs** for peer cells?
- **Signing** (C): optional GPG-like flow deferred until hooks + config stable?

---

## Python environment (all phases)

```bash
source .venv/bin/activate
uv pip install <dependency>
```

Use **`uv pip install -e ".[dev]"`** for local development.

---

## Recommended implementation order (summary)

| Wave | Theme | Contents |
|------|--------|----------|
| **1** | **A-lite — inspection** | `hex log`, `hex show`, `hex diff` (minimal viable “git feel”) |
| **2** | **B — swarm remotes** | Config file, `hex remote`, `hex fetch`, `hex pull`, optional outbox/sync |
| **3** | **C — hooks & porcelain** | `.honeyhex/config`, hook runner, `hex cell init`, bundles/replay (stretch) |
| **4** | **A-deep — full Git parity** | `log --graph`, local `hex merge`, `blame`, `reflog`-style, tags |

---

## Wave 1 — A-lite: inspection commands

### Functionality

| Command | Behavior |
|---------|----------|
| `hex log` | List thought-commits (Git `log` over `.honeyhex/`), optional `-n`, `--oneline`. |
| `hex show <rev>` | Show one commit: message + deserialized snapshot metadata (and/or raw `snapshot.json` at that rev). |
| `hex diff <rev> [<rev>]` | Diff `thoughts/snapshot.json` (or full tree diff) between commits; default `HEAD` vs `HEAD~1`. |

### Implementation notes

- Implement on **`HoneyHexLedger` + GitPython** (`git log`, `git show`, `git diff`).
- Parsing: reuse Pydantic where possible for snapshot JSON at each revision (`git show <rev>:thoughts/snapshot.json`).
- Keep output **stable** for scripting (JSON mode optional: `--json`).

### Subagent guidelines

| Role | Focus |
|------|--------|
| `backend-specialist` | CLI wiring, GitPython edge cases |
| `test-engineer` | Fixture repos with linear history; golden outputs for `log`/`diff` |

### Verification

- [ ] `pytest` covers 3+ commits linear chain; `log`/`show`/`diff` assertions.
- [ ] `ruff` / `mypy` clean on touched modules.

---

## Wave 2 — B: Swarm remotes & sync (local-first)

### Functionality

| Deliverable | Behavior |
|-------------|----------|
| **Config** | e.g. `.honeyhex/swarm.toml` (or `swarm.json`): named remotes → URL or **local path** to another cell. |
| `hex remote add \| list \| remove` | Manage remotes; store in `.honeyhex/` (version-controlled or gitignored—decide per security). |
| `hex fetch <remote>` | Update **remote-tracking refs** (e.g. fetch `HEAD` / tags from peer `.honeyhex` or bare repo). |
| `hex pull <remote> [<ref>]` | Integrate into current branch per policy (fast-forward first; document merge behavior). |
| **Optional** | Local **outbox** for PR intents when offline: `hex push` queues JSON; `hex sync` flushes to registry if configured. |

### Implementation notes

- v1 can **scope to `file://` / absolute paths**; SSH/HTTP later.
- Clearly document **trust model**: fetching from a path reads their object store—treat as **same trust as cloning a repo**.

### Subagent guidelines

| Role | Focus |
|------|--------|
| `backend-specialist` | Remote config schema, fetch/pull semantics |
| `security-auditor` | Path traversal, arbitrary URL fetch, hook interaction if remotes trigger hooks |
| `test-engineer` | Two temp dirs as two “agents”; fetch/pull integration test |

### Verification

- [ ] Integration test: two cells, `fetch` updates refs; `pull` advances branch.
- [ ] Docs: example `swarm.toml` fragment in plan follow-up or README (user-approved).

---

## Wave 3 — C: Hooks, config, porcelain

### Functionality

| Deliverable | Behavior |
|-------------|----------|
| **Config** | `.honeyhex/config.toml` (or yaml): default branch, enabled hooks, safe mode. |
| **Hooks** | `pre-thought`, `post-thought`, `pre-push`, `post-merge` — subprocess with env vars (`HONEYHEX_CELL`, `HONEYHEX_HEAD`, …). |
| `hex hook run <name>` | Manual invocation for debugging. |
| `hex cell init` | Scaffold cell: `.honeyhex/` init, sample config, optional hook stubs. |
| **Stretch** | `hex bundle` / `hex replay`; optional **sign/verify** metadata on commits. |

### Implementation notes

- **Security**: `HONEYHEX_HOOKS=off|safe|full` or equivalent; document **never auto-run** hooks from untrusted cells without explicit opt-in.
- Hooks must not block **read-only** commands (`log`, `show`) unless explicitly configured.

### Subagent guidelines

| Role | Focus |
|------|--------|
| `backend-specialist` | Hook runner, config loading, precedence rules |
| `security-auditor` | Command injection, path safety, env leakage |
| `test-engineer` | Temp hook scripts; assert exit codes abort/continue `commit` as designed |

### Verification

- [ ] Tests: hook failure blocks/succeeds per spec; `cell init` produces valid structure.
- [ ] Manual checklist: run `hex commit` with hook logging once.

---

## Wave 4 — A-deep: full Git parity (after 1–3 stable)

### Functionality

| Command | Behavior |
|---------|----------|
| `hex log --graph` | ASCII graph (or delegate to `git log --graph` in `.honeyhex`). |
| `hex merge` | Merge local branches inside `.honeyhex` (thought-level); conflict policy documented. |
| `hex blame` | Map fields in snapshot to introducing commit (line/field-level best effort). |
| `hex reflog` / safety | Replay safety for resets; document equivalence to `git reflog`. |
| `hex tag` | Tag thought releases (`v1.0-thought`). |

### Implementation notes

- Build on **Wave 1** parsers; may require richer storage than single `snapshot.json` path for blame—**document migration** if schema splits per-commit files.
- Consider **feature flags** or subcommands `hex git …` passthrough for power users.

### Subagent guidelines

| Role | Focus |
|------|--------|
| `backend-specialist` | Merge/blame algorithms, performance on long histories |
| `test-engineer` | Branchy histories, merge conflicts, blame spot checks |

### Verification

- [ ] Property or snapshot tests for `blame` on small DAG.
- [ ] Performance smoke: N=1000 commits optional benchmark not blocking CI.

---

## Dependency graph (waves)

```
Wave 1 (log/show/diff)
    → Wave 2 (remotes/fetch/pull)
        → Wave 3 (config/hooks/cell init)
            → Wave 4 (graph/merge/blame/reflog/tag)
```

**Parallelism:** Documentation and **JSON output flags** for Wave 1 can proceed alongside schema design for Wave 2 config—avoid merging large refactors in the same PR as behavioral changes without tests.

---

## Subagent assignment matrix (quick reference)

| Concern | Subagent |
|---------|----------|
| CLI & GitPython | `backend-specialist` |
| Security (hooks, remotes) | `security-auditor` |
| Tests | `test-engineer` |
| DX / examples | optional `documentation-writer` (only if user requests docs PR) |

---

## Phase X: Verification (definition of done for the whole initiative)

| Step | Check |
|------|--------|
| 1 | `source .venv/bin/activate` — full test suite green. |
| 2 | `pytest` — coverage for each wave’s critical paths. |
| 3 | `ruff check src tests` / `mypy src` — clean. |
| 4 | **Manual script**: two cells + `remote`/`fetch`/`pull`; one hook blocking a bad commit; `log`/`show`/`diff` on a 5-commit chain. |
| 5 | Security review: hooks and remote paths documented; no default arbitrary execution from untrusted content. |

**Phase X completion block (fill when done):**

```markdown
## PHASE X COMPLETE
- Tests: Pass
- Manual swarm script: Pass
- Date: YYYY-MM-DD
```

---

## File delivered

| Artifact | Path |
|----------|------|
| This plan | `docs/PLAN-cli-swarm-abc.md` |

---

*Planning mode: no application code was written; this file is the sole deliverable for `/plan`.*
