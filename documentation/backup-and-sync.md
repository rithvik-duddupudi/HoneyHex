# Backup and encrypted sync

The thought ledger is a normal Git repository under **`.honeyhex/`**. You can back it up with any Git-friendly workflow.

## Happy path: ledger-only private remote

Use a **dedicated private Git remote** that stores only the **`.honeyhex`** repository (same as “push the ledger somewhere safe”). No HoneyHex-specific server is required—standard Git hosting works.

## Push to a private remote

From the **cell root** (parent of `.honeyhex/`):

```bash
git -C .honeyhex remote add backup git@github.com:you/honeyhex-ledger.git
git -C .honeyhex push -u backup main
```

Use a **private** empty repository; treat it like any sensitive project data.

## Bundle export (file-based)

Use **`hex bundle create`** to write a zip of thought snapshots for archival (see [CLI reference](cli-reference.md)).

## git-crypt (encrypted Git contents)

To encrypt blobs **before** they reach a remote:

1. Install [git-crypt](https://github.com/AGWA/git-crypt) and enable it in **`.honeyhex`** (not the outer project) following upstream docs.
2. Add a `.gitattributes` rule so `thoughts/**` (or the whole tree) is encrypted.
3. Share the symmetric key with collaborators out-of-band.

HoneyHex does not wrap git-crypt; use standard Git tooling. After conflicts or checkouts, run **`hex validate`** to ensure the ledger still opens.

## Restoring

Clone the remote (or unzip a bundle), ensure **`.honeyhex/.git`** exists, then run **`hex validate`** and **`hex log`**.
