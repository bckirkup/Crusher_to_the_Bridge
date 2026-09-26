# SMALLN-01
**Date:** 2026-09-26
**Commit:** fbad8738
**Pathogens:** all
**Status:** measured
**Measured at:** fbad8738

## What this entry decides

CABIN-FLOOR-02 left four anomalous cells. This entry classifies each as a
**dead channel** (a gate/route/host term annihilated the dose), an
**under-exercised probe** (the slot yield could not support a conclusion), or a
**real miss** (mechanism fired, dose delivered, verdict stands). The four
arms are `clostridioides_difficile`, `measles_virus`,
`vibrio_cholerae_parahaemolyticus` and `andes_hantavirus` in the edison
bundle (`data/pathogens/edison_10pathogen_profiles.json`).

No fix, no constant change, no profile edit is made here, and no new anchor is
adopted.

Settled inputs, not re-derived: `docs/ledger/CABIN-FLOOR-02.md`,
`tools/cabin_floor_probe.py`, `classic_cruise_1900`, 288 epochs, paired seeds
8105/8106, declared SOP-017 confinement day 1 → end.

## Instrument

`tools/smalln_diag/confined_challenge_trace.py` wraps
`TransmissionCore._resolve_pathogen_challenge` and re-runs
`cabin_floor_probe.run_arm` unchanged — same bundle, same arm isolation, same
explicit seeds, same confinement. Nothing in the engine, the profiles, or the
arm construction is modified; the wrapper only records, per challenged host:
challenge count, post-efficiency pathway dose, protection, effective dose,
persistent dose-response susceptibility, per-epoch hazard, and conversion.

All four arms reproduced their CABIN-FLOOR-02 cells exactly (c.diff 0/81 +
0/62 = 0/143; measles 0/2 + 1/1 = 1/3; vibrio 0/3 + 1/3 = 1/6; andes 0/2 +
1/1 = 1/3), which is the local end-to-end canary for this instrument: the
probe ran, and the dose/event fields are populated. No Batch job was
submitted.

"Σ hazard" below is the summed naive per-epoch hazard
\(\sum_t -\mathrm{expm1}(-s\,d_t)\) over the voyage — the model's own expected
conversion count, which the cascade requires before any "blocked" claim.

## Cascade result common to all four cells (measured)

| Arm | seed | challenges with dose > 0 | challenges blocked by protection | Σ hazard, all hosts | Σ hazard, confined non-index | slots | secondaries |
|---|---|---|---|---|---|---|---|
| c.diff | 8105 | 15,185 | 0 | 0.00301 | 0.000974 | 81 | 0 |
| c.diff | 8106 | 9,385 | 0 | 0.0313 | 0.0312 | 62 | 0 |
| measles | 8105 | 129,860 | 0 | 1.255 | 1.255 | 2 | 0 |
| measles | 8106 | 184,492 | 49 | 3.320 | 3.320 | 1 | 1 |
| vibrio | 8105 | 621 | 0 | 0.594 | 0.258 | 3 | 0 |
| vibrio | 8106 | 327 | 0 | 3.446 | 0.636 | 3 | 1 |
| andes | 8105 | 203,149 | 0 | 0.0579 | 0.0579 | 2 | 0 |
| andes | 8106 | 256,126 | 0 | 1.445 | 1.445 | 1 | 1 |

**No cell is a dead channel.** In every arm the mechanism fired (event count
≫ 0), the declared routes carried non-zero post-efficiency dose, protection
annihilated nothing on the scored slots (the only non-zero protection is
measles seed 8106 agent 1089, already an index case), and the observed
conversion count is within the range the summed hazard predicts. No
forced-challenge trace is therefore required by the cascade: no blocker is
being alleged.

Post-efficiency pathway dose (voyage totals, both seeds):

| Arm | direct_contact | droplet | hvac_airborne | fomite | environmental |
|---|---|---|---|---|---|
| c.diff | 0.33 / 0.40 | 0 | 0 | 18.3 / 160.2 | 0.082 / 0.087 |
| measles | 7.8e-05 / 1.9e-04 | 31.6 / 71.0 | 2.6e-05 / 1.2e-04 | 0.022 / 0.025 | — |
| vibrio | 0.112 / 0.611 | 0 | 0 | 197.4 / 858.5 | — |
| andes | 1.2e-06 / 1.6e-05 | 5.79 / 150.8 | 9.1e-04 / 0.0147 | 6.3e-05 / 0.0098 | — |

Dose quantities are diagnostic evidence from this instrument only. They are
not anchors and not fitted constants; every dose figure in the repository is
void pending the refit recorded in `docs/norovirus/norovirus_open_ledger.md`.

## Instrument caveat found while measuring (measured)

