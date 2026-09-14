"""Posting is a tail probability: measure it without spending the tail.

A voyage posts when the reported-case attack rate clears 3% in either
role, so ``posted`` is the indicator of a *continuous* quantity — the
posting margin ``max(AR_passenger, AR_crew)`` — crossing a fixed
threshold. Once the model's posting frequency is near the observed few
per 1,000, the indicator throws away almost every voyage: at 41 postings
per 1,000 a 1,000-voyage cell buys 41 usable observations and discards
959. Sweeping an axis that way needs run counts we cannot afford.

This instrument reads the same runs three ways, cheapest first, and
prints all three so they can disagree in public:

1. **Direct.** The binomial estimate with its Jeffreys interval — the
   thing being replaced, kept as the reference. It is never overwritten
   by a model estimate.
2. **Peaks-over-threshold.** A generalised Pareto tail fitted by
   probability-weighted moments to the margins above an anchor well
   below 3%, then extrapolated to 3%. Every voyage in the upper 15%
   informs it, so its sampling error falls with the *anchor* count, not
   the posting count. It is a distributional assumption, so the readout
   also refits at an intermediate level where the direct estimate is
   still well resolved and prints both — a model that misses the
   in-sample check has no licence to extrapolate.
3. **Paired differences.** Cells that differ in exactly one coordinate
   share their seeds, so the per-voyage *difference* is measurable even
   where each cell's rate is not. On the continuous margin this is a
   paired mean with a bootstrap interval; on the posting indicator it is
   McNemar's discordant pairs, which spends only the voyages that
   actually changed. The delta-method line then checks the two against
   each other: a shift of the margin distribution by ``d`` should move
   posting by ``f(tau)*d``, and printing predicted beside observed says
   whether the axis moved the distribution or only the noise.

Every pair also reports the fraction of shared seeds whose realised
import cohort is identical. That is a pairing *validity* diagnostic, not
a nicety: an arm that consumes a shared random stream decorrelates the
pair and inflates the difference's variance, which is exactly how the
declaration screen's stream leak was found.

Nothing here fits, selects or adopts a model value; A4 and A9 are not
read at all.

    python3 -m telemetry_buffer.observation_model.posting_tail_sensitivity \\
        --arm shipped=telemetry_buffer/boarding_posting_v1 \\
        --arm ladder=telemetry_buffer/realism_ladder_v1 \\
        --out telemetry_buffer/observation_model/posting_tail_v1.json \\
        --markdown docs/norovirus/posting_tail_sensitivity_v1.md
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binomtest

from simulation_utils.paths import resolve_repo_path, validated_open
from telemetry_buffer.observation_model.boarding_posting_readout import (
    BOARDING_KEYS,
)
from telemetry_buffer.observation_model.expedition_posting_readout import (
    jeffreys_interval,
)
from telemetry_buffer.observation_model.realism_ladder_readout import (
    MECHANISM_KEYS,
    SCREEN_KEYS,
    collect_rows,
)
from telemetry_buffer.observation_model.vsp_class_era_scoring import (
    POSTING_THRESHOLD,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# The coordinates a cell is keyed by, in the order the key tuple carries
# them, so a differing position can be named rather than numbered.
FAMILY_KEYS = (
    "arm",
    "platform_id",
    "surveillance",
    "dose_adjustment",
    "num_epochs",
)
COORD_KEYS = FAMILY_KEYS + MECHANISM_KEYS + SCREEN_KEYS + BOARDING_KEYS

# The anchor's exceedance probability. It fixes how much of the sample
# the tail fit sees: 0.15 keeps the anchor far enough below 3% that the
# extrapolation is short, while leaving a fittable number of points in a
# 200-voyage cell. Stated here, not tuned to an outcome.
ANCHOR_EXCEEDANCE = 0.15
MIN_EXCEEDANCES = 25

# A generalised Pareto tail is asymptotic in the anchor: too low an anchor
# fits the body and biases the extrapolation, too high a one has nothing
# to fit. The choice cannot be settled by assertion, so every cell is
# refitted across this ladder of anchors and the whole scan is reported.
# A modelled estimate that moves with the anchor is not measuring a tail.
ANCHOR_SCAN = (0.30, 0.20, 0.15, 0.10, 0.05)

# Half-width of the window the margin density at the threshold is read
# over, in attack-rate units. The density converts a distribution shift
# into a posting change; 0.5 percentage points is narrow against the
# spread of posted margins and wide enough to hold voyages.
DENSITY_HALFWIDTH = 0.005

# Where the tail model is checked against a still-well-resolved direct
# estimate before it is allowed to extrapolate to the threshold.
CHECK_LEVEL = 0.02

BOOTSTRAP_DRAWS = 400
BOOTSTRAP_SEED = 20260914
MIN_PAIRED_SEEDS = 50

MARGIN_KEY = "posting_margin"
DIFF_KEYS = (
    MARGIN_KEY,
    "reported_case_attack_rate_passenger",
    "secondary_infections",
    "imported",
)


def _margin(row: dict[str, Any]) -> float:
    """The continuous quantity whose 3% crossing *is* a posting.

    The VSP rule is an or-rule over the two roles, so the margin is the
    larger of the two reported attack rates and ``posted`` is exactly
    ``margin >= threshold`` — no approximation enters here.
    """
    return max(
        float(row["reported_case_attack_rate_passenger"]),
        float(row["reported_case_attack_rate_crew"]),
    )


def _cell_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row[key] for key in COORD_KEYS)


def _gpd_pwm(exceedances: list[float]) -> tuple[float, float] | None:
    """Fit ``1-(1+xi*y/sigma)**(-1/xi)`` by probability-weighted moments.

    Hosking and Wallis' estimator: closed-form, so there is no optimiser
    to fail silently, and it is better behaved than maximum likelihood at
    the sample sizes a single cell provides.
    """
    ordered = sorted(exceedances)
    n = len(ordered)
    if n < MIN_EXCEEDANCES:
        return None
    b0 = statistics.fmean(ordered)
    b1 = statistics.fmean([
        (1.0 - (i + 1 - 0.35) / n) * value
        for i, value in enumerate(ordered)
    ])
    denominator = b0 - 2.0 * b1
    if b0 <= 0.0 or abs(denominator) < 1e-12:
        return None
    xi = 2.0 - b0 / denominator
    sigma = 2.0 * b0 * b1 / denominator
    if sigma <= 0.0:
        return None
    return xi, sigma


def _gpd_exceedance(xi: float, sigma: float, distance: float) -> float:
    """``P(Y > distance)`` under the fitted tail, at the xi -> 0 limit too."""
    if distance <= 0.0:
        return 1.0
    if abs(xi) < 1e-6:
        return float(math.exp(-distance / sigma))
    scaled = 1.0 + xi * distance / sigma
    if scaled <= 0.0:
        # A bounded tail (xi < 0) whose endpoint sits below the level:
        # the model says the level is unreachable, which is a finding.
        return 0.0
    return float(scaled ** (-1.0 / xi))


def _tail_probability(
    values: list[float],
    level: float,
    anchor: float,
) -> float | None:
    """Modelled ``P(margin >= level)`` from the exceedances over anchor."""
    exceedances = [value - anchor for value in values if value > anchor]
    fit = _gpd_pwm(exceedances)
    if fit is None:
        return None
    xi, sigma = fit
    rate = len(exceedances) / len(values)
    return rate * _gpd_exceedance(xi, sigma, level - anchor)


def _bootstrap_ci(estimates: list[float]) -> list[float] | None:
    """Percentile interval over the resamples that produced an estimate."""
    if len(estimates) < BOOTSTRAP_DRAWS // 2:
        return None
    ordered = sorted(estimates)
    return [
        float(np.quantile(ordered, 0.025)),
        float(np.quantile(ordered, 0.975)),
    ]


def _tail_bootstrap(
    values: list[float],
    level: float,
    anchor: float,
) -> list[float] | None:
    """Resample voyages, refitting the anchor-relative tail each time."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    sample = np.asarray(values, dtype=float)
    estimates = []
    for _ in range(BOOTSTRAP_DRAWS):
        drawn = rng.choice(sample, size=sample.size, replace=True)
        estimate = _tail_probability(list(drawn), level, anchor)
        if estimate is not None:
            estimates.append(estimate)
    return _bootstrap_ci(estimates)


