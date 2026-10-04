# NORO-ONSET-CURVE-01
**Date:** 2026-10-04
**Commit:** f1ce5c5c
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** f1ce5c5c

Onset/acquisition clustering readout on the hot campaign zips —
`campaign/noro_outbreak_02/` (expedition, 8 cells), `noro_outbreak_03/`
(classic, 4), `noro_outbreak_04/` (spirit, 4), `noro_mega_01/` (mega
partial, 2) — image `campaign-1e158d47` (CAREGIVER-V1 + PROPENSITY-V1).
Instrument `tools/noro_diag/onset_curve_readout.py`: per-voyage
`epoch_acquired` distributions from `growth_census.json.gz` via ranged
prefix reads (hosts[] only). ~200 voyages per cell plus every posted
voyage found by summary sweep of the screening cells: 3,225 + 308 voyages
read, 0 errors. Design `docs/norovirus/noro_onset_curve_01_design.md`;
full tables `docs/norovirus/noro_onset_curve_01_readout.md`.

## Measured

- Every voyage on every hull is a **propagated ramp** — no voyage anywhere
  carries the point-source signature. On the cells where discrimination is
  possible (cls/spr/mega scr, ~130–500 acquisitions/voyage), the densest
  48-epoch window holds med **0.25–0.31** of a voyage's acquisitions, the
  densest 12-epoch window **0.09–0.13**, the densest 6-epoch window
  **0.06–0.10**. Share of voyages with burst12 > 0.5: **0.00** on all six
  big-hull scr cells and both mega cells (308 voyages).
- **All 33 posted voyages are ordinary voyages**: burst48 0.24–0.43,
  burst12 0.10–0.25, burst-centre 0.24–0.92 — inside their cells' IQRs.
  VSP trips ride the accumulated report-volume tail of a ramp, not an
  event; no synchronized "excursion" subpopulation exists to trigger on.
- Acquisition times smear across the whole voyage: med acq frac
  **0.57–0.79**, densest window centred at **0.55–0.70** of the voyage —
  consistent with OUTBREAK-02/03/04's "peak at ~ep 270–286 of 288" and the
  "too slow" verdict: the epidemic never crests in-window.
- Symptomatic cohort shows the same shape (symp burst48 med 0.34–0.55 on
  big hulls).
- Small-hull cells (exp, ~12–43 acq/voyage) cannot discriminate — a fast
  propagated wave on 450 agents fills a 48-epoch window anyway
  (burst48 ~0.38–0.62; ~0.92 share > 0.5 on the 7-day cells).

## Reading

The current mechanism stack is structurally incapable of the real-world
signature: a posted noro outbreak clusters onsets inside ~one incubation
window (point-source epidemic curve), while the model's densest 48 h
window holds a quarter of acquisitions even in its tail events. VSP trips
can only ride the thin report-accumulation tail — matching the measured
0–0.8 % posting on saturated scr cells. Supports the excursion
hypothesis: the missing generator is a *synchronized common-source dose*
(single-meal event dosing a large cohort at once → clustered
acquisitions → clustered onsets one incubation later), not another
reporting- or dose-side channel. A food-handler/contaminated-item
seeding event is the leading candidate substrate (`crew_duty_exclusion`,
`ship_functions`, `fomite_food_rederivation` machinery exists; whether any
existing pathway emits synchronized mass dose is an open design question —
NORO-ONSET-CURVE-01 only measures the absence).

## Caveats

- `epoch_acquired` is acquisition time, not symptom onset; incubation
  shifts the curve right but preserves clustering, so the discrimination
  is unaffected. Symptom-onset epochs are not serialized in the census
  (flagged for the next image's emit list in the design doc).
- Instrument reads only the `hosts[]` prefix of the census member; the
  trailing `emits[]` event log is skipped by design.
- Posted-voyage census reads used the same ranged-prefix path; posted
  keys were located by summary-member sweep of the screening cells.
