# CONTAM-AMBIENT-MAKEUP-FICTION-01
**Date:** 2026-11-16
**Commit:** 4029759f
**Pathogens:** all
**Status:** measured
**Measured at:** 4029759f

## Scope

After-witnesses measured at `4029759f`; before-witnesses at `origin/main`
`ebdf051f` with only the witness-hull additions in the diagnostic tools and no
platform declaration. Stage 3 of
[`../proposals/ambient_exposure_audit_and_fix_plan.md`](../proposals/ambient_exposure_audit_and_fix_plan.md)
§6 for the **fiction hull class only**:
`enterprise_constitution_tos` and `enterprise_galaxy_tng`. With the cruise half
in [`CONTAM-AMBIENT-MAKEUP-CRUISE-01`](CONTAM-AMBIENT-MAKEUP-CRUISE-01.md), this
entry **completes governing-plan stage 6 (`CONTAM-FIELD-ENVELOPE-MAKEUP-01`)
cruise+fiction half per owner ruling D6(a)**. Machinery:
[`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md) and
[`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md).
Evidence base: [`CONTAM-FIELD-PRESSURE-REVIEW-01`](CONTAM-FIELD-PRESSURE-REVIEW-01.md).

Not changed: any `flow_rate_m3h` or exhaust-sink magnitude (the two hulls'
prescribed `Galley_Service_Exhaust` / `Galley_Hood_Exhaust` pair stays 5,000
and 8,000 m³/h; the `air_flow_paths.json` diffs are additions only),
`envelope_leak` area or any exporter constant, the transmission layer, any
cruise or naval hull. No weather-zone, balcony or hatch opening is authored
(stages 4-6). No cache was produced or uploaded and nothing was submitted.

## Records

One record per hull, appended as top-level `ambient_openings` (D1(a)),
`type: makeup_louvre`, `schedule: always_open`, placed on `Mess_Hall` — the
zone the prescribed `Galley_Service_Exhaust` transfer draws the galley
make-up air from; `Galley` itself is balanced by that transfer and by the
`Galley_Hood_Exhaust` sink it feeds.

| hull | zone | area_m2 | served prescribed demand, m³/h | exchange_m3h |
|---|---|---|---|---|
| enterprise_constitution_tos | `Mess_Hall` | 0.556 | `Galley_Hood_Exhaust` 5,000 | 0.0 |
| enterprise_galaxy_tng | `Mess_Hall` | 0.889 | `Galley_Hood_Exhaust` 8,000 | 0.0 |

### Placement and area

The placement rule is the cruise rule: the louvre goes on the room the
make-up transfer draws from, not on the galley. In-memory scratch exports on
both fiction hulls solved inward-only flow for both candidate rooms
(`Mess_Hall` and `Galley`) in both field lanes, so direction did not choose
the room; the transfer topology did. Every area is
`ASSUMED-MAKEUP-LOUVRE-AREA`, Grade C: no drawing gives a louvre, so it is the
served demand at the same assumed 2.5 m/s free-area face velocity used by the
cruise records (`area = Q / 3600 / 2.5`, three decimals). It was not checked
against literature or a standard and was not tuned per hull or against any
pressure target.

Scratch candidate flows (inward m³/h; outward was 0 in every case):

| hull | candidate | design inward | commissioned inward |
|---|---|---:|---:|
| enterprise_constitution_tos | `Mess_Hall` | 4,956.1 | 9,242.7 |
| enterprise_constitution_tos | `Galley` | 4,851.0 | 9,049.1 |
| enterprise_galaxy_tng | `Mess_Hall` | 7,579.0 | 12,610.0 |
| enterprise_galaxy_tng | `Galley` | 7,294.0 | 12,298.0 |

## D5 derivation: native rate from the ContamX-solved range

Method is the cruise precedent: author the opening, export `design` and
`commissioned`, solve with ContamX, read `Flow0` on both legs, split outward
from inward, and declare the native sink rate inside the measured **outward**
range. The committed after-witness gives the same reading on both fiction
hulls (`authored` equals `commissioned`):

