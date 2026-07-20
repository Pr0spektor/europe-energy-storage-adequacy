# Results — seasonal swing of gas demand in Europe, 2020–2026

Source: **Eurostat `nrg_cb_gasm`** (inland gas consumption, monthly, TJ GCV), pulled 2026-07-20, raw responses in `data/raw/`. **38 countries, 217 complete country-years, 0 validation issues.** Every number below is computed, not assumed.

## 1. How uneven is demand, and is it getting worse?

Median across all countries, per year:

| Year | Countries | Median peak/trough | Median winter/summer | Median swing above baseline |
|---|---|---|---|---|
| 2020 | 33 | 2.73 | 2.12 | 14.8% |
| 2021 | 34 | 2.98 | 2.30 | 15.2% |
| 2022 | 32 | 3.06 | 2.15 | 14.9% |
| 2023 | 32 | 2.74 | 1.97 | 13.1% |
| 2024 | 33 | 2.92 | 2.07 | 14.9% |

EU-27 as one system:

| Year | Annual gas (TWh) | Peak/trough | Winter/summer | Swing above baseline (TWh) |
|---|---|---|---|---|
| 2020 | 4213 | 2.29 | 2.05 | 598 |
| 2021 | 4396 | 2.72 | 2.34 | 671 |
| 2022 | 3803 | 2.75 | 2.24 | 579 |
| 2023 | 3534 | 2.32 | 2.16 | 516 |
| 2024 | 3547 | 2.59 | 2.27 | 557 |

**Read:** consumption fell hard after 2021, but the *shape* did not flatten — the median peak-to-trough ratio is higher in 2025 than in 2020. Less gas, same winter dependence.

## 2. Which countries lean hardest on winter supply?

Mean over 2020–2025:

| Rank | Country | Peak/trough | Winter/summer | Swing above baseline | Annual gas (TWh, 2025) |
|---|---|---|---|---|---|
| 1 | North Macedonia (MK) | 10.02 | 1.67 | 19.0% | n/a |
| 2 | Moldova (MD) | 7.28 | 5.81 | 31.4% | n/a |
| 3 | Latvia (LV) | 7.13 | 3.93 | 24.4% | n/a |
| 4 | Albania (AL) | 5.03 | 0.83 | 11.6% | n/a |
| 5 | Estonia (EE) | 4.90 | 3.71 | 22.0% | n/a |
| 6 | Georgia (GE) | 4.68 | 3.91 | 24.3% | n/a |
| 7 | France (FR) | 4.05 | 3.27 | 21.3% | n/a |
| 8 | Hungary (HU) | 3.81 | 3.27 | 21.2% | n/a |
| 9 | Ukraine (UA) | 3.68 | 3.17 | 22.3% | n/a |
| 10 | Luxembourg (LU) | 3.64 | 2.81 | 17.7% | n/a |
| 11 | Slovakia (SK) | 3.56 | 2.99 | 19.6% | n/a |
| 12 | Romania (RO) | 3.55 | 3.01 | 20.9% | n/a |
| 13 | Germany (DE) | 3.45 | 2.93 | 19.1% | n/a |
| 14 | Czechia (CZ) | 3.40 | 3.04 | 19.9% | n/a |
| 15 | Austria (AT) | 3.34 | 2.88 | 18.6% | n/a |
| 16 | Serbia (RS) | 3.31 | 2.87 | 19.6% | n/a |
| 17 | Turkiye (TR) | 2.89 | 2.07 | 15.5% | n/a |
| 18 | Sweden (SE) | 2.87 | 1.79 | 12.2% | n/a |
| 19 | Finland (FI) | 2.77 | 1.68 | 12.6% | n/a |
| 20 | Denmark (DK) | 2.54 | 2.15 | 13.8% | n/a |
| 21 | Lithuania (LT) | 2.51 | 1.76 | 12.3% | n/a |
| 22 | Belgium (BE) | 2.47 | 2.13 | 14.3% | n/a |
| 23 | Slovenia (SI) | 2.47 | 2.11 | 13.7% | n/a |
| 24 | Croatia (HR) | 2.44 | 1.87 | 12.4% | n/a |
| 25 | Italy (IT) | 2.44 | 2.00 | 13.8% | n/a |
| 26 | Netherlands (NL) | 2.40 | 2.01 | 13.1% | n/a |
| 27 | Poland (PL) | 2.25 | 1.99 | 12.9% | n/a |
| 28 | Bulgaria (BG) | 2.23 | 1.78 | 11.8% | n/a |
| 29 | Greece (EL) | 1.83 | 1.03 | 6.7% | n/a |
| 30 | Malta (MT) | 1.79 | 0.78 | 6.7% | n/a |
| 31 | Spain (ES) | 1.56 | 1.26 | 5.7% | n/a |
| 32 | Portugal (PT) | 1.48 | 1.03 | 5.0% | n/a |
| 33 | Ireland (IE) | 1.41 | 1.22 | 4.4% | n/a |
| 34 | Norway (NO) | 1.29 | 1.03 | 2.8% | n/a |

