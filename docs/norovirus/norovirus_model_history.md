# Norovirus fit: model history and defect record

> **Status:** Permanent record

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

Measured after the fix, matched seeds, nothing else changed (120 runs at
`d557f39` against the same 120 at `7a9b439`;
`telemetry_buffer/observation_model/postfix_anchor_pilot_d557f39/postfix_anchor_findings.md`).
Natural-history arm, dose 2.0: infection attack rate 0.797 -> 0.407
(expedition) and 0.794 -> 0.465 (classic); ill/infected 0.264 -> 0.341 and
0.224 -> 0.364. Direction is uniform across all six natural-history cells,
1.8-2.9x down on infection and 1.3-2.0x up on illness.

**The fix cost the model its one endpoint agreement, and that is the honest
result.** Expedition's reported attack rate sat inside the VSP IQR at 6.02%
before the fix; it was a cancellation of an inflated infection rate against a
deflated illness ratio, and correcting only the inflated side drops it to 3.48%,
below the 4.51% floor. A4 now fails on both hulls. Classic's reported rate, by
contrast, is unchanged to three decimals (3.88% -> 3.89%) because the same two
moves cancelled there. Any claim that this model reproduces VSP attack rates is
withdrawn. Take-off also fell in five of six cells at fixed dose, so the ladder
is effectively lower and must be re-cut before any fit.

The fix does not reach the anchors and must not be read as doing so. Under the
corrected form, infection attack rate and ill/infected are welded to the same
dose (attack rate 0.32 caps ill/infected at 0.45; 0.68 caps it at 0.71), so A1
and A2 are jointly unsatisfiable with homogeneous exposure. Host-level exposure
heterogeneity reconciles them (at attack rate 0.21 and sigma_log10 = 3,
ill/infected 0.61 and ever-ill 0.128), which is the point-source picture the
literature describes; the droplet pathway, carrying 94-95% of establishments,
gives every susceptible in a zone the identical well-mixed dose and cannot
produce it.

## 9a. Stale inoculum surviving recovery

**A host's unresolved challenge dose carried across episodes.**
`cumulative_exposure` was zeroed when an infection established, but never when
one resolved. An already-infected host keeps accumulating superinfection dose
into the same pool, so on recovery the residue survived and would have been
added to the inoculum of any later episode, inflating that episode's
dose-conditioned illness and incubation draws. The persistent Beta draw
`dose_response_susceptibility` is deliberately *not* reset: secretor-status-like
susceptibility is a permanent property of the host, and resetting it would
re-introduce the defect of §9 across episodes rather than within them.

Reach is small — it needs superinfection during an episode followed by
reinfection after it — so no reported measurement changes. It is recorded
because it is the same class of error as §9 (state that should be scoped to one
challenge outliving it), and because it was found by specification review rather
than by an anomaly.

## 9b. Clearance proposed as the mechanism for A2, and why it is not

A within-host specification review proposed exponential clearance of the
retained pre-establishment inoculum
(`inoculum_clearance_rate_per_day`) as the mechanism that would make diffuse and
concentrated exposure biologically distinct, and so raise ill/infected without
touching the Teunis constants. **It cannot, and the reason is algebraic.** With
hazard linear in the retained pool `R` and `R` decaying exponentially, the
accumulated hazard from deliveries `D_i` at times `t_i` over a horizon `T` is

```text
H = (r_rate / lambda) * sum_i D_i * (1 - exp(-lambda * (T - t_i)))
```

Each delivery enters linearly, discounted only by the part of its decay integral
that the end of the horizon truncates. Once the horizon extends past the
exposure, the weights go to 1 and `H` depends on total delivered dose and
nothing else. This is the same result that withdrew the fixed-window proposal:
grouping, resetting, or leaking a linear accumulator cannot distinguish diffuse
from concentrated delivery.

Measured over 40,000 hosts at total dose 1000 delivered across five days
(`telemetry_buffer/observation_model/clearance_additivity_check.py`), every
calibrated cell sits on the additive closed form 0.3181 regardless of `lambda`
or of delivery in 1, 24 or 168 increments; the single departure (0.306 at
`lambda` = 0.5) is predicted to three decimals by the end-of-voyage truncation
weight. And ill/infected moves the *wrong* way — 0.43 for a bolus against 0.354,
0.297 and 0.226 at `lambda` = 0.5, 2 and 12 — because clearance shrinks the
retained pool that conditions the illness draw. A2 is already ~1.8x low; this
would deepen the miss.

