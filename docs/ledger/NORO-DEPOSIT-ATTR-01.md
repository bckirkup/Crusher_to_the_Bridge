# NORO-DEPOSIT-ATTR-01
**Date:** 2026-09-26
**Commit:** d10d0392
**Pathogens:** norwalk_gi
**Status:** declared

Per-change attribution of the post-#724 surface-pool deposit-mass collapse
(~5 orders of magnitude) measured by NORO-REBASE-01 (`a872367c`) on the
`fl_spr_12d` cell — `spirit_cruise_3000`, n=3000, 288 epochs,
`syndromic_comp65`, rung `reportable`, paired seeds 8105/8106, cell
overrides `sanitary_visit_mode: dwell_weighted`, `flush_aerosol_fraction: 0.0`,
`flush_cabin_emission: true`, `cabin_air_mode: cabin_compartment`,
`hvac.pathogen_pool_transport: airflow`.

## Attribution criterion (declared before any ablation ran)

Statistic, per (arm, seed) voyage: the per-epoch
`sanitary_activity.dose_delivered` series, plus the deposit split this probe
records — `deposit_by_venue_class_gec` (shared_head / cabin_fittings /
other_zone), `deposit_by_call_site_gec`, per-epoch `pool_{class}` mass,
`stool_venue_destinations`, `new_infections` (non-seed).

- **Carrier**: the arm restores the shared-head deposit mass and
  `dose_delivered` to within the pre-fix archive's order of magnitude
  (>= 1e4/epoch peak vs the post-724 ~2-5) on both paired seeds, while the
  other arms stay at the post-724 reading. Partial restoration (>= 10x the
  post-724 reading, < 1e4/epoch peak, same on both seeds) is **partial**.
- **Null**: an arm within the seed-pair spread of the post-724 base on
  deposit mass and `dose_delivered`.
- **Multiplicative collapse**: no single arm restores — the fall is split
  across several correct removals; reported immediately (fork changes: refit
  becomes mandatory).
- **Overshoot**: an arm restores beyond the pre-fix trace — reported
  immediately; the pre-fix level may itself be artifact-inflated.
- **RNG reorder**: arms that move spawn draws (watch_off) or remove
  downstream draws (emesis_zonepool drops patch-pickup draws) are flagged
  stream-non-neutral; for those arms the criterion is read on event ordering
  and the venue-class deposit split, not just totals, per the
  stochastic-attribution skill.

Instrument: `tools/noro_diag/deposit_attr_trace.py` — verbatim
`generate_tier_runs(manifest, "fl_spr_12d")` specs, arm overrides merged on
top, read-only wrappers plus a per-epoch observer; no engine writes, no
wrapper draws RNG.

## Method per candidate (fixed before running)

| candidate | arm | method |
|---|---|---|
| emesis footprint localization (#604, `9daa4a8f`) | `emesis_zonepool` | in-process revert of `_emit_emesis`/`_deposit_emesis` to the pre-604 filing (share `min(1, high_touch/footprint)`, zone-pool deposit); draw order preserved in the emitter |
| blackwater bowl share (`transmission.blackwater_plumbing`, default-on `b120ad3d`) | `blackwater_off` | labelled config baseline `false`; documented stream-neutral |
| crew watch schedules (#723, `e86b73bf`) | `watch_off` | `ship_graph.agent_classes` without `schedule` keys (pre-723 verbatim state) + `agent_behavior.schedule_jitter_hours` zeroed; spawn draws reorder — distribution caveat |
| sub-copy pickup gate (NORO-GATE-FLOOR-01, #674/677) | `gate_off` | in-process `SURFACE_PICKUP_MIN_GEC = 0.0` for the run — equivalent to reverting the constant; gate consumes no RNG either way |
| reporting de-stack (NORO-CHANNEL-02, `b9cae80f`) | `report_scale` | `pathogen_overrides.norwalk_gi.observation_model.reporting_belief_scaling: "trust_medical"` — the pre-change stacking as a labelled baseline; added after static review showed reporting speed changed confinement timing in-window |
| cabin-pair fomite (NORO-CABIN-01, `b49a3ec2`) | `cabin_fomite_off` | labelled config baseline `transmission.cabin_confined_fomite.mode: "off"` |

Named-candidate coverage: all four ledger-named drivers have arms; the two
extra rows are in-window changes found on the deposit path during the method
inventory (confinement timing, cabin-pair delivery). Considered and rejected
as carriers: `room_air_removal`, `cabin_cooccupancy`, `cabin_air_mode`
(airborne-side or already pinned identically in both cells);
`norwalk_only.json` registration (bundle untouched by this cell — profile
diff in-window adds only `reporting_belief_scaling`, exercised by the
`report_scale` arm).

## Pre-run static audit (recorded so the table is read against it)

Byte-identical across `7f689b9..fbad8738`: the whole stool->hand chain
(`_route_stool_event_venue`, `_stool_event_occurs`, `_stool_bowl_copies`,
`_replenish_hand`, `_stationary_hand_load`, `_hand_carriage_propensity`,
`shedding_value`, `_shedding_curve_point`, `get_pathogen_hand_target`,
`_get_shedders`, `_get_susceptible`, `_cabin_confinement_active`,
`_draw_sanitary_visits`, `_sanitary_visit_share`, `_fomite_surface_contacts`,
`_hand_to_surface_drying`, `_delivery_scale`), and the deposit formula in
`_sanitary_venue_deposits` (contacts x share x used_fraction x
transfer_efficiency x hand, `min(hand, requested)`).

Changed in-window on the same path: `_fomite_pickup_request` (new
`_cabin_presence_share` factor, dedicated `_fomite_rng` stream),
`_hand_to_mouth_dose`, `_consume_surface_mass` (exact-empty on capped pools),
`_update_surface_pools`, `_fomite_surface_area`, `_emit_emesis` (patch
filing), `_deposit_surface_mass` (per-surface mirror, inert when pooled),
sanitary exposure split into helpers at `94b179ab` (mechanical S3776 split —
formula preserved verbatim, verified line-by-line).

## Results

(pending — canary `base` arm first: must reproduce `dose_delivered` ~2-5/epoch
on s8105 before any ablation is read)