| hull | lane | legs | min leg inward m³/h | max leg inward m³/h | total inward m³/h | outward legs | outward m³/h | max leg \|ΔP\| Pa |
|---|---|---|---|---|---|---|---|---|
| enterprise_constitution_tos | design | 2 | 2,477.96 | 2,478.18 | 4,956.15 | 0 | 0 | 10.25 |
| enterprise_constitution_tos | commissioned | 2 | 4,621.14 | 4,621.54 | 9,242.68 | 0 | 0 | 35.66 |
| enterprise_galaxy_tng | design | 2 | 3,789.31 | 3,789.64 | 7,578.96 | 0 | 0 | 9.38 |
| enterprise_galaxy_tng | commissioned | 2 | 6,304.72 | 6,305.27 | 12,609.99 | 0 | 0 | 25.96 |

No leg is outward on either hull in any lane, so the measured outward range is
0 to 0 m³/h and `exchange_m3h: 0.0` is declared per record. Scope of this
claim is the same as the cruise entry: steady solves at the authored
placement with the exporter's ΔT = 0; a different placement or a nonzero
temperature difference must be re-measured.

## Acceptance: design-lane max |ΔP|

| hull | design before Pa | design after Pa | in 0.5-374 Pa | commissioned before Pa | commissioned after Pa |
|---|---|---|---|---|---|
| enterprise_constitution_tos | 1.669e5 | 13.71 | yes | 3.008e5 | 106.1 |
| enterprise_galaxy_tng | 1.254e5 | 3.246e4 | no | 1.904e5 | 1.650e5 |

The prescribed exhaust sink is fixed on both hulls: after the change the
`Galley_Hood_Exhaust` sink's own max |ΔP| is 12.0 Pa on
`enterprise_constitution_tos` and 9.4 Pa on `enterprise_galaxy_tng` in the
design lane, and 99.3 / 28.2 Pa in the commissioned lane. `enterprise_galaxy_tng`
still has a large residual, recorded here with its measured cause and not
tuned:

- design 32,460 Pa: `ShuttleBay`, `Airlock`, `CargoMain` and `CargoAux`
  `Sanitary_Makeup` passive openings toward `HD_4D_M`/`HD_4D_F` solve zero
  flow at about -32.5 kPa. That flight/engineering cluster is not reached by
  the louvred `Mess_Hall` in the design lane (225 interior paths remain
  blocked); the exhaust sink itself is at 9.4 Pa.
- commissioned 165,030 Pa: the same `ShuttleBay`/`CargoMain`/`CargoAux`/
  `Airlock` cluster drives prescribed `Drive_Flight_Trunk` links toward
  `MainEng`, `WarpCore`, `EPSDist`, `Jefferies` and `Deflector` at about
  -165 kPa. Hull make-up demand is 14,557.8 m³/h (8,000 exhaust + 6,557.8 AHS
  return-minus-supply) and is met by 12,610.0 m³/h louvre inflow plus 1,947.8
  m³/h envelope-leak inflow; the residual is AHS/flight-trunk distribution,
  not the prescribed exhaust sink.

## Balance residual

`balance_residual_m3h` stays at the float-noise level on every hull and lane:
|value| ≤ 3.15e-4 m³/h before and ≤ 1.43e-4 m³/h after. The pressure diagnostic's
boundary summary counts the louvre's inward flow as make-up, so the residual
does not read the opening as an imbalance.

## Bundles and design pins

- The two committed `data/platforms/<hull>/contam/platform.prj` and
  `path_map.json` bundles are regenerated in commissioned mode. Before
  regenerating, the same export with `ambient_openings` removed in memory
  reproduced both committed bundles byte-for-byte (`git diff --exit-code`
  clean), so the bundle diff is this change alone. Path-map entries:
  constitution 568 → 570, galaxy 1,430 → 1,432 (two legs per record).
- `tools/contam_commissioned_check.py --platform enterprise_constitution_tos
  --platform enterprise_galaxy_tng`: PASS, every commissioned terminal solves
  inside 5% of declared. ContamX converged on both hulls and all witness lanes.
- No fiction hull pins a frozen Contam design: `enterprise_constitution_tos`
  and `enterprise_galaxy_tng` do not appear under `campaigns/contam`, and the
  cruise-only `phase2_cruise_contrasts_01` `_02` design is untouched. No
  `_v1` cache was re-run.