Two further points on the proposal, recorded so they are not rediscovered.
Calibration is not optional: a bolus accrues total hazard `r_rate * D / lambda`,
so keeping the single-bolus response equal to the fitted beta-frailty form
requires `r_rate = r * lambda`, and without that rescaling the parameter
silently multiplies all infectivity by `1 / lambda` — an unlabelled fit knob on
the dose-response itself. And a zero default is not behaviour-preserving under
that formulation: with no decay the pool accrues hazard indefinitely, returning
attack rate 0.42-0.45 against the correct 0.318.

What remains open is any mechanism nonlinear in delivered dose: host-level
exposure heterogeneity as near-field physics, cooperative or multi-hit
establishment (the aggregate/packaging picture), or clearance that is itself
induced by exposure. Clearance remains the right description of the inoculum's
fate and worth parameterising from the literature per pathogen; it is not the
resolution of A1/A2.

## 9c. Route-specific clearance: a real correction that is not the missing mechanism

Literature-derived pre-establishment clearance rates arrived resolved *by route*
rather than as the single pathogen-wide scalar the specification asked for. That
distinction matters, and it cuts both ways.

A single `lambda` is a no-op for infection (§9b). A route-varying `lambda` is
not: with a separate retained pool per route, a delivery `D_j` accrues total
hazard `r_rate * D_j / lambda_j`, so per-virion infectivity goes as
`1 / lambda_j`. Clearance therefore *derives* the route efficiency multiplier
instead of assuming it, and the mean residence time `1 / lambda_j` converts a
rate into a survival fraction without needing a separately supplied portal
residence time.

Calibration is forced, not chosen. `alpha` = 0.111 and `beta` = 32.81 were
fitted to *administered oral* Norwalk inoculum, so every loss between mouth and
gut epithelium is already inside `r`. The oral route is the reference and
`r_rate = r * lambda_food`; any other choice multiplies all infectivity by a
constant. Under the supplied norovirus rates that gives per-virion efficiency
1.00 for food, 0.50 for direct contact and fomite, and 0.071 for droplet and
HVAC — a 14-fold discount on the route carrying 94-95% of our establishments.
Simulation reproduces the closed form to within 0.7%
(`telemetry_buffer/observation_model/route_clearance_efficiency.py`).

**Consequence 1: every fitted dose is withdrawn again.** All doses quoted so far
are referenced to efficiency 1.0 on all routes. At fixed delivered dose the
droplet-dominated mix we actually produce gives infection attack rate 0.147
against 0.319 for a pure-oral exposure, so the fitted dose rises by roughly
6.6x. This is a change in what "dose" means, not a retune.

**Consequence 2: it does not resolve A2.** Dose is the one fitted parameter, so
the fair comparison holds infection attack rate fixed. Rescaled to attack rate
0.318 at hourly delivery, ill/infected moves from 0.315 (pure oral) to 0.322
(emission weights) to 0.336 (droplet-dominated) — a 7% relative gain against a
~1.8x miss. Within a route the hazard is still linear in delivered dose, so
re-weighting routes rescales the fitted dose and little else.

**The largest single effect rests on the weakest number, and the portal is
mis-assigned.** `lambda_droplet` = 0.7/h is grade C, annotated "respiratory
clearance proxy". Norovirus does not replicate in the respiratory tract:
aerosolised virus deposits in the oropharynx and is swallowed, establishing in
the gut, so the physically correct rate for that route is the oral one. Re-assign
the portal and the efficiency spread collapses to at most 2x and the correction
becomes nearly inert for us. Two grade-C numbers differing 14-fold, selected by
an unstated portal assumption, is a fit knob until that assumption is stated and
defended. The open question is not the value of `lambda_droplet` but which
portal norovirus droplet exposure terminates at.

**A double-count to avoid when the enteric bacteria are added.** A separate
`gastric_survival_fraction` is mechanistically right and is inert for norovirus
(value 1.0, acid-stable). But dose-response constants fitted to *ingested
challenge* doses — norovirus (Teunis), Campylobacter (Black 1988), Vibrio
(Cash 1974) — already contain gastric survival. Applying a survival fraction of
0.01-0.1 on top of such a fit discounts the same loss twice. The fraction is
valid only against a dose-response referenced to the dose arriving at the
epithelium, or as a *relative* modifier for hosts whose gastric pH differs from
the challenge-study population.

