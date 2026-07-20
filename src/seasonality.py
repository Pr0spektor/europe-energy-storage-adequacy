"""Seasonal swing of energy consumption, per country and per year, from real monthly data.

The whole storage case rests on this number: how much more energy a country burns in
winter than in summer, and how much of the annual total has to be carried across the year.
Metrics per country-year:

  peak_to_trough   — highest month / lowest month (the classic seasonality ratio)
  winter_summer    — mean(Dec-Feb) / mean(Jun-Aug)
  swing_share      — share of annual consumption that sits above a flat baseline
                     (i.e. the fraction that must come from storage or flexible supply)
  swing_absolute   — that share expressed in the data's own unit

Stdlib only; unit-tested.
"""
from __future__ import annotations
from typing import Sequence
from eurostat import monthly_series, GAS

WINTER = (11, 0, 1)      # Dec, Jan, Feb (0-indexed)
SUMMER = (5, 6, 7)       # Jun, Jul, Aug


def _clean(months: Sequence[float | None]) -> list[float]:
    return [m for m in months if m is not None]


def peak_to_trough(months: Sequence[float | None]) -> float | None:
    v = _clean(months)
    if len(v) < 12 or min(v) <= 0:
        return None
    return max(v) / min(v)


def winter_summer_ratio(months: Sequence[float | None]) -> float | None:
    if len(months) < 12 or any(months[i] is None for i in WINTER + SUMMER):
        return None
    w = sum(months[i] for i in WINTER) / 3.0
    s = sum(months[i] for i in SUMMER) / 3.0
    return w / s if s else None


def swing(months: Sequence[float | None]) -> dict | None:
    """Energy above a flat (annual-average) baseline — what flexibility must cover."""
    v = _clean(months)
    if len(v) < 12:
        return None
    total = sum(v)
    baseline = total / 12.0
    above = sum(m - baseline for m in v if m > baseline)
    return {"annual_total": total, "swing_absolute": above,
            "swing_share": above / total if total else None}


def country_year_table(series: dict | None = None) -> list[dict]:
    """One row per country-year with every seasonality metric."""
    series = series if series is not None else monthly_series(GAS)
    rows = []
    for geo, years in sorted(series.items()):
        for year, months in sorted(years.items()):
            sw = swing(months)
            rows.append({
                "country": geo, "year": year,
                "peak_to_trough": peak_to_trough(months),
                "winter_summer": winter_summer_ratio(months),
                "swing_share": sw["swing_share"] if sw else None,
                "swing_absolute": sw["swing_absolute"] if sw else None,
                "annual_total": sw["annual_total"] if sw else None,
            })
    return rows


def summarise(rows: Sequence[dict]) -> dict:
    """Averages across the period, per country, plus the trend in seasonality."""
    out = {}
    for geo in sorted({r["country"] for r in rows}):
        sub = [r for r in rows if r["country"] == geo and r["peak_to_trough"]]
        if not sub:
            continue
        first, last = sub[0], sub[-1]
        out[geo] = {
            "years": [r["year"] for r in sub],
            "mean_peak_to_trough": sum(r["peak_to_trough"] for r in sub) / len(sub),
            "mean_winter_summer": sum(r["winter_summer"] for r in sub) / len(sub),
            "mean_swing_share": sum(r["swing_share"] for r in sub) / len(sub),
            "peak_to_trough_first_year": first["peak_to_trough"],
            "peak_to_trough_last_year": last["peak_to_trough"],
            "change": last["peak_to_trough"] - first["peak_to_trough"],
        }
    return out


if __name__ == "__main__":
    rows = country_year_table()
    if not rows:
        print("no cached data — run: python src/eurostat.py --refresh --geo DE IT FR")
    else:
        print(f"{'country':8s}{'year':6s}{'peak/trough':>13s}{'winter/summer':>15s}{'swing share':>13s}")
        for r in rows:
            print("%-8s%-6s%13.2f%15.2f%12.1f%%"
                  % (r["country"], r["year"], r["peak_to_trough"],
                     r["winter_summer"], r["swing_share"] * 100))
        print()
        for geo, s in summarise(rows).items():
            print("%s: mean peak/trough %.2f, winter/summer %.2f, swing %.1f%% of annual "
                  "(%.2f -> %.2f over %s-%s)"
                  % (geo, s["mean_peak_to_trough"], s["mean_winter_summer"],
                     s["mean_swing_share"] * 100, s["peak_to_trough_first_year"],
                     s["peak_to_trough_last_year"], s["years"][0], s["years"][-1]))
