#!/usr/bin/env python3
"""Import a country-aggregated AGSI CSV export into the repository's snapshot format.

AGSI's API needs a key, but the website's "Download current data view" button exports the
same view as a semicolon-separated CSV. That file is enough to rebuild everything this
repository uses except the winter block: a single gas day carries current stock, fill,
capacities and flows, but not the min/max fill and peak withdrawal of a whole winter.

So the importer writes what the file can support and refuses to invent the rest. The
winter-derived modules keep using the last full snapshot; anything reading current levels
uses this one. Mixing the two silently is exactly the failure this repository audits.

    python tools/import_agsi_csv.py path/to/AGSI_CountryAggregatedDataset_gasDayEnd_2026-11-17.csv
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "current")

# AGSI prints names; the rest of the repository keys on ISO-2.
CODES = {
    "Austria": "AT", "Belgium": "BE", "Bulgaria": "BG", "Croatia": "HR",
    "Czechia": "CZ", "Czech Republic": "CZ", "Denmark": "DK", "France": "FR",
    "Germany": "DE", "Hungary": "HU", "Ireland": "IE", "Italy": "IT",
    "Latvia": "LV", "Lithuania": "LT", "Netherlands": "NL", "Poland": "PL",
    "Portugal": "PT", "Romania": "RO", "Slovakia": "SK", "Slovenia": "SI",
    "Spain": "ES", "Sweden": "SE", "Ukraine": "UA", "United Kingdom": "GB",
    "United Kingdom (Post-Brexit)": "GB", "Serbia": "RS",
}

# The export carries rows this repository does not model: an empty pre-Brexit placeholder and
# a Non-EU aggregate. Both are dropped by name rather than by guessing at their numbers.
SKIP = {"United Kingdom (Pre-Brexit)"}

# The EU aggregate covers member states only; Ukraine, Serbia and the UK sit outside it, so a
# naive sum over every country row lands about 117 TWh above the EU total.
EU_MEMBERS = {"AT", "BE", "BG", "HR", "CZ", "DK", "FR", "DE", "HU", "IE", "IT", "LV",
              "LT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}

FIELDS = {
    "stored": "Gas in storage (TWh)",
    "full": "Full (%)",
    "injection": "Injection Capacity (GWh/d)",
    "withdrawal": "Withdrawal Capacity (GWh/d)",
    "volume": "Technical Capacity (TWh)",
}


def _num(row: dict, key: str) -> float:
    raw = (row.get(key) or "").strip().replace(",", ".")
    return float(raw) if raw else 0.0


def gas_day_from_name(path: str) -> str | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
    return m.group(1) if m else None


def read_csv(path: str) -> tuple[dict, list[dict], list[str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    if not rows:
        raise RuntimeError("the file has no rows")
    missing = [k for k in FIELDS.values() if k not in rows[0]]
    if missing:
        raise RuntimeError(f"unexpected columns, missing: {missing}")

    eu_row = next((r for r in rows if r.get("Type") == "EU"), None)
    if eu_row is None:
        raise RuntimeError("no EU aggregate row in the file")

    countries, unknown = [], []
    for r in rows:
        if r.get("Type") != "country":
            continue
        name = (r.get("Name") or "").strip()
        if name in SKIP:
            continue
        code = CODES.get(name)
        if not code:
            unknown.append(name)
            continue
        countries.append({
            "code": code,
            "gasInStorage": _num(r, FIELDS["stored"]),
            "workingGasVolume": _num(r, FIELDS["volume"]),
            "full": _num(r, FIELDS["full"]),
            "injectionCapacity": _num(r, FIELDS["injection"]),
            "withdrawalCapacity": _num(r, FIELDS["withdrawal"]),
            "flowWithdrawal": _num(r, "Withdrawal (GWh/d)"),
            "flowInjection": _num(r, "Injection (GWh/d)"),
            "consumption": _num(r, "Consumption (TWh)"),
            "stock_over_consumption": _num(r, "Stock/Cons (%)"),
        })

    eu = {
        "gasInStorage": _num(eu_row, FIELDS["stored"]),
        "workingGasVolume": _num(eu_row, FIELDS["volume"]),
        "full": _num(eu_row, FIELDS["full"]),
        "injectionCapacity": _num(eu_row, FIELDS["injection"]),
        "withdrawalCapacity": _num(eu_row, FIELDS["withdrawal"]),
        "flowWithdrawal": _num(eu_row, "Withdrawal (GWh/d)"),
        "flowInjection": _num(eu_row, "Injection (GWh/d)"),
        "consumption": _num(eu_row, "Consumption (TWh)"),
        "stock_over_consumption": _num(eu_row, "Stock/Cons (%)"),
    }
    return eu, sorted(countries, key=lambda c: -c["gasInStorage"]), unknown


def validate(eu: dict, countries: list[dict]) -> list[str]:
    problems = []
    if not countries:
        problems.append("no country rows recognised")
    volume, stored, full = eu["workingGasVolume"], eu["gasInStorage"], eu["full"]
    if volume <= 0:
        problems.append("EU technical capacity is zero")
    else:
        if not 0 <= stored <= volume * 1.05:
            problems.append(f"EU stored {stored} outside 0..{volume}")
        implied = 100 * stored / volume
        if abs(implied - full) > 1.5:
            problems.append(f"EU full={full} disagrees with stored/volume={implied:.2f}")
        total = sum(c["gasInStorage"] for c in countries if c["code"] in EU_MEMBERS)
        if abs(total - stored) > max(2.0, 0.01 * stored):
            problems.append(f"EU member rows sum to {total:.1f} TWh against EU {stored:.1f}")
    for c in countries:
        if c["workingGasVolume"] > 0:
            implied = 100 * c["gasInStorage"] / c["workingGasVolume"]
            if abs(implied - c["full"]) > 2.0:
                problems.append(f"{c['code']}: full={c['full']} vs {implied:.1f}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path")
    ap.add_argument("--gas-day", help="override the date taken from the filename")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    day = args.gas_day or gas_day_from_name(args.csv_path)
    if not day:
        print("cannot read the gas day from the filename; pass --gas-day YYYY-MM-DD")
        return 1
    dt.date.fromisoformat(day)

    eu, countries, unknown = read_csv(args.csv_path)
    if unknown:
        print("unknown country names, add them to CODES:", unknown)
        return 1

    problems = validate(eu, countries)
    if problems:
        print("rejected file:")
        for p in problems:
            print("  -", p)
        return 1

    payload = {
        "_gas_day": day,
        "_retrieved": dt.date.today().isoformat(),
        "_units": {"stored": "TWh", "capacity": "GWh/d", "consumption": "TWh"},
        "_source": "AGSI country-aggregated CSV export",
        "_note": ("single gas day: current stock, fill, capacities and flows. The winter "
                  "block (min/max fill, peak withdrawal) needs a season of daily data and is "
                  "not derivable from one file."),
        "eu": eu,
        "countries": countries,
        "winter_2025_26": [],
    }

    print(f"gas day {day}: EU {eu['gasInStorage']:.1f} / {eu['workingGasVolume']:.1f} TWh "
          f"= {eu['full']:.2f}% full, {len(countries)} countries")
    if args.dry_run:
        print("dry run: nothing written")
        return 0

    os.makedirs(RAW, exist_ok=True)
    target = os.path.join(RAW, f"agsi_{day}.json")
    if os.path.exists(target):
        print(f"{os.path.relpath(target, ROOT)} already exists, not overwriting")
        return 0
    with open(target, "w") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
        f.write("\n")
    print("wrote", os.path.relpath(target, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
