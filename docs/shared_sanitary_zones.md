# Shared sanitary zones across every hull — structural design v1

> **Status:** Implemented — heads on all 12 platforms
> (`data/platforms/*/spatial_layout.json`), exhaust-only one-way air
> wiring, `transmission.sanitary_visit_mode` (`none` default /
> `dwell_weighted`), Bridge zones on the three cruise hulls that lacked
> them. Landed on the shared-sanitary-zones branch; the flush emission is
> a separate change.

Nothing in this design is chosen to move posting frequency, the
VSP attack-rate distributions, A4, A9, Park's surface measurements or the
passenger/crew ratio, and no flush emission is part of it.

As landed, three implementation notes stand against the text below: the
zone record gained a `serves` array in the schema (preferred to encoding
the served-cluster mapping inside `description`); the visit arm's fomite
surface class is `sanitary` with the declared-geometry area basis
described at `HIGH_TOUCH_AREA_M2`; and visits to a host's own cabin
fittings while at home count in telemetry but add no fomite exposure,
because whole-epoch occupancy already covers that venue.

## 0. Why this is a structural change and not a constant

The model has no sanitary space of any kind. A host with diarrhoea who is in
the theatre, the buffet, the pool deck or a galley at that epoch has nowhere to
defecate, and there is no shared air volume for a flush to dose. Adding an
aerosol constant to a model with no head would put the emission in a
1,400 m³ dining room or a 100 m³ cabin fallback — which is the repository's
recurring defect archetype (a well-mixed pool standing in for a small number of
concentrated events) committed deliberately. So the structure lands first, is
measured on its own, and the flush emission follows as a separate change.

The structure is expected to matter before any flush term exists: a public head
is a high-touch shared surface visited by passengers from every deck and by
crew, so it creates a fomite mixing venue the model currently lacks entirely.

## 1. What the inventory found

Three findings, in descending order of how much they should bother us.

1. **No sanitary zone exists on any of the twelve platforms.** The zone `type`
   enum in `schemas/spatial_layout.schema.json` is closed over
   `Free`, `Dining`, `Room`, `Medical`, `Engineering`, `Cabin_Corridor`; there
   is no member a head could take.

2. **`classic_cruise_1900`, `spirit_cruise_3000` and `expedition_cruise_450`
   have no `Bridge` zone.** They are the only three hulls without one — every
   naval hull, both Enterprises, `mega_cruise_5000`, `messy_cruise_500` and
   even the superseded `expedition_cruise_300` have a bridge — and they are
   precisely the three hulls every norovirus campaign has run on. The deck and
   navigation watch has had nowhere to be for the whole series. This looks like
   a regression introduced when these three moved to recipe generation
   (`scripts/cruise_platform_recipes.py`), since the legacy hand-authored
   expedition layout still has its bridge.

3. **Both Enterprise hulls carry a `HeadsMain` zone typed `Free`**, at 90 m³
   (TOS) and 110 m³ (TNG) with `max_occupancy` 20 and 30. Typed `Free` it
   enters `_leisure_catalog`, so it is a whole-epoch leisure destination: the
   model currently believes twenty people spend an hour together in the
   lavatory. These are replaced by the structure below rather than kept.

## 2. Provisioning — which zones get a head, and how many fixtures

Every rule is regulatory and none is fitted. Occupant loads are each layout's
own `max_occupancy`, split 50/50 by sex; MLC 2006 Standard A3.1.11(a) and
VSP 2025 §36 both require separate facilities for men and for women, so
provisioning is emitted per (deck cluster × sex).

