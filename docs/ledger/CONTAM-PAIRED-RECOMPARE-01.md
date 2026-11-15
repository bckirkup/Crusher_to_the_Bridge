# CONTAM-PAIRED-RECOMPARE-01
**Date:** 2026-11-15
**Commit:** 43ecb68d
**Pathogens:** all
**Status:** open
**Measured at:** 43ecb68d

## Scope

Rebuilt the paired native-vs-ContamX diagnostic as a committed local tool, `tools/diag/contam_paired_diagnostic.py`, parameterized by `--hull`, `--lane`, `--source`, and `--timing` with no AWS dependency. The matrix is both bundled hulls (`expedition_cruise_450`, `destroyer_baseline`) x three lanes x the stated sources x `pulse_t0` and `split_t0_t1`.

Lanes:
- `native`: current hull `spatial_layout.json` + `air_flow_paths.json` through `ContamTransportEngine`.
- `commissioned`: fresh `export_prj_with_path_map(..., hobbyist=True, ahs_terminal_mode="commissioned")`, solved by the local official NIST ContamX 3.4.0.3 binary, then bridged by `ContamXTransportEngine`.
- `authored`: committed `data/platforms/<hull>/contam/platform.prj` + `path_map.json`, solved as-is (not commissioned).

Material settings are fixed: filter efficiency 0.3, natural decay 0.1/h, 12 h horizon, one emitted unit. `pulse_t0` emits one unit at t=0h; `split_t0_t1` emits 0.5 at t=0h and 0.5 at t=1h. Estimands are exact augmented-system integrals of the linear transport operator: whole-hull normalized material-time (h), local/remote material-time split by the source's declared AHU group, retained mass at 12 h, reachable-other-rooms count (zones other than the source with integrated material-time > 1e-12 mass-fraction*h), and per-trajectory closure `emitted = retained + natural_decay_loss + transport_loss`.

## Change-detector

