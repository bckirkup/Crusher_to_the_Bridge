# Greg Mortimer platform provenance

> Status: current — provenance for the `greg_mortimer` platform bundle.

## Primary source
- Aurora Expeditions / Chimu Adventures published deck plan PDF: https://www.chimuadventures.com/sites/default/files/2025-11/Aurora%20Greg%20Mortimer-A3%20-%20Deck%20Plan.pdf
- Mirror checked: https://www.chimuadventures.com/sites/default/files/2026-04/Aurora%2520Greg%2520Mortimer-A3%2520-%2520Deck%2520Plan%5B1%5D.pdf

## Measured / published facts used
- Length 104.4 m, beam 18.4 m, built 2019, IMO 9834648, Polar Class 6 (Ulstein reference; SunStone vessel page).
- Passenger capacity: Aurora lists 148 maximum / 130 on expedition and 76 cabins; SunStone lists 80 passenger cabins / 160 passenger beds; operator fact sheet lists max 130 passengers plus expedition/hotel/deck-engine crew complements.
- Published deck plan shows decks 3-8, cabin numbers 301-318, 401-434, 601-630, 701-704, and feature legend items 1-24.

## Declared model choices / inferences
- Zone IDs are grouped cabin-corridor blocks, not individual staterooms. Passenger occupancy is allocated to sum to the 148-passenger maximum; actual voyage complements vary.
- Crew berthing, crew mess, galley, laundry, and machinery spaces are inferred below the published passenger decks because the A3 sheet does not show decks 1-2.
- `nominal_complement` uses 148 passengers and 95 crew. The 95-crew value is within the operator fact sheet crew-component range and matches the documented 2020 complement; it is an archetype declaration, not a fitted constant.
- HVAC ACHs, `oa_fraction`, `hvac_duty`, confinement/contact factors, and buffet contamination multiplier use existing repository cruise-platform conventions; no Greg Mortimer HVAC drawings or measurements were available.
- Dining service is declared `buffet` for the main dining room because Aurora describes buffet-style family meals with a la carte dinner; the optional private dining area is `specialty`.
