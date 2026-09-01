# SARS-CoV-2 trajectory fit — training and out-of-sample design

> **Status:** Proposal, 2026-09-01. **Nothing here is implemented.** Per
> `docs/AGENTS.md`, a document in `proposals/` describes no existing behaviour.
> Prerequisites in §7 must land before any of it can run.

## 1. Why this arm is shaped differently from the norovirus arm

Norovirus gives us 37,258 voyages, no per-day series anywhere, and an
observation process (VSP posting at ≥3% reported illness) that is a threshold on
self-reported sick calls. SARS-CoV-2 gives the mirror image: a handful of hulls,
each with a per-day series, and an observation process that is a *testing
campaign* whose schedule was itself published. The anchors therefore cannot be
shared, and this spec keeps them in a separate `covid.*` namespace. Norovirus
anchors A1–A10 are not scored against COVID runs and vice versa.

The asymmetry also decides what is identifiable. A trajectory across a
quarantine boundary identifies a growth rate and the effect of a discrete
intervention; it does not identify a posting probability. A cross-ship attack
rate distribution identifies levels and the takeoff/no-takeoff split; it does not
identify a generation interval.

## 2. Train / test split — fixed before data collection

Fixed on 2026-09-01, before any model was run against any of it, so the split
cannot be chosen after seeing which hull fits.

**Training (one hull):** Diamond Princess, Yokohama, Feb 2020.

**Held out (never used to set a parameter):**

- Greg Mortimer, Antarctic/South Georgia, Mar–Apr 2020.
- The Willebrand 2022 cross-ship attack-rate distribution.

If a held-out score is used to revise a parameter, it stops being held out and
this document must say so.

## 3. The observable channels

The model knows the true infection state of every agent. **The truth channel is
barred from scoring.** Every anchor below is a quantity an observer of the real
event actually held, reproduced by simulating the observation process that
produced it. This is the point of the exercise: we score what was observable
with what would have been observable.

### 3.1 Training anchors — Diamond Princess

Population 3,711 (2,666 passengers, 1,045 crew). Index case disembarked Hong
Kong 25 Jan; cabin quarantine ran 5–19 Feb; crew continued working through it.

| id | observable | value | source | grade |
|---|---|---|---|---|
| `covid.T1` | symptom-onset curve, daily, passenger and crew separately | 197–199 cases with recorded onset; 34 onsets before 6 Feb vs 163 on/after; crew/passenger split published per day | MHLW/NIID epi curve (200223_epi_curveENG), NIID Field Briefing | A |
| `covid.T2` | onset-curve turn relative to the 5 Feb quarantine | passenger onsets fall away after quarantine; crew onsets persist later | same | A |
| `covid.T3` | daily PCR positives under the published test schedule | 31 tests → 10 positive (5 Feb) … 681 tests → 88 positive (18 Feb); cumulative 3,063 tests / 634 positive by 20 Feb | Eurosurveillance 2020;25(10):2000180 Table 1 | A |
| `covid.T4` | asymptomatic share among positives | 320 of 634 by 20 Feb; 311 of 712 at final count | as above; Willebrand 2022 | A |

`covid.T2` is the load-bearing one. A level can be matched by any number of
parameter combinations; a curve that bends at a known intervention date, in one
subpopulation and not the other, is far harder to satisfy by accident. It is
also the reason the training hull must be Diamond Princess rather than the
expedition hull — no other vessel has an enumerated intervention mid-curve.

### 3.2 Held-out anchors

| id | observable | value | source | grade |
|---|---|---|---|---|
| `covid.H1` | final PCR prevalence under near-complete testing, expedition hull | 128/217 positive (59%) on a single ship-wide test day, 128 passengers + 95 crew aboard, cabin confinement from day 8, tested day ~20 | Ing 2020, *Thorax* 75(8) | A |
| `covid.H2` | asymptomatic share under near-complete testing | 104/128 (81%) asymptomatic at test; 24 (19%) symptomatic | Ing 2020 | A |
| `covid.H3` | cross-ship attack-rate distribution | 79 ships, 104 voyages to Oct 2020; median AR 0.2% (IQR 0.03–1.5), mean 3.7%; median 3 cases per ship; Diamond Princess 712 and Ruby Princess 907 as outliers | Willebrand 2022, *Eurosurveillance* 27(1) | A for the aggregate, C for any single ship |
| `covid.H4` | serology-based case ascertainment in a repatriated subgroup | 45/49 (92%) cases by PCR-or-IgG; 42% of cases asymptomatic; only 15% of symptomatic reported fever | Rockett/repatriate cohort, *Epidemiol Infect* (PMC7900670) | B — a self-selected subgroup of one hull |

`covid.H3` is the answer to "do we have COVID data on other classes": we have
104 voyages, and the distribution is violently right-skewed — most ships
recorded a handful of cases and two exploded. A model tuned to reproduce
Diamond Princess and nothing else will fail `covid.H3` by predicting an epidemic
on every hull. That failure mode is the main thing the held-out set exists to
catch.

