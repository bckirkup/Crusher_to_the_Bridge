# COVID platform-fidelity study — pre-registration v1

Status: pre-registered, frozen before any cell ran. This document is the
criterion of record for PLATFORM-FIDELITY-01; nothing below is altered after
the first cell's surface is seen. Campaign registration:
`campaigns/covid/platform_fidelity_01/`; designs:
`picard_framework/runs/covid_platform_fidelity_{dp,gm}_design.json`.

## 1. Question

How much does hull fidelity move the two frozen 2020 COVID event replays —
the Diamond Princess training hull and the Greg Mortimer held-out hull —
when each event is replayed on its event-faithful platform versus the
generic proxy platform it currently rides, with everything else held fixed?

This is a **pre-registered sensitivity measurement**. It selects no Theta,
crowns no canonical platform, and does not reopen the train/test split. It
measures the size and sign of the platform effect so that later decisions
(e.g. whether the proxy hulls are adequate for the COVID arm) are made on a
measured number rather than an assumption.

## 2. Settled design (frozen)

Source: `docs/covid/covid_platform_fidelity_handoff_2026_11_07.md` §8.

**Primary contrast — shared Θ = 7.9e6, four arms:**

| Event pair | Proxy arm (baseline, empty overrides) | Dedicated arm (`platform_id` override) |
|---|---|---|
| Diamond Princess (training) | `mega_cruise_5000` | `diamond_princess` |
| Greg Mortimer (held-out) | `expedition_cruise_450` | `greg_mortimer` |

- Event populations fixed (3,711 DP / 223 GM); full voyage; one shared SHA;
  one emission-fraction state (5e-5, "declared not applied" per the
  provenance register tranche 27 §6).
- The platform override is campaign-level: `catalog.platform_id` is
  rewritten by the new `platform_id` arm key in
  `picard_framework/covid_boarding_screen.py`; the frozen scenario records
  and the split in `data/scenarios/covid_hull_scenarios.json` are untouched.
- Resolved `platform_id`, the frozen protocols path, per-input-file SHA-256
  hashes, and the set of protocol ids the engine activated are echoed in
  every cell payload (`platform_fidelity` block) — the payload did not echo
  `platform_id` before this campaign; that echo is part of the registration.
- DP-side debugging first; GM arms are revealed once, after the DP
  machinery is proven. The GM canary is **technical acceptance only**; Θ is
  frozen before any GM epidemiological output is examined. If GM fizzles on
  both hulls at 7.9e6, that is reported as-is — no Θ change to make GM
  informative.

**Descriptive layers (pre-declared; none selectable, none fitted):**

1. GM pair at Θ = 2.37e11 (the GM-RESCORE-02 anchor row).
2. GM θ-lattice {1e11, 2.37e11, 1e12} × both GM hulls.

No DP θ-lattice unless a pre-declared escalation rule fires (none is
declared here).

**Base configuration.** DP cells carry the boxed `sect_mess_boxed`
configuration verbatim (SOP-017-MESSBOX + the boxed caregiver-service block,
`base_overrides` in the DP design) — the operating point of the DP
believability line (`docs/covid/covid_dp_replay_handoff_2026_10_09.md` §2).
GM cells are the as-declared `greg_mortimer_2020` replay (no arm overrides
beyond the platform swap), matching the GM-RESCORE grammar.

**Frozen reading of the protocol discipline.** The handoff's "frozen
per-event-pair protocols file carrying SOP-017 only" is implemented as: each
event pair gets a frozen protocols file carrying **the single scheduled
confinement protocol the cells resolve** — `SOP-017-MESSBOX` on DP (the
boxed variant the base schedules) and `SOP-017` on GM — and **no reactive
protocols**. `SOP-007`/`SOP-009` carry mega-hull `close_zones` zone names
and are absent by construction, so an unwanted closure cannot fire on either
hull. The scheduled protocol must be present or the scenario schedule cannot
activate; this is the only coherent reading of "SOP-017 only" and is frozen
here for confirmation at prereg review.

## 3. Cells and seeds

