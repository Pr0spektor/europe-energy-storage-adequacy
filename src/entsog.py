"""ENTSOG Transparency Platform client — the gas network layer.

https://transparency.entsog.eu/api/v1/ is fully open: **no API key, no registration**.
Two endpoints are used:

  interconnections.csv?fromCountryKey=DE&toCountryKey=PL
      topology — which points join which two countries, which TSO runs each side,
      and ENTSOG's schematic map coordinates (tpMapX / tpMapY).

  operationalData.csv?indicator=Physical Flow&periodType=day&pointDirection=<key>
      metered daily flow, and with indicator="Firm Technical" the firm capacity
      of the same point-direction.  `pointDirection` = operatorKey + pointKey +
      direction, e.g. "DE-TSO-0009ITP-00080entry".

Only periodType=day is supported by operationalData, and the API caps how many
pointDirection values fit in one URL, so `fetch_flows` batches them.

Running offline: a verified snapshot of Germany's borders on the gas day
2026-01-15 is bundled in data/raw/entsog_de_border_2026-01-15.json, and every
function falls back to it when the network is unavailable.
"""
from __future__ import annotations
import csv, io, json, os, urllib.parse, urllib.request

BASE = "https://transparency.entsog.eu/api/v1"
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SNAPSHOT = os.path.join(DATA, "raw", "entsog_de_border_2026-01-15.json")
BATCH = 3          # pointDirection values per request — the API limits URL length
TIMEOUT = 30


def _get(endpoint: str, params: dict) -> str:
    url = "%s/%s?%s" % (BASE, endpoint, urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")


def _rows(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text.strip()))) if text.strip() else []


def snapshot() -> dict:
    with open(SNAPSHOT) as f:
        return json.load(f)


def fetch_topology(from_country: str, to_country: str) -> list[dict]:
    """Interconnection points between two countries. Falls back to the snapshot."""
    try:
        rows = _rows(_get("interconnections.csv",
                          {"fromCountryKey": from_country, "toCountryKey": to_country}))
    except Exception:
        snap = snapshot()
        return [p for p in snap["points"]
                if p.get("from") == from_country and p.get("to") == to_country]
    out = []
    for r in rows:
        if not r.get("pointKey", "").startswith("ITP"):
            continue                     # keep interconnection points, drop DIS/UGS/FNC
        out.append({"pointKey": r["pointKey"], "label": r["pointLabel"],
                    "from": r["fromCountryKey"], "to": r["toCountryKey"],
                    "operator": r.get("fromOperatorLabel") or r.get("toOperatorLabel"),
                    "operatorKey": r.get("fromOperatorKey") or r.get("toOperatorKey"),
                    "direction": r.get("fromDirectionKey") or r.get("toDirectionKey"),
                    "x": float(r["pointTpMapX"] or 0), "y": float(r["pointTpMapY"] or 0)})
    return out


def point_direction(operator_key: str, point_key: str, direction: str) -> str:
    return "%s%s%s" % (operator_key, point_key, direction)


def fetch_flows(point_directions: list[str], gas_day: str,
                indicator: str = "Physical Flow") -> dict[str, float]:
    """{pointDirection: value in kWh/d} for one gas day. Falls back to the snapshot."""
    out: dict[str, float] = {}
    try:
        for i in range(0, len(point_directions), BATCH):
            chunk = point_directions[i:i + BATCH]
            for r in _rows(_get("operationalData.csv",
                                {"from": gas_day, "to": gas_day, "indicator": indicator,
                                 "periodType": "day", "pointDirection": ",".join(chunk)})):
                if r.get("value") in (None, ""):
                    continue
                out[point_direction(r["operatorKey"], r["pointKey"], r["directionKey"])] = \
                    float(r["value"])
        return out
    except Exception:
        field = "physical_flow" if indicator == "Physical Flow" else "firm_technical"
        snap = snapshot()
        for p in snap["points"]:
            key = point_direction(p["operatorKey"], p["pointKey"], p["direction"])
            if key in point_directions and p.get(field) is not None:
                out[key] = p[field]
        return out


if __name__ == "__main__":
    snap = snapshot()
    print("bundled snapshot: gas day %s, %d verified metered points"
          % (snap["_gas_day"], len(snap["points"])))
    for p in snap["points"]:
        print("  %-22s %s->%s  flow %8.1f GWh/d  firm %8.1f GWh/d"
              % (p["label"], p["from"], p["to"],
                 p["physical_flow"] / 1e6, p["firm_technical"] / 1e6))
