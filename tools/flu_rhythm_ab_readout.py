#!/usr/bin/env python3
"""FLU-RHYTHM-01 readout — folds ``<arm>/<tier>/*.zip`` cells per class.

Per (class, arm): pooled confined cabinmate attack fraction vs the
dose-derived expected-SAR floor band (``docs/confined_attack_floor_spec.md``
— the band bounds E[1−exp(−k·D_slot)] over the cell's own pooled slot
doses at the declared k sourced interval; the withdrawn 15–25% fixed band
is filed in CABIN-FLOOR-03), delivered confined dose (stage-probe slot
rows + engine-drawn implied SAR), per-epoch dosed-set size and challenged
share (covid-probe fields), corridor-front correlation at event-egress
epochs, and the wiring witnesses (rhythm attached, dealt commitments,
ashore dosing). Per-seed paired deltas join on the run stem ``s<seed>``.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.diag.readout_common import wilson_interval  # noqa: E402
from tools.flu_anchors import (  # noqa: E402
    K_DECLARED,
    K_SOURCED_INTERVAL,
)
from tools.noro_diag.rhythm_ab_readout import (  # noqa: E402
    _clock_correlation,
    load_cells,
)

_ARMS = ("off", "on")
_wilson = wilson_interval


def _expected_sar(doses: list[float], k: float) -> float:
    return sum(1.0 - math.exp(-k * d) for d in doses) / len(doses)


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"n": 0, "p50": None, "p90": None}
    ordered = sorted(values)
    p90 = ordered[min(len(ordered) - 1, int(0.9 * (len(ordered) - 1)))]
    return {
        "n": len(ordered),
        "p50": statistics.median(ordered),
        "p90": p90,
    }


def _accumulate_confined(
    confined: dict[str, Any],
    acc: dict[str, Any],
) -> None:
    acc["slots"] += int(confined.get("confined_slots") or 0)
    acc["secondaries"] += int(confined.get("confined_secondaries") or 0)
    stage_totals = confined.get("stage_totals") or {}
    acc["emitted"] += float(stage_totals.get("emitted_member_copies", 0.0))
    acc["delivered_copies"] += float(
        confined.get("delivered_dose_copies") or 0.0,
    )
    for field, value in stage_totals.items():
        acc["stage_totals"][field] = (
            acc["stage_totals"].get(field, 0.0) + float(value)
        )
    for row in confined.get("slot_rows") or []:
        acc["delivered"].append(float(row.get("delivered_p_dose") or 0.0))
    for row in confined.get("slot_dose_rows") or []:
        acc["implied_sar"].append(float(row.get("implied_sar") or 0.0))


def _confined_block(runs: list[tuple[Path, dict, dict]]) -> dict[str, Any]:
    acc: dict[str, Any] = {
        "slots": 0, "secondaries": 0, "emitted": 0.0,
        "delivered_copies": 0.0, "delivered": [], "implied_sar": [],
        "stage_totals": {},
    }
    for _, _, r in runs:
        _accumulate_confined(r.get("confined") or {}, acc)
    slots = acc["slots"]
    secondaries = acc["secondaries"]
    emitted = acc["emitted"]
    delivered_copies = acc["delivered_copies"]
    delivered = acc["delivered"]
    implied_sar = acc["implied_sar"]
    stage_totals = acc["stage_totals"]
    lo, hi = _wilson(secondaries, slots)
    band = (
        [_expected_sar(delivered, k) for k in K_SOURCED_INTERVAL]
        if delivered else None
    )
    in_band = None
    if band is not None and slots > 0:
        # n-aware: the band bounds the expectation, so consistency is
        # Wilson-interval overlap, not a hard edge on the point estimate.
        in_band = lo <= band[1] and band[0] <= hi
    return {
        "n_slots": slots,
        "confined_secondaries": secondaries,
        "attack": secondaries / slots if slots else None,
        "attack_wilson": [lo, hi],
        "expected_sar": (
            _expected_sar(delivered, K_DECLARED) if delivered else None
        ),
        "floor_band": band,
        "in_floor_band": in_band,
        "delivered_p_dose": _quantiles(delivered),
        "implied_sar": _quantiles(implied_sar),
        "capture_ratio": (
            delivered_copies / emitted if emitted > 0 else None
        ),
        "stage_totals": stage_totals,
    }


def _mechanism_block(runs: list[tuple[Path, dict, dict]]) -> dict[str, Any]:
    cell_medians: list[float] = []
    challenged_share: list[float] = []
    commitments: list[int] = []
    ashore_dosed = 0
    attached = 0
    for _, _, r in runs:
        mech = r.get("mechanism") or {}
        sizes = [int(v) for v in (mech.get("dosed_set_sizes") or {}).values()]
        if sizes:
            cell_medians.append(float(statistics.median(sizes)))
        share = mech.get("challenged_share")
        if share is not None:
            challenged_share.append(float(share))
        commitments.append(int(r.get("commitments_total") or 0))
        ashore_dosed += int(r.get("ashore_dosed_epochs") or 0)
        attached += 1 if r.get("rhythm_attached") else 0
    return {
        "n_runs": len(runs),
        "rhythm_attached": attached,
        "median_epoch_dosed_set": _median(cell_medians),
        "challenged_share_mean": (
            statistics.mean(challenged_share) if challenged_share else None
        ),
        "commitments_median": _median([float(c) for c in commitments]),
        "ashore_dosed_epochs": ashore_dosed,
        "corridor_front": _clock_correlation(runs),
    }


def _paired_table(
    off_runs: list[tuple[Path, dict, dict]],
    on_runs: list[tuple[Path, dict, dict]],
) -> dict[str, Any]:
    def attack(r: dict[str, Any]) -> float | None:
        confined = r.get("confined") or {}
        slots = int(confined.get("confined_slots") or 0)
        if slots <= 0:
            return None
        return int(confined.get("confined_secondaries") or 0) / slots

    off = {p.stem: attack(r) for p, _, r in off_runs}
    on = {p.stem: attack(r) for p, _, r in on_runs}
    deltas = [
        on[s] - off[s] for s in sorted(set(off) & set(on))
        if off[s] is not None and on[s] is not None
    ]
    return {
        "paired_seeds": len(deltas),
        "attack_delta_median": _median(deltas),
        "attack_delta_mean": (
            statistics.mean(deltas) if deltas else None
        ),
    }


def build_readout(results_root: Path) -> dict[str, Any]:
    cells = load_cells(results_root)
    tiers = sorted({key[1] for key in cells})
    out: dict[str, Any] = {"tiers": {}}
    for tier in tiers:
        per_arm = {}
        for arm in _ARMS:
            runs = cells.get((arm, tier), [])
            per_arm[arm] = {
                "confined": _confined_block(runs),
                "mechanism": _mechanism_block(runs),
            }
        per_arm["paired"] = _paired_table(
            cells.get(("off", tier), []),
            cells.get(("on", tier), []),
        )
        out["tiers"][tier] = per_arm
    return out


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_markdown(readout: dict[str, Any]) -> str:
    lines = [
        "| class | arm | cells | slots | 2nd | attack [Wilson] | floor |",
        "|---|---|---|---|---|---|---|",
    ]
    for tier, per_arm in readout["tiers"].items():
        for arm in _ARMS:
            c = per_arm[arm]["confined"]
            m = per_arm[arm]["mechanism"]
            lo, hi = c["attack_wilson"]
            if c["in_floor_band"] is None:
                floor_cell = "—"
            else:
                floor_cell = "in" if c["in_floor_band"] else "OUT"
            lines.append(
                f"| {tier} | {arm} | {m['n_runs']} | {c['n_slots']} | "
                f"{c['confined_secondaries']} | "
                f"{_fmt(c['attack'])} [{_fmt(lo)}–{_fmt(hi)}] | "
                f"{floor_cell} |",
            )
        paired = per_arm["paired"]
        lines.append(
            f"| {tier} | paired Δ | {paired['paired_seeds']} |  |  | "
            f"{_fmt(paired['attack_delta_median'])} "
            f"(mean {_fmt(paired['attack_delta_mean'])}) |  |",
        )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--json", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    readout = build_readout(args.root.resolve())
    if args.json is not None:
        args.json.write_text(
            json.dumps(readout, indent=1) + "\n", encoding="utf-8",
        )
    print(render_markdown(readout))


if __name__ == "__main__":
    main()
