# Ledger entry files

Repository-wide defect and measurement entries are stored as one Markdown file
per entry in this directory. The filename is the entry's stable identifier:
`<ID>.md`, where `<ID>` matches `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$`. Examples
include `AERO-CABIN-06.md`, `SWAB-01.md`, and `FLUSH-S2E.md`.

Every entry begins with this header:

```text
# <ID>
**Date:** YYYY-MM-DD
**Commit:** <7–40 hex SHA of main the entry was authored against, or #NNN PR number>
**Pathogens:** all | comma-separated pathogen profile ids
**Status:** declared|open|measured|closed|superseded
```

`declared` is a campaign design frozen before any of its cells ran — the
campaign-preflight declaration. It carries no numbers and nothing in it may be
quoted as a result; it moves to `measured` when its canary is read out.

`superseded` marks an entry whose frozen design or conclusion was overtaken by
a later change before it produced results — name the superseding entry or SHA
in the body. A superseded design may not be run as spec'd; a revival re-scopes
around the successor.

An entry that reports numbers must also include `**Measured at:** <SHA>`.
Pathogen profile IDs are the `pathogen_id` values in
`data/pathogens/active_profiles.json`.
The remainder uses the same prose style as the relevant open-ledger page.
Numbered norovirus items 00–58 in
`docs/norovirus/norovirus_open_ledger.md` are frozen forever because they are
cross-referenced by number. Per-pathogen "currently withdrawn" pages are
`docs/norovirus/norovirus_open_ledger.md` §1,
`docs/covid/covid_open_ledger.md`, and `docs/flu/flu_open_ledger.md`.
**Every pathogen arm — including fictional bundles — gets a docs home:**
`docs/<name>/` plus `<name>_open_ledger.md`, added to this list and to
`docs/README.md` when the arm lands. New entries never receive a number; refer
to them as ledger `<ID>`.

## Registered entries

New ledger entries are registered here as they land; the filename remains the stable identifier.

