# NORO-HAND-RESERVOIR-01
**Date:** 2026-09-30
**Commit:** 55cb6b61
**Pathogens:** norwalk_gi
**Status:** measured

Repair campaign for the `NORO-HAND-STATIONARY-01` defect_candidate (PR #797):
the shipped hand reservoir is a spike-and-crash that occupies the Liu 2013
rinse distribution at 0.66% against a measured 25.4% (38× low), with the
ordering sign-flipped (post-defecation 0.381 above routine 0.0034; Liu
measures post-bathroom 12.4% @2.30 *below* routine 37.5% @3.32, P<0.05) and
never-positive share 0.763 against 0.33. Tranche 40's mechanism reading, which
this design implements: **the bathroom visit is a wash event, not a load
event — hand load is activity-driven state, suppressed by washing, rebuilt by
routine contact.**

The repair binds the two halves of that sentence to mechanisms that already
exist in the engine: routine re-uptake through the existing surface→hand
pickup chain, and explicit washing as the suppression term. No emission term
is invented.

## Design declarations (frozen before building)

### (i) Mass bookkeeping — host pickup depletes pools

Under the repair, every occupant of a fomite unit — not only the challengeable
subset `_get_susceptible` returns — builds a pickup request on the existing
request/deliver/consume path (`_fomite_pickup_request*` →
`_deliver_fomite_requests*` → `_consume_surface_mass`). Pool depletion is
identical for every requester: the surface→hand transfer does not check
infection state, so an already-infected host's hand draws the same mass and
the pool pays it. The swallowed share (`_hand_to_mouth_dose`) likewise removes
mass from every hand — an infected host's mouth contacts are the same physical
acts — but **dose bookkeeping stays challengeable-only**: `_record_fomite_
pickup` writes `agent_doses` / pathway doses / `fomite_trailing_exposures`
only for targets `_get_susceptible` admits, so the challenge ledger is
unchanged in scope. Declared interaction, measured not fitted: shedder-drawn
pickup mass is a new sink on the same pools susceptibles draw from, and the
re-census reports the shedder share of delivered mass per cell. The mass is
not lost — shedder hands redeposit through the existing
`_shedder_surface_deposits` (hand→surface) path — so the reservoir is a
recirculation loop, not a drain.

### (ii) Wash placement — every defecation event ends in a wash

The bathroom-visit analogue is the stool event the profile already declares
(`stool_events_per_day`, register rows 346/347: baseline 1.0/day, diarrhoeal
5.63/day swept). Under the repair each such event is, in order: contaminate
the hand if this host's carriage propensity fires, then wash — deterministic
on the visit, stochastic in efficacy (per-act log10 reduction drawn per
`_hand_hygiene_efficacy`). No propensity-drawn *compliance*: Liu's own
post-bathroom samples still carry 12.4% positivity, which a deterministic
wash with a spread efficacy distribution produces; a second thinning
parameter would be an unsourced second gate on the same observation.
Non-bathroom washes are **not** added: `_apply_hand_hygiene` stays the
profile-driven mechanism it shipped as (`hand_hygiene_rate_per_hour`,
default 0.0), and between-visit suppression stays with the existing
`hand_inactivation_rate_per_hour` U(0.61, 1.7). Flagged interaction, not
resolved: the `sanitary_visit_mode` urination stream (6.0/day, Chung 2009,
register row 357) is *not* a wash driver — Liu does not decompose "post-
bathroom" by visit type, and binding the wash to the dwell_weighted visit
stream would make the reservoir repair silently mode-dependent; if the
census under-suppresses, that is the first place to look. Declared:
wash placement = defecation events only.

### (iii) Ceiling spike survives as the colonizing load

The Liu-ceiling spike `10^3.86 × 10^(curve[idx] − 11)` stays as the
pre-wash contamination load of a visit that contaminates — the only
defecation-derived hand loading in the model, and the mass that seeds the
cabin/zone pools the re-uptake chain then recirculates. It is not replaced:
the wash, not the spike, produces the post-bathroom depression Liu measures.
Within the same event the sequence is spike-then-wash, so the post-visit
state the census reads (`load_post_replenish` on event rows) is the
post-wash residual — the analogue Liu's post-bathroom rinses sample.
First-seen hosts (mid-illness boarders) initialise at the post-wash
residual of a notional last visit: the shipped backward-recurrence draw on
the *un-thinned* visit rate, times a drawn wash residual —
`target × 10^(−eff) × exp(−kτ)` — an upper-bound convention (assumes the
last visit contaminated), declared because the marginal hand state of a
host mid-course is unidentifiable without the voyage history.

### (iv) Propensity Beta(0.911, 3.489) — kept, same role

The per-host beta-binomial stays the probability that a defecation
contaminates the hand (register: ML fit to Liu Table 3 per-subject
positivity counts, Grade B). Repurposing it to wash compliance is rejected:
its 0.207 mean would leave most visits unwashed and cannot produce Liu's
post-bathroom *suppression*. Retiring it is rejected: it is the only
per-host heterogeneity in the reservoir and carries the never-positive
tail Liu observes (0/12, 0/9 subjects). Flagged caveat, measured not
resolved: the Beta was fitted to *net post-visit* positivity, which
confounds contamination with wash survival, so as a pre-wash
contamination probability it is a lower bound; the wash draw stacks a
second suppression on top and the re-census measures whether the stack
under- or over-suppresses.

## Engine gating

`transmission.hand_reservoir_mode`: **`wash_reuptake`** (default — the
repair) / **`spike_decay`** (labelled baseline reproducing the shipped
mechanism bit-identically on matched seeds: under it, requester sets stay
challengeable-only, events stay propensity-thinned, and no wash draw
exists). Follows the repo's gating convention (`sanitary_visit_mode`,
`cabin_air_mode`): a `transmission.*` key with the new mechanism default-ON
and the shipped behaviour as a named baseline.

