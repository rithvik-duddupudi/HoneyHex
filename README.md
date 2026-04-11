# HoneyHex

Distributed ledger of intelligence for multi-agent systems: thought cycles are stored as Git commits under `.honeyhex/` in each **cell** (project directory).

**Documentation:** see **[`documentation/`](documentation/README.md)** — setup, full CLI reference, optional Redis/registry/LLM stacks, HTTP API, security, and development.

## Quickstart

**Requirements:** Python 3.12+, `git` on your `PATH`.

```bash
pip install honeyhex
cd your-agent-cell
hex cell init
hex commit -m "why I acted" --prompt "..." --scratchpad "..."
```

## Development install

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

## Tests

```bash
pytest
pytest -o addopts=   # full suite (registry + LLM markers); requires [dev] extras
ruff check src tests
mypy src
```

## Optional features

Mesh (Redis), central registry (HTTP API), and LLM validators install via extras (`honeyhex[redis]`, `[registry]`, `[llm]`). See **[documentation/optional-components.md](documentation/optional-components.md)**.