## 9d. The role asymmetry (A5) is blocked by the same route defect

VSP puts passenger attack rates at 5.7-6.9% against crew 2.0-2.4%, a ratio near
2.9 that holds on both sides of the COVID break. The model returns roughly
parity, and it does so at the *illness* level (ever-ill ratios 0.94-1.15 at the
fitted dose), not merely in reporting — so this is not an observation-layer
defect. Nothing in the sick-call path reads role; the only role-aware
surveillance is an optional crew screening pass that can only add crew reports.

The cause is that 94-96% of establishing dose arrives by droplet, a per-zone
aerosol pool that every occupant draws from on the same terms. The routes that
carry role structure — who you touch, which mess you eat in, whose cabin you
share — are the ones delivering nothing. Total fomite dose over a classic
voyage is 0.13 particles against 7.0e7 for droplet, a factor of about 6e8, and
the factor is arithmetic: a 1e-4 surface deposition fraction against droplet's
0.05 at emission, then a pickup step that spreads surface mass over the zone's
whole deck footprint (`zone_volume / 2.5`) and samples a 2e-4 m² fingerpad from
it, at 0.1 touch events per epoch. Norovirus contaminates touched surfaces of
order 1-10 m², not 400 m² of floor, and hand-to-surface contact is two to three
orders more frequent than that; there is also no hand-to-mouth step at all.

The model therefore behaves as a set of well-mixed rooms with a schedule
decoration. That is sufficient for a hull-size gradient and an epidemic curve
and insufficient for any role, venue or food-handler structure. Restoring the
route magnitudes is necessary for A5, not shown to be sufficient: uniform
`immune_ratio` across a resident crew and a weekly-turnover passenger cohort is
itself an assumption, and crew presenteeism and mandatory occupational
reporting are absent in both directions. The route constants must be fixed on
physical grounds with sources, not fitted to 2.9. Detail:
`telemetry_buffer/observation_model/a5_role_asymmetry_diagnosis.md`.

## 9e. The fomite chain rebuilt from measurements, and the first out-of-sample test

The §9d magnitudes were re-derived rather than rescaled. Detail:
`telemetry_buffer/observation_model/fomite_food_rederivation.md`.

Two findings came out of the derivation before any code changed. First,
`dose_adjustment` is not a calibration constant: the shedding curve is log10
copies per *gram of stool*, and `10^(curve − adj)` is an absolute amount, so
`adj` is `−log10` of the grams of stool released to the environment per epoch.
At the default of 4.0 it asserts 0.1 mg per shedder per hour. It has been
renamed to say so, with the old key kept as an alias. Second, the fomite
discount was applied twice — a 1e-4 deposition fraction at emission and the
0.30 route weight at delivery — doing the same job in two places.

The replacement is the standard fomite QMRA chain with a per-agent hand
compartment: shedder hand load anchored to Liu et al.'s 3.86 log10 copies per
hand from the Norwalk challenge study, hand-to-surface and surface-to-hand
transfer at Julian et al.'s efficiencies, hand-to-mouth at Rusin et al.'s,
contact frequencies from Wilson et al.'s 199-adult public-venue observations,
and a high-touch surface area of 1.5-10 m² by zone class in place of the
400 m² deck footprint. Hands decay fast (0.61-1.7/h) and surfaces slowly
(0.0048-0.013/h); the existing `surface_decay_per_day: 0.25` sits mid-range in
the literature interval and was left alone. Hand hygiene is implemented with
efficacy from the same source but a rate defaulting to zero, so the change is
an upper bound with respect to hygiene rather than a guess at compliance.

Two quantities remain declared rather than measured — shared-surface contact
frequency and the per-zone high-touch areas — and both are Grade C and swept
rather than asserted.

**The first out-of-sample test this model has faced returned a split verdict.**
Park et al. (2015) swabbed a cruise ship during a norovirus outbreak: 80-31,217
copies per swab in sick passengers' cabins against 16-113 in public spaces.
Nothing here was fitted to that. The corrected chain predicts 1,434 and 59
copies/swab at plausible occupancy — both inside the observed ranges, across
1.5 orders of magnitude, from constants assembled entirely from independent
studies. That is a real result and it deserves a discount: shedder-hours per
zone is a free input, and the public prediction slides from 59 to 1,190 across
its plausible range, so the check constrains the chain to about a factor of 10
rather than pinning it.

