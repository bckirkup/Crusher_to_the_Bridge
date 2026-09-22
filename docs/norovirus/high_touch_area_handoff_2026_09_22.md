> **Status:** Handoff record. Reports **no new numbers**: every figure is quoted
> from the ledger entry, readout or committed artifact that measured it, with
> that entry's `Measured at` SHA where it has one. Read
> `docs/norovirus/norovirus_open_ledger.md` §1 before quoting any dose figure —
> every dose figure in the repository remains withdrawn pending the refit.

# High-touch area handoff — 2026-09-22

## 1. The question

What is `HIGH_TOUCH_AREA_M2`, and what is it allowed to be?

It is the areal denominator of the fomite pickup term: the engine keeps one
surface pool per unit, spreads deposited mass uniformly over a scalar area, and
divides by it (`_fomite_surface_area`, `engines/transmission_core.py`). Six
declared entries — cabin, sanitary, dining, public, galley, crew_mess — set the
magnitude of the whole fomite route. The immediate question was whether one
operational definition of "high touch", argued from the touch-frequency
literature, makes those six entries internally consistent. The question it has
become, and the one a successor inherits, is the wider one Benjamin posed:

> "I need EVERY variable that is a range and potentially impactful, because if
> there is a variable anywhere that fits inside all those ranges and allows all
> the ship classes to hit all the anchors, then we are done."

That is a feasibility problem, not an estimation problem. **Success** is a
single point inside the joint box of independently sourced intervals that
satisfies all anchors on all four hulls. **Failure that means something** is an
empty region measured over a box whose every coordinate was fixed from its own
sourcing *before* the search. **Failure that means nothing** is an empty region
over a box in which most coordinates are pinned at unsourced points — which is
what the repository currently has. The asymmetry is the governing fact of this
thread: a non-empty result would be conclusive; an empty one is only as strong
as the box is complete.

## 2. Current hypothesis

`HIGH_TOUCH_AREA_M2` is not a property of the ship. It is the scalar that a
pooled one-surface-per-zone representation *requires* in order to turn mass
into a concentration, wearing square metres. That is why two literature
tranches registered a hard null on it while every input to it is measured:
outside this model the summed high-touch area of a room is not a quantity
anyone needs, so no amount of retrieval will close it. It follows that the
parameter should be either **bounded and swept as a behavioural quantity** or
**retired as a parameter** by disaggregating the pool so the area becomes a
derived roll-up — and that arguing for any single value of it, as the
definition ledger's point table does, is the wrong shape of answer.

The sweep is the near-term move and the disaggregation is the eventual one. The
sweep is also not a separate piece of work: `A` is one more coordinate in the
joint box of §1, and its seam is already shipped.

## 3. Evidence for

- **`NORO-TRANSFER-PRODUCT-01`** (`docs/ledger/NORO-TRANSFER-PRODUCT-01.md`,
  measured at `bd462c5`): every term in the per-touch chain except the areal
  denominator behaves as declared — surface→hand implied efficiency 0.115–0.127
  across six source/zone buckets against a 0.1176 closed form, hand→mouth 0.339,
  essentially uncapped at shipped area (8 truncations in 170,023 pickups). The
  decade-scale whole-voyage "transfer loss" was whole-voyage bookkeeping, not
  transfer efficiency. `f_touch` spans 6.1e-5–7.5e-4 and that gap is almost
  entirely `HIGH_TOUCH_AREA_M2`. This is what isolates the denominator as the
  single unsourced term carrying the route's magnitude.
- **`NORO-HIGH-TOUCH-AREA-01`** (`docs/ledger/NORO-HIGH-TOUCH-AREA-01.md`,
  measured at `25eaa17`; tranche
  `docs/literature/consensus_tranche_45_high_touch_area.md`): no retrieved
  source reports the summed high-touch area of any room — null register `∅nr`,
  `∅lit` for cruise zone classes — although item sets, per-item areas and total
  room surface are each measured. A derived Grade C envelope exists per zone
  class under two readings, with a measured total-room-surface ceiling.
- **The `g0.25` canary** (same entry, 20 seeds 8000–8019, 288 epochs, measured
  at `25eaa17`): per touch the areal knob is exact — area ratio 0.250000, log10
  `f_touch` shift +0.60 against a predicted +0.602. This is the relation that
  lets the cost of any candidate area be stated analytically without a run.
- **`NORO-HIGH-TOUCH-DEFINITION-01`** (`docs/ledger/NORO-HIGH-TOUCH-DEFINITION-01.md`,
  `**Commit:** 97b6af7`, `**Measured at:** 25eaa17`; tranche
  `docs/literature/consensus_tranche_46_touch_behaviour.md`): one definition
  forced by the numerator — `SURFACE_CONTACTS_PER_HOUR` is already declared as a
  shared/multi-user surface rate, so the denominator must enumerate the same
  set. Under it the shipped table's per-occupant denominator tightens from a
  54× spread to 4.2×, at a price of roughly one log10 of per-touch fomite dose
  in dining, crew_mess and public. Retrieval did **not** contradict tranche 45's
  null. Nothing was adopted and no constant moved.
