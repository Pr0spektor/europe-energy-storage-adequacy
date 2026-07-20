"""Run the full analysis: charts, summary.json and a model-driven insight memo.

Run:  python src/analysis.py
"""
from __future__ import annotations
import json, os
from data import (ELECTRICITY_DEMAND_TWH, VRE_SHARE_TARGET, UGS_NATURAL_GAS_TWH,
                  UGS_H2_BY_TYPE, GIE_H2_STORAGE_TARGET_TWH, total_ugs_h2_twh)
from hydrogen import volumetric_energy_ratio, energy_loss_factor, capacity_vs_target
from adequacy import residual_load, simulate_store, binding_constraint, days_of_cover
from storage import ladder, seasonal_capable
from seasonality import country_year_table, summarise

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
os.makedirs(RESULTS, exist_ok=True)

GAS_DELIVERABILITY_GW = 700.0     # EU UGS peak withdrawal capability (natural gas)
H2_DELIVERABILITY_GW = 250.0      # repurposed fleet, hydrogen


def scenario(vre_share: float) -> dict:
    sim = simulate_store(residual_load(ELECTRICITY_DEMAND_TWH, vre_share))
    h2 = total_ugs_h2_twh()
    return {"vre_share": vre_share,
            "seasonal_energy_twh": round(sim["required_energy_twh"], 1),
            "peak_withdrawal_gw": round(sim["peak_withdrawal_gw"], 1),
            "h2_fleet_utilisation": round(sim["required_energy_twh"] / h2, 3),
            "balancing_baseload_twh_per_day": round(sim["baseload_twh_per_day"], 2)}


def compute() -> dict:
    res = residual_load(ELECTRICITY_DEMAND_TWH, VRE_SHARE_TARGET)
    sim = simulate_store(res)
    req_e, req_p = sim["required_energy_twh"], sim["peak_withdrawal_gw"]
    peak_daily = max(res)

    gas = binding_constraint(req_e, req_p, UGS_NATURAL_GAS_TWH, GAS_DELIVERABILITY_GW)
    h2 = binding_constraint(req_e, req_p, total_ugs_h2_twh(), H2_DELIVERABILITY_GW)
    grid = [scenario(v) for v in (0.6, 0.7, 0.8, 0.9, 1.0)]
    # first VRE share at which the repurposed fleet no longer covers the swing
    breach = next((g["vre_share"] for g in grid if g["h2_fleet_utilisation"] > 1.0), None)

    return {
        "assumptions": {"electricity_demand_twh": ELECTRICITY_DEMAND_TWH,
                        "vre_share": VRE_SHARE_TARGET},
        "requirement": {"seasonal_energy_twh": round(req_e, 1),
                        "peak_withdrawal_gw": round(req_p, 1),
                        "peak_daily_twh": round(peak_daily, 2),
                        "balancing_baseload_twh_per_day": round(sim["baseload_twh_per_day"], 2)},
        "hydrogen": {"volumetric_energy_ratio": round(volumetric_energy_ratio(), 3),
                     "ch4_fleet_twh": UGS_NATURAL_GAS_TWH,
                     "h2_fleet_twh": total_ugs_h2_twh(),
                     "energy_shrink_factor": round(energy_loss_factor(), 2),
                     "by_store": UGS_H2_BY_TYPE,
                     "vs_gie_target": capacity_vs_target(GIE_H2_STORAGE_TARGET_TWH)},
        "adequacy": {"gas_today": gas, "repurposed_h2": h2,
                     "vre_share_where_h2_fleet_is_exceeded": breach,
                     "days_of_cover_gas": round(days_of_cover(UGS_NATURAL_GAS_TWH, peak_daily), 1),
                     "days_of_cover_h2": round(days_of_cover(total_ugs_h2_twh(), peak_daily), 1)},
        "flexibility_ladder": ladder(),
        "seasonal_capable": seasonal_capable(),
        "scenarios": grid,
        "observed_seasonality": {"by_country_year": country_year_table(),
                                 "summary": summarise(country_year_table())},
    }