The gradient is the part occupancy cannot move, and it fails. Predicted
cabin/public ratio 4.0× against an observed 100-300×. The emission scale and
transfer efficiencies cancel out of a ratio, leaving a structural 1.33× times
the shedder-hour ratio, so reaching 100× would need a cabin to accumulate 75×
more shedder-hours than a public lounge — the real ratio runs the other way.
No adjustment to any Grade C declaration can produce it.

That failure is diagnostic. Park's sick-cabin loads are the signature of direct
emesis and faecal deposition in a small bathroom, not of contaminated hands on
a door handle. Every route the model has is continuous in time and proportional
to shedding; a vomiting event is discrete, enormous and spatially concentrated,
in exactly the zone class where a sick passenger is confined. §9d asked why role
structure cannot appear and found the routes carrying it deliver nothing; §9e
asks why sick cabins are not hotter than lounges and finds the same absence of
concentrated, localised deposition. Detail:
`telemetry_buffer/observation_model/park_surface_findings.md`.

None of this is validation. It says the fomite route is now in the right
numerical territory to be worth testing, which at 0.13 particles per voyage it
was not, and it says nothing yet about A1-A5.

## 9f. The contact layer re-derived, and the fitted scalar's second passenger

Two unsourced constants in different mechanisms, both low by about a decade,
both absorbed by the same fitted parameter. Corrected together in #353, because
splitting them would have attributed the correction to whichever landed first.

**Shared-surface touch rates.** `PUBLIC_SURFACE_CONTACTS_PER_HOUR = 6.0` and
`CABIN_SURFACE_CONTACTS_PER_HOUR = 2.0`, the two Grade C declarations §9e left
outstanding, were replaced by a zone-class table: cabin 17.9/h (Yuan et al.
2024, dormitory primary shared surfaces), public 21.0/h (Ackerley et al.
2023/2025, hotel lobby), dining 42.8/h and galley 545.4/h (Jin et al. 2022,
restaurant diners and staff respectively). These are shared-surface rates, not
all-surface rates: the studies separate touches of one's own belongings from
touches of shared fomites, and only the latter drive fomite transmission.
Taking a study's headline all-surface figure instead would overstate the route
substantially, which is a definitional error rather than a magnitude one and is
easy to make.

The last two are the same study, setting and hour, differing only in what the
person was doing: staff touch shared surfaces 12.7x more than diners. Touch
rate is a property of the activity, so crew in a service zone take the staff
rate, reusing the `_service_zones` set that `_effective_contacts` already uses
for `crew_contact_multiplier`.

**The inherited Korkin contact kernel.** `AVG_R_POOL` averages 1.333
contacts/day against POLYMOD's 13.4 (Mossong et al. 2008). §10 recorded this as
unresolved and `docs/density_contact_spec.md` had already concluded the
inherited kernel should be rejected; it never was, because
`base_contacts_per_day = 13.4` applied only to `density_dependent` and
`heterogeneous_zone_dose` while the shipped default `per_partner_contact` fell
through to the pool. **The shipped model had been running at 1.33 contacts/day
throughout the effort.** `per_partner_contact` now draws
`Poisson(POLYMOD_CONTACTS_PER_DAY per epoch)`, which is exactly
timestep-invariant rather than invariant in mean only. `legacy` is unchanged.

**Measured, not fitted.** Park's cabin/public gradient moves 4.02x -> 14.5x and
the shedder-hour asymmetry needed to reach 100x by hand transfer alone falls
from 75x to 29.3x. Still short, and the §9e conclusion is unchanged: the
residual is where people vomit. Cabin loading rises 1,434 -> 5,571 copies/swab
and public 356.9 -> 384.9, both still inside Park's observed ranges.

The deposition clamp `min(hand, n·f·e·hand)` now binds: reachable from 4
contacts/h in the tail, mean crossover at ~31.9/h, binding on 19.9% of draws at
21/h, 35.5% at 42.8/h and 88.5% at the 545.4/h service rate. So the fomite
route is superlinear in touch rate at the low end and saturates at the high
end, and the galley rate does far less than its 90x nominal increase suggests —
a galley worker's hands turn over completely every hour and cannot deposit more
than they carry.

