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
    de = [r for r in rows if r["country"] == "DE"]
    assert len(de) >= 5
    # winter gas burn is at least twice the summer level in every year on record
    assert all(r["winter_summer"] > 2.0 for r in de)
    assert all(2.0 < r["peak_to_trough"] < 6.0 for r in de)
    # roughly a fifth of annual consumption sits above a flat baseline
    assert all(0.10 < r["swing_share"] < 0.30 for r in de)

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
