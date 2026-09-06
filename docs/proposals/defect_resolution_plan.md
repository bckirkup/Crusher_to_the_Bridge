# The collective plan: sequencing every open construction defect towards one test

> **Status:** Proposed. This document specifies no mechanism of its own; it
> sequences work specified elsewhere. It moves to `history/` when the gate in §7
> has been run, whatever the gate returns.

## 1. Why a collective plan, and what it is for

The [parameter provenance register](../parameter_provenance_register.md) says
what is blocked and, in its §4, what change each blocked quantity needs. It does
not say in what **order**, and the order is not free: most of these items are
prerequisites of each other, and three of them invalidate work done before them.
One Morris screen has already been wasted this way — the pre-rebuild ranking in
task #36 was invalidated by a factor substitution that landed after it started.

So this plan is a dependency graph, not a list. It has one organising claim:

> **Almost nothing still open is blocked on the literature. It is blocked on
> fields that cannot express what is measured.**

Every item in the register's §4 has the same shape — the paper exists, the field
cannot take it. That is why the plan sequences by *structural prerequisite* and
not by pathogen, by parameter, or by how easy each item looks.

Everything terminates in one test, and the plan exists to make that test
meaningful rather than to make it pass. See §7.

## 2. The two classes of defect, kept apart

The list in §1 of the [norovirus ledger](../norovirus/norovirus_open_ledger.md)
mixes two things that need different work.

**Construction errors** — a number or mechanism that exists because someone
built it, not because anything measured it. These are found by reading the code
against the paper. Every one so far has been found that way, and none by
searching for a better number. They are fixed by a code change, and they cost
nothing to fix except the goldens they move.

**Unsourced values** — a field that is correctly shaped and honestly empty.
These are fixed by a search, which may return nothing, in which case the honest
outcome is a declared axis (as `never_symptomatic_fraction` now is: shipped with
no value, and enabling the channel is a load error until a sweep supplies one).

The distinction matters for sequencing because **a construction error can hide
inside a sourced value.** Three of them did: the emesis triple was three
individually-cited knobs for one measured quantity; `airborne_half_life_hours`
1.1 carried a citation to a paper measuring 2.7; and the length-bias mechanism
reviewed out of PR #388 would have promoted `chronic_shedder_fraction` from a
share of *immunocompromised hosts* to a share of *all infections* under a live
citation. Sourcing a field before its structure is right therefore does not just
waste the search — it launders the defect.

**Hence the ordering rule for the whole plan: structure before sourcing, and
sourcing before fitting.**

## 3. Track A — structure: fields that cannot express what is measured

Nothing else starts clean until this track is done. Its exit condition is that
the register's §4 no longer has an entry whose blocker is the shape of a field.

| | Item | Task | Why it is in this track |
|---|---|---|---|
| A1 | Host natural-history module | #49 | **Resolved.** The keystone; see below. Host natural history now has one owning module, `engines/natural_history.py`, and the extraction was behaviour-preserving — orchestrator output is byte-identical to its parent and no constant moved with it |
| A2 | `sars_cov2_resp` gets `shedding_duration_days` | #51 | **Resolved:** the arm carries `shedding_duration_days` 15 on the sourced RNA-positivity interval [10.8, 18.4], and `recovery_day` 7 still clears the illness, so the two clocks are separate. The field takes the **detectability** endpoint rather than the infectious one, because the curve it releases is a nasal RNA concentration; splitting *those* two clocks is a further structural item and is recorded, not fixed. The tranche-8 clock separation never reached this arm: shedding still clears at `recovery_day` 7 and 7 of 15 authored curve days are unreachable. Negligible for dose (0.02% of curve mass) and decisive for *detectability*, which is what the COVID arm is scored on |
| A3 | Symptom severity gets a trajectory | #48 | **Resolved.** Severity was drawn once at onset and held for the whole illness, so what an observer saw did not vary over the course — and observability is the quantity this model exists to predict. The onset draw is now the *peak* of the course and `severity_model.trajectory_ladder_offsets_by_day` says how far below it the host reads on each illness day, on the same onset axis as the shedding curve. The field ships absent on every profile, which holds the peak and is the previous behaviour exactly: what the path is belongs to Track C (#27, #31), and adopting one before the seam existed would have been sourcing a number no field could hold |
| A4 | Influenza `surface_decay_per_day` becomes a rate; `illness_probability` stops being dose-conditional | #44 | **Resolved, in two landed changes and one refusal.** Register §4 items 2 and 3. The Hill form could not express Carrat's dose *in*dependence, and R3 deleted it rather than sourcing 0.67 into η: both influenza profiles now carry `symptomatic_fraction` 0.669 and presentation is dose-independent. The fractional daily loss is gone too — R1 put every profile in both bundles on `surface_decay_log10_per_day`, the unit every source measures in. What remains of the surface row is not a field shape this track can fix: the axis the scalar cannot express is *time since deposition*, and [`surface_decay_biphasic_spec.md`](surface_decay_biphasic_spec.md) §7.1 refuses the biphasic form **on evidence** — the respiratory matrix a ship deposit resembles shows no wet/dry split at all. That is a shape question for #36 to make live before #60 answers it, not a structural prerequisite of Track B |
| A5 | Route efficiency vs. the clearance layer: pick one parameterisation | #25 | **Resolved.** Register §4 item 1. Six route multipliers and Edison's per-portal clearance layer parameterise the same object, so neither was identifiable while both could exist — a structural choice, not a search, and it was made in favour of the multipliers. `route_efficiency_multipliers` is the sole owner; a measured clearance rate is a *derivation* of it, `route_efficiency_from_clearance_rates` returning `λ_reference/λ_j` against a declared reference portal, so only the ratios enter and the absolute rate scale cannot rescale the already-degenerate dose axis. The schema and the loader refuse a clearance layer beside it — `pre_establishment_clearance`, `route_clearance_rate_per_hour`, `gastric_survival_fraction` — including at inert defaults, because shipping a layer at no-op is how it becomes live later. No value moved: the six numbers ship as before, and which portal a route terminates at is Track C's question (#27) |