The channel-dose, `lambda_confined_*` and `implied_sar` columns of
CABIN-FLOOR-01/02 are tallied from `ContactTracingMatrix` exposure records,
which `TransmissionCore` writes **before** `_apply_route_efficiencies` scales
each pathway by the profile's route weights. For c.diff and vibrio — whose
`droplet` and `hvac_airborne` weights are both 0.0 — the archived ledger books
pool+plume dose of 1e5–1e7 while the dose the engine actually delivered on
those routes is exactly 0.0 (table above).

Inferred: the pair-ledger λ column is a pre-efficiency exposure statistic and
must not be read as delivered dose for any pathogen with a zero route weight.
The slot and secondary counts are unaffected — they are read from infection
state — so all CABIN-FLOOR-02 verdicts stand as counts.

## Cell 1 — `clostridioides_difficile` 0/143 vs ~5% floor

**Classification: under-exercised probe (denominator composition), not a dead
channel.**

Measured:

- 15,185 / 9,385 dose-bearing challenges; fomite and direct-contact dose
  non-zero; protection blocked nothing; every scored host's cached
  susceptibility is the profile's exponential `k` = 0.001.
- Σ hazard over confined non-index hosts is 0.000974 (8105) and 0.0312
  (8106): the model expects **0.032 secondaries in 143 slots**, i.e. ~0.02%
  per slot. The best-exposed single slot in each arm reaches P = 0.079%
  (8105) and 3.07% (8106).
- The arm carries 153 (8105) and 113 (8106) infected hosts against **2**
  planted index seeds, because the c.diff profile boards by prevalence
  (`boarding.mode: prevalence`, passenger and crew 0.076) with
  `never_symptomatic_fraction` 0.9. 83 and 63 confined cabins held a case.

Inferred: ~90% of the 143 scored slots are cabins whose index is a
**never-symptomatic boarding carrier** shedding on the asymptomatic curve
(`asymptomatic_shedding_log10` peak 5.0) rather than a CDI patient
(`shedding_curve_log10` peak 8.0). The ~5% cabin-mate floor describes
household/roommate acquisition from symptomatic CDI, so the denominator is
large but composed of the wrong index state: 0/143 excludes 5% for *this*
arm (Clopper-Pearson upper 2.55%) while saying nothing about the arm the
floor describes.

Hypothesis (not measured here): a symptomatic-index arm would raise delivered
cabin-mate dose by up to the ~3 log10 gap between the two shedding curves and
could approach the floor without any change to the transmission code.

Denominator repair: suppress `boarding.prevalence` for the arm and plant
explicit symptomatic index cases in distinct cabins — k = 16 single-passenger
seeds per voyage gives ~30 symptomatic-index slots over the 8105/8106 pair,
versus ~15 paired voyages (30 seeds) if the party-shaped seeding is kept.

Report-immediately check: c.diff's zero is **not** a shared gate. Nothing was
annihilated; the fomite and contact routes that would also serve scored
pathways delivered dose in this very arm.

## Cell 2 — `measles_virus` 1/3 vs 75–90% floor

**Classification: under-exercised probe.**

Measured:

