#!/usr/bin/env python3
"""FLU-VIS-01 readout: aggregate the visibility-grid ``cell_<seed>.json``
payloads and contrast every arm against the FLU-OPEN-01 baseline.

Reads ``--root`` laid out as ``<block>/cell_<seed>.json`` (block names
``flu_<tier>_r<scale>_<corner>``) and, optionally, ``--baseline-root``
pointed at the synced FLU-OPEN-01 artifacts (blocks ``flu_<tier>``) —
the reuse-baseline column the DESIGN declares. Emits JSON + Markdown.

The comparators applied here were frozen in ``DESIGN.md`` before any
cell ran; this file measures declared corners against them, it never
selects an arm and never tunes a constant.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.diag.readout_common import quantiles, wilson_interval  # noqa: E402

_WARD_PRESENTING = 0.007
_WARD_PRESENTING_BAND = (0.004, 0.010)
_F5_FRAME = (0.03, 0.15)
_BLOCK_RE = re.compile(r"^flu_(?P<tier>\w+?)_r(?P<scale>\d+)_(?P<corner>dec|str)$")
_BASELINE_BLOCK_RE = re.compile(r"^flu_(?P<tier>\w+)$")
_ARM_ORDER = {"r100_dec": 0, "r025_dec": 1, "r025_str": 2,
              "r050_dec": 3, "r050_str": 4, "r200_dec": 5, "r200_str": 6}


def _wilson(k: int, n: int) -> dict[str, float]:
    lo, hi = wilson_interval(k, n)
    return {"lo": lo, "hi": hi}


def _arm_key(block: str) -> str | None:
    m = _BLOCK_RE.match(block)
    return f"r{m['scale']}_{m['corner']}" if m else None


def _tier_of(block: str) -> str | None:
    m = _BLOCK_RE.match(block)
    if m:
        return m["tier"]
    m = _BASELINE_BLOCK_RE.match(block)
    return m["tier"] if m else None


def _iter_cells(root: Path) -> dict[str, list[dict[str, Any]]]:
    blocks: dict[str, list[dict[str, Any]]] = {}
    for block_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for cell_file in sorted(block_dir.glob("cell_*.json")):
            cell = json.loads(cell_file.read_text())
            cell["_block"] = block_dir.name
            blocks.setdefault(block_dir.name, []).append(cell)
    return blocks


def _first_status_epoch(cell: dict[str, Any], status: str) -> int | None:
    for e in cell.get("escalation_log") or []:
        if str(e.get("to")) == status and not e.get("pending"):
            return int(e["epoch"])
    return None


def _sum_rows(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Pool per-cell infection rows into arm×class counters."""
    out: dict[str, Any] = {
        "cells": len(cells),
        "infected": 0,
        "ill": 0,
        "reported": 0,
        "index": 0,
        "onboard": 0,
        "acq_reported": 0,
        "acq_ill": 0,
        "acq_infected": 0,
        "outbreak_cells": 0,
        "index_invariant_fails": 0,
        "confined_cells": 0,
        "quarantined": 0,
        "isolated": 0,
        "alert_cells": 0,
        "alert_epochs": [],
        "presenting_attack": [],
        "cell_infected": [],
        "cell_onboard": [],
        "cell_reported": [],
        "trigger": {},
        "routes": {},
        "caregiver_dom": 0,
        "mild_onsets": 0,
        "complement": 0,
        "per_seed": {},
    }
    for cell in cells:
        c = cell["counts"]
        out["cell_infected"].append(c["ever_infected"])
        out["cell_reported"].append(c["ever_reported"])
        complement = (cell.get("complement") or {}).get("total") or 0
        out["complement"] += complement
        out["presenting_attack"].append(
            c["ever_reported"] / complement if complement else 0.0,
        )
        out["outbreak_cells"] += int(c["onboard_acquired"] > 0)
        out["index_invariant_fails"] += int(c["index_cases"] < 2)
        confined = c["quarantined_end"] + c["isolated_end"]
        out["confined_cells"] += int(confined > 0)
        out["quarantined"] += c["quarantined_end"]
        out["isolated"] += c["isolated_end"]
        out["cell_onboard"].append(c["onboard_acquired"])
        trig = str(cell.get("final_trigger_status"))
        out["trigger"][trig] = out["trigger"].get(trig, 0) + 1
        alert_epoch = _first_status_epoch(cell, "ALERT")
        if alert_epoch is not None or trig == "ALERT":
            out["alert_cells"] += 1
        if alert_epoch is not None:
            out["alert_epochs"].append(alert_epoch)
        out["mild_onsets"] += int(
            (cell.get("onset_severity_counts") or {}).get("mild", 0),
        )
        _sum_infections(cell["infections"], out)
        out["per_seed"][cell["seed"]] = {
            "infected": c["ever_infected"],
            "reported": c["ever_reported"],
            "onboard": c["onboard_acquired"],
            "quarantined": confined,
        }
    return out


