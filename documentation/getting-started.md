# Getting started

## Install from PyPI

```bash
pip install honeyhex
hex --help
```

Install optional stacks when you need them:

```bash
pip install 'honeyhex[redis]'      # Hive-Daemon, Redis pub/sub mesh
pip install 'honeyhex[registry]'   # HTTP registry client + honeyhex-api server deps
pip install 'honeyhex[llm]'       # LiteLLM + Polars (validators, tabular summaries)
```

## Install from source (contributors)

```bash
git clone https://github.com/rithvik-duddupudi/HoneyHex.git
cd HoneyHex
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## First cell

A **cell** is any directory where you run `hex`. The ledger lives in **`.honeyhex/`** (a Git repository).

```bash
mkdir ~/my-agent-cell && cd ~/my-agent-cell
hex cell init
hex commit -m "First thought" \
  --prompt "User request summary." \
  --scratchpad "Plan: init, commit, inspect."
hex log --oneline
hex show HEAD
```

## What gets stored

Each **thought-commit** stores structured state (prompt, scratchpad, optional RAG context, tool outputs) as JSON under `.honeyhex/`, with Git history for inspection, branching, merge, and export.

See [CLI reference](cli-reference.md) for all commands and [Configuration](configuration.md) for `config.toml` and hooks.
