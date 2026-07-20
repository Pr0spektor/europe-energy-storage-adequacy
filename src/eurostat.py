"""Eurostat client — real monthly energy consumption for every European country.

One request returns **all countries** (no `geo` filter) from 2020-01 to the latest month
Eurostat publishes; the client discovers that latest month from the dataset's own metadata,
parses JSON-stat, validates the result and caches it to `data/`.

Automatic by design: `ensure_data()` refreshes the cache when it is missing or stale and
falls back to the cached copy when offline, so `analysis.py` always runs on the freshest
data available.

    python src/eurostat.py --refresh                    # all countries, gas, 2020-01..latest
    python src/eurostat.py --refresh --dataset nrg_cb_em   # electricity
    python src/eurostat.py --report                     # coverage + validation report

Datasets
    nrg_cb_gasm : gas, monthly       (nrg_bal=IC_OBS, siec=G3000, unit=TJ_GCV)
    nrg_cb_em   : electricity, monthly (unit=GWH; balance code discovered at runtime)
"""
from __future__ import annotations
import argparse, json, os, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
START = "2020-01"                      # covers COVID, the 2022 energy crisis, and after

GAS = {"key": "gas", "dataset": "nrg_cb_gasm",
       "params": {"nrg_bal": "IC_OBS", "siec": "G3000", "unit": "TJ_GCV"},
       "cache": "eurostat_gas_monthly.json", "unit": "TJ_GCV"}
ELEC = {"key": "electricity", "dataset": "nrg_cb_em",
        "params": {"siec": "E7000", "unit": "GWH"},
        "cache": "eurostat_electricity_monthly.json", "unit": "GWH"}

# aggregates carried alongside the countries
AGGREGATES = {"EU27_2020", "EA21", "EA20", "EA19"}


def _url(dataset: str, params: dict) -> str:
    return f"{BASE}/{dataset}?" + urllib.parse.urlencode({"format": "JSON", "lang": "EN", **params},
                                                         doseq=True)


def fetch_jsonstat(dataset: str, params: dict, timeout: float = 90.0):
    """GET one JSON-stat document; returns None on any network/parse failure."""
    try:
        with urllib.request.urlopen(_url(dataset, params), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:                                    # offline / blocked / API change
        print(f"    fetch failed: {type(e).__name__}: {e}")
        return None


def _annotation(doc, kind: str):
    for a in doc.get("extension", {}).get("annotation", []):
        if a.get("type") == kind:
            return a.get("title") or a.get("date")
    return None


def latest_period(dataset: str, params: dict) -> str | None:
    """Ask the dataset which month it currently ends at (no hard-coded end date)."""
    doc = fetch_jsonstat(dataset, {**params, "sinceTimePeriod": "2026-01",
                                   "untilTimePeriod": "2026-01"})
    return _annotation(doc, "OBS_PERIOD_OVERALL_LATEST") if doc else None


def parse_jsonstat(doc) -> dict:
    """JSON-stat (all geos x all months) -> {geo: {year: [12 values]}}.

    Uses the declared dimension sizes so the flat value index is decoded correctly
    regardless of how many dimensions the dataset carries.
    """
    if not doc or not doc.get("value"):
        return {}
    ids, sizes = doc["id"], doc["size"]
    geo_axis, time_axis = ids.index("geo"), ids.index("time")
    geos = list(doc["dimension"]["geo"]["category"]["index"].keys())
    times = list(doc["dimension"]["time"]["category"]["index"].keys())

    # strides for a row-major flat index
    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]

    out: dict[str, dict[str, list]] = {}
    for flat, val in doc["value"].items():
        idx = int(flat)
        g = (idx // strides[geo_axis]) % sizes[geo_axis]
        t = (idx // strides[time_axis]) % sizes[time_axis]
        geo, period = geos[g], times[t]
        year, month = period.split("-")
        out.setdefault(geo, {}).setdefault(year, [None] * 12)[int(month) - 1] = val
    return out


def validate(series: dict) -> dict:
    """Sanity-check the pulled data before anything is computed from it."""
    issues, complete, partial = [], 0, 0
    for geo, years in series.items():
        for year, months in years.items():
            present = [m for m in months if m is not None]
            if not present:
                issues.append(f"{geo} {year}: no observations")
                continue
            if any(m < 0 for m in present):
                issues.append(f"{geo} {year}: negative consumption")
            if len(present) == 12:
                complete += 1
            else:
                partial += 1
    return {"countries": len(series), "complete_country_years": complete,
            "partial_country_years": partial, "issues": issues, "ok": not issues}


def refresh(spec: dict, since: str = START, until: str | None = None) -> dict:
    """Pull every country in one request, validate, and write the cache."""
    params = dict(spec["params"])
    if spec is ELEC and "nrg_bal" not in params:
        codes = balance_codes(spec["dataset"])
        params["nrg_bal"] = "FC_E" if "FC_E" in codes else (codes[0] if codes else "FC_E")
        print(f"    electricity balance code: {params['nrg_bal']}")
    until = until or latest_period(spec["dataset"], params)
    q = {**params, "sinceTimePeriod": since}
    if until:
        q["untilTimePeriod"] = until
    print(f"  requesting {spec['dataset']} for ALL countries {since}..{until or 'latest'}")
    doc = fetch_jsonstat(spec["dataset"], q)
    series = parse_jsonstat(doc)
    if not series:
        print("  no data returned — keeping existing cache")
        return load_cache(spec) or {}
    rep = validate(series)
    blob = {"_source": f"Eurostat {spec['dataset']}", "_unit": spec["unit"],
            "_indicator": params, "_api": f"{BASE}/{spec['dataset']}",
            "_period": {"since": since, "until": until},
            "_retrieved": time.strftime("%Y-%m-%d %H:%M:%S"),
            "_validation": rep, "series": series}
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, spec["cache"]), "w") as f:
        json.dump(blob, f, indent=1)
    print(f"  cached {rep['countries']} countries, {rep['complete_country_years']} complete "
          f"country-years ({len(rep['issues'])} issues)")
    return blob


