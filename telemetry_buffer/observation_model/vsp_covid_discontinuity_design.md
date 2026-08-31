# Scoring the COVID discontinuity: design

The refit must be scored against the COVID break, not only against the VSP
level targets. This note fixes what is scored, why those statistics and not the
obvious ones, and what the model needs before any of it can be run. It defines
no constant and fits nothing.

Status: design. The observed values are not in here — they come from
`vsp_outbreak_series.csv` (extraction spec: `vsp_series_spec.md`) and are
recorded in the findings note once measured.

## 1. Why bother, given the level targets already exist

Every anchor in `anchor_measurement_spec.md` is a level. A level target is
satisfied by any combination of errors that cancels, and this effort's entire
history is a record of finding such cancellations after the fact: §12 of
`docs/norovirus/norovirus_model_history.md`, and the withdrawn "Expedition agreement"
that turned out to be an inflated infection rate against a deflated illness
ratio. The COVID break is the first anchor available that is a **difference**
between two configurations of the same ships, so errors common to both arms
cancel in the target instead of in the model.

That is also its limit: it constrains only the mechanisms that *changed* across
the break. It says nothing about the dose level, and it cannot be swapped in for
A4.

## 2. The two things that make the naive comparison inadmissible

**The posting threshold conditions the sample.** VSP posts a voyage when 3% or
more of passengers *or* crew report AGE to the ship's medical staff (plus
discretionary "public health significance" postings). Both eras use the same
rule — verified in both the archived and the current pages. So the observed
attack-rate distribution is a truncated one, and the truncation interacts with
the thing being measured: a downward shift in the underlying attack rate mostly
removes voyages from the sample rather than moving the mean of what remains.
Worse, the *reported* attack rate is a product of transmission and reporting
propensity, and there is every reason to think passengers' willingness to
report GI symptoms to a ship's medical centre changed in 2022 for reasons that
have nothing to do with transmission.

**The outbreak count has no denominator.** Panel A of
`docs/norovirus/vsp_covid_discontinuity.png` shows postings recovering to 14-23/year by
2024-2025 against 10-16/year in 2013-2019, but VSP does not publish voyages
sailed, and fleet capacity, itinerary mix and ships under jurisdiction all moved
across the break. The count is uninterpretable as a rate and cannot be a target.

## 3. The resolution: condition the model the same way, and difference

Two rules, and between them the caveats stop being caveats.

**Rule 1 — score only statistics conditional on posting.** Anything of the form
"per voyage" or "per year" needs the denominator we do not have. Anything of the
form "among posted outbreaks" needs no denominator at all. So every scored
statistic is conditional on posting.

**Rule 2 — apply VSP's posting rule to the simulated voyages, then compare.**
Do not attempt to de-truncate the observation. Filter simulated voyages by the
published criteria — 100+ passengers, 3-21 day voyage, and 3% or more of
passengers or crew *reported* (the reported channel, not ever-ill, so the
five-state observation layer is in the path) — and compute the same statistics
on the surviving simulated voyages. Selection bias then applies identically to
both sides and needs no correction. This is the only admissible way to use the
series, and it makes the observation layer part of what is being tested, which
is appropriate: A3 capture is one of the anchors.

**Then difference against crew.** Within a posted outbreak, crew are a control
group for the era-level reporting shift: an era-wide change in reporting
propensity multiplies passenger and crew reported attack rates alike and
divides out of a ratio of ratios. Crew are also the group the COVID-era
sanitation changes reached *least* — the enhanced measures were passenger-facing
— so the passenger-minus-crew contrast is close to the quantity the model's NPI
configuration is supposed to produce.

Caveat on Rule 2's residual, stated because it does not vanish: posting is
driven mostly by the passenger arm (larger denominator, usually higher attack
rate), so the crew distribution is less truncated than the passenger one and
the truncation corrections do not cancel exactly in the ratio of ratios. Under
Rule 2 this is not a bias to correct — the simulated arm inherits the same
asymmetry — but it does mean the difference-in-differences cannot be read as a
clean causal contrast in the observation alone. §6 measures how large that
residual is.

## 4. The statistics

Let `posted(e)` be the posted outbreaks of era `e`, `e ∈ {pre, post}`, with
`pre` = voyages ending 2004-2019 and `post` = voyages ending 2022 onward. 2020
and 2021 are excluded: the industry was shut down or restarting under
protocols that no longer apply. All attack rates are *reported* attack rates,
which is what VSP publishes.

