# NORO-SUPPLY-SOLVER-SCREEN-01
**Date:** 2026-11-17
**Commit:** #1280
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 6742f1a456e5717cf813c57bc9b3e34bb532fda5

Expedition p06 supply-contamination solver screen. Design is frozen in `campaigns/noro/supply_solver_screen_01/DESIGN.md`; the frozen seed list is `campaigns/noro/supply_solver_screen_01/seed_selection.json`; job/array IDs are in `campaigns/noro/supply_solver_screen_01/LEDGER.md`. AWS Batch image `picard-campaign:noro-supply-solver01` digest `sha256:f25d74cd225bc4ade19a012ba801b25f91289f80f3c3778bfd6c27c343a0053a` (`ENGINE_GIT_SHA=3500c205`); S3 artifacts: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_solver_screen_01/`.

Run contract: 88 cells = 2 `transmission.contamination_solver` arms (`discrete` labelled baseline vs `continuous` RK4 default) × 44 paired seeds on `fl_exp_12d_sens_p06_paxv` (`expedition_cruise_450`, 288 epochs, `natural_history_clock="hours"`, dose adjustment 7.57, `syndromic_comp65`, `station_zone_pin=['MainDining']`, `source_venue_arm='passenger_venue'`, `q_source=0.0047`, passenger/crew prevalence 0.025/0.03, point illness draw, route scale ×2.0). Supply strata per solver: `station_lots` 16 contaminated + 8 quiet, `single_line_receipt` 10 contaminated, `declared_receipts` 10 contaminated (`receipts_per_item_line: 2`). Posting means `vsp_trigger_epoch is not None` (either-channel reported-case VSP rule); days use 24 epochs/day. The canonical readout is `docs/norovirus/supply_solver_screen_01_readout.md`.

## Outcomes

All 88 Batch children SUCCEEDED; 88 zips read, 0 failed/missing.

- Posting: contaminated strata posted on every cell in both arms (`station_lots` 16/16, `single_line_receipt` 10/10, `declared_receipts` 10/10 each arm). Quiet `station_lots` controls posted 0/8 on both arms. The solver arm alone did not manufacture posting, and posting frequency did not separate the arms.
- Paired `continuous - discrete` medians (sign-test p): `station_lots` posted-conditional passenger reported-case AR −0.2% (p = 0.791), VSP epoch −3.5 (p = 0.454); `single_line_receipt` pax reported AR −0.3% (p = 1.000), VSP epoch +2.0 (p = 0.344); `declared_receipts` pax reported AR +0.8% (p = 0.508), VSP epoch −1.5 (p = 1.000). Every role-partition sign test had p ≥ 0.180.
- Posted-conditional pax reported-AR ranges overlap in every contaminated stratum: `station_lots` discrete 2.9–19.6% vs continuous 3.5–17.7%; `single_line_receipt` 4.4–15.2% vs 4.1–14.2%; `declared_receipts` 3.8–16.1% vs 4.8–17.4%. VSP epoch ranges: `station_lots` discrete 50–283 vs continuous 40–112; `single_line_receipt` 49–122 vs 49–143; `declared_receipts` 57–122 vs 39–98.

## Measured / inferred / hypothesis

Measured: the 88-cell paired screen above; all contaminated supply seeds posted under both solvers, quiet controls did not post, and no endpoint reached the frozen sign-test separation on this seed set.

Inferred: on expedition p06 supply-contamination seeds, replacing the legacy ordered intra-epoch updates with the continuous hand↔surface↔food RK4 solve changes posted AR, VSP timing and passenger/crew role partition only within seed-to-seed noise at this screen's resolution. The direction is not consistent across strata (station_lots/continuous slightly earlier VSP median but later in `single_line_receipt`; `declared_receipts` slightly earlier and higher pax reported AR), so there is no robust solver-arm association to report.

Hypothesis/next: this is a screen, not anchor fitting. It does not by itself justify reverting the continuous default or tuning supply constants; if a solver-sensitive supply effect is suspected, the next step is a targeted mechanism witness (hand↔food/surface flux or per-host dose) on the seeds where the paired AR/VSP diffs are largest, not another unpaired seed sweep.
