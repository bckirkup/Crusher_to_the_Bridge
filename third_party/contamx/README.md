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

## Quick start (Linux / macOS)

```bash
export CONTAMX_BINARY=/path/to/contamx3
# or place a runnable binary under third_party/contamx/
python3 tools/contam_engine_compare.py --suite data/config/contam_compare/suite.json
```

Platform ContamW 3.4 projects live under `data/platforms/<id>/contam/` and
**are** tracked in git (fiction-ship PRJs for dual-path runs).
