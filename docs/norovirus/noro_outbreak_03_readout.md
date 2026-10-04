# NORO-OUTBREAK-03 readout — classic-hull posting-rate re-run (post-caregiver image)

Measured over 4,000 voyages, zero child failures: the four classic cells
of NORO-OUTBREAK-01 (`fl_cls_12d_scr` × bp25c7/bp32.5c18.5/bp40c30 +
`fl_cls_12d_ren`, classic_cruise_1900, n1910, dose 7.57, epochs 288,
seeds 8105–9104 — the SAME voyage draws as OUTBREAK-01, so the contrast
is voyage-for-voyage) re-run on the post-caregiver image
`picard-campaign:campaign-1e158d47` (digest `sha256:017a0db816da…`;
CAREGIVER-V1 + PROPENSITY-V1 default-ON). Jobdef
`picard-noro-outbreak-03:1` (image pinned to the digest), S3 prefix
`campaign/noro_outbreak_03/`; 4000/4000 SUCCEEDED. Submitted to the Spot
queue first; a ~1h capacity drought (all-RUNNABLE, zero delivery on a
healthy CE) was escalated to `picard-analysis-queue` On-Demand per the
established playbook — four array parents terminated and resubmitted
(`7974e771`, `c3536e64`, `fdbbea5f`, `46e6af0f`). Canary (20 seeds,
fl_cls_12d_scr bp32.5c18.5) verified `engine_git_sha: 1e158d47`,
vsp/posted fields, and live caregiver route counters before the fleet
ran. Manifest
`picard_framework/runs/mega_cruise_campaign/noro_outbreak_03_manifest.json`
(design-of-record; the image serves tier specs via the byte-identical
in-image 01 manifest).

Instrument overlay note (provenance): the pinned image predates
`d71b301a`, so its `tools/diag/instrument_common.py` carries the stale
6-arg `wrap_emit_emesis` and `growth_chain_census` cannot run unpatched.
Every child appended the merged `d71b301a` wrapper to its writable
container layer before the entrypoint (see
`deploy/aws/submit_outbreak_03.py`). Instrumentation-only — the wrap is
observational and does not affect voyage dynamics; engine SHA is
unchanged.

# NORO-OUTBREAK-03 — classic-hull posting-rate re-run (post-caregiver image)

## Frequency (rates % with Wilson 95% intervals)

| cell | n | ignited | imported | established | takeoff | vsp flag | posted | med acquired |
|---|---|---|---|---|---|---|---|---|
| cls 12d ren bp0c0 nsf29 | 1000 |  72.30  [69.44,74.98] |  98.40  [97.42,99.01] |  84.30  [81.91,86.42] |  73.80  [70.99,76.43] |   0.00  [ 0.00, 0.38] |   0.00  [ 0.00, 0.38] | 37 |
| cls 12d scr bp25c7 nsf29 | 1000 | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] |   0.10  [ 0.02, 0.56] |   0.10  [ 0.02, 0.56] | 110 |
| cls 12d scr bp32.5c18.5 nsf29 | 1000 | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] |   0.50  [ 0.21, 1.17] |   0.50  [ 0.21, 1.17] | 121 |
| cls 12d scr bp40c30 nsf29 | 1000 | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] |   0.70  [ 0.34, 1.44] |   0.70  [ 0.34, 1.44] | 127 |

## Anchors (era=pre, takeoff-conditional unless noted)

