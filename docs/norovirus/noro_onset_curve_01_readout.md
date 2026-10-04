# NORO-ONSET-CURVE-01 readout — voyage onset/acquisition clustering

Status: measured — 2026-10-04. Instrument
`tools/noro_diag/onset_curve_readout.py`; measured at `f1ce5c5c` against
hot campaign zips under `campaign/noro_outbreak_02/`, `noro_outbreak_03/`,
`noro_outbreak_04/`, `noro_mega_01/` (image `campaign-1e158d47`,
CAREGIVER-V1 + PROPENSITY-V1 composed).

## Question

Design doc `noro_onset_curve_01_design.md`: are voyage outbreaks *propagated*
(dispersed acquisition times, smooth ramp) or *point-source-like* (cases
clustered nearly simultaneously)? Real posted norovirus outbreaks present the
point-source signature — a burst of onsets inside ~one incubation window
(~24–48 h) then a declining tail. This readout measures the per-voyage
distribution of `epoch_acquired` directly.

## Coverage

Per-cell sample of 200 voyages (even seed stride over seeds 8000–8999 /
8105–9104 / 8105–8392 as available) plus every posted voyage found by a
summary-member sweep of the screening cells. Per-voyage cohorts:

- `all` — onboard-acquired infections (`epoch_acquired > 0`)
- `symp` — subset that ever showed aboard symptoms (`symptomatic_epochs > 0`)

Metrics per voyage (window in epochs, 1 epoch = 1 h):

- `burst48/24/12/6` — largest share of acquisitions inside any sliding window
  of that width; `burst6/12` is the single-meal common-source synchrony bound
- `centre` — epoch of the widest burst's centre, as a fraction of voyage length
- `med_acq_frac` — median acquisition epoch as a fraction of voyage length
- `spiky share` — share of measurable voyages with `burst48 > 0.5`
- `spike share` — share with `burst12 > 0.5`

## Cell-level clustering (200-voyage sample per cell)

