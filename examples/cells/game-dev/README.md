# Example: game dev cell

**Purpose:** Track design decisions, build milestones, and playtest feedback in the thought ledger.

**Suggested layout (besides `.honeyhex/`):**

- Project code and assets live alongside the cell; the ledger only stores agent/human reasoning.
- Use **`hex experiment start`** for risky mechanics (`honeyhex/exp/…` branches) and merge when stable.

**Try:**

```bash
cd examples/cells/game-dev
hex cell init --guided
hex experiment start combat-proto
hex log --oneline
```

Replace this README with your real project notes; keep `hex commit` messages short and snapshot JSON for prompts/scratchpad detail.
