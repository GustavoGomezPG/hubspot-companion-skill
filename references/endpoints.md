# Endpoint catalog + payload shapes

Base URL: `https://api.hubapi.com`. All paginated list endpoints use
`?limit=1000&after=<cursor>` and return `{ results: [...], paging: { next: { after } } }`.
Always paginate to completion — a single `limit=1000` page silently truncates large sets
(a portal can have thousands of redirects/pages).

## Account
- `GET /account-info/v3/details` → `{ portalId }`. Use to validate a key.

## Domains  (read-only via API)
- `GET /cms/v3/domains/?limit=100` → list. Per-domain fields that matter:
  `domain`, `isResolving`, `isSslEnabled`, `isUsedForBlogPost/SitePage/LandingPage/...`.
  NOTE: `isUsedFor*` = "this domain MAY serve that content type" — it is **not** the same as
  "primary". Connecting/disconnecting a domain, SSL, and setting a primary host are **UI-only**;
  the API cannot do them. Use this endpoint to read state and diagnose, then tell the user
  what to click.

## URL redirects  (full CRUD)  →  see references/url-redirects.md for the deep dive
- `GET /cms/v3/url-redirects/?limit=1000`
- `POST /cms/v3/url-redirects/`  body below
- `PATCH /cms/v3/url-redirects/{id}`  (partial)
- `DELETE /cms/v3/url-redirects/{id}`  → 204
- Create/patch body:
  ```json
  {
    "routePrefix": "https://www.old.com/path",   // full URL when isMatchFullUrl
    "destination": "https://new.com/path",
    "redirectStyle": 301,
    "isMatchFullUrl": true,          // scope to a host in multi-domain portals
    "isOnlyAfterNotFound": false,    // false = override served pages; true = last-resort fallback
    "isProtocolAgnostic": true,
    "isTrailingSlashOptional": true,
    "isMatchQueryString": false,
    "isPattern": false,              // true for :name / *name patterns
    "precedence": 999999             // lower number = higher priority
  }
  ```

## Pages
- `GET /cms/v3/pages/site-pages/?limit=100`
- `GET /cms/v3/pages/landing-pages/?limit=100`
- `PATCH /cms/v3/pages/{site-pages|landing-pages}/{id}` — edit content/meta/slug/domain.
- `DELETE /cms/v3/pages/...` = **reversible soft-archive** (restore via `?archived=true` or
  the Archived view in the UI). Good for non-destructive "take it offline".
- A page with a blank `domain` serves on the portal's PRIMARY domain ("follow the primary").

## Blogs
- `GET /cms/v3/blogs/posts/?limit=100` · `POST` · `PATCH /{id}` · `DELETE`
- `GET /cms/v3/blogs/tags/?limit=100` · `POST` (create tags as a migration prerequisite)
- `GET /cms/v3/blog-settings/settings` — content group ids, listing paths.
- Legacy v2 (sometimes needed): `/content/api/v2/blogs`, `/content/api/v2/templates`.
- Create posts as DRAFT, preserve publish dates, rewrite media URLs + ids, map authors/tags
  into the target first. Idempotency: skip posts whose slug already exists in target.

## HubDB  →  see references/hubdb.md (READ IT — column PATCH can wipe all rows)
- `GET /cms/v3/hubdb/tables/?limit=100`
- `GET /cms/v3/hubdb/tables/{tableId}/rows?limit=1000`
- `POST/PATCH/DELETE /cms/v3/hubdb/tables/{tableId}/rows/{rowId}`
- Publishing draft: `POST /cms/v3/hubdb/tables/{tableId}/draft/publish` (or push live).
- Dynamic pages: a CMS page with `dynamicPageHubDbTableId` renders one URL per row;
  dynamic URL = page base path + "/" + row `hs_path`.

## Source code (themes/templates/modules)
- `GET /cms/v3/source-code/{environment}/content/{path}` to read.
- `PUT` is **multipart** to upload a file (template/module/css/js). Used to fix templates,
  e.g. HubL referencing a HubDB FILE column (use `row.col.url`, the column renders as an object).

## Media / File Manager
- `GET /files/v3/files/search` · folders `GET /files/v3/folders`
- Upload: `POST /files/v3/files` (multipart) with
  `options={"duplicateValidationStrategy":"RETURN_EXISTING"}` → **idempotent** (re-running an
  import returns the existing file instead of duplicating). Preserve folder structure.
