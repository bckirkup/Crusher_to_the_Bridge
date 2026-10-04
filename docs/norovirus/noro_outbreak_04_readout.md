# NORO-OUTBREAK-04 readout — 4 spirit cells, voyage-paired vs NORO-OUTBREAK-01

Measured over 4,000 voyages, zero child failures, at engine `1e158d47`
(image `picard-campaign:campaign-1e158d47`, digest `sha256:017a0db8…`,
CAREGIVER-V1 + PROPENSITY-V1 default-ON). Identical voyage draws to the
OUTBREAK-01 spirit extension — spirit_cruise_3000, `fl_spr_12d_scr` split
at bp25c7 / bp32.5c18.5 / bp40c30 + `fl_spr_12d_ren`, nsf 0.29, dose 7.57,
epochs 288, seeds 8105–9104 — so the posting contrast is
voyage-for-voyage. Jobdef `picard-noro-outbreak-04:1` (image pinned to
digest), prefix `campaign/noro_outbreak_04/`, 4 arrays × 1000 children on
`picard-campaign-queue` (~2.3 h fleet). Canary `38459575` (20 seeds,
fl_spr_12d_scr bp32.5c18.5) verified vsp/posted and caregiver fields +
`engine_git_sha: 1e158d47` before the fleet ran. Instrument overlay: the
pinned image predates `d71b301a`, so each child appended the fixed
`wrap_emit_emesis` to `instrument_common.py` in its writable layer —
instrumentation-only (see `deploy/aws/submit_outbreak_04.py`).

Headline: **spirit posts for the first time — 3/1000 on scr-bp40c30
(0.30% [0.10, 0.88]), all through the crew channel** (≥27 crew reports;
pax max 58 vs the 63 wire). Baseline was zero postings on all 4,000
voyages. The lift arrives through the reporting channel (A3 +0.15…+0.18),
pushing A8 incidence 20–75% higher and costing the two marginal anchor
passes the 01 image earned (A5 scr-bp25c7 2.70→2.04; A8 ren 17.91→24.79
— both now out of band from opposite sides). Takeoff, A1 and A2 are
flat: the caregiver mechanism does not create outbreaks, it reports
them.

# NORO-OUTBREAK-04 readout

## Frequency (rates % with Wilson 95% intervals)

| cell | n | ignited | imported | established | takeoff | vsp flag | posted | med acquired |
|---|---|---|---|---|---|---|---|---|
| spr 12d ren bp0c0 nsf29 | 1000 |  89.80  [87.77,91.53] |  99.90  [99.44,99.98] |  96.00  [94.60,97.05] |  91.30  [89.39,92.89] |   0.00  [ 0.00, 0.38] |   0.00  [ 0.00, 0.38] | 90 |
| spr 12d scr bp25c7 nsf29 | 1000 | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] |   0.00  [ 0.00, 0.38] |   0.00  [ 0.00, 0.38] | 182 |
| spr 12d scr bp32.5c18.5 nsf29 | 1000 | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] |   0.00  [ 0.00, 0.38] |   0.00  [ 0.00, 0.38] | 195 |
| spr 12d scr bp40c30 nsf29 | 1000 | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] | 100.00  [99.62,100.00] |   0.30  [ 0.10, 0.88] |   0.30  [ 0.10, 0.88] | 204 |

## Anchors (era=pre, takeoff-conditional unless noted)

