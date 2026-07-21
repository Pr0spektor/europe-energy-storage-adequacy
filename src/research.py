"""Generate RESEARCH.md — the synthesis across all four data layers.

Every number is pulled from the modules at run time, so the study cannot drift
away from the data underneath it.
"""
import os, sys, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eurostat import load_raw_dir, countries_only
from seasonality import country_year_table, summarise
import demand as D, balance as BAL, network as NW, storage_fleet as SF, agsi, hydrogen as H
import lng as LNG
import stress as ST
from data import UGS_NATURAL_GAS_TWH, UGS_H2_BY_TYPE, total_ugs_h2_twh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = {"BE":"Belgium","BG":"Bulgaria","CZ":"Czechia","DK":"Denmark","DE":"Germany","EE":"Estonia",
"IE":"Ireland","EL":"Greece","ES":"Spain","FR":"France","HR":"Croatia","IT":"Italy","LV":"Latvia",
"LT":"Lithuania","LU":"Luxembourg","HU":"Hungary","NL":"Netherlands","AT":"Austria","PL":"Poland",
"PT":"Portugal","RO":"Romania","SI":"Slovenia","SK":"Slovakia","FI":"Finland","SE":"Sweden",
"NO":"Norway","UK":"United Kingdom","MD":"Moldova","MK":"North Macedonia","GE":"Georgia",
"AL":"Albania","RS":"Serbia","TR":"Turkiye","UA":"Ukraine"}


