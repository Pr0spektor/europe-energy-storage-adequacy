"""Gas → hydrogen repurposing physics for underground storage.

The point that decides seasonal adequacy: a cavern or depleted field holds a *volume*,
not an energy. Hydrogen is far lighter than methane (density ratio ≈8:1) but carries
≈2.4x more energy per kilogram, so per cubic metre it stores only about **a third** of
methane's energy. Repurposing an existing gas store to hydrogen therefore shrinks the
stored energy by roughly 3-4x once cushion gas and pressure limits are included.

Stdlib only; unit-tested.
"""
from __future__ import annotations
from data import (LHV_CH4_KWH_PER_M3, LHV_H2_KWH_PER_M3, CUSHION_GAS_SHARE,
                  UGS_NATURAL_GAS_TWH, UGS_H2_BY_TYPE)


def volumetric_energy_ratio() -> float:
    """Energy stored per unit volume: hydrogen relative to methane (≈0.30)."""
    return LHV_H2_KWH_PER_M3 / LHV_CH4_KWH_PER_M3


def repurposed_energy_twh(ch4_energy_twh: float, ratio: float | None = None) -> float:
    """Energy a store holds after switching from methane to hydrogen (same volume)."""
    r = volumetric_energy_ratio() if ratio is None else ratio
    return ch4_energy_twh * r


def energy_loss_factor(observed_h2_twh: float | None = None) -> float:
    """How many times the stored energy shrinks when the EU fleet is repurposed.

    Uses the published per-store estimates when available (which include cushion gas and
    pressure effects) rather than the clean physics ratio alone.
    """
    h2 = observed_h2_twh if observed_h2_twh is not None else sum(UGS_H2_BY_TYPE.values())
    if h2 <= 0:
        raise ValueError("hydrogen capacity must be positive")
    return UGS_NATURAL_GAS_TWH / h2


def working_volume_for_energy(target_twh: float, gas: str = "H2") -> float:
    """Geometric working volume (billion m³, standard conditions) for a target energy."""
    lhv = LHV_H2_KWH_PER_M3 if gas.upper() == "H2" else LHV_CH4_KWH_PER_M3
    # TWh -> kWh, divide by kWh/m3, express in billion m3
    return (target_twh * 1e9) / lhv / 1e9


def total_gas_in_place(working_twh: float, cushion_share: float = CUSHION_GAS_SHARE) -> float:
    """Working gas is only part of the inventory — cushion gas keeps pressure up."""
    if not 0 <= cushion_share < 1:
        raise ValueError("cushion share must be in [0, 1)")
    return working_twh / (1.0 - cushion_share)


def capacity_vs_target(target_twh: float) -> dict:
    """Compare repurposable capacity by store type against a policy target."""
    rows = []
    cumulative = 0.0
    for name, twh in sorted(UGS_H2_BY_TYPE.items(), key=lambda kv: -kv[1]):
        cumulative += twh
        rows.append({"store": name, "h2_twh": twh, "cumulative_twh": cumulative,
                     "covers_target": cumulative >= target_twh})
    total = cumulative
    return {"target_twh": target_twh, "total_h2_twh": total,
            "target_met": total >= target_twh,
            "headroom_twh": total - target_twh, "by_store": rows}


if __name__ == "__main__":
    from data import GIE_H2_STORAGE_TARGET_TWH
    print("H2 vs CH4 energy per volume: %.2f" % volumetric_energy_ratio())
    print("EU fleet: %.0f TWh (CH4) -> %.0f TWh (H2); energy shrinks %.1fx"
          % (UGS_NATURAL_GAS_TWH, sum(UGS_H2_BY_TYPE.values()), energy_loss_factor()))
    r = capacity_vs_target(GIE_H2_STORAGE_TARGET_TWH)
    print("GIE target %.0f TWh met by repurposing? %s (headroom %.0f TWh)"
          % (r["target_twh"], r["target_met"], r["headroom_twh"]))
    print("Salt caverns alone cover the target: %s"
          % (UGS_H2_BY_TYPE["Salt caverns"] >= GIE_H2_STORAGE_TARGET_TWH))

# ---------------------------------------------------------------- uncertainty band ---
# The repurposed-energy figure is a model result, not a measurement: it depends on the
# volumetric ratio (which moves with gas quality and compressibility) and on the share of
# the working volume that has to be kept as cushion gas. Both are reported as ranges in the
# literature, so the headline should be a range too.
LHV_H2_RANGE = (2.9, 3.1)          # kWh per m3 at standard conditions
LHV_CH4_RANGE = (9.9, 10.5)
CUSHION_RANGE = (0.40, 0.60)


def repurposed_energy_band(n: int = 20000, seed: int = 42) -> dict:
    """Monte Carlo over the two assumptions behind the hydrogen capacity figure.

    The published per-store totals already embed a central ratio and cushion share, so each
    draw scales that total by the relative deviation of the two parameters. Returns P10,
    P50 and P90 of the fleet total in TWh.
    """
    import random
    rng = random.Random(seed)
    base = float(sum(UGS_H2_BY_TYPE.values()))
    central_ratio = volumetric_energy_ratio()
    draws = []
    for _ in range(n):
        ratio = rng.uniform(*LHV_H2_RANGE) / rng.uniform(*LHV_CH4_RANGE)
        cushion = rng.uniform(*CUSHION_RANGE)
        scale = (ratio / central_ratio) * ((1.0 - cushion) / (1.0 - CUSHION_GAS_SHARE))
        draws.append(base * scale)
    draws.sort()

    def pct(q: float) -> float:
        return round(draws[min(int(q / 100.0 * (n - 1)), n - 1)], 1)

    return {"base_twh": round(base, 1), "p10_twh": pct(10), "p50_twh": pct(50),
            "p90_twh": pct(90), "n": n, "seed": seed,
            "assumptions": {"lhv_h2_kwh_per_m3": LHV_H2_RANGE,
                            "lhv_ch4_kwh_per_m3": LHV_CH4_RANGE,
                            "cushion_share": CUSHION_RANGE}}