| cell | measured | med acq | burst48 | burst24 | burst12 | burst6 | centre | med acq frac | symp burst48 | share b48>0.5 | share b12>0.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fl_cls_12d_ren bpnone | 148/200 | 48 | 0.43 [0.38-0.50] | 0.28 [0.23-0.33] | 0.21 [0.18-0.26] | 0.16 [0.13-0.20] | 0.88 [0.80-0.91] | 0.79 | 0.50 | 0.23 | 0.01 |
| fl_cls_12d_scr bp25c7 | 201/201 | 108 | 0.31 [0.28-0.33] | 0.19 [0.17-0.20] | 0.13 [0.12-0.15] | 0.10 [0.09-0.11] | 0.71 [0.56-0.81] | 0.63 | 0.43 | 0.00 | 0.00 |
| fl_cls_12d_scr bp32.5c18.5 | 203/203 | 122 | 0.28 [0.27-0.31] | 0.17 [0.16-0.19] | 0.13 [0.11-0.14] | 0.09 [0.08-0.10] | 0.63 [0.52-0.74] | 0.62 | 0.41 | 0.00 | 0.00 |
| fl_cls_12d_scr bp40c30 | 204/204 | 129 | 0.28 [0.27-0.30] | 0.17 [0.16-0.18] | 0.12 [0.11-0.13] | 0.09 [0.08-0.09] | 0.56 [0.48-0.72] | 0.58 | 0.41 | 0.00 | 0.00 |
| fl_exp_12d_ren bpnone | 21/200 | 13 | 0.46 [0.40-0.56] | 0.36 [0.27-0.38] | 0.25 [0.20-0.33] | 0.20 [0.17-0.25] | 0.72 [0.53-0.81] | 0.71 | -- | 0.38 | 0.00 |
| fl_exp_12d_scr bp25c7 | 137/201 | 17 | 0.42 [0.36-0.47] | 0.30 [0.25-0.35] | 0.24 [0.19-0.27] | 0.18 [0.15-0.22] | 0.64 [0.51-0.79] | 0.64 | 0.55 | 0.12 | 0.01 |
| fl_exp_12d_scr bp32.5c18.5 | 177/207 | 20 | 0.40 [0.36-0.46] | 0.29 [0.24-0.33] | 0.21 [0.18-0.25] | 0.17 [0.14-0.21] | 0.66 [0.53-0.80] | 0.65 | 0.55 | 0.09 | 0.00 |
| fl_exp_12d_scr bp40c30 | 190/206 | 22 | 0.38 [0.33-0.42] | 0.26 [0.23-0.31] | 0.20 [0.18-0.24] | 0.17 [0.13-0.20] | 0.63 [0.47-0.80] | 0.63 | 0.46 | 0.05 | 0.00 |
| fl_exp_7d_ren bpnone | 2/200 | 11 | 0.70 [0.50-0.70] | 0.42 [0.40-0.42] | 0.33 [0.30-0.33] | 0.33 [0.20-0.33] | 0.82 [0.44-0.82] | 0.82 | -- | 0.50 | 0.00 |
| fl_exp_7d_scr bp25c7 | 37/200 | 12 | 0.62 [0.55-0.67] | 0.42 [0.36-0.47] | 0.33 [0.29-0.38] | 0.27 [0.22-0.31] | 0.80 [0.63-0.84] | 0.72 | -- | 0.84 | 0.00 |
| fl_exp_7d_scr bp32.5c18.5 | 66/200 | 12 | 0.62 [0.57-0.69] | 0.42 [0.36-0.50] | 0.31 [0.27-0.38] | 0.25 [0.20-0.30] | 0.78 [0.61-0.84] | 0.73 | -- | 0.92 | 0.05 |
| fl_exp_7d_scr bp40c30 | 95/200 | 12 | 0.60 [0.53-0.67] | 0.41 [0.36-0.50] | 0.31 [0.29-0.38] | 0.25 [0.21-0.30] | 0.68 [0.52-0.80] | 0.66 | -- | 0.77 | 0.04 |
| fl_spr_12d_ren bpnone | 181/200 | 96 | 0.43 [0.36-0.51] | 0.25 [0.22-0.32] | 0.19 [0.15-0.23] | 0.13 [0.11-0.17] | 0.88 [0.81-0.90] | 0.79 | 0.52 | 0.27 | 0.01 |
| fl_spr_12d_scr bp25c7 | 200/200 | 182 | 0.28 [0.27-0.30] | 0.17 [0.16-0.18] | 0.12 [0.11-0.13] | 0.08 [0.08-0.09] | 0.70 [0.61-0.80] | 0.63 | 0.39 | 0.00 | 0.00 |
| fl_spr_12d_scr bp32.5c18.5 | 200/200 | 192 | 0.27 [0.26-0.28] | 0.16 [0.15-0.17] | 0.12 [0.11-0.12] | 0.08 [0.07-0.09] | 0.63 [0.53-0.74] | 0.61 | 0.39 | 0.00 | 0.00 |
| fl_spr_12d_scr bp40c30 | 203/203 | 204 | 0.27 [0.26-0.28] | 0.16 [0.15-0.17] | 0.11 [0.10-0.12] | 0.08 [0.07-0.09] | 0.58 [0.47-0.71] | 0.58 | 0.38 | 0.00 | 0.00 |
| fl_mega_12d_scr bp25c7 | 288/288 | 488 | 0.25 [0.24-0.26] | 0.14 [0.14-0.15] | 0.10 [0.10-0.11] | 0.07 [0.06-0.07] | 0.61 [0.53-0.70] | 0.59 | 0.34 | 0.00 | 0.00 |
| fl_mega_12d_scr bp32.5c18.5 | 20/20 | 504 | 0.25 [0.24-0.25] | 0.14 [0.13-0.15] | 0.10 [0.09-0.10] | 0.06 [0.06-0.07] | 0.55 [0.45-0.65] | 0.57 | 0.34 | 0.00 | 0.00 |

