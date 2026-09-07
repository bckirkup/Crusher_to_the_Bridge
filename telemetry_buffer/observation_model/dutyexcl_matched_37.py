"""What the regulated crew duty exclusion moved, voyage by matched voyage.

VSP's 2018 Operations Manual 4.4.1.1.1 requires a crew member meeting the AGE
case definition off duty -- food employees until 48 h symptom-free with
documented medical clearance -- where 4.4.2.1 only advises isolation of
passengers. ``SOP-VSP-CREW-01`` implements that as a standing operational rule
(``crew_duty_exclusion``), off by default, and this reads the two arms of a
matched campaign over the quiet corner of the #37 v2 box: the same twelve grid
indices, the same factor vectors, the same 1,440 seeds per point, in the same
order, differing only in whether the rule is on.

Because the seeds are common random numbers, every voyage has a partner, so the
comparison is a paired one: the transition table below counts voyages that
changed posting channel, and the interval on the difference is McNemar's exact
one over the discordant pairs. Nothing here is fitted. Compliance is 1.0 in the
intervention arm -- the enforced-regulation upper bound, declared in the ledger,
not an estimate of maritime compliance, which is null in the literature -- so
the measured effect is the most the rule can do at these coordinates, and a
smaller effect is what a graded-compliance arm would show.

    python3 -m telemetry_buffer.observation_model.dutyexcl_matched_37 \\
        --baseline <merged rows, exclusion off> \\
        --exclusion <merged rows, exclusion on> \\
        --out telemetry_buffer/observation_model/dutyexcl_matched_37_v1_analysis.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from scipy.stats import binomtest

from simulation_utils.paths import resolve_repo_path, validated_open
from telemetry_buffer.observation_model.gate37_lowposting import (
    exact_binomial_interval,
    posted,
    posting_channels,
    rate_summary,
)
from telemetry_buffer.observation_model.score_anchors import A9_POSTING_THRESHOLD

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = Path(__file__).with_name("dutyexcl_matched_37_v1_analysis.json")

# A9's target frequency, and the observed crew-channel share of the postings
# behind it: one of 208 public postings is crew-only, and MMWR's crew arm is
# 16 of 172 outbreaks, an upper bound because the two arms are not disjoint.
A9_TARGET = (0.0042, 0.0056)
OBSERVED_CREW_CHANNEL_SHARE = (0.0048, 0.093)

CHANNELS: tuple[str, ...] = ("quiet", "passenger_only", "crew_only", "both")

PAIRED_FIELDS: tuple[str, ...] = (
    "infection_attack_rate_passenger",
    "infection_attack_rate_crew",
    "A1_ever_ill_passenger",
    "ever_ill_attack_rate_crew",
    "reported_case_attack_rate_passenger",
    "reported_case_attack_rate_crew",
    "peak_prevalence",
)


def channel(row: dict[str, Any]) -> str:
    """Which complement carried the voyage, under the scorer's ``or`` rule."""
    pax = row["reported_case_attack_rate_passenger"] >= A9_POSTING_THRESHOLD
    crew = row["reported_case_attack_rate_crew"] >= A9_POSTING_THRESHOLD
    if pax and crew:
        return "both"
    if pax:
        return "passenger_only"
    if crew:
        return "crew_only"
    return "quiet"


