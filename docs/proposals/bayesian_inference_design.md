# Bayesian inference design: priors fix width, not shape

> **Status:** Proposed. **Nothing in this document is implemented, and no
> library, prior family or inference method is selected by it.** It adopts no
> value: every interval it cites is already recorded in the
> [provenance register](../parameter_provenance_register.md) and every number in
> §4's table is that register's own state, re-read rather than re-derived. Its
> purpose is to fix the *rules* — what becomes a prior, what may enter a
> likelihood, and what no prior can repair — before any inference code exists,
> because three of those rules are only credible if committed in advance.
> §6 describes machinery that **does** exist; the rest does not.

## 0. Why this exists

The register now holds intervals of wildly unequal evidential weight: a
dose-independence result measured across 4.2 logs with a published CI sits
beside a figure digitization, beside an abstract's rounded "about one-third". A
bounded sweep treats all three as boxes of equal standing. That is not caution —
it discards the difference between them, and it discards the measurement's shape
along with it.

Three commitments follow, and they are separable. §2 says evidence strength
should set prior **width**. §3 says circularity is a property of a **fit**, not
of a datum. §1 says neither of those repairs a field that cannot express what
was measured. Getting §1 wrong is the failure that a prior makes *harder* to
see, because a wide prior on the wrong object still produces a posterior.

## 1. The field-versus-value split

**A finding of the form "the literature measures a function and the field holds
one number" is dimensional, not evidential.** No amount of evidence and no
choice of prior repairs it. This class is unequivocal, and it must be resolved
by changing the field, not by widening a distribution.

Four in-tree instances, all confirmed by search rather than by argument:

| Field | Holds | The literature measures |
|-------|-------|-------------------------|
| `surface_decay_per_day` (influenza) | a scalar | a half-life conditioned on material, matrix, humidity and temperature — a surface, not a number ([register](../parameter_provenance_register.md) §3, `⊘ field`) |
| `illness_probability.eta` / `gamma` (influenza) | `1 − (1 + η·dose)^−γ`, strictly increasing in dose | a flat endpoint across 4.2 orders (Carrat 2008). The **functional form** is refuted, which is stronger than any value being wrong |
| `airborne_emission_fraction` | emission as a fraction of shedding | emission in absolute units — copies/minute or copies/hour. The field's *definition* has no referent, so the search returns `∅` however it is phrased |
| SARS-CoV-2 copies per infectious unit | an implied constant | no fixed conversion across specimen, variant, or point in the infection course. Not a missing number: an absent constant |

