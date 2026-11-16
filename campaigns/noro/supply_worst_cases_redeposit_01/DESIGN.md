# FOOD-SUPPLY-01 worst-case mega redeposit contrast

**Date:** 2026-11-16
**Pathogens:** norwalk_gi
**Status:** design frozen before cells run
**Parent ranking:** `campaigns/noro/supply_worst_cases_01/ranking.json` (`docs/ledger/FOOD-SUPPLY-01-WORST-CASES.md`)

## Question

Do the four highest-burden mega supply-seed examples change final posted AR,
VSP timing, or role channels when carrier hand redeposition is enabled?

## Seed selection (frozen)

Use the first four entries of `ranking.json` `top_by_hull.meg`, ranked by the
committed burden rule (`quantity_g * titre` for receipt lots;
`lot_servings * titre * 150 g` for station lots):

| rank | supply arm | seed | burden_est | witness |
|---:|---|---:|---:|---|
| 1 | `single_line_receipt` | 1030001 | 580,203,309.568 | shellfish, 524 servings, 116,103 g, titre 4,997 GEC/g |
| 2 | `declared_receipts` | 1031386 | 520,046,935.806 | shellfish, 505 servings, 124,063 g, titre 4,192 GEC/g |
| 3 | `station_lots` | 1036232 | 455,349,796.777 | bakery + deli, 673 servings, max titre 4,771 GEC/g |
| 4 | `station_lots` | 1020931 | 444,673,387.088 | dairy + deli, 1,389 servings, max titre 3,904 GEC/g |

Station-lot burdens are midpoint estimates, not exact masses; receipt burdens
are exact receipt mass × titre.

## Arms (frozen)

Each seed runs paired on the same p06 passenger-venue mega cell:

- `shedders_only`: `transmission.hand_redeposit_mode = "shedders_only"`
- `carriers`: `transmission.hand_redeposit_mode = "carriers"`

Held fixed: `intra_epoch_causal_order = legacy` (default),
`intra_epoch_substeps = 1` (default), `hand_reservoir_mode = hygiene_cycle`
(default), p06 route scale ×2.0, q_source 0.0047, passenger/crew prevalence
0.025/0.03, illness draw `point`, 288 epochs, `syndromic_comp65`, dose
adjustment 7.57, `station_zone_pin=['MainDining_L']`, `--payload lean`,
`PYTHONHASHSEED=1`.

This isolates the redeposit gate only. It does **not** test `ordered`,
`carriers_ordered`, or `M>1` substeps.

## Cells (frozen)

8 cells = 4 seeds × 2 redeposit modes. Supply arm stays paired to the seed's
ranking row; the two `station_lots` seeds share the station-lots tiers.

| block | tier | seed |
|---|---|---:|
| `meg_single_line_receipt_1030001_shedders_only` | `fl_meg_12d_sens_p06_paxv_single_line_receipt_shedders_only` | 1030001 |
| `meg_single_line_receipt_1030001_carriers` | `fl_meg_12d_sens_p06_paxv_single_line_receipt_carriers` | 1030001 |
| `meg_declared_receipts_1031386_shedders_only` | `fl_meg_12d_sens_p06_paxv_declared_receipts_shedders_only` | 1031386 |
| `meg_declared_receipts_1031386_carriers` | `fl_meg_12d_sens_p06_paxv_declared_receipts_carriers` | 1031386 |
| `meg_station_lots_1036232_shedders_only` | `fl_meg_12d_sens_p06_paxv_station_lots_shedders_only` | 1036232 |
| `meg_station_lots_1036232_carriers` | `fl_meg_12d_sens_p06_paxv_station_lots_carriers` | 1036232 |
| `meg_station_lots_1020931_shedders_only` | `fl_meg_12d_sens_p06_paxv_station_lots_shedders_only` | 1020931 |
| `meg_station_lots_1020931_carriers` | `fl_meg_12d_sens_p06_paxv_station_lots_carriers` | 1020931 |

## Endpoints and admissibility (frozen)

Primary readout per seed is the paired contrast `carriers − shedders_only`:

- `posted` / `outbreak_occurred`, `vsp_trigger_epoch` and VSP day;
- passenger and crew infection AR, ever-ill AR, and reported-case AR;
- common-source provisioned-lot events/takers/dose credited;
- census acquisitions/imports, role checkpoints, and compact mechanism counters.

A cell is admissible only if:

- the zip has the unchanged `summary.json` + `growth_census.json.gz` +
  `rss_samples.json` contract;
- `parameters.engine_git_sha` equals the pinned image SHA;
- `mechanisms.provisioned_source` resolves the intended supply arm
  (`lot_layer_mode`/absence for `station_lots`) and the seed's item lines /
  venues match the ranking row;
- the carrier arm is confirmed to have consumed the `carriers` redeposit path
  by a nonzero carrier-deposit witness or an engine-config readback; if no
  readback exists, report that limitation explicitly rather than claiming the
  override fired.

Diagnostics reported but never selected on: quiet-voyage acquisition counts,
crew-only posts, non-supply common-source events, and RSS peaks.

## Interpretation limit (frozen)

Four paired seeds are an existence/contrast probe, not a rate estimate and not
an effect-size campaign. No anchor fitting, no default flip, and no claim that
a carriers-arm move is epidemiologically correct follows from this panel.

## Non-goals

- No `intra_epoch_causal_order=ordered`, `intra_epoch_substeps>1`, or
  `hand_reservoir_mode` changes.
- No renewal-boarding, contact-constant, or dose-refit changes.
- No CE comparator work; CE remains paused pending the missing-constants audit.
