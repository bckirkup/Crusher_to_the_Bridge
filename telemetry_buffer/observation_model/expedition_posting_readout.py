"""How often an expedition voyage posts, and the attack rate when it does.

Two quantities, per design cell, over the run zips of a campaign:

1. **Posting frequency.** The fraction of voyages whose cumulative reported
   cases reach ``POSTING_THRESHOLD`` (3%) in passengers *or* crew -- the VSP
   reporting rule, taken from ``vsp_class_era_scoring`` rather than restated
   here. The passenger-only channel is reported beside the or-rule because 206
   of the 208 postings in the project's series crossed 3% on passengers, so
   A9's numerator is effectively the passenger channel
   (``midrs_observed_targets.md`` section 4). Disagreements with the in-sim
   ``vsp_trigger_epoch`` flag are counted rather than reconciled: the flag fires
   on the passenger channel alone, which is a known definitional gap.
2. **Attack rate conditional on posting.** The distribution of reported
   passenger attack rate over the voyages that posted -- the quantity VSP
   publishes and A4 targets. Infection and ever-ill passenger attack rates are
   reported on the same voyages so that a change in the reported rate stays
   separable into transmission and ascertainment.

Conditioning is on *posting*, not on take-off. ``score_anchors`` conditions its
anchor levels on peak prevalence >= 10, which is a different subset: a voyage
can take off without reaching the reporting threshold, and the two subsets
diverge exactly where posting frequency is the quantity of interest.

Cells are keyed by platform, surveillance branch, declared release scale
(``environmental_faecal_release_log10_g_per_epoch``, the legacy
``dose_adjustment`` key) and voyage length, and are never pooled across the
release scale: it enters the emission as an exponent, and ledger item 00
records that a frequency marginalised over it reports a mixture of regimes
rather than a rate.

A cell whose surveillance branch sets ``sick_call_probability_per_day`` to zero
models no reporting at all, so its posting frequency is not a posting
measurement and is emitted as ``None`` with the branch marked report-free.

Nothing here selects, fits or adopts anything. The observed comparators (A4's
per-class quantile triple over postings, A9's fleet and voyage-length posting
probabilities) are printed beside the measured values so a departure is visible,
and the interval a cell's voyage count can actually resolve is printed with them
so an unresolvable comparison is not read as agreement.

    python3 -m telemetry_buffer.observation_model.expedition_posting_readout \\
        telemetry_buffer/mega_cruise_campaign \\
        --out telemetry_buffer/observation_model/expedition_posting_v1.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from scipy.stats import beta

from simulation_utils.paths import resolve_repo_path, validated_open
from telemetry_buffer.observation_model.midrs_incidence_targets import a9_targets
from telemetry_buffer.observation_model.vsp_class_era_scoring import (
    POSTING_THRESHOLD,
    vsp_attack_rate_targets,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_NAME = "summary.json"

# Jeffreys Beta(1/2, 1/2) is the reference prior for a binomial rate; it is
# stated rather than chosen, and it is the same prior the staged posting
# readout uses, so the two instruments report comparable intervals.
JEFFREYS_PRIOR = (0.5, 0.5)
CREDIBLE_MASS = 0.95

# ``score_anchors`` calls a voyage taken-off at this peak prevalence. Reported
# here only so that the posted subset can be seen against it; nothing in this
# readout conditions on it.
TAKEOFF_PEAK_PREVALENCE = 10

LEVEL_KEYS = (
    "reported_case_attack_rate_passenger",
    "reported_case_attack_rate_crew",
    "infection_attack_rate_passenger",
    "ever_ill_attack_rate_passenger",
)


def _summaries(path: Path) -> Iterable[dict[str, Any]]:
    """Yield every run summary in an archive, including fused shard zips."""
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name == SUMMARY_NAME or name.endswith(f"/{SUMMARY_NAME}"):
                yield json.loads(archive.read(name))


def collect_rows(root: Path) -> list[dict[str, Any]]:
    """Flatten every run under ``root`` into one row per voyage."""
    rows: list[dict[str, Any]] = []
    for archive in sorted(root.rglob("*.zip")):
        for summary in _summaries(archive):
            rows.append(_row(summary))
    return rows


def _row(summary: dict[str, Any]) -> dict[str, Any]:
    params = summary["parameters"]
    derived = summary["derived"]
    row: dict[str, Any] = {
        "run_id": summary["run_id"],
        "tier_id": params.get("tier_id"),
        "platform_id": params["platform_id"],
        "surveillance": params.get("surveillance"),
        "dose_adjustment": params.get("dose_adjustment"),
        "num_epochs": params["num_epochs"],
        "seed": params["seed"],
        "sick_call_probability_per_day": params.get(
            "sick_call_probability_per_day",
        ),
        "peak_prevalence": derived.get("peak_prevalence"),
        "vsp_trigger_epoch": derived.get("vsp_trigger_epoch"),
    }
    for key in LEVEL_KEYS:
        row[key] = float(derived[key])
    row["posted_passenger"] = (
        row["reported_case_attack_rate_passenger"] >= POSTING_THRESHOLD
    )
    row["posted"] = row["posted_passenger"] or (
        row["reported_case_attack_rate_crew"] >= POSTING_THRESHOLD
    )
    return row


def _cell_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["platform_id"],
        row["surveillance"],
        row["dose_adjustment"],
        row["num_epochs"],
    )


def jeffreys_interval(successes: int, trials: int) -> list[float] | None:
    """Equal-tailed 95% Jeffreys credible interval on a binomial rate."""
    if trials <= 0:
        return None
    a, b = JEFFREYS_PRIOR
    tail = (1.0 - CREDIBLE_MASS) / 2.0
    posterior = beta(a + successes, b + trials - successes)
    return [float(posterior.ppf(tail)), float(posterior.ppf(1.0 - tail))]


def _spread(values: list[float]) -> dict[str, float | None]:
    """Median, quartiles and range of a conditional level."""
    if not values:
        return {"n": 0, "median": None, "q1": None, "q3": None,
                "min": None, "max": None}
    if len(values) >= 2:
        q1, _median, q3 = statistics.quantiles(
            values, n=4, method="inclusive",
        )
    else:
        q1 = q3 = values[0]
    return {
        "n": len(values),
        "median": statistics.median(values),
        "q1": q1,
        "q3": q3,
        "min": min(values),
        "max": max(values),
    }


def _is_report_free(rows: list[dict[str, Any]]) -> bool:
    """True when the branch models no sick-call reporting at all."""
    return all(
        row["sick_call_probability_per_day"] == 0.0
        for row in rows
    )


def summarise_cell(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Posting frequency and the posting-conditional level distributions."""
    trials = len(rows)
    posted = [row for row in rows if row["posted"]]
    posted_pax = [row for row in rows if row["posted_passenger"]]
    report_free = _is_report_free(rows)
    cell: dict[str, Any] = {
        "n_voyages": trials,
        "n_posted": len(posted),
        "n_posted_passenger_channel": len(posted_pax),
        "n_takeoff": sum(
            (row["peak_prevalence"] or 0) >= TAKEOFF_PEAK_PREVALENCE
            for row in rows
        ),
        "trigger_flag_disagreements": sum(
            row["posted_passenger"] != (row["vsp_trigger_epoch"] is not None)
            for row in rows
        ),
        "report_free_branch": report_free,
    }
    if report_free:
        cell["posting_frequency"] = None
        cell["posting_frequency_ci95"] = None
        cell["posting_frequency_passenger_channel"] = None
    else:
        cell["posting_frequency"] = len(posted) / trials if trials else None
        cell["posting_frequency_ci95"] = jeffreys_interval(len(posted), trials)
        cell["posting_frequency_passenger_channel"] = (
            len(posted_pax) / trials if trials else None
        )
    cell["conditional_on_posting"] = {
        key: _spread([row[key] for row in posted]) for key in LEVEL_KEYS
    }
    cell["unconditional"] = {
        key: _spread([row[key] for row in rows]) for key in LEVEL_KEYS
    }
    return cell