- `CONTAM-AMBIENT-WEATHER-CRUISE-01.md` — ambient-exposure stage 4, cruise class: 23 open weather-deck zones on the six cruise hulls declare `exposure: weather` (D7(b)) and a Grade C `open_deck` `ambient_openings` record; ΔT = 0 resolution — ContamX solves 0 outward at ambient deck temperature and ignores the exported wind (flag clear, `Ws=0`), so a record's `wind_speed_m_s` imposes constant windward/leeward `wPset` on its own two legs; D5 — native `exchange_m3h` = commissioned-lane solved outward flow at the committed 1 m/s (27,472–421,508 m³/h, 11.7–171.7 ACH), axis 0–10 m/s; design-lane max |ΔP| does not worsen on any hull (classic 693 → 127 Pa, spirit 1,213 → 757 Pa, greg 938 → 934 Pa unchanged); six bundles regenerated, phase 2 `_02` design rebuilt, opening guards moved; no `flow_rate_m3h`, leak area or balcony factor changed.
- `CONTAM-AMBIENT-MAKEUP-FICTION-01.md` — ambient-exposure stage 3, fiction class (discharges the fiction half of governing-plan stage 6 `CONTAM-FIELD-ENVELOPE-MAKEUP-01` per D6(a), completing cruise+fiction): Grade C `makeup_louvre` `ambient_openings` on `enterprise_constitution_tos` and `enterprise_galaxy_tng`, placed on `Mess_Hall`; D5 method — native `exchange_m3h` 0.0 from the ContamX-solved outward range (0 on both hulls and lanes); design-lane max |ΔP| 1.67e5/1.25e5 Pa → 13.7/3.25e4 Pa with the galaxy flight/engineering residual recorded; two bundles regenerated and opening guards moved; no exhaust magnitude or leak constant changed.
- `CONTAM-AMBIENT-MAKEUP-CRUISE-01.md` — ambient-exposure stage 3, cruise class (discharges the cruise half of governing-plan stage 6 `CONTAM-FIELD-ENVELOPE-MAKEUP-01` per D6(a)): Grade C `makeup_louvre` `ambient_openings` on the six cruise hulls, placed on the room the galley transfer draws from; D5 method — native `exchange_m3h` 0.0 from the ContamX-solved outward range (0 on every hull and lane); design-lane max |ΔP| 1.76e5–7.16e5 Pa → 11.3–1,213 Pa (three hulls inside 0.5–374 Pa, three residuals recorded); six bundles regenerated, phase 2 `_02` design rebuilt; no exhaust magnitude or leak constant changed.
- `CONTAM-AMBIENT-OPENING-BOUNDARY-01.md` — ambient-exposure stage 2 (no platform declares a record): the ContamX field lane treats solved outward `ambient_opening` flow as a contaminant boundary sink independently of `envelope_leak_mode`; compare/pressure diagnostics report ambient-opening rows; one-hull paired-orifice witness, mass-balance closure, and fleet zero-declaration guard.
- `CONTAM-AMBIENT-OPENING-SCHEMA-01.md` — ambient-exposure stage 1 (no platform declares a record): optional `ambient_openings` list in the `air_flow_paths.json` schema, native `ambient_exchange_<type>` exchange sink, exporter emitter and path_map `kind: "ambient_opening"`; D8 decision (paired orifices at two heights) with the one-hull ContamX witness; 82-platform byte-identity witness
- `CONTAM-AMBIENT-EXPOSURE-01.md` — ambient-exposure audit (no behaviour change): 82-platform inventory of weather-deck zones (243), `balcony_partial` zones (153), opening adjacency edges and the 12 ambient links with their treatment in the native and ContamX lanes; owner-hypothesis verdict per class; in-memory envelope-area sweep showing the cruise/fiction exhaust-sink pressures are a missing-make-up symptom; proposed `ambient_openings` representation and owner decisions
- `CONTAM-FIELD-PRESSURE-REVIEW-01.md` — stage 1 pressure/balance diagnostic (no behaviour change): `tools/diag/contam_pressure_balance_diagnostic.py` and the 77-hull fleet table of per-path ΔP, envelope direction/flow, AHS return-minus-supply imbalance, blocked one-way openings and native-vs-field outflow coefficients; defines the stage-6 envelope/make-up scope by hull class.
- `CONTAM-FIELD-POOLDECK-OPENINGS-01.md` — class-(b) Expedition pool-deck opening authoring fix: duplicate CasualDining doorway removed, ObsLounge open-deck void corrected to a doorway, Expedition bundle re-synced, before/after witnesses recorded, and class-(d) evidence deferred to the pressure-review/envelope-makeup sequence.
- `CONTAM-PAIRED-RECOMPARE-01.md` — paired native/commissioned/authored exact-integral diagnostic rerun after the #1241 `plr_bdq` laminar fix, with pre-fix change-detector reproduction and per-trajectory closure.
- `CONTAM-FIELD-ADJUDICATION-01.md` — doc-only adjudication of Edison's preserved native-vs-field Contam differences at `78a023b6`: per-class verdicts, measured flow/ΔP/material-time evidence, and versioned fix stages; no transport-kernel defect proven.
- `CONTAM-FIELD-ENVELOPE-BOUNDARY-01.md` — stage 5 (verdict (e)): owner decision that outward envelope leakage is a contaminant sink; solved-positive `envelope_leak` flow becomes a boundary sink in the ContamX lane and compare fates, with `pressure_only` baseline mode, destroyer before/after witnesses and fleet enumeration; no path_map schema or data change.
- `CONTAM-FIELD-AHS-COMMISSIONED-01.md` — class-(f) stage: fleet re-export of committed authored Contam bundles to the declaration-faithful commissioned AHS terminal encoding, with byte-pinned path_map counts, paired before/after measurements, and the Phase-2 P lane marked historical design-mode.
- `CONTAM-BDQ-LAMINAR-01.md` — commissioned one-way passive `plr_bdq` openings now carry the documented NIST TN 1887r1 laminar-transition coefficient, with live two-zone and hull-level ContamX controls.
- `CONTAM-PATHMAP-FILTERED-01.md` — PATHMAP-FILTERED stage 2: path_map `filtered` carry-through, schema, and exporter endpoint fail-loud.
- `CONTAM-EXHAUST-SINK-02.md` — EXHAUST-SINK stage 3: explicit `ambient` sink endpoints across schema, sanity checks, native transport, exporter/path_map, and the ContamX lane; inert until stage 4.
- `CONTAM-EXHAUST-SINK-03.md` — EXHAUST-SINK stage 4: re-point the three audited exhaust links to ambient sinks with before/after native exact-check measurements.
- `CONTAM-BUNDLE-RESYNC-01.md` — EXHAUST-SINK stage 5: re-sync the stale committed Contam bundles for `mega_cruise_5000` and the two Enterprise hulls from committed hull JSON.
- `CONTAM-EXHAUST-SINK-04.md` — EXHAUST-SINK stage 6 row 1: re-point the two `Dining_to_Galley_Transfer` links to ambient sinks with before/after native exact-check measurements and the `mega_cruise_5000` bundle re-sync.
- `CONTAM-EXHAUST-SINK-05.md` — EXHAUST-SINK stage 6 row 2: author galley hood once-through ambient sinks paired to the existing galley make-up links, with before/after native exact-check measurements and bundle/Phase-2 re-syncs.
- `FOOD-SUPPLY-01-SMOKE.md` — bounded local smoke of the default-off provisioning receipt/lot arms on one mega p06 cell.
- `FOOD-SUPPLY-01-RECEIPT-PIN.md` — receipt/lot `station_zone_pin` carry-through fix and seed-pairing contract.
- `FOOD-SUPPLY-01-PIN-RESMOKE.md` — pinned seed-8118 re-smoke of the FOOD-SUPPLY-01 receipt arms after the carry-through fix.
- `FOOD-SUPPLY-01-CANARY.md` — pinned 20-seed local canary of the FOOD-SUPPLY-01 receipt/lot arms on one mega p06 cell.
- `FOOD-SUPPLY-01-SEED-SCAN.md` — AWS Batch supply-initiation census over 126,200 seeds × 3 arms: contaminated station-lot/receipt prevalence, served-lot yield, lot-size/titre, and item-line composition.
- `FOOD-SUPPLY-01-WORST-CASES.md` — full-fidelity worst-case supply-seed examples across the four hulls: final posted AR, VSP timing, role channels, and supply witnesses.
- `FOOD-SUPPLY-01-REDEPOSIT-WORST.md` — paired mega worst-seed `shedders_only` vs `carriers` hand-redeposit contrast: posting, role AR, timing, route/channel witnesses, and supply/census pairing caveats.
- `NORO-HAND-CASCADE-01-MEAL-SECONDARY.md` — posted-cell same-span secondary-transmission probe for provisioned-lot pans.
- `NORO-HAND-CASCADE-01-PAN-COHORT-REACH.md` — posted-cell non-taker pan-cohort reach probe for secondary hand transfers.

## For drafting and analysis

Anyone (human or agent) drafting a manuscript, report or analysis from this repository must draw from, in this order:
1. The pathogen's open-ledger page — `docs/norovirus/norovirus_open_ledger.md` §1, `docs/covid/covid_open_ledger.md` §1, or `docs/flu/flu_open_ledger.md` §1 — for what is currently withdrawn. A figure listed there may not be quoted as a result.
2. Ledger entries in this directory with `Status: measured` or `closed`, quoting the `Measured at` SHA alongside every number. If that SHA is not an ancestor of the current `main` head with no later entry touching the same mechanism, the number is historical, not current.
3. Readouts under `docs/covid/`, `docs/norovirus/` and `docs/flu/` only as the evidence behind an entry; their header records the `main` SHA they were run at and must match.
Constants are quoted from their definition-site provenance comment with its evidence grade (`.agents/skills/model-parameter-provenance/SKILL.md`), never from a readout.