This is expected to push A5 *further* from 2.9, since crew work the
highest-rate zones and their berthing is already denser. That would be a
finding about what is still missing, not a reason to revisit the constants.
Every dose figure is withdrawn again: the fit was against a contact layer that
no longer exists.

## 9g. Surfaces that nothing ever cleaned, and why cleaning them hurt

Until #355 no mechanism in the model removed pathogen from a surface except
natural inactivation at 0.25-0.50/day. A cruise ship that never cleans anything
is not a modelling simplification; it is a missing process, and it had been
absorbed into the same fitted dose the last three sections withdrew.

The cheap implementation is a single coverage-weighted reduction on the whole
surface pool, which is the recurring defect of this effort in a new costume:
replacing a concentrated, spatially heterogeneous process with a well-mixed
mean. Carling et al. 2009 measured what actually happens — a covert
fluorescent-marker audit of 8,344 objects in 273 public restrooms on 56 cruise
ships found **37% cleaned daily** (95% CI 29.2-45.4%, range 4-100% by ship) —
so 63% of high-touch objects are not reached at all. Averaging over that gives
every object a small daily reduction and drives the pool towards zero on a
long enough voyage; the measurement says a persistent reservoir survives
indefinitely on the objects housekeeping skips.

So the surface pool is now two compartments, cleaned and missed, per zone per
pathogen, with the aggregate `surface_pools` preserved as their sum so every
existing reader and dose path is unchanged. A routine pass is a discrete event
fired off a `SimClock` day-fraction accumulator (one pass/day, exactly one
event per epoch under the legacy epoch-is-a-day clock) that multiplies **only**
the cleaned compartment by 10^-1.29 — the midpoint of the two definition-matched
measurements available, 1.0 log10 for a single soap or 250-ppm-chlorine wipe of
hNoV on steel (Tuladhar et al. 2012) and 1.57 for targeted wipes and sprays
tracked with a viral tracer in a hotel lobby (Spitzer et al. 2025).

Outbreak response is a separate method, not a stronger setting of the same one:
detergent preclean then 5,000 ppm hypochlorite, 1.29 + 3.0 = 4.29 log10 (Park
et al. 2011; Escudero-Abarca et al. 2022), over a coverage of 0.58 that nests
the routine 37% and reaches (0.58-0.37)/(1-0.37) = one third of the objects
routine cleaning misses. Both the log10 additivity and the 0.58 are Grade C and
recorded in §10. The old fractional knobs `surface_decontamination_factor`
(0.4/0.5/0.6 across SOP-003/010/016, three different physical claims about the
same procedure) and the never-read `surface_decay_rate_override` are deleted,
not aliased.

**Measured, not fitted, and it went the wrong way.** Park's cabin/public
gradient falls from 14.5x to **11.2x**. Cleaning removes proportionally more
from a quiet cabin (pool x0.74, continuous loss 0.029/h) than from a busy
public zone (x0.96, loss 0.33/h), because in the public zone hand pickup
already clears surfaces faster than a daily pass can. Cabin loading 5,571 ->
4,120 copies/swab, public 384.9 -> 368.0, both still inside Park's observed
ranges. Real ships clean cabins and public spaces on different schedules with
different products, and that asymmetry is the obvious candidate — but no
measurement of per-zone-class frequency was found, so it is left as ledger
§4.1 rather than chosen to close the gap. The §9e/§9f conclusion stands: the
residual is where people vomit.

## 10. Parameters held fixed by assumption

These are not identified by anything in the fit, and any of them could move the
reported rate. They are listed so that "one fitted parameter against six
anchors" is not read as a stronger claim than it is; the system is
over-determined *given* these.

- Route weights (contact 0.35, fomite 0.30, food 0.20, droplet 0.10, HVAC 0.05):
  assumed, not traced to a source.
- Direct-contact transfer fraction: implicitly 1.0, where a contact-model
  anchor in the literature is ~0.25, and contact is the largest dose route.
- ~~Contact rate: Korkin 1.33/day against POLYMOD 13.4/day. Unresolved.~~
  Resolved in #353 (§9f): `per_partner_contact` now draws Poisson at POLYMOD's
  13.4/day. Raising it was not equivalent to raising dose, because it changes
  the variance that produces the intermediate outbreak regime — which is why
  the fitted scalar could absorb it without the error becoming visible.
