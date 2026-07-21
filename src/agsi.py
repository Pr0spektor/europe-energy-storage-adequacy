"""GIE AGSI+ client — facility-level gas storage.

AGSI+ is free but authenticated: create an account at https://agsi.gie.eu/account,
copy the key from the API Account page, and pass it in the **x-key header** (it is
rejected as a query parameter).

    cp .env.example .env && $EDITOR .env      # paste your key into AGSI_KEY
    python src/agsi.py                        # or: AGSI_KEY=... python src/agsi.py

Without a key nothing breaks: every function falls back to the snapshots bundled in
data/raw/, which is what reproduces the published figures. The key only buys fresher data.

Endpoints used:
    /api                                    latest gas day, EU -> countries -> companies -> facilities
    /api?type=eu&from=..&to=..&size=..      EU aggregate daily history (paginated)
    /api?country=DE&from=..&to=..           one country's daily history

Offline, everything falls back to the bundled snapshots in data/raw/:
    agsi_2026-07-18.json                 EU + 18 countries, 7 gas years, winter 2025/26
    agsi_de_facilities_2026-07-18.json   German operators and individual sites
"""
from __future__ import annotations
import json, os, urllib.request

API = "https://agsi.gie.eu/api"
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
SNAP = os.path.join(DATA, "agsi_2026-07-18.json")
FAC = os.path.join(DATA, "agsi_de_facilities_2026-07-18.json")
TIMEOUT = 30


def key() -> str | None:
    """The AGSI+ key, from the environment or from a local .env file.

    Never stored in the repository: .env is git-ignored and .env.example ships empty.
    """
    k = os.environ.get("AGSI_KEY")
    if k:
        return k.strip() or None
    env = os.path.join(os.path.dirname(DATA), "..", ".env")
    env = os.path.normpath(env)
    if os.path.exists(env):
        for line in open(env):
            line = line.strip()
            if line.startswith("AGSI_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"\'') or None
    return None


def _get(params: str = "") -> dict:
    k = key()
    if not k:
        raise RuntimeError("AGSI_KEY is not set — see https://agsi.gie.eu/account")
    req = urllib.request.Request(API + ("?" + params if params else ""), headers={"x-key": k})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def snapshot() -> dict:
    with open(SNAP) as f:
        return json.load(f)


def facilities_de() -> dict:
    with open(FAC) as f:
        return json.load(f)


def fetch_latest() -> dict:
    """EU + country snapshot for the latest gas day. Falls back to the bundle."""
    try:
        eu = _get()["data"][0]
        f = lambda v: float(v) if v not in ("", None) else float("nan")
        return {"_gas_day": eu["gasDayStart"],
                "eu": {"gasInStorage": f(eu["gasInStorage"]), "workingGasVolume": f(eu["workingGasVolume"]),
                       "full": f(eu["full"]), "injectionCapacity": f(eu["injectionCapacity"]),
                       "withdrawalCapacity": f(eu["withdrawalCapacity"])},
                "countries": [{"code": c["code"], "gasInStorage": f(c["gasInStorage"]),
                               "workingGasVolume": f(c["workingGasVolume"]), "full": f(c["full"]),
                               "injectionCapacity": f(c["injectionCapacity"]),
                               "withdrawalCapacity": f(c["withdrawalCapacity"])}
                              for c in eu.get("children", [])]}
    except Exception:
        return snapshot()


def fetch_history(country: str = "eu", start: str = "2020-01-01", end: str = "2026-07-18") -> list[dict]:
    """Daily series. `country='eu'` uses the type=eu aggregate. Empty list when offline."""
    sel = "type=eu" if country.lower() == "eu" else "country=" + country
    rows: list[dict] = []
    try:
        page = 1
        while page <= 20:
            j = _get("%s&from=%s&to=%s&size=300&page=%d" % (sel, start, end, page))
            data = j.get("data") or []
            rows += [d for d in data if d.get("gasDayStart")]
            if not data or page >= (j.get("last_page") or 1):
                break
            page += 1
    except Exception:
        return []
    rows.sort(key=lambda d: d["gasDayStart"])
    return rows


if __name__ == "__main__":
    s = fetch_latest()
    eu = s["eu"]
    print("gas day %s — EU storage %.0f / %.0f TWh (%.1f%% full), withdrawal capacity %.1f TWh/d"
          % (s["_gas_day"], eu["gasInStorage"], eu["workingGasVolume"], eu["full"],
             eu["withdrawalCapacity"] / 1000))
    print("key present:", bool(key()))
