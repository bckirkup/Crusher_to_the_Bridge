# tools/ — diagnostic and campaign drivers

> **Status:** Living index. Loose one-off drivers (`tools/*.py`), shared
> machinery (`tools/diag/`), and the per-pathogen readout dirs. Naming follows
> the arm-naming crosswalk in `docs/README.md`: `covid_*` / `flu_*` /
> `noro_diag/` per arm. This file does not enumerate every file — it names the
> conventions and the load-bearing entry points; check the directory before
> adding a file that forks an existing helper.

## Shared machinery — use before writing a new probe

| Path | Role |
|------|------|
| `diag/` | Readout machinery every tier-walker shares — `readout_common` (Wilson/quantiles/rate tables, zip IO), `instrument_common`, `manifest_args`, `json_io`, `conditioned_cell` (EDISON/ACTIVE bundles, `DECLARED_CONFINEMENT`, `conditioned_spec`: isolated arm + explicit seed + replay-calendar SOP-017) |
| `sanity_checker.py` | The config validation gate (`--from-config` in CI) |
| `cabin_floor_probe.py` | The conditioned confined-window probe surface (`run_arm`/`instrumented_voyage` monkeypatch seam; argv[0]-pinned in `submit_cabin_floor.sh`) |

## Families

| Prefix | Arm / surface | Notes |
|--------|---------------|-------|
| `covid_*` | SARS-CoV-2 | ~44 drivers, probes and readouts across the DP-replay and theta-screen lines |
| `flu_*` | influenza-A | `flu_anchors.py` is the arm's anchor loader (`data/observation/flu_fit_targets.json`); the rest are conditioned-cell drivers + readouts |
| `noro_diag/` | norovirus | 40+ tools for the fleet-level line; several are argv[0]-pinned by registered jobdefs |
| `smalln_diag/` | small-n conditioning | `confined_challenge_trace` and variants |
| `contam*`, `contamw*` | ContamX interop | flow diagnostics, SIM readers, compare suites |
| `git`/`config`/`campaign`/`fit`/`gis` singles | misc | read the file docstring before generalizing |

## Conventions

- Probe drivers run single voyages and emit `telemetry_buffer/<probe>/`;
  readouts walk run archives and print Wilson-bounded tables.
- Files named in a registered jobdef's argv[0] cannot move until that
  campaign's array work drains (`deploy/aws/README.md` boundary note).
- A file under `telemetry_buffer/` is a **run output record**, not a
  tool — probes live here (`tools/`).
- Any new arm's tools follow the same prefix grammar; see the arm-naming
  crosswalk in `docs/README.md`.
