# COVID-SEED-GEOM-01
**Date:** 2026-09-26
**Commit:** f09ebb1b
**Pathogens:** sars_cov2_resp
**Status:** declared

## What is being measured

The Diamond Princess takeoff cells seed one index case whose geometry is
declared, not drawn: `count` 1, `infection_age_days` 3.3 (the
`covid_sero_channel_v1` axis value; the scenario file carries 6.8),
`onset_day` −1.0, `departure_day` 5.0. Under a declared `onset_day` the
engine anchors shedding to onset, not to infection age
(`engines/infection_dynamics_bridge.py` `_shedding_age`; stamping in
`engines/initiation.py` `_apply_one_seed`), so `infection_age_days` is a
claimed null axis — the design file says so verbatim ("NOT an axis") but
the claim has never been measured end-to-end.

Two quantities:

1. **Ring burn.** Every non-seeded infection's acquisition epoch on a
   takeoff cell, split by whether it happened while the index was aboard
   (epoch < `departure_epoch` = 120). The bound separating index-direct
   from generation-2 acquisitions is the earliest epoch any secondary
   could emit, `max(infection_epoch, infection_epoch + onset −
   presymptomatic)` with the profile's presymptomatic window of 2.0 d —
   note this bound can clamp to the acquisition epoch itself when a
   secondary's incubation draw (min 0.5 d) is shorter than the window.
2. **Age-null check.** The same seeds re-run with
   `infection_age_days` rewritten to 6.8; the per-agent infection-epoch
   maps are compared bit-for-bit.

## Declared cells and statistics before running

- Cell: `covid_sero_channel_v1`, arm `D0_declared`, theta x1.0 =
  4.22e10, imports 1, voyage truncated at 168 epochs (7 d) — the burn is
  over by day ~5 and truncation is declared here rather than selected
  after the fact.
- Seeds: 20200205–20200209 (5 seeds).
- Statistics: per-seed acquisition count by voyage day; aboard-window
  count and dominant-route split; near-field (ring + cabin addback)
  share of droplet dose among aboard-window infections; per-seed
  `infected_total` at truncation.
- Contrast arms on the same seeds, declared before running:
  - `departure_day: 0` — the index leaves at embarkation; expected null
    secondary count (it validates that all onboard spread descends from
    the index; a nonzero count would mean another infection source).
  - `onset_day`/`departure_day` dropped, `infection_age_days` 0.0 — a
    just-infected index that stays aboard the whole voyage; measures how
    much of the burn is the declared mid-course onset geometry versus a
    fresh introduction. This arm moves RNG draws (the symptomatic-history
    stamp is skipped), so it is a mechanism contrast, not a null test.
  - `--age-pair 6.8` on 48 epochs: bit-identity of the infection map is
    the measured criterion for the null-axis claim.
- Tool: `tools/covid_seed_ring_burn.py` (read-only observer pattern, the
  same `QuarantineAttributionLedger`/`NearFieldShareLedger` instruments
  the route-attribution tool uses). Local CPython 3.12.13 — local numbers
  are mechanism reads, never Batch-comparable.

## What would change scope

- If the age pair is not bit-identical, `infection_age_days` is a live
  axis after all and every prior "age cancels" claim is void.
- If `departure_day: 0` still produces onboard infections, the seed is
  not the only infection source on this cell.
- If the aboard-window burn is O(10–100) rather than O(1–5) co-primaries,
  the "ring burn ≈ cluster of co-primaries" framing understates the
  geometry by an order of magnitude.