| | statistic | scored |
|---|---|---|
| A7a | median passenger attack rate over `posted(post)` / same over `posted(pre)` | yes |
| A7b | median crew attack rate over `posted(post)` / same over `posted(pre)` | yes |
| A7c | **A7a / A7b** — the passenger-specific component | yes, primary |
| A7d | tail counts `pax AR >= t` per era, `t` in {10, 12.5, 15, 20}% | reported, exact test |
| A7e | postings per year, and the norovirus fraction of postings | **no** |

A7d is included because the upper tail is where the 3% floor does not reach:
the floor truncates from below, so a change in the mass above a high threshold
is a statement about distribution shape that the threshold cannot manufacture.
Panel C of the operator figure suggests the post-era distribution loses the
>15% tail entirely.

It is **not** a bootstrap statistic, and the reason is worth stating because it
is a trap I walked into. At the real sample size the post-era tail above 15%
can be empty. Every resample of an empty tail is empty, so a percentile
interval on the post/pre tail ratio collapses to exactly [0, 0] — an interval
that excludes 1, and would be read as a decisive tail collapse while resting on
zero observations. The tail is therefore reported as counts with Wilson
intervals per era and a two-sided Fisher exact test, and at four thresholds
fixed in advance so that no threshold can be chosen after the fact for its
p-value. To calibrate what those numbers can support: 13/261 against 0/64 gives
p = 0.080, and 13/261 against 1/64 gives p = 0.32. A vanished tail at the real
post-era sample size is suggestive and not significant. 51/261 against 4/64 —
the shape of the 10% threshold — gives p = 0.009, so if the tail carries a
signal at all it will be at the lower thresholds.

A7e is reported at every scoring and never scored: A7e's numerator has no
denominator (§2), and the norovirus fraction moves with laboratory
ascertainment, which also changed across the break.

Each statistic is scored against a bootstrap interval over posted outbreaks,
not against a point estimate. With roughly 64 posted outbreaks in the post era,
the interval on a 15-20% shift is wide, and a model that lands inside it is
compatible with the observation rather than validated by it. A model that
reproduces the point estimate exactly is not thereby better than one that lands
elsewhere in the interval, and no constant may be moved to close a gap that is
inside the interval.

**Sign is not assumed.** Whether crew attack rates moved across the break is
the measurement that decides whether the model needs a passenger-facing lever
or a global one. The ledger currently asserts crew rates did not move, on the
strength of A5's stability; that assertion is unverified and is flagged as such
until A7b is measured. If A7b turns out to equal A7a, the "passenger-facing
sanitation" account is wrong and the discontinuity is telling us something
era-wide changed instead — which would be a finding, not a nuisance.

## 5. What the model does not yet have

`docs/formal_spec_v2.md` §3.7 defines the interface this needs — a per-agent,
per-route `dose_reduction_multipliers` with a single `npi_compliance`
interpolating between no benefit and reference efficacy. **None of it is
implemented**: `dose_reduction_multipliers` and `npi_compliance` appear nowhere
outside that spec. Until they exist there is no lever to move between the two
arms, and the discontinuity cannot be scored at all.

#355 supplies the sanitation half of the lever (routine coverage and per-event
log10 are separately configurable, and outbreak response is a distinct
mechanism), but sanitation coverage is currently one schedule for every zone
class, which is precisely the asymmetry a passenger-facing intervention needs.
That is ledger §4.1 and it blocks this.

