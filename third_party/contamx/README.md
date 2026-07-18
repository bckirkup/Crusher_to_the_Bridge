# ContamX / ContamW local install

Drop NIST ContamX (and optional ContamW) binaries **here**. This directory is
gitignored except for this README — Contam is not redistributable via the
repo.

## Layout

```
third_party/contamx/
  README.md              # this file (tracked)
  ContamX3.exe           # Windows ContamX (typical)
  contamx3               # Linux / wine-wrapped name (optional)
  ContamW/               # optional ContamW GUI install tree
  ...                    # any DLLs ContamX needs beside the exe
```

Download Contam from NIST:  
https://www.nist.gov/services-resources/software/contam

## How Crusher finds the binary

Resolution order (`engines/contamx_runner.find_contamx`):

1. `hvac.contamx.binary_path` in `crusher_labs/config.yaml`
2. `CONTAMX_BINARY` environment variable
3. `CONTAMX_HOME` directory (searched for known executable names)
4. **`third_party/contamx/`** under the repo root (this folder)
5. Known names on `PATH` (`contamx`, `contamx3`, `ContamX3.exe`, …)

## Quick start (Windows)

1. Copy `ContamX3.exe` (and its DLLs) into this folder.
2. From the repo root, run:

```bat
run_contam_compare.bat
```

Or set an explicit path:

```bat
set CONTAMX_BINARY=%CD%\third_party\contamx\ContamX3.exe
python tools\contam_engine_compare.py --suite data\config\contam_compare\suite.json
```

Per-path Flow0 diagnostic (after a compare, or standalone):

```bat
python tools\contam_flow_compare.py --platform destroyer_baseline --inject Bridge --run-contamx --output telemetry_buffer\contam_flow_destroyer.json
```

Healthy destroyer read (post SIM `nr` fix): ~17 kept + ~8 AHS synth; Fan_25/26/27
≈ 16.7 / 13.3 / 10 m³/h. If all kept links share ~300 m³/h, the SIM reader is
regressing — see `docs/CONTAM_INTEROP.md` (`.SIM` reader contract) and skill
`contamx-interop`.

Offline regression without ContamX:

```bat
python tools\contam_flow_compare.py --platform destroyer_baseline --inject Bridge --sim tests\fixtures\contam\destroyer_baseline.sim
```

## Quick start (Linux / macOS)

```bash
export CONTAMX_BINARY=/path/to/contamx3
# or place a runnable binary under third_party/contamx/
python3 tools/contam_engine_compare.py --suite data/config/contam_compare/suite.json
```

Platform ContamW 3.4 projects live under `data/platforms/<id>/contam/` and
**are** tracked in git (fiction-ship PRJs for dual-path runs). Runtime `.sim`
sidecars under platforms are gitignored; the destroyer Flow0 fixture lives at
`tests/fixtures/contam/destroyer_baseline.sim`.
