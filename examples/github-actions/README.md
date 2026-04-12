# GitHub Actions examples

## `hex-validate.yml`

Copy into **`.github/workflows/`** in a repository that keeps a HoneyHex **cell** at the repo root (or set **`working-directory`** in the job). Installs **`honeyhex`** from PyPI and runs **`hex validate`**.

## Reusable composite (this repository)

For HoneyHex itself or any repo that can reference this tree, use the composite action at **`.github/actions/hex-validate`**:

```yaml
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - uses: ./.github/actions/hex-validate
        with:
          working-directory: .
          package-spec: honeyhex
```

For a **monorepo** where the cell lives in a subdirectory, set **`working-directory`** to that path. To test against a branch of HoneyHex, set **`package-spec`** to a VCS URL or **`-e .`** when the workflow installs from the same checkout.
