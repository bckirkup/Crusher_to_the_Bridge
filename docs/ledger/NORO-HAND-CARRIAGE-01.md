# NORO-HAND-CARRIAGE-01
**Date:** 2026-10-01
**Commit:** #811
**Pathogens:** norwalk_gi, sars_cov2_resp
**Status:** measured
**Measured at:** 1c94de2d

Second repair pass on the hand reservoir, on the measured
`NORO-HAND-PRACTICE-01` verdict (PR #808): under `hygiene_cycle` the
frozen-cell census read occupancy 2.82% vs Liu's 25.4% (R = 0.111),
ordering `event_higher` un-flipped, with never-positive 0.564 and
positive-mean 2.586 log10 inside their windows — `still_starved` a
second time. The decomposition appended to
`docs/ledger/NORO-HAND-RESERVOIR-01.md` named why: the source is
additive and propensity-scaled (~90 GEC/tick typical) while the strip is
multiplicative (~10⁻⁵/day of washes plus inactivation), so the
equilibrium sits ~2 orders under the 141 GEC LOD; and the ordering
cannot flip because the routine source rides the same Beta(0.911,3.489)
carriage trait as the events. Both are structural absences, not a
magnitude to retune — this entry declares the two missing structures,
still inside the `hygiene_cycle` arm:

1. **A wash-resistant residual compartment.** Liu's own post-bathroom
   arm shows washing does not sterilize — 12.4% of post-visit rinses
   still read ≥ 2.30 log10 — but the model's scalar hand load can be
   multiplied to zero by every wash act. Real hands retain carriage in
   sites a wash cannot reach: subungual folds and creases are "the area
   that harbors the most microorganisms and is most difficult to clean"
   (Lin 2003, FCV — a norovirus surrogate — persisting beneath natural
   and artificial nails through every non-nailbrush method; Walaszek
   2018 nail colonization surviving disinfection). The hand now splits
   into *accessible* and *protected* compartments; washes act only on
   accessible.

2. **A routine emission coupled to the host's own environment.** The
   fixed propensity×increment tick is replaced by a per-host
   own-environment pool: the host's own deposits onto its own fittings
   (own cabin compartment / home zone) are bookkept and decay at the
   profile's surface inactivation rate, and each routine self-contact
   tick draws a measured surface→hand fraction of the standing pool.
   Recontamination opportunities run an order above any viable wash
   frequency (Alonso 2013: 3.3 surface + 3.6 mucosal touches/hour), and
   the concentrated own-cabin pool — not the deck-diluted shared pools —
   is where an infected host's own virus actually waits for it (the
   recurring defect archetype: a well-mixed pool standing in for a
   concentrated personal reservoir).

## Design declarations (frozen before building)

### (i) Protected compartment fill — sequester per contaminating event

