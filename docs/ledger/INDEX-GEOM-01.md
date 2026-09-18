# INDEX-GEOM-01
**Date:** 2026-09-18
**Commit:** 70b5871
**Pathogens:** sars_cov2_resp
**Status:** open

## Defect

The Diamond Princess index case never left the ship. The record's index
boarded 20 January already symptomatic (cough onset 19 January), took the
Kagoshima shore excursion on 22 January, and disembarked permanently at Hong
Kong on 25 January (Yamagishi 2020, Eurosurveillance 25(23):2000272, Results
prose, grade A). The scenario seeded him at day 0 and kept him aboard
shedding for the whole 32-day replay — 27 days of shedding the record does
not contain — and no permanent-departure mechanism existed anywhere in the
engine: `ashore` is a port-excursion flag that is cleared on the next
non-port epoch, and nothing else removes a host from transmission.

## Fix: declared per-agent departure

`KorkinAgent.departure_epoch` records the first epoch the host is no longer
aboard (`None` = the whole run), read through `has_departed(epoch)`.
Departure gates at *placement*, reusing the excursion machinery rather than
a new flag inside the dose math: the placement loop in
`KorkinShipEngine.step` sets `current_location` to a new `LOCATION_DEPARTED`
sentinel (`"Departed"`, deliberately distinct from `"Ashore"` — a port
excursion returns, a departure does not, and reports reading the location
must not conflate them) before the ashore/isolated/quarantined/scheduled
checks. `TransmissionCore.execute_transmission` then excludes `"Departed"`
from `zone_occupants` alongside `"Ashore"` and skips departed hosts in the
dose-response challenge loop outright, since a host who left cannot acquire
aboard and a zero-dose challenge is a silent invitation to a future defect.

The denominators an excursion does not need but a departure does are
excluded explicitly: testing-campaign eligibility
(`TestingCampaign._tier_members`), specimen sampling, sick-call, onset
recording and `total_agents` in the syndromic modality, the VSP
`total_pop`/`total_ill` counters, shore introductions, the wastewater
sampler (same reason as `ashore`), and the ever-reported / group-rate
rosters. Everything reads the sentinel through one predicate,
`agent_is_departed` (engines/voyage_itinerary.py), which accepts both a
`KorkinAgent` and its exported telemetry dict.

Declaration is per seed: `ExplicitSeed.departure_day` (finite, ≥ 0, and not
earlier than the seed's own epoch in days — refused at seed application in
`_apply_one_seed` rather than at resolve time because the run clock lives
there and an epoch is not a day on hourly clocks), written to
`agent.departure_epoch` through `engine.clock.epochs_for_days`. The Diamond
Princess seed declares `departure_day: 5.0` (20 Jan boarding = day 0, 25 Jan
Hong Kong disembarkation = day 5, Yamagishi 2020 grade A). Verified
end-to-end: the seeded host is placed `"Departed"` from epoch 120 on the
hourly hull clock.

## Scoped note: `ashore` is honoured almost nowhere

Port-call `ashore` gates transmission correctly — via the same placement
sentinel this change reuses — and is honoured by the wastewater sampler.
It is honoured by **no other denominator**: an ashore host remains
campaign-swabbable, onset-recordable, and VSP-countable. That is tolerable
for an hours-long excursion and is *not* fixed here; it matters for any
future mechanism that keeps hosts off-ship longer.

## Declared omissions

- **The roster still carries the departed host.** `to_schema_dict` exports
  every agent including departed ones; the roster is a manifest, not an
  aboard-count, and no schema change ships in this PR.
- **Off-ship progression continues.** A departed host's infections still
  advance (`step_infection_progression` iterates all agents): the host is
  not resurrected, it is simply no longer coupled to the ship.
- **The 22 January Kagoshima excursion is not modelled.** Departure is
  permanent once declared; the record's leave-and-return port call is
  declared out of scope (it falls on the aboard side of day 5 anyway).

## Change-detector status

This entry adds a second pinned cell to
`tests/test_covid_hull_change_detector.py`: until now the only pinned reading
was the held-out `greg_mortimer_2020`, which declares no departure and is
unaffected by construction (it read `(1, 1, 217, 4, 0)` before and after),
so no CI cell touched the hull Θ is actually fitted on. The new
`diamond_princess_2020` cell holds every knob identical to the Greg Mortimer
cell — Θ = 1e10, seed 20200333, the same five pinned fields — and its first
reading, taken with the index case departing on day 5, is
`(3522, 2934, 1706, 252, 73)` on CPython 3.12; the 3.11 entry is pending a
CI reading. The DP cell is marked `slow` — a full Diamond Princess replay
is ~20 minutes, a signal needed per PR at most, so it lands on the nightly
tier while the Greg Mortimer cell keeps a fast-tier reading on every push. The file's comment block states that the cell is a change
detector and not an anchor comparison — it is not the Diamond Princess
observables of `data/observation/covid_fit_targets.json`, covid.T1/T3 are
real scored anchors on the same scenario, and nothing in the file may be
quoted as a result.

A reading caveat on the group-rate denominator: `update_ever_reported_ids`
accumulates and `_compute_group_rates` now divides by the aboard-only
denominator, so a host who reported sick and *then* departed stays in the
numerator while leaving the denominator. That is the intended reading — the
ship's record keeps what it recorded — but it means the group rate is a
cumulative-reports-over-current-aboard ratio, not a prevalence, and it can
only be read as such.

No Θ is claimed by this entry. `infection_age_days` is left at its declared
value: Yamagishi 2020 places cough onset at day −1, so the boarding-age
truth is one day plus an incubation period, and that uncertainty is exactly
why infection age is a screened axis rather than a pinned constant.
