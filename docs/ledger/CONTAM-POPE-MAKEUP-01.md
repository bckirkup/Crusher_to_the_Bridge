# CONTAM-POPE-MAKEUP-01
**Date:** 2026-11-18
**Commit:** 88ba9a8c
**Pathogens:** all
**Status:** measured
**Measured at:** 88ba9a8c

## Scope

Owner ruling (Benjamin, 2026-11-18): the `pope_ap110` commissioned
sanitary make-up residual uses mechanism option 1, explicit ambient make-up
openings, following the Greg/Olympia precedent. This entry authors seven Grade
C `makeup_louvre` `ambient_openings` records on `pope_ap110` only, one per
exhaust-only sanitary AHS branch's HD zone, from the merged evidence note
`docs/audits/2026-11-18_pope_ap110_envelope_makeup_boundary/README.md`.
Schema and lane conventions:
[`CONTAM-AMBIENT-OPENING-SCHEMA-01`](CONTAM-AMBIENT-OPENING-SCHEMA-01.md),
[`CONTAM-AMBIENT-OPENING-BOUNDARY-01`](CONTAM-AMBIENT-OPENING-BOUNDARY-01.md),
[`CONTAM-GREG-SERVICE-MAKEUP-01`](CONTAM-GREG-SERVICE-MAKEUP-01.md),
[`CONTAM-OLYMPIA-MAKEUP-01`](CONTAM-OLYMPIA-MAKEUP-01.md), and D5 in
[`CONTAM-AMBIENT-MAKEUP-CRUISE-01`](CONTAM-AMBIENT-MAKEUP-CRUISE-01.md).

Before-witnesses are the evidence-note values. The note was pinned at
`95b4974bfd980ddc1051ac11fd018ecbf9e3b8b1`; current `origin/main` is
`dab0959dde7849a4812a513d4cff6f354fb66425`, and
`git diff 95b4974bfd980ddc1051ac11fd018ecbf9e3b8b1 dab0959dde7849a4812a513d4cff6f354fb66425 -- data/platforms/pope_ap110`
is empty, so the note's before-state is the immediate before-state for this
change. The after-state is the same ContamX solves on the regenerated
commissioned bundle.

Not changed: any `flow_rate_m3h`, `ach`, `oa_fraction`, `hvac_duty`, AHS
declared flow or `Sanitary_Makeup` link; envelope-leak schema/exporter
semantics; the design-lane declaration; any other hull; any epidemiological
constant. The diff to `air_flow_paths.json` is seven added records and the
regenerated `contam/platform.prj` / `contam/path_map.json`. No campaign
submission.

## Record

All seven records share `"type": "makeup_louvre"`, `"exchange_m3h": 0.0`, and
`"schedule": "always_open"`; each has a Grade C `description` citing the
evidence note and the 2.5 m/s sizing bound.

| zone | AHS | `area_m2` | served demand m³/h | area basis |
|---|---:|---:|---:|---|
| `HD_Boat` | `ahs_nr` 9 | 0.134220 | 1,207.982929 | 1207.982929 / 3600 / 2.5 = 0.134220 |
| `HD_Main` | `ahs_nr` 10 | 0.183574 | 1,652.167982 | 1652.167982 / 3600 / 2.5 = 0.183574 |
| `HD_Troop_Aft_2D` | `ahs_nr` 11 | 0.830908 | 7,478.173193 | 7478.173193 / 3600 / 2.5 = 0.830908 |
| `HD_Troop_Fwd_2D` | `ahs_nr` 12 | 0.571260 | 5,141.339998 | 5141.339998 / 3600 / 2.5 = 0.571260 |
| `HD_Troop_Aft_3D` | `ahs_nr` 13 | 0.830908 | 7,478.173193 | 7478.173193 / 3600 / 2.5 = 0.830908 |
| `HD_CPO_3D` | `ahs_nr` 14 | 0.207748 | 1,869.735693 | 1869.735693 / 3600 / 2.5 = 0.207748 |
| `HD_Troop_Fwd_3D` | `ahs_nr` 15 | 0.415475 | 3,739.278811 | 3739.278811 / 3600 / 2.5 = 0.415475 |

