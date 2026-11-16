# CONTAM-AMBIENT-MAKEUP-CRUISE-01
**Date:** 2026-11-16
**Commit:** e8c49684
**Pathogens:** all
**Status:** measured
**Measured at:** e8c49684

## Scope

After-witnesses measured at `e8c49684`; before-witnesses at `origin/main` `8bb227ad`.

Stage 3 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6 for the **cruise hull class only**: `makeup_louvre` `ambient_openings`
records that give the prescribed exhaust sinks of the six cruise hulls a real
ambient make-up path. Per owner ruling D6(a) this entry **discharges the cruise
half of governing-plan stage 6 (`CONTAM-FIELD-ENVELOPE-MAKEUP-01`)**; the
fiction-hull half is a separate, later entry and no fiction hull is touched
here. Machinery: [`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md)
(stage 1) and [`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md)
(stage 2). Evidence base: [`CONTAM-FIELD-PRESSURE-REVIEW-01`](CONTAM-FIELD-PRESSURE-REVIEW-01.md).

Not changed: any `flow_rate_m3h` or exhaust-sink magnitude (the six hulls'
solved prescribed exhaust sinks total 72,960.9 m³/h before and after; the diff
to the six `air_flow_paths.json` files is additions only), `envelope_leak`
area or any exporter constant, the transmission layer, any fiction hull. No
weather-zone, balcony or hatch opening is authored (stages 4-6). No cache was
produced or uploaded and nothing was submitted.

## Records

One record per served room, appended as top-level `ambient_openings`
(D1(a)), `type: makeup_louvre`, `schedule: always_open`.

| hull | zone | area_m2 | served prescribed demand, m³/h | exchange_m3h |
|---|---|---|---|---|
| classic_cruise_1900 | `MainDining_L` | 1.333 | `Galley_Hood_Exhaust` 12,000 | 0.0 |
| diamond_princess | `International` | 2.0 | `Galley_Hood_Exhaust` 18,000 | 0.0 |
| expedition_cruise_450 | `MainDining` | 0.889 | `Galley_Hood_Exhaust` 8,000 | 0.0 |
| greg_mortimer | `DiningRoom` | 0.556 | `Galley_Hood_Exhaust` 5,000 | 0.0 |
| mega_cruise_5000 | `Pool_Bar_Grill` | 0.167 | `Dining_to_Galley_Transfer` 15,000 / 10 rooms = 1,500 | 0.0 |
| mega_cruise_5000 | `Kids_Club` | 0.167 | `Dining_to_Galley_Transfer` 15,000 / 10 rooms = 1,500 | 0.0 |
| mega_cruise_5000 | `Teen_Zone` | 0.167 | `Dining_to_Galley_Transfer` 15,000 / 10 rooms = 1,500 | 0.0 |
| mega_cruise_5000 | `MainDining_L` | 0.167 | `Dining_to_Galley_Transfer` 15,000 / 10 rooms = 1,500 | 0.0 |
| mega_cruise_5000 | `MainDining_U` | 0.167 | `Dining_to_Galley_Transfer` 15,000 / 10 rooms = 1,500 | 0.0 |
| mega_cruise_5000 | `Windjammer` | 0.167 | `Dining_to_Galley_Transfer` 15,000 / 10 rooms = 1,500 | 0.0 |
| mega_cruise_5000 | `SpecRest_A` | 0.167 | `Dining_to_Galley_Transfer` 15,000 / 10 rooms = 1,500 | 0.0 |
| mega_cruise_5000 | `SpecRest_B` | 0.167 | `Dining_to_Galley_Transfer` 15,000 / 10 rooms = 1,500 | 0.0 |
| mega_cruise_5000 | `CafeBakery` | 0.167 | `Dining_to_Galley_Transfer` 15,000 / 10 rooms = 1,500 | 0.0 |
| mega_cruise_5000 | `Ice_Rink_Studio` | 0.167 | `Dining_to_Galley_Transfer` 15,000 / 10 rooms = 1,500 | 0.0 |
| spirit_cruise_3000 | `MainDining_L` | 1.667 | `Galley_Hood_Exhaust` 15,000 | 0.0 |

### Placement (measured on the first hull, then applied by rule)

The louvre is placed on **the room the galley make-up air is drawn from**, not
on the galley. On the five hulls with a `MainGalley -> ambient`
`Galley_Hood_Exhaust` sink, an equal prescribed dining-room → `MainGalley`
transfer already balances the galley, so the hull's air deficit sits in the
dining room. Scratch in-memory sweep on `expedition_cruise_450` at `8bb227ad`
(nothing committed from it):

| louvre | design max \|ΔP\| Pa | commissioned max \|ΔP\| Pa |
|---|---|---|
| none | 715,686 | 981,975 |
| `MainGalley` 0.89 m² | 5,581 | 11,397 |
| `MainGalley` 8.9 m² | 5,572 | 11,377 |
| `MainDining` 0.89 m² | 11.3 | 90.6 |
| `MainDining` 8.9 m² | 1.4 | 66.5 |

Placement, not area, decides the result. `mega_cruise_5000` has no hood sink:
its sink is `Dining_to_Galley_Transfer` leaving HVAC group
`AHU_Network_Aft_Dining_Rec`, which the exporter splits evenly over the group's
ten rooms; an opening record must name a spatial room, so each of the ten rooms
gets one record carrying its 1/10 share.

### Area: `ASSUMED-MAKEUP-LOUVRE-AREA`, Grade C

No drawing gives a louvre on any of the six hulls. Every area is the served
prescribed demand divided by an **assumed 2.5 m/s free-area face velocity**
(`area = Q / 3600 / 2.5`, three decimals). The 2.5 m/s figure is a sizing
assumption that was **not checked against literature or a standard**; it is
applied identically to every record and was not tuned per hull or against any
pressure target. The sweep above shows the result is insensitive to a tenfold
area change, so the grade does not carry the conclusion.

## D5 derivation: native rate from the ContamX-solved range

Method (the precedent for the fiction leg and later stages):

1. Author the opening on the hull and export both field lanes
   (`ahs_terminal_mode` design and commissioned).
2. Solve with ContamX and read `Flow0` on each of the opening's two legs
   (`Flow0` is positive out of the zone).
3. Split the solved flow by direction. Under stage 2 only **outward** flow is a
   contaminant boundary sink; inward flow is clean-air make-up.
4. The native `exchange=True` sink rate is declared inside the measured
   **outward** range. The inward make-up flow is not a native sink rate: the
   native lane already carries that dilution through the prescribed transfer
   and exhaust it feeds.

First hull, `expedition_cruise_450`, `MainDining` 0.889 m²: both legs solve
inward, 3,989.3 and 3,988.9 m³/h at -10.4 Pa (design) and 6,229.0 and
6,228.5 m³/h at -25.3 Pa (commissioned). Measured ranges: **outward 0 to 0
m³/h; inward 7,978 to 12,457 m³/h**. The native axis is therefore declared
`exchange_m3h: 0.0` on each record. It is set per record rather than as
`hvac.ambient_exchange_m3h.makeup_louvre`, so no `hvac` block is edited and the
value sits beside the measurement it comes from.

The same reading on all six hulls (every leg, both lanes; `authored` equals
`commissioned`):

