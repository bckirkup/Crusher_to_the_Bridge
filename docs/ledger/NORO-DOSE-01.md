# NORO-DOSE-01
**Date:** 2026-09-19
**Commit:** f55e93f
**Pathogens:** norwalk_gi
**Status:** open

Dose reaching hosts on `classic_cruise_1900`: ordered transmission-blocker
cascade after `NORO-SUSCEPT-02` closed the credited-dose to evaluated-hazard
chain and `NORO-SUSCEPT-03` excluded the sourced α interval. Those findings are
settled inputs and are not re-derived. In particular, no arm in this entry may
move `dose_response.alpha` or `dose_response.beta`; `RNG-FRAILTY-STREAM-01`
makes such arms unpairable at fixed seed.

This entry freezes the design and decision criteria **before any cell runs**.
The instrument is `tools/noro_diag/per_host_dose_challenge.py`. No model
constant, pathogen profile or shipped configuration value will change.

## Settled inputs

- `NORO-SUSCEPT-02`, measured at `9f4cd79`: the post-route credited dose, dose
  read at challenge and effective dose evaluated reconcile exactly. At seed
  8105 a 288-epoch voyage credited 0.100952 GEC after host susceptibility
  scaling and produced Σ evaluated hazard 3.8091e-4; seed 8106 credited
  0.002713 GEC and produced 1.1871e-5.
- `NORO-SUSCEPT-03`, measured at `f5f9ff3`: 0 secondaries in 14 voyages, maximum
  Σ hazard 1.186e-2, and the sourced α interval moves mean susceptibility only
  about 2.2-fold. α is closed and will not be reopened here.
- The open question is upstream dose delivery: route attribution, route pickup
  terms, host blockers, then a forced challenge trace, in that order.

## Frozen design

| Item | Declaration |
| --- | --- |
| Platform | `classic_cruise_1900`, declared complement (1,910 agents) |
| Voyage | 288 epochs |
| Observational seeds | 8105 and 8106, fixed shipped profile, no overrides |
| Primary trace | seed 8105, because the settled reference voyage has non-zero emesis and fomite witnesses and the larger credited dose |
| Confirming trace | seed 8106; an all-zero route witness makes a route conclusion void for that seed, not negative evidence |
| Forced challenge | seed 8105, one labelled direct state injection after Steps 1–3; no profile or configuration override |
| Forbidden arms | any arm changing `dose_response.alpha` or `.beta`; any constant or shipped configuration change |

The two observational seeds are a mechanism smoke, not an effect-size sample.
No rate, population mean or calibrated parameter will be estimated from them.

## Criterion, frozen before execution

### Step 0 — anything to explain

Report observed secondaries and the engine's summed evaluated hazard. Zero
secondaries is called a downstream blocker only if the Poisson approximation
`P(N = 0) = exp(-Σ hazard)` is below 0.05. Otherwise zero is an ordinary draw;
the remaining cascade is explicitly a dose-delivery diagnosis, not a search for
a Bernoulli failure.

### Step 1 — route attribution

For every credited host, record credited dose by route, and for the voyage
report each route's total and share. For the most-dosed host, report route,
epoch and dose concentration. A route is called **exercised** only when its own
execution witness is non-zero. A route with zero witness is **untested**, never
blocked. The suspect route is the exercised route contributing the largest
share of post-route credited dose; if no route exceeds 50%, carry every route
within 10 percentage points of the largest into Step 2.

### Step 2 — pickup terms

For each suspect route, record the ordered mass terms available from the
instrument. For fomite these are surface mass offered → pickup mass requested →
mass delivered to hands → hand load presented to hand-to-mouth → ingested dose
→ `_accumulate` dose → post-route credited dose. Report adjacent pass-through
ratios and `-log10(ratio)` losses. The **principal attenuation term** is the
largest adjacent log loss, provided its input and output witnesses are both
non-zero; ties within 0.25 log10 are reported as joint, not selected.

Independently probe the recurring carrier-dead-end archetype: give a
non-shedding carrier a non-zero hand reservoir and exercise each applicable
hand-mediated source route. If the route witness fires but moves zero mass, the
source-status gate is a defect. If the route does not fire, the probe is void.
No fix is made in this entry.

### Step 3 — host blockers

For the most-dosed challenged host at its largest-dose epoch, record in engine
order: challenge entry state and exit reason, protection, secretor multiplier,
persistent susceptibility, effective dose, recomputed hazard and engine
hazard. A host blocker is declared only for one of these pre-specified cases:

- protection is at least 1.0;
- the challenge exits before hazard evaluation despite positive dose;
- susceptibility is absent or non-positive;
- effective dose differs from dose read by more than `1e-12` relative after
  accounting for protection;
- recomputed and engine hazard differ by more than `1e-12` relative.

A very small positive susceptibility or hazard is reported as scale, not called
a blocker.

### Step 4 — forced challenge trace

Only after Steps 1–3, inject a labelled challenge into one susceptible host in
the seed-8105 voyage without changing α, β or any constant. Use that host's
cached susceptibility and choose dose so `-expm1(-s*d)` rounds to 1.0. The trace
passes only if the challenge witness records positive dose, positive
susceptibility, hazard 1.0, and a susceptible→infected transition with a
transmission event. Failure localises the defect to `_establish` or later; pass
shows that downstream establishment is intact and the shipped voyage simply
does not deliver enough dose.

## Reported but never selected on

Secondaries, imports, attack rate, route shares, concentration quantiles,
emesis counts, individual stochastic pickup draws and frailty quantiles are
reported for diagnosis. None licenses a constant change or a recommendation to
fit a model parameter. The final recommendation must be one of: repair a
measured defect; instrument a route whose witness is missing; or leave the
engine unchanged and identify the measured dose-delivery term that should be
studied next with a declared replicated design.
