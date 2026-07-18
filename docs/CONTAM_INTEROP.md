# CONTAM Interoperability

This document maps Crusher-to-the-Bridge's native JSON contracts onto NIST
**CONTAM** concepts and documents the ContamW 3.4 dual-path workflow:

1. **Path A (ContamX):** run an authentic ContamW 3.4 `.prj` through ContamX
   for the airflow field; Crusher keeps pathogen mass balance.
2. **Path B (native simplify):** simplify a full `.prj` into
   `spatial_layout.json` + `air_flow_paths.json` and use the pure-Python
   prescribed-flow solver.

> **CONTAM** (NIST multizone airflow and contaminant transport) is documented
> in **NIST Technical Note 1887r1**, *CONTAM User Guide and Program
> Documentation Version 3.4*:
> <https://nvlpubs.nist.gov/nistpubs/TechnicalNotes/NIST.TN.1887r1.pdf>

**Non-goals**

- Blueprint / as-built drawings → Contam authoring is a **separate project**.
- Do **not** grow the native solver’s pressure-network physics until a proper
  `.prj` + ContamX vs simplified twin shows that airflow fidelity moves
  epidemic outcomes enough to matter.

## 1. Concept crosswalk

| Crusher-to-the-Bridge (JSON) | CONTAM concept | Notes |
|------------------------------|----------------|-------|
| `zone` (`spatial_layout.json`) | CONTAM **zone** (airflow node) | A well-mixed control volume. |
| `zone.volume_m3` | Zone **volume** | In CONTAM, volume = floor area × ceiling height. |
| `zone.floor_area_m2` | Zone **floor area** | Optional; derived on ContamW export if absent. |
| `zone.ceiling_height_m` | Level / zone **height** | Optional; default 3.0 m on export. |
| `zone.elevation_m` | Relative **level elevation** | Optional; deck-stacked on export if absent. |
| `zone.deck` | CONTAM **level** | Distinct decks become CONTAM levels. |
| `zone.display.{x,y}` | SketchPad **icon** coordinates | Dashboard / layout aid. |
| `air_flow_paths.adjacency` edge | CONTAM **airflow path** (orifice) | Doors / hatches / passageways. |
| `air_flow_paths.hvac_zones` | Simple **air-handling system (AHS)** | Rooms sharing ACH + Ret/Sup phantoms. |
| `hvac_zones.ach` | **Air change rate** | Encoded as balanced OA + recirculation fans. |
| `air_flow_paths.cross_zone_links` | Inter-zone **fan_cvf** path | Prescribed volumetric flow. |
| HVAC `filter_efficiency` (config) | Filter applied in Crusher mass balance | Not a Contam filter element (yet). |
| `natural_decay_rate` (config) | 1st-order sink / **removal** | Settling + viral inactivation per epoch. |

## 2. Dual-path architecture

```
ContamW_3.4.prj
    ├─ Path A ContamX ──► airflow field ──► ContamXTransportEngine
    └─ Path B simplify ──► spatial + air_flow JSON ──► ContamTransportEngine
         └── matched Picard / orchestrator runs ──► outcome comparison
```

Fiction platforms ship a plausible ContamW 3.4 bundle under
`data/platforms/<id>/contam/`:

| File | Role |
|------|------|
| `platform.prj` | ContamW 3.4 project (ContamX-parseable grammar) |
| `path_map.json` | ContamX path index → `(from_zone, to_zone, is_hvac_ducted)` |
| `hobbyist_overrides.json` | Optional fiction-ship Contam portfolio overrides |

Bundled for: `destroyer_baseline` (hobbyist-plus),
`enterprise_constitution_tos` (hobbyist-plus),
`enterprise_galaxy_tng` (hobbyist-plus),
`mega_cruise_5000` (hobbyist-plus). Regenerate after
JSON edits:

```bash
python3 scripts/generate_platform_contam_prj.py --hobbyist
python3 scripts/generate_platform_contam_prj.py --hobbyist --platform destroyer_baseline
```

Shared templates live in [`data/contam_hobbyist/`](../data/contam_hobbyist/).
These PRJs are **fiction-plausible** (derived from our JSON platforms), not
as-built ship models.

### ContamX-critical export invariants

ContamX 3.4 rejects (or buffer-overflows on) PRJs that violate ContamW
grammar. The fiction exporter (`tools/contamw34_prj.py`) enforces:

| Rule | Why |
|------|-----|
| Symbolic names ≤ **15** characters (zones, AHS, levels, elements) | ContamX fatal `Buffer overflow: <truncated name>` |
| Simple-AHS system paths (flags 16/32/64) have `a#=0` and `e#=0` | `ERROR Invalid AHS number, path N` if `a#` is set on OA/recirc/exhaust |
| Supply/return terminals (flag 8) have `a#=<AHS>` and `e#=0`; flow in `Fahs` (kg/s) | Contam AHS design flow, not fan elements |
| AHS record `pr#` / `ps#` / `px#` = recirculation / outdoor-air / exhaust path numbers | Matches ContamW 3.4 `3-Room-OffAt14days.prj` |
| Phantom Ret/Sup zones named `ahsN(Ret)` / `ahsN(Sup)` | Short Contam-style names; path_map keeps full Crusher zone ids |
| Every real zone has a small `plr_orfc` path to **ambient** | ContamX `FATAL Zero on the diagonal` when only fans/AHS (dF/dP=0) connect zones |