| served class | rule | fixtures |
|---|---|---|
| food-preparation area (galley, crew galley) | VSP 2025 §7.3.1 — at least one employee toilet room near the work area of *all* food preparation areas, inside the area or in the passageway immediately outside | 1 per 25 employees on the maximum shift |
| child activity centre | VSP 2025 §34.1.2 | 1 child-sized toilet per 25 children at maximum capacity |
| recreational water facility (pool, waterpark, solarium, sports court, aqua theatre, ice rink) | VSP 2025 §26.5/§26.6 fix *placement* — within 60 m walking distance of every RWF and of every waterslide staircase entrance, same or adjacent deck — but state no fixture count; count from IPC Table 403.1 indoor-pool ratio | 1 per 75 male, 1 per 40 female |
| assembly (theatre, casino, promenade, lounge, library, spa, shops, reception, gallery, arboretum) | VSP is silent; IPC Table 403.1 assembly ratio as a declared land-side analogue | 1 per 125 male, 1 per 65 female |
| food service (dining room, buffet, specialty, crew mess) | IPC Table 403.1 restaurant ratio | 1 per 75 male, 1 per 75 female |
| navigating bridge; machinery space / engine control | MLC 2006 Standard A3.1.11(b) — sanitary facilities within easy access of the navigating bridge *and* the machinery space or engine room control centre | 1 each (watch complement is small) |
| service work area (laundry, stores, waste treatment) and medical | IPC Table 403.1 business ratio | 1 per 25 for the first 50 |
| passenger and crew cabins | MLC 2006 Standard A3.1.11(c) requires 1 toilet per ≤6 persons *who do not have personal facilities*; every cabin in the model has its own fittings, so no public head is provisioned for berthing | — |

Two functional requirements that bear on later mechanism work rather than on
counts: VSP §7.3.2 requires exhaust ventilation in every toilet room and
forbids air hand dryers, and §36.2/§7.3.3 require hands-free exit, with
doorless entry the standard arrangement — so your "in a shared restroom there
is no door to close" is literally what the construction standard prescribes.

Where a single block would exceed 10 water closets it is split into two blocks,
representing the fore and aft lobbies that serve a large assembly space in
practice. That split is a declared structural assumption (Grade C), not a
measurement.

## 3. Geometry and ventilation — derived, with an independent check

| quantity | value | basis |
|---|---|---|
| floor area per water closet | 2.7 m² | 0.9 × 1.5 m stall footprint, doubled to carry the handwashing and circulation share. **Grade C declared geometry** — no source measures ship head area. |
| deckhead height | 2.3 m | ship accommodation typical; MLC 2006 Standard A3.1.6 sets a 2.03 m headroom floor |
| volume per water closet | 6.21 m³ | product of the two above |
| exhaust | 70 cfm = 118.9 m³/h per water closet | ASHRAE 62.1 Table 6-5, public toilets, intermittent operation |
| `base_ach` | **19.2**, independent of fixture count | exhaust ÷ volume; both scale with the fixture count |

The check worth having: Johnson et al. 2013, the study whose droplet-nuclei
generation rate is the candidate anchor for the later flush emission, measured
in a 5 m³ water closet ventilated at ~18 ACH. A code-compliant ship head comes
out at 19.2 ACH from an entirely independent derivation. The flush measurement's
setting and a ship head are therefore ventilation-comparable, which is a
precondition for the emission being commensurable at all — and it was not
arranged, it fell out.

Resulting provisioning (`scripts/derive_sanitary_provisioning.py`):

| platform | head zones | water closets | total head volume |
|---|---:|---:|---:|
| classic_cruise_1900 | 16 | 72 | 447 m³ |
| spirit_cruise_3000 | 27 | 114 | 708 m³ |
| expedition_cruise_450 | 12 | 37 | 230 m³ |
| mega_cruise_5000 | 63 | 355 | 2,205 m³ |
| messy_cruise_500 | 63 | 355 | 2,205 m³ |
| expedition_cruise_300 (superseded) | 11 | 38 | 236 m³ |
| enterprise_constitution_tos | 19 | 37 | 230 m³ |
| enterprise_galaxy_tng | 37 | 55 | 342 m³ |
| destroyer_baseline | 3 | 6 | 37 m³ |
| fletcher_class_destroyer | 13 | 27 | 168 m³ |
| legend_class_nsc | 9 | 20 | 124 m³ |
| san_antonio_class_lpd | 7 | 25 | 155 m³ |

Per-block volumes run 6–62 m³. That is the point: the smallest existing
compartment abstraction is a 100 m³ cabin fallback, so a head is the first zone
in the model whose volume is small enough for a concentrated event to matter.

## 4. A new zone type, not `Free`

`Sanitary` is added to the `type` enum. Typing heads `Free` would be a smaller
diff and is wrong: `_free_zones`/`_leisure_catalog`
(`engines/infection_dynamics_bridge.py:1720-1762`) would make a 6 m³ head an
hour-long leisure destination drawn in proportion to `max_occupancy` — the
Enterprise `HeadsMain` defect, generalised to every hull.

A new enum member is inert by construction (it enters no catalog and no
schedule token can reach it), so the following consumers get explicit entries
rather than silent defaults:

