# Class reference photos (dashboard deck plates)

Precompute (`python3 scripts/precompute_deck_assets.py`) downloads representative
images from [Wikimedia Commons](https://commons.wikimedia.org/) (or other
licenses noted in `class_photo_catalog.json`), composites them under the
vector hull outline, and writes `deck_blueprint_bg.png` per platform.

## Catalog

Sources and URLs: `class_photo_catalog.json`

## Licenses (summary)

| Platform | Image subject | License |
|----------|---------------|---------|
| destroyer_baseline | USS Arleigh Burke (DDG-51) | US Navy — public domain |
| fletcher_class_destroyer | Fletcher-class technical drawing, 1954 | US Navy — public domain |
| legend_class_nsc | USCGC Bertholf (WMSL-750) | US Coast Guard — public domain |
| san_antonio_class_lpd | USS San Antonio (LPD-17) | US Navy — public domain |
| expedition_cruise_300 | Cruise ship side elevation | CC BY-SA 3.0 (Marcusroos) |
| mega_cruise_5000 | Icon of the Seas | CC BY-SA 2.0 (Kahunapule Michael Johnson) |
| enterprise_constitution_tos | USS Enterprise (CVN-65) | US Navy — public domain; **fiction-adapted** |
| enterprise_galaxy_tng | DD silhouette | US Navy — public domain; **fiction-adapted** |

Fiction-adapted platforms use real-world photos as **visual stand-ins** only;
they are not official Star Trek blueprints.

## Offline / air-gapped runs

If download fails, precompute falls back to the synthetic blueprint plate
(grid + vector hull) with no network required.

## Refreshing assets

```bash
python3 scripts/precompute_deck_assets.py
# or one platform:
python3 scripts/precompute_deck_assets.py --platform fletcher_class_destroyer
```

Cached files: `data/platforms/<platform_id>/reference_photo.jpg`
