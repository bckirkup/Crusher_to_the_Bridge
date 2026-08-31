"""Per-class, per-era VSP scoring targets: attack rates and posting incidence.

``score_anchors.py`` carries four hard-coded ``VSP_TARGETS`` class quantile
triples with no recorded provenance and no era split.  This module recomputes
them from ``vsp_outbreak_series.csv`` -- the per-outbreak table extracted from
CDC-hosted pages, whose extraction is documented in
``vsp_outbreak_series_extraction_log.md`` -- separately for the pre-2020 and
post-2020 arms, so that a hull can be scored against the health-practice era it
is configured to represent rather than against a pooled distribution that
straddles the break.

Two quantities per class per era:

``attack rate``
    Distribution of ``reported passengers ill / passengers aboard`` over posted
    outbreaks.  Conditional on VSP posting the voyage.  This is what A4 scores.

``posting incidence``
    Postings per class-year.  This is *not* a per-voyage rate: VSP publishes no
    voyage denominator, so the denominator here is calendar years covered by the
    arm, not voyages sailed.  A per-voyage incidence needs an external
    denominator (fleet size and voyages per ship-year by capacity band) which is
    not in this repository.  Reported so the takeoff channel is visible and so
    the missing denominator is explicit rather than silently absent.

Usage:
    python3 telemetry_buffer/observation_model/vsp_class_era_scoring.py
"""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, NamedTuple

from simulation_utils.paths import resolve_repo_path, validated_open

SERIES = Path(__file__).with_name("vsp_outbreak_series.csv")
REPO_ROOT = Path(__file__).resolve().parents[2]

# Nominal passenger complement of each scored hull, from the platform ids.
HULL_CAPACITY: dict[str, int] = {
    "expedition_cruise_450": 450,
    "classic_cruise_1900": 1900,
    "spirit_cruise_3000": 3000,
    "mega_cruise_5000": 5000,
}

# Capacity band edges assigning a posted outbreak to the hull whose complement
# it most nearly matches.  Edges are the geometric means of adjacent nominal
# complements, so the assignment is scale-symmetric rather than favouring the
# larger class: sqrt(450*1900)=925, sqrt(1900*3000)=2387, sqrt(3000*5000)=3873.
BAND_EDGES: list[tuple[float, str]] = [
    (925.0, "expedition_cruise_450"),
    (2387.0, "classic_cruise_1900"),
    (3873.0, "spirit_cruise_3000"),
    (float("inf"), "mega_cruise_5000"),
]

# Eras present in the series, in chronological order.  ``shutdown`` (2020-2021)
# is reported but never scored and never pooled into either arm: cruising was
# suspended under the CDC No Sail Order and then the Framework for Conditional
# Sailing, so those years carry almost no voyages and would dilute any rate
# computed over them.  ``legacy_pre2004`` is reported as context -- it precedes
# both the 2005 VSP construction guidelines and ATP-era cleaning practice, so it
# is a third health-practice regime rather than more of the pre arm.
ERAS: tuple[str, ...] = ("legacy_pre2004", "pre", "shutdown", "post")
SCORED_ERAS: tuple[str, ...] = ("pre", "post")


class Posting(NamedTuple):
    year: int
    era: str
    hull: str
    pax_total: int
    pax_rate: float
    crew_rate: float | None


def _capacity_band(pax_total: float) -> str:
    for edge, hull in BAND_EDGES:
        if pax_total < edge:
            return hull
    raise AssertionError("unreachable: last edge is infinite")


def load_postings(path: Path = SERIES) -> list[Posting]:
    """Postings with a usable passenger denominator and rate."""
    out: list[Posting] = []
    safe_path = resolve_repo_path(str(SERIES.parent), str(path))
    with validated_open(
        safe_path,
        "r",
        allowed_roots=(str(SERIES.parent),),
        encoding="utf-8",
        newline="",
    ) as handle:
        for row in csv.DictReader(handle):
            pax_total = row["pax_total"].strip()
            pax_ill = row["pax_ill"].strip()
            if not pax_total or not pax_ill:
                continue
            total = int(float(pax_total))
            if total <= 0:
                continue
            crew_ill = row["crew_ill"].strip()
            crew_total = row["crew_total"].strip()
            crew_rate = None
            if crew_ill and crew_total and float(crew_total) > 0:
                crew_rate = float(crew_ill) / float(crew_total)
            out.append(
                Posting(
                    year=int(row["year"]),
                    era=row["era"].strip(),
                    hull=_capacity_band(total),
                    pax_total=total,
                    pax_rate=float(pax_ill) / total,
                    crew_rate=crew_rate,
                ),
            )
    return out


def quantiles(values: list[float]) -> dict[str, float] | None:
    """Median and quartiles, by the same linear interpolation numpy uses."""
    if len(values) < 4:
        return None
    ordered = sorted(values)

    def at(fraction: float) -> float:
        position = fraction * (len(ordered) - 1)
        low = int(position)
        high = min(low + 1, len(ordered) - 1)
        weight = position - low
        return ordered[low] * (1.0 - weight) + ordered[high] * weight

    return {
        "q1": at(0.25),
        "median": at(0.50),
        "q3": at(0.75),
        "min": ordered[0],
        "max": ordered[-1],
        "mean": statistics.fmean(ordered),
    }


