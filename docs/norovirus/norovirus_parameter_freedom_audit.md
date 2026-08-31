# Norovirus parameter freedom: what is still free, and what is off-source

Status: audit, 2026-08-30. Supersedes nothing; it is the inventory behind
`docs/norovirus/norovirus_model_history.md` §10, taken after #351, #352, #353, #355 and
#358 and after the finding that `environmental_faecal_release_log10_g_per_epoch`
no longer moves the attack rate.

## 1. Why this exists

The model used to have one calibration knob per pathogen and several anchors, so
the knob absorbed every mechanism error underneath it. Five mechanism changes
later, the knob is inert: at dose 8 and above, the emesis-fed fomite pool
dominates so completely that a 14 log10 change in faecal release produces
byte-identical output (§2). That is the intended direction of travel — more
measured mechanism, less fitting — but it raises the question this document
answers:

1. Which parameters currently in use are set **away from** an available
   literature value?
2. How many free parameters remain, and where do they act?

The second question matters more than it looks, because a free parameter that
acts on the *observed* quantity is worth more fitting leverage than one that
acts on biology. VSP scores a reported attack rate, and the map from infection
to reported case is almost entirely assumption (§4).

## 2. The dose knob is inert, and the reason is measured

Route attribution at seed 500, `expedition_cruise_450`, 168 epochs, comparing
`environmental_faecal_release_log10_g_per_epoch` 10 against 24:

| Route | Summed pathway dose, release 10 | release 24 |
|---|---:|---:|
| fomite | 320,318.86 | 320,318.86 |
| direct_contact | 13.22 | 0.00 |
| droplet | 0.01 | 0.00 |
| food, hvac_airborne | 0.00 | 0.00 |

