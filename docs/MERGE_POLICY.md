# Merge policy (local `hex merge`)

`hex merge <branch>` runs **`git merge <branch>`** inside `.honeyhex/`, i.e. standard Git merge semantics on the thought ledger.

- **Fast-forward** applies when possible.
- **Conflicts** stop the merge with a non-zero exit code and conflict markers in the working tree (same as Git). Resolve manually with `hex git …` (passthrough) or a normal editor, then `git add` / `hex commit` as appropriate.
- After a **successful** merge, **`post-merge`** hooks run (when `HONEYHEX_HOOKS` / config enables them).

For registry-side merges (`hex merge-quorum --pr …`), see the API and quorum rules in the registry service, not this document.
