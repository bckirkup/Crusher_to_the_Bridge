# CONTAM-GROUPED-WEATHER-AUXILIARY-01
**Date:** 2026-11-17
**Commit:** 4a3d7a55
**Pathogens:** all
**Status:** measured
**Measured at:** e33bbd6a

## Scope

Stage G4 auxiliary-class rollout of
[`docs/proposals/grouped_weather_openings_decision_plan.md`](../proposals/grouped_weather_openings_decision_plan.md)
under the owner ruling of 2026-11-17: grouped weather zones MAY receive
`ambient_openings`; the opening REPLACES the HVAC group's OA leg for that zone
(NO double-count). This is the auxiliary-class staged rollout authorized by the
same ruling, not a fleet-wide PR. Pope, Aeolus and fiction are non-goals.

Roster: the stage-4 auxiliary ledger
[`CONTAM-AMBIENT-WEATHER-AUXILIARY-01`](CONTAM-AMBIENT-WEATHER-AUXILIARY-01.md)
had 19 auxiliary-type hulls. Seven still had grouped weather zones with
group outdoor ACH > 0 and are changed here:
`assistance_ar17`, `gosper_apa170`, `jupiter_ac3`, `legend_class_nsc`,
`luzon_arg2`, `mercury_aks20`, `squier_ap130`. `pope_ap110` is excluded by the
task non-goal. The remaining auxiliary roster hulls are no-op for this ledger:
`aeolus_arc3`, `apl_24`, `bolster_ars38`, `cobalt_k124`,
`gordon_gunter_r338`, `liberty_cargo_ec2`, `lyon_ap71`,
`passumpsic_ao106`, `savannah_ns`; `alexander_henry_cgs119` is owned by the
cruiser ledger.

Steady ContamX solves used the local official NIST binary
`third_party/contamx/contamx3`; no seeds, no AWS. All numbers below are
measured on the data committed at `e33bbd6a`, on top of `origin/main`
`4a3d7a55`; "before" is `4a3d7a55` itself.

## Change (exactly)

For each hull, only `data/platforms/<hull>/spatial_layout.json` and
`data/platforms/<hull>/air_flow_paths.json` changed, plus regenerated
`contam/{platform.prj,path_map.json}` for the six hulls that have committed
bundles (`legend_class_nsc` has no committed bundle by the existing
five-authored-hull exception). No engine, exporter or schema code changed.

Per hull:

1. each opened zone gained `exposure: "weather"` (D7(b));
2. each opened zone gained one `ambient_openings` record: `type` `open_deck`,
   Grade C deck-face `area_m2 = 2 * sqrt(V / 3) * 3`, `wind_speed_m_s` 1.0,
   `schedule` `always_open`, and D5 `exchange_m3h` measured after the change;
3. the weather zone was removed from its HVAC group's `rooms`, so the group no
   longer counts that zone's outdoor exchange as HVAC OA; `ach`,
   `oa_fraction`, duty, filters and remaining member rooms are unchanged, so
   remaining member zones are not stranded;
4. every `cross_zone_links` record addressed by a changed group id was split
   into a remaining-group record plus one room-id record per opened zone, with
   flows re-declared so the per-room-pair reference flow is unchanged. This is
   a re-addressing of unchanged reference flows, not a magnitude change, but it
   does edit `flow_rate_m3h` fields and is called out for owner review exactly
   as in `CONTAM-GROUPED-WEATHER-MIDWAY-01`.

| hull | HVAC group | rooms before→after | open_deck records | exchange_m3h total |
|---|---|---:|---:|---:|
| assistance_ar17 | HVAC_Accom | 26→22 | 4 | 251125.8 |
| gosper_apa170 | VENT_Machinery_Holds | 34→28 | 6 | 422406.7 |
| jupiter_ac3 | VENT_Cargo | 15→13 | 2 | 232494.3 |
| legend_class_nsc | HVAC_Aviation | 3→1 | 2 | 51995.2 |
| luzon_arg2 | HVAC_Accom | 28→24 | 4 | 204463.5 |
| mercury_aks20 | HVAC_Accom | 24→22 | 2 | 183430.0 |
| squier_ap130 | VENT_Stores_Open | 17→16 | 1 | 52693.8 |

D5 per-opening values (`exchange_m3h` is the commissioned-lane ContamX-solved
outward flow at the committed 1 m/s fleet-default relative wind, measured after
the edits):

| hull | zone | area_m2 | exchange_m3h |
|---|---|---:|---:|
| assistance_ar17 | Boat_Gun_Deck_Aft | 108.718 | 72953.4 |
| assistance_ar17 | Boat_Deck_Fwd | 72.478 | 48624.6 |
| assistance_ar17 | Stern_Working_Deck | 87.16 | 69424.7 |
| assistance_ar17 | Fwd_Working_Deck | 75.262 | 60123.1 |
| gosper_apa170 | Boat_Deck_Open | 95.268 | 76246.6 |
| gosper_apa170 | Boat_Deck_Open_Fwd | 128.154 | 102762.7 |
| gosper_apa170 | Focsle_Deck_Open | 91.008 | 71071.7 |
| gosper_apa170 | Fantail | 61.109 | 48988.1 |
| gosper_apa170 | Boat_Stowage_Deck | 67.557 | 53247.1 |
| gosper_apa170 | Main_Deck_Open_Fwd | 88.083 | 70476.2 |
| jupiter_ac3 | Poop_Deck_Open | 275.906 | 185140.5 |
| jupiter_ac3 | Focsle_Deck_Open | 70.993 | 47353.8 |
| legend_class_nsc | Flight_Deck | 48.99 | 32004.8 |
| legend_class_nsc | Boat_Deck | 30.984 | 19990.4 |
| luzon_arg2 | Gun_Weather_Sup | 61.779 | 41310.7 |
| luzon_arg2 | Boat_Deck_Aft | 97.285 | 78309.0 |
| luzon_arg2 | Stern_Weather | 78.299 | 61993.8 |
| luzon_arg2 | Chain_Locker_Focsle | 29.298 | 22849.8 |
| mercury_aks20 | Fantail | 130.154 | 104471.2 |
| mercury_aks20 | Foredeck | 98.096 | 78958.8 |
| squier_ap130 | Stern_Deck_Up | 69.339 | 52693.8 |

