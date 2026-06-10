# HubSpot Companion

A Claude Code / Claude Agent **skill** for operating on a HubSpot portal safely through its
API — auditing and extracting content, fixing and creating URL redirects, migrating pages,
blog posts, and media between portals or domains, editing content, and HubDB work.

Its defining principle is a **non-destructive workflow**: never run a bulk write without a
JSON backup and a verified single-item canary first.

```
READ → BACKUP (JSON) → CANARY (test-on-one, verified) → CONFIRM → BATCH (idempotent,
in-flight progress, per-item log) → SUMMARIZE + re-verify
```

## Capabilities

- **Audit & extract** — list domains, pages, posts, redirects, HubDB rows; export to JSON/CSV.
- **URL redirect management** — create, fix, and verify redirects; catch-alls, patterns, bulk strategy.
- **Domain verification & cutover** — check connection / SSL / DNS / serving; diagnose primary-domain effects.
- **Page & blog post transfer** — move pages and posts between portals, with source + target backups.
- **Media transfer & optimization** — migrate File Manager assets (idempotent); compress/resize before upload.
- **HubDB** — read/write tables, rows, and columns safely (avoids the row-wipe trap).
- **Content editing & URL overwrites** — patch page/post bodies; rewrite links, media, and host inside content.
- **Deduplication** — find and archive duplicate page / post copies.
- **Content Staging transfer** — publish staged content live; clear obsolete staged pages.
- **Design Manager / templates** — read, create, update, delete templates, modules, CSS, JS (Source Code API).
- **Bulk rollback / disaster recovery** — scripted, reversible "undo" of an import.

Everything runs through the same non-destructive flow: **backup → canary → batch → verify**.

## Quick start (the easy path)

