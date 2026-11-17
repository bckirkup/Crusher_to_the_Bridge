# CONTAM-GREG-SERVICE-MAKEUP-01
**Date:** 2026-11-17
**Commit:** bb090693
**Pathogens:** all
**Status:** measured
**Measured at:** bb090693

## Scope

After-witnesses measured at `bb090693`; before-witnesses at `origin/main`
`0bfc058d`, whose `data/platforms/greg_mortimer/` tree is byte-identical to the
localization pin `c93fa32fbe05440e797de8b551a2781b236d7e43` (`git diff` empty).

One `makeup_louvre` `ambient_openings` record on `greg_mortimer` `Engine_Room`
gives the hull's service/crew passive-opening component a pressure-responsive
ambient route for the sanitary make-up it already declares. Evidence base: the
executed localization, its independent QA and the synthesis, committed in
parallel under `docs/audits/2026-11-17_contam_pressure_localization/`
(`findings.md` §1, `qa.md` §3, `localization_review.md`). Schema and lane
conventions: [`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md),
[`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md),
[`CONTAM-AMBIENT-MAKEUP-CRUISE-01`](CONTAM-AMBIENT-MAKEUP-CRUISE-01.md) (which
recorded this residual as separate from the DiningRoom louvre),
[`CONTAM-AMBIENT-WEATHER-CRUISE-01`](CONTAM-AMBIENT-WEATHER-CRUISE-01.md),
[`CONTAM-DEFAULT-WEATHER-01`](CONTAM-DEFAULT-WEATHER-01.md).

Not changed: any `flow_rate_m3h`, `ach`, `oa_fraction` or `hvac_duty`; the three
service sanitary groups and their `Sanitary_Makeup` links; the DiningRoom louvre
(`area_m2` 0.556); any weather opening, exposure tag or wind declaration; the
schema, exporter, transport operator or any duct/interface contract; any
epidemiological constant. The diff to `air_flow_paths.json` is one added record.
No cache was produced or uploaded and nothing was submitted. The auxiliary
duct-spine/transport contract (`findings.md` §3) is out of scope.

## Defect (settled input, not re-derived)

The 11-room component `MainGalley`, `Laundry`, `Engine_Room`, `CrewMess`, four
crew-cabin groups and sanitary `HD_0E_M` / `HD_2C_M` / `HD_2C_F` had no ambient
opening. The three heads withdraw 0.239279 kg/s; the galley transfer/hood pair
supplies a 0.022512 kg/s surplus; the 0.216767 kg/s deficit entered through the
component's envelope-reference leaks. The DiningRoom louvre cannot serve it: it
sits upstream of the fixed-flow `Dining_Galley_Exhaust` 5000 m³/h transfer.

## Record

```json
{"zone": "Engine_Room", "type": "makeup_louvre", "area_m2": 0.079,
 "exchange_m3h": 0.0, "schedule": "always_open"}
```

| Assumption | Value | Grade | Basis |
|---|---|---|---|
| ASSUMED-SERVICE-INTAKE-LOCATION | `Engine_Room` | C | No Greg Mortimer drawing in the repository shows decks 0-2 or a ventilator. A machinery-space weather intake is assumed as the service group's outdoor-air route; `Engine_Room` is an `AHU_Service` room, and `AHU_Service` is the declared source of all three `Sanitary_Makeup` links. Not evidence that the vessel has an opening there. |
| ASSUMED-MAKEUP-LOUVRE-AREA | 0.079 m² | C | Served demand 713.6 m³/h (118.9 + 356.8 + 237.9, the existing `Sanitary_Makeup` links) at the 2.5 m/s free-area face velocity already assumed by `CONTAM-AMBIENT-MAKEUP-CRUISE-01`: 713.6 / 3600 / 2.5 = 0.0793, declared to two significant figures. Not a machinery-ventilation sizing; not chosen against a pressure target. |
| ASSUMED-SERVICE-INTAKE-PASSIVE | `always_open`, no fan | C | No service supply fan is declared, so the route is a passive opening rather than a new prescribed flow. |
| Native rate | `exchange_m3h` 0 | convention (D5) | Committed commissioned-lane solved flow through both legs is inward only (clean make-up), so the opening is not a native contaminant sink. |

The area was fixed from the declared demand before the after-solve was run and
was not adjusted afterwards. Sensitivity, measured in scratch solves and not
committed: the same 0.079 m² at `MainGalley`, `Laundry` or `CrewMess` gives a
commissioned max path ΔP of 12.31, 12.06 or 17.45 Pa; 0.79 m² at `Engine_Room`
gives 7.24 Pa. Location within the component and a tenfold area change move the
result by a few pascals, not by orders of magnitude.

## Witnesses

Official NIST ContamX 3 binary (`third_party/contamx/contamx3`, SHA-256
`d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`, not
committed). Driver: `tools/diag/ambient_makeup_witness.py --hull greg_mortimer`,
which runs `tools/diag/contam_pressure_balance_diagnostic.py` (lanes `authored`,
`commissioned`, `design`; sources `DiningRoom`, `MainGalley`; `--all-paths`),
`tools/contam_flow_compare.py --run-contamx`,
`tools/diag/contam_paired_diagnostic.py` and
`tools/diag/forced_exhaust_audit.py exact-check`.

### Pressure balance

