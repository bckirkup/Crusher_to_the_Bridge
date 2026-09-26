# NORO-CHANNEL-02
**Date:** 2026-09-26
**Commit:** 0e4aab73
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** b9cae80f

## 0. The question

`NORO-CHANNEL-01` §5 asked whether the ≈0.60 elicitation behind
`reporting_probability_by_severity_*` names the probability a
symptomatic-eligible person reports **net of** reluctance (post-trust —
then the channel's `× (0.5 + 0.5·trust_medical)` double-counts
reluctance) or **given** willingness (pre-trust — then the stacking is
the declared composition). Answered on documentary grounds, not on the
band miss.

## 1. The trace

**Elicitation side** (`../norovirus/cruise_pathogen_severity_observation_priors_v2.md`):

- §4.1: "One cruise investigation estimated that infirmary surveillance
  captured approximately **0.60 [E]** of AGE cases." Captured *of* cases —
  reports per case meeting the AGE case definition. The denominator is
  all AGE-ill people, including every person who was ill and chose not
  to present. Reluctance is already inside the measured quantity.
- §4.1/§2: the shipped vector `[0,.45,.70,.94,1]` yields weighted
  eligible-case reporting ≈0.61 [M/A], explicitly *constrained by* that
  0.60. A vector entry therefore denotes the fraction of
  syndrome-eligible hosts of that severity who end up reported —
  realized capture.
- No clause in v2 conditions any entry on willingness, intent, or trust;
  the document's own decomposition (§4.1, §8) is
  `eligibility × reporting` with no third factor.

**Code side** (`crusher_labs/modalities/syndromic.py`, git log):

- `fce68793` introduced the Layer-1 belief scaling
  `p × (0.5 + 0.5·trust_medical)` as the composition of the *scalar*
  sick-call channel — trust meaning propensity to report at all.
- `88bacda6` (severity hazards) and `c76b1978` (five-state observation
  model) carried that multiplier unchanged over the newly declared
  vectors; `8c755d24` made the vectors a `prior.scenarios` declaration.
  At no point was the vector re-declared willingness-conditional — the
  multiplier just survived the refactor.
- `trust_medical` itself is the Layer-1 diffusion belief
  (`initial_trust_medical` 0.78 in
  `presidio/data/social/information_diffusion_default.json`,
  `InformationState` in `decision_engine/information/diffusion.py`) —
  an agent-level reluctance/willingness variable, the same quantity
  the 0.60 denominator already averages over.

**Verdict: post-trust (inferred — documentary, both sides).** Each
document independently owns reluctance; stacking them is a double
count. The v2 numbers stay exactly as elicited; it is the composition
that was wrong.

### 1.1 A third owner, dormant at this cell (measured in code, inferred in effect)

`ThresholdBeliefPolicy` — the default `population_policy` — also emits
`hide_symptoms` / `report_sick_call` overrides off the same
`trust_medical`/`severity_belief` pair, so reluctance has a third
claimant on the default path. At the canary cell it never binds: 20/20
seeds end ALERT and `severity_belief` never crosses the thresholds
(NORO-CHANNEL-01 §4.3: recognition is unreachable here). Recorded, not
changed — de-stacking it is a separate decision.

## 2. The fix (labelled default-path change)

Option chosen: **remove the double count on the declared-vector path**,
because it keeps every number traceable to its source — the vectors
stay v2 Table 2 verbatim and `trust_medical` stays the Layer-1 quantity
it was declared to be. The rejected alternative (divide the elicitation
through mean trust to re-declare the vectors pre-trust) would mint
numbers no document contains and would bake a population mean into a
per-agent scale. Chosen on traceability grounds, not on what lands in
the band.

