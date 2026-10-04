Status: measured readout — partial coverage (campaign halted by user call at
~10% of planned cells; see Coverage).

# NORO-MEGA-01 measured readout — first noro outbreak-map measurement on mega_cruise_5000

Measured at `1e158d47` (jobdef `picard-noro-mega-01:5`, image
`picard-campaign:campaign-1e158d47` digest
`sha256:017a0db816da98a8a9cbf2fe6ca864a4a9e1e061d876216ef9439fc2cbc76202` —
CAREGIVER-V1 + PROPENSITY-V1 composed, mechanisms default-ON). Absolute
measurement, no paired baseline: mega has never run the outbreak map on this
stack; its last noro run was the #37 admissibility gate on 2026-09-06, before
the hand-reservoir rebuild, presentation-share repair, funnel instruments,
and the caregiver/propensity stack.

## Coverage (partial — declared, not patched over)

Planned design: tier `fl_mega_12d_scr`, `mega_cruise_5000`, norovirus,
dose_adjustment 7.57, surveillance `syndromic_comp65`, boarding rung
`shipped`, never_symptomatic_fraction 0.29, boarding_prevalence diagonal
{(0.025,0.007), (0.0325,0.0185), (0.040,0.030)} → 3 cells x 1000 seeds
(8000-8999), 288 epochs, 7000 agents; config_overrides copied from the exp
scr tier of `noro_outbreak_01_manifest.json`.