Declared areas are the evidence note's per-HD-branch proportional clear areas;
their six-decimal sum is 3.174093 m² versus the note's total equivalent clear
area 3.174095 m², the difference being per-branch rounding. The 2.5 m/s
free-area face velocity is the prior `ASSUMED-MAKEUP-LOUVRE-AREA` sizing
bound, not a measurement; placement on the HD zones is the owner-ruled
per-branch mechanism assumption. Areas were fixed from the declared served
demand before the after-solve and were not adjusted afterwards.

| Assumption | Value | Grade | Basis |
|---|---|---|---|
| ASSUMED-POPE-MAKEUP-LOCATION | one `makeup_louvre` per exhaust-only HD zone | C | Owner ruling selects explicit ambient make-up openings; the evidence note states placement is unknown. The seven zones are the served zones of the seven exhaust-only sanitary AHS groups whose return-minus-supply demand is carried by envelope leaks. |
| ASSUMED-MAKEUP-LOUVRE-AREA | per-HD areas above | C | Evidence-note Grade C bound: served demand at 2.5 m/s free-area face velocity. Not a measured louvre and not chosen against a pressure target. |
| ASSUMED-POPE-MAKEUP-PASSIVE | `always_open`, no fan, no `wind_speed_m_s` | C | No service supply fan is declared for these routes, so they are passive openings rather than prescribed flows or weather openings. |
| Native rate | `exchange_m3h` 0 | convention (D5) | Commissioned/authored solved legs are inward-only, so the openings are not native contaminant sinks. |

## Witnesses

Official NIST ContamX 3.4.0.3 binary (`third_party/contamx/contamx3`, SHA-256
`d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`, not
committed). Drivers:
`tools/diag/contam_pressure_balance_diagnostic.py --hull pope_ap110 --lane commissioned --lane design --all-paths`,
`tools/contam_flow_compare.py --platform pope_ap110 --run-contamx` on the
committed commissioned bundle, and
`tools/contam_commissioned_check.py --platform pope_ap110`. Both diagnostics
reported 0 unsolved rows after the change.

### Pressure balance

| lane | paths before → after | all max \|ΔP\| Pa before → after | envelope max \|ΔP\| Pa before → after | interior flowing max \|ΔP\| Pa before → after |
|---|---:|---:|---:|---:|
| commissioned | 1,160 → 1,174 | 1,633,363.125 → 214.655655 | 1,633,363.125 → 12.054038 | 67,544.53125 → 0.887779 |
| design | 1,160 → 1,174 | 214.655655 → 214.655655 | — | 0.090717688 → 0.090717688 |

Commissioned boundary balance:

| quantity m³/h | before | after |
|---|---:|---:|
| make-up demand | 28,566.851797 | 28,566.851797 |
| envelope net inward | 28,566.851752 | 73.565294 |
| ambient opening net inward | 0 | 28,493.286537 |
| balance residual | 4.490999e-05 | -3.333163e-05 |

Design boundary balance remains at solver round-off: make-up demand 0;
envelope net inward 0.720015; ambient-opening net inward -0.720046 (net
outward 0.720046 m³/h); balance residual 3.104899e-05. The design lane does
not degrade by the requested witnesses: all-path and interior-flowing max
|ΔP| are unchanged and make-up demand stays 0. The openings' design-lane
gross exchange is 1,285.019392 m³/h inward versus 1,285.739438 m³/h
outward.

After-state class maxima on the commissioned/authored lanes: the all-path
maximum is 214.655655 Pa on zero-flow `ahs_oa`/`ahs_exhaust` rows, the same
value already present on the healthy design lane; `envelope_leak` max is
12.054038 Pa; `ambient_opening` max is 10.375715 Pa; interior max is
1.178519 Pa and interior flowing max is 0.887779 Pa.

### Opening flows and D5

