# NORO-OUTBREAK-03
**Date:** 2026-10-04
**Commit:** 1e158d47539ab2b8de9ca46ed13db1da028d3238
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 1e158d47539ab2b8de9ca46ed13db1da028d3238

Paired posting-rate re-measurement of the four NORO-OUTBREAK-01 classic
cells on the post-caregiver image `picard-campaign:campaign-1e158d47`
(digest `sha256:017a0db816da…`; CAREGIVER-V1 + PROPENSITY-V1 default-ON).
Identical voyage draws to OUTBREAK-01 — classic_cruise_1900,
`fl_cls_12d_scr` at bp25c7 / bp32.5c18.5 / bp40c30 + `fl_cls_12d_ren`,
nsf 0.29, dose 7.57, epochs 288, seeds 8105–9104 — so the contrast is
voyage-for-voyage, not two independent rates. Manifest
`picard_framework/runs/mega_cruise_campaign/noro_outbreak_03_manifest.json`
(design-of-record; the image serves tier specs via the byte-identical
in-image 01 manifest). 4 arrays × 1000 children, jobdef
`picard-noro-outbreak-03:1` (image pinned to the campaign-1e158d47
digest), S3 prefix `campaign/noro_outbreak_03/`; 4000/4000 SUCCEEDED.
Spot drought (~1h all-RUNNABLE, zero delivery) escalated to
`picard-analysis-queue` On-Demand — array parents `7974e771`, `c3536e64`,
`fdbbea5f`, `46e6af0f`. Canary (20 seeds, fl_cls_12d_scr bp32.5c18.5)
verified `vsp_trigger_epoch`/posted fields, `engine_git_sha: 1e158d47`,
and live caregiver route counters before the fleet ran. Canonical tables:
`docs/norovirus/noro_outbreak_03_readout.md`.

Instrument overlay note (provenance): the pinned image predates
`d71b301a`, so its `tools/diag/instrument_common.py` carries the stale
6-arg `wrap_emit_emesis` and `growth_chain_census` cannot run unpatched.
Every child appended the merged `d71b301a` wrapper to its writable
container layer before the entrypoint (see
`deploy/aws/submit_outbreak_03.py`). Instrumentation-only — the wrap is
observational and does not affect voyage dynamics; engine SHA is
unchanged.

Baseline caveat (provenance): the whole `campaign/noro_outbreak_01/`
prefix was lifecycle-swept to DEEP_ARCHIVE, so per-seed pairing required
a restore initiated from the user's credentials — `picard-deploy-role`
lacks `s3:RestoreObject`. The ren tier (1,000 keys) was restored and
paired; the scr restore was abandoned before its ~2,700 keys were
submitted, so scr paired-seed rows are permanently absent. Cell-level
deltas in the readout are computed against the committed OUTBREAK-01
tables and are unaffected.

## Measured — frequency (noro_outbreak_03 vs noro_outbreak_01)

- The classic hull now posts: bp32.5c18.5 0→0.5% [0.21,1.17],
  bp40c30 0.1%→0.7% [0.34,1.44], bp25c7 0→0.1% [0.02,0.56]; ren stays
  0/1000. 13 postings in 4,000 voyages (0.33% pooled) vs 1 at baseline —
  the same shape as expedition's paired run (0.2%→0.7–0.8% on saturated
  cells).
- Every post crosses on the crew channel (≥18 crew reports at comp 572);
  passenger reports max 35–38 vs the ≥41 bar — the pax channel never
  crosses. Median voyage reports: 13–15 pax / 2–5 crew on scr cells.
- Takeoff flat (scr 100% both campaigns; ren −4.1 pp inside Wilson) —
  the caregiver mechanism reports more of what was already happening.

## Measured — anchor deltas (new − old)

- A3 rep/ill +0.16…+0.18 on all four cells (0.38→0.54 ren;
  ~0.50–0.53→0.68–0.71 scr) — the reporting lift confirmed at classic
  scale.
- A8 incidence hotter: ΔA8 pax +4.4 ren / +19.1…+20.8 scr;
  ΔA8 crew +4.0 ren / +19.9…+31.4 scr (bp40c30 crew 49.29→80.66).
- A1/A2 flat (|Δ| ≤ 0.01); A5 pax/crew compresses −0.32…−0.42 on scr.
- Posted pax AR medians 0.013–0.019 stay far below the pre-2020 classic
  A4 band (median 5.52%, IQR 4.15–7.82) — posting frequency moved,
  posting severity did not.

## Interpretation

- Posting rate moves in the direction the funnel/expedition evidence
  predicted and lands at the same order on saturated cells (~0.5–0.7%),
  at the low end of the MIDRS ~0.5%-class reference — but exclusively
  through the crew channel; the larger passenger complement keeps the
  pax threshold out of reach.
- The lift comes through reporting (A3) and measured incidence (A8),
  consistent with CAREGIVER-V1's design; it does not create outbreaks
  (Δtakeoff ≈ 0) and does not close the illness-expression deficit
  (A1 0.00–0.02, A2 0.15–0.17) — matching OUTBREAK-02's conclusion at
  the next hull class up.

## Measured — paired delta vs NORO-OUTBREAK-01 (ren only)

- `fl_cls_12d_ren` fully paired (1,000 seed-pairs): established 68/76,
  takeoff 95/136 (net −41 takeoff voyages), posted 0/0 — ren stays
  non-posting under the caregiver stack. Δ acquired/peak/rep-AR medians
  all 0: reporting shifts, trajectory doesn't.
- scr paired-seed table **dropped** — the scr baseline keys were never
  submitted for restore before the effort was abandoned; posting
  gained/lost per-seed on scr is unknown, and the cell-level posting
  rates above are the measurement of record.
