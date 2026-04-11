# Demo: local HoneyHex agent cell

This folder is a **minimal walkthrough**. HoneyHex stores an agent’s “thought ledger” as Git commits under `.honeyhex/` in any directory you treat as a **cell** (usually your project or agent workspace).

## 1. Install HoneyHex locally

From the **HoneyHex repo root** (recommended while developing):

```bash
cd /path/to/HoneyHex
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Confirm the CLI:

```bash
hex --help
```

You need **`git`** on your `PATH`. Python **3.12+** is required.

## 2. Run the scripted demo

From this directory:

```bash
chmod +x run-demo.sh
./run-demo.sh
```

The script creates a **temporary** workspace, runs `hex cell init`, records a few thought-commits, and prints `hex log` / `hex show` output. Nothing is written under this repo unless you change the script.

## 3. Same steps by hand

Pick any empty folder as your cell:

```bash
mkdir ~/my-agent-cell && cd ~/my-agent-cell
hex cell init
hex commit -m "First reasoning step" \
  --prompt "User asked for a summary." \
  --scratchpad "Need to outline sections."
hex commit -m "Refined plan" \
  --prompt "Same task" \
  --scratchpad "Sections: intro, body, conclusion."
hex log --oneline
hex show HEAD
```

Your history lives in `.honeyhex/` (a Git repo). Use `hex --help` and the main project `README.md` for more commands (`diff`, branches, bundles, etc.).