At c19b73ef (before #1241) the commissioned Expedition `pulse_t0` whole-hull times reproduce Edison's published pre-fix values to <= 5e-7 h:

| Source | Reproduced pre-fix h | Edison pre-fix h |
|---|---:|---:|
| MainDining | 0.189023403 | 0.189023 |
| HD_5P_M | 0.051756485 | 0.0517565 |
| PoolDeck | 0.740704071 | 0.740704 |
| MainGalley | 0.104060914 | 0.104061 |

The same pre/post comparison leaves `native` and `authored` bit-identical (max |delta| = 0), as expected because #1241 touched only commissioned `plr_bdq` export.

## Lane-by-lane movement after #1241

- authored / pulse_t0: max |delta| = 0 h
- authored / split_t0_t1: max |delta| = 0 h
- commissioned / pulse_t0: max |delta| = 0.226659 h
- commissioned / split_t0_t1: max |delta| = 0.226659 h
- native / pulse_t0: max |delta| = 0 h
- native / split_t0_t1: max |delta| = 0 h

Only the `commissioned` lane moved. The movement is attributed to #1241 restoring forward flow through commissioned one-way passive `plr_bdq` sanitary make-up openings (destroyer control 7/7 paths / 478.085 m3/h; Expedition control 20/53 paths / 1372.394 m3/h). Sources that do not use sanitary make-up (`HD_5P_M`, `HD_MAIN_M`) are unchanged to <1e-8 h. Expedition `pulse_t0` commissioned values rise where make-up air now reaches served spaces; destroyer `Mess_Hall` and `Bridge` fall because restored sanitary forward flow drains mass out of those zones faster.

Commissioned `pulse_t0` pre -> post:

| Hull | Source | Pre-#1241 whole-hull h | Post-fix whole-hull h | Delta h | Reachable other rooms pre -> post |
|---|---|---:|---:|---:|---|
| expedition_cruise_450 | MainDining | 0.189023 | 0.191260 | 0.002237 | 9 -> 9 |
| expedition_cruise_450 | HD_5P_M | 0.051756 | 0.051756 | 0.000000 | 0 -> 0 |
| expedition_cruise_450 | PoolDeck | 0.740704 | 0.774098 | 0.033394 | 13 -> 17 |
| expedition_cruise_450 | MainGalley | 0.104061 | 0.106844 | 0.002783 | 9 -> 9 |
| destroyer_baseline | Mess_Hall | 0.536905 | 0.325211 | -0.211694 | 5 -> 4 |
| destroyer_baseline | HD_MAIN_M | 0.051687 | 0.051687 | 0.000000 | 0 -> 0 |
| destroyer_baseline | Bridge | 0.643254 | 0.416595 | -0.226659 | 5 -> 8 |

## Full post-fix results

Closure is reported per trajectory; max |closure_error| across all 42 cells is 8.88e-16 emitted units.

### pulse_t0

| Hull | Lane | Source | Material-time h | Local h | Remote h | Retained 12h | Decay loss | Transport loss | Closure error | Reachable other rooms |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| expedition_cruise_450 | native | MainDining | 0.176756 | 0.105102 | 0.071653 | 1.386e-06 | 0.017676 | 0.982323 | 2.22e-16 | 46 |
| expedition_cruise_450 | native | HD_5P_M | 0.051813 | 0.051813 | 0.000000 | 2.615e-101 | 0.005181 | 0.994819 | 1.11e-16 | 0 |
| expedition_cruise_450 | native | PoolDeck | 2.569332 | 2.299789 | 0.269544 | 0.006803 | 0.256933 | 0.736263 | -8.88e-16 | 46 |
| expedition_cruise_450 | native | MainGalley | 0.086846 | 0.085178 | 0.001668 | 9.895e-10 | 0.008685 | 0.991315 | 3.33e-16 | 46 |
| expedition_cruise_450 | commissioned | MainDining | 0.191260 | 0.123090 | 0.068171 | 2.823e-11 | 0.019126 | 0.980874 | -1.11e-16 | 9 |
| expedition_cruise_450 | commissioned | HD_5P_M | 0.051756 | 0.051756 | 0.000000 | 2.026e-101 | 0.005176 | 0.994824 | 2.22e-16 | 0 |
| expedition_cruise_450 | commissioned | PoolDeck | 0.774098 | 0.508563 | 0.265534 | 2.363e-10 | 0.077410 | 0.922590 | 4.44e-16 | 17 |
| expedition_cruise_450 | commissioned | MainGalley | 0.106844 | 0.082798 | 0.024046 | 2.922e-11 | 0.010684 | 0.989316 | 1.11e-16 | 9 |
| expedition_cruise_450 | authored | MainDining | 0.188614 | 0.118523 | 0.070091 | 7.941e-11 | 0.018861 | 0.981139 | 2.22e-16 | 9 |
| expedition_cruise_450 | authored | HD_5P_M | 0.231018 | 0.231018 | 0.000000 | 2.760e-23 | 0.023102 | 0.976898 | 2.22e-16 | 0 |
| expedition_cruise_450 | authored | PoolDeck | 0.749262 | 0.470513 | 0.278749 | 2.828e-10 | 0.074926 | 0.925074 | 0.00e+00 | 13 |
| expedition_cruise_450 | authored | MainGalley | 0.103552 | 0.085168 | 0.018384 | 8.290e-11 | 0.010355 | 0.989645 | 4.44e-16 | 9 |
| destroyer_baseline | native | Mess_Hall | 0.300821 | 0.238253 | 0.062568 | 1.251e-14 | 0.030082 | 0.969918 | -1.11e-16 | 8 |
| destroyer_baseline | native | HD_MAIN_M | 0.051813 | 0.051813 | 0.000000 | 2.615e-101 | 0.005181 | 0.994819 | 1.11e-16 | 0 |
| destroyer_baseline | native | Bridge | 0.345927 | 0.246326 | 0.099601 | 1.951e-14 | 0.034593 | 0.965407 | 1.11e-16 | 8 |
| destroyer_baseline | commissioned | Mess_Hall | 0.325211 | 0.302692 | 0.022519 | 5.880e-19 | 0.032521 | 0.967479 | 2.22e-16 | 4 |
| destroyer_baseline | commissioned | HD_MAIN_M | 0.051687 | 0.051687 | 0.000000 | 1.484e-101 | 0.005169 | 0.994831 | 0.00e+00 | 0 |
| destroyer_baseline | commissioned | Bridge | 0.416595 | 0.295892 | 0.120703 | 2.370e-15 | 0.041660 | 0.958340 | 0.00e+00 | 8 |
| destroyer_baseline | authored | Mess_Hall | 0.669937 | 0.666579 | 0.003358 | 3.044e-09 | 0.066994 | 0.933006 | -3.33e-16 | 5 |
| destroyer_baseline | authored | HD_MAIN_M | 0.230714 | 0.230714 | 0.000000 | 2.578e-23 | 0.023071 | 0.976929 | 2.22e-16 | 0 |
| destroyer_baseline | authored | Bridge | 0.643233 | 0.598510 | 0.044724 | 2.740e-09 | 0.064323 | 0.935677 | -2.22e-16 | 5 |

### split_t0_t1

| Hull | Lane | Source | Material-time h | Local h | Remote h | Retained 12h | Decay loss | Transport loss | Closure error | Reachable other rooms |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| expedition_cruise_450 | native | MainDining | 0.176755 | 0.105102 | 0.071652 | 1.752e-06 | 0.017675 | 0.982323 | 0.00e+00 | 46 |
| expedition_cruise_450 | native | HD_5P_M | 0.051813 | 0.051813 | 0.000000 | 3.150e-93 | 0.005181 | 0.994819 | 0.00e+00 | 0 |
| expedition_cruise_450 | native | PoolDeck | 2.565094 | 2.296050 | 0.269045 | 0.008603 | 0.256509 | 0.734887 | -5.55e-16 | 46 |
| expedition_cruise_450 | native | MainGalley | 0.086846 | 0.085178 | 0.001668 | 1.263e-09 | 0.008685 | 0.991315 | 3.33e-16 | 46 |
| expedition_cruise_450 | commissioned | MainDining | 0.191260 | 0.123090 | 0.068171 | 8.359e-11 | 0.019126 | 0.980874 | -1.11e-16 | 9 |
| expedition_cruise_450 | commissioned | HD_5P_M | 0.051756 | 0.051756 | 0.000000 | 2.493e-93 | 0.005176 | 0.994824 | 1.11e-16 | 0 |
| expedition_cruise_450 | commissioned | PoolDeck | 0.774098 | 0.508563 | 0.265534 | 8.230e-10 | 0.077410 | 0.922590 | -1.11e-16 | 17 |
| expedition_cruise_450 | commissioned | MainGalley | 0.106844 | 0.082798 | 0.024046 | 8.653e-11 | 0.010684 | 0.989316 | -1.11e-16 | 9 |
| expedition_cruise_450 | authored | MainDining | 0.188614 | 0.118523 | 0.070091 | 2.225e-10 | 0.018861 | 0.981139 | -1.11e-16 | 9 |
| expedition_cruise_450 | authored | HD_5P_M | 0.231018 | 0.231018 | 0.000000 | 1.061e-21 | 0.023102 | 0.976898 | 1.11e-16 | 0 |
| expedition_cruise_450 | authored | PoolDeck | 0.749262 | 0.470513 | 0.278749 | 8.338e-10 | 0.074926 | 0.925074 | -1.11e-16 | 13 |
| expedition_cruise_450 | authored | MainGalley | 0.103552 | 0.085168 | 0.018384 | 2.323e-10 | 0.010355 | 0.989645 | 1.11e-16 | 9 |
| destroyer_baseline | native | Mess_Hall | 0.300821 | 0.238253 | 0.062568 | 8.573e-14 | 0.030082 | 0.969918 | -1.11e-16 | 8 |
| destroyer_baseline | native | HD_MAIN_M | 0.051813 | 0.051813 | 0.000000 | 3.150e-93 | 0.005181 | 0.994819 | 0.00e+00 | 0 |
| destroyer_baseline | native | Bridge | 0.345927 | 0.246326 | 0.099601 | 1.337e-13 | 0.034593 | 0.965407 | 1.11e-16 | 8 |
| destroyer_baseline | commissioned | Mess_Hall | 0.325211 | 0.302692 | 0.022519 | 1.020e-17 | 0.032521 | 0.967479 | 0.00e+00 | 4 |
| destroyer_baseline | commissioned | HD_MAIN_M | 0.051687 | 0.051687 | 0.000000 | 1.875e-93 | 0.005169 | 0.994831 | 0.00e+00 | 0 |
| destroyer_baseline | commissioned | Bridge | 0.416595 | 0.295892 | 0.120703 | 1.983e-14 | 0.041660 | 0.958340 | 2.22e-16 | 8 |
| destroyer_baseline | authored | Mess_Hall | 0.669937 | 0.666579 | 0.003358 | 9.431e-09 | 0.066994 | 0.933006 | -1.11e-16 | 5 |
| destroyer_baseline | authored | HD_MAIN_M | 0.230714 | 0.230714 | 0.000000 | 9.960e-22 | 0.023071 | 0.976929 | 1.11e-16 | 0 |
| destroyer_baseline | authored | Bridge | 0.643233 | 0.598510 | 0.044724 | 8.577e-09 | 0.064323 | 0.935677 | 0.00e+00 | 5 |