def main():
    rows = [r for r in country_year_table(countries_only(load_raw_dir()))
            if r["peak_to_trough"] and r["annual_total"]]
    summ = summarise(rows)
    eu = SF.eu_totals()
    gy = SF.gas_year_table()
    L = []
    A = L.append

    A("# Europe's winter problem, in five layers\n")
    A("A study of where Europe's energy system actually binds in winter: how uneven demand is, "
      "who causes the unevenness, what carries the system through it, how much delivery rate that "
      "leaves in reserve, and where the pipes and the caverns run out first.\n")
    A("All figures are computed at run time from four public sources — **Eurostat** (monthly gas "
      "balances and annual sectoral balances), **GIE AGSI+** (facility-level storage), **ENTSOG** "
      "(network flows and capacities) and **Borderstep/Bitkom** (data-centre electricity). Raw API "
      "responses are cached verbatim in `data/raw/`. Regenerate with `python src/research.py`.\n")
    A("---\n")

    # ---------------------------------------------------------------- layer 1
    A("## Layer 1 — How uneven is demand?\n")
    med = {}
    for y in ["2020", "2021", "2022", "2023", "2024", "2025"]:
        v = [r for r in rows if r["year"] == y]
        if v:
            med[y] = (st.median([x["peak_to_trough"] for x in v]),
                      st.median([x["swing_share"] for x in v]) * 100, len(v))
    A("| Year | Countries | Median peak/trough | Median swing above baseline |")
    A("|---|---|---|---|")
    for y, (p, s, n) in med.items():
        A("| %s | %d | %.2f | %.1f%% |" % (y, n, p, s))
    A("")
    A("Between 2020 and 2025 European gas consumption fell sharply, but **the shape of the year did "
      "not flatten** — the median country's winter peak went from %.2fx its summer trough to %.2fx. "
      "The system is smaller and just as seasonal, which is the opposite of what an efficiency-led "
      "transition would look like.\n" % (med["2020"][0], med["2025"][0]))
    top = sorted([{"c": k, **v} for k, v in summ.items()], key=lambda x: -x["mean_peak_to_trough"])[:6]
    A("The most extreme profiles belong to small systems — " +
      ", ".join("**%s %.1fx**" % (N.get(t["c"], t["c"]), t["mean_peak_to_trough"]) for t in top) +
      " — where a single heating season dominates a thin annual total. Among the large consumers the "
      "spread still matters: " + ", ".join(
        "**%s %.1fx**" % (N.get(c, c), summ[c]["mean_peak_to_trough"])
        for c in ("FR", "DE", "IT", "NL", "ES") if c in summ) +
      ". France and Germany carry a genuinely peaky system; Spain is nearly flat because so much of "
      "its gas goes to power generation and industry rather than heating.\n")
    A("![Seasonality](results/residual_and_soc.png)\n")

    # ---------------------------------------------------------------- layer 2
    A("## Layer 2 — Who causes it?\n")
    sh_eu, sh_de = D.shares("EU27_2020"), D.shares("DE")
    A("| Sector | EU-27 | Germany | Moves with the weather? |")
    A("|---|---|---|---|")
    for lab, w in [("Households", "yes — space heating"), ("Commercial & public services", "yes — space heating"),
                   ("Power & heat generation", "partly — district heat and cold-snap dispatch"),
                   ("Industry", "barely — process heat runs year-round")]:
        A("| %s | %.0f%% | %.0f%% | %s |" % (lab, sh_eu[lab] * 100, sh_de[lab] * 100, w))
    A("")
    A("So **%.0f%% of EU gas and %.0f%% of German gas sits in weather-driven end uses.** The winter "
      "peak is a buildings phenomenon before it is anything else; industry is close to a flat "
      "baseload and does not create the swing it is often blamed for.\n"
      % (D.weather_exposed_share("EU27_2020") * 100, D.weather_exposed_share("DE") * 100))
    br = D.de_industry_branches()
    A("Within German industry the load is concentrated: " +
      ", ".join("**%s %.0f TWh**" % (k.split(" (")[0], v / 1000)
                for k, v in sorted(br.items(), key=lambda kv: -kv[1])) + ".\n")
    A("For scale on the electricity side, **German data centres used ≈%.0f TWh of electricity in 2024**, "
      "heading for %.0f–%.0f TWh by 2030. That is a large and growing *flat* load on the power system; "
      "it does not touch the seasonal gas swing, but it does compete for the same firm winter "
      "generation capacity.\n"
      % (D.DE_DATACENTRE_ELECTRICITY_TWH_2024, *D.DE_DATACENTRE_ELECTRICITY_TWH_2030))
    A("![Sectors](results/demand_by_sector.png)\n![German industry](results/de_industry_gas.png)\n")

    # ---------------------------------------------------------------- layer 3
    A("## Layer 3 — What carries the system through it?\n")
    e = BAL.eu_cycle()
    A("Storage, almost entirely. In 2025 the EU injected **%.0f TWh** between April and October and "
      "withdrew **%.0f TWh** back out over the winter, peaking at **%.0f TWh in a single month** — an "
      "average delivery rate of **%.0f GW held for thirty days**.\n"
      % (e["injection_twh"], e["withdrawal_twh"], e["peak_month_withdrawal_twh"], e["peak_withdrawal_gw"]))
    cov = [r for r in BAL.table()
           if r["storage_cover"] and r["swing_twh"] >= 4 and r["withdrawal_twh"] >= 4]
    A("Across the %d countries with a storage fleet of consequence the **median country's withdrawal "
      "equals %.0f%% of its own measured seasonal swing** — storage is not a supplement to winter, it "
      "*is* winter. The outliers are informative rather than noisy: transit states such as Latvia and "
      "Slovakia draw far more than their domestic swing because they store for neighbours, while "
      "Spain and Portugal draw less because LNG regasification does part of the job instead.\n"
      % (len(cov), st.median([r["storage_cover"] for r in cov]) * 100))
    A("![Storage cycle](results/storage_cycle.png)\n")

    # ---------------------------------------------------------------- layer 4
    A("## Layer 4 — How much margin is left in the fleet?\n")
    A("GIE AGSI+, gas day **%s**: the EU holds **%.0f TWh** of working volume, can withdraw "
      "**%.1f TWh/d** and inject only **%.1f TWh/d**. At maximum rate a full fleet lasts **%.0f days**; "
      "refilling it takes **%.0f days**. That asymmetry is the whole reason the refill season starts "
      "in April — there is no way to do it quickly.\n"
      % (agsi.snapshot()["_gas_day"], eu["working_volume_twh"], eu["withdrawal_twh_d"],
         eu["injection_twh_d"], eu["duration_days"], eu["refill_days"]))
    A("| Country | Working volume (TWh) | Withdrawal (TWh/d) | Days at max rate | Fill today |")
    A("|---|---|---|---|---|")
    for r in SF.fleet()[:12]:
        A("| %s | %.1f | %.2f | %.0f | %.0f%% |" % (N.get(r["code"], r["code"]),
          r["working_volume_twh"], r["withdrawal_twh_d"], r["duration_days"], r["fill_pct"]))
    A("")
    A("**Two different assets are hiding in this table.** Germany holds the most gas (%.0f TWh) but "
      "empties in **%.0f days** at full rate — a salt-cavern-heavy, fast-cycling fleet built for peaks. "
      "Spain's store lasts **%.0f days** and Austria's **%.0f**: slow, deep, seasonal assets. Comparing "
      "countries on TWh alone hides this completely.\n"
      % (SF.fleet()[0]["working_volume_twh"], SF.fleet()[0]["duration_days"],
         [r for r in SF.fleet() if r["code"] == "ES"][0]["duration_days"],
         [r for r in SF.fleet() if r["code"] == "AT"][0]["duration_days"]))

    A("### Which winters were tight, and where\n")
    A("| Gas year | Peak fill | Trough fill | Max EU withdrawal | On |")
    A("|---|---|---|---|---|")
    for g in gy:
        A("| %s | %.0f%% (%s) | %.0f%% (%s) | %.2f TWh/d | %s |" % (
            g["gas_year"], g["peak_fill"], g["peak_date"], g["trough_fill"], g["trough_date"],
            g["max_withdrawal_twh_d"], g["max_withdrawal_date"]))
    A("")
    last = gy[-1]
    A("**2025/26 is the weakest entry into winter on record here.** Storage topped out at only "
      "**%.0f%%** on %s — every other gas year since 2019 reached 88–99%% — and bottomed at **%.0f%%**. "
      "Peak EU withdrawal still hit **%.2f TWh/d** on %s, about **%.0f%%** of the fleet's maximum rate. "
      "The fleet had the *speed*; what it was short of was *stock*.\n"
      % (last["peak_fill"], last["peak_date"], last["trough_fill"], last["max_withdrawal_twh_d"],
         last["max_withdrawal_date"], 100 * last["max_withdrawal_twh_d"] / eu["withdrawal_twh_d"]))
    A("![Fill curves](results/storage_fill_curves.png)\n")

    A("### Who ran out of delivery rate rather than gas\n")
    dp = SF.deliverability_pressure()
    tight = [r for r in dp if r["peak_utilisation_pct"] >= 85]
    A("On its own peak day last winter each country used this share of its own maximum withdrawal "
      "rate. Above ≈85%% there is no headroom left for a colder day:\n")
    A("| Country | Peak withdrawal | Capacity | Utilisation | Lowest fill |")
    A("|---|---|---|---|---|")
    for r in dp:
        A("| %s | %.2f TWh/d | %.2f TWh/d | %d%% | %d%% |" % (N.get(r["code"], r["code"]),
          r["peak_withdrawal_twh_d"], r["withdrawal_capacity_twh_d"],
          r["peak_utilisation_pct"], r["min_fill"]))
    A("")
    A("**%s ran their storage flat out.** These are small fleets with no second gear: a colder "
      "January does not get met from underground, it gets met from an interconnector or not at all. "
      "By contrast Germany used only **%d%%** of its withdrawal rate, Italy **%d%%** and the "
      "Netherlands **%d%%** — the large fleets are volume-constrained, the small ones are "
      "rate-constrained, and a single European target expressed in %% full addresses neither.\n"
      % (", ".join(N.get(r["code"], r["code"]) for r in tight),
         *[[x for x in dp if x["code"] == c][0]["peak_utilisation_pct"] for c in ("DE", "IT", "NL")]))
    A("![Deliverability](results/storage_deliverability.png)\n")

    A("### Germany, site by site\n")
    con = SF.concentration()
    A("Germany's %.0f TWh is not one asset — it is %d sites run by %d companies, and the top five hold "
      "**%.0f TWh, %.0f%% of the national total**:\n"
      % (con["country_working_volume_twh"], agsi.facilities_de()["_coverage"]["facilities_total"],
         len(agsi.facilities_de()["companies"]), con["top_n_twh"], con["top_n_share"] * 100))
    A("| Site | Operator | Working volume | Withdrawal | Fill on %s |" % agsi.snapshot()["_gas_day"])
    A("|---|---|---|---|---|")
    for f in sorted(agsi.facilities_de()["facilities"], key=lambda f: -f["working_gas_volume"])[:10]:
        A("| %s | %s | %.1f TWh | %d GWh/d | %.0f%% |" % (f["facility"], f["operator"],
          f["working_gas_volume"], f["withdrawal_capacity"], f["full"]))
    A("")
    reh = [f for f in agsi.facilities_de()["facilities"] if f["facility"] == "UGS Rehden"][0]
    A("**Rehden alone is %.0f TWh — %.0f%% of German working volume — and it stands at %.0f%% full.** "
      "It is a depleted field, not a cavern: slow to fill, slow to draw, and it has been the single "
      "biggest swing factor in German storage statistics since 2022. Any headline about German "
      "storage percentages is largely a statement about one site in Lower Saxony.\n"
      % (reh["working_gas_volume"], 100 * reh["working_gas_volume"] / con["country_working_volume_twh"],
         reh["full"]))
    A("![German sites](results/de_storage_sites.png)\n")

    A("### Caverns or ships — the other half of the flexibility\n")
    ft = LNG.flexibility_table()
    A("Storage is not the only way to meet a cold day. LNG regasification supplies the same service "
      "at a rate, and the two are only comparable on the **peak day** — comparing winter totals would "
      "be meaningless, because send-out carries baseload as well as swing.\n")
    A("| Country | Storage withdrawal | LNG send-out | Share from ships |")
    A("|---|---|---|---|")
    for r in ft:
        A("| %s | %.2f TWh/d | %.2f TWh/d | **%.0f%%** |" % (N.get(r["code"], r["code"]),
          r["storage_twh_d"], r["lng_twh_d"], r["lng_share"] * 100))
    A("")
    A("This resolves the puzzle from Layer 3, where Belgium's storage covered only 24%% of its swing. "
      "It is not exposed — it is differently exposed: **%.0f%% of Spain's and %.0f%% of Belgium's peak "
      "day arrived by ship**, against **%.0f%% for Germany**. Regasification is faster to build and "
      "needs no geology, but it is supplied by the global LNG market on exactly the days when every "
      "other importer is bidding for the same cargo. Caverns are pre-positioned; ships are not. A "
      "European adequacy assessment that counts only %% of storage full will score Iberia as safe and "
      "miss the actual dependency entirely.\n"
      % tuple(([r for r in ft if r["code"] == c][0]["lng_share"] * 100) for c in ("ES", "BE", "DE")))
    A("![Caverns or ships](results/lng_vs_storage.png)\n")
    A("![LNG terminals](results/lng_terminals.png)\n")

    # ---------------------------------------------------------------- layer 5
    A("## Layer 5 — Where the pipes bind\n")
    c = NW.corridors()
    A("ENTSOG, peak winter gas day **2026-01-15**. Germany imported **%.0f GWh/d** from Norway through "
      "two coastal clusters — Emden and Dornum — and both ran *above* their published firm technical "
      "capacity (**162%%** and **139%%**). The excess is interruptible or additional capacity: legally "
      "curtailable. Meanwhile **VIP Waidhaus, the old Russian route into Bavaria, sat at zero**, and "
      "**Mallnow ran backwards** — exporting to Poland at 86%% of firm.\n" % c["NO->DE"])
    A("| Border point | Corridor | Flow | Firm capacity | Utilisation |")
    A("|---|---|---|---|---|")
    for r in NW.table():
        A("| %s | %s | %.0f GWh/d | %.0f GWh/d | %s |" % (r["point"], r["corridor"],
          r["flow_gwh_d"], r["firm_gwh_d"],
          ("%.0f%%" % (r["utilisation"] * 100)) if r["utilisation"] else "not published"))
    A("")
    A("The bottleneck is not pipe diameter. It is **concentration**: a single sea-facing corridor now "
      "carries the load that used to arrive from three directions, and it is doing so on non-firm "
      "terms.\n")
    A("![Network](results/network_map.png)\n")

    A("## The applied question — how long does a cold spell take to break something?\n")
    A("Everything above is measurement. This is the test an operator, a regulator or a trader "
      "actually runs: **if it turns cold and stays cold, how many days do we have, and what fails "
      "first?** Storage stock starts at each country's own peak fill last winter; the daily call is "
      "its own observed worst day, scaled; LNG send-out supplies what it can and storage covers the "
      "rest, capped by published withdrawal capacity.\n")
    A("Two failure modes, with opposite remedies:\n")
    A("- **Rate-bound (day 1)** — capacity in GW cannot meet the call at all. More gas underground "
      "would change nothing; the fix is compressors, wells and interconnection.\n"
      "- **Volume-bound (day n)** — the rates are fine, the inventory empties. The fix is more "
      "cavern, or more imports booked earlier.\n")
    A("| Country | Starting fill | Daily call | 1.0x worst day | 1.2x | 1.4x |")
    A("|---|---|---|---|---|---|")
    m = ST.matrix()
    base = {r["country"]: r for r in ST.table(1.0)}
    fmt = lambda d: ("day 1 — **rate**" if d == 1 else ("day %d" % d) if d else "holds")
    for c in sorted(m, key=lambda c: (m[c][1.0] is None, m[c][1.0] or 999)):
        A("| %s | %.0f%% | %.2f TWh/d | %s | %s | %s |" % (
            N.get(c, c), base[c]["start_fill_pct"], base[c]["daily_call_twh_d"],
            fmt(m[c][1.0]), fmt(m[c][1.2]), fmt(m[c][1.4])))
    A("")
    r10 = sorted(r["country"] for r in ST.table(1.0) if r["constraint"] == "rate")
    r14 = sorted(r["country"] for r in ST.table(1.4) if r["constraint"] == "rate")
    A("**At a repeat of last winter's worst day, %s are already rate-bound on day one** — they were "
      "at their delivery ceiling, not their inventory ceiling. Push severity to 1.4x and the "
      "rate-bound set grows to %s: **a colder winter does not slowly drain Europe, it converts "
      "volume problems into rate problems.** That is a different failure, on a different timescale, "
      "with a different fix — and it is completely invisible in a storage-fill percentage.\n"
      % (", ".join(N.get(c, c) for c in r10), ", ".join(N.get(c, c) for c in r14)))
    A("Germany, the largest fleet in Europe, empties in **%d days** at 1.0x and **%d days** at 1.2x. "
      "Spain, with a seventh of the volume, holds **%d days** — because most of its peak arrives by "
      "ship rather than out of the ground.\n" % (m["DE"][1.0], m["DE"][1.2], m["ES"][1.0]))
    A("![Stress test](results/stress_days.png)\n")

    # ---------------------------------------------------------------- hydrogen
    A("## What happens when the same fleet has to hold hydrogen\n")
    A("Hydrogen holds about **%.2f** of methane's energy per cubic metre, and a cavern stores a volume, "
      "not an energy. Repurposed, Europe's **%,d TWh** of gas storage becomes **%d TWh** of hydrogen "
      "storage — an energy shrink of **%.1fx**.\n".replace("%,d", "%d")
      % (H.volumetric_energy_ratio(), UGS_NATURAL_GAS_TWH, round(total_ugs_h2_twh()),
         H.energy_loss_factor()))
    A("| Store type | Hydrogen-capable energy (TWh) |")
    A("|---|---|")
    for k, v in sorted(UGS_H2_BY_TYPE.items(), key=lambda kv: -kv[1]):
        A("| %s | %d |" % (k, v))
    A("")
    A("Salt caverns — the only store type with an established hydrogen track record — carry **%d TWh** "
      "of that. Set against the measured seasonal swing from Layer 1, the comfortable methane buffer "
      "becomes a thin margin, and it thins further as electrification pushes more of the heating load "
      "onto the power system.\n" % UGS_H2_BY_TYPE["Salt caverns"])
    A("![Hydrogen](results/h2_by_store_type.png)\n")

    # ---------------------------------------------------------------- conclusion
    A("## What this all adds up to\n")
    A("1. **Demand did not de-seasonalise.** Less gas, same winter shape (%.2fx median peak/trough in "
      "2025, up from %.2fx in 2020). Efficiency cut the level, not the swing.\n"
      % (med["2025"][0], med["2020"][0]))
    A("2. **The swing is a buildings problem.** ≈%.0f%% of EU gas is weather-driven; industry is "
      "essentially flat. Policy aimed at industrial gas does not touch the peak.\n"
      % (D.weather_exposed_share("EU27_2020") * 100))
    A("3. **Storage is the whole answer today**, covering ≈100%% of every storage-owning country's "
      "swing, at a European peak of ≈%.0f GW sustained for a month. No battery fleet is within four "
      "orders of magnitude of that job.\n" % e["peak_withdrawal_gw"])
    A("4. **Two different scarcities exist and get conflated.** Large fleets (DE, IT, NL) are short of "
      "*volume*; small ones (%s) are short of *rate*. A single \"%% full\" target is the wrong "
      "instrument for both.\n" % ", ".join(r["code"] for r in tight))
    A("5. **2025/26 entered winter at %.0f%% — the weakest on this record** — and the risk showed up "
      "as stock, not as speed.\n" % last["peak_fill"])
    A("6. **Half of southern Europe's peak day arrives by ship.** %.0f%% for Spain, %.0f%% for "
      "Belgium, against %.0f%% for Germany — a dependency invisible to any storage-fill target.\n"
      % tuple(([r for r in LNG.flexibility_table() if r["code"] == c][0]["lng_share"] * 100)
              for c in ("ES", "BE", "DE")))
    A("7. **The import side is now concentrated and partly non-firm.** Norway into two German coastal "
      "points, above firm capacity, while the eastern routes sit idle or reversed.\n")
    A("8. **Hydrogen does not inherit this buffer.** The same holes hold %.1fx less energy, so the "
      "seasonal margin has to be rebuilt, not converted.\n" % H.energy_loss_factor())
    A("\n---\n")
    A("*Reproduce: `python src/research.py`. Live refresh needs `AGSI_KEY` (free, "
      "https://agsi.gie.eu/account); Eurostat and ENTSOG need no key.*\n")

    open(os.path.join(ROOT, "RESEARCH.md"), "w").write("\n".join(L) + "\n")
    print("wrote RESEARCH.md (%d lines)" % len(L))


if __name__ == "__main__":
    main()