## Constants bound (no new magnitudes invented)

- Wash timing/frequency: the existing `stool_events_per_day` stream —
  register rows 346/347; no new rate constant.
- Per-wash log10 reduction: existing `hand_hygiene_efficacy_log10_reduction`
  (`HAND_HYGIENE_EFFICACY_LOG10` N(1.06, 0.54) clip [0, 1.89], authored-spec
  arm). Bound-not-adopted: Tuladhar 2015 per-act infectious removal soap
  [2.6, 3.4] / rub [1.3, 4.3] (register row 308) — a 30 s protocol wash on
  finger pads; Liu's post-bathroom residuals (12.4% ≥ LOD) argue the
  unsupervised act is weaker, so the weaker shipped distribution is kept
  and Tuladhar stays the recorded bound. The row's own caveat stands: this
  distribution has no dedicated primary citation beyond the authored spec.
- Pickup transfer coefficient on the host path: existing
  `SURFACE_TO_HAND_LOGNORMAL` (−2.1, 1.4) — register row 322 — identical
  draws, identical request builder; the change widens *who requests*, not
  *how much a request is worth*.
- Routine-contact rate: existing `SURFACE_CONTACTS_PER_HOUR` /
  `CREW_SERVICE_SURFACE_CONTACTS_PER_HOUR` zone-class rates — unchanged;
  a shedding host's routine contact rate is the same zone-class rate a
  susceptible pays.

## Match criteria (frozen before the census runs)

Pooled across the two frozen cells exactly as the defect census measured
them (`fl_spr_12d` seeds 8105–8164 spirit_cruise_3000, `classic_cruise_1900`
seeds 8000–8019; end-of-epoch hand loads on shedding-host rows vs Liu rinse
LOD 10^2.15):

