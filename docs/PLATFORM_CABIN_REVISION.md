# Mega Cruise Platform Revision: Cabin-Level Spatial Resolution

**Status:** Implemented in `data/platforms/mega_cruise_5000/` (Feb 2026). Regenerate with
`python3 scripts/generate_mega_cruise_cabin_layout.py`. Legacy well-mixed model:
`data/platforms/messy_cruise_500/`.

## Problem

The legacy `messy_cruise_500` platform (archived from the original `mega_cruise_5000`
berthing model) used 27 passenger cabin blocks of ~200 occupants each. These blocks
were modeled as well-mixed zones — everyone in `Passenger_Cabins_D6_Port` was in
direct contact with everyone else, as if in an open ward. Cabin confinement was
therefore meaningless: confining someone to their "cabin zone" still exposed them
to ~199 other people via direct contact, plus thousands more via shared HVAC.

**Legacy platform:** `data/platforms/messy_cruise_500/` — retained for regression and
comparison only. Do not use for quarantine or cabin-confinement studies.

**Active revision target:** `data/platforms/mega_cruise_5000/` — to be updated per this
document.

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

Naming: `Pax_Corridor_D{deck}_{Port|Stbd|Central}`

Example: `Pax_Corridor_D6_Port` (30 cabins, 60 pax, 1200 m³)

### Cabin Ventilation Type Flag

Each corridor section gets a ventilation type:

- `interior_hvac` — fully dependent on ship HVAC, no outdoor air
- `balcony_partial` — outdoor air exchange through balcony doors (when open)
- `atrium_view` — opens to Central Park or Royal Promenade (semi-outdoor)

This affects the HVAC transmission model: balcony cabins should have reduced aerosol
accumulation due to outdoor air dilution.

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

- **Direct contact:** should be much lower than the legacy model
  - Within a cabin corridor, direct contact should model hallway encounters, not
    room-sharing. A person confined to their cabin should have near-zero direct
    contact with other cabins on their corridor.
  - Need a `confinement_isolation_factor` that reduces direct contact dose by 90–95%
    for confined agents (they only contact their cabin-mates)
- **HVAC/aerosol:** the primary inter-cabin transmission route
  - Depends on corridor section sharing an AHU branch
  - Balcony cabins with doors open: 50% reduction in aerosol exposure
- **Fomite:** corridor surfaces (handrails, door handles, elevator buttons)
  - Relevant for norovirus, less so for respiratory

### Confinement Model Fix

When an agent is confined (quarantined/isolated):

- Their `current_location` stays in their cabin corridor zone
- Direct contact is restricted to cabin-mates only (2–4 people), not all 60
- Fomite contribution is zeroed (they're not touching corridor surfaces)
- HVAC/aerosol exposure continues at the corridor section level
- If balcony cabin: aerosol exposure reduced by balcony ventilation factor

This requires a change in the transmission core: confined agents should have a
modified contact multiplier, not just a location assignment.

## Implementation Plan

1. Generate new `spatial_layout.json` with ~93 cabin zones + existing 40 public zones ≈ 133 total
2. Generate new `air_flow_paths.json` with deck-level HVAC sub-zones
3. Add `confinement_isolation_factor` to TransmissionCore
4. Add `cabin_ventilation_type` to zone metadata
5. Recalibrate `dose_adjustment` at the new zone resolution

## Impact on Simulation Performance

- Zone count: 67 → ~133 (2×)
- But each zone has fewer occupants (~60 vs ~200)
- Transmission calculations are O(n²) within zones
- Net: fewer per-zone calculations, more zones = roughly similar total compute
