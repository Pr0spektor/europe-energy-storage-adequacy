"""What actually refills the swing: storage injection / withdrawal, and who has none.

Source: Eurostat `nrg_cb_gasm`, balance item STK_CHG_MG (stock changes as defined in
MOS GAS), natural gas, TJ GCV, monthly, 2025. Raw response cached verbatim in
data/raw/gas_stock_change_2025.json.

Sign convention in the source: positive = net injection into storage,
negative = net withdrawal. Summer injection and winter withdrawal are therefore
directly observable, and their ratio to the demand swing shows how much of the
seasonal job storage does versus flexible imports/LNG.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seasonality import country_year_table
from eurostat import load_raw_dir, countries_only

_RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "raw", "stock_change_2025.json")
TJ_PER_TWH = 3600.0
AGGREGATES = ("EU27_2020", "EA21", "EA19", "EA20")


def load(path=_RAW):
    with open(path) as f:
        return json.load(f)


def parse(doc=None):
    """{country: [12 monthly stock changes, TJ]} — same stride decoding as eurostat.py."""
    doc = doc or load()
    gidx = doc["dimension"]["geo"]["category"]["index"]
    tidx = doc["dimension"]["time"]["category"]["index"]
    nt = len(tidx)
    inv_g = {v: k for k, v in gidx.items()}
    out = {}
    for flat, val in doc["value"].items():
        f = int(flat)
        g, t = divmod(f, nt)
        c = inv_g.get(g)
        if c is None:
            continue
        out.setdefault(c, [None] * 12)[t] = val
    return out


def cycle(country_series):
    """Injection / withdrawal / peak rate for one country's 12 monthly stock changes."""
    v = [x for x in country_series if x is not None]
    inj = sum(x for x in v if x > 0) / TJ_PER_TWH
    wd = -sum(x for x in v if x < 0) / TJ_PER_TWH
    peak_wd_month = -min(v) / TJ_PER_TWH if v and min(v) < 0 else 0.0
    # a 31-day month; converts a monthly volume into an average daily rate in GW
    peak_gw = peak_wd_month * 1000 / (31 * 24) if peak_wd_month else 0.0
    return {"injection_twh": inj, "withdrawal_twh": wd,
            "peak_month_withdrawal_twh": peak_wd_month, "peak_withdrawal_gw": peak_gw,
            "has_storage": (inj + wd) > 1.0}


def table(year="2025"):
    """Per country: seasonal swing vs what storage actually delivered."""
    stock = parse()
    swings = {r["country"]: r for r in country_year_table(countries_only(load_raw_dir()))
              if r["year"] == year and r["swing_absolute"]}
    rows = []
    for c, series in stock.items():
        if c in AGGREGATES or c not in swings:
            continue
        cy = cycle(series)
        swing = swings[c]["swing_absolute"] / TJ_PER_TWH
        cy.update(country=c, swing_twh=swing,
                  storage_cover=(cy["withdrawal_twh"] / swing) if swing else None,
                  annual_twh=swings[c]["annual_total"] / TJ_PER_TWH)
        rows.append(cy)
    return sorted(rows, key=lambda r: -r["swing_twh"])


def no_storage(min_annual_twh=1.0):
    """Countries that consume gas but hold none of it underground.

    Their entire winter swing has to arrive in real time through pipelines or LNG —
    that is where the physical bottleneck sits.
    """
    # most recent year in which the country actually reported gas use
    consumption = {}
    for r in sorted(country_year_table(countries_only(load_raw_dir())),
                    key=lambda r: r["year"]):
        if r["annual_total"]:
            consumption[r["country"]] = r["annual_total"] / TJ_PER_TWH
    out = []
    for c, series in parse().items():
        if c in AGGREGATES:
            continue
        cy = cycle(series)
        use = consumption.get(c, 0.0)
        if not cy["has_storage"] and use >= min_annual_twh:
            cy["country"] = c
            cy["annual_twh"] = use
            out.append(cy)
    return sorted(out, key=lambda r: -r["annual_twh"])


def eu_cycle():
    return cycle(parse()["EU27_2020"])


if __name__ == "__main__":
    e = eu_cycle()
    print("EU-27 2025: injected %.0f TWh, withdrew %.0f TWh, peak month %.0f TWh (%.0f GW avg)"
          % (e["injection_twh"], e["withdrawal_twh"], e["peak_month_withdrawal_twh"],
             e["peak_withdrawal_gw"]))
    for r in table()[:12]:
        print("%-3s swing %6.1f TWh | storage withdrew %6.1f TWh (%s) | peak %5.1f GW"
              % (r["country"], r["swing_twh"], r["withdrawal_twh"],
                 ("%.0f%% cover" % (r["storage_cover"]*100)) if r["storage_cover"] else "n/a",
                 r["peak_withdrawal_gw"]))
    ns = no_storage()
    print("no domestic storage (%d): %s" % (
        len(ns), ", ".join("%s %.0f TWh/y" % (r["country"], r["annual_twh"]) for r in ns)))
