#!/usr/bin/env python3
"""Two-hop LIVE verification of redirects: old URL -> 301 (Location==expected) -> follow -> 200.

No HubSpot token needed (it hits the live web). Feed it a CSV with source_url,destination_url
columns (the same shape you'd import to HubSpot), or a JSON list of {source,expected}.

Categories: OK | WRONG_DEST | DEST_404 | NO_REDIRECT | DEAD | ERROR
Comparison ignores scheme, leading 'www.', and trailing slash.

Usage:
    python3 verify_redirects.py redirects.csv [--limit 50] [--workers 5]
    python3 verify_redirects.py redirects.json
"""
import os, sys, csv, json, time, urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

UA = {"User-Agent": "Mozilla/5.0 (hubspot-companion-verifier)"}


def _arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def norm(u):
    if not u:
        return ""
    s = urllib.parse.urlsplit(u.strip())
    host = s.netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    return host + urllib.parse.unquote(s.path).rstrip("/")


def _enc(u):
    s = urllib.parse.urlsplit(u)
    return urllib.parse.urlunsplit((s.scheme, s.netloc, urllib.parse.quote(s.path), s.query, s.fragment))


def _hop_nofollow(u):
    for a in range(5):
        try:
            r = _opener.open(urllib.request.Request(_enc(u), method="GET", headers=UA), timeout=25)
            return r.status, r.headers.get("Location")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(min(3 * (a + 1), 20)); continue
            return e.code, e.headers.get("Location")
        except Exception:
            time.sleep(2 * (a + 1))
    return None, None


def _hop_follow(u):
    for a in range(5):
        try:
            r = urllib.request.urlopen(urllib.request.Request(_enc(u), headers=UA), timeout=25)
            return r.status
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(min(3 * (a + 1), 20)); continue
            return e.code
        except Exception:
            time.sleep(2 * (a + 1))
    return None


def check(row):
    src, exp = row["source"], row["expected"]
    st, loc = _hop_nofollow(src)
    fst = _hop_follow(loc) if (st in (301, 302, 307, 308) and loc) else None
    if st in (301, 302, 307, 308):
        if norm(loc) != norm(exp):
            cat = "WRONG_DEST"
        elif fst and 200 <= fst < 300:
            cat = "OK"
        elif fst in (404, 410):
            cat = "DEST_404"
        elif fst:
            cat = f"DEST_{fst}"
        else:
            cat = "DEST_ERROR"
    elif st and 200 <= st < 300:
        cat = "NO_REDIRECT"
    elif st in (404, 410):
        cat = "DEAD"
    elif st:
        cat = f"HTTP_{st}"
    else:
        cat = "ERROR"
    return {"category": cat, "status": st, "final_status": fst, "source": src, "expected": exp, "actual": loc or ""}


def load(path):
    if path.endswith(".json"):
        data = json.load(open(path))
        return [{"source": d.get("source") or d.get("source_url"),
                 "expected": d.get("expected") or d.get("destination_url")} for d in data]
    rows = []
    for r in csv.DictReader(open(path)):
        s = r.get("source_url") or r.get("source")
        d = r.get("destination_url") or r.get("expected")
        if s and d:
            rows.append({"source": s, "expected": d})
    return rows


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rows = load(sys.argv[1])
    limit = int(_arg("--limit", "0"))
    if limit:
        rows = rows[:limit]
    workers = int(_arg("--workers", "5"))
    print(f"verifying {len(rows)} redirects (two-hop, {workers} workers)...")

    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, res in enumerate(ex.map(check, rows), 1):
            results.append(res)
            if i % 25 == 0 or i == len(rows):
                t = Counter(x["category"] for x in results)
                print(f"   {i}/{len(rows)}  OK={t.get('OK',0)} issues={i-t.get('OK',0)}", flush=True)

    tally = Counter(x["category"] for x in results)
    out = os.path.splitext(sys.argv[1])[0] + ".verify.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["category", "status", "final_status", "source", "expected", "actual"])
        w.writeheader()
        for x in sorted(results, key=lambda r: (r["category"] != "OK", r["category"])):
            w.writerow(x)
    print(f"\n=== RESULT ({len(results)}) ===")
    for c, n in tally.most_common():
        print(f"   {n:>5}  {c}")
    print(f"   OK rate: {tally.get('OK',0)}/{len(results)} = {100*tally.get('OK',0)//max(1,len(results))}%")
    print(f"   report -> {out}")
    print("   NOTE: re-check ERROR rows gently (single worker) — most are transient rate-limit blips.")


if __name__ == "__main__":
    main()
