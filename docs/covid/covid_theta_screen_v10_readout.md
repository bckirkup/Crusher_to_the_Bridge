# COVID Theta screen v10 — readout: the v9 Θ surface is seed-for-seed stable across QUAR-EXEMPT-01 + REINFECT-01

> **Status:** Findings (2026-09-21), full surface. Campaign `covid_theta_screen_v10`,
> declared in `picard_framework/runs/covid_theta_screen_v10_design.json` (#639,
> `docs/ledger/THETA-SCREEN-V10.md`). **All 200 cells have run**: the
> pre-committed canary (Θ 1e9 × 20 seeds, indices 160–179, §1–§5) first,
> then the remaining 180 after the user's decision (§6). §1–§5 are the canary
> readout as written before the rest ran and are left as they were. Run on
> AWS Batch at `main` = `a9b4f1f` (engine identical to `d62f10d`: the only
> diff is the v10 design file), image `picard-campaign:theta-v10-a9b4f1f`
> (`sha256:325dde73ac57039dee318f451700fd1886fa3c35d60f880d060ea93146b4d3b1`,
> the campaign base layered with `deploy/aws/Dockerfile.covid_hull`), job
> definition `picard-covid-boarding-screen:12`, canary child
> `6555b89d-f44f-420e-b607-41ebd239c1b9` (index 160, seed 20200205) then
> array `cf4865ef-2a4b-48ef-bf31-6830d062fd0c` (size 19, indices 161–179) on
> `picard-campaign-queue`. 20 of 20 children SUCCEEDED, zero failures,
> ~20 min per cell. Cells:
> `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v10/a9b4f1f/cells/`.
> Merge: `python3 tools/fit_covid_theta.py screen --design
> picard_framework/runs/covid_theta_screen_v10_design.json --cells <cells>
> --allow-partial --out <surface json>`, then
> `python3 tools/covid_theta_screen_csv.py <surface json> --out
> docs/covid/covid_theta_screen_v10_canary_surface.csv --cells <cells>
> --parent-cells <v9 Θ 1e9 age 3.3 cells> --pairs-out
> docs/covid/covid_theta_screen_v10_canary_pairs.csv`.
> No Theta is claimed here; nothing below may be quoted as a fit. The
> remaining 180 cells ran as arrays `a83a2b5b-1b73-475c-8857-71ef9d0cbeae`
> (size 160, offsets 0–159) and `dfe080e6-b83b-42d9-9177-1c3991e99f85` (size
> 20, offsets 180–199) on the same job definition, digest and prefix; the
> full-surface artefacts are `docs/covid/covid_theta_screen_v10_surface.csv`
> and `docs/covid/covid_theta_screen_v10_pairs.csv` (merge without
> `--allow-partial`, v9 parents from `campaign/covid_theta_screen_v9/cells/`).

Every figure below is measured at `a9b4f1f` inside the campaign image, seeds
`20200205 + k`, k = 0..19, `diamond_princess_2020`, one declared import,
declared index onset day −1, infection age 3.3 d (measured inert in v9). §1–§3
are measurements; §4 separates measured from inferred; §5 is the decision the
design file reserved for the user.

## 1. Preflight and the pre-committed gate

- Dry-run array size 200 (design); v9 still 600.
- Job definition `picard-covid-boarding-screen:11` was registered against the
  bare campaign image by mistake (no `deploy/aws/` layer; the role cannot
  deregister). It was never used; revision 12 pins the layered digest above.
- In-image local smoke of the shared-seed cell (index 160, Θ 1e9, seed
  20200205): `infections_total` 3458, `attack_rate` 0.9318,
  `index_onset_day` −1.0, `index_shedding_at_day0` true, no `arm_id`, payload
  contract intact (`cell`, `observables`, `onset_curve`, `attack_rate`,
  `infections_total`, `vsp_reported_case_fraction_max`, …).
- AWS canary child at the same cell: 3458 / 0.9318 — **byte-identical to the
  local in-image run and to the QUAR-ATTR-V2 `A0_declared` cell of record at
  `d62f10d` (3458 / 0.9318)**. The screen payload has no
  before/during/after window fields, so the 3414–43–1 split is not re-read
  here; the distinct-host totals it accompanies are.
- Sub-block submission: the entrypoint resolved
  `AWS_BATCH_JOB_ARRAY_INDEX` directly and Batch drops a user-supplied value
  of that reserved name, so the canary ran through a `python3 -c` wrapper
  (`runpy` over the unchanged entrypoint) adding an `INDEX_OFFSET` of 160/161.
  The entrypoint now has `--index-offset` for the same purpose; it is in the
  tree, not in the image that ran.

Gate checks from the design file:

