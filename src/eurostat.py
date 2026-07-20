"""Eurostat client: real monthly gas and electricity consumption per country.

Pulls JSON-stat from the open Eurostat dissemination API (no key required), parses it
into {country: {year: [12 monthly values]}}, and caches to data/. Falls back to the
bundled cache when offline so the analysis always runs.

    python src/eurostat.py                      # show what is cached
    python src/eurostat.py --refresh --geo DE IT FR NL PL
    python src/eurostat.py --refresh --dataset nrg_cb_em --geo DE   # electricity

Datasets
    nrg_cb_gasm : gas, monthly   (nrg_bal=IC_OBS, siec=G3000, unit=TJ_GCV)
    nrg_cb_em   : electricity, monthly (unit=GWH; balance code discovered at runtime)
"""
from __future__ import annotations
import argparse, json, os, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

GAS = {"dataset": "nrg_cb_gasm", "params": {"nrg_bal": "IC_OBS", "siec": "G3000", "unit": "TJ_GCV"},
       "cache": "eurostat_gas_monthly.json", "unit": "TJ_GCV"}
ELEC = {"dataset": "nrg_cb_em", "params": {"siec": "E7000", "unit": "GWH"},
        "cache": "eurostat_electricity_monthly.json", "unit": "GWH"}


def _url(dataset: str, params: dict) -> str:
    q = {"format": "JSON", "lang": "EN", **params}
    return f"{BASE}/{dataset}?" + urllib.parse.urlencode(q, doseq=True)


def fetch_jsonstat(dataset: str, params: dict, timeout: float = 60.0):
    """GET one JSON-stat document. Returns None on any network/parse failure."""
    try:
        with urllib.request.urlopen(_url(dataset, params), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def balance_codes(dataset: str) -> list[str]:
    """Discover the valid nrg_bal codes for a dataset (they differ between gas and power)."""
    doc = fetch_jsonstat(dataset, {"sinceTimePeriod": "2024-01", "untilTimePeriod": "2024-01"})
    if not doc:
        return []
    return list(doc["dimension"]["nrg_bal"]["category"]["index"].keys())


def parse_monthly(doc) -> dict:
    """JSON-stat -> {year: [12 values]} for a single-country response (None for gaps)."""
    if not doc or not doc.get("value"):
        return {}
    times = list(doc["dimension"]["time"]["category"]["index"].keys())
    vals = doc["value"]
    out: dict[str, list] = {}
    for i, period in enumerate(times):
        year, month = period.split("-")
        out.setdefault(year, [None] * 12)[int(month) - 1] = vals.get(str(i))
    return out


def refresh(spec: dict, geos: list[str], since="2020-01", until="2024-12") -> dict:
    """Fetch each country and merge into the on-disk cache (keeps existing entries)."""
    path = os.path.join(DATA, spec["cache"])
    blob = load_cache(spec) or {"series": {}}
    blob.setdefault("series", {})
    for geo in geos:
        params = {**spec["params"], "geo": geo, "sinceTimePeriod": since, "untilTimePeriod": until}
        doc = fetch_jsonstat(spec["dataset"], params)
        series = parse_monthly(doc)
        if series:
            blob["series"][geo] = series
            print(f"  fetched {geo}: {len(series)} years")
        else:
            print(f"  {geo}: no data returned (check balance code or connectivity)")
    blob["_source"] = spec["dataset"]
    blob["_unit"] = spec["unit"]
    os.makedirs(DATA, exist_ok=True)
    with open(path, "w") as f:
        json.dump(blob, f, indent=2)
    return blob


def load_cache(spec: dict) -> dict | None:
    path = os.path.join(DATA, spec["cache"])
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def monthly_series(spec: dict = GAS) -> dict:
    """{country: {year: [12 monthly values]}} from the cache (bundled real data)."""
    blob = load_cache(spec)
    return (blob or {}).get("series", {})


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Eurostat monthly energy consumption")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--dataset", default="nrg_cb_gasm", choices=["nrg_cb_gasm", "nrg_cb_em"])
    ap.add_argument("--geo", nargs="*", default=["DE"])
    ap.add_argument("--since", default="2020-01")
    ap.add_argument("--until", default="2024-12")
    a = ap.parse_args()
    spec = GAS if a.dataset == "nrg_cb_gasm" else ELEC
    if a.refresh:
        if spec is ELEC and "nrg_bal" not in spec["params"]:
            codes = balance_codes(spec["dataset"])
            if codes:
                spec["params"]["nrg_bal"] = "FC_E" if "FC_E" in codes else codes[0]
                print("using electricity balance code:", spec["params"]["nrg_bal"])
        print(f"refreshing {a.dataset} for {a.geo} ({a.since}..{a.until})")
        refresh(spec, a.geo, a.since, a.until)
    s = monthly_series(spec)
    print(f"cached countries: {sorted(s)} | unit {spec['unit']}")
    for geo, years in s.items():
        print(f"  {geo}: years {sorted(years)}")
