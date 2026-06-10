# Domains, primary-domain effects, cutovers, and content migration

## "Follow the primary domain" — the #1 source of surprises

A page / blog post with a **blank `domain`** serves on the portal's **PRIMARY** domain for
that content type. So when you make `new.com` primary, ALL blank-domain content in that portal
starts serving under `new.com` — this is how homepage collisions, listing-page takeovers, and
"texas content bleeding onto newdomain" happen. Diagnose collisions by checking which domain is
primary and which content has a blank vs explicit `domain`.

Fixes for unwanted bleed-through, in order of preference (all reversible):
- **Archive** the offending pages (`DELETE` = soft-archive, restore via `?archived=true`).
- Pin content to an explicit non-primary domain (may 409 if a redirect already occupies the path).
- Add override redirects with `isOnlyAfterNotFound:false` to beat still-served pages.

## Domain connect / cutover (UI-only actions, API can only observe)

The API **cannot** connect/disconnect a domain, provision SSL, or set a primary host — those
are UI / DNS actions. The companion's job is to diagnose and drive the user through them.

Cutover sequence to move `www.brand.com` from old portal → new portal:
1. **Release** `www.brand.com` from the old portal (UI).
2. **Repoint DNS:** `www.brand.com` CNAME → the new portal's target
   (e.g. `<portalgroup>.sites.hubspot.net`; copy the exact target from the new portal's
   "Show DNS records"). Query authoritative nameservers directly (`dig @ns... CNAME`) to confirm
   the record actually changed — don't trust a green "Connected" chip while DNS still points old.
3. **Finish the connection wizard** ("Redirect/hosting domain setup ... Continue") in the UI.
4. **SSL activation** — can take minutes to several hours. Until it's done, the host returns
   `403 "Domain ownership validation not complete"` (a LIVE response, `s-maxage=5`, not cache),
   and redirect creation on that host `400`s with "domain not connected to this portal."
5. To cover **both `www` and apex** on one record, add it as a **hosting/brand domain** (both
   hosts under one brand) — keep it **non-primary** and assign no content, so it serves only your
   redirects. Bare apex needs its own host entry; otherwise it `409`s / has no SSL.

Background-watcher pattern (used successfully): poll the host every ~2 min until it stops
returning `403` (or until a sample redirect returns `301`), then auto-run the bulk apply +
two-hop verify. Watch authoritative DNS + the served status, debounce 2 consecutive good reads.

## Content migration (export → dry-run → import-as-draft)

Two-phase, non-destructive: **Export** (source → local JSON, never touches target) then
**Import** (local → target, dry-run gated).

- **Media:** export folders + files preserving structure; import with
  `duplicateValidationStrategy:RETURN_EXISTING` (idempotent) and build an old→new URL map.
- **Blog posts:** create prerequisites in target first (authors, tags, content groups); upload
  media; rewrite URLs + ids; create as **DRAFT** preserving publish dates. Idempotency = skip
  posts whose slug already exists in target. Scan HTML for portal-specific breakage before import:
  HubL `{% %}`/`{{ }}` tokens, `hbspt.forms.create` form embeds, CTA GUIDs, media that 404s.
- **Pages:** recreate title, featured image, body HTML, slug, publish date, meta on a target
  template; upload + rewrite media. Watch for theme/global-group dependencies that only exist in
  the source portal (a copied auto-generated layout won't render if its theme/header/footer ids
  are portal-specific) — normalize onto a clean target template instead of porting the legacy theme.
- **Always offer a CSV fallback** for imports (HubSpot's CSV import tool) and a **dry-run** that
  logs what would happen without writing.

## Redirects as the migration tail
After pages/posts move, generate redirects old-URL → new-URL. Mind structure differences
(e.g. `/blog/topic/<x>` vs `/blog/tag/<x>`; dated blog URLs `/blog/2011/12/20/<slug>` → `/blog/<slug>`;
landing-page slugs → resource/HubDB paths). See `references/url-redirects.md`.
