# Merge and fork cells

A **cell** is a project directory whose ledger lives in **`.honeyhex/`** (a Git repo). Combining or splitting work uses normal Git semantics.

## Merge another cell’s history into yours

1. Register the peer (local path or Git URL) in **`.honeyhex/swarm.json`**:

   ```bash
   hex remote add peer /path/to/other-cell
   ```

2. Fetch and merge the peer’s current branch into your ledger branch:

   ```bash
   hex peer-merge peer
   ```

   If both sides touched **`thoughts/snapshot.json`** independently, Git may report a conflict—resolve inside **`.honeyhex/`** (or pass **`--favor ours`** / **`--favor theirs`** to bias the merge; see **`hex peer-merge --help`**).

This is equivalent to **`hex pull peer`** when you want fetch+merge in one step for configured swarm remotes; **`peer-merge`** mirrors **`git merge swarm-<name>/<branch>`** after **`hex fetch peer`**.

## Fork (copy a ledger)

- **File copy:** duplicate the cell directory; re-init remotes if needed.
- **Git bundle:** **`hex bundle create`** on the source, **`hex bundle replay`** into a fresh cell (see [CLI reference](cli-reference.md)).
- **Branching experiments:** use **`hex experiment start`** for isolated **`honeyhex/exp/...`** branches before merging.

## Splitting one cell into two

There is no single automated split: create a new cell (**`hex cell init`**), then copy or cherry-pick commits with **`hex cherry-pick`** / **`hex git`** as needed, or export bundles for a clean import.