- Per-zone high-touch surface areas (`HIGH_TOUCH_AREA_M2`, 1.5-10 m² by class):
  no study has ever measured high-touch surface area per room in m². Permanent
  Grade C. It is the denominator of the fomite pickup model.
- The fraction of a host's vomiting episodes occurring in its own cabin:
  unmeasured, swept rather than asserted, and not a model parameter (§9f, and
  `telemetry_buffer/observation_model/park_emesis_findings.md`).
- Confinement attenuation factor 0.05.
- The 20% innate non-susceptible ceiling, which is why infection attack rate
  pins at exactly 0.800 and why the fit must be read on reported cases.
- `shedding_variance_log10` = 1.0: literature-anchored, but to a range.
- Outbreak-response cleaning coverage 0.58 (§9g): no shipboard measurement
  exists; carried over from a 34%→53% supervision-and-feedback effect in two
  hospitals (Murphy et al. 2011) applied to Carling's 37%. Sweep, never assert.
- Log10 additivity of preclean-then-hypochlorite (1.29 + 3.0). The field
  reports two-step efficacy that way; the composition is not measured.
- One housekeeping pass per day, uniform across zone classes: the denominator
  of Carling's "cleaned on a daily basis", not an observed schedule.
- Newly deposited surface mass splits between cleaned and missed compartments
  in proportion to coverage — shedders are assumed to touch reached and missed
  objects alike. If soiling concentrates on the objects housekeeping skips, the
  surviving reservoir is larger than modelled.

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

Eleven distinct unit, dimension, time-origin, sign or state-scoping defects were
found in this effort, the first eight by chasing an anomaly rather than by a
check that would have caught it, and every campaign before v4 was invalidated by
a defect discovered after it ran. The ninth (§9a) is the only one found by
reading a specification against the code rather than by an anomaly, which is an
argument for more of that and not evidence that the rest are gone. The tenth
(§9d, the fomite and food pickup magnitudes) was found by asking why a
role asymmetry could not appear, which is the same pattern: an anchor failure
led to a defect nobody was looking for. The eleventh (§9e, the fomite route
discount applied twice, once as a deposition fraction and once as a route
weight) was found while re-deriving the tenth, which is the ordinary way
defects are found: by rewriting the code rather than by reading it.

Two things from §9e belong here rather than in the count. `dose_adjustment`
being grams of stool per epoch wearing a calibration constant's name is a
semantics defect, not a numeric one — the arithmetic was self-consistent and no
result changes — but it meant the one fitted parameter had no interpretation for
the entire effort, and nobody noticed until a joke about fomite transfer
prompted the dimensional check. And the replacement hand compartment shipped
with a timestep-dependent steady state, the same class of defect as §9, caught
in review before it landed. The base rate applies to new code too.

The twelfth (§9f) is the contact layer: two unsourced constants, in unrelated
mechanisms, each about a decade low, both absorbed by the same fitted scalar.
One of them — the Korkin kernel — had been recorded as a known discrepancy in
two separate documents for weeks without being acted on, which is its own
lesson: writing a defect down is not fixing it, and a documented-but-live defect
is more dangerous than an unknown one because it reads as handled. It was found
not by a check but by a joke about fomite transfer prompting a dimensional
audit, then by asking what else the fitted scalar might be covering for.

Guards now cover naked epochs, dose-pathway dimensions, reservoir
conservation, per-capita invariance to occupancy, cross-clock equivalence of
per-day quantities and epoch-invariance of the dose-response. The audit is not exhausted, and the correct prior is that
further defects exist. Absence of a further finding is not evidence of
correctness.

## 9h. The COVID discontinuity was not the discontinuity we had been quoting

The ledger's instrument for the NPI lever was "passenger attack rates fell
15-20% across the 2020 break, p=0.032, while crew rates held still". That
sentence was read off `docs/norovirus/vsp_covid_discontinuity.png`, an operator-supplied
figure whose per-outbreak table had never been in the repository, so no number
in it could be checked. Rebuilding the table was supposed to be bookkeeping
before the refit. It was not.

**The extraction found two defects in itself before it found anything about
norovirus**, and both are the same defect class the rest of this document is
about: a check that passes on data that is wrong.