- 129,860 / 184,492 dose-bearing challenges; droplet dose 31.6 / 71.0;
  cached susceptibility 0.5 (the profile's exponential `k`).
- Only 2 and 1 confined slots exist because only 2 and 3 hosts were ever
  infected in the arm: the probe plants `count = party size` = 2 explicit
  seeds as a travelling party, so the index cases occupy 1–2 cabins and
  nothing else on the ship converts. In seed 8106 both seeds shared a cabin
  (agent 1089 is an index and was itself challenged at protection 1.0),
  costing one slot.
- Per-slot conversion probabilities implied by the measured hazard: 0.670 and
  0.136 (8105, 0 observed), 0.964 (8106, 1 observed). Expected conversions
  1.77 across the 3 slots; observed 1.

Inferred: 1/3 = 33% is not distinguishable from the 75–90% floor —
Clopper-Pearson 95% CI [0.8%, 90.6%] — and it is not distinguishable from the
model's own 59% expectation either. This is a denominator failure, not a
mechanism finding; the droplet channel is manifestly alive.

Denominator repair: slot yield is bounded by index cabins, ~1.5 per voyage.
To put the CI upper bound below 0.75 at a ~1/3 truth needs ≥10 slots (upper
0.653 at 10, 0.592 at 20). Cheapest shape: replace the party seed with k = 10
independent single-passenger index cases in distinct cabins, giving ~20 slots
across the 8105/8106 pair; keeping the party shape instead needs ~14 paired
voyages (28 seeds).

## Cell 3 — `vibrio_cholerae_parahaemolyticus` 1/6 vs ~0 floor

**Classification: real miss (high).**

Measured:

- 621 / 327 dose-bearing challenges from 3 planted index cases per arm; 3
  confined slots per arm out of 510 / 894 confined cabin targets (a cabin
  scores only when it holds a case).
- Delivered dose is almost entirely **fomite** — 197.4 and 858.5 against
  direct-contact 0.11 and 0.61 — and `droplet`/`hvac_airborne` are exactly
  0.0 post-efficiency.
- Σ hazard on confined non-index hosts: 0.258 (8105) and 0.636 (8106);
  per-slot conversion probabilities 0.227 and 0.471 for the two exposed
  slots, everything else ≤ 7e-04. Expected conversions ≈ 0.70 over 6 slots;
  observed 1. The one secondary (agent 1054, seed 8106) took 317.8 units of
  fomite dose at susceptibility 0.00205 — a 47% coin, not a fluke draw.

Report-immediately check: the miss-high does **not** trace to emission leaking
through a route this pathogen should not have. Fomite is a declared vibrio
route (`transmission_routes: food, water, direct_contact, fomite`, fomite
efficiency 0.15) and the airborne routes delivered literally zero.

Inferred: the model's own hazard, not the small denominator, is what misses
the ~0 person-to-person floor. Even at n = 6 the verdict stands, because the
expected count (0.70) is itself incompatible with ~0; enlarging the
denominator would sharpen the rate but cannot rescue it.

Flagged for the anchor/audit session. The quantities that need an anchor
before this miss can be sized: (a) the cabin fomite surface-transfer dose
delivered to a confined cabin-mate per index-day for *V. cholerae* /
*V. parahaemolyticus*, and (b) the beta-Poisson susceptibility scale that
turns it into hazard (`alpha` 0.25, `beta` 16.2 in the profile). Note also
that the arm's dominant declared route, food contamination (weight 0.70),
delivered no dose at all under cabin confinement — passengers never reach a
galley-fed venue — so the confined arm tests the fomite term alone.

## Cell 4 — `andes_hantavirus` 1/3 = 33% vs 1.2–3.4% floor

**Classification: under-exercised probe, with a dose-scale miss flagged as
hypothesis.**

Measured:

- 203,149 / 256,126 dose-bearing challenges; droplet dose 5.79 / 150.8;
  cached susceptibility 0.01 (exponential `k`); protection blocked nothing.
- 2 and 1 confined slots, for the same reason as measles: 3 party-shaped
  index seeds occupy 1–2 cabins and the arm produces 3 and 4 infections
  total.
- Per-slot conversion probabilities: 0.054 and 0.0019 (8105, 0 observed),
  0.764 (8106, 1 observed). Expected conversions 0.82 over 3 slots; observed
  1.

Inferred: 1/3 is uninformative against a 1.2–3.4% floor — Clopper-Pearson
[0.8%, 90.6%] contains the floor — and matches the model's own 27%
expectation, so the *rate* is a small-n artifact. What is not small-n is the
single 150.8-unit droplet dose that produced a 76% conversion probability in
one confined cabin: one slot at that exposure is already inconsistent with a
1.2–3.4% per-contact floor.

Hypothesis: the confined droplet dose scale for andes (emission per index-day
into a cabin's berth share, times exponential `k` = 0.01) is too high by
roughly the factor that moves a 0.76 slot to ≤0.034. Sizing that needs an
anchor for andes person-to-person secondary attack among household/cabin
contacts and for aerosol emission per index-day — named, not adopted, here.

Denominator repair: same shape as measles — k = 10 single-passenger index
cabins per voyage, ~20 slots across the seed pair, which separates a 3% floor
from a 30% rate.

## Summary

| Cell | Classification | Mechanism fired | Σ hazard (confined, both seeds) | Decisive evidence |
|---|---|---|---|---|
| c.diff 0/143 | under-exercised probe (denominator composition) | yes | 0.032 | 143 slots but ~90% carrier-index; 0.02% expected per slot |
| measles 1/3 | under-exercised probe | yes | 4.58 | only 3 slots exist; CI [0.8%, 90.6%] |
| vibrio 1/6 | **real miss (high)** | yes | 0.894 | 0.70 expected conversions vs ~0 floor, fomite route, no leak |
| andes 1/3 | under-exercised probe (+ dose-scale hypothesis) | yes | 1.503 | 3 slots; one 76% slot against a 1.2–3.4% floor |

No dead channel among the four. One real miss (vibrio) goes to the
anchor/audit session. Three cells need a denominator, not a repair; the
arm-shape change that produces one (independent single-passenger index cabins
instead of a party seed) is the same for all three and is a probe-design
decision, deliberately not made here.
