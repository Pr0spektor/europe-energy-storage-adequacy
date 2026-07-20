"""Who actually burns the gas — sectoral split of natural-gas demand.

Source: Eurostat `nrg_bal_c` (complete energy balances), natural gas G3000, GWh, 2024.
Raw response cached verbatim in data/raw/gas_sectors_2024.json.

The seasonal swing measured in seasonality.py has to come from somewhere. This module
attributes annual volume to the four sectors that can produce it, and flags how
weather-driven each one is:

  households / commercial  -> space heating, almost entirely temperature-driven
  power & heat generation  -> partly heating (district heat), partly power-market driven
  industry                 -> process heat and feedstock, largely flat through the year
"""
import json, os

_RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "raw", "sectors_2024.json")

SECTORS = {
    "TI_EHG_E":    "Power & heat generation",
    "FC_IND_E":    "Industry",
    "FC_OTH_HH_E": "Households",
    "FC_OTH_CP_E": "Commercial & public services",
}

# How much of each sector's annual volume moves with outdoor temperature.
# Households/commercial gas in Europe is overwhelmingly space heating; industry
# process heat is close to flat; power & heat sits in between (district heating +
# winter dispatch). Used only to attribute the swing, never to compute totals.
WEATHER_SENSITIVITY = {
    "FC_OTH_HH_E": 0.85,
    "FC_OTH_CP_E": 0.80,
    "TI_EHG_E":    0.35,
    "FC_IND_E":    0.10,
}

# Germany, electricity (not gas) — for scale comparison only.
# Borderstep Institute / Bitkom: German data centres used ~20 TWh of electricity in 2024,
# projected 25-37 TWh by 2030 depending on efficiency and AI growth.
DE_DATACENTRE_ELECTRICITY_TWH_2024 = 20.0
DE_DATACENTRE_ELECTRICITY_TWH_2030 = (25.0, 37.0)


def load():
    with open(_RAW) as f:
        return json.load(f)


def by_sector(country="DE"):
    """{sector label: GWh} for one country, 2024."""
    raw = load()
    idx = raw["_geo_index"].get(country)
    if idx is None:
        raise KeyError(country)
    out = {}
    for code, label in SECTORS.items():
        v = raw[code].get(str(idx))
        if v is not None:
            out[label] = v
    return out


def shares(country="DE"):
    """{sector label: share of the four-sector total}."""
    s = by_sector(country)
    tot = sum(s.values())
    return {k: (v / tot if tot else 0.0) for k, v in s.items()} if tot else {}


def weather_exposed_share(country="DE"):
    """Fraction of the country's gas that moves with the weather."""
    raw = load()
    idx = str(raw["_geo_index"][country])
    num = den = 0.0
    for code in SECTORS:
        v = raw[code].get(idx)
        if v:
            num += v * WEATHER_SENSITIVITY[code]
            den += v
    return num / den if den else 0.0


def ranking(sector_code, top=10, exclude_aggregates=True):
    """Largest consumers of gas in one sector, GWh 2024."""
    raw = load()
    inv = {str(v): k for k, v in raw["_geo_index"].items()}
    rows = [(inv[i], v) for i, v in raw[sector_code].items() if i in inv and v]
    if exclude_aggregates:
        rows = [r for r in rows if r[0] not in ("EU27_2020", "EA21", "EA19", "EA20")]
    return sorted(rows, key=lambda r: -r[1])[:top]


def de_industry_branches():
    """{branch: GWh} for Germany, 2024 — which factories carry the industrial load."""
    return dict(load()["_DE_industry_branches_GWh_2024"])