The first was a column misalignment. CDC's outbreak index publishes 2023 and
2024 in a seven-column table — it inserts `Voyage Number` between `Sailing
Dates` and `Causative Agent` — while every other year uses six columns. A
parser binding columns by position therefore read voyage identifiers as
causative agents for 32 of the 68 postings in the entire post-COVID arm:
`j301`, `eu241230`, `sn240331016`. Five consistency checks passed on that file,
including a printed-percentage check, because the counts were in the last two
columns and were read correctly; only the agent moved. What surfaced it was a
descriptive quantity nothing was scored against — the norovirus fraction read
exactly 0.00 in 2023 and 0.00 in 2024, sitting between 0.80 in 2019 and 0.78
in 2025, and a fraction of zero is not a thing that happens to norovirus on
cruise ships. The lesson is not "bind by header", though the parser now does
and now fails loudly on an unrecognised header. It is that the unscored
descriptive series earned its place: it was the only quantity in the report
capable of being visibly absurd.

The second was the source of record. The first extraction took 1994-2019 from
`web.archive.org` snapshots of a retired CDC page. CDC in fact hosts its own
archive, and two pages there carry 1993-2018 and 2019-2022 as single tables
with the counts inline. Repointing at those made the provenance defensible,
recovered the 2020-2021 postings that the snapshot lacked (an era with no rows
is indistinguishable from an era with no outbreaks), and left the snapshot as an
independent cross-check: 428 rows, seven count disagreements between the two
paths, all logged with both URLs. CDC's own `Data not available` for every
outbreak through 2003 is now recorded as the sentinel it is, rather than
counted as 91 parse failures.

**Then the measurement contradicted the claim it was built to quantify.**
Passenger medians barely move across the break: 5.39% to 4.91%, a ratio of
0.912 (0.788-1.182, p=0.26). There is no detectable level drop, and the 15-20%
figure is withdrawn. What is there instead is three things the level statistic
had hidden:

- the crew median *rises*, 1.365x (1.004-1.677, p=0.007), so the
  passenger-specific component — the passenger shift over the crew shift — is
  0.668 (0.532-0.907, p<0.001);
- about half of that crew rise is fleet composition rather than crew behaviour.
  Post-2020 postings include small expedition vessels, several below VSP's own
  100-passenger posting criterion, whose crew denominators are a few hundred;
  holding composition fixed at 1000+ passengers leaves the crew ratio at 1.211
  (0.846-1.561, p=0.098) and the passenger-specific component at 0.736
  (0.581-1.053);
- what actually disappears is the upper tail. On ships carrying 1000+
  passengers, 11 of 226 pre-2020 postings exceeded 15% of passengers ill and 0
  of 48 post-2020 do, the worst posting falling from 25.2% to 13.5%. Fisher's
  exact test gives p=0.22 on counts that sparse, so this is direction, not
  evidence, and it is recorded as descriptive for exactly that reason.

This matters for the refit in a way a smaller number would not. A model that
matches the passenger-specific shift by lowering every voyage uniformly and a
model that matches it by removing the tail are different models with different
mechanisms, and the level anchors cannot tell them apart. It also removes the
premise for the passenger-facing-sanitation story as it was stated: crew rates
did not hold still, so a post-2020 configuration that leaves the crew arm
untouched contradicts the data rather than matching it.

The statistic itself came within one design revision of asserting the opposite
with false confidence. The upper-tail ratio was originally scored with a
percentile bootstrap; with no post-era posting above the threshold, every
resample returns a tail share of zero, the interval collapses to [0, 0], and it
excludes 1 — a decisive tail collapse on the evidence of nothing at all. It is
now reported as counts with Wilson intervals and an exact test, and the
degenerate case is a regression test.

## 9i. Per-zone cleaning was swept, not fitted

PR #355 made routine housekeeping a discrete pass over separate cleanable and
missed surface compartments, but its coverage and one-pass-per-day frequency
remain uniform across zone classes. The open question was whether a measured
schedule could replace that uniform pair. A search found no measured
cleaning-frequency schedule differentiated by zone class in an accommodation or
passenger-vessel setting. The implementation therefore exposes an optional
per-zone-class schedule and evaluates it only as the sourced envelope described
in
[`cleaning_schedule_sweep_spec.md`](../../telemetry_buffer/observation_model/cleaning_schedule_sweep_spec.md).