def _sum_infections(rows: list[dict[str, Any]], out: dict[str, Any]) -> None:
    for r in rows:
        out["infected"] += 1
        out["ill"] += int(r["ill"])
        out["reported"] += int(r["reported"])
        out["index"] += int(r["index"])
        is_acq = not r["index"]
        out["onboard"] += int(is_acq)
        if is_acq:
            out["acq_infected"] += 1
            out["acq_ill"] += int(r["ill"])
            out["acq_reported"] += int(r["reported"])
        dom = r.get("dominant_route") or ("index_or_boarding" if r["index"] else "unknown")
        out["routes"][dom] = out["routes"].get(dom, 0) + 1
        if dom == "caregiver":
            out["caregiver_dom"] += 1


def _surfaces(tot: dict[str, Any]) -> dict[str, Any]:
    """The frozen-frame surfaces for one arm×class cell group."""
    n = tot["infected"]
    na = tot["acq_infected"]
    res: dict[str, Any] = {
        "cells": tot["cells"],
        "infected": n,
        "complement": tot["complement"],
    }
    attack = tot["presenting_attack"]
    res["presenting_attack"] = {
        "mean": sum(attack) / max(1, len(attack)),
        "median": quantiles(attack).get("median"),
        "ward": _WARD_PRESENTING,
        "ward_band": list(_WARD_PRESENTING_BAND),
        "brackets_ward": bool(
            attack
            and _WARD_PRESENTING_BAND[0]
            <= sum(attack) / len(attack)
            <= _WARD_PRESENTING_BAND[1],
        ),
    }
    if n:
        res["reported_per_infected"] = {
            "p": tot["reported"] / n,
            "k": tot["reported"],
            "n": n,
            "wilson": _wilson(tot["reported"], n),
            "f5_frame": list(_F5_FRAME),
            "in_frame": _F5_FRAME[0] <= tot["reported"] / n <= _F5_FRAME[1],
        }
        res["ill_per_infected"] = {"p": tot["ill"] / n}
    if na:
        res["acq_reported_per_infected"] = {
            "p": tot["acq_reported"] / na,
            "k": tot["acq_reported"],
            "n": na,
            "wilson": _wilson(tot["acq_reported"], na),
        }
        res["acq_ill_per_infected"] = {"p": tot["acq_ill"] / na}
    res["outbreak_rate"] = tot["outbreak_cells"] / max(1, tot["cells"])
    res["alert_rate"] = tot["alert_cells"] / max(1, tot["cells"])
    res["alert_epoch"] = quantiles(tot["alert_epochs"])
    res["confinement"] = {
        "cells_with_confinement": tot["confined_cells"],
        "quarantined_end": tot["quarantined"],
        "isolated_end": tot["isolated"],
    }
    res["infected_dist"] = quantiles(tot["cell_infected"])
    res["index_invariant_fails"] = tot["index_invariant_fails"]
    res["mild_onsets"] = tot["mild_onsets"]
    res["dominant_routes"] = tot["routes"]
    res["caregiver_dominant"] = tot["caregiver_dom"]
    return res


def _paired_deltas(
    arm_cells: list[dict[str, Any]],
    baseline_per_seed: dict[int, dict[str, int]],
) -> dict[str, Any]:
    """Per-seed feedback contrast vs the baseline arm (DESIGN §4.4)."""
    deltas: dict[str, list[int]] = {"infected": [], "onboard": [],
                                   "reported": [], "quarantined": []}
    paired = 0
    for cell in arm_cells:
        base = baseline_per_seed.get(cell["seed"])
        if base is None:
            continue
        paired += 1
        cur = (cell["counts"]["ever_infected"], cell["counts"]["onboard_acquired"],
               cell["counts"]["ever_reported"],
               cell["counts"]["quarantined_end"] + cell["counts"]["isolated_end"])
        deltas["infected"].append(cur[0] - base["infected"])
        deltas["onboard"].append(cur[1] - base["onboard"])
        deltas["reported"].append(cur[2] - base["reported"])
        deltas["quarantined"].append(cur[3] - base["quarantined"])
    out: dict[str, Any] = {"paired_seeds": paired}
    for key, vals in deltas.items():
        out[key] = {
            "mean": sum(vals) / len(vals) if vals else None,
            "median": quantiles(vals).get("median"),
            "share_positive": (
                sum(1 for v in vals if v > 0) / len(vals) if vals else None
            ),
        }
    return out


