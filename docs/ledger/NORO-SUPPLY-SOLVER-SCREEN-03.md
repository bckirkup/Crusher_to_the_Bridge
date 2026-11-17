# NORO-SUPPLY-SOLVER-SCREEN-03
**Date:** 2026-11-17
**Commit:** #1292
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** c6c3c25fbabefa7ed918cba55311ceec231dbba3

Mega extension of the expedition supply-contamination solver screen. Design is frozen in `campaigns/noro/supply_solver_screen_03/DESIGN.md`; the frozen seed list is `campaigns/noro/supply_solver_screen_03/seed_selection.json`; job/array IDs are in `campaigns/noro/supply_solver_screen_03/LEDGER.md`. AWS Batch image `picard-campaign:noro-supply-solver03` digest `sha256:203536dea284153523e1ea874ad76651efecb34d0458a08d957c8f465277452a` (`ENGINE_GIT_SHA=db899fd3`); S3 artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_03/`.

Run contract: 88 cells = 1 hull (`mega_cruise_5000`, `num_agents=7000`) × 2 `transmission.contamination_solver` arms (`discrete` labelled baseline vs `continuous` RK4 default) × 44 paired seeds. Supply strata per solver: `station_lots` 16 contaminated + 8 quiet, `single_line_receipt` 10 contaminated, `declared_receipts` 10 contaminated. All cells: 288 epochs, `natural_history_clock="hours"`, dose adjustment 7.57, `syndromic_comp65`, `station_zone_pin=['MainDining_L']`, passenger/crew prevalence 0.025/0.03, point illness draw, route scale ×2.0. Posting means `vsp_trigger_epoch is not None`; days use 24 epochs/day. Canonical readout: `docs/norovirus/supply_solver_screen_03_readout.md`; machine-readable `campaigns/noro/supply_solver_screen_03/readout.json`.

Measured result: 88/88 cells SUCCEEDED, 0 failed/missing/duplicate. Posting is rare on mega: `station_lots` posted 1/16 on each solver arm (the same seed posted on both); `single_line_receipt` and `declared_receipts` posted 0/10; quiet controls posted 0/8 on both solvers. The single posted `station_lots` pair had passenger reported-case AR 0.0455 discrete vs 0.0445 continuous and VSP epoch 56 vs 75; paired continuous-minus-discrete sign tests are uninformative (`posted_both=1`). The frozen stratified supply seeds almost never reach the 3% VSP wire on the 7000-agent hull.

Next decision: whether mega needs a different seed/burden stratum or a posting-frequency-targeted design before the solver arms can be separated, or whether supply contamination should be down-weighted as a posting mechanism at this complement. Do not fit constants to these anchors; do not treat the single posted pair as solver separation.