| hull | lane | legs | min leg inward m³/h | max leg inward m³/h | total inward m³/h | outward legs | outward m³/h | max leg \|ΔP\| Pa |
|---|---|---|---|---|---|---|---|---|
| classic_cruise_1900 | design | 2 | 5848.5 | 5849.0 | 11697.5 | 0 | 0 | 9.93 |
| classic_cruise_1900 | commissioned | 2 | 10132.2 | 10133.0 | 20265.2 | 0 | 0 | 29.81 |
| diamond_princess | design | 2 | 8957.1 | 8957.9 | 17915.0 | 0 | 0 | 10.35 |
| diamond_princess | commissioned | 2 | 21733.4 | 21735.3 | 43468.7 | 0 | 0 | 60.96 |
| expedition_cruise_450 | design | 2 | 3988.9 | 3989.3 | 7978.2 | 0 | 0 | 10.37 |
| expedition_cruise_450 | commissioned | 2 | 6228.5 | 6229.0 | 12457.5 | 0 | 0 | 25.28 |
| greg_mortimer | design | 2 | 2491.8 | 2492.0 | 4983.8 | 0 | 0 | 10.32 |
| greg_mortimer | commissioned | 2 | 5268.1 | 5268.5 | 10536.6 | 0 | 0 | 46.14 |
| mega_cruise_5000 | design | 20 | 733.7 | 760.7 | 14875.2 | 0 | 0 | 10.71 |
| mega_cruise_5000 | commissioned | 20 | 2814.5 | 2848.1 | 56662.1 | 0 | 0 | 150.07 |
| spirit_cruise_3000 | design | 2 | 7230.4 | 7231.0 | 14461.5 | 0 | 0 | 9.71 |
| spirit_cruise_3000 | commissioned | 2 | 13624.3 | 13625.5 | 27249.8 | 0 | 0 | 34.47 |

