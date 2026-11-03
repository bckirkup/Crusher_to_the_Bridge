# COVID-EMIT-LEVEL-01
**Date:** 2026-11-02
**Commit:** 7b7f0ea0
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** e2f761be

Item #30 (Edison task 2): the `sars_cov2_resp` arm's emission level was a
nasal titre offset by `dose_adjustment = 3.0`, a norovirus stool-mass
normalizer — the documented defect behind the profile's
mis-dimensioned `shedding_curve_log10` magnitude row and the
undeployable `airborne_emission_fraction` (register §§392, 405;
tranche 9 §1; tranche 27 §6). Resolution per Edison scope: a sourced
`environmental_release_log10_per_day` from measured exhaled viral
loads, `dose_adjustment` removed as this arm's fallback, deposit
verified against the declared measured bracket.

## Measurement

- **Level shipped:** `environmental_release_log10_per_day = 1.93` —
  peak emission 10^(9.0−1.93) = 1.19e7 RNA copies/day = 4.9e5
  copies/h, the geometric midpoint of the arm's declared Grade-B
  bracket [4.2e3, 5.8e7] copies/epoch (Alsved 2022 breathing floor,
  Zheng 2022 Omicron top; corroborating Coleman 2021, Ma 2021,
  Li 2021, Malik 2023 — all retrieved with full-text chunks, origins
  and grades in
  `docs/literature/consensus_tranche_54_covid_emission_level.md`).
  Selected against no anchor; the 4.1-log span stays the declared
  sweep axis.
- **`dose_adjustment` reads before removal, attributed:** its only
  engine read on any arm is the release-normalizer precedence chain
  (`infection_dynamics_bridge.py` line ~102). Two COVID-path
  consumers pinned it to 0 and would have gone silently inert under
  the profile-level key — the Theta-fit override
  (`covid_theta_fit.theta_profile_overrides`) and the Presidio
  workspace override
  (`_workspace_ctb_sim_v7_experiments_surveillance_roi_mega_cruise_v1.json`
  + its design doc). Both migrated to pin
  `environmental_release_log10_per_day: 0.0` — bit-identical
  adj = 0, no run semantics moved. `norovirus_gii4`,
  `sars_cov2_ba5`, and the `norwalk_gi` arm keep `dose_adjustment`.
  No test expectation moved.
- **Pair-inconsistency finding (the "report the inconsistency"
  branch, reported immediately):** deposit per shedder-epoch =
  `sv × airborne_emission_fraction`. At the shipped level (peak
  sv 4.9e5), the shipped 5e-5 deposits ~25 copies/epoch — ~170×
  below the bracket floor, and ~1.4× short even at the bracket's top
  level (level −0.14 → 2.9e3). The in-bracket fraction at the
  shipped level is [8.5e-3, ~1.2]: the measured fine share **0.85**
  (Coleman 2021) satisfies it at every measured level and is exactly
  the share tranche 27 §6 licensed for adoption once this level
  existed. `airborne_emission_fraction` is **unchanged** — adopting
  the share is a value change that is the follow-on Edison decision.
- **8-run diagnostic** (`tools/covid_emission_level_30_diag.py`,
  `reports/covid_emission_level_30_diag.json`): 4 seeds × the 2 COVID
  hulls (DP training, GM held-out), no Theta overrides, per-epoch
  per-shedder deposit recorded at the shipped fraction; Theta-regime
  witness quoted analytically (peak-0 curve, adj 0 → deposit 2.1e-6,
  i.e. the composite carried the entire scale, which is why the
  comparison is by regime not by seed). DP cells ran
  `--num-epochs 480` (day 20; the full 840-epoch voyage on 3,711
  agents is a Batch-scale cell on this box — the window covers the
  index's whole shedding course, the pre-quarantine transmission mass
  and the day-16 SOP-017 order); GM cells ran the full 672-epoch
  voyage. **Measured:** per-shedder-epoch deposit at 5e-5 sits ~3–6
  orders under the 4.2e3 floor as central tendency (cell medians
  3.5e-5–3.1e-2); only high-multiplier shedder-epochs reach the
  bracket — in-bracket share 1.1% (DP seed 20201004, max 1.7e5) and
  3.5% (GM seed 20201001, max 1.04e4), 0% on the other six cells.
  The simulation confirms the analytic pair inconsistency: the
  shipped fraction cannot carry a real exhaled rate; the licensed
  0.85 fine share would deposit level × 0.85 in-bracket.
- **Also corrected in the record:** tranche 9's "5 × 10⁴
  copies/epoch" and the register's "7.6× above Alsved's talking
  median" omitted the release normalizer and the per-day→epoch
  division — the pre-change arm's actual peak airborne deposit was
  ~2.1 copies/epoch.
