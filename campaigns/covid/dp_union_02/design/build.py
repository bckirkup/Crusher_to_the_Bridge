"""Generate ``campaign.json`` blocks from the DP-UNION-02 design lattice.

One 20-seed ``_canary`` block and one 4-seed ``_rest`` block per lattice
theta, over the frozen ascertainment-conditioned seed cohort. Run from the
repo root: ``python3 campaigns/covid/dp_union_02/design/build.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
_DESIGN_REL = "picard_framework/runs/covid_dp_union_02_design.json"
_SPEC = Path(__file__).resolve().parents[1] / "campaign.json"
_CANARY_SEEDS = 20


def theta_label(theta: float) -> str:
    """``316000.0`` -> ``3e5``; ``1e10`` -> ``1e10``."""
    mantissa, exponent = f"{theta:.0e}".split("e")
    return f"{mantissa}e{int(exponent)}"


def design_seeds(design: dict) -> list[int]:
    """The frozen seed sequence: explicit when ascertainment-conditioned."""
    if design.get("seed_values") is not None:
        return [int(seed) for seed in design["seed_values"]]
    return [design["seed_base"] + i for i in range(design["seeds"])]


def build_blocks(design: dict) -> dict:
    seeds = design_seeds(design)
    if len(seeds) != int(design["seeds"]):
        raise ValueError("design seed_values length must equal seeds")
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
