---
name: ship-function-capacity
description: Configure and extend the ship-function capacity layer — function registry, crew-availability read, systems health, feedback writers, PPE wear-fatigue — for any vessel platform.
---

# Ship Function Capacity

Use this skill when declaring `ship_functions` / `ship_systems` blocks on a
platform, adding a feedback writer, or extending the capacity/fatigue channels.
Governing spec: `docs/ship_functions/ship_function_capacity_spec.md`
(§3–§7 implemented; §8 hazard arm is separate work).

## The contract in one paragraph

`engines/ship_functions.py` scores each declared `(function_id, serves)`
instance per epoch from three inputs — staffing pools (crew class or
`zone:<work_zone>` membership, on-watch, ABSENT/IMPAIRED/FIT), required zones
(open fraction), and `ship_systems` multipliers — and writes a
`function_capacity` record on each epoch. Feedback writers then write *inputs
the engines already read* (coverage scales, dining weights, `close_zones`,
route scalars), never physics. Everything is `enabled: false`; absent or
disabled is bit-identical — verify with a paired seeded run, not by reasoning.

## Declaration checklist (platform `voyage_config.json`)

- `ship_systems`: `system_id`, `health_start`, `degradation.rate_per_day`,
  `repair.labor_class` + `repair.rate_per_person_hour`, `repair_priority`,
  `failure_threshold`, `effects.<function_id>.capacity_multiplier_at_failure`.
- `ship_functions.functions[]`: `function_id` + `serves`
  (`passengers|crew|both|mission`) is the instance key — one vessel may
  declare `food_service` twice (passenger dining and crew mess sharing the
  `crew_galley` pool). `staffing` (class-keyed) XOR `staffing_by_duty_zone`.
  `required_zone_ids` / `required_zone_types` (a type needs ≥1 open member).
  `capacity_model`: `staffing_fraction` or `bottleneck_min` (hard gate below
  `minimum_on_watch`). Optional `capacity_schedule` hour→demand scale.
- `feedback.kind`: `readout_only` | `cleaning_coverage_scale` |
  `dining_weights` | `zone_modifiers` | `route_scalar_scale`; `threshold`,
  `sustained_hours` (wall-clock — never `sustained_epochs`), per-kind keys
  (`floor`, `degraded_weights`, `zone_close_on_loss`, `scalar_name`).
  `crew_sustenance: true` on crew-served functions writes
  `agent.sustenance_deficit` — the second-order channel (dead galley →
  impaired crew) the §7 fatigue accumulator also reads.
- Validation is referential at load: staffing classes must exist in
  `ship_graph.agent_classes`, zones in the platform layout, systems in
  `ship_systems`. Validation runs even when `enabled: false` — a bad
  declaration fails loudly, not silently.

## Provenance and constants

- `symptomatic_effectiveness` default 0.7 is the Grade B arm of the sourced
  [0.55, 0.85] interval — see `docs/ship_functions/parameter_sources.md`, the
  register of record; source or NULL-SOURCE-declare every constant there
  before editing engine defaults.
- PPE fatigue channel (`engines/ppe_fatigue.py`, spec §7): `ppe_types`
  registry in `crusher_labs/config.yaml`, `agent.fatigue_score` accumulates
  declared inputs (per-type wear-hours + `sustenance_deficit`),
  `ppe_dexterity_impairment` scales repair labor, `ppe_symptomatic_active`
  folds into exported `symptom_presentation` — deliberately NOT
  `illness_status` (natural history recomputes it; endogenous onsets would be
  cleared). Copy that pattern for any new non-infectious state.

## Gotchas that have already cost time

- New top-level voyage config keys MUST be added to
  `merge_voyage_overrides`' full-doc detection in `voyage_itinerary.py` or
  `config_overrides` nests them under `voyage.` and they are ignored.
- New `KorkinAgent` fields go in BOTH `__slots__` and `__init__`.
- `zone_occupancy_cap` has no consumer — only `close_zones` and the four
  route scalars (`direct_contact_scalar`, `droplet_scalar`,
  `hvac_airborne_scalar`, `fomite_scalar`) are live seams; write through
  `merge_capacity_modifiers` / `_merge_modifier_value` inside
  `_step_protocols`, never direct setattr (reset each epoch).
- Block-level `ship_functions.symptomatic_effectiveness` is plumbed to the
  runner at build time — add new block-level defaults in
  `_build_ship_function_runner`, not just the parser.
- `_pools` returns `(counts, members)` — repair labor needs the member list
  to fold `ppe_dexterity_impairment` per agent.
- Capacity reads are hazard-agnostic on purpose (symptomatic/absent/covered,
  never pathogen ids) — keep them that way so a §8 chemical incapacitation
  feeds `available_for_duty` identically to a viral one.
- Sonar on test files: `pytest.approx` for every float compare, one
  condition per assert (S1244/S9073).
