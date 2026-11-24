#!/usr/bin/env python3
"""DP-UNION-01 readout: the frozen joint contract over theta.

Applies the criteria frozen in ``docs/covid/covid_dp_union_01_design.md`` to
the cell artifacts of ``campaigns/covid/dp_union_01``. Every threshold is
read from the design JSON's ``joint_contract`` block; changing one after a
cell ran is a criterion change, not a readout fix.

Usage:
    aws s3 sync s3://<bucket>/campaign/covid_dp_union_01/ out/dpunion/
    scripts/campaign readout covid/dp_union_01 -- --cells-dir out/dpunion \
        --out docs/covid/dp_union_01_readout.json
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DESIGN = _REPO_ROOT / "picard_framework/runs/covid_dp_union_01_design.json"
_ARM = "union_niid"
_PROTOCOLS = "data/config/protocols_covid_dp_dedicated.json"
_ORDER = "SOP-017-DEDQUARTER"
_PARENT_ORDER = "SOP-017-DEDICATED"
_EXEMPT = {"crew_general": 0.25}
_WAVE = "crew_wave"
_ACTIVATION_EPOCH = 391
_ONSET_DAY = 3.0
_ALPHA, _BETA = 0.18, 58.0
_LEGS = ("timing_ignition", "timing_before_share", "attack", "during",
         "capture", "t3", "onboard_table")


def _load_cells(cells_dir: Path) -> dict[float, dict[int, dict[str, Any]]]:
    """Every ``cell_<seed>.json`` under ``cells_dir``, keyed theta -> seed."""
    cells: dict[float, dict[int, dict[str, Any]]] = {}
    for path in sorted(cells_dir.rglob("cell_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        block = payload.get("dp_union") or {}
        if block.get("arm_id") != _ARM or block.get("smoke_num_epochs") is not None:
            continue
        by_seed = cells.setdefault(float(block["theta"]), {})
        if int(block["seed"]) in by_seed:
            raise SystemExit(f"duplicate cell for {path}")
        by_seed[int(block["seed"])] = payload
    return cells


def _audit_inherited(cell: dict[str, Any], theta: float) -> dict[str, bool]:
    """The DP-THETA-FIT-01 invariants that carry over unchanged."""
    block = cell["dp_union"]
    witness = cell.get("quarantine_witness") or {}
    fidelity = cell.get("platform_fidelity") or {}
    scale = (cell.get("dose_response") or {}).get("susceptibility_scale")
    return {
        "platform": fidelity.get("resolved_platform_id") == "diamond_princess",
        "index_onset_day": cell.get("index_onset_day") == _ONSET_DAY,
        "susceptibility_scale": scale is not None and math.isclose(
            scale, theta * (_ALPHA + _BETA) / _ALPHA, rel_tol=1e-9,
        ),
        "quarantine_activation": (
            bool(witness.get("activated"))
            and witness.get("activation_epoch") == _ACTIVATION_EPOCH
        ),
        "close_zones": not fidelity.get("close_zones_fired_flag"),
        "testing_ran": block["t3"]["specimens_through_day"] > 0,
        "observable_agrees": (
            block["onboard_table"]["positives_through_day"]
            == cell["observables"]["campaign_positives"]
        ),
    }


def _audit_wave(
    cell: dict[str, Any], contract: dict[str, Any],
) -> dict[str, bool]:
    """The armed crew wave: day 34 only, wave-tagged, within its test count."""
    table = cell["dp_union"]["onboard_table"]
    t3_day = int(contract["t3"]["through_day_index"])
    wave_day = int(contract["onboard_table"]["through_day_index"])
    late_days = {int(d) for d in table["by_day"] if int(d) > t3_day}
    late = sum(
        row["specimens"] for day, row in table["by_day"].items()
        if int(day) > t3_day
    )
    tagged = table["specimens_by_wave"]
    return {
        "no_specimen_after_wave_day": (
            table["last_specimen_day"] is not None
            and table["last_specimen_day"] <= wave_day
        ),
        "late_specimens_are_the_wave": (
            late_days <= {wave_day}
            and set(tagged) <= {_WAVE}
            and late == tagged.get(_WAVE, 0)
        ),
        "wave_ran": (
            0 < tagged.get(_WAVE, 0)
            <= int(contract["onboard_table"]["wave_tests"])
        ),
    }


def _audit_arming(cell: dict[str, Any]) -> dict[str, bool]:
    """The union's three arming keys, echoed as resolved by the engine."""
    fidelity = cell.get("platform_fidelity") or {}
    fired = set(fidelity.get("fired_protocol_ids") or ())
    crew = cell.get("crew_window") or {}
    total = (crew.get("at_activation") or {}).get("total_crew")
    drawn = (crew.get("exempt_fraction_drawn") or {}).get(_ORDER) or {}
    duty = (cell.get("crew_duty_exclusion") or {}).get("resolved") or {}
    channel = cell.get("specimen_channel") or {}
    capture = cell["dp_union"]["capture"]
    return {
        "protocols_path": fidelity.get("protocols_path") == _PROTOCOLS,
        "quarter_order_fired": _ORDER in fired and _PARENT_ORDER not in fired,
        "exempt_fraction_echo": (
            crew.get("exempt_fraction") == _EXEMPT
            and not crew.get("exempt_work_zones")
        ),
        "exempt_fraction_drawn": (
            total is not None
            and drawn == {"crew_general": int(_EXEMPT["crew_general"] * total + 0.5)}
        ),
        "crew_duty_exclusion": duty.get("enabled") is True,
        "retest_sweeps_armed": channel.get("retest_negatives_on_sweep") is True,
        "campaign_waves_armed": channel.get("campaign_waves") == [_WAVE],
        "funnel_present": (
            capture["infections_funnel"] > 0 or cell["infections_total"] == 0
        ),
    }


