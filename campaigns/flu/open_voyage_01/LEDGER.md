# FLU-OPEN-01 ledger — open-voyage influenza census

> Status: **specced, not yet run**. Design + frozen verdict frames:
> `DESIGN.md`. Do not alter the frames after any cell has run.

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

## Open decisions

- Whether the canary on the exp block (1 child) precedes the four block
  submits — default yes per `campaign-preflight`.
- Whether `docs/flu/flu_open_voyage_01_readout.md` gets an
  `open_voyage` surface row in `flu_open_ledger.md` §2 — yes on first
  measured readout.