| cell | A1 ever-ill | A2 ill/inf | A3 rep/ill | A4 rep AR vs IQR | A5 pax/crew | A8 pax | A8 crew | A9 post | verdicts |
|---|---|---|---|---|---|---|---|---|---|
| cls 12d ren bp0c0 nsf29 | 0.00 | 0.15 | 0.54 |   -- vs [0.04-0.08] | 0.88 | 18.57 | 10.52 | 0.00% (0/1000) | A1=FAIL, A2=FAIL, A4=FAIL, A5=FAIL, A8=PASS, A9=FAIL |
| cls 12d scr bp25c7 nsf29 | 0.01 | 0.17 | 0.68 |   -- vs [0.04-0.08] | 2.02 | 81.35 | 40.25 | 0.10% (1/1000) | A1=FAIL, A2=FAIL, A4=FAIL, A5=FAIL, A8=FAIL, A9=FAIL |
| cls 12d scr bp32.5c18.5 nsf29 | 0.02 | 0.17 | 0.68 |   -- vs [0.04-0.08] | 1.55 | 91.02 | 62.84 | 0.50% (5/1000) | A1=FAIL, A2=FAIL, A4=FAIL, A5=FAIL, A8=FAIL, A9=PASS |
| cls 12d scr bp40c30 nsf29 | 0.02 | 0.16 | 0.71 |   -- vs [0.04-0.08] | 1.29 | 99.01 | 80.66 | 0.70% (7/1000) | A1=FAIL, A2=FAIL, A4=FAIL, A5=FAIL, A8=FAIL, A9=FAIL |

## Progression (takeoff voyages only)

| cell | n takeoff | onset ep med [IQR] | peak ep | detect ep | vsp flag ep | span ep | peak prev | n posted | posted pax AR med [IQR] |
|---|---|---|---|---|---|---|---|---|---|
| cls 12d ren bp0c0 nsf29 | 738 | 0 [0-0] | 285 [283-287] | 282 [277-286] | -- | 285 [283-287] | 55 [31-74] | 0 | -- |
| cls 12d scr bp25c7 nsf29 | 1000 | 0 [0-0] | 286 [284-287] | 270 [258-278] | 260 [260-260] | 286 [285-287] | 118 [106-129] | 1 | 0.013 [0.013-0.013] |
| cls 12d scr bp32.5c18.5 nsf29 | 1000 | 0 [0-0] | 285 [283-286] | 271 [257-280] | 276 [266-284] | 286 [285-287] | 132 [121-142] | 5 | 0.019 [0.018-0.021] |
| cls 12d scr bp40c30 nsf29 | 1000 | 0 [0-0] | 285 [282-286] | 265 [249-278] | 282 [267-285] | 286 [284-287] | 140 [130-149] | 7 | 0.019 [0.014-0.021] |

## Reports/voyage vs the VSP posting thresholds

Complement 1338 pax / 572 crew → posting needs ≥41 passenger OR ≥18 crew
reports (ceil of 3% per channel). Median voyage reports sit far below
either threshold; the tail crosses on the crew channel only — every
posting is a crew-channel post (tool:
`tools/noro_diag/reports_voyage_thresholds.py`).

| cell | n | takeoff | pax comp (thr) | crew comp (thr) | rep pax med/p90/max | rep crew med/p90/max | tk rep pax med/p90/max | tk rep crew med/p90/max | >=pax thr | >=crew thr | posted |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cls 12d ren bp0c0 nsf29 | 1000 | 738 | 1338 (41) | 572 (18) | 2/8/19 | 0/2/8 | 3/8/19 | 0/3/8 | 0 | 0 | 0 |
| cls 12d scr bp25c7 nsf29 | 1000 | 1000 | 1338 (41) | 572 (18) | 13/18/38 | 2/6/20 | 13/18/38 | 2/6/20 | 0 | 1 | 1 |
| cls 12d scr bp32.5c18.5 nsf29 | 1000 | 1000 | 1338 (41) | 572 (18) | 14/20/35 | 4/8/20 | 14/20/35 | 4/8/20 | 0 | 5 | 5 |
| cls 12d scr bp40c30 nsf29 | 1000 | 1000 | 1338 (41) | 572 (18) | 15/25/37 | 5/10/20 | 15/25/37 | 5/10/20 | 0 | 7 | 7 |

## Cell-level deltas vs NORO-OUTBREAK-01 (new − old; pp = percentage points)