def charts(s: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 1) residual load + state of charge
    res = residual_load(ELECTRICITY_DEMAND_TWH, VRE_SHARE_TARGET)
    sim = simulate_store(res)
    base = sim["baseload_twh_per_day"]
    net = [r - base for r in res]
    days = range(len(res))
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.fill_between(days, [max(x, 0) for x in net], color="#C0504D", alpha=.65,
                    label="Deficit beyond baseload (store discharges)")
    ax.fill_between(days, [min(x, 0) for x in net], color="#3B6EA5", alpha=.55,
                    label="Surplus (store refills)")
    ax2 = ax.twinx()
    ax2.plot(days, sim["soc_path"], color="#20344a", lw=1.8)
    ax.set_xlabel("Day of year"); ax.set_ylabel("Net residual (TWh/day)")
    ax2.set_ylabel("Storage state of charge (TWh)")
    ax.set_title("Europe: seasonal cycle the store must carry (%.0f%% wind + solar)"
                 % (VRE_SHARE_TARGET * 100))
    ax.legend(loc="upper right", fontsize=8); ax.axhline(0, color="#666", lw=.8)
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, "residual_and_soc.png"), dpi=120); plt.close(fig)

    # 2) requirement vs available
    req = s["requirement"]["seasonal_energy_twh"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    names = ["Seasonal swing needed", "UGS today (natural gas)", "UGS repurposed to H2"]
    vals = [req, UGS_NATURAL_GAS_TWH, total_ugs_h2_twh()]
    bars = ax.bar(names, vals, color=["#20344a", "#3B6EA5", "#C0504D"])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width()/2, v, f" {v:,.0f}", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("TWh"); ax.set_title("Seasonal storage: needed vs what the fleet holds")
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, "requirement_vs_available.png"), dpi=120); plt.close(fig)

    # 3) hydrogen capacity by store type vs GIE target
    fig, ax = plt.subplots(figsize=(8, 4))
    st = sorted(UGS_H2_BY_TYPE.items(), key=lambda kv: -kv[1])
    ax.barh([k for k, _ in st], [v for _, v in st], color="#3B6EA5")
    ax.axvline(GIE_H2_STORAGE_TARGET_TWH, color="#C0504D", ls="--",
               label=f"GIE need: {GIE_H2_STORAGE_TARGET_TWH:.0f} TWh")
    ax.set_xlabel("Repurposable hydrogen working gas energy (TWh)")
    ax.set_title("Where hydrogen can actually be stored underground")
    ax.legend(fontsize=8); ax.invert_yaxis()
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, "h2_by_store_type.png"), dpi=120); plt.close(fig)

    # 4) flexibility ladder
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    for r in s["flexibility_ladder"]:
        ax.scatter(r["hours_at_rated_power"], r["energy_twh"], s=70, color="#3B6EA5")
        ax.annotate(r["technology"], (r["hours_at_rated_power"], r["energy_twh"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Discharge duration at rated power (hours, log)")
    ax.set_ylabel("Stored energy (TWh, log)")
    ax.set_title("The flexibility ladder: only underground storage spans seasons")
    ax.grid(alpha=.3, which="both")
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, "flexibility_ladder.png"), dpi=120); plt.close(fig)

    # 5) scenario curve: VRE share vs requirement, against the H2 fleet
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    xs = [g["vre_share"] * 100 for g in s["scenarios"]]
    ys = [g["seasonal_energy_twh"] for g in s["scenarios"]]
    ax.plot(xs, ys, "-o", color="#3B6EA5", label="Seasonal storage needed")
    ax.axhline(total_ugs_h2_twh(), color="#C0504D", ls="--",
               label=f"UGS repurposed to H2 ({total_ugs_h2_twh():.0f} TWh)")
    ax.set_xlabel("Wind + solar share of annual demand (%)")
    ax.set_ylabel("Seasonal storage energy (TWh)")
    ax.set_title("The hydrogen fleet runs out as the system decarbonises")
    ax.legend(fontsize=8); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, "scenarios.png"), dpi=120); plt.close(fig)


