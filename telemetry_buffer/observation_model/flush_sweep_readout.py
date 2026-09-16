"""Where the flush-aerosol fraction first becomes resolvable.

``flush_sweep_v1`` stage 1 runs four arms on one seed prefix
(8000-8099): ``off`` -- the item-42 ``dwell_weighted`` configuration, in
which the shared heads execute and are measured inert -- and
``flush_aerosol_fraction`` at 1e-9, 1e-7 and 1e-5. Emission is exactly
linear in the fraction, so the arms differ only in the size of a bowl
deposit's aerosolised share; what is not linear is the beta-Poisson
response, which is why the campaign asks which decade first moves an
outcome rather than what the fraction is.

The 1e-5 arm is a falsifier, not filler. The closed-form per-visit dose
(``10^titre x 107 g / V_head x f_vent x inhaled x dwell share``) against
the shipped GII.4 curve predicts saturation at and above 1e-5; if that
arm does not saturate, the analysis behind the staging is wrong and
stage 2's placement would inherit the error.

Every arm is read against ``off`` on shared seeds, never against another
arm's archive, and three things are kept separable per cell:

1. **The execution witness.** ``flush_events`` counts emitting
   defecations, ``flush_aerosol_emitted`` the copies released,
   ``flush_recipients`` the exposure events and ``flush_dose_delivered``
   the particles inhaled. All four are zero in ``off`` by construction:
   a nonzero one there is a leak, not a result. In a live arm, events
   without recipients is a real finding -- a flush nobody shared air
   with -- and is counted rather than averaged away.
2. **The paired contrast.** ``off`` vs each live arm, seed by seed, on
   the posting margin, the passenger attack rate and secondaries;
   posting from McNemar's discordant pairs. ``identical imports`` must
   be 1.000 -- the boarding cohort may not move between arms.
3. **Route attribution.** ``flush_aerosol`` is its own route key, so an
   arm that moves the outcome without attributing infections to
   ``flush_aerosol`` is moving it by some other path and the reading is
   not about flush at all.

The arm coordinate is read from each run's archived
``parameters.flush_aerosol_fraction``, never from a directory name, and
a root whose runs disagree about it is refused.

A4 and A9 are printed beside the measured values and are used to choose
nothing: no decade acquires standing from its distance to an anchor.

    python3 -m telemetry_buffer.observation_model.flush_sweep_readout \\
        --arm off=telemetry_buffer/flush_sweep_v1_off_s1 \\
        --arm 1e-9=telemetry_buffer/flush_sweep_v1_1e-9_s1 \\
        --arm 1e-7=telemetry_buffer/flush_sweep_v1_1e-7_s1 \\
        --arm 1e-5=telemetry_buffer/flush_sweep_v1_1e-5_s1 \\
        --out telemetry_buffer/observation_model/flush_sweep_v1_s1.json \\
        --markdown docs/norovirus/flush_sweep_v1_stage1_readout.md
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from telemetry_buffer.observation_model.boarding_posting_readout import _pairs
from telemetry_buffer.observation_model.midrs_incidence_targets import a9_targets
from telemetry_buffer.observation_model.posting_tail_sensitivity import (
    MARGIN_KEY,
    _mcnemar,
    _paired_diff,
)
from telemetry_buffer.observation_model.readout_common import (
    paired_rows,
    run_readout_cli,
)
from telemetry_buffer.observation_model.realism_ladder_readout import (
    summarise_cell,
)
from telemetry_buffer.observation_model.sanitary_structure_readout import (
    _fraction_positive,
    _mean,
    _per_import_yield,
    _visit_row,
    witness_block,
)
from telemetry_buffer.observation_model.vsp_class_era_scoring import (
    POSTING_THRESHOLD,
    vsp_attack_rate_targets,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

FRACTION_KEY = "flush_aerosol_fraction"
BASELINE_ARM = "off"

# The flush witness, as the core keeps it. ``recipients`` counts
# exposure events, not distinct hosts.
FLUSH_KEYS = (
    "flush_events",
    "flush_aerosol_emitted",
    "flush_recipients",
    "flush_dose_delivered",
)

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
    "route_dom_flush_aerosol",
    "flush_recipients",
)

# clock-exempt: num_epochs counts 1-hour epochs; days is a presentation
# conversion used for the per-person-day rates only.
EPOCHS_PER_DAY = 24.0


def _flush_row(
    summary: dict[str, Any],
    profile: dict[str, Any] | None,
    arm: str,
) -> dict[str, Any]:
    row = _visit_row(summary, profile, arm)
    block = (summary.get("summary") or {}).get("sanitary_activity")
    row[FRACTION_KEY] = summary["parameters"].get(FRACTION_KEY)
    row["flush_witness_present"] = isinstance(block, dict) and all(
        key in block for key in FLUSH_KEYS
    )
    for key in FLUSH_KEYS:
        row[key] = (block or {}).get(key)
    return row


def collect_rows(root: Path, arm: str) -> list[dict[str, Any]]:
    """One row per distinct run under ``root``, deduplicated by run id."""
    rows: dict[str, dict[str, Any]] = {}
    for archive in sorted(root.rglob("*.zip")):
        for summary, profile in _pairs(archive):
            row = _flush_row(summary, profile, arm)
            rows.setdefault(row["run_id"], row)
    return list(rows.values())


def declared_fraction(rows: list[dict[str, Any]]) -> float:
    """The arm's own archived fraction; a disagreeing root is refused."""
    declared = {float(row[FRACTION_KEY] or 0.0) for row in rows}
    if len(declared) != 1:
        raise ValueError(
            f"arm {rows[0]['arm']!r} archives disagree about {FRACTION_KEY}: "
            f"{sorted(declared)}",
        )
    return declared.pop()


