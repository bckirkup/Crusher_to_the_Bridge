# Class reference photos & architectural plates

Precompute (`python3 scripts/precompute_deck_assets.py`) builds vector
`deck_graphics.geojson`, optional Wikimedia class photos, and registers
**user-supplied architectural plates** under each platform’s `graphics/` folder.

## Architectural graphics (preferred)

Place plates when configuring a ship:

```
data/platforms/<platform_id>/graphics/
  graphics.json          # manifest
  elevation.jpg          # side elevation of the whole ship
  plan_overview.jpg      # top-down hull / class plan
  decks/<deck>_plan.jpg  # optional per-deck plans
```

The dashboard **Tactical Sensor Grid** shows elevation and a single-deck plan
side-by-side so drawings do not overwrite each other. Compartment polygons are
packed per deck into the hull plan (non-overlapping).

### Platforms with committed notional plates

| Platform | Style | Notes |
|----------|-------|-------|
| mega_cruise_5000 | AI-generated notional schematic | Original composition (plan + elevation) |
| enterprise_galaxy_tng | AI-generated fiction-adapted | Simplified Galaxy-inspired silhouette — **not** televised Star Trek artwork |
| enterprise_constitution_tos | AI-generated fiction-adapted | Simplified Constitution-inspired silhouette — **not** televised Star Trek artwork |

## Legacy Wikimedia catalog

Sources and URLs for remaining platforms: `class_photo_catalog.json`

| Platform | Image subject | License |
|----------|---------------|---------|
| destroyer_baseline | USS Gleaves (DD-423) | US Navy — public domain |
| fletcher_class_destroyer | Fletcher-class technical drawing, 1954 | US Navy — public domain |
| legend_class_nsc | USCGC Hamilton (WHEC-715) | US Coast Guard — public domain |
| san_antonio_class_lpd | USS Austin (LPD-4) | US Navy — public domain |
| expedition_cruise_300 | Cruise ship side elevation | CC BY-SA 3.0 (Marcusroos) |
| messy_cruise_500 | Icon of the Seas (legacy archive) | CC BY-SA 2.0 |

## Offline / air-gapped runs

If download fails and no `graphics/` plates exist, precompute falls back to the
synthetic blueprint plate (grid + vector hull) with no network required.

## Refreshing assets

```bash
python3 scripts/precompute_deck_assets.py
# or one platform:
python3 scripts/precompute_deck_assets.py --platform mega_cruise_5000
```