def build_report(rows: list[dict[str, Any]], era: str) -> dict[str, Any]:
    """One cell per design point, with the observed comparators attached."""
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_cell_key(row)].append(row)
    cells = []
    for key in sorted(grouped, key=lambda k: tuple(str(part) for part in k)):
        platform, surveillance, dose, epochs = key
        cell = {
            "platform_id": platform,
            "surveillance": surveillance,
            "environmental_faecal_release_log10_g_per_epoch": dose,
            "num_epochs": epochs,
            # clock-exempt: num_epochs counts 1-hour epochs in this campaign,
            # so the division is an hours-to-days presentation conversion.
            "voyage_days": epochs / 24.0,  # clock-exempt: epochs->days
        }
        cell.update(summarise_cell(grouped[key]))
        cells.append(cell)
    return {
        "posting_threshold": POSTING_THRESHOLD,
        "n_runs": len(rows),
        "n_cells": len(cells),
        "observed_comparators": {
            "note": (
                "Reported for contrast only. No value in this campaign was "
                "selected to move any of them."
            ),
            "A4_reported_passenger_ar_over_postings_by_hull": (
                vsp_attack_rate_targets(era)
            ),
            "A9_posting_probability_per_1000_voyages": a9_targets(era),
        },
        "cells": cells,
    }


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _cell_row(cell: dict[str, Any]) -> str:
    conditional = cell["conditional_on_posting"][
        "reported_case_attack_rate_passenger"
    ]
    ci = cell["posting_frequency_ci95"]
    ci_text = (
        f"{_fmt(ci[0])}-{_fmt(ci[1])}" if ci else "n/a"
    )
    return (
        f"| {cell['surveillance']} "
        f"| {_fmt(cell['environmental_faecal_release_log10_g_per_epoch'], 1)} "
        f"| {_fmt(cell['voyage_days'], 1)} "
        f"| {cell['n_voyages']} "
        f"| {cell['n_posted']} "
        f"| {_fmt(cell['posting_frequency'])} "
        f"| {ci_text} "
        f"| {conditional['n']} "
        f"| {_fmt(conditional['median'])} "
        f"| {_fmt(conditional['q1'])}-{_fmt(conditional['q3'])} |"
    )