Each propensity-fired contaminating event sequesters
`10^U(log10 50, log10 3200)` GEC into the protected compartment —
Liu's post-bathroom positive band: after a bathroom visit + wash the
positive arm still reads ~2.30–4 log10, and that surviving mass IS the
protected compartment measured directly. Log-uniform (two-order span).
Grade B (magnitude bounded by Liu's own post-bathroom positives).
`HAND_PROTECTED_SEQUESTER_GEC_RANGE = (50.0, 3200.0)`.

### (ii) Protected compartment decay — sheltered inactivation

Protected load decays at a per-infection draw U(0.01, 0.06)/h — an
order below the fingertip-pad `HAND_INACTIVATION_RATE_PER_HOUR_RANGE`
(0.61, 1.7). Sheltered sites lose virus slowly (nail folds/creases hold
material against the desiccation that drives fingertip inactivation);
no dedicated under-nail survival series was retrieved, so the interval
is declared Grade C with the mechanism Grade B via Lin 2003 /
Walaszek 2018. `HAND_PROTECTED_INACTIVATION_PER_HOUR_RANGE =
(0.01, 0.06)`, drawn once per infection inside `_hand_practice`.

### (iii) Wash acts cannot reach the protected compartment

Every wash act — post-visit compliance-gated or routine — multiplies
only the accessible part by `10^−eff`. The hand's recorded load is
accessible + protected, so a wash floors at the protected compartment,
not at zero (the Lin 2003 finding: only soap + nailbrush reaches
subungual material, and the model has no nailbrush).

### (iv) Own-environment pool — bookkeeping + measured uptake

`hand_self_pool_by_pathogen` is credited at the two hand-deposit sites
when the deposit lands on the host's own environment: venue deposits
whose venue is the host's own cabin compartment key (or `home_zone` on
hulls without compartments), and zone surface deposits where
`zone_name == home_zone`. It decays at the existing
`_surface_survival(profile)` per epoch — the pool is own surfaces.
Each self-contact tick moves `min(pool, pool × SURFACE_TO_HAND draw)`
onto the accessible hand, reusing the measured
`SURFACE_TO_HAND_LOGNORMAL` (2–24% MNV/FCV non-porous) — no new uptake
constant. Emesis-patch mass is out of scope (tracked reservoirs; cleanup
already removes ~98%). Ambient shared-environment re-uptake for
shedders remains absent by construction — the pickup chain serves
susceptibles only, and the own pool is the declared concentrated
substitute. `SELF_CONTACT_INCREMENT_GEC_RANGE` is superseded and
deleted (register row marked).

### (v) Rinse and deposits read the total

`hand_load_by_pathogen` stays the total (accessible + protected) — a
hand rinse recovers both compartments and under-nail material does
deposit (declared simplification: protected deposits at the same rate).
The occupancy instrument gains `hand_protected_gec` and
`hand_self_pool_gec` witnesses per row.

## Admissibility criteria + verdict map (frozen)

Unchanged from NORO-HAND-RESERVOIR-01 — the same Liu criteria the
42-cell census measures: occupancy R vs 0.254 (`mechanism_restored` ∈
[1/3, 3]; `partial` inside defect band [0.2, 5]; `still_starved` < 0.2;
`over_supplied` > 5), ordering event < routine required, never-positive
(0.05, 0.80), positive-mean [2.30, 5.45]. New witnesses declared for
interpretation, not gates: `hand_protected_gec` share of positive rows,
`hand_self_pool_gec` level. Success criterion beyond the Liu windows:
**ordering flips structurally** — event rows carry post-wash residual
(protected only) while routine rows carry protected + rebuilt
accessible, so the declared structure produces event < routine rather
than a tuned margin.

## Validation gate

pytest slice over touched paths + `pre-commit` + `sonar_guard` +
`tools/sanity_checker.py --from-config`; a local occupancy practice
readout on the declared bounds before the PR; then the same 42-cell
frozen census on AWS Batch at the merged SHA, verdict appended here.
The Diamond Princess `covid_hand_ab_v1` array stays held until the
measured verdict lands (user direction 2026-10-01).

Local practice readout on declared bounds (fomite_mass_balance,
classic_cruise_1900, 288 epochs, `hygiene_cycle` + compartments):
seed 8001 positive-share 17.05% (1206/7075), seed 8002 21.11%
(1528/7238) — R = 0.67 / 0.83 vs Liu 0.254, inside the [1/3, 3]
restored band where the same block read 2.8%-class before this
change. Ordering / never-positive / positive-mean wait for the pooled
42-cell census; these numbers bound direction, not the verdict.

## Measured verdict — 42-cell re-census at `1c94de2d`