## 3. Germany in detail

| Year | Annual gas (TWh) | Peak month | Trough month | Peak/trough | Swing above baseline (TWh) |
|---|---|---|---|---|---|
| 2020 | 962 | Jan | Aug | 2.73 | 166 |
| 2021 | 1009 | Jan | Aug | 3.68 | 194 |
| 2022 | 854 | Jan | Aug | 4.05 | 171 |
| 2023 | 821 | Jan | Jul | 3.42 | 162 |
| 2024 | 837 | Jan | Aug | 3.38 | 161 |

**Read:** Germany's annual gas use fell ~17% from 2021 to 2025, yet the winter peak still runs 3.4x the summer trough, and ~161 TWh a year has to be carried from summer into winter.

## 4. Who burns it, and which part of it moves with the weather

Source: **Eurostat `nrg_bal_c`**, natural gas, GWh, 2024 (`data/raw/gas_sectors_2024.json`).

| Country | Power & heat | Industry | Households | Commercial & public | Total (TWh) | Weather-exposed |
|---|---|---|---|---|---|---|
| EU-27 | 33% | 28% | 27% | 12% | 2887 | 47% |
| Germany | 30% | 27% | 30% | 13% | 736 | 49% |
| Italy | 40% | 20% | 28% | 12% | 556 | 49% |
| Turkiye | 25% | 25% | 38% | 11% | 474 | 53% |
| France | 15% | 33% | 33% | 19% | 302 | 52% |
| Spain | 39% | 37% | 14% | 10% | 248 | 37% |
| Netherlands | 40% | 23% | 26% | 11% | 207 | 47% |
| Poland | 30% | 29% | 31% | 10% | 157 | 48% |
| Romania | 33% | 21% | 36% | 10% | 86 | 52% |
| Belgium | 19% | 38% | 29% | 14% | 118 | 46% |
| Hungary | 29% | 20% | 40% | 11% | 71 | 55% |
| Czechia | 24% | 32% | 27% | 17% | 63 | 48% |
| Austria | 30% | 43% | 20% | 7% | 62 | 38% |

![Sectoral split](results/demand_by_sector.png)

**Where the swing comes from.** Industry runs process heat more or less flat through the year; households and commercial buildings are almost pure space heating. So the winter peak is overwhelmingly a *buildings* phenomenon, amplified by gas-fired power and district heat in cold snaps. In Germany ~49% of gas volume sits in weather-driven end uses — which is why a mild winter moves the whole European balance.

### Germany — which factories

| Branch | Gas, TWh (2024) |
|---|---|
| Chemical and petrochemical | 53.9 |
| Food, beverages and tobacco | 31.6 |
| Non-metallic minerals (cement, glass, ceramics) | 22.3 |
| Paper, pulp and printing | 18.9 |
| Iron and steel | 18.7 |

Chemicals alone burn 54 TWh — more than the next two branches combined, and this is *energy use only*, excluding gas used as feedstock. For scale, **German data centres consumed ~20 TWh of electricity in 2024**, projected to 25–37 TWh by 2030 (Borderstep/Bitkom). Data centres are a fast-growing *electricity* load, not a gas load — they add to the power system's flat baseload, not to the seasonal gas swing.

![German industry](results/de_industry_gas.png)

## 5. What refills it, and where the bottlenecks are

Source: **Eurostat `nrg_cb_gasm`, STK_CHG_MG** (stock changes), 2025 monthly (`data/raw/gas_stock_change_2025.json`). Positive = injection, negative = withdrawal.

In 2025 the EU-27 injected **557 TWh** into storage between April and October and withdrew **667 TWh** over the winter. The single heaviest month took **201 TWh** out — an average delivery rate of about **270 GW**, sustained for a month. That is the physical answer to "what replenishes it": summer pipeline and LNG imports, parked underground, released again from November.

![Storage cycle](results/storage_cycle.png)