def render_markdown(report: dict[str, Any]) -> str:
    """A table of posting frequency and posting-conditional passenger AR."""
    lines = [
        "# Expedition posting frequency and posting-conditional attack rate",
        "",
        f"Posting rule: reported cases >= {report['posting_threshold']:.0%} of "
        "passengers or of crew. Attack rate is the reported passenger attack "
        "rate over posted voyages. Release scale is "
        "`environmental_faecal_release_log10_g_per_epoch` and cells are never "
        "pooled across it.",
        "",
        "| surveillance | release | days | voyages | posted | P(post) "
        "| P(post) 95% CI | n posted | median pax AR | IQR |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    lines.extend(_cell_row(cell) for cell in report["cells"])
    lines.extend([
        "",
        "Observed comparators, reported and not fitted: A4 expedition "
        "reported passenger AR over pre-2020 postings, and A9 posting "
        "probability per 1,000 voyages (fleet-pooled and by voyage-length "
        "band). A9 publishes no per-hull numerator, so the fleet and "
        "length rows are the only observed posting comparators available.",
        "",
        "```json",
        json.dumps(report["observed_comparators"], indent=1, sort_keys=True),
        "```",
    ])
    return "\n".join(lines) + "\n"


def _write(path: Path, text: str) -> None:
    """Write inside the repository, through the containment check."""
    resolved = Path(resolve_repo_path(str(REPO_ROOT), str(path)))
    with validated_open(
        str(resolved), "w", allowed_roots=(str(REPO_ROOT),), encoding="utf-8",
    ) as handle:
        handle.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--vsp-era", default="pre", choices=("pre", "post"))
    args = parser.parse_args(argv)

    rows = collect_rows(args.results_root)
    if not rows:
        parser.error(f"no run summaries found under {args.results_root}")
    report = build_report(rows, args.vsp_era)
    _write(args.out, json.dumps(report, indent=1, sort_keys=True) + "\n")
    markdown = render_markdown(report)
    if args.markdown:
        _write(args.markdown, markdown)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
