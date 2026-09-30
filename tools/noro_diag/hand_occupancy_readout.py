#!/usr/bin/env python3
"""Readout for the NORO-HAND-STATIONARY-01 cells.

Aggregation only: this script reads the per-seed dumps written by
``growth_chain_census.py`` (``fl_spr_12d`` zips) and
``fomite_mass_balance.py`` (``classic_cruise_1900`` gzips) and never re-runs
or re-derives a measurement. It answers the question frozen in
``docs/ledger/NORO-HAND-STATIONARY-01.md``: whether the shipped hand
reservoir occupies the Liu 2013 rinse distribution.

The Liu comparison set is restated from register tranche 40
(``docs/literature/consensus_tranche_40_hand_event_amplitude.md``,
PMC3837815) as comparison targets; nothing here is fitted to them.

Sampling map (declared in the ledger before any cell ran): the model's
point-in-time rinse analogue is the *end-of-epoch realized load* on each
shedding-host epoch row (post-replenish, post-deposit, post-hygiene); the
post-defecation analogue is the post-replenish load on rows where a stool
event fired; the routine analogue is the end-of-epoch load on rows where
none did.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import statistics
import sys
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulation_utils.paths import (  # noqa: E402
    prepare_output_directory,
    resolve_child_path,
)
from tools.noro_diag.cell_readout import print_block, spread  # noqa: E402
from tools.noro_diag.hand_occupancy import LIU_LOD_GEC  # noqa: E402

# Liu 2013 rinse distribution (tranche 40): the frozen comparison targets.
LIU_POSITIVE_SHARE = 18 / 71
LIU_POSITIVE_MEAN_LOG10 = (3.30, 4.45)
LIU_NEVER_POSITIVE_SHARE = 2 / 6
LIU_POST_BATHROOM = {"positive_share": 11 / 89, "mean_log10": 2.30}
LIU_ROUTINE = {"positive_share": 6 / 16, "mean_log10": 3.32}

# Verdict thresholds, declared in the ledger before any cell ran.
RATIO_TOLERANCE = 5.0
POSITIVE_MEAN_LO = LIU_POSITIVE_MEAN_LOG10[0] - 1.0
POSITIVE_MEAN_HI = LIU_POSITIVE_MEAN_LOG10[1] + 1.0
NEVER_POSITIVE_HI = 0.80
NEVER_POSITIVE_LO = 0.05

SPIRIT_TIER = "fl_spr_12d"
CLASSIC_CELL = "classic_cruise_1900"
IGNITED_SEEDS = [
    8105, 8107, 8110, 8112, 8113, 8114, 8115, 8117, 8121, 8123, 8124,
    8129, 8132, 8135, 8137, 8148, 8149, 8156, 8158, 8159, 8162, 8163,
]
CLASSIC_SEEDS = list(range(8000, 8020))


def _spirit_cells(raw_dir: Path) -> list[dict[str, Any]]:
    """One growth-census payload per seed, from the campaign-layout zips."""
    cells = []
    cell_dir = raw_dir / SPIRIT_TIER
    for path in sorted(cell_dir.glob("*.zip")):
        with zipfile.ZipFile(path) as archive:
            payload = json.loads(
                gzip.decompress(
                    archive.read("growth_census.json.gz"),
                ).decode("utf-8"),
            )
            payload["zip"] = path.name
            cells.append(payload)
    return sorted(cells, key=lambda c: c["meta"]["seed"])


def _classic_cells(raw_dir: Path) -> list[dict[str, Any]]:
    cell_dir = raw_dir / CLASSIC_CELL
    cells = []
    for path in sorted(cell_dir.glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            cells.append(json.load(handle))
    return sorted(cells, key=lambda c: c["seed"])


def _seed_of(cell: dict[str, Any]) -> int:
    return int(cell.get("meta", {}).get("seed", cell.get("seed", -1)))


def _rows(cell: dict[str, Any]) -> list[dict[str, Any]]:
    return cell.get("hand_occupancy_rows") or []


def _is_admissible(cell: dict[str, Any]) -> bool:
    """The declared void rule: zero norwalk_gi fomite deliveries -> void."""
    zones = cell.get("zones") or []
    if zones:
        return sum(int(z.get("delivery_calls", 0)) for z in zones) > 0
    return bool(cell.get("pickups"))


def _shedding_rows(cell: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in _rows(cell) if row.get("shedding")]


def _log10_of(load: float) -> float:
    return math.log10(load) if load > 0.0 else -math.inf


def _end_loads(rows: list[dict[str, Any]]) -> list[tuple[dict, float]]:
    """(row, end-load) pairs for rows the hygiene pass reached."""
    return [
        (row, float(row["load_end_epoch_gec"]))
        for row in rows
        if row.get("load_end_epoch_gec") is not None
    ]


def _positivity(rows: list[tuple[dict, float]]) -> dict[str, Any]:
    n = len(rows)
    positive = [(row, load) for row, load in rows if load >= LIU_LOD_GEC]
    out: dict[str, Any] = {
        "samples": n,
        "positive_samples": len(positive),
        "positive_share": len(positive) / n if n else None,
    }
    if positive:
        logs = [_log10_of(load) for _row, load in positive]
        out["positive_mean_log10"] = statistics.fmean(logs)
        out["positive_sd_log10"] = (
            statistics.stdev(logs) if len(logs) > 1 else 0.0
        )
        out["positive_mean_gec"] = 10.0 ** out["positive_mean_log10"]
    return out


def _never_positive(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Share of shedding hosts whose end-load never reaches LOD."""
    peaks: dict[int, float] = {}
    for row in rows:
        load = row.get("load_end_epoch_gec")
        if load is None:
            continue
        aid = int(row["agent_id"])
        peaks[aid] = max(peaks.get(aid, 0.0), float(load))
    if not peaks:
        return {"hosts": 0}
    never = sum(1 for load in peaks.values() if load < LIU_LOD_GEC)
    return {
        "hosts": len(peaks),
        "never_positive_hosts": never,
        "never_positive_share": never / len(peaks),
    }


