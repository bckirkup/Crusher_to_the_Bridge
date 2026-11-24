# DP θ unification plan — why single-mechanism arms keep failing, and the suite order that fixes it

> **Status:** Approach record (2026-11-23), written on Benjamin's "we write up
> the approach and start" after DP-THETA-FIT-01 read out. Reports no new
> numbers — every figure is quoted from the ledger entry or readout that
> measured it, with that entry's `Measured at` SHA. Nothing here is a fit and
> no epidemiological constant is proposed. Each suite's own design file
> freezes its scored criteria before any cell runs; this plan names the legs,
> the order, and what each suite decides.

## 1. The confound: θ is doing three jobs at once

Every single-mechanism arm measured on the DP record has moved one leg while
another failed. The legs are structurally independent of θ:

- **Founder-pool creation.** `COVID-IGNITION-01` (measured at `b4591170`):
  founder yield discriminates ignition day with zero overlap — ≥10
  aboard-window acquisitions → ignition ≤9; ≤5 → ignition ≥10 or dead. The
  constraint is whether the drawn index participates in day-0 surge geometry
  at all: `COVID-SEED-RING-01` (measured at `87e8e3bb`) measured
  NULL-PLACEMENT (dining-zone assignment moves nothing) and
  `COVID-SEED-RING-02` measured windowed intensity NULL on the *median*
  founder pool at α=8 — while 6/20 seeds still produced record-class pools
  when the draw lands in surge geometry. Dose cannot create participation;
  the itinerary layer cannot yet express it.
- **Post-founder growth rate.** `dp_growth_cooling_bound.md` (measured at
  `1dfac0e4`): model ramp ~1.8×/day vs the record's ~1.2×/day; homogeneous
  final-size math rules out slowdown-only arms. `COVID-EARLY-GROWTH-01`
  confirmed the overshoot is in place by day 15 on record-timed cells
  (d15 infections median 1,292 vs the [712,960] band; SEED-RING-02 leg-2
  confirmed at 2,404 under windowed uplift). Both candidate coolants the
  bound named — susceptibility ceiling and delivery-heat truncation — were
  already measured on full lattices and retired (`SUSCEPT-V1`, `HEAT-V1`).
  The remaining unmeasured coolant is the routine-stage contact structure
  itself (the Pung close-contact mapping deferred in
  `covid_voyage_stage_contacts_evidence.md` §6).
- **Confinement-era composition.** `COVID-QUAR-TAIL-SEAM-01` (measured at
  `b4591170`): only the joint quarter-exempt × symptomatic-crew-removal arm
  (FRAQMB_DUTY) lands the during-quarantine mass band [150,350] — FRAQMB
  alone reads 394, MB_DUTY alone 425, joint 257. Single-lever confinement
  fixes are falsified at the boxed θ.

And the scored observable itself compresses: `DP-THETA-FIT-01` (measured at
`6e23f0d9`) shows T3's 634 campaign positives cannot separate attack 0.47
from 0.80 (medians 600 → 735.5 across 3.16e9 → 1e10 on a fixed 3,063
specimens), and its selected θ leaves all-channel `lab_confirmed_total` at
1,282 vs the final 712. **"Consistent θ" was never testable on a single
observable** — each prior screen scored one number, so θ slid to satisfy it
and broke the others.

## 2. The most-likely-consistent combination

One declared arm carrying every measured mechanism simultaneously:

| Piece | Provenance | State |
|---|---|---|
| `replay_niid` environs (dedicated `diamond_princess` hull, real-2020 itinerary + `diamond` rhythm catalog, hour-level confinement @ epoch 391, exercise outings, passenger disposition, interior/exterior ventilation cohort, NIID index clock) | `DP-REPLAY-ENVIRON-01` | shipped, acceptance-tested |
| FRAQMB_DUTY-analog confinement composition (quarter-exempt × symptomatic-crew removal) re-declared against the dedicated hull's protocols | `COVID-QUAR-TAIL-SEAM-01` (measured on `boxed_s1s2`) | arm grammar exists; needs re-declaration on `protocols_covid_dp_dedicated.json` |
| Record's testing structure: `retest_tiers` 15–20 Feb + 23 Feb `crew_wave` (831 crew-only tests) armed | `CREW-REACH-01` (measured +535/+97 lab_confirmed toward record) | declared scenario data, arms per-scenario; `dp_theta_fit_01` deliberately left it unarmed |
| Conditioned capture basis (`confirmed / infections_reachable`) | `COVID-CAPTURE-01` | adopted scored basis (owner call) |
| Index day-0 participation channel (muster / boarding-crush geometry) | IGNITION-01 + SEED-RING-01/02 | **not expressible yet** — Suite 2 decides whether it must be built |
| Routine-stage contact redeclaration (Pung-anchored `activity_contacts` or voyage-stage routine multiplier) | `covid_voyage_stage_contacts_evidence.md` | **deferred declaration** — Suite 3 decides |
| Fixed rings / cabin-mate addback | ROUTE-ATTR-V1 (~⅓ of droplet dose weight) | **inexpressible in arm grammar** — Suite 4 only |

