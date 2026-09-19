# NORO-SUSCEPT-02
**Date:** 2026-09-19
**Commit:** dbddd47
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 9f4cd79

Per-host join of credited dose against evaluated challenge, to settle the one
open finding of `NORO-SUSCEPT-01`: a whole-run summed naive hazard of 0.197
against 394,281 GEC credited is an ordinary draw only if the dose effectively
reached one or two hosts, while the recovered per-host maximum (49,572 GEC,
12.6% of the total) needs at least eight. Either the credited dose and the
evaluated hazard are taken over different host sets, or they are taken over
different quantities.

## Attribution criterion, declared before the run

Runs: seeds 8105 and 8106, `classic_cruise_1900` at its declared complement
(1,910 agents), 288 epochs, shipped `data/pathogens/active_profiles.json`, no
configuration, profile or constant override. The two arms differ from a shipped
run only by read-only wrappers
(`tools/noro_diag/per_host_dose_challenge.py`).

Statistics, in the order they are read:

1. `hosts_for_90pct` — the number of hosts holding 90% of the dose credited to
   `agent_pathogen_doses` over the voyage.
2. `dose_to_never_evaluated_hosts_gec` — dose credited to hosts for which
   `_dose_response_hazard` was never evaluated, and its share of the credited
   total, classified by the state that held at the crediting epochs
   (infected, immune/recovered, secretor-negative) and by the exit reason
   recorded at `_resolve_pathogen_challenge`.
3. The reconciliation chain, each term measured at its own seam: mass
   accumulated by `_accumulate` → dose credited after the route-efficiency
   multiplier → dose scaled by `susceptibility_multiplier` in
   `_merge_pathogen_doses` → dose read at `_resolve_pathogen_challenge` →
   effective dose passed to `_dose_response_hazard` → summed hazard.
4. Emesis witness counters: `draw_emesis_schedule` calls, scheduled episodes,
   `_emit_emesis` events, patch mass filed, patch-pickup sweeps that found a
   filed patch, sweeps whose filed unit matched a pickup unit, susceptible
   occupants at those matched units, and `_emesis_patch_pickup_one` deliveries.

Decision rules, fixed before execution:

- **Host-set mismatch is declared** only if `dose_to_never_evaluated_hosts_gec`
  exceeds 1% of the credited total in *both* seeds. Below that, the
  "different host sets" reading of the open finding is refuted and the
  divergence must be named as a quantity mismatch instead, at the specific
  seam where two adjacent terms of the chain disagree.
- **Concentration** is reported as measured; no threshold is attached to it,
  because `NORO-SUSCEPT-01`'s eight-host floor is an arithmetic consequence of
  its own recovered maximum and is not re-derived here.
- **The emesis pathway is declared to fire** only if a witness counter is
  non-zero at every link: schedule draw, emitted event, filed patch, matched
  pickup unit, and a delivered patch dose. A single witness in a single seed is
  sufficient for existence. Zero at a link in both seeds is a blocker claim at
  that link, and is entered as its own finding.
- Two seeds cannot bound a rate. No per-voyage rate, attack rate or secondary
  count is claimed from this measurement, and nothing here is fitted or
  selected: reported but not selected are `hosts_for_50pct`,
  `hosts_for_95pct`, `hosts_for_99pct`, the per-route dose split, the fomite
  transfer-chain terms, and the per-host hazard sums.

## Result

Both arms ran to completion: `classic_cruise_1900`, 1,910 agents, 288 epochs,
seeds 8105 and 8106, shipped bundle, no override. The per-seed JSON dumps —
every one of the 1,910 hosts with its credited dose, crediting epochs,
persistent frailty, challenge count and hazard sum, plus the run-level
reconciliation and witness blocks — are committed gzipped next to this entry as
`docs/norovirus/noro_suscept_02/per_host_dose_challenge_seed{8105,8106}.json.gz`
(1.8 MB and 1.1 MB raw). Regenerate with
`python3 tools/noro_diag/per_host_dose_challenge.py --epochs 288 --seeds 8105
8106 --out docs/norovirus/noro_suscept_02`.

### a. Dose is not credited to hosts that are never challenged