def _density_at(values: list[float], level: float) -> float | None:
    """Margin density at ``level``, read over a fixed window."""
    if not values:
        return None
    low = sum(1 for value in values if value >= level - DENSITY_HALFWIDTH)
    high = sum(1 for value in values if value >= level + DENSITY_HALFWIDTH)
    return (low - high) / (len(values) * 2.0 * DENSITY_HALFWIDTH)


def _direct(values: list[float], level: float) -> dict[str, Any]:
    """The binomial estimate this instrument is measured against."""
    crossings = sum(1 for value in values if value >= level)
    trials = len(values)
    return {
        "n_voyages": trials,
        "n_crossings": crossings,
        "probability": crossings / trials if trials else None,
        "probability_ci95": jeffreys_interval(crossings, trials),
    }


def tail_cell(values: list[float]) -> dict[str, Any]:
    """Direct and modelled posting probability for one cell's margins.

    ``check_level`` carries the same pair of estimates at a level the
    direct estimate still resolves: the model's licence to extrapolate to
    the threshold is that it reproduces the level it did not need to.
    """
    anchor = float(np.quantile(values, 1.0 - ANCHOR_EXCEEDANCE))
    record: dict[str, Any] = {
        "anchor_margin": anchor,
        "n_exceedances": sum(1 for value in values if value > anchor),
        "margin_median": statistics.median(values),
        "margin_p99": float(np.quantile(values, 0.99)),
        "density_at_threshold": _density_at(values, POSTING_THRESHOLD),
        "direct": _direct(values, POSTING_THRESHOLD),
        "check_level": CHECK_LEVEL,
        "direct_at_check_level": _direct(values, CHECK_LEVEL),
    }
    if anchor >= POSTING_THRESHOLD:
        # The cell posts so often that the anchor is above the threshold:
        # the direct estimate is already well resolved and a tail model
        # would extrapolate backwards into the body.
        record["modelled"] = None
        record["modelled_reason"] = "anchor_above_threshold"
        return record
    fit = _gpd_pwm([value - anchor for value in values if value > anchor])
    record["gpd_xi"] = None if fit is None else fit[0]
    record["gpd_sigma"] = None if fit is None else fit[1]
    record["modelled"] = _tail_probability(values, POSTING_THRESHOLD, anchor)
    record["modelled_ci95"] = _tail_bootstrap(
        values, POSTING_THRESHOLD, anchor,
    )
    record["modelled_at_check_level"] = (
        _tail_probability(values, CHECK_LEVEL, anchor)
        if CHECK_LEVEL > anchor else None
    )
    record["calibration_ratio_at_check_level"] = _ratio(
        record["modelled_at_check_level"],
        record["direct_at_check_level"]["probability"],
    )
    record["anchor_scan"] = _anchor_scan(values)
    return record