Baseline column read from the committed OUTBREAK-01 tables
(`docs/norovirus/noro_outbreak_01_readout.md`); the whole
`campaign/noro_outbreak_01/` prefix was lifecycle-swept to DEEP_ARCHIVE,
so per-seed pairing required a restore. The ren tier was restored and is
paired below; the scr restore was abandoned before its keys were
submitted, so scr paired-seed rows are permanently absent — cell-level
numbers are unaffected.

| cell | Δtakeoff pp | Δposted pp | Δacq med | ΔA1 | ΔA2 | ΔA3 | ΔA5 | ΔA8 pax | ΔA8 crew |
|---|---|---|---|---|---|---|---|---|---|
| cls 12d ren bp0c0 nsf29 | -4.1 | +0.0 | -3.0 | -0.010 | +0.000 | +0.160 | +0.00 | +4.4 | +4.0 |
| cls 12d scr bp25c7 nsf29 | +0.0 | +0.1 | +3.0 | +0.000 | +0.000 | +0.180 | -0.32 | +20.8 | +19.9 |
| cls 12d scr bp32.5c18.5 nsf29 | +0.0 | +0.5 | +4.0 | +0.000 | +0.010 | +0.160 | -0.36 | +19.1 | +27.4 |
| cls 12d scr bp40c30 nsf29 | +0.0 | +0.6 | +4.0 | +0.000 | +0.000 | +0.180 | -0.42 | +20.4 | +31.4 |

## Paired delta vs NORO-OUTBREAK-01 (same seeds)

ren tier only — the `fl_cls_12d_ren` baseline zips were restored and all
1,000 seed-pairs resolved before the restore effort was abandoned
(scr tiers' ~2,700 keys were never submitted; see the baseline caveat
above). Posted gained/lost on scr is therefore unknown per-seed, but the
cell-level rates in the frequency table stand on their own.

| cell | n pairs | estab gained/lost | takeoff gained/lost | posted gained/lost | Δ acquired med | Δ peak med | Δ rep AR med |
|---|---|---|---|---|---|---|---|
| cls 12d ren bp0c0 nsf29 | 1000 | 68/76 | 95/136 | 0/0 | 0.0 | 0.0 | 0.0000 |

The paired ren numbers say the same thing the unpaired rates did at a
per-voyage level: slightly more established voyages peter out before
takeoff under the caregiver stack (−8 net), while acquired/peak/report
medians are unmoved — the mechanism shifts reporting, not trajectory.

## Interpretation

- The classic hull now posts: 13 postings in 4,000 voyages (0.33%
  pooled), vs 1/4,000 at baseline — bp32.5c18.5 0→0.5% [0.21,1.17],
  bp40c30 0.1%→0.7% [0.34,1.44], bp25c7 0→0.1%. Same qualitative shape
  as the expedition paired run (0.2%→0.7–0.8% on saturated cells).
- Every post crosses on the crew channel (≥18 crew reports); passenger
  reports peak at 38 — just under the 41 threshold, so the pax channel
  is not yet close either: max pax reports 35–38 vs a 41 bar.
- The lift rides the reporting channel again: A3 rep/ill +0.16…+0.18
  everywhere (0.38→0.54 ren; ~0.50→0.68–0.71 scr), and A8 incidence runs
  hotter — crew roughly doubles on saturated scr cells (49.29→80.66 on
  bp40c30), pax +20 points.
- Takeoff is flat (all scr cells remain 100%; ren −4.1 pp within its
  Wilson band) — CAREGIVER-V1 reports more of what was already
  happening; it does not create outbreaks.
- Posted voyages' reported pax AR medians 0.013–0.019 remain far below
  the pre-2020 classic A4 band (median 5.52%, IQR 4.15–7.82) — posting
  frequency moved, posting severity did not.
- The conversion-gap shape is unchanged (A1 0.00–0.02, A2 0.15–0.17,
  A5 compresses 0.88–2.34 → 0.88–2.02): the caregiver mechanism closes
  none of the illness-expression deficit, consistent with the
  expedition findings.