## 3. Explicit zone geometry (ceiling height)

`schemas/spatial_layout.schema.json` `Zone` accepts optional
`floor_area_m2`, `ceiling_height_m`, and `elevation_m`. ContamW export
**derives** missing geometry (`ceiling_height_m=3.0`,
`floor_area_m2=volume/3`, deck-stacked elevation) without rewriting platform
JSON.

## 4. `.prj` export / simplify / import

`tools/contam_prj_bridge.py` (+ `tools/contamw34_prj.py`):

### Export (JSON → ContamW 3.4)

```bash
python3 tools/contam_prj_bridge.py --export \
    --platform data/platforms/mega_cruise_5000 \
    --output data/platforms/mega_cruise_5000/contam/platform.prj
```

Writes ContamW **3.4** sections: header/sim params, species (Air+Virus in
hobbyist mode), levels, typed `plr_orfc` / `fan_cvf` flow elements, simple
AHS with Ret/Sup phantoms, zones, flow paths, plus hobbyist wind / filters /
schedules / duct leakage spines / light controls / annotations when
`--hobbyist` is set. Always writes `path_map.json`.

### Simplify (Path B: ContamW 3.4 → JSON)

```bash
python3 tools/contam_prj_bridge.py --simplify \
    --input path/to/full.prj \
    --output data/platforms/imported_from_contam/
```

Maps zones / AHS / fan paths / orifices into platform JSON. Drops (with
warnings): control networks, schedules, wind profiles, kinetic reactions,
source/sinks, ducts, exposures.

### Import (auto-detect)

```bash
python3 tools/contam_prj_bridge.py --import \
    --input some.prj \
    --output data/platforms/imported/
```

Accepts ContamW 3.4 **or** the legacy Crusher `!------` interchange dialect.

```bash
python3 tools/sanity_checker.py --platform-dir data/platforms/imported_from_contam
```

## 5. Path A — ContamX solver (opt-in)

```yaml
hvac:
  transport_engine: "native"   # native | contamx | auto
  contamx:
    binary_path: ""            # ContamX executable (optional)
    prj_path: ""               # optional override
```

**Binary resolution:** `hvac.contamx.binary_path` → `CONTAMX_BINARY` →
`CONTAMX_HOME` → repo **`third_party/contamx/`** → `PATH`.

Drop NIST ContamX into `third_party/contamx/` (gitignored except the README).
See [`third_party/contamx/README.md`](../third_party/contamx/README.md).

**PRJ resolution:** `hvac.contamx.prj_path` →
`data/platforms/<id>/contam/platform.prj` → temp ContamW 3.4 export from JSON.

ContamX computes the airflow field; Crusher applies pathogen mass balance.
ContamX is **not** in CI; paths fall back to native.

### Install ContamX

Download from <https://www.nist.gov/services-resources/software/contam>
and place the executable under `third_party/contamx/` (or set
`CONTAMX_BINARY`).

Smoke (operators with ContamX installed):

```bash
python3 tools/contam_benchmark.py \
    --platform data/platforms/enterprise_galaxy_tng \
    --epochs 12 --inject Bridge:1e6
```

## 6. Comparing outcomes (results + speed)

Job configs live under [`data/config/contam_compare/`](../data/config/contam_compare/):

| Artifact | Role |
|----------|------|
| `suite.json` | Default suite listing all jobs |
| `jobs/*.json` | Per-platform transport and/or full Picard jobs |

| Tool | What it compares |
|------|------------------|
| `tools/contam_engine_compare.py` | **Primary** — results (L1/L∞ or attack-rate deltas) **and** wall-clock timing with repeats |
| `tools/contam_benchmark.py` | Transport concentrations only |
| `tools/contam_outcome_compare.py` | Full Picard outcomes only |
| `run_contam_compare.bat` | Windows one-click runner for the suite |

```bash
# Full suite (native always; ContamX when binary present)
python3 tools/contam_engine_compare.py --suite data/config/contam_compare/suite.json

# Windows
run_contam_compare.bat
```

Reports write to `telemetry_buffer/contam_compare/` (gitignored).

When ContamX is unavailable the suite still runs native-only and records
`contamx_error` per job.

## 7. Related components

- `engines/py_contam_bridge.py` — native prescribed-flow mass-balance engine
- `engines/contamx_runner.py` — ContamX capability detection, subprocess, `.SIM` reader
- `engines/contamx_transport.py` — ContamX airflow field + native mass balance
- `tools/contamw34_prj.py` — ContamW 3.4 writer / simplify
- `tools/contam_prj_bridge.py` — CLI export / simplify / import
- `tools/contam_engine_compare.py` — results + speed suite runner
- `scripts/generate_platform_contam_prj.py` — regenerate fiction-ship bundles
- `third_party/contamx/` — local ContamX drop directory (gitignored binaries)
- `tests/fixtures/contam/` — authentic ContamW 3.4 parse fixtures
- Sibling `py-contam` — `.SIM` layout reference (Law 6, read-only)