def load_raw_dir(subdir: str = "raw", prefix: str = "gas_") -> dict:
    """Parse every raw JSON-stat file in data/raw/ and merge into {geo: {year: [12]}}.

    Raw responses are stored verbatim (no interpretation) and decoded by the same
    unit-tested parser used for live pulls, so the bundled data is auditable.
    """
    d = os.path.join(DATA, subdir)
    merged: dict[str, dict[str, list]] = {}
    if not os.path.isdir(d):
        return merged
    for name in sorted(os.listdir(d)):
        if not (name.startswith(prefix) and name.endswith(".json")):
            continue
        with open(os.path.join(d, name)) as f:
            doc = json.load(f)
        for geo, years in parse_jsonstat(doc).items():
            for year, months in years.items():
                slot = merged.setdefault(geo, {}).setdefault(year, [None] * 12)
                for i, v in enumerate(months):
                    if v is not None:
                        slot[i] = v
    return merged


def load_cache(spec: dict) -> dict | None:
    path = os.path.join(DATA, spec["cache"])
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def cache_age_days(spec: dict) -> float:
    path = os.path.join(DATA, spec["cache"])
    return (time.time() - os.path.getmtime(path)) / 86400.0 if os.path.exists(path) else 1e9


def ensure_data(spec: dict = GAS, max_age_days: float = 7.0, offline: bool = False) -> dict:
    """Refresh automatically when the cache is missing or stale; fall back when offline."""
    if not offline and cache_age_days(spec) > max_age_days:
        print(f"[eurostat] cache for {spec['key']} is stale/missing — refreshing")
        refresh(spec)
    blob = load_cache(spec) or {}
    if not blob:
        print(f"[eurostat] no data for {spec['key']}")
    return blob


def monthly_series(spec: dict = GAS, auto: bool = True) -> dict:
    blob = ensure_data(spec) if auto else (load_cache(spec) or {})
    return blob.get("series", {})


def balance_codes(dataset: str) -> list[str]:
    doc = fetch_jsonstat(dataset, {"sinceTimePeriod": "2026-01", "untilTimePeriod": "2026-01"})
    if not doc:
        return []
    return list(doc["dimension"]["nrg_bal"]["category"]["index"].keys())


def countries_only(series: dict) -> dict:
    return {g: y for g, y in series.items() if g not in AGGREGATES}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Eurostat monthly energy consumption (all countries)")
    ap.add_argument("--refresh", action="store_true", help="force a pull from the API")
    ap.add_argument("--report", action="store_true", help="print coverage and validation")
    ap.add_argument("--dataset", default="nrg_cb_gasm", choices=["nrg_cb_gasm", "nrg_cb_em"])
    ap.add_argument("--since", default=START)
    a = ap.parse_args()
    spec = GAS if a.dataset == "nrg_cb_gasm" else ELEC
    blob = refresh(spec, a.since) if a.refresh else (load_cache(spec) or {})
    series = blob.get("series", {})
    print(f"\n{spec['key']}: {len(countries_only(series))} countries "
          f"(+{len(series) - len(countries_only(series))} aggregates), unit {spec.get('_unit', spec['unit'])}")
    print(f"period: {blob.get('_period')}  retrieved: {blob.get('_retrieved')}")
    if a.report:
        rep = blob.get("_validation") or validate(series)
        print(f"complete country-years: {rep['complete_country_years']}, "
              f"partial: {rep['partial_country_years']}, issues: {len(rep['issues'])}")
        for i in rep["issues"][:15]:
            print("   -", i)