- **Occupancy** — positive share vs Liu 0.254, ratio R: R ∈ [0.2, 5.0]
  clears the defect band (as declared in NORO-HAND-STATIONARY-01); the
  *restored* grade additionally requires R ∈ [1/3, 3].
- **Ordering** — `median(post-visit load on event rows) < median(end-of-epoch
  load on non-event rows)`: the sign flip is now *required*, not weighed —
  it is the mechanism's whole prediction.
- **Never-positive share** in the declared window (0.05, 0.80) vs Liu 0.33.
- **Positive-mean** log10 inside the declared window [2.30, 5.45] vs Liu's
  per-subject positive means [3.30, 4.45].

Verdict map, declared: `mechanism_restored` = all four pass with the ordering
flipped and R ∈ [1/3, 3]; `partial` = occupancy inside the defect band
(R ∈ [0.2, 5]) but ordering un-flipped or a secondary window missed;
`still_starved` = R < 0.2 (deposited mass cannot carry the reservoir — per
the agreed direction that outcome is a scope change and is reported, not
repaired with a new emission term). R > 5 is an over-supply miss and is
reported as such. The dose-side witness from (i) — shedder share of delivered
pickup mass — is reported alongside, ungated.

## Validation gate

pytest slice over the touched paths + `tools/sanity_checker.py
--from-config` + the frozen-cell re-census on AWS Batch before merge; the
measured verdict is appended to this entry and `NORO-HAND-STATIONARY-01`
is pointed at it.

## Measured at `55cb6b61` (merged `9850c4b3`) — verdict: `still_starved`

Frozen-cell re-census under `transmission.hand_reservoir_mode:
wash_reuptake` (shipped default), same cells and probes as
`NORO-HAND-STATIONARY-01`: `fl_spr_12d` 22 ignited seeds 8105–8163
(growth-chain census zips) + `classic_cruise_1900` 8000–8019, 288 epochs,
`picard-hand-occupancy:4` / image `noro-hand-reservoir01`, dumps in S3
`campaign/noro_hand_reservoir_01/`; 14/20 classic cells admissible, the
same six void as the baseline census (8000, 8007, 8011, 8013, 8015, 8017 —
no shedding rows to occupy). Aggregation:
`tools/noro_diag/hand_occupancy_readout.py` over 70,705 shedding
host-epoch rows.

**Primary: occupancy 3.35% vs Liu's 25.4% → R = 0.132 — inside no band.**
R moved 0.026 → 0.132 (5×), short of the defect-band floor 0.2; per the
declared map that is `still_starved`, reported, not repaired with a new
emission term. By cell: spirit 3.99% (22/22 seeds admissible, per-seed
0.0–14.0%), classic 1.65%.

**Secondary: two of four criteria now pass.** never-positive 0.745 moved
inside (0.05, 0.80) from 0.763 (Liu 0.33); positive-mean 3.47 log10 inside
[2.30, 5.45] (was 3.28). Ordering unflipped pooled — event 7.8% vs routine
3.1% (`event_higher`), Liu measures post-bathroom *below* routine; the
declared requirement fails. Positive-mean remains the only criterion
unchanged across designs.

**Witness (i): the shared pickup chain carries the mass.** 242.8M GEC of
302.7M delivered (80%) landed on non-challengeable hands — zero under the
susceptible-only requester set — and shedders redeposit through the
existing surface-deposit path. Deposited mass exists and reaches hands;
the reservoir is fed.

**Decomposition: the deficit is retention, not delivery.** 87% of
shedding rows underflow at end-epoch: per-event washes (1.06–1.89 log10 ×
~8978 spirit events) plus inactivation [0.61, 1.7]/h remove load faster
than ~250 GEC/host-epoch mean routine re-uptake rebuilds ≥141 GEC, and
delivery concentrates on hosts co-located with contaminated units. A
routine-only source holding Liu's occupancy against the sourced removals
needs a *new emission term* — the declared scope change — not a
re-balance of existing constants.

