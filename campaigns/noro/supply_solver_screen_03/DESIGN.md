# NORO supply solver screen 03 — mega

**Date:** 2026-11-17
**Pathogens:** norwalk_gi
**Status:** design frozen before cells run
**Parent census:** `campaigns/noro/supply_seed_scan_01/` (`docs/ledger/FOOD-SUPPLY-01-SEED-SCAN.md`)
**Siblings:** `campaigns/noro/supply_solver_screen_01/` (`docs/ledger/NORO-SUPPLY-SOLVER-SCREEN-01.md`), `campaigns/noro/supply_solver_screen_02/` (`docs/ledger/NORO-SUPPLY-SOLVER-SCREEN-02.md`)

## Question

On the mega p06 passenger-venue cell, does `transmission.contamination_solver` change supply-contamination outcomes: posted attack rate, VSP timing, and passenger/crew role partition? This is the last-ship-class extension of the expedition and classic+spirit screens.

## Arms

- Solver arms, paired by voyage seed: `transmission.contamination_solver` = `discrete` (labelled pre-change baseline) vs `continuous` (default RK4 hand/surface/food flow).
- Supply arms: `station_lots`, `single_line_receipt`, `declared_receipts` (`receipts_per_item_line=2`).
- Quiet controls: `station_lots` seeds with zero contaminated supply in all three arms.

Only `transmission.contamination_solver` and the supply-arm fields (`common_source.provisioned_source.lot_layer_mode`, `receipts_per_item_line`) vary by block. `hand_redeposit_mode` is not swept.

## Held fixed

The pinned SENSITIVITY-01 p06 passenger-venue cell:

- `meg`: `fl_meg_12d_sens_p06_paxv`, `mega_cruise_5000`, `num_agents=7000`, `epochs=288`, `natural_history_clock="hours"`, `dose_adjustments=[7.57]`, surveillance `syndromic_comp65`, `station_zone_pin=['MainDining_L']`, `source_venue_arm='passenger_venue'`, `q_source=0.0047`, passenger/crew prevalence `0.025/0.03`, illness draw `point`, route scale x2.0.

Worker payload is `lean`; campaign runs use `PYTHONHASHSEED=1`.

## Seed rule

Source: `noro_supply_seed_scan_01` mega rows synced from `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_supply_seed_scan_01/meg_{arm}/`. This is a boarding census, not a posted-AR measurement.

Burden rules match `supply_worst_cases_01` and the prior screens: station lots `lot_servings * lot_titre_gec_per_g * 150 g` summed over contaminated lot objects; receipt lots `quantity_g * lot_titre_gec_per_g` summed over served lot objects. Contaminated means burden `> 0`.

Per hull:

- `station_lots`: 16 contaminated seeds.
- `single_line_receipt`: 10 contaminated seeds.
- `declared_receipts`: 10 contaminated seeds.
- Quiet controls: 8 seeds with zero contaminated provisioned lots/receipts in all three arms for that hull, selected by middle-of-bin rank across the sorted quiet seed list.

Within each supply arm, selection stratifies by item line and burden quantiles exactly as the prior screens: station lots use two burden quantiles (`0.9`, `0.3`) per item line plus two highest-burden top-ups; receipt arms use `fresh_produce` `[0.9, 0.3]`, `salad_leaf` `[0.9, 0.5, 0.2]`, and `shellfish` `[0.95, 0.75, 0.5, 0.25, 0.1]`. Quantiles are computed on raw burden; selection is nearest in `log10` burden with ties by lower seed.

## Cells

88 runs = 1 hull x 2 solver arms x 44 seeds. Per solver: `station_lots` 16 contaminated + 8 quiet, `single_line_receipt` 10, `declared_receipts` 10. Station contaminated and quiet blocks share the station tier but have disjoint seed lists.

## Endpoints

Primary: posting frequency (`vsp_trigger_epoch is not None`, the either-channel 3% reported-case VSP rule), posted-conditional passenger reported-case AR, VSP trigger epoch/day, and passenger/crew role partition (`reported_case_attack_rate_*`, `infection_attack_rate_*`, `ever_ill_attack_rate_*`).

Secondary: unconditional attack rates, peak prevalence/timing, and supply/mechanism witnesses (`common_source` events/takers, `provisioned_source`, growth-census mechanism counters). Hull is a stratifier, not a fitted covariate.

## Analysis rule

Pair by seed within supply stratum. Report per-stratum medians/IQRs and paired differences `continuous - discrete`. Success is an uncertainty-qualified association; failure is an uninformative screen (overlapping ranges, no posted cells, or a stream-neutrality failure). No anchor fitting and no default flips.

## Preflight gate

Before any array: local smoke proving `contamination_solver` reaches the engine with the output contract unchanged; `--dry-run` count = 88; pinned jobdef revision and image digest; manifest present in S3; one canary child inspected; ETA reported at submission. Stop after the canary for the user decision.
