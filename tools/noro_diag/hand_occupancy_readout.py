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
from tools.diag.readout_common import seed_from_cell  # noqa: E402
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


def _spirit_cell_paths(raw_dir: Path) -> list[Path]:
    return sorted((raw_dir / SPIRIT_TIER).glob("*.zip"))


def _classic_cell_paths(raw_dir: Path) -> list[Path]:
    return sorted((raw_dir / CLASSIC_CELL).glob("*.json.gz"))


def _load_cell(path: Path) -> dict[str, Any]:
    """One projected cell; the caller drops it before loading the next."""
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            payload = json.loads(
                gzip.decompress(
                    archive.read("growth_census.json.gz"),
                ).decode("utf-8"),
            )
    else:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
    return _project(payload)


def _seed_of(cell: dict[str, Any]) -> int:
    return seed_from_cell(cell)


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


def _sign(a: float | None, b: float | None) -> str | None:
    if a is None or b is None:
        return None
    if a > b:
        return "event_higher"
    if a < b:
        return "event_lower"
    return "equal"


class _Fold:
    """Streaming equivalent of the list-based helpers, one pass per row.

    Every aggregate the readout publishes is a count, a sum, a per-agent
    peak, or a mean/stdev over the *positive* loads -- so the only lists
    kept are positive log10 loads (~20% of rows), never the row dicts.
    The output shape is identical to the list-based helpers'.
    """

    def __init__(self) -> None:
        self.n_rows = 0
        self.end_rows = 0
        self.end_nonzero_logs: list[float] = []
        self.pos_logs: list[float] = []
        self.symp_rows = 0
        self.symp_pos_logs: list[float] = []
        self.event_rows = 0
        self.routine_rows = 0
        self.event_end_rows = 0
        self.routine_end_rows = 0
        self.symp_end_rows = 0
        self.post_event_pos_logs: list[float] = []
        self.event_end_pos_logs: list[float] = []
        self.routine_end_pos_logs: list[float] = []
        self.agent_peaks: dict[int, float] = {}
        self.at_target = 0
        self.underflowed = 0
        self.first_seen = 0
        self.continuous_path = 0
        self.wet_n = 0
        self.wet_open = 0
        self.wet_sum = 0.0
        self.prot_n = 0
        self.prot_sum = 0.0
        self.pos_prot_n = 0
        self.pos_prot_sum = 0.0
        self.pool_n = 0
        self.pool_sum = 0.0

    def add(self, row: dict[str, Any]) -> None:
        self.n_rows += 1
        end = row.get("load_end_epoch_gec")
        positive = end is not None and float(end) >= LIU_LOD_GEC
        self._add_end(row, end, positive)
        self._add_stool(row, end, positive)
        self._add_flags(row)
        self._add_factors(row, positive)

    def _add_end(
        self, row: dict[str, Any], end: Any, positive: bool,
    ) -> None:
        if end is not None:
            self.end_rows += 1
            if float(end) > 0.0:
                self.end_nonzero_logs.append(_log10_of(float(end)))
            if positive:
                self.pos_logs.append(_log10_of(float(end)))
            aid = int(row["agent_id"])
            if float(end) > self.agent_peaks.get(aid, 0.0):
                self.agent_peaks[aid] = float(end)
        if row.get("symptomatic"):
            self.symp_rows += 1
            if end is not None:
                self.symp_end_rows += 1
            if positive:
                self.symp_pos_logs.append(_log10_of(float(end)))

    def _add_stool(
        self, row: dict[str, Any], end: Any, positive: bool,
    ) -> None:
        if row.get("stool_event"):
            self.event_rows += 1
            post = row.get("load_post_replenish_gec")
            if post is not None and float(post) >= LIU_LOD_GEC:
                self.post_event_pos_logs.append(_log10_of(float(post)))
            if end is not None:
                self.event_end_rows += 1
            if positive:
                self.event_end_pos_logs.append(_log10_of(float(end)))
        elif row.get("stool_event") is False:
            self.routine_rows += 1
            if end is not None:
                self.routine_end_rows += 1
            if positive:
                self.routine_end_pos_logs.append(_log10_of(float(end)))

    def _add_flags(self, row: dict[str, Any]) -> None:
        if row.get("at_target"):
            self.at_target += 1
        if row.get("underflowed"):
            self.underflowed += 1
        if row.get("first_seen"):
            self.first_seen += 1
        if not row.get("event_path"):
            self.continuous_path += 1

    def _add_factors(self, row: dict[str, Any], positive: bool) -> None:
        factor = row.get("hand_wet_transfer")
        if factor is not None:
            self.wet_n += 1
            self.wet_sum += float(factor)
            if factor > 0.08:
                self.wet_open += 1
        protected = row.get("hand_protected_gec")
        if protected is not None:
            self.prot_n += 1
            self.prot_sum += float(protected)
            if positive:
                self.pos_prot_n += 1
                self.pos_prot_sum += float(protected)
        pool = row.get("hand_self_pool_gec")
        if pool is not None:
            self.pool_n += 1
            self.pool_sum += float(pool)

    def merge(self, other: "_Fold") -> None:
        """Fold another cell block's accumulator into this one."""
        self.n_rows += other.n_rows
        self.end_rows += other.end_rows
        self.end_nonzero_logs.extend(other.end_nonzero_logs)
        self.pos_logs.extend(other.pos_logs)
        self.symp_rows += other.symp_rows
        self.symp_pos_logs.extend(other.symp_pos_logs)
        self.event_rows += other.event_rows
        self.routine_rows += other.routine_rows
        self.event_end_rows += other.event_end_rows
        self.routine_end_rows += other.routine_end_rows
        self.symp_end_rows += other.symp_end_rows
        self.post_event_pos_logs.extend(other.post_event_pos_logs)
        self.event_end_pos_logs.extend(other.event_end_pos_logs)
        self.routine_end_pos_logs.extend(other.routine_end_pos_logs)
        for aid, peak in other.agent_peaks.items():
            if peak > self.agent_peaks.get(aid, 0.0):
                self.agent_peaks[aid] = peak
        self.at_target += other.at_target
        self.underflowed += other.underflowed
        self.first_seen += other.first_seen
        self.continuous_path += other.continuous_path
        self.wet_n += other.wet_n
        self.wet_open += other.wet_open
        self.wet_sum += other.wet_sum
        self.prot_n += other.prot_n
        self.prot_sum += other.prot_sum
        self.pos_prot_n += other.pos_prot_n
        self.pos_prot_sum += other.pos_prot_sum
        self.pool_n += other.pool_n
        self.pool_sum += other.pool_sum

    def _positivity(self, n: int, pos_logs: list[float]) -> dict[str, Any]:
        out: dict[str, Any] = {
            "samples": n,
            "positive_samples": len(pos_logs),
            "positive_share": len(pos_logs) / n if n else None,
        }
        if pos_logs:
            out["positive_mean_log10"] = statistics.fmean(pos_logs)
            out["positive_sd_log10"] = (
                statistics.stdev(pos_logs) if len(pos_logs) > 1 else 0.0
            )
            out["positive_mean_gec"] = 10.0 ** out["positive_mean_log10"]
        return out

    def positivity(self) -> dict[str, Any]:
        return self._positivity(self.end_rows, self.pos_logs)

    def positivity_symptomatic_only(self) -> dict[str, Any]:
        return self._positivity(self.symp_end_rows, self.symp_pos_logs)

    def never_positive(self) -> dict[str, Any]:
        peaks = self.agent_peaks
        if not peaks:
            return {"hosts": 0}
        never = sum(1 for load in peaks.values() if load < LIU_LOD_GEC)
        return {
            "hosts": len(peaks),
            "never_positive_hosts": never,
            "never_positive_share": never / len(peaks),
        }

    def ordering(self) -> dict[str, Any]:
        post_event = self._positivity(
            self.event_rows, self.post_event_pos_logs,
        )
        routine_end = self._positivity(
            self.routine_end_rows, self.routine_end_pos_logs,
        )
        event_end = self._positivity(
            self.event_end_rows, self.event_end_pos_logs,
        )
        return {
            "post_defecation": post_event,
            "routine_end": routine_end,
            "event_end": event_end,
            "event_rows": self.event_rows,
            "routine_rows": self.routine_rows,
            "model_ordering_post_vs_routine": _sign(
                post_event.get("positive_share"),
                routine_end.get("positive_share"),
            ),
            "model_ordering_end_vs_end": _sign(
                event_end.get("positive_share"),
                routine_end.get("positive_share"),
            ),
            "liu_ordering": "post_bathroom_lower",
        }

    def wet_window_witness(self) -> dict[str, Any]:
        return {
            "rows_with_factor": self.wet_n,
            "wet_window_open_rows": self.wet_open,
            "wet_window_open_share": (
                self.wet_open / self.wet_n if self.wet_n else None
            ),
            "mean_transfer_factor": (
                self.wet_sum / self.wet_n if self.wet_n else None
            ),
        }

    def carriage_witness(self) -> dict[str, Any]:
        return {
            "rows_with_protected": self.prot_n,
            "mean_protected_gec": (
                self.prot_sum / self.prot_n if self.prot_n else None
            ),
            "mean_protected_on_positive_gec": (
                self.pos_prot_sum / self.pos_prot_n
                if self.pos_prot_n else None
            ),
            "rows_with_pool": self.pool_n,
            "mean_self_pool_gec": (
                self.pool_sum / self.pool_n if self.pool_n else None
            ),
        }


