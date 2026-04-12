# Example: research cell

**Purpose:** Log literature notes, hypotheses, and experiment outcomes as thought-commits.

**Conventions:**

- Put long-form prose in **`--scratchpad`** or **`--prompt`** snapshots; use **`--task`** / **`--session-id`** on `hex commit` to tie commits to papers or runs (see CLI reference).
- Use **`hex export --format md`** before sharing a milestone with collaborators.

**Try:**

```bash
cd examples/cells/research
hex cell init --guided
hex commit -m "paper: attention is all you need" \
  --task "literature" \
  --prompt "Key claim: …" \
  --scratchpad "Questions for next session: …"
hex stats
```
