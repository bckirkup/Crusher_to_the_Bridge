# CREW-WINDOW-02 design — fractional and activity-scoped crew duty

Status: declared, pre-run. Criteria in this file are frozen before any
cell runs; nothing below is altered after the surface is seen.

## Question

CREW-WINDOW-01 (measured at `ea9550ef`, 240/240 cells; readout
`docs/covid/covid_crew_window_01_readout.md`, ledger
`docs/ledger/CREW-WINDOW-01.md`) returned **CLIFF-STRUCTURE**: the
during-quarantine mass is bracketed by the two realized corners —

| arm (20 seeds, takeoff-conditional medians) | Θ1e6 | Θ7.9e6 |
|---|---:|---:|
| `D0_declared` — shipped SOP-017, all four crew classes exempt | 601 | 739 |
| `CREWDUTY` — VSP duty exclusion armed | 563 | 758 |
| `EXEMPT_*` (degenerate on this hull — confined the whole crew) | 18 | 70 |
| `MESS_0P5` / `MESS_0P25` — mess far-field ladder | 611/615 | 729/734 |
| record-informed band | **150–350** | |

with during-window crew share ~0.99 against the record's 0.29. The class
vocabulary is the reason the corners are all that was measured: the
`diamond_princess_2020` hull instantiates ONLY `passenger_general`
(2,666) + `crew_general` (1,045) — `crew_galley`, `crew_engineering`,
`crew_medical` name EMPTY sets (`data/scenarios/covid_hull_scenarios.json`
`role_classes`), so every class-subset exemption is degenerate by
construction and the record's "essential service" distinction lives
inside `crew_general`'s duty mix.

The question this design answers: **which interior point between "zero
crew working" and "the whole crew working" lands the during-quarantine
median inside [150, 350], with the before-phase seed-paired unmoved and
the crew share moving toward the record's 0.29?**

Two arm families express "interior point" on the verbatim replay
contract (owner pick 2026-10-05; skeleton
`docs/covid/covid_crew_window_02_design_skeleton.md`): activity-scoped
zone-essential exemptions (family A) and headcount-fraction exemptions
(family B). `CREW_DUTY_MIX` subclassing (family C) is a separate later
stage — NOT in this design.

## Arm semantics (fixed here before implementation)

### A. Zone-essential exemption — `ZONE_NARROW` / `ZONE_WIDE`

