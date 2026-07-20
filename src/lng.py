"""LNG regasification capacity and winter send-out, the other half of the seasonal swing.

LNG terminals deliver natural gas in real time from imported liquefied cargo;
unlike storage, what they send out cannot be stockpiled. This matters for countries
(Belgium, Türkiye) whose underground storage holds little of their seasonal swing.
Storage covers the seasonal swing up to its winter withdrawal rate; LNG terminals cover
the part that arrives just-in-time from ships. Their sum shows the total flex infrastructure.

Source: GIE ALSI API (free, same account as AGSI+). See data/raw/alsi_2026-07-18.json.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import balance

_RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "raw", "alsi_2026-07-18.json")


def load(path=_RAW):
    """Load and parse the ALSI snapshot."""
    with open(path) as f:
        return json.load(f)


def terminals(country=None):
    """List of LNG terminals, optionally filtered by country code, sorted by send-out descending."""
    doc = load()
    rows = doc.get("terminals", [])
    if country:
        rows = [r for r in rows if r.get("code") == country]
    return sorted(rows, key=lambda r: -(r.get("send_out_gwh_d") or 0))


def by_country():
    """Aggregate LNG send-out by country, excluding nulls, sorted by send-out descending."""
    doc = load()
    rows = doc.get("terminals_by_country", [])
    # Filter out rows where send_out_gwh_d is None or NaN
    rows = [r for r in rows if r.get("send_out_gwh_d") is not None and
            r.get("send_out_gwh_d") == r.get("send_out_gwh_d")]  # NaN != NaN
    return sorted(rows, key=lambda r: -(r.get("send_out_gwh_d") or 0))


def winter():
    """Winter 2025/26 LNG send-out by country, sorted by peak send-out descending."""
    doc = load()
    rows = doc.get("winter_2025_26", [])
    return sorted(rows, key=lambda r: -(r.get("peak_send_out_twh_d") or 0))


def peak_flexibility(country):
    """Where a country's *peak-day* flexibility physically comes from.

    On the coldest day the extra gas has to arrive from somewhere at a rate, not
    as an annual volume. Two sources can supply it:

        storage withdrawal   AGSI+ peak day, TWh/d   — stockpiled last summer
        LNG send-out         ALSI  peak day, TWh/d   — arriving by ship, in real time

    The split matters for risk, not just accounting. Storage is pre-positioned and
    physically inside the country; regasification depends on a cargo being at the
    jetty, so it is exposed to the global LNG market on exactly the days when every
    other importer wants the same cargo.

    Comparing the *winter totals* of the two would be meaningless — LNG send-out
    runs all winter and carries baseload as well as the swing. Only the peak day
    puts them on the same footing.

    Returns {storage_twh_d, lng_twh_d, lng_share} or None if either side is missing.
    """
    import agsi
    st = {r["code"]: r for r in agsi.snapshot()["winter_2025_26"]}
    lng = {r["code"]: r for r in winter()}
    if country not in st or country not in lng:
        return None
    s_ = st[country]["peak_withdrawal_twh_d"]
    l_ = lng[country]["peak_send_out_twh_d"]
    tot = s_ + l_
    return {"storage_twh_d": s_, "lng_twh_d": l_,
            "lng_share": (l_ / tot) if tot else None, "total_twh_d": tot}


def flexibility_table():
    """Peak-day flexibility split for every country that has both sources."""
    import agsi
    codes = {r["code"] for r in agsi.snapshot()["winter_2025_26"]} & {r["code"] for r in winter()}
    rows = []
    for c in sorted(codes):
        f = peak_flexibility(c)
        if f:
            f["code"] = c
            rows.append(f)
    return sorted(rows, key=lambda r: -r["lng_share"])


if __name__ == "__main__":
    d = load()
    print("gas day %s — EU LNG send-out %.0f GWh/d across %d terminals\n"
          % (d["_gas_day"], d["eu_send_out_gwh_d"], len(d["terminals"])))
    print("peak-day flexibility, winter 2025/26 (TWh/d)")
    for r in flexibility_table():
        print("  %-3s storage %5.2f  LNG %5.2f  ->  %3.0f%% of the peak came from ships"
              % (r["code"], r["storage_twh_d"], r["lng_twh_d"], r["lng_share"] * 100))
