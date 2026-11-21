# COVID-H5-RESCORE-01 — readout

> **Status:** Measured (2026-11-20), run against `main` = `eb024892`,
> on the committed THETA-REFIT-01 cell payloads (`Measured at` `c053e15f`).
> Pure readout — no new cells, no constants, no contract change.

## What was run

`tools/covid_h5_rescore.py` decomposes all 840 committed campaign cells
(DP `boxed_s1s2` 12 θ × 20 seeds; GM `hygiene_cycle` 12 θ × 50 seeds),
recomputing the verbatim `merge_fit` T1+T3 loss per cell and attaching
the `covid.H5` band residual (takeoff-conditional `infections_total` vs
[712, 960], log-space distance; inside-band = 0; cells with no
`infections_total` carry no residual) per seed. Paired-seed
bootstrap (2000 resamples, seed 20200205, ties to smaller θ — the
merge's own rule) gives two selection surfaces:

- **verbatim** — T1+T3 only, as scored by THETA-REFIT-01.
- **augmented** — candidate contract: verbatim loss + the H5 band
  residual averaged over the resample's drawn takeoff seeds, equal
  weight. θ rows under the takeoff-seed floor (5) sit out the augmented
  comparison. H5's own declaration forbids fitting Θ to it; the
  augmented column is published as a readout only, to measure whether
  the term *could* move the selection if a contract decision adopted it.

Evidence: `reports/h5_rescore/surface.json` (per-cell projection +
surface). Ledger entry: `docs/ledger/COVID-H5-RESCORE-01.md`.

## Selection surfaces

| contract | winner | freq | runner-up | freq |
|---|---|---|---|---|
| verbatim T1+T3 | 3.162e11 | **0.736** | 1e9 | 0.154 |
| augmented +H5 | 3.162e11 | **0.6315** | 1e9 | 0.1995 |

The verbatim frequency reproduces THETA-REFIT-01's reported 0.736
exactly — the rescore machinery is faithful.

## Per-θ table (DP, takeoff-conditional medians)

| θ | takeoff | infections med | in-band | H5 resid | verbatim loss | recorded_onsets | campaign_pos |
|---|---|---|---|---|---|---|---|
| 7.9e6 | 0.45 | 171 | 1/9 | 1.39 | 50.9 | 8 | 10 |
| 1e7 | 0.45 | 161 | 0/9 | 1.52 | 57.8 | 4 | 8 |
| 3.16e7 | 0.45 | 214 | 0/9 | 1.19 | 53.5 | 5 | 7 |
| 1e8 | 0.80 | 448 | 0/16 | 0.81 | 28.0 | 66 | 48 |
| 3.16e8 | 0.80 | 677 | 2/16 | 0.48 | 21.8 | 216 | 159 |
| 1e9 | 0.90 | 2,246 | 1/18 | 0.78 | 19.2 | 1,460 | 596 |
| 3.16e9 | 0.90 | 2,710 | 1/18 | 0.92 | 20.1 | 1,866 | 683 |
| 1e10 | 0.95 | 3,294 | 0/19 | 1.12 | 15.7 | 2,692 | 676 |
| 3.16e10 | 0.95 | 3,456 | 0/19 | 1.23 | 15.7 | 2,802 | 672 |
| 1e11 | 0.95 | 3,522 | 0/19 | 1.30 | 15.5 | 2,880 | 669 |
| 3.16e11 | 0.95 | 3,573 | 0/19 | 1.31 | 13.7 | 2,878 | 443 |
| 1e12 | 0.95 | 3,599 | 0/19 | 1.32 | 14.2 | 2,812 | 364 |

In-band takeoff cells total: **5/190** across the whole grid.

## GM held-out rows (takeoff-conditional medians)

| θ | takeoff | infections | campaign_pos | asym | recorded_onsets |
|---|---|---|---|---|---|
| 7.9e6 | 0.18 | 77 | 4.0 | 0.50 | 2 |
| 3.16e11 (fitted) | 0.96 | 180 | 108.5 | 0.272 | 46 |
| 1e12 | 0.96 | 205 | 118.0 | 0.239 | 44 |

GM carries no serology band; the asym invariant (0.272 vs 0.8125 at the
fitted θ) is the settled observation-channel residual.

## Reading

- **Empty joint set**: the H5 band lives between θ≈3.16e8 (median 677,
  under floor) and 1e9 (median 2,246, 2.3× over top) — a half-decade
  the observable channels cannot inhabit: at 3.16e8 campaign positives
  run 159 vs the record's 634; at 1e9 recorded onsets run 1,460 vs 197.
- **The defect is capture, not dose**: takeoff-conditional
  confirmed/infections at right-sized truth ≈ 0.60 (406/677 at
  θ=3.16e8) vs the record's ~0.85 (712/840). The all-cells
  `lab_confirmed` median is also reported per θ in the surface JSON
  (`lab_confirmed_total` vs `lab_confirmed_total_takeoff`); the capture
  comparison is made on the takeoff-conditional population only —
  mixing the fizzle-inclusive confirmations with takeoff-only
  infections would understate capture.
- **Augmentation cannot select its way out**: the band residual's
  0.78–1.32 spread is flat next to the verbatim gradient (13.7 vs ≥19.2).
- **Named, not taken**: whether a serology-aware observable enters
  `merge_fit` is a contract decision (H5 is declared held-out-forever);
  this entry measures the surface it would score.
