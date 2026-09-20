# QUAR-ATTR-V1
**Date:** 2026-09-20
**Commit:** 861a0b9
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 861a0b9

## Hypothesis

The Diamond Princess outbreak in the model keeps growing through the enforced
quarantine (day 16 on) because one identifiable transmission channel — exempt
crew, cross-zone HVAC pool transport, or meal-table near-field air — carries
infections into the confined population; removing that channel on matched
seeds should cut `infections_during_quarantine` by half or more
(`picard_framework/runs/covid_quarantine_attribution_v1_design.json`, six
arms × two Θ × 20 seeds, criterion frozen before any cell ran).

## Evidence for

- Every override reached the engine (witness fields in 240/240 cells; A5
  reads zero droplet and zero `hvac_airborne` events in every cell). Canary
  reproduces QUAR-EXEMPT-01's HEAD figures exactly.
- On *first* infections during quarantine (event ledger, post-hoc diagnostic,
  same medians and thresholds), confining the crew (A1) cuts the conditional
  median 825.5 → 198.5 at Θ 1e9 (n = 12) and 393 → 102 at Θ 1e5 (n = 3);
  removing pool transport (A2) cuts 351.5 → 123 at 1e9 (n = 8); both together
  (A4) 351.5 → 52.5. Removing near-field air (A3) does not reduce it at either
  Θ (+14%, −49%/n = 3 disagree only at 1e5 where n is 3).
- Removing all shared air (A5) collapses takeoff (0/20 at 1e5, 1/20 at 1e9,
  fomite-only, 271 infections all crew).

## Evidence against

- On the **frozen** measure, no channel is load-bearing: at Θ 1e9 (n = 8–12)
  A1 −21% (indeterminate), A2 −16% and A3 +3% (non-load-bearing), A4 −23%
  (indeterminate); A5 has one overlapping seed and no verdict. At Θ 1e5 all
  all-seed medians are 0 (17/20 seeds extinct) and n ≤ 3.
- The frozen measure counts reinfections (REINFECT-01): 32% of the Θ 1e9
  `A0` during-window count, 96% in the saturated seed `20200205`. The
  criterion's verdicts are recorded as its literal output and are not read
  as channel attribution.
- Whole-voyage attack rate is arm-invariant once a seed takes off (Θ 1e9
  conditional median 0.83–0.91 across A0–A4; 2,060 of 3,711 infected before
  day 16). The quarantine leak is not where the magnitude mismatch lives.
- Pool transport moves takeoff probability (12/20 → 9/20 at 1e9), not
  conditional size — the same lever v9 found for Θ.

## PRs landed

- #633 — design, arm wiring, `QuarantineAttributionLedger`, QUAR-EXEMPT-01
  (merged as `861a0b9`; campaign image built from it).
- This entry's PR — readout, surface CSV, `tools/covid_attribution_readout.py`,
  `tools/covid_attribution_timing_probe.py`, REINFECT-01, open-ledger update.

## AWS jobs

- Canary child `5a18f6fe-68b4-45c3-b230-da6154a351ba` (A0, Θ 1e5, seed
  `20200205`), SUCCEEDED, 17 min container time.
- Array `f3e71e02-1231-46dd-a0b2-8e173fd6df64` (`picard-attribution-v1-861a0b9`),
  240/240 SUCCEEDED, 0 failed, 0 Spot retries, 29 min wall clock,
  `picard-covid-boarding-screen:8`, image
  `picard-campaign:attribution-v1-861a0b9`
  `sha256:d38988416a971a5b7f0dadf43f5bedb29638fbbc64ad042d97905589c8ccea31`.
- Nothing is running.

## S3 prefix

`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_quarantine_attribution_v1/cells/`
(240 objects, one per (Θ, arm, seed)). Per-cell CSV committed at
`docs/covid/covid_quarantine_attribution_v1_surface.csv`.

## Prior results now void

- Any `infections_before/during/after_quarantine` figure in any COVID payload
  read as hosts infected in that window (REINFECT-01), including the 678/455/38
  split quoted for the QUAR-EXEMPT-01 canary and the "continues through
  enforced quarantine" reading in `covid_theta_handoff_2026_09_19.md` §12 /
  v9 readout §6 at the truth-channel scale.
- The open-ledger item "795 repeat infection events … lifecycle not yet
  traced": traced, see REINFECT-01.

## Prior results that remain valid

- THETA-SCREEN-V9 at `0fb186b` and QUAR-EXEMPT-01 at `008c8c8`:
  `infections_total`, `attack_rate`, `recorded_onsets` (distinct hosts / first
  onsets), the geometry invariant, the inert age axis, the v9 "Θ moves takeoff
  not size" reading.
- The A5 zero-air proof and the route/zone first-infection breakdowns of this
  campaign.
- No Θ is admissible or fitted; covid.T1/T3 not scored here.

## Open decision (one)

Fix REINFECT-01 before any further COVID campaign, or re-run the attribution
on the current engine with a first-infection criterion? Recommendation: fix
first — the channel that reinfects a recovered host is the same shared-air
dose that infects a naive one, so any attribution on the unrepaired engine
measures both at once. Successor gate: paired canary cell (A0, Θ 1e5 and
1e9, seed `20200205`) inside the campaign image before and after the fix,
then stop and report.
