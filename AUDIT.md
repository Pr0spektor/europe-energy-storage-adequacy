# Methodology audit — European gas storage adequacy

A reviewer-grade pass over the model: what holds, what does not, what was changed in this
pass, and what a critical reader should discount. Read alongside `results/stress_days.png`
and `SOURCES.md`.

## Findings

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | High | The peak-day flexibility split adds **two maxima taken on different days**: the country's peak storage withdrawal (AGSI+) and its peak LNG send-out (ALSI). `max(a) + max(b)` is an upper bound on any single day's total, so the split is a **capacity mix**, not an observed same-day flow. The README said LNG "arrived by ship" on the peak day, which the data cannot support. | **Wording fixed.** The claim now says capacity mix and points here. The arithmetic cannot be corrected from the bundled snapshot: it carries per-source peaks, not date-aligned daily series. Fixing it properly needs daily send-out and daily withdrawal on the same calendar, which the refresh tool can now collect. |
| 2 | High | The denominator excludes **pipeline imports**, which are the dominant supply source for Germany and much of Central Europe. A country can be 14% LNG by this metric and still be almost entirely dependent on one pipeline route. | **Open, and stated.** The metric measures the mix between the two *swing* sources (storage and LNG), not total supply security. It answers "what does this country have that can move on the day", not "where does its gas come from". |
| 3 | Medium | The stress test scales the observed peak day by 1.0/1.2/1.4 and assumes LNG send-out runs at its observed peak every day of the spell. Real send-out depends on cargo arrivals, which are lumpy and contested. | **Open.** The assumption is conservative in the country's favour on the LNG side, so the reported rate-bound days are, if anything, optimistic. Stated in `docs/`. |
| 4 | Medium | Withdrawal capacity is the operator-reported technical figure, not firm capacity. Countries that can physically withdraw above firm rights will look more resilient than their contractual position allows. | **Open.** The Germany/Norway point in the README (162% and 139% of firm capacity) is exactly this effect showing up on the import side; the same caveat applies to storage. |
| 5 | Medium | Country coverage is 18 countries plus an EU aggregate, chosen by data availability rather than by system relevance. | **Open.** Stated in `SOURCES.md`. A country omitted for missing data is not a country without risk. |
| 6 | Medium | The hydrogen repurposing figure was a point estimate at a 35% cushion share — a methane-derived number applied to a lighter, more mobile molecule. | **Fixed earlier in this pass.** `repurposed_energy_band` propagates the LHV and cushion ranges: 164–227 TWh (P10–P90, median 195) against the 260 TWh point. |
| 7 | Low | The bundled AGSI snapshot was dated and could age silently. | **Fixed.** `tools/refresh_snapshots.py` validates and writes a new dated file; a monthly workflow opens a PR and fails after 150 days without a refresh. |

## What a top-tier reviewer would still say

The structural argument — that volume, rate and duration are three different scarcities, and
that a cold snap converts a volume problem into a rate problem — is the strongest part of this
repository and it survives the audit. It is a genuinely useful reframing, and the RATE/VOLUME
split gives opposite remedies, which is what makes it operational rather than decorative.

What does not survive is any claim about *where the molecules came from*. Without date-aligned
daily send-out and withdrawal, finding 1 cannot be closed, and finding 2 means the metric
answers a narrower question than a reader will assume. Both are now stated in the README
rather than buried.

The gap to a top-five deliverable is the same as in the climate repository: no primary data
collection, no operator interviews, no reconciliation against actual curtailment events. The
model is auditable and the arithmetic is right; the evidence base is public data only.