def flush_witness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Did the route emit, and did anyone inhale what it emitted?"""
    if not rows:
        return {}
    person_days = [
        row["num_agents"] * row["num_epochs"] / EPOCHS_PER_DAY for row in rows
    ]
    events = [row["flush_events"] for row in rows]
    block: dict[str, Any] = {
        "witness_present_fraction": (
            sum(1 for row in rows if row["flush_witness_present"]) / len(rows)
        ),
        "events_per_person_day": _mean([
            None if event is None else event / days
            for event, days in zip(events, person_days)
        ]),
        "voyages_with_events": _fraction_positive(rows, "flush_events"),
        "voyages_with_recipients": _fraction_positive(
            rows, "flush_recipients",
        ),
    }
    for key in FLUSH_KEYS:
        block[f"mean_{key}"] = _mean([row[key] for row in rows])
        block[f"total_{key}"] = sum(float(row[key] or 0.0) for row in rows)
    dose = block["total_flush_dose_delivered"]
    exposures = block["total_flush_recipients"]
    block["dose_per_exposure"] = dose / exposures if exposures else None
    return block


def _arm_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    record = {
        "arm": rows[0]["arm"],
        FRACTION_KEY: declared_fraction(rows),
        "secondaries_per_import": _per_import_yield(rows),
        "flush": flush_witness(rows),
        "sanitary": witness_block(rows),
    }
    record.update(summarise_cell(rows))
    return record


def _contrast(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """``right - left`` on shared seeds; None when the pairing is invalid."""
    paired = paired_rows(left_rows, right_rows)
    if paired is None:
        return None
    left, right, n_shared = paired
    differences = {key: _paired_diff(left, right, key) for key in DIFF_KEYS}
    left_yield = _per_import_yield(left)
    right_yield = _per_import_yield(right)
    return {
        "left_arm": left[0]["arm"],
        "right_arm": right[0]["arm"],
        "n_shared_seeds": n_shared,
        "identical_import_fraction": (
            differences["imported"]["n_identical"] / n_shared
        ),
        "secondaries_per_import_difference": (
            None
            if left_yield is None or right_yield is None
            else right_yield - left_yield
        ),
        "secondaries_per_import_ratio": (
            None
            if not left_yield or right_yield is None
            else right_yield / left_yield
        ),
        "differences": differences,
        "posting": _mcnemar(left, right),
    }


def _header(key: tuple[Any, ...]) -> dict[str, Any]:
    header = dict(zip(CELL_KEYS, key))
    header["voyage_days"] = header["num_epochs"] / EPOCHS_PER_DAY
    return header


def _cell_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row[key] for key in CELL_KEYS)


def _sorted_arms(arms: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Baseline first, then live arms by their archived fraction."""
    live = [arm for arm in arms if arm != BASELINE_ARM]
    live.sort(key=lambda arm: declared_fraction(arms[arm]))
    return ([BASELINE_ARM] if BASELINE_ARM in arms else []) + live


