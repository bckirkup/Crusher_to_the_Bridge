# Duct-spine transport contract audit and fix plan

> **Status:** Proposed audit; no fix has landed. Measured against
> `origin/main` `0bfc058d` (2026-11-17). Audit ledger:
> [`../ledger/CONTAM-DUCT-TRANSPORT-01.md`](../ledger/CONTAM-DUCT-TRANSPORT-01.md).
> Fleet inventory:
> [`../audits/2026-11-17_duct_spine_fleet_inventory/fleet_inventory.csv`](../audits/2026-11-17_duct_spine_fleet_inventory/fleet_inventory.csv).
> This document lives in `docs/proposals/` because the contract it versions is
> not decided in-tree; its inventory is measured, but it is not documentation
> of current intended behaviour.

**Evidence base.** The committed record of the executed analysis is
[`../audits/2026-11-17_contam_pressure_localization/`](../audits/2026-11-17_contam_pressure_localization/)
(findings.md §3, qa.md §1–2, localization_review.md "Additional
transport-interface issue"), landing via PR #1286 (open at authoring; not yet
on `main`). Those reports pin revision
`c93fa32fbe05440e797de8b551a2781b236d7e43`; this session re-verified that
`tools/contamw34_prj.py`, `engines/contamx_transport.py`,
`engines/contamx_ahs_bridge.py` and the `greg_mortimer` /
`spirit_cruise_3000` platform data are byte-identical between the pin and
current `origin/main` (`git diff c93fa32f..origin/main` on those paths is
empty).

**Evidence vocabulary.** *Measured* = counted this session from committed
files at `0bfc058d`, or quoted from the committed audit record. *Inferred* =
follows from measured facts plus the cited code path. *Unverified* = not
measured anywhere; labelled as such.

## 1. Finding (bounded restatement)

Fresh hobbyist Contam exports append an auxiliary duct network — duct trunk
element, per-room terminal junctions, and duct segments — to the **pressure
solve**, but the generated `path_map.json` covers ordinary airflow paths only.
The field transport adapter iterates that map and does not reconstruct the
appended records:

- `tools/contamw34_prj.py:1664-1727` (`_build_duct_spines`, called at
  `tools/contamw34_prj.py:542-543` when `hobbyist and not
  overrides["skip_duct_spines"]`) builds one terminal junction per room of
  each HVAC group with at least `min_rooms_for_trunk` (2) rooms, joined
  sequentially by segments; `tools/contamw34_prj.py:2185-2246` writes them to
  the `.prj` without extending `path_map`.
- `engines/contamx_transport.py:164-191` (`_build_airflow_paths_from_field`)
  consumes only `path_map_entries`; `engines/contamx_ahs_bridge.py:76-113`
  reads only mapped entries with AHS numbers and kinds
  `ahs_return`/`ahs_supply`/`ahs_recirc`; its declared-outdoor-air fallback
  (`engines/contamx_ahs_bridge.py:160-182`) reconstructs simple-AHS
  recirculation only.

Measured consequence (committed audit record, not re-derived here): Spirit's
commissioned project has 1,311 mapped paths alongside 1,462 airflow records
(67 duct segments + 84 terminal junctions); including the actual duct-terminal
flows closes room air budgets (Greg Mortimer 0.083512 → 4.28e-7 kg/s; Spirit
0.641617 → 2.05e-6 kg/s), and all 491 decoded terminal rows across nine saved
cases agree exactly with independent SIM decoding. Terminal sums are
essentially zero: **internal redistribution, not omitted net outdoor supply**.
These are additional pressure-responsive room-to-room routes in the solved
network — not another encoding of the mapped AHS terminal records — and not
evidence of a native-engine defect, a stock-CONTAM concentration failure, or
a fleet-wide result. Full-hull source-to-receptor differences from the field
adapter on affected hulls must not be read as complete CONTAM contaminant
transport until this contract is reconciled.

## 2. Fleet inventory (measured)

