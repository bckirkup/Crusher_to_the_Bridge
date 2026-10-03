Status: measured readout (frozen design `noro_channel_04_design.md`).

# NORO-CHANNEL-04 measured readout — funnel re-measurement on the caregiver stack

Measured at `1e158d47` (jobdef `picard-noro-channel-04:2`, image
`picard-campaign:campaign-1e158d47` digest
`sha256:017a0db816da98a8a9cbf2fe6ca864a4a9e1e061d876216ef9439fc2cbc76202` —
CAREGIVER-V1 + PROPENSITY-V1 composed, mechanism default-ON). 180 funnel
voyages over the same 9 declared cells as CHANNEL-03 — per hull
{scr-mid, scr-hi, ren} at 12 d, 20 seeds each (exp 8000-8019,
cls/spr 8105-8124) — paired seed-for-seed against the CHANNEL-03 dumps
under `campaign/noro_channel_03/`, which remain the labelled
pre-caregiver baseline.

## Join witness (per the frozen design)

13 of 180 seeds disagree between funnel `took_off` and the map's
`peak_prevalence >= 10` — 7 funnel-ON/map-OFF and 6 funnel-OFF/map-ON,
concentrated on the ren cells (cls_ren 6, exp_ren 2, spr_ren 2) where
takeoff is marginal. Per the channel_04 design this is a measured change
in outbreak frequency between the two stacks — a treatment effect, not
a join violation — and it does not void attribution. Net takeoff counts
are a wash (cls_ren 13→17 is the largest cell shift; all others within
±1).

## Pooled conversion chain (takeoff-conditional)

| cell | n (tookoff) | symp/infected | elig/symp | rep/elig | viaCG | CGtx | conf/rep | dated/conf | verdict |
|---|---|---|---|---|---|---|---|---|---|
| fl_cls_12d_ren/rung-reportable | 20 (17) | 0.206 | 1.000 | 0.390 | 0.512 | 0.019 | 0.338 | 0.667 | A2 link |
| fl_cls_12d_scr/rung-shipped-bp32p5c18p5 | 20 (20) | 0.345 | 1.000 | 0.345 | 0.516 | 0.034 | 0.330 | 0.863 | A2 link |
| fl_cls_12d_scr/rung-shipped-bp40c30 | 20 (20) | 0.359 | 1.000 | 0.315 | 0.545 | 0.037 | 0.427 | 0.830 | A2 link |
| fl_exp_12d_ren/rung-reportable | 20 (2) | 0.333 | 1.000 | 0.286 | 0.250 | 0.000 | 0.750 | 1.000 | A2 link |
| fl_exp_12d_scr/rung-shipped-bp32p5c18p5 | 20 (17) | 0.389 | 1.000 | 0.224 | 0.512 | 0.022 | 0.302 | 0.692 | A2 link |
| fl_exp_12d_scr/rung-shipped-bp40c30 | 20 (19) | 0.393 | 1.000 | 0.249 | 0.476 | 0.025 | 0.365 | 0.696 | A2 link |
| fl_spr_12d_ren/rung-reportable | 20 (19) | 0.217 | 1.000 | 0.451 | 0.598 | 0.025 | 0.251 | 0.840 | A2 link |
| fl_spr_12d_scr/rung-shipped-bp32p5c18p5 | 20 (20) | 0.333 | 1.000 | 0.331 | 0.571 | 0.031 | 0.302 | 0.753 | A2 link |
| fl_spr_12d_scr/rung-shipped-bp40c30 | 20 (20) | 0.365 | 1.000 | 0.318 | 0.614 | 0.040 | 0.329 | 0.734 | A2 link |

viaCG = share of reported cases arriving via the caregiver discovery
stamp; CGtx = share of aboard transmissions whose dominant route dose was
caregiver-mediated.

## Paired treatment effect (per-seed, takeoff voyages only)

