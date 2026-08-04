# CONTAM Interoperability

> **Status:** Living. Index: [README.md](README.md).

Crusher treats a ContamW **3.4 `.prj` as the high-fidelity airflow source of
truth**. The native Python engine is the *fast, lower-fidelity* twin.

1. **Path A (ContamX):** run the `.prj` through ContamX → airflow field →
   Crusher pathogen mass balance (`ContamXTransportEngine` + AHS bridge).
2. **Path B (simplify):** dumb the `.prj` down to
   `spatial_layout.json` + `air_flow_paths.json` + `path_map.json` →
   native prescribed-flow solver.

**Fiction bootstrap (reverse, temporary):** for Mega Cruise / Enterprise /
destroyer demos that have *no* authentic Contam model, JSON→PRJ export can
synthesize a plausible `.prj`. That is **not** the normal Contam authoring
path — prefer bringing a real ContamW project and simplifying it.

> **CONTAM** (NIST multizone airflow and contaminant transport) is documented
> in **NIST Technical Note 1887r1**, *CONTAM User Guide and Program
> Documentation Version 3.4*:
> <https://nvlpubs.nist.gov/nistpubs/TechnicalNotes/NIST.TN.1887r1.pdf>

**Non-goals**

- Blueprint / as-built **duct and leakage** digitization from drawings remains
  engineer ContamW handwork (Target C).
- **Target B** naval GA → ContamW *starter* PRJ (zones, openings, AHS, path_map)
  is supported via `python3 -m tools.ship_blueprint_import author_contam` — see
  [SHIP_BLUEPRINT_IMPORT.md](SHIP_BLUEPRINT_IMPORT.md). That starter is meant to
  run ContamX Path A and be refined in ContamW; it is not an as-built HVAC model.
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
| `hvac_zones.ach` | **Air change rate** | Recovered from AHS `Fahs` on simplify when possible. |
| `air_flow_paths.cross_zone_links` | Inter-zone **fan_cvf** path | Prescribed volumetric flow. |
| HVAC `filter_efficiency` (config) | Filter applied in Crusher mass balance | Not a Contam filter element (yet). |
| `natural_decay_rate` (config) | 1st-order sink / **removal** | Settling + viral inactivation per epoch. |
| `path_map.json` | ContamX path index alignment | **Derived from the `.prj`** (`path_map_from_prj`). |

## 2. Dual-path architecture (PRJ primary)

```
ContamW_3.4.prj   ←── primary high-fidelity input
    ├─ Path A ContamX ──► airflow field ──► AHS bridge ──► Crusher mass balance
    └─ Path B simplify ──► spatial + air_flow + path_map JSON ──► native engine
         └── matched Picard / orchestrator runs ──► outcome comparison

Fiction JSON platforms (no Contam model yet)
    └─ bootstrap only ──► synthesize contam/platform.prj + path_map.json
```

### Path B — simplify (preferred for native)

```bash
python3 tools/contam_prj_bridge.py --simplify \
    --input path/to/full.prj \
    --output data/platforms/imported_from_contam/
```

Writes `spatial_layout.json`, `air_flow_paths.json`, and **`path_map.json`**
(ContamX index order from the PRJ itself). Controls / schedules / wind /
ducts / sources are dropped (with warnings).

### Path A — ContamX on a real `.prj`

Set `hvac.transport_engine: contamx` (or `auto`) and point
`hvac.contamx.prj_path` at the project (or place it at
`data/platforms/<id>/contam/platform.prj`). Path map resolution:

1. Sidecar `path_map.json` beside the PRJ (from `--simplify` or fiction bootstrap)
2. Else **`path_map_from_prj`** parses the PRJ (never rebuilds fiction export order)

### Fiction bootstrap only (JSON → PRJ)

Bundled under `data/platforms/<id>/contam/` for destroyer / Mega / Enterprises
so ContamX demos work without an authentic Contam model. Default regen uses
**hobbyist-plus** templates from [`data/contam_hobbyist/`](../data/contam_hobbyist/)
(+ optional `contam/hobbyist_overrides.json`): typed orifices with
**physically sized** doors/hatches/shafts and open–closed week schedules,
wind, filters, OA/HVAC schedules, duct leakage spines, annotations,
Air+Virus species.

```bash
python3 scripts/generate_platform_contam_prj.py --hobbyist
python3 scripts/generate_platform_contam_prj.py --hobbyist --platform destroyer_baseline
```

These PRJs are **fiction-plausible**, not as-built ship models.