def rows_by_seed(point: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """One point's retained voyages, keyed by the seed that produced them."""
    return {int(row["seed"]): row for row in point["runs"]}


def paired_points(
    baseline: Sequence[dict[str, Any]],
    exclusion: Sequence[dict[str, Any]],
) -> list[tuple[int, dict[int, dict[str, Any]], dict[int, dict[str, Any]]]]:
    """Match the two arms by grid index, refusing anything unpaired.

    A missing index or a seed set that differs breaks the common random
    numbers the whole comparison rests on, so it is an error rather than a
    smaller sample.
    """
    left = {int(point["point_index"]): point for point in baseline}
    right = {int(point["point_index"]): point for point in exclusion}
    if set(left) != set(right):
        raise ValueError(
            f"arms cover different grid indices: {sorted(set(left) ^ set(right))}",
        )
    pairs = []
    for index in sorted(left):
        base = rows_by_seed(left[index])
        arm = rows_by_seed(right[index])
        if set(base) != set(arm):
            raise ValueError(
                f"point {index} arms ran different seeds: "
                f"{len(set(base) ^ set(arm))} unmatched",
            )
        pairs.append((index, base, arm))
    return pairs


def transitions(
    base: dict[int, dict[str, Any]],
    arm: dict[int, dict[str, Any]],
) -> dict[str, int]:
    """Baseline channel to intervention channel, over the matched voyages."""
    counts: dict[str, int] = {}
    for seed, row in base.items():
        key = f"{channel(row)} -> {channel(arm[seed])}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def mcnemar(gained: int, lost: int) -> dict[str, Any]:
    """Exact two-sided test on the discordant matched pairs.

    ``gained`` posts only with the rule on, ``lost`` only with it off. With no
    discordant pairs there is nothing to test and the p-value is null rather
    than 1.0, which would read as a measured absence of effect.
    """
    discordant = gained + lost
    if discordant == 0:
        return {"gained": 0, "lost": 0, "discordant": 0, "p_value": None}
    result = binomtest(lost, discordant, 0.5)
    return {
        "gained": gained,
        "lost": lost,
        "discordant": discordant,
        "p_value": round(float(result.pvalue), 8),
    }


def discordance(
    base: dict[int, dict[str, Any]],
    arm: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """The posting rule's matched discordance, and McNemar's exact p."""
    gained = sum(1 for seed, row in base.items() if not posted(row) and posted(arm[seed]))
    lost = sum(1 for seed, row in base.items() if posted(row) and not posted(arm[seed]))
    return mcnemar(gained, lost)


def paired_deltas(
    base: dict[int, dict[str, Any]],
    arm: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Mean matched change in each principal output, and how many pairs moved."""
    deltas: dict[str, Any] = {}
    for field in PAIRED_FIELDS:
        diffs = [float(arm[seed][field]) - float(row[field]) for seed, row in base.items()]
        moved = sum(1 for diff in diffs if abs(diff) > 0.0)
        deltas[field] = {
            "mean_change": round(sum(diffs) / len(diffs), 8) if diffs else None,
            "changed_pairs": moved,
            "changed_fraction": round(moved / len(diffs), 6) if diffs else None,
        }
    return deltas


def arm_summary(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """One arm's posting frequency, channels, and reported-rate shape."""
    voyages = list(rows)
    n = len(voyages)
    k = sum(1 for row in voyages if posted(row))
    channels = posting_channels(voyages)
    return {
        "n_voyages": n,
        "posted": k,
        "posting_frequency": round(k / n, 6) if n else None,
        "posting_interval_95": exact_binomial_interval(k, n) if n else None,
        "channels": channels,
        "quiet": n - k,
        "crew_channel_share": (
            round((channels["crew_only"] + channels["both"]) / k, 6) if k else None
        ),
        "reported_passenger": rate_summary(voyages, "reported_case_attack_rate_passenger"),
        "reported_crew": rate_summary(voyages, "reported_case_attack_rate_crew"),
    }


def compare(
    index: int | None,
    base: dict[int, dict[str, Any]],
    arm: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """One matched cell (or the pool, with ``index`` null) in both arms."""
    return {
        "point_index": index,
        "baseline": arm_summary(base.values()),
        "exclusion": arm_summary(arm.values()),
        "discordance": discordance(base, arm),
        "transitions": transitions(base, arm),
        "paired_deltas": paired_deltas(base, arm),
    }


def pool(
    pairs: Sequence[tuple[int, dict[int, dict[str, Any]], dict[int, dict[str, Any]]]],
) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    """Pool the arms over points, re-keying voyages so seeds stay matched."""
    base: dict[int, dict[str, Any]] = {}
    arm: dict[int, dict[str, Any]] = {}
    for offset, (_index, left, right) in enumerate(pairs):
        for seed, row in left.items():
            base[offset * 10**7 + seed] = row
            arm[offset * 10**7 + seed] = right[seed]
    return base, arm


def analyse(
    baseline: Sequence[dict[str, Any]],
    exclusion: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """The matched read-out: per point, pooled, and against A9's target."""
    pairs = paired_points(baseline, exclusion)
    per_point = [compare(index, base, arm) for index, base, arm in pairs]
    pooled_base, pooled_arm = pool(pairs)
    pooled = compare(None, pooled_base, pooled_arm)
    return {
        "design": {
            "points": [index for index, _base, _arm in pairs],
            "voyages_per_point": [
                record["baseline"]["n_voyages"] for record in per_point
            ],
            "arms": {
                "baseline": "crew_duty_exclusion off",
                "exclusion": "crew_duty_exclusion on, compliance_fraction 1.0",
            },
        },
        "targets": {
            "A9_posting_frequency": list(A9_TARGET),
            "observed_crew_channel_share": list(OBSERVED_CREW_CHANNEL_SHARE),
        },
        "pooled": pooled,
        "per_point": per_point,
    }


def load_points(path: Path) -> list[dict[str, Any]]:
    """One merged gate artifact's points, refusing one without voyage rows."""
    resolved = resolve_repo_path(str(REPO_ROOT), str(path))
    with validated_open(
        resolved, allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        payload = json.load(handle)
    points = payload.get("points", [])
    if not points or "runs" not in points[0]:
        raise ValueError(
            f"{path} keeps no voyage rows; merge a --stream run, not a cell summary",
        )
    return points


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--exclusion", required=True)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    record = analyse(
        load_points(Path(args.baseline)),
        load_points(Path(args.exclusion)),
    )
    out = resolve_repo_path(str(REPO_ROOT), str(args.out))
    with validated_open(
        out, "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        json.dump(record, handle, indent=2)
    pooled = record["pooled"]
    print(
        f"baseline {pooled['baseline']['posted']}/{pooled['baseline']['n_voyages']} "
        f"-> exclusion {pooled['exclusion']['posted']}/"
        f"{pooled['exclusion']['n_voyages']}; "
        f"McNemar p={pooled['discordance']['p_value']}",
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
