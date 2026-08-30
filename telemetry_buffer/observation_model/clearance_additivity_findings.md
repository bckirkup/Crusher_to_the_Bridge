# Exponential pre-establishment clearance does not break dose additivity

Date: 2026-08-30. Code: `clearance_additivity_check.py` (this directory).
Prompted by Edison's `formal_spec_v2.md` §3, which proposes
`inoculum_clearance_rate_per_day` as the mechanism for making diffuse and
concentrated exposure biologically distinct.

## The claim under test

Adding exponential clearance of the retained pre-establishment inoculum makes
fractionated exposure less infective than a bolus of the same total dose, and
so raises ill/infected (anchor A2) without touching the Teunis constants.

## Result: the claim is false for a single-hit hazard

With retained inoculum `R` decaying at rate `lambda` and hazard `r_rate * R(t)
dt`, the accumulated hazard from a set of deliveries `D_i` at times `t_i` over
a horizon `T` is

```text
H = (r_rate / lambda) * sum_i D_i * (1 - exp(-lambda * (T - t_i)))
```

Each delivery enters **linearly**, discounted only by how much of its decay
integral is truncated by the end of the horizon. Once the horizon extends past
the exposure, every weight goes to 1 and

```text
H = (r_rate / lambda) * sum_i D_i
```

which depends on total delivered dose and on nothing else. Clearance is
integrated out. This is the same algebra that killed the fixed-window
proposal: a hazard linear in the retained pool, and a pool that decays
linearly, cannot distinguish diffuse from concentrated delivery.

## Calibration: lambda is otherwise a global infectivity knob

A bolus `D` accrues total hazard `r_rate * D / lambda`. To keep the
single-bolus response equal to the beta-frailty single-hit form `1 - exp(-r D)`
that the model is calibrated to, the rate coefficient must be
`r_rate = r * lambda`. Without that rescaling, choosing `lambda` multiplies all
infectivity by `1/lambda`. Edison's PEC-03 fixes `r = 0.02` independently of
`mu = 1`, so as written the parameter silently rescales the dose-response.

## Measured (N = 40,000 hosts, total dose 1000, exposure over 5 d, horizon 7 d)

Closed-form additive target: infection AR **0.3181**.

| lambda /day | increments | infection AR | ill/infected |
|---:|---:|---:|---:|
| 0 (uncalibrated) | 1 | 0.4499 | 0.4468 |
| 0 (uncalibrated) | 24 | 0.4227 | 0.3765 |
| 0 (uncalibrated) | 168 | 0.4234 | 0.3751 |
| 0.5 | 1 | 0.3184 | 0.4281 |
| 0.5 | 24 | 0.3059 | 0.3538 |
| 0.5 | 168 | 0.3084 | 0.3530 |
| 2 | 1 | 0.3202 | 0.4277 |
| 2 | 24 | 0.3156 | 0.2966 |
| 2 | 168 | 0.3178 | 0.2933 |
| 12 | 1 | 0.3199 | 0.4332 |
| 12 | 24 | 0.3171 | 0.2258 |
| 12 | 168 | 0.3180 | 0.2043 |

Three readings.

1. **Infection attack rate is invariant to `lambda` and to fractionation** once
   calibrated: every calibrated cell is within Monte-Carlo distance of 0.3181.
   The one systematic departure is `lambda = 0.5, n >= 24` at 0.306, which is
   the end-of-horizon truncation term above: dose delivered on day 5 has only
   `1 - exp(-0.5 * 2) = 0.63` of its hazard realised by day 7, and the
   exposure-averaged weight of 0.865 predicts 0.306 exactly. It is a boundary
   effect of the voyage length, not a biological mechanism.

2. **ill/infected moves the wrong way.** Because the illness draw conditions on
   the retained pool at establishment, and clearance shrinks that pool for
   diffuse exposure, A2 falls monotonically with `lambda`: 0.354 at
   `lambda = 0.5`, 0.297 at 2, 0.226 at 12, against 0.43 for a bolus. Our
   measured post-#346 value is already ~1.8x too low at 0.34-0.36. Enabling
   clearance makes the discriminating anchor worse.

3. **`lambda = 0` is not the current model.** The literal PEC-04 limit
   (`hazard = r * R_0 * T`) lets an undecayed pool accrue hazard indefinitely
   and returns AR 0.42-0.45 against the correct 0.318. So the specification's
   backwards-compatibility claim — that a zero default preserves d557f39 —
   holds only for the other, non-functional formulation in the same document.

## What this leaves

Within a single-hit model, infection risk is a function of total delivered
dose. No linear clearance, retention window, or reset changes that. Breaking
the A1/A2 deadlock requires a mechanism that is nonlinear in delivered dose:

- **host-level exposure heterogeneity** — a minority receiving concentrated
  inocula, which is the vomitus/point-source picture, and needs to arrive as
  near-field physics rather than a fitted sigma;
- **cooperative or multi-hit establishment** — aggregates and multi-virion
  packaging, where establishment requires several co-arriving particles, which
  is genuinely superlinear in local concentration;
- **induced (dose-dependent) innate clearance** — where early exposure raises
  the clearance rate, so diffuse exposure is disproportionately wasted.

The first two are physical and independently measurable. The third is the one
that would still make a clearance parameter matter, and it is not what the
specification describes.

Note what this does **not** withdraw: clearance remains the right description
of the inoculum's fate, and the stale-dose leak it was also meant to fix
(SPEC-CLEAR-01, no reset of `cumulative_exposure` on recovery) is a genuine
defect that should be repaired on its own terms.