1. **Create a HubSpot Service Key** — Settings ▸ Account Management ▸ Integrations ▸ Service Keys ▸
   **Create service key** ▸ add scopes **`content`**, **`hubdb`**, **`files`** ▸ copy the key.
   (Detailed walkthrough in [Getting a HubSpot Service Key](#getting-a-hubspot-service-key).)
2. **Install** — one command. It clones into `~/.claude/skills/`, sets up your key, and validates it:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/GustavoGomezPG/hubspot-companion-skill/main/install.sh | bash
   ```
   Paste your key when prompted. *(Rather not pipe to bash? `git clone` and run `./install.sh` — see [Install](#install-claude-code).)*
3. **Use it** — restart Claude Code if `~/.claude/skills` was just created, then run **`/hubspot-companion`**
   (or just ask Claude to do HubSpot work).

## What's inside

```
SKILL.md                     Entry point: setup, the workflow, capability map, safety rules
references/                  On-demand deep dives
  authentication.md            Service Keys, scopes, rate limits, token/.env resolution
  endpoints.md                 Endpoint catalog + payload shapes
  url-redirects.md             Patterns, precedence, catch-alls, the apex↔www loop, verification
  hubdb.md                     Tables/rows/columns (incl. the row-wipe trap, FILE-object gotcha)
  domains-and-migrations.md    Domain verification + cutovers, primary-domain effects, page/post/media transfer + backup, rollback
  content-operations.md        Edit pages/posts, content URL overwrites, dedupe copies, staging transfer, Design Manager template/module CRUD
  gotchas.md                   All the hard-won facts in one list
scripts/                     Stdlib-only Python (no pip installs)
  hs_client.py                 Rate-limited client: get/post/patch/delete, paginate, validate
  backup.py                    Dump any endpoint → timestamped JSON
  batch_runner.py              Non-destructive batch template (backup→canary→batch→summary)
  verify_redirects.py          Two-hop live redirect verifier
install.sh                   One-command installer (clone → .env → validate)
.env.example                 Copy to .env and add your key
```

## Requirements

- **Python 3** (standard library only — nothing to `pip install`).
- A **HubSpot Service Key** with scopes `content`, `hubdb`, `files`, `files.ui_hidden.read`.
  Get one at *HubSpot → Settings → Account Management → Keys → Service Keys*.

## Getting a HubSpot Service Key

Service Keys are HubSpot's credential for system-to-system API access (public beta since
Feb 2026). You need the **"Developer tools access"** permission on your HubSpot user — Super
Admins have it; otherwise ask an admin to grant it or to create the key for you.

1. In HubSpot, click the **Settings** gear (top-right nav).
2. In the left sidebar, go to **Account Management → Integrations → Service Keys**
   *(or, under Development, **Keys → Service keys**)*.
3. Click **Create service key** (top right).
4. Give it a **name** (e.g. `hubspot-companion`).
5. Click **Add new scope** and add **each** of the scopes in the table below (use the search box
   in the scope picker to find each one by name), then click **Update**.
6. Create/save the key, then **copy the generated key value**.
7. Paste it into your `.env`:
   ```
   HUBSPOT_SERVICE_KEY=your-copied-key-here
   ```
8. Verify it: `python3 scripts/hs_client.py validate` → should print your portal id.

### Scopes to add

In the key's scope picker, use the **"Find a scope"** search box and add each identifier below.
These are broad scopes (HubSpot lists them under "requires **one of** the following scopes"), so
this short list covers every API the skill uses — **verified against HubSpot's live API reference**:

```
content                # URL redirects · website + landing pages · blog posts/tags · blog settings ·
                       #   domain reads · Design Manager templates/modules/source code · staging ·
                       #   content edits & URL overwrites · duplicate deletion
hubdb                  # HubDB tables, rows, and columns
files                  # File Manager — read/write media (migrations, optimization)
files.ui_hidden.read   # only if you read system / hidden files (optional)
```

- **`content`** is the one scope HubSpot requires for nearly everything this skill does — URL
  redirects, pages, blog, **Design Manager templates/modules (Source Code API)**, content updates,
  staging transfers, deduplication, *and* domain reads. Verified on each endpoint's
  "Scope requirements" (url-redirects, source-code, and domains all list `content`). You do **not**
  need `cms.domains.read` or any `cms.source_code.*` scope.
- **`hubdb`** covers all HubDB operations; **`files`** covers File Manager media.
- A `403` on a call means you're missing that area's scope — add it and retry.
- Add extra scopes only if you extend the skill (e.g. `crm.objects.*` for CRM data).

> Don't see Service Keys? The account may not have the beta enabled yet. As a fallback you
> can use a **Private App access token** (HubSpot → Settings → Integrations → Private Apps),
> which is also a Bearer token and works with every script here — put it in `.env` the same way.

## Install (Claude Code)

It's a **plain skill** — a folder named `hubspot-companion/` with `SKILL.md` at its root, dropped
into a Claude Code skills directory. The folder name becomes the command: **`/hubspot-companion`**.

### Easiest — one command

```bash
curl -fsSL https://raw.githubusercontent.com/GustavoGomezPG/hubspot-companion-skill/main/install.sh | bash
```
Clones into `~/.claude/skills/hubspot-companion`, creates `.env`, prompts for your Service Key, and
validates it. **Then restart Claude Code and type `/hubspot-companion`.**

Rather not pipe to bash (or want it in one project)? Clone and run the script:
```bash
git clone https://github.com/GustavoGomezPG/hubspot-companion-skill.git
./hubspot-companion-skill/install.sh                                   # → ~/.claude/skills/hubspot-companion
# project-only:  ./hubspot-companion-skill/install.sh /path/to/project/.claude/skills/hubspot-companion
```

### Manual (no script)

```bash
git clone https://github.com/GustavoGomezPG/hubspot-companion-skill.git ~/.claude/skills/hubspot-companion
cd ~/.claude/skills/hubspot-companion
cp .env.example .env            # paste your key into .env
python3 scripts/hs_client.py validate
```
For one project only, clone into `<project>/.claude/skills/hubspot-companion` instead.

### Make it show up

- **Restart Claude Code** if `~/.claude/skills/` was just created — Claude Code only starts watching
  a brand-new skills directory on restart. If that directory already existed, the skill is live
  immediately (no restart).
- Verify: type `/` and confirm **`hubspot-companion`** is listed, or just run `/hubspot-companion`.

## Configure

```bash
cp .env.example .env
# .env:  HUBSPOT_SERVICE_KEY=your-service-key-here
```
The install script does this for you. The `.env` is **gitignored** — never commit it. The scripts
also accept `HUBSPOT_SERVICE_KEY` from your shell env, or `--token <key>` for a second portal.

## Update

```bash
git -C ~/.claude/skills/hubspot-companion pull        # or just re-run install.sh
```
Edits take effect in-session. Your `.env`, `backups/`, and `batch-logs/` are untracked, so an
update never touches them.

## Uninstall

```bash
rm -rf ~/.claude/skills/hubspot-companion
```
That's the whole uninstall — nothing is installed system-wide.

## Use as a plain toolkit (no Claude Code)

Clone anywhere, set up `.env`, and run the `scripts/` directly — the `references/*.md` double
as standalone documentation.

## Quick check

```bash
python3 scripts/hs_client.py validate                 # -> portalId
python3 scripts/hs_client.py get /cms/v3/domains/
python3 scripts/backup.py /cms/v3/url-redirects/      # -> backups/...json
```

## Safety

- Never bulk-write without a JSON backup and a verified canary.
- Confirm before irreversible/bulk writes; approval is per-operation and per-portal.
- HubDB column PATCH **must include every column's `id`** or it wipes all rows — back up first.
- Redirect edge cache is ~120s; the API stored value is the source of truth.
- Domain connect/disconnect, SSL, and "set primary" are UI-only — the API can only observe.

See `references/gotchas.md` for the full list.
