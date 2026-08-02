# Enterprise Cabin-Resolution Revision

**Status:** Implemented — Constitution + Galaxy rebuilt to cruise-class (or
higher) spatial resolution via informed fiction engineering guesses.

Regenerate::

```bash
python3 scripts/generate_enterprise_platform_layout.py --platform enterprise_constitution_tos
python3 scripts/generate_enterprise_platform_layout.py --platform enterprise_galaxy_tng
python3 scripts/generate_platform_contam_prj.py --hobbyist --platform enterprise_constitution_tos
python3 scripts/generate_platform_contam_prj.py --hobbyist --platform enterprise_galaxy_tng
python3 scripts/precompute_deck_assets.py --platform enterprise_constitution_tos
python3 scripts/precompute_deck_assets.py --platform enterprise_galaxy_tng
```

See `scripts/enterprise_platform_recipes.py` for the authoritative zone / HVAC /
adjacency inventories.

## Premise

Cruise cabin-corridor models taught us that **well-mixed berthing wards invalidate
quarantine**. Starships deserve the same discipline. We make **informed guesses**
from Trek cues + spacecraft/naval practice; fiction frees us to be *more*
detailed than any real cruise survey.

Shared assumptions:

1. **Atmosphere is compartmentalized ECLSS** — local fans → deck trunks → hull
   AHUs; turbolifts and Jefferies tubes are ducts *and* leakage paths.
2. **Pocket doors** are the default orifice (`pocket_door`): tight when closed,
   schedule-modulated open pulses. Not permanent passageways.
3. **Berthing is cabin-scale** (`Cabin_Corridor` + cabin-mates). Officers share
   less; enlisted share more; Galaxy adds family suites.
4. **Medical and engineering are isolated AHU islands** (HEPA / high ACH).
5. **Breach readiness** is encoded in the compartment graph (pressure bulkheads
   at saucer/drive neck and sector boundaries). Dynamic dump-to-space is a
   future runtime hook; the topology must already support isolation.

## Constitution-class (~430 crew)

Target: **~50–55 zones** (expedition/classic class resolution).

| Block | Count | Notes |
|-------|------:|-------|
| Enlisted cabin corridors | 12 | Decks 4–6 × Port/Stbd × Fwd/Aft; ~30–36 crew each |
| Officer cabin corridors | 6 | Decks 5–6 × Fwd/Mid/Aft; cabin_size 1–2 |
| Ops / command | 4 | Bridge, BriefRoom, Comms, Library |
| Medical | 3 | Sickbay + 2 isolation bays |
| Science / security | 5 | Science×2, Transporter×2, Security, Brig (−1 if merged) |
| Living / food | 5 | RecDeck, Gym, Galley, Mess_Hall, Heads |
| Logistics | 3 | StoresDry, StoresCold, Armory |
| Engineering | 4 | EngMain, WarpCore, EPSDist, Jefferies |
| Pressure / access | 2 | NeckHub (saucer↔secondary), Airlock |

HVAC: command, ops, living, medical (HEPA), galley/service, engineering,
stores. Cross-hull trunk throttled at the neck. OA default ~0.15 (closed
ecosystem fiction); medical 0.40 exhaust-biased.

Ventilation types: all berthing `interior_hvac` (no balconies). Optional
future enum for `cabin_recirc` not required — `interior_hvac` is correct.

## Galaxy-class (~1,000+ with families)

Target: **~85–95 zones** (spirit-class resolution or denser).

| Block | Count | Notes |
|-------|------:|-------|
| Enlisted corridors | 36 | Decks 7–12 × P/S × F/M/A |
| Family suite corridors | 12 | Decks 23–25 × P/S × F/A; cabin_size 3–4 |
| Officer corridors | 6 | Decks 8–9 × F/M/A |
| Public / civic | ~20 | TenFwd, Holodeck×2, School, Arboretum, Lounges, … |
| Medical | 4 | Sickbay ward + 3 isol |
| Engineering / drive | 5 | MainEng, WarpCore, EPS, Jefferies, Deflector |
| Flight / cargo | 4 | Shuttlebay, Cargo×2, Airlock |
| Logistics / heads | ~6 | Galley, Mess, Heads, Stores, Armory |

HVAC: saucer living / family / public / medical / command; drive-section
engineering island; shuttlebay high-ACH when operational. Saucer-separation
implies the drive and saucer graphs can be treated as weakly coupled
pressure domains (neck bulkheads).

Some family/inner-ring corridors use `atrium_view` where they face a
multi-deck civic void (Arboretum / Ten-Forward stack); most berthing remains
`interior_hvac`.

## Orifice vocabulary (additions)

| Adjacency `type` | Contam orifice | Role |
|------------------|----------------|------|
| `pocket_door` | PocketDoor ~1.4 m² + DoorTrafficW | Default shipboard door |
| `pressure_bulkhead` | PressBlk ~0.002 m² | Sector / neck seal residual |
| `turbolift` | existing | Vertical bank leakage |
| `connecting_tube` | existing | Saucer↔secondary neck duct |
| `service_corridor` | existing | Jefferies / service |

## Comparison to prior fiction shells

| | Old TOS / TNG | Revised |
|--|---------------|---------|
| Berthing | 2 well-mixed Rooms | Cabin corridors + mates |
| Zones | 13 / 17 | ~52 / ~90 |
| Doors | doorway/passageway | pocket_door dominant |
| Breach | not representable | bulkhead edges in graph |
| Contam paths | ~100 / ~130 | scales with adjacency |

## Calibration / campaigns

No AGE targets (fiction). Smoke Picard specs should use revised agent counts
(~430 Constitution, ~1000 Galaxy). Fiction pathogen bundles unchanged.
