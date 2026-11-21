# NORO-JE-REPRO-01
**Date:** 2026-11-21
**Commit:** 0ba4a7ce
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 90aa3ec2

The Paper-1 WP2 reproduction arm
(`campaigns/noro/paper1_joint_eval_01`, tier
`fl_je_repro_exp_solver01_station_continuous`, 16 cells on AWS Batch,
image `sha256:80884d60…f149a`) does not reproduce: seed by seed against
the `noro_supply_solver_screen_01` reference fingerprints of
`fl_exp_12d_sens_p06_paxv_station_lots_continuous`, 16/16 compared,
**0/16 identical**.

The cells ran correctly — all 16 posted (posting rate 1.00, reported AR
median 0.057, max 0.131, all detected by swab and tank) — so this is a
systematic divergence between the joint-eval wiring and the
solver-screen wiring on identical seeds, not a seed-specific or
transport failure. The fingerprint excludes the declared parameter
allowlist; the divergence is therefore in run content, not in the
recorded provenance.

The campaign's frozen continuation map selects `justified_defect_fix`
for exactly this evidence ("the reproduction arm does not reproduce").
Technical completion of the full 1,696-cell campaign itself passed:
45/45 tier cells, 0 audit defects, `engine_git_sha` `bf0ec168` on
Stage-A archives and `90aa3ec2` on Stage-B.

Readout: `telemetry_buffer/noro_paper1_joint_eval_01/`; campaign
ledger: `campaigns/noro/paper1_joint_eval_01/LEDGER.md` "Full readout
(2026-11-21)". The open question is which wiring step differs — the
joint-eval cell applies the class-mix arm difference plus the
joint-eval observer hooks on top of the shared baseline block the
solver screen ran.
