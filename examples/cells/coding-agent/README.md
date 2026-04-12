# Example: coding-agent cell

**Purpose:** Record planning, diffs-in-words, and review notes for a software project.

**Conventions:**

- One cell per repo (or per service) so **`hex log`** matches your shipping cadence.
- Use **`hex validate`** in CI (see `examples/github-actions/hex-validate.yml`) so merges fail if `.honeyhex` is broken.

**Try:**

```bash
cd examples/cells/coding-agent
hex cell init --guided
hex commit -m "refactor auth" --prompt "Goal: session cookies" --scratchpad "Steps: …"
hex search "TODO"
```
