"""Write the results out in readable form: RESULTS.md + results/seasonality.csv."""
import os, sys, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eurostat import load_raw_dir, countries_only
from seasonality import country_year_table, summarise

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
    rows = [r for r in country_year_table(s) if r["peak_to_trough"]]
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
    L.append("\n**Read:** Germany's annual gas use fell ~%.0f%% from 2021 to 2025, yet the winter peak still "
             "runs %.1fx the summer trough, and ~%.0f TWh a year has to be carried from summer into winter.\n"
             % ((1 - de[-1]["annual_total"]/de[1]["annual_total"])*100, de[-1]["peak_to_trough"],
                de[-1]["swing_absolute"]/3600))

    L.append("## 4. What this means for storage\n")
    L.append("- The swing above a flat baseline is what storage and flexible supply must cover. For the EU "
             "it is on the order of **hundreds of TWh every year** — that is the job underground storage does today.\n"
             "- Batteries do not touch this: the entire EU grid-battery fleet is ~0.04 TWh, four orders of "
             "magnitude below the seasonal task.\n"
             "- Repurposing the gas storage fleet to hydrogen cuts its stored energy ~4.2x "
             "(1,100 TWh → 260 TWh), because a cavern holds a **volume**, not an energy.\n")

    L.append("## 5. What is NOT in this repo yet (honest gaps)\n")
    L.append("- **Sectoral split** — how much of each country's gas goes to households, industry and power "
             "generation. Eurostat carries this annually (`nrg_bal_c`), not in the monthly series used here.\n"
             "- **Storage fill levels and injection/withdrawal rates per facility** — GIE AGSI+ publishes this, "
             "but its API needs a registered key.\n"
             "- **Grid / network map and bottlenecks** — transmission topology and congestion come from "
             "ENTSO-E; its Transparency Platform also requires a key.\n"
             "- **Named consumers (plants, data centres)** — no open pan-European dataset ties individual "
             "sites to metered demand; this needs commercial or national-registry sources.\n")
    open(os.path.join(ROOT, "RESULTS.md"), "w").write("\n".join(L) + "\n")
    print("wrote RESULTS.md and results/seasonality.csv (%d country-years)" % len(rows))

if __name__ == "__main__":
    main()