| Quantity | seed 8105 | seed 8106 |
|---|---|---|
| Hosts credited any `norwalk_gi` dose | 1,441 | 187 |
| Hosts with at least one evaluated challenge | 1,441 | 187 |
| **Hosts credited but never evaluated** | **0** | **0** |
| **Dose to never-evaluated hosts** | **0 GEC** | **0 GEC** |
| Crediting host-epochs | 251,824 | 6,928 |
| ... of those, challenge evaluated the same epoch | 251,824 | 6,928 |
| ... host infected at the crediting epoch | 0 | 0 |
| ... host immune/recovered at the crediting epoch | 0 | 0 |
| ... host secretor-negative at the crediting epoch | 48,457 | 725 |
| `_resolve_pathogen_challenge` exits: `evaluated` | 251,824 | 6,928 |
| ... `no_dose_this_epoch` | 297,296 | 542,642 |
| ... `resident_superinfection_closed` | 960 | 510 |

The declared 1%-of-credited threshold is not approached: the never-evaluated
share is exactly zero in both arms. No host was credited dose while infected,
immune or recovered, and no host was credited dose in an epoch whose challenge
was skipped. The only hosts skipped at `_resolve_pathogen_challenge` are the
resident index cases under a closed superinfection door (960 and 510
host-epochs, i.e. 4 and 2 imports carried to the end of the voyage), and they
are credited no dose at all. Secretor-negative hosts are challenged like
everyone else: their `secretor_negative_relative_susceptibility` 0.20 enters as
the `susceptibility_multiplier` in `_merge_pathogen_doses`, before the
challenge, which is why `sum_credited_scaled` is below `sum_credited_raw`
(0.1010 vs 0.1230 GEC at seed 8105; 236 of 1,910 hosts carry the 0.20
multiplier, 25 at 8106).

**The "different host sets" reading of the open finding is refuted.**

### b. The challenge reads exactly what the accumulator credited

Measured at each seam of the chain, whole run (GEC):

| Seam | seed 8105 | seed 8106 |
|---|---|---|
| `_accumulate` mass, all routes | 0.409361 | 0.009683 |
| credited after route-efficiency multiplier (`sum_credited_raw`) | 0.122967 | 0.002906 |
| after `susceptibility_multiplier` (`sum_credited_scaled`) | 0.100952 | 0.002713 |
| dose read at `_resolve_pathogen_challenge` | 0.100952 | 0.002713 |
| effective dose passed to `_dose_response_hazard` | 0.100952 | 0.002713 |
| Σ evaluated hazard | 3.8091e-04 | 1.1871e-05 |

The last three lines agree to the last recorded digit, in both arms: the
challenge reads the *per-epoch* dose the accumulator credited that epoch, not a
residue of it, and not the voyage total. `protection` is 0.0 for every host, so
effective dose equals dose read. The per-epoch structure loses nothing at these
magnitudes — the summed naive hazard recomputed per host from the voyage total
and the host's persistent frailty (`naive_hazard_all_credited_hosts`) is
3.80909e-04 against the engine's 3.80909e-04 at seed 8105, and 1.18710e-05
against 1.18710e-05 at 8106. `Σ credited dose` and `Σ evaluated hazard`
therefore reconcile exactly, over the same host set, at the same seam. **There
is no divergence line to name inside the dose→hazard chain.**

### c. Concentration of credited dose

| Quantity | seed 8105 | seed 8106 |
|---|---|---|
| Hosts credited | 1,441 | 187 |
| Max per-host credited dose | 0.009518 GEC (9.4% of total) | 0.000435 GEC (16.0%) |
| **Hosts holding 90% of credited dose** | **106** | **48** |
| Hosts holding 50% / 95% / 99% | 21 / 139 / 194 | 10 / 65 / 96 |
| Persistent frailty, median (min–max) | 6.85e-05 (4.6e-27 – 0.118) | 4.40e-05 (8.4e-28 – 0.054) |

The dose is spread over roughly a hundred hosts, which is the shape
`NORO-SUSCEPT-01` inferred from its recovered per-host maximum. What it is
*not* is 394,281 GEC.

### d. Where the open finding's two numbers actually diverge

The divergence is not between host sets; it is between two different
quantities, and it sits **upstream of `_accumulate`, in the fomite transfer
chain**, measured here (seed 8105, whole run):

| Term | seed 8105 | seed 8106 |
|---|---|---|
| Max per-host hand load / hand target | 139,245 GEC | 1.97 / 165 GEC |
| Emesis patch mass filed | 1,961,774 GEC | 0 |
| Surface mass offered at pickup, summed over 1,917 / 605 calls | 5,170.4 | 3.87 |
| Mass requested by `_fomite_pickup_request_for_area` | 35.13 | 1.056 |
| Mass delivered to hands | 33.03 | 1.056 |
| Dose ingested by `_hand_to_mouth_dose` | 0.6919 | 0.010276 |
| Credited to `agent_pathogen_doses` after route efficiency 0.30 | 0.1230 | 0.002906 |