- Seeds per row: **20** (20200205–20200224), the handoff's proposed default,
  uniform across every row of both event pairs (vs GM-RESCORE's 50-seed
  convention). The same seed list on both arms of a pair gives the CRN
  pairing. Confirmed by this prereg's merge.
- Cell counts: DP design 40 cells (1 Θ × 2 arms × 20 seeds); GM design 160
  cells (4 Θ × 2 arms × 20 seeds). Total 200.
- Campaign blocks mirror the rows; `scripts/campaign` submits per block.

## 4. Metrics (frozen)

Per event pair and theta row:

- **Paired hull delta**: per-seed `dedicated − proxy` `recorded_onsets`,
  takeoff-conditional (a seed contributes only when BOTH arms record ≥ 10
  onsets — the design's `takeoff_recorded_onsets` gate). Report the median
  Δ with q05–q95.
- **P(takeoff)** per hull: fraction of the 20 seeds with
  `recorded_onsets ≥ 10`.
- **Takeoff-conditional asymptomatic share** of `lab_confirmed` per hull.
- **CRN correlation** on the canary batch: Pearson ρ of `recorded_onsets`
  across the two arms over both-takeoff seeds. ρ < 0.3 → the unpaired
  analysis is declared.
- **Minimum detectable effect**: 30% of the proxy arm's takeoff-conditional
  median `recorded_onsets` (declared at prereg review).

## 5. Audits and stop rules (frozen)

- **Failed comparison**: any cell whose protocol engine fired a
  `close_zones` protocol is a **FAILED COMPARISON** — reported, never
  deleted (firing is outbreak-severity-dependent; deletion would bias the
  contrast). Stop, diagnose, apply a predeclared correction/rerun policy;
  failed attempts stay in the record.
- **Technical failures**: cells missing payloads or erroring are counted;
  a failure rate above 10% of a submitted block → stop, diagnose, resubmit.
- **Report immediately**: any `close_zones` firing; technical-failure rate
  > 10%; the paired delta's q05–q95 interval excluding zero.
- Campaign gate (bounded-research-sessions rule): geometry/seed gate
  validated, local smoke passed, canary (≥20 seeds at one arm-row = 40
  executions per event pair) read out — then **stop and report**; the user
  decides whether the full array runs.

## 6. Execution order

1. Local smoke (both designs, capped epochs for DP; full voyage for GM).
2. Batch canary: the DP pair (`dp_t7e6_proxy` + `dp_t7e6_dedicated`, 40
   cells) — read out and STOP.
3. GM blocks only after the DP machinery is proven and the owner approves;
   GM canary is technical acceptance only.

## 7. What this cannot settle

- It does not select a platform, refit Θ, or crown a canonical hull; it
  measures the platform effect at frozen operating points.
- The descriptive GM layers are not selectable and carry no criterion; they
  are reported as measured.
- Platform-data defects discovered during bring-up (see §8) are fixed as
  data-consistency repairs, not as fitted constants; none touches an
  epidemiological constant.

## 8. Bring-up repairs (data consistency, declared)

Two disabled worked-example blocks on `data/platforms/diamond_princess/
voyage_config.json` were referentially invalid for the hull's own zone
catalog / the DP scenario's collapsed crew classes, and crashed spec
resolution before any cell ran:

- `hazard_sources.penetrations[0].zones` named `Promenade`/`LidoBuffet`,
  absent from the hull's spatial layout → repointed to the hull's real
  promenade/outdoor zones (`PromGalleria`, `HorizonTerrace`). Block remains
  `enabled: false` (inert).
- `ship_functions.functions` (6 entries, `enabled: false`) staffed
  `crew_galley`/`crew_engineering`/`crew_medical`, which the DP scenario's
  `agent_classes` (passenger_general + crew_general only) does not declare
  → the functions list was emptied. Behaviorally identical: the capacity
  runner is `None` whether the block is disabled or empty, and the sibling
  replay hulls (`mega_cruise_5000`, `expedition_cruise_450`,
  `greg_mortimer`) carry no `ship_functions` block.

Neither repair touches an epidemiological constant; both are recorded here
so the canary's hashes and this prereg stay the criterion of record.
