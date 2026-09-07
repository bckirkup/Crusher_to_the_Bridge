"""How many of #37's voyages stayed below the VSP posting threshold, and where.

A9's per-point verdict says only that the posting frequency is out of band. It
does not say whether the cell is a mixture of quiet voyages and outbreaks -- the
mixture VSP actually observes -- or a cell of uniformly loud voyages. This reads
that shape off the committed merged artifact of
``docs/norovirus/admissible_region_37_v2.md``.

The conditional level among posting voyages is reported as a *ceiling*, not an
estimate: the artifact stores cells rather than per-run rows, so
``E[reported AR | posted] <= mean / P(posted)`` is the most the mean supports.
The matching lower bound, ``(mean - (1 - p) * threshold) / p``, is printed
alongside it and is normally zero, i.e. uninformative.

    python3 telemetry_buffer/observation_model/gate37_quiet_voyages.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from simulation_utils.paths import resolve_repo_path, validated_open
from telemetry_buffer.observation_model.score_anchors import A9_POSTING_THRESHOLD

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = Path(__file__).with_name("admissible_region_37_v2.json")

# A1's band, and the boundaries that separate "nothing happened" from it.
A1_BANDS: tuple[tuple[float, float], ...] = (
    (0.0, 0.01),
    (0.01, 0.05),
    (0.05, 0.10),
    (0.10, 0.22),
    (0.22, 1.01),
)


def _quartiles(values: Sequence[float]) -> list[float]:
    ordered = sorted(values)
    if not ordered:
        return []
    last = len(ordered) - 1
    return [
        round(ordered[round(fraction * last)], 4)
        for fraction in (0.0, 0.25, 0.5, 0.75, 1.0)
    ]


def voyage_days(points: Sequence[dict[str, Any]]) -> float:
    """Recover the voyage length the scorer used from A8's own definition."""
    for point in points:
        cell = point["cell"]
        rate = cell.get("reported_case_attack_rate_passenger")
        incidence = cell.get("A8_pax_incidence")
        if rate and incidence:
            return float(rate) / float(incidence) * 1e5
    raise SystemExit("no cell defines a voyage length; A8 was never scored")


def posting_totals(points: Sequence[dict[str, Any]]) -> tuple[int, int]:
    """Eligible voyages, and those that stayed under the posting threshold."""
    eligible = sum(point["cell"]["A9_eligible_runs"] for point in points)
    posted = sum(point["cell"]["A9_posted_eligible"] for point in points)
    return eligible, eligible - posted


def by_a1_band(points: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Quiet-voyage counts grouped by the point's ever-ill attack rate."""
    rows = []
    for low, high in A1_BANDS:
        chosen = [
            point for point in points
            if low <= point["cell"]["A1_ever_ill_passenger"] < high
        ]
        eligible, quiet = posting_totals(chosen) if chosen else (0, 0)
        rows.append(
            {
                "band": (low, high),
                "points": len(chosen),
                "eligible": eligible,
                "quiet": quiet,
            },
        )
    return rows


def conditional_levels(
    points: Sequence[dict[str, Any]],
    days: float,
    max_posting_fraction: float = 0.5,
) -> dict[str, Any]:
    """Bound the reported attack rate of posting voyages at the quieter points."""
    ceilings: list[float] = []
    floors: list[float] = []
    medians: list[float] = []
    infections: list[float] = []
    means: list[float] = []
    for point in points:
        cell = point["cell"]
        fraction = cell["A9_posted_eligible"] / cell["A9_eligible_runs"]
        if not 0.0 < fraction < max_posting_fraction:
            continue
        mean = cell["A8_pax_incidence"] * days / 1e5
        ceilings.append(mean / fraction)
        floors.append(
            max(0.0, (mean - (1.0 - fraction) * A9_POSTING_THRESHOLD) / fraction),
        )
        medians.append(cell["reported_case_attack_rate_passenger"])
        infections.append(cell["infection_attack_rate_passenger"])
        means.append(mean)
    return {
        "n_points": len(ceilings),
        "ceiling_quartiles": _quartiles(ceilings),
        "floor_quartiles": _quartiles(floors),
        "median_voyage_reported": _quartiles(medians),
        "median_voyage_infection": _quartiles(infections),
        "cell_mean_reported": _quartiles(means),
        "silent_median_points": sum(1 for value in medians if value == 0.0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    args = parser.parse_args()
    artifact = resolve_repo_path(str(REPO_ROOT), str(args.artifact))
    with validated_open(
        artifact, allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        points = json.load(handle)["points"]
    days = voyage_days(points)
    eligible, quiet = posting_totals(points)
    counts = sorted(point["cell"]["A9_posted_eligible"] for point in points)

    print(f"{len(points)} points, {eligible} eligible voyages, {days:.3f} voyage-days")
    print(f"below the {A9_POSTING_THRESHOLD} posting threshold: {quiet} ({quiet / eligible:.3%})")
    print(f"per-point postings, quartiles: {_quartiles(counts)}")
    print(f"points with at least one quiet voyage: {sum(1 for k in counts if k < max(counts))}")
    print(f"points posting on every voyage: {sum(1 for k in counts if k == max(counts))}")

    print("\nquiet voyages by the point's ever-ill attack rate:")
    for row in by_a1_band(points):
        low, high = row["band"]
        if not row["points"]:
            continue
        share = row["quiet"] / row["eligible"]
        print(
            f"  [{low:.2f}, {high:.2f}): {row['points']:3d} points, "
            f"{row['quiet']:6d}/{row['eligible']:6d} quiet ({share:.1%})",
        )

    levels = conditional_levels(points, days)
    print(f"\nat the {levels['n_points']} points posting on under half their voyages:")
    print(f"  median voyage reported AR:  {levels['median_voyage_reported']}")
    print(f"  median voyage infection AR: {levels['median_voyage_infection']}")
    print(f"  cell mean reported AR:      {levels['cell_mean_reported']}")
    print(f"  E[reported AR | posted] <=  {levels['ceiling_quartiles']}")
    print(f"  E[reported AR | posted] >=  {levels['floor_quartiles']}")
    print(
        "  points whose median voyage reports nothing: "
        f"{levels['silent_median_points']}",
    )
    ceiling = levels["ceiling_quartiles"][2]
    print(f"  median ceiling / threshold: {ceiling / A9_POSTING_THRESHOLD:.2f}x")


if __name__ == "__main__":
    main()
