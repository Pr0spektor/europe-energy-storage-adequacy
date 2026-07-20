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

## Demand-side split and storage cycle (added 2026-07-20)

| Source | Dataset | What it gives | Cached as |
|---|---|---|---|
| Eurostat | `nrg_bal_c` — complete energy balances, natural gas (G3000), GWh, 2024 | gas by sector: power & heat, industry, households, commercial; German industry by branch | `data/raw/gas_sectors_2024.json` |
| Eurostat | `nrg_cb_gasm` — `STK_CHG_MG`, TJ GCV, monthly 2025, all geos | net injection / withdrawal per country per month | `data/raw/gas_stock_change_2025.json` |
| Borderstep Institute / Bitkom | German data centre electricity: ~20 TWh (2024); 25-37 TWh projected 2030 | scale comparison for the data-centre question (electricity, not gas) | constant in `src/demand.py` |

Raw API responses are stored verbatim and decoded by the same unit-tested parsers used
for live pulls, so every figure in RESULTS.md can be traced back to the source document.

## Gas network (added 2026-07-20)

| Source | Endpoint | What it gives | Cached as |
|---|---|---|---|
| ENTSOG Transparency Platform | `interconnections.csv?fromCountryKey=..&toCountryKey=..` | topology: which points join which countries, operator on each side, schematic map coordinates | `data/raw/entsog_de_border_2026-01-15.json` |
| ENTSOG Transparency Platform | `operationalData.csv?indicator=Physical Flow\|Firm Technical&periodType=day&pointDirection=..` | metered daily flow and firm technical capacity per point-direction | same file |

**No API key and no registration are required for ENTSOG.** `src/entsog.py` calls it
directly and falls back to the bundled snapshot when offline.

## Storage, facility level (added 2026-07-20)

| Source | Endpoint | What it gives | Cached as |
|---|---|---|---|
| GIE AGSI+ | `/api` | latest gas day: EU → country → company → facility, working volume, injection and withdrawal capacity, fill % | `data/raw/agsi_2026-07-18.json`, `data/raw/agsi_de_facilities_2026-07-18.json` |
| GIE AGSI+ | `/api?type=eu&from=..&to=..` | EU daily history 2020-2026 (2,391 gas days) → gas-year peaks, troughs and maximum withdrawal | `data/raw/agsi_2026-07-18.json` |
| GIE AGSI+ | `/api?country=XX&from=..&to=..` | per-country winter 2025/26 daily withdrawal vs capacity | `data/raw/agsi_2026-07-18.json` |

AGSI+ is free but authenticated. Create an account at <https://agsi.gie.eu/account>; the
key appears on the API Account page and does not expire. It must be sent in the **`x-key`
header** — passing it as a query parameter returns `access denied`. `src/agsi.py` reads it
from the `AGSI_KEY` environment variable and never stores it in the repository.

## LNG regasification (added 2026-07-20)

| Source | Endpoint | What it gives | Cached as |
|---|---|---|---|
| GIE ALSI | `/api` | terminals per country and daily send-out, gas day 2026-07-18 | `data/raw/alsi_2026-07-18.json` |
| GIE ALSI | `/api?country=XX&from=..&to=..` | winter 2025/26 daily send-out → peak day and winter total | same file |

ALSI uses the **same GIE account and `x-key` header as AGSI+**; one key covers both.

One further source is free but gated behind a registration:

- **ENTSO-E Transparency Platform** (electricity flows, generation, congestion) — register
  at <https://transparency.entsoe.eu/>, then email transparency@entsoe.eu with subject
  "RESTful API access"; access is granted within ~3 working days, after which the security
  token is generated in account settings.
