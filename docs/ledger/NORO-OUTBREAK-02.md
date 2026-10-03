# NORO-OUTBREAK-02
**Date:** 2026-10-03
**Commit:** 1e158d47539ab2b8de9ca46ed13db1da028d3238
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 1e158d47539ab2b8de9ca46ed13db1da028d3238

Paired posting-rate re-measurement of the eight NORO-OUTBREAK-01
expedition cells on the post-caregiver image `picard-campaign:campaign-1e158d47`
(digest `sha256:017a0db816da…`; CAREGIVER-V1 + PROPENSITY-V1 default-ON).
Identical voyage draws to OUTBREAK-01 — expedition_cruise_450,
`fl_exp_{7d,12d}_{scr,ren}`, scr split at bp25c7 / bp32.5c18.5 / bp40c30,
nsf 0.29, dose 7.57, seeds 8000–8999 — so the contrast is
voyage-for-voyage, not two independent rates. Manifest
`picard_framework/runs/mega_cruise_campaign/noro_outbreak_02_manifest.json`
(design-of-record; the image serves tier specs via the byte-identical
in-image 01 manifest). 8 arrays × 1000 children on
`picard-campaign-queue`, jobdef `picard-noro-outbreak-01:6`
(image pinned to the campaign-1e158d47 digest), S3 prefix
`campaign/noro_outbreak_02/`; 8000/8000 SUCCEEDED, ~50 min fleet time.
Canary `cb8c43fa` (20 seeds, fl_exp_12d_scr bp32.5c18.5) verified
`vsp_trigger_epoch`/posted fields and `engine_git_sha: 1e158d47` before
the fleet ran. Canonical tables:
`docs/norovirus/noro_outbreak_02_readout.md`.

Instrument overlay note (provenance): the pinned image predates
`d71b301a`, so its `tools/diag/instrument_common.py` carries the stale
6-arg `wrap_emit_emesis` and `growth_chain_census` cannot run unpatched.
Every child appended the merged `d71b301a` wrapper to its writable
container layer before the entrypoint (see
`deploy/aws/submit_outbreak_02.py`). Instrumentation-only — the wrap is
observational and does not affect voyage dynamics; engine SHA is
unchanged.

## Measured — frequency (noro_outbreak_02 vs noro_outbreak_01)

- Posted rate rises ~4x on the two high-prevalence 12d screening cells:
  bp32.5c18.5 0.2%→0.7% [0.34,1.44]; bp40c30 0.2%→0.8% [0.41,1.57].
  bp25c7 stays 0.2%→0.1% [0.02,0.56]; exp 7d scr bp40c30 0→0.1%.
  All other cells 0 posted of 1000 (both campaigns).
- Takeoff is within noise of baseline everywhere (Δ −0.9 … +2.2 pp);
  the caregiver mechanism does not move epidemic takeoff.
- Posted voyages' reported pax AR medians 0.016–0.022 — still below the
  expedition class IQR floor (4.0%) even where posting occurs.

## Measured — paired gained/lost (same seeds, n=1000/cell)

- Posted gained/lost: 12d scr bp40c30 **8/2**, bp32.5c18.5 **7/2**,
  bp25c7 1/2, 7d scr bp40c30 1/0, 12d ren 0/1, all others 0/0. Net
  +10 postings map-wide (17 vs 7 on these cells; baseline total was 8
  including the classic cell not re-run here).
- Takeoff churn is large but symmetric (e.g. 131/140 on 7d scr bp25c7,
  50/40 on 12d scr bp32.5c18.5) — the mechanism perturbs individual
  voyages without shifting the marginal takeoff rate.

## Measured — anchor deltas (new − old)

- A3 rep/ill rises +0.16…+0.33 on every screening cell (0.51→0.66–0.71
  on 12d scr; 0.17→0.60–0.66 on 7d scr) — the caregiver reporting lift
  the funnel campaign predicted, now confirmed at 1000-seed scale.
- A8 incidence ratios run hotter: ΔA8 pax +7.4…+17.4, crew +2.8…+19.8
  on screening cells.
- A1/A2 essentially flat (|Δ| ≤ 0.01); A5 pax/crew +0.14…+0.63.
- Detection arrives earlier on several cells (Δdetect −120 … −4 ep);
  vsp epoch ~unchanged where it fires (Δ −5 … +20 ep, n≤8).

## Interpretation

- The posting rate moves in the direction the funnel measurement
  predicted but remains rare: 17 postings in 8000 voyages (0.21%
  pooled), and only the two near-saturated 12d screening cells reach
  ~0.7–0.8% — at the low end of the MIDRS ~0.5%-class reference, not
  above it.
- The lift comes through the reporting channel (A3), consistent with
  CAREGIVER-V1's design; it does not create outbreaks that weren't
  already taking off (Δtakeoff ≈ 0, ΔA1/A2 ≈ 0).
- Even where posting occurs, reported attack rates stay under the
  class IQR floor — the illness-expression deficit (A1 0.01, A2 0.13)
  that OUTBREAK-01 measured is unchanged by the caregiver mechanism.
