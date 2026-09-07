"""The shape of one gate cell, read from its voyages rather than its summary.

``admissible_region_37_v2`` scored each of its 256 points on 180 voyages and
kept the cell. This reads a re-run of named grid indices that kept every
voyage's row (``--seed-shards`` streams pooled by ``--merge``), and reports the
empirical distributions directly: how often the point posts, how much of its
mass is exactly zero, and where the reported, ever-ill and infection attack
rates sit -- overall, among the voyages that stayed under the threshold, and
among the ones that posted.

Nothing here is fitted or selected. A posting frequency is a count over the
voyages that ran; its interval is the exact binomial one, so a point whose
count is zero is reported as an upper bound and not as "quiet".

    python3 -m telemetry_buffer.observation_model.gate37_lowposting \\
        --artifact telemetry_buffer/observation_model/gate37_lowposting_v1_merged.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from scipy.stats import beta

from simulation_utils.paths import resolve_repo_path, validated_open
from telemetry_buffer.observation_model.score_anchors import A9_POSTING_THRESHOLD

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = Path(__file__).with_name("gate37_lowposting_v1_merged.json")
REFERENCE_GATE = Path(__file__).with_name("admissible_region_37_v2.json")

# The grid indices the re-run selected, by why they were chosen from the
# 180-seed gate: the twelve quietest cells, two at the quiet/A1 transition,
# and two inside A1's band as comparators.
GROUPS: dict[str, tuple[int, ...]] = {
    "quietest": (46, 142, 12, 18, 126, 0, 20, 36, 145, 171, 172, 202),
    "transition": (102, 206),
    "a1_band": (243, 107),
}

QUANTILES: tuple[float, ...] = (0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0)
RATE_FIELDS: tuple[str, ...] = (
    "infection_attack_rate_passenger",
    "A1_ever_ill_passenger",
    "reported_case_attack_rate_passenger",
    "reported_case_attack_rate_crew",
)


def posted(row: dict[str, Any]) -> bool:
    """The scorer's posting rule: either complement reaches the threshold."""
    return (
        row["reported_case_attack_rate_passenger"] >= A9_POSTING_THRESHOLD
        or row["reported_case_attack_rate_crew"] >= A9_POSTING_THRESHOLD
    )


