# NORO-FOOD-SCORE-01
**Date:** 2026-10-08
**Commit:** 420e0326
**Pathogens:** norwalk_gi
**Status:** measured

Scores the shipped FOOD-COMMON-SOURCE-02 contamination objects
(default-ON `lot_mode`/`handler_mode`/`diner_mode: "object"`,
`"independent"` the labelled v1 baseline) against the frozen
measurement plan in `docs/food_common_source_02_design.md`. Declared
before any cell ran; no array submitted under this design — the user
gates image build, canary, and every wave.

Grid: 3 hulls (exp/cls/spr) × 6 arms (`off`, `ind` = v1 baseline on
the current engine, and a `lot_object_probability` rung ladder
ol1 [0.0005,0.0025] / ol2 [0.001,0.006] / ol3 [0.002,0.012] /
ship [0.001,0.02]) × 1,000 seeds = 18,000 voyages on the `gen` age
mix, fixed coordinates identical to FOOD-01/02 and AGE-FOOD-01
(rung `shipped`, bp32.5c18.5, nsf29, 288 epochs, dose_adjustment 7.57,
`syndromic_comp65`), AGE-FOOD-01 seed lists (exp 8000–8999, cls/spr
8105–9104).

Frozen scored criteria, must-not-move list, canary (24 ship + 12 ind
+ 8 off on exp, then STOP), wave order, and report-immediately
triggers: `docs/norovirus/noro_food_score_01_sweep_design.md`.
Campaign package `campaigns/noro/noro_food_score_01/`; manifest
`noro_food_score_01_manifest.json` (18 tiers, 18,000 cells); local
smoke of `fl_exp_12d_scr_ship` index 0 passed (override echo +
handler object witness + 3-member zip contract).
