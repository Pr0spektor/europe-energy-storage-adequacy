"""The flexibility ladder: which technology serves which timescale.

Batteries are power devices (hours), pumped hydro bridges days, and only underground
storage carries energy across seasons. Comparing them on energy alone is the classic
mistake; this module keeps energy, power and duration together.
"""
from __future__ import annotations
from data import FLEX_TECHNOLOGIES, ELECTRICITY_DEMAND_TWH


def ladder() -> list[dict]:
    """Technologies with the duration they can sustain and the demand they can cover."""
    daily_demand = ELECTRICITY_DEMAND_TWH / 365.0
    rows = []
    for name, energy_twh, power_gw, eff, duration_h in FLEX_TECHNOLOGIES:
        # hours it can run at its own rated power
        hours_at_rated = (energy_twh * 1000.0) / power_gw if power_gw else float("inf")
        rows.append({
            "technology": name,
            "energy_twh": energy_twh,
            "power_gw": power_gw,
            "round_trip_eff": eff,
            "nominal_duration_h": duration_h,
            "hours_at_rated_power": hours_at_rated,
            "days_of_eu_demand": energy_twh / daily_demand,
        })
    rows.sort(key=lambda r: r["energy_twh"])
    return rows


def seasonal_capable(rows=None, min_days: float = 30.0) -> list[str]:
    """Technologies that can carry at least `min_days` of EU demand (i.e. seasonal)."""
    rows = rows or ladder()
    return [r["technology"] for r in rows if r["days_of_eu_demand"] >= min_days]


def diurnal_gap_twh(peak_daily_swing_twh: float, battery_energy_twh: float) -> float:
    """Day/night balancing energy that batteries cannot yet cover."""
    return max(peak_daily_swing_twh - battery_energy_twh, 0.0)


if __name__ == "__main__":
    for r in ladder():
        print("%-26s %9.3f TWh %7.0f GW  %6.1f h at rated  %8.2f days of EU demand"
              % (r["technology"], r["energy_twh"], r["power_gw"],
                 r["hours_at_rated_power"], r["days_of_eu_demand"]))
    print("\nSeasonal-capable (>=30 days):", seasonal_capable())