def build_readout(
    root: Path,
    baseline_root: Path | None,
) -> dict[str, Any]:
    """Aggregate every arm×class block; baseline cells fold in as the
    ``r100_dec`` arm when ``--baseline-root`` is given."""
    tiers: dict[str, dict[str, list[dict[str, Any]]]] = {}
    baseline: dict[str, dict[int, dict[str, int]]] = {}
    if baseline_root is not None:
        for block, cells in _iter_cells(baseline_root).items():
            tier = _tier_of(block)
            if tier is None:
                continue
            tiers.setdefault(tier, {})["r100_dec"] = cells
            tot = _sum_rows(cells)
            baseline[tier] = tot["per_seed"]
    for block, cells in _iter_cells(root).items():
        arm = _arm_key(block)
        tier = _tier_of(block)
        if arm is None or tier is None:
            continue
        tiers.setdefault(tier, {})[arm] = cells
        if arm == "r100_dec" and baseline_root is None:
            tot = _sum_rows(cells)
            baseline[tier] = tot["per_seed"]

    per_tier: dict[str, Any] = {}
    for tier, arms in sorted(tiers.items()):
        arm_rows: dict[str, Any] = {}
        for arm, cells in sorted(
            arms.items(), key=lambda kv: _ARM_ORDER.get(kv[0], 99),
        ):
            tot = _sum_rows(cells)
            arm_rows[arm] = {
                "surfaces": _surfaces(tot),
                "paired_vs_baseline": _paired_deltas(
                    cells, baseline.get(tier) or {},
                ),
            }
        per_tier[tier] = arm_rows
    return {
        "schema": "flu_visibility_01.readout.v1",
        "root": str(root),
        "baseline_root": str(baseline_root) if baseline_root else None,
        "cells": sum(
            len(c) for arms in tiers.values() for c in arms.values()
        ),
        "per_tier": per_tier,
    }


def _pct(p: float | None) -> str:
    return f"{p * 100:.1f}%" if p is not None else "n/a"


def _fmt_p(p: float | None) -> str:
    return f"{p * 100:.2f}%" if p is not None else "n/a"


def render_markdown(readout: dict[str, Any]) -> str:
    lines = ["# FLU-VIS-01 visibility sweep readout", ""]
    lines.append(
        f"cells={readout['cells']}  tiers={len(readout['per_tier'])}  "
        f"baseline_root={readout['baseline_root'] or 'r100_dec blocks'}",
    )
    for tier, arms in readout["per_tier"].items():
        lines.append("")
        lines.append(f"## {tier}")
        lines.append(
            "| arm | cells | presenting attack | rep/inf pooled | rep/inf acq | "
            "outbreak | ALERT (rate, med epoch) | confined | mild onsets |",
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for arm, row in arms.items():
            s = row["surfaces"]
            pa = s["presenting_attack"]
            rpi = s.get("reported_per_infected") or {}
            acq = s.get("acq_reported_per_infected") or {}
            lines.append(
                f"| {arm} | {s['cells']} "
                f"| {_fmt_p(pa['mean'])} (med {_fmt_p(pa['median'])}) "
                f"{'≈Ward' if pa['brackets_ward'] else ''} "
                f"| {_pct(rpi.get('p'))} {'in-frame' if rpi.get('in_frame') else ''} "
                f"| {_pct(acq.get('p'))} "
                f"| {_pct(s['outbreak_rate'])} "
                f"| {_pct(s['alert_rate'])}, ep {s['alert_epoch'].get('median', '—')} "
                f"| {s['confinement']['cells_with_confinement']} "
                f"| {s['mild_onsets']} |",
            )
        lines.append("")
        lines.append("### per-seed paired deltas vs baseline")
        lines.append(
            "| arm | paired | Δonboard (mean/med) | Δinfected (mean/med) | "
            "Δreported (mean/med) | Δquarantine (mean/med) |",
        )
        lines.append("|---|---|---|---|---|---|")
        for arm, row in arms.items():
            if arm == "r100_dec":
                continue
            d = row["paired_vs_baseline"]
            if not d["paired_seeds"]:
                continue

            def _dd(key: str) -> str:
                v = d[key]
                m = f"{v['mean']:+.2f}" if v["mean"] is not None else "n/a"
                md = f"{v['median']:+g}" if v["median"] is not None else "n/a"
                return f"{m}/{md}"

            lines.append(
                f"| {arm} | {d['paired_seeds']} "
                f"| {_dd('onboard')} | {_dd('infected')} "
                f"| {_dd('reported')} | {_dd('quarantined')} |",
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", required=True,
        help="dir laid out as flu_<tier>_r<scale>_<corner>/cell_<seed>.json",
    )
    parser.add_argument(
        "--baseline-root", default=None,
        help="optional synced FLU-OPEN-01 artifacts dir (flu_<tier>/cell_*.json)",
    )
    parser.add_argument(
        "--out", default=None, help="write JSON readout here (markdown -> stdout)",
    )
    args = parser.parse_args(argv)
    readout = build_readout(
        Path(args.root),
        Path(args.baseline_root) if args.baseline_root else None,
    )
    if args.out:
        Path(args.out).write_text(
            json.dumps(readout, indent=1) + "\n",
            encoding="utf-8",
        )
    print(render_markdown(readout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
