#!/usr/bin/env python3
"""Refresh the bundled AGSI+ snapshot so the published figures do not age silently.

The repository ships a dated snapshot in ``data/raw/`` and every number in the report is
computed from it. That is reproducible, but a snapshot rots: six months later the "winter
2025/26" stress test is describing a winter that has already happened.

This tool closes the loop:

    python tools/refresh_snapshots.py --check 30     # CI: fail if the snapshot is older than 30 days
    python tools/refresh_snapshots.py --write        # fetch and write a new dated snapshot
    python tools/refresh_snapshots.py --write --dry-run

Design rules
------------
* No key, no write. AGSI+ requires ``AGSI_KEY``; without it the tool reports the age of the
  snapshot and exits 0, so a missing secret never turns into a red build.
* Validate before writing. A payload that fails the checks is rejected and the old snapshot
  stays in place — a corrupt refresh is worse than a stale one.
* Write a new dated file instead of overwriting. History stays auditable, and a bad snapshot
  can be reverted by deleting one file.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import agsi  # noqa: E402

RAW = os.path.join(ROOT, "data", "raw")


def snapshots() -> list[str]:
    """Dated AGSI snapshots, oldest first (facility files excluded)."""
    files = [f for f in glob.glob(os.path.join(RAW, "agsi_*.json")) if "facilities" not in f]
    return sorted(files)


def newest() -> str | None:
    s = snapshots()
    return s[-1] if s else None


def snapshot_age_days(path: str | None = None) -> int | None:
    path = path or newest()
    if not path:
        return None
    stem = os.path.basename(path).replace("agsi_", "").replace(".json", "")
    try:
        day = dt.date.fromisoformat(stem)
    except ValueError:
        return None
    return (dt.date.today() - day).days


def api_error(payload) -> str | None:
    """AGSI answers with HTTP 200 and an error object when it refuses a request.

    A wrong or expired key therefore looks like a successful call whose body happens to be
    empty. Left alone, the validator would report "no gas day" and send the reader looking
    for a parsing bug instead of an access problem.
    """
    if not isinstance(payload, dict):
        return "response is not a JSON object"
    if payload.get("error"):
        return f"{payload.get('error')}: {payload.get('message') or 'no message'}"
    if str(payload.get("dataset") or "").endswith("ERROR"):
        return f"dataset marked ERROR: {payload.get('message') or 'no message'}"
    return None


def validate(payload: dict) -> list[str]:
    """Return a list of problems; an empty list means the payload may be written."""
    problems: list[str] = []
    day = payload.get("_gas_day")
    if not day:
        problems.append("no gas day")
        return problems
    try:
        gas_day = dt.date.fromisoformat(day)
    except ValueError:
        return [f"gas day is not an ISO date: {day!r}"]
    if gas_day > dt.date.today() + dt.timedelta(days=1):
        problems.append(f"gas day in the future: {day}")

    eu = payload.get("eu") or {}
    for field in ("gasInStorage", "workingGasVolume", "full"):
        if field not in eu:
            problems.append(f"eu.{field} missing")
    stored, volume, full = eu.get("gasInStorage"), eu.get("workingGasVolume"), eu.get("full")
    if isinstance(stored, (int, float)) and isinstance(volume, (int, float)) and volume > 0:
        if not 0 <= stored <= volume * 1.02:
            problems.append(f"stored {stored} outside 0..{volume:.0f}")
        implied = 100 * stored / volume
        if isinstance(full, (int, float)) and abs(implied - full) > 2.0:
            problems.append(f"full={full} disagrees with stored/volume={implied:.1f}")
    if not payload.get("countries"):
        problems.append("no country breakdown")
    return problems


def describe(payload: dict) -> str:
    eu = payload.get("eu", {})
    return ("gas day %s: EU %.0f / %.0f TWh (%.1f%% full), %d countries"
            % (payload.get("_gas_day"), eu.get("gasInStorage", float("nan")),
               eu.get("workingGasVolume", float("nan")), eu.get("full", float("nan")),
               len(payload.get("countries", []))))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="fetch and write a new snapshot")
    ap.add_argument("--dry-run", action="store_true", help="fetch and validate, write nothing")
    ap.add_argument("--check", type=int, metavar="DAYS", default=0,
                    help="exit 1 if the newest snapshot is older than DAYS")
    args = ap.parse_args()

    current = newest()
    age = snapshot_age_days(current)
    print(f"newest snapshot: {os.path.basename(current) if current else 'none'} "
          f"({age if age is not None else '?'} days old)")

    if args.check and age is not None and age > args.check:
        print(f"FAIL: snapshot is {age} days old, limit {args.check}. "
              f"Run with --write and a valid AGSI_KEY.")
        return 1

    if not args.write and not args.dry_run:
        return 0

    if not agsi.key():
        print("AGSI_KEY is not set — nothing fetched. The snapshot stays as it is.")
        return 0

    payload = agsi.fetch_latest()
    refusal = api_error(payload)
    if refusal:
        print(f"AGSI refused the request ({refusal}).")
        print("A key is required: register at https://agsi.gie.eu/ and export AGSI_KEY.")
        return 1
    problems = validate(payload)
    fetched_day = payload.get("_gas_day")
    if fetched_day:
        age_of_fetch = (dt.date.today() - dt.date.fromisoformat(fetched_day)).days
        if age_of_fetch > 30:
            problems.append(f"the API returned {fetched_day}, {age_of_fetch} days old")
    if problems:
        print("rejected payload:")
        for p in problems:
            print("  -", p)
        return 1

    print("fetched:", describe(payload))
    if args.dry_run:
        print("dry run: nothing written")
        return 0

    day = payload["_gas_day"]
    target = os.path.join(RAW, f"agsi_{day}.json")
    if os.path.exists(target):
        print(f"snapshot for {day} already exists, not overwriting")
        return 0
    payload["_meta"] = {
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "GIE AGSI+ https://agsi.gie.eu/api",
        "tool": "tools/refresh_snapshots.py",
    }
    with open(target, "w") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
        f.write("\n")
    print("wrote", os.path.relpath(target, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