Measured at `1c94de2d` (merged #811) on the same frozen cells —
`fl_spr_12d` 22 ignited seeds + `classic_cruise_1900` 8000–8019, 288
epochs, read-only census, jobdef `picard-hand-occupancy:6` pinned to
image digest `sha256:ec35bcfb…` (`noro-hand-carriage01-1c94de2d`);
records in S3 `campaign/noro_hand_carriage01/`, merged cell table
`docs/norovirus/noro_hand_carriage01/hand_occupancy_cells.json`
(334,926 shedding host-epoch rows, all 42 cells admissible, no void
seeds).

**Verdict `partial` — the starvation is repaired; the ordering miss
persists.** Primary occupancy 18.69% vs Liu's 25.4% → **R = 0.737**,
inside the [1/3, 3] restored band (was 0.111 `still_starved` under
PRACTICE-01, 0.132 under RESERVOIR-01, 0.026 at STATIONARY-01). Both
secondary windows pass: positive-mean 2.743 log10 ∈ [2.30, 5.45],
never-positive 0.362 ∈ (0.05, 0.80). One secondary miss remains:
ordering `event_higher` — event-end rows 35.3% @2.935 vs post-defecation
35.9% @2.944 vs routine-end 17.6% @2.717, where Liu measured
post-bathroom *lower* than routine. The frozen rule calls the run
`intended_reading` (primary pass + one secondary miss); the reservoir
map lands `partial` because `mechanism_restored` requires the flip.

Per-block consistency: fl_spr_12d share 0.187 (R = 0.74), classic 0.186
(R = 0.73) — the band pass is not a single-hull artefact. Symptomatic-
only lens: 0.329 positive (both blocks ~0.33), R ≈ 1.30 — the same
reading the RESERVOIR-01 lens gave, now above the Liu point rather than
under it.

Carriage witnesses confirm the declared structure is what produced the
numbers: protected compartment mean 153.9 GEC per shedding row (771 GEC
on positive rows — a standing sub-LOD floor the wash cannot strip),
own-environment pool mean 43–56 GEC live on 100% of shedding rows,
`at_target` occupancy rows 20.5% (was ~0% — ticks now land on a stocked
pool), `underflowed` 41.0% (was 87%), first-seen rows 178. Wet window
open 4.6% of rows, mean deposit transfer factor 0.046 — the drying
blend unchanged. `reservoir_delivered_gec = 0` persists — the witness
counter still reads only the `wash_reuptake` channel; an instrument
hole, not a zero term (same caveat as the PRACTICE-01 census).

**What the miss is.** The ordering's event arm is not sampling what
Liu's post-bathroom arm sampled: the census's post-defecation rows are
row-time loads recorded at event end — fresh contamination *before*
the compliance-gated wash completes — while Liu's post-bathroom rinses
were taken after the bathroom episode, i.e. post-wash. With a wash
that now floors at the protected compartment instead of zero, a
post-wash-conditioned comparator is the mechanism's honest version of
Liu's arm: event rows would carry protected-only load while routine
rows carry protected + rebuilt accessible — the declared structure
that produces event < routine. Conditioning the comparator on
wash-completed rows is a sampling-lens question on the readout, not a
mechanism change; it is recorded as the open declared-scope decision
in `docs/norovirus/noro_hand_carriage_handoff_2026_10_01.md` §8 and is
**Benjamin's call, not a silent fix.**

The Diamond Princess `covid_hand_ab_v1` array's hold lifted on this
verdict: resumed on image `covid-hand-carriage-1c94de2d` into fresh
prefix `campaign/covid_hand_carriage01/` (the `covid_hand_ab_v1/`
prefix's two prior-mechanism canary cells stand as the recorded
baseline, labelled, not voided).

**Post-wash comparator — measured (2026-10-01, same cells).**
Benjamin approved conditioning the ordering on wash-completed rows.
It turns out the rows already carry the conditioning: every shedding
row in the 42-cell census has `hygiene_calls` ≥ 1, and
`load_end_epoch_gec` is the load after the epoch's last wash — the
readout's `event_end` arm *is* the post-wash post-visit sample. The
answer is negative: pooled event post-wash positivity **35.3%**
(7,343/20,774 rows, positive mean 2.93 log10) vs routine post-wash
**17.6%** (55,246/314,152) — ordering stays `event_higher`, ~2×, in
both blocks (classic 33.9% vs 17.6%; fl_spr 35.8% vs 17.6%). Liu's
comparator reads post-bathroom 12.4% @2.30 *below* routine 37.5%
@3.32. The wash is nearly inert on the event arm
(post_defecation 35.9% → event_end 35.3%, ~0.6pp): the fresh event
load sits ~entirely inside the protected compartment by the time the
wash runs, so the post-visit wash only sees the accessible sliver.

**What this makes the miss be.** Not a sampling lens — a mechanism
property. Liu's wash drops post-visit hands *below* routine because a
real wash acts on freshly-deposited accessible contamination. Ours
cannot: the protected sequestration (`10^U(log10 50, log10 3200)`
GEC) draws **at the event instant**, so there is nothing accessible
left for the wash to strip. Inference (hypothesis, not implemented):
real subungual/crease colonization accrues over contact-time, not at
the visit instant — a delayed accessible→protected transfer (hours,
like the drying wet-window) would let the post-visit wash strip the
fresh accessible load first and is the plausible honest shape of the
Liu ordering. That is a mechanism-scope decision — Benjamin's call,
recorded in the outstanding ledger.

**Delayed sequestration — declared and implemented (2026-10-01,
approved).** Benjamin approved the mechanism-scope rebuild: a
contaminating visit's sequester draw (`HAND_PROTECTED_SEQUESTER_GEC_RANGE`
unchanged, Liu-bounded logU(50, 3200)) now lands in
`hand_protected_pending_by_pathogen` and settles into the protected
compartment at a per-infection exponential rate with timescale τ ∈
`HAND_PROTECTED_SEQUESTER_HOURS_RANGE` = U(24, 72) h — order-days,
declared Grade C: McNeil 2001 (Clin Infect Dis 32:367, artificial-nail
pathogen colonization 21% positive day-1 → 71% day-15) plus McGinley
1988's standing ~10⁵-CFU subungual reservoir bound the shape; no
mass-accretion-rate series exists (`?nr`). Post-visit washes now act on
the fresh accessible load first — the measured event-post-wash vs
routine ordering gets its honest shot at flipping toward Liu. Pending
mass is not rinse-visible until it settles; the practice dict carries
one extra per-infection uniform (τ). Whether routine-row occupancy
holds the R = 0.737 band — and whether ordering flips — is the frozen
42-cell re-census, pending at merge.