def _audit_cell(
    cell: dict[str, Any], theta: float, contract: dict[str, Any],
) -> list[str]:
    """Audit-invariant deviations of one cell (empty list = clean)."""
    checks = {
        **_audit_inherited(cell, theta),
        **_audit_wave(cell, contract),
        **_audit_arming(cell),
    }
    return sorted(name for name, ok in checks.items() if not ok)


def _median(values: list[Any]) -> float | None:
    kept = [v for v in values if v is not None]
    return statistics.median(kept) if kept else None


def _path(cell: dict[str, Any], *keys: str) -> Any:
    value: Any = cell
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def _side(counts: list[int], target: int, fraction: float) -> dict[str, Any]:
    """FIT-01's side rule on the scored class (18 of 24 as a fraction)."""
    need = math.ceil(fraction * len(counts))
    above = sum(1 for c in counts if c > target)
    below = sum(1 for c in counts if c < target)
    side = "compatible"
    if above >= need:
        side = "above"
    elif below >= need:
        side = "below"
    return {
        "target": target,
        "median": statistics.median(counts),
        "seeds_above_target": above,
        "seeds_below_target": below,
        "seeds_needed_to_exclude": need,
        "side": side,
        "ok": side == "compatible",
    }


def _before_share(cell: dict[str, Any]) -> float | None:
    onsets = _path(cell, "observables", "recorded_onsets") or 0
    before = _path(cell, "observables", "onsets_before_split_day") or 0
    return before / onsets if onsets > 0 else None


def _banded(values: list[Any], low: float, high: float) -> dict[str, Any]:
    """A median leg that passes inside the closed interval [low, high]."""
    median = _median(values)
    return {
        "median": median,
        "band": [low, high],
        "ok": median is not None and low <= median <= high,
    }


def _ignition(cells: list[dict[str, Any]], day_max: int) -> dict[str, Any]:
    """Median ignition day; a cell that never ignites counts as +inf."""
    days = [
        math.inf if (day := c["dp_union"]["timing"]["ignition_day"]) is None
        else day
        for c in cells
    ]
    median = statistics.median(days) if days else None
    return {
        "median": None if median in (None, math.inf) else median,
        "never_ignited": sum(1 for d in days if d == math.inf),
        "day_max": day_max,
        "ok": median is not None and median <= day_max,
    }


