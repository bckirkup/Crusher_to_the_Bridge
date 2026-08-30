# Five-state severity and observation model — implementation spec (norovirus)

Authored as the design of record. Supersedes the provisional three-stratum
`symptom_severity` block landed in #341. Numbers are from the supplied severity /
observation prior review; the architectural decision (dose-conditioned entry
retained, severity simplex applied conditionally) was taken deliberately and
diverges from the source document's contract, for the reason in §2.

## 1. States

Canonical order, biologically ordered (not ordered by care use):

```
["asymptomatic", "subclinical", "mild", "moderate", "severe_critical"]
```

Norovirus infection-conditioned prior:

```
base_probabilities = [0.25, 0.55, 0.19, 0.009, 0.001]
```

## 2. Entry into the severity model is dose-conditioned, not prior-drawn

The source contract makes the simplex the primary draw and
`illness_probability` a derived view. We do not adopt that, because
`illness_probability` here is not a constant: P(ill | infected) is evaluated per
host on the realised inoculum (Teunis eta = 0.508, gamma = 0.095), and a fixed
five-vector cannot carry that dose dependence. Instead:

1. The existing dose-conditioned draw decides **asymptomatic vs symptomatic**
   (unchanged code path, unchanged parameters).
2. Given symptomatic, the state is drawn from the prior **renormalised over the
   four symptomatic states**:

```
p(s | symptomatic) = base_probabilities[1:] / (1 - base_probabilities[0])
                   = [0.7333, 0.2533, 0.0120, 0.00133]
```

Consequence, and it is the point: the asymptomatic fraction becomes a **model
prediction** measured against the literature's 0.19-0.35, not a parameter set to
it. The severity shape is a prior; the asymptomatic split is an anchor.

`base_probabilities[0]` is therefore reference/documentary for the fraction, and
load-bearing only through the renormalisation. Validation must still require the
full five-vector to be a simplex.

## 3. Observation layer

Norovirus surveillance system is `VSP_AGE`, not a universal channel.

```
syndrome_case_eligibility_by_severity              = [0, 0.55, 0.98, 1.0, 1.0]
reporting_probability_by_severity_pre_recognition   = [0, 0.45, 0.70, 0.94, 1.0]
reporting_probability_by_severity_post_recognition  = [0, 0.50, 0.76, 0.96, 1.0]
episode_reporting_window_days                       = 2.0
```

Recognition state is the ship-level trigger: post-recognition when
`STATUS_RANK[state.trigger_status] >= STATUS_RANK[STATUS_SUSPECTED]`, else
pre-recognition. Surveillance runs before escalation within an epoch, so the
status read is the previous epoch's; that is acceptable and must be documented at
the call site rather than worked around.

### 3.1 Episode probability to per-epoch hazard (unit-safe mapping)

Eligibility and reporting are **per-episode** probabilities; our engine reports
through a **per-day sick-call hazard** converted once by `SimClock`. The mapping,
which must not be short-circuited:

```
P_episode(s, t) = eligibility[s] * reporting[s][t]
h_per_day(s, t) = 1 - (1 - P_episode(s, t)) ** (1 / episode_reporting_window_days)
h_per_epoch     = SimClock.probability_per_epoch(h_per_day)
```

`episode_reporting_window_days = 2.0` is the central norovirus symptomatic
duration (1-3 d). It is a declared unit-bearing parameter, not a tuning knob.

The `0.5 + 0.5 * trust_medical` modifier from #341 is retained, applied to
`h_per_day` before clock conversion. Aggregate capture is therefore *measured*,
not asserted.

Asymptomatic hosts never sick-call (index 0 is exactly 0.0 in both arrays).
Background noise reporting is a separate channel and is unaffected.

## 4. Analytic cross-checks (assert these in tests, on the vectors alone)

```
eligible  / infected     = 0.498700
reported  / infected     = 0.302402   (post-recognition)
reported  / eligible     = 0.606381   -> inside the 0.60 +/- 0.05 cruise anchor
reported  / symptomatic  = 0.403203
```

(Earlier revisions of this spec carried 0.3018 / 0.6053 / 0.4024 for the last
three; those were a rounding error of mine. The values above are exact.)

This is the correction that matters for the fit: the 0.60 anchor is capture among
**AGE-eligible** cases. Our earlier anchor A3 read it as reported/ill and would
have driven reported cases ~1.5x too high.

## 5. Validation (fail loudly; no silent defaults)

- `states` must equal the canonical five, in order.
- `base_probabilities`: length 5, finite, non-negative, sums to 1
  (`np.isclose`), and `base_probabilities[0] < 1`.
- eligibility and both reporting arrays: length 5, all in [0, 1], index 0
  exactly 0.0, and non-decreasing in severity (ordering invariant, in the spirit
  of the dimensional audit).
- `episode_reporting_window_days` > 0.
- `fatality_probability_by_severity`: null for norovirus. A non-null value must
  raise `NotImplementedError` — fatality conditional on severity trajectory is
  not implemented, and must not be double-counted against an independent CFR.
- `assay_sensitivity_by_time_since_infection`: null. A non-null value must raise
  `NotImplementedError` — a universal scalar sensitivity is inadequate and must
  not be silently substituted.
- `lab_sampling_probability_by_severity` (`[0, 0.05, 0.20, 0.60, 0.90]`): stored
  and validated, deliberately **unused**. It is an operational parameter of an
  independent active-sampling channel, not clinical reporting, and wiring it in
  is out of scope here.
- The legacy three-stratum `symptom_severity` block is removed, not deprecated:
  a profile carrying it must fail validation, so no profile can carry both.

## 6. Scope

Norovirus only. The remaining nine pathogens, and the special structures
(Legionella `pontiac_fever_split`, CDI colonisation progression, Ebola
reconstructed recognition) are follow-up work; the schema must accommodate them
but this change must not invent generic five-vectors for them. Profiles with no
`severity_model` keep the existing scalar sick-call fallback.

## 7. Anchors, restated after this change

| # | Quantity | Target | Source |
|---|---|---|---|
| A1 | passenger ever-ill (AGE-eligible) | ~0.154 | whole-ship cohort |
| A2a | asymptomatic / infected | 0.19-0.35 | challenge + outbreak series |
| A2b | activity-limiting (mild+) / infected | ~0.20 | severity review |
| A3a | reported / AGE-eligible | 0.60 +/- 0.05 | cruise cohort |
| A3b | reported / infected | ~0.30 | derived, this spec |
| A4 | top-decile emitters' share of secondaries | ~0.57, with lower symptom frequency and longer detection delay | outbreak reconstruction |

A4 is now the discriminating test: 73% of symptomatic hosts are subclinical with
0.55 eligibility and 0.50 reporting, so detection delay acquires a long tail
endogenously. The three-stratum prior (65% moderate+severe) could not produce it.