### ContamX-critical fiction-export invariants

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
| Week schedule `OAFracW` (`fo=0.2`) on AHS recirc paths | Without it Contam defaults to 100% OA → no HVAC recirculation |
| Cross-zone `fan_cvf` expanded to all room×room pairs | Matches native cross-zone expansion; ContamX flows are Crusher-visible |
| `path_map.ahs_nr` on AHS paths + ContamX AHS bridge | Synthesizes star HVAC (room↔plenum) from Contam Ret/Sup/recirc SIM flows |
| Initial zone/junction concentration headers = `n_items × n_ctm` | ContamX `Zones*contaminant count mis-match` if only `n_items` |
| Duct terminals: emit `vf_node_name` even when `vf_type=0`; **omit** ContamW `"T:"` | ContamX always reads the name string; `"T:"` → `Bad integer: T:`; omitting name shifts Ad onto `bal` → `Bad short integer: <Ad>` |

> **Docs gap:** NIST TN 1887r1 Appendix A still documents ContamW 2.3 `"T:"` before
> terminal fields. ContamX 3.4.0.3 rejects that marker and always consumes
> `vf_node_name` on junctions. Fiction export follows ContamX behavior verified
> by the Windows compare suite, not the appendix text alone.

### ContamX → Crusher airflow bridge

Contam simple-AHS keeps Ret/Sup **phantoms**. ContamX solves those paths;
Crusher mass balance only accepts **real zone ↔ real zone**. The bridge
(`engines/contamx_ahs_bridge.py`) collapses each AHS group:

```
Q_ij = R_i · (Rec / ΣR) · (S_j / ΣS)   (i ≠ j)
```

so ContamX remains the detailed airflow model and Crusher stays the simple
pathogen mass-balance consumer (with HVAC filter η on synthesized ducted
edges). Envelope leaks and AHS OA/exhaust stay Contam-only.

## 3. Explicit zone geometry (ceiling height)

`schemas/spatial_layout.schema.json` `Zone` accepts optional
`floor_area_m2`, `ceiling_height_m`, and `elevation_m`. ContamW export
**derives** missing geometry (`ceiling_height_m=3.0`,
`floor_area_m2=volume/3`, deck-stacked elevation) without rewriting platform
JSON.

## 4. `.prj` simplify / import / fiction bootstrap

`tools/contam_prj_bridge.py` (+ `tools/contamw34_prj.py`):

### Simplify (Path B: ContamW 3.4 → JSON + path_map) — primary

```bash
python3 tools/contam_prj_bridge.py --simplify \
    --input path/to/full.prj \
    --output data/platforms/imported_from_contam/
```

Maps zones / AHS / fan paths / orifices into platform JSON and emits
`path_map.json` via `path_map_from_prj` (ContamX index order from the PRJ).
Drops (with warnings): control networks, schedules, wind profiles, kinetic
reactions, source/sinks, ducts, exposures. Recovers `hvac_zones.ach` from
AHS supply `Fahs` when the AHS description lacks `ach=`.

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

### Fiction bootstrap (JSON → ContamW 3.4) — temporary only

```bash
python3 tools/contam_prj_bridge.py --export \
    --platform data/platforms/mega_cruise_5000 \
    --output data/platforms/mega_cruise_5000/contam/platform.prj
```

Synthesizes ContamW **3.4** for fiction ships without an authentic Contam
model. Prefer Path B on a real `.prj` whenever one exists.

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
`data/platforms/<id>/contam/platform.prj` → fiction-bootstrap temp export
from JSON (last resort). Path map: sidecar beside PRJ, else
`path_map_from_prj` on the PRJ text.

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

Transport reports include `path_inventory` (path-type histogram, injection
out-degree, capped edge sample) for both engines so a ContamX `n_paths`
collapse is diagnosable without a separate flow dump. When ContamX leaves an
injection zone with zero Crusher out-edges, the job also sets
`contamx_injection_isolated: true`.

When ContamX is unavailable the suite still runs native-only and records
`contamx_error` per job.

### `.SIM` reader contract (critical)

`engines/contamx_runner.SimResults` decodes ContamX binary results:

| Record | Layout | Notes |
|--------|--------|-------|
| Path | `nr(i4) dP(f4) Flow0(f4) Flow1(f4)` | **Key flows by embedded `nr`**, not the header xref table |
| Node | `nr(i4) T(f4) P(f4) D(f4)` | Density from `D`; skip trailing summary frames with `D≈0` |
| Header xref | `(typ, nr) × nafpt` byte span | Occupies space before frames; ContamX 3.x content is **not** a reliable slot→path_nr map |