The pre/post configuration sets must come from what the industry actually
changed and what the literature says those changes do. That audit is now its
own document, `post_covid_configuration_sources.md`, and it revises two guesses
made here. Alcohol hand rub is weak against norovirus, but the figure to use is
the measured one — soap and water removes >3.0 log10 infectious MNV1 against
2.8 for alcohol rub, and >5-6 log10 genomic copies against 1.2-3.3
(Tuladhar 2015) — not the "~90% kill, m ≈ 0.1" previously written here, which
had no source. And the enhanced-HVAC row is **not** irrelevant: norovirus has
an aerosolised-vomitus route, the fleetwide MERV 8 → MERV 13 upgrade is
specified and quantified (Healthy Sail Panel Rec. 31), and it acts on the
mechanism behind large events rather than on the median voyage. The post-2020
arm must also carry raised susceptibility (O'Reilly 2021, Lappe 2023), which
pushes the opposite way; leaving it at the pre-2020 value would let the NPI
configuration silently absorb it. **The post-2020 set may not be chosen to
produce A7c.** If the literature ranges cannot produce the observed difference,
that is recorded as a failure of the model, and the ranges are not widened to
fix it.

## 6. What the estimator actually recovers

Before trusting any of this I ran the estimator against synthetic voyages with
a known answer: lognormal passenger attack rates, crew rates a fixed share of
passenger rates with correlation `rho` between the two arms, the 3% posting
rule applied, and a known post-era multiplier on each arm. 20,000 posted
voyages per arm, so what follows is bias, not noise
(`tests/test_vsp_discontinuity_analysis.py`).

With a true passenger shift of 0.80 and crew genuinely unchanged:

| dependence | A7a measured | A7b measured | A7c measured | A7c truth |
|---|---:|---:|---:|---:|
| rho=1.0 | 0.869 | 1.086 | 0.800 | 0.800 |
| rho=0.7 | 0.868 | 1.060 | 0.819 | 0.800 |
| rho=0.0 | 0.855 | 1.021 | 0.837 | 0.800 |

Three things follow, and they are the reason the design is shaped this way.

**The naive level comparison is attenuated.** A7a reads 0.86-0.87 against a
truth of 0.80: the posting floor removes the voyages that the intervention
pushed below 3%, so what survives understates the shift by 7-9% relative. Any
statement of the form "posted attack rates fell 15%, so transmission fell 15%"
is wrong in a known direction.

**The difference-in-differences is identified, and its residual is small.** A7c
recovers 0.800 exactly when the arms move together and errs by at most 4.6%
relative across the whole range of dependence. That residual is the §3 caveat,
quantified; Rule 2 removes it, because the simulated arm goes through the same
filter.

**A crew increase can be pure artifact, and this refutes a reading of A5.** A7b reads 1.02-1.09 in every row
above even though crew rates did not move at all: when passenger rates fall,
posting increasingly requires the crew arm to be the one over 3%, which selects
high-crew voyages into the sample. So if the measured A7b comes out above 1,
that is not evidence crew fared worse post-COVID, and the ledger's "crew rates
did not move" is not testable by reading A7b alone. Only A7c, or the model run
through Rule 2's filter, can separate the two.

**A whole class of intervention is invisible here, and A7c is a lower bound.**
Conditioning on posting is what makes the estimator admissible (§3), and it
costs exactly this: an intervention that stops an introduction from taking off
prevents the posting rather than shrinking it, so it leaves no trace in any A7
statistic. Its effect lands entirely in the annual posting count, the one
series with no voyage denominator, which is why A7e stays descriptive. An
intervention that halved the number of outbreaks while leaving the survivors'
shape untouched scores A7c = 1.0 exactly. So a flat A7a is not evidence that
NPIs did nothing, and A7c bounds the capping half of the effect only. Several
of the best-documented post-2020 measures — pre-boarding screening, denial of
boarding — are of precisely the invisible kind; see
`post_covid_configuration_sources.md` §1. Recovering the takeoff channel needs
a voyage denominator from outside VSP, which would be a separate anchor on
outbreak incidence and is not part of this design.

A fifth point, from the same synthetic voyages: the naive tail bootstrap
degenerates to [0, 0] exactly as §4 describes, which is why A7d is scored by an
exact test on counts instead. The check is a test, not a claim.

Sample size for the model arm follows from the same run: at 261/64 posted
voyages the bootstrap interval on A7a is about ±10% relative, so the simulated
arms need enough posted voyages that their own Monte Carlo error is small
against that — at least 1,000 posted voyages per configuration, which at a
posting rate that is itself unknown means the voyage count must be set by
measuring the posting rate first, not assumed.

## 7. Order of work

1. Extract the series and check it (`vsp_series_spec.md`). No model change.
2. Measure A7a-A7e with intervals, and settle the sign question in §4. Record
   in the findings note and as an anchor in `anchor_measurement_spec.md`.
3. Implement §3.7's NPI interface, and per-zone-class cleaning coverage.
4. Define the two configuration sets from the literature.
5. Refit the common dose against the level anchors on the **pre** arm only —
   the pre arm is where 261 of the 325 outbreaks are — then run the post arm at
   the same dose with the post configuration, and score A7. The dose is fitted
   once, on one arm; the difference is a prediction, not a second fit.

Step 5 is the point of the whole exercise: the discontinuity is only evidence if
nothing about it was fitted.
