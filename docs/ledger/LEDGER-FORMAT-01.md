# LEDGER-FORMAT-01
**Date:** 2026-09-17
**Commit:** #593
**Pathogens:** all
**Status:** closed

New ledger entries are stored as one file per stable identifier under
`docs/ledger/`. This removes the shared running number from concurrent pull
requests while preserving the numbered history in the main norovirus ledger.
The convention moved to `docs/ledger/` under LEDGER-FORMAT-02.