def _ratio(modelled: float | None, direct: float | None) -> float | None:
    """Modelled over direct, where the direct estimate is nonzero."""
    if modelled is None or not direct:
        return None
    return modelled / direct


def _anchor_scan(values: list[float]) -> list[dict[str, Any]]:
    """The same fit at every anchor, so anchor dependence is visible."""
    scan = []
    for exceedance in ANCHOR_SCAN:
        anchor = float(np.quantile(values, 1.0 - exceedance))
        if anchor >= POSTING_THRESHOLD:
            continue
        scan.append({
            "exceedance": exceedance,
            "anchor_margin": anchor,
            "n_exceedances": sum(1 for value in values if value > anchor),
            "modelled": _tail_probability(values, POSTING_THRESHOLD, anchor),
            "modelled_at_check_level": (
                _tail_probability(values, CHECK_LEVEL, anchor)
                if CHECK_LEVEL > anchor else None
            ),
        })
    return scan


def _by_seed(rows: list[dict[str, Any]]) -> dict[Any, dict[str, Any]] | None:
    """One row per seed, or None when a seed repeats inside the cell."""
    indexed: dict[Any, dict[str, Any]] = {}
    for row in rows:
        if row["seed"] in indexed:
            return None
        indexed[row["seed"]] = row
    return indexed


