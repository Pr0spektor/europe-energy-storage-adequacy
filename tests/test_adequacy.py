"""Unit tests. Runs under pytest or standalone: python tests/test_adequacy.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from data import ELECTRICITY_DEMAND_TWH, UGS_NATURAL_GAS_TWH, UGS_H2_BY_TYPE, total_ugs_h2_twh
import hydrogen as H
import adequacy as A
import storage as S


def approx(a, b, rel=1e-6, abs_=1e-9):
    return abs(a - b) <= max(rel * max(abs(a), abs(b)), abs_)


# ---- hydrogen physics ----
def test_volumetric_ratio_about_one_third():
    r = H.volumetric_energy_ratio()
    assert 0.25 < r < 0.35, r          # hydrogen holds ~a third of methane's energy per m3

def test_repurposing_reduces_energy():
    assert H.repurposed_energy_twh(1000) < 1000

def test_energy_shrink_factor_matches_published_split():
    f = H.energy_loss_factor()
    assert approx(f, UGS_NATURAL_GAS_TWH / total_ugs_h2_twh())
    assert 3.0 < f < 5.0               # fleet energy falls roughly 4x

def test_cushion_gas_raises_total_inventory():
    assert H.total_gas_in_place(100, 0.35) > 100
    assert approx(H.total_gas_in_place(65, 0.35), 100.0, rel=1e-9)

def test_working_volume_scales_inversely_with_lhv():
    v_h2 = H.working_volume_for_energy(10, "H2")
    v_ch4 = H.working_volume_for_energy(10, "CH4")
    assert v_h2 > v_ch4                # hydrogen needs more volume for the same energy

def test_salt_caverns_alone_cover_the_policy_target():
    r = H.capacity_vs_target(45.0)
    assert r["target_met"] and UGS_H2_BY_TYPE["Salt caverns"] >= 45.0


# ---- adequacy model ----
def test_profiles_conserve_annual_energy():
    d = A.demand_profile(ELECTRICITY_DEMAND_TWH)
    assert len(d) == 365 and approx(sum(d), ELECTRICITY_DEMAND_TWH, rel=1e-9)
    v = A.vre_profile(ELECTRICITY_DEMAND_TWH, 0.7)
    assert approx(sum(v), ELECTRICITY_DEMAND_TWH * 0.7, rel=1e-9)

def test_demand_peaks_in_winter():
    d = A.demand_profile()
    assert d[15] > d[182]              # mid-January above early July

def test_residual_is_winter_heavy():
    r = A.residual_load()
    assert r[15] > r[182]              # mid-January residual exceeds early July

def test_store_is_balanced_by_a_flat_baseload():
    sim = A.simulate_store(A.residual_load())
    assert sim["baseload_twh_per_day"] > 0        # non-VRE carries the annual level
    assert abs(sim["soc_path"][-1]) < 1e-6        # the seasonal cycle closes on itself

def test_storage_requirement_positive_and_bounded():
    sim = A.simulate_store(A.residual_load())
    assert sim["required_energy_twh"] > 0
    assert sim["required_energy_twh"] < ELECTRICITY_DEMAND_TWH
    assert sim["peak_withdrawal_gw"] > 0

def test_higher_vre_share_raises_seasonal_requirement():
    lo = A.simulate_store(A.residual_load(vre_share=0.5))["required_energy_twh"]
    hi = A.simulate_store(A.residual_load(vre_share=0.8))["required_energy_twh"]
    assert hi > lo

def test_binding_constraint_detects_energy_limit():
    b = A.binding_constraint(required_energy_twh=400, required_power_gw=90,
                             available_energy_twh=260, available_power_gw=250)
    assert b["binding_constraint"].startswith("working energy")
    assert approx(b["energy_gap_twh"], 140.0)

def test_binding_constraint_detects_power_limit():
    b = A.binding_constraint(required_energy_twh=100, required_power_gw=300,
                             available_energy_twh=260, available_power_gw=250)
    assert b["binding_constraint"].startswith("deliverability")

def test_no_constraint_when_ample():
    b = A.binding_constraint(100, 100, 1100, 700)
    assert b["binding_constraint"].startswith("none")


# ---- flexibility ladder ----
def test_only_underground_storage_is_seasonal():
    names = S.seasonal_capable()
    assert all("UGS" in n for n in names) and len(names) >= 1

def test_batteries_cover_far_less_than_a_day():
    rows = {r["technology"]: r for r in S.ladder()}
    assert rows["Grid batteries (Li-ion)"]["days_of_eu_demand"] < 0.02


# ---- seasonality on real Eurostat data ----
import seasonality as SE
from eurostat import monthly_series, GAS

_flat = [10.0] * 12
_seasonal = [20, 18, 15, 10, 7, 5, 5, 5, 8, 12, 16, 19]

def test_flat_year_has_no_seasonality():
    assert approx(SE.peak_to_trough(_flat), 1.0)
    assert approx(SE.winter_summer_ratio(_flat), 1.0)
    assert approx(SE.swing(_flat)["swing_share"], 0.0, abs_=1e-12)

def test_seasonal_year_metrics():
    assert approx(SE.peak_to_trough(_seasonal), 20 / 5)
    assert SE.winter_summer_ratio(_seasonal) > 3.0
    sw = SE.swing(_seasonal)
    assert 0 < sw["swing_share"] < 0.5
    assert approx(sw["annual_total"], sum(_seasonal))

def test_incomplete_year_returns_none():
    assert SE.peak_to_trough([1, 2, 3]) is None
    assert SE.swing([1, 2, 3]) is None

def test_real_eurostat_cache_is_loaded():
    s = monthly_series(GAS)
    assert "DE" in s and len(s["DE"]) >= 5           # five real years bundled
    assert all(len(m) == 12 for m in s["DE"].values())

def test_real_german_gas_is_strongly_seasonal():
    rows = SE.country_year_table()
    # complete years only — the current year is still part-reported
    de = [r for r in rows if r["country"] == "DE" and r["winter_summer"] is not None]
    assert len(de) >= 5
    # winter gas burn is at least twice the summer level in every year on record
    assert all(r["winter_summer"] > 2.0 for r in de)
    assert all(2.0 < r["peak_to_trough"] < 6.0 for r in de)
    # roughly a fifth of annual consumption sits above a flat baseline
    assert all(0.10 < r["swing_share"] < 0.30 for r in de)

# ---- Eurostat client: JSON-stat decoding & validation ----
import eurostat as EU

def _doc(values):
    """A JSON-stat document shaped exactly like the real Eurostat response (2 geos x 2 months)."""
    return {
        "id": ["freq", "nrg_bal", "siec", "unit", "geo", "time"],
        "size": [1, 1, 1, 1, 2, 2],
        "value": values,
        "dimension": {
            "geo": {"category": {"index": {"DE": 0, "FR": 1}}},
            "time": {"category": {"index": {"2024-01": 0, "2024-02": 1}}},
        },
    }

def test_parse_decodes_geo_and_time_from_flat_index():
    # flat index = geo_idx * n_time + time_idx  ->  DE Jan=0, DE Feb=1, FR Jan=2, FR Feb=3
    s = EU.parse_jsonstat(_doc({"0": 100.0, "1": 90.0, "2": 50.0, "3": 45.0}))
    assert s["DE"]["2024"][0] == 100.0 and s["DE"]["2024"][1] == 90.0
    assert s["FR"]["2024"][0] == 50.0 and s["FR"]["2024"][1] == 45.0
    assert s["DE"]["2024"][5] is None          # untouched months stay empty

def test_parse_handles_sparse_values():
    s = EU.parse_jsonstat(_doc({"2": 50.0}))   # only FR January reported
    assert "FR" in s and s["FR"]["2024"][0] == 50.0
    assert "DE" not in s

def test_parse_empty_document():
    assert EU.parse_jsonstat({"value": {}}) == {}
    assert EU.parse_jsonstat(None) == {}

def test_validate_flags_negative_and_counts_coverage():
    good = {"DE": {"2024": [1.0] * 12}}
    rep = EU.validate(good)
    assert rep["ok"] and rep["complete_country_years"] == 1 and rep["countries"] == 1
    bad = {"DE": {"2024": [-1.0] + [1.0] * 11}, "FR": {"2024": [None] * 12}}
    rep2 = EU.validate(bad)
    assert not rep2["ok"] and rep2["partial_country_years"] >= 0
    assert any("negative" in i for i in rep2["issues"])
    assert any("no observations" in i for i in rep2["issues"])

def test_aggregates_are_separated_from_countries():
    s = {"EU27_2020": {}, "EA21": {}, "DE": {}, "FR": {}}
    assert set(EU.countries_only(s)) == {"DE", "FR"}

def test_cached_dataset_passes_its_own_validation():
    blob = EU.load_cache(EU.GAS) or {}
    rep = EU.validate(blob.get("series", {}))
    assert rep["ok"], rep["issues"]


# ---- demand-side split (Eurostat nrg_bal_c) ----
import demand as DM

def test_sector_shares_sum_to_one():
    sh = DM.shares("DE")
    assert approx(sum(sh.values()), 1.0, rel=1e-9)
    assert len(sh) == 4

def test_germany_sector_volumes_are_plausible():
    b = DM.by_sector("DE")
    assert 600_000 < sum(b.values()) < 900_000        # GWh, i.e. 600-900 TWh
    assert b["Households"] > b["Commercial & public services"]

def test_weather_exposed_share_between_industry_and_households():
    w = DM.weather_exposed_share("DE")
    assert DM.WEATHER_SENSITIVITY["FC_IND_E"] < w < DM.WEATHER_SENSITIVITY["FC_OTH_HH_E"]

def test_germany_is_the_largest_industrial_gas_user():
    assert DM.ranking("FC_IND_E", 1)[0][0] == "DE"

def test_chemicals_lead_german_industry():
    br = DM.de_industry_branches()
    assert max(br, key=br.get) == "Chemical and petrochemical"


# ---- storage cycle & bottlenecks (Eurostat STK_CHG_MG) ----
import balance as BAL

def test_stock_change_parses_all_twelve_months():
    st = BAL.parse()
    assert len(st["DE"]) == 12 and all(v is not None for v in st["DE"])

def test_winter_is_withdrawal_and_summer_is_injection():
    de = BAL.parse()["DE"]
    assert de[0] < 0 and de[1] < 0          # January, February: net withdrawal
    assert de[5] > 0 and de[6] > 0          # June, July: net injection

def test_eu_cycle_roughly_balances_over_the_year():
    e = BAL.eu_cycle()
    assert e["injection_twh"] > 300 and e["withdrawal_twh"] > 300
    assert abs(e["injection_twh"] - e["withdrawal_twh"]) < 0.5 * e["withdrawal_twh"]

def test_storage_covers_the_seasonal_swing_where_it_exists():
    rows = [r for r in BAL.table() if r["storage_cover"] is not None][:10]
    assert len(rows) >= 8
    assert all(0.7 < r["storage_cover"] < 1.6 for r in rows), \
        [(r["country"], round(r["storage_cover"], 2)) for r in rows]

def test_countries_without_storage_are_flagged():
    codes = {r["country"] for r in BAL.no_storage()}
    assert "IE" in codes                    # Ireland consumes ~55 TWh/y and stores none
    assert "DE" not in codes

def test_peak_withdrawal_rate_is_a_power_not_an_energy():
    de = [r for r in BAL.table() if r["country"] == "DE"][0]
    assert de["peak_withdrawal_gw"] > 20    # tens of GW sustained through the peak month
    assert de["peak_withdrawal_gw"] < de["peak_month_withdrawal_twh"] * 1000

if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for fn in fns:
        try:
            fn(); passed += 1; print(f"  PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"  FAIL  {fn.__name__}: {e}")
    print(f"{passed}/{passed+failed} tests passed.")
    sys.exit(1 if failed else 0)
