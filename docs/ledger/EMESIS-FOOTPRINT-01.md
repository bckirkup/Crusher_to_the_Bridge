# EMESIS-FOOTPRINT-01
**Date:** 2026-10-26
**Commit:** ee16ca0882cdc924302b8f06e211c9f305b1f71f
**Pathogens:** norwalk_gi
**Status:** open

The touchable share of an emesis bolus was computed as
`high_touch_area / deposition_footprint` — the zone's *total* high-touch
inventory divided by the 7.8 m² bolus footprint (`_emit_emesis`,
`engines/transmission_core.py`). Two consequences, both measured
mechanically on the FLUSH-S4 `off` arm replay:

- The share had no dependence on room size, and the relation ran backwards:
  a vomit in a theatre and a vomit in a stateroom put the same fraction of
  their mass onto hand-transferable surface — largest share in the largest
  venue (dining clipped to 1.0, public 0.77) and smallest in a cabin (0.19).
- The resulting mass entered the zone-wide scalar surface pool, so every
  susceptible in the zone drew from one bolus in the same epoch. On the
  archived `fl_spr_12d` seed 8105 voyage (621 ever-infected), a single
  subclinical passenger's emesis event at epoch 16 deposited 1.35e8 GEC into
  MainTheater's pool and produced 100 infections among 562 occupants — the
  "explosive voyage" tail behind `off`-arm posting readings of 5 per 1,000
  (classic) and 20 per 1,000 (spirit).

## Repair

- **Part 1** — the touchable share is now the high-touch areal fraction of
  the room: `min(1.0, high_touch_area / max(floor_area, footprint_area))`.
  Floor area is the layout's declared `floor_area_m2` where present
  (sanitary zones) else the unit's air volume over `PASSENGER_DECK_HEIGHT_M`
  (2.8 m, Grade C, Bruce 2014 — see the constant's provenance block);
  cabin compartments resolve to their berth share of the block volume, so a
  stateroom gets a realistic ~15 m² floor with no new partition. The result
  is weakly sensitive to the deck height: floor area ∝ 1/h, so 2.5 vs 2.8 m
  moves the touchable fraction by ~12%, not a decade. **The change is not a
  uniform reduction**: public venues ~0.77 → ~0.003, staterooms 0.19 →
  ~0.10, and sanitary venues rise 0.064 → ~0.19 because a head declares a
  2.7 m²/WC floor.
- **Part 2** — the touchable mass is filed as an `EmesisPatch` localised to
  the bolus footprint instead of joining the zone pool. Each susceptible
  occupant is exposed with probability `footprint_area / floor_area`; the
  per-touch transfer chain is unchanged and the patch's areal density
  equals the zone share's density by construction — the extent shrinks, the
  dose does not. Patches decay at the same `_surface_survival` and are
  cleaned/disinfected by the same machinery as the zone pool; mass stays
  visible to `zone_surface_mass` (the swab reads a venue-average density,
  which under-reads a targeted swab of the patch itself — known limitation).
  A unit with no patches consumes no RNG, so voyages without emesis events
  are bit-identical to before.

No emesis source term, dose-response, or transfer constant changed.

Review follow-up on the same branch: patch consumption scales the unit's
strain-composition bucket by the delivered share of the unit's *total*
surface mass (zone pool plus patches), not of the patch alone — the bucket
holds both, so scaling by patch mass would wipe pool composition. And
`zone_surface_mass(zone)` with no pathogen argument sums patches across
all pathogens, matching the per-pathogen view.

## Consequences for recorded numbers

- FLUSH-S4 (`7f689b9`) `off`-arm posting readings (5/1,000 classic, 20/1,000
  spirit) were measured on the zone-wide delivery and are invalidated; the
  FLUSH-S3 re-bracket (`65d9fb2`) and every earlier campaign's fomite-route
  attributions carry the same deposition defect and are historical.
- Ledger item 26(d)–(f)'s scalar-per-zone limitation is partly addressed
  for emesis only: continuous hand deposition remains a zone-wide pool.
- Whether a vomit incident triggers immediate cleanup is held as a separate
  task and deliberately not in this change.
- Remaining known limitations, recorded not fixed: a targeted swab of the
  patch itself is not modelled (the swab sees a venue-average density), and
  vomiting is *aimed* — toilet, basin, bed — rather than spread uniformly
  over the deck, so the uniform-footprint rule understates high-touch
  deposition in cabins and heads where the aim point is high-touch
  hardware.