Method: counts read from each committed
`data/platforms/<id>/contam/platform.prj` section headers (`N ! duct
junctions:`, `N ! duct segments:`) and `path_map.json` entry counts at
`0bfc058d`. `spine_groups = junctions − segments` (one junction per room, one
segment per consecutive pair). `duct_records_in_pressure_solve =
junctions + segments`; `duct_records_in_path_map` is 0 by exporter
construction (`_build_duct_spines` never appends to `path_map`; spot-verified
on `spirit_cruise_3000`, whose 1,311 path_map entries are all ordinary kinds).
The two Greg/Spirit counts reproduce the audit record exactly (Spirit 67/84,
Greg 23/31).

Of **77 committed Contam bundles**, **9 emit duct spines** — all
`hobbyist_fiction_cruise` exports with no `skip_duct_spines` override:

| platform | junctions (terminals) | segments | spine groups | path_map entries |
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

The other **68 bundles are naval GA Target B exports** with
`skip_duct_spines: true` (and `duct_hvac_ids: []`) in
`contam/hobbyist_overrides.json` plus `author_contam_provenance.json`; all
have 0 junctions / 0 segments. Full per-hull rows:
[`../audits/2026-11-17_duct_spine_fleet_inventory/fleet_inventory.csv`](../audits/2026-11-17_duct_spine_fleet_inventory/fleet_inventory.csv).

`destroyer_baseline` is the only hull with an explicit `duct_hvac_ids`
allow-list (`zone_main`, `zone_lower`), limiting it to 2 spine groups; the
other eight have no duct keys in their overrides, so every HVAC group with
≥2 rooms spined.

**Export-logic consequence (inferred from `tools/contamw34_prj.py:542-543,
1664-1727`).** The spine trigger is `hobbyist=True` (the generator default,
`scripts/generate_platform_contam_prj.py:60-68`) **and** no
`skip_duct_spines` override **and** at least one HVAC group with ≥2 rooms. Five
platforms have **no committed Contam bundle** (`legend_class_nsc`,
`san_antonio_class_lpd`, `messy_cruise_500`, `expedition_cruise_300`,
`fletcher_class_destroyer`) and no overrides; all five have multi-room HVAC
groups in `air_flow_paths.json` (e.g. `expedition_cruise_300` `AHU_1_Upper`
8 rooms, `AHU_2_Main` 9 rooms; `messy_cruise_500` 72 groups). A future
`--hobbyist` export of any of them would emit spines. Per-hull spine flow
magnitudes on the seven non-Greg/Spirit spined hulls are **unverified** — no
committed `.sim` exists to decode; only presence is measured here.

## 3. Authoring-intent determination (measured, cited)

**Determination: the duct spines are an unanchored hobbyist-pack placeholder
for generic duct leakage trunks on fiction/cruise hulls that have no real
duct model — authoring decoration, not documented intended coupled-transport
physics.** No in-repo document establishes them as intended vessel physics,
and none rules them out; the contract choice is an owner decision (qa.md §1
qualification, preserved).

Citations:

- Introduced 2026-07-18 in `ca19560f` (PR #163, "hobbyist-plus fiction ships")
  as one of the portfolio-grade pack features alongside typed orifices, wind,
  filters, schedules, annotations and species.
- `data/contam_hobbyist/README.md`: `duct_defaults.json` = "Darcy trunk
  leakage spines"; `data/contam_hobbyist/duct_defaults.json` itself: "Darcy-Colebrook
  trunk defaults for hobbyist duct leakage spines" (0.30 m diameter, 5 m
  segments, `terminal_loss_Ct` 0.5, leakage 1.0 Ls/m² at 250 Pa).
- `docs/CONTAM_INTEROP.md` lists "duct leakage spines" among hobbyist-plus
  features and states these PRJs are "**fiction-plausible**, not as-built
  ship models."
- `tools/contamw34_prj.py:1665-1667` docstring: naval GA Target B sets
  `skip_duct_spines` / empty `duct_hvac_ids` "so engineers author real ducts
  in ContamW (**ducts are not on general arrangements**)."
