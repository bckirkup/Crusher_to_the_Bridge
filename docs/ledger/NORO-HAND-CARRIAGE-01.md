# NORO-HAND-CARRIAGE-01
**Date:** 2026-10-01
**Commit:** #810
**Pathogens:** norwalk_gi, sars_cov2_resp
**Status:** open

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
