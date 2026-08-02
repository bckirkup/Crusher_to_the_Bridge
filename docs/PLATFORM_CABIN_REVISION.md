# Mega Cruise Platform Revision: Cabin-Level Spatial Resolution

**Status:** Implemented in `data/platforms/mega_cruise_5000/` (Feb 2026). Cabin-mate
direct-contact pairing implemented June 2026 — see `docs/SHEDDING_AND_CABINMATES.md`.
Regenerate layout: `python3 scripts/generate_mega_cruise_cabin_layout.py`. Legacy
well-mixed model: `data/platforms/messy_cruise_500/`.

**Fleet extension (Aug 2026):** Additional CDC size-class platforms use the shared
generator `scripts/generate_cruise_platform_layout.py` + recipes in
`scripts/cruise_platform_recipes.py`:

| Platform | CDC category | Notes |
|----------|--------------|-------|
| `expedition_cruise_450` | Small/Medium | Replaces `expedition_cruise_300` (archived) |
| `classic_cruise_1900` | Large | Cabin-corridor + buffet / promenade / atrium |
| `spirit_cruise_3000` | Extra-Large | Multi-specialty dining, teen/sports, isolation ward |
| `mega_cruise_5000` | Super-Mega | Reference standard |

Fiction starship platforms reuse the same cabin-corridor generator extensions
(`id_prefix`, `extra_corridors`, Contam-safe IDs) via
`scripts/generate_enterprise_platform_layout.py` — see
`docs/ENTERPRISE_CABIN_REVISION.md` for Constitution / Galaxy inventories.

Future calibration targets (AGE per 100K traveler-days; **not yet enforced in-repo**):
expedition 9.06, classic 21.4, spirit 22.1, mega 24.4.

Wall-clock cost of the cabin-corridor fleet can be characterised with
`python3 _epoch_timing/time_epochs.py --compare-cruise` (see `_epoch_timing/README.md`).

## Problem

The legacy `messy_cruise_500` platform (archived from the original `mega_cruise_5000`
berthing model) used 27 passenger cabin blocks of ~200 occupants each. These blocks
were modeled as well-mixed zones — everyone in `Passenger_Cabins_D6_Port` was in
direct contact with everyone else, as if in an open ward. Cabin confinement was
therefore meaningless: confining someone to their "cabin zone" still exposed them
to ~199 other people via direct contact, plus thousands more via shared HVAC.

**Legacy platform:** `data/platforms/messy_cruise_500/` — retained for regression and
comparison only. Do not use for quarantine or cabin-confinement studies.

**Active revision target:** `data/platforms/mega_cruise_5000/` — cabin-corridor zones
with per-stateroom cabin-mate pairing at init. Smaller cruise classes follow the same
`Cabin_Corridor` schema via the shared recipe generator.

## Oasis-Class Reference Data

- 2,796 passenger staterooms total
- ~6,400 max passengers (double occupancy + some triples/quads)
- 2,150 crew in ~1,200 crew cabins
- 10 passenger cabin decks (Decks 6–14, skipping 13)
- Cabin types:
  - ~529 Interior cabins: 16 m², no outdoor air, fully HVAC-dependent
  - ~1,500 Balcony cabins: 17 m² + outdoor balcony, partial natural ventilation
  - ~170 Suites: 26–143 m², some with private HVAC
  - ~600 Promenade/Central Park view: interior but open to atrium
- ~280 passenger cabins per deck, roughly split port/starboard/central
- Crew cabins: Decks 1–4, shared 2–4 per cabin

## Proposed Zone Structure

### Passenger Cabins (replace 27 blocks with ~81 corridor sections)

For each of 9 passenger decks × 3 sections (port/starboard/central):

- Each corridor section: ~30 cabins, ~60 occupants
- Zone type: `Cabin_Corridor`
- Volume: ~30 cabins × 40 m³/cabin = 1,200 m³ (cabin volumes only, not shared)
- Max occupancy: 60–80

Naming: `Pax_Corridor_D{deck}_{Port|Stbd|Central}_{Fwd|Mid|Aft}`

Example: `PC_D6_P_F` (~10 cabins, ~67 pax, 1200 m³)

### Cabin Ventilation Type Flag

Each corridor section gets a ventilation type:

- `interior_hvac` — fully dependent on ship HVAC, no outdoor air
- `balcony_partial` — outdoor air exchange through balcony doors (when open)
- `atrium_view` — opens to Central Park or Royal Promenade (semi-outdoor)

This affects the HVAC transmission model: balcony cabins should have reduced aerosol
accumulation due to outdoor air dilution (`BALCONY_AEROSOL_REDUCTION = 0.5` in
`TransmissionCore`).

### Crew Cabins (replace 4 blocks with 12 sections)

4 crew decks × 3 sections = 12 zones:

- Each: ~100 crew, shared cabins (2–4 per cabin)
- Higher density, less ventilation than passenger cabins
- Naming: `Crew_Corridor_D{deck}_{Fwd|Mid|Aft}`

### HVAC Zones (revise from 2 cabin AHUs to more granular)

Current (legacy `messy_cruise_500`): 2 AHUs serve all cabins (port and stbd/central).

Revised:

- Each deck has its own air handling branch (fan coil units per deck)
- Cross-deck recirculation through main AHU trunk
- Practical: 9 deck-level HVAC sub-zones for passengers, 4 for crew
- Each sub-zone still connects to the main trunk but with reduced cross-flow

### Key Transmission Parameters for Cabin Corridors

- **Direct contact:** hallway encounter rate vs well-mixed ward
  (`corridor_direct_contact_factor = 0.15` on platform layout)
- **Confinement / cabin-mates:** when quarantined in a `Cabin_Corridor` zone,
  direct contact is **pair-based** via `cabin_mate_ids`:
  - Full dose to cabin-mates (shared stateroom)
  - `0.01×` dose to non-mates (closed door / hallway)
  - Implemented in `TransmissionCore._cabin_pair_contact_factor()`
- **HVAC/aerosol:** primary inter-cabin transmission route; confinement does **not**
  reduce HVAC dose
- **Fomite:** corridor surfaces; confined agents skip fomite pickup
- **Balcony ventilation:** `balcony_partial` zones reduce droplet/HVAC aerosol dose

### Confinement Model

When an agent is confined (quarantined/isolated):

- Their `current_location` stays in their cabin corridor zone
- Direct contact is restricted to cabin-mates (2–3 people), not all ~67 corridor occupants
- Fomite contribution is zeroed (they're not touching corridor surfaces)
- HVAC/aerosol exposure continues at corridor section level
- If balcony cabin: aerosol exposure reduced by balcony ventilation factor

Initialization: `orchestrator_init.assign_cabin_mates()` groups agents by
`home_zone` using `cabin_size` (default 2 pax / 3 crew per stateroom).

## Implementation Plan

1. ✅ Generate `spatial_layout.json` with ~93 cabin zones + existing public zones
2. ✅ Generate `air_flow_paths.json` with deck-level HVAC sub-zones
3. ✅ Add `confinement_isolation_factor` to TransmissionCore (legacy uniform factor;
   superseded for direct contact by cabin-mate pairing)
4. ✅ Add `cabin_ventilation_type` to zone metadata
5. ✅ Add `cabin_size` to corridor zones (generator script)
6. ✅ Cabin-mate pairing at init + pair-based direct contact under confinement

## Impact on Simulation Performance

- Zone count: 67 → ~129 (2×)
- But each zone has fewer occupants (~60 vs ~200)
- Transmission calculations are O(n²) within zones
- Net: fewer per-zone calculations, more zones = roughly similar total compute