**A1 goes first, and this reverses my earlier recommendation.** I argued for
doing the extraction *after* the symptom curve, on the grounds that pure
refactors of a state machine you are still adding axes to get redone. That
condition has expired. Host natural history has no owning module — the record
and the reads are on `KorkinAgent` in `engines/infection_dynamics_bridge.py`,
the transitions are in `orchestrator_epoch.py`, the consequences are in
`engines/transmission_core.py` — and PR #388 added a **fourth** writer in
`engines/initiation.py`. A2 and A3 each land in all four. The refactor is now
cheaper than the two changes that would otherwise straddle it, and the split is
not incidental to the defects: the clock and the curve came to disagree in #382
precisely because the transition that cleared illness and the read that selected
the curve lived in different modules with nothing owning "which curve is this
host on".

A2–A5 are independent of each other and can run in any order after A1.

**Track A is done, and the one thing it did not do was refused rather than
skipped.** A1, A2, A3 and A5 landed, and A4's two register items landed as R1
and R3. What survives is the influenza scalar surface-decay rate, whose remedy
would be the biphasic wet/dry form — and §7.1 of the spec refuses that form on
evidence, because the matrix a ship deposit resembles shows no wet/dry split.
A shape that the literature does not support is not a field defect this track
can repair; #36 decides whether the question is live at all. So the exit
condition holds in the sense that matters: no entry in the register's §4 is
waiting on a field a *sourced* number could not be written into today. The next
unblocked work is Track B.

## 4. Track B — anchors: what we are allowed to score against

This track defines the objective function, so **it must complete before any
fitting begins** — otherwise we discover what we are scoring against by seeing
what fits.

| | Item | Task | Depends on |
|---|---|---|---|
| B1 | Demote A3 from scored anchor to construction constraint | #23 | — (**resolved**, see below) |
| B2 | The observation model's ~15 numbers: source them or declare them | #27 | B1 (**resolved as a declaration**, see below) |
| B3 | Recut the A4 class bins | #29 | — (**resolved**, see below) |
| B4 | An external voyage denominator for VSP posting rates | #13 | — (**resolved as a declaration; the series stays blocked**, see below) |
| B5 | Measure or externally bound the cabin-localization fraction `f` | #12 | — (**resolved as an external ceiling; still no measurement and no lower bound**, see below) |

**B1 is resolved.** `score_anchors.py` scored A3 against 0.35–0.45 while its own
module docstring already called A3 a construction constraint, so the scorer was
testing the observation layer against a target that layer's capture and
eligibility parameters produce. A3 now sits in `CONSTRUCTION_BANDS`, is reported
beside the measured ratio as `in band (not scored)` or `out of band (not
scored)`, and enters no verdict — the verdict column is A1, A2, A4, A5, A8, A9.
Nothing was re-sourced and no interval moved; what changed is what the number is
allowed to mean.

**B1 before B2, because the two were circular.** Register §4 item 5: the
observation model's fifteen numbers are jointly constrained by a single
empirical aggregate, and that aggregate *is* anchor A3 — so A3 cannot also be a
test of them. Sourcing them while A3 was still scored would have been fitting to
the target through fifteen intermediaries. **B1 has landed, so B2 is unblocked**;
the band A3 is now reported against is a wiring check, and reading in-band as
agreement would restore the circularity the demotion removed. B4 and B5
are searches with no in-repo prerequisite and can run in parallel with Track A.

**B2 resolved on the second branch of its own title: declared, not sourced.**
The document these vectors come from,
[`../norovirus/cruise_pathogen_severity_observation_priors_v2.md`](../norovirus/cruise_pathogen_severity_observation_priors_v2.md),
grades every entry `[A]` — assumed prior — and states that the decomposition is
**not identified** by the one cruise investigation behind it, since many
severity-specific vectors give the same weighted fraction. There is therefore
nothing to source, and the alternative to saying so was choosing values against
the aggregate B1 had just stopped scoring. So the profile block now carries its
class (`C`, origin `Tr`), its origin, and the consequence in prose: the
reported-attack-rate comparison against VSP is *conditional* on this assumed
observation process, and agreement with a reported rate is not evidence the
fifteen numbers are right. Uncertainty travels as `observation_model.prior`, a
two-member `scenario_set` of whole ladders — the loader refuses a scenario that
moves one component, or one that sits beside a stale `active_scenario`, and
`bounded_screen.py` re-runs the design **per scenario** instead of ranging a
reporting probability over an interval, which would sweep a ladder no observer
could exhibit. No number moved: `base_reporting` is the shipped decomposition
unchanged, so orchestrator output is byte-identical.