| Country | Seasonal swing (TWh) | Storage withdrawal (TWh) | Cover | Peak withdrawal rate (GW) |
|---|---|---|---|---|
| Germany | 146.1 | 172.0 | 118% | 73.7 |
| Italy | 112.4 | 114.9 | 102% | 41.8 |
| France | 88.4 | 89.5 | 101% | 43.0 |
| Netherlands | 79.9 | 83.9 | 105% | 34.7 |
| Austria | 49.8 | 57.4 | 115% | 21.6 |
| Turkiye | 37.4 | 35.6 | 95% | 20.9 |
| Hungary | 27.7 | 31.4 | 113% | 13.9 |
| Czechia | 27.1 | 26.3 | 97% | 9.9 |
| Poland | 23.6 | 24.9 | 106% | 11.5 |
| Romania | 23.3 | 22.3 | 96% | 9.1 |
| Spain | 16.3 | 16.3 | 100% | 8.7 |
| Slovakia | 15.1 | 20.9 | 139% | 8.6 |
| Latvia | 8.4 | 10.5 | 125% | 4.6 |
| Belgium | 6.3 | 6.2 | 99% | 3.0 |
| Lithuania | 5.3 | 5.2 | 99% | 1.8 |
| Denmark | 4.3 | 5.1 | 120% | 2.3 |

![Storage cover](results/storage_cover.png)

**Conclusion.** In every country that owns storage, withdrawal lands within roughly ±15% of its own seasonal swing — storage is not a supplement to the winter, it *is* the winter. The bottleneck is therefore not the annual volume but two other things:

1. **Deliverability.** Germany alone must pull ~74 GW out of the ground in the peak month. A cavern field that holds the energy but cannot deliver the rate is useless in a cold snap.

2. **Countries with no storage at all.** Ireland (55 TWh/y), Georgia (34 TWh/y), Slovenia (10 TWh/y), Luxembourg (7 TWh/y), Estonia (4 TWh/y) consume gas but hold none of it underground. Their entire winter swing has to arrive in real time through a pipeline or an LNG terminal — so an interconnector outage there is immediately a supply event, not a price event.

## 6. The network — where the gas physically has to squeeze through

Source: **ENTSOG Transparency Platform** (`transparency.entsog.eu/api/v1`, open, no API key), gas day **2026-01-15**, cached in `data/raw/entsog_de_border_2026-01-15.json`. Utilisation = physical flow / firm technical capacity at the same point-direction.

| Border point | Operator | Corridor | Flow (GWh/d) | Firm capacity (GWh/d) | Utilisation | Status |
|---|---|---|---|---|---|---|
| Dornum / NETRA | OGE | NO->DE | 589 | 423 | 139% | above firm — running on non-firm capacity |
| Emden (EPT1) | OGE | NO->DE | 426 | 263 | 162% | above firm — running on non-firm capacity |
| Mallnow | GASCADE | DE->PL | 223 | 259 | 86% | at the firm limit |
| VIP Oberkappel | OGE | DE->AT | 217 | 215 | 101% | above firm — running on non-firm capacity |
| Uberackern ABG | OGE | DE->AT | 68 | 0 | — | no firm capacity published |
| VIP Waidhaus | OGE | DE->CZ | 0 | 0 | — | idle |

![Network map](results/network_map.png)

![Corridors](results/network_corridors.png)

**Conclusion.** On a peak winter day Germany pulls **1015 GWh/d** in from Norway through just two point clusters, Emden and Dornum, and both are running *above* their published firm capacity — 162% and 139% respectively. That extra volume is interruptible or additional capacity: contractually curtailable, not guaranteed. The single-corridor concentration is the bottleneck, not the pipe diameter.

Meanwhile **VIP Waidhaus sits at zero** — the Czech route that used to carry Russian gas into Bavaria is idle, and **Mallnow now runs west-to-east at 86% of firm**, exporting to Poland instead of importing from it. The map of 2019 has been redrawn: the load has moved from the eastern border to the North Sea coast, and the eastern points are now transit and reverse-flow assets.

## 7. What this means for storage

- The swing above a flat baseline is what storage and flexible supply must cover. For the EU it is on the order of **hundreds of TWh every year** — that is the job underground storage does today.
- Batteries do not touch this: the entire EU grid-battery fleet is ~0.04 TWh, four orders of magnitude below the seasonal task.
- Repurposing the gas storage fleet to hydrogen cuts its stored energy ~4.2x (1,100 TWh → 260 TWh), because a cavern holds a **volume**, not an energy.

## 8. What is NOT in this repo yet (honest gaps)

- **Facility-level storage** — this uses national stock changes, not individual site fill levels and injection/withdrawal curves. GIE AGSI+ publishes those, but its API needs a registered key.
- **The rest of Europe's border points** — the ENTSOG client in `src/entsog.py` fetches any country pair live; the bundled snapshot covers Germany's borders with NO, PL, CZ, AT and CH. Run it with a network connection to extend to NL, BE, FR, DK and the rest of the EU.
- **Electricity grid congestion** — ENTSO-E's Transparency Platform needs a free registered token: register on the site, then email transparency@entsoe.eu for RESTful API access.
- **Named sites** — no open pan-European dataset ties an individual plant or data centre to metered demand, so branch-level is as granular as public data honestly goes.

