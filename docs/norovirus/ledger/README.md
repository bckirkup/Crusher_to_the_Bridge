# Norovirus ledger entry files

Entries added after the frozen numbered ledger are stored as one Markdown file
per entry in this directory. The filename is the entry's stable identifier:
`<ID>.md`, where `<ID>` matches `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$`. Examples
include `AERO-CABIN-06.md`, `SWAB-01.md`, and `FLUSH-S2E.md`.

Every entry begins with this header:

```text
# <ID>
**Date:** YYYY-MM-DD
**Commit:** <short sha or PR #>
**Status:** open|measured|closed
```

The remainder uses the same prose style as the numbered items in
`norovirus_open_ledger.md`. Numbered items 00–57 in the main ledger are frozen
forever because they are cross-referenced by number. New entries never receive
a number; refer to them as ledger `<ID>`.