def write_memo(s: dict):
    req, h2, ad = s["requirement"], s["hydrogen"], s["adequacy"]
    seas = s["observed_seasonality"]["summary"].get("DE", {})
    seas_first = seas.get("peak_to_trough_first_year", 0.0)
    seas_last = seas.get("peak_to_trough_last_year", 0.0)
    seas_y0 = seas.get("years", ["?"])[0]
    seas_y1 = seas.get("years", ["?"])[-1]
    seas_mean_pt = seas.get("mean_peak_to_trough", 0.0)
    seas_mean_ws = seas.get("mean_winter_summer", 0.0)
    seas_swing = seas.get("mean_swing_share", 0.0) * 100
    breach = ad["vre_share_where_h2_fleet_is_exceeded"]
    breach_txt = (f"at about **{breach*100:.0f}% wind and solar** the repurposed fleet no longer "
                  f"covers the swing") if breach else "the repurposed fleet covers every case modelled"
    memo = f"""# Insight memo — Europe's seasonal storage as gas gives way to hydrogen

*Figures are produced directly from the model (`python src/analysis.py`).*

## Situation
With wind and solar at {s['assumptions']['vre_share']*100:.0f}% of annual electricity demand,
Europe must carry a **seasonal swing of {req['seasonal_energy_twh']:,.0f} TWh** and deliver
**{req['peak_withdrawal_gw']:,.0f} GW** at the winter peak, on top of a flat
{req['balancing_baseload_twh_per_day']:.1f} TWh/day of other dispatchable supply. Today's
underground gas storage holds ~{UGS_NATURAL_GAS_TWH:,.0f} TWh — roughly
{UGS_NATURAL_GAS_TWH/req['seasonal_energy_twh']:.0f}x that swing.

## Key findings
1. **A cavern stores a volume, not an energy.** Hydrogen carries only
   ~{h2['volumetric_energy_ratio']:.2f} of methane's energy per cubic metre, so repurposing the
   fleet cuts stored energy ~{h2['energy_shrink_factor']:.1f}x — from {h2['ch4_fleet_twh']:,.0f} TWh
   to **{h2['h2_fleet_twh']:,.0f} TWh**.
2. **Comfort becomes a thin margin.** Against the same seasonal swing, the gas fleet is
   {ad['gas_today']['energy_utilisation']*100:.0f}% utilised; on hydrogen it is
   **{ad['repurposed_h2']['energy_utilisation']*100:.0f}%** — and {breach_txt}.
3. **Volume binds before deliverability.** The hydrogen fleet uses
   {ad['repurposed_h2']['power_utilisation']*100:.0f}% of its withdrawal capability but
   {ad['repurposed_h2']['energy_utilisation']*100:.0f}% of its working energy: the scarce
   resource is subsurface working volume, not injection/withdrawal rate.
4. **Salt caverns meet policy, not the system.** Salt caverns give
   {UGS_H2_BY_TYPE['Salt caverns']:.0f} TWh — enough for the {GIE_H2_STORAGE_TARGET_TWH:.0f} TWh
   Europe currently targets — but a fully decarbonised winter needs the depleted fields
   ({UGS_H2_BY_TYPE['Depleted gas fields']:.0f} TWh), which carry the harder technical questions.
5. **Batteries cannot close a seasonal gap.** On the flexibility ladder only underground storage
   carries more than a month of demand; batteries cover hours and pumped hydro days.
6. **The seasonal swing is real, measured — and it grew.** On Eurostat monthly data,
   German gas consumption ran at a peak-to-trough ratio of {seas_first:.1f} in {seas_y0} and
   {seas_last:.1f} in {seas_y1}, averaging {seas_mean_pt:.1f} (winter/summer {seas_mean_ws:.1f}).
   About **{seas_swing:.0f}% of annual consumption sits above a flat baseline** — that is the
   share the storage system has to carry every single year.

## Recommendation
Treat seasonal adequacy as a **subsurface working-volume problem**. Qualify depleted fields and
aquifers for hydrogen early (cushion gas, purity, microbial activity, deliverability), reserve
salt caverns for fast-cycling duty, and size electrolysis and injection to refill the store over
summer. Track working volume and deliverability as two separate constraints — a store with
enough energy can still fail on peak days.

---
*Illustrative, publicly-anchored inputs (see SOURCES.md); a transparent adequacy model, not a
market simulation. Decision support, not investment advice.*
"""
    with open(os.path.join(ROOT, "INSIGHT_MEMO.md"), "w") as f:
        f.write(memo)


def main():
    s = compute()
    with open(os.path.join(RESULTS, "summary.json"), "w") as f:
        json.dump(s, f, indent=2)
    charts(s)
    write_memo(s)
    print("Analysis complete. Seasonal swing %.0f TWh / %.0f GW | H2 fleet %.0f TWh (%.0f%% utilised) | shrink %.1fx"
          % (s["requirement"]["seasonal_energy_twh"], s["requirement"]["peak_withdrawal_gw"],
             s["hydrogen"]["h2_fleet_twh"],
             s["adequacy"]["repurposed_h2"]["energy_utilisation"] * 100,
             s["hydrogen"]["energy_shrink_factor"]))


if __name__ == "__main__":
    main()
