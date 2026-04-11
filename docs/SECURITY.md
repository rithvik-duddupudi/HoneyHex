# HoneyHex security notes

## Hooks

- Default **`hooks_mode` is `off`**. Hooks never run unless you set `hooks_mode` in `.honeyhex/config.json` (or `config.toml`) or override with **`HONEYHEX_HOOKS=safe|full`**.
- **`safe`** only runs **`pre-thought`** and **`post-thought`** (around `hex commit`). **`full`** also runs **`pre-push`** (before registry PR POST / outbox sync) and **`post-merge`** (after local `hex merge`).
- Hook scripts must live **under** `.honeyhex/` (paths are validated). They run with **`SHELL`** invoking the script; treat them like CI scripts.

## Swarm remotes

- **`hex remote add`** accepts a **local cell path** or a **Git remote URL** (`https://`, `git@`, `ssh://`). Fetching from a path or URL has the **same trust model as Git**: you are executing object transfer from that peer.

## Signing

- **`hex sign` / `hex verify`** use **HMAC-SHA256** over the canonical `git cat-file commit <sha>` body. Set a shared secret in **`HONEYHEX_SIGNING_KEY`** (UTF-8 string). This is **symmetric** (anyone with the key can forge); use for tamper-evidence between trusted agents, not public provenance.

## Registry

- **`hex push`**, **`hex outbox sync`**, and **`hex sync`** contact **`HONEYHEX_REGISTRY_URL`**. Use TLS and network policies in production.