def _ordering(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Event vs routine ordering inside the model, both samplings."""
    event = [r for r in rows if r.get("stool_event")]
    routine = [r for r in rows if r.get("stool_event") is False]
    post_event = [
        (r, float(r["load_post_replenish_gec"])) for r in event
    ]
    end_routine = _end_loads(routine)
    end_event = _end_loads(event)
    return {
        "post_defecation": _positivity(post_event),
        "routine_end": _positivity(end_routine),
        "event_end": _positivity(end_event),
        "event_rows": len(event),
        "routine_rows": len(routine),
        "model_ordering_post_vs_routine": _sign(
            _positivity(post_event).get("positive_share"),
            _positivity(end_routine).get("positive_share"),
        ),
        "model_ordering_end_vs_end": _sign(
            _positivity(end_event).get("positive_share"),
            _positivity(end_routine).get("positive_share"),
        ),
        "liu_ordering": "post_bathroom_lower",
    }


def _sign(a: float | None, b: float | None) -> str | None:
    if a is None or b is None:
        return None
    if a > b:
        return "event_higher"
    if a < b:
        return "event_lower"
    return "equal"


def _cell_readout(
    cells: list[dict[str, Any]], expected_seeds: list[int],
) -> dict[str, Any]:
    """One cell block: per-seed rows plus the pooled reading."""
    admissible = [c for c in cells if _is_admissible(c)]
    void = [_seed_of(c) for c in cells if not _is_admissible(c)]
    seen = {_seed_of(c) for c in cells}
    missing = [s for s in expected_seeds if s not in seen]
    all_rows = [row for c in admissible for row in _shedding_rows(c)]
    end_pairs = _end_loads(all_rows)
    symptomatic_rows = [r for r in all_rows if r.get("symptomatic")]
    return {
        "cells_loaded": len(cells),
        "seeds_missing": missing,
        "void_seeds": void,
        "admissible_cells": len(admissible),
        "shedding_host_epoch_rows": len(all_rows),
        "end_load_missing_rows": len(all_rows) - len(end_pairs),
        "positivity": _positivity(end_pairs),
        "positivity_symptomatic_only": _positivity(
            _end_loads(symptomatic_rows),
        ),
        "never_positive": _never_positive(all_rows),
        "ordering": _ordering(all_rows),
        "occupancy": {
            "at_target_rows": sum(1 for r in all_rows if r.get("at_target")),
            "underflowed_rows": sum(
                1 for r in all_rows if r.get("underflowed")
            ),
            "first_seen_rows": sum(
                1 for r in all_rows if r.get("first_seen")
            ),
            "event_rows": sum(
                1 for r in all_rows if r.get("stool_event")
            ),
            "continuous_path_rows": sum(
                1 for r in all_rows if not r.get("event_path")
            ),
        },
        "per_seed": [
            {
                "seed": _seed_of(c),
                "shedding_rows": len(_shedding_rows(c)),
                "positive_share": _positivity(
                    _end_loads(_shedding_rows(c)),
                ).get("positive_share"),
                "never_positive_share": (
                    _never_positive(_shedding_rows(c)).get(
                        "never_positive_share",
                    )
                ),
            }
            for c in admissible
        ],
    }


def _evaluate(positivity: dict[str, Any]) -> dict[str, Any]:
    """The verdict criteria applied to one pooled positivity block."""
    share = positivity.get("positive_share")
    checks: dict[str, Any] = {
        "positive_share": share,
        "liu_positive_share": LIU_POSITIVE_SHARE,
        "ratio": (
            share / LIU_POSITIVE_SHARE
            if share is not None else None
        ),
        "ratio_tolerance": RATIO_TOLERANCE,
    }
    primary_miss = (
        share is None
        or share / LIU_POSITIVE_SHARE > RATIO_TOLERANCE
        or share / LIU_POSITIVE_SHARE < 1 / RATIO_TOLERANCE
    )
    checks["primary_positivity_miss"] = primary_miss
    return checks


def _verdict(
    pooled: dict[str, Any], never: dict[str, Any],
) -> dict[str, Any]:
    """The frozen rule: primary miss, or >=2 secondary misses."""
    primary = _evaluate(pooled)
    mean_log = pooled.get("positive_mean_log10")
    mean_miss = (
        mean_log is not None
        and not (POSITIVE_MEAN_LO <= mean_log <= POSITIVE_MEAN_HI)
    )
    never_share = never.get("never_positive_share")
    never_miss = (
        never_share is not None
        and not (NEVER_POSITIVE_LO <= never_share <= NEVER_POSITIVE_HI)
    )
    ordering_miss = (
        pooled.get("ordering_sign") is not None
        and pooled["ordering_sign"] == "event_higher"
    )
    secondary_misses = sum(
        [mean_miss, never_miss, ordering_miss],
    )
    defect = bool(primary["primary_positivity_miss"]) or (
        secondary_misses >= 2
    )
    return {
        "primary": primary,
        "secondary": {
            "positive_mean_log10": mean_log,
            "positive_mean_window": [POSITIVE_MEAN_LO, POSITIVE_MEAN_HI],
            "positive_mean_miss": mean_miss,
            "never_positive_share": never_share,
            "never_positive_window": [
                NEVER_POSITIVE_LO, NEVER_POSITIVE_HI,
            ],
            "never_positive_miss": never_miss,
            "ordering_sign": pooled.get("ordering_sign"),
            "ordering_miss": ordering_miss,
            "ordering_note": (
                "weighs toward defect but alone never decides: the "
                "engine's routine rows are near-underflow by construction "
                "of the mechanism being measured"
            ),
        },
        "secondary_misses": secondary_misses,
        "verdict": "defect_candidate" if defect else "intended_reading",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir", type=Path,
        default=REPO_ROOT / "docs/norovirus/noro_hand_stationary_01",
    )
    parser.add_argument(
        "--out", type=Path,
        default=REPO_ROOT / "docs/norovirus/noro_hand_stationary_01",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    spirit = _cell_readout(
        _spirit_cells(args.raw_dir), IGNITED_SEEDS,
    )
    classic = _cell_readout(
        _classic_cells(args.raw_dir), CLASSIC_SEEDS,
    )
    all_rows: list[dict[str, Any]] = []
    for cell in _spirit_cells(args.raw_dir) + _classic_cells(args.raw_dir):
        if _is_admissible(cell):
            all_rows.extend(_shedding_rows(cell))
    end_pairs = _end_loads(all_rows)
    pooled_pos = _positivity(end_pairs)
    pooled_pos["ordering_sign"] = _ordering(all_rows)[
        "model_ordering_post_vs_routine"
    ]
    pooled_never = _never_positive(all_rows)
    payload = {
        "raw_dir": str(args.raw_dir),
        "liu_targets": {
            "positive_share": LIU_POSITIVE_SHARE,
            "positive_mean_log10": LIU_POSITIVE_MEAN_LOG10,
            "never_positive_share": LIU_NEVER_POSITIVE_SHARE,
            "post_bathroom": LIU_POST_BATHROOM,
            "routine": LIU_ROUTINE,
        },
        "cells": {
            SPIRIT_TIER: spirit,
            CLASSIC_CELL: classic,
        },
        "pooled": {
            "shedding_host_epoch_rows": len(all_rows),
            "positivity": pooled_pos,
            "never_positive": pooled_never,
            "ordering": _ordering(all_rows),
        },
        "end_load_spread_log10": spread(
            [
                _log10_of(load) for _row, load in end_pairs
                if load > 0.0
            ],
            quartiles=True,
        ),
    }
    verdict = _verdict(pooled_pos, pooled_never)
    payload["verdict"] = verdict
    for key in ("cells", "pooled", "verdict"):
        print_block(key, payload[key])
    out_dir = Path(
        prepare_output_directory(str(args.out), allowed_roots=(str(REPO_ROOT),)),
    )
    path = resolve_child_path(str(out_dir), "hand_occupancy_cells.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True, default=str)
    print(f"\nwritten: {path}")
    study_ok = (
        len(spirit["void_seeds"]) <= 4 and len(classic["void_seeds"]) <= 4
    )
    return 0 if study_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