def _paired_diff(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    key: str,
) -> dict[str, Any]:
    """Mean per-seed difference, its interval, and what pairing bought."""
    diffs = np.asarray(
        [float(b[key]) - float(a[key]) for a, b in zip(left, right)],
        dtype=float,
    )
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    means = [
        float(rng.choice(diffs, size=diffs.size, replace=True).mean())
        for _ in range(BOOTSTRAP_DRAWS)
    ]
    paired_var = float(diffs.var(ddof=1)) / diffs.size
    unpaired_var = (
        float(np.var([float(row[key]) for row in left], ddof=1)) / len(left)
        + float(np.var([float(row[key]) for row in right], ddof=1)) / len(right)
    )
    return {
        "mean_difference": float(diffs.mean()),
        "mean_difference_ci95": _bootstrap_ci(means),
        "variance_reduction": (
            unpaired_var / paired_var if paired_var > 0.0 else None
        ),
        "n_identical": int(sum(1 for value in diffs if value == 0.0)),
    }


def _mcnemar(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
) -> dict[str, Any]:
    """The discordant pairs: the only voyages a posting change lives in."""
    gained = sum(1 for a, b in zip(left, right) if b["posted"] and not a["posted"])
    lost = sum(1 for a, b in zip(left, right) if a["posted"] and not b["posted"])
    discordant = gained + lost
    return {
        "n_pairs": len(left),
        "n_posted_left": sum(1 for row in left if row["posted"]),
        "n_posted_right": sum(1 for row in right if row["posted"]),
        "n_gained": gained,
        "n_lost": lost,
        "observed_difference": (gained - lost) / len(left) if left else None,
        "exact_p_value": (
            float(binomtest(gained, discordant, 0.5).pvalue)
            if discordant else None
        ),
    }


def _predicted_shift(
    density: float | None,
    margin_diff: dict[str, Any],
) -> dict[str, Any]:
    """Delta-method posting change from the margin shift, for contrast.

    Valid only for a shift small against the window the density was read
    over; it is printed beside the observed change so a disagreement is
    visible rather than assumed away.
    """
    if density is None:
        return {"predicted_difference": None}
    shift = margin_diff["mean_difference"]
    interval = margin_diff["mean_difference_ci95"]
    return {
        "predicted_difference": density * shift,
        "predicted_difference_ci95": (
            None if interval is None
            else [density * interval[0], density * interval[1]]
        ),
    }


