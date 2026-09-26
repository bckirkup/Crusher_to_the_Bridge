"""What shared heads do to posting, before any flush term exists.

``sanitary_structure_v1`` runs two arms on identical seeds: ``none`` (the
heads exist on every hull but nobody enters them, bit-identical to the
pre-#538 engine on paired seeds) and ``dwell_weighted`` (hosts visit the
head serving their current zone, and away-from-cabin stool events land on
its fittings). No flush aerosol is emitted in either arm, so this is the
structure alone: a small, exhaust-ventilated, high-traffic surface added to
the fomite route.

Three things are kept separable per cell, because each can fail on its
own:

1. **The execution witness.** ``sanitary_activity`` is copied from the
   core into every epoch summary. In the ``none`` arm every counter is
   zero; in the visits arm ``visits`` and ``person_seconds`` say the
   mechanism ran, and ``recipients``/``dose_delivered`` say whether a
   susceptible ever picked dose up off a head. A voyage with thousands of
   visits and zero recipients is a real finding — no shedder deposited at
   a shared head while a susceptible passed through — and is counted as
   such rather than folded into a mean.
2. **The paired contrast.** Cells differing only in the visit mode are
   matched seed by seed on the posting margin, the passenger attack rate
   and secondaries per voyage; posting itself is read from McNemar's
   discordant pairs. ``identical imports`` must be 1.0: the visit stream
   has its own rng, so a pair whose boarding cohort moved is a leak.
3. **Route attribution.** Sanitary pickups are booked to ``fomite``, so
   the fomite share of established infections is the only route readout
   that can move; the arm difference in its dominant count is reported.

Nothing here selects, fits or adopts anything: A4 and A9 are printed beside
the measured values, never used to choose one.

    python3 -m telemetry_buffer.observation_model.sanitary_structure_readout \\
        --arm baseline=telemetry_buffer/sanitary_structure_v1_baseline \\
        --arm visits=telemetry_buffer/sanitary_structure_v1_visits \\
        --out telemetry_buffer/observation_model/sanitary_structure_v1.json \\
        --markdown docs/norovirus/sanitary_structure_v1_readout.md
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from simulation_utils.paths import resolve_repo_path, validated_open
from telemetry_buffer.observation_model.boarding_posting_readout import _pairs
from telemetry_buffer.observation_model.expedition_posting_readout import (
    jeffreys_interval,
)
from telemetry_buffer.observation_model.midrs_incidence_targets import a9_targets
from telemetry_buffer.observation_model.posting_tail_sensitivity import (
    MARGIN_KEY,
    MIN_PAIRED_SEEDS,
    _by_seed,
    _margin,
    _mcnemar,
    _paired_diff,
)
from telemetry_buffer.observation_model.realism_ladder_readout import (
    _row,
    summarise_cell,
)
from telemetry_buffer.observation_model.vsp_class_era_scoring import (
    POSTING_THRESHOLD,
    vsp_attack_rate_targets,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

MODE_KEY = "sanitary_visit_mode"

# The witness counters, in the order the core keeps them. ``recipients``
# counts susceptible pickup events, not distinct hosts.
WITNESS_KEYS = (
    "visits",
    "person_seconds",
    "stool_visits",
    "unresolved",
    "recipients",
    "dose_delivered",
)

# The cell is the hull at its own complement and voyage length under one
# surveillance and dose point; the visit mode is the contrast, not a cell
# coordinate, so it is carried separately and the pairing is exact.
CELL_KEYS = (
    "platform_id",
    "num_agents",
    "num_epochs",
    "surveillance",
    "dose_adjustment",
    "boarding_mechanism_rung",
)

DIFF_KEYS = (
    MARGIN_KEY,
    "reported_case_attack_rate_passenger",
    "reported_case_attack_rate_crew",
    "secondary_infections",
    "imported",
    "route_dom_fomite",
    "sanitary_recipients",
)

# clock-exempt: num_epochs counts 1-hour epochs, so this is a presentation
# conversion to days used only for the per-person-day visit rate.
EPOCHS_PER_DAY = 24.0


def _witness(summary: dict[str, Any]) -> dict[str, Any]:
    block = (summary.get("summary") or {}).get("sanitary_activity")
    if not isinstance(block, dict):
        return dict.fromkeys(WITNESS_KEYS)
    return {key: block.get(key) for key in WITNESS_KEYS}


def _visit_row(
    summary: dict[str, Any],
    profile: dict[str, Any] | None,
    arm: str,
) -> dict[str, Any]:
    row = _row(summary, profile)
    row["arm"] = arm
    row[MODE_KEY] = summary["parameters"].get(MODE_KEY)
    row["sanitary_witness_present"] = isinstance(
        (summary.get("summary") or {}).get("sanitary_activity"), dict,
    )
    for key, value in _witness(summary).items():
        row[f"sanitary_{key}"] = value
    row[MARGIN_KEY] = _margin(row)
    return row


def collect_rows(root: Path, arm: str) -> list[dict[str, Any]]:
    """One row per distinct run under ``root``.

    A shard's ``<shard>.zip`` and the per-run zips it was assembled from
    can coexist in one results root, so runs are deduplicated by id.
    """
    rows: dict[str, dict[str, Any]] = {}
    for archive in sorted(root.rglob("*.zip")):
        for summary, profile in _pairs(archive):
            row = _visit_row(summary, profile, arm)
            rows.setdefault(row["run_id"], row)
    return list(rows.values())


def _cell_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row[key] for key in CELL_KEYS)


def _mean(values: list[float | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    return statistics.fmean(present) if present else None


def _fraction_positive(
    rows: list[dict[str, Any]], key: str,
) -> dict[str, Any]:
    trials = len(rows)
    count = sum(1 for row in rows if (row[key] or 0) > 0)
    return {
        "count": count,
        "fraction": count / trials if trials else None,
        "ci95": jeffreys_interval(count, trials),
    }


def witness_block(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Did the heads run, and did anyone pick anything up off them?

    Means are given per voyage; ``visits_per_person_day`` normalises the
    visit count by complement and length so hulls can be read against one
    another. ``voyages_with_recipients`` is the honest form of "did the
    structure ever deliver dose": a mean over voyages that are mostly zero
    hides the fraction that are structurally silent.
    """
    if not rows:
        return {}
    person_days = [
        row["num_agents"] * row["num_epochs"] / EPOCHS_PER_DAY for row in rows
    ]
    visits = [row["sanitary_visits"] for row in rows]
    block: dict[str, Any] = {
        "n_voyages": len(rows),
        "witness_present_fraction": (
            sum(1 for row in rows if row["sanitary_witness_present"]) / len(rows)
        ),
        "visits_per_person_day": _mean([
            None if visit is None else visit / days
            for visit, days in zip(visits, person_days)
        ]),
        "voyages_with_visits": _fraction_positive(rows, "sanitary_visits"),
        "voyages_with_stool_visits": _fraction_positive(
            rows, "sanitary_stool_visits",
        ),
        "voyages_with_recipients": _fraction_positive(
            rows, "sanitary_recipients",
        ),
    }
    for key in WITNESS_KEYS:
        block[f"mean_{key}"] = _mean([row[f"sanitary_{key}"] for row in rows])
        block[f"total_{key}"] = sum(
            float(row[f"sanitary_{key}"] or 0.0) for row in rows
        )
    return block


