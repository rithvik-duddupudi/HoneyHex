# Development

## Local setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Checks

```bash
pytest                    # core tests (default markers exclude registry/llm integration)
pytest -o addopts=        # full suite (needs all extras from [dev])
ruff check src tests
mypy src
```

Git must be installed; tests use temporary repositories and may require **`git config user.email` / `user.name`** (CI sets these in GitHub Actions).

## Continuous integration

GitHub Actions workflows (see **`.github/workflows/`**):

- **`ci.yml`** — on push/PR to `main`: Python 3.12 and 3.13, ruff, mypy, pytest (core + full).
- **`publish.yml`** — on version tags `v*` or manual dispatch: build sdist/wheel and publish to PyPI (token or trusted publishing).

### Validating a cell in CI

After installing HoneyHex in the job, run **`hex validate`** in the agent project root (or pass **`--cell`**). A minimal reusable workflow snippet ships under **`examples/github-actions/hex-validate.yml`**.

### pre-commit (optional)

```yaml
repos:
  - repo: local
    hooks:
      - id: honeyhex-validate
        name: hex validate
        entry: hex validate
        language: system
        pass_filenames: false
```

Run from the cell root, or set **`always_run: true`** with **`cd`** in **`entry`** if your repo layout differs.

### direnv (optional)

Optional hint when entering a directory that contains a ledger:

```bash
# .envrc (example)
[ -d .honeyhex/.git ] && echo "HoneyHex cell — try: hex doctor"
```

Use direnv for secrets and environment too; HoneyHex does not depend on it.

### Reusable `hex validate` action

This repo ships a composite action at **`.github/actions/hex-validate`** (install from PyPI, run **`hex validate`**). See **`examples/github-actions/README.md`** for usage; the sample workflow **`examples/github-actions/hex-validate.yml`** is the copy-paste workflow variant.

## Packaging note

**`MANIFEST.in`** prunes **`examples/`** from sdists so sample cells stay Git-only; wheels include only package data under **`src/`** by default.

## Releases

See **[Release checklist](release-checklist.md)** for pre-tag tests (including **`pytest -o addopts=`**) and the optional **`scripts/adoption_smoke.sh`** run.

1. Bump **`version`** in **`pyproject.toml`**.
2. Commit and push.
3. Tag: `git tag v0.1.x && git push origin v0.1.x`  
   Or run the **Publish to PyPI** workflow manually.

Configure **`PYPI_API_TOKEN`** in GitHub repository secrets, or use **PyPI trusted publishing** without a long-lived token (see workflow comments).

## Merge behavior (local)

**`hex merge`** runs standard Git merge inside **`.honeyhex/`**. Fast-forward when possible; conflicts leave the tree in a conflicted state like normal Git—resolve with **`hex git`** or manual editing, then commit.

Registry-side merges use **`hex merge-quorum`** and server-side quorum rules, not local Git merge semantics.
