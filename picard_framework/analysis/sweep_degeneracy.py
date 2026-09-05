#!/usr/bin/env python3
"""Detect swept axes that never reached the model.

A campaign that sweeps an axis is only informative where the axis moves the
output. When two rungs produce bit-identical outputs at every shared seed, the
sweep has no resolution there: the rungs are replicates, not design points, and
a bracket read off them would be an artefact of the replication rather than a
measurement.

This is the design-time check the C1 reported-case bracket failed. Its ladder
``dose_adjustment`` 12.0-14.0 sat entirely inside the region where the
environmental-release term has already gone to zero, so 2,880 runs were 320
distinct runs repeated nine times, and the ladder could not be read either way.

Usage:
    python3 -m picard_framework.analysis.sweep_degeneracy <summary.csv> \
        --axis parameters.dose_adjustment \
        --outputs derived.infection_attack_rate_passenger \
        [--group parameters.platform_id --group parameters.surveillance] \
        [--replicate parameters.seed]

The CSV is the flattened campaign summary written by
``deploy/aws/aggregate_results.py``.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

DEFAULT_REPLICATE = "parameters.seed"


class SweepColumnError(ValueError):
    """A requested axis, output or grouping column is absent from the rows."""


def _require_columns(rows: Sequence[Mapping[str, Any]], columns: Iterable[str]) -> None:
    if not rows:
        raise SweepColumnError("no rows to check")
    present = set(rows[0])
    missing = [column for column in columns if column not in present]
    if missing:
        raise SweepColumnError(f"columns absent from the summary: {missing}")


def _cell_key(
    row: Mapping[str, Any],
    group: Sequence[str],
    replicate: str,
) -> tuple[Any, ...]:
    return tuple(row[column] for column in (*group, replicate))


def rung_outputs(
    rows: Sequence[Mapping[str, Any]],
    *,
    axis: str,
    outputs: Sequence[str],
    group: Sequence[str] = (),
    replicate: str = DEFAULT_REPLICATE,
) -> dict[Any, dict[tuple[Any, ...], tuple[str, ...]]]:
    """Output tuple of every (group, replicate) cell, per rung of ``axis``.

    Values are compared as their literal serialised text: two rungs are only
    called identical when the recorded outputs are the same characters, so a
    difference below the printed precision is treated as a difference rather
    than folded away by a tolerance.
    """
    _require_columns(rows, (axis, replicate, *outputs, *group))
    per_rung: dict[Any, dict[tuple[Any, ...], tuple[str, ...]]] = defaultdict(dict)
    for row in rows:
        cell = _cell_key(row, group, replicate)
        values = tuple(str(row[column]) for column in outputs)
        per_rung[row[axis]][cell] = values
    return dict(per_rung)


def degenerate_rung_groups(
    rows: Sequence[Mapping[str, Any]],
    *,
    axis: str,
    outputs: Sequence[str],
    group: Sequence[str] = (),
    replicate: str = DEFAULT_REPLICATE,
) -> list[list[Any]]:
    """Rungs of ``axis`` that are indistinguishable, as sorted groups.

    Two rungs join a group when they share at least one replicate cell and
    agree on every output in every cell they share. A group with more than one
    member is a stretch of the axis the model did not resolve.
    """
    per_rung = rung_outputs(
        rows, axis=axis, outputs=outputs, group=group, replicate=replicate,
    )
    rungs = sorted(per_rung, key=_sort_key)
    groups: list[list[Any]] = []
    for rung in rungs:
        for existing in groups:
            if _rungs_agree(per_rung[existing[0]], per_rung[rung]):
                existing.append(rung)
                break
        else:
            groups.append([rung])
    return [members for members in groups if len(members) > 1]


def _rungs_agree(
    left: Mapping[tuple[Any, ...], tuple[str, ...]],
    right: Mapping[tuple[Any, ...], tuple[str, ...]],
) -> bool:
    shared = set(left) & set(right)
    if not shared:
        return False
    return all(left[cell] == right[cell] for cell in shared)


def _sort_key(value: Any) -> tuple[int, float, str]:
    try:
        return (0, float(value), "")
    except (TypeError, ValueError):
        return (1, 0.0, str(value))


def resolved_fraction(
    rows: Sequence[Mapping[str, Any]],
    *,
    axis: str,
    outputs: Sequence[str],
    group: Sequence[str] = (),
    replicate: str = DEFAULT_REPLICATE,
) -> float:
    """Share of the axis's rungs that are distinguishable from every other.

    1.0 means every rung moved at least one output; 0.0 means the whole ladder
    collapsed onto one behaviour and carries no information about the axis.
    """
    per_rung = rung_outputs(
        rows, axis=axis, outputs=outputs, group=group, replicate=replicate,
    )
    degenerate = degenerate_rung_groups(
        rows, axis=axis, outputs=outputs, group=group, replicate=replicate,
    )
    collapsed = sum(len(members) for members in degenerate)
    distinct = len(per_rung) - collapsed + len(degenerate)
    return distinct / len(per_rung) if per_rung else 0.0


def format_report(
    rows: Sequence[Mapping[str, Any]],
    *,
    axis: str,
    outputs: Sequence[str],
    group: Sequence[str] = (),
    replicate: str = DEFAULT_REPLICATE,
) -> str:
    """Markdown report naming the collapsed stretches of the axis."""
    per_rung = rung_outputs(
        rows, axis=axis, outputs=outputs, group=group, replicate=replicate,
    )
    degenerate = degenerate_rung_groups(
        rows, axis=axis, outputs=outputs, group=group, replicate=replicate,
    )
    fraction = resolved_fraction(
        rows, axis=axis, outputs=outputs, group=group, replicate=replicate,
    )
    lines = [
        f"# Sweep resolution: `{axis}`",
        "",
        f"- rows: {len(rows)}",
        f"- rungs: {len(per_rung)}",
        f"- outputs compared: {', '.join(outputs)}",
        f"- grouped by: {', '.join(group) if group else '(none)'}",
        f"- replicate column: `{replicate}`",
        f"- resolved fraction: {fraction:.3f}",
        "",
    ]
    if not degenerate:
        lines.append("Every rung is distinguishable from every other rung.")
        return "\n".join(lines) + "\n"
    lines.append("## Collapsed rungs")
    lines.append("")
    lines.append(
        "Each group below produced identical outputs at every shared "
        "replicate, so the axis carries no information across it.",
    )
    lines.append("")
    for members in degenerate:
        rendered = ", ".join(str(member) for member in members)
        lines.append(f"- {rendered}")
    return "\n".join(lines) + "\n"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_csv", type=Path)
    parser.add_argument("--axis", required=True)
    parser.add_argument("--outputs", nargs="+", required=True)
    parser.add_argument("--group", action="append", default=[])
    parser.add_argument("--replicate", default=DEFAULT_REPLICATE)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--fail-on-degenerate",
        action="store_true",
        help="exit non-zero when any rung group collapsed",
    )
    args = parser.parse_args(argv)

    rows = load_rows(args.summary_csv)
    report = format_report(
        rows,
        axis=args.axis,
        outputs=args.outputs,
        group=tuple(args.group),
        replicate=args.replicate,
    )
    if args.out is not None:
        args.out.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)
    if args.fail_on_degenerate and degenerate_rung_groups(
        rows,
        axis=args.axis,
        outputs=args.outputs,
        group=tuple(args.group),
        replicate=args.replicate,
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