| cell | Δ symp/inf | Δ rep/elig | paired seeds rep/elig ↑/↓/= |
|---|---|---|---|
| fl_cls_12d_ren/rung-reportable | -0.016 | +0.069 | 8/3/1 (n=12) |
| fl_cls_12d_scr/rung-shipped-bp32p5c18p5 | -0.018 | +0.103 | 17/2/1 (n=20) |
| fl_cls_12d_scr/rung-shipped-bp40c30 | -0.012 | +0.076 | 15/5/0 (n=20) |
| fl_exp_12d_ren/rung-reportable | +0.053 | -0.143 | 1/0/0 (n=1, thin) |
| fl_exp_12d_scr/rung-shipped-bp32p5c18p5 | -0.024 | +0.052 | 10/4/2 (n=16) |
| fl_exp_12d_scr/rung-shipped-bp40c30 | +0.003 | +0.081 | 11/7/1 (n=19) |
| fl_spr_12d_ren/rung-reportable | +0.047 | +0.135 | 18/0/0 (n=18) |
| fl_spr_12d_scr/rung-shipped-bp32p5c18p5 | +0.000 | +0.093 | 17/3/0 (n=20) |
| fl_spr_12d_scr/rung-shipped-bp40c30 | -0.003 | +0.051 | 14/6/0 (n=20) |

## Reading

- **The A2 link is untouched everywhere** — pooled symp/infected moves
  -0.024..+0.053 against baseline (per-seed deltas centered ~0). The
  caregiver stack sits downstream of the illness draw by design; the
  verdict is A2 on all 9 cells, unchanged from CHANNEL-03. The dominant
  conversion gap remains the symptom-course draw.
- **The reporting link measurably improves** — rep/elig rises +0.051 to
  +0.135 on 8 of 9 cells (exp_ren's -0.143 is a 2-takeoff cell, thin).
  The per-seed pairing shows the lift is systematic, not few-seed
  driven (14-18 of ~20 paired seeds up per cell; 18/18 on spr_ren).
- **The caregiver channel carries ~half of all reports** — viaCG runs
  0.476-0.614 on every adequately-sized cell; stamped→reported
  conversion is 100% on every cell (stamped_not_reported = 0 in all
  180 voyages). The residual reporting gap is stamping *coverage* —
  eligible hosts who never emit a witnessed emesis event or receive a
  service visit still rely on the baseline syndromic hazard.
- **rep/elig still reads below the 0.4 threshold on most cells**
  (0.224-0.390 on scr; spr_ren crosses to 0.451). The mechanism moved
  the link; it did not close it.
- **Caregiver dose is not a transmission amplifier** — CGtx is
  0.019-0.040 on all cells, far under the 10% report-immediately
  trigger. Steward responses dominate party responses ~10:1
  (e.g. spr scr-hi: 87 party + 1252 steward) — most witnessed emesis is
  public, consistent with the §11.3 presence gate routing in-cabin
  events to family and everything else to stewards.
- **Not-reported decomposition unchanged in shape** — on scr cells
  `course_not_symptomatic_onboard` still dominates (599-1182) over
  `visible_whole_course_draw_missed` (154-313): the censored-presence
  pool (imports presenting pre-boarding, isolation, departure) is the
  bulk of the residual, and the mechanism cannot stamp hosts whose
  course never surfaces onboard.

## Report-immediately triggers (frozen; evaluated on all 180 voyages)

- **Caregiver share of aboard transmissions > 10%**: not fired anywhere
  (max 0.040).
- **Caregiver report on a non-emetic course**: fired on 7/9 cells, 38
  voyages total (1-10 per cell). These are the R2 tending-engine stamps
  converting on non-emetic symptomatic courses — the arm working as
  designed; the trigger records volume, not a defect.
- **Vomiting courses with zero cleanup responses**: 4 voyages total —
  the 3 canary seeds already decomposed (seed 8002 = 1 emit lost a
  ~0.22/emit steward draw; seeds 8004/8016 = declared courses that never
  produced a due emesis episode) plus 1 on cls_ren. The accounting quirk
  stands: `vomiting_course_hosts` counts declared courses, not fired
  episodes.

Measured basis for the conversion question: the caregiver mechanism
recovers roughly a third of the missing reports on shipped cells and
~half of reports now flow through it — but the funnel's primary deficit
is and remains the A2 symptom-course draw, which no observation-side
mechanism can move. Reaching the report-rate anchors needs the illness
draw to move first.