| Lane | Paths | Max path \|ΔP\| Pa before | after | Interior flowing max \|ΔP\| Pa before | after |
|---|---|---|---|---|---|
| commissioned | 368 → 370 | 44878.17578125 | 15.426214218139648 | 6.674605369567871 | 6.674605369567871 |
| authored (committed bundle) | 368 → 370 | 44878.17578125 | 15.426214218139648 | 6.674605369567871 | 6.674605369567871 |
| design | 368 → 370 | 934.3681640625 | 6.856197834014893 | 6.619757175445557 | 6.619757175445557 |

The ledgered value for the authored route is **15.426214218139648 Pa**
(commissioned = committed bundle), in the class of the localization's 12.25 Pa
`MainGalley` witness. The after-state maximum is the `CC_D1_F` envelope leak
(−15.43 Pa); the next largest are `CC_D1_A` (−15.28), `CC_D2_F` (−14.94) and the
`Galley_Hood_Exhaust` fan path (−14.88).

Commissioned-lane solved flow through the new legs: path 213 −322.57383265965217
m³/h at −8.567841529846191 Pa, path 214 −315.8080277397164 m³/h at
−8.212199211120605 Pa — 638.4 m³/h inward, none outward. Envelope-leak net
inflow 653.0 → 14.65 m³/h. Prescribed exhaust sinks 4943.591468228695 m³/h
before and after. `tools/contam_commissioned_check.py --platform greg_mortimer`:
PASS, every commissioned terminal inside 5 % of declared.

Design lane (diagnostic only, not the operating semantics): the same legs carry
6.78 and 65.28 m³/h outward at 0.004 and 0.358 Pa.

### Flow compare and paired diagnostic (same cells)

| Quantity | before | after |
|---|---|---|
| path_map entries | 368 | 370 |
| native links | 293 | 294 |
| kept Crusher paths | 149 | 149 |
| synthesized AHS paths | 79 | 79 |
| `ambient_opening` legs | 12 | 14 |
| opening inward m³/h (hull total) | 178377 | 179015 |
| opening outward sink m³/h (hull total) | 167633 | 167633 |
| native `ambient_exchange` links / total m³/h | 7 / 1.676e+05 | 7 / 1.676e+05 |

The hull totals are dominated by the ten existing weather-deck legs; the service
intake adds 638 m³/h inward and nothing outward.

Whole-hull material time, h:

| Source | Timing | native before → after | commissioned / authored before → after | design before → after |
|---|---|---|---|---|
| DiningRoom | pulse_t0, split_t0_t1 | 0.1323 → 0.1323 | 0.1329 → 0.1426 | 0.1587 → 0.1571 |
| MainGalley | pulse_t0, split_t0_t1 | 0.05768 → 0.05768 | 0.05932 → 0.07074 | 0.08477 → 0.08295 |

Paired-matrix transport loss: native 0.9868 / 0.9942 unchanged; commissioned
0.9867 → 0.9857 (DiningRoom), 0.9941 → 0.9929 (MainGalley). Closure error
≤ 4.5e-16 in every cell before and after.

The commissioned field material time rises by 7 % (DiningRoom) and 19 %
(MainGalley). Attribution (inferred from the solved pressures, not separately
measured): before, the service component sat near −44.8 kPa
gauge, a solved air density far below ambient; the fixed mass-flow galley fans
then swept more volume per hour through `MainGalley`. That is the artifact this
entry removes; the after values are the field lane at physical density.

### Native lane (D4/D5)

The record declares `exchange_m3h` 0, so the native operator gains one
zero-rate link (293 → 294) and no sink: every native material time, transport
loss and closure above is unchanged to the printed digits, and the native
`ambient_exchange` set is still the seven existing links. The forced-exhaust
exact check is unchanged in class: sanitary exact integral 0.05208333 h native
against 0.05208322 h commissioned (n = 11), `Dining_Galley_Exhaust` solved at
4999.999861395759 m³/h.

## Byte pins

`greg_mortimer` bundle regenerated with
`scripts/generate_platform_contam_prj.py --platform greg_mortimer --ahs-terminal-mode commissioned`:

| File | SHA-256 |
|---|---|
| `contam/platform.prj` | `c40f343e27031a7dbe82119777a3550340058b2fd410ebf6893d80d8aedf5c69` |
| `contam/path_map.json` | `f90d21fbacb1418d5890c5d57d29b519886285607e5e0aaceb9d4341a0b56c67` |

Running the same generator on the unmodified tree reproduced the committed
`greg_mortimer` bundle with an empty diff, so every byte that moved is
attributable to the added record. The other 81 hulls:
`git diff --stat 0bfc058d bb090693 -- data/platforms` lists only the three
`greg_mortimer` files; no exporter or shared input changed.

## Tests

`tests/test_contam_ambient_opening.py::TestSchema::test_declared_makeup_louvres`
(`greg_mortimer` 1 → 2 make-up records) and
`tests/test_contam_ambient_opening_boundary.py::test_committed_ambient_opening_legs_are_the_declared_records`
(`greg_mortimer` 12 → 14 legs) pin record counts; both moves are the added
record and nothing else.

## Open

- Location and area are Grade C. A deck plan or ventilation drawing of decks
  0-2 would replace both; until then the record is an operating assumption.
- The 15.43 Pa residual is the crew-cabin envelope leaks under sanitary and
  galley draw, not the intake.