- Moved test expectations, each attributed to the authored records: the
  stage-1 guard `test_only_cruise_makeup_louvres_are_declared` becomes
  `test_only_makeup_louvres_are_declared`, and the stage-2 guard
  `test_committed_ambient_opening_legs_are_the_cruise_makeup_louvres` becomes
  `test_committed_ambient_opening_legs_are_the_makeup_louvres`. They now
  assert exactly the six cruise hulls plus the two fiction hulls declare
  make-up louvres (1 record each, 10 on `mega_cruise_5000`; 2 legs per record)
  at native rate 0.

## Witnesses

Runner: `tools/diag/ambient_makeup_witness.py --label <before|after> --hull
enterprise_constitution_tos --hull enterprise_galaxy_tng`, then `--compare
before after`. It drives the pressure-balance diagnostic (design,
commissioned, authored lanes, all paths), `tools/contam_flow_compare.py`,
`tools/diag/contam_paired_diagnostic.py` and the
`tools/diag/forced_exhaust_audit.py exact-check` on each hull.
`contam_paired_diagnostic.py` previously knew neither fiction hull; both are
added as opt-in `--hull` choices and its bare invocation is unchanged.

Native lane: native material times are identical before and after in every
cell, and each record appears as a native `ambient_exchange_makeup_louvre`
link at 0 m³/h. Field lanes: material times move where the louvre changes the
solved flow field, most on the commissioned/authored lanes (for example
`enterprise_constitution_tos` `Mess_Hall` 0.110 → 0.229 h and
`enterprise_galaxy_tng` `Mess_Hall` 0.0803 → 0.216 h).

### Pressure balance (before -> after)

| hull | lane | paths | max dP Pa | interior flowing max dP Pa | exhaust sinks m3/h | envelope net in m3/h | opening in m3/h | opening out m3/h | opening max dP Pa | balance residual m3/h | k field/native median |
|---|---|---|---|---|---|---|---|---|---|---|---|
| enterprise_constitution_tos | design | 568 -> 570 | 1.669e+05 -> 13.71 | 46.77 -> 2.605 | 5000 -> 5000 | 5000 -> 43.85 | 4956 | 0 | 10.25 | 0.0001671 -> 0.0001158 | 1.016 -> 0.9295 |
| enterprise_constitution_tos | commissioned | 568 -> 570 | 3.008e+05 -> 106.1 | 51.08 -> 63.59 | 5000 -> 5000 | 9412 -> 168.9 | 9243 | 0 | 35.66 | 0.0001559 -> 0.0001015 | 1 -> 1 |
| enterprise_constitution_tos | authored | 568 -> 570 | 3.008e+05 -> 106.1 | 51.08 -> 63.59 | 5000 -> 5000 | 9412 -> 168.9 | 9243 | 0 | 35.66 | 0.0001559 -> 0.0001015 | 1 -> 1 |
| enterprise_galaxy_tng | design | 1430 -> 1432 | 1.254e+05 -> 3.246e4 | 859.8 -> 79.88 | 8000 -> 8000 | 8000 -> 421 | 7579 | 0 | 9.379 | -0.0003146 -> -7.464e-05 | 0.9977 -> 0.9952 |
| enterprise_galaxy_tng | commissioned | 1430 -> 1432 | 1.904e+05 -> 1.65e+05 | 933.9 -> 219.5 | 8000 -> 8000 | 1.456e+04 -> 1948 | 1.261e+04 | 0 | 25.96 | -0.0002896 -> -0.000143 | 1 -> 1 |
| enterprise_galaxy_tng | authored | 1430 -> 1432 | 1.904e+05 -> 1.65e+05 | 933.9 -> 219.5 | 8000 -> 8000 | 1.456e+04 -> 1948 | 1.261e+04 | 0 | 25.96 | -0.0002896 -> -0.000143 | 1 -> 1 |

### Flow compare (before -> after)

