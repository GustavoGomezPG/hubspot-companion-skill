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
  domains-and-migrations.md    Primary-domain effects, domain cutovers, content migration
  gotchas.md                   All the hard-won facts in one list
scripts/                     Stdlib-only Python (no pip installs)
  hs_client.py                 Rate-limited client: get/post/patch/delete, paginate, validate
  backup.py                    Dump any endpoint → timestamped JSON
  batch_runner.py              Non-destructive batch template (backup→canary→batch→summary)
  verify_redirects.py          Two-hop live redirect verifier
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
5. Click **Add new scope** and select the scopes this skill needs:
   `content`, `hubdb`, `files`, `files.ui_hidden.read` *(add any others your task needs,
   e.g. CRM scopes)*. Click **Update**.
6. Create/save the key, then **copy the generated key value**.
7. Paste it into your `.env`:
   ```
   HUBSPOT_SERVICE_KEY=your-copied-key-here
   ```
8. Verify it: `python3 scripts/hs_client.py validate` → should print your portal id.

> Don't see Service Keys? The account may not have the beta enabled yet. As a fallback you
> can use a **Private App access token** (HubSpot → Settings → Integrations → Private Apps),
> which is also a Bearer token and works with every script here — put it in `.env` the same way.

## Install

A skill is just a folder. Put it where your agent looks for skills, then add your key.

**Option A — personal (available in every project):**
```bash
git clone <THIS_REPO_URL> ~/.claude/skills/hubspot-companion
cd ~/.claude/skills/hubspot-companion
cp .env.example .env        # then edit .env and paste your HUBSPOT_SERVICE_KEY
python3 scripts/hs_client.py validate
```

**Option B — single project only:**
```bash
git clone <THIS_REPO_URL> /path/to/your/project/.claude/skills/hubspot-companion
cd /path/to/your/project/.claude/skills/hubspot-companion
cp .env.example .env        # then edit .env
python3 scripts/hs_client.py validate
```

**Option C — standalone toolkit (no agent integration):** clone anywhere, set up `.env`,
and run the scripts directly. The references double as documentation.

After install, invoking the skill (e.g. `/hubspot-companion` in Claude Code, if your client
lists it) loads `SKILL.md`; the agent reads the relevant `references/*.md` on demand.

> Skill auto-discovery location depends on your client. Claude Code reads `~/.claude/skills/`
> (personal) and `<project>/.claude/skills/` (project). If your client uses a different path,
> clone or symlink the folder there.

## Configure

```bash
cp .env.example .env
# .env:
#   HUBSPOT_SERVICE_KEY=your-service-key-here
```
The `.env` is **gitignored** — it holds a live credential, never commit it. For a second
portal, pass `--token <key>` on any script, or keep a separate `.env`.

## Update

```bash
cd <install-dir>/hubspot-companion
git pull
```
Your `.env` and any local `backups/` / `batch-logs/` are untracked, so a pull won't touch them.

## Uninstall

```bash
rm -rf <install-dir>/hubspot-companion
```
(e.g. `rm -rf ~/.claude/skills/hubspot-companion`). That's it — nothing is installed system-wide.

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
