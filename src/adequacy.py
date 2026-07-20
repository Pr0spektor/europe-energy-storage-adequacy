"""Seasonal adequacy: how much storage energy and withdrawal power Europe needs.

Method (daily resolution over a year):
  1. build a demand profile (winter-peaking) and wind/solar profiles (wind winter-heavy,
     solar summer-heavy) scaled to a target VRE share of annual demand;
  2. residual load = demand − VRE. Positive days must be served from storage/dispatchable,
     negative days are surplus available to refill it;
  3. run the store: charge on surplus, discharge on deficit, tracking state of charge;
  4. read off the two numbers that decide adequacy —
        * **energy**: the deepest drawdown over the year (TWh of working gas needed), and
        * **power**: the largest single-day withdrawal rate (GW of deliverability needed).

The distinction matters: an underground store can hold plenty of energy and still fail on
peak days because it cannot *deliver* fast enough. Stdlib only; unit-tested.
"""
from __future__ import annotations
import math
from typing import Sequence
from data import (ELECTRICITY_DEMAND_TWH, WINTER_DEMAND_UPLIFT, SUMMER_DEMAND_DIP,
                  VRE_SHARE_TARGET, WIND_SHARE_OF_VRE, WIND_WINTER_UPLIFT,
                  SOLAR_SUMMER_UPLIFT)

DAYS = 365


def _seasonal(day: int, amplitude: float, peak_day: int) -> float:
    """1 + amplitude * cos(2*pi*(day - peak_day)/365) — a smooth seasonal shape."""
    return 1.0 + amplitude * math.cos(2.0 * math.pi * (day - peak_day) / DAYS)


def demand_profile(annual_twh: float = ELECTRICITY_DEMAND_TWH) -> list[float]:
    """Daily electricity demand (TWh/day), winter-peaking, normalised to the annual total."""
    amp = (WINTER_DEMAND_UPLIFT + SUMMER_DEMAND_DIP) / 2.0
    raw = [_seasonal(d, amp, peak_day=15) for d in range(DAYS)]      # peak mid-January
    scale = annual_twh / sum(raw)
    return [r * scale for r in raw]


def vre_profile(annual_twh: float = ELECTRICITY_DEMAND_TWH,
                vre_share: float = VRE_SHARE_TARGET) -> list[float]:
    """Daily wind + solar generation (TWh/day): wind winter-heavy, solar summer-heavy."""
    wind_raw = [_seasonal(d, WIND_WINTER_UPLIFT, peak_day=10) for d in range(DAYS)]
    solar_raw = [_seasonal(d, SOLAR_SUMMER_UPLIFT, peak_day=182) for d in range(DAYS)]
    wind_total = annual_twh * vre_share * WIND_SHARE_OF_VRE
    solar_total = annual_twh * vre_share * (1.0 - WIND_SHARE_OF_VRE)
    ws = wind_total / sum(wind_raw)
    ss = solar_total / sum(solar_raw)
    return [wind_raw[d] * ws + solar_raw[d] * ss for d in range(DAYS)]


def residual_load(annual_twh: float = ELECTRICITY_DEMAND_TWH,
                  vre_share: float = VRE_SHARE_TARGET) -> list[float]:
    """Demand minus wind+solar, per day (TWh/day). Positive = must be served from storage."""
    d = demand_profile(annual_twh)
    v = vre_profile(annual_twh, vre_share)
    return [d[i] - v[i] for i in range(DAYS)]


def simulate_store(residual: Sequence[float], efficiency: float = 1.0) -> dict:
    """Size the seasonal store from a residual-load profile.

    Storage fixes *timing*, not the energy *level*: a flat dispatchable/import baseload
    equal to the mean residual carries the annual balance, and the store carries the
    seasonal swing around it. So we net out that baseload (leaving a profile that sums to
    zero over the year), integrate it, and read the working energy off the peak-to-trough
    range of the state-of-charge path.

    Returns working energy required (TWh), peak daily withdrawal (GW), the balancing
    baseload (TWh/day) and the SoC path.
    """
    n = len(residual)
    baseload = sum(residual) / n if n else 0.0        # flat non-VRE generation
    net = [r - baseload for r in residual]

    soc = 0.0
    lowest = highest = 0.0
    peak_withdrawal_twh_day = 0.0
    discharged = 0.0
    path = []
    for x in net:
        if x > 0:                       # deficit beyond baseload: withdraw
            soc -= x
            discharged += x
            peak_withdrawal_twh_day = max(peak_withdrawal_twh_day, x)
        else:                           # surplus: inject (with efficiency loss)
            soc += (-x) * efficiency
        lowest = min(lowest, soc)
        highest = max(highest, soc)
        path.append(soc)

    required_energy_twh = highest - lowest            # peak-to-trough seasonal swing
    peak_power_gw = peak_withdrawal_twh_day * 1000.0 / 24.0    # TWh/day -> GW
    return {"required_energy_twh": required_energy_twh,
            "peak_withdrawal_gw": peak_power_gw,
            "baseload_twh_per_day": baseload,
            "energy_discharged_twh": discharged,
            "soc_path": path}


def binding_constraint(required_energy_twh: float, required_power_gw: float,
                       available_energy_twh: float, available_power_gw: float) -> dict:
    """Which limit bites first — stored volume (energy) or deliverability (power)?"""
    energy_ratio = required_energy_twh / available_energy_twh if available_energy_twh else float("inf")
    power_ratio = required_power_gw / available_power_gw if available_power_gw else float("inf")
    if energy_ratio <= 1 and power_ratio <= 1:
        limit = "none — both energy and deliverability are sufficient"
    elif energy_ratio > power_ratio:
        limit = "working energy (stored volume)"
    else:
        limit = "deliverability (withdrawal rate)"
    return {"energy_utilisation": energy_ratio, "power_utilisation": power_ratio,
            "binding_constraint": limit,
            "energy_gap_twh": max(required_energy_twh - available_energy_twh, 0.0),
            "power_gap_gw": max(required_power_gw - available_power_gw, 0.0)}


def days_of_cover(available_energy_twh: float, peak_daily_twh: float) -> float:
    """How many consecutive peak-demand days the store can serve."""
    return available_energy_twh / peak_daily_twh if peak_daily_twh > 0 else float("inf")


if __name__ == "__main__":
    from data import total_ugs_h2_twh, UGS_NATURAL_GAS_TWH
    res = residual_load()
    sim = simulate_store(res)
    print("Seasonal storage requirement: %.0f TWh, peak withdrawal %.0f GW"
          % (sim["required_energy_twh"], sim["peak_withdrawal_gw"]))
    for label, energy, power in [("Gas UGS today", UGS_NATURAL_GAS_TWH, 700.0),
                                 ("UGS repurposed to H2", total_ugs_h2_twh(), 250.0)]:
        b = binding_constraint(sim["required_energy_twh"], sim["peak_withdrawal_gw"], energy, power)
        print("  %-22s energy %.0f%% used, power %.0f%% used -> %s"
              % (label, b["energy_utilisation"] * 100, b["power_utilisation"] * 100,
                 b["binding_constraint"]))
