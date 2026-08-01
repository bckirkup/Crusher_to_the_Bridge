---
name: adding-new-platform
description: Add a new ship/vessel platform to Crusher-to-the-Bridge. Covers creating spatial layout, air flow paths, and validating referential integrity. Use when adding a new vessel type.
---

# Adding a New Platform

## Prerequisites

- Python 3.11+ with pydantic, numpy, and pyyaml installed
- Working directory: repo root (`Crusher_to_the_Bridge/`)
- Familiarity with the existing platform structure (see `data/platforms/destroyer_baseline/`)

## Devin Secrets Needed

None.

## Steps

### 1. Create the platform directory
```bash
mkdir -p data/platforms/<platform_name>
```
Use snake_case for the directory name (e.g., `arleigh_burke_ddg`, `freedom_class_lcs`).

### 2. Create `spatial_layout.json`

Copy from an existing platform and adapt:
```bash
cp data/platforms/destroyer_baseline/spatial_layout.json data/platforms/<platform_name>/spatial_layout.json
```

Required structure per zone (matches `schemas/spatial_layout.schema.json`):
```json
{
  "graywater_zones": ["Engine_Room"],
  "zones": [
    {
      "id": "unique_zone_name",
      "type": "Free",
      "traffic": "low",
      "volume_m3": 150.0,
      "floor_area_m2": 50.0,
      "ceiling_height_m": 3.0,
      "elevation_m": 0.0,
      "deck": "main",
      "display": {"x": 100, "y": 12}
    }
  ]
}
```

`floor_area_m2`, `ceiling_height_m`, and `elevation_m` are **optional**
CONTAM-geometry fields (all must be > 0 except `elevation_m`, which may be
negative). When both `floor_area_m2` and `ceiling_height_m` are present,
`volume_m3` should equal their product (`50.0 * 3.0 = 150.0` above); the
sanity checker warns if they disagree by more than 1%. Zones may still
specify only `volume_m3` (backward compatible). These fields map onto NIST CONTAM zone geometry — see
`docs/CONTAM_INTEROP.md`. Prefer bringing an authentic ContamW 3.4 `.prj`
and Path B `--simplify` (writes JSON + `path_map.json`). Fiction ships may
bootstrap a temporary Contam bundle:

```
data/platforms/<platform_name>/contam/
  platform.prj      # fiction bootstrap only (JSON→PRJ)
  path_map.json     # ContamX path index (also emitted by --simplify)
```

Regenerate fiction bundles with `scripts/generate_platform_contam_prj.py`
only when there is no authentic Contam model. Prefer `--hobbyist` so openings
use realistic catalog areas (see `docs/CONTAM_PRJ_AUDIT.md`).

After adding Contam assets, validate offline:

```bash
python3 -m pytest tests/test_contam_hobbyist_destroyer.py tests/test_contamw34_dual_path.py -v --tb=short
# If you have a ContamX .SIM for the new platform, also:
python3 tools/contam_flow_compare.py --platform <platform_name> --inject <Zone> --sim path/to/platform.sim
```

With ContamX installed, add a job under `data/config/contam_compare/jobs/` and
run the suite (skill `contamx-interop`). Confirm Flow0 is keyed by embedded
path `nr` — identical ~300 m³/h on distinct fans means the SIM reader regressed.

`graywater_zones` lists downstream greywater/blackwater collection zone(s)
for ship-wide wastewater sequencing (e.g. `Engine_Room_Aft` on large cruise
platforms). Every entry must match a zone `id` in the same file.

Zone `type` values include `Free`, `Dining`, `Room`, **`Cabin_Corridor`**, etc.
**Dining** zones enable food-contamination pathway pools.

For mega-cruise cabin-corridor platforms (`mega_cruise_5000`), corridor zones may
include:

| Field | Purpose |
|-------|---------|
| `cabin_ventilation_type` | `interior_hvac`, `balcony_partial`, or `atrium_view` — affects aerosol dose |
| `cabin_size` | Stateroom occupancy for cabin-mate pairing (default: 2 pax, 3 crew) |

At ship init, `assign_cabin_mates()` groups agents by `home_zone` into staterooms.
See `docs/SHEDDING_AND_CABINMATES.md` and `docs/PLATFORM_CABIN_REVISION.md`.

**Law 3 constraints:**
- `volume_m3` must be > 0
- `display.x` and `display.y` must be present (used by LCARS dashboard tactical deck)
- All `id` values must be unique

### 3. Create `air_flow_paths.json`

