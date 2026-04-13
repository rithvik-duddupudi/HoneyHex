# Security

This page summarizes **security-relevant behavior** and **recommended practices**. It is **not** a substitute for a threat model, penetration test, or organizational security policy.

## Security best practices (checklist)

| Practice | Why it matters |
|----------|----------------|
| **Keep HoneyHex and dependencies updated** | Install from PyPI/Homebrew regularly; run `pip list --outdated` or your org’s patch process. |
| **Treat `.honeyhex/` like sensitive data** | It can contain prompts, internal notes, and metadata—use **private Git remotes**, access control, and encryption at rest if required (see [Backup & sync](backup-and-sync.md)). |
| **Never commit secrets into the ledger** | Do not put API keys, passwords, or PII into `--prompt` / `--scratchpad` if those commits are pushed or exported. Use env vars and secret managers; use **`hex scrub`** before sharing files (see [CLI reference](cli-reference.md)). |
| **Hooks: start with `off` or `safe`** | Enable **`full`** only after reviewing scripts under `.honeyhex/`. Hooks run arbitrary code (see [Hooks](#hooks)). |
| **Only install plugins you trust** | Third-party `honeyhex.plugins` code runs inside the `hex` process (see [Plugins](plugins.md)). |
| **Registry / Redis / LLM extras** | Run **behind TLS**, firewalls, and authentication appropriate to your environment. Do not expose optional services to the public internet without a designed security posture. |
| **Verify downloads** | Prefer **official** PyPI, signed Git tags, or your org’s artifact registry; verify checksums when distributing internally. |
| **Separate dev and prod** | Use different cells, remotes, or signing keys so a test never overwrites production policy. |

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

**Production guidance (summary):** terminate TLS at a reverse proxy or load balancer, require authentication and authorization for the HTTP API, restrict database and Redis to private networks, and log access for incident response.

## LLM and cloud keys

The **`[llm]`** stack may send prompts to configured providers. Protect **API keys** (`OPENAI_API_KEY`, etc.) via environment or secret management—never commit them to the repository.

Review provider policies for **data retention**, **training**, and **regions** before sending production content.

## Reporting security issues

If you believe you have found a **security vulnerability** in HoneyHex, please report it responsibly (for example via the repository’s **Security** policy or maintainer contact), with enough detail to reproduce. Avoid posting exploit details in public issues until maintainers have had time to respond.

## Further reading

- [Legal disclaimer](legal-disclaimer.md) — warranties, liability, third-party services.
- [HTTP API](http-api.md) — registry endpoints and deployment assumptions.
