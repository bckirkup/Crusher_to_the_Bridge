# ROOM-AIR-01
**Date:** 2026-09-26
**Commit:** #PENDING
**Pathogens:** all
**Status:** open

Every room-pool inhalation route now doses occupants on the **epoch-mean
concentration of a room exchanging at its declared ventilation rate**,
instead of the implicit sealed-room assumption the pool model carried
(emitted mass sitting at full concentration for the whole epoch). The
mechanism COVID-VENT-AUDIT-01's source table exposed: hulls declare real
per-zone AHU rates in `air_flow_paths.json` (`ach × hvac_duty`, sanitary
branches running dedicated extract at `ach` with `hvac_duty: 0,
oa_fraction: 1.0`), and the dose path was not reading them.

Mechanics (`transmission.room_air_removal`, default `"first_order"`;
`"sealed"` is the labelled bit-identical baseline):

- `build_zone_air_exchange_map(air_flow_paths)` computes each HVAC zone's
  removal rate `ach × hvac_duty` (duty-0 extract-only branches take `ach`
  directly — a sanitary exhaust fan runs on its own schedule, not the
  AHU's duty cycle) and `ShipSimulation` passes it to `TransmissionCore`
  as `zone_air_exchange_per_hour`.
- Each room-pool route scales its dose by the residence factor
  `f(x) = (1 − e^{−x}) / x` at `x = rate × hours_per_epoch` — the
  pulse-average of a first-order-decaying concentration, the same form
  the sanitary flush route already used. Zones with no declared rate
  (rate 0) keep `f = 1.0` — the sealed pre-change value, so nothing
  changes where the hull does not declare an exchange.
- Applies ship-wide at the air unit: zone droplet pool, cabin-compartment
  pool (whose rate additionally takes `max(zone rate,
  SANITARY_EXHAUST_M3H_PER_WC / compartment_volume)` — the stateroom
  bathroom exhaust the compartment already models), HVAC downstream
  delivery, emesis aerosol, flush aerosol, and the environmental pool
  routes.
- **CONTAM boundary unchanged**: the factor corrects within-epoch in-room
  concentration for the occupant dose integral; inter-zone transport of
  `aerosol_pools` still runs the exact linear CONTAM operator
  (AERO-CABIN-03), and the py_contam bridge already uses `ach·V·duty` for
  room→plenum return — the same convention this change adopts.

Second half of this change: `_cabin_presence_share` multiplies every
inhalation route's dose by the confined target's in-cabin share (see
CABIN-OCC-01) — a confined agent ashore for its absence share does not
inhale cabin air while absent.

No shared-stream draws; `sealed` vs `first_order` differ only in dose.
The change-detector cells moved exactly by this mechanism:
`test_covid_hull_change_detector` Greg Mortimer (4, 2, 217, 5, 2) →
(1, 1, 217, 2, 0) and Diamond Princess (3412, 2677, 2002, 199, 81) →
(3400, 2206, 2090, 274, 120) on CPython 3.12, attributed and repinned
with the move notes in-file.
