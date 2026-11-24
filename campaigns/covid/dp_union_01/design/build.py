"""Generate ``campaign.json`` blocks from the DP-UNION-01 design lattice.

One 20-seed ``_canary`` block and one 4-seed ``_rest`` block per lattice
theta. Run from the repo root: ``python3 campaigns/covid/dp_union_01/design/build.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
_DESIGN_REL = "picard_framework/runs/covid_dp_union_01_design.json"
_SPEC = Path(__file__).resolve().parents[1] / "campaign.json"
_CANARY_SEEDS = 20


def theta_label(theta: float) -> str:
    """``316000.0`` -> ``3e5``; ``1e10`` -> ``1e10``."""
    mantissa, exponent = f"{theta:.0e}".split("e")
    return f"{mantissa}e{int(exponent)}"


def build_blocks(design: dict) -> dict:
    seeds = [design["seed_base"] + i for i in range(design["seeds"])]
    arm = design["theta_grid"]["arm_id"]
    blocks = {}
    for theta in design["thetas"]:
        for suffix, chunk in (
            ("canary", seeds[:_CANARY_SEEDS]), ("rest", seeds[_CANARY_SEEDS:]),
        ):
            blocks[f"union_t{theta_label(theta)}_{suffix}"] = {
                "worker": "campaigns/covid/dp_union_01/cell.py",
                "artifact": "cell_{seed}.json",
                "args": {"theta": theta, "arm_id": arm, "design": _DESIGN_REL},
                "seeds": chunk,
            }
    return blocks


def main() -> int:
    design = json.loads((_ROOT / _DESIGN_REL).read_text(encoding="utf-8"))
    spec = json.loads(_SPEC.read_text(encoding="utf-8"))
    spec["blocks"] = build_blocks(design)
    _SPEC.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(f"{len(spec['blocks'])} blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