**Re-census — measured (2026-10-02, `a3c76061`, rev 7 digest-pinned).**
All 42 frozen cells re-censused on the delayed-sequestration arm
(`campaign/noro_hand_carriage02/`, jobdef `picard-hand-occupancy:7`,
canary seed 8105 inspected clean before the arrays). One void
(classic seed 8004, zero fomite deliveries — the declared rule).
Verdict stays **`partial`**, and the ordering miss narrowed ~40%:

- Occupancy 18.91% vs Liu 25.35% → **R = 0.746**, inside the restored
  [1/3, 3] band (was 0.737). The starvation repair held.
- Ordering still `event_higher`: post-defecation 26.96% vs routine-end
  18.46% pooled (was 35.9% vs ~17.6% — the event arm dropped ~8pp
  while routine held; the queued sequester no longer outruns the
  post-visit wash). Both blocks agree (fl_spr 26.7/18.5;
  classic 27.5/18.4).
- Positive-mean 2.59 log10 and never-positive 0.576 both in-window.
- The residual ordering miss is the event-deposit magnitude question:
  the fresh accessible event deposit keeps event rows above routine
  for the epoch it is sampled in, before any sequester settles — a
  different knob from sequestration timing and the next declared-scope
  decision, recorded in `norovirus_open_ledger.md`.

Process: `tools/noro_diag/hand_occupancy_readout.py` was OOM-killed on
this box while materializing ~13M shedding-row dicts; its pooled and
per-block aggregation is now a one-pass streaming fold (validated
bit-exact against the previous helpers on a full cell — positivity,
mean, sd, never-positive, all three ordering arms, wet window).