185 of 185 infections were fomite-dominant in both runs. The fomite pool is fed
by emesis deposition (`volume x emesis_titre_gec_per_ml`, #352), which does not
read the faecal-release term at all; faecal release is numerically comparable to
the emesis pool only below about 8, which is why release 4 and 6 still moved the
attack rate (0.484, 0.370) and 10 through 24 did not (0.377 throughout).

The emesis constants are Grade B measurements (Kirby 2016 titre;
Tung-Thompson 2015 and Booth & Frost 2019 volume, aerosol fraction and
deposition footprint). So the dominant route is driven by measured quantities
and the calibration term is not. **This is not a defect to patch.** The term is
named faecal release and behaves like faecal release. What it means is that
"fit one common dose against the VSP class targets" no longer describes an
operation the model supports.

## 3. Parameters set away from an available literature value

These are the answer to question 1. Both push the attack rate **up**, and
neither was chosen to do so — they are inherited defaults that were never
revisited. Correcting them is not fitting, because the replacement value comes
from the source rather than from the target; but the correction must be made for
that reason and reported whichever way the anchor moves.

### 3.1 FUT2 non-secretor resistance is switched off in the profile actually used

`data/pathogens/active_profiles.json`, `norwalk_gi`:

```json
"innate_nonsusceptible_fraction": 0.0,
"nonsusceptible_mechanism": "none"
```

The same repository carries `norovirus_gii4` in
`data/pathogens/edison_10pathogen_profiles.json` with the literature value:

```json
"innate_nonsusceptible_fraction": 0.2,
"nonsusceptible_mechanism": "FUT2_nonsecretor"
```

The campaign uses the first one: `campaign_manifest.json` maps
`pathogen_configs.norovirus` to bundle `active_profiles`, id `norwalk_gi`. The
profile's own name is "Norwalk Virus (Norovirus GII.4)" and its genotypes are
GII.4/GII.17/GII.2, so GII.4 secretor dependence applies to it.

Two things follow. First, `docs/norovirus/norovirus_model_history.md` §10 lists "the 20%
innate non-susceptible ceiling, which is why infection attack rate pins at
exactly 0.800" as a live held-fixed assumption — that statement is false for the
profile the campaign runs, and the recent probe's unsaturated 0.377 floor is
consistent with the ceiling being absent. Second, two profiles for the same
pathogen disagree on a well-measured quantity, which is the condition under
which a correction silently fails to apply.

Caveat against over-correcting: 0.2 is the European non-secretor prevalence and
secretor dependence is strongest for GII.4. GII.2 and GII.17 are less
secretor-restricted, so a mixed-genotype profile arguably warrants something
below 0.2. That is an argument for sourcing the number properly, not for leaving
it at zero.

#### Measured size of the correction

Run as an override arm rather than a data edit, so the base profile was
untouched: `expedition_cruise_450`, syndromic surveillance, 168 epochs,
`n_init=5`, seeds 500-504, at faecal release 4 and 24. Medians over five seeds,
passenger:

| Arm | Release | Ever-ill AR | Reported AR | Infection AR range |
|---|---:|---:|---:|---:|
| 0.0 (shipped) | 4 | 0.1108 | 0.0348 | 0.152 - 0.326 |
| 0.2 (literature) | 4 | 0.0696 | 0.0190 | 0.142 - 0.206 |
| 0.0 (shipped) | 24 | 0.0475 | 0.0127 | 0.022 - 0.193 |
| 0.2 (literature) | 24 | 0.0190 | 0.0095 | 0.013 - 0.082 |

The override reaches the simulation: each `run_spec.json` records
`innate_nonsusceptible_fraction` 0.0 and 0.2 respectively, with
`nonsusceptible_mechanism: FUT2_nonsecretor` on the literature arm. The run
artifacts do not serialise the post-merge resolved profile, so this is
confirmation of the input, not of the resolved profile — worth fixing, because an
override that silently failed to apply would be indistinguishable from a small
effect.

Three things follow, and the third is the uncomfortable one.

1. Correcting to the literature value **cuts the ever-ill attack rate by 37% at
   release 4 and 60% at release 24** — far more than the 20% of hosts removed,
   because removing susceptibles also removes their onward transmission. This is
   not a minor provenance tidy; it is one of the largest single-parameter effects
   measured in the model.
2. The §10 claim that infection attack rate "pins at exactly 0.800" is not
   reproducible in either arm: infection AR spans 0.013-0.326 across these runs
   and never approaches the ceiling. That sentence describes a configuration the
   model no longer runs and should be struck.
3. **The correction moves the model away from the VSP levels, not toward them.**
   Ever-ill passenger AR is already 0.11 shipped against A1's ~0.154, and the
   literature value takes it to 0.07. So the answer to "is anything being held
   off its literature value in a direction that flatters the anchors" is yes,
   and removing the flattery widens the gap. That is a result and it is reported
   as one; it is not a reason to leave the parameter at zero.

What these runs are not: a VSP comparison. One 450-berth hull, five seeds, no
posting-rule filter, and outbreak response active throughout. They size the
parameter's effect; they do not score an anchor.

#### An open question this raised

Under `none_true` surveillance the faecal-release term was inert from 8 upward
(§2). Under syndromic surveillance, release 4 and 24 differ substantially in
both arms — consistent with §2, since 4 sits below the plateau, but the absolute
levels are three to eight times lower than the `none_true` probe at matching
release. Outbreak response is doing most of that work. Whether the plateau above
release 8 survives with response active has not been measured, and it should be
before the C1 ladder is declared flat in the configuration the campaign actually
runs.

### 3.2 Direct-contact transfer fraction is 1.0 against a literature ~0.25

`contact_transfer_fraction` defaults to 1.0 in
`engines/transmission_core.py` and the norovirus profile does not set it, so
every direct contact transfers the entire computed dose. §10 records the
contact-model anchor as ~0.25 and has done since before #353. #353 raised the
contact kernel to POLYMOD rates without revisiting the transfer fraction, so
contact is now sampled at a measured rate and transferred at an unsourced
efficiency.

This currently matters less than it reads, because direct contact contributes
13.22 dose units against fomite's 320,318 (§2) — but it will matter as soon as
the fomite pool is corrected, and it is off-source either way.

## 4. Free parameters that act directly on the scored quantity

This is the honest answer to question 2, and the count is worse than the
transmission-side inventory suggests, because the largest cluster sits in the
observation model rather than in the biology.

### 4.1 The observation model: about 15 assumed numbers, one aggregate constraint

`observation_model` on the norovirus profile carries three five-element vectors
plus a lab-sampling vector:

```json
"syndrome_case_eligibility_by_severity":             [0, 0.55, 0.98, 1, 1],
"reporting_probability_by_severity_pre_recognition":  [0, 0.45, 0.70, 0.94, 1],
"reporting_probability_by_severity_post_recognition": [0, 0.50, 0.76, 0.96, 1],
"lab_sampling_probability_by_severity":              [0, 0.05, 0.20, 0.60, 0.90]
```

`docs/norovirus/cruise_pathogen_severity_observation_priors_v2.md` §4.1 grades every one
of these `[A]` — assumption — and states the position plainly:

> With the default severity vector, the eligible symptomatic mass is about 0.50
> and the reported eligible mass is about 0.30. Their ratio is approximately
> 0.61, close to the empirical 0.60 constraint. **This decomposition is not
> identified by that study; many severity-specific vectors yield the same
> weighted fraction.**

So roughly fifteen assumed numbers are constrained by exactly one empirical
aggregate: the ~0.60 infirmary capture fraction from one cruise investigation
(Wikswo 2011). Every one of them scales the reported attack rate, which is the
quantity VSP is scored on. In fitting terms this is the largest remaining source
of freedom in the model, and it is the freedom least visible as such, because
each individual number looks like a clinical fact.

### 4.2 That single constraint is anchor A3, so A3 is not a test

The ledger lists A3 as "reported / ever-ill (infirmary capture), 0.60 +/- 0.05"
and scores the model against it. But the observation vectors were assembled to
reproduce ~0.61 against that same 0.60. **A3 therefore cannot be evidence that
the observation model is right** — passing it is a restatement of how the
vectors were chosen. It should be recorded as a construction constraint, not as
a scored anchor, and the anchor count reduced accordingly.

This does not touch A1, A2, A5 or A7, which are not constraints the vectors were
built against.

### 4.3 Route weights look like shares and are not

```json
"transmission_route_weights": {
  "direct_contact": 0.35, "fomite": 0.30, "food_contamination": 0.20,
  "droplet": 0.10, "hvac_airborne": 0.05, "environmental_source": 0.00
}
```

They sum to exactly 1.0, which invites reading them as route shares. They are
applied as six independent per-route multipliers on independently computed route
doses, so the realized share is whatever the mechanisms produce — measured at
100% fomite against a nominal 0.30 (§2). §10 already records them as "assumed,
not traced to a source"; the sum-to-one is the part that makes them a trap, and
any statement of the form "fomite is 30% of transmission in the model" taken
from this block is wrong.

Six free parameters, no source, acting multiplicatively on every route.

### 4.4 The rest, already declared

Carried from §10 and unchanged by this audit: `HIGH_TOUCH_AREA_M2` (permanent
Grade C, denominator of fomite pickup, never measured by anyone); the
cabin-localization fraction `f` (unmeasured, swept, and the binding uncertainty
for Park); outbreak cleaning coverage 0.58 (Grade C, sweep only); log10
additivity of preclean-then-hypochlorite (Grade C); one housekeeping pass per
day; the cleaned/missed deposition split; confinement attenuation 0.05;
`surface_deposition_fraction` 1e-4 and `surface_decay_per_day` 0.25 (no
provenance comment found); `shedding_variance_log10` 1.0 (anchored to a range,
not a value); and the declared `strain_evolution` placeholders
(`superinfection_susceptibility`, `recombination_rate_per_day`).

## 5. What is measured, and therefore not available for fitting

For completeness, because the point of the inventory is the ratio. Emesis titre,
volume, aerosol fraction and deposition footprint (Grade B); shared-surface
contact rates by zone class (Grade B, Yuan 2024 / Ackerley 2023 / Jin 2022);
POLYMOD contact rate (#353); routine cleaning coverage 0.37 (Grade A for cruise
public restrooms, an unsourced extension to cabins); routine and hypochlorite
log10 reductions (Grade B); beta-Poisson dose response alpha 0.111 / beta 32.81;
illness probability eta/gamma; incubation distribution (Lee 2013, with its own
documented dose-reference caveat); presymptomatic window (Atmar 2008); severity
vector (M/A); immune waning (Simmons 2013).

## 6. Consequences

1. **A dose refit is probably not available, but the negative result is not yet
   complete.** The term is inert above release 8 under `none_true` (§2). Under
   syndromic surveillance, which is what the campaign runs, only 4-versus-24 has
   been measured and the plateau has not been retested (§3.1). That measurement
   is cheap and it gates the C1 decision, so it should be taken before the arm is
   cancelled or submitted.
2. **Two corrections are owed regardless of what they do to the anchors** (§3):
   FUT2 non-secretor fraction, and contact transfer fraction. Sourcing them is
   provenance repair, not fitting, and the result must be reported in whichever
   direction it moves. For FUT2 that direction is now measured and it is
   unfavourable — ever-ill drops 37-60%, away from A1 (§3.1). The correction
   should still be made.
3. **The model may undershoot VSP rather than overshoot it.** Shipped ever-ill
   passenger AR on the 450 hull is 0.11 against A1's ~0.154, before the FUT2
   correction takes it to 0.07. Both off-source parameters in §3 are currently
   inflating the attack rate, so provenance repair and anchor agreement pull in
   opposite directions here. This is the situation the no-fitting rule exists
   for, and it is also the situation in which it is most tempting to break it.
4. **A3 must be demoted** from scored anchor to construction constraint (§4.2),
   which reduces the anchor count the model is actually tested against.
5. **The observation model is the model's real remaining freedom** (§4.1). If
   the model is to be scored against VSP honestly, those fifteen numbers need
   either independent sourcing or an explicit declaration that the reported-rate
   comparison is conditional on an assumed observation process — and in the
   latter case a sensitivity sweep over coherent scenario vectors, per the
   priors document's own instruction not to sweep components independently.
6. **Route weights should stop summing to one** or stop being called weights
   (§4.3), and the realized route shares should be reported from telemetry
   rather than read off the configuration.
7. **Run artifacts should serialise the resolved pathogen profile.** Override
   arms are currently verifiable only from the input `run_spec.json` (§3.1); a
   patch that failed to merge would be indistinguishable from a null effect.

## 7. Rules this audit does not relax

The measured constants in §5 are not candidates for adjustment because the
attack rate comes out wrong. It now looks more likely to come out low than high
(§6.3), which changes the direction of the temptation but not the rule: if the
model misses VSP after §3 is repaired, that is a result and it gets reported as
one. The failure mode this whole effort exists to correct was a fitted scalar
that kept the aggregate looking right while two order-of-magnitude mechanism
errors sat underneath it; substituting the observation model for that scalar
would be the same mistake with a longer parameter vector.
