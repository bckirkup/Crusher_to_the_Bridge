#!/usr/bin/env python3
"""DP-UNION-02 readout shim over the shared DP union readout."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SOURCE = Path(__file__).resolve().parents[1] / "dp_union_01" / "readout.py"
_DESIGN = "picard_framework/runs/covid_dp_union_02_design.json"

spec = importlib.util.spec_from_file_location("dp_union_readout", _SOURCE)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {_SOURCE}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if "--design" not in sys.argv:
    sys.argv.extend(["--design", _DESIGN])
raise SystemExit(module.main())
