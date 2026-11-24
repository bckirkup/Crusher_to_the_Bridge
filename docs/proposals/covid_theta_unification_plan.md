# DP θ unification plan — why single-mechanism arms keep failing, and the suite order that fixes it

> **Status:** Proposal (2026-11-23), written on Benjamin's "we write up the
> approach and start" after DP-THETA-FIT-01 read out; filed under
> `proposals/` until the arm it specifies exists in-tree. Reports no new
> numbers — every figure is quoted from the ledger entry or readout that
> measured it, with that entry's `Measured at` SHA. Nothing here is a fit.
> Each suite's own design file freezes its scored criteria before any cell
> runs; this plan names the legs, the order, and what each suite decides.
>
> **Owner decisions recorded (2026-11-23):**
> (a) envelope/conditioned scoring is **adopted** — but as a joint
> multi-objective contract, not a single observable (§5);
> (b) the measured airborne fine share is **adopted** as
> `airborne_emission_fraction` — it lands as its own leg before any θ is
> named (§4).

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
| Record's testing structure: `retest_tiers` (already declared scenario data on every arm — the truthful replica carries serial testing regardless; `CREW-REACH-01` erratum) **plus** the 23 Feb `crew_wave` (831 crew-only) and the optional retest sweeps armed | `CREW-REACH-01` (+535/+97 lab_confirmed toward record) | `crew_wave`/`retest_negative_sweeps` are arm-gated; `dp_theta_fit_01` deliberately left both unarmed |
| Conditioned capture basis (`confirmed / infections_reachable`) | `COVID-CAPTURE-01` | adopted scored basis (owner call) |
| Index day-0 participation channel (muster / boarding-crush geometry) | IGNITION-01 + SEED-RING-01/02 | **not expressible yet** — Suite 2 decides whether it must be built |
| Routine-stage contact redeclaration (Pung-anchored `activity_contacts` or voyage-stage routine multiplier) | `covid_voyage_stage_contacts_evidence.md` | **deferred declaration** — Suite 3 decides |
| Fixed rings / cabin-mate addback | ROUTE-ATTR-V1 (~⅓ of droplet dose weight) | **inexpressible in arm grammar** — Suite 4 only |

The joint conditioned contract (all legs frozen per cell, before any cell
runs, and each scored on the *conditional* distribution — see §5):
T3 campaign positives through day 31; the onboard-table 691/3,894
cross-check through Feb 23 (crew wave armed); during-quarantine mass band
[150,350]; `before_share` vs 0.173 ± band; conditioned capture; founder
yield reported; ignition day scored in the §5 timing leg. A θ that lands
all legs at once is the "consistent θ" the program has been missing; the
outcome per leg at every θ names the next structure, not a refit.

## 3. Suites, in order (weakest assumption first)

**Suite 1 — union test, config-only.** `replay_niid` + FRAQMB_DUTY-analog +
armed `crew_wave`/retest sweeps + the conditioned contract of §5. θ grid on
the **post-fine-share scale** (§4 gate), 24 matched seeds
20200205–20200228. Everything already expressible; no engine work. Decides:
does *one* θ satisfy the joint conditioned contract on the united arm — the
first honest "consistent θ" test, and the first run of the 691-cross-check
that FIT-01 left unrun. **Split-verdict rule:** legs may pass at disjoint
θ — that outcome is itself the measurement; the disjoint leg-pair names the
opposing structures (e.g. growth-rate vs tail composition) and becomes the
next structural question, the same way a leg failing at every θ does.

**Suite 2 — participation falsification probe.** Pin the index's day-0
itinerary deterministically inside the declared surge venues
(muster/terminal/boarding crush) vs the drawn-itinerary baseline, matched
seeds. Frozen criterion is an *improvement over the matched baseline*, not
the bare biconditional: the pinned arm must lift median founder yield to
≥10 with ignition ≤9 where the same seeds on drawn itineraries do not.
SEED-RING-02 showed the mechanism fires as a lottery (6/20 seeds hit
record-class pools when the draw lands in the geometry) — this tests
whether *forced* participation is sufficient before the participation
channel is built.

**Suite 3 — routine-stage coolant.** Resolve the Pung close-contact
threshold → Polymod-class mapping (the deferred §6 question), then declare
the routine stage (Pung-anchored `activity_contacts`, or a voyage-stage
routine multiplier). Frozen two-leg prediction: founder median ≥10 AND d15
infections inside a bound declared at freeze from the record's
*pre-quarantine* evidence (the day-16 arrest plus pre-quarantine
confirmations) — not from the held-out band or from whole-voyage capture,
which bounds only total reachable infections and says nothing about day
15. EARLY-GROWTH-01 measured the overshoot as a d15 median of 1,292.
Decides whether a declared routine stage cools
sustained growth without touching θ — the untested half of the growth bound.

