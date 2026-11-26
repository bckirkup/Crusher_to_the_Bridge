# COVID-PRESHED-GATE-01
**Date:** 2026-11-26
**Commit:** f567c293
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** f567c293

Owner-approved precursor to DP-UNION-02. The presymptomatic emission gate on
the active COVID arm now covers the Zhou shape's negative support, and explicit
seed onset stamping is consistent with the engine's epoch-quantized infection
age. No outcome anchor was consulted or fitted.

## Measured defect

Before the fix, the DP union NIID seed (`infection_age_days` 2.8, `onset_day`
3.0) boarded at onset-relative day -3, but the active profile's legacy
`presymptomatic_shedding_days` 2.0 closed emission there. A zero-epoch
ascertainment probe over the predeclared 360-seed DP-UNION-02 candidate
sequence therefore produced **360 of 360** `index_shedding_at_day0=False`.
This was structural, not sampling noise.

A second clock inconsistency was exposed at the same boundary: the engine
represents the stated 2.8-day infection age as 67 whole hourly epochs
(2.7916667 days), while the stamped incubation was computed from the unrounded
2.8 days. That put the represented onset-relative age at day -4 rather than
the intended day -3.

## Correction

1. `presymptomatic_shedding_days` on active `sars_cov2_resp` is 5.0, the
   negative support of the active Zhou onset-aligned shape. This is not a new
   emission magnitude: the day-resolved occurrence probabilities and
   conditional masses remain the shape rows. He et al. remains independent
   evidence that infectiousness begins before onset, but the precise gate is
   now the adopted shape's support rather than the legacy 2.0-day truncation.
2. `_seed_epoch_fields` computes onset incubation from the engine-represented
   infection age after epoch rounding. The stated onset voyage day is the
   fixed record; the fractional infection age is the quantity the hourly clock
   cannot represent exactly.
3. The DP boarding-screen geometry audit reads that same represented age, so
   the payload's onset/day-0-emission audit evaluates the geometry the engine
   actually simulates.

## Ascertainment probe after correction

The predeclared candidate sequence is the 360 calendar-date integer seeds
beginning 20200205 and ending 20210129. Zero-epoch `union_niid` cells at
theta 1e8 read only `index_shedding_at_day0`; no attack, onset, founder,
testing, capture, or other outcome observable was read. Result: **42 of 360**
positive-emission candidates. The first 24 in candidate order are frozen for
DP-UNION-02:

```text
20200208, 20200213, 20200302, 20200320, 20200321, 20200323,
20200324, 20200412, 20200507, 20200509, 20200520, 20200525,
20200530, 20200610, 20200612, 20200621, 20200703, 20200713,
20200715, 20200721, 20200722, 20200724, 20200725, 20200727
```

Machine record: `campaigns/covid/dp_union_02/ascertainment_probe.json`.
The probe rate is consistent with the day -3 occurrence probability 0.1
(inference, not an independent validation). Theta independence is inferred
from initialization order: the occurrence sequence is written at infection
initialization before transmission dynamics, while every scored cell still
audits the emission bit directly.

## Consequences

- `COVID-INDEX-CLOCK-01` remains an accurate trace of its own pre-shape,
  pre-correction revision, but its 2.0-day gate and exact seed-boundary
  arithmetic are historical.
- All pre-shape COVID measurements were already withdrawn by
  `COVID-SHED-SHAPE-01`; no post-shape scored campaign existed before this
  correction, so no additional campaign result is withdrawn here.
- DP-UNION-02 is the first design that may produce an ascertainment-valid
  post-shape DP refit. GM remains validation-only; H5 remains held out
  forever.
