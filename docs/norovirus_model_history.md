# Norovirus fit: model history and defect record

Dated record of every substantive change to the norovirus transmission,
observation and measurement model during the common-dose fit effort, what each
change moved quantitatively, and which campaigns it invalidated.

It exists because the credibility of any eventual fit rests on this record and
not on the fit's goodness. The model has been wrong, repeatedly, in ways that
produced plausible output; a reader cannot assess the current version without
knowing how the previous ones failed. Numbers superseded here should be treated
as withdrawn, including those already quoted in write-ups under
`telemetry_buffer/`.

Convention: each entry gives the defect, the mechanism, the measured effect, and
the campaigns whose results it invalidates. PR numbers are the merge record.

## Why this document rather than a pre-registration

Pre-registration governs confirmatory analysis and presupposes there is no
process to show. This is model development, and the process is the evidence: a
frozen protocol here would have locked in defects that had not yet been found,
and a clean protocol-plus-fit presentation would lay a tidy surface over the
defect history below. The discipline substituted for it is workflow
transparency — this record, priors propagated rather than pinned
(`telemetry_buffer/observation_model/severity_prior_sensitivity_findings.md`),
and explicit labelling of internal checks as internal.

In particular: a dose-recovery exercise (simulate at a known dose, refit, see
whether the dose is recovered) is an identifiability check on the estimator
against our own generative model. It is not evidence that the model is correct
and must never be reported as validation.

## 1. Time-unit and clock defects

**VSP trigger read instantaneous prevalence.** The outbreak declaration
compared a point-in-time symptomatic count against the CDC thresholds, which are
defined on cumulative reported cases. Fixed in #325.

**Rates authored per day, consumed per epoch.** Reservoir, contact, behavioural
and cost rates, then delays, intervals, windows and the CONTAM timestep, were
consumed as though their declared magnitudes were per-epoch quantities. Every
time-dependent parameter now carries a declared unit and is converted once
through `SimClock`; a repo-wide guard test fails on new naked
`*_per_epoch` / `*_epochs` physical parameters. #327, #328.

**Shedding emission was per-epoch, not per-day.** The same profile was therefore
24x more infectious on the hourly clock than on the legacy daily clock. A pure
global factor, so it relabels the dose axis by +1.38 log10 rather than changing
model structure. #338.

## 2. Time-origin defects

**The shedding curve was read on the wrong axis.** Curve boundaries authored as
days since *onset* were evaluated at days since *infection*, so hosts shed at
peak before they could biologically do so. Measured effect on expedition,
transmission-only, held-out seeds: infection doubling time went from 2-10 h (1.3 h
on mega) to 15-29 h at the fit-relevant rungs, against a norovirus serial
interval of ~1.2-1.5 d. Attack rate stopped being pinned at 0.800 and an
intermediate outbreak regime appeared. The dose ladder moved down ~1.5 rungs.
#334.

**The wearable physiological phase curve had the same defect**, with the sign
consequence reversed: simulated fever peaked ~1.2 d before symptom onset and
pre-onset hosts fell through to the recovery phase. #334.

Invalidates: all campaigns before v3.

## 3. Dimensional defects in the dose pathway

**Airborne dose multiplied a concentration by a room volume.** Replaced with a
clock-scaled inhaled air volume per host. This removed an occupancy dependence
that had been read as a hull-size effect. #332.

**The airborne reservoir never decayed on the production path.** The half-life
decay lived in an engine method the Picard simulation never calls. Measured on an
expedition voyage with a single constant shedder, zone mass climbed +1.55/epoch
and never came down: 1.55 at hour 18, 36,591 by hour 90. The same array was
also fed by a surface deposition fraction and scrubbed by surface
decontamination, so one array stood in for two reservoirs and a surface SOP was
reducing airborne dose. #338.

**Fomite and food doses were extensive.** No surface-area or per-serving
normalisation, so per-capita dose rose with hull size — the same defect #332
removed from the air. Neither route subtracted what it delivered, making both
pools infinite sources. #338.

**Direct-contact dose was taken from the zone average** rather than from the
partners actually contacted. #329.

Invalidates: v3 (92/94 children of the v3 Spot job also failed for unrelated
reasons and were discarded).

## 4. Sign and symmetry defects

**Confinement was one-sided.** A quarantined agent's *received* dose scaled by
the isolation factor 0.05; nothing scaled what they *emitted*. Measured on an
isolated pathway test, confining a shedder changed the droplet dose to twenty
co-occupants by exactly zero. Compounding it, quarantine parks the host in
`home_zone`, a shared cabin-corridor aggregate with 23-189 occupants on mega, for
every epoch instead of the few they would otherwise spend there — so with droplet
carrying 94-95% of establishments, quarantining an infectious host slightly
*increased* cumulative emission. This is the entire explanation for the v4
finding that 38k-150k quarantine person-epochs bought nothing above 450 berths
and that compliance was a null knob. #340.

