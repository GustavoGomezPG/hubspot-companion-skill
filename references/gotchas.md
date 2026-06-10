# Consolidated gotchas (hard-won, in one place)

1. **Service Key validation** = `/account-info/v3/details`, NOT `/oauth/v1/access-tokens/`.
2. **Paginate everything.** A single `limit=1000` page truncates; portals have thousands of
   redirects/pages. Loop on `paging.next.after`.
3. **HubDB column PATCH without each column `id` WIPES ALL ROWS.** Export to CSV first.
4. **HubDB FILE column = object** `{id,url,type}` — use `row.col.url` in HubL, not `row.col`.
5. **Dynamic-page URLs** (HubDB-bound pages) aren't in the pages API — enumerate
   `dynamicPageHubDbTableId` rows or you'll get false 404s when checking destinations.
6. **"Follow the primary domain":** blank-`domain` content serves on the portal's primary —
   making a domain primary makes all blank-domain content appear under it.
7. **Redirect precedence:** lower number = higher priority — BUT a pattern catch-all with
   `isOnlyAfterNotFound:false` can beat exact redirects unpredictably. Use
   `isOnlyAfterNotFound:true` for catch-alls so specifics always win.
8. **`isOnlyAfterNotFound:true` patterns only match single-segment paths.** Multi-segment
   unmapped paths 404. Full any-depth coverage needs a custom 404 page, not a redirect.
9. **Pattern syntax:** `:name` = one segment (`{name}` in dest, truncates multi-seg);
   `*name` = rest-of-url incl. slashes; bare `/*` is rejected.
10. **`isMatchFullUrl:true`** on redirects in a multi-domain portal so a rule fires only on its
    own host.
11. **Destination host = apex** of the target if its primary is the apex — else you add a
    `www→apex` hop.
12. **apex↔www redirect loop:** if a brand's primary host is the apex, `www→apex` is automatic;
    an `apex→www` catch-all loops forever. Make every catch-all terminal on the target domain.
13. **"domain not connected to this portal" (400)** on redirect create = the host isn't fully
    connected/SSL-validated yet. Finish DNS repoint → wizard → SSL first.
14. **`403 "Domain ownership validation not complete"`** is a LIVE response (`s-maxage=5`), not
    cache — the host is connected to the portal but DNS/SSL/wizard isn't finished.
15. **Redirect edge cache `max-age=120`; `?cb=` does NOT bust it.** Wait a clean 130s before
    declaring a redirect re-test failed. API stored value is the source of truth.
16. **DELETE on v3 pages = reversible soft-archive** (`?archived=true` to restore). DELETE on
    url-redirects = permanent (204) — back up first.
17. **Domain connect/disconnect, SSL, set-primary are UI-only.** API observes; user clicks.
18. **File upload idempotency:** `duplicateValidationStrategy:RETURN_EXISTING` — re-imports
    don't duplicate.
19. **Authoritative DNS vs cache:** a green "Connected" chip can lie while DNS still points to the
    old portal. `dig @<authoritative-ns> <host> CNAME` is the truth; expect both NS to agree.
20. **Two-hop verify** every redirect change; re-check `ERROR` rows gently — most are transient
    rate-limit blips, not real failures.
21. **CHECK THE DOCS FIRST.** Before reverse-engineering behavior with live trial-and-error,
    read `knowledge.hubspot.com` and the community — it saves hours (and cache-wait cycles).