| hull | path_map entries | native links | kept Crusher paths | synth AHS paths | ambient_opening legs | opening inward m3/h | opening outward sink m3/h | native ambient_exchange links / total m3/h |
|---|---|---|---|---|---|---|---|---|
| enterprise_constitution_tos | 568 -> 570 | 465 -> 466 | 254 -> 289 | 107 -> 107 | 0 -> 2 | 0 -> 9242.68 | 0 -> 0 | 1 / 0 |
| enterprise_galaxy_tng | 1430 -> 1432 | 1215 -> 1216 | 760 -> 886 | 217 -> 217 | 0 -> 2 | 0 -> 12610 | 0 -> 0 | 1 / 0 |

### Whole-hull material time, h (pressure diagnostic source cells)

| hull | source / timing / lane | before | after |
|---|---|---|---|
| enterprise_constitution_tos | Galley/pulse_t0/design | 0.05158 | 0.0553 |
| enterprise_constitution_tos | Galley/pulse_t0/native | 0.04599 | 0.04599 |
| enterprise_constitution_tos | Galley/split_t0_t1/design | 0.05158 | 0.0553 |
| enterprise_constitution_tos | Galley/split_t0_t1/native | 0.04599 | 0.04599 |
| enterprise_constitution_tos | Mess_Hall/pulse_t0/design | 0.1125 | 0.1559 |
| enterprise_constitution_tos | Mess_Hall/pulse_t0/native | 0.1087 | 0.1087 |
| enterprise_constitution_tos | Mess_Hall/split_t0_t1/design | 0.1125 | 0.1559 |
| enterprise_constitution_tos | Mess_Hall/split_t0_t1/native | 0.1087 | 0.1087 |
| enterprise_constitution_tos | Galley/pulse_t0/commissioned | 0.05117 | 0.06072 |
| enterprise_constitution_tos | Galley/pulse_t0/native | 0.04599 | 0.04599 |
| enterprise_constitution_tos | Galley/split_t0_t1/commissioned | 0.05117 | 0.06072 |
| enterprise_constitution_tos | Galley/split_t0_t1/native | 0.04599 | 0.04599 |
| enterprise_constitution_tos | Mess_Hall/pulse_t0/commissioned | 0.11 | 0.2286 |
| enterprise_constitution_tos | Mess_Hall/pulse_t0/native | 0.1087 | 0.1087 |
| enterprise_constitution_tos | Mess_Hall/split_t0_t1/commissioned | 0.11 | 0.2286 |
| enterprise_constitution_tos | Mess_Hall/split_t0_t1/native | 0.1087 | 0.1087 |
| enterprise_constitution_tos | Galley/pulse_t0/authored | 0.05117 | 0.06072 |
| enterprise_constitution_tos | Galley/pulse_t0/native | 0.04599 | 0.04599 |
| enterprise_constitution_tos | Galley/split_t0_t1/authored | 0.05117 | 0.06072 |
| enterprise_constitution_tos | Galley/split_t0_t1/native | 0.04599 | 0.04599 |
| enterprise_constitution_tos | Mess_Hall/pulse_t0/authored | 0.11 | 0.2286 |
| enterprise_constitution_tos | Mess_Hall/pulse_t0/native | 0.1087 | 0.1087 |
| enterprise_constitution_tos | Mess_Hall/split_t0_t1/authored | 0.11 | 0.2286 |
| enterprise_constitution_tos | Mess_Hall/split_t0_t1/native | 0.1087 | 0.1087 |
| enterprise_galaxy_tng | Galley/pulse_t0/design | 0.03724 | 0.03737 |
| enterprise_galaxy_tng | Galley/pulse_t0/native | 0.03602 | 0.03602 |
| enterprise_galaxy_tng | Galley/split_t0_t1/design | 0.03724 | 0.03737 |
| enterprise_galaxy_tng | Galley/split_t0_t1/native | 0.03602 | 0.03602 |
| enterprise_galaxy_tng | Mess_Hall/pulse_t0/design | 0.082 | 0.08273 |
| enterprise_galaxy_tng | Mess_Hall/pulse_t0/native | 0.07985 | 0.07985 |
| enterprise_galaxy_tng | Mess_Hall/split_t0_t1/design | 0.082 | 0.08273 |
| enterprise_galaxy_tng | Mess_Hall/split_t0_t1/native | 0.07985 | 0.07985 |
| enterprise_galaxy_tng | Galley/pulse_t0/commissioned | 0.03619 | 0.04606 |
| enterprise_galaxy_tng | Galley/pulse_t0/native | 0.03602 | 0.03602 |
| enterprise_galaxy_tng | Galley/split_t0_t1/commissioned | 0.03619 | 0.04606 |
| enterprise_galaxy_tng | Galley/split_t0_t1/native | 0.03602 | 0.03602 |
| enterprise_galaxy_tng | Mess_Hall/pulse_t0/commissioned | 0.0803 | 0.2159 |
| enterprise_galaxy_tng | Mess_Hall/pulse_t0/native | 0.07985 | 0.07985 |
| enterprise_galaxy_tng | Mess_Hall/split_t0_t1/commissioned | 0.0803 | 0.2159 |
| enterprise_galaxy_tng | Mess_Hall/split_t0_t1/native | 0.07985 | 0.07985 |
| enterprise_galaxy_tng | Galley/pulse_t0/authored | 0.03619 | 0.04606 |
| enterprise_galaxy_tng | Galley/pulse_t0/native | 0.03602 | 0.03602 |
| enterprise_galaxy_tng | Galley/split_t0_t1/authored | 0.03619 | 0.04606 |
| enterprise_galaxy_tng | Galley/split_t0_t1/native | 0.03602 | 0.03602 |
| enterprise_galaxy_tng | Mess_Hall/pulse_t0/authored | 0.0803 | 0.2159 |
| enterprise_galaxy_tng | Mess_Hall/pulse_t0/native | 0.07985 | 0.07985 |
| enterprise_galaxy_tng | Mess_Hall/split_t0_t1/authored | 0.0803 | 0.2159 |
| enterprise_galaxy_tng | Mess_Hall/split_t0_t1/native | 0.07985 | 0.07985 |