- `_fomite_zone_class` (`transmission_core.py:4160`) — a `sanitary` surface
  class. Without it a head falls silently to `"public"` and its
  `HIGH_TOUCH_AREA_M2` 6.0 m², which would spread a head's touchable surface
  over the same area as a promenade.
- `DEFAULT_HETEROGENEOUS_SIGMA_BY_ZONE_TYPE` (`transmission_core.py:614`),
  `SURFACE_TYPE_RECOVERY_ORDER` / `DEFAULT_RECOVERY_BY_SURFACE_TYPE`
  (`crusher_labs/modalities/surface_strain_recovery.py:33`), `ZONE_TYPE_MODIFIERS`
  (`crusher_labs/modalities/sequencing.py:73`).
- `tools/sanity_checker.py`'s `SpatialZone` does not validate `type` as an
  enum; it is tightened to the schema's list so the two cannot drift.

## 5. Air — exhaust-only and one-way

A head is on exhaust, so air flows *into* it from the space it serves and out
overboard. It must never be an air source for the space it serves, or a flush
would blow back into the theatre through the AHU.

`build_hvac_downstream_map` (`transmission_core.py:5611-5649`) makes members of
one `hvac_zones` group **mutually** downstream and treats `adjacency` edges as
**bidirectional** (both directions are appended). Only `cross_zone_links` are
directional. So:

- each head block is its own `hvac_zones` entry, `oa_fraction` 1.0, exhaust
  duty, `ach` 19.2 — one group per block, so two heads never mix through a
  shared AHU;
- transport in is one directional `cross_zone_links` edge from the served
  space's AHU to the head's, and there is **no** reverse edge and **no**
  `adjacency` edge;
- this also satisfies the coverage check in
  `scripts/generate_cruise_platform_layout.py:309-322`, which raises unless
  every non-exterior zone sits in exactly one HVAC group.

Heads are **not** added to `graywater_zones`. That list is the blackwater
collection point (engine/waste zones) and feeds an environmental-source route;
adding heads to it would introduce a second new mechanism inside this change.

## 6. Visits — transient and dwell-weighted, not whole-epoch occupancy

This is the part that decides whether the structure is physical. Occupancy in
the model is whole-epoch: an agent is in exactly one zone for the hour. Putting
400 theatre-goers in a 12 m³ head for an hour is not a small approximation, it
is the archetype defect again. Heads are therefore **not** a location an agent
occupies. They are a transient micro-environment an agent *visits* within an
epoch, and exposure is scaled by the visit's share of the epoch.

- **Visit rate.** Chung et al. 2009 (*J Urol*), 935 healthy male volunteers,
  3-day voiding diary: median 6 voids daily and 0.5 nightly. Grade B (healthy
  adults, not shipboard), origin `Ab`/`R`. The existing sourced defecation
  draw (`stool_events_per_day` 1.0 baseline, 5.63 diarrhoeal) is *not*
  duplicated — it is rerouted through the same resolution.
- **Dwell.** Gwynne et al. 2019 (*J Building Engineering*), 502 users of male,
  female and accessible bathrooms in a North American airport: mean dwell
  **155 s** with no queuing, female facilities 22% longer than male. Grade B
  (public transport hub), origin `Ab`. Exposure scales as dwell ÷ epoch, so a
  155 s visit to a 19.2 ACH head is 4.3% of an hourly epoch.
- **Where the visit happens is structural, not a parameter.** If the agent's
  location this epoch is its home cabin, the visit is to its own cabin
  fittings (the existing cabin compartment). Otherwise it is to the head
  serving its current zone. There is deliberately **no** free "fraction of
  visits away from the cabin" constant: it falls out of the schedule the model
  already has, so it cannot be tuned.
- **Concurrency** is whatever the Poisson visit draws produce against the
  block's fixture count — the mechanism by which a large hull's head is busier
  than a small hull's, which is the headcount channel this structure opens.
- **Its own RNG stream** (`sanitary_visits`), so the arm pairs exactly on
  matched seeds. #523 shipped an arm described as rng-neutral that was not,
  because its draws consumed the shared boarding stream, and the resulting
  noise was the size of the effect the sweep was meant to measure.
- **Default off** (`sanitary_visits: none`): the zones exist in the layout and
  no agent enters them, so the baseline is bit-identical to today's engine and
  the matched contrast measures the structure alone. Default-on is proposed
  after it is measured, not in the same change.