def _class_legs(
    cells: list[dict[str, Any]], contract: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Every leg of the joint contract on one conditioning class."""
    enough = len(cells) >= int(contract["conditioning"]["min_class_cells"])
    if not cells:
        return {
            name: {"median": None, "pass": False,
                   "verdict": "insufficient class mass"}
            for name in _LEGS
        }
    share = contract["before_share"]
    fraction = float(contract["side_fraction"])
    legs = {
        "timing_ignition": _ignition(
            cells, int(contract["ignition"]["day_max"]),
        ),
        "timing_before_share": _banded(
            [_before_share(c) for c in cells],
            share["record"] - share["tolerance"],
            share["record"] + share["tolerance"],
        ),
        "attack": _banded(
            [c["infections_total"] for c in cells],
            *contract["attack_infections_band"],
        ),
        "during": _banded(
            [c.get("infections_during_window") for c in cells],
            *contract["during_quarantine_band"],
        ),
        "capture": _banded(
            [c["dp_union"]["capture"]["conditioned_capture"] for c in cells],
            float(contract["conditioned_capture"]["floor"]), 1.0,
        ),
        "t3": _side(
            [c["dp_union"]["t3"]["positives_through_day"] for c in cells],
            int(contract["t3"]["cumulative_positives"]), fraction,
        ),
        "onboard_table": _side(
            [c["dp_union"]["onboard_table"]["positives_through_day"]
             for c in cells],
            int(contract["onboard_table"]["positives"]), fraction,
        ),
    }
    for leg in legs.values():
        leg["pass"] = bool(enough and leg.pop("ok"))
        leg["verdict"] = None if enough else "insufficient class mass"
    return legs


def _classes(
    cells: list[dict[str, Any]], contract: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """The founder class (scored) and the takeoff class (reported)."""
    cond = contract["conditioning"]
    founders = int(cond["founder_min_aboard_window_acquisitions"])
    onsets = int(cond["takeoff_min_recorded_onsets"])
    return {
        "founder": [
            c for c in cells
            if (_path(c, "seed_ring", "aboard_window_acquisitions") or 0)
            >= founders
        ],
        "takeoff": [
            c for c in cells
            if (_path(c, "observables", "recorded_onsets") or 0) >= onsets
        ],
        "all": cells,
    }


def _median_by_day(cells: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Per specimen day, the median specimens and positives over cells."""
    tables = [cell["dp_union"]["onboard_table"]["by_day"] for cell in cells]
    days = sorted({day for table in tables for day in table}, key=int)
    return {
        day: {
            field: statistics.median(
                table.get(day, {}).get(field, 0) for table in tables
            )
            for field in ("specimens", "positives")
        }
        for day in days
    }


def _crew_share(cell: dict[str, Any]) -> float | None:
    by_role = cell.get("during_window_by_role") or {}
    crew = float(by_role.get("crew") or 0)
    total = crew + float(by_role.get("passenger") or 0)
    return crew / total if total > 0 else None


def _reported_only(
    seeds: list[int], cells: list[dict[str, Any]], taken: list[dict[str, Any]],
) -> dict[str, Any]:
    """Quantities the design reports and never scores."""
    secondaries = [c["infections_total"] for c in cells]
    capture = [c["dp_union"]["capture"] for c in cells]

    def _med(*keys: str) -> float | None:
        return _median([_path(c, *keys) for c in cells])

    return {
        "p31_per_seed": {
            str(s): c["dp_union"]["t3"]["positives_through_day"]
            for s, c in zip(seeds, cells)
        },
        "p34_per_seed": {
            str(s): c["dp_union"]["onboard_table"]["positives_through_day"]
            for s, c in zip(seeds, cells)
        },
        "secondaries_per_seed": dict(zip(map(str, seeds), secondaries)),
        "extinct_seeds": sum(1 for s in secondaries if s == 0),
        "median_secondaries": statistics.median(secondaries),
        "median_attack_rate": _med("attack_rate"),
        "median_specimens_through_31": _med(
            "dp_union", "t3", "specimens_through_day"),
        "median_specimens_through_34": _med(
            "dp_union", "onboard_table", "specimens_through_day"),
        "median_wave_positives": _median([
            c["dp_union"]["onboard_table"]["positives_through_day"]
            - c["dp_union"]["t3"]["positives_through_day"] for c in cells
        ]),
        "median_recorded_onsets": _med("observables", "recorded_onsets"),
        "median_lab_confirmed_total": _med("lab_confirmed_total"),
        "median_infections_before_quarantine": _med(
            "infections_before_quarantine"),
        "median_infections_during_window_all_seeds": _med(
            "infections_during_window"),
        "median_infections_after_quarantine": _med(
            "infections_after_quarantine"),
        "median_crew_share_during_takeoff": _median(
            [_crew_share(c) for c in taken]),
        "median_unconditioned_capture": _median([
            b["confirmed_funnel"] / b["infections_funnel"]
            for b in capture if b["infections_funnel"]
        ]),
        "median_infections_reachable": _median(
            [b["infections_reachable"] for b in capture]),
        "median_duty_excluded_hosts": _med(
            "crew_duty_exclusion", "excluded_hosts"),
        "duty_excluded_zero_on_takeoff_seeds": sum(
            1 for c in taken
            if not _path(c, "crew_duty_exclusion", "excluded_hosts")
        ),
        "median_realized_exempt_share": _med(
            "crew_window", "at_activation", "realized_exempt_share"),
        "median_founder_yield": _med(
            "seed_ring", "aboard_window_acquisitions"),
        "founder_yield_per_seed": {
            str(s): _path(c, "seed_ring", "aboard_window_acquisitions")
            for s, c in zip(seeds, cells)
        },
        "ignition_day_per_seed": {
            str(s): c["dp_union"]["timing"]["ignition_day"]
            for s, c in zip(seeds, cells)
        },
        "machinery_gap_seeds": [
            s for s, c in zip(seeds, cells)
            if c["dp_union"]["capture"]["infections_reachable"] > 0
            and c["dp_union"]["onboard_table"]["positives_through_day"] == 0
        ],
        "median_by_day": _median_by_day(cells),
    }


def _theta_row(
    theta: float, by_seed: dict[int, dict[str, Any]],
    contract: dict[str, Any], expected_seeds: int,
) -> dict[str, Any]:
    """Per-theta summary: the legs per class, edge flags, audits."""
    seeds = sorted(by_seed)
    cells = [by_seed[s] for s in seeds]
    p31 = [c["dp_union"]["t3"]["positives_through_day"] for c in cells]
    # ``infections_total`` already excludes the seeded index host.
    secondaries = [c["infections_total"] for c in cells]
    classes = _classes(cells, contract)
    scored = contract["conditioning"]["scored_class"]
    legs = _class_legs(classes[scored], contract)
    dead = sum(1 for p in p31 if p == 0) >= int(contract["dead_seeds"])
    saturated = statistics.median(secondaries) >= (
        float(contract["saturation_fraction"]) * (cells[0]["aboard_total"] - 1)
    )
    provisional = len(seeds) != expected_seeds
    low, high = (
        int(contract["t3"]["cumulative_positives"]) * f
        for f in contract["representative_band"]
    )
    in_band = sum(1 for p in p31 if low <= p <= high)
    audits = {
        str(s): found for s, c in zip(seeds, cells)
        if (found := _audit_cell(c, theta, contract))
    }
    return {
        "theta": theta,
        "n": len(seeds),
        "provisional": provisional,
        "scored_class": scored,
        "class_n": {name: len(members) for name, members in classes.items()},
        "legs": legs,
        "passing_legs": [name for name in _LEGS if legs[name]["pass"]],
        "failing_legs": [name for name in _LEGS if not legs[name]["pass"]],
        "dead": dead,
        "saturated": saturated,
        "consistent": (
            None if provisional else
            all(legs[name]["pass"] for name in _LEGS)
            and not dead and not saturated
        ),
        "seeds_in_band": in_band,
        "median_not_representative": (
            in_band < int(contract["representative_min_seeds"])
        ),
        "audit_deviations": audits,
        "reported_only": {
            "legs_on_takeoff_class": _class_legs(classes["takeoff"], contract),
            "legs_on_all_seeds": _class_legs(classes["all"], contract),
            **_reported_only(seeds, cells, classes["takeoff"]),
        },
    }


def _joint(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The joint verdict over complete rows, including the split verdict."""
    live = [r for r in rows if not r["dead"] and not r["saturated"]]
    passes_at = {
        name: [r["theta"] for r in live if r["legs"][name]["pass"]]
        for name in _LEGS
    }
    consistent = [r["theta"] for r in rows if r["consistent"]]
    never = [name for name in _LEGS if not passes_at[name]]
    disjoint = [
        [first, second]
        for i, first in enumerate(_LEGS) for second in _LEGS[i + 1:]
        if passes_at[first] and passes_at[second]
        and not set(passes_at[first]) & set(passes_at[second])
    ]
    return {
        "consistent_thetas": consistent,
        "leg_pass_thetas": passes_at,
        "legs_failing_at_every_theta": never,
        "split_verdict": bool(not consistent and not never and rows),
        "disjoint_leg_pairs": disjoint,
        "dead_thetas": [r["theta"] for r in rows if r["dead"]],
        "saturated_thetas": [r["theta"] for r in rows if r["saturated"]],
        "not_representative_thetas": [
            r["theta"] for r in rows
            if r["consistent"] and r["median_not_representative"]
        ],
    }


def _pilot(
    rows: list[dict[str, Any]], grid: dict[str, Any], contract: dict[str, Any],
) -> list[dict[str, Any]]:
    """T3 side of each pilot decade: median P31 over the pilot seeds only.

    Locates the bracket for the grid's selection rule; no leg is scored.
    """
    pilot = grid.get("pilot") or {}
    seeds = [str(s) for s in pilot.get("seeds", [])]
    target = int(contract["t3"]["cumulative_positives"])
    out = []
    for row in rows:
        if not any(
            math.isclose(row["theta"], t, rel_tol=1e-12)
            for t in pilot.get("thetas", [])
        ):
            continue
        per_seed = row["reported_only"]["p31_per_seed"]
        p31 = [per_seed[s] for s in seeds if s in per_seed]
        median = statistics.median(p31) if p31 else None
        out.append({
            "theta": row["theta"],
            "n": len(p31),
            "p31": p31,
            "median_p31": median,
            "at_or_above_t3": None if median is None else median >= target,
            "dead": row["dead"],
            "saturated": row["saturated"],
        })
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells-dir", required=True,
                        help="local directory holding the synced cell artifacts")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    design = json.loads(_DESIGN.read_text(encoding="utf-8"))
    contract = design["joint_contract"]
    expected = int(design["seeds"])
    cells = _load_cells(Path(args.cells_dir))
    rows = [
        _theta_row(theta, cells[theta], contract, expected)
        for theta in sorted(cells)
    ]
    complete = [row for row in rows if row["n"] == expected]
    grid = design.get("theta_grid") or {}
    scored = grid.get("scored_thetas") or []
    scored_rows = [
        row for row in complete
        if any(math.isclose(row["theta"], t, rel_tol=1e-12) for t in scored)
    ]
    readout = {
        "task_id": "DP-UNION-01",
        "design_id": design["design_id"],
        "joint_contract": contract,
        "declared_thetas": design["thetas"],
        "complete_thetas": [row["theta"] for row in complete],
        "incomplete_thetas": {
            str(row["theta"]): row["n"] for row in rows if row["n"] != expected
        },
        "theta_grid": grid,
        "pilot": _pilot(rows, grid, contract),
        "joint": (
            _joint(scored_rows)
            if scored and len(scored_rows) == len(scored) else None
        ),
        "rows": rows,
    }
    text = json.dumps(readout, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"WROTE {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
