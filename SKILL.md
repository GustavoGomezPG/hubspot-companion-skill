---
name: hubspot-companion
description: >-
  Use when working with a HubSpot portal through its API — auditing or extracting
  content, fixing/creating URL redirects, migrating pages, blog posts, or media
  between portals or domains, editing content, HubDB table operations, or domain
  cutovers. Asks for a HubSpot Service Key and always works through a
  non-destructive backup → test-on-one → full-batch workflow with in-flight
  progress checks and summaries. Triggers on mentions of HubSpot, service key,
  CMS migration, url-redirects, HubDB, portal, domain connect/cutover, blog/page
  migration, or bulk content edits.
---

# HubSpot Companion

A toolkit + playbook for operating on a HubSpot portal safely. It knows the
endpoints, the payload shapes, the rate limits, and — most importantly — the
**non-destructive operating pattern**: never run a bulk write without a JSON
backup and a single-item canary first.

## When to use

- Audit / extract: list domains, pages, posts, redirects, HubDB rows; export to JSON/CSV.
- Fix: repair redirects, patch content, correct HubDB rows, resolve domain serving issues.
- Migrate: pages, blog posts, media, HubDB tables between portals or onto new domains.
- Domain work: connect/cutover analysis, primary-domain effects, redirect strategy.
- Bulk edits: any change touching more than one record.

## Setup — get the key, configure .env, validate (do this first)

1. **Get a Service Key.** HubSpot **Service Keys** (beta), NOT Private App tokens:
   `Settings > Account Management > Keys > Service Keys`.
2. **Put it in a `.env` file** in the skill folder (or your working dir):
   ```
   cp .env.example .env
   # edit .env -> HUBSPOT_SERVICE_KEY=your-service-key-here
   ```
   The `.env` is gitignored — never commit it. One key per file; for a second portal use
   `--token <key>` or a separate `.env`.
3. **Validate** the key and learn the portal id:
   ```
   python3 scripts/hs_client.py validate            # GET /account-info/v3/details -> portalId
   ```
   Use `/account-info/v3/details` — **never** `/oauth/v1/access-tokens/` (that's for OAuth apps).
4. **Required scopes:** `content`, `hubdb`, `files`, `files.ui_hidden.read`. If a call
   401/403s, the key is missing a scope — tell the user which one.
5. **Cross-portal migrations** read from source, write to target — keep them straight and
   label every operation with its portal (pass `--token` for the second portal's key).

See `references/authentication.md` for rate limits (100 req/10s, search 4 req/s), 429
auto-retry, and token handling.

## THE CORE WORKFLOW — non-destructive, always

**Every write operation (create / patch / delete / bulk) follows this. No exceptions.**

```
1. READ + UNDERSTAND   Pull current state via API (paginate fully). Confirm the
                       target set with the user. Print counts + a few samples.
2. BACKUP              Dump the full current state of everything you will touch to a
                       timestamped JSON file BEFORE any write. This is the undo.
                         python3 scripts/backup.py <endpoint> backups/<name>-<date>.json
3. CANARY (test-on-one) Apply the operation to ONE representative item. Verify the
                       result end-to-end (re-GET it; for redirects, two-hop check the URL).
                       If the canary is wrong, STOP and rethink — do not batch.
4. CONFIRM             Show the user: backup path, canary result, and the full plan
                       (N items, sample of before→after). Get a clear go-ahead for
                       irreversible / bulk writes (see Safety).
5. BATCH               Run the full batch with:
                         - idempotency (skip already-correct items)
                         - rate limiting + 429 retry
                         - IN-FLIGHT progress every ~200 items (i/total, ok, failed)
                         - a per-item result log (CSV/JSON)
6. SUMMARIZE + VERIFY  Report created/skipped/failed/total. Re-verify a sample live.
                       Surface any failures with their error text. Never claim done
                       without the numbers.
```

`scripts/batch_runner.py` is a ready template implementing steps 2–6 — adapt its
`plan()` and `apply_one()` for the task. Use it rather than hand-rolling loops.

## Capabilities map (read the reference when you start that kind of work)

| Task | Reference |
|------|-----------|
| Auth, scopes, rate limits, token resolution | `references/authentication.md` |
| Endpoint catalog + payload shapes | `references/endpoints.md` |
| URL redirects (patterns, precedence, catch-alls, verification) | `references/url-redirects.md` |
| HubDB tables/rows/columns (incl. the row-wipe trap) | `references/hubdb.md` |
| Domains, primary-domain effects, cutovers, migrations | `references/domains-and-migrations.md` |
| Consolidated hard-won gotchas | `references/gotchas.md` |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/hs_client.py` | Rate-limited client: `get/post/patch/delete`, `paginate()`, `validate()`. Importable + CLI. |
| `scripts/backup.py` | Dump any collection endpoint (auto-paginated) to timestamped JSON. |
| `scripts/batch_runner.py` | Non-destructive batch template: backup → canary → confirm → batch → summary. |
| `scripts/verify_redirects.py` | Two-hop live verifier (old URL → 301 → follow → 200) with progress + report. |

All scripts are stdlib-only (no pip installs). Token resolves from `--token` or
`HUBSPOT_SERVICE_KEY` in a `.env` file (see `.env.example`).

## Safety (hard rules — these override any task pressure)

- **Never bulk-write without a JSON backup of the exact records being changed.**
- **Never skip the canary.** One item first, verified, every time.
- **Confirm before irreversible/bulk writes** (delete, mass patch, publish). Approval is
  per-operation and per-portal — don't generalize one yes to the next batch.
- **Deletes:** back up the full records (not just ids) so they can be recreated.
- **HubDB column PATCH:** include EVERY column's `id` or HubSpot recreates columns and
  **wipes all rows** — export the table to CSV first. (See `references/hubdb.md`.)
- **Edge cache lag** is ~120s on redirects (`?cb=` does NOT bust it) — the API stored
  value is the source of truth; wait a clean 130s before declaring a redirect re-test failed.
- Domain connect/disconnect, SSL, and "set primary" are **UI-only** — surface them to the
  user; the API can't do them.

## Quickstart

```
cd skills/hubspot-companion
cp .env.example .env          # then put your HUBSPOT_SERVICE_KEY in it
python3 scripts/hs_client.py validate
python3 scripts/hs_client.py get /cms/v3/domains/
python3 scripts/backup.py /cms/v3/url-redirects/ backups/redirects-pre.json
# then adapt scripts/batch_runner.py for the change, run dryrun, canary, batch
```