SOP-017 variants (the `scheduled_protocol_id` swap convention, as
CW-01's ENGMED/ESSENTIAL) carrying a new modifier
`exempt_work_zones: [<zone ids>]` — the order's *essential service* zone
list. An exempt-classed agent is **confined anyway when its posted
`work_zone` is not on the order's essential list**. The gate applies
inside both the enforced `confine_all_to_quarters` path and every
voluntary/status path that honors `exempt_classes`
(`orchestrator_epoch.py` `confine_all_agents` / `confine_agents`,
including the merged LOCKDOWN path).

On this hull `crew_general` declares no `duty_zone`, so every crew work
posting is a uniform lottery draw over the hull's 34 Free+Dining zones
(`_resolve_class_zones`) — the realized exempt share is therefore a
lottery realization whose expectation is list-size/34, and MUST be
witnessed per cell (below).

Zone lists verbatim (mega hull, `data/platforms/mega_cruise_5000/
spatial_layout.json`; Free+Dining work pool = 34 zones):

- **`SOP-017-NARROW` — 11 postable essential zones:**
  `Main_Galley_Aft`, `SpecGalley`, `BuffetGal_U`, `Engine_Room_Aft`,
  `EngControl`, `Bridge`, `Central_Stores`, `Laundry_Main`,
  `WasteTreat`, `Crew_Mess_Main`, `CrewMess_Fwd`.
  Lottery expectation: 11/34 ≈ **0.324** of crew exempt.
  *(`Medical_Center` reads essential in the record's sense but is type
  `Medical`, outside the Free+Dining work pool — it can never be a
  posting, so it is named here for the record and absent from the
  modifier list. The skeleton's "10/34 + 2 messes ≈ 35%" counted it;
  the postable-zone count is 9 + 2 messes = 11.)*
- **`SOP-017-WIDE` — 19 zones = NARROW + 8 dining venues:**
  adds `MainDining_L`, `MainDining_U`, `Windjammer`, `SpecRest_A`,
  `SpecRest_B`, `CafeBakery`, `Pool_Bar_Grill`, `ComedyClub`.
  Lottery expectation: 19/34 ≈ **0.559** of crew exempt.

Both lists are declared Grade C probes (essentiality reading of the
record), not sourced fractions — whichever lands the band is a magnitude
to source afterward, not a number adopted silently.

### B. Headcount-fraction exemption — `FRAC_25` / `FRAC_50` / `FRAC_75`

SOP-017 variants carrying `exempt_fraction: {"crew_general": f}` —
exempt-classed agents keep working only if drawn into the order's
exempt subset:

- The draw happens **once, at the first confinement epoch the order
  binds**, is sticky for the order's lifetime (no per-epoch re-draw),
  and is recorded (`state.exempt_fraction_draws[protocol_id]`, echoed
  into the cell payload).
- Exact-count draw without replacement: `k = int(f × n_class + 0.5)`
  of the class's agents, uniformly. On this hull `crew_general` n =
  1,045 → k = **261 / 523 / 784** (realized exempt share exactly
  0.250 / 0.500 / 0.784→0.750 … i.e. f).
- The draw consumes a **dedicated RNG stream** seeded
  `[sim.seed, digest("exempt_fraction:" + protocol_id)]` — it touches
  neither the voyage stream nor the host-draw stream, so the
  before-phase stays bit-paired seed-for-seed with D0 and the
  during-window deviation is attributable to the confinement outcome,
  not RNG reordering.
- Agents in `exempt_classes` whose class is not in the
  `exempt_fraction` map keep full exemption (the map is a restriction
  list, not a redefinition).

### Confined-crew path (verified, documented)

A confined exempt-classed agent takes the same cabin-bound path as a
confined passenger (the confinement gate is the only place the
exemption is honored). Crew meals while confined: **R3 steward cabin
delivery** — `_caregiver_service_epoch` serves one delivery per Meal
token to every confined host with no role check; the rhythm layer's
`meals_to_cabin` flag re-routes passenger Meal-token *locations* only
and never gated crew. `service_deliveries` counts these deliveries and
is a per-cell witness (below).

## Cells, seeds, pairing

Grid: `{Θ1e6, Θ7.9e6}` × `{D0_declared, ZONE_NARROW, ZONE_WIDE,
FRAC_25, FRAC_50, FRAC_75}` × 20 seeds (20200205–20200224, the matched
set) = **240 cells** on the verbatim replay contract
(`diamond_princess_2020`, scenario_calendar SOP-017 days 16–30,
infection_age_days 6.8, imports 1, `dwell_weighted`). D0 pairs
seed-for-seed with every arm and doubles as the drift witness against
the CW-01 D0 row at `ea9550ef`. Canary = `ZONE_WIDE @ Θ7.9e6` (20
seeds) — the furthest interior point, which reads the realized exempt
share immediately.

## Frozen admissibility and verdict grammar

Verbatim from CW-01. Per arm per theta, seed-paired vs the in-design
D0 row:

- **CHANNEL-LANDED** — takeoff-conditional median
  `infections_during_quarantine` inside [150, 350] AND
  `infections_before_quarantine` unmoved within seed-paired noise AND
  during-window crew share moves measurably toward the record's 0.29.
- **UNDER-ATTENUATED** — median moves toward but stays above the band:
  report residual size, crew share, and the band-side miss.
- **OVER-ATTENUATED** — median lands below the band: joins ALLHANDS as
  too-strong; the bracket narrows but no candidate conforms.
- **UNMOVED** — seed-paired delta inside RNG-reorder noise: the arm
  never reached the channel (audit the witness echo first).

`D0_declared` is scored on the clause (T1 recorded/before-share) and
total band [712, 960]; every other arm is a non-scoring probe — these
are discriminating probes of a channel, not candidates to adopt
verbatim. `SOP-017-ALLHANDS` is NOT re-run: its corner is measured.

## Audit invariants (halt the campaign on failure)

- `quarantine_witness` echoes on every cell: window `[16,30]`,
  `activated` true; `exempt_classes` equals the shipped four-class set
  on every arm (the CW-02 modifiers restrict **within** the exempt set;
  the declared class list is unchanged).
- `index_onset_day == -1.0`, `index_shedding_at_day0` true on every cell.
- `propensity_draw.units_drawn > 0`; `delivery.caregiver.mode` resolves
  `on`; `presentation_draw_mode == 'once_per_course'`;
  `hand_reservoir_mode == 'hygiene_cycle'`; `delivery` echo's resolved
  `droplet_field_split` matches the shipped values on every arm (no
  MESS arm in this design).
- **Realized-share witnesses** (the CW-01 audit gap — declared set was
  checked, realized membership was not). Every cell carries a
  `crew_window` block:
  - `total_crew` = 1,045; `confined_crew_count` + `working_crew_count`
    = `total_crew` at activation and at end;
  - `exempt_work_zones` echoed verbatim on ZONE cells (null elsewhere);
  - `exempt_fraction_drawn` == `{"crew_general": k}` exactly on FRAC
    cells (k = 261/523/784), absent/empty elsewhere;
  - `realized_exempt_share` = working_crew / total_crew at activation —
    strictly in (0, 1) on ZONE and FRAC arms (0 or 1 means the gate
    never fired), ≈1 on D0;
  - `service_deliveries` recorded per cell.

## Report immediately if

Any audit invariant fails; a ZONE arm's realized exempt share departs
materially from its lottery expectation (report the realized
distribution); any arm lands the band with before-mass unmoved
(CHANNEL-LANDED — stop and report); `service_deliveries` collapses to
~zero on a confining arm (R3 starved); or child failure rate exceeds 5%.

## Non-goals

- No fitting — arm fractions and zone lists are declared probes; a
  landing is a magnitude to source afterward.
- No `CREW_DUTY_MIX` subclassing (family C — separate later stage).
- No passenger-side channel work (the map's F13/F14 legs, D2's
  confined-passenger bound is reported but not scored).
- No changes to the replay contract.
- No new arms mid-campaign: if the whole fractional axis skips the
  band, the readout says so.

## Required deltas before cells run

1. `telemetry_buffer/fields.py`: `work_zone` into
   `AGENT_OPTIONAL_FIELDS`; `infection_dynamics_bridge.py`
   `_export_optional_state` emits it (presence-checked passthrough).
2. `orchestrator_epoch.py` / `orchestrator_types.py`: the
   `exempt_work_zones` and `exempt_fraction` gates inside
   `confine_all_agents` / `confine_agents`, plumbed per-order through
   `step_quarantine_confinement` (whole-body, enforced, voluntary, and
   merged-LOCKDOWN paths); `SimulationState.exempt_fraction_draws`;
   `ship_simulation.py` passes `run_seed` for the dedicated draw
   stream.
3. `data/config/protocols.json`: `SOP-017-NARROW`,
   `SOP-017-WIDE`, `SOP-017-{QUARTER,HALF,THREEQ}` — verbatim SOP-017
   plus the new modifier.
4. `covid_boarding_screen.py`: `quarantine_witness` echoes the
   declared `exempt_work_zones` / `exempt_fraction`; new `crew_window`
   payload block (counts, realized share, zone decomposition, drawn
   sets, `service_deliveries`).
5. `picard_framework/runs/covid_crew_window_02_design.json` carrying
   this grid, the arm override blocks, and this verdict grammar
   verbatim in `admissibility`.
6. `campaigns/covid/crew_window_02/` registration (campaign.json,
   cell.py, entry.py, readout.py, LEDGER.md); jobdef
   `picard-covid-crew-window-02`, image `covid-crew-window-02`, S3
   prefix `campaign/covid_crew_window_02/`.

Execution: the campaign-preflight gate in full — local smoke proving
each new modifier reaches the confinement path (a confined
exempt-classed agent must show up in `quarantined_ids`), dry-run count
= 240, pinned image digest + jobdef revision, manifest in S3, then the
20-seed canary read out and reported before the array.
