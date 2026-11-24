# DP-PARTICIPATION-01
**Date:** 2026-11-24
**Commit:** d93522e7
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** c7f7f927

Suite 2 of `docs/proposals/covid_theta_unification_plan.md` — the
participation falsification probe (pin the index's day-0 itinerary inside
the declared surge venues vs the drawn itinerary, matched seeds
20200205–20200228). **The probe was not run.** No design was frozen, no
campaign was registered, no cell ran and nothing was submitted to AWS
Batch. The session closed at two findings, by owner decision
(2026-11-24): the pin is not expressible, and under the union arm it would
have nothing to act on.

## 1. Per-index day-0 pinning is not expressible (read from code, `d93522e7`)

- `engines/rhythm_layer.py` deals each day's commitments to every eligible
  agent from event-level draws on its own stream (`deal_day` →
  `_deal_event` → `_deal_occurrence` → `_commit_agent`). It has no
  per-agent hook and does not know which agent is the index.
- Its only override, `event_overrides`, patches an event for all agents,
  and the arm grammar does not expose it: `rhythm_overrides` accepts
  `catalog`, `exercise`, `passenger_disposition` and
  `port_day_onboard_midday_residual` only.
- `seed_patch.placement` accepts `dining_service_type` only (the retired
  placement axis, COVID-SEED-RING-01). `voyage_overrides` writes ship-wide
  day entries (the retired windowed-intensity axis, COVID-SEED-RING-02).
- The `diamond` catalog already declares `boarding_flow` (12:00–16:00,
  `gangway_corridor` + `piazza_promenade`) and `onboard_assembly`
  (16:00–16:30, plus `open_deck`) at `participation_fraction` 1.0. The
  draw therefore decides the capacity cut, the venue zone, the arrival
  offset inside the boarding window and the 0.5 `embark_buffet` Bernoulli,
  not attendance.
- Pairing: a pin that skips or adds a draw for the index shifts the rhythm
  stream for every later agent. A pin would have to be applied after the
  normal deal for the two arms to be paired realizations.

Expressing the pin needs engine work, which the deliverable excluded.

## 2. Under the union arm the founder class is not made on day 0 (measured)

Pure readout over the 96 completed DP-UNION-01 cells (θ 1e8, 3.16e8, 1e9,
3.16e9 × seeds 20200205–20200228, arm `union_niid`,
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_dp_union_01/union_t{1e8,3e8,1e9,3e9}_{canary,rest}/`),
`tools/covid_dp_participation_diag.py`, evidence
`reports/dp_participation_01/day_of_acquisition.json`. Day index 0 is
embarkation day (`sim.clock.day_index`).

| θ | founder-class cells | aboard-window acquisitions | day 0 | day 1 | day 2 | day 3 | day 4 |
|---|---|---|---|---|---|---|---|
| 1e8 | 0 | 28 | 0 | 0 | 1 | 6 | 21 |
| 3.16e8 | 2 | 60 | 0 | 3 | 5 | 8 | 44 |
| 1e9 | 4 | 141 | 0 | 5 | 13 | 12 | 111 |
| 3.16e9 | 7 | 639 | 0 | 22 | 24 | 76 | 517 |
| pooled | 13 | 868 | 0 | 30 | 43 | 102 | 693 |

- Zero of 868 aboard-window acquisitions fall on embarkation day, in every
  cell. `index_shedding_at_day0` is false in all 96 cells: the arm's
  `seed_patch` (`infection_age_days` 2.8, `onset_day` 3.0) boards an index
  that emits nothing during boarding flow and assembly.
- 693 of 868 (80%) fall on day index 4, a sea day and the index's last
  full day aboard (`index_departed_epoch` 120 in all cells).
- At θ 3.16e9 the 7 founder-class cells take 505 of 601 acquisitions by
  `hvac_airborne`, 86 by droplet and 10 by caregiver.

Consequence: a day-0 itinerary pin cannot change founder yield under the
union arm. Suite 2 as written would return a null that says nothing about
participation.

## What is not measured

- The cells carry day and route, not venue or hour. Which venue the index
  occupied on day index 4, and whether the high-yield seeds share one, is
  unknown.
- The "surge geometry" readings in COVID-IGNITION-01 and
  COVID-SEED-RING-01/02 come from arms whose design files carry no
  `seed_patch` on onset or infection age
  (`picard_framework/runs/covid_seed_ring_0{1,2}_design.json`), and their
  readouts report day-0 acquisitions. That they do not transfer to the
  union arm because its index is pre-shedding at boarding is an inference
  from the design files; those cells were not re-read here.

## Open decision (owner)

Suite 2 needs re-scoping before any campaign. The options named at close:

1. Aim the pin at the index's shedding days (day index 3–4) instead of
   day 0. Departs from the Suite-2 text; still needs the engine hook of §1.
2. Keep day-0 pinning and change the seed patch so the index sheds at
   boarding. That changes the union arm, so the Suite-1 cells stop being
   the matched baseline.
3. First a venue-attribution replay (24 seeds at θ 3.16e9, AWS Batch) to
   locate the day-4 acquisitions, then choose.

GM still held out; H5 held out forever; nothing scored against [712,960].