For `legend_class_nsc`, which has no committed `contam/` bundle, the D5 values
were measured from a fresh commissioned-lane export in
`telemetry_buffer/g4_aux/legend_export/` (not committed); no bundle was created.

Tests: `tests/test_contam_ambient_opening.py` `_WEATHER_ZONES` gained the seven
hull zone sets; `tests/test_contam_ambient_opening_boundary.py` committed-leg
census gained two legs per opening on the six bundled hulls
(`legend_class_nsc` contributes no committed legs). Both moves are the opening
legs / exposure tags of this change. `tests/test_forced_exhaust_audit.py`
`Sanitary_Makeup` count moved 585 → 623 because the same group-link splits
re-addressed 38 group-addressed `Sanitary_Makeup` records for opened weather
zones (assistance +12, legend +4, luzon +16, mercury +6) while preserving
per-room-pair flow; direction and native-reverse invariants are unchanged.

## Witnesses

Pressure/balance diagnostic
`tools/diag/contam_pressure_balance_diagnostic.py`, commissioned lane, before
(`4a3d7a55`) vs after (`e33bbd6a`); legend has no authored lane because it has no
committed bundle. Envelope max |ΔP| is the `envelope_leak` class maximum;
interior max |ΔP| is the maximum over the remaining path classes.

| hull | envelope max \|ΔP\| Pa before→after | interior max \|ΔP\| Pa before→after | make-up demand m³/h before→after | opening net inward m³/h before→after | balance residual m³/h before→after | exchange_m3h |
|---|---:|---:|---:|---:|---:|---:|
| assistance_ar17 | 3.95e+04 → 3.81 | 226 → 226 | 3.18e+03 → 3.18e+03 | 0 → 3.16e+03 | 1.12e-05 → -0.00836 | 2.51e+05 |
| gosper_apa170 | 3.35e+05 → 15.9 | 1.6e+04 → 107 | 1.15e+04 → 1.15e+04 | 0 → 1.15e+04 | -3.37e-05 → 0.0165 | 4.23e+05 |
| jupiter_ac3 | 5.1e+03 → 4.25 | 137 → 137 | 1e+03 → 1e+03 | 0 → 985 | -1.4e-06 → -0.000508 | 2.32e+05 |
| legend_class_nsc | 1.09e+05 → 14.7 | 1.09e+05 → 8.63 | 2.48e+03 → 2.48e+03 | 0 → 2.46e+03 | 1.11e-05 → 0.00113 | 5.2e+04 |
| luzon_arg2 | 7.01e+04 → 12.1 | 224 → 224 | 5.14e+03 → 5.14e+03 | 0 → 5.08e+03 | 1.13e-05 → -0.00177 | 2.04e+05 |
| mercury_aks20 | 1.2e+04 → 5.12 | 205 → 205 | 1.88e+03 → 1.85e+03 | 0 → 1.85e+03 | 2.81e-06 → 0.00732 | 1.83e+05 |
| squier_ap130 | 1.33e+05 → 127 | 126 → 126 | 5.33e+03 → 5.33e+03 | 0 → 5.17e+03 | -1.13e-05 → -0.00308 | 5.27e+04 |

Commissioned terminal check:
`python3 tools/contam_commissioned_check.py --platform assistance_ar17
--platform gosper_apa170 --platform jupiter_ac3 --platform legend_class_nsc
--platform luzon_arg2 --platform mercury_aks20 --platform squier_ap130
--tolerance 0.05` → PASS, every commissioned terminal solved inside 5% of
declared; remaining HVAC group terminals are unchanged.

Flow compare: `python3 tools/contam_flow_compare.py --platform <hull>
--run-contamx` for the six bundled hulls reports the new `ambient_opening`
legs; outward legs are boundary sinks and inward legs are skipped, matching the
`CONTAM-AMBIENT-OPENING-BOUNDARY-01` contract. Paired diagnostic is not
supported for these hull ids: `tools/diag/contam_paired_diagnostic.py --help`
accepts only the cruise/destroyer/fiction roster, not the auxiliary hulls.

Non-target hulls are byte-identical; only the seven target platform
directories, the two opening-census tests and this ledger/README registration
changed.

## Non-goals observed

No Pope/Aeolus/fiction data changed; no `flow_rate_m3h` magnitude fitting (only
group-link re-addressing splits described above); no stage-5/6; no readout
annotation; no AWS/S3; no frozen campaign dirs; no epidemiological constants; no
schema changes.