The frequency bounds are 0.33–1.0 events/day for cabins, 1.0–12.0 for public
zones, and 1.0–6.0 for dining, galley, and crew-mess zones. The coverage bounds
are 0.336–0.600 for cabins, 0.292–0.454 for public zones, and 0.292–0.600 for
dining, galley, and crew-mess zones. Boone et al. 2025/Gerba 2025, Carling et
al. 2009, Zhang et al. 2024, Ge et al. 2020, and McKinley et al. 2022 are
retained as the named sources and the spec distinguishes measured practice
from modelled optima and analogues. Zhuang et al. 2023 and Odoyo et al. 2021
were intentionally not used as bounds. Carling's Grade A 37% is a measurement
of public restrooms on cruise ships; applying it to cabins is an unsourced
extension.

Two independent mechanism findings support retaining the explicit process
without supplying a fitted schedule. Lei et al. 2017's MRSA ODE model found
that even daily whole-room cleaning at 100% efficiency leaves substantial
transmission when surfaces recontaminate rapidly, agreeing that a daily pass
cannot hold down a fast-recontaminating zone. Park et al. 2019 found higher ATP
readings and counted high-touch surfaces in hotel guestrooms than in public
areas, independently supporting the sign of the cabin/public contamination
gradient in a hospitality setting.

The sweep reports the minimum and maximum hand-only gradient over the fixed
cabin/public 81-cell grid and leaves the uniform shipped default alongside it.
That envelope is 8.6635–18.5054x versus 11.1977x for the default: it bounds
schedule leverage at roughly 1.65x upward, rather than testing whether a
schedule can reach Park, because Park already showed the hand-transfer channel
unreachable at any occupancy. The Park comparison is made by adding the
emesis term and evaluating the same 81 cells at the separate, unmeasured
cabin-localization values f=0.50, 0.80, 0.95, 0.99, and 1.00. The
emesis-inclusive gradient envelopes are respectively 3.01078–6.43105x,
10.8563–23.1892x, 39.5985–84.583x, 94.0539–200.9x, and
139.893–298.813x; 0, 0, 0, 78, and 81 cells respectively fall in Park's
100–300x range. The uniform-default gradients at those f values are 3.89146x,
14.0319x, 51.1815x, 121.566x, and 180.813x. Neither f nor any schedule cell
may be read back into the model or adopted as a parameter value. A future
measured per-zone-class schedule may narrow the bounds, but the no-selection
rule remains.

## 9j. PKG-02: the container ran a different model, and said nothing

Seed-level Morris sharding (#457) was validated by comparing a merged AWS screen
against a local unsharded screen on the same design seed. They differed in 55
raw effect entries. Local sharded and local unsharded output were identical, and
two independent AWS submissions were identical to each other, so the pooling
arithmetic was exonerated in both directions and the difference had to be in the
execution environment.

It was. `deploy/aws/Dockerfile.design`, `deploy/aws/Dockerfile.analysis` and the
root `Dockerfile` copied `data/` and `schemas/` but never `presidio/data/`, so
the class-interaction matrix, the information-diffusion configuration and the
global-health timeline were absent in every image. `DecisionRuntime.from_run_spec`
resolved each of those with an `os.path.isfile` test and simply skipped the load
when the file was missing, leaving an empty `ClassInteractionMatrix`, a default
diffusion engine and an empty timeline. The Stackelberg social layer therefore
ran degraded, and the run reported success.

The isolating test was to copy the deployed image's `/app` tree next to the
checkout, diff it, and then delete `presidio/` from a local copy: the resulting
per-epoch trace is md5-identical to the container trace
(`70008e84b83f5f8a5eb9539b60222215`) while the intact checkout gives
`6ae534de2d82be4146915bb951b2f043`. Restoring or removing platform PNGs, deck
GeoJSON, generated telemetry and the ContamX assets changed nothing, and the
image matched the checkout on model code, NumPy version and architecture. After
the repair the image reproduces the local trace exactly.

Two things follow. First, the divergence appeared at epoch 147 in operational
state and epoch 160 in infection state, which is why it read as noise rather
than as a missing subsystem — a silent default is at its most dangerous when it
is nearly right. Second, an absent input is now a `FileNotFoundError` naming the
path, for the agent-profile bundle as well: the runtime no longer has a mode in
which the same run spec means two different models. Any figure computed in a
container before this change is withdrawn in the open ledger, including the
20-shard `bounded_design_v1` screen, which completed operationally with zero
failed children and must nonetheless be re-run.