Committed bundle `path_map.json` grows 1,160 → 1,174 entries and
`ambient_opening` legs 0 → 14. Committed-bundle flow compare: 14
`ambient_opening` legs, outward 0 m³/h, inward 28,493.286537 m³/h; native
path inventory includes `ambient_exchange_makeup_louvre`: 7; boundary sink
out is 0.

Commissioned/authored solved flow through the new legs (two legs per zone,
Flow0 negative toward ambient):

| zone | legs | inward m³/h | outward m³/h | max \|ΔP\| Pa |
|---|---:|---:|---:|---:|
| `HD_Boat` | 2 | 1,159.637143 | 0 | 9.479820 |
| `HD_Main` | 2 | 1,631.487560 | 0 | 10.122285 |
| `HD_Troop_Aft_2D` | 2 | 7,477.265292 | 0 | 10.375690 |
| `HD_Troop_Fwd_2D` | 2 | 5,140.432277 | 0 | 10.374521 |
| `HD_Troop_Aft_3D` | 2 | 7,477.265292 | 0 | 10.375715 |
| `HD_CPO_3D` | 2 | 1,868.828062 | 0 | 10.368276 |
| `HD_Troop_Fwd_3D` | 2 | 3,738.370911 | 0 | 10.373204 |
| **total** | 14 | 28,493.286537 | 0 | 10.375715 |

Total inward 28,493.286537 m³/h and 0 m³/h outward, so the declared native
`exchange_m3h` remains 0.0 by D5. The remaining boundary flow is 73.565294
m³/h net inward through envelope leaks, and the balance residual stays at
-3.333163e-05 m³/h.

`tools/contam_commissioned_check.py --platform pope_ap110`: PASS, every
commissioned terminal solved inside 5% of declared. The hull has no
prescribed exhaust-sink boundary rows (`exhaust_sink_out_m3h` 0), so the
forced-exhaust exact check is not applicable to this change.

## Byte pins

`pope_ap110` bundle regenerated with
`scripts/generate_platform_contam_prj.py --platform pope_ap110 --ahs-terminal-mode commissioned`:

| File | SHA-256 |
|---|---|
| `contam/platform.prj` | `128a6cb933648803e455ed6f8b5cb883cdecfe57f0d36d220a4934d1d1d43e0c` |
| `contam/path_map.json` | `69fd0cb214c039f2e4c72d87aa68bab12c4057298dbec9bc33ec3970fc2c986f` |

`git diff --name-only origin/main...HEAD -- data/platforms ':(exclude)data/platforms/pope_ap110/**'`
is empty; the only platform data files changed are the three `pope_ap110`
files (`air_flow_paths.json`, `contam/platform.prj`,
`contam/path_map.json`). The PRJ/path-map diff renumbers later `path_nr`
values because the new opening legs are emitted before the AHS legs; this is
the expected consequence of inserting 14 paths into the committed
commissioned bundle, not a change to another hull or to AHS declared flows.

## Tests

`tests/test_contam_ambient_opening.py::_MAKEUP_RECORDS` gains
`pope_ap110: 7`, and
`tests/test_contam_ambient_opening_boundary.py::test_committed_ambient_opening_legs_are_the_declared_records`
gains `pope_ap110: 14` legs. Both moves are the seven added records and
nothing else; no test was edited to hide a failure. Targeted schema,
ambient-opening, boundary, JSON-schema and data-contract tests pass; the
full fast tier, `sonar_guard`, pre-commit and ledger-entry tests are run
before the PR and recorded in the PR checks.

## Open

- Placement and area are Grade C. AP110 ventilation/HPAC, closure or deck
  drawings naming the actual make-up openings, or geometry-derived areas,
  would replace the assumptions.
- The openings carry 28,493.286537 m³/h of the 28,566.851797 m³/h make-up
  demand; the residual 73.565294 m³/h is still admitted by envelope leaks.
  That is consistent with the evidence note's statement that the openings
  are a boundary mechanism, not a leakage measurement.