**B3 is resolved.** It was a plain defect: A4's denominator is passengers, but
the bins compared `pax_total` against the platform ids, three of which name a
passenger-plus-crew total. Each hull now declares `nominal_complement` as a
passengers/crew split in its own `spatial_layout.json` (300+150, 1,350+560,
2,100+900, 5,000+2,000) and the band edges are the geometric means of the
passenger halves, so no edge is chosen and changing a complement moves them.
The recut moves anchor availability in both directions — the mega hull gains a
pre-2020 A4 anchor (4 postings became 16) and the classic hull loses its
post-2020 one (32 became 8) — which is a change in *which cells are scored*,
decided by a posting floor rather than by any result. Recorded here and repaired later (§10): the
hull-to-GRT mapping behind A8/A9 chose representative ships for the classic and
spirit hulls against the same total-agent figures, so their band was one band
too high.

**B4 is resolved as a declaration, and it resolves by making the gap explicit
rather than by closing it.** The search was already done and had already failed:
CDC publishes annual voyage counts for 2008–2014 only (Freeland 2016, in two
units — voyages required to report, and the 3–21 d / >100 pax subset analysed),
one pooled 2006–2019 total in a third unit (Jenkins 2021, unduplicated voyage
reports), and nothing at all after 2019. What was wrong was not the absence but
the silence about it: A9 divided by Jenkins's 37,258 with no unit or window
recorded, so a period average in voyage *reports* read as a voyage rate.
`midrs_incidence_targets.py` now declares that denominator's unit, window and
source in the target itself and in the scoring report, and
`vsp_voyage_denominator.py` carries the two Freeland series side by side, the
reason each uncovered year is uncovered, and the posting rate the project's own
numerator would give under each unit as a diagnostic **no anchor scores**.

Three findings that keep the row blocked in the register rather than clearing
it. The numerator is *posted* outbreaks against denominators CDC pairs with
*investigated* outbreaks, and the two definitions point opposite ways — 91
postings against 132 investigations in Freeland's window, 208 against 156 in
Jenkins's — so no ratio converts one into the other. Freeland's own printed
per-1,000-voyage rates are reproducible from Freeland's own counts for 1 of 7
years and fall outside the bracket its two units span in 4 of 7, which is why
both units are carried rather than either quoted — though the miss is small and
graded, not open-ended: `published_rate_residuals()` puts the printed rates on
the required-report column to within 4.8% on average and 8.5% at worst in six
of the seven years, with 2010 the lone material outlier (its printed 3.8 needs
~5,526 voyages, above either published count, so one of that year's three cells
is misprinted). The denominator is uncertain by about a tenth, not unknown; what
blocks the row is the numerator definition, not this residual. And the post-2020
arm has no published voyage count, so the discontinuity that arm exists to
measure is expressible only against a Grade C bracket built from CDC's
inspection census (below) — the class-composition observable of
[`fleet_emergence_decision.md`](fleet_emergence_decision.md) §3 remains the only
*measured* fleet statistic there.

**The numerator mismatch is nobody's task, so it is now somebody's request.**
None of B1–B5 owns it, and no literature search can close it: the posted count
runs 91 against Freeland's 132 investigated outbreaks but 208 against Jenkins's
156, so the ratio inverts and the two products are counting different events —
deriving a conversion from those two ratios would be choosing a definition to
make a rate come out. The only source that can answer is CDC VSP, which also
holds the missing annual years and the absent post-2020 count, so the question
leaves the plan as an external data request:
[`vsp_midrs_extract_request.md`](vsp_midrs_extract_request.md), which records in
advance what each possible reply does and does not license. Until it is answered
the row stays blocked as a *rate*; a reply that supplies counts but not the
posting criterion closes the denominator gaps only, and the remaining move would
then be to declare and sweep the posting step as an observation-model parameter,
never to fit it.

