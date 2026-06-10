# URL redirects — patterns, precedence, catch-alls, verification

The most subtle part of HubSpot. These rules were established the hard way; trust them
over intuition.

## Fields that matter

| Field | Meaning / why it matters |
|-------|--------------------------|
| `routePrefix` | The source. Use the **full URL** (`https://host/path`) with `isMatchFullUrl:true` in a multi-domain portal, so the rule only fires on its own host. |
| `destination` | Target URL. Prefer the **apex** form of the target (e.g. `https://datamaxinc.com/x`, not `https://www.datamaxinc.com/x`) if the target's primary host is the apex — otherwise you add a needless extra `www→apex` hop. |
| `isMatchFullUrl` | `true` scopes the rule to the host in `routePrefix`. Essential when one portal serves several domains. |
| `isOnlyAfterNotFound` | `false` = fire even over a served page (use for specific migration redirects). `true` = last-resort fallback, only when nothing else matches (use for catch-alls). |
| `isPattern` | `true` for `:name` / `*name` flexible patterns. |
| `precedence` | **Lower number = higher priority.** HubSpot auto-assigns high numbers (e.g. `2000000001`) to bulk-imported legacy redirects. |
| `isProtocolAgnostic`, `isTrailingSlashOptional` | Almost always `true`. |
| `redirectStyle` | `301` permanent. |

## Pattern syntax (flexible redirects)

- `:name` matches **exactly one** path segment. In the destination, `{name}` substitutes it.
  Multi-segment input still "matches" but only the first segment is captured — so
  `/a/b/c` with `/:p → /{p}` yields `/a` (truncation trap).
- `*name` matches the **rest of the URL including slashes** (multi-segment). Destination uses
  `{name}`. Example (HubSpot docs): `…/posts/*rest → …/posts/{rest}`.
- Bare `/*` is **rejected**: error `"Pattern URL must contain : or * followed by a string"`.
  The `*` must be followed by a name.
- "HubSpot executes the first rule that matches" — ordering is by precedence.

## Precedence / pattern-vs-exact — the unreliable part (verified empirically)

- The documented rule is "lowest precedence wins; first match executes." In practice:
- **A pattern catch-all with `isOnlyAfterNotFound:false` can beat an EXACT redirect
  unpredictably, regardless of precedence number.** Observed: a legacy exact at
  precedence `2000000001` lost to a catch-all even after lowering the exact to `999999`,
  while a different `999999` exact won. Conclusion: **never use `isOnlyAfterNotFound:false`
  for a broad catch-all** — it silently swallows real specific redirects.
- **`isOnlyAfterNotFound:true` reliably lets every specific redirect win.** Use it for any
  catch-all/fallback.
- **Trade-off of `isOnlyAfterNotFound:true`:** a fallback pattern only fires for
  **single-segment** paths. Multi-segment unmapped paths (`/a/b/c`) do NOT match an
  `onlyAfterNotFound:true` pattern → they fall through to a 404. Depth patterns (`/:a/:b`)
  and `*name` do not work around this under `onlyAfterNotFound:true`. The clean fix for full
  any-depth coverage is a **custom "site moved" 404 page** on the retired domain, not a redirect.

## Proven retired-domain fallback design

To retire `old.com` so every URL goes to `new.com` without loops or brand-404s:
1. Keep all the **specific** migration redirects (exact, `isOnlyAfterNotFound:false`, full-URL).
2. Add ONE **catch-all per host**: `https://<host>/:path → https://new.com/<landing>`,
   `isPattern:true`, `isOnlyAfterNotFound:true`, `precedence:2147483600` (lowest), destination on
   the target's **apex** host. Covers single-segment unmapped + acts as the fallback.
3. Add the **apex-root** + **www-root** exact redirects → the same landing (the `:path` pattern
   does not match an empty root path).
4. Apex deep links: if both apex and `www` are connected under one brand, point the apex
   catch-all **terminal at the target** (`apex/:path → new.com/...`), never `apex → www`.

### The apex↔www loop trap
If the brand's primary host is the **apex**, HubSpot auto-redirects `www → apex`. An
`apex → www` catch-all then loops forever (`www → apex → www → …`, ~50 hops) on any path
without a specific redirect. Fix: every catch-all must be **terminal on the target domain**
(apex→target, www→target), never apex→www. (If primary host is `www`, there's no loop.)

### "domain not connected to this portal"
Creating a redirect whose `routePrefix` host isn't fully connected/validated to the portal
returns `400 "...from a domain not connected to this portal."` Redirect creation is gated on
the same ownership validation as serving. You must finish: DNS CNAME repoint → the domain
connection wizard ("Continue") → SSL activation (can take hours) before redirects on that host
can be created. The bare-apex variant 409s/SSL-fails until the apex is added as its own host.

## Verification — always two-hop

After creating/fixing redirects, verify LIVE: old URL → expect `301` with `Location` ==
intended dest → follow → final `200`. `scripts/verify_redirects.py` does this with progress
and a categorized report (OK / WRONG_DEST / DEST_404 / NO_REDIRECT / DEAD / ERROR). Re-check
any `ERROR` rows gently single-threaded — most are transient rate-limit blips, not real failures.

## Edge cache
Redirect responses carry `cache-control: max-age=120`. A `?cb=<rand>` query does **not** bust
it (`isMatchQueryString:false`). After changing a redirect, wait a clean **130s untouched**
before concluding a re-test failed — the API stored value is the source of truth.

## Pagination + idempotency for bulk redirect work
- Paginate ALL existing redirects first; index by normalized `routePrefix` path to skip
  already-present ones (idempotent re-runs).
- Rate-limit ~0.11s between writes; retry 429/5xx.
- Log every create/patch/delete with its result; print progress every ~200.

## CSV import limits (the manual fallback path)
HubSpot's **bulk URL-redirect CSV importer** (in the UI) is the manual fallback when you can't use
the API. It has hard limits the API does NOT:
- **≤ 500 rows per file** — split large sets into multiple ≤500-row files.
- **≤ 140 characters per URL** — longer source/destination URLs are rejected.
- Split per-domain (one set of files per source host) — each domain is managed separately.
Prefer the **API** (this skill) for anything non-trivial — no row/length cap, idempotent, and
verifiable. Generate CSVs only when handing off to someone using the HubSpot UI importer.