| cell | A1 ever-ill | A2 ill/inf | A3 rep/ill | A4 rep AR vs IQR | A5 pax/crew | A8 pax | A8 crew | A9 post | verdicts |
|---|---|---|---|---|---|---|---|---|---|
| spr 12d ren bp0c0 nsf29 | 0.01 | 0.15 | 0.53 |   -- vs [0.04-0.07] | 1.50 | 24.79 | 12.10 | 0.00% (0/1000) | A1=FAIL, A2=FAIL, A4=FAIL, A5=FAIL, A8=FAIL, A9=FAIL |
| spr 12d scr bp25c7 nsf29 | 0.02 | 0.17 | 0.68 |   -- vs [0.04-0.07] | 2.04 | 85.85 | 45.80 | 0.00% (0/1000) | A1=FAIL, A2=FAIL, A4=FAIL, A5=FAIL, A8=FAIL, A9=FAIL |
| spr 12d scr bp32.5c18.5 nsf29 | 0.02 | 0.17 | 0.68 |   -- vs [0.04-0.07] | 1.46 | 92.82 | 65.71 | 0.00% (0/1000) | A1=FAIL, A2=FAIL, A4=FAIL, A5=FAIL, A8=FAIL, A9=FAIL |
| spr 12d scr bp40c30 nsf29 | 0.02 | 0.16 | 0.70 |   -- vs [0.04-0.07] | 1.28 | 100.41 | 81.64 | 0.30% (3/1000) | A1=FAIL, A2=FAIL, A4=FAIL, A5=FAIL, A8=FAIL, A9=FAIL |

## Progression (takeoff voyages only)

| cell | n takeoff | onset ep med [IQR] | peak ep | detect ep | vsp flag ep | span ep | peak prev | n posted | posted pax AR med [IQR] |
|---|---|---|---|---|---|---|---|---|---|
| spr 12d ren bp0c0 nsf29 | 913 | 0 [0-0] | 286 [285-287] | -- | -- | 286 [285-287] | 99 [66-124] | 0 | -- |
| spr 12d scr bp25c7 nsf29 | 1000 | 0 [0-0] | 286 [285-287] | 273 [264-282] | -- | 286 [286-287] | 195 [181-208] | 0 | -- |
| spr 12d scr bp32.5c18.5 nsf29 | 1000 | 0 [0-0] | 286 [284-287] | 274 [262-281] | -- | 286 [285-287] | 212 [199-225] | 0 | -- |
| spr 12d scr bp40c30 nsf29 | 1000 | 0 [0-0] | 286 [284-287] | 273 [257-280] | 278 [277-281] | 286 [285-287] | 224 [211-237] | 3 | 0.017 [0.016-0.019] |

## Posted voyages (all three, scr-bp40c30)

All crossings are crew-channel: reported crew cases 27–28 vs the ≥27
wire; reported passenger cases 33–39 remain well short of ≥63.

| run | seed | pax rep AR | crew rep AR | pax reports | crew reports | vsp ep | acquired | peak prev |
|---|---|---|---|---|---|---|---|---|
| `…_bp40c30_…_s8511` | 8511 | 1.57% | 3.00% | 33.0 | 27.0 | 277 | 218 | 240 |
| `…_bp40c30_…_s8721` | 8721 | 1.86% | 3.11% | 39.1 | 28.0 | 278 | 239 | 265 |
| `…_bp40c30_…_s8887` | 8887 | 1.71% | 3.11% | 35.9 | 28.0 | 281 | 228 | 249 |

## Paired postings vs NORO-OUTBREAK-01 (same seeds)

The 01 baseline posted **zero of 4,000** spirit voyages (committed
`noro_outbreak_01_readout.md`), so the posting contrast is exact
per-seed: every 04 posting is a gain, no posting can be lost.

| cell | n pairs | posted gained/lost |
|---|---|---|
| spr 12d ren bp0c0 nsf29 | 1000 | 0/0 |
| spr 12d scr bp25c7 nsf29 | 1000 | 0/0 |
| spr 12d scr bp32.5c18.5 nsf29 | 1000 | 0/0 |
| spr 12d scr bp40c30 nsf29 | 1000 | **3/0** (s8511, s8721, s8887) |

## Reported cases per voyage vs the VSP posting cutoffs

Cutoffs: ≥3% of channel complement → ≥63 passenger reports or ≥27 crew
reports on spirit (2100 pax / 900 crew). The crew channel is the nearer
wire post-caregiver: median crew reports rose to 8 on the saturated cell
with max 28 crossing; passenger reports sit at ~30–40% of their wire
(med ~24, max 58).

