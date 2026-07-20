# Methods note

## Seasonal storage sizing
Storage fixes *timing*, not the energy *level*. From a daily residual-load profile
(demand − wind − solar) we net out a flat baseload equal to the mean residual — the
non-VRE generation and imports that carry the annual balance — leaving a profile that sums
to zero over the year. Integrating it gives the store's state-of-charge path; the **working
energy required is the peak-to-trough range** of that path, and the **withdrawal power
required is the largest single-day deficit**.

This is why a naive "total annual deficit" framing is wrong: it measures dispatchable energy,
not the seasonal cycle a store must carry.

## Two constraints, not one
An underground store can hold ample energy and still fail on peak days because it cannot
*deliver* fast enough. `binding_constraint()` reports utilisation of both working energy and
deliverability and names whichever binds first — the distinction that governs real UGS
operation.

## Hydrogen repurposing
A cavern or depleted field holds a volume. Hydrogen's volumetric energy is ~0.30 of methane's,
so the same fleet holds ~4x less energy once cushion gas and pressure limits are included
(published per-store estimates are used rather than the clean physics ratio alone).

## Observed seasonality
Computed from real Eurostat monthly consumption per country-year:
* `peak_to_trough` — highest month ÷ lowest month;
* `winter_summer` — mean(Dec–Feb) ÷ mean(Jun–Aug);
* `swing_share` — share of annual consumption sitting above a flat monthly baseline, i.e. the
  fraction that flexibility must carry.

## Limitations
Daily resolution, EU-aggregate; no transmission network, no hourly ramping, no price
formation, no demand response. Renewable profiles are smooth seasonal shapes calibrated to a
target VRE share, not reanalysis weather years. The model bounds the problem — it does not
simulate a market.
