# Release checklist

Use before tagging a version or publishing to PyPI.

## Tests and static checks

```bash
pip install -e ".[dev]"
ruff check src tests
mypy src
pytest -q
```

**Full suite** (registry + LLM integration markers — requires `[dev]` extras):

```bash
pytest -q -o addopts=
```

Run this before a release tag; default CI runs both core and full pytest (see `.github/workflows/ci.yml`).

## Adoption smoke (optional)

End-to-end check of a fresh cell (requires `hex` on `PATH`):

```bash
chmod +x scripts/adoption_smoke.sh
./scripts/adoption_smoke.sh
```

Or manually:

1. `hex cell init --guided`
2. `hex doctor`
3. `hex validate`
4. `hex export --format md -n 3`
5. `hex audit HEAD`

## Version and publish

1. Bump `version` in `pyproject.toml`.
2. Update changelog or release notes if you maintain them.
3. Tag: `git tag v0.x.y && git push origin v0.x.y` (or use the Publish workflow).

See [Development](development.md) for CI and PyPI details.