### Paired diagnostic matrix (before -> after)

| hull | source | lane | timing | whole-hull material time h | transport loss | closure error |
|---|---|---|---|---|---|---|
| enterprise_constitution_tos | Mess_Hall | native | pulse_t0 | 0.1087 -> 0.1087 | 0.9891 -> 0.9891 | 2.22e-16 -> 2.22e-16 |
| enterprise_constitution_tos | Mess_Hall | native | split_t0_t1 | 0.1087 -> 0.1087 | 0.9891 -> 0.9891 | 1.11e-16 -> 1.11e-16 |
| enterprise_constitution_tos | Galley | native | pulse_t0 | 0.04599 -> 0.04599 | 0.9954 -> 0.9954 | 2.22e-16 -> 2.22e-16 |
| enterprise_constitution_tos | Galley | native | split_t0_t1 | 0.04599 -> 0.04599 | 0.9954 -> 0.9954 | 3.331e-16 -> 3.331e-16 |
| enterprise_constitution_tos | Mess_Hall | commissioned | pulse_t0 | 0.11 -> 0.2286 | 0.989 -> 0.9771 | 7.772e-16 -> -3.331e-16 |
| enterprise_constitution_tos | Mess_Hall | commissioned | split_t0_t1 | 0.11 -> 0.2286 | 0.989 -> 0.9771 | 5.551e-16 -> -4.441e-16 |
| enterprise_constitution_tos | Galley | commissioned | pulse_t0 | 0.05117 -> 0.06072 | 0.9949 -> 0.9939 | 1.11e-16 -> 4.441e-16 |
| enterprise_constitution_tos | Galley | commissioned | split_t0_t1 | 0.05117 -> 0.06072 | 0.9949 -> 0.9939 | 4.441e-16 -> 4.441e-16 |
| enterprise_constitution_tos | Mess_Hall | authored | pulse_t0 | 0.11 -> 0.2286 | 0.989 -> 0.9771 | 7.772e-16 -> -3.331e-16 |
| enterprise_constitution_tos | Mess_Hall | authored | split_t0_t1 | 0.11 -> 0.2286 | 0.989 -> 0.9771 | 5.551e-16 -> -4.441e-16 |
| enterprise_constitution_tos | Galley | authored | pulse_t0 | 0.05117 -> 0.06072 | 0.9949 -> 0.9939 | 1.11e-16 -> 4.441e-16 |
| enterprise_constitution_tos | Galley | authored | split_t0_t1 | 0.05117 -> 0.06072 | 0.9949 -> 0.9939 | 4.441e-16 -> 4.441e-16 |
| enterprise_galaxy_tng | Mess_Hall | native | pulse_t0 | 0.07985 -> 0.07985 | 0.992 -> 0.992 | 2.22e-16 -> 2.22e-16 |
| enterprise_galaxy_tng | Mess_Hall | native | split_t0_t1 | 0.07985 -> 0.07985 | 0.992 -> 0.992 | 2.22e-16 -> 2.22e-16 |
| enterprise_galaxy_tng | Galley | native | pulse_t0 | 0.03602 -> 0.03602 | 0.9964 -> 0.9964 | 4.441e-16 -> 4.441e-16 |
| enterprise_galaxy_tng | Galley | native | split_t0_t1 | 0.03602 -> 0.03602 | 0.9964 -> 0.9964 | 3.331e-16 -> 3.331e-16 |
| enterprise_galaxy_tng | Mess_Hall | commissioned | pulse_t0 | 0.0803 -> 0.2159 | 0.992 -> 0.9784 | -2.22e-16 -> -4.441e-16 |
| enterprise_galaxy_tng | Mess_Hall | commissioned | split_t0_t1 | 0.0803 -> 0.2159 | 0.992 -> 0.9784 | 0 -> 3.331e-16 |
| enterprise_galaxy_tng | Galley | commissioned | pulse_t0 | 0.03619 -> 0.04606 | 0.9964 -> 0.9954 | -2.22e-16 -> -4.441e-16 |
| enterprise_galaxy_tng | Galley | commissioned | split_t0_t1 | 0.03619 -> 0.04606 | 0.9964 -> 0.9954 | -2.22e-16 -> -3.331e-16 |
| enterprise_galaxy_tng | Mess_Hall | authored | pulse_t0 | 0.0803 -> 0.2159 | 0.992 -> 0.9784 | -2.22e-16 -> -4.441e-16 |
| enterprise_galaxy_tng | Mess_Hall | authored | split_t0_t1 | 0.0803 -> 0.2159 | 0.992 -> 0.9784 | 0 -> 3.331e-16 |
| enterprise_galaxy_tng | Galley | authored | pulse_t0 | 0.03619 -> 0.04606 | 0.9964 -> 0.9954 | -2.22e-16 -> -4.441e-16 |
| enterprise_galaxy_tng | Galley | authored | split_t0_t1 | 0.03619 -> 0.04606 | 0.9964 -> 0.9954 | -2.22e-16 -> -3.331e-16 |

