#!/usr/bin/env python3
"""The campaign-manifest CLI vocabulary the noro_diag probes share.

Every manifest-mode probe declares the same three arguments —
``--manifest`` selecting the campaign JSON, ``--tier`` selecting the
tier inside it, and ``--index`` selecting a single run for Batch array
children — plus the same identifier/seed-list argparse types and the
same run-selection arithmetic.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any


def identifier(value: str) -> str:
    """argparse type: a plain tier/arm/run identifier."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError(f"invalid identifier: {value!r}")
    return value


def seed_list(value: str) -> list[int]:
    """argparse type: a comma-separated seed list."""
    try:
        return [int(v) for v in value.split(",") if v.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid --seeds list: {value!r}",
        ) from exc


def add_manifest_args(
    parser: argparse.ArgumentParser,
    *,
    required: bool = False,
    tier_type: Any = None,
    manifest_help: str | None = (
        "campaign manifest JSON (tier specs verbatim)"
    ),
    index_help: str | None = (
        "run only the tier's runs[index] (Batch array child / canary)"
    ),
) -> None:
    """Add the shared ``--manifest``/``--tier``/``--index`` arguments."""
    parser.add_argument(
        "--manifest", type=Path, required=required, default=None,
        help=manifest_help,
    )
    parser.add_argument(
        "--tier", type=tier_type, required=required, default=None,
        help="tier inside --manifest; required with --manifest",
    )
    parser.add_argument(
        "--index", type=int, default=None,
        help=index_help,
    )


def index_run(
    runs: list[tuple[str, dict[str, Any]]],
    index: int | None,
    tier: str,
) -> list[tuple[str, dict[str, Any]]]:
    """Slice a tier's generated runs to ``runs[index]`` (Batch child)."""
    if index is None:
        return runs
    if index >= len(runs):
        raise SystemExit(
            f"--index {index} outside tier {tier} ({len(runs)} runs)",
        )
    return [runs[index]]


def filter_runs_by_seeds(
    runs: list[tuple[str, dict[str, Any]]],
    seeds: list[int] | None,
) -> list[tuple[str, dict[str, Any]]]:
    """Keep the runs whose ``run.random_seed`` is in *seeds*."""
    if seeds is None:
        return runs
    wanted = set(seeds)
    return [
        pair for pair in runs
        if int(pair[1]["run"]["random_seed"]) in wanted
    ]
