# Insight memo — Europe's seasonal storage as gas gives way to hydrogen

*Figures are produced directly from the model (`python src/analysis.py`).*

## Situation
With wind and solar at 70% of annual electricity demand,
Europe must carry a **seasonal swing of 238 TWh** and deliver
**85 GW** at the winter peak, on top of a flat
2.2 TWh/day of other dispatchable supply. Today's
underground gas storage holds ~1,100 TWh — roughly
5x that swing.

## Key findings
1. **A cavern stores a volume, not an energy.** Hydrogen carries only
   ~0.30 of methane's energy per cubic metre, so repurposing the
   fleet cuts stored energy ~4.2x — from 1,100 TWh
   to **260 TWh**.
2. **Comfort becomes a thin margin.** Against the same seasonal swing, the gas fleet is
   22% utilised; on hydrogen it is
   **92%** — and at about **90% wind and solar** the repurposed fleet no longer covers the swing.
3. **Volume binds before deliverability.** The hydrogen fleet uses
   34% of its withdrawal capability but
   92% of its working energy: the scarce
   resource is subsurface working volume, not injection/withdrawal rate.
4. **Salt caverns meet policy, not the system.** Salt caverns give
   49 TWh — enough for the 45 TWh
   Europe currently targets — but a fully decarbonised winter needs the depleted fields
   (171 TWh), which carry the harder technical questions.
5. **Batteries cannot close a seasonal gap.** On the flexibility ladder only underground storage
   carries more than a month of demand; batteries cover hours and pumped hydro days.
6. **The seasonal swing is real, measured — and it grew.** On Eurostat monthly data,
   German gas consumption ran at a peak-to-trough ratio of 2.7 in 2020 and
   3.4 in 2024, averaging 3.5 (winter/summer 2.9).
   About **19% of annual consumption sits above a flat baseline** — that is the
   share the storage system has to carry every single year.

## Recommendation
Treat seasonal adequacy as a **subsurface working-volume problem**. Qualify depleted fields and
aquifers for hydrogen early (cushion gas, purity, microbial activity, deliverability), reserve
salt caverns for fast-cycling duty, and size electrolysis and injection to refill the store over
summer. Track working volume and deliverability as two separate constraints — a store with
enough energy can still fail on peak days.

---
*Illustrative, publicly-anchored inputs (see SOURCES.md); a transparent adequacy model, not a
market simulation. Decision support, not investment advice.*
