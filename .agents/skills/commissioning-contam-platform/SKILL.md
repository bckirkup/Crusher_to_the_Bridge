---
name: commissioning-contam-platform
description: Commission a new hull's Contam bundle — the hand-authored layer the recipe generators do NOT emit (forced-exhaust declarations, galley pair, make-up louvre, open-deck ambient openings, weather tags, commissioned re-export, audit-pin moves). Use after adding a platform via cruise_platform_recipes or generate_*_layout, when a hull's committed .prj must solve in the commissioned lane, or when forced-exhaust audit tests move.
---

# Commissioning a Contam Platform

The recipe generators (`scripts/cruise_platform_recipes.py`,
`scripts/generate_cruise_platform_layout.py`) emit hull data only. Every
commissioned hull (`diamond_princess`, `mega_cruise_5000`, the four ladder
hulls, `explorer_seas_06`) additionally carries a **hand-authored
commissioning layer** that no generator writes. A new recipe hull without it
bootstraps clean only because supply = return; commissioned it pulls the
sanitary/galley exhaust through cabin leaks at hundreds of kPa.

Reference implementation: `diamond_princess` (first commissioned cruise hull)
and `explorer_seas_06` (most recent; commit `2897df87`). Ledger IDs:
`CONTAM-AMBIENT-WEATHER-CRUISE-01`, `CONTAM-AMBIENT-MAKEUP-CRUISE-01`.

## Prerequisites

- Platform data generated and passing `adding-new-platform` validation.
- ContamX binary (`third_party/contamx/contamx3`) for the field solve.
- `hobbyist_overrides.json` already present (`skip_duct_spines: true`).

## The commissioning layer (six edits)

Apply to `data/platforms/<id>/air_flow_paths.json` and
`spatial_layout.json`. JSON round-trips with `json.dump(obj, indent=2)` —
mutate programmatically to keep diffs clean.

### 1. Declare direction/mechanism/filtered on migration-era links

Every forced/relief link in `cross_zone_links` needs the explicit triple the
pre-S1 alias no longer implies:

| Link class | direction | mechanism | filtered |
|---|---|---|---|
| `*_Trunk_*`, `Cabin_Relief_*`, sanitary/exhaust (ducted) | `oneway` | `prescribed_flow` | `true` |
| `Dining_Galley_Exhaust` (dining→galley transfer) | `oneway` | `prescribed_flow` | `false` |
| `*_Door_Leakage`, `*_Open_Doorway` (passive) | `bidirectional` | `pressure_opening` | `false` |

Add the galley-pair `description` texts verbatim from `diamond_princess`
(VSP/ISO transfer + once-through-sink wording).

### 2. Galley_Hood_Exhaust once-through sink

```json
{"from": "MainGalley", "to": "ambient", "flow_rate_m3h": 18000.0,
 "is_hvac_ducted": true, "path": "Galley_Hood_Exhaust",
 "direction": "oneway", "mechanism": "prescribed_flow", "filtered": false}
```

Insert immediately after `Dining_Galley_Exhaust`; the galley name comes from
the hull's own layout (`MainGalley` on all recipe hulls so far).

### 3. makeup_louvre ambient opening

On the zone `Dining_Galley_Exhaust` draws from (the zone whose air the galley
make-up pulls through — `International` on Diamond, `DaGamaDR` on Explorer):

```json
{"zone": "<source zone>", "type": "makeup_louvre", "area_m2": 2.0,
 "exchange_m3h": 0.0, "schedule": "always_open"}
```

Area is ASSUMED-MAKEUP-LOUVRE-AREA (Grade C): served demand 18000 m³/h ÷
3600 ÷ 2.5 m/s face velocity = 2.0 m². `exchange_m3h` stays 0 — the solved
flow is inward only, so it is not a native sink.

### 4. open_deck ambient openings on exterior zones

One per `exposure: weather` zone:

```json
{"zone": "<id>", "type": "open_deck",
 "area_m2": 2 * sqrt(volume_m3 / 3) * 3,
 "exchange_m3h": <ContamX-solved outward flow>, "wind_speed_m_s": 1.0,
 "schedule": "always_open"}
```

`area_m2` is ASSUMED-OPEN-DECK-FACE-AREA (Grade C): two opposite side faces
of a square-plan deck at the exporter's 3 m zone height. Solve
`exchange_m3h` AFTER the re-export in step 5 — see "Filling exchange_m3h".

### 5. exposure tags

`spatial_layout.json`: add `"exposure": "weather"` to each exterior zone,
keyed after `deck` (Diamond ordering).

### 6. Commissioned re-export

```bash
.venv/bin/python3 scripts/generate_platform_contam_prj.py \
  --platform <id> --hobbyist --ahs-terminal-mode commissioned
```

Writes `contam/platform.prj` + `contam/path_map.json`. One declared relative
wind (1 m/s) is emitted automatically; never set per-path wind
(`CONTAM-DEFAULT-WEATHER-01`).

## Filling exchange_m3h

The `.prj` does not consume `exchange_m3h` (native-lane field only), so fill
it after the export:

```python
from engines.contamx_runner import find_contamx, run_contamx, SimResults
res = SimResults(run_contamx('data/platforms/<id>/contam/platform.prj',
                           find_contamx(), allowed_roots=('.',)))
frame = res.steady_state_frame()
flow0 = res.path_volumetric_flow_m3h(frame)
# per ambient_opening path_map entry: exchange_m3h = sum of positive Flow0
# over the zone's legs (gross outward flow).
```

Values on commissioned hulls run 40k–135k m³/h — open-deck two-way exchange,
not a bug. `makeup_louvre` stays 0.0.

## Validation gates

```bash
.venv/bin/python3 tools/diag/contam_pressure_balance_diagnostic.py \
  --hull <id> --lane commissioned
.venv/bin/python3 tools/contam_commissioned_check.py --platform <id>
```

Pass criteria (Diamond-class): interior max |dP| ~tens of Pa, **zero** paths
above 100 Pa, `balance_residual_m3h` ≈ 0, every commissioned terminal within
5% of declared. If interior dP is kPa-scale, a make-up path is missing or a
link is still undeclared.

## Audit-pin moves (expected, not breakage)

A commissioned hull legitimately moves four pins; update with an attribution
comment naming the platform and the link count it adds:

- `tests/test_forced_exhaust_audit.py` — `len(sanitary)` and
  `sanitary_makeup_links` += the hull's `Sanitary_Makeup` count;
  `len(galley)` += its `Dining_Galley_Exhaust` count (the hood sink is not
  in `GALLEY_PATHS`).
- `tests/test_contam_forced_exhaust_ducted.py` — `len(rows)` += ducted
  `Cabin_Relief_*` count; add `EXPECTED_PLATFORM_COUNTS["<id>"]`.
- `tests/test_contam_s1_migration.py` — add `("<id>", "Dining_Galley_Exhaust")`
  to `POST_S1_GALLEY_LINKS` and `("<id>", "Galley_Hood_Exhaust")` to
  `POST_S1_EXHAUST_SINK_LINKS`; this also puts the hull in
  `POST_S1_AUTHORED_OPERATOR_PLATFORMS`, correctly skipping the
  pre-migration operator pin (there is no pre-migration operator).

Then run the three files plus sanity + schemas + `test_data_contracts.py`.
