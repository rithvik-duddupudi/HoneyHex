# HoneyHex manual runbook (Phase X)

**Minimal path:** `pip install honeyhex` is enough for sections 1–3 and 5 (local ledger, remotes, hooks, bundles). **Registry / Redis / LLM** steps below are optional and need `pip install 'honeyhex[registry]'`, `pip install 'honeyhex[redis]'`, or `pip install 'honeyhex[llm]'` as noted.

For full integration tests and the HTTP API, use a dev environment: `source .venv/bin/activate` and `uv pip install -e ".[dev]"`.

## 1. Five-commit inspection

```bash
cd "$(mktemp -d)"
hex cell init
hex commit -m "t1" --prompt "p1"
hex commit -m "t2" --prompt "p2"
hex commit -m "t3" --prompt "p3"
hex commit -m "t4" --prompt "p4"
hex commit -m "t5" --prompt "p5"
hex log --oneline
hex show HEAD --json | head
hex diff
hex log --json | head
```

## 2. Two cells: remote / fetch / pull

```bash
base="$(mktemp -d)"
peer="$base/peer"
loc="$base/local"
mkdir -p "$peer" "$loc"
(cd "$peer" && hex cell init && hex commit -m "peer" --prompt "x")
(cd "$loc" && hex cell init && hex commit -m "local" --prompt "y")
git clone "$peer/.honeyhex" "$loc/.honeyhex"  # align history; or use fresh init + remote add
# Simpler path:
(cd "$peer" && hex commit -m "ahead" --prompt "z")
(cd "$loc" && hex remote add up "$peer" && hex fetch up && hex pull up)
```

For a minimal scripted check, see `tests/test_plan_cli_abc.py` (`test_fetch_remote_local_peer`, `test_pull_remote_fast_forward`).

## 3. Hook blocking a commit

```bash
cd "$(mktemp -d)"
export HONEYHEX_HOOKS=full
hex cell init --hook-stubs
echo '#!/bin/sh
exit 1' > .honeyhex/hooks/pre-thought.sh
chmod +x .honeyhex/hooks/pre-thought.sh
hex commit -m "fail" --prompt "n"   # expect error / non-zero from Python API
```

## 4. Registry + outbox (needs `honeyhex[registry]`)

```bash
export HONEYHEX_REGISTRY_URL=http://127.0.0.1:8765
# start honeyhex-api in another shell
hex outbox enqueue --source a1 --target a2 --title "offline"
hex outbox list
hex sync --refresh-head
```

## 5. Bundle round-trip

```bash
cd "$(mktemp -d)"
hex cell init
hex commit -m "c1" --prompt "p"
hex bundle create /tmp/bundle.zip
mkdir other && cd other && hex cell init
hex bundle replay /tmp/bundle.zip --cell .
```
