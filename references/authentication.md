# Authentication, scopes, rate limits

## Service Keys (not Private App tokens)

HubSpot **Service Keys** are a beta credential type obtained from:
`Settings > Account Management > Keys > Service Keys`.

- Sent as a bearer token: `Authorization: Bearer <key>`.
- **Validate** and discover the portal id with:
  `GET /account-info/v3/details` → `{ "portalId": 489415, ... }`.
- Do **NOT** use `/oauth/v1/access-tokens/<token>` — that endpoint is for OAuth app
  access tokens and will not work for a Service Key.

## Required scopes for full CMS/migration work

| Scope | Grants |
|-------|--------|
| `content` | CMS pages, blog posts, blog settings, url-redirects, source code |
| `hubdb` | HubDB tables / rows / columns |
| `files` | File Manager read/write (media) |
| `files.ui_hidden.read` | System / hidden files |

A `401` means a bad/expired key; a `403` usually means a missing scope — name the
specific scope to the user so they can add it to the key.

## Rate limits

- **100 requests / 10 seconds** per token. Stay under it by spacing calls ~0.11–0.12s
  (`hs_client.py` does this automatically).
- **Search endpoints: 4 requests / second** — much stricter; throttle harder when hitting
  `/crm/v3/objects/.../search` or CMS search.
- On `429`, back off and retry (the client retries with increasing sleep). Also retry
  `500/502/503` a few times — HubSpot has transient 5xx.

## Token resolution (hs_client.py)

Order: `--token` arg → `HUBSPOT_SERVICE_KEY` in a `.env` file → `HUBSPOT_SERVICE_KEY` in the
real environment. The `.env` is searched in the current working dir, then the skill root,
then the scripts dir. Aliases also accepted: `HUB_SPOT_SERVICE_KEY`, `HUBSPOT_TOKEN`.

`.env` example (copy `.env.example` → `.env`, never commit it):
```
HUBSPOT_SERVICE_KEY=your-service-key-here
```

For cross-portal work, pass a separate `--token` per portal (or use a second `.env`), and
**label every operation** with which portal it targets. Reading from the source portal and
writing to the target is the common migration shape — never mix them up.

## Storage limits (for media migrations)

Free 250 MB · Starter 500 MB · Pro/Enterprise 5 GB. Max file 300 MB (2 GB on paid).
Run a storage pre-check (export size vs target free space) before a media import.