> **Correction:** The four rows above are four different defects with four
> different remedies; only influenza `surface_decay_per_day` is curve-shaped.
> The claim that `airborne_emission_fraction` has no measurable referent under
> any phrasing is withdrawn: the register records that field defect as
> resolved and names a Grade B source under an emesis-event-conditioned
> definition. The corrected table is [§0 of
> `field_repair_sequence.md`](field_repair_sequence.md#0-the-correction).

The remedy in each case is a covariate-indexed parameter — a prior over
functions with the conditioning variables explicit (material, RH, temperature,
dose, day-since-onset) — or a field deletion. Both are structural work, and both
belong to Track A of the
[defect resolution plan](defect_resolution_plan.md), *before* any inference runs
over the quantity. This is the same ordering rule that plan already argues for,
arriving from the inference side: a wide prior on a mis-specified field is the
laundering step, not the fix.

## 2. Evidence grade sets prior width, not admission

The current grades (A/B/C/M/I/∅/⊘) have been operating as an **admission gate**:
A and B adoptable, C blocked. Under a prior they should operate as **width**.

- A figure digitization is not worthless, it is *wide*.
- An abstract's rounded "about one-third" supports a prior centred near 0.33
  with enough spread to absorb the rounding — which is strictly more
  information than the uniform box over a swept range that the alternative
  uses.
- An analogous setting (paediatric where the population is adult; a surrogate
  organism; a porous surface where the model has non-porous) enters as a
  hierarchical level with its own offset and between-setting variance, not as a
  direct observation and not as an exclusion.

So: **second-hand beats none, and a sweep is none dressed as rigour.** The
grade letters stay in the register as provenance; they stop deciding whether a
row exists.

Three things this does **not** license, because they are wrongness rather than
weak evidence and a wide prior does not rescue them:

1. **Unverified transcription.** The Freeland 2016 voyage counts are recorded at
   Grade M because the sourcing unit transcribed a table from a source it could
   not re-open, the paper's own published per-1,000-voyage rates do not
   reproduce from those counts for 5 of 7 years, and its text says 133 where its
   table says 132. That is an unresolved discrepancy in the datum, not
   uncertainty about the quantity.
2. **Unit incommensurability.** TCID50 against genome copies (Killingley's
   challenge, Teunis Table III, task #43) is not a wide prior on the same
   quantity; it is a different quantity until a conversion is sourced.
3. **A definition mismatch.** See §1.

## 3. Circularity is a property of a fit, not of a datum

A circular value carries real information — Wikswo's cabin-mate odds ratio
measures something — it just cannot serve as evidence that the model got the
answer right, because the agreement was assembled rather than found. **It voids
the confirmation, not the datum.**

The consequence is that a register row cannot be marked "circular" full stop. It
must be marked circular *against a named anchor*, and the bookkeeping is
per-fit:

> Every fit declares the data entering its likelihood. A datum entering that
> likelihood is barred from that fit's prior. A datum entering neither is
> unconstrained. The same row may be prior in one fit and likelihood in another,
> and may never be both in one.

Two consequences run in opposite directions, and both are load-bearing:

**Fleet-level VSP data sits outside any single cruise.** Condition on one voyage
and the class-level aggregates (A4/A8/A9) and other ships' outbreak
investigations become genuinely *external* evidence about that voyage. Wikswo,
Chimonas and Mouchtouri are attack rates from *other* outbreaks; they were
circular against A4/A8/A9 only because the design fit to fleet aggregates and
scored on fleet aggregates. **Under an N=1 likelihood the same rows stop being
circular** — including the empirical cabin-localization bound `f ≤ 0.18–0.45`,
which is barred against the fleet anchors and admissible against a single hull.
Carrying that exclusion forward as though it were intrinsic would wrongly
exclude information.

**And the COVID arm tightens where norovirus loosens.** The two convenient ID50
figures from the DHS Master Question List — Prentiss's 361–2,000 particles,
Riediker's 500/300/100 copies — are fitted to attack-rate data from
high-attack-rate ship and superspreading events. Condition on Diamond Princess
and that is plausibly *the same voyage on both sides of the inference*, not a
related dataset. Both directions follow from the one rule.

This also settles the Diamond Princess question left open by the
[COVID trajectory fit spec](covid_trajectory_fit_spec.md): the constraint was
never that Diamond Princess is barred, only that it cannot be both prior and
likelihood. The train/test split that spec fixes in advance — Diamond Princess
to fit, Greg Mortimer and the Willebrand 104-voyage distribution held out —
remains the split, and stays fixed before implementation.

## 4. What the 21 blocked rows become

The register records **21** blocked quantities. They are not blocked for one
reason, and the split decides how much of this is worth doing. Counted by what
actually blocks each row:

| Cause | Rows | What a Bayesian treatment does |
|-------|------|--------------------------------|
| Field or functional-form defect (`⊘ field`, refuted form) | 7 | **Nothing.** §1. These need the field changed |
| Identifiability (`⊘ joint`, "not identifiable as a single ratio") | 7 | **Unblocks all seven.** See below |
| Literature- or design-side (no measurement exists; unit ambiguity in published rates; paediatric-only setting; challenge inocula far above natural exposure; value absent on an arm) | 7 | Widens or hierarchises some; two unblock for unrelated reasons, below |

**The identifiability third is the largest single gain, and it is a gain of
honesty rather than of power.** Every `⊘ joint` row is blocked because two
quantities enter only as a product or a composite: the shedding-curve peak
against β (both arms), the six route-efficiency multipliers against Edison's
pre-establishment clearance layer (both arms), `dose_response.k`, and the
asymptomatic offset, which is "not identifiable as a single ratio". Under a
joint posterior none of these is blocked — "not separately identifiable" stops
being a reason to withhold a number and becomes a **correlated posterior**,
which is the honest object anyway, because the data genuinely constrain the
product and not the factors. The interval scheme cannot express that and so
discards all seven.

It follows that the feasibility test (#37) must be recast. Sampling independent
interval boxes and asking whether any point satisfies every anchor destroys
exactly the correlations that carry the information: a box product can be empty
while the joint admissible set is not, and can be non-empty at points the joint
posterior gives no mass. #37 becomes **posterior mass in the admissible set**,
or posterior-predictive adequacy against the anchors, not a box search. The
advance commitment in [§7 of the plan](defect_resolution_plan.md) — what an
infeasible result means, fixed before the result is seen — is unaffected, and
is the reason that recasting is safe to do now rather than after.

Two rows in the third column unblock without any new search:

1. **Boarding / importation prevalence** is recorded as `⊘ mech — no importation
   channel exists; a host cannot board infected`. That is now stale:
   `engines/initiation.py` exists. Passengers **[0.025, 0.040]** and crew
   **[0.007, 0.030]** (Grade B, already recorded) are sweepable as soon as the
   shipped profile leaves `initial_infected` (task #54).
2. **The observation model's ~15 numbers** are blocked as `⊘ A3 is not a test` —
   their only constraint is an anchor that is itself circular. Declare the
   likelihood as one voyage's actual testing series and they acquire a
   non-circular constraint. So #27 unblocks by changing what we condition on
   rather than by sourcing anything — contingent on the observation streams
   existing (#32, #33), so a route rather than a result.

## 5. N=1, and why there is no likelihood to write

Conditioning on one well-observed voyage is the right target: it is the
observation unit a real maritime observer actually has, and a class IQR is an
aggregate no observer ever sees. But a single voyage is **one stochastic
realisation of an agent-based model**, so there is no closed-form
`p(observation | parameters)` to hand to a sampler. Two consequences:

- **The likelihood must be simulated, not written.** That points at
  simulation-based inference — ABC, synthetic likelihood, or a learned posterior
  over summary statistics — with the ABM in the loop or an emulator standing in
  for it. It does not point at Stan over the ABM's parameters, which is what the
  existing hurdle models are sometimes mistaken for (§6).
- **The observation process becomes part of the model, not a post-processing
  step.** At N=1 the difference between "38 hosts were infectious on day 6" and
  "the vessel reported 12 cases by day 6" is most of the inference. Symptom
  onset, care-seeking, assay sensitivity and specificity, turnaround, reporting
  delay, VSP's 3% posting threshold and missingness all sit *inside* the
  likelihood. This is the same statement as §4's second unblocked row, seen from
  the other side.

The summary statistics are therefore the design's most consequential free
choice, and they are a place where a scored anchor could re-enter through the
back door. They must be **observable** quantities — what a ship's medical log,
its testing campaign and its VSP submission actually contain — and they must be
declared before any fit, for the same reason the train/test split is.

## 6. What machinery exists — three patterns, and the join is missing

`picard_framework/analysis/stan/` holds nine models. They are **not** one layer,
and the distinction matters more than the count:

1. **Descriptive output regressions over campaign design factors.**
   `norovirus_outbreak.stan` (Bernoulli-logit P(outbreak)) and
   `norovirus_trajectory.stan` (NegBin2 trajectory | outbreak) put posteriors on
   `alpha_platform`, `beta_d`, `delta_surveillance`, `eta_vsp` — coefficients on
   the *swept axes of the campaign design*. `beta_d` is a coefficient on the
   dose axis, not the dose-response β. Their own README says it outright: "the
   ABM remains the mechanistic simulator." **We are already Bayesian about the
   outputs and not at all about the parameters.**
2. **Hierarchical models with a real observation layer.**
   `sentinel_fleet.stan` is the architectural template and I had understated it:
   a non-centred hierarchy over ports, visits, calendar weeks and ships,
   *plus* an explicit observation model linking latent shedder prevalence to
   observed wastewater — a beta-binomial read fraction (`ww_logit_base`,
   `ww_slope`, `ww_conc`) and a log10 copies/L concentration model
   (`conc_intercept`, `conc_slope`, `conc_sigma`). Hierarchy-plus-observation-
   process is therefore already implemented, tested, and exercised by the slow
   tier's posterior-recovery fits — for the sentinel surveillance problem rather
   than for the ABM's physics.
3. **Latent-parameter recovery from ABM run outcomes.**
   `synthetic_recovery_latent.stan` places priors on `dose_adj` and `alpha_c`
   and recovers them from run outcomes. This is the seam to the mechanistic
   model, and parameter recovery on synthetic data is precisely the validation
   an inference pipeline needs before anyone believes a posterior from it.

**What is missing is the join, not the parts.** Nothing puts a prior on a
*physical* pathogen parameter and conditions on a *voyage's observation stream*.
Pattern 2 supplies the hierarchy and the observation layer, pattern 3 supplies
the link to the simulator, and pattern 1 supplies neither and should stop being
described as parameter inference. Composing three existing patterns is a
materially smaller job than building an inference layer, which is the one
optimistic finding in this document.

Two cautions about reuse:

- **The `outbreak_surface` emulator is keyed on the wrong index.**
  `picard_framework/analysis/boundary/` exports response curves keyed by
  introductions `k`, resolved from `summary.parameters.initial_infected` and
  `initN` run-id tags. That is an emulator over ABM outputs — the expensive half
  of an SBI training set — but `initial_infected` is exactly the deterministic
  construction the initiation engine replaced, and task #54 retires it. Re-key
  on boarding prevalence before reusing it, or the emulator will index a channel
  the model no longer uses.
- **`log_crew_ratio` in `sentinel_fleet.stan` is a fitted crew:passenger ashore
  hazard ratio.** The passenger/crew ratio is one of the quantities
  `AGENTS.md` forbids fitting to. Nothing currently feeds that posterior into
  the ABM's crew asymmetry, and nothing should without checking it against A5
  first.

## 7. The validation gate

No posterior over a physical parameter is quotable until the pipeline has
recovered known parameters from synthetic data generated by the ABM itself. The
gate, in order:

1. **Parameter recovery.** Simulate at known parameter values, run the full
   pipeline, and check the posterior covers the truth at nominal rates across
   the design. `synthetic_recovery_*.stan` and the slow tier establish the
   pattern.
2. **Prior predictive check.** The prior, pushed through the ABM, must produce
   voyages that look like voyages — before any data is conditioned on.
3. **Posterior predictive check on held-out observables.** Not on the fitted
   hull. The split of
   [covid_trajectory_fit_spec.md](covid_trajectory_fit_spec.md) applies.
4. **Prior sensitivity.** Where a posterior moves with a prior whose width came
   from a grade rather than from a measurement, the posterior is reporting the
   grade. Say so.

Contraction from prior to posterior is also the direct answer to the question
this whole track exists to answer — how many knobs are left, and how much of
what the model claims comes from the data rather than from us.

## 8. What this document does not do

It does not select a probabilistic programming language, an SBI method, a prior
family, a summary-statistic vector, or an emulator. It does not authorise any
change to `data/pathogens/active_profiles.json`. It does not adopt a literature
value. It does not re-grade any register row. And it does not begin
implementation: §1 says four fields cannot express their measurements, and
inference over those fields would launder the defect rather than expose it.

## 9. Open decisions

1. **Emulator or ABM in the loop.** Re-keying the existing `outbreak_surface`
   export is cheap and its coverage is already paid for; an emulator also
   commits us to its summary statistics.
2. **The summary-statistic vector**, declared before any fit.
3. **Which quantities go hierarchical over pathogen and platform** versus
   independent per-arm.
4. **How far the field repairs of §1 go before inference starts** — all four, or
   the two that touch the anchors.
5. **Whether the fleet aggregates are prior or likelihood in the first fit.**
   §3 permits either; it forbids both.
