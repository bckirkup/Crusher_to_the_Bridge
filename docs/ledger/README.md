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

- `CONTAM-PAIRED-RECOMPARE-01.md` — paired native/commissioned/authored exact-integral diagnostic rerun after the #1241 `plr_bdq` laminar fix, with pre-fix change-detector reproduction and per-trajectory closure.
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
- `NORO-HAND-CASCADE-01-MEAL-SECONDARY.md` — posted-cell same-span secondary-transmission probe for provisioned-lot pans.
- `NORO-HAND-CASCADE-01-PAN-COHORT-REACH.md` — posted-cell non-taker pan-cohort reach probe for secondary hand transfers.

## For drafting and analysis

Anyone (human or agent) drafting a manuscript, report or analysis from this repository must draw from, in this order:
1. The pathogen's open-ledger page — `docs/norovirus/norovirus_open_ledger.md` §1, `docs/covid/covid_open_ledger.md` §1, or `docs/flu/flu_open_ledger.md` §1 — for what is currently withdrawn. A figure listed there may not be quoted as a result.
2. Ledger entries in this directory with `Status: measured` or `closed`, quoting the `Measured at` SHA alongside every number. If that SHA is not an ancestor of the current `main` head with no later entry touching the same mechanism, the number is historical, not current.
3. Readouts under `docs/covid/`, `docs/norovirus/` and `docs/flu/` only as the evidence behind an entry; their header records the `main` SHA they were run at and must match.
Constants are quoted from their definition-site provenance comment with its evidence grade (`.agents/skills/model-parameter-provenance/SKILL.md`), never from a readout.
