"""Where the gas network binds — utilisation of Germany's border points.

Utilisation = physical flow / firm technical capacity on the same gas day.

Reading the number honestly:
  < 100%  spare firm capacity at that point
  ~100%   the point is at its firm limit — nothing left to lean on in a cold snap
  > 100%  the point is only carrying that volume because interruptible or
          additional (non-firm) capacity is being used. That extra volume is
          contractually curtailable, so a corridor above 100% is a *risk*
          concentration, not a comfort.
  firm = 0 with flow > 0: the TSO publishes no firm technical capacity for that
          direction at all — the whole flow is non-firm.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entsog

GWH = 1e6          # kWh -> GWh


def points(snap=None):
    return (snap or entsog.snapshot())["points"]


def utilisation(p):
    """None when the operator publishes no firm capacity for that direction."""
    f = p.get("firm_technical") or 0.0
    return (p["physical_flow"] / f) if f > 0 else None


def classify(p):
    u = utilisation(p)
    if u is None:
        return "no firm capacity published" if p["physical_flow"] > 0 else "idle"
    if p["physical_flow"] == 0:
        return "idle"
    if u > 1.0:
        return "above firm — running on non-firm capacity"
    if u > 0.85:
        return "at the firm limit"
    return "spare firm capacity"


def table(snap=None):
    rows = []
    for p in points(snap):
        rows.append({
            "point": p["label"], "operator": p["operator"],
            "corridor": "%s->%s" % (p["from"], p["to"]),
            "flow_gwh_d": p["physical_flow"] / GWH,
            "firm_gwh_d": p["firm_technical"] / GWH,
            "utilisation": utilisation(p),
            "status": classify(p),
        })
    return sorted(rows, key=lambda r: -r["flow_gwh_d"])


def corridors(snap=None):
    """Flow aggregated per country pair, GWh/d."""
    agg = {}
    for p in points(snap):
        k = "%s->%s" % (p["from"], p["to"])
        agg[k] = agg.get(k, 0.0) + p["physical_flow"] / GWH
    return dict(sorted(agg.items(), key=lambda kv: -kv[1]))


def stressed(snap=None):
    """Points carrying gas beyond, or without, firm capacity."""
    return [r for r in table(snap)
            if r["flow_gwh_d"] > 0 and (r["utilisation"] is None or r["utilisation"] > 1.0)]


if __name__ == "__main__":
    for r in table():
        u = "%6.0f%%" % (r["utilisation"] * 100) if r["utilisation"] else "     -"
        print("%-22s %-8s %8.1f / %8.1f GWh/d  %s  %s"
              % (r["point"], r["corridor"], r["flow_gwh_d"], r["firm_gwh_d"], u, r["status"]))
    print("\ncorridors:", {k: round(v) for k, v in corridors().items()})
    print("stressed :", [r["point"] for r in stressed()])
