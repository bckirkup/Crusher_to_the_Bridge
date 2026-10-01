# COVID-HAND-AB-01 readout — three-arm hand-line attribution on the DP record leg

Measured at `1c94de2d` (cells) / audit fix `abcfa6db` (PR #817),
AWS Batch job-def `picard-covid-boarding-screen:43`
(image `picard-campaign@sha256:5f4485e5…`), arrays `e503114d` (cells
0–57) + `df330100` (cells 58–59 — the jobdef command map lacks
`--index-offset`, so the resume's `index_offset` parameter was silently
dropped and the tail pair was re-submitted via `--container-overrides`),
60/60 cells SUCCEEDED, 0 audit failures. Index-geometry invariant held
on every cell (`index_onset_day == -1.0`, `index_shedding_at_day0`
true). Cells at
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_hand_carriage01/cells/`.
The two prior-mechanism canary cells under
`campaign/covid_hand_ab_v1/` stand as the recorded baseline — labelled by
their `delivery.hand_reservoir_mode` echo, not voided.

## Arm rows (Θ 2.37e11, seeds 20200205–20200224, declared replay)

| arm | takeoff | recorded_onsets med [q05, q95] | infections_total med | before_share med | during med | during share |
|-----|---------|------------------------------|----------------------|------------------|------------|--------------|
| hygiene_cycle | 17/20 | 3.37e3 [2.00e3, 3.54e3] | 3.57e3 | 0.885 | 39 | 0.0137 |
| wash_reuptake | 16/20 | 3.38e3 [2.32e3, 3.56e3] | 3.57e3 | 0.821 | 86 | 0.0241 |
| spike_decay   | 16/20 | 3.38e3 [2.32e3, 3.56e3] | 3.57e3 | 0.821 | 86 | 0.0241 |

Record legs for contrast: 197 recorded onsets, before_share 0.173. All
three arms burn at ~96% attack — consistent with every axis measured at
this Θ to date.

## Baseline degeneracy (measured)

`wash_reuptake` and `spike_decay` cells are **byte-identical on all 20
seeds** — every scored field matches; only `cell`, `arm_id`, and the
`delivery.hand_reservoir_mode` echo differ. The RESERVOIR-01-vs-v13
contrast the design was built to decompose does not exist on this
scenario: the two baselines differ only on the stool-event path, which
the SARS-CoV-2 arm never exercises. The hand line has exactly one
effective baseline on `diamond_princess_2020`.

## Seed-paired deltas vs the degenerate baseline (20 pairs each)

| pair | Δ recorded_onsets med [q05, q95] | Δ infections_total med | Δ before_share med | takeoff flips |
|------|----------------------------------|------------------------|--------------------|---------------|
| spike_decay − hygiene_cycle | +27 [−3530, +3540] | +10 [−3572, +3576] | +0.057 [−0.006, +0.284] | 5/20 |
| wash_reuptake − hygiene_cycle | +27 [−3530, +3540] | +10 [−3572, +3576] | +0.057 [−0.006, +0.284] | 5/20 |

During-quarantine paired delta (hygiene_cycle − baseline): median −15.5,
range [−1297, +1393]. `hygiene_cycle` draws extra RNG (routine-wash and
wet-window draws the baselines lack), so every seeded cell re-rolls near
the takeoff boundary — the ±3.5e3 paired spread and the 5/20 flips are
the stream-reorder band, inside which all three medians sit.

## Route decomposition (pooled, all 60 cells)

During-quarantine infections by route: droplet 15,617, hvac_airborne 82,
direct_contact 2, **fomite 0**, all other routes 0. The hand reservoir
— repaired or not — is not the during-quarantine carrier on this hull:
the confinement window is ~99.5% droplet (cabin-mate/ring-side per
ROUTE-ATTR-V1), and the hand→face channel wins zero acquisitions at this
Θ on this scenario.

## Verdict — `hand_line_replay_neutral`

Under the design's frozen criterion the arm effect does not count: the
baseline's same-seed spread is 0 by degeneracy, and every arm delta sits
inside the stream-reorder band the criterion was written against. The
repaired hand mechanism (protected compartment + own-environment pool,
`1c94de2d`) is **replay-neutral on the record leg** — directionally the
arm reads slightly *more* burn (+27 rec med, +0.057 bshr), not the
suppression the report-immediately clause watched for. The DP replay
residual is unchanged: the burn is airborne, and hand-mediated
transmission contributes no measured acquisition on this scenario.

## Consequence for the v14 ladder

The canary's job was to decide whether the 3,600-cell
`covid_theta_screen_v14` stage-1 lattice (hygiene_cycle × spike_decay,
200 seeds × 9 Θ) measures anything its arm pairing can see. On this
readout the two arms are replay-neutral at the one measured Θ and the
spike_decay baseline is degenerate on this scenario — so the pairing's
marginal information at stage-2 coordinates is nil. Options for stage 1
(open decision, owner's call):

- run v14 verbatim (pairing kept for bit-comparable contrast vs v13
  cells, at 2× the cell count);
- run v14 single-arm (hygiene_cycle only, 1,800 cells) — same Θ surface
  information at half the compute;
- skip the re-screen — the canary's neutrality plus v13's measured
  surface argues the hand line doesn't change the admissible set.
