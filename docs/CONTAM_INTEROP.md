# CONTAM Interoperability

This document maps Crusher-to-the-Bridge's native JSON contracts onto NIST
**CONTAM** concepts and documents the `.prj` import/export workflow, so that
operators familiar with CONTAM / ContamW can read, visualize, and round-trip
shipboard models.

> **CONTAM** (NIST multizone airflow and contaminant transport) is documented
> in **NIST Technical Note 1887r1**, *CONTAM User Guide and Program
> Documentation Version 3.4*:
> <https://nvlpubs.nist.gov/nistpubs/TechnicalNotes/NIST.TN.1887r1.pdf>

The project's transport physics is a native-Python re-implementation of
CONTAM's multizone mass-balance equations (`engines/py_contam_bridge.py`).
Historically the geometry and airflow network were described only by this
project's own JSON contracts. The additions documented here make those
contracts *legible and interoperable* with CONTAM tooling.

## 1. Concept crosswalk

| Crusher-to-the-Bridge (JSON) | CONTAM concept | Notes |
|------------------------------|----------------|-------|
| `zone` (`spatial_layout.json`) | CONTAM **zone** (airflow node) | A well-mixed control volume. |
| `zone.volume_m3` | Zone **volume** | In CONTAM, volume = floor area × ceiling height. |
| `zone.floor_area_m2` | Zone **floor area** | New optional field (see §2). |
| `zone.ceiling_height_m` | Level / zone **height** | New optional field (see §2). |
| `zone.elevation_m` | Relative **level elevation** | New optional field; may be negative. |
| `zone.deck` | CONTAM **level** | Distinct decks become CONTAM levels. |
| `zone.display.{x,y}` | SketchPad **icon** coordinates | Used to lay zones out on the CONTAM floor plan. |
| `air_flow_paths.adjacency` edge | CONTAM **airflow path** (opening) | Doors / hatches / passageways between two zones. |
| `adjacency.type` | Opening / **flow element** class | `passageway`, `service_hatch`, `ladder_well`, `sealed_door`. |
| `air_flow_paths.hvac_zones` | Simple **air-handling system (AHS)** | A group of rooms sharing recirculated supply air. |
| `hvac_zones.ach` | **Air change rate** | Air changes per hour for the AHS group. |
| `air_flow_paths.cross_zone_links` | Inter-AHS **ducted / passive link** | Ventilation shafts, ladder wells between systems. |
| `cross_zone_links.flow_rate_m3h` | Path **design flow** (m³/h) | Volumetric flow along the link. |
| `cross_zone_links.is_hvac_ducted` | Ducted vs. passive path | Ducted paths are subject to filtration. |
| HVAC `filter_efficiency` (config) | CONTAM **filter** element | η ∈ [0,1] applied to ducted paths (MERV/HEPA). |
| `natural_decay_rate` (config) | 1st-order sink / **removal** | Settling + viral inactivation per epoch. |

## 2. Explicit zone geometry (ceiling height)

`schemas/spatial_layout.schema.json` `Zone` now accepts three **optional**
fields (JSON Schema draft 2020-12):

| Field | Type | Constraint | Meaning |
|-------|------|-----------|---------|
| `floor_area_m2` | number | `exclusiveMinimum: 0` (Law 3) | CONTAM zone floor area. |
| `ceiling_height_m` | number | `exclusiveMinimum: 0` (Law 3) | CONTAM ceiling height. |
| `elevation_m` | number | (may be negative) | Relative floor elevation. |

`volume_m3` remains **required** for backward compatibility. Resolution rules
(implemented in `engines.py_contam_bridge.derive_volume_m3`):

1. If `volume_m3` is present, it is used directly.
2. Otherwise, if both `floor_area_m2` and `ceiling_height_m` are present,
   volume is derived as `floor_area_m2 * ceiling_height_m`.
3. Otherwise a default (100 m³) is used.

When `volume_m3`, `floor_area_m2`, and `ceiling_height_m` are all present, the
sanity checker (`tools/sanity_checker.py`) emits a `GEOMETRY` **warning** if
`volume_m3` disagrees with `floor_area_m2 * ceiling_height_m` by more than 1%.

Example zone with explicit geometry:

```json
{
  "id": "Mess_Hall",
  "type": "Dining",
  "traffic": "high",
  "volume_m3": 120.0,
  "floor_area_m2": 40.0,
  "ceiling_height_m": 3.0,
  "elevation_m": 0.0,
  "deck": "main",
  "display": {"x": 55, "y": 8}
}
```

## 3. `.prj` import / export workflow

`tools/contam_prj_bridge.py` translates between the two platform JSON files
and a CONTAM `.prj` project file. It mirrors the CLI conventions of
`tools/gis_spatial_bridge.py` (`--input`, `--output`, `--platform`).

### Export (JSON → `.prj`)

```bash
python tools/contam_prj_bridge.py --export \
    --platform data/platforms/destroyer_baseline \
    --output telemetry_buffer/contam/destroyer_baseline.prj
```

The exporter reads `spatial_layout.json` + `air_flow_paths.json` and writes a
`ContamW`-signed `.prj` with these sections:

- **levels** — one CONTAM level per distinct `deck` (reference elevation and
  height derived from zone `elevation_m` / `ceiling_height_m`).