Blocked does not mean unquantified. `vsp_voyage_denominator.py` now carries the
disputed quantities as frozen intervals: the 2008-2014 denominators bracket both
published columns and the count each printed rate implies (one rule for all
seven years, so 2010's misprint widens that year rather than removing it),
2006-2007 and 2015-2019 take the union envelope [3,964, 5,527] as a declared
Grade C stationarity assumption, Jenkins's pooled total works out to 0.48-0.67
of a required-report voyage per year as a measure of the unit mismatch, and the
posting step is bounded to [0.53, 1.0] --- the observed 2008-2014 floor up to the
structural ceiling that a posting presupposes an investigation, with the
Jenkins-window ratio of 1.33 excluded because it violates that ceiling. Every
one of those is swept and none is centred.

Post-2020 is bounded where a fleet was there to measure and null where it was
not. The fleet term stops being an assumption: CDC's inspection query tool
covers every ship in VSP jurisdiction, and harvesting it month by month
(`vsp_inspection_series.csv`, 1,901 inspections of 248 ships, 2014-2026) gives a
census of 108-122 ships per year before the pandemic against 136/149/179 in
2023/2024/2025, so the same instrument measures both sides of the discontinuity.
Scaling the pre-pandemic envelope by those census ratios (1.17, 1.28, 1.54)
gives 2023 [4,640, 6,471], 2024 [5,084, 7,090] and 2025 [6,108, 8,517] --- Grade
C, because voyages per ship-year enters as a declared assumption and a ship
census is not a voyage count. 2020-2022 stay null: the record dates the pause
itself (last inspection March 2020, first resumed October 2022), and a census
taken while inspections were suspended measures the programme rather than the
fleet. The sources that would replace the assumption with a measurement ---
CruiseDig's paid historic itinerary extract, thecruiseglobe's in-app schedules,
and CDC's per-ship inspection and mitigation reports as a risk-factor dataset
--- are identified, unretrieved, and recorded in the request document so the
assumption stays visible as one.

**B5 is resolved on its second clause, not its first: `f` is externally
bounded, and it is still measured nowhere.** Tranche 17's search stands --- no
study on any ship reports the share of norovirus transmission occurring between
cabinmates, and the tighter empirical `f <= 0.18-0.45` is derived from the same
cruise attack rates A4/A8/A9 score against, so it cannot constrain a sweep those
anchors also score. What #12 adds is the missing external input to the one bound
that needs no epidemiology at all. The ceiling `f <= 1 - cabins/occupants` is
occupancy combinatorics --- every cabin's first case was infected elsewhere by
construction --- and it needs a berthing plan, which the operators publish: in
cruise-industry practice occupancy is passengers per *lower berth*, two per
cabin by definition, and Carnival's own note says percentages above 100% mean
more than two passengers occupied some cabins. So published occupancy *is*
occupants per two cabins, and `f <= 1 - 1/(2 x occupancy)`.

That moves the bound, and in the direction that matters: every published full
year since the restart is at or above unity (CCL 100% / 105%, RCL 105.6% /
108.5%), so the fleet-wide ceiling is **0.500-0.539** and 0.5 is its *floor*,
not the ceiling. The register's previous `f <= 0.5` was slightly too tight
rather than conservative, which is the kind of error a structural bound is
supposed to be immune to. Per hull the same identity runs off the declared
berthing plan instead: `default_cabin_size` puts passengers in doubles, crew in
triples and officers in singles, giving whole-hull 0.53-0.55, crew-only ~0.66,
passenger-only <=0.50, and *below* 0.5 for naval hulls with single cabins.
`cabin_localization_ceiling.py` computes all of it and returns nothing but
bounds: no lower bound (`f = 0` is not excluded), no central value.

B5 also found a name collision, which is why the Park harness changes in the
same item. The factor the sensitivity spec lists as "cabin-localization fraction
`f`, 0.80-0.99" is not this `f` at all --- it is the fraction of a symptomatic
host's *emesis episodes* that occur in its own cabin, an episode-location
fraction that nothing caps near a half, and it is a parameter of the Park
surface harness only. Under one name, its 0.80-1.00 range read as a claim about
transmission localization that sits entirely above the transmission ceiling. It
is now `EMESIS_IN_OWN_CABIN_SWEEP`, and a test asserts the old name is gone.

## 5. Track C — intervals: no scored parameter stays a point value

Task #35 is the umbrella. This track can start during Track A, but **adoption of
any interval lands after the Track A item that owns its field.**

> **All seven items are closed.** One adopted interval in the whole track
> (influenza's fine-aerosol share, C4), three declared-not-applied (C6, C3, and
> the SARS-CoV-2 half of C4), three refusals (C1 and C2 on evidence, C5 on
> identifiability), and C7's re-tests re-run. No constant moved except that
> adoption. **#54 is now closed too:** the campaign's index-case axis is re-keyed
> onto the boarding channel and `norwalk_gi` boards through
> `initiation.boarding` with `never_symptomatic_fraction` swept, not licensed. Two screen inputs changed under #36/#37: the #22
> row is withdrawn as aliased and the C6 dose span is declared, not applied.

| | Item | Task | Note |
|---|---|---|---|
| C1 | `never_symptomatic_fraction`, and migrate `norwalk_gi` off `initial_infected` | #53, #54 | Gates the boarding channel built in #388. Exclude outbreak-conditioned asymptomatic prevalence (18–22%) for the tranche-10 reason: it is conditioned on the outcome being scored. **#53 refused on evidence by [tranche 24](../literature/consensus_tranche_24_never_symptomatic_adult_null.md)**: the null is now twice-searched and structural — every adult natural-exposure design fails at the *denominator* (asymptomatic-only screening, AGE-triggered enrolment, or positive-specimen share, the last length-biased upward by convalescent shedding), so the two tranche-11 intervals stand unpooled and no value is licensed. **#54 blocked, not done:** the destination channel needs the refused coordinate, and the intermediate move — relocating the fiat index case into `initiation.explicit_seeds` — would silently override the campaign's swept `initial_infected` axis, since initiation ownership drops a pathogen from legacy seeding while the run id keeps the `init<N>` label. That collision is now a load error on both mechanisms rather than a silent one. **#54 resolved** (tranche 24 §3, resolution): the shipped `norwalk_gi` profile carries `initial_infected: null` and boards through `initiation.boarding` in `crusher_labs/config.yaml` — prevalence at the register-interval midpoints (passenger 0.0325 of [0.025, 0.040], crew 0.0185 of [0.007, 0.030]), `presymptomatic_share_of_presenting` 0.04 (derived), and `never_symptomatic_fraction` as a **swept axis in two unpooled regimes** (`adult_challenge` [0.22, 0.36] default for the mean-age-72.6 population; `community_cohort` [0.59, 0.68] available but never the default). The campaign's `sr*`, `vd*`, sentinel, calibration, variant and t6 sites drive `config_overrides["initiation"]["boarding"]` through `boarding_axis.py`, run ids carry the swept coordinate (`nsf<…>`, `bp<…>c<…>`, `psp<…>`) in place of `init<N>`, and a tier that still lists a count axis for an owned pathogen fails generation unless it declares `fiat_index_case: true`. Manifests that keep a deliberate fiat design (boundary surface, C1 dose arms, Paper 3, calibration v1) carry that flag so their existing count sweeps stay explicit rather than migrated silently. **Extended to every shipped profile:** all fourteen boarding-owned pathogens across the four bundles (the ten real, the four starship) now carry their own profile-level `boarding` block and `initial_infected: null`, ownership is derived from the loaded bundles rather than a hardcoded set, and `legionella_pneumophila` keeps a fiat count because its modelled reservoir is the ship's water plant rather than an embarking host. Imports that realistically arrive as a group (Andes hantavirus, Ebola, measles, cholera) board through a new clustered **`party`** mode — one per-voyage Bernoulli, then one party of the stated size all infected and drawn cabin-mates-first — rather than an independent per-person draw over 7,000 heads. Defaults are Consensus-sourced plausible defaults, campaign-adjustable for season and port status (register §3.5), and the starship values are declared fiction-grade. No value licensed: every real-pathogen default is a swept starting point, not an adopted constant |
| C2 | SARS-CoV-2 emission scale × β, jointly | #30 | Register §4 item 4. They enter the beta-frailty law strictly as a product, so neither is adoptable alone. Blocks all of Track D. **Refused on evidence by [tranche 25](../literature/consensus_tranche_25_covid_emission_beta_alias.md), and the prescribed sweep is withdrawn with it.** Two results. (i) The pair is not merely non-identifiable but **one axis**: the hazard reads `susceptibility × dose` and nothing else (identical to 1.1e-16 under reciprocal rescaling), and β⁻¹ is a scale on the susceptibility draw to within 0.7% across four logs, so #36 must carry **one** factor for them or it will report a spurious aliased pair. (ii) The β endpoint the register told this item to sweep to — Zhang & Wang's k in copies — is **inadmissible**: murine prior, attack-rate-meta-analysis calibration, and an exhaled-shedding input shared with the other factor of the same product. Killingley is one dose level in TCID50 behind a 2.7-log unit bridge, so there is no span. The emission side stays bounded (Grade B, [4.2e3, 5.8e7] copies/epoch); the per-copy factor is ∅ null. No constant moved |
| C3 | Norovirus shedding-curve peak magnitude | #47 | Same identifiability as C2 in the other arm: a −2 log emission correction applied alone is absorbed into an unidentified quantity. Declared, not applied, unless adopted with the dose axis. **Closed as declared-not-applied** (tranche 26): the peak is also the reference denominator of the *hand* route, so the GII interval cannot be applied to the faecal curve alone — it would move Liu 2013's measured hand load to below one copy per hand at the interval floor, and the stool-mass-per-hand bridge that would license it is a searched null |
| C4 | `airborne_emission_fraction`, and a swept result for the drying axis | #42 | No study reports emission as a fraction of shedding, so the *definition* is the construction. The drying multiplier ships neutral and needs a swept result before any value is adopted. **Closed by [tranche 27](../literature/consensus_tranche_27_airborne_fraction_and_drying_axis.md), and the "no study reports it" premise is corrected: the null is per-arm, not universal.** The field multiplies an emission the arm has already computed, so it is a dimensionless share only where that level is a measured **release rate**. On `influenza_a` it is — the level is pinned to Yan 2018's exhaled geometric means — so the fine (≤5 µm) share is **adopted as an interval [0.76, 0.92]**, Grade B, from paired size-resolved exhaled measurements (Yan 2018 → 0.76, Chow 2023 → ≈0.92, Coleman 2021's 0.85 for SARS-CoV-2 inside it), shipped at the floor because the profile field is a scalar. On `sars_cov2_resp` it is not: the level is a nasal specimen titre, so the shipped 5e-5 is a unit-bearing titre→emission conversion and stays **declared, not applied** — what licenses a share there is C2's level defect, not more sourcing. `norwalk_gi` takes no continuous share (`emesis_conditioned`, per-event range preserved), and the helper's unsourced 1e-4 fallback is now named and test-fenced. The **swept result is delivered**: `scripts/drying_axis_sweep.py` (five log-spaced points, eight common random numbers) puts the axis span at **0.19–0.27 of one seed's SD** on all four attack rates and on VSP posting, so the factor is below the noise floor everywhere it is scored — and the one output that moves, `peak_epoch`, moves because the 168-epoch window censors the peak, which is a finding against that output rather than a sensitivity |
| C5 | `contact_transfer_fraction` | #22 | Deliberately last in this track: it clears no noise floor anywhere across its whole sourced interval. Correct it; do not prioritise it. **Closed as a refusal on identifiability, and the noise-floor reason is withdrawn with it** ([tranche 12](../literature/consensus_tranche_12_contact_transfer.md) §10). The field multiplied the direct-contact pathway dose inside `_direct_contact_dose` / `_per_partner_contact_dose`, and `_apply_route_efficiencies` multiplies that same pathway's dose by `route_efficiency_multipliers["direct_contact"]` immediately afterwards — two scalars in the same position of one product, so only the product was ever identifiable and the #368 screen entry ranged half of a product, which is why its near-zero `mu_star` is not a sensitivity result either. Same archetype as #25 and C2. The field is therefore **retired**, not sourced: deleted from the engine, the schema and the screen box, and refused at load by the loader, the schema and the sanity checker so it cannot return as a silent second layer; the surviving owner keeps the whole 0.06–0.50 range. The sourcing question is moot rather than open, and was unanswerable anyway — its denominator was a partner's *emission*, which no assay uses, and two further unfiltered Consensus queries re-confirm both nulls. The **~0.25** anchor stays refuted as a direction-free quantity; the two directional fomite intervals are untouched |
| C6 | ~~Ask Edison whether the Teunis Table III ID50 of 18 is in aggregates~~ **Done: question withdrawn, answered from the published exchange** | #43 | **Closed by [tranche 23](../literature/consensus_tranche_23_teunis_atmar_dose_unit.md).** The axis is genome copies; the ≈925 copies-per-aggregate bridge is withdrawn as circular and replaced by Kirby's published µ_c = 517, which retracts the ~100× aggregation fork; the dose-axis span [1.32×10³, 1.69×10⁴] gEq is declared and not applied. Teunis 2008's Table III stays `?nr` (paywalled) and its "18" is recorded as contested in print, not settled. No external latency remains |
| C7 | Re-tests the rebuild invalidated: Alsved airborne check, A5 role asymmetry, faecal-release plateau under syndromic surveillance | #39, #40, #24 | These are conclusions drawn on a structure that no longer exists. They are cheap and they are not optional. **All three re-run; two conclusions hold and one was measured on a censored output.** (1) The Alsved check is re-done against the *event-conditioned* mechanism that replaced the continuous fraction ([tranche 28](../literature/consensus_tranche_28_airborne_norovirus_out_of_sample.md), `scripts/alsved_airborne_check.py`): the interval's ceiling reaches 5.0–6.7 copies/m³ against Alsved's measured floor of 5, so there is no over-emission — and no discrimination either, since inverting the comparison admits receiving volumes across five decades. The 3-hour vomiting association supports the *mode*; the window is not representable on the 24-hour epoch, which is a clock-grain finding. (2) The A5 parity **survives the route re-measurement**: passenger:crew is 1.01–1.14 across twelve design points, so it was never droplet's doing ([diagnosis](../../telemetry_buffer/observation_model/a5_role_asymmetry_diagnosis.md)). (3) The faecal-release plateau **survives with outbreak response and syndromic reporting active** (0.03–0.05 of one seed's SD above release 8), its edge is 12 rather than 8, and the old `none_true` probe's infection attack rate was pinned at the susceptible fraction (`IMMUNE_RATIO = 0.2`), so that arm could not have reported an effect at all ([audit §2a](../norovirus/norovirus_parameter_freedom_audit.md)). No constant moves and no anchor is scored |

## 6. Tracks D and E — the two things the intervals are for

**Track D, the COVID arm as the held-out test.** This is where the
defensibility claim is actually cashed: fit *one* quantity on Diamond Princess
and score hulls that were never seen. D runs strictly in order — A2 → #31
(severity and observation models) → #33 (testing-campaign replica and onset
observation) → #32 (the two scenarios) → #34 (fit, then score held out). It
depends on Track A for the clock, B2 for the observation model, and C2 for the
emission bracket — and C2's refusal changes what D inherits: the bracket, but no
sourced per-copy risk to divide it by, so the one quantity D fits on Diamond
Princess is the composite Θ = emission × per-copy risk, and it must be declared
as that rather than attributed to either factor. The train/test split is already fixed in writing in
`covid_trajectory_fit_spec.md` §7, before implementation, and must not be
revisited after seeing which hull fits.

