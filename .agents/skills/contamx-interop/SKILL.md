---
name: contamx-interop
description: Run and debug ContamX vs native HVAC transport (SIM reader, AHS bridge, compare suite, flow diagnostics). Use when editing contamx_runner, contamx_transport, contamx_ahs_bridge, contam_engine_compare, contam_flow_compare, fiction PRJs, or investigating ContamX concentration divergence.
---

# ContamX Interop (Path A)

## Prerequisites

- Python 3.11+ with repo `requirements.txt`
- Working directory: repo root
- ContamX binary optional (offline tests use fixtures; live compare needs NIST ContamX)

## When to use

- ContamX vs native concentration / attack-rate divergence
- `.SIM` Flow0 looks wrong (identical rates across fans, Bridge “600 m³/h”)
- Editing `engines/contamx_*.py`, `tools/contam_*compare*.py`, or `data/platforms/*/contam/`
- After regenerating fiction PRJs (`scripts/generate_platform_contam_prj.py`)

## Key docs

| Doc | Role |
|-----|------|
| `docs/CONTAM_INTEROP.md` | Path A/B, `.SIM` reader contract, compare + flow_compare |
| `docs/CONTAM_PRJ_AUDIT.md` | Fiction PRJ realism + before/after SIM fix table |
| `third_party/contamx/README.md` | Binary drop + Windows compare bat |

## `.SIM` reader contract (do not regress)

`SimResults.path_volumetric_flow_m3h` **must** key Flow0 by the path-record
embedded `nr` (`nr(i4) dP Flow0 Flow1`). Do **not** key by header xref
`(typ, nr)` — ContamX 3.x xref content is not a reliable slot→path map.

Trailing same-`sim_time` summary frames can have invalid node densities;
`steady_state_frame()` skips those.

**Fingerprint of the old bug:** all kept links share one flow (≈300 m³/h =
0.1 kg/s at ρ=1.2) despite distinct `fan_cvf` design rates.

Regression fixture: `tests/fixtures/contam/destroyer_baseline.sim`.

## Quick offline tests

```bash
python3 -m pytest tests/test_contamx_solver.py tests/test_contamx_ahs_bridge.py \
  tests/test_contam_flow_compare.py tests/test_contam_engine_compare.py -v --tb=short
```

Expect `test_sim_reader_uses_embedded_path_nr_not_xref` to pass (Fan_25/26/27 ≈
16.7 / 13.3 / 10 m³/h on the destroyer fixture).

## Flow diagnostic (with or without ContamX)

```bash
# Topology only
python3 tools/contam_flow_compare.py --platform destroyer_baseline --inject Bridge

# Live ContamX (Windows / CONTAMX_BINARY set)
python3 tools/contam_flow_compare.py --platform destroyer_baseline \
  --inject Bridge --run-contamx \
  --output telemetry_buffer/contam_flow_destroyer.json

# Reuse a .SIM
python3 tools/contam_flow_compare.py --platform destroyer_baseline \
  --sim tests/fixtures/contam/destroyer_baseline.sim --inject Bridge
```

Healthy destroyer read: ~17 kept + ~8 AHS synth; Bridge out ~76 m³/h;
native recirculation on Contam platforms uses `oa_fraction=0.2` /
`hvac_duty=0.5` (Contam-aligned; zone_lower pairs ~350 m³/h);
`zero_flow_real_candidates` = 0. Console prints `kept_links` and flags identical
Flow0 fingerprints in hypotheses.

## Compare suite (results + speed)

```bash
python3 tools/contam_engine_compare.py --suite data/config/contam_compare/suite.json
# Windows: run_contam_compare.bat
```

Transport reports include `path_inventory` and `contamx_injection_isolated`.
Reports land in `telemetry_buffer/contam_compare/` (gitignored).

## Config switch

```yaml
hvac:
  transport_engine: "auto"   # native | contamx | auto
  contamx:
    binary_path: ""
    prj_path: ""             # else data/platforms/<id>/contam/platform.prj
```

## After changing Contam engines / PRJs

1. Offline pytest slice above (always).
2. If SIM layout or Flow0 join changed: confirm destroyer fixture fans still match design.
3. With ContamX installed: re-run `contam_flow_compare --run-contamx` then the compare suite.
4. Update `docs/CONTAM_PRJ_AUDIT.md` if destroyer kept/synth counts or L1 baselines change materially.
5. Zone IDs on Contam fiction platforms must be ≤15 chars (mega `PC_*`/`CC_*`). Prefer editing
   the PRJ as SoT after bootstrap; regenerate with `scripts/generate_platform_contam_prj.py`
   only for fiction ships without an authentic Contam model.
6. Passive cross-zone (`is_hvac_ducted: false`) exports as sized `plr_orfc`; ducted stays `fan_cvf`.
   Per-AHU `oa_fraction` overrides emit dedicated `OAFr_{pct}` schedules on AHS recirc paths.