| check | result |
|---|---|
| `index_onset_day == -1.0` and `index_shedding_at_day0` in every cell | 20/20 |
| `invalid_reason` | null in 20/20 |
| shared-seed reproduction of the `d62f10d` record | exact |
| child failure rate | 0/20 |
| any cell with episode ≥ 2 | the screen payload carries no episode field (as QUAR-ATTR-V2 readout §6 notes); not readable here, not asserted |
| Θ 1e9 takeoff where v9 showed none or vice versa, outside 2/20 | none — same 12 seeds take off |

## 2. The Θ 1e9 row, v9 vs v10

Takeoff is `recorded_onsets >= 10` (design). v9 at `0fb186b`
(`docs/covid/covid_theta_screen_v9_surface.csv`, age 3.3 row); v10 at
`a9b4f1f`.

| quantity | v9 (`0fb186b`) | v10 (`a9b4f1f`) |
|---|---|---|
| takeoff fraction | 0.60 (12/20) | 0.60 (12/20, same seeds) |
| recorded onsets median (all 20) | 1,008 | 1,004 |
| recorded onsets median given takeoff | 3,103 | 2,991.5 |
| recorded onsets p10 / p90 | 0 / 3,323 | 0 / 3,282 |
| attack q10 / q50 / q90 | 0.0002 / 0.315 / 0.924 | 0.0002 / 0.310 / 0.923 |
| attack median given takeoff | 0.865 | 0.865 |
| before_share median | 0.208 | 0.214 |
| campaign positives p10 / p90 | 0 / 628.5 | 0 / 646.9 |
| campaign specimens median | 3,028.5 | 3,028.5 |
| vsp_threshold_crossing_fraction | 0.60 | 0.60 |
| onset_mass_near_target | 0.00 | 0.00 |
| index_geometry_ok | yes | yes |
| covid.T1 | pass (interval-span) | pass (interval-span) |
| covid.T3 | fail | pass (see §3) |

Per-seed onsets, sorted — v9:
`0 0 0 1 1 1 1 2 969 982 1034 1474 2330 3103 3103 3187 3277 3318 3368 3379`;
v10: `0 0 0 1 1 1 1 2 976 982 1026 1443 2367 2879 3104 3147 3169 3278 3315 3318`.

The handoff's gate text quotes v9's Θ 1e9 takeoff as 0.85; the v9 surface CSV
and readout table give 0.60 at 1e9 (0.85 is the 1e10 row). The comparison
above uses the CSV.

## 3. Paired by seed

`docs/covid/covid_theta_screen_v10_canary_pairs.csv` has all 20 rows. The
eight extinct seeds (20200206/07/09/10/11/13/15/17) are identical in
`infections_total`, `attack_rate` and `recorded_onsets` between v9 and v10.
Over the twelve takeoff seeds `infections_total` moves by −23 … +69 hosts
(|Δ| ≤ 2.1% of the cell) and `recorded_onsets` by −224 … +37; the largest
onset move is the saturated seed 20200205 (3,103 → 2,879), the cell REINFECT-01
was diagnosed on. No seed changes takeoff class; no cell crosses the
`onset_mass_near_target` window [98.5, 394].

The `covid.T3` verdict flips fail → pass only because the p90 of campaign
positives moves 628.5 → 646.9 across the 634 target while p10 stays 0. It is
the same bimodal interval-span the v9 readout §3 documented for `covid.T1`: a
pass produced by an interval running from extinct seeds to burning seeds, with
no seed near the target. It is reported, not selected on, and it changes no
conclusion.

## 4. Measured, inferred, hypothesis

**Measured** (`a9b4f1f`, 20 cells, seeds above): everything in §1–§3.

**Inferred**: QUAR-EXEMPT-01 and REINFECT-01 together leave the Θ 1e9 row of
the screen surface materially unchanged — same takeoff set, distinct-host
totals within 2%, conditional medians within 4%. This is consistent with the
QUAR-ATTR-V2 finding that the reinfection inflation lived in the window counts
(973 → 43 during quarantine at the saturated seed) and not in
`infections_total` (0.314 → 0.310). The screen surface never carried window
counts, so it had little to lose.

**Hypothesis** (one Θ, not yet measured elsewhere): the other nine v9 rows
will also hold seed-for-seed within the 2/20 band. The v9 structural
readings — extinction-or-burn at every decade, Θ moving takeoff probability
rather than size, no near-critical band for one declared import — would then
stand on the repaired engine. That is what the remaining 180 cells test, and
it is the only reason to run them.

## 5. Decision reserved for the user

The design file stops here. Options:

- **Run the remaining 180 cells** (~200 cells × ~20 min on the Spot queue;
  240 children ran in ~30 min wall clock in QUAR-ATTR-V2, so expect
  ≤ 1 h): the same job definition `:12`, same prefix, offsets 0–159 and
  180–199. This converts §4's hypothesis into a measurement and lets the v9
  verdicts be formally superseded or confirmed per Θ.
- **Do not run them** and accept the v9 surface as the Θ locator on the
  repaired engine on the strength of the Θ 1e9 row alone, moving directly to
  the QUAR-ATTR-V2 follow-up (a crew-confinement SOP variant) or to the
  pre-quarantine magnitude question.

The readout's own reading: the canary gives no reason to expect surprises and
the cost is one hour; the case for running the rest is completeness of the
record, not an open question at Θ 1e9.

## 6. The full surface, v9 vs v10 (200 of 200 cells)

The user chose to run the rest. 180/180 children SUCCEEDED (0/200 failures
over the campaign); S3 holds exactly one payload per (Θ, seed). Every cell:
`index_onset_day` −1.0, `index_shedding_at_day0` true, `invalid_reason`
null; `index_geometry_ok` true on all ten rows.

| Θ | takeoff v9 → v10 | median recorded onsets | attack q90 | T1/T3 | `infections_total` identical to v9 |
|---|---|---|---|---|---|
| 1e1 | 0.00 → 0.00 | 0 → 0 | 0.000 → 0.000 | F/F → F/F | 20/20 |
| 1e2 | 0.00 → 0.00 | 0 → 0 | 0.000 → 0.000 | F/F → F/F | 20/20 |
| 1e3 | 0.00 → 0.00 | 0 → 0 | 0.000 → 0.000 | F/F → F/F | 20/20 |
| 1e4 | 0.10 → 0.10 | 0 → 0 | 0.001 → 0.001 | F/F → F/F | 20/20 |
| 1e5 | 0.15 → 0.15 | 0 → 0 | 0.115 → 0.115 | F/F → F/F | 17/20 |
| 1e6 | 0.10 → 0.10 | 0 → 0 | 0.047 → 0.046 | F/F → F/F | 18/20 |
| 1e7 | 0.20 → 0.20 | 1 → 1 | 0.327 → 0.322 | F/F → F/F | 16/20 |
| 1e8 | 0.35 → 0.35 | 1.5 → 1.5 | 0.804 → 0.822 | F/F → F/F | 13/20 |
| 1e9 | 0.60 → 0.60 | 1008 → 1004 | 0.924 → 0.923 | T/F → T/T | 8/20 |
| 1e10 | 0.90 → 0.90 | 3381.5 → 3354 | 0.957 → 0.955 | F/F → F/F | 2/20 |

**Measured.** Takeoff fraction is identical at every decade and **no seed of
200 changes takeoff class** (the declared band was 2/20 per row).
`onset_mass_near_target` is identical to v9 on every row (0.05 at 1e4 and
1e8, 0.10 at 1e5, 0 elsewhere): still no decade puts more than two seeds
near 197 onsets. `covid.T1` passes only at Θ 1e9 in both versions; `covid.T3`
fails everywhere except the Θ 1e9 flip of §2. `infections_total` is
byte-identical to v9 on 154/200 cells: all 80 at Θ ≤ 1e4, and every extinct
seed at every Θ but one (Θ 1e8, seed 20200224, 48 → 46 hosts). Among takeoff
seeds the two largest paired moves are Θ 1e5 seed 20200205, 1110 → 950 —
which is the QUAR-ATTR-V2 `A0_declared` Θ 1e5 cell of record (950 / 0.2560)
reproduced exactly — and Θ 1e7 seed 20200214, 457 → 621; every other
takeoff seed is within 7% of its v9 total, and row medians at 1e9 and 1e10
move ≤ 1%.

**Inferred.** QUAR-EXEMPT-01 and REINFECT-01 do not move the screen surface.
The v9 structural readings — extinction-or-burn at every decade, Θ moving the
probability of takeoff rather than the size of the burn, no near-critical band
for one declared import — hold on the repaired engine and are now measured
there, not carried from `0fb186b`. The v10 CSV supersedes the v9 CSV as the
surface of record; the v9 rows are confirmed, not withdrawn.

**Hypothesis (unchanged, now the blocker).** Θ is not the parameter that
produces onset mass near 197. The criterion question — T1 trajectory with
import geometry as the next axis, versus takeoff probability against covid.H3
with onsets conditional on takeoff — is what stands between this surface and a
calibration, and it must be declared in a design file before any cell runs.

**Not read here.** The screen payload carries no quarantine-window or episode
fields, so the 3414–43–1 split and "no episode ≥ 2" are not asserted from
these 200 cells; they rest on QUAR-ATTR-V2 and REINFECT-01's own tests.