Required structure (matches `schemas/air_flow_paths.schema.json`):
```json
{
  "hvac_zones": [
    {
      "id": "zone_main",
      "rooms": ["MedBay", "Galley"],
      "ach": 6.0
    }
  ],
  "cross_zone_links": [
    {
      "from": "zone_main",
      "to": "zone_upper",
      "flow_rate_m3h": 50.0,
      "is_hvac_ducted": false,
      "path": "ladder_well"
    }
  ],
  "adjacency": [
    {
      "from": "Bridge",
      "to": "MedBay",
      "type": "door"
    }
  ]
}
```

**Law 4 referential integrity constraints:**
- Every room in `hvac_zones[].rooms` must reference a valid zone `id` from `spatial_layout.json`
- Every `from` / `to` in `cross_zone_links` must reference a valid `hvac_zones[].id`
- Every `from` / `to` in `adjacency` must reference a valid spatial zone `id`
- `ach` and `flow_rate_m3h` must be >= 0

### 4. Validate with the sanity checker
```bash
python tools/sanity_checker.py --platform-dir data/platforms/<platform_name>
```
Expected: No ERROR findings.

### 5. Validate against JSON schemas
```bash
pip install check-jsonschema
check-jsonschema --schemafile schemas/spatial_layout.schema.json data/platforms/<platform_name>/spatial_layout.json
check-jsonschema --schemafile schemas/air_flow_paths.schema.json data/platforms/<platform_name>/air_flow_paths.json
```

### 6. Run data contract tests
```bash
python3 -m pytest tests/test_data_contracts.py tests/test_cabin_corridor_transmission.py \
  tests/test_shedding_variance_cabin_mates.py -v --tb=short
```

### 7. Test with the orchestrator (optional)

Update `crusher_labs/config.yaml` to point to the new platform paths, then run:
```bash
python orchestrator.py --epochs 10
```

### 8. Architectural graphics + precompute deck assets

Add user-supplied architectural plates (recommended) under the platform:

```
data/platforms/<platform_name>/graphics/
  graphics.json
  elevation.jpg          # side elevation of the whole ship
  plan_overview.jpg      # top-down hull plan
  decks/<deck>_plan.jpg  # optional per-deck plans
```

See `data/platforms/mega_cruise_5000/graphics/graphics.json` for the schema.
The dashboard shows elevation and a single-deck plan side-by-side (no stacking).

Then generate vector overlays:

```bash
python3 scripts/precompute_deck_assets.py --platform <platform_name>
```

This writes `deck_graphics.geojson` (per-deck non-overlapping compartments),
`deck_hull.png`, and `deck_manifest.json`. Optional Wikimedia class photos remain
in `class_photo_catalog.json` (see `CLASS_PHOTO_ATTRIBUTION.md`).

## Available Platforms for Reference

| Platform | Directory |
|----------|-----------|
| Destroyer Baseline | `data/platforms/destroyer_baseline` |
| Enterprise Constitution (TOS) | `data/platforms/enterprise_constitution_tos` |
| Enterprise Galaxy (TNG) | `data/platforms/enterprise_galaxy_tng` |
| Expedition Cruise 300 (legacy) | `data/platforms/expedition_cruise_300` |
| Expedition Cruise 450 | `data/platforms/expedition_cruise_450` |
| Classic Cruise 1900 | `data/platforms/classic_cruise_1900` |
| Spirit Cruise 3000 | `data/platforms/spirit_cruise_3000` |
| Fletcher-class Destroyer | `data/platforms/fletcher_class_destroyer` |
| Legend-class NSC | `data/platforms/legend_class_nsc` |
| Mega Cruise 5000 | `data/platforms/mega_cruise_5000` |
| Messy Cruise 500 (legacy) | `data/platforms/messy_cruise_500` |
| San Antonio-class LPD | `data/platforms/san_antonio_class_lpd` |

Regenerate cabin-corridor cruise layouts with
`python3 scripts/generate_cruise_platform_layout.py --platform <id>`
(see `scripts/cruise_platform_recipes.py`).

## Common Mistakes

- Using `zone_id` instead of `id` — fails schema and sanity checker
- Forgetting `display` coordinates — LCARS tactical deck map will misplace zones
- Referencing zone names in `air_flow_paths.json` that don't exist in `spatial_layout.json` — fails Law 4
- Setting `volume_m3` to 0 — fails Law 3 (must be > 0)
- Duplicate zone `id` values — fails uniqueness check
