"""Shared plumbing for the telemetry_buffer observation-model readouts.

Each readout keeps its own statistics; the boilerplate that was copied
across them — the ``name=root`` arm parser, the repo-rooted writer, the
``--arm/--out/--markdown/--title/--vsp-era`` CLI shape and the
shared-seed pairing prologue every paired contrast begins with — lives
here so a new readout introduces none of it a second time.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from simulation_utils.paths import resolve_repo_path, validated_open
from telemetry_buffer.observation_model.posting_tail_sensitivity import (
    MIN_PAIRED_SEEDS,
    _by_seed,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_arm(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected name=path")
    name, _, path = value.partition("=")
    return name, Path(path)


def write_text(path: Path, text: str) -> None:
    resolved = Path(resolve_repo_path(str(REPO_ROOT), str(path)))
    with validated_open(
        str(resolved), "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        handle.write(text)


def paired_rows(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int] | None:
    """``(left, right, n_shared)`` aligned on shared seeds; None if unpaired."""
    left_by_seed = _by_seed(left_rows)
    right_by_seed = _by_seed(right_rows)
    if left_by_seed is None or right_by_seed is None:
        return None
    shared = sorted(set(left_by_seed) & set(right_by_seed))
    if len(shared) < MIN_PAIRED_SEEDS:
        return None
    left = [left_by_seed[seed] for seed in shared]
    right = [right_by_seed[seed] for seed in shared]
    return left, right, len(shared)


def run_readout_cli(
    *,
    collect_rows: Callable[[Path, str], list[dict[str, Any]]],
    build_report: Callable[[list[dict[str, Any]], str], dict[str, Any]],
    render_markdown: Callable[..., str],
    description: str | None,
    default_title: str,
    argv: list[str] | None = None,
) -> int:
    """The readout ``main`` shape: arms in, JSON report out, markdown rendered."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--arm", action="append", required=True, type=parse_arm,
                        help="name=results_root, repeatable")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--title", default=default_title)
    parser.add_argument("--vsp-era", default="pre", choices=("pre", "post"))
    args = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    for name, root in args.arm:
        found = collect_rows(root, name)
        if not found:
            parser.error(f"no run summaries found under {root}")
        rows.extend(found)
    report = build_report(rows, args.vsp_era)
    write_text(args.out, json.dumps(report, indent=1, sort_keys=True) + "\n")
    markdown = render_markdown(report, title=args.title)
    if args.markdown:
        write_text(args.markdown, markdown)
    print(markdown)
    return 0
