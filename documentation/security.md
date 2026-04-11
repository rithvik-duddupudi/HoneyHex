# Security

## Hooks

- Default **`hooks_mode`** is **`off`**. Hooks do not run unless enabled via **`.honeyhex/config.json`**, **`config.toml`**, or **`HONEYHEX_HOOKS=safe|full`**.
- **`safe`** runs **`pre-thought`** and **`post-thought`** around **`hex commit`** only.
- **`full`** also runs **`pre-push`** (before registry PR POST / outbox sync) and **`post-merge`** (after **`hex merge`**).
- Hook scripts must live **under `.honeyhex/`**; paths are validated. They execute like CI scripts—review before enabling **`full`**.

## Swarm remotes

**`hex remote add`** accepts a local filesystem path to another cell or a normal Git remote URL. Treat peers like any Git remote: only add sources you trust.

## Signing (`hex sign` / `hex verify`)

Uses **HMAC-SHA256** over the canonical Git commit object. Set **`HONEYHEX_SIGNING_KEY`** (UTF-8 shared secret). This is **symmetric**—anyone with the key can forge signatures. Use for tamper-evidence among trusted agents, not public provenance.

## Registry and transport

**`hex push`**, **`hex outbox sync`**, and **`hex sync`** call **`HONEYHEX_REGISTRY_URL`**. Use **TLS** and network policies in production; do not expose the registry unauthenticated on untrusted networks without an explicit security design.

## LLM and cloud keys

The **`[llm]`** stack may send prompts to configured providers. Protect **API keys** (`OPENAI_API_KEY`, etc.) via environment or secret management—never commit them to the repository.