Delivered: **bp25c7 n=288** (array offset 0, seeds 8000-8287) and
**bp32.5c18.5 n=20** (canary seeds 8000-8019 only). bp40c30 n=0 — its array
was never serviced before cancellation. The user cancelled the remaining
arrays at ~11:40 UTC 2026-10-04 on cost grounds ("too dear for the data");
Batch marks un-run children FAILED, so the large FAILED counts on the
array parents are cancellation artifacts, not defects. Real per-child
failure rate while running: 0/288+. Dumps under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_mega_01/fl_mega_12d_scr/`.

The bp32.5c18.5 column is canary-depth only (n=20) — quoted for direction,
not tight bounds.

## Image-drift caveat (instrumentation-only shim)

Image `1e158d47` predates merged fix `d71b301a` (PR #861): its
`tools/diag/instrument_common.py` `wrap_emit_emesis` inner wrapper lacks
the `*args/**kwargs` tail-forward CAREGIVER-V1 needs, so an unpatched child
dies at its first emesis deposit (`wrapper() takes 6 positional arguments
but 8 were given`). Jobdef `picard-noro-mega-01:5` applies the identical
two-hunk splice to `/app/tools/diag/instrument_common.py` at container
start (one-occurrence asserts fail loudly on drift). Instrumentation-only;
engine untouched. Same workaround class as sibling NORO-OUTBREAK-02's
append-shim, whose 8000 children all SUCCEEDED.

## Frequency (rates % with Wilson 95% intervals)

| cell | n | ignited | imported | established | takeoff | vsp flag | posted | med acquired | med imports |
|---|---|---|---|---|---|---|---|---|---|
| mega 12d scr bp25c7 nsf29 | 288 | 100.00 [98.68,100.00] | 100.00 [98.68,100.00] | 100.00 [98.68,100.00] | 100.00 [98.68,100.00] | 0.00 [0.00,1.32] | 0.00 [0.00,1.32] | 488 | 109 |
| mega 12d scr bp32.5c18.5 nsf29 | 20 | 100.00 [83.89,100.00] | 100.00 [83.89,100.00] | 100.00 [83.89,100.00] | 100.00 [83.89,100.00] | 0.00 [0.00,16.11] | 0.00 [0.00,16.11] | 504 | 160 |

Every boarded voyage ignites and propagates on this hull; none reaches a
VSP posting.

## Progression (takeoff voyages only)

| cell | n takeoff | onset ep med [IQR] | peak ep | detect ep | vsp flag ep | span ep | peak prev | n posted |
|---|---|---|---|---|---|---|---|---|
| mega 12d scr bp25c7 nsf29 | 288 | 0 [0-0] | 287 [286-287] | 282 [267-286] | -- | 287 [286-287] | 516 [494-534] | 0 |
| mega 12d scr bp32.5c18.5 nsf29 | 20 | 0 [0-0] | 287 [286-287] | 278 [260-284] | -- | 287 [287-287] | 540 [509-562] | 0 |

Detection itself is rare and late: only 29/288 (10.1%) of bp25c7 voyages
ever set `detection_epoch` (4/20 on the canary cell), landing at median
epoch 282-283 of 288 — the syndromic channel sees the outbreak only in the
final ~10 hours of a 12-day voyage. Peak prevalence (~516-540 aboard at
peak) arrives at epoch ~287 because incidence is still climbing when the
voyage ends; the epidemic curve does not turn over inside 12 days.

## Reports per voyage vs VSP posting thresholds

VSP trips at >=150 pax OR >=60 crew aboard reports
(`_reported_case_counter_exceeded`, 3% either-channel). Measured report
counts per voyage (complements 4900 pax / 2100 crew aboard):

| cell | n | pax reports med [p90, max] | pax >=150 | crew reports med [p90, max] | crew >=60 | VSP trip |
|---|---|---|---|---|---|---|
| mega 12d scr bp25c7 nsf29 | 288 | 55.4 [65.2, 105.8] | 0/288 | 18.1 [26.0, 47.0] | 0/288 | 0/288 |
| mega 12d scr bp32.5c18.5 nsf29 | 20 | 58.3 [67.1, 82.8] | 0/20 | 21.5 [29.0, 44.1] | 0/20 | 0/20 |

No voyage comes near either channel: the best single voyage delivered 105.8
pax reports (needs 150) and 47.0 crew reports (needs 60) — each channel's
*maximum* sits ~30% under its threshold, and medians are ~2.7x (pax) and
~3.3x (crew) short. Median infection attack rates meanwhile are 9.1% pax /
7.1% crew (9.7% / 8.6% on the canary cell): the outbreaks are large and
real, but the observation funnel — syndromic presentation share, comp65
sick-call, detection arriving at epoch ~280+ — cannot convert them into
VSP report volume inside 12 days. Mega is the deepest tail in the stack,
as predicted.

## Anchors (era=pre, takeoff-conditional unless noted)

| cell | A1 ever-ill | A2 ill/inf | A3 rep/ill | A4 rep AR vs IQR [3.55-7.49%] | A5 pax/crew | A8 pax | A8 crew | A9 post | verdicts |
|---|---|---|---|---|---|---|---|---|---|
| mega 12d scr bp25c7 nsf29 | 0.02 | 0.18 | 0.68 | -- vs [0.04-0.07] | 1.35 | 95.51 | 72.70 | 0.00% (0/288) | A1,A2,A4,A5,A8,A9 all FAIL |
| mega 12d scr bp32.5c18.5 nsf29 | 0.02 | 0.18 | 0.71 | -- vs [0.04-0.07] | 1.04 | 99.67 | 93.25 | 0.00% (0/20) | A1,A2,A4,A5,A8,A9 all FAIL |

Against the mega pre-2020 target row (A4 posted-AR median 6.00%, IQR
3.55-7.49, n=16): nothing posts, so posted-AR is unmeasurable rather than
low — the model produces zero VSP postings where the historical record has
16. All computable anchors FAIL on both cells.

## Operational notes (for the ledger)

- Child sizing: 1 vCPU / 16384 MB. The expedition-calibrated 4096 MB
  container OOM-killed at ~28-33 min (SIGKILL; local probe reached 4.76 GB
  still climbing on a 7000-agent voyage). 16 GB runs ~34 min/child with
  ~3x headroom; zips ~210 MB each (~65 GB delivered).
- Spot drought ~20:18-23:28 UTC 2026-10-03 (~3 h, zero CE capacity);
  canary ran on `picard-analysis-queue` (On-Demand), arrays held for Spot
  per user call and submitted ~00:02 UTC as capacity returned.
- Fleet packing was memory-bound: Spot CE instance types carry ~2 GB/vCPU,
  so the 256-vCPU CE packs only ~30 concurrent 16 GB children fleet-wide;
  observed ~18-20 concurrent for this campaign while sibling campaigns
  held the rest (~25-40 completions/hr). Full-fleet projection at that
  share was ~75-100 h, which is why the user cancelled.
- Array jobs (all `picard-noro-mega-01:5`, queue `picard-campaign-queue`,
  terminated 2026-10-04 ~11:40 UTC): `4cc2390d-f324-4f37-bddf-849a82c7e0a0`
  (offset 0 — delivered all 288), `64d87c9b-7e9c-43d5-aa4d-dce6cef671f6`
  (offset 1000 — canary 20 zips under the same tier prefix; array itself
  never serviced), `d82f1e5b-e277-489a-bdae-be1f30970119` (offset 2000 —
  never serviced).
