#!/usr/bin/env python3
"""PRESENT-SHARE-01 flu rescore driver (scratch): conditioned flu cells under
once_per_course vs daily_hazard presentation draws, rhythm=on, classic hull.

Not a committed probe — local A/B harness for the session's direction read.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.flu_rhythm_ab_probe import flu_cell_spec, run_cell  # noqa: E402

PLATFORM = "classic_cruise_1900"
EPOCHS = 288
SEEDS = [8105, 8106, 8107, 8108]
MODES = ["once_per_course", "daily_hazard"]
OUT = REPO_ROOT / "telemetry_buffer" / "flu_present_ab"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for mode in MODES:
        for seed in SEEDS:
            t0 = time.perf_counter()
            spec = flu_cell_spec(
                seed=seed, platform=PLATFORM, epochs=EPOCHS,
                confinement="declared",
            )
            spec["pathogen_overrides"]["influenza_a"][
                "presentation_draw_mode"
            ] = mode
            spec["description"] = f"flu_present_ab_{PLATFORM}_s{seed}_{mode}"
            summary = run_cell(
                seed=seed, platform=PLATFORM, epochs=EPOCHS, arm="on",
                spec_dict=spec,
            )
            path = OUT / f"{PLATFORM}_s{seed}_{mode}.json"
            path.write_text(json.dumps(summary))
            confined = (summary.get("rhythm") or {}).get("confined") or {}
            print(
                f"done {mode} s{seed} in {time.perf_counter()-t0:.0f}s "
                f"confined={confined.get('confined_secondaries')}/"
                f"{confined.get('confined_slots')}",
                flush=True,
            )


if __name__ == "__main__":
    main()
