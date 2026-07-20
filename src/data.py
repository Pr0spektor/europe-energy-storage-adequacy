"""European storage & demand inputs, publicly anchored (see SOURCES.md).

Figures are planning inputs for a transparent adequacy model, not a licensed dataset.
Energy is in TWh, power in GW, unless stated otherwise.
"""

# ---- Underground gas storage (UGS) inventory, EU ----------------------------------
# Working gas energy today (natural gas) and the energy the SAME pore/cavern volume
# would hold if repurposed to hydrogen (studies land near a quarter of the CH4 energy).
UGS_NATURAL_GAS_TWH = 1100.0        # EU working gas capacity (GIE / AGSI order of magnitude)

# Repurposed-to-hydrogen working gas energy by store type (TWh H2)
UGS_H2_BY_TYPE = {
    "Salt caverns":            49.0,   # fast-cycling, high deliverability, H2-proven
    "Depleted gas fields":    171.0,   # largest volume, slower, purity/cushion challenges
    "Aquifers":                40.0,   # smallest share, most uncertain for H2
}

# ---- Flexibility technologies (EU scale) -----------------------------------------
# energy_twh = usable stored energy; power_gw = discharge/withdrawal capability
FLEX_TECHNOLOGIES = [
    # name,                 energy_twh, power_gw, round_trip_eff, typical_duration_h
    ("Grid batteries (Li-ion)",   0.035,     20.0, 0.87,     4),
    ("Pumped hydro",              0.250,     55.0, 0.78,    10),
    ("UGS — natural gas today", 1100.0,     700.0, 0.45,  2000),   # gas-to-power efficiency
    ("UGS — repurposed to H2",   260.0,     250.0, 0.35,  1500),
]

# ---- Demand & renewables (EU electricity) ----------------------------------------
ELECTRICITY_DEMAND_TWH = 2700.0     # EU annual electricity demand
WINTER_DEMAND_UPLIFT = 0.20         # winter daily demand above annual mean
SUMMER_DEMAND_DIP = 0.15            # summer daily demand below annual mean

VRE_SHARE_TARGET = 0.70             # wind + solar share of annual demand modelled
WIND_SHARE_OF_VRE = 0.60            # rest is solar
WIND_WINTER_UPLIFT = 0.35           # wind output above mean in winter
SOLAR_SUMMER_UPLIFT = 0.90          # solar output above mean in summer

# ---- Hydrogen physics -------------------------------------------------------------
LHV_CH4_KWH_PER_M3 = 9.97           # methane lower heating value, standard conditions
LHV_H2_KWH_PER_M3 = 3.00            # hydrogen LHV, standard conditions
CUSHION_GAS_SHARE = 0.35            # share of total gas in place that must stay as cushion

# ---- Policy benchmark --------------------------------------------------------------
GIE_H2_STORAGE_TARGET_TWH = 45.0    # GIE: underground hydrogen storage Europe needs


def total_ugs_h2_twh() -> float:
    return sum(UGS_H2_BY_TYPE.values())