def targets_by_class_era(postings: list[Posting]) -> dict[tuple[str, str], Any]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for posting in postings:
        grouped[(posting.hull, posting.era)].append(posting.pax_rate)
    return {
        key: {"n": len(values), **(quantiles(values) or {})}
        for key, values in sorted(grouped.items())
    }


MIN_POSTINGS_FOR_TARGET = 10


def vsp_attack_rate_targets(
    era: str = "pre",
    series: Path = SERIES,
) -> dict[str, dict[str, float] | None]:
    """A4 quantile targets per hull for one era, or ``None`` where too thin.

    ``mega_cruise_5000`` carries 4 pre-2020 and 3 post-2020 postings, so it has
    no usable A4 anchor and returns ``None`` rather than a quantile triple read
    off four points; ``MIN_POSTINGS_FOR_TARGET`` is that floor.
    """
    if era not in ERAS:
        raise ValueError(f"unknown era {era!r}; expected one of {ERAS}")
    rates = targets_by_class_era(load_postings(series))
    out: dict[str, dict[str, float] | None] = {}
    for hull in HULL_CAPACITY:
        cell = rates.get((hull, era))
        if cell is None or cell["n"] < MIN_POSTINGS_FOR_TARGET:
            out[hull] = None
            continue
        out[hull] = {
            "q1": cell["q1"],
            "median": cell["median"],
            "q3": cell["q3"],
            "n": float(cell["n"]),
        }
    return out


def era_year_spans(postings: list[Posting]) -> dict[str, int]:
    """Calendar years covered by each era, taken from the series itself.

    Read from the data rather than hard-coded so that re-extracting the series
    forward in time cannot leave a stale denominator behind.
    """
    years: dict[str, set[int]] = defaultdict(set)
    for posting in postings:
        years[posting.era].add(posting.year)
    return {era: max(seen) - min(seen) + 1 for era, seen in years.items()}


def incidence_by_class_era(postings: list[Posting]) -> dict[tuple[str, str], Any]:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for posting in postings:
        counts[(posting.hull, posting.era)] += 1
    spans = era_year_spans(postings)
    out: dict[tuple[str, str], Any] = {}
    for (hull, era), count in sorted(counts.items()):
        years = spans[era]
        out[(hull, era)] = {
            "postings": count,
            "years": years,
            "postings_per_year": count / years,
        }
    return out


def _fmt(value: float | None, places: int = 4) -> str:
    return "n/a" if value is None else f"{value:.{places}f}"


def _validated_cli_path(path: Path, root: Path) -> Path:
    """Resolve a CLI path under a fixed root before filesystem access."""
    return Path(resolve_repo_path(str(root), str(path)))


def render(postings: list[Posting]) -> str:
    rates = targets_by_class_era(postings)
    incidence = incidence_by_class_era(postings)
    lines = [
        "# VSP posted-outbreak targets by hull class and era",
        "",
        f"Source: `vsp_outbreak_series.csv`, {len(postings)} postings with a "
        "passenger denominator.",
        "All rates are conditional on VSP posting the voyage.",
        "",
        "## Reported passenger attack rate among posted outbreaks",
        "",
        "| hull | era | n | q1 | median | q3 | max |",
        "|---|---|---|---|---|---|---|",
    ]
    for hull in HULL_CAPACITY:
        for era in ERAS:
            row = rates.get((hull, era))
            if not row:
                continue
            lines.append(
                f"| {hull} | {era} | {row['n']} | {_fmt(row.get('q1'))} | "
                f"{_fmt(row.get('median'))} | {_fmt(row.get('q3'))} | "
                f"{_fmt(row.get('max'))} |",
            )
    lines += [
        "",
        "## Posting count per class-year (NOT a per-voyage rate)",
        "",
        "The denominator is calendar years in the era, not voyages sailed. "
        "`shutdown` (2020-2021) is never pooled into either scored arm.",
        "A per-voyage incidence requires an external fleet-size and "
        "voyages-per-ship-year denominator that is not in this repository.",
        "",
        "| hull | era | postings | years | postings/year |",
        "|---|---|---|---|---|",
    ]
    for hull in HULL_CAPACITY:
        for era in ERAS:
            row = incidence.get((hull, era))
            if not row:
                continue
            lines.append(
                f"| {hull} | {era} | {row['postings']} | {row['years']} | "
                f"{row['postings_per_year']:.2f} |",
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--series", type=Path, default=SERIES)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    series_path = _validated_cli_path(args.series, SERIES.parent)
    text = render(load_postings(series_path))
    if args.out:
        output_path = _validated_cli_path(args.out, REPO_ROOT)
        with validated_open(
            str(output_path),
            "w",
            allowed_roots=(str(REPO_ROOT),),
            encoding="utf-8",
        ) as handle:
            handle.write(text)
    print(text)


if __name__ == "__main__":
    main()
