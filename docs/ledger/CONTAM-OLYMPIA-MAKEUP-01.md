# CONTAM-OLYMPIA-MAKEUP-01
**Date:** 2026-11-17
**Commit:** d2a0026e
**Pathogens:** all
**Status:** measured
**Measured at:** d2a0026e

## Scope

One `makeup_louvre` `ambient_openings` record on `olympia_c6`
`MD_Forecastle_Open` gives the hull's sanitary make-up demand an explicit,
pressure-responsive ambient route at the open forecastle. Owner ruling
(2026-11-17): author the Olympia make-up route as a Grade C opening, the
open-forecastle scenario from the committed pressure-localization evidence in
`docs/audits/2026-11-17_contam_pressure_localization/` (`localization_review.md`,
`evidence/OLYMPIA_FINDING.md`, `evidence/current_local_solve_summary.csv`).
Schema and lane conventions:
[`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md),
[`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md),
[`CONTAM-AMBIENT-MAKEUP-CRUISE-01`](CONTAM-AMBIENT-MAKEUP-CRUISE-01.md) (D5),
[`CONTAM-GREG-SERVICE-MAKEUP-01`](CONTAM-GREG-SERVICE-MAKEUP-01.md),
[`CONTAM-AMBIENT-WEATHER-OLYMPIA-01`](CONTAM-AMBIENT-WEATHER-OLYMPIA-01.md).

Before-witnesses were measured on the branch base `origin/main`
`1264d863ef1bc7b643d4a97a34bd8806e6b38d05`, which already contains the Olympia
self-path fix #1285 and the stage-4 weather openings #1291. That matters: the
localization's 27.6 kPa commissioned envelope residual is the pre-#1291
self-path baseline. On current main the weather openings already carry most of
the boundary flow, so the measured before-state below is post-#1291, not
27.6 kPa. The after-state is the same solve with only the added record.

Not changed: any `flow_rate_m3h`, `ach`, `oa_fraction` or `hvac_duty`; the four
`AHU_HD_*` sanitary branches or their `Sanitary_Makeup` links; any existing
weather `open_deck` record, exposure tag or wind declaration; the schema,
exporter, transport operator or any duct/interface contract; any
epidemiological constant. The diff to `air_flow_paths.json` is one added
record. No campaign submission.

## Record

```json
{"zone": "MD_Forecastle_Open", "type": "makeup_louvre", "area_m2": 0.502,
 "exchange_m3h": 0.0, "schedule": "always_open"}
```

| Assumption | Value | Grade | Basis |
|---|---|---|---|
| ASSUMED-FORECASTLE-MAKEUP-LOCATION | `MD_Forecastle_Open` | C | The owner-ruled open-forecastle scenario identifies a possible route for the sanitary make-up demand, but no drawing establishes the historical opening location or dimensions. `MD_Forecastle_Open` is the main-deck open forecastle adjacent to the forward passageway/barbette route; it already carries an `open_deck` weather record, and this record is the separate passive make-up assumption, not a retune of that weather opening. |
| ASSUMED-MAKEUP-LOUVRE-AREA | 0.502 m² | C | Served demand 4518.2 m³/h (1189.0 + 713.4 + 1189.0 + 1426.8, the existing `Sanitary_Makeup` cross-zone link reference flows) at the 2.5 m/s free-area face-velocity convention: 4518.2 / 3600 / 2.5 = 0.502022 m², declared as 0.502 m². Not a measured louvre and not chosen against a pressure target. |
| ASSUMED-FORECASTLE-MAKEUP-PASSIVE | `always_open`, no fan, no `wind_speed_m_s` | C | No service supply fan is declared for this route, so it is a passive opening rather than a new prescribed flow or a weather opening. |
| Native rate | `exchange_m3h` 0 | convention (D5) | Commissioned-lane ContamX-solved flow through the two new legs is inward only (clean make-up), so the opening is not a native contaminant sink. |

The area was fixed from the declared `Sanitary_Makeup` link sum before the
after-solve was run and was not adjusted afterwards.

## Witnesses

Official NIST ContamX 3.4.0.3 binary (`third_party/contamx/contamx3`, SHA-256
`d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`, not
committed). Drivers: `tools/diag/contam_pressure_balance_diagnostic.py`
(lanes `authored`, `commissioned`, `design`; `--all-paths`),
`tools/contam_flow_compare.py --platform olympia_c6 --run-contamx` on the
committed commissioned bundle, and
`tools/contam_commissioned_check.py --platform olympia_c6`.

### Pressure balance

