# NORO-MEGA-01
**Date:** 2026-10-04
**Commit:** 00bd0ee6
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 1e158d47

## Question

First absolute noro outbreak-map measurement on `mega_cruise_5000` in the
current stack (CAREGIVER-V1 + PROPENSITY-V1 at `1e158d47`): what does a
12-day mega voyage do on the `fl_mega_12d_scr` diagonal {(0.025,0.007),
(0.0325,0.0185), (0.040,0.030)}, and does the report funnel ever reach the
mega VSP posting thresholds (>=150 pax OR >=60 crew aboard reports)?
Mega's only prior noro run was the #37 admissibility gate on 2026-09-06,
pre-hand-reservoir-rebuild — no paired baseline exists or was required.

## Coverage (partial — cancelled on cost grounds)

Design was 3 cells x 1000 seeds (8000-8999), 288 epochs, 7000 agents.
Delivered: bp25c7 n=288 (seeds 8000-8287) + bp32.5c18.5 n=20 (canary
seeds 8000-8019); bp40c30 n=0. User terminated all three arrays
(~11:40 UTC 2026-10-04): fleet throughput was memory-bound at ~18-20
concurrent children (16 GB/child on a ~2 GB/vCPU Spot CE → ~30 concurrent
fleet cap, shared with siblings), projecting ~75-100 h for the remaining
~2700 cells. Batch FAILED counts on the array parents are cancellation
artifacts; observed real failure rate was 0/308.

## Measured (n=288 bp25c7; n=20 bp32.5c18.5 canary)

- Frequency: 100% ignited/imported/established/takeoff on both cells;
  vsp flag 0/288 [0,1.32%] and 0/20; posted 0/288 and 0/20.
- Reports per voyage vs thresholds (measured counts): pax med 55.4,
  p90 65.2, **max 105.8 < 150 needed**; crew med 18.1, p90 26.0,
  **max 47.0 < 60 needed** → 0/308 VSP trips. Even the single best voyage
  misses each channel's threshold by ~30%.
- Progression: onset epoch 0 (boarding imports), peak prevalence
  ~516-540 aboard at epoch ~287 — the curve is still climbing when the
  voyage ends; detection fires in only 29/288 (10.1%) of bp25c7 voyages,
  median epoch 282 of 288.
- Infection AR medians: 9.1% pax / 7.1% crew (bp25c7); 9.7% / 8.6%
  (canary cell). Median acquired 488-504/voyage; median imports 109-160.
- A-anchors vs the mega pre-2020 row (A4 median 6.00%, IQR 3.55-7.49,
  n=16): nothing posts → posted-AR unmeasurable; all computable anchors
  FAIL on both cells. Model produces zero VSP postings where the
  historical record has 16 — the report-funnel gap, not the outbreak
  itself, is what fails to reproduce the record.
- Direction (consistent with CHANNEL-03/04 funnel findings): mega is the
  deepest tail — outbreaks ignite and grow freely, but syndromic_comp65
  reporting cannot reach VSP volume inside 12 days.

## Caveats carried forward

- Image `1e158d47` predates `d71b301a` (PR #861): each child applied an
  in-container two-hunk `*args/**kwargs` splice to
  `tools/diag/instrument_common.py` `wrap_emit_emesis` (assert-guarded;
  instrumentation-only, engine untouched) — same workaround class as
  NORO-OUTBREAK-02. Numbers above are from shimmed instrumentation.
- Partial coverage: bp32.5c18.5 is canary-depth (n=20) and bp40c30 has no
  data; no high-prevalence-cell statement is made.
- All dumps remain at
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_mega_01/fl_mega_12d_scr/`
  (308 zips, ~65 GB); resuming the same seeds/jobdef dedup-skips them.
- Ops history: 4 GB container OOM at ~28-33 min on 7000-agent cells →
  jobdef rev 5 at 16 GB (~34 min/child); ~3 h Spot drought 2026-10-03
  20:18-23:28 UTC; Spot fleet cancelled on cost 2026-10-04 ~11:40 UTC.
- Readout: `docs/norovirus/noro_mega_01_readout.md`. Jobdef/manifest:
  commit `9e8e5e42` (`deploy/aws/batch_job_definition_noro_mega_01.json`,
  `picard_framework/runs/mega_cruise_campaign/noro_mega_01_manifest.json`).
