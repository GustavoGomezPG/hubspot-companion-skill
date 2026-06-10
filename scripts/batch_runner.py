#!/usr/bin/env python3
"""Non-destructive batch template for the hubspot-companion skill.

Implements the core workflow: BACKUP -> CANARY (test-on-one) -> CONFIRM -> BATCH (idempotent,
in-flight progress, per-item log) -> SUMMARY. Adapt the two TODO functions for your task; the
safety scaffolding stays the same.

Modes:
    dryrun   plan only, write nothing (default)
    canary   apply to ONE item, verify, stop
    apply    backup + full batch (auto-backs-up first; refuses without a fresh backup)

Usage:
    python3 batch_runner.py <dryrun|canary|apply> [--limit N] [--token pat-...]
"""
import os, sys, csv, json, datetime
from hs_client import HS, _arg

# ----- CONFIGURE -----------------------------------------------------------
BACKUP_ENDPOINT = "/cms/v3/url-redirects/"   # what to snapshot before writing
LOG_DIR = "batch-logs"
PROGRESS_EVERY = 200
# ---------------------------------------------------------------------------


def plan(hs):
    """TODO: return a list of work items (dicts). Pull current state, decide changes.
    Example: find redirects whose destination should change and return
    [{"id": r["id"], "before": r["destination"], "after": "https://..."}, ...]."""
    raise NotImplementedError("fill in plan(hs): return list of work items")


def apply_one(hs, item):
    """TODO: perform ONE item's write. Return (ok: bool, detail: str).
    Be idempotent — return (True, 'skip: already correct') if no change needed.
    Example:
        st, _ = hs.patch(f"/cms/v3/url-redirects/{item['id']}", {"destination": item["after"]})
        return (st == 200, str(st))"""
    raise NotImplementedError("fill in apply_one(hs, item)")


def verify_one(hs, item):
    """OPTIONAL: re-check a single item end-to-end after writing. Return (ok, detail).
    For redirects, prefer a live two-hop check (see verify_redirects.py)."""
    return (True, "no verify configured")


# ---- scaffolding (don't edit) ---------------------------------------------

def _backup(hs, pid):
    rows = hs.paginate(BACKUP_ENDPOINT)
    os.makedirs("backups", exist_ok=True)
    path = os.path.join("backups", f"batch-{BACKUP_ENDPOINT.strip('/').replace('/','-')}-{pid}-{datetime.date.today().isoformat()}.json")
    with open(path, "w") as f:
        json.dump({"portal": pid, "endpoint": BACKUP_ENDPOINT, "count": len(rows), "results": rows}, f, indent=1)
    print(f"  backup: {len(rows)} records -> {path}")
    return path


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("dryrun", "canary", "apply") else None
    if not mode:
        sys.exit(__doc__)
    limit = int(_arg("--limit", "0"))
    hs = HS(token=_arg("--token"))
    pid = hs.validate()
    print(f"== batch_runner  mode={mode}  portal={pid} ==")

    items = plan(hs)
    if limit:
        items = items[:limit]
    print(f"  planned items: {len(items)}")
    for s in items[:5]:
        print(f"    sample: {json.dumps(s)[:140]}")

    if mode == "dryrun":
        print("\nDRY RUN — nothing written. Review the plan, then run canary.")
        return

    if not items:
        print("nothing to do."); return

    if mode == "canary":
        one = items[0]
        print(f"\nCANARY on: {json.dumps(one)[:160]}")
        ok, detail = apply_one(hs, one)
        print(f"  apply_one -> ok={ok} detail={detail}")
        vok, vdetail = verify_one(hs, one)
        print(f"  verify_one -> ok={vok} detail={vdetail}")
        print("\nIf the canary is correct, run: apply  (otherwise STOP and rethink).")
        return

    # apply: backup first, then full batch
    _backup(hs, pid)
    os.makedirs(LOG_DIR, exist_ok=True)
    logp = os.path.join(LOG_DIR, f"apply-{datetime.date.today().isoformat()}.csv")
    ok = fail = 0
    with open(logp, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["i", "item", "ok", "detail"])
        for i, item in enumerate(items, 1):
            success, detail = apply_one(hs, item)
            ok += success; fail += (not success)
            w.writerow([i, json.dumps(item)[:300], success, detail])
            if i % PROGRESS_EVERY == 0 or i == len(items):
                print(f"  {i}/{len(items)}  ok={ok} failed={fail}", flush=True)
    print(f"\nDONE — ok={ok}, failed={fail}, total={len(items)}. Log -> {logp}")
    if fail:
        print("  re-open the log and inspect failed rows' detail.")


if __name__ == "__main__":
    main()
