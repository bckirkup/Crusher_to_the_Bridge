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
| B2 | The observation model's ~15 numbers: source them or declare them | #27 | B1 |
| B3 | Recut the A4 class bins | #29 | — |
| B4 | An external voyage denominator for VSP posting rates | #13 | — |
| B5 | Measure or externally bound the cabin-localization fraction `f` | #12 | — |

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
agreement would restore the circularity the demotion removed. B3 is a plain
defect (the bins bin
passenger counts against total-agent capacities). B4 and B5 are searches with no
in-repo prerequisite and can run in parallel with Track A.

## 5. Track C — intervals: no scored parameter stays a point value

Task #35 is the umbrella. This track can start during Track A, but **adoption of
any interval lands after the Track A item that owns its field.**

| | Item | Task | Note |
|---|---|---|---|
| C1 | `never_symptomatic_fraction`, and migrate `norwalk_gi` off `initial_infected` | #53, #54 | Gates the boarding channel built in #388. Exclude outbreak-conditioned asymptomatic prevalence (18–22%) for the tranche-10 reason: it is conditioned on the outcome being scored. **#53 refused on evidence by [tranche 24](../literature/consensus_tranche_24_never_symptomatic_adult_null.md)**: the null is now twice-searched and structural — every adult natural-exposure design fails at the *denominator* (asymptomatic-only screening, AGE-triggered enrolment, or positive-specimen share, the last length-biased upward by convalescent shedding), so the two tranche-11 intervals stand unpooled and no value is licensed. **#54 blocked, not done:** the destination channel needs the refused coordinate, and the intermediate move — relocating the fiat index case into `initiation.explicit_seeds` — would silently override the campaign's swept `initial_infected` axis, since initiation ownership drops a pathogen from legacy seeding while the run id keeps the `init<N>` label. That collision is now a load error on both mechanisms rather than a silent one; the shipped profile keeps `initial_infected: 1` |
| C2 | SARS-CoV-2 emission scale × β, jointly | #30 | Register §4 item 4. They enter the beta-frailty law strictly as a product, so neither is adoptable alone. Blocks all of Track D |
| C3 | Norovirus shedding-curve peak magnitude | #47 | Same identifiability as C2 in the other arm: a −2 log emission correction applied alone is absorbed into an unidentified quantity. Declared, not applied, unless adopted with the dose axis |
| C4 | `airborne_emission_fraction`, and a swept result for the drying axis | #42 | No study reports emission as a fraction of shedding, so the *definition* is the construction. The drying multiplier ships neutral and needs a swept result before any value is adopted |
| C5 | `contact_transfer_fraction` | #22 | Deliberately last in this track: it clears no noise floor anywhere across its whole sourced interval. Correct it; do not prioritise it |
| C6 | ~~Ask Edison whether the Teunis Table III ID50 of 18 is in aggregates~~ **Done: question withdrawn, answered from the published exchange** | #43 | **Closed by [tranche 23](../literature/consensus_tranche_23_teunis_atmar_dose_unit.md).** The axis is genome copies; the ≈925 copies-per-aggregate bridge is withdrawn as circular and replaced by Kirby's published µ_c = 517, which retracts the ~100× aggregation fork; the dose-axis span [1.32×10³, 1.69×10⁴] gEq is declared and not applied. Teunis 2008's Table III stays `?nr` (paywalled) and its "18" is recorded as contested in print, not settled. No external latency remains |
| C7 | Re-tests the rebuild invalidated: Alsved airborne check, A5 role asymmetry, faecal-release plateau under syndromic surveillance | #39, #40, #24 | These are conclusions drawn on a structure that no longer exists. They are cheap and they are not optional |

## 6. Tracks D and E — the two things the intervals are for

**Track D, the COVID arm as the held-out test.** This is where the
defensibility claim is actually cashed: fit *one* quantity on Diamond Princess
and score hulls that were never seen. D runs strictly in order — A2 → #31
(severity and observation models) → #33 (testing-campaign replica and onset
observation) → #32 (the two scenarios) → #34 (fit, then score held out). It
depends on Track A for the clock, B2 for the observation model, and C2 for the
emission bracket. The train/test split is already fixed in writing in
`covid_trajectory_fit_spec.md` §7, before implementation, and must not be
revisited after seeing which hull fits.

**Track E, the pre/post-COVID regime.** #9 (the formal_spec_v2 3.7 NPI
dose-reduction interface) → #10 (pre-2020 and post-2020 configuration sets built
from the literature, not from the target) → #11 (score jointly on levels and on
the A6 discontinuity). Depends on Track B, because #11 scores against A6 and the
recut class bins.

D and E are independent of each other.

## 7. The gate, and what it means to fail it

Two items, strictly last, plus the infrastructure they need.

**#16 and #17** — rebuild and push the campaign image, and submit the C1
levels-only dose bracket — are infrastructure with wall-clock cost and no
in-repo dependency. Start them early; they are the only items whose duration is
not our own working time.

**#36, the Morris screen, re-run on the rebuilt structure.** It cannot run until
Tracks A and C are complete, because every item in them changes either the
structure or the box. Running it earlier does not produce a partial answer; it
produces an answer to a question about a model that no longer exists. That has
already happened once.

**#37, the admissible-region feasibility test:** does *any* point inside the
literature-bounded box satisfy all the anchors simultaneously?

[`bayesian_inference_design.md`](bayesian_inference_design.md) recasts this
gate as posterior mass in the admissible set; the plan's advance commitment
about what an infeasible result means is unaffected.

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