- `docs/SHIP_BLUEPRINT_IMPORT.md` (hobbyist_overrides row; "Fiction Darcy
  duct spines are omitted by default (`skip_duct_spines`) so engineers author
  real ducts from HVAC drawings — those details are not on GAs") and
  `docs/GA_IMPORT_APPROACH.md` ("Duct spines, AHU sizing, fan schedules,
  leakage classes — `skip_duct_spines` default stays on").
- Presence is test-pinned for the hobbyist exports:
  `tests/test_contam_hobbyist_destroyer.py:84-86`,
  `tests/test_contam_hobbyist_constitution.py:50`,
  `tests/test_contam_hobbyist_galaxy.py:49`,
  `tests/test_contam_hobbyist_mega.py:71`.
- No `docs/ledger/` entry mentions duct spines, junctions or segments
  (grepped 2026-11-17); git history shows no design document beyond the
  hobbyist-pack feature list.

The spines' geometry and loss parameters are hobbyist defaults, not
measured or drawn values, and the naval import flow deliberately omits them
for exactly that reason. Treating them as intended vessel physics would
require new evidence (duct drawings, fan curves, leakage classes — Target C
handwork per `docs/SHIP_BLUEPRINT_IMPORT.md`).

## 4. Contract options

Each option is its own future PR with its own ledger entry, `Pathogens: all`.
This PR is stage 0 (audit + plan) only. "Witnesses" below are the minimum
before/after evidence; none is a fleet rerun.

| Option | Contract | Witnesses / validation | Cost | Risk |
|---|---|---|---|---|
| **A — represent duct transport in the field adapter** | Parse duct junction/segment SIM records (embedded record numbers per qa.md §2) and reduce junction mixing, terminal flows and trunk leakage into `airflow_paths` consistently; never count terminals as AHS supply/return or as independent ambient sinks | Room air budgets close on all 9 spined hulls (Greg/Spirit arithmetic already demonstrated); junction mass balances ≤ solver noise; small source→receptor `pulse_t0` cells before/after on the 9 hulls; `contam_flow_compare`/`contam_engine_compare` slices | **High** — new SIM duct-record decoding, a duct-network reduction in `engines/contamx_transport.py`/`contamx_ahs_bridge.py`, contaminant transport through leaky Darcy trunks, tests; must not double-count AHS | Prices unanchored hobbyist geometry (0.3 m ducts, 5 m segments, Ct 0.5, 1 Ls/m² @ 250 Pa) as validated physics; largest engineering cost; only correct if the owner rules the spines intended physics |
| **B — exclude unintended auxiliary duct networks from the pressure solve (exporter-side gate)** | Extend `skip_duct_spines: true` (the existing gate) to the 9 affected hulls — or make skipping the default for exports without real duct data — regenerate bundles, and re-run the bounded pressure witnesses | Room budgets close with mapped paths only once spines are absent; stage-3/4 before/after pressure tables (balance residuals, max \|ΔP\| classes); re-derive stage-4 D5 `exchange_m3h` axes for the six cruise hulls from spine-free solves; byte-pin and `test_contam_hobbyist_*` spine assertions updated; `destroyer_baseline.sim` fixture decision | **Medium** — data-only per hull plus one exporter-default decision, bundle regeneration, test updates | Changes the pressure fields underlying merged stage-3/4 measurements (see §5); declared Grade C rates inherit spine-free re-derivation; if any spine is later ruled intended physics, that hull needs option A instead |
| **C — per-hull adjudication** | Decide each of the 9 hulls (or each spine group) individually: keep + option A where ducts are defensible, skip where not | As A or B per hull, plus a written per-hull rationale | **Highest** — up to 9 mixed-semantics adjudications and two transport behaviours fleet-wide | Only justified if the owner wants hull-level nuance; `destroyer_baseline`'s explicit `duct_hvac_ids` allow-list suggests a past deliberate choice that needs owner recall before overriding |

**Recommendation.** Absent owner evidence that any spine is intended vessel
physics, **B is the coherent default**: the spines are unanchored
hobbyist placeholders (§3), they create a pressure/transport representation
mismatch the field adapter cannot close (§1), and excluding them makes the
pressure network match the transport contract the adapter actually
implements — the same logic the naval GA Target B flow already applies.
**A** is the physically complete option but validates placeholder geometry as
if it were drawn; choose it only with new duct evidence. **C** only if the
owner rules some hulls' spines intended. This proposal does not choose the
physics; it prices the contracts.

## 5. Load-bearing check on merged stage-3/4 witnesses (measured/inferred)

Stage-3 (`CONTAM-AMBIENT-MAKEUP-CRUISE-01`,
`CONTAM-AMBIENT-MAKEUP-FICTION-01`) and stage-4 cruise/fiction
(`CONTAM-AMBIENT-WEATHER-CRUISE-01`, `CONTAM-AMBIENT-WEATHER-FICTION-01`)
witnesses were measured on **spine-inclusive** solves — all eight stage-3
hulls (six cruise + two Enterprise) and all six stage-4 cruise hulls are in
the §2 spined set; naval stage-4 classes carry no spines. Conclusion:
**not load-bearing for the witnesses' conclusions**, because:

- Every witness is a whole-hull boundary budget (make-up demand = exhaust +
  AHS imbalance; balance residual ≈ 0) or a comparative before/after
  measurement under an identical spine-inclusive pressure field. Duct
  terminals are interior redistribution with ≈0 net boundary exchange
  (terminal sums ≈ 0, qa.md §2; `_build_duct_spines` connects only room
  junctions — no ambient leg exists in `tools/contamw34_prj.py:1664-1727`).
- No merged ledger entry cites duct flows, and the pressure localizations
  verified no duct segment crosses the Greg service cut or the Spirit cabin
  cut (qa.md §3).
- The stage-1 fleet pressure review already documents cruise/fiction
  design-lane implausibility **with** spines present
  (`CONTAM-FIELD-PRESSURE-REVIEW-01` result 6), so spine exclusion does not
  rescue or invalidate that class finding.

**Caveat (inferred, unverified per-hull):** absolute solved values in those
ledgers — stage-4 D5 `exchange_m3h` declarations derived from commissioned-lane
`Flow0` at 1 m/s, and stage-3 max |ΔP| tables — were measured with spines
active. Under option B they must be re-derived/re-verified as bounded
witnesses (six cruise hulls for D5), and the declared Grade C rates carry that
note. This is a targeted re-verification, not a fleet rerun.

## 6. Owner decisions required

1. **Physics ruling:** are the hobbyist duct spines intended vessel physics
   for any hull (starting with `destroyer_baseline`'s explicit
   `duct_hvac_ids`), or authoring decoration fleet-wide? If physics: supply
   or accept the duct evidence option A needs.
2. **Contract choice:** A, B or C per §4 (recommendation: B unless (1) says
   otherwise for a hull).
3. **Export default:** if B, should `skip_duct_spines: true` become the
   exporter default for hulls without real duct data (affects the 5
   unexported platforms' future exports), or stay per-hull override?
4. **Witness scope:** approve the bounded re-verification set in §5 (stage-3/4
   hulls only) before any bundle regeneration merges.
5. **Field-adapter claims:** until the contract lands, field-adapter
   source-to-receptor numbers on the 9 spined hulls carry the audit record's
   caveat; decide whether any committed readout needs an annotation.

## 7. Limits and non-goals

No exporter, engine or transport code changes; no platform data changes; no
fleet rerun; no S3/AWS. Frozen Phase1/Phase2 directories, S3 prefixes,
`_v1` caches and committed readouts untouched. The inventory counts junctions
and segments, not flows; flow magnitudes are measured only for Greg Mortimer
and Spirit (committed audit record) and unverified elsewhere. Nothing here
certifies real-vessel ventilation adequacy or extends the finding to a
fleet-wide result.