- **Morris screening** (`telemetry_buffer/observation_model/bounded_screen_v2_merged.json`,
  `bounded_design_v2`, AWS Batch job `77d99c06-485d-4bed-8e87-8bcb6663fad2`,
  200/200 children): `environmental_faecal_release_log10_g_per_epoch` ranks
  first on attack rate at μ\* 0.268, 13× the next factor. The file's own
  provenance string states that μ\*/σ "select no value, narrow no interval, and
  establish no admissibility" — it is a ranking, not evidence for a value.
- **The feasibility machinery exists and encodes the discipline.**
  `telemetry_buffer/observation_model/admissible_region.py` Sobol-samples the
  box, runs a matched seed block per point, scores the anchors, and carries a
  third verdict, `design-limited`, for anchors a cell of a given size cannot
  arithmetically resolve. Its docstring states the rule in full: it "selects
  nothing, fits nothing, and reports an empty region as a result rather than as
  a failure to be repaired".

## 4. Evidence against / unexplained

- **The committed empty verdict cannot currently be read as the model's
  fault.** `telemetry_buffer/observation_model/admissible_region_37_v2.json`
  (feasibility gate, Sobol 2^8, design seed 37) reports `n_points` 256 and
  `admissible_volume_fraction` 0.0, with no joint pass for any anchor pair. But
  (a) it ran one hull, `classic_cruise_1900`, while the scorer carries per-hull
  targets for all four; (b) its box is 10 coordinates while ~103 bare
  epidemiological scalars in `engines/` carry no range at all, including
  `HIGH_TOUCH_AREA_M2` itself; and (c) the gate's own source flags the A4↔A8
  comparison as a mapping artifact — A4 is conditional on VSP posting and A8 is
  over all travel-days, so passing both requires a mixture that a cell of
  identically distributed voyages structurally cannot represent. See §7.
- **Two of four hulls have no post-era A4 target at all.** `MIN_POSTINGS_FOR_TARGET`
  is 10 in `telemetry_buffer/observation_model/vsp_class_era_scoring.py`, and
  that module's own docstring records `mega_cruise_5000` at 3 post-2020 postings
  and `classic_cruise_1900` at 8. Since the question of §1 is explicitly whether
  *all* ship classes hit *all* anchors, this is a hole in the anchor set rather
  than in the parameterization, and no choice of parameters fills it.
- **The post-COVID discontinuity does not have the shape the engineering story
  predicts.** `telemetry_buffer/observation_model/vsp_covid_discontinuity_findings.md`
  (bootstrap and permutation 10,000 replicates, seed 20260830) measures, on
  norovirus-confirmed postings, a passenger median attack-rate ratio of 0.897 at
  p=0.1439 — mild and not significant — against a crew median ratio of 1.518 at
  p=0.0008 and a passenger-over-crew difference-in-differences of 0.591 at
  p=0.0001. Less fomite for everyone does not predict crew rising. The post era
  redistributed risk between passengers and crew far more clearly than it
  lowered it.
- **No stratum isolates the 2020 retrofits.** `era_for` in
  `telemetry_buffer/observation_model/fetch_vsp_outbreaks.py` assigns 2020–2021
  to `shutdown`, and `SCORED_ERAS` is `("pre", "post")` — the scored contrast is
  pre-2019 against 2022-onward, with the retrofit year excluded on both sides.
  `telemetry_buffer/observation_model/era_configuration_sets.py` already
  registers `surfaces.touchless_fittings` as unrepresented and unmeasured,
  "direction clear, magnitude unmeasured, trade-press sourcing only".
- **Unrepaired, numerator side, not attributed:** `SURFACE_CONTACTS_PER_HOUR["cabin"]`
  = 17.9/h cites Yuan 2024 for shared surfaces, but Yuan's four named surfaces
  are desks, cellphones, keyboards and mice — personal objects. Recorded in
  `docs/literature/consensus_tranche_46_touch_behaviour.md` §2. This is a
  sourcing defect in the rate, not in the area, and it has had no session.
- **The three derived readings disagree by up to 39×** (hardware / shared /
  broad, `tools/noro_diag/high_touch_area_envelope.py`), and within the shared
  reading the seated zones are ~99% driven by two declared geometries — a
  place-setting footprint and a chair — that nothing independent pins. The
  definition ledger reported the middle reading as the answer; the defensible
  object is the span.

## 5. PRs landed this session

In dependency order:

1. **#648** — `docs/ledger/NORO-HIGH-TOUCH-DEFINITION-01.md` plus
   `docs/literature/consensus_tranche_46_touch_behaviour.md` and the
   `shared` reading in `tools/noro_diag/high_touch_area_envelope.py`. Ledger
   entry `NORO-HIGH-TOUCH-DEFINITION-01`, status `open`. Adopted nothing.
