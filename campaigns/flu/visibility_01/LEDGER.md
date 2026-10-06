# FLU-VIS-01 — execution ledger

> **Status:** specced (criteria frozen in `DESIGN.md`, no cells run).
> Campaign `flu/visibility_01`; workers `cell.py`; aggregator
> `readout.py`. Sits on FLU-OPEN-01 (`7f4702ef`).

## Design

- Grid: report_scale {0.25, 0.5, 2.0} (multiply-then-clip 1.0 on both
  reporting vectors) × eligibility {declared, strict(mild=0)} — 6 arms;
  baseline (1.0 × declared) reused from FLU-OPEN-01 pending the
  baseline-canary identity check (DESIGN §3/§5).
- 4 tiers × 100 seeds (8105–8204) × 6 arms = 2400 committed cells;
  4 × `*_r100_dec` blocks (400 cells) declared but submitted only if the
  canary voids reuse.
- Cells identical to FLU-OPEN-01 otherwise (`confinement="organic"`,
  2-pax epoch-0 seed, shipped prevalence draw, k=6e-4, 288 epochs).

## Execution log

| event | detail |
|-------|--------|
| spec | `campaigns/flu/visibility_01/` — DESIGN/cell/readout/campaign.json/LEDGER |
| local smoke | pending |
| image | pending (tag `flu-vis01` at spec-merge SHA) |
| canary | pending (`flu_exp_12d_r100_dec` idx 0 → baseline-identity check) |
| arrays | pending (24 blocks, `picard-analysis-queue` On-Demand) |
| readout | pending (`docs/flu/flu_visibility_01_readout.md` + `docs/ledger/FLU-VIS-01.md`) |

## Open decisions

- whether the four `r100_dec` blocks run for real (only if the baseline
  canary's payload diverges from OPEN-01 `flu_exp_12d/cell_8105.json`).
- whether `active_screening` gets its own arm family (Ward-denominator
  scenario) — parked per DESIGN §7.