### Forced-exhaust exact check (before -> after)

The link-count change from the new ambient links is in the flow-compare table
above (path_map entries, native links, `ambient_opening` legs).

ContamX commissioned-export arm. Differences are at the last float digit and
also vary between two runs of the same tree.

| hull | arm | zones | sanitary sources | sanitary exact h (median) | sanitary endpoint sum h (median) | galley-related solved flow m³/h |
|---|---|---|---|---|---|---|
| enterprise_constitution_tos | as_authored | 63 | 19 | 0.052083 -> 0.052083 | 4.586992e-09 -> 4.586992e-09 | 5000.000 -> 5000.000 |
| enterprise_constitution_tos | sanitary_makeup_oneway | 63 | 19 | 0.052083 -> 0.052083 | 4.586992e-09 -> 4.586992e-09 | 5000.000 -> 5000.000 |
| enterprise_galaxy_tng | as_authored | 127 | 37 | 0.052083 -> 0.052083 | 4.586992e-09 -> 4.586992e-09 | 8000.000 -> 8000.000 |
| enterprise_galaxy_tng | sanitary_makeup_oneway | 127 | 37 | 0.052083 -> 0.052083 | 4.586992e-09 -> 4.586992e-09 | 8000.000 -> 8000.000 |

## Reproduction

```text
.venv/bin/python tools/diag/ambient_makeup_witness.py --label after \
  --hull enterprise_constitution_tos --hull enterprise_galaxy_tng
.venv/bin/python tools/contam_commissioned_check.py \
  --platform enterprise_constitution_tos --platform enterprise_galaxy_tng
```
