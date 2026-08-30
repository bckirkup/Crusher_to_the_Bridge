"""Measure the COVID discontinuity in the VSP posted-outbreak series.

Computes the statistics fixed in ``vsp_covid_discontinuity_design.md`` — A7a
(passenger attack-rate shift), A7b (crew shift), A7c (the difference-in-
differences, primary), A7d (upper-tail shift) and the reported-but-never-scored
A7e — over ``vsp_outbreak_series.csv``.

Every statistic is conditional on posting, because VSP publishes no voyage
denominator. Intervals are percentile bootstrap over posted outbreaks,
resampling whole rows so that a voyage's passenger and crew rates stay paired.
Era labels are permuted for the p-values, which is the same null as the
bootstrap but stated the way the surveillance literature states it.

Nothing here fits anything. Usage:

    python3 vsp_discontinuity_analysis.py [--series PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

BOOTSTRAP_REPLICATES = 10000
PERMUTATION_REPLICATES = 10000
SEED = 20260830

# A7d's tail threshold. The 3% posting floor truncates from below, so mass
# above this level is a statement about distribution shape that the floor
# cannot manufacture. 15% is where the operator figure's pre-era tail runs out
# of post-era counterpart; it is a reporting choice, not a fitted one, and the
# sweep below reports neighbouring thresholds so it cannot be cherry-picked.
TAIL_THRESHOLD_PCT = 15.0
TAIL_SWEEP_PCT = (10.0, 12.5, 15.0, 20.0)


# Fleet composition is the live alternative explanation for any era contrast:
# the post-era postings include small expedition vessels whose crew denominator
# is a few hundred, where two cases move the crew rate by a point. Restricting
# to ships this size or larger holds the composition roughly fixed.
LARGE_SHIP_MIN_PAX = 1000


@dataclass(frozen=True)
class Outbreak:
    """One posted outbreak. Rates are percentages as published by VSP."""

    year: int
    era: str
    agent: str
    pax_rate: float
    crew_rate: float | None
    pax_total: int = 0


def _rate(ill: str, total: str) -> float | None:
    if not ill.strip() or not total.strip():
        return None
    denominator = float(total)
    if denominator <= 0.0:
        return None
    return 100.0 * float(ill) / denominator


def load_series(path: Path) -> list[Outbreak]:
    """Read the extracted series, keeping only rows with a passenger rate.

    Rates are recomputed from the counts rather than read from the page's
    printed percentage: the extraction has already checked the two agree, and
    the counts carry more digits.
    """
    outbreaks: list[Outbreak] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            pax = _rate(row["pax_ill"], row["pax_total"])
            if pax is None:
                continue
            outbreaks.append(
                Outbreak(
                    year=int(row["year"]),
                    era=row["era"].strip(),
                    agent=row["causative_agent"].strip().lower(),
                    pax_rate=pax,
                    crew_rate=_rate(row["crew_ill"], row["crew_total"]),
                    pax_total=int(float(row["pax_total"])),
                )
            )
    return outbreaks


def _median_pax(sample: list[Outbreak]) -> float | None:
    rates = [o.pax_rate for o in sample]
    return statistics.median(rates) if rates else None


def _median_crew(sample: list[Outbreak]) -> float | None:
    rates = [o.crew_rate for o in sample if o.crew_rate is not None]
    return statistics.median(rates) if rates else None


def _tail_share(sample: list[Outbreak], threshold: float) -> float | None:
    if not sample:
        return None
    return sum(1 for o in sample if o.pax_rate >= threshold) / len(sample)


def _ratio(post: float | None, pre: float | None) -> float | None:
    if post is None or pre is None or pre == 0.0:
        return None
    return post / pre


def _a6c(pre: list[Outbreak], post: list[Outbreak]) -> float | None:
    """Difference-in-differences: the passenger-specific component."""
    pax = _ratio(_median_pax(post), _median_pax(pre))
    crew = _ratio(_median_crew(post), _median_crew(pre))
    if pax is None or crew is None or crew == 0.0:
        return None
    return pax / crew


Statistic = Callable[[list["Outbreak"], list["Outbreak"]], float | None]

STATISTICS: dict[str, Statistic] = {
    "A7a_pax_median_ratio": lambda pre, post: _ratio(
        _median_pax(post), _median_pax(pre)
    ),
    "A7b_crew_median_ratio": lambda pre, post: _ratio(
        _median_crew(post), _median_crew(pre)
    ),
    "A7c_did_pax_over_crew": _a6c,
}

# A7d is deliberately absent from STATISTICS. The percentile bootstrap cannot
# represent the uncertainty of a zero count: with no post-era outbreak above
# 15%, every resample gives a tail share of 0 and the interval collapses to
# [0, 0], which excludes 1 and would read as a decisive tail collapse on
# evidence of nothing at all (tests/test_vsp_discontinuity_analysis.py). The
# tail is therefore reported as counts with exact intervals and an exact test.

Z_975 = 1.959963984540054


def wilson_interval(successes: int, trials: int) -> tuple[float, float] | None:
    """95% score interval for a proportion, valid at zero and at one."""
    if trials <= 0:
        return None
    z2 = Z_975 * Z_975
    phat = successes / trials
    denominator = 1.0 + z2 / trials
    centre = (phat + z2 / (2.0 * trials)) / denominator
    half = (
        Z_975
        * math.sqrt(phat * (1.0 - phat) / trials + z2 / (4.0 * trials * trials))
        / denominator
    )
    return max(0.0, centre - half), min(1.0, centre + half)


def _hypergeometric_pmf(a: int, row1: int, row2: int, col1: int) -> float:
    """P(top-left cell = a) in a 2x2 table with the margins held fixed."""
    total = row1 + row2
    return (
        math.comb(row1, a)
        * math.comb(row2, col1 - a)
        / math.comb(total, col1)
    )


def fisher_exact_p(pre_tail: int, pre_n: int, post_tail: int, post_n: int) -> float:
    """Two-sided Fisher exact p for a tail count differing between the eras.

    Exact rather than bootstrap or chi-square because the post-era tail count
    is single digits and may be zero.
    """
    row1, row2 = pre_n, post_n
    col1 = pre_tail + post_tail
    observed = _hypergeometric_pmf(pre_tail, row1, row2, col1)
    low = max(0, col1 - row2)
    high = min(row1, col1)
    tail = 0.0
    for a in range(low, high + 1):
        probability = _hypergeometric_pmf(a, row1, row2, col1)
        if probability <= observed * (1.0 + 1e-9):
            tail += probability
    return min(1.0, tail)


def _tail_rows(pre: list[Outbreak], post: list[Outbreak]) -> list[str]:
    lines = [
        "| threshold | pre share (95% Wilson) | post share (95% Wilson) "
        "| ratio | Fisher exact p |",
        "|---|---|---|---:|---:|",
    ]
    for threshold in TAIL_SWEEP_PCT:
        pre_tail = sum(1 for o in pre if o.pax_rate >= threshold)
        post_tail = sum(1 for o in post if o.pax_rate >= threshold)
        pre_ci = wilson_interval(pre_tail, len(pre))
        post_ci = wilson_interval(post_tail, len(post))
        if pre_ci is None or post_ci is None:
            continue
        ratio = _ratio(post_tail / len(post), pre_tail / len(pre))
        ratio_text = f"{ratio:.3f}" if ratio is not None else "undefined"
        lines.append(
            f"| >={threshold:g}% "
            f"| {pre_tail}/{len(pre)} = {pre_tail / len(pre):.3f} "
            f"({pre_ci[0]:.3f}-{pre_ci[1]:.3f}) "
            f"| {post_tail}/{len(post)} = {post_tail / len(post):.3f} "
            f"({post_ci[0]:.3f}-{post_ci[1]:.3f}) "
            f"| {ratio_text} "
            f"| {fisher_exact_p(pre_tail, len(pre), post_tail, len(post)):.4f} |"
        )
    return lines


def _resample(sample: list[Outbreak], rng: random.Random) -> list[Outbreak]:
    return [sample[rng.randrange(len(sample))] for _ in range(len(sample))]


def bootstrap_interval(
    statistic: Statistic,
    pre: list[Outbreak],
    post: list[Outbreak],
    rng: random.Random,
) -> tuple[float, float] | None:
    """Percentile interval, resampling whole outbreaks within each era."""
    if not pre or not post:
        return None
    draws: list[float] = []
    for _ in range(BOOTSTRAP_REPLICATES):
        value = statistic(_resample(pre, rng), _resample(post, rng))
        if value is not None:
            draws.append(value)
    if len(draws) < BOOTSTRAP_REPLICATES // 2:
        return None
    draws.sort()
    low = draws[int(0.025 * (len(draws) - 1))]
    high = draws[int(0.975 * (len(draws) - 1))]
    return low, high


def permutation_p(
    statistic: Statistic,
    pre: list[Outbreak],
    post: list[Outbreak],
    rng: random.Random,
) -> float | None:
    """Two-sided p against the null that the era label carries no information.

    The null statistic is 1.0 for every ratio here, so the test is on
    ``|log(value)|`` and is undefined where either arm gives a non-positive
    value.
    """
    if not pre or not post:
        return None
    observed = statistic(pre, post)
    if observed is None or observed <= 0.0:
        return None
    pooled = pre + post
    split = len(pre)
    extreme = 0
    total = 0
    for _ in range(PERMUTATION_REPLICATES):
        rng.shuffle(pooled)
        value = statistic(pooled[:split], pooled[split:])
        if value is None or value <= 0.0:
            continue
        total += 1
        if abs(math.log(value)) >= abs(math.log(observed)):
            extreme += 1
    if total == 0:
        return None
    return (extreme + 1) / (total + 1)


def _describe_arm(name: str, sample: list[Outbreak]) -> list[str]:
    if not sample:
        return [f"- **{name}**: no posted outbreaks with passenger counts."]
    crew = [o for o in sample if o.crew_rate is not None]
    lines = [
        f"- **{name}**: n={len(sample)} posted outbreaks, "
        f"{len(crew)} with crew counts "
        f"({100.0 * len(crew) / len(sample):.0f}%)."
    ]
    lines.append(
        "  Median passengers onboard "
        f"{statistics.median(o.pax_total for o in sample):.0f}, "
        f"{sum(1 for o in sample if o.pax_total >= LARGE_SHIP_MIN_PAX)} of "
        f"{len(sample)} carrying {LARGE_SHIP_MIN_PAX}+."
    )
    median_pax = _median_pax(sample)
    median_crew = _median_crew(sample)
    if median_pax is not None:
        lines.append(
            f"  Median passenger attack rate {median_pax:.2f}%, "
            f"mean {statistics.fmean(o.pax_rate for o in sample):.2f}%, "
            f"max {max(o.pax_rate for o in sample):.2f}%."
        )
    if median_crew is not None:
        lines.append(f"  Median crew attack rate {median_crew:.2f}%.")
    for threshold in TAIL_SWEEP_PCT:
        share = _tail_share(sample, threshold)
        if share is not None:
            lines.append(
                f"  Share at or above {threshold:g}%: {share:.3f} "
                f"({round(share * len(sample))} of {len(sample)})."
            )
    return lines


def _format_statistic(
    key: str,
    value: float | None,
    interval: tuple[float, float] | None,
    p_value: float | None,
) -> str:
    if value is None:
        return f"| {key} | undefined | | |"
    span = f"{interval[0]:.3f}-{interval[1]:.3f}" if interval else "n/a"
    p_text = f"{p_value:.4f}" if p_value is not None else "n/a"
    return f"| {key} | {value:.3f} | {span} | {p_text} |"


def _yearly_counts(outbreaks: list[Outbreak]) -> list[str]:
    lines = [
        "| year | postings | norovirus | norovirus fraction |",
        "|---|---:|---:|---:|",
    ]
    years = sorted({o.year for o in outbreaks})
    for year in years:
        rows = [o for o in outbreaks if o.year == year]
        noro = [o for o in rows if o.agent == "norovirus"]
        fraction = len(noro) / len(rows) if rows else 0.0
        lines.append(f"| {year} | {len(rows)} | {len(noro)} | {fraction:.2f} |")
    return lines


def _analyse_arms(
    pre: list[Outbreak],
    post: list[Outbreak],
    label: str,
) -> list[str]:
    rng = random.Random(SEED)
    lines = [f"### {label}", ""]
    lines.extend(_describe_arm("pre (voyages ending 2004-2019)", pre))
    lines.extend(_describe_arm("post (voyages ending 2022 onward)", post))
    lines.extend(
        [
            "",
            "| statistic | post/pre | 95% bootstrap | permutation p |",
            "|---|---:|---|---:|",
        ]
    )
    for key, statistic in STATISTICS.items():
        lines.append(
            _format_statistic(
                key,
                statistic(pre, post),
                bootstrap_interval(statistic, pre, post, rng),
                permutation_p(statistic, pre, post, rng),
            )
        )
    lines.extend(
        [
            "",
            "A7d, the upper tail of the passenger attack-rate distribution. "
            "Reported as counts with exact intervals, because the post-era "
            "tail is single digits: a percentile bootstrap on a zero count "
            "collapses to [0, 0] and would falsely exclude 1.",
            "",
        ]
    )
    if pre and post:
        lines.extend(_tail_rows(pre, post))
    lines.append("")
    return lines


def build_report(outbreaks: list[Outbreak]) -> str:
    pre = [o for o in outbreaks if o.era == "pre"]
    post = [o for o in outbreaks if o.era == "post"]
    lines = [
        "# VSP COVID discontinuity: measured",
        "",
        "Generated by `vsp_discontinuity_analysis.py` over "
        "`vsp_outbreak_series.csv`. Statistics and their justification are "
        "fixed in `vsp_covid_discontinuity_design.md`. Every statistic is "
        "conditional on VSP posting a voyage; nothing here is per voyage or "
        "per year, because VSP publishes no voyage denominator.",
        "",
        f"Bootstrap {BOOTSTRAP_REPLICATES} replicates, permutation "
        f"{PERMUTATION_REPLICATES} replicates, seed {SEED}. A7d threshold "
        f"{TAIL_THRESHOLD_PCT:g}%.",
        "",
    ]
    lines.extend(_analyse_arms(pre, post, "All posted outbreaks"))
    lines.extend(
        _analyse_arms(
            [o for o in pre if o.agent == "norovirus"],
            [o for o in post if o.agent == "norovirus"],
            "Norovirus-confirmed postings only",
        )
    )
    lines.extend(
        _analyse_arms(
            [o for o in pre if o.pax_total >= LARGE_SHIP_MIN_PAX],
            [o for o in post if o.pax_total >= LARGE_SHIP_MIN_PAX],
            f"Ships carrying {LARGE_SHIP_MIN_PAX}+ passengers "
            "(fleet-composition control)",
        )
    )
    lines.extend(
        [
            "### A7e, reported and never scored",
            "",
            "Postings per year have no voyage denominator, and the norovirus "
            "fraction moves with laboratory ascertainment. Both are recorded "
            "so a change in them is visible, and neither is a target.",
            "",
        ]
    )
    lines.extend(_yearly_counts(outbreaks))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--series", type=Path, default=here / "vsp_outbreak_series.csv")
    parser.add_argument(
        "--out",
        type=Path,
        default=here / "vsp_covid_discontinuity_findings.md",
    )
    args = parser.parse_args()
    report = build_report(load_series(args.series))
    args.out.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