Two multiplicative steps do essentially all of the work: the pickup request
takes 0.68% of the mass offered (`_fomite_pickup_request_for_area`: surface
contacts × used fraction × hand area / the unit's high-touch area ×
surface-to-hand transfer efficiency), and `_hand_to_mouth_dose` takes 2.1% of
the hand load. A quantity read at the top of that chain is five to six orders
of magnitude above the dose the challenge is evaluated on.
`NORO-SUSCEPT-01` §1 records `raw_fomite_in_sum` = 394,281 GEC
as "dose credited in full" — a 1.11 GEC mean per accumulate call, against the
4.0e-07 GEC per call measured here at the same seam on the same hull and epoch
count (304,929 calls, seed 8105). The recovered figure is of the order of the
*hand-load and patch-mass* ledger (1e5–1e6 GEC), not of the credited-dose
ledger. Its diagnostic does not exist in the repository and cannot be re-read,
so this entry does not assert which line it summed; what is measured is that no
quantity at or below `_accumulate` is within five orders of magnitude of it,
and that the credited/evaluated pair reconciles exactly once both are read at
the same seam.

So the open finding's premise — "these cannot both be true" — resolves as a
seam mismatch between a recovered pre-transfer mass and a measured
post-transfer dose. The measured hazard sums are 3.8e-04 and 1.2e-05, three to
four orders below the recovered 0.197; zero secondaries is the correct draw at
either figure (`transmission-blocker-cascade` step 0).

### e. The emesis pathway fires

Witness counters, seed 8105 (one imported index case reached a vomiting
presentation; seed 8106 drew none, so its whole emesis chain is untouched —
`schedule_draws` 0, which is why a single positive arm is what the criterion
required):

| Link | seed 8105 | seed 8106 |
|---|---|---|
| `draw_emesis_schedule` calls / episodes scheduled | 1 / 3 | 0 / 0 |
| `_emesis_phase` eligible / blocked | 24 / 550,056 | 0 / 550,080 |
| `_emit_emesis` deposition records created | 1 | 0 |
| Patch mass filed | 1,961,774 GEC | 0 |
| Pickup sweeps finding a filed patch / matching a pickup unit | 274 / 274 | 0 |
| Susceptible occupants at matched units | 263 | 0 |
| **`_emesis_patch_pickup_one` calls / deliveries / dose to hands** | **263 / 2 / 2.610 GEC** | 0 |

Every link is non-zero at seed 8105, ending in mass actually delivered from the
patch to a host's hands, which then enters the same `_hand_to_mouth_dose` →
`_accumulate` path as the zone pool. The patch was filed in the emitter's own
stateroom compartment (`CC_D1_F::cabin1581`) as the `EMESIS-FOOTPRINT-01`
repair specifies — localised to the bolus footprint, not the zone pool — and it
reached a cabin mate only in the epochs the mate was co-present and still
susceptible (263 of 274 matched sweeps). **The emesis pathway is not blocked
at this SHA.**

Two observations are recorded but not claimed as findings, because two seeds
cannot size either: only 1 of 3 scheduled episodes became an emitted event, and
a patch confined to a single-occupancy compartment has no reachable susceptible
at all (seed 8105's 24-epoch prefix shows exactly that:
`matched_unit_susceptible` 0 over 10 sweeps). Both are candidates for a
replicated measurement, not for a change.

## Consequence for `NORO-SUSCEPT-01`

Its open finding is answered: the credited dose and the evaluated hazard are
taken over the same host set, at the same seam, and reconcile exactly, with
zero dose reaching a host that was never challenged. `NORO-SUSCEPT-01` is
closed by this entry. Its §1 recovered figures keep no `Measured at` SHA and
must not be quoted as credited dose: `raw_fomite_in_sum` = 394,281 GEC and
`raw_fomite_in_max` = 49,572 GEC are void as credited-dose figures at this SHA.

Nothing here is fitted or selected, and no constant is changed or recommended
for change by this entry. With (2) and (3) both clean, the admissible next move
is the expectation itself: α swept within [0.072, 0.161] with β held fixed, as
a declared swept axis, never a refit and never chosen against VSP — its own
session with its own paired-seed measurement.