**Track E, the pre/post-COVID regime.** #9 (the formal_spec_v2 3.7 NPI
dose-reduction interface) → #10 (pre-2020 and post-2020 configuration sets built
from the literature, not from the target) → #11 (score jointly on levels and on
the **A7** discontinuity). Depends on Track B, because #11 scores against A7 and
the recut class bins. Earlier revisions of this paragraph wrote A6 for the
discontinuity; A6 is the superspreader proxy and is deliberately not scored the
same way (`anchor_measurement_spec.md`), so #11 must not be built against it.

**#9 is done and adopts nothing.** `engines/non_pharmaceutical_interventions.py`
gives a measure a source, a per-role coverage, a compliance and a per-route
surviving fraction; the engine applies it per host after route efficiency and
before gastric survival, so an NPI is what the operator put between a route and
a portal rather than a second copy of the route's own efficiency. No measure
ships — `config.yaml` carries the shape commented out with its magnitudes
written `XXX` — so #9 changes no output and #10 owns every number, including
whether the post-2020 buffet-entry prompt's two arms (soap vs. alcohol rub,
which Tuladhar 2015 separates by 3–4 log10 on GII.4) survive sourcing at all.

**#10 is done, and it adopts no magnitude either.**
`telemetry_buffer/observation_model/era_configuration_sets.py` holds both arms as
lever sets: one swept lever for the pre arm, ten for the post arm, and
`era_config_patch` refuses to build either unless the caller states a coordinate
in [0, 1] for every one of them, so no era acquires a point value by omission.
The buffet prompt is two measures of four levers each — coverage, compliance, a
sourced `removal_log10`, and an unsourced `hand_share` that alone can produce no
reduction. Three findings #11 inherits:

- The soap-versus-rub separation quoted above is on **genomic copies**. On
  infectious MNV1 Tuladhar's own intervals overlap (>3.0 ± 0.4 against
  2.8 ± 1.5), so both arms are carried at the infectious spans — the weaker
  separation — and the wider genomic gap is recorded and unused.
- The shipped `hvac.filter_efficiency` of 0.50, whose comment labels it
  `MERV-13`, lies in **neither** era's sourced span (pre [0.0, 0.30], post
  [0.90, 0.99] from the Healthy Sail Panel's own MERV 8 / MERV 13 figures): it
  is a post-pandemic label on a value matching no filter, in an arm whose
  anchors are overwhelmingly pre-2020. It is swept per era rather than
  redefaulted, because moving the default moves every golden; §10 closes the
  path by which a run could reach it without saying so.
- Six documented post-2020 mechanisms enter as **declared absences** rather than
  numbers — ≥6 ACH (no field: the native transport has only
  `natural_decay_rate`), staff-assisted buffet service, isolation capacity,
  touchless fittings, pre-boarding screening (takeoff-preventing, so invisible
  to A7 by construction) and the cleaning schedule. #11 therefore cannot report
  that "the post-2020 configuration" was applied while meaning a third of it.

Immunity is deliberately not an NPI: `ship_graph.immune_fraction` is swept
[0.0, 0.2] with only its **sign** sourced (O'Reilly 2021, Lappe 2023), because
it pushes A7 the opposite way to every intervention and folding it into a
hygiene multiplier would let the two cancel invisibly.

**#11 is done as a procedure, and it has nothing to score yet.**
`telemetry_buffer/observation_model/era_joint_scoring.py` fits the common dose on
the pre arm alone — `fit_common_dose` refuses any run not labelled `era = "pre"`,
and what it returns is the *set* of dose cells the pre-2020 levels admit, never a
ranked best dose — then reads A7c at each post-arm sweep point held at those same
doses. A post run at a rejected dose is reported unscored rather than scored, a
post run that does not state a coordinate for every swept lever of #10 is an
error, and a fit whose recorded `arms_seen` is anything but `("pre",)` cannot
score A7c at all. Simulated voyages enter either arm only through VSP's own
posting rule (≥100 passengers, 3–21 days, ≥3% of passengers or of crew), applied
identically to both, because a simulated fleet mean and a posted-outbreak median
are not the same quantity. Three consequences worth stating:

- The scored anchor is **A7c**, the passenger-specific component, against the
  measurement's own 0.53–0.91. The composition-controlled 0.581–1.053 is carried
  beside every verdict as context and never substituted for it, because it
  contains 1.
- The report names the anchor that rejected each dose and the six declared
  absences of #10, so an **empty region is diagnosable**: it says which half
  failed, and it is a result rather than licence to widen a target.
- Nothing here searches. A7c is read once per post-arm point and cannot promote a
  dose the pre-2020 levels rejected or rescue one they did.

What it does not yet have is arms to read: the pre/post sweep of #10 has not been
run, so no admissible region — empty or otherwise — is reported yet.

D and E are independent of each other.

## 7. The gate, and what it means to fail it

Two items, strictly last, plus the infrastructure they need.

**#16 and #17** — rebuild and push the campaign image, and submit the C1
levels-only dose bracket — are infrastructure with wall-clock cost and no
in-repo dependency. Start them early; they are the only items whose duration is
not our own working time.

They have run, and the C1 bracket they submitted returned nothing: all nine
`dose_adjustment` rungs produced identical output at every seed, so 2,880 runs
were 320 distinct runs replicated across a ladder sited where the axis is flat
([`../norovirus/c1_reported_case_bracket_result.md`](../norovirus/c1_reported_case_bracket_result.md)).
A sweep that cannot distinguish its own rungs is a third way to waste a
campaign, beside the two in §1, and it is the one that survives a completely
successful run. Every campaign submitted from here on states which axis it is
resolving and is checked for resolution on a short probe *before* submission,
with `picard_framework/analysis/sweep_degeneracy.py`.

**#36, the Morris screen, re-run on the rebuilt structure.** It cannot run until
Tracks A and C are complete, because every item in them changes either the
structure or the box. Running it earlier does not produce a partial answer; it
produces an answer to a question about a model that no longer exists. That has
already happened once.

**Run, 2026-09-05:**
[`../norovirus/bounded_screen_isolated_36.md`](../norovirus/bounded_screen_isolated_36.md).
350 runs on the completed Tracks A and C, six factors, matched seeds, other
bundle pathogens' seeds suppressed. One factor resolves above the measured noise
floor (`environmental_faecal_release_log10_g_per_epoch`, the box's only Grade D
interval); five do not, and no factor resolves on the crew reported-case
channel. The surface-shape question A4 left to this screen is **not made live by
it**: `surface_decay_log10_per_day` sits at 0.19–0.58 of the critical value on
every output, so #60 has no sensitivity result licensing a biphasic form. The
screen's one input to #37 is a budget: a design resolving one factor of six at
five seeds per point says the region search is seed-bound, not
trajectory-bound.

**And it has already been overtaken, in the way this row warned about.**
#54/#440 landed the day after those runs and replaced the one fiat index case
with a boarding prevalence draw the initiation engine owns; at the same box
centre the passenger infection attack rate moves from ≈0.005 to 0.0759. The
screen's ranking and its floor both describe the retired condition, so neither
restricts #37, and the "five factors unresolved" reading — attributed there to
an epidemic near extinction — is the finding most likely to change under the
denser arrival. The harness now isolates through the initiation channel and a
replacement pass is runnable; it has not been run.

**#37, the admissible-region feasibility test:** does *any* point inside the
literature-bounded box satisfy all the anchors simultaneously?

[`bayesian_inference_design.md`](bayesian_inference_design.md) recasts this
gate as posterior mass in the admissible set; the plan's advance commitment
about what an infeasible result means is unaffected.

**Run, 2026-09-06:**
[`../norovirus/admissible_region_37.md`](../norovirus/admissible_region_37.md).
128 Sobol' points over the **full** six-factor box (not #36's screened subset,
which the boarding migration retired), 5 matched seeds each, `mega_cruise_5000`,
pre-2020, norovirus isolated at the boarding channel. **The region is empty:**
0 of 128 admissible, the best point passing two of five scoreable anchors, and
every anchor pair jointly passing zero times except A5+A4.

