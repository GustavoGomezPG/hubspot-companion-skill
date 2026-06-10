#!/usr/bin/env python3
"""Backup any HubSpot collection endpoint to a timestamped JSON file BEFORE writes.

The non-destructive workflow's step 2. Dumps the FULL paginated current state so any
later change is reversible (you have every record, not just ids).

Usage:
    python3 backup.py <endpoint> [out.json] [--token pat-...]

Examples:
    python3 backup.py /cms/v3/url-redirects/                 # -> backups/url-redirects-<date>.json
    python3 backup.py /cms/v3/hubdb/tables/250847509/rows backups/tbl-rows.json
    python3 backup.py /cms/v3/pages/site-pages/
"""
import os, sys, json, datetime
from hs_client import HS, _arg

if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
    sys.exit(__doc__)

endpoint = sys.argv[1]
out = None
for a in sys.argv[2:]:
    if a.endswith(".json"):
        out = a
        break

hs = HS(token=_arg("--token"))
pid = hs.validate()
rows = hs.paginate(endpoint)

if not out:
    name = endpoint.strip("/").replace("/", "-").split("?")[0]
    stamp = datetime.date.today().isoformat()
    os.makedirs("backups", exist_ok=True)
    out = os.path.join("backups", f"{name}-{pid}-{stamp}.json")

os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
with open(out, "w") as f:
    json.dump({"portal": pid, "endpoint": endpoint, "count": len(rows), "results": rows}, f, indent=1)

print(f"backed up {len(rows)} records from portal {pid}")
print(f"  endpoint: {endpoint}")
print(f"  -> {out}")
