# FLU-VIS-01 — execution ledger

> **Status:** measured — 2400/2400 arm cells, readout of record
> `docs/flu/flu_visibility_01_readout.md`, ledger `docs/ledger/FLU-VIS-01.md`.
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
| spec | `campaigns/flu/visibility_01/` — DESIGN/cell/readout/campaign.json/LEDGER (PR #928, merged `ca775a0b`) |
| local smoke | PASS — exp r025_str cell: resolved eligibility [0,0,0,1,1], reporting ×0.25; 0 mild dated onsets; r100_dec local payload bit-identical to OPEN-01 `cell_8105` counts |
| image | `picard-campaign:flu-vis01` @ `sha256:1c0aa1d570f0fe905b936db9e08b3509369997d5a74999913a3decf95a2a17d3`, ENGINE_GIT_SHA `ca775a0b`; in-container `--local` voyage clean under the 4 GB cap |
| canary | `b346d49d-33b6-4d7c-81ba-d12d39f81052` (jobdef rev :1) SUCCEEDED ~4 min — **baseline-identity PASS**: seed-8105 payload bit-identical to OPEN-01 on every count field, infections, complement → reuse holds, `r100_dec` blocks unsubmitted (contingency not triggered) |
| arrays | 24 blocks submitted 13:40 UTC, jobdef `picard-flu-visibility-01` revs :2–:25, queue `picard-analysis-queue` On-Demand — **2400/2400 SUCCEEDED, 0 FAILED**; ~5.7 h wall (CE shared with a sibling covid session; exp+spr+cls landed ~2.3 h, mega serialized the tail) |
| audits | `index_invariant_fails=0` all cells; arm echo: `arm.resolved` = declared patch on 2401/2401 (0 mismatches); schema `flu_visibility_01.v1` everywhere; strict-arm mild onsets = 0 on all 1200 strict cells (witness fired) |
| readout | `docs/flu/flu_visibility_01_readout.md` + `docs/ledger/FLU-VIS-01.md` + `flu_open_ledger.md` §2 row + `docs/README.md` index row |

## Measured headline

Reporting saturates — no declared corner reaches Ward's ~0.7 %
presenting attack on spr/cls/mega (flat 0.13–0.25 % across the 8× span
including ceiling-saturated r200); exp brackets Ward on every arm. The
big-hull residual is incidence, not visibility. Feedback is real but
non-monotone (r200 *adds* infections on exp); strict-mild is live but
second-order.

## Open decisions

- The four `r100_dec` blocks stay unsubmitted (canary passed).
- The comparator question for the next decision: is Ward's 0.7 % a
  fleet-level expectation or a realized outbreak voyage? Under shipped
  incidence the model answers "off-distribution on the big hulls, at
  Ward on expedition" — the next lever is incidence-side (importation
  intensity / onboard acquisition / exposure window), not the
  observation layer.
- whether `active_screening` gets its own arm family (Ward-denominator
  scenario) — parked per DESIGN §7.