Withdrawn as a result: the v4 operational conclusion that response is ineffective
at scale. Post-fix, paired at matched hull/dose/seed, syndromic surveillance with
85% compliance cuts ever-ill by 56-91% relative, straddling the literature's
~71% averted under 72 h isolation.

Still open, deliberately: confined hosts get the corridor aggregate rather than a
per-cabin zone. That is a layout change, not a sign error.

## 5. Heterogeneity and seeding

**The apparent hull-specific dose requirement was a seeding artifact, not
biology.** v4 scoring found classic/spirit/mega inside their VSP IQRs at
dose_adjustment 2.5-3.0 while expedition fitted only at 1.0 — two log10 rungs.
Two probes settled it. Holding the emitting side at exactly one shedder, dose
delivered per shedder-epoch is hull-independent to within 1.16x (expedition
7,664 vs mega 8,862), so no occupancy defect remained in the pathway. What
differed was ignition: with `shedding_variance_log10` = 1.5, a persistent
per-host lognormal whose mean is 389x its median, and seeding at constant
per-capita prevalence, the four index cases shed 5.0e2 / 1.6e3 / 1.9e4 / 5.1e5 on
identical biology — 1 draw at the tail on expedition against 11 on mega. Seeded
equally at dose 3.0, classic/spirit/mega fall from 3-6.6% reported to
0.02-0.17%, and expedition — the hull that "needed 100x more dose" — is the
easiest of the four to ignite.

Consequences: sigma set to 1.0 on the Teunis 2014 between-host range (~4 log10
in 102 subjects) (#340); one index case per hull adopted as the primary seeding
arm, with per-capita seeding retained as sensitivity.

Withdrawn: every statement that the four hull classes require different doses,
and the hull-size gradient magnitudes quoted before #340 (the classic/expedition
ever-ill ratio is 1.5x at sigma = 0 and 2.4-4.9x at sigma = 1.5, i.e. the
ordering was largely sigma).

## 6. Comparison-set definition

VSP records exist only for voyages that had a reportable outbreak, so the
marginal distribution over seeds — which includes fizzles — is not the
comparable quantity. The primary comparison is now conditioned on take-off.

Noted limitation: the conditioning is approximate. VSP selection is a
3%-reported threshold; the take-off criterion used here is a prevalence
condition. Related, not identical.

## 7. Observation model

**Sick-call was driven by the ship's alert status, not by the host.** The
per-host sick-call hazard was scaled by `severity_belief`, an information-state
variable that starts at 0.1 and rises only when an outbreak is declared,
attenuating a documented 0.70/day to ~0.06/day and making the fit target depend
on the response branch. How sick a host actually is was represented nowhere.
Replaced by a severity-conditioned own-sick-call hazard. #341.

**The 0.60 capture estimate was applied to the wrong denominator.** It
constrains reporting among AGE-*eligible* cases, not among all symptomatic
infections; calibrating to the latter reading would have produced ~1.5x too many
reported cases. #343.

**The severity prior was ~50x too heavy at the top and had no subclinical
state.** #341's provisional prior put 65% of symptomatic hosts in
moderate+severe; the five-state synthesis puts ~1.3% there and ~73% subclinical.
Subclinical hosts shed, mostly fail the AGE case definition and mostly do not
report, which is the mechanism behind the documented superspreading correlation
(top-decile emitters carrying ~57% of secondary cases, with lower symptom
frequency and 83 h vs 47 h diagnostic delay). #343.

**Evidence grading.** Of the twenty numbers in the five-state layer, the
severity vector is a synthesis [M] and the eligibility and reporting vectors are
assumed [A]. Two quantities in the chain are empirical [E]: the ~0.60 capture
(one cruise investigation) and the asymptomatic range 0.19-0.35. Sensitivity
analysis shows four components carry ~0.97 of the elasticity, that
reported/eligible is a weak constraint (98.6% of prior draws satisfy 0.60 +/-
0.05), and that reported/infected — the quantity the dose fit runs through —
spans 0.250-0.361 under the prior and reaches 0.188 under an
isolation-avoidance scenario. Any fitted dose inherits that band and must be
quoted with it.

No study identifies the infection-to-reported ratio on a cruise: none links an
infection denominator (serology or universal serial PCR) to reporting. MIDRS/VSP
is purely syndromic and carries no seroconversion arm. That ratio is therefore an
explicit scenario calculation, not a fitted constant.