def posting_channels(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Which complement carried each posting: the rule is an ``or`` over two."""
    channels = {"passenger_only": 0, "crew_only": 0, "both": 0}
    for row in rows:
        pax = row["reported_case_attack_rate_passenger"] >= A9_POSTING_THRESHOLD
        crew = row["reported_case_attack_rate_crew"] >= A9_POSTING_THRESHOLD
        if pax and crew:
            channels["both"] += 1
        elif pax:
            channels["passenger_only"] += 1
        elif crew:
            channels["crew_only"] += 1
    return channels


def quantiles(values: Sequence[float]) -> list[float]:
    """Nearest-rank quantiles at ``QUANTILES``; ``[]`` for no values."""
    ordered = sorted(values)
    if not ordered:
        return []
    last = len(ordered) - 1
    return [round(ordered[round(q * last)], 5) for q in QUANTILES]


def exact_binomial_interval(k: int, n: int, level: float = 0.95) -> list[float]:
    """Clopper-Pearson bounds on a frequency observed as ``k`` of ``n``."""
    alpha = 1.0 - level
    low = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    high = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return [round(low, 6), round(high, 6)]


def voyage_classes(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Each voyage in exactly one class along infection -> illness -> report -> post."""
    counts = {
        "no_infection": 0,
        "infected_no_illness": 0,
        "ill_no_report": 0,
        "reported_below_threshold": 0,
        "posted": 0,
    }
    for row in rows:
        if posted(row):
            counts["posted"] += 1
        elif row["reported_case_attack_rate_passenger"] > 0.0:
            counts["reported_below_threshold"] += 1
        elif row["A1_ever_ill_passenger"] > 0.0:
            counts["ill_no_report"] += 1
        elif row["infection_attack_rate_passenger"] > 0.0:
            counts["infected_no_illness"] += 1
        else:
            counts["no_infection"] += 1
    return counts


def rate_summary(rows: Sequence[dict[str, Any]], field: str) -> dict[str, Any]:
    """Zero mass, quantiles, and the quantiles of the nonzero part of one rate."""
    values = [float(row[field]) for row in rows]
    nonzero = [value for value in values if value > 0.0]
    return {
        "zero_fraction": round(1.0 - len(nonzero) / len(values), 5) if values else None,
        "quantiles": quantiles(values),
        "nonzero_quantiles": quantiles(nonzero),
    }


def summarise_point(point: dict[str, Any]) -> dict[str, Any]:
    """One cell's empirical read-out from its retained voyages."""
    rows = point["runs"]
    n = len(rows)
    k = sum(1 for row in rows if posted(row))
    quiet = [row for row in rows if not posted(row)]
    loud = [row for row in rows if posted(row)]
    return {
        "point_index": point["point_index"],
        "n_voyages": n,
        "took_off": sum(1 for row in rows if row["took_off"]),
        "posted": k,
        "posting_frequency": round(k / n, 6) if n else None,
        "posting_interval_95": exact_binomial_interval(k, n) if n else None,
        "classes": voyage_classes(rows),
        "posting_channels": posting_channels(rows),
        "rates": {field: rate_summary(rows, field) for field in RATE_FIELDS},
        "quiet_reported_passenger": rate_summary(
            quiet, "reported_case_attack_rate_passenger",
        ),
        "posted_reported_passenger": rate_summary(
            loud, "reported_case_attack_rate_passenger",
        ),
        "posted_infection_passenger": rate_summary(
            loud, "infection_attack_rate_passenger",
        ),
    }


def summarise_group(
    name: str,
    summaries: Sequence[dict[str, Any]],
    points: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Pool a group's voyages, and keep the per-point posting counts beside them."""
    rows = [row for point in points for row in point["runs"]]
    n = len(rows)
    k = sum(1 for row in rows if posted(row))
    return {
        "group": name,
        "points": [summary["point_index"] for summary in summaries],
        "n_voyages": n,
        "posted": k,
        "posting_frequency": round(k / n, 6) if n else None,
        "posting_interval_95": exact_binomial_interval(k, n) if n else None,
        "per_point_posted": [summary["posted"] for summary in summaries],
        "classes": voyage_classes(rows),
        "posting_channels": posting_channels(rows),
        "rates": {field: rate_summary(rows, field) for field in RATE_FIELDS},
    }


def reference_counts(reference: Sequence[dict[str, Any]]) -> dict[int, int]:
    """The 180-seed gate's posting count per point, for the same grid indices."""
    return {
        int(point["point_index"]): int(point["cell"]["A9_posted_eligible"])
        for point in reference
    }


def analyse(
    points: Sequence[dict[str, Any]],
    reference: Sequence[dict[str, Any]] = (),
    groups: dict[str, tuple[int, ...]] | None = None,
) -> dict[str, Any]:
    """Per-point and per-group read-outs, as one JSON-serialisable record."""
    groups = GROUPS if groups is None else groups
    by_index = {int(point["point_index"]): point for point in points}
    summaries = {index: summarise_point(point) for index, point in by_index.items()}
    prior = reference_counts(reference)
    for index, summary in summaries.items():
        summary["gate_180_posted"] = prior.get(index)
    group_records = []
    for name, indices in groups.items():
        chosen = [index for index in indices if index in by_index]
        if not chosen:
            continue
        group_records.append(
            summarise_group(
                name,
                [summaries[index] for index in chosen],
                [by_index[index] for index in chosen],
            ),
        )
    return {
        "n_points": len(summaries),
        "n_voyages": sum(summary["n_voyages"] for summary in summaries.values()),
        "posting_threshold": A9_POSTING_THRESHOLD,
        "points": [summaries[index] for index in sorted(summaries)],
        "groups": group_records,
    }


def _point_lines(summary: dict[str, Any]) -> list[str]:
    low, high = summary["posting_interval_95"]
    reported = summary["rates"]["reported_case_attack_rate_passenger"]
    infection = summary["rates"]["infection_attack_rate_passenger"]
    ill = summary["rates"]["A1_ever_ill_passenger"]
    prior = summary["gate_180_posted"]
    prior_text = "" if prior is None else f" (180-seed gate: {prior}/180)"
    return [
        f"point {summary['point_index']:3d}: posted {summary['posted']}/"
        f"{summary['n_voyages']} = {summary['posting_frequency']:.4%} "
        f"[{low:.4%}, {high:.4%}]{prior_text}; took off "
        f"{summary['took_off']}/{summary['n_voyages']}",
        f"  classes: {summary['classes']}",
        f"  infection AR  q{list(QUANTILES)}: {infection['quantiles']}",
        f"  ever-ill AR   zero {ill['zero_fraction']:.3f}, "
        f"nonzero q: {ill['nonzero_quantiles']}",
        f"  reported AR   zero {reported['zero_fraction']:.3f}, "
        f"nonzero q: {reported['nonzero_quantiles']}",
        f"  reported AR | posted: "
        f"{summary['posted_reported_passenger']['quantiles']}",
    ]


def _group_lines(record: dict[str, Any]) -> list[str]:
    low, high = record["posting_interval_95"]
    return [
        "",
        f"group {record['group']} ({len(record['points'])} points, "
        f"{record['n_voyages']} voyages): posted {record['posted']} = "
        f"{record['posting_frequency']:.4%} [{low:.4%}, {high:.4%}]",
        f"  per-point posted: {record['per_point_posted']}",
        f"  classes: {record['classes']}",
        f"  channels: {record['posting_channels']}",
    ]


def report(analysis: dict[str, Any]) -> list[str]:
    """The read-out as lines, so the arithmetic is testable without stdout."""
    lines = [
        f"{analysis['n_points']} points, {analysis['n_voyages']} voyages, "
        f"posting threshold {analysis['posting_threshold']}",
    ]
    for summary in analysis["points"]:
        lines += _point_lines(summary)
    for record in analysis["groups"]:
        lines += _group_lines(record)
    return lines


def load_points(artifact: Path) -> list[dict[str, Any]]:
    """Read a merged gate artifact's point records from inside the repository."""
    resolved = resolve_repo_path(str(REPO_ROOT), str(artifact))
    with validated_open(
        resolved, allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        return json.load(handle)["points"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--reference", type=Path, default=REFERENCE_GATE)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Also write the analysis record here (inside the repository)",
    )
    args = parser.parse_args()
    reference = load_points(args.reference) if args.reference.exists() else []
    analysis = analyse(load_points(args.artifact), reference)
    for line in report(analysis):
        print(line)
    if args.json_out is not None:
        target = resolve_repo_path(str(REPO_ROOT), str(args.json_out))
        with validated_open(
            target, "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
        ) as handle:
            json.dump(analysis, handle, indent=2)


if __name__ == "__main__":
    main()
