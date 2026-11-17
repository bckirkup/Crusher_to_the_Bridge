# CONTAM-DUCT-TRANSPORT-01
**Date:** 2026-11-17
**Commit:** 0bfc058d
**Pathogens:** all
**Status:** open
**Measured at:** 0bfc058d

## Scope

Doc-only audit and contract proposal; no code, data, schema, campaign, S3, or
frozen artifact is changed. Proposal of record:
[`../proposals/duct_transport_contract_audit_and_fix_plan.md`](../proposals/duct_transport_contract_audit_and_fix_plan.md).
Fleet inventory:
[`../audits/2026-11-17_duct_spine_fleet_inventory/fleet_inventory.csv`](../audits/2026-11-17_duct_spine_fleet_inventory/fleet_inventory.csv).
Evidence record: [`../audits/2026-11-17_contam_pressure_localization/`](../audits/2026-11-17_contam_pressure_localization/)
(landing via PR #1286; findings.md §3, qa.md §1–2).

Fresh hobbyist Contam exports append auxiliary duct trunk elements, per-room
terminal junctions and duct segments to the **pressure solve**
(`tools/contamw34_prj.py:1664-1727`, written at `2185-2246`), but
`path_map.json` covers ordinary airflow paths only. The field transport
adapter consumes only the path map
(`engines/contamx_transport.py:164-191`) and the AHS bridge reads only mapped
AHS terminal kinds (`engines/contamx_ahs_bridge.py:76-113`, fallback
`160-182`); neither reconstructs the duct records.

## Measured inventory (at `0bfc058d`)

Of 77 committed Contam bundles, 9 hobbyist fiction/cruise exports emit duct
spines (junctions = terminals, segments, spine groups, path_map entries):

| platform | junctions | segments | groups | path_map |
|---|---:|---:|---:|---:|
| classic_cruise_1900 | 61 | 48 | 13 | 840 |
| destroyer_baseline | 5 | 3 | 2 | 69 |
| diamond_princess | 112 | 94 | 18 | 1,789 |
| enterprise_constitution_tos | 44 | 34 | 10 | 570 |
| enterprise_galaxy_tng | 90 | 73 | 17 | 1,432 |
| expedition_cruise_450 | 31 | 24 | 7 | 347 |
| greg_mortimer | 31 | 23 | 8 | 368 |
| mega_cruise_5000 | 124 | 104 | 20 | 2,603 |
| spirit_cruise_3000 | 84 | 67 | 17 | 1,311 |

The 68 naval GA Target B bundles carry `skip_duct_spines: true` and emit zero
duct records. Five platforms have no committed Contam bundle; the exporter
trigger (`hobbyist` and no `skip_duct_spines` and an HVAC group with ≥2 rooms)
implies their future `--hobbyist` exports would emit spines. Counts were read
from committed `platform.prj` section headers and `path_map.json`; Greg/Spirit
counts reproduce the audit record exactly. Per-hull duct flow magnitudes
outside Greg Mortimer and Spirit are unverified (no committed `.sim`).

## Authoring intent (cited in the proposal)

Unanchored hobbyist-pack placeholder for generic duct leakage trunks
("Darcy trunk leakage spines", `data/contam_hobbyist/`), introduced with the
2026-07-18 hobbyist-plus fiction package (`ca19560f`, PR #163); the naval GA
flow deliberately omits spines because ducts are not on general arrangements
(`tools/contamw34_prj.py:1665-1667`, `docs/SHIP_BLUEPRINT_IMPORT.md`,
`docs/GA_IMPORT_APPROACH.md`). No ledger entry or design document establishes
the spines as intended coupled-transport physics; the contract choice is an
owner decision.

## Contract options and owner decisions

(A) represent and reduce duct transport consistently in the field adapter
(junction mixing, terminals, leakage — high cost, needs duct evidence);
(B) exclude the auxiliary networks from the pressure solve via the existing
exporter-side `skip_duct_spines` gate (medium cost, recommended absent owner
physics evidence); (C) per-hull adjudication (highest cost). Load-bearing
check: merged stage-3/4 witnesses are whole-hull boundary budgets and
comparative before/after measurements on spine-inclusive solves; duct
terminals are interior redistribution with ≈0 net boundary exchange, so the
witness conclusions do not depend on spine flow — but absolute solved values
(stage-4 D5 `exchange_m3h` axes, stage-3 max |ΔP| tables) were measured with
spines active and need bounded re-verification under option B. Owner
decisions: physics ruling per hull, contract choice, exporter default for
unexported platforms, witness scope, and field-adapter readout annotation.

## Follow-ups

Versioned stages are in the proposal. Until one lands, field-adapter
source-to-receptor numbers on the 9 spined hulls must not be described as
complete CONTAM contaminant transport. No measured value in any open ledger
is invalidated by this audit, so no open-ledger notes were added.
