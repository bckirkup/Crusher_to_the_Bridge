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
**Status:** declared|open|measured|closed
```

`declared` is a campaign design frozen before any of its cells ran — the
campaign-preflight declaration. It carries no numbers and nothing in it may be
quoted as a result; it moves to `measured` when its canary is read out.

An entry that reports numbers must also include `**Measured at:** <SHA>`.
Pathogen profile IDs are the `pathogen_id` values in
`data/pathogens/active_profiles.json`.
The remainder uses the same prose style as the relevant open-ledger page.
Numbered norovirus items 00–58 in
`docs/norovirus/norovirus_open_ledger.md` are frozen forever because they are
cross-referenced by number. Per-pathogen "currently withdrawn" pages are
`docs/norovirus/norovirus_open_ledger.md` §1 and
`docs/covid/covid_open_ledger.md`. New entries never receive a number; refer
to them as ledger `<ID>`.

## For drafting and analysis

Anyone (human or agent) drafting a manuscript, report or analysis from this repository must draw from, in this order:
1. The pathogen's open-ledger page — `docs/norovirus/norovirus_open_ledger.md` §1 or `docs/covid/covid_open_ledger.md` §1 — for what is currently withdrawn. A figure listed there may not be quoted as a result.
2. Ledger entries in this directory with `Status: measured` or `closed`, quoting the `Measured at` SHA alongside every number. If that SHA is not an ancestor of the current `main` head with no later entry touching the same mechanism, the number is historical, not current.
3. Readouts under `docs/covid/` and `docs/norovirus/` only as the evidence behind an entry; their header records the `main` SHA they were run at and must match.
Constants are quoted from their definition-site provenance comment with its evidence grade (`.agents/skills/model-parameter-provenance/SKILL.md`), never from a readout.