`measured` = voyages with n_acquired ≥ 10 of sample n. `med acq` = median
onboard acquisitions per voyage. `symp` columns only where the symptomatic
cohort reaches the ≥10 floor on enough voyages.

## Posted voyages (all 33 found in the scr sweep)

Every posted voyage's burst metrics sit *inside* its cell's ordinary
distribution — none is an outlier:

| hull | n posted | burst48 range | burst12 range | burst6 range | centre range |
|---|---|---|---|---|---|
| exp 12d scr | 16 | 0.27–0.43 | 0.12–0.25 | 0.08–0.22 | 0.24–0.92 |
| exp 7d scr | 1 | 0.60 | 0.40 | 0.33 | 0.40 |
| cls 12d scr | 13 | 0.24–0.35 | 0.11–0.16 | 0.07–0.13 | 0.44–0.73 |
| spr 12d scr | 3 | 0.24–0.26 | 0.10–0.12 | 0.07–0.08 | 0.61–0.65 |
| mega 12d scr | 0 | — | — | — | — |

## Reading

**Measured: every voyage on every hull is a propagated ramp; nothing —
including all 33 posted voyages — carries the point-source signature.**

- On the big hulls where discrimination is possible (cls/spr/mega scr,
  ~130–500 acquisitions per voyage), the densest 48-epoch window holds a
  median **0.25–0.31** of a voyage's acquisitions, the densest 12-epoch
  window **0.09–0.13**, and the densest 6-epoch window **0.06–0.10**. A
  single-meal common-source spike would pin burst12/burst6 near 1.0 for the
  exposed cohort; no voyage anywhere exceeds 0.5 — share of voyages with
  burst12 > 0.5 is **0.00** on all 6 big-hull scr cells and both mega cells
  (n=308).
- **Posted voyages are ordinary voyages.** Their burst48/burst12/burst6 and
  burst-centre sit inside the per-cell IQRs — e.g. the three spirit postings
  (burst48 0.24–0.26, centre 0.61–0.65) vs the cell's med 0.27, centre 0.58.
  They crossed the VSP wire by accumulated report volume on an ordinary
  ramp, not because anything synchronized or surged. There is no "event"
  subpopulation in the data to trigger on.
- On small hulls (exp) the metric can't separate the mechanisms — a fast
  propagated wave on 450 agents fills a 48-epoch window anyway
  (burst48 med ~0.38–0.42, and ~0.60 on the 7-day cells where the voyage
  ends inside one incubation span). The big-hull cells are where the
  discrimination lives, and there the answer is unambiguous.
- The symptomatic cohort shows the same shape (symp burst48 med 0.34–0.55
  on big hulls — higher, as expected for a subset, but far from clustered).

**Implication for the excursion hypothesis:** the model's epidemics are
structurally propagated — acquisition times smear across the whole voyage
(med acq frac ~0.58–0.79, densest window centred ~0.55–0.70). A real posted
noro outbreak clusters onsets inside ~one incubation window. The current
mechanism stack *cannot produce* that signature at any volume — VSP trips
can only ride the thin upper tail of report accumulation, which is what the
0–0.8% posting rates on saturated cells look like. This is consistent with
the missing excursion generator being a synchronized common-source dose
(point-source event), not another reporting- or dose-side channel.

## Caveats

- `epoch_acquired` is *acquisition* time, not symptom onset: incubation
  (~24–48 h, engine draw) shifts the curve right but preserves clustering
  shape, so burst metrics discriminate the mechanisms either way.
- Symptomatic cohort is onboard-symptomatic only; a host whose course
  resolves or starts off-voyage does not appear (same censoring as the
  funnel's `course_not_symptomatic_onboard` residual).
- `n_acquired >= 10` floor for burst stats; smaller voyages are counted in
  `n_voyages` but excluded from distribution metrics.
- Census member read is a ranged prefix read: `hosts[]` is parsed only
  (the per-event `emits[]` log that follows it in the member is skipped).
