"""Run one post-confinement-fix pilot specification."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from picard_framework.runs.mega_cruise_campaign import campaign_runner  # noqa: E402


def run(spec_path: Path, output_dir: Path) -> int:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    run_id = str(spec["description"])
    ok = campaign_runner.run_simulation(
        run_id,
        spec,
        output_root=output_dir,
        accumulation_suffix="postfix",
    )
    sidecar = output_dir / f"{run_id}.pilot.json"
    sidecar.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "spec": str(spec_path),
                "ok": bool(ok),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run(Path(sys.argv[1]), Path(sys.argv[2])))
