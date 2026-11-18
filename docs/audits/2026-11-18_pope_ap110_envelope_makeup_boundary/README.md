> **Status:** Evidence note for the `pope_ap110` ContamX envelope/make-up boundary residual. This note authors no openings, platform data, schema, exporter, constants, or behaviour change.

# Pope AP110 envelope/make-up boundary residual

## Scope and pins

- Repository: `bckirkup/Crusher_to_the_Bridge`; branch base `origin/main` `95b4974bfd980ddc1051ac11fd018ecbf9e3b8b1` (includes #1303 Pope control-A).
- ContamX: official NIST ContamX 3.4.0.3 at `third_party/contamx/contamx3`, SHA-256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`.
- Witness command: `.venv/bin/python tools/diag/contam_pressure_balance_diagnostic.py --hull pope_ap110 --lanes commissioned,design --all-paths`; output `telemetry_buffer/contam_pressure_balance_diagnostic/pope_ap110_envelope_makeup.json`, **2 rows, 0 unsolved**.
- Commissioned-terminal check: `.venv/bin/python tools/contam_commissioned_check.py --platform pope_ap110` → **PASS**, every commissioned terminal inside 5% of declared.
- Prior evidence: `docs/ledger/CONTAM-POPE-TOPOLOGY-01.md`, `docs/audits/2026-11-17_pope_ap110_grouped_weather_evidence/`, `docs/ledger/CONTAM-FIELD-PRESSURE-REVIEW-01.md`.

## Witness summary

| lane | paths | all max \|ΔP\| Pa | interior flowing max \|ΔP\| Pa | make-up demand m³/h | envelope net inward m³/h | ambient opening inward m³/h | balance residual m³/h |
|---|---:|---:|---:|---:|---:|---:|---:|
| commissioned | 1,160 | 1,633,363.125 | 67,544.53125 | 28,566.851797 | 28,566.851752 | 0 | 4.490999e-05 |
| design | 1,160 | 214.655655 | 0.090717688 | 0 | -1.041614e-07 | 0 | 1.041614e-07 |

The commissioned design-lane contrast is the residual: the design lane has no AHS return-minus-supply imbalance and no make-up demand, while the commissioned lane has seven exhaust-only AHS groups and 28,566.85 m³/h of make-up demand.

## Path-level attribution

### Envelope maximum

The commissioned all-path maximum is an `envelope_leak`, not an interior path:

| path_nr | from_zone | to_zone | kind | flow m³/h | ΔP Pa |
|---:|---|---|---|---:|---:|
| 80 | `Engine_Rm_Fwd` | `ambient` | `envelope_leak` | -358.642074 | -1,633,363.125 |
| 77 | `Engine_Rm_Aft` | `ambient` | `envelope_leak` | -358.622044 | -1,633,180.625 |
| 62 | `Hold7_Berthing_1P` | `ambient` | `envelope_leak` | -358.614746 | -1,633,114.250 |
| 63 | `Hold6_Berthing_1P` | `ambient` | `envelope_leak` | -358.614746 | -1,633,114.250 |
| 64 | `Hold5_Berthing_1P` | `ambient` | `envelope_leak` | -358.614724 | -1,633,114.000 |

Envelope census, commissioned lane:

- 88 `envelope_leak` paths, one per non-phantom zone.
- 80 carry inward flow, 8 are zero-flow, **0 carry outward flow**.
- Active inward total: **-28,566.851752 m³/h** (inward magnitude 28,566.851752).
- Active inward flow range: about -358.642 to -350.919 m³/h; median absolute envelope ΔP 1,631,180.375 Pa.
- Zero-flow envelope paths: `Top_House`, `Nav_Bridge`, `Signal_Control_Block`, `Boat_Deck_Open`, `Stern_Gun_Deck`, `Aft_Loading_House`, `Resistor_House_Aft`, `Focsle_Deck`.

The separate interior flowing maximum remains **67,544.53125 Pa** on `ladder_well_5` paths, led by path_nr 708 `Engine_Casing_Fwd_1P -> Refrig_Stores` at -23.233602 m³/h. That is the post-control-A interior residual recorded in `CONTAM-POPE-TOPOLOGY-01.md`; it is not the envelope maximum and is not itself a boundary make-up path.

### Make-up legs

The diagnostic identity is:

`makeup_demand = AHS return-minus-supply + exhaust_sink_out`
`balance_residual = makeup_demand - envelope_net_inward - ambient_opening_net_inward`

Measured commissioned values: exhaust sink out = 0, ambient openings = 0, AHS return-minus-supply = 28,566.851797 m³/h, envelope net inward = 28,566.851752 m³/h, residual = 4.490999e-05 m³/h.

The AHS imbalance is exactly seven exhaust-only sanitary groups (`ahs_nr` 9-15), each with supply 0 and return equal to its make-up demand:

| AHS group | served HD zone | return = demand m³/h | `Sanitary_Makeup` inward m³/h | direct HD-zone envelope inward m³/h | check sum m³/h |
|---:|---|---:|---:|---:|---:|
| 9 | `HD_Boat` | 1,207.982929 | 849.997259 | 357.985714 | 1,207.982973 |
| 10 | `HD_Main` | 1,652.167982 | 1,293.767232 | 358.400728 | 1,652.167960 |
| 11 | `HD_Troop_Aft_2D` | 7,478.173193 | 7,119.667712 | 358.507501 | 7,478.175213 |
| 12 | `HD_Troop_Fwd_2D` | 5,141.339998 | 4,782.882706 | 358.457561 | 5,141.340267 |
| 13 | `HD_Troop_Aft_3D` | 7,478.173193 | 7,119.613259 | 358.561124 | 7,478.174383 |
| 14 | `HD_CPO_3D` | 1,869.735693 | 1,511.171422 | 358.561101 | 1,869.732523 |
| 15 | `HD_Troop_Fwd_3D` | 3,739.278811 | 3,380.767784 | 358.511184 | 3,739.278968 |
| **total** |  | **28,566.851797** | **26,057.867375** | **2,508.984913** | **28,566.852279** |

Path-level reading:

- `Sanitary_Makeup` has 70 path-map rows; 60 solve positive, gross/positive total 26,057.867375 m³/h. Largest single legs are `Crew_Berthing_1P -> HD_Troop_Aft_2D` and `Crew_Berthing_1P -> HD_Troop_Aft_3D` at 3,932.826143 m³/h each.
- The remaining 2,508.984913 m³/h enters the seven HD zones directly through their own `envelope_leak` paths (path_nr 13, 25, 30, 41, 44, 54, 59), not through `ambient_openings`.
- The remaining 73 active inward envelope leaks are the non-HD-zone side of the same balance: they admit 26,057.866839 m³/h inward while `Sanitary_Makeup` carries 26,057.867375 m³/h from served rooms into the HD zones. There are no `ambient_openings` rows.

This is the already-ledgered fleet-wide class from `CONTAM-FIELD-PRESSURE-REVIEW-01`: commissioned exhaust-only AHS groups have no authored make-up path, so fixed-area envelope leaks carry the deficit. Pope AP110 is a concrete instance, not a new defect class.

## Candidate boundary fixes

No candidate is authored here. Grades are evidence grades for the *candidate assumption*, not for the measured residual.

| candidate | current expressibility | Grade C bound | evidence that would raise the grade |
|---|---|---|---|
| Explicit make-up opening declarations | Expressible today as `ambient_openings` records (`makeup_louvre`, `open_deck`, `weather_hatch`, etc.); exporter emits paired orifices and path-map kind `ambient_opening`; **no schema change**. | Total demand is 28,566.851797 m³/h. Using the prior `ASSUMED-MAKEUP-LOUVRE-AREA` 2.5 m/s free-area face velocity only as a sizing bound, one equivalent clear area is 3.174095 m²; per-HD-branch proportional areas are 0.134220 (`HD_Boat`), 0.183574 (`HD_Main`), 0.830908 (`HD_Troop_Aft_2D`), 0.571260 (`HD_Troop_Fwd_2D`), 0.830908 (`HD_Troop_Aft_3D`), 0.207748 (`HD_CPO_3D`), 0.415475 (`HD_Troop_Fwd_3D`) m². Placement is unknown; area is not evidence. | AP110 ventilation/HPAC, closure, or deck drawings naming the actual make-up opening(s); geometry-derived area rather than the 2.5 m/s assumption; paired ContamX witnesses on commissioned and design lanes with 0 unsolved rows; native `exchange_m3h` derived from the measured outward range after solving, not fitted to a pressure target. |
| Envelope leak area declarations | **Not expressible per zone or per hull today.** The export emits one `EnvLeak` element for every zone from `data/contam_hobbyist/orifice_catalog.json` (`area_m2` 0.0001); `air_flow_paths.schema.json` has no envelope-leak area field and `hobbyist_overrides.json` has no consumed envelope-area key. A Pope-specific physical leakage declaration would require schema/exporter support. | Current 0.0001 m² is a solver/Jacobian reference, not an AP110 leakage measurement. The measured conductance is 80 active leaks carrying 28,566.851752 m³/h at median |ΔP| ≈1.631 MPa. Any physical area model must admit that demand; exact area cannot be derived from the residual without choosing a target pressure, which would be fitting. | AP110 hull leakage/closure schedule or measured leakage; orifice-coefficient validation; scratch ContamX solves over a declared area axis before any authoring; owner decision whether leakage is per-zone, per-deck, or hull-total. |
| `boundary_sink` semantics | Already implemented as `hvac.contamx.envelope_leak_mode` = `boundary_sink` default or `pressure_only` baseline. It changes contaminant fate only, not the pressure network or solved flows. | Commissioned Pope has **0 outward envelope leaks**, so there is no outward envelope contaminant sink to reinterpret. Inward leaks are clean-air make-up and add no contaminant path. This candidate cannot reduce the 1.633 MPa envelope maximum or the 28,566.85 m³/h make-up demand. | Only relevant if a future boundary fix produces outward envelope flow or if the owner wants a transport-fate comparison; would need paired ContamX/native transport witnesses, not pressure witnesses. |

## Owner decisions required before any authoring

1. **Choose the boundary mechanism:** explicit ambient make-up openings versus a declared physical envelope-leakage model versus accepting the residual as the documented commissioned-state artifact.
2. **If openings:** choose placement and type (`makeup_louvre` on machinery/service spaces, weather-exposed decks, or per-HDV-branch locations), and provide or accept Grade C area provenance.
3. **If leakage:** decide whether envelope leakage is per-zone, per-deck, or hull-total, and approve the schema/exporter change needed to declare it; do not tune area to the 1.633 MPa residual or to an arbitrary pressure cutoff.
4. **Set acceptance criteria before a fix PR:** candidate witnesses must be commissioned and design lanes with 0 unsolved rows, plus an owner-accepted pressure-residual target; the stage-4 0.5-374 Pa range is a comparison, not a universal cutoff.
5. **Confirm scope:** keep this to `pope_ap110` boundary work; do not change `flow_rate_m3h`, AHS declared flows, other hulls, epidemiological constants, or the already-ledgered fleet-wide exhaust-only-AHS class.

## Validation

- Docs-only change: one new `docs/audits/2026-11-18_pope_ap110_envelope_makeup_boundary/README.md`.
- No `data/`, engine, exporter, schema, test, ledger, or campaign file is changed; `data/platforms/**` is byte-unchanged.
- No ledger entry is created, so `tests/test_ledger_entries.py` is not implicated.
- Pre-commit is run on the changed file before PR.