**Suite 4 — engine work, only if 1–3 still fail.** Fixed-ring addback made
arm-expressible, plus the onset-dating channel probe (ROUTE-ATTR-V1 measured
dating ascertainment ≈3.4× of the ~18× recorded-onset gap; recorded_onsets
~2.9k vs 197 is the largest single channel residual).

## 4. Gates and exclusions

- **Fine-share lands first (owner decision 2026-11-23).** The measured
  airborne fine share (declared interval [0.76, 0.92], Coleman's 0.85 inside
  it, tranche-27 license; `COVID-EMIT-LEVEL-01`) is adopted as
  `airborne_emission_fraction`, replacing the shipped 5e-5
  (COVID-EMIT-FINE-01, PR #1412). Measured scope of the move (read from
  code, not assumed): only the **zone airborne pool deposit** rises ×1.7e4
  — the profile fraction is read at one site
  (`orchestrator_epoch._accumulate_pathogen_zone_mass`); the droplet route
  uses the uniform `DROPLET_AEROSOL_FRACTION = 0.05` and does not read it,
  and direct/fomite do not either. Graywater reads the same pool, so
  earlier wastewater read mixes are pre-change. The route mix therefore
  shifts toward the room-pool airborne route — old θ values are old-unit
  and **cannot be converted by dividing by 1.7e4**; a new θ must be fit on
  the new scale. This is its own leg with its own attribution, sequenced
  before Suite 1 names a θ grid: the union design's grid is declared on the
  post-adoption scale and no fit runs in old units.
- **Retired axes are not legs.** SUSCEPT-V1, HEAT-V1, SEED-GEOM-V1,
  PROPENSITY-V1, COVID-HAND-AB-01, COVID-COOP-V1, index dining placement,
  windowed embarkation intensity, dose-law/θ-alone — all measured and
  retired; none is re-proposed.
- **GM stays held-out; H5 stays held-out-forever.** imports>1 remains a
  falsification probe, not an axis.
- **Capture basis is conditioned** (`confirmed / infections_reachable`);
  the unconditioned ~0.52 is the structural post-window residual.

## 5. The adopted contract: envelope scoring with a joint objective set

Benjamin rescoped to envelope/conditioned scoring (2026-11-23), with the
explicit caveat that the record's observables form a complex objective set,
not one number. Under this contract the outbreak record is treated as a draw
of the founder lottery: legs are scored on the distribution *conditioned on
the founder class* (e.g. takeoff-class seeds, the conditioned capture basis)
rather than on unconditional medians, but **every leg is still scored** —
the envelope widens *which draws count*, it does not drop objectives:

| Objective leg | Record quantity | Status |
|---|---|---|
| Timing | ignition day, onset-peak at confinement (d13–15), `before_share` 0.173 ± band | measured targets |
| Attack rate | the record's final confirmed count = 712 (~19% of 3,711 aboard); implied infections via the conditioned capture | no fit-target id covers the final count yet — the freeze declares it scored directly or folds it into the cross-check; `covid.T4` is the asymptomatic-share diagnostic (320/634), not this target; the serology band [712,960] is `covid.H5`'s admissible_band, held-out-forever and never a selection criterion |
| Confinement tail | during-quarantine mass [150,350], crew-skewed lag | measured band |
| Testing observables | T3 = 634/3,063 through day 31; onboard 691/3,894 through Feb 23 | scored + cross-check |
| Capture | confirmed/infections_reachable ≥ 0.80 class | conditioned basis |

What this changes and what it does not: FIT-01's θ values (3.16e9 selected,
4.22e9 interpolated) were produced on **T3 unconditional medians** — they
are the old contract's answer, and whether the same θs hold under the
conditioned contract is unmeasured; the earlier handoff's θ=3.162e8 was a
different kernel's answer and does not carry. The suites in §3 still run —
the envelope decides *how* legs are scored (conditional distribution), not
*whether* the structure is needed; the union arm still has to satisfy the
joint objective set, which is why Suite 1 is still the first leg.

## 6. Execution shape

One bounded session per leg (flat children, skeleton prompts):

1. **Fine-share adoption** (own leg): declare the value inside [0.76,0.92]
   with provenance register entry + evidence grade + attribution for every
   moved golden; merge before Suite 1's θ grid freezes. Open item it
   surfaced (a decision, not part of this plan): whether the droplet route
   should read the arm's declared share instead of the uniform
   `DROPLET_AEROSOL_FRACTION = 0.05`.
2. **Suite 1**: design freeze → campaign registration → canary (20 seeds at
   one union-arm θ cell) → stop and report; the array decision follows the
   canary per the campaign gate.
3. **Suites 2–4** spawn only on their named trigger conditions in §3, and
   Suite 2's probe precedes any participation-channel engine work.