And the stop rule below applies to the *reading* of that result as much as to
the response, because two of the six required anchors never became evidence.
A4 is conditional on a posted outbreak while A8 is unconditional over all
travel-days on the same numerator — 23x apart once converted into common units —
so no parameter value satisfies both in a cell of replicate runs of one
configuration; and A9's target needs at least 180 eligible voyages per cell to
be attainable at all, so it is reported design-limited. Of the pairs that do
bind, A1-vs-A4 binds inside the assumed observation model (capture saturates at
1.0, and A3 lands outside its construction band at 123 of 128 points), which
leaves **A1 against A2 as the only genuinely structural tension**: ill/infected
reaches its literature floor only at an attack rate half again above A1's
ceiling. That is the finding, and it is recorded rather than repaired.

This is the test the whole campaign is for, and **the plan should be read as
building towards a test we may fail.** Two outcomes:

- **Feasible.** The model is consistent with the literature and with the
  observations at once, and the admissible region — not a fitted point — is the
  result. The width of that region is the honest uncertainty.
- **Infeasible.** No literature-bounded point satisfies the anchors. This is the
  **more informative outcome**, and it is the one I would bet on. It says either
  a mechanism is missing or an anchor is wrong, and it says so in a way that
  cannot be absorbed by tuning — which is exactly the property fourteen tranches
  of removing knobs was bought to obtain.