**Bug fingerprint (fixed 2026-07-18):** keying Flow0 by xref assigned AHS terminal
mass (~0.1 kg/s ≈ 300 m³/h at ρ=1.2) onto distinct fan path numbers — all
“kept” links identical. Regression fixture:
`tests/fixtures/contam/destroyer_baseline.sim` (expects Fan_25/26/27 ≈
16.7 / 13.3 / 10 m³/h).

`steady_state_frame()` returns the last frame with positive node densities
(not a trailing same-`sim_time` summary row).

### Per-path flow diagnostic

When concentrations diverge but ContamX loads, dump native ACH links vs
ContamX SIM flows (joined on embedded path ``nr``) and AHS-synthesized edges:

```bash
# Offline topology (no ContamX) — shows Bridge isolation risk without SIM
python3 tools/contam_flow_compare.py --platform destroyer_baseline --inject Bridge

# Windows / ContamX installed — join live SIM Flow0 onto path_map
python3 tools/contam_flow_compare.py --platform destroyer_baseline \
    --inject Bridge --run-contamx \
    --output telemetry_buffer/contam_flow_destroyer.json

# Or reuse a .SIM from a prior ContamX run (repo-relative path)
python3 tools/contam_flow_compare.py --platform destroyer_baseline \
    --sim tests/fixtures/contam/destroyer_baseline.sim \
    --inject Bridge
```

**How to read the report**

| Signal | Meaning |
|--------|---------|
| `native.n_paths` ≫ `contamx.n_crusher_paths` | ContamX dropped zero-SIM real↔real edges and/or AHS synth failed |
| `zero_flow_real_candidates` | Adjacency orifices / cross-zone fans solved ≈0 in ContamX (ΔP≈0) |
| `connectivity_gap[].bridge_isolated` | Injection zone has native out-edges but zero ContamX Crusher out-edges |
| `kept_links` all share one `flow_m3h` | **SIM join/reader bug** (see `.SIM` reader contract) — not Contam physics |
| destroyer after healthy read | ~17 kept + ~8 AHS synth; Fan_25/26/27 match design m³/h |

Native builds a **Contam-aligned prescribed ACH digraph** from JSON:
Star topology through a virtual AHU plenum (not an N×N room digraph)::

`room → plenum` at `ACH·V·duty`; `plenum → room` at that flow × `(1−oa)` (filtered).

Native contaminant transport uses the analytical well-mixed ODE
`M(t+Δt)=M e^{-kΔt}+(S/k)(1−e^{-kΔt})` (unconditionally stable at 1-hour epochs).

Fiction Contam platforms set `oa_fraction: 0.2` and `hvac_duty: 0.5` so the native twin matches
hobbyist ContamX steady frames (night half-duty). ContamX builds a
**pressure/AHS/fan field**, then Crusher keeps only non-zero real↔real SIM
paths plus AHS room↔room synthesis (`Rec≈0` → `(1−oa)·min(ΣR,ΣS)`). Calibrate
**native toward ContamX**, not the reverse — Contam/PRJ is airflow SoT.

## 7. Related components

- `engines/py_contam_bridge.py` — native prescribed-flow mass-balance engine
- `engines/contamx_runner.py` — ContamX capability detection, subprocess, `.SIM` reader
- `engines/contamx_transport.py` — ContamX airflow field + AHS→room bridge + native mass balance
- `engines/contamx_ahs_bridge.py` — synthesize star HVAC (room↔plenum) from Contam AHS SIM flows
- `tools/contamw34_prj.py` — ContamW 3.4 writer / simplify
- `tools/contam_prj_bridge.py` — CLI export / simplify / import
- `tools/contam_engine_compare.py` — results + speed suite runner
- `tools/contam_flow_compare.py` — native ACH vs ContamX SIM per-path diagnostic
- `docs/CONTAM_PRJ_AUDIT.md` — fiction PRJ physical realism audit
- `scripts/generate_platform_contam_prj.py` — regenerate fiction-ship bundles
- `third_party/contamx/` — local ContamX drop directory (gitignored binaries)
- `tests/fixtures/contam/` — ContamW 3.4 parse fixtures **and** `destroyer_baseline.sim` Flow0 regression
- Sibling `py-contam` — `.SIM` layout reference (Law 6, read-only)