def _fold_cell(cell: dict[str, Any], fold: _Fold) -> None:
    for row in cell["rows"]:
        if row.get("shedding"):
            fold.add(row)


def _cell_readout(
    paths: list[Path], expected_seeds: list[int],
) -> tuple[dict[str, Any], _Fold]:
    """One cell block: per-seed rows plus the pooled reading.

    Cells are parsed one at a time and dropped after their rows are
    folded -- the block's rows never coexist in memory.
    """
    fold = _Fold()
    seen: set[int] = set()
    void: list[int] = []
    admissible = 0
    reservoir_delivered = 0.0
    pickup_delivered = 0.0
    per_seed: list[dict[str, Any]] = []
    for path in paths:
        cell = _load_cell(path)
        seed = _seed_of(cell)
        seen.add(seed)
        if not _is_admissible(cell):
            void.append(seed)
            del cell
            continue
        admissible += 1
        reservoir_delivered += cell["reservoir_delivered_gec"]
        pickup_delivered += cell["pickup_delivered_gec"]
        shedding = _shedding_rows(cell)
        per_seed.append({
            "seed": seed,
            "shedding_rows": len(shedding),
            "positive_share": _positivity(
                _end_loads(shedding),
            ).get("positive_share"),
            "never_positive_share": (
                _never_positive(shedding).get("never_positive_share")
            ),
        })
        for row in shedding:
            fold.add(row)
        del cell
        del shedding
    missing = [s for s in expected_seeds if s not in seen]
    return {
        "cells_loaded": len(paths),
        "seeds_missing": missing,
        "void_seeds": void,
        "admissible_cells": admissible,
        "shedding_host_epoch_rows": fold.n_rows,
        "end_load_missing_rows": fold.n_rows - fold.end_rows,
        "positivity": fold.positivity(),
        "positivity_symptomatic_only": fold.positivity_symptomatic_only(),
        "never_positive": fold.never_positive(),
        "ordering": fold.ordering(),
        "reservoir_witness": {
            "reservoir_delivered_gec": reservoir_delivered,
            "pickup_delivered_gec": pickup_delivered,
        },
        "wet_window_witness": fold.wet_window_witness(),
        "carriage_witness": fold.carriage_witness(),
        "occupancy": {
            "at_target_rows": fold.at_target,
            "underflowed_rows": fold.underflowed,
            "first_seen_rows": fold.first_seen,
            "event_rows": fold.event_rows,
            "continuous_path_rows": fold.continuous_path,
        },
        "per_seed": per_seed,
    }, fold


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
    spirit, spirit_fold = _cell_readout(
        _spirit_cell_paths(args.raw_dir), IGNITED_SEEDS,
    )
    classic, classic_fold = _cell_readout(
        _classic_cell_paths(args.raw_dir), CLASSIC_SEEDS,
    )
    pooled_fold = _Fold()
    pooled_fold.merge(spirit_fold)
    pooled_fold.merge(classic_fold)
    pooled_pos = pooled_fold.positivity()
    pooled_pos["ordering_sign"] = pooled_fold.ordering()[
        "model_ordering_post_vs_routine"
    ]
    pooled_never = pooled_fold.never_positive()
    reservoir_witness = {
        "reservoir_delivered_gec": (
            spirit["reservoir_witness"]["reservoir_delivered_gec"]
            + classic["reservoir_witness"]["reservoir_delivered_gec"]
        ),
        "pickup_delivered_gec": (
            spirit["reservoir_witness"]["pickup_delivered_gec"]
            + classic["reservoir_witness"]["pickup_delivered_gec"]
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
            "shedding_host_epoch_rows": pooled_fold.n_rows,
            "positivity": pooled_pos,
            "never_positive": pooled_never,
            "ordering": pooled_fold.ordering(),
        },
        "end_load_spread_log10": spread(
            pooled_fold.end_nonzero_logs,
            quartiles=True,
        ),
    }
    verdict = _verdict(pooled_pos, pooled_never)
    payload["verdict"] = verdict
    payload["reservoir_witness"] = reservoir_witness
    payload["reservoir_verdict"] = _reservoir_verdict(
        pooled_pos, pooled_never, pooled_pos["ordering_sign"],
    )
    payload["wet_window_witness"] = pooled_fold.wet_window_witness()
    payload["carriage_witness"] = pooled_fold.carriage_witness()
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
