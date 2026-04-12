# HoneyHex documentation

HoneyHex is a **distributed ledger of intelligence** for agent workflows: thought cycles are recorded as Git commits under `.honeyhex/` inside each **cell** (project directory).

| Document | Contents |
|----------|----------|
| [Getting started](getting-started.md) | Install, first cell, first commit |
| [Configuration](configuration.md) | Cell config, environment variables, hooks |
| [CLI reference](cli-reference.md) | Every `hex` command |
| [Optional components](optional-components.md) | Extras: Redis, registry, LLM, `docker-compose` |
| [HTTP API](http-api.md) | `honeyhex-api` (registry service) |
| [Security](security.md) | Hooks, remotes, signing, registry |
| [Development](development.md) | Tests, lint, types, CI/CD, releases |
| [Release checklist](release-checklist.md) | Pre-tag tests, full pytest, adoption smoke |
| [Plugins](plugins.md) | `honeyhex.plugins` entry points for third-party `hex` commands |
| [Backup & sync](backup-and-sync.md) | Remotes, bundles, git-crypt notes |
| [Merge & fork](merge-and-fork.md) | Combining or splitting ledgers |

**Requirements:** Python 3.12+, `git` on `PATH`. The CLI entry point is **`hex`**.
