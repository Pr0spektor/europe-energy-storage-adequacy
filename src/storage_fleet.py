"""What the storage fleet can actually do — volume, deliverability, concentration.

Three different limits get confused in the storage debate. This module keeps them apart:

  working volume (TWh)      how much energy the fleet can hold at all
  deliverability (TWh/d)    how fast it can push that energy back into the grid
  duration (days)           working volume / withdrawal capacity — how long a full
                            store lasts at maximum rate, i.e. whether the country
                            owns a marathon asset or a sprint asset

A country can fail on any one of them independently, and the ranking is different
for each. Source: GIE AGSI+ (see src/agsi.py).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agsi

GWH_PER_TWH = 1000.0


def fleet(snap=None):
    """Per country: volume, rates, duration at max withdrawal, and inject/withdraw asymmetry."""
    snap = snap or agsi.snapshot()
    rows = []
    for c in snap["countries"]:
        wgv, wdr, inj = c["workingGasVolume"], c["withdrawalCapacity"], c["injectionCapacity"]
        if not (wgv and wgv == wgv):
            continue
        rows.append({
            "code": c["code"],
            "working_volume_twh": wgv,
            "withdrawal_twh_d": wdr / GWH_PER_TWH,
            "injection_twh_d": inj / GWH_PER_TWH,
            "duration_days": (wgv / (wdr / GWH_PER_TWH)) if wdr else None,
            "refill_days": (wgv / (inj / GWH_PER_TWH)) if inj else None,
            "fill_pct": c["full"],
        })
    return sorted(rows, key=lambda r: -r["working_volume_twh"])


def eu_totals(snap=None):
    snap = snap or agsi.snapshot()
    eu = snap["eu"]
    return {
        "working_volume_twh": eu["workingGasVolume"],
        "withdrawal_twh_d": eu["withdrawalCapacity"] / GWH_PER_TWH,
        "injection_twh_d": eu["injectionCapacity"] / GWH_PER_TWH,
        "duration_days": eu["workingGasVolume"] / (eu["withdrawalCapacity"] / GWH_PER_TWH),
        "refill_days": eu["workingGasVolume"] / (eu["injectionCapacity"] / GWH_PER_TWH),
        "fill_pct": eu["full"],
    }


def deliverability_pressure(snap=None):
    """Winter 2025/26: how close each country came to its own maximum withdrawal rate."""
    snap = snap or agsi.snapshot()
    return sorted(snap["winter_2025_26"], key=lambda r: -r["peak_utilisation_pct"])


def gas_year_table(snap=None):
    return (snap or agsi.snapshot())["gas_years_eu"]


def concentration(top_n=5):
    """How much of Germany's storage sits in the largest few sites (HHI-style check)."""
    fac = agsi.facilities_de()["facilities"]
    total = agsi.snapshot()
    de = [c for c in total["countries"] if c["code"] == "DE"][0]["workingGasVolume"]
    top = sorted(fac, key=lambda f: -f["working_gas_volume"])[:top_n]
    return {"country_working_volume_twh": de,
            "top_n": top_n,
            "top_n_twh": sum(f["working_gas_volume"] for f in top),
            "top_n_share": sum(f["working_gas_volume"] for f in top) / de,
            "sites": [(f["facility"], f["working_gas_volume"], f["full"]) for f in top]}


if __name__ == "__main__":
    e = eu_totals()
    print("EU-27: %.0f TWh working volume, %.1f TWh/d withdrawal, %.1f TWh/d injection"
          % (e["working_volume_twh"], e["withdrawal_twh_d"], e["injection_twh_d"]))
    print("       %.0f days to empty at max rate, %.0f days to refill\n"
          % (e["duration_days"], e["refill_days"]))
    for r in fleet()[:10]:
        print("%-3s %7.1f TWh  %5.2f TWh/d out  %5.0f days duration  %4.0f%% full"
              % (r["code"], r["working_volume_twh"], r["withdrawal_twh_d"],
                 r["duration_days"], r["fill_pct"]))
    print("\nclosest to their withdrawal limit last winter:")
    for r in deliverability_pressure()[:6]:
        print("  %-3s %3d%% of max rate on the peak day (min fill %d%%)"
              % (r["code"], r["peak_utilisation_pct"], r["min_fill"]))
    c = concentration()
    print("\nGermany: top %d sites hold %.0f of %.0f TWh (%.0f%%)"
          % (c["top_n"], c["top_n_twh"], c["country_working_volume_twh"], c["top_n_share"] * 100))
