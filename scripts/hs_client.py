#!/usr/bin/env python3
"""Rate-limited HubSpot API client for the hubspot-companion skill. Stdlib only.

Token resolution order:
    1. --token <key>                         (CLI override)
    2. HUBSPOT_SERVICE_KEY in a .env file     (recommended — see .env.example)
       (also accepts HUB_SPOT_SERVICE_KEY / HUBSPOT_TOKEN as aliases)
    3. HUBSPOT_SERVICE_KEY already in the environment

The .env is searched in: the current working dir, then the skill root, then this scripts dir.
Never commit your .env — it holds a live credential (see .gitignore).

Library use:
    from hs_client import HS
    hs = HS()                              # reads the key from .env / env
    hs.validate()                          # -> portal id, raises on a bad key
    domains = hs.get("/cms/v3/domains/?limit=100")
    allred  = hs.paginate("/cms/v3/url-redirects/")        # auto-paginated list
    hs.patch("/cms/v3/url-redirects/123", {"destination": "https://x/y"})
    hs.delete("/cms/v3/url-redirects/123")

CLI:
    python3 hs_client.py validate
    python3 hs_client.py get /cms/v3/domains/
    python3 hs_client.py paginate /cms/v3/url-redirects/
    python3 hs_client.py validate --token pat-xxxx        # one-off, bypass .env
"""
import os, sys, json, time, urllib.request, urllib.parse, urllib.error

API = "https://api.hubapi.com"
KEY_ALIASES = ["HUBSPOT_SERVICE_KEY", "HUB_SPOT_SERVICE_KEY", "HUBSPOT_TOKEN"]


def load_dotenv():
    """Load KEY=VALUE lines from a .env (cwd -> skill root -> scripts dir) into os.environ.
    Does not override variables already set in the real environment. Returns the path used."""
    here = os.path.dirname(os.path.abspath(__file__))
    for envp in (os.path.join(os.getcwd(), ".env"),
                 os.path.join(here, "..", ".env"),
                 os.path.join(here, ".env")):
        if os.path.isfile(envp):
            for line in open(envp):
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return envp
    return None


def resolve_token(token=None):
    if token:
        return token
    load_dotenv()
    for k in KEY_ALIASES:
        if os.environ.get(k):
            return os.environ[k]
    raise SystemExit(
        "No HubSpot Service Key found.\n"
        "  Create a .env file in this folder containing:\n"
        "      HUBSPOT_SERVICE_KEY=your-service-key-here\n"
        "  (copy .env.example to .env), or pass --token <key>.\n"
        "  Get a key at: Settings > Account Management > Keys > Service Keys.")


class HS:
    def __init__(self, token=None, min_interval=0.12):
        self.token = resolve_token(token)
        self.min_interval = min_interval
        self._last = 0.0
        self.portal_id = None

    def _req(self, method, path, body=None):
        # space requests to respect 100 req / 10s
        dt = time.time() - self._last
        if dt < self.min_interval:
            time.sleep(self.min_interval - dt)
        url = API + path
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, method=method, data=data, headers={
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    self._last = time.time()
                    txt = resp.read().decode()
                    return resp.status, (json.loads(txt) if txt else None)
            except urllib.error.HTTPError as e:
                self._last = time.time()
                if e.code in (429, 500, 502, 503) and attempt < 5:
                    time.sleep(min(2 * (attempt + 1), 20))
                    continue
                return e.code, e.read().decode()[:400]
            except Exception:
                time.sleep(2 * (attempt + 1))
        return None, "exhausted retries"

    def get(self, path):
        return self._req("GET", path)

    def post(self, path, body):
        return self._req("POST", path, body)

    def patch(self, path, body):
        return self._req("PATCH", path, body)

    def delete(self, path):
        return self._req("DELETE", path)

    def paginate(self, path, limit=1000):
        """Return the full results[] list of a paginated collection endpoint."""
        sep = "&" if "?" in path else "?"
        out, after = [], None
        while True:
            p = f"{path}{sep}limit={limit}" + (f"&after={after}" if after else "")
            st, d = self._req("GET", p)
            if st != 200 or not isinstance(d, dict):
                raise SystemExit(f"paginate failed at after={after}: {st} {str(d)[:200]}")
            out += d.get("results", [])
            after = (d.get("paging", {}).get("next") or {}).get("after")
            if not after:
                return out

    def validate(self):
        st, d = self._req("GET", "/account-info/v3/details")
        if st != 200:
            raise SystemExit(f"key invalid ({st}): {str(d)[:200]}")
        self.portal_id = d.get("portalId")
        return self.portal_id


def _arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    hs = HS(token=_arg("--token"))
    if cmd == "validate":
        print("portalId:", hs.validate())
    elif cmd == "get":
        st, d = hs.get(sys.argv[2])
        print(st); print(json.dumps(d, indent=1)[:4000])
    elif cmd == "paginate":
        rows = hs.paginate(sys.argv[2])
        print(f"{len(rows)} results")
        print(json.dumps(rows[:3], indent=1))
    else:
        sys.exit(__doc__)