| Lane | Paths | Max path \|ΔP\| Pa before | after | Envelope max \|ΔP\| Pa before | after |
|---|---|---|---|---|---|
| commissioned | 821 → 823 | 92.051025390625 | 92.051025390625 | 23.765886306762695 | 23.761777877807617 |
| authored (committed bundle) | 821 → 823 | 92.051025390625 | 92.051025390625 | 23.765886306762695 | 23.761777877807617 |
| design | 821 → 823 | 92.051025390625 | 92.051025390625 | 2.028080463409424 | 2.0241177082061768 |

The unchanged 92.051025390625 Pa max path ΔP is the AHS OA/exhaust terminal
rows, not the make-up envelope residual. Pressure diagnostic reported 0
unsolved rows for all three lanes before and after. Commissioned interior
flowing max |ΔP| moved 16.385726928710938 → 16.385786056518555 Pa; design
interior flowing max |ΔP| moved 0.40041422843933105 → 0.4041154384613031 Pa.

Commissioned/authored boundary balance: make-up demand stays
4491.42740875508 m³/h; envelope net inward 101.2709216397363 →
101.2578796011428 m³/h; ambient-opening net inward 4390.159862154884 →
4390.174954551232 m³/h; balance residual -0.0033750395396054955 →
-0.005425397294857248 m³/h. Design residual 0.004360399258619196 →
0.002608510573260503 m³/h. The residual stays at solver round-off scale; the
new opening changes the distribution by hundredths of m³/h, not the balance.

### Opening flows and D5

Committed bundle `path_map.json` grows 821 → 823 entries and `ambient_opening`
legs 20 → 22. Committed-bundle flow compare: 22 `ambient_opening` legs, outward
386,734.3596681957 m³/h, inward 391,124.5346227469 m³/h; native path inventory
includes `ambient_exchange_makeup_louvre`: 1.

Commissioned/authored solved flow through the two new legs (both inward, Flow0
negative toward ambient):

| path | flow m³/h | ΔP Pa |
|---|---:|---:|
| 665 | -422.47681024241933 | -0.35750138759613037 |
| 666 | -274.62209968888476 | -0.15105774998664856 |

Total 697.0989099313031 m³/h inward, 0 m³/h outward, so the declared native
`exchange_m3h` remains 0.0. Design lane solves the same legs inward:
-406.6119084752591 m³/h at -0.3311556577682495 Pa and -249.5313061463146 m³/h
at -0.12471597641706467 Pa.

`tools/contam_commissioned_check.py --platform olympia_c6`: PASS, every
commissioned terminal solved inside 5% of declared. The hull has no prescribed
exhaust-sink boundary rows (`exhaust_sink_out_m3h` 0), so the forced-exhaust
exact check is not applicable to this change.

## Byte pins

`olympia_c6` bundle regenerated with
`scripts/generate_platform_contam_prj.py --platform olympia_c6 --ahs-terminal-mode commissioned`:

| File | SHA-256 |
|---|---|
| `contam/platform.prj` | `703545512b6518ac8a2f132ebf117406e5d41ba4035f2f2ffb0147a3973b13d9` |
| `contam/path_map.json` | `09bb52d938aad8c6f5e0ff99ebf1ff655d0c4827b53692ac03057cdbe1b3d2ce` |

`git diff --name-only 1264d863ef1bc7b643d4a97a34bd8806e6b38d05 d2a0026ebc -- data/platforms`
lists only the three `olympia_c6` files (`air_flow_paths.json`,
`contam/platform.prj`, `contam/path_map.json`); the other 81 hull platform
trees are byte-identical. No frozen `_01`/`_v1` design was touched and no
`_v2`/`_02` succession was required.

## Tests

`tests/test_contam_ambient_opening.py::TestSchema::test_declared_makeup_louvres`
gains `olympia_c6: 1` in `_MAKEUP_RECORDS`, and
`tests/test_contam_ambient_opening_boundary.py::test_committed_ambient_opening_legs_are_the_declared_records`
moves `olympia_c6` 20 → 22 legs. Both moves are the added record and nothing
else; no test was edited to hide a failure.

## Open

- Location and area are Grade C. A deck plan or ventilation drawing of the
  forecastle/sanitary route would replace both; until then the record is an
  operating assumption.
- The opening carries only 697.1 m³/h of the 4,491.4 m³/h make-up demand in
  the commissioned solve because the stage-4 weather openings already carry
  the bulk of the boundary flow. This entry authors the explicit route; it is
  not evidence that the historical louvre had these dimensions.