## 8. Measurement defects

**Infection attack rate and illness rate had different denominators.**
`attack_rate` in run summaries was (infected + recovered) over the whole ship
while ever-ill and reported were passenger-only, with crew at 30-40% of
complement. Every "80% infected vs 15% ever-ill" comparison quoted before #342,
including in the v4 scoring and both pilots, mixed populations. Separately, the
per-epoch counter named `attack_rate` was instantaneous symptomatic prevalence.
Both fixed and renamed. #342.

Withdrawn: all ill/infected ratios computed before #342.

## 9. Dose-response applied per epoch

**Infection depended on how finely time was sliced, not on the dose received.**
The beta-Poisson dose-response was evaluated on one epoch's dose with an
independent Bernoulli drawn every epoch, and the illness draw then conditioned
on `acquired_particles` = that single epoch's slice. Beta-Poisson is a Poisson
single-hit model mixed over a host susceptibility `r ~ Beta(alpha, beta)`; `r` is
a property of the host, so re-drawing it hourly treats each hour as a fresh
person. At 10^3 total particles, splitting into 24 hourly slices instead of one
exposure took infection attack rate from 0.32 to 0.89 and ill/infected from 0.45
to 0.26. The hourly-epoch migration did not introduce this, but multiplied the
trial count by ~24. Fixed by drawing `r` once per host and pathogen, running the
hazard on effective dose (protection and superinfection now scale dose, not
probability, because scaling probability is not epoch-invariant), and passing
the cumulative inoculum to the illness and incubation draws. No fitted parameter
added. #346.

Withdrawn: every infection attack rate reported under hourly epochs, which are
inflated by this, and every ill/infected, which is deflated by it — including
the v4 campaign and the post-merge anchor pilot at `7a9b439`. Fitted doses from
those runs do not transfer.

The fix does not reach the anchors and must not be read as doing so. Under the
corrected form, infection attack rate and ill/infected are welded to the same
dose (attack rate 0.32 caps ill/infected at 0.45; 0.68 caps it at 0.71), so A1
and A2 are jointly unsatisfiable with homogeneous exposure. Host-level exposure
heterogeneity reconciles them (at attack rate 0.21 and sigma_log10 = 3,
ill/infected 0.61 and ever-ill 0.128), which is the point-source picture the
literature describes; the droplet pathway, carrying 94-95% of establishments,
gives every susceptible in a zone the identical well-mixed dose and cannot
produce it.

## 10. Parameters held fixed by assumption

These are not identified by anything in the fit, and any of them could move the
reported rate. They are listed so that "one fitted parameter against six
anchors" is not read as a stronger claim than it is; the system is
over-determined *given* these.

- Route weights (contact 0.35, fomite 0.30, food 0.20, droplet 0.10, HVAC 0.05):
  assumed, not traced to a source.
- Direct-contact transfer fraction: implicitly 1.0, where a contact-model
  anchor in the literature is ~0.25, and contact is the largest dose route.
- Contact rate: Korkin 1.33/day against POLYMOD 13.4/day. Unresolved. Raising it
  is not equivalent to raising dose, because it changes the variance that
  produces the intermediate outbreak regime.
- Confinement attenuation factor 0.05.
- The 20% innate non-susceptible ceiling, which is why infection attack rate
  pins at exactly 0.800 and why the fit must be read on reported cases.
- `shedding_variance_log10` = 1.0: literature-anchored, but to a range.

## 11. Corrections to claims made during the work

- GitHub Actions was reported as broken on the #341 branch. It was slow to
  queue; the full check set ran. Escalated too fast.
- Direct contact was reported as the dominant establishing route. Post-#338 it
  is droplet, at 94-95% of infections on every hull.
- The 120-run post-fix pilot's provenance was questioned after a rebase revealed
  the branch predated #340. Checked: the recorded commit already contained
  emission-side confinement and sigma = 1.0. The numbers stand.
- The superspreader anchor cannot be measured as stated. Transmission goes
  through reservoirs, so no infection has an identifiable infector; the reported
  quantity is a proxy (per-host cumulative emission weighted by susceptible
  co-occupants) and must be labelled as one.

## 12. Standing defect base rate

Eight distinct unit, dimension, time-origin or sign defects were found in this
effort, each by chasing an anomaly rather than by a check that would have caught
it, and every campaign before v4 was invalidated by a defect discovered after it
ran. Guards now cover naked epochs, dose-pathway dimensions, reservoir
conservation, per-capita invariance to occupancy, cross-clock equivalence of
per-day quantities and epoch-invariance of the dose-response. The audit is not exhausted, and the correct prior is that
further defects exist. Absence of a further finding is not evidence of
correctness.
