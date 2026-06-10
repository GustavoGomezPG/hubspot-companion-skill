# HubDB — tables, rows, columns

## ⚠️ The row-wipe trap (read before any column change)

**A column-level `PATCH` to a HubDB table must include EVERY column's `id`.** If you send a
columns array without each existing column's `id`, HubSpot treats them as new columns,
**recreates the schema, and WIPES ALL ROWS.** This is destructive and not easily reversible.

Before ANY schema/column change:
1. Export the full table (all rows + the column definitions) to CSV/JSON as a backup.
2. GET the table, keep each column's `id`, and include those ids in the PATCH body.
3. Canary on a draft / single column change, verify rows survive, then proceed.

## Rows
- `GET /cms/v3/hubdb/tables/{tableId}/rows?limit=1000` (paginate).
- `POST/PATCH/DELETE /cms/v3/hubdb/tables/{tableId}/rows/{rowId}`.
- Row values live under `row.values` keyed by column **name**; `row.path` is the
  `hs_path` used for dynamic-page URLs.
- Changes land in **draft** — publish with the table's publish/push-live action
  (`POST /cms/v3/hubdb/tables/{tableId}/draft/publish`) or they won't go live.

## FILE columns render as objects in HubL
A HubDB **FILE** column is an OBJECT `{ id, url, type }`, not a bare string. In templates use
`row.column_name.url` (and in JS-built download links, `'{{ row.column_name.url }}'`). Using
the bare `row.column_name` yields `[object]`/"Cannot parse path (id=…, url=https:…)" errors.
Fixing this is a `source-code` multipart `PUT` to the template/module.

## Dynamic pages (find the real live URLs)
A CMS page with `dynamicPageHubDbTableId` set renders one URL per published row. The live URL
= the page's base path + "/" + the row's `hs_path`. When auditing "does this destination page
exist", you MUST enumerate these — the pages API does not list dynamic-page URLs, so they look
like 404s if you only check static pages. Steps:
1. Find pages with `dynamicPageHubDbTableId`.
2. GET that table's published rows.
3. Build base_path + "/" + hs_path for each row → those are live URLs.

## Migrating a HubDB table between portals
1. Backup source table (schema + rows) to JSON.
2. Create the table in target with the **same column definitions** (capture new column ids).
3. Insert rows mapping values by column name; rewrite any media/portal-specific urls.
4. Publish the draft. Verify a sample of dynamic-page URLs resolve.