def _per_import_yield(rows: list[dict[str, Any]]) -> float | None:
    imported = sum(row["imported"] for row in rows)
    if imported <= 0:
        return None
    return sum(row["secondary_infections"] for row in rows) / imported


def _arm_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    modes = sorted({str(row[MODE_KEY]) for row in rows})
    record = {
        "arm": rows[0]["arm"],
        MODE_KEY: modes[0] if len(modes) == 1 else modes,
        "secondaries_per_import": _per_import_yield(rows),
        "sanitary": witness_block(rows),
    }
    record.update(summarise_cell(rows))
    return record


def _contrast(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """``right - left`` on shared seeds; None when the pairing is invalid."""
    left_by_seed = _by_seed(left_rows)
    right_by_seed = _by_seed(right_rows)
    if left_by_seed is None or right_by_seed is None:
        return None
    shared = sorted(set(left_by_seed) & set(right_by_seed))
    if len(shared) < MIN_PAIRED_SEEDS:
        return None
    left = [left_by_seed[seed] for seed in shared]
    right = [right_by_seed[seed] for seed in shared]
    differences = {key: _paired_diff(left, right, key) for key in DIFF_KEYS}
    return {
        "left_arm": left[0]["arm"],
        "right_arm": right[0]["arm"],
        "n_shared_seeds": len(shared),
        "identical_import_fraction": (
            differences["imported"]["n_identical"] / len(shared)
        ),
        "secondaries_per_import_difference": (
            None
            if _per_import_yield(left) is None or _per_import_yield(right) is None
            else _per_import_yield(right) - _per_import_yield(left)
        ),
        "differences": differences,
        "posting": _mcnemar(left, right),
    }


def _header(key: tuple[Any, ...]) -> dict[str, Any]:
    header = dict(zip(CELL_KEYS, key))
    header["voyage_days"] = header["num_epochs"] / EPOCHS_PER_DAY
    return header


def build_report(rows: list[dict[str, Any]], era: str) -> dict[str, Any]:
    """One cell per hull and length; the arms inside it, and their contrast."""
    grouped: dict[tuple[Any, ...], dict[str, list[dict[str, Any]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    for row in rows:
        grouped[_cell_key(row)][row["arm"]].append(row)
    cells = []
    for key in sorted(grouped, key=lambda k: tuple(str(part) for part in k)):
        arms = grouped[key]
        cell = _header(key)
        cell["arms"] = {arm: _arm_summary(arms[arm]) for arm in sorted(arms)}
        names = sorted(arms)
        cell["contrast"] = (
            _contrast(arms[names[0]], arms[names[1]]) if len(names) == 2 else None
        )
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


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _interval(values: list[float] | None, digits: int = 4) -> str:
    if not values:
        return "n/a"
    return f"[{values[0]:.{digits}f}, {values[1]:.{digits}f}]"


def _arm_line(cell: dict[str, Any], arm: str) -> str:
    record = cell["arms"][arm]
    witness = record["sanitary"]
    fomite = record["secondary_route_attribution"]["fomite"]
    conditional = record["conditional_on_posting"][
        "reported_case_attack_rate_passenger"
    ]
    return (
        f"| {cell['platform_id']} | {cell['num_agents']} "
        f"| {_fmt(cell['voyage_days'], 0)} | {arm} | {record[MODE_KEY]} "
        f"| {record['n_voyages']} "
        f"| {_fmt(witness['visits_per_person_day'], 2)} "
        f"| {witness['voyages_with_stool_visits']['count']} "
        f"| {witness['voyages_with_recipients']['count']} "
        f"| {_fmt(witness['mean_recipients'], 1)} "
        f"| {_fmt(witness['mean_dose_delivered'], 5)} "
        f"| {_fmt(record['secondaries_per_import'], 3)} "
        f"| {_fmt(record['secondary_infection_spread']['mean'], 2)} "
        f"| {_fmt(record['secondary_infection_spread']['fraction_zero'])} "
        f"| {100.0 * fomite['fraction_dominant']:.1f}% "
        f"| {_fmt(record['posting_frequency_per_1000'], 1)} "
        f"| {_interval(record['posting_frequency_ci95'], 4)} "
        f"| {_fmt(conditional['median'], 4)} |"
    )


def _contrast_line(cell: dict[str, Any]) -> str:
    contrast = cell["contrast"]
    if contrast is None:
        return (
            f"| {cell['platform_id']} | {_fmt(cell['voyage_days'], 0)} "
            "| unpaired | | | | | | | | |"
        )
    diffs = contrast["differences"]
    posting = contrast["posting"]
    return (
        f"| {cell['platform_id']} | {_fmt(cell['voyage_days'], 0)} "
        f"| {contrast['n_shared_seeds']} "
        f"| {_fmt(contrast['identical_import_fraction'], 3)} "
        f"| {_fmt(diffs['sanitary_recipients']['mean_difference'], 1)} "
        f"| {_fmt(contrast['secondaries_per_import_difference'], 3)} "
        f"| {_fmt(diffs['secondary_infections']['mean_difference'], 3)} "
        f"{_interval(diffs['secondary_infections']['mean_difference_ci95'], 3)} "
        f"| {_fmt(diffs['route_dom_fomite']['mean_difference'], 3)} "
        f"| {_fmt(diffs[MARGIN_KEY]['mean_difference'], 5)} "
        f"{_interval(diffs[MARGIN_KEY]['mean_difference_ci95'], 5)} "
        f"| {_fmt(diffs[MARGIN_KEY]['variance_reduction'], 1)} "
        f"| {posting['n_gained']}/{posting['n_lost']} "
        f"| {_fmt(posting['exact_p_value'], 3)} |"
    )


DEFAULT_TITLE = (
    "Shared heads without a flush term: the structure-only matched arm"
)


def render_markdown(
    report: dict[str, Any], title: str = DEFAULT_TITLE,
) -> str:
    lines = [
        f"# {title}",
        "",
        f"Posting rule: reported cases >= {report['posting_threshold']:.0%} of "
        "passengers or of crew. `visits/p-d` is shared-head visits per "
        "person-day aboard; `stool v.` and `recip v.` count voyages with any "
        "stool event landing on a shared head and any susceptible pickup off "
        "one. `recipients` counts pickup events, not hosts. `sec/import` is "
        "pooled secondaries over pooled imports. The fomite column is the "
        "share of dominant-attributed infections booked to `fomite`, which "
        "is where sanitary pickups land.",
        "",
        "| platform | agents | days | arm | mode | voyages | visits/p-d "
        "| stool v. | recip v. | recipients | dose | sec/import "
        "| mean sec | zero | fomite % | post/1,000 | posting CI "
        "| median pax AR |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
        "---|---|",
    ]
    for cell in report["cells"]:
        lines.extend(_arm_line(cell, arm) for arm in sorted(cell["arms"]))
    lines.extend([
        "",
        "## Paired contrasts (visits − baseline, seed by seed)",
        "",
        "`identical imports` must be 1.000: the visit stream has its own "
        "rng, so a pair whose boarding cohort moved is a leak, not a result. "
        "`gained/lost` are McNemar's discordant postings.",
        "",
        "| platform | days | seeds | identical imports | Δ recipients "
        "| Δ sec/import | Δ secondaries (CI) | Δ fomite dominant "
        "| Δ margin (CI) | var reduction | gained/lost | exact p |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ])
    lines.extend(_contrast_line(cell) for cell in report["cells"])
    lines.extend([
        "",
        "Observed comparators, reported and not fitted: A4 reported passenger "
        "AR over pre-2020 postings by hull, and A9 posting probability per "
        "1,000 voyages, fleet-pooled and by voyage-length band.",
        "",
        "```json",
        json.dumps(report["observed_comparators"], indent=1, sort_keys=True),
        "```",
    ])
    return "\n".join(lines) + "\n"


def _write(path: Path, text: str) -> None:
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
    parser.add_argument("--arm", action="append", required=True, type=_parse_arm,
                        help="name=results_root, repeatable")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--vsp-era", default="pre", choices=("pre", "post"))
    args = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    for name, root in args.arm:
        found = collect_rows(root, name)
        if not found:
            parser.error(f"no run summaries found under {root}")
        rows.extend(found)
    report = build_report(rows, args.vsp_era)
    _write(args.out, json.dumps(report, indent=1, sort_keys=True) + "\n")
    markdown = render_markdown(report, title=args.title)
    if args.markdown:
        _write(args.markdown, markdown)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
