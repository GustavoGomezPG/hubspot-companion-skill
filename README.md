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
.claude-plugin/              Claude Code plugin packaging
  plugin.json                  Plugin manifest (enables marketplace install)
  marketplace.json             Marketplace catalog (enables /plugin marketplace add)
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

Two ways — both end up giving you the **`/hubspot-companion`** command. The repo ships a plugin
manifest (`.claude-plugin/plugin.json`) and a marketplace (`.claude-plugin/marketplace.json`),
and a `SKILL.md` at its root, so it works as a one-command plugin *and* as a plain skill folder.

### Method 1 — Plugin via marketplace (one-command install, recommended)

From inside Claude Code:
```
/plugin marketplace add GustavoGomezPG/hubspot-companion-skill
/plugin install hubspot-companion@hubspot-companion-skill
```
The first command registers the marketplace from the GitHub repo; the second installs the
plugin. Then invoke it with **`/hubspot-companion`** (or just ask Claude to do HubSpot work).
You can also run `/plugin` to browse/install/manage from the UI.

> **Where does the key go for a plugin install?** A plugin is copied into Claude Code's cache,
> so you don't edit a `.env` inside it. Instead the scripts read the key from your **current
> working directory** — put a `.env` (with `HUBSPOT_SERVICE_KEY=...`) in your project folder, or
> `export HUBSPOT_SERVICE_KEY=...` in your shell. (`hs_client.py` searches: CWD → skill root → env.)

### Method 2 — Skill folder (git clone)

A skill is a folder named `<skill-name>/` with `SKILL.md` at its root, under a skills directory;
the folder name becomes the command. Clone into a folder named **`hubspot-companion`**:

**Personal (all projects):**
```bash
git clone git@github.com:GustavoGomezPG/hubspot-companion-skill.git ~/.claude/skills/hubspot-companion
cd ~/.claude/skills/hubspot-companion
cp .env.example .env            # then edit .env and paste your HUBSPOT_SERVICE_KEY
python3 scripts/hs_client.py validate
```
(HTTPS instead of SSH: `https://github.com/GustavoGomezPG/hubspot-companion-skill.git`.)

**Project (this repo only):** clone into `/path/to/project/.claude/skills/hubspot-companion`.

> Because the repo also contains `.claude-plugin/plugin.json`, a clone into a skills directory is
> picked up as a local plugin (`hubspot-companion@skills-dir`) on the **next session**, so
> **restart Claude Code once** after cloning. (A skill folder *without* a plugin manifest would be
> live-watched with no restart — see the [docs](https://code.claude.com/docs/en/skills).)

**Verify (either method):** type `/` and confirm `hubspot-companion` appears, or run `/hubspot-companion`.

## Configure

```bash
cp .env.example .env
# .env:
#   HUBSPOT_SERVICE_KEY=your-service-key-here
```
The `.env` is **gitignored** — it holds a live credential, never commit it. For a plugin install,
put the `.env` in your working folder (or export `HUBSPOT_SERVICE_KEY`). For a second portal, pass
`--token <key>` on any script.

## Update

**Plugin:**
```
/plugin marketplace update hubspot-companion-skill
```
(The manifest omits a fixed `version`, so it tracks the latest commit — every push is an update.)

**Skill folder:**
```bash
git -C ~/.claude/skills/hubspot-companion pull
```
`SKILL.md`/reference edits take effect in-session. Your `.env`, `backups/`, `batch-logs/` are
untracked, so neither update touches them.

## Uninstall

**Plugin:** `/plugin uninstall hubspot-companion@hubspot-companion-skill` (or remove it from the
`/plugin` UI). To also drop the marketplace: `/plugin marketplace remove hubspot-companion-skill`.

**Skill folder:**
```bash
rm -rf ~/.claude/skills/hubspot-companion
```
Nothing is installed system-wide; removing the plugin/folder is the complete uninstall.

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