def build_report(rows: list[dict[str, Any]], era: str) -> dict[str, Any]:
    """One cell per hull and length; every live arm against ``off``."""
    grouped: dict[tuple[Any, ...], dict[str, list[dict[str, Any]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    for row in rows:
        grouped[_cell_key(row)][row["arm"]].append(row)
    cells = []
    for key in sorted(grouped, key=lambda k: tuple(str(part) for part in k)):
        arms = grouped[key]
        order = _sorted_arms(arms)
        cell = _header(key)
        cell["arm_order"] = order
        cell["arms"] = {arm: _arm_summary(arms[arm]) for arm in order}
        cell["contrasts"] = {
            arm: _contrast(arms[BASELINE_ARM], arms[arm])
            for arm in order
            if arm != BASELINE_ARM and BASELINE_ARM in arms
        }
        cells.append(cell)
    return {
        "posting_threshold": POSTING_THRESHOLD,
        "baseline_arm": BASELINE_ARM,
        "n_runs": len(rows),
        "n_cells": len(cells),
        "observed_comparators": {
            "note": (
                "Reported for contrast only. No arm was selected, and no "
                "fraction adopted, on its distance to any of them."
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


def _sci(value: Any, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}e}"


def _interval(values: list[float] | None, digits: int = 4) -> str:
    if not values:
        return "n/a"
    return f"[{values[0]:.{digits}f}, {values[1]:.{digits}f}]"


def _arm_line(cell: dict[str, Any], arm: str) -> str:
    record = cell["arms"][arm]
    flush = record["flush"]
    routes = record["secondary_route_attribution"]
    conditional = record["conditional_on_posting"][
        "reported_case_attack_rate_passenger"
    ]
    return (
        f"| {cell['platform_id']} | {_fmt(cell['voyage_days'], 0)} | {arm} "
        f"| {_sci(record[FRACTION_KEY])} | {record['n_voyages']} "
        f"| {flush['voyages_with_events']['count']} "
        f"| {flush['voyages_with_recipients']['count']} "
        f"| {_sci(flush['mean_flush_aerosol_emitted'])} "
        f"| {_fmt(flush['mean_flush_recipients'], 1)} "
        f"| {_sci(flush['dose_per_exposure'])} "
        f"| {_fmt(record['secondaries_per_import'], 3)} "
        f"| {_fmt(record['secondary_infection_spread']['mean'], 2)} "
        f"| {_fmt(record['secondary_infection_spread']['fraction_zero'])} "
        f"| {100.0 * routes['flush_aerosol']['fraction_dominant']:.1f}% "
        f"| {100.0 * routes['fomite']['fraction_dominant']:.1f}% "
        f"| {_fmt(record['posting_frequency_per_1000'], 1)} "
        f"| {_interval(record['posting_frequency_ci95'], 4)} "
        f"| {_fmt(conditional['median'], 4)} |"
    )


def _contrast_line(cell: dict[str, Any], arm: str) -> str:
    contrast = cell["contrasts"].get(arm)
    if contrast is None:
        return (
            f"| {cell['platform_id']} | {_fmt(cell['voyage_days'], 0)} "
            f"| {arm} | unpaired | | | | | | | |"
        )
    diffs = contrast["differences"]
    posting = contrast["posting"]
    return (
        f"| {cell['platform_id']} | {_fmt(cell['voyage_days'], 0)} | {arm} "
        f"| {contrast['n_shared_seeds']} "
        f"| {_fmt(contrast['identical_import_fraction'], 3)} "
        f"| {_fmt(diffs['flush_recipients']['mean_difference'], 1)} "
        f"| {_fmt(contrast['secondaries_per_import_difference'], 3)} "
        f"| {_fmt(contrast['secondaries_per_import_ratio'], 2)} "
        f"| {_fmt(diffs['secondary_infections']['mean_difference'], 3)} "
        f"{_interval(diffs['secondary_infections']['mean_difference_ci95'], 3)} "
        f"| {_fmt(diffs['route_dom_flush_aerosol']['mean_difference'], 3)} "
        f"| {_fmt(diffs[MARGIN_KEY]['mean_difference'], 5)} "
        f"{_interval(diffs[MARGIN_KEY]['mean_difference_ci95'], 5)} "
        f"| {posting['n_gained']}/{posting['n_lost']} "
        f"| {_fmt(posting['exact_p_value'], 3)} |"
    )


DEFAULT_TITLE = (
    "Which decade of the flush aerosol fraction first moves an outcome: "
    "stage 1"
)


def render_markdown(
    report: dict[str, Any], title: str = DEFAULT_TITLE,
) -> str:
    lines = [
        f"# {title}",
        "",
        f"Posting rule: reported cases >= {report['posting_threshold']:.0%} "
        "of passengers or of crew. `f_aero` is each arm's own archived "
        "`flush_aerosol_fraction`, read from the run parameters and not "
        "from a prefix. `ev. v.` and `rec. v.` count voyages with any "
        "emitting flush and any exposure event; `recipients` counts "
        "exposure events, not hosts. `dose/exp` is pooled inhaled "
        "particles per exposure event, against N50 = 16,871. `sec/import` "
        "is pooled secondaries over pooled imports. Every `off` row must "
        "show zero flush events: the baseline is the item-42 "
        "`dwell_weighted` configuration with the route off.",
        "",
        "| platform | days | arm | f_aero | voyages | ev. v. | rec. v. "
        "| emitted | recipients | dose/exp | sec/import | mean sec | zero "
        "| flush % | fomite % | post/1,000 | posting CI | median pax AR |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
        "---|---|",
    ]
    for cell in report["cells"]:
        lines.extend(_arm_line(cell, arm) for arm in cell["arm_order"])
    lines.extend([
        "",
        f"## Paired contrasts (arm − {report['baseline_arm']}, seed by seed)",
        "",
        "`identical imports` must be 1.000: the flush route draws no rng of "
        "its own, so a pair whose boarding cohort moved is a leak rather "
        "than a result. `gained/lost` are McNemar's discordant postings.",
        "",
        "| platform | days | arm | seeds | identical imports "
        "| Δ flush exposures | Δ sec/import | × sec/import "
        "| Δ secondaries (CI) | Δ flush dominant | Δ margin (CI) "
        "| gained/lost | exact p |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ])
    for cell in report["cells"]:
        lines.extend(
            _contrast_line(cell, arm)
            for arm in cell["arm_order"]
            if arm != report["baseline_arm"]
        )
    lines.extend([
        "",
        "Observed comparators, reported and not fitted: A4 reported "
        "passenger AR over pre-2020 postings by hull, and A9 posting "
        "probability per 1,000 voyages.",
        "",
        "```json",
        json.dumps(report["observed_comparators"], indent=1, sort_keys=True),
        "```",
    ])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    return run_readout_cli(
        collect_rows=collect_rows,
        build_report=build_report,
        render_markdown=render_markdown,
        description=__doc__,
        default_title=DEFAULT_TITLE,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
