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


def _project(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep only what this readout needs; the rest is released per cell."""
    balance = payload.get("voyage_balance") or {}
    pickups = payload.get("pickups") or []
    doses = payload.get("doses") or []
    return {
        "seed": _seed_of(payload),
        "rows": payload.get("hand_occupancy_rows") or [],
        "zones": payload.get("zones") or [],
        # Lean per-seed extracts carry the flag precomputed; full dumps
        # carry the pickups row table it is derived from.
        "has_pickups": payload.get(
            "has_pickups", bool(payload.get("pickups")),
        ),
        # NORO-HAND-RESERVOIR-01 witness: pool mass drawn by
        # non-challengeable hands. Classic cells carry it precomputed in
        # the voyage balance; spirit cells carry the tagged row tables --
        # zone/patch pickups plus the sanitary channel's dose rows.
        # Dumps from the defect census have no ``challengeable`` field and
        # correctly project 0: baseline cells had no reservoir deliveries.
        "reservoir_delivered_gec": float(
            balance.get("delivered_to_reservoir_gec", 0.0),
        )
        + sum(
            float(row.get("delivered", 0.0)) for row in pickups
            if row.get("challengeable") is False
        )
        + sum(
            float(row.get("delivered", 0.0)) for row in doses
            if row.get("channel") == "sanitary"
            and row.get("challengeable") is False
        ),
        "pickup_delivered_gec": float(
            balance.get("delivered_all_paths_gec", 0.0),
        )
        or sum(
            float(row.get("delivered", 0.0)) for row in pickups
        )
        + sum(
            float(row.get("delivered", 0.0)) for row in doses
            if row.get("channel") == "sanitary"
        ),
    }


def _spirit_cells(raw_dir: Path) -> list[dict[str, Any]]:
    """Projected cells, parsed one at a time -- payloads are ~300MB each."""
    cell_dir = raw_dir / SPIRIT_TIER
    cells = []
    for path in sorted(cell_dir.glob("*.zip")):
        with zipfile.ZipFile(path) as archive:
            payload = json.loads(
                gzip.decompress(
                    archive.read("growth_census.json.gz"),
                ).decode("utf-8"),
            )
        cells.append(_project(payload))
        del payload
    return sorted(cells, key=lambda c: c["seed"])


def _classic_cells(raw_dir: Path) -> list[dict[str, Any]]:
    cell_dir = raw_dir / CLASSIC_CELL
    cells = []
    for path in sorted(cell_dir.glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            cells.append(_project(json.load(handle)))
    return sorted(cells, key=lambda c: c["seed"])


def _seed_of(cell: dict[str, Any]) -> int:
    return int(cell.get("meta", {}).get("seed", cell.get("seed", -1)))


def _is_admissible(cell: dict[str, Any]) -> bool:
    """The declared void rule: zero norwalk_gi fomite deliveries -> void."""
    if cell["zones"]:
        return sum(int(z.get("delivery_calls", 0)) for z in cell["zones"]) > 0
    return cell["has_pickups"]


def _shedding_rows(cell: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in cell["rows"] if row.get("shedding")]


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
        "reservoir_witness": {
            "reservoir_delivered_gec": sum(
                c["reservoir_delivered_gec"] for c in admissible
            ),
            "pickup_delivered_gec": sum(
                c["pickup_delivered_gec"] for c in admissible
            ),
        },
        "wet_window_witness": _wet_window_witness(all_rows),
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


def _wet_window_witness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """NORO-HAND-PRACTICE-01 witness: the deposit-side drying blend.

    ``hand_wet_transfer`` is recorded per row only under the
    ``hygiene_cycle`` arm; rows from every other arm carry ``None`` and
    count as unmeasured, not dry. A row counts as wet-window-open when
    its blend factor exceeds the dry ceiling of the declared interval
    (0.08).
    """
    factors = [
        row["hand_wet_transfer"] for row in rows
        if row.get("hand_wet_transfer") is not None
    ]
    wet_open = [f for f in factors if f > 0.08]
    return {
        "rows_with_factor": len(factors),
        "wet_window_open_rows": len(wet_open),
        "wet_window_open_share": (
            len(wet_open) / len(factors) if factors else None
        ),
        "mean_transfer_factor": (
            statistics.fmean(factors) if factors else None
        ),
    }


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


def _reservoir_verdict(
    pooled: dict[str, Any], never: dict[str, Any],
    ordering_sign: str | None,
) -> dict[str, Any]:
    """NORO-HAND-RESERVOIR-01 verdict map, frozen before the re-census ran.

    ``mechanism_restored`` needs the tighter band R in [1/3, 3], the
    ordering actually flipped (event < routine -- the mechanism's whole
    prediction), and both secondary windows. ``still_starved`` is R < 0.2:
    deposited mass cannot carry the reservoir. R > 5 is an over-supply
    miss, reported as ``partial`` with ``over_supply`` flagged.
    """
    share = pooled.get("positive_share")
    ratio = share / LIU_POSITIVE_SHARE if share is not None else None
    mean_log = pooled.get("positive_mean_log10")
    never_share = never.get("never_positive_share")
    flipped = ordering_sign == "event_lower"
    over_supply = ratio is not None and ratio > RATIO_TOLERANCE
    starved = ratio is None or ratio < 1 / RATIO_TOLERANCE
    restored_band = ratio is not None and (1 / 3.0) <= ratio <= 3.0
    mean_ok = (
        mean_log is not None
        and POSITIVE_MEAN_LO <= mean_log <= POSITIVE_MEAN_HI
    )
    never_ok = (
        never_share is not None
        and NEVER_POSITIVE_LO <= never_share <= NEVER_POSITIVE_HI
    )
    if restored_band and flipped and mean_ok and never_ok:
        verdict = "mechanism_restored"
    elif starved:
        verdict = "still_starved"
    else:
        verdict = "partial"
    return {
        "verdict": verdict,
        "positive_share": share,
        "liu_positive_share": LIU_POSITIVE_SHARE,
        "ratio_vs_liu": ratio,
        "restored_band": [1 / 3.0, 3.0],
        "defect_band": [1 / RATIO_TOLERANCE, RATIO_TOLERANCE],
        "ordering_sign": ordering_sign,
        "ordering_flipped": flipped,
        "positive_mean_log10": mean_log,
        "positive_mean_window": [POSITIVE_MEAN_LO, POSITIVE_MEAN_HI],
        "positive_mean_ok": mean_ok,
        "never_positive_share": never_share,
        "never_positive_window": [NEVER_POSITIVE_LO, NEVER_POSITIVE_HI],
        "never_positive_ok": never_ok,
        "over_supply": over_supply,
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
    spirit_cells = _spirit_cells(args.raw_dir)
    classic_cells = _classic_cells(args.raw_dir)
    spirit = _cell_readout(spirit_cells, IGNITED_SEEDS)
    classic = _cell_readout(classic_cells, CLASSIC_SEEDS)
    all_rows = [
        row
        for cell in spirit_cells + classic_cells
        if _is_admissible(cell)
        for row in _shedding_rows(cell)
    ]
    end_pairs = _end_loads(all_rows)
    pooled_pos = _positivity(end_pairs)
    pooled_pos["ordering_sign"] = _ordering(all_rows)[
        "model_ordering_post_vs_routine"
    ]
    pooled_never = _never_positive(all_rows)
    reservoir_witness = {
        "reservoir_delivered_gec": sum(
            c["reservoir_delivered_gec"]
            for c in spirit_cells + classic_cells if _is_admissible(c)
        ),
        "pickup_delivered_gec": sum(
            c["pickup_delivered_gec"]
            for c in spirit_cells + classic_cells if _is_admissible(c)
        ),
    }
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
    payload["reservoir_witness"] = reservoir_witness
    payload["reservoir_verdict"] = _reservoir_verdict(
        pooled_pos, pooled_never, pooled_pos["ordering_sign"],
    )
    payload["wet_window_witness"] = _wet_window_witness(all_rows)
    for key in ("cells", "pooled", "verdict", "reservoir_verdict",
                "reservoir_witness", "wet_window_witness"):
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