The joint scored contract (all frozen per cell, before any cell runs):
T3 median positives through day 31; the 691/3894 onboard-table cross-check
through day 23 Feb (crew wave armed); during-quarantine mass band [150,350];
`before_share` 0.173 ± band; conditioned capture ≥ band floor; founder yield
and ignition day reported. A θ that lands all legs at once is the "consistent
θ" the program has been missing; a leg that fails at every θ names the next
structure, not a refit.

## 3. Suites, in order (weakest assumption first)

**Suite 1 — union test, config-only.** `replay_niid` + FRAQMB_DUTY-analog +
armed retest/crew-wave + conditioned capture. ~3–4 θ spanning
{1e9, 3.16e9, 1e10} (+ the 4.22e9 interpolation point if the bracket moves)
× 24 matched seeds 20200205–20200228. Everything already expressible; no
engine work. Decides: does *one* θ satisfy the joint contract on the united
arm — the first honest "consistent θ" test, and the first run of the
691-cross-check that FIT-01 left unrun. If a leg fails at every θ the
failing leg names Suite 2 or 3.

**Suite 2 — participation falsification probe.** Pin the index's day-0
itinerary deterministically inside the declared surge venues
(muster/terminal/boarding crush) vs the drawn-itinerary baseline, matched
seeds, frozen criterion founder yield ≥10 ↔ ignition ≤9. SEED-RING-02
showed the mechanism fires as a lottery (6/20 seeds hit record-class pools
when the draw lands in the geometry) — this tests whether *forced*
participation is sufficient before the participation channel is built.

**Suite 3 — routine-stage coolant.** Resolve the Pung close-contact
threshold → Polymod-class mapping (the deferred §6 question), then declare
the routine stage (Pung-anchored `activity_contacts`, or a voyage-stage
routine multiplier). Frozen two-leg prediction: founder median ≥10 AND d15
infections ≤960 at one θ. Decides whether a declared routine stage cools
sustained growth without touching θ — the untested half of the growth bound.

**Suite 4 — engine work, only if 1–3 still fail.** Fixed-ring addback made
arm-expressible, plus the onset-dating channel probe (ROUTE-ATTR-V1 measured
dating ascertainment ≈3.4× of the ~18× recorded-onset gap; recorded_onsets
~2.9k vs 197 is the largest single channel residual).

## 4. Gates and exclusions

- **Emission fine-share first for any named θ.** The pending adoption of the
  measured airborne fine share moves every deposit ×1.7e4 and re-denominates
  the θ composite. A suite's *consistency* verdict is unit-independent and
  can run on current physics; any θ value it names carries the emission
  scale shipped at freeze and re-runs if the adoption lands mid-work.
- **Retired axes are not legs.** SUSCEPT-V1, HEAT-V1, SEED-GEOM-V1,
  PROPENSITY-V1, COVID-HAND-AB-01, COVID-COOP-V1, index dining placement,
  windowed embarkation intensity, dose-law/θ-alone — all measured and
  retired; none is re-proposed.
- **GM stays held-out; H5 stays held-out-forever.** imports>1 remains a
  falsification probe, not an axis.
- **Captured basis is conditioned** (`confirmed / infections_reachable`);
  the unconditioned ~0.52 is the structural post-window residual.

## 5. The alternative this plan does not take

The 2026-11-21 handoff's standing option: re-scope the θ contract to
envelope/conditioned scoring — the record is a ~1-in-4 lottery draw, so score
the conditional distribution rather than the median. Under that contract the
FIT-01 result (3.16e9 selected, 4.22e9 interpolated, T3-unbounded above) is
already defensible and Suites 1–4 are unnecessary. **The plan assumes
median-on-record scoring stays; choosing the envelope re-scope instead is an
owner decision that voids most of §3.**

## 6. Execution shape

One bounded session per suite leg (flat children, skeleton prompts):
Suite 1 = design freeze → campaign registration → canary (20 seeds at one
θ cell) → stop and report; the array decision follows the canary per the
campaign gate. Suites 2–4 spawn only on their named trigger conditions in
§3, and Suite 2's probe precedes any participation-channel engine work.