**Lens note (measured, not re-declared):** on the symptomatic-only lens
the spirit cell reads 19.7% vs 25.4% (R = 0.78, inside [1/3, 3]) and
classic 10.9%; the deficit concentrates in pre-/a-symptomatic shedding
rows. Whether Liu's challenge cohort is better matched by the symptomatic
lens is a sampling-map question for the next repair, not re-decided here.

**Interaction flagged, not resolved:** the −7.14 bridge stays shipped;
the within-study pairing (−3.5…−4.4) bounds the same row.

No constant, profile, or default moved after the measurement — the
mechanism, its gate and both arms are exactly `55cb6b61`; `spike_decay`
remains the labelled baseline.

## Re-measured at `d0466064` under `hygiene_cycle` (PR #804) — verdict: `still_starved`

Same frozen cells, probes and aggregation; `picard-hand-occupancy:5`
digest-pinned to the image built at the PR #804 merge SHA:
`fl_spr_12d` 22/22 (job `21b2d82f`), `classic_cruise_1900` 18/20
(void 8011, 8015; job `877f22f2`), 288 epochs, dumps in S3
`campaign/noro_hand_practice_01/`; 62,162 shedding host-epoch rows
(readout `docs/norovirus/noro_hand_practice_01/hand_occupancy_cells.json`).

**Primary: occupancy 2.82% vs Liu's 25.4% → R = 0.111 — `still_starved`
a second time.** R moved 0.132 → 0.111: the declared routine-source
emission term runs on every cell (hygiene counters fire fleet-wide) but
the tick equilibrium sits below the 141 GEC LOD on ~97% of routine
rows. By tier: spirit ~4.0% (per-seed 0.6–7.5%), classic ~1.7%.

**Secondary: the same two of four pass.** never-positive 0.564 (was
0.745; inside (0.05, 0.80); Liu 0.33) and positive-mean 2.586 log10
inside [2.30, 5.45]. Ordering still `event_higher` — event rows 5.99%
(3,235 samples) vs routine 2.65% (58,927 samples): Liu's post-bathroom
depression cannot appear while routine rows stay this empty, and under
this arm it cannot appear at all — the criterion asks routine rows to
exceed event rows while both ride the same carriage propensity.

**Witnesses.** `reservoir_delivered_gec` sums 0.0 on every cell — an
instrument hole, not a zero emission: that counter reads the
`challengeable = false` pickup channel `wash_reuptake` used, while
`hygiene_cycle`'s self-contact increments land directly on
`hand_load_by_pathogen`, outside its row path (the delivered-mass tally
of the new term is simply unmeasured by this census). The drying blend
is active and strong: mean deposit factor 0.046, window open on 4.7%
of rows — hand→surface deposits run ~20× below the wet calibration
almost all the time.

**Decomposition: the strip is multiplicative, the source is additive
and propensity-scaled.** Each routine tick adds `propensity ×
logU(50, 6300)` GEC (Beta(0.911, 3.489) mean 0.207 → ~90 GEC on a
typical tick, 2–8 ticks/day); each routine wash multiplies the load by
`10^(−eff)` (eff ~ N(1.06, 0.54) clipped to 1.89, 2–8 washes/day) plus
inactivation U(0.61, 1.7)/h — order-of-magnitude, the strip removes
~10⁻⁵ or more per day while the source adds ~10² GEC/day, so the
equilibrium sits below LOD on most hosts (measured: routine
positive-mean 345 GEC on the 2.65% of rows that make LOD at all). What
this census adds over the retention-deficit reading: the emission term
now exists and fires, and it still starves — its magnitude is bounded
by the same Beta carriage trait that gates the events, and its
additive increments are erased by an orders-of-magnitude-larger
multiplicative strip. A Liu-occupying reservoir needs either a routine
source of order the strip loss (not a Pickering increment) or the
symptomatic-lens sampling question resolved first — both are declared
scope questions, not a re-tune of what was declared.
