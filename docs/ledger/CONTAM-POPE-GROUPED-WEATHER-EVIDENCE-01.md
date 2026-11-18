# CONTAM-POPE-GROUPED-WEATHER-EVIDENCE-01
**Date:** 2026-11-17
**Commit:** 0229916a
**Pathogens:** all
**Status:** open
**Measured at:** 0229916a

## Scope

G2 Pope leg of [`../proposals/grouped_weather_openings_decision_plan.md`](../proposals/grouped_weather_openings_decision_plan.md) §4/§7: assemble the P0–P3 evidence table and the topology-control witness position for `pope_ap110` before any opening control. This entry changes no behaviour: no `ambient_openings`, no platform data, no topology/HVAC change, no `flow_rate_m3h` change, and no epidemiological constant. Evidence record: [`../audits/2026-11-17_pope_ap110_grouped_weather_evidence/`](../audits/2026-11-17_pope_ap110_grouped_weather_evidence/).

## Measured witness

Fresh local ContamX diagnostic (`tools/diag/contam_pressure_balance_diagnostic.py --hull pope_ap110 --lane commissioned --lane design --all-paths`; binary `third_party/contamx/contamx3`, SHA-256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`) at `0229916a`:

| lane | envelope max abs ΔP | flowing interior max abs ΔP | makeup demand | opening net inward | balance residual |
|---|---:|---:|---:|---:|---:|
| commissioned | 1,355,146.75 Pa | 58,552.332 Pa | 28,574.922724 m³/h | 0 | 0.000157229 m³/h |
| design | 214.656 Pa | 0.081486 Pa | 0 | 0 | 1.20642e-07 m³/h |

The commissioned row reproduces the committed audit baseline (`docs/audits/2026-11-17_contam_pressure_localization/evidence/current_local_solve_summary.csv`, project SHA-256 `6dde4ae8146221f13557610c2e5737feb52ee4dafc843a3db16f37cb490b9cce`). The committed all-open audit control remains an opening control, not a topology control: envelope max |ΔP| falls to 806,283.75 Pa while flowing-interior max |ΔP| rises to 804,135.812 Pa, concentrated on `ladder_well_5` (`VENT_Machinery -> VENT_Stores_Holds`; baseline net −5,576.084 m³/h / max |ΔP| 58,552.332 Pa; all-open net −10,527.138 m³/h / max |ΔP| 804,135.812 Pa).

## Open decisions recorded, not guessed

- P0 intended AP110 operating/closure state is **open**: repo evidence gives `usn_ww2` era practice and draft GA/Contam starter openings, but no HPAC/closure schedule or watertight-door/hatch state for `VENT_Stores_Holds`.
- P2 candidate-edge adjudication is **open**: adjacency/`openings_draft.json` are starter/draft evidence; hobbyist overrides require watertight-door/hatch confirmation.
- P3 `VENT_Stores_Holds` grouping is **open for owner decision**: the 28-room group mixes three open-deck candidates with enclosed stores/holds/tankage/superstructure under one `mech_supply_exhaust` group; any split or closure authoring is G-later.
- Control A (topology/closure/HVAC-group change with no new ambient openings) was **not run** because it requires authoring a platform-data change; control B is already witnessed by the committed all-open audit variant and is not adequate alone; control C is blocked until control A exists.

## Validation

- `python3 tools/diag/contam_pressure_balance_diagnostic.py --hull pope_ap110 --lane commissioned --lane design --all-paths` → 2 rows, 0 unsolved; full path output stayed in gitignored `telemetry_buffer/`.
- Byte-pin proof: `data/platforms/pope_ap110/**` unchanged; this PR adds only the audit evidence directory, this ledger entry, and the ledger README registration.
- `pre-commit` run on changed files and `pytest tests/test_ledger_entries.py` run before PR.
