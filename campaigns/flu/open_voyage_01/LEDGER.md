# FLU-OPEN-01 ledger — open-voyage influenza census

> Status: **measured** at `7f4702ef` — 400/400 cells, 0 failed.
> Design + frozen verdict frames: `DESIGN.md`. Frames were not altered.
> Readout of record: `docs/flu/flu_open_voyage_01_readout.md`;
> ledger entry: `docs/ledger/FLU-OPEN-01.md`.

## Intent

Measure the reporting-side surfaces `HOST-AGE-02/03` now own (ever-ill,
reported, age-band presentation, age-band severity mix) plus caregiver
reach, on a **free-running** `influenza_a` voyage — the conditioned-census
spec minus declared SOP-017 — across the four real cruise classes
(expedition_450 / spirit_3000 / classic_1900 / mega_5000), seeds
8105–8204, 288 epochs, single arm, 400 cells.

## Settled inputs (do not re-derive)

- Confined-SAR surface is in-band on all four classes at `8c03e9d7`
  (FLU-SOCIAL-01); this census does not re-measure it.
- FLU-AGE-01 expedition canary (`b4207e5f`): confined endpoint invariant;
  caregiver-pathway divergence flagged as the open-voyage amplifier
  question this census answers.
- Engine delta `b4207e5f..de4441f3` inert for `influenza_a`
  (`susceptibility_age_mode` labels a baseline the arm does not carry).
- `k = 6e-4` shipped (FLU-DELIVERY-01); no constant overrides anywhere.

## Execution log

| date | step | detail |
|------|------|--------|
| 2026-10-05 | spec authored | `campaign.json` (4 blocks × 100 seeds), `cell.py`, `readout.py`, `DESIGN.md`; local short-epoch smoke of `cell.py` on expedition_cruise_450 OK. No AWS submission — pending user approval. |
| 2026-10-05 | image `flu-open-voy01` | root `Dockerfile` + `deploy/aws/Dockerfile.campaign` at merge SHA `7f4702ef`; in-container `--local` run of the literal entrypoint argv produced valid `cell_8105.json` on expedition AND on mega under a hard 4 GB cap (4096 MB confirmed for all blocks). Pushed `picard-campaign@sha256:bc72e55295de111b3b14a987daad3dd422983d5c922b2604befcd5707d952324`. |
| 2026-10-05 | Spot drought | canary `5023fe35` parked ~35 min RUNNABLE on `picard-campaign-queue` (0 capacity, CE desired 256 unmet); terminated, resubmitted On-Demand on user decision. |
| 2026-10-05 | canary + arrays | jobdef `picard-flu-open-voyage-01` revs :1–:2 (canary registers), :3–:6 (blocks); queue `picard-analysis-queue`. Canary `4c84471a` SUCCEEDED + inspected (8 index, organic confinement, ALERT-class). Arrays `18074d2e`/`7224370a`/`bb8fdf0e`/`c86b415f`: **400/400 SUCCEEDED**, ~75 min wall. Prefix `campaign/flu_open_voyage_01/`, 100 `cell_<seed>.json` per block. |
| 2026-10-05 | readout | `readout.py` over synced cells → `docs/flu/flu_open_voyage_01_readout.md` + `docs/ledger/FLU-OPEN-01.md` + `flu_open_ledger.md` §2 row. |

## Open decisions — resolved

- Canary precedes blocks: done (`4c84471a`, inspected).
- `flu_open_ledger.md` §2 row added: `FLU-OPEN-01 | measured | 7f4702ef`.
- Frozen frames read as written; where a frame breached, the readout
  decomposes import vs onboard-acquired cohorts rather than re-scoring —
  the composition failure of the frame is recorded in FLU-OPEN-01, not
  re-frozen here.