2. **#649** — `docs/proposals/fomite_surface_disaggregation_spec.md`. Belongs to
   no ledger entry; it is a proposal, and per `docs/AGENTS.md` describes nothing
   that exists. Changed no constant.

## 6. Running jobs

None. No campaign, array job, canary or local sweep was submitted in this
session, and none is pending. No S3 prefix was written.

## 7. What is now void

Nothing measured in this session invalidates a recorded measurement — no code
ran and no constant moved. One previously reported result was found to be
already void and had not been written down anywhere:

- **The empty admissible region of
  `telemetry_buffer/observation_model/admissible_region_37_v2.json` is
  pre-refit and must not be cited as a current verdict.** Its `box` carries the
  factor `emesis_total_shed_gec`, which no longer exists in `engines/` — the
  emesis source term is now drawn as `emesis_titre_gec_per_ml` times
  per-episode volume, with no fallback (`docs/norovirus/emesis_source_term_v1.md`,
  ledger item 13). The file records no commit SHA, so the engine it was measured
  on cannot be established from the artifact. Any successor citing "the
  admissible region is empty" is quoting a model that is no longer run.

This is recorded in `docs/norovirus/norovirus_open_ledger.md` §1 in the same
change.

The necessary-condition logic built on top of it survives and should be kept:
if a single anchor has an empty satisfiable subregion across the box, the joint
is empty, and that is what justified scoring one anchor at a time on cheap
runs. What expired is every *specific* "cannot hit target X" claim measured on
the old structure. The converse never held: passing each anchor somewhere in
the box does not mean passing them together at one point, because the
per-anchor regions can be pairwise disjoint. Single-anchor screening can rule
out; it can never declare done.

## 8. The single open decision

**Does `HIGH_TOUCH_AREA_M2` enter the joint box as a ranged coordinate now, or
does the pooled representation get retired first?**

Options, with what settles them:

- **(a) Sweep now.** Add `A` per zone class as a ranged coordinate using the
  three readings already computed by `tools/noro_diag/high_touch_area_envelope.py`
  as its interval — 3.3× on sanitary to 39× on galley — through the shipped
  `transmission.high_touch_area_scale_by_zone_class` seam, which is
  behaviourally neutral by default, banded `[0.01, 100.0]`, and consumes no RNG
  draw. Changes no constant. Settled by whether the joint region is non-empty
  with `A` free.
- **(b) Disaggregate first.** Implement
  `docs/proposals/fomite_surface_disaggregation_spec.md` and let `A` become a
  derived roll-up. Priced in §7 of that spec. Settled by its neutrality
  identity, not by an anchor: with touch weights proportional to area share and
  no per-class cleaning, the per-surface arm must reproduce the pooled arm at
  paired seeds, because uniform density over areal weights *is* the pooled case.
- **(c) Sequence: (a), then (b) as its own session.** The recommendation. (b) is
  an engine change whose justification depends on whether a defensible interval
  on `A` admits a solution at all, and (a) answers that without touching the
  engine.

Ranked below it, and not to be confused with it: the post-era A4 hole of §4 is
a defect in the anchor set that no parameter search can resolve, and the cabin
touch-rate mislabelling of §4 is a numerator sourcing defect. Each wants its own
bounded session.

## 9. Do not reopen

- **No constant may be chosen because it makes VSP, Park, an attack rate or the
  passenger/crew ratio come out right** (`.agents/skills/model-parameter-provenance/SKILL.md`,
  `AGENTS.md`). This binds `HIGH_TOUCH_AREA_M2` specifically: it has never been
  fitted, which is a materially better position than a laundered fit, and that
  must not be spent.
- **Each coordinate's interval is fixed from its own sourcing before the search
  and is never widened afterwards to admit a solution.** Intervals narrow on new
  evidence only. A point that satisfies the anchors is legitimate only if every
  coordinate was independently admissible first; widening after seeing the
  result converts the box into an instrument for producing agreement, which is
  the failure the gate's docstring names.
- **The `∅nr` / `∅lit` null on summed high-touch area is registered twice** and
  should not be re-retrieved without a new reason. Report immediately if a
  source does contradict it.
- **`NORO-TRANSFER-PRODUCT-01`, `NORO-HIGH-TOUCH-AREA-01` and the `g0.25` canary
  are settled inputs.** Do not re-derive or re-measure them; quote them with
  their SHAs.
- **The eight-arm area campaign does not run on its current design.** Its
  criterion 2b must first be rescored as a paired per-seed dose distribution
  with censored shares rather than a ±10% median ratio — whole-voyage dose does
  not scale as 1/A even though per-touch dose does, because a per-touch change
  re-routes the outbreak rather than scaling a fixed deposition history
  (`NORO-HIGH-TOUCH-AREA-01`, measured at `25eaa17`).
- **The 2020 touchless-door retrofit is a signed consistency bound, never a
  scored anchor,** for the three reasons in §4. An architecture that predicted
  elimination from deleting one high-degree surface class would be falsified by
  the measured knee; one that reproduces "reduced, not eliminated" for the right
  reason is corroboration. Neither is an anchor pass.
