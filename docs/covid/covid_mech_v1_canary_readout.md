# COVID-RINGCAP-V1 + COVID-SUSCPOOL-V1 — canary read-out

**Status: canary measured (anchor row only).** The full replay arrays
(240 + 480 cells) and the coarse fleet designs (500 + 1000 cells) are
NOT submitted; this file records the declared canary stage only.

Engine commit `472cdf13` (PR #767). Image
`picard-campaign:covid-mech-v1-472cdf13`, two-layer build (campaign +
`Dockerfile.covid_hull`, ENTRYPOINT `python3`), digest
`sha256:10902239ffc1e1650ffa1d93d66d2146ab743040d902db9b81c1a5e971034b89`.
Job definition `picard-covid-boarding-screen:31` (digest-pinned).
Ring canary: Batch job `5a815be5-3804-4eaf-9c53-4356d6c36db3` (40
children, indices 0-39 = Theta1e9 anchor row, both arms). Susc-pool
canary: `205ca152-3ea8-4f67-a979-b1a9506abfd8` (80 children, indices
0-79 = anchor row, four arms). Cells under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/<design>/472cdf13/cells/`.
120/120 children SUCCEEDED; 0 failures (0% < the 5% trigger).

## Flag-landed evidence

Cell payloads carry no spec dump, so the declared wiring check ran as
paired-seed divergence plus the engine-level unit tests and the
local run-spec smoke (the override lands in `prepare_cell_run_spec`
exactly on the arm that declares it).

- ring: 9/20 seed pairs differ cap_on vs rings_first (same seed, same
  point). Largest: seed 20200210, 14 -> 880 recorded onsets. The 11
  identical pairs are mostly extinct cells (0 onsets) where the ring
  spend cannot matter.
- susc: per-arm max recorded_onsets over the anchor row falls
  monotonically in fraction — declared 3123, f025 2400, f050 1477,
  f075 629 — the mechanism's signature direction.
- `declared` arm reproduces the v13/cap_on anchor row exactly (q05
  11.75, q95 3087.25, med 2412.5, before_share 0.373) — the baseline
  arm is bit-comparable, so arm deltas attribute to the overrides,
  not stream drift.

## Audit invariant + non-degeneracy

`index_geometry_pass_fraction` = 1.0 on every arm row in both canaries.
Every arm has nonzero takeoff mass at the anchor. No cell row is
degenerate.

## Conditional clause at the Theta1e9 anchor row

Frozen clause (v13 stage-2, verbatim): takeoff seeds
(recorded_onsets >= 10) q05-q95 contains 197 AND median before_share
within 0.10 of 0.173; >=5 takeoff seeds required.

| arm | takeoff n | q05 | q95 | med onsets | before_share med | clause |
|-----|-----------|-----|-----|------------|------------------|--------|
| ring cap_on     | 6 | 11.75  | 3087.25 | 2412.5 | 0.373 | FAIL |
| ring rings_first| 6 | 133.25 | 3146.0  | 1349.0 | 0.128 | **PASS** |
| susc declared   | 6 | 11.75  | 3087.25 | 2412.5 | 0.373 | FAIL |
| susc f025       | 7 | 441.2  | 2338.2  | 1984.0 | 0.176 | FAIL (floor above 197) |
| susc f050       | 5 | 80.6   | 1466.0  | 339.0  | 0.213 | **PASS** |
| susc f075       | 3 | 66.6   | 610.2   | 441.0  | 0.533 | n/a — below the >=5 takeoff floor |

## Read

Both mechanisms move the anchor row in the predicted direction:
bounding fixed-ring spend and bounding the susceptible pool each pull
before_share toward the 0.173 window while retaining takeoff mass. The
anchor row is the boundary endpoint — the declared trigger list
includes "clause PASS confined to a boundary endpoint", and v13's
anchor also passed there alone. Whether the PASS survives at the
admissible-Theta rows ({1.78e11..5.62e11}) is exactly what the full
arrays answer; this canary cannot rule the trigger in or out.

Canary-stage observations, not triggers:

- f075 shows only 3 takeoff seeds at the anchor (3 < 5): at this Theta
  a 75% non-susceptible draw suppresses ignition on most seeds. The
  trigger reads "every f075 row" — one row measured so far.
- f025's clause fails on the HIGH side (q05 floor 441 > 197): the
  mechanism moved mass but not enough — consistent with the declared
  response-curve reading (f050 is between f025-overshoot and
  f075-suppression).

## Non-goals held

No shipped-default change (flag stays default-off; fractions are arm
labels, not adopted constants); no anchor fitting; no new seeds or
cell families; naval platforms untouched; no dose-ledger change.
