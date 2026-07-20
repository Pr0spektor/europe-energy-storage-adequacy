# Data sources & provenance

## Real, retrieved data
- **Eurostat — `nrg_cb_gasm`** "Supply, transformation and consumption of gas (monthly)",
  indicator *Inland consumption – observed* (IC_OBS), natural gas (G3000), unit TJ (GCV).
  Retrieved 2026-07-20 via the open dissemination API (no key required); cached in
  `data/eurostat_gas_monthly.json`. Every seasonality figure in this repo is computed from
  these observations.
  https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_cb_gasm
- **Eurostat — `nrg_cb_em`** "Supply, transformation and consumption of electricity (monthly)",
  unit GWh — supported by the same client (`src/eurostat.py --dataset nrg_cb_em`); the valid
  energy-balance code is discovered from the dataset's own dimensions at refresh time.

## Published capacity estimates
- **EU underground gas storage working capacity ≈ 1,100 TWh** — Gas Infrastructure Europe
  (GIE) AGSI+ aggregate. https://www.gie.eu/ · https://agsi.gie.eu/
- **Repurposing EU gas storage to hydrogen ≈ 260–265 TWh** working gas energy, split roughly
  **salt caverns ~49 TWh (18%), depleted gas fields ~171 TWh (68%), aquifers ~40 TWh (14%)** —
  techno-economic analysis of underground hydrogen storage in Europe (iScience / PMC).
  https://pmc.ncbi.nlm.nih.gov/articles/PMC10821165/
- **GIE: Europe needs ~45 TWh of underground hydrogen storage** — GIE position paper.
  https://www.gie.eu/wp-content/uploads/filr/9697/RPT-EU_Underground_Hydrogen_Storage_Targets-090424-CLEAN.pdf
- **EU electricity demand ≈ 2,700 TWh/yr; wind + solar ≈ 29% of the EU power mix (2024);
  renewables ≈ 47.5% of gross consumption** — Ember European Electricity Review 2025 and
  Eurostat. https://ember-energy.org/latest-insights/european-electricity-review-2025/ ·
  https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20260114-1

## Physics
- Hydrogen vs methane: mass density ratio ≈ 8:1 in methane's favour, gravimetric energy ≈ 2.4:1
  in hydrogen's favour, so **volumetric energy ≈ 0.30 of methane** (LHV ~3.0 vs ~9.97 kWh/m³ at
  standard conditions). This, not chemistry alone, is why repurposing shrinks stored energy.

> Capacity and demand figures are planning inputs at EU aggregate level, not a licensed
> asset-level dataset. Replace with operator data before commercial use.
