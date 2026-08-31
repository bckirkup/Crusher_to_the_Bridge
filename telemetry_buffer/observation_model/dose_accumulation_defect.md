# Defect: the dose-response is applied per epoch, so infection depends on the clock

Date: 2026-08-29. Analysis commit: `75716b0`. Author: model-development record,
continues `docs/norovirus/norovirus_model_history.md`.

## What the code does

`TransmissionCore._dose_response` (engines/transmission_core.py:1111) evaluates
the beta-Poisson dose-response on **one epoch's dose**, and
`_apply_doses` (engines/transmission_core.py:1485-1490) draws an independent
Bernoulli against it every epoch:

```python
inf_prob = self._dose_response(pathogen_id, p_dose)   # p_dose = this epoch only
if self.rng.random() < inf_prob:
    ...
```

On infection, `infect_with_pathogen` stores `acquired_particles = dose` — again
the single epoch's dose (engines/infection_dynamics_bridge.py:639) — and the
illness draw reads exactly that value (orchestrator_epoch.py:419-423):

```python
ill_prob = 1.0 - (1.0 + eta * inf["acquired_particles"]) ** -gamma
```

So both the infection event and the illness event are functions of a *time
slice*, not of an exposure.

## Why that is wrong

The beta-Poisson model is a Poisson single-hit model mixed over a host
susceptibility `r ~ Beta(α, β)`:

```
P(inf | D) = E_r[1 - exp(-rD)] = 1 - (1 + D/β)^(-α)
```

`r` is a property of the **host** (for norovirus GII.4 it is largely secretor
status and pre-existing immunity), not of the hour. Re-drawing the Beta mixture
every epoch treats each hour as a fresh person and destroys the correlation
that makes the model a dose-response at all. The consequence is that the same
total exposure gives a different attack rate depending only on how finely time
is sliced.

Measured on the model's own arithmetic (400k hosts, α=0.111, β=32.81,
η=0.508, γ=0.095), fixed total dose `T` split into `n` equal exposures:

| total dose | n | current: infection AR | current: ill/infected | invariant form: infection AR | invariant form: ill/infected |
|---|---:|---:|---:|---:|---:|
| 10^2 | 1 | 0.144 | 0.313 | 0.144 | 0.313 |
| 10^2 | 24 | 0.273 | 0.102 | 0.145 | 0.228 |
| 10^2 | 168 | 0.285 | 0.025 | 0.143 | 0.221 |
| 10^3 | 1 | 0.318 | 0.447 | 0.319 | 0.421 |
| 10^3 | 24 | 0.887 | 0.255 | 0.320 | 0.336 |
| 10^3 | 168 | 0.955 | 0.124 | 0.319 | 0.314 |
| 10^4 | 1 | 0.470 | 0.555 | 0.472 | 0.350 |
| 10^4 | 24 | 0.999 | 0.399 | 0.474 | 0.438 |
| 10^4 | 168 | 1.000 | 0.279 | 0.471 | 0.395 |

At 10^3 total particles, slicing the day into hours takes the infection attack
rate from 0.32 to 0.89 and takes ill/infected from 0.45 to 0.25. Nothing
physical changed; only the epoch length did.

This is the same class of error as the seven already recorded in
`docs/norovirus/norovirus_model_history.md` — a quantity evaluated on the wrong axis —
and the hourly-epoch migration did not cause it but did amplify it by roughly
24x in trial count.

## Direction of the bias, and why it matches the symptoms

Both observed anchor failures are the signature of this defect:

- infection attack rate too high (measured 0.60–0.80 against a Wikswo-implied
  ≈0.22): many independent small trials beat one large trial;
- ill/infected too low (measured 0.22–0.26 against 0.59–0.81): the illness draw
  sees only the sliver of dose delivered in the successful hour, so the
  inoculum it conditions on is ~n times too small.

## The invariant formulation

Draw each host's susceptibility once at initialisation, `r_i ~ Beta(α, β)`, and
accumulate:

```
hazard per epoch  = 1 - exp(-r_i * d_epoch)
cumulative        = 1 - exp(-r_i * Σ d)          # exactly beta-Poisson in Σ d
illness draw uses   Σ d up to and including the infecting epoch
```

This reproduces the published beta-Poisson exactly for a single exposure
(n=1 rows above agree to sampling error) and is invariant to epoch length
(0.318 / 0.320 / 0.319 across n=1/24/168). It adds no fitted parameter: α and β
are unchanged, and `r` is the mixing variable the model already assumes.

## What the fix does *not* do

It is not sufficient to reach the anchors, and it should not be sold as such.
Under the invariant form, ill/infected and infection AR are tied together by
the same dose:

| log10 total dose | infection AR | max ill/infected |
|---:|---:|---:|
| 3 | 0.320 | 0.447 |
| 4 | 0.472 | 0.555 |
| 5 | 0.591 | 0.643 |
| 6 | 0.684 | 0.713 |
| 7 | 0.756 | 0.769 |

So with a **homogeneous** exposure there is no dose at which infection AR ≈0.22
coexists with ill/infected ≈0.7: A1 and A2 are jointly unsatisfiable. Adding
host-level exposure heterogeneity (lognormal total dose across hosts, 20%
innately non-susceptible, infection AR pinned at 0.22) does reconcile them:

| σ (log10 of host total dose) | log10 median | infection AR | ill/infected | ever-ill |
|---:|---:|---:|---:|---:|
| 0.0 | 2.70 | 0.214 | 0.409 | 0.088 |
| 1.0 | 2.70 | 0.215 | 0.467 | 0.100 |
| 2.0 | 2.50 | 0.212 | 0.547 | 0.116 |
| 3.0 | 2.15 | 0.210 | 0.610 | 0.128 |

The literature picture — a minority receiving a vomitus/point-source inoculum
while most of the ship receives almost nothing — is a σ of that order, and it
is the only structure found so far that satisfies A1 and A2 at once. The
engine cannot currently produce it: the droplet pathway, which carries 94–95%
of establishments, gives every susceptible in a zone the **identical**
well-mixed concentration × inhaled volume every epoch
(engines/transmission_core.py:1977-1985), with no proximity or point-source
structure. The one heterogeneity knob that exists,
`contact_mode: heterogeneous_zone_dose` (a mean-1 lognormal, σ≈0.25–1.0 by zone
type), applies only to the direct-contact pathway.

## Consequences for prior results

Every infection attack rate this project has reported under hourly epochs is
inflated by this defect, and every ill/infected is deflated by it. That
includes the v4 campaign and the post-merge anchor pilot at `7a9b439`. The
fitted dose from any of them is not transferable to the corrected model.

## Order of work implied

1. Fix the dose-response to be exposure-accumulating and epoch-invariant
   (persistent per-host `r`, cumulative dose for the illness draw).
2. Re-measure A1/A2/A4 with no other change; expect infection AR to fall
   sharply and ill/infected to rise, and expect both to still miss.
3. Only then decide whether exposure heterogeneity is added as physics
   (near-field/point-source droplet structure) rather than as a fitted σ.
