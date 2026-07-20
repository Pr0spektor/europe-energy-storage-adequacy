"""Cold-snap stress test — how many days before a country's flexibility binds, and on what.

This is the applied end of the repo. Every other module measures something; this one
answers the question an operator, a regulator or a trader actually asks:

    "If it turns cold and stays cold, how many days do we have, and what runs out first —
     the gas, or the ability to move it?"

Method (deliberately simple, fully auditable):

  1. Start of a cold spell. Storage stock = the country's own peak fill last winter
     applied to its working volume (AGSI+), so the test starts from a realistic,
     not a hypothetical, inventory.
  2. Daily flexibility requirement = what the country actually needed on its own peak
     day (storage withdrawal + LNG send-out, both observed), scaled by a severity
     factor: 1.0 = repeat of last winter's worst day, 1.2 and 1.4 = colder.
  3. Each day, LNG send-out supplies up to its observed peak rate; storage covers the
     remainder, capped by the country's published withdrawal capacity, and capped
     again by what is physically left in the ground.
  4. Two ways to fail:
        RATE   — day one. Withdrawal capacity plus send-out cannot meet the daily call
                 at all. More gas underground would not help; the constraint is GW.
        VOLUME — day n. The rates are sufficient but the inventory runs out.

The point of separating them is that they have opposite remedies. A rate-bound system
needs compressors, wells and interconnection; a volume-bound system needs more cavern.
A single "% full" target cannot distinguish the two, which is why it is the wrong
instrument for both.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agsi, lng

SEVERITIES = (1.0, 1.2, 1.4)
MAX_DAYS = 200


def _inputs():
    """Per country: inventory at the start of a cold spell, rates, and the daily call."""
    snap = agsi.snapshot()
    wgv = {c["code"]: c["workingGasVolume"] for c in snap["countries"]}
    wcap = {c["code"]: c["withdrawalCapacity"] / 1000.0 for c in snap["countries"]}  # TWh/d
    lngpeak = {r["code"]: r["peak_send_out_twh_d"] for r in lng.winter()}
    out = {}
    for w in snap["winter_2025_26"]:
        c = w["code"]
        if c not in wgv:
            continue
        out[c] = {
            "working_volume_twh": wgv[c],
            "start_stock_twh": wgv[c] * w["max_fill"] / 100.0,
            "start_fill_pct": w["max_fill"],
            "withdrawal_capacity_twh_d": wcap[c],
            "lng_capacity_twh_d": lngpeak.get(c, 0.0),
            "observed_peak_call_twh_d": w["peak_withdrawal_twh_d"] + lngpeak.get(c, 0.0),
        }
    return out


def simulate(country, severity=1.0, inputs=None):
    """Run one country through a sustained cold spell. Returns the binding outcome."""
    d = (inputs or _inputs()).get(country)
    if not d:
        return None
    call = d["observed_peak_call_twh_d"] * severity
    lng_rate = min(d["lng_capacity_twh_d"], call)
    from_storage = call - lng_rate
    if from_storage > d["withdrawal_capacity_twh_d"] + 1e-12:
        return {"country": country, "severity": severity, "binds_on_day": 1,
                "constraint": "rate", "daily_call_twh_d": call,
                "shortfall_twh_d": from_storage - d["withdrawal_capacity_twh_d"],
                "start_fill_pct": d["start_fill_pct"]}
    if from_storage <= 1e-12:
        return {"country": country, "severity": severity, "binds_on_day": None,
                "constraint": "none — LNG alone covers it", "daily_call_twh_d": call,
                "shortfall_twh_d": 0.0, "start_fill_pct": d["start_fill_pct"]}
    stock = d["start_stock_twh"]
    for day in range(1, MAX_DAYS + 1):
        stock -= from_storage
        if stock <= 0:
            return {"country": country, "severity": severity, "binds_on_day": day,
                    "constraint": "volume", "daily_call_twh_d": call,
                    "shortfall_twh_d": 0.0, "start_fill_pct": d["start_fill_pct"]}
    return {"country": country, "severity": severity, "binds_on_day": None,
            "constraint": "none within %d days" % MAX_DAYS, "daily_call_twh_d": call,
            "shortfall_twh_d": 0.0, "start_fill_pct": d["start_fill_pct"]}


def table(severity=1.0):
    inp = _inputs()
    rows = [simulate(c, severity, inp) for c in inp]
    rows = [r for r in rows if r]
    return sorted(rows, key=lambda r: (r["binds_on_day"] is None, r["binds_on_day"] or 0))


def matrix():
    """{country: {severity: days}} across the severity ladder."""
    inp = _inputs()
    return {c: {s: simulate(c, s, inp)["binds_on_day"] for s in SEVERITIES} for c in inp}


def fragile(severity=1.2, threshold_days=30):
    """Countries that bind on rate, or run out of gas inside a month."""
    return [r for r in table(severity)
            if r["constraint"] == "rate" or (r["binds_on_day"] or 999) <= threshold_days]


if __name__ == "__main__":
    for s in SEVERITIES:
        print("\n=== severity %.1fx last winter's worst day ===" % s)
        for r in table(s):
            days = "day %d" % r["binds_on_day"] if r["binds_on_day"] else "holds"
            extra = (" (short %.2f TWh/d of rate)" % r["shortfall_twh_d"]) if r["constraint"] == "rate" else ""
            print("  %-3s starts %3.0f%% full, needs %.2f TWh/d -> %-8s %s%s"
                  % (r["country"], r["start_fill_pct"], r["daily_call_twh_d"], days,
                     r["constraint"], extra))
