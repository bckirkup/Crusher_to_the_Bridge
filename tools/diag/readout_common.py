#!/usr/bin/env python3
"""Shared readout machinery for the diagnostic tools.

Every noro_diag readout walks ``<root>/<tier>/*.zip`` run archives,
pulls JSON members out of them, derives a seed and a cell coordinate
from the run parameters, and reports rates with Wilson intervals. The
cell coordinate itself is campaign-specific (each readout keys on its
own design axes, so ``*_cell_key``/``*_cell_label`` stay in the owning
tool); this module carries the pieces that were byte-for-byte or
semantically identical across the tools.
"""

from __future__ import annotations

import gzip
import json
import math
import os
import sys
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ),
)

from simulation_utils.paths import resolve_child_path  # noqa: E402
from tools.diag.json_io import gz_json_load  # noqa: E402

# scipy.stats.norm.ppf(0.975): the 95% two-sided normal quantile the
# readouts use for their Wilson intervals.
Z95 = 1.959963984540054


def iter_tier_dirs(
    root: Path, tiers: list[str] | None = None,
) -> Iterator[Path]:
    """Yield ``<root>/<tier>`` directories in sorted order.

    *tiers* restricts the walk to the named tiers (an empty or missing
    list walks them all).
    """
    for tier_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if tiers and tier_dir.name not in tiers:
            continue
        yield tier_dir


def iter_tier_zips(
    root: Path, tiers: list[str] | None = None,
) -> Iterator[tuple[str, Path]]:
    """Yield ``(tier, zip_path)`` for every ``<root>/<tier>/*.zip``."""
    for tier_dir in iter_tier_dirs(root, tiers):
        for zip_path in sorted(tier_dir.glob("*.zip")):
            yield tier_dir.name, zip_path


def read_zip_member(zip_path: Path, member: str) -> bytes | None:
    """The raw bytes of one member of a run zip; None if unreadable."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            return zf.read(member)
    except (KeyError, zipfile.BadZipFile, OSError):
        return None


def load_zip_json(
    zip_path: Path, member: str, *, gunzipped: bool = False,
) -> dict | None:
    """``json.loads`` of one member of a run zip; None on any failure."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            blob = zf.read(member)
        if gunzipped:
            blob = gzip.decompress(blob)
        return json.loads(blob)
    except (KeyError, zipfile.BadZipFile, json.JSONDecodeError, OSError):
        return None


def write_run_zip(
    out_dir: Path | str,
    tier: str,
    run_id: str,
    anchor: dict[str, Any],
    members: dict[str, str | bytes],
) -> Path:
    """Write ``<out_dir>/<tier>/<run_id>.zip``.

    ``anchor`` is serialized as ``summary.json``; ``members`` maps extra
    member names to their already-serialized contents (``str`` or
    ``bytes``). Returns the zip path.
    """
    cell_dir = Path(resolve_child_path(str(out_dir), tier))
    cell_dir.mkdir(parents=True, exist_ok=True)
    zip_path = Path(resolve_child_path(str(cell_dir), f"{run_id}.zip"))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("summary.json", json.dumps(anchor))
        for member, blob in members.items():
            archive.writestr(member, blob)
    return zip_path


def load_arm_cells(
    directory: Path, tag: str | None = None,
) -> dict[int, dict[str, Any]]:
    """The per-seed cells one arm wrote, keyed by seed."""
    stem = "per_host_dose_challenge_" + (f"{tag}_" if tag else "")
    cells = {}
    for path in sorted(directory.glob(f"{stem}seed*.json.gz")):
        cell = gz_json_load(path)
        cells[int(cell["seed"])] = cell
    return cells


def seed_from_params(params: dict[str, Any]) -> int:
    """The ``parameters.seed`` convention: explicit seed field, -1 if unset."""
    return int(params.get("seed", -1))


def seed_from_run_id(params: dict[str, Any]) -> int:
    """The ``*_s<seed>`` run_id suffix convention."""
    return int(str(params.get("run_id", "")).rsplit("_s", 1)[-1])


def seed_from_cell(cell: dict[str, Any]) -> int:
    """The per-seed cell dump convention: ``meta.seed`` or top-level ``seed``."""
    return int(cell.get("meta", {}).get("seed", cell.get("seed", -1)))


def wilson_centered(
    k: int, n: int, z: float = Z95,
) -> tuple[float, float, float]:
    """Wilson score interval; ``(p, lo, hi)``, zeros when ``n <= 0``."""
    if n <= 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def wilson_interval(
    k: int, n: int, z: float = Z95,
) -> tuple[float, float]:
    """The ``(lo, hi)`` pair of :func:`wilson_centered`."""
    _p, low, high = wilson_centered(k, n, z)
    return (low, high)


def rate_summary(x: int, n: int, z: float = Z95) -> dict[str, float]:
    """A count's rate and Wilson bounds as a report row."""
    low, high = wilson_interval(x, n, z)
    return {
        "x": x, "n": n,
        "rate": x / n if n else 0.0,
        "lo": low, "hi": high,
    }


def rate_ci_str(x: int, n: int, z: float = Z95) -> str:
    """``x/n (pct% [lo,hi])``, or ``-`` when the cell has no runs."""
    if not n:
        return "-"
    lo, hi = wilson_interval(x, n, z)
    return f"{x}/{n} ({100 * x / n:.2f}% [{100 * lo:.2f},{100 * hi:.2f}])"