`covid.H2` versus `covid.T4` is a second, subtler test: 81% asymptomatic under
one-shot universal testing against ~50% under rolling symptom-prioritised
testing is largely an artefact of *when* people were tested relative to onset.
A model with a correct observation layer should reproduce both from the same
biology; one that has absorbed the ascertainment into its biology cannot.

## 4. The observation layer

Nothing in §3 can be scored without this, and it is where most of the
implementation work sits.

**Diamond Princess testing campaign.** A replica that reproduces, per simulated
day: the number of tests available (published daily), the eligibility rule in
force (high-risk and symptomatic first; from 11 Feb all passengers by descending
age band; crew last), and PCR sensitivity as a function of days since infection.
Simulated "confirmed cases" are the output of this campaign, never the truth
channel. Test counts and the eligibility sequence are published, so this layer
is largely *measured* rather than assumed — a materially better position than the
norovirus observation model's fifteen assumed numbers constrained by one
aggregate.

**Greg Mortimer testing campaign.** A single ship-wide test event on one day,
with the same sensitivity curve. Trivial by comparison, which is exactly why it
is the held-out hull: if the fit only works under the complicated campaign, the
campaign is absorbing the error.

**Symptom observation.** `covid.T1`/`covid.T2` need onset dates, not sick calls.
This is a different observable from the norovirus reported-case channel and must
not reuse `sick_call_probability`.

Assumed quantities in this layer (PCR sensitivity curve, symptom-report
completeness) get sourced and graded individually per
`.agents/skills/model-parameter-provenance/SKILL.md`, and are counted in §6.

## 5. What is fitted, and what is not

**Fitted — one parameter.** The respiratory emission scale (the sourced
replacement for the misapplied faecal-release term, §7.1). One scalar,
fitted only to `covid.T1`/`covid.T3` on Diamond Princess.

**Fixed from the profile or the literature, not adjusted:** incubation
distribution (median 5.8 d, dispersion 1.57), shedding curve shape,
presymptomatic window, recovery day, asymptomatic infectiousness ratio,
dose-response α/β, contact kernel, HVAC parameters, ship geometry.

**Fixed from the event record, not fitted:** quarantine start date, who it
applied to (passengers confined, crew working), test volumes and eligibility
order, population and passenger/crew split.

If one scalar cannot reproduce the trajectory shape, that is a reported miss and
a statement about the mechanism. It is not a licence to open a second knob. In
particular, quarantine efficacy is *not* a free parameter: cabin confinement is
represented by the existing movement and contact machinery, so `covid.T2` tests
the contact model rather than a fitted compliance number.

## 6. Degrees of freedom

To be counted explicitly before the first fit, in the format of
`docs/norovirus/norovirus_parameter_freedom_audit.md`: one fitted biological
scalar, plus however many assumed numbers the §4 observation layer requires,
against four training observables and four held-out ones. The audit must state
the count, not assert that it is small.

## 7. Prerequisites

1. **Emission scale re-sourced.** Per `docs/covid_arm_status.md`, the only
   shedding scaler is `environmental_faecal_release_log10_g_per_epoch` — grams
   of stool — and `sars_cov2_resp` pays 3 log10 of it. The profile's N50 is
   quoted in units that same key defines, so the emission scale and the
   dose-response denominator must be re-derived together against a respiratory
   measurement (viral copies per expelled respiratory volume). Until then the
   arm has no meaningful dose axis to fit.
2. **Severity and observation models for `sars_cov2_resp`.** Currently absent,
   which `orchestrator_init` permits when both are absent, so COVID reporting
   silently falls back to a flat `sick_call_probability`. Needed for §4, sourced
   independently of any anchor here.
3. **Voyage geometry per scenario.** Diamond Princess is a ~4-week confined
   event and Greg Mortimer a 28-day isolation; both exceed the campaign's 10-day
   voyage. Scenario duration, population, and the quarantine schedule become
   scenario configuration.
4. **Route-weight semantics** (`docs/norovirus/norovirus_parameter_freedom_audit.md`)
   — declared droplet/HVAC weights are not realized shares on this arm either.

## 8. Known threats to this design

- **One training hull.** Diamond Princess is an outlier in its own distribution.
  Fitting to it risks a model that cannot produce the 0.2% median of
  `covid.H3`. This is stated as the expected failure mode, not a caveat.
- **Testing-driven counts.** `covid.T3` moves with test volume. If the campaign
  replica is wrong, the fit absorbs the error into biology. `covid.T1` (onset,
  test-independent) is therefore the primary and `covid.T3` the secondary.
- **Onset-curve incompleteness.** The published curve covers 197–199 of the
  cases with recorded onset; the source notes further symptomatic cases whose
  onset dates were imputed from a ~3-day report lag. The scored statistic must
  use the recorded-onset subset with its own denominator, not the full case
  count.
- **Ancestral lineage.** All of this is pre-Alpha SARS-CoV-2 in an unvaccinated,
  immunologically naive population. A fit here does not transfer to any later
  era without an explicit immunity and variant argument.
