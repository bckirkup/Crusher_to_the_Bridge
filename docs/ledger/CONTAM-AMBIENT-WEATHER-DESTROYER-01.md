# CONTAM-AMBIENT-WEATHER-DESTROYER-01
**Date:** 2026-11-17
**Commit:** 5b2cfbc1
**Pathogens:** all
**Status:** measured
**Measured at:** 5b2cfbc1

## Scope

After-witnesses measured at `5b2cfbc1`; before-witnesses at `origin/main`
`6efb316f`. Steady ContamX solves with the local binary
`third_party/contamx/contamx3`; no seeds, no AWS.

Stage 4 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6 for the **destroyer naval class**. The roster was enumerated from
[`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md) and
`data/platforms/`: the `dd`/`dde`/`dms`/`de` hulls plus `destroyer_baseline`.
Included hulls are the nine with authored weather openings below; the roster
hulls with no qualifying ungrouped stage-4 weather zone are recorded and
skipped (`bainbridge_dd1`, `destroyer_baseline`, `fletcher_class_destroyer`).
Borderline calls: `pce_874` is a PCE rescue/patrol escort and `ruchamkin_apd89`
is an APD, not dd/dde/dms/de or `destroyer_baseline`, so both are excluded;
`alexander_henry_cgs119`, `independence_cvl26` and `middlesex_lst983` were
regex false positives (`de` inside the name) and are not destroyers.
`fletcher_class_destroyer` is a Fletcher-class destroyer by name but has no
committed Contam bundle and no qualifying ungrouped weather zone, so it is
recorded and skipped rather than given a bundle here.

Each weather zone keeps its finite zone (D2(a)), declares `exposure: weather`
in `spatial_layout.json` where the lexical fallback was wrong or absent (D7(b))
and carries one `open_deck` `ambient_openings` record (D1(a)) with the Grade C
deck-face area rule, `wind_speed_m_s` 1 m/s committed on the declared 0–10 m/s
axis, `schedule: always_open`, and `exchange_m3h` = the commissioned-lane
ContamX-solved outward flow at that point (D5). No `flow_rate_m3h`,
`envelope_leak.area_m2`, engine/exporter constant, wind override, balcony,
hatch or door changed. Naval hulls keep the fleet default weather from
`CONTAM-DEFAULT-WEATHER-01` (1 m/s from ahead); the overrides inspected carry
only `wind_profile: ship_hull`.

Machinery: [`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md),
[`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md),
[`CONTAM-DEFAULT-WEATHER-01`](CONTAM-DEFAULT-WEATHER-01.md).
Recipe precedent: [`CONTAM-AMBIENT-WEATHER-CRUISE-01`](CONTAM-AMBIENT-WEATHER-CRUISE-01.md).
Inventory: [`CONTAM-AMBIENT-EXPOSURE-01`](CONTAM-AMBIENT-EXPOSURE-01.md).

## Exposure calls

- **Weather records: 37** across nine hulls. The lexical `_is_exterior` fallback
  was right for 33; four more open zones were authored because the id/type match
  missed them although their own descriptions say open weather:
  `hunter_killer_dd692/Signal_Bridge` (open signal bridge) and
  `keppler_dd765/Signal_Shelter` (open signal shelter),
  `keppler_dd765/Helo_Platform` (open deck), and
  `keppler_dd765/Forecastle_Top_01` (open deckhouse top).
- **Enclosed corrections: 3.** The lexical id match called these weather but
  their own descriptions are enclosed spaces, so they declare
  `exposure: enclosed` and carry no opening: `cannon_de701/Signal_Deck`
  (signal shelter, HVAC_Accom), `davison_dd618/Bow_Focsle` (windlass/repair
  room) and `nields_dd616/Bow_Focsle` (windlass/chain room).
- All other roster hulls either have no ungrouped lexical weather zone
  (`bainbridge_dd1`, `destroyer_baseline`, `fletcher_class_destroyer`) or are
  outside the destroyer roster.

## Bundles and design pins

Regenerated the nine affected committed bundles with
`scripts/generate_platform_contam_prj.py --platform <hull> --ahs-terminal-mode commissioned`.
Path counts rise by two legs per `open_deck` record (37 records → 74 legs).
No frozen Phase 1/2 campaign design names these hulls (the only committed
Contam campaign designs are `phase1_hvac_tracer_01` and
`phase2_cruise_contrasts_01`, on other hulls), so no `_v2` succession was
needed; `_01`/`_v1` artifacts are byte-untouched. No cache was produced or
uploaded.

## Witnesses

`tools/diag/contam_pressure_balance_diagnostic.py` (design, commissioned and
authored lanes), `tools/contam_flow_compare.py --run-contamx`, and
`tools/diag/contam_paired_diagnostic.py` (same cells before/after; the GA
destroyer hulls are not in the tool's default `PLATFORM_SOURCES`, so the same
matrix was run programmatically with explicit source zones:
`pulse_t0` and `split_t0_t1`, native/commissioned/authored lanes). Pressure and
flow outputs are the committed-tree diagnostic files; the paired diagnostic
reports 12 cells per hull. `tools/contam_commissioned_check.py` on the nine
touched hulls: PASS, every commissioned terminal inside 5% of declared.

### Pressure balance (before -> after)

| hull | lane | paths | max abs dP Pa | balance residual m3/h | envelope net in m3/h | ambient-opening net in m3/h | k field/native median |
|---|---|---:|---:|---:|---:|---:|---:|
| `cannon_de701` | design | 255 -> 263 | 110.9 -> 110.9 | 0 -> -0.001166 | 0 -> 3.019 | 0 -> -3.018 | 0.8912 -> 0.9969 |
| `cannon_de701` | commissioned | 255 -> 263 | 1.726e+04 -> 110.9 | -5.597e-06 -> -7.096e-05 | 1176 -> 4.468 | 0 -> 1171 | 1.043 -> 1.007 |
| `cannon_de701` | authored | 255 -> 263 | 1.726e+04 -> 110.9 | -5.597e-06 -> -7.096e-05 | 1176 -> 4.468 | 0 -> 1171 | 1.043 -> 1.007 |
| `cushing_dd376` | design | 396 -> 400 | 184 -> 184 | -4.358e-08 -> -0.0009984 | 4.358e-08 -> 2.677 | 0 -> -2.676 | 0.9037 -> 0.9875 |
| `cushing_dd376` | commissioned | 396 -> 400 | 4245 -> 184 | 1.395e-06 -> 0.000631 | 744.4 -> 8.442 | 0 -> 736 | 0.9124 -> 1.002 |
| `cushing_dd376` | authored | 396 -> 400 | 4245 -> 184 | 1.395e-06 -> 0.000631 | 744.4 -> 8.442 | 0 -> 736 | 0.9124 -> 1.002 |
| `davison_dd618` | design | 257 -> 267 | 158.1 -> 158.1 | -0.0007228 -> 0.001868 | 0.0007228 -> 1.505 | 0 -> -1.507 | 0.8262 -> 0.8773 |
| `davison_dd618` | commissioned | 257 -> 267 | 2.011e+04 -> 241.8 | 2.808e-06 -> 0.002088 | 1393 -> 144.3 | 0 -> 1249 | 1.017 -> 0.9689 |
| `davison_dd618` | authored | 257 -> 267 | 2.011e+04 -> 241.8 | 2.808e-06 -> 0.002088 | 1393 -> 144.3 | 0 -> 1249 | 1.017 -> 0.9689 |
| `fletcher_dde_dd445` | design | 400 -> 404 | 77.89 -> 77.89 | 2.746e-08 -> 0.001133 | -2.746e-08 -> 6.006 | 0 -> -6.007 | 1.131 -> 1.131 |
| `fletcher_dde_dd445` | commissioned | 400 -> 404 | 3417 -> 77.89 | 1.406e-06 -> 0.002569 | 574.9 -> 44.98 | 0 -> 529.9 | 0.9925 -> 0.9783 |
| `fletcher_dde_dd445` | authored | 400 -> 404 | 3417 -> 77.89 | 1.406e-06 -> 0.002569 | 574.9 -> 44.98 | 0 -> 529.9 | 0.9925 -> 0.9783 |
| `hunter_killer_dd692` | design | 887 -> 901 | 47.22 -> 47.22 | -1.646e-08 -> -0.005795 | 1.646e-08 -> 8.622 | 0 -> -8.616 | 0.8044 -> 0.9686 |
| `hunter_killer_dd692` | commissioned | 887 -> 901 | 5.161e+04 -> 8614 | -5.619e-06 -> -0.001895 | 3635 -> 1205 | 0 -> 2430 | 1.009 -> 0.9896 |
| `hunter_killer_dd692` | authored | 887 -> 901 | 5.161e+04 -> 8614 | -5.619e-06 -> -0.001895 | 3635 -> 1205 | 0 -> 2430 | 1.009 -> 0.9896 |
| `keppler_dd765` | design | 1474 -> 1488 | 172.2 -> 172.2 | 1.429e-07 -> -0.001971 | -1.429e-07 -> 12.2 | 0 -> -12.19 | 0.9689 -> 1.003 |
| `keppler_dd765` | commissioned | 1474 -> 1488 | 5830 -> 172.2 | -1.407e-06 -> -0.001059 | 1674 -> 71.07 | 0 -> 1603 | 1.033 -> 0.9795 |
| `keppler_dd765` | authored | 1474 -> 1488 | 5830 -> 172.2 | -1.407e-06 -> -0.001059 | 1674 -> 71.07 | 0 -> 1603 | 1.033 -> 0.9795 |
| `nields_dd616` | design | 258 -> 268 | 158.1 -> 158.1 | 6.034e-07 -> 0.0001384 | -6.034e-07 -> 2.999 | 0 -> -2.999 | 0.8029 -> 0.8645 |
| `nields_dd616` | commissioned | 258 -> 268 | 2.442e+04 -> 158.1 | 2.808e-06 -> -0.001106 | 1579 -> 72.43 | 0 -> 1507 | 1.02 -> 0.9672 |
| `nields_dd616` | authored | 258 -> 268 | 2.442e+04 -> 158.1 | 2.808e-06 -> -0.001106 | 1579 -> 72.43 | 0 -> 1507 | 1.02 -> 0.9672 |
| `palmer_dms5` | design | 353 -> 355 | 102.7 -> 102.7 | -2.18e-08 -> -0.001657 | 2.18e-08 -> -0.3069 | 0 -> 0.3086 | 0.844 -> 0.8498 |
| `palmer_dms5` | commissioned | 353 -> 355 | 6353 -> 102.7 | -8.37e-06 -> 0.002551 | 866.8 -> 27.56 | 0 -> 839.2 | 0.9221 -> 0.9998 |
| `palmer_dms5` | authored | 353 -> 355 | 6353 -> 102.7 | -8.37e-06 -> 0.002551 | 866.8 -> 27.56 | 0 -> 839.2 | 0.9221 -> 0.9998 |
| `sigsbee_dd502` | design | 303 -> 311 | 141.6 -> 141.6 | 2.799e-07 -> 0.0005555 | -2.799e-07 -> 4.937 | 0 -> -4.938 | 0.797 -> 0.9074 |
| `sigsbee_dd502` | commissioned | 303 -> 311 | 3.669e+04 -> 141.6 | -5.62e-06 -> 0.002512 | 2152 -> 39.62 | 0 -> 2112 | 1.025 -> 1.004 |
| `sigsbee_dd502` | authored | 303 -> 311 | 3.669e+04 -> 141.6 | -5.62e-06 -> 0.002512 | 2152 -> 39.62 | 0 -> 2112 | 1.025 -> 1.004 |

Design-lane after max |dP| is 184 Pa on `cushing_dd376` (before 184 Pa); largest after balance residual is 0.005795 m3/h.

### Flow compare (before -> after)

| hull | path_map entries | native links | kept Crusher paths | synth AHS paths | ambient_opening legs | opening inward m3/h | opening outward sink m3/h | boundary-sink paths | boundary sink out m3/h |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `cannon_de701` | 255 -> 263 | 360 -> 364 | 154 -> 154 | 55 -> 55 | 0 -> 8 | 0 -> 183904 | 0 -> 182733 | 0 -> 14 | 0 -> 182734 |
| `cushing_dd376` | 396 -> 400 | 510 -> 512 | 264 -> 263 | 76 -> 76 | 0 -> 4 | 0 -> 56574.9 | 0 -> 55838.9 | 0 -> 5 | 0 -> 55839.1 |
| `davison_dd618` | 257 -> 267 | 310 -> 315 | 136 -> 136 | 64 -> 64 | 0 -> 10 | 0 -> 198920 | 0 -> 197671 | 0 -> 8 | 0 -> 197672 |
| `fletcher_dde_dd445` | 400 -> 404 | 590 -> 592 | 284 -> 284 | 64 -> 64 | 0 -> 4 | 0 -> 99039 | 0 -> 98509.1 | 0 -> 3 | 0 -> 98509.2 |
| `hunter_killer_dd692` | 887 -> 901 | 1387 -> 1394 | 699 -> 675 | 100 -> 100 | 0 -> 14 | 0 -> 374063 | 0 -> 371633 | 0 -> 10 | 0 -> 371634 |
| `keppler_dd765` | 1474 -> 1488 | 2489 -> 2496 | 1220 -> 1204 | 136 -> 136 | 0 -> 14 | 0 -> 339841 | 0 -> 338238 | 0 -> 12 | 0 -> 338239 |
| `nields_dd616` | 258 -> 268 | 309 -> 314 | 137 -> 134 | 64 -> 64 | 0 -> 10 | 0 -> 205561 | 0 -> 204054 | 0 -> 9 | 0 -> 204055 |
| `palmer_dms5` | 353 -> 355 | 430 -> 431 | 220 -> 208 | 74 -> 74 | 0 -> 2 | 0 -> 33023.9 | 0 -> 32184.7 | 0 -> 3 | 0 -> 32185 |
| `sigsbee_dd502` | 303 -> 311 | 376 -> 380 | 169 -> 169 | 72 -> 72 | 0 -> 8 | 0 -> 151822 | 0 -> 149709 | 0 -> 6 | 0 -> 149709 |

### Paired diagnostic matrix (before -> after)

| hull | cells | max abs move in whole-hull material time h | largest cell |
|---|---:|---:|---|
| `cannon_de701` | 12 | 6.894 | Gun_Deck_Open/native/pulse_t0: 6.908 -> 0.013971 |
| `cushing_dd376` | 12 | 4.587 | Focsle_Open/native/pulse_t0: 4.5921 -> 0.0052795 |
| `davison_dd618` | 12 | 6.982 | Super_Open/commissioned/pulse_t0: 6.9881 -> 0.0061588 |
| `fletcher_dde_dd445` | 12 | 5.995 | Fantail/native/pulse_t0: 6.0022 -> 0.0075045 |
| `hunter_killer_dd692` | 12 | 6.979 | Signal_Bridge/commissioned/pulse_t0: 6.9881 -> 0.0090698 |
| `keppler_dd765` | 12 | 6.983 | Signal_Shelter/native/pulse_t0: 6.9881 -> 0.0049923 |
| `nields_dd616` | 12 | 5.815 | Super_Open/native/pulse_t0: 5.8233 -> 0.0080729 |
| `palmer_dms5` | 12 | 4.541 | Boat_Deck_Uptakes/commissioned/pulse_t0: 4.5578 -> 0.01703 |
| `sigsbee_dd502` | 12 | 6.981 | Midship_Deckhouse/commissioned/pulse_t0: 6.9881 -> 0.0070247 |

### D5 opening records (commissioned outward flow at U=1; axis upper at U=10)

| hull | zone | area_m2 | exchange_m3h | design U=1 out m3/h | commissioned U=1 out m3/h | commissioned U=10 out m3/h | U=1 inward m3/h |
|---|---|---:|---:|---:|---:|---:|---:|
| `cannon_de701` | `Gun_Deck_Open` | 112.32 | 75141.1 | 75156.2 | 75141.1 | 751514.0 | 75171.5 |
| `cannon_de701` | `Island_Open_Aft` | 46.82 | 31006.4 | 31328.4 | 31006.4 | 312992.6 | 31647.4 |
| `cannon_de701` | `Fantail` | 50.57 | 33659.0 | 33838.7 | 33659.0 | 338190.2 | 34015.4 |
| `cannon_de701` | `Focsle_Deck` | 64.26 | 42926.1 | 42998.6 | 42926.1 | 429900.5 | 43069.7 |
| `cushing_dd376` | `Focsle_Open` | 40.74 | 27018.6 | 27167.8 | 27018.6 | 271524.0 | 27315.2 |
| `cushing_dd376` | `Fantail` | 43.55 | 28820.4 | 29041.6 | 28820.4 | 290184.5 | 29259.7 |
| `davison_dd618` | `Super_Open` | 49.65 | 33338.0 | 33338.0 | 33338.0 | 333382.5 | 33337.9 |
| `davison_dd618` | `After_Deckhouse_Top` | 57.16 | 38380.6 | 38380.6 | 38380.6 | 383808.1 | 38380.7 |
| `davison_dd618` | `Midship_Deckhouse` | 56.60 | 38004.5 | 38004.5 | 38004.5 | 380047.7 | 38004.7 |
| `davison_dd618` | `Focsle_Open` | 69.07 | 46377.8 | 46377.8 | 46377.8 | 463780.8 | 46377.7 |
| `davison_dd618` | `Fantail_MS` | 52.98 | 41570.2 | 42195.7 | 41570.2 | 354648.0 | 42818.9 |
| `fletcher_dde_dd445` | `Fantail` | 70.96 | 56460.1 | 56593.3 | 56460.1 | 476357.3 | 56725.2 |
| `fletcher_dde_dd445` | `Focsle_Main` | 52.89 | 42049.1 | 42182.3 | 42049.1 | 355020.4 | 42313.8 |
| `hunter_killer_dd692` | `Signal_Bridge` | 73.18 | 49157.3 | 49157.3 | 49157.3 | 491575.0 | 49157.2 |
| `hunter_killer_dd692` | `Boat_Deck_01` | 89.97 | 71462.1 | 71681.8 | 71462.1 | 603339.9 | 71901.0 |
| `hunter_killer_dd692` | `Launcher_Deck_01` | 54.59 | 42769.4 | 43495.2 | 42769.4 | 365495.7 | 44213.7 |
| `hunter_killer_dd692` | `Fantail` | 67.30 | 53608.0 | 53621.1 | 53608.0 | 451443.8 | 53634.4 |
| `hunter_killer_dd692` | `Torpedo_Deck` | 58.29 | 46183.2 | 46442.4 | 46183.2 | 390797.4 | 46703.7 |
| `hunter_killer_dd692` | `Fwd_Mount_Deck` | 62.65 | 49916.3 | 49916.3 | 49916.3 | 420285.5 | 49916.1 |
| `hunter_killer_dd692` | `Focsle_Fwd` | 73.47 | 58537.1 | 58537.1 | 58537.1 | 492871.1 | 58536.9 |
| `keppler_dd765` | `Signal_Shelter` | 40.33 | 27140.2 | 27140.2 | 27140.2 | 271402.9 | 27140.1 |
| `keppler_dd765` | `Helo_Platform` | 56.43 | 45027.4 | 45040.8 | 45027.4 | 379224.2 | 45053.3 |
| `keppler_dd765` | `Weather_Deck_01` | 83.06 | 66154.6 | 66297.2 | 66154.6 | 558079.4 | 66437.6 |
| `keppler_dd765` | `Forecastle_Top_01` | 70.38 | 56005.4 | 56176.5 | 56005.4 | 472829.2 | 56345.7 |
| `keppler_dd765` | `Fantail` | 58.23 | 46468.5 | 46479.0 | 46468.5 | 391315.5 | 46489.4 |
| `keppler_dd765` | `Gun_Deck_Aft` | 65.90 | 52412.6 | 52601.3 | 52412.6 | 442715.6 | 52791.4 |
| `keppler_dd765` | `Focsle_Fwd` | 56.76 | 45029.5 | 45306.9 | 45029.5 | 381180.7 | 45583.7 |
| `nields_dd616` | `Super_Open` | 63.47 | 42238.2 | 42618.9 | 42238.2 | 425796.5 | 42993.6 |
| `nields_dd616` | `After_Deckhouse_Top` | 61.77 | 41476.0 | 41476.0 | 41476.0 | 414762.6 | 41476.1 |
| `nields_dd616` | `Midship_Deckhouse` | 50.55 | 33942.2 | 33942.2 | 33942.2 | 339424.1 | 33942.4 |
| `nields_dd616` | `Focsle_Open` | 69.58 | 46720.2 | 46720.2 | 46720.2 | 467205.3 | 46720.1 |
| `nields_dd616` | `Fantail` | 50.29 | 39677.8 | 40052.8 | 39677.8 | 336856.3 | 40428.8 |
| `palmer_dms5` | `Boat_Deck_Uptakes` | 48.88 | 32184.7 | 32606.8 | 32184.7 | 325624.5 | 33023.9 |
| `sigsbee_dd502` | `Midship_Deckhouse` | 56.67 | 38076.0 | 38076.0 | 38076.0 | 380758.7 | 38076.2 |
| `sigsbee_dd502` | `Mt2_Deck` | 55.55 | 37092.3 | 37324.6 | 37092.3 | 373000.4 | 37553.4 |
| `sigsbee_dd502` | `Fantail` | 43.55 | 34475.0 | 34706.4 | 34475.0 | 291985.2 | 34939.4 |
| `sigsbee_dd502` | `Focsle_Deck` | 51.02 | 40065.8 | 40661.0 | 40065.8 | 341743.2 | 41252.6 |


## Findings

1. Measured: the design lane already sat inside the stage-1 naval range on all
   nine hulls (47.22–184 Pa) and is unchanged to the printed precision; the
   worst after value is 184 Pa on `cushing_dd376`. Commissioned/authored max |ΔP|
   falls to the same design-lane values on most hulls because the openings
   relieve the previously unvented weather zones.
2. Measured: boundary balance residuals stay at the diagnostic's residual scale
   (largest after |residual| 5.795e-3 m3/h on `hunter_killer_dd692`; before
   values were ~1e-8–7e-4 m3/h with no openings). No hull went unsolved (27/27
   pressure rows solved before and after).
3. Measured: native `ambient_exchange_open_deck` links rise by exactly one per
   record and the ContamX field lane classifies the solved outward legs as
   `ambient_opening` boundary sinks; flow-compare outward sink totals match the
   D5 commissioned outward totals to rounding.
4. Measured: whole-hull material time from a weather source collapses once the
   opening exists (largest moves are the weather `pulse_t0` cells, e.g.
   `cannon_de701/Gun_Deck_Open/native/pulse_t0` 6.908 -> 0.013971 h). Interior
   source cells move much less, as expected for finite weather zones.

## Residuals and open items

1. The `exchange_m3h` values are Grade C solved rates, not measured ship
   ventilation: they are large (27,018.6–75,141.1 m3/h per opening) because the
   area rule is a two-face deck estimate at 1 m/s relative wind. They are
   recorded, not tuned to any anchor.
2. The U=10 column is the axis upper bound only; the committed record keeps the
   fleet default 1 m/s point. A per-hull wind override would move the ContamX
   lane but not the native `exchange_m3h`, the same caveat as cruise.
3. `contam_paired_diagnostic.py` CLI choices still exclude these GA hulls;
   coverage here is via the same `_run_matrix` cells with explicit `--source`,
   not a CLI allow-list change.
