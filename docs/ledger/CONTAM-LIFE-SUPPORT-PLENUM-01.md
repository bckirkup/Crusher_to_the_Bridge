# CONTAM-LIFE-SUPPORT-PLENUM-01
**Date:** 2026-11-16
**Commit:** a61aca07
**Pathogens:** all
**Status:** measured
**Measured at:** a61aca07

The two Enterprise fiction hulls now use a dedicated life-support plenum as the only hull ambient boundary in the hobbyist ContamX export. Owner direction: the Enterprise ship models should be sealed and operate as close to 1 atm as possible; the prior boundary was one tiny `envelope_leak` per real zone plus a `Mess_Hall` make-up louvre, which left `enterprise_galaxy_tng` with localized flight/engineering/sanitary pressure singularities.

Change: `tools/contamw34_prj.py` gains an opt-in `life_support_plenum` hobbyist override. When enabled it appends an exporter-only `LS_Plenum` zone (1 m³, Grade C numerical boundary volume), replaces every per-zone `envelope_leak` with a non-transfer `life_support_link` orifice (0.2 m² per link, Grade C numerical boundary area), suppresses declared `ambient_openings`, and emits one paired `ambient_opening` relief/make-up orifice on the plenum sized from explicit ambient exhaust links plus the AHS ambient imbalance (including commissioned exhaust-only heads) at the existing 2.5 m/s Grade C louvre face-velocity assumption. The plenum is not in `spatial_layout.json`, so the ContamX transport lane treats `life_support_link` endpoints as unknown and does not create contaminant transfer paths.

Measured at `a61aca07` with local ContamX (`third_party/contamx/contamx3`):

- design lane max |ΔP|: Constitution 10.591 Pa, Galaxy 35.544 Pa; ambient make-up inflow equals declared exhaust 5,000 / 8,000 m³/h.
- commissioned lane max |ΔP|: Constitution 10.603 Pa, Galaxy 35.544 Pa; ambient make-up inflow 9,411.593 / 14,557.774 m³/h.
- `PYTHONPATH=. .venv/bin/python tools/contam_commissioned_check.py --platform enterprise_constitution_tos --platform enterprise_galaxy_tng --tolerance 0.05` PASS: 570 / 1,432 emitted paths against 63 / 127 declared room branches, every commissioned terminal inside 5%.

Link-area sweep that set the Grade C 0.2 m² choice (Galaxy commissioned): 0.002 m² -> 1,289.859 Pa; 0.02 -> 234.685 Pa; 0.2 -> 35.544 Pa; 1.0 -> 10.826 Pa, with ambient inflow fixed at the declared demand. 0.2 m² is the compromise between pressure residual and opening size; 1.0 m² is lower pressure but a much larger boundary.

Verification: `pytest tests/test_contam_life_support_plenum.py` plus the Contam exporter/ContamX slices passed (234 focused exporter tests and 51 ContamX interop tests), `tests/test_json_schema_validation.py` passed 220 tests, both regenerated `path_map.json` files validate against `schemas/contam_path_map.schema.json`, `tools/sanity_checker.py --from-config` passed with the two pre-existing TAT warnings, and pre-commit/ruff/Sonar guards passed.

Status: measured for the exporter/boundary change. No campaign re-measurement; frozen campaign artifacts keep their inputs. Native `air_flow_paths.json` / `spatial_layout.json` are unchanged; only the ContamW export bundles and hobbyist overrides changed.