**Track B is what makes an infeasible result interpretable**, and this is the
strongest argument for its position in the sequence. If the anchors have not
been cleaned first — A3 demoted, the class bins recut, the denominator
externalised — then an infeasible result is uninterpretable, because we cannot
tell whether the model is wrong or the target is. Cleaning the anchors *after*
seeing an infeasible result would be indistinguishable from moving the goalposts,
regardless of how principled each individual change was.

**A stop rule, stated in advance:** if #37 returns infeasible, the response is to
identify the *binding* constraint and report it. It is not to widen an interval
to its most favourable end, and it is not to drop an anchor. Any interval widened
after the gate has been run must be justified by a source found after it, and
recorded as such in the register.

## 8. Sequencing and cost

Tracks A, B, and C are largely independent and can run concurrently; D and E are
downstream of all three; the gate is last.

| Track | Items | Estimate |
|---|---|---|
| A — structure | 5 | ~3 sessions, A1 the largest |
| B — anchors | 5 | ~2 sessions |
| C — intervals | 7 | ~4 sessions, mostly search-bound |
| D — COVID held-out test | 5 | ~4 sessions |
| E — regime | 3 | ~2 sessions |
| Gate | #36, #37 (+#16, #17) | ~2 sessions plus campaign wall-clock |

Roughly **17 sessions of work, and nearer 10 elapsed** with A/B/C overlapped.
One cost is not working time and should be started immediately rather than
scheduled: the campaign image and Spot submission (#16, #17). The other, the
Edison question (C6), no longer exists — it was answered from the published
exchange and withdrawn rather than sent.

## 9. What this plan deliberately does not do

- It does not schedule a refit. Every dose figure in the repository is void
  pending one, and the refit belongs after the gate, not before it — a refit run
  on an unfinished structure would have to be redone, and would meanwhile look
  like a result.
- It does not add a parameter anywhere. Every item either removes a degree of
  freedom, converts a point to an interval, or fixes a field's shape.
- It does not promise the model will pass. See §7.

## 10. The two defects recorded in passing, repaired

**A8/A9's hull-to-GRT mapping no longer names a ship per hull.** The old map
paired each hull with one representative vessel and inherited B3's defect twice:
Coral Princess (1,970 lower berths) and Voyager class (3,114) were matched to the
classic and spirit hulls by their *total* complements, so both hulls scored
against a tonnage band above their own. Picking two better ships would repeat the
method, and the record does not identify a canonical ship for a synthetic hull.
The four published tonnage/berth pairs are used instead for the only thing they
jointly measure — space ratio, 41.7–57.1 GT per lower berth — and a hull's
passenger complement (from B3's `nominal_complement`) maps through that span to a
tonnage *interval*. Every band the interval meets is kept, so the classic hull
(≈56,300–77,100 GT) carries both the 30,001–60,000 and 60,001–120,000 pooled
rates and A8 scores it against the envelope of the two; deciding which side of
60,000 GT it falls on would be a midpoint, and nothing in the record decides it.
Widening a target is only admissible because the width is the published spread of
real ships, not a response to a failure: a hull outside the envelope still fails,
and 120,001–140,000 now maps to no hull at all. A9's per-hull numerator remains
unpublished, so it stays null per hull.

**`hvac.filter_efficiency` = 0.50 stays put, and stops being reachable by
accident.** The value is not replaced: every candidate replacement is a point
inside a sourced span, which is the choice the whole plan refuses, and the
non-era goldens were generated at 0.50. What was wrong is that it was also the
value a run got when it said nothing — `hvac_cfg.get("filter_efficiency", 0.50)`
in both transport builders — so an era arm with a dropped coordinate would have
run a filter belonging to neither era while reporting an era. The fallback is now
`require_filter_efficiency`, which raises on an absent key; the constant is named
`UNSOURCED_LEGACY_FILTER_EFFICIENCY` and documented as unsourced where it is
defined; and the `MERV-13` label is gone from the config, the manual and the
README, because the span that names MERV 13 puts it at 0.90 and a label that
contradicts its own source is a claim rather than a note.
