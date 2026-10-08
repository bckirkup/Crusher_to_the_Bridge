# Influenza-A thread

> **Status:** Living. The `influenza_a` arm exists and executes. The scored
> surface is the confined-cabinmate SAR endpoint (`flu.F1`, the Lau 2012 PCR
> SIR spread [0.03, 0.38]) bounded by the dose-derived `confined_sar_floor`
> constants, plus the `flu.F5` ≈0.08 reported/infected internal check — all
> three live in `data/observation/flu_fit_targets.json` (loader:
> `tools/flu_anchors.py`). The arm carries no train/test split; every anchor
> is an internal consistency check, never a fit objective. Read
> [`flu_open_ledger.md`](flu_open_ledger.md) before quoting any figure.

| Doc | Status | Role |
|-----|--------|------|
| [flu_open_ledger.md](flu_open_ledger.md) | Living | Current withdrawals and measurement status for the influenza arm |
| [flu_social_01_readout.md](flu_social_01_readout.md) | Findings | FLU-SOCIAL-01 readout (ledger `FLU-SOCIAL-01`) |
| [flu_reassess_01_readout.md](flu_reassess_01_readout.md) | Measurement of record | FLU-REASSESS-01 post-enhancement re-census (ledger `campaigns/flu/reassess_01/LEDGER.md`) |

Flu ledger entries live at `docs/ledger/FLU-*.md`. Campaign drivers and
readouts are `tools/flu_*.py`; the confined-cell spec machinery they share
with the noro arm is `tools/diag/conditioned_cell.py`.