## 7. What this changes before any flush term exists

- A new fomite venue with cross-cohort mixing: heads are touched by passengers
  from every deck and by crew, where the existing surface pools are
  cabin-scoped or venue-scoped.
- Partial bridging of the passenger/crew separation, which the model currently
  gets almost entirely through dining and work zones.
- The first compartment small enough that a concentrated event is not diluted
  to nothing — which is why the flush emission is worth measuring afterwards
  and would not have been worth measuring before.
- Bridge zones on the three cruise hulls, which relocates the deck and
  navigation watch out of whatever zone currently absorbs it. This is a
  crew work-location change with a wider blast radius than a head, so it is
  a separate commit inside the change and separately attributed.

## 8. Blast radius

Schema/data: `schemas/spatial_layout.schema.json` (enum),
`schemas/air_flow_paths.schema.json` (exhaust duty), all twelve
`spatial_layout.json` + `air_flow_paths.json`, `deck_graphics.geojson`,
`deck_manifest.json`, `deck_hull.png` via `scripts/precompute_deck_assets.py`.

Generators (the layouts are generated, not hand-authored — roundtrip tests
assert rebuilt ids equal committed ids): `scripts/cruise_platform_recipes.py`,
`scripts/generate_cruise_platform_layout.py`,
`scripts/generate_mega_cruise_cabin_layout.py`,
`scripts/enterprise_platform_recipes.py`,
`scripts/generate_enterprise_platform_layout.py`,
`tools/ship_blueprint_import/` for the naval hulls.

Engine: `engines/infection_dynamics_bridge.py` (visit resolution, RNG stream),
`engines/transmission_core.py` (fomite class, sigma, dwell-weighted exposure),
`tools/sanity_checker.py`.

Goldens that will move, each to be attributed to a specific part of the diff
before it is touched: exact zone counts in
`tests/test_cruise_platform_cabin_corridor.py` (86/61/33 and the corridor
sub-counts), `tests/test_enterprise_platforms.py` (zone and contam-path minima,
`graywater_zones` exact lists), `tests/test_exterior_zone_hvac_isolation.py`,
`tests/test_graywater_zones.py`, `tests/test_json_schema_validation.py`,
contam `path_map.json` minima. Zone ids stay ≤ 15 characters (`_CONTAM_ID_MAX`).

## 9. Measurement

Matched seeds, both arms on one engine, `sanitary_visits` off vs on, on the
three campaign hulls at the complements already used, 7 and 12 days, with
route attribution on — so the structure's effect on fomite, direct contact and
posting is read as a paired contrast rather than against an archived arm. The
expected direction is a *rise* in fomite establishments from the new shared
surface; the honest possibility is that it is inert, which would itself
constrain how much of the missing amplification a flush term could supply.

## 10. Uncertainties documented now, swept later (flush change, not this one)

- **Vacuum blackwater vs gravity/flushometer.** Every virus or surrogate
  measurement available (Boles 2021, Johnson 2013, Best 2011, Wilson 2020) is
  gravity or flushometer. Cruise ships use vacuum systems, for which the only
  evidence is aircraft-lavatory particle counts (Li 2022) and no virus. A
  declared system-type axis, swept, not pinned.
- **Aerosol fraction across ~5 decades**: Johnson's droplet-nuclei generation
  rate (1e-9–8e-8 of bowl load) against Boles' near-field back-calculation
  (~1e-4–1e-3). Reported as a swept Grade C axis with both anchors named.
- **Private cabin bathroom containment** — door open/closed, and the
  open/open, open/closed, closed/closed combinations across a cabin's two
  doors — applies only to the cabin emitter. A shared head has no door to
  close, so its escape term is ventilation and traffic, and the two must not
  share a variable.
- **Head volume and ACH**, above, as declared geometry with a Grade C floor
  area.
- **Bidets and seat washers: out of scope**, per instruction.
- Stall-level containment within a head, queueing, and hand-dryer aerosol
  (VSP forbids air dryers in toilet rooms, so this one is closed) are named
  and not modelled.

## 11. Not in this change

Flush aerosolisation; any new emission constant; the COVID
`airborne_emission_fraction` inconsistency; graywater/blackwater routing;
default-on for the visit mechanism; the flush campaign.