| cell | n | pax reports med [IQR] | pax max | pax over wire | crew reports med [IQR] | crew max | crew over wire | posted (either) |
|---|---|---|---|---|---|---|---|---|
| spr 12d ren bp0c0 nsf29 | 1000 | 6.1 [2.1-10.1] | 29 | 0 of >=63 (  0.00  [ 0.00, 0.38]) | 1.0 [0.0-2.0] | 9 | 0 of >=27 (  0.00  [ 0.00, 0.38]) | 0 (  0.00  [ 0.00, 0.38]) |
| spr 12d scr bp25c7 nsf29 | 1000 | 21.0 [18.1-25.0] | 50 | 0 of >=63 (  0.00  [ 0.00, 0.38]) | 4.0 [3.0-6.0] | 21 | 0 of >=27 (  0.00  [ 0.00, 0.38]) | 0 (  0.00  [ 0.00, 0.38]) |
| spr 12d scr bp32.5c18.5 nsf29 | 1000 | 22.1 [18.9-26.0] | 55 | 0 of >=63 (  0.00  [ 0.00, 0.38]) | 7.0 [5.0-9.0] | 25 | 0 of >=27 (  0.00  [ 0.00, 0.38]) | 0 (  0.00  [ 0.00, 0.38]) |
| spr 12d scr bp40c30 nsf29 | 1000 | 23.9 [19.9-27.9] | 58 | 0 of >=63 (  0.00  [ 0.00, 0.38]) | 8.0 [6.0-11.0] | 28 | 3 of >=27 (  0.30  [ 0.10, 0.88]) | 3 (  0.30  [ 0.10, 0.88]) |

## Cell-level deltas vs committed NORO-OUTBREAK-01 readout (new − old)

Baseline values are the committed `noro_outbreak_01_readout.md` cell
statistics (the 01 zip payloads are lifecycle-archived in S3 Deep
Archive; a Standard-tier restore of the two spirit tiers was requested
2026-10-04 and the full per-seed established/takeoff pairing can be
backfilled from `--import-root` once objects are hot — the posting
contrast above is already exact, since the baseline posted count is
committed zero).

| cell | Δtakeoff pp | Δposted pp | Δacq med | Δpeak prev | Δdetect ep | ΔA1 | ΔA2 | ΔA3 | ΔA5 | ΔA8 pax | ΔA8 crew |
|---|---|---|---|---|---|---|---|---|---|---|---|
| spr 12d ren bp0c0 nsf29 | −0.1 | 0.0 | +1 | +3 | n/a (now null) | 0.00 | 0.00 | +0.15 | +0.19 | +6.9 | +4.9 |
| spr 12d scr bp25c7 nsf29 | 0.0 | 0.0 | +7 | +8 | +2 | 0.00 | −0.01 | +0.18 | −0.66 | +19.3 | +21.9 |
| spr 12d scr bp32.5c18.5 nsf29 | 0.0 | 0.0 | +4 | +5 | −2 | 0.00 | 0.00 | +0.18 | −0.50 | +22.2 | +28.3 |
| spr 12d scr bp40c30 nsf29 | 0.0 | +0.3 | +5 | +5 | +2 | 0.00 | 0.00 | +0.18 | −0.38 | +23.2 | +34.9 |

Anchor verdicts that changed: ren **A8 pax PASS→FAIL** (17.91→24.79,
now over the band's top); scr-bp25c7 **A5 pax/crew PASS→FAIL**
(2.70→2.04, now under the band's floor — crew reports rose faster than
passenger reports). No new passes.

Other observations: `detection_epoch` is now null on every ren takeoff
voyage (baseline 282 [282-282]); scr detection is unchanged (~ep 273).
Crew-channel vsp flags fire on exactly the 3 posted voyages (ep
277–281).