- `SyndromicSurveillance._declared_reporting_hazard` now returns the
  hazard together with the profile's `observation_model
  .reporting_belief_scaling` semantics: `"none"` (default; the vector
  is realized capture — the `0.5 + 0.5·trust_medical` factor is not
  applied again) or `"trust_medical"` (the labelled pre-change
  composition — vector willingness-conditional, multiplier composes on
  top). `reporting_belief_scaling` is added to
  `schemas/pathogen_profiles.schema.json` and the `sanity_checker`
  `ObservationModel`.
- The scalar fallback (no `severity_model` in profile) and the
  `information_belief` mode keep the multiplier — that *is* the scalar
  channel's declared composition.
- `norwalk_only.json` and the byte-identical `norwalk_gi` block of
  `active_profiles.json` declare `"none"` explicitly with provenance in
  `notes`. The `sars_cov2_resp`/`influenza_a` observation models take
  the new default implicitly; their vectors are declared reporting
  probabilities of the same kind (inferred — not re-traced here).

## 3. Canary re-read (same instrument, same cell, fix applied)

Re-ran the NORO-CHANNEL-01 canary once, locally:
`tools/noro_diag/observation_channel_funnel.py --out
docs/norovirus/noro_channel_02/ --bundle norwalk_only` — 20 seeds
8000–8019, `spirit_cruise_3000 × norwalk_only × 168 epochs`, pooled
default arm, at b9cae80f (the run's working tree is exactly that
commit's tree).

### 3.1 The funnel (pooled over 20 seeds)

| rung | total | pax | crew | vs CHANNEL-01 |
|---|---|---|---|---|
| infected | 142 | 100 | 42 | 143 → 142 |
| symptomatic course | 106 | 76 | 30 | identical |
| symptomatic onboard | 24 | 20 | 4 | identical |
| syndrome-eligible | 106 | 76 | 30 | identical |
| eligible onboard | 24 | 20 | 4 | identical |
| reported infirmary | 9 (all pre-recognition) | 9 | 0 | identical |
| lab-sampled | 5 | 5 | 0 | identical |
| lab-confirmed | 3 | 3 | 0 | identical |
| onset-dated | 3 | 3 | 0 | identical |

`reported_per_eligible_onboard` pooled **0.375**, per-seed median 0
[q05 0, q95 1.0] — numerically identical to the pre-fix canary, band
≈0.4–0.8 still just missed. `symptomatic_per_infected` 0.746; dating
still exact (dated/confirmed 1.0, max abs error 0); still 20/20 seeds
ending ALERT so post-recognition is never exercised.

### 3.2 Why identical (measured)

Removing the multiplier does not consume or reorder any RNG draw — the
same uniforms roll against a hazard that rose ~12% relative
(×0.5+0.5·0.78 ≈ ×0.89 removed). Per-seed payloads are identical to
CHANNEL-01's apart from wall-clock fields **except seed 8011**: 4 more
sick-call events on the same 5 distinct reporters (draws that the
removed factor had previously failed), and one fewer onboard-acquired
infection (21→20 total, consistent with an earlier first call isolating
a host one transmission sooner — inferred). So
the fix demonstrably fired; it simply could not add a distinct reporter
at this cell — 24 eligible-onboard hosts with ~1–3 exposed epochs each,
and every flipped draw belonged to a host who already reported under the
old composition. The band miss is therefore cleanly attributable to the
denominator-mix issue CHANNEL-01 §4.3 flagged (68% subclinical onboard),
not to ascertainment arithmetic.

Direct rate check of both arms (20000 epochs, moderate host,
trust_medical 0.78): `"none"` observed 0.753 vs declared
`1−(1−0.94)^0.5` = 0.755; `"trust_medical"` observed 0.669 vs 0.672 —
the labelled pre-change composition reproduces the old stack.

### 3.3 Goldens and fixtures

None moved. The fast tier passes with no baseline update: tests that
exercise the vector path assert ordering/structure, not the stacked
rate; the scalar fallback and `information_belief` compositions are
unchanged. No fixture regeneration was needed or attributed.

## 4. What this does not do

No constant changed; the vectors are byte-identical to v2. Nothing was
tuned to Wikswo/VSP/attack rate. The dormant third owner
(`ThresholdBeliefPolicy` overrides) and the unreachable post-recognition
vector are recorded, not touched.

## 5. Next decision

**Who owns reluctance at recognition time?** The documentary verdict
here covers the v2 vectors, which own reluctance unconditionally.
`ThresholdBeliefPolicy` (the default `population_policy`) still emits
`hide_symptoms`/`report_sick_call` overrides from the same
`trust_medical`/`severity_belief` axes — a third claimant, dormant at
this cell only because severity_belief never crosses its thresholds
while status stays ALERT. If those overrides are meant to model
behaviour beyond realized capture, their seam needs its own
elicitation; if not, they double-count the same reluctance the vector
already owns whenever they do fire. Decide before any cell that
escalates past ALERT reads a post-recognition vector — otherwise the
second and third owners stack again exactly where the measurement was
supposed to change.