- **zones** — every zone with volume, floor area, ceiling height, elevation,
  temperature, SketchPad coordinates, type, and traffic.
- **flow paths** — one CONTAM airflow path per `adjacency` opening.
- **air-handling systems** — one AHS per `hvac_zones` entry (member rooms +
  ACH).
- **inter-system links** — one link per `cross_zone_links` entry (flow rate,
  ducted flag, path name).

### Import (`.prj` → JSON)

```bash
python tools/contam_prj_bridge.py --import \
    --input telemetry_buffer/contam/destroyer_baseline.prj \
    --output data/platforms/imported_from_contam/
```

The importer parses the same sections and emits `spatial_layout.json` +
`air_flow_paths.json`, exactly as `tools/gis_spatial_bridge.py` emits those two
files from GIS input.

### Referential integrity (Law 4)

The importer reconstructs `hvac_zones`, `cross_zone_links`, and `adjacency`
from the corresponding `.prj` sections. As with GIS import, run the sanity
checker afterwards to confirm every room in `hvac_zones` and every
`from`/`to` endpoint resolves to a zone id:

```bash
python tools/sanity_checker.py --platform-dir data/platforms/imported_from_contam
```

### Round-trip fidelity

The JSON → `.prj` → JSON round-trip preserves zone identity, geometry
(volume, and area/height/elevation when present), and the full airflow graph
(`adjacency`, `hvac_zones`, `cross_zone_links`). This is guarded by
`tests/test_contam_prj_bridge.py`.

> **Note on ContamW compatibility.** The exporter writes the documented
> CONTAM 3.x project-file structure (a `ContamW` signature line followed by
> `!`-delimited sections closed with `-999` sentinels). Because ContamW /
> ContamX is a Windows GUI/CLI that is not available in the offline build
> environment, exact byte-level ContamW openability is *best-effort* and not
> automatically verified. If ContamW reports issues opening an exported file,
> re-saving from within ContamW normalizes the project.

## 5. Real ContamX solver (opt-in parallel engine)

By default, transport is solved by the pure-Python `ContamTransportEngine`
(offline, deterministic, CI-validated). You can optionally swap in the **real
NIST ContamX solver** to compute the inter-zone airflow field, with Crusher's
own contaminant mass balance applied on top of it:

```
ContamX  →  per-path volumetric airflows (the "airflow field")
Crusher  →  discrete-time pathogen mass balance on those flows
```

Because the contaminant math is identical to the native engine, the two are
directly comparable (see the benchmark below).

### Selecting the engine

In `config.yaml` under `hvac:`:

```yaml
hvac:
  transport_engine: "native"   # native | contamx | auto
  contamx:
    binary_path: ""            # path to the ContamX executable
```

- `native` (default) — pure-Python engine; no external dependency.
- `contamx` — require ContamX; if the binary/project/OS is unavailable, it
  logs a warning and falls back to native.
- `auto` — use ContamX when available, otherwise silently fall back.

The binary is located via `hvac.contamx.binary_path`, then the
`CONTAMX_BINARY` environment variable, then known executable names on `PATH`.

### Installing ContamX

ContamX is a **NIST executable and is not pip-installable**. Download it from
the CONTAM software page (<https://www.nist.gov/services-resources/software/contam>)
and either add it to `PATH` or point `hvac.contamx.binary_path` /
`CONTAMX_BINARY` at it. It is **not** present in CI or the offline build
environment, so ContamX-dependent code paths fall back to native and
integration tests skip cleanly there.

### Benchmark: native vs ContamX

`tools/contam_benchmark.py` runs a platform through both engines with an
identical pathogen injection and reports per-epoch L1 / L∞ concentration
divergence (and prints the native trajectory only when ContamX is
unavailable):

```bash
python tools/contam_benchmark.py \
    --platform data/platforms/destroyer_baseline \
    --epochs 12 --inject Bridge:1e6
```

> **Current limitation.** Running ContamX end-to-end needs a `.prj` that
> ContamX can parse. The exporter (§3) currently writes a *CONTAM-style
> interchange* file, not a byte-faithful, ContamX-validated project.
> Producing a fully ContamX-parseable `.prj` is tracked as follow-on work.
> The solver seam here (capability detection, subprocess runner, `.SIM`
> reader, engine selection, fallback) is complete and unit-tested with
> crafted `.SIM` fixtures; it "lights up" once a valid project and the
> binary are present.

## 6. Related components

- `engines/py_contam_bridge.py` — native-Python CONTAM mass-balance transport
  engine (`ContamZoneNode`, `ContamTransportEngine`).
- `engines/contamx_runner.py` — ContamX capability detection, subprocess
  runner, and native binary `.SIM` results reader.
- `engines/contamx_transport.py` — `ContamXTransportEngine` (ContamX airflow
  field + native mass balance).
- `tools/contam_benchmark.py` — native vs ContamX divergence report.
- `tools/gis_spatial_bridge.py` — GIS (Shapefile/GeoJSON) → platform JSON.
- `docs/OPERATORS_MANUAL.md` §4.2 (spatial layout) and §11.3 (py-contam).
- Sibling `py-contam` repository — CONTAM binary `.sim` results reader and
  weather/species file writers (read-only, Law 6); its `.SIM` byte layout is
  the reference for `engines/contamx_runner.SimResults`.
