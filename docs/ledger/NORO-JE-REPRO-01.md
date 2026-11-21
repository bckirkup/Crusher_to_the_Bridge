# NORO-JE-REPRO-01
**Date:** 2026-11-21
**Commit:** 01156c62
**Pathogens:** norwalk_gi
**Status:** closed
**Measured at:** 90aa3ec2

The Paper-1 WP2 reproduction arm
(`campaigns/noro/paper1_joint_eval_01`, tier
`fl_je_repro_exp_solver01_station_continuous`, 16 cells on AWS Batch,
image `sha256:80884d60…f149a`) does not reproduce: seed by seed against
the `noro_supply_solver_screen_01` reference fingerprints of
`fl_exp_12d_sens_p06_paxv_station_lots_continuous`, 16/16 compared,
**0/16 identical**.

**Attribution (paired-seed, seed 939824, local replays):**

- Both arms reproduce their own archives bit-identically:
  `3500c205` + `tools/noro_diag/growth_chain_census.py` → the
  solver-screen fingerprint; `bf0ec168` + joint-eval `cell.py` → the
  joint-eval fingerprint. `parameters` differ only in
  `engine_git_sha`/`tier_id`, both excluded from the fingerprint.
- The solver-screen worker at `bf0ec168` produces the **joint-eval**
  fingerprint — the worker is irrelevant; the engine moved.
- Reverting `engines/`, `picard_framework/simulation/`, `orchestrator*`,
  `telemetry_buffer/fields.py` and the platform data to `3500c205`
  inside `bf0ec168` restores the reference fingerprint bit-identically —
  all divergence lives in that set.

**Named causes (each independently perturbs the trajectory):**

- `9661da33` (ROOM-AIR-01): ambient openings newly counted in the
  room-air ACH exchange map — expedition PoolDeck's ~73,400 m³/h
  open-deck exchange becomes a live removal path on the airborne pool.
- `63210391` (CONTAM-DUCT-EXCLUDE-01): PoolDeck `exchange_m3h`
  re-solved 73376.0 → 73493.4; reverting the value alone at `bf0ec168`
  yields a third trajectory.
- Recording-level only (no infection effect): the `room_air_witness`
  and `room_air_map_arm` summary fields added by the
  ROOM-AIR-PAIRED-VALIDATION-01 series, and a `total_pathogen_mass`
  float move at epoch 74 from the supply-structure / Contam-dedupe
  window.

**Mechanism:** identical through epoch 42; the PoolDeck dilution flips
one Bernoulli draw at epoch 43 (52 vs 53 infected), cascading after.
Systematic across seeds — every voyage has the PoolDeck opening —
consistent with 16/16.

**Verdict:** the divergence is engine drift across the campaign
boundary — reviewed, intended work merged between the reference run and
the freeze — not a joint-eval wiring defect and not an engine bug
(open-deck dilution behaving as designed). The reproduction arm's
premise — bit-identity while excluding `engine_git_sha` — cannot hold
across path-touching commits.

**Resolution (2026-11-21, measured):** the reference was re-baselined.
The 16 `exp_station_lots_continuous` cells re-ran on AWS Batch
(job `1ba4083f`, jobdef `picard-noro-supply-solver-screen-01:11`,
solver-screen worker `growth_chain_census.py`) on the retagged
`bf0ec168` image (`noro-supply-solver01-bf0@sha256:d88f2593`, the
`noro-explorer-recon01` build), archives at
`s3://…/campaign/noro_supply_solver_screen_01_bf0/` →
`out/noro/supply_solver_screen_01_bf0/` (the original `3500c205`
reference is preserved). All 16 children SUCCEEDED, every archive
stamps `engine_git_sha bf0ec168`, and **16/16 fingerprints are
identical** to the reproduction arm's — the repro arm reproduces once
the reference lives at the same engine commit.

Readout: `telemetry_buffer/noro_paper1_joint_eval_01/`; campaign
ledger: `campaigns/noro/paper1_joint_eval_01/LEDGER.md` "Full readout
(2026-11-21)".
