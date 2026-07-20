# europe-energy-storage-adequacy

**Can Europe carry winter without natural gas?** A transparent adequacy model of the
seasonal storage Europe needs as it electrifies — and of what underground storage can
still deliver once it is repurposed from methane to hydrogen. Built on **real Eurostat
monthly consumption data** plus published storage capacities.

Author: **[Pr0spektor](https://github.com/Pr0spektor)**

---

## The finding

| | |
|---|---|
| Seasonal swing to carry (70% wind + solar) | **238 TWh / 85 GW** |
| UGS today (natural gas) | 1,100 TWh — **22% utilised** |
| Same fleet repurposed to hydrogen | **260 TWh — 92% utilised** |
| Energy lost in the switch | **~4.2×** |
| Binding constraint | **working volume**, not deliverability |

A cavern stores a *volume*, not an energy. Hydrogen holds only ~0.30 of methane's energy
per cubic metre, so Europe's comfortable gas buffer becomes a thin hydrogen margin — and it
runs out entirely as wind and solar deepen.

![Storage cycle](results/storage_cycle.png)
![Sectoral split](results/demand_by_sector.png)
![Requirement vs available](results/requirement_vs_available.png)
![Scenarios](results/scenarios.png)

**→ One-page findings: [INSIGHT_MEMO.md](INSIGHT_MEMO.md)**
**→ Full results, every country and year: [RESULTS.md](RESULTS.md)** · raw table: [results/seasonality.csv](results/seasonality.csv)

### The chain of evidence, in one place

| Question | Answer | Where |
|---|---|---|
| How uneven is European gas demand? | EU-27 peak/trough **2.68** in 2025, up from 2.29 in 2020 — 38 countries, 2020-2026 | [RESULTS §1-2](RESULTS.md) |
| Who causes it? | ~**47%** of EU gas sits in weather-driven end uses; industry is nearly flat | [RESULTS §4](RESULTS.md) |
| Which factories? | German chemicals **54 TWh**, food **32**, cement/glass **22**, paper **19**, steel **19** | [RESULTS §4](RESULTS.md) |
| What about data centres? | **~20 TWh of electricity** in Germany (2024) → 25-37 TWh by 2030 — a power load, not a gas load | [RESULTS §4](RESULTS.md) |
| What refills the swing? | EU injected **557 TWh** Apr-Oct 2025, withdrew **667 TWh** in winter; peak month **270 GW** | [RESULTS §5](RESULTS.md) |
| Where are the bottlenecks? | Deliverability (Germany **74 GW** peak) and five gas-consuming countries with **zero** storage | [RESULTS §5](RESULTS.md) |
| What happens under hydrogen? | Same caverns hold **4.2× less** energy — the buffer disappears | [RESULTS §6](RESULTS.md) |


## Measured seasonality (real data, not assumptions)

Monthly consumption straight from the **Eurostat** API (`nrg_cb_gasm`), per country and year:

| Country | Year | Peak/trough | Winter/summer | Swing above baseline |
|---|---|---|---|---|
| DE | 2020 | 2.73 | 2.50 | 17.3% |
| DE | 2021 | 3.68 | 3.12 | 19.2% |
| DE | 2022 | 4.05 | 3.16 | 20.1% |
| DE | 2023 | 3.42 | 2.99 | 19.7% |
| DE | 2024 | 3.38 | 2.87 | 19.2% |

Germany burns ~3x more gas in the peak month than the trough month, and about **a fifth of
annual consumption sits above a flat baseline** — the share flexibility must carry each year.

`src/eurostat.py` is a working client for the open Eurostat API (no key needed). The
repository ships a real cached slice so everything runs offline; extend it to any country
or to electricity with:

```bash
python src/eurostat.py --refresh --geo DE IT FR NL PL ES BE AT CZ RO
python src/eurostat.py --refresh --dataset nrg_cb_em --geo DE IT FR   # electricity
```

## What's in the model
- **Seasonal adequacy** (`adequacy.py`) — daily residual load (demand − wind/solar); a flat
  baseload carries the annual level and the store carries the seasonal swing; returns the
  working energy (TWh) and peak withdrawal (GW) required.
- **Hydrogen repurposing** (`hydrogen.py`) — volumetric energy ratio, cushion gas, working
  volume per TWh, capacity by store type against the GIE target.
- **Flexibility ladder** (`storage.py`) — batteries vs pumped hydro vs underground storage
  on energy *and* duration; only underground storage spans seasons.
- **Observed seasonality** (`seasonality.py`) — peak/trough, winter/summer and swing share
  per country-year from Eurostat.
- **Binding constraint** — whether volume or deliverability bites first.

## Repository layout
```
src/adequacy.py     # residual load, storage sizing, binding constraint
src/hydrogen.py     # CH4 -> H2 repurposing physics
src/storage.py      # flexibility ladder (energy x duration)
src/seasonality.py  # per-country/per-year seasonal swing from real data
src/eurostat.py     # Eurostat API client + disk cache (offline fallback)
src/analysis.py     # charts + results/summary.json + INSIGHT_MEMO.md
data/               # cached real Eurostat monthly series
tests/              # 22 unit tests (incl. checks against the real data)
```

## Run it
```bash
python src/analysis.py         # charts + memo + summary.json  (needs matplotlib)
python src/seasonality.py      # per-country seasonality table
python src/demand.py           # sectoral split of demand
python src/balance.py          # storage injection/withdrawal cycle + bottlenecks
python src/report.py           # RESULTS.md + results/seasonality.csv
python src/demand_chart.py     # demand_by_sector.png, de_industry_gas.png
python src/balance_chart.py    # storage_cycle.png, storage_cover.png
python tests/test_adequacy.py  # 22/22 standalone …
pytest -q                      # … or under pytest (CI)
```

## Caveats
A transparent adequacy model, not a market or network simulation: no country-by-country
transmission, no hourly resolution, no price formation. Storage capacities are published
estimates (see [SOURCES.md](SOURCES.md)); the seasonality figures are real Eurostat
observations. Decision support, not investment advice.

## License
MIT — see [LICENSE](LICENSE).
