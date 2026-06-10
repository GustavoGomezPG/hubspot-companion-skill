# Content operations — editing, URL overwrites, deduplication, staging

Operations on existing pages/posts in a portal (as opposed to cross-portal migration, which is in
`domains-and-migrations.md`). All of these are **writes** — follow backup → canary → batch.

## Editing content (pages & posts)

- Pages: `PATCH /cms/v3/pages/{site-pages|landing-pages}/{id}` — change body/meta/slug/domain/
  publish state. Blog: `PATCH /cms/v3/blogs/posts/{id}`.
- A page/post body is HTML (in fields like `postBody` / module rich-text). To change anything inside
  it, fetch the object, edit the HTML string, PATCH it back.
- Changes may land as a new draft/buffer — publish (or set the publish state) so they go live.
- **Module swaps:** a page built from modules references modules by `module_id` in its layout/flex
  columns. To swap a broken or capped module for a working clone, repoint that `module_id` (e.g. a
  marketplace parent module that caps a value → a child clone that doesn't). Edit the page's module
  field and PATCH. Back up the page JSON first; canary on one page and eyeball the render.

## Content URL overwrites (rewrite links/media/host inside bodies)

When a host or path changes (e.g. retiring `old.com` → `new.com`, or repointing media to a new CDN
host), the URLs **embedded in page/post HTML** need rewriting too — redirects fix inbound traffic,
but in-content links/images still point at the old host.

Pattern:
1. Pull the items (paginate); for each, read the body HTML (and meta/featured-image fields).
2. Apply the rewrite — old host/path → new (regex or string replace). Common targets: anchor
   `href`, `<img src>`, inline CDN/`hubfs` URLs, canonical/og meta.
3. **Idempotency:** skip an item whose body already contains only new URLs (so re-runs are no-ops).
4. Back up the original body HTML (full JSON) before writing; PATCH the changed field; publish.
5. Verify a sample renders and the links resolve.

Media URLs specifically: use the **absolute** uploaded URL (not relative `/hubfs/...`), or the page
errors with "Cannot parse path". Keep an old→new URL map from the media upload step and apply it.

## Deduplication — deleting duplicate copies

Migrations and collisions create duplicate pages/posts (same slug/path/title, or "copy of …"). To
clean up:
1. Group candidates by normalized **slug / path / title**; identify the **canonical** one to keep
   (usually the one that's published, on the right domain, most recently updated — confirm, don't
   guess).
2. **Archive the copies** — `DELETE /cms/v3/pages/...` is a reversible soft-archive (restore via
   `?archived=true` / the Archived view). Prefer archive over hard delete so a wrong call is undoable.
3. Back up the full records of everything you archive (so they can be recreated), and log each id.
4. Canary on one duplicate, confirm the canonical still serves, then batch.

This is also the fix for **primary-domain bleed-through** and homepage/listing collisions: archive
the duplicate/stale pages so the intended content wins (see `domains-and-migrations.md`).

## Design Manager — templates & modules (CRUD)

Templates, modules, CSS, JS, and theme files live in the **Design Manager** / developer file system
and are managed through the **Source Code API**:

- **Read:** `GET /cms/v3/source-code/{environment}/content/{path}` — download a file's contents.
  `{environment}` is `draft` or `published`. `metadata/{path}` lists folder contents.
- **Create / update:** `PUT /cms/v3/source-code/{environment}/content/{path}` — **multipart**
  (`file=@...`) to upload/replace a template, module file, CSS, or JS. This is how you edit a
  template's HubL/HTML programmatically (e.g. we fixed a HubDB **FILE** column reference so a
  download link used `row.col.url` instead of `row.col`).
- **Delete:** `DELETE /cms/v3/source-code/{environment}/content/{path}`.
- **Modules** are folders named `<name>.module/` containing `module.html`, `meta.json`,
  `fields.json`, `module.css`, `module.js`. To edit a module, GET/PUT the specific file inside it.
- Edits go to the **draft** environment — publish them so they go live.
- **Legacy listing:** `/content/api/v2/templates` and `/content/api/v2/layouts` enumerate templates
  (useful to find which template/path to edit, since the v3 source-code API works by path).

CRUD safety: GET and save the current file as a backup before any PUT/DELETE; canary on one file and
eyeball the rendered page; only then batch. A bad template edit can break every page using it — keep
the pre-edit copy so you can PUT it back.

## CMS content updates (general)

"Update content" = any PATCH to a page/post (above), a HubDB row (see `hubdb.md`), or a template/
module file (above). The pattern is uniform: GET current → back up → change → PATCH/PUT → publish →
verify a sample. Batch via `scripts/batch_runner.py`.

## Content Staging transfer

HubSpot **Content Staging** is a sandbox area for building/redesigning pages before they go live;
staged pages live on a staging host (e.g. `*-sandbox.hs-sites.com` or the account's staging domain).

- **Transfer staged → live:** publish the staged version onto its real domain (the staging tool's
  "publish" / replacing the live page). Via API this is editing the page's domain/publish state to
  the live target; confirm the live URL serves the staged content afterward.
- **Clear staging:** when staged drafts/proofs are obsolete, **archive** them (reversible) rather
  than hard-deleting — back up first. Identify them by the staging host or a naming convention
  (e.g. "Staged proof"/"Staged draft") before bulk-archiving.
- Watch for the staging host appearing in served URLs or redirects — those are leftovers to clean.

## Domain verification (read-only diagnostics)

The skill can't connect/disconnect domains (UI-only), but it verifies state and diagnoses serving:
- **Portal side:** `GET /cms/v3/domains` — check `isResolving`, `isSslEnabled`/`isHttpsEnabled`,
  the `isPrimary*` / `isUsedFor*` flags (primary vs "allowed to serve"), and `expectedCname`.
- **DNS side:** query the **authoritative** nameservers directly (`dig @<ns> <host> CNAME`) — a
  green "Connected" chip can lie while DNS still points at the old portal; expect all authoritative
  NS to agree on the new target.
- **Serving side:** `curl -sI` the host. `403 "Domain ownership validation not complete"` (live,
  `s-maxage=5`) = connected to the portal but DNS/SSL/wizard unfinished. A `409`/SSL failure on a
  bare apex = the apex host isn't connected. A `301` to the intended target = working.
- For redirects specifically, two-hop verify (see `url-redirects.md`).
- Background watcher pattern: poll the host every ~2 min until `403`→served (or a sample redirect
  `301`s), debounce 2 good reads, then auto-run the apply + verify.