def _pair_record(
    coordinate: str,
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """One single-coordinate contrast, measured on its shared seeds."""
    left_by_seed = _by_seed(left_rows)
    right_by_seed = _by_seed(right_rows)
    if left_by_seed is None or right_by_seed is None:
        return None
    shared = sorted(set(left_by_seed) & set(right_by_seed))
    if len(shared) < MIN_PAIRED_SEEDS:
        return None
    left = [left_by_seed[seed] for seed in shared]
    right = [right_by_seed[seed] for seed in shared]
    margins = [row[MARGIN_KEY] for row in left + right]
    differences = {key: _paired_diff(left, right, key) for key in DIFF_KEYS}
    record: dict[str, Any] = {
        "coordinate": coordinate,
        "n_shared_seeds": len(shared),
        "identical_import_fraction": (
            differences["imported"]["n_identical"] / len(shared)
        ),
        "differences": differences,
        "posting": _mcnemar(left, right),
    }
    record["posting"].update(
        _predicted_shift(
            _density_at(margins, POSTING_THRESHOLD),
            differences[MARGIN_KEY],
        ),
    )
    return record


def _single_difference(
    left: tuple[Any, ...],
    right: tuple[Any, ...],
) -> str | None:
    """The one coordinate two keys differ in, or None if not exactly one."""
    differing = [
        key for key, a, b in zip(COORD_KEYS, left, right) if a != b
    ]
    return differing[0] if len(differing) == 1 else None


def _describe(key: tuple[Any, ...]) -> dict[str, Any]:
    header = dict(zip(COORD_KEYS, key))
    # num_epochs counts 1-hour epochs, so this is a presentation
    # conversion to days.
    header["voyage_days"] = header["num_epochs"] / 24.0  # clock-exempt: epoch->day presentation
    return header


def build_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-cell tail estimates, plus every single-coordinate pairing."""
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        row[MARGIN_KEY] = _margin(row)
        grouped[_cell_key(row)].append(row)
    keys = sorted(grouped, key=lambda k: tuple(str(part) for part in k))
    cells = []
    for key in keys:
        cell = _describe(key)
        cell.update(tail_cell([row[MARGIN_KEY] for row in grouped[key]]))
        cells.append(cell)
    pairs = []
    for index, left in enumerate(keys):
        for right in keys[index + 1:]:
            coordinate = _single_difference(left, right)
            if coordinate is None:
                continue
            record = _pair_record(coordinate, grouped[left], grouped[right])
            if record is None:
                continue
            record["left"] = _describe(left)
            record["right"] = _describe(right)
            pairs.append(record)
    return {
        "posting_threshold": POSTING_THRESHOLD,
        "anchor_exceedance": ANCHOR_EXCEEDANCE,
        "n_runs": len(rows),
        "n_cells": len(cells),
        "n_pairs": len(pairs),
        "cells": cells,
        "pairs": pairs,
    }


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _interval(values: list[float] | None, digits: int = 4) -> str:
    if not values:
        return "n/a"
    return f"{values[0]:.{digits}f}-{values[1]:.{digits}f}"


def _cell_line(cell: dict[str, Any]) -> str:
    direct = cell["direct"]
    return (
        f"| {cell['arm']} | {cell['platform_id']} "
        f"| {_fmt(cell['voyage_days'], 1)} "
        f"| {cell['boarding_mechanism_rung']} "
        f"| {_fmt(cell['preboarding_crew_declaration_compliance'], 2)}"
        f"/{_fmt(cell['preboarding_crew_recall_halflife_days'], 1)}"
        f"/{_fmt(cell['preboarding_crew_denial_probability'], 2)} "
        f"| {direct['n_voyages']} | {direct['n_crossings']} "
        f"| {_fmt(direct['probability'])} "
        f"| {_interval(direct['probability_ci95'])} "
        f"| {_fmt(cell.get('modelled'))} "
        f"| {_interval(cell.get('modelled_ci95'))} "
        f"| {_fmt(cell['direct_at_check_level']['probability'], 3)} "
        f"| {_fmt(cell.get('modelled_at_check_level'), 3)} "
        f"| {_fmt(cell.get('calibration_ratio_at_check_level'), 2)} "
        f"| {_anchor_span(cell.get('anchor_scan'))} "
        f"| {_fmt(cell.get('gpd_xi'), 3)} |"
    )


def _anchor_span(scan: list[dict[str, Any]] | None) -> str:
    """The range the modelled estimate covers across the anchor ladder."""
    if not scan:
        return "n/a"
    estimates = [
        record["modelled"] for record in scan
        if record["modelled"] is not None
    ]
    if not estimates:
        return "n/a"
    return f"{min(estimates):.4f}-{max(estimates):.4f}"


def _pair_line(pair: dict[str, Any]) -> str:
    posting = pair["posting"]
    margin = pair["differences"][MARGIN_KEY]
    return (
        f"| {pair['coordinate']} "
        f"| {pair['left']['platform_id']} "
        f"| {_fmt(pair['left']['voyage_days'], 1)} "
        f"| {pair['n_shared_seeds']} "
        f"| {_fmt(pair['identical_import_fraction'], 3)} "
        f"| {_fmt(margin['mean_difference'], 5)} "
        f"| {_interval(margin['mean_difference_ci95'], 5)} "
        f"| {_fmt(margin['variance_reduction'], 1)} "
        f"| {posting['n_gained']}/{posting['n_lost']} "
        f"| {_fmt(posting['observed_difference'], 4)} "
        f"| {_fmt(posting.get('predicted_difference'), 4)} "
        f"| {_fmt(posting['exact_p_value'], 3)} |"
    )


def render_markdown(report: dict[str, Any]) -> str:
    """Two tables: the per-cell tail estimates and the paired contrasts."""
    lines = [
        "# Posting as a tail probability: the estimators, side by side",
        "",
        f"Posting rule: margin = max(reported AR passenger, crew) >= "
        f"{report['posting_threshold']:.0%}, so posting is exactly a "
        "threshold crossing of a continuous quantity. `direct` is the "
        "binomial estimate; `modelled` is a generalised Pareto tail fitted "
        f"above the {1 - report['anchor_exceedance']:.0%} margin quantile "
        "and extrapolated to the threshold. The two check columns repeat "
        "both estimates at 2%, where the direct one is still well "
        "resolved: a model that misses there is not licensed to "
        "extrapolate, and `modelled/direct@2%` states that miss as a ratio "
        "rather than leaving it to be read off. `anchor scan` is the range "
        "the modelled estimate covers as the anchor is moved across "
        f"{ANCHOR_SCAN[0]:.0%}-{ANCHOR_SCAN[-1]:.0%} exceedance: an estimate "
        "that moves with the anchor is fitting the body, not a tail. `xi` "
        "is the fitted shape; xi < 0 is a bounded tail.",
        "",
        "| arm | platform | days | rung | crew c/h/d | voyages | crossings "
        "| direct | direct CI | modelled | modelled CI | direct@2% "
        "| modelled@2% | modelled/direct@2% | anchor scan | xi |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    lines.extend(_cell_line(cell) for cell in report["cells"])
    lines.extend([
        "",
        "## Paired contrasts",
        "",
        "Cells differing in exactly one coordinate, matched seed by seed. "
        "`identical imports` is the fraction of shared seeds whose realised "
        "boarding cohort is unchanged — a pairing validity check, since an "
        "arm that consumes a shared random stream decorrelates the pair. "
        "`var reduction` is how much less variance the paired difference "
        "carries than the unpaired one. `gained/lost` are McNemar's "
        "discordant pairs, and `predicted` is the delta-method posting "
        "change implied by the margin shift, printed for contrast with the "
        "observed one rather than in place of it.",
        "",
        "| coordinate | platform | days | seeds | identical imports "
        "| margin shift | shift CI | var reduction | gained/lost "
        "| observed | predicted | exact p |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ])
    lines.extend(_pair_line(pair) for pair in report["pairs"])
    return "\n".join(lines) + "\n"


def _write(path: Path, text: str) -> None:
    """Write inside the repository, through the containment check."""
    resolved = Path(resolve_repo_path(str(REPO_ROOT), str(path)))
    with validated_open(
        str(resolved), "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        handle.write(text)


def _parse_arm(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("expected name=path")
    name, _, path = value.partition("=")
    return name, Path(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", action="append", required=True,
                        type=_parse_arm, help="name=results_root, repeatable")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    for name, root in args.arm:
        found = collect_rows(root, name)
        if not found:
            parser.error(f"no run summaries found under {root}")
        rows.extend(found)
    report = build_report(rows)
    _write(args.out, json.dumps(report, indent=1, sort_keys=True) + "\n")
    markdown = render_markdown(report)
    if args.markdown:
        _write(args.markdown, markdown)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