No leg is outward on any hull in any lane, so 0 is inside the measured outward
range everywhere. Scope of this claim: steady solves at the authored placement
with the exporter's ΔT = 0. A louvre placed on a galley did solve one outward
leg in exploratory sweeps, so a different placement must be re-measured, and
the parked ΔT = 0 buoyancy finding of
[`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md) is
carried forward unchanged: with a temperature difference the paired legs can
counterflow and the outward range would no longer be zero.

## Acceptance: design-lane max |ΔP|

| hull | design before Pa | design after Pa | in 0.5-374 Pa | commissioned before Pa | commissioned after Pa |
|---|---|---|---|---|---|
| classic_cruise_1900 | 4.85e5 | 693 | no | 9.89e5 | 1,052 |
| diamond_princess | 2.91e5 | 16.8 | yes | 1.04e6 | 109 |
| expedition_cruise_450 | 7.16e5 | 11.3 | yes | 9.82e5 | 90.7 |
| greg_mortimer | 3.37e5 | 938 | no | 9.77e5 | 44,878 |
| mega_cruise_5000 | 1.76e5 | 21.7 | yes | 1.24e6 | 433 |
| spirit_cruise_3000 | 3.95e5 | 1,213 | no | 8.74e5 | 4,022 |

Every hull's design-lane maximum falls by a factor of 359 (`greg_mortimer`)
to 63,000 (`expedition_cruise_450`); the smallest commissioned-lane factor is
22 (`greg_mortimer`). Three hulls reach the stage-1 plausible range in the
design lane and three do not. Nothing was tuned
to close the gap. The residuals, from the per-path rows (measured rows; the
stated cause is the reading of those rows, not a separate experiment):

- `classic_cruise_1900` design 693 Pa: `LidoBuffet`, `PoolDeck` and `SpaFit`
  each draw 7.3 m³/h through their 0.0001 m² envelope leak at -693 Pa; their
  `Sanitary_Makeup` passive openings to the deck-9 heads solve zero flow, so
  this cluster has no flowing path to the louvred `MainDining_L`. Commissioned
  1,052 Pa is the same cluster plus the deck-9 heads at 9.0 m³/h per leak,
  under an AHS return-minus-supply imbalance of 8,706 m³/h.
- `spirit_cruise_3000` design 1,213 Pa: `MainPool` and `LidoBuffet` draw
  9.5 m³/h per leak at -1,166 Pa while `ArtGallery` sits at +45 Pa; the
  maximum is across the `Cabin_Relief_D*` prescribed links between those two
  clusters. Commissioned 4,022 Pa: deck-10/11 heads at 17.7 m³/h per leak
  (AHS return-minus-supply 13,714 m³/h).
- `greg_mortimer` design 938 Pa: the authored `Dining_Galley_Exhaust`
  transfer solves 5,011.0 m³/h into `MainGalley` and `Galley_Hood_Exhaust`
  removes 4,943.6 m³/h. The 67.4 m³/h surplus pressurises the
  galley/laundry/engine-room cluster to about +930 Pa and leaves through
  eight leaks at 8.4 m³/h each (design envelope net inward is -40.2 m³/h).
  Removing it would mean changing a `flow_rate_m3h`, a non-goal here. Design
  `k` field/native median also moves 0.977 → 0.699 on this hull.
- `greg_mortimer` commissioned 44,878 Pa: `CC_D1_A`, `CC_D1_F` and `HD_2C_M`
  draw 59.1 m³/h per leak at about -44.8 kPa under an AHS
  return-minus-supply imbalance of 6,453 m³/h. That demand is not a
  prescribed exhaust sink and that cluster does not reach `DiningRoom`.

Open after this entry: the residual clusters above are make-up demand that is
not a prescribed exhaust sink (AHS imbalance, sanitary branches) or a
transfer/exhaust mismatch in authored data. Neither is addressed by a louvre on
the served room, and both remain for the governing plan.

## Balance residual

`tools/diag/contam_pressure_balance_diagnostic.py` computed
`balance_residual_m3h = make-up demand - envelope-leak net inflow`. With a
louvre that reads the louvre's own inflow as an imbalance (7,978 m³/h on
`expedition_cruise_450` design) although the hull conserves. `summarize_boundary`
now reports `ambient_opening_net_inward_m3h` and subtracts it, so the residual
is demand minus everything the boundary admits. It is identical to the old
definition on any hull without an opening. Under the amended definition the
residual is at most 1.2e-3 m³/h in magnitude on every hull and lane before and
after (table below); under the old definition the after value would equal the
"opening in" column.

## Bundles and design pins

- The six committed `data/platforms/<hull>/contam/platform.prj` and
  `path_map.json` bundles are regenerated in commissioned mode. Before
  regenerating, the same export with `ambient_openings` removed in memory
  reproduced all six committed bundles byte-for-byte, so the bundle diff is
  this change alone. Path-map entries: classic 836 → 838, diamond 1,771 →
  1,773, expedition 343 → 345, greg 356 → 358, mega 2,573 → 2,593, spirit
  1,303 → 1,305 (two legs per record).
- `tools/contam_commissioned_check.py` on the six hulls: PASS, every
  commissioned terminal solves inside 5% of declared. ContamX converged on
  every hull and lane.
- `campaigns/contam/phase2_cruise_contrasts_01`: the `_02` successor design
  (`design/phase2_cruise_contrasts_design_v2.json`) is rebuilt in place under
  the same design id, as in
  [`CONTAM-FIELD-POOLDECK-OPENINGS-01`](CONTAM-FIELD-POOLDECK-OPENINGS-01.md):
  only the four hull-panel `path_map_entries` move (panel total 5,055 →
  5,081); `source_pools_v2.json` and `campaign_v2.json` are byte-identical.
  No `_02` field cache has been produced, so no successor beyond `_02` is
  needed. The `_01` design, pools, campaign and readouts are byte-untouched.
  The test pin `test_v2_hull_panel_tracks_current_platform_jsons` moves with
  those four counts.
- Moved test expectations, each attributed to the authored records: the
  stage-1/2 guards `test_no_committed_platform_declares_an_opening` and
  `test_no_committed_path_map_declares_an_ambient_opening` become guards that
  exactly the six cruise hulls declare make-up louvres (1 record each, 10 on
  mega; 2 legs per record) at native rate 0.
- `campaigns/contam/phase1_hvac_tracer_01`: rebuilding the `_02` successor is
  a no-op (no file changes); `_01` byte-untouched.

## Witnesses

Runner: `tools/diag/ambient_makeup_witness.py --label <before|after>`, then
`--compare before after`. It drives the pressure-balance diagnostic (design,
commissioned, authored lanes, all paths), `tools/contam_flow_compare.py`,
`tools/diag/contam_paired_diagnostic.py` and the
`tools/diag/forced_exhaust_audit.py exact-check` on each hull. "Before" was run
in a worktree of `origin/main` `8bb227ad` carrying only the three changed
diagnostic tools. `contam_paired_diagnostic.py` previously knew only
`expedition_cruise_450` among these hulls; the other five are added as opt-in
`--hull` choices and its bare invocation is unchanged.

Native lane: native material times are identical before and after in every
cell, and each record appears as a native `ambient_exchange_makeup_louvre`
link at 0 m³/h. Field lanes: material times move where the louvre changes the
solved flow field, most on the commissioned lane (for example
`greg_mortimer` `DiningRoom` 0.131 → 0.241 h).

### Pressure balance (before -> after)

| hull | lane | paths | max dP Pa | interior flowing max dP Pa | exhaust sinks m3/h | envelope net in m3/h | opening in m3/h | opening out m3/h | opening max dP Pa | balance residual m3/h | k field/native median |
|---|---|---|---|---|---|---|---|---|---|---|---|
| classic_cruise_1900 | design | 836 -> 838 | 4.847e+05 -> 693.5 | 265.9 -> 683.6 | 1.2e+04 -> 1.2e+04 | 1.2e+04 -> 305.5 | 1.17e+04 | 0 | 9.933 | -0.0006907 -> -0.0005855 | 0.9968 -> 0.9968 |
| classic_cruise_1900 | commissioned | 836 -> 838 | 9.888e+05 -> 1052 | 458.2 -> 1002 | 1.2e+04 -> 1.2e+04 | 2.071e+04 -> 443.9 | 2.027e+04 | 0 | 29.81 | -0.0007353 -> -0.000706 | 1.005 -> 1 |
| classic_cruise_1900 | authored | 836 -> 838 | 9.888e+05 -> 1052 | 458.2 -> 1002 | 1.2e+04 -> 1.2e+04 | 2.071e+04 -> 443.9 | 2.027e+04 | 0 | 29.81 | -0.0007353 -> -0.000706 | 1.005 -> 1 |
| diamond_princess | design | 1771 -> 1773 | 2.913e+05 -> 16.79 | 25.05 -> 14.54 | 1.8e+04 -> 1.8e+04 | 1.8e+04 -> 85.03 | 1.791e+04 | 0 | 10.35 | -1.114e-05 -> 0.0001748 | 1.073 -> 0.9978 |
| diamond_princess | commissioned | 1771 -> 1773 | 1.043e+06 -> 108.8 | 21.48 -> 23.36 | 1.8e+04 -> 1.8e+04 | 4.387e+04 -> 404.7 | 4.347e+04 | 0 | 60.96 | 4.455e-05 -> 0.0001761 | 1.021 -> 1 |
| diamond_princess | authored | 1771 -> 1773 | 1.043e+06 -> 108.8 | 21.48 -> 23.36 | 1.8e+04 -> 1.8e+04 | 4.387e+04 -> 404.7 | 4.347e+04 | 0 | 60.96 | 4.455e-05 -> 0.0001761 | 1.021 -> 1 |
| expedition_cruise_450 | design | 343 -> 345 | 7.157e+05 -> 11.34 | 446.5 -> 1.006 | 8009 -> 8009 | 8009 -> 30.67 | 7978 | 0 | 10.37 | -0.0002899 -> -0.0004635 | 1.077 -> 0.9627 |
| expedition_cruise_450 | commissioned | 343 -> 345 | 9.82e+05 -> 90.65 | 612.6 -> 63.79 | 8009 -> 8009 | 1.254e+04 -> 87.17 | 1.246e+04 | 0 | 25.28 | -0.0003122 -> -0.0006477 | 1.081 -> 1.001 |
| expedition_cruise_450 | authored | 343 -> 345 | 9.82e+05 -> 90.65 | 612.6 -> 63.79 | 8009 -> 8009 | 1.254e+04 -> 87.17 | 1.246e+04 | 0 | 25.28 | -0.0003122 -> -0.0006477 | 1.081 -> 1.001 |
| greg_mortimer | design | 356 -> 358 | 3.373e+05 -> 938.4 | 302.6 -> 3.563 | 4944 -> 4944 | 4944 -> -40.21 | 4984 | 0 | 10.32 | 0.0002002 -> 0.0001553 | 0.9768 -> 0.6989 |
| greg_mortimer | commissioned | 356 -> 358 | 9.769e+05 -> 4.488e+04 | 221.4 -> 554.2 | 4944 -> 4944 | 1.14e+04 -> 859.8 | 1.054e+04 | 0 | 46.14 | 4.465e-05 -> 3.994e-05 | 1.011 -> 1.011 |
| greg_mortimer | authored | 356 -> 358 | 9.769e+05 -> 4.488e+04 | 221.4 -> 554.2 | 4944 -> 4944 | 1.14e+04 -> 859.8 | 1.054e+04 | 0 | 46.14 | 4.465e-05 -> 3.994e-05 | 1.011 -> 1.011 |
| mega_cruise_5000 | design | 2573 -> 2593 | 1.76e+05 -> 21.7 | 17.49 -> 11.47 | 1.5e+04 -> 1.5e+04 | 1.5e+04 -> 127.6 | 1.488e+04 | 0 | 10.71 | -0.0008578 -> -0.0007321 | 0.9951 -> 0.9951 |
| mega_cruise_5000 | commissioned | 2573 -> 2593 | 1.236e+06 -> 433.3 | 122.8 -> 283 | 1.5e+04 -> 1.5e+04 | 5.734e+04 -> 676.1 | 5.666e+04 | 0 | 150.1 | -0.0008689 -> -0.001223 | 1.011 -> 1 |
| mega_cruise_5000 | authored | 2573 -> 2593 | 1.236e+06 -> 433.3 | 122.8 -> 283 | 1.5e+04 -> 1.5e+04 | 5.734e+04 -> 676.1 | 5.666e+04 | 0 | 150.1 | -0.0008689 -> -0.001223 | 1.011 -> 1 |
| spirit_cruise_3000 | design | 1303 -> 1305 | 3.948e+05 -> 1213 | 8119 -> 1189 | 1.5e+04 -> 1.5e+04 | 1.5e+04 -> 541.1 | 1.446e+04 | 0 | 9.709 | 0.0001114 -> 1.284e-05 | 0.998 -> 0.997 |
| spirit_cruise_3000 | commissioned | 1303 -> 1305 | 8.737e+05 -> 4022 | 1.241e+04 -> 2105 | 1.5e+04 -> 1.5e+04 | 2.872e+04 -> 1467 | 2.725e+04 | 0 | 34.47 | 2.228e-05 -> -0.0001744 | 1 -> 1.006 |
| spirit_cruise_3000 | authored | 1303 -> 1305 | 8.737e+05 -> 4022 | 1.241e+04 -> 2105 | 1.5e+04 -> 1.5e+04 | 2.872e+04 -> 1467 | 2.725e+04 | 0 | 34.47 | 2.228e-05 -> -0.0001744 | 1 -> 1.006 |

### Flow compare (before -> after)

| hull | path_map entries | native links | kept Crusher paths | synth AHS paths | ambient_opening legs | opening inward m3/h | opening outward sink m3/h | native ambient_exchange links / total m3/h |
|---|---|---|---|---|---|---|---|---|
| classic_cruise_1900 | 836 -> 838 | 736 -> 737 | 462 -> 510 | 139 -> 139 | 0 -> 2 | 0 -> 20265.2 | 0 -> 0 | 1 / 0 |
| diamond_princess | 1771 -> 1773 | 1557 -> 1558 | 968 -> 1103 | 263 -> 263 | 0 -> 2 | 0 -> 43468.7 | 0 -> 0 | 1 / 0 |
| expedition_cruise_450 | 343 -> 345 | 272 -> 273 | 106 -> 137 | 79 -> 79 | 0 -> 2 | 0 -> 12457.5 | 0 -> 0 | 1 / 0 |
| greg_mortimer | 356 -> 358 | 287 -> 288 | 137 -> 149 | 79 -> 79 | 0 -> 2 | 0 -> 10536.6 | 0 -> 0 | 1 / 0 |
| mega_cruise_5000 | 2573 -> 2593 | 2291 -> 2301 | 1553 -> 1725 | 311 -> 311 | 0 -> 20 | 0 -> 56662.1 | 0 -> 0 | 10 / 0 |
| spirit_cruise_3000 | 1303 -> 1305 | 1141 -> 1142 | 727 -> 766 | 196 -> 196 | 0 -> 2 | 0 -> 27249.8 | 0 -> 0 | 1 / 0 |

### Whole-hull material time, h (pressure diagnostic source cells)

| hull | source / timing / lane | before | after |
|---|---|---|---|
| classic_cruise_1900 | MainDining_L/pulse_t0/design | 0.203 | 0.2073 |
| classic_cruise_1900 | MainDining_L/pulse_t0/native | 0.1726 | 0.1726 |
| classic_cruise_1900 | MainDining_L/split_t0_t1/design | 0.203 | 0.2073 |
| classic_cruise_1900 | MainDining_L/split_t0_t1/native | 0.1726 | 0.1726 |
| classic_cruise_1900 | MainGalley/pulse_t0/design | 0.106 | 0.1035 |
| classic_cruise_1900 | MainGalley/pulse_t0/native | 0.09452 | 0.09452 |
| classic_cruise_1900 | MainGalley/split_t0_t1/design | 0.106 | 0.1035 |
| classic_cruise_1900 | MainGalley/split_t0_t1/native | 0.09452 | 0.09452 |
| classic_cruise_1900 | MainDining_L/pulse_t0/commissioned | 0.1953 | 0.2208 |
| classic_cruise_1900 | MainDining_L/pulse_t0/native | 0.1726 | 0.1726 |
| classic_cruise_1900 | MainDining_L/split_t0_t1/commissioned | 0.1953 | 0.2208 |
| classic_cruise_1900 | MainDining_L/split_t0_t1/native | 0.1726 | 0.1726 |
| classic_cruise_1900 | MainGalley/pulse_t0/commissioned | 0.1057 | 0.1099 |
| classic_cruise_1900 | MainGalley/pulse_t0/native | 0.09452 | 0.09452 |
| classic_cruise_1900 | MainGalley/split_t0_t1/commissioned | 0.1057 | 0.1099 |
| classic_cruise_1900 | MainGalley/split_t0_t1/native | 0.09452 | 0.09452 |
| classic_cruise_1900 | MainDining_L/pulse_t0/authored | 0.1953 | 0.2208 |
| classic_cruise_1900 | MainDining_L/pulse_t0/native | 0.1726 | 0.1726 |
| classic_cruise_1900 | MainDining_L/split_t0_t1/authored | 0.1953 | 0.2208 |
| classic_cruise_1900 | MainDining_L/split_t0_t1/native | 0.1726 | 0.1726 |
| classic_cruise_1900 | MainGalley/pulse_t0/authored | 0.1057 | 0.1099 |
| classic_cruise_1900 | MainGalley/pulse_t0/native | 0.09452 | 0.09452 |
| classic_cruise_1900 | MainGalley/split_t0_t1/authored | 0.1057 | 0.1099 |
| classic_cruise_1900 | MainGalley/split_t0_t1/native | 0.09452 | 0.09452 |
| diamond_princess | International/pulse_t0/design | 0.2523 | 0.2621 |
| diamond_princess | International/pulse_t0/native | 0.2337 | 0.2337 |
| diamond_princess | International/split_t0_t1/design | 0.2523 | 0.2621 |
| diamond_princess | International/split_t0_t1/native | 0.2337 | 0.2337 |
| diamond_princess | MainGalley/pulse_t0/design | 0.1071 | 0.09058 |
| diamond_princess | MainGalley/pulse_t0/native | 0.08395 | 0.08395 |
| diamond_princess | MainGalley/split_t0_t1/design | 0.1071 | 0.09058 |
| diamond_princess | MainGalley/split_t0_t1/native | 0.08395 | 0.08395 |
| diamond_princess | International/pulse_t0/commissioned | 0.2491 | 0.3748 |
| diamond_princess | International/pulse_t0/native | 0.2337 | 0.2337 |
| diamond_princess | International/split_t0_t1/commissioned | 0.2491 | 0.3748 |
| diamond_princess | International/split_t0_t1/native | 0.2337 | 0.2337 |
| diamond_princess | MainGalley/pulse_t0/commissioned | 0.1021 | 0.08522 |
| diamond_princess | MainGalley/pulse_t0/native | 0.08395 | 0.08395 |
| diamond_princess | MainGalley/split_t0_t1/commissioned | 0.1021 | 0.08522 |
| diamond_princess | MainGalley/split_t0_t1/native | 0.08395 | 0.08395 |
| diamond_princess | International/pulse_t0/authored | 0.2491 | 0.3748 |
| diamond_princess | International/pulse_t0/native | 0.2337 | 0.2337 |
| diamond_princess | International/split_t0_t1/authored | 0.2491 | 0.3748 |
| diamond_princess | International/split_t0_t1/native | 0.2337 | 0.2337 |
| diamond_princess | MainGalley/pulse_t0/authored | 0.1021 | 0.08522 |
| diamond_princess | MainGalley/pulse_t0/native | 0.08395 | 0.08395 |
| diamond_princess | MainGalley/split_t0_t1/authored | 0.1021 | 0.08522 |
| diamond_princess | MainGalley/split_t0_t1/native | 0.08395 | 0.08395 |
| expedition_cruise_450 | MainDining/pulse_t0/design | 0.1886 | 0.1898 |
| expedition_cruise_450 | MainDining/pulse_t0/native | 0.1768 | 0.1768 |
| expedition_cruise_450 | MainDining/split_t0_t1/design | 0.1886 | 0.1898 |
| expedition_cruise_450 | MainDining/split_t0_t1/native | 0.1768 | 0.1768 |
| expedition_cruise_450 | MainGalley/pulse_t0/design | 0.1036 | 0.1015 |
| expedition_cruise_450 | MainGalley/pulse_t0/native | 0.08685 | 0.08685 |
| expedition_cruise_450 | MainGalley/split_t0_t1/design | 0.1036 | 0.1015 |
| expedition_cruise_450 | MainGalley/split_t0_t1/native | 0.08685 | 0.08685 |
| expedition_cruise_450 | MainDining/pulse_t0/commissioned | 0.1913 | 0.2803 |
| expedition_cruise_450 | MainDining/pulse_t0/native | 0.1768 | 0.1768 |
| expedition_cruise_450 | MainDining/split_t0_t1/commissioned | 0.1913 | 0.2802 |
| expedition_cruise_450 | MainDining/split_t0_t1/native | 0.1768 | 0.1768 |
| expedition_cruise_450 | MainGalley/pulse_t0/commissioned | 0.1068 | 0.1073 |
| expedition_cruise_450 | MainGalley/pulse_t0/native | 0.08685 | 0.08685 |
| expedition_cruise_450 | MainGalley/split_t0_t1/commissioned | 0.1068 | 0.1073 |
| expedition_cruise_450 | MainGalley/split_t0_t1/native | 0.08685 | 0.08685 |
| expedition_cruise_450 | MainDining/pulse_t0/authored | 0.1913 | 0.2803 |
| expedition_cruise_450 | MainDining/pulse_t0/native | 0.1768 | 0.1768 |
| expedition_cruise_450 | MainDining/split_t0_t1/authored | 0.1913 | 0.2802 |
| expedition_cruise_450 | MainDining/split_t0_t1/native | 0.1768 | 0.1768 |
| expedition_cruise_450 | MainGalley/pulse_t0/authored | 0.1068 | 0.1073 |
| expedition_cruise_450 | MainGalley/pulse_t0/native | 0.08685 | 0.08685 |
| expedition_cruise_450 | MainGalley/split_t0_t1/authored | 0.1068 | 0.1073 |
| expedition_cruise_450 | MainGalley/split_t0_t1/native | 0.08685 | 0.08685 |
| greg_mortimer | DiningRoom/pulse_t0/design | 0.1587 | 0.159 |
| greg_mortimer | DiningRoom/pulse_t0/native | 0.1323 | 0.1323 |
| greg_mortimer | DiningRoom/split_t0_t1/design | 0.1587 | 0.159 |
| greg_mortimer | DiningRoom/split_t0_t1/native | 0.1323 | 0.1323 |
| greg_mortimer | MainGalley/pulse_t0/design | 0.08477 | 0.08477 |
| greg_mortimer | MainGalley/pulse_t0/native | 0.05768 | 0.05768 |
| greg_mortimer | MainGalley/split_t0_t1/design | 0.08477 | 0.08477 |
| greg_mortimer | MainGalley/split_t0_t1/native | 0.05768 | 0.05768 |
| greg_mortimer | DiningRoom/pulse_t0/commissioned | 0.1311 | 0.2408 |
| greg_mortimer | DiningRoom/pulse_t0/native | 0.1323 | 0.1323 |
| greg_mortimer | DiningRoom/split_t0_t1/commissioned | 0.1311 | 0.2408 |
| greg_mortimer | DiningRoom/split_t0_t1/native | 0.1323 | 0.1323 |
| greg_mortimer | MainGalley/pulse_t0/commissioned | 0.05932 | 0.05932 |
| greg_mortimer | MainGalley/pulse_t0/native | 0.05768 | 0.05768 |
| greg_mortimer | MainGalley/split_t0_t1/commissioned | 0.05932 | 0.05932 |
| greg_mortimer | MainGalley/split_t0_t1/native | 0.05768 | 0.05768 |
| greg_mortimer | DiningRoom/pulse_t0/authored | 0.1311 | 0.2408 |
| greg_mortimer | DiningRoom/pulse_t0/native | 0.1323 | 0.1323 |
| greg_mortimer | DiningRoom/split_t0_t1/authored | 0.1311 | 0.2408 |
| greg_mortimer | DiningRoom/split_t0_t1/native | 0.1323 | 0.1323 |
| greg_mortimer | MainGalley/pulse_t0/authored | 0.05932 | 0.05932 |
| greg_mortimer | MainGalley/pulse_t0/native | 0.05768 | 0.05768 |
| greg_mortimer | MainGalley/split_t0_t1/authored | 0.05932 | 0.05932 |
| greg_mortimer | MainGalley/split_t0_t1/native | 0.05768 | 0.05768 |
| mega_cruise_5000 | MainDining_L/pulse_t0/design | 0.5581 | 0.5665 |
| mega_cruise_5000 | MainDining_L/pulse_t0/native | 0.3659 | 0.3659 |
| mega_cruise_5000 | MainDining_L/split_t0_t1/design | 0.5581 | 0.5664 |
| mega_cruise_5000 | MainDining_L/split_t0_t1/native | 0.3658 | 0.3658 |
| mega_cruise_5000 | Windjammer/pulse_t0/design | 0.5665 | 0.5986 |
| mega_cruise_5000 | Windjammer/pulse_t0/native | 0.3681 | 0.3681 |
| mega_cruise_5000 | Windjammer/split_t0_t1/design | 0.5664 | 0.5979 |
| mega_cruise_5000 | Windjammer/split_t0_t1/native | 0.3681 | 0.3681 |
| mega_cruise_5000 | MainDining_L/pulse_t0/commissioned | 0.3698 | 0.4259 |
| mega_cruise_5000 | MainDining_L/pulse_t0/native | 0.3659 | 0.3659 |
| mega_cruise_5000 | MainDining_L/split_t0_t1/commissioned | 0.3698 | 0.4257 |
| mega_cruise_5000 | MainDining_L/split_t0_t1/native | 0.3658 | 0.3658 |
| mega_cruise_5000 | Windjammer/pulse_t0/commissioned | 0.3698 | 0.4337 |
| mega_cruise_5000 | Windjammer/pulse_t0/native | 0.3681 | 0.3681 |
| mega_cruise_5000 | Windjammer/split_t0_t1/commissioned | 0.3698 | 0.4335 |
| mega_cruise_5000 | Windjammer/split_t0_t1/native | 0.3681 | 0.3681 |
| mega_cruise_5000 | MainDining_L/pulse_t0/authored | 0.3698 | 0.4259 |
| mega_cruise_5000 | MainDining_L/pulse_t0/native | 0.3659 | 0.3659 |
| mega_cruise_5000 | MainDining_L/split_t0_t1/authored | 0.3698 | 0.4257 |
| mega_cruise_5000 | MainDining_L/split_t0_t1/native | 0.3658 | 0.3658 |
| mega_cruise_5000 | Windjammer/pulse_t0/authored | 0.3698 | 0.4337 |
| mega_cruise_5000 | Windjammer/pulse_t0/native | 0.3681 | 0.3681 |
| mega_cruise_5000 | Windjammer/split_t0_t1/authored | 0.3698 | 0.4335 |
| mega_cruise_5000 | Windjammer/split_t0_t1/native | 0.3681 | 0.3681 |
| spirit_cruise_3000 | MainDining_L/pulse_t0/design | 0.2116 | 0.2061 |
| spirit_cruise_3000 | MainDining_L/pulse_t0/native | 0.1746 | 0.1746 |
| spirit_cruise_3000 | MainDining_L/split_t0_t1/design | 0.2116 | 0.2061 |
| spirit_cruise_3000 | MainDining_L/split_t0_t1/native | 0.1746 | 0.1746 |
| spirit_cruise_3000 | MainGalley/pulse_t0/design | 0.1172 | 0.1024 |
| spirit_cruise_3000 | MainGalley/pulse_t0/native | 0.09267 | 0.09267 |
| spirit_cruise_3000 | MainGalley/split_t0_t1/design | 0.1172 | 0.1024 |
| spirit_cruise_3000 | MainGalley/split_t0_t1/native | 0.09267 | 0.09267 |
| spirit_cruise_3000 | MainDining_L/pulse_t0/commissioned | 0.2013 | 0.1995 |
| spirit_cruise_3000 | MainDining_L/pulse_t0/native | 0.1746 | 0.1746 |
| spirit_cruise_3000 | MainDining_L/split_t0_t1/commissioned | 0.2013 | 0.1995 |
| spirit_cruise_3000 | MainDining_L/split_t0_t1/native | 0.1746 | 0.1746 |
| spirit_cruise_3000 | MainGalley/pulse_t0/commissioned | 0.1183 | 0.09468 |
| spirit_cruise_3000 | MainGalley/pulse_t0/native | 0.09267 | 0.09267 |
| spirit_cruise_3000 | MainGalley/split_t0_t1/commissioned | 0.1183 | 0.09468 |
| spirit_cruise_3000 | MainGalley/split_t0_t1/native | 0.09267 | 0.09267 |
| spirit_cruise_3000 | MainDining_L/pulse_t0/authored | 0.2013 | 0.1995 |
| spirit_cruise_3000 | MainDining_L/pulse_t0/native | 0.1746 | 0.1746 |
| spirit_cruise_3000 | MainDining_L/split_t0_t1/authored | 0.2013 | 0.1995 |
| spirit_cruise_3000 | MainDining_L/split_t0_t1/native | 0.1746 | 0.1746 |
| spirit_cruise_3000 | MainGalley/pulse_t0/authored | 0.1183 | 0.09468 |
| spirit_cruise_3000 | MainGalley/pulse_t0/native | 0.09267 | 0.09267 |
| spirit_cruise_3000 | MainGalley/split_t0_t1/authored | 0.1183 | 0.09468 |
| spirit_cruise_3000 | MainGalley/split_t0_t1/native | 0.09267 | 0.09267 |

### Paired diagnostic matrix (before -> after)

| hull | source | lane | timing | whole-hull material time h | transport loss | closure error |
|---|---|---|---|---|---|---|
| classic_cruise_1900 | MainDining_L | native | pulse_t0 | 0.1726 -> 0.1726 | 0.9827 -> 0.9827 | -2.22e-16 -> -2.22e-16 |
| classic_cruise_1900 | MainDining_L | native | split_t0_t1 | 0.1726 -> 0.1726 | 0.9827 -> 0.9827 | 2.22e-16 -> 2.22e-16 |
| classic_cruise_1900 | MainGalley | native | pulse_t0 | 0.09452 -> 0.09452 | 0.9905 -> 0.9905 | -1.11e-16 -> -1.11e-16 |
| classic_cruise_1900 | MainGalley | native | split_t0_t1 | 0.09452 -> 0.09452 | 0.9905 -> 0.9905 | -2.22e-16 -> -2.22e-16 |
| classic_cruise_1900 | MainDining_L | commissioned | pulse_t0 | 0.1953 -> 0.2208 | 0.9805 -> 0.9779 | 2.22e-16 -> 1.11e-16 |
| classic_cruise_1900 | MainDining_L | commissioned | split_t0_t1 | 0.1953 -> 0.2208 | 0.9805 -> 0.9779 | -1.11e-16 -> -1.11e-16 |
| classic_cruise_1900 | MainGalley | commissioned | pulse_t0 | 0.1057 -> 0.1099 | 0.9894 -> 0.989 | -2.22e-16 -> 0 |
| classic_cruise_1900 | MainGalley | commissioned | split_t0_t1 | 0.1057 -> 0.1099 | 0.9894 -> 0.989 | -5.551e-16 -> -1.11e-16 |
| classic_cruise_1900 | MainDining_L | authored | pulse_t0 | 0.1953 -> 0.2208 | 0.9805 -> 0.9779 | 2.22e-16 -> 1.11e-16 |
| classic_cruise_1900 | MainDining_L | authored | split_t0_t1 | 0.1953 -> 0.2208 | 0.9805 -> 0.9779 | -1.11e-16 -> -1.11e-16 |
| classic_cruise_1900 | MainGalley | authored | pulse_t0 | 0.1057 -> 0.1099 | 0.9894 -> 0.989 | -2.22e-16 -> 0 |
| classic_cruise_1900 | MainGalley | authored | split_t0_t1 | 0.1057 -> 0.1099 | 0.9894 -> 0.989 | -5.551e-16 -> -1.11e-16 |
| diamond_princess | International | native | pulse_t0 | 0.2337 -> 0.2337 | 0.9766 -> 0.9766 | 1.11e-16 -> 1.11e-16 |
| diamond_princess | International | native | split_t0_t1 | 0.2337 -> 0.2337 | 0.9766 -> 0.9766 | 2.22e-16 -> 2.22e-16 |
| diamond_princess | MainGalley | native | pulse_t0 | 0.08395 -> 0.08395 | 0.9916 -> 0.9916 | -1.11e-16 -> -1.11e-16 |
| diamond_princess | MainGalley | native | split_t0_t1 | 0.08395 -> 0.08395 | 0.9916 -> 0.9916 | 2.22e-16 -> 2.22e-16 |
| diamond_princess | International | commissioned | pulse_t0 | 0.2491 -> 0.3748 | 0.9751 -> 0.9625 | 4.441e-16 -> 6.661e-16 |
| diamond_princess | International | commissioned | split_t0_t1 | 0.2491 -> 0.3748 | 0.9751 -> 0.9625 | 5.551e-16 -> 3.331e-16 |
| diamond_princess | MainGalley | commissioned | pulse_t0 | 0.1021 -> 0.08522 | 0.9898 -> 0.9915 | 4.441e-16 -> 2.22e-16 |
| diamond_princess | MainGalley | commissioned | split_t0_t1 | 0.1021 -> 0.08522 | 0.9898 -> 0.9915 | 3.331e-16 -> -1.11e-16 |
| diamond_princess | International | authored | pulse_t0 | 0.2491 -> 0.3748 | 0.9751 -> 0.9625 | 4.441e-16 -> 6.661e-16 |
| diamond_princess | International | authored | split_t0_t1 | 0.2491 -> 0.3748 | 0.9751 -> 0.9625 | 5.551e-16 -> 3.331e-16 |
| diamond_princess | MainGalley | authored | pulse_t0 | 0.1021 -> 0.08522 | 0.9898 -> 0.9915 | 4.441e-16 -> 2.22e-16 |
| diamond_princess | MainGalley | authored | split_t0_t1 | 0.1021 -> 0.08522 | 0.9898 -> 0.9915 | 3.331e-16 -> -1.11e-16 |
| expedition_cruise_450 | MainDining | native | pulse_t0 | 0.1768 -> 0.1768 | 0.9823 -> 0.9823 | 1.11e-16 -> 1.11e-16 |
| expedition_cruise_450 | MainDining | native | split_t0_t1 | 0.1768 -> 0.1768 | 0.9823 -> 0.9823 | 0 -> 0 |
| expedition_cruise_450 | HD_5P_M | native | pulse_t0 | 0.05181 -> 0.05181 | 0.9948 -> 0.9948 | 1.11e-16 -> 1.11e-16 |
| expedition_cruise_450 | HD_5P_M | native | split_t0_t1 | 0.05181 -> 0.05181 | 0.9948 -> 0.9948 | 0 -> 0 |
| expedition_cruise_450 | PoolDeck | native | pulse_t0 | 2.602 -> 2.602 | 0.7325 -> 0.7325 | -1.443e-15 -> -1.443e-15 |
| expedition_cruise_450 | PoolDeck | native | split_t0_t1 | 2.598 -> 2.598 | 0.731 -> 0.731 | -1.221e-15 -> -1.221e-15 |
| expedition_cruise_450 | MainGalley | native | pulse_t0 | 0.08685 -> 0.08685 | 0.9913 -> 0.9913 | -3.331e-16 -> -3.331e-16 |
| expedition_cruise_450 | MainGalley | native | split_t0_t1 | 0.08685 -> 0.08685 | 0.9913 -> 0.9913 | -2.22e-16 -> -2.22e-16 |
| expedition_cruise_450 | MainDining | commissioned | pulse_t0 | 0.1913 -> 0.2803 | 0.9809 -> 0.972 | -1.11e-16 -> 0 |
| expedition_cruise_450 | MainDining | commissioned | split_t0_t1 | 0.1913 -> 0.2802 | 0.9809 -> 0.972 | -1.11e-16 -> 1.11e-16 |
| expedition_cruise_450 | HD_5P_M | commissioned | pulse_t0 | 0.05176 -> 0.05176 | 0.9948 -> 0.9948 | 2.22e-16 -> 2.22e-16 |
| expedition_cruise_450 | HD_5P_M | commissioned | split_t0_t1 | 0.05176 -> 0.05176 | 0.9948 -> 0.9948 | 1.11e-16 -> 0 |
| expedition_cruise_450 | PoolDeck | commissioned | pulse_t0 | 1.071 -> 1.838 | 0.8929 -> 0.8158 | 0 -> -7.772e-16 |
| expedition_cruise_450 | PoolDeck | commissioned | split_t0_t1 | 1.071 -> 1.837 | 0.8929 -> 0.8157 | 1.11e-16 -> -3.331e-16 |
| expedition_cruise_450 | MainGalley | commissioned | pulse_t0 | 0.1068 -> 0.1073 | 0.9893 -> 0.9893 | 1.11e-16 -> 1.11e-16 |
| expedition_cruise_450 | MainGalley | commissioned | split_t0_t1 | 0.1068 -> 0.1073 | 0.9893 -> 0.9893 | 1.11e-16 -> 2.22e-16 |
| expedition_cruise_450 | MainDining | authored | pulse_t0 | 0.1913 -> 0.2803 | 0.9809 -> 0.972 | -1.11e-16 -> 0 |
| expedition_cruise_450 | MainDining | authored | split_t0_t1 | 0.1913 -> 0.2802 | 0.9809 -> 0.972 | -1.11e-16 -> 1.11e-16 |
| expedition_cruise_450 | HD_5P_M | authored | pulse_t0 | 0.05176 -> 0.05176 | 0.9948 -> 0.9948 | 2.22e-16 -> 2.22e-16 |
| expedition_cruise_450 | HD_5P_M | authored | split_t0_t1 | 0.05176 -> 0.05176 | 0.9948 -> 0.9948 | 1.11e-16 -> 0 |
| expedition_cruise_450 | PoolDeck | authored | pulse_t0 | 1.071 -> 1.838 | 0.8929 -> 0.8158 | 0 -> -7.772e-16 |
| expedition_cruise_450 | PoolDeck | authored | split_t0_t1 | 1.071 -> 1.837 | 0.8929 -> 0.8157 | 1.11e-16 -> -3.331e-16 |
| expedition_cruise_450 | MainGalley | authored | pulse_t0 | 0.1068 -> 0.1073 | 0.9893 -> 0.9893 | 1.11e-16 -> 1.11e-16 |
| expedition_cruise_450 | MainGalley | authored | split_t0_t1 | 0.1068 -> 0.1073 | 0.9893 -> 0.9893 | 1.11e-16 -> 2.22e-16 |
| greg_mortimer | DiningRoom | native | pulse_t0 | 0.1323 -> 0.1323 | 0.9868 -> 0.9868 | 1.332e-15 -> 1.332e-15 |
| greg_mortimer | DiningRoom | native | split_t0_t1 | 0.1323 -> 0.1323 | 0.9868 -> 0.9868 | 4.441e-16 -> 4.441e-16 |
| greg_mortimer | MainGalley | native | pulse_t0 | 0.05768 -> 0.05768 | 0.9942 -> 0.9942 | 4.441e-16 -> 4.441e-16 |
| greg_mortimer | MainGalley | native | split_t0_t1 | 0.05768 -> 0.05768 | 0.9942 -> 0.9942 | -1.11e-16 -> -1.11e-16 |
| greg_mortimer | DiningRoom | commissioned | pulse_t0 | 0.1311 -> 0.2408 | 0.9869 -> 0.9759 | 2.22e-16 -> 0 |
| greg_mortimer | DiningRoom | commissioned | split_t0_t1 | 0.1311 -> 0.2408 | 0.9869 -> 0.9759 | 2.22e-16 -> -2.22e-16 |
| greg_mortimer | MainGalley | commissioned | pulse_t0 | 0.05932 -> 0.05932 | 0.9941 -> 0.9941 | 1.11e-16 -> 4.441e-16 |
| greg_mortimer | MainGalley | commissioned | split_t0_t1 | 0.05932 -> 0.05932 | 0.9941 -> 0.9941 | 1.11e-16 -> 2.22e-16 |
| greg_mortimer | DiningRoom | authored | pulse_t0 | 0.1311 -> 0.2408 | 0.9869 -> 0.9759 | 2.22e-16 -> 0 |
| greg_mortimer | DiningRoom | authored | split_t0_t1 | 0.1311 -> 0.2408 | 0.9869 -> 0.9759 | 2.22e-16 -> -2.22e-16 |
| greg_mortimer | MainGalley | authored | pulse_t0 | 0.05932 -> 0.05932 | 0.9941 -> 0.9941 | 1.11e-16 -> 4.441e-16 |
| greg_mortimer | MainGalley | authored | split_t0_t1 | 0.05932 -> 0.05932 | 0.9941 -> 0.9941 | 1.11e-16 -> 2.22e-16 |
| mega_cruise_5000 | MainDining_L | native | pulse_t0 | 0.3659 -> 0.3659 | 0.9634 -> 0.9634 | 0 -> 0 |
| mega_cruise_5000 | MainDining_L | native | split_t0_t1 | 0.3658 -> 0.3658 | 0.9634 -> 0.9634 | 6.661e-16 -> 6.661e-16 |
| mega_cruise_5000 | Windjammer | native | pulse_t0 | 0.3681 -> 0.3681 | 0.963 -> 0.963 | 0 -> 0 |
| mega_cruise_5000 | Windjammer | native | split_t0_t1 | 0.3681 -> 0.3681 | 0.963 -> 0.963 | 0 -> 0 |
| mega_cruise_5000 | MainDining_L | commissioned | pulse_t0 | 0.3698 -> 0.4259 | 0.963 -> 0.9571 | 1.11e-16 -> 6.661e-16 |
| mega_cruise_5000 | MainDining_L | commissioned | split_t0_t1 | 0.3698 -> 0.4257 | 0.963 -> 0.9571 | -2.22e-16 -> 6.661e-16 |
| mega_cruise_5000 | Windjammer | commissioned | pulse_t0 | 0.3698 -> 0.4337 | 0.963 -> 0.9563 | -3.331e-16 -> 0 |
| mega_cruise_5000 | Windjammer | commissioned | split_t0_t1 | 0.3698 -> 0.4335 | 0.963 -> 0.9563 | -2.22e-16 -> 0 |
| mega_cruise_5000 | MainDining_L | authored | pulse_t0 | 0.3698 -> 0.4259 | 0.963 -> 0.9571 | 1.11e-16 -> 6.661e-16 |
| mega_cruise_5000 | MainDining_L | authored | split_t0_t1 | 0.3698 -> 0.4257 | 0.963 -> 0.9571 | -2.22e-16 -> 6.661e-16 |
| mega_cruise_5000 | Windjammer | authored | pulse_t0 | 0.3698 -> 0.4337 | 0.963 -> 0.9563 | -3.331e-16 -> 0 |
| mega_cruise_5000 | Windjammer | authored | split_t0_t1 | 0.3698 -> 0.4335 | 0.963 -> 0.9563 | -2.22e-16 -> 0 |
| spirit_cruise_3000 | MainDining_L | native | pulse_t0 | 0.1746 -> 0.1746 | 0.9825 -> 0.9825 | 0 -> 0 |
| spirit_cruise_3000 | MainDining_L | native | split_t0_t1 | 0.1746 -> 0.1746 | 0.9825 -> 0.9825 | 1.11e-16 -> 1.11e-16 |
| spirit_cruise_3000 | MainGalley | native | pulse_t0 | 0.09267 -> 0.09267 | 0.9907 -> 0.9907 | 2.22e-16 -> 2.22e-16 |
| spirit_cruise_3000 | MainGalley | native | split_t0_t1 | 0.09267 -> 0.09267 | 0.9907 -> 0.9907 | 0 -> 0 |
| spirit_cruise_3000 | MainDining_L | commissioned | pulse_t0 | 0.2013 -> 0.1995 | 0.9799 -> 0.9801 | 3.331e-16 -> 1.11e-16 |
| spirit_cruise_3000 | MainDining_L | commissioned | split_t0_t1 | 0.2013 -> 0.1995 | 0.9799 -> 0.9801 | 5.551e-16 -> 3.331e-16 |
| spirit_cruise_3000 | MainGalley | commissioned | pulse_t0 | 0.1183 -> 0.09468 | 0.9882 -> 0.9905 | 3.331e-16 -> 2.22e-16 |
| spirit_cruise_3000 | MainGalley | commissioned | split_t0_t1 | 0.1183 -> 0.09468 | 0.9882 -> 0.9905 | 4.441e-16 -> -2.22e-16 |
| spirit_cruise_3000 | MainDining_L | authored | pulse_t0 | 0.2013 -> 0.1995 | 0.9799 -> 0.9801 | 3.331e-16 -> 1.11e-16 |
| spirit_cruise_3000 | MainDining_L | authored | split_t0_t1 | 0.2013 -> 0.1995 | 0.9799 -> 0.9801 | 5.551e-16 -> 3.331e-16 |
| spirit_cruise_3000 | MainGalley | authored | pulse_t0 | 0.1183 -> 0.09468 | 0.9882 -> 0.9905 | 3.331e-16 -> 2.22e-16 |
| spirit_cruise_3000 | MainGalley | authored | split_t0_t1 | 0.1183 -> 0.09468 | 0.9882 -> 0.9905 | 4.441e-16 -> -2.22e-16 |


### Forced-exhaust exact check (before -> after)

The link-count change from the new ambient links is in the flow-compare table
above (path_map entries, native links, `ambient_opening` legs).

ContamX commissioned-export arm. Differences are at the last float digit and
also vary between two runs of the same tree.

| hull | arm | zones | sanitary sources | sanitary exact h (median) | sanitary endpoint sum h (median) | galley-related solved flow m³/h |
|---|---|---|---|---|---|---|
| classic_cruise_1900 | as_authored | 79 -> 79 | 17 -> 17 | 0.052083221 -> 0.052083221 | 4.586992e-09 -> 4.586992e-09 | 11999.999 -> 11999.999 |
| classic_cruise_1900 | sanitary_makeup_oneway | 79 -> 79 | 17 -> 17 | 0.052083221 -> 0.052083221 | 4.586992e-09 -> 4.586992e-09 | 11999.999 -> 11999.999 |
| diamond_princess | as_authored | 159 -> 159 | 39 -> 39 | 0.052083221 -> 0.052083221 | 4.586992e-09 -> 4.586992e-09 | 18000.000 -> 18000.000 |
| diamond_princess | sanitary_makeup_oneway | 159 -> 159 | 39 -> 39 | 0.052083221 -> 0.052083221 | 4.586992e-09 -> 4.586992e-09 | 18000.000 -> 18000.000 |
| expedition_cruise_450 | as_authored | 47 -> 47 | 13 -> 13 | 0.052083221 -> 0.052083221 | 4.586992e-09 -> 4.586992e-09 | 8000.000 -> 8000.000 |
| expedition_cruise_450 | sanitary_makeup_oneway | 47 -> 47 | 13 -> 13 | 0.052083221 -> 0.052083221 | 4.586992e-09 -> 4.586992e-09 | 8000.000 -> 8000.000 |
| greg_mortimer | as_authored | 50 -> 50 | 11 -> 11 | 0.052083221 -> 0.052083221 | 4.586992e-09 -> 4.586992e-09 | 5000.000 -> 5000.000 |
| greg_mortimer | sanitary_makeup_oneway | 50 -> 50 | 11 -> 11 | 0.052083221 -> 0.052083221 | 4.586992e-09 -> 4.586992e-09 | 5000.000 -> 5000.000 |
| mega_cruise_5000 | as_authored | 192 -> 192 | 63 -> 63 | 0.052083221 -> 0.052083221 | 4.586992e-09 -> 4.586992e-09 | 0.000 -> 0.000 |
| mega_cruise_5000 | sanitary_makeup_oneway | 192 -> 192 | 63 -> 63 | 0.052083221 -> 0.052083221 | 4.586992e-09 -> 4.586992e-09 | 0.000 -> 0.000 |
| spirit_cruise_3000 | as_authored | 115 -> 115 | 28 -> 28 | 0.052083221 -> 0.052083221 | 4.586992e-09 -> 4.586992e-09 | 14999.999 -> 14999.999 |
| spirit_cruise_3000 | sanitary_makeup_oneway | 115 -> 115 | 28 -> 28 | 0.052083221 -> 0.052083221 | 4.586992e-09 -> 4.586992e-09 | 14999.999 -> 14999.999 |

## Reproduction

```text
.venv/bin/python tools/diag/ambient_makeup_witness.py --label after
.venv/bin/python tools/contam_commissioned_check.py --platform classic_cruise_1900 \
  --platform diamond_princess --platform expedition_cruise_450 \
  --platform greg_mortimer --platform mega_cruise_5000 --platform spirit_cruise_3000
.venv/bin/python campaigns/contam/phase2_cruise_contrasts_01/design/build.py
```
