# LEDGER-FORMAT-01
**Date:** 2026-09-17
**Commit:** this PR
**Status:** closed

New norovirus ledger entries are stored as one file per stable identifier
under `docs/norovirus/ledger/`. This removes the shared running number from
concurrent pull requests while preserving the numbered history in the main
ledger.
