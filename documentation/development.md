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

## Releases

1. Bump **`version`** in **`pyproject.toml`**.
2. Commit and push.
3. Tag: `git tag v0.1.x && git push origin v0.1.x`  
   Or run the **Publish to PyPI** workflow manually.

Configure **`PYPI_API_TOKEN`** in GitHub repository secrets, or use **PyPI trusted publishing** without a long-lived token (see workflow comments).

## Merge behavior (local)

**`hex merge`** runs standard Git merge inside **`.honeyhex/`**. Fast-forward when possible; conflicts leave the tree in a conflicted state like normal Git—resolve with **`hex git`** or manual editing, then commit.

Registry-side merges use **`hex merge-quorum`** and server-side quorum rules, not local Git merge semantics.
