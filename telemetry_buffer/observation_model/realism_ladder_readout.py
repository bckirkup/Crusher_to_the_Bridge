"""What each rung of the introduction realism chain does to posting.

``realism_ladder_v1`` steps one mechanism at a time against matched seeds:
``shipped`` (the screening prevalence midpoints, the authored age window, a
point illness duration, no symptomatic boarder, no pre-boarding assessment)
is reproduced by ``boarding_posting_v1``'s runs and is not re-run here;
``renewal_stationary`` replaces the import rate with the incidence-duration
identity and the age draw with a stationary one over the detectable window;
``symptomatic`` partitions that rate into an ill-at-embarkation stream; and
``reportable`` adds the VSP §4.1.1.2 crew clause, whose declared onsets
inside three days are reportable AGE cases at epoch 0.

Because each rung is a different *mechanism* rather than a different value
of one coordinate, this readout keeps three quantities separable per cell:

1. **Posting frequency** on the VSP rule, with the passenger channel and
   the crew-only channel split, because the or-rule lets a voyage post on a
   handful of crew while A9's numerator is effectively the passenger
   channel — and the §4.1.1.2 clause writes only into the crew channel.
2. **The realised import cohort**: how many hosts actually board infected
   by role, the composition including the ``cleared`` hosts a stationary
   draw exposes and the ``symptomatic`` hosts the partition creates, so a
   change in posting stays attributable to the cohort that produced it.
3. **The screen's own tallies**: eligible, declared, screened out and
   pre-boarding reportable per role, straight off the initiation manifest.
   At p_sym of order 1e-4 the eligible count is a rare event, so the cell
   reports the per-voyage mean *and* the count of voyages with any eligible
   host, with a Jeffreys interval on the latter — a mean alone cannot say
   whether a zero is structural or sampling.

Nothing here selects, fits or adopts anything: A4 and A9 are printed beside
the measured values, never used to choose one.

    python3 -m telemetry_buffer.observation_model.realism_ladder_readout \\
        --arm shipped=telemetry_buffer/boarding_posting_v1 \\
        --arm ladder=telemetry_buffer/realism_ladder_v1 \\
        --out telemetry_buffer/observation_model/realism_ladder_v1.json \\
        --markdown docs/norovirus/realism_ladder_v1_readout.md
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from simulation_utils.paths import resolve_repo_path, validated_open
from telemetry_buffer.observation_model.boarding_posting_readout import (
    BOARDING_KEYS,
    _counts,
    _dispersion,
    _pairs,
)
from telemetry_buffer.observation_model.expedition_posting_readout import (
    LEVEL_KEYS,
    _spread,
    jeffreys_interval,
)
from telemetry_buffer.observation_model.midrs_incidence_targets import a9_targets
from telemetry_buffer.observation_model.vsp_class_era_scoring import (
    POSTING_THRESHOLD,
    vsp_attack_rate_targets,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# A run that names no rung predates the ladder: the archived posting
# campaigns are the shipped mechanism by construction, which is why they are
# reused as the ladder's first rung rather than re-run.
DEFAULT_RUNG = "shipped"

# The mechanism coordinates a run records. They are what the cell is keyed
# by, so two rungs are never pooled into one row.
MECHANISM_KEYS = (
    "boarding_mechanism_rung",
    "boarding_rate_mode",
    "boarding_age_draw",
    "illness_duration_draw",
    "symptomatic_stream",
)

# The screen's swept coordinates. Absent keys mean the tier did not sweep
# them, and the cell header then carries None rather than a fabricated point.
SCREEN_KEYS = (
    "preboarding_crew_declaration_compliance",
    "preboarding_crew_recall_halflife_days",
    "preboarding_crew_denial_probability",
    "preboarding_crew_reportable",
    "preboarding_passenger_declaration_compliance",
    "preboarding_passenger_recall_halflife_days",
    "preboarding_passenger_denial_probability",
)

# Every boarding state the composition can carry. ``cleared`` exists only
# under the stationary age draw (an RNA-positive host past its shedding
# window boards with no infection record) and ``symptomatic`` only under the
# partitioned rate, so a zero here is itself a mechanism readout.
COMPOSITION_STATES = (
    "never_symptomatic",
    "presymptomatic",
    "convalescent",
    "incubating",
    "symptomatic",
    "cleared",
    "screened_out",
)

# The complement and contact-kernel coordinates the hull-compounding
# campaign moves. ``num_agents`` is recorded on every run; the kernel
# coordinates are absent in the older archives and read as None there.
ARCHITECTURE_KEYS = (
    "num_agents",
    "contact_class_exponent",
    "density_exponent",
    "contact_mode",
)

TALLY_KEYS = ("eligible", "declared", "screened_out", "preboarding_reportable")
ROLES = ("passenger", "crew")


def _boarding_entry(profile: dict[str, Any] | None) -> dict[str, Any]:
    """The initiation manifest's boarding entry, pooled over pathogens."""
    initiation = (profile or {}).get("initiation") or {}
    boarding = initiation.get("boarding") or {}
    entry: dict[str, Any] = {
        "mode": initiation.get("mode"),
        "drawn": dict.fromkeys(ROLES, 0),
        "composition": {},
        "assessment": None,
    }
    for record in boarding.values():
        roles = record.get("drawn_by_role") or {}
        for role in ROLES:
            entry["drawn"][role] += int(roles.get(role, 0))
        entry["composition"] = record.get("composition") or {}
        if record.get("preboarding_assessment") is not None:
            entry["assessment"] = record["preboarding_assessment"]
    return entry


def _tallies(assessment: dict[str, Any] | None) -> dict[str, int]:
    """Per-role screen counts; zeros when the arm is off, not absences.

    A disabled role genuinely saw nobody, so zero is the honest reading; an
    absent assessment block is the same statement about both roles.
    """
    counts: dict[str, int] = {}
    for role in ROLES:
        block = (assessment or {}).get(role) or {}
        for key in TALLY_KEYS:
            counts[f"{role}_{key}"] = int(block.get(key, 0))
    return counts


def _row(summary: dict[str, Any], profile: dict[str, Any] | None) -> dict[str, Any]:
    """One voyage, flattened to the coordinates and the outcomes."""
    params = summary["parameters"]
    derived = summary["derived"]
    entry = _boarding_entry(profile)
    counts = _counts(derived)
    imported = sum(entry["drawn"].values())
    if entry["mode"] != "boarding":
        imported = int(params.get("n_init") or 0)
    infections = counts["infections_passenger"] + counts["infections_crew"]
    row: dict[str, Any] = {
        "run_id": summary["run_id"],
        "tier_id": params.get("tier_id"),
        "platform_id": params["platform_id"],
        "surveillance": params.get("surveillance"),
        "dose_adjustment": params.get("dose_adjustment"),
        "num_epochs": params["num_epochs"],
        "seed": params["seed"],
        "initiation_mode": entry["mode"] or "fiat",
        "imported": imported,
        "imported_passenger": entry["drawn"]["passenger"],
        "imported_crew": entry["drawn"]["crew"],
        "infections_total": infections,
        "secondary_infections": max(infections - imported, 0),
    }
    row.update(counts)
    row.update(_tallies(entry["assessment"]))
    for state in COMPOSITION_STATES:
        row[f"composition_{state}"] = int((entry["composition"] or {}).get(state, 0))
    row["boarding_mechanism_rung"] = params.get(
        "boarding_mechanism_rung", DEFAULT_RUNG,
    )
    for key in (
        MECHANISM_KEYS[1:] + SCREEN_KEYS + BOARDING_KEYS + ARCHITECTURE_KEYS
    ):
        row[key] = params.get(key)
    for key in LEVEL_KEYS:
        row[key] = float(derived[key])
    row["posted_passenger"] = (
        row["reported_case_attack_rate_passenger"] >= POSTING_THRESHOLD
    )
    row["posted_crew"] = (
        row["reported_case_attack_rate_crew"] >= POSTING_THRESHOLD
    )
    row["posted"] = row["posted_passenger"] or row["posted_crew"]
    return row


def collect_rows(root: Path, arm: str) -> list[dict[str, Any]]:
    """Flatten every run under ``root`` into one row per voyage."""
    rows = []
    for archive in sorted(root.rglob("*.zip")):
        for summary, profile in _pairs(archive):
            row = _row(summary, profile)
            row["arm"] = arm
            rows.append(row)
    return rows


def _cell_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["arm"],
        row["platform_id"],
        row["surveillance"],
        row["dose_adjustment"],
        row["num_epochs"],
        *(row[key] for key in MECHANISM_KEYS),
        *(row[key] for key in SCREEN_KEYS),
        # The archived shipped arm swept the prevalence corners and the
        # state split; pooling them would average two mechanisms' cells
        # into one row and hide the corner that produced a posting rate.
        *(row[key] for key in BOARDING_KEYS),
        # Complement and kernel: constant inside every archived cell, the
        # coordinates the hull-compounding cells differ in.
        *(row[key] for key in ARCHITECTURE_KEYS),
    )


def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
    return statistics.fmean([float(row[key]) for row in rows]) if rows else None


def _any_count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row[key] > 0)


def _imports(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The realised cohort, per voyage, with the composition it resolved to."""
    record: dict[str, Any] = {
        "mean_imported_passenger": _mean(rows, "imported_passenger"),
        "mean_imported_crew": _mean(rows, "imported_crew"),
        "mean_imported_total": _mean(rows, "imported"),
    }
    for state in COMPOSITION_STATES:
        record[f"mean_{state}"] = _mean(rows, f"composition_{state}")
    return record


def _screen(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The assessment's tallies: per-voyage means and rare-event counts.

    ``voyages_with_any`` and its interval are the point of this block. An
    eligible host needs a symptomatic boarder, which at p_sym of order 1e-4
    is a rare event; a per-voyage mean of 0.01 and a structural zero are
    different findings and a mean cannot distinguish them.
    """
    trials = len(rows)
    record: dict[str, Any] = {"n_voyages": trials}
    for role in ROLES:
        for key in TALLY_KEYS:
            column = f"{role}_{key}"
            with_any = _any_count(rows, column)
            record[column] = {
                "mean_per_voyage": _mean(rows, column),
                "total": sum(row[column] for row in rows),
                "voyages_with_any": with_any,
                "voyages_with_any_ci95": jeffreys_interval(with_any, trials),
            }
    return record


def summarise_cell(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Posting frequency, the posting-conditional levels, and the spread."""
    trials = len(rows)
    posted = [row for row in rows if row["posted"]]
    crew_only = [
        row for row in rows
        if row["posted_crew"] and not row["posted_passenger"]
    ]
    return {
        "n_voyages": trials,
        "n_posted": len(posted),
        "n_posted_passenger_channel": sum(row["posted_passenger"] for row in rows),
        "n_posted_crew_channel": sum(row["posted_crew"] for row in rows),
        "n_posted_crew_only": len(crew_only),
        "posting_frequency": len(posted) / trials if trials else None,
        "posting_frequency_ci95": jeffreys_interval(len(posted), trials),
        "posting_frequency_per_1000": (
            1000.0 * len(posted) / trials if trials else None
        ),
        "imports": _imports(rows),
        "preboarding_assessment": _screen(rows),
        "secondary_infection_spread": _dispersion(
            [row["secondary_infections"] for row in rows],
        ),
        "reported_passenger_case_spread": _dispersion(
            [row["reported_cases_passenger"] for row in rows],
        ),
        "conditional_on_posting": {
            key: _spread([row[key] for row in posted]) for key in LEVEL_KEYS
        },
        "unconditional": {
            key: _spread([row[key] for row in rows]) for key in LEVEL_KEYS
        },
    }


def _cell_header(key: tuple[Any, ...]) -> dict[str, Any]:
    arm, platform, surveillance, dose, epochs = key[:5]
    header: dict[str, Any] = {
        "arm": arm,
        "platform_id": platform,
        "surveillance": surveillance,
        "environmental_faecal_release_log10_g_per_epoch": dose,
        "num_epochs": epochs,
        # clock-exempt: num_epochs counts 1-hour epochs in this campaign, so
        # the division is an hours-to-days presentation conversion.
        "voyage_days": epochs / 24.0,  # clock-exempt: epochs->days
    }
    header.update(
        dict(zip(
            MECHANISM_KEYS + SCREEN_KEYS + BOARDING_KEYS + ARCHITECTURE_KEYS,
            key[5:],
        )),
    )
    return header


def build_report(rows: list[dict[str, Any]], era: str) -> dict[str, Any]:
    """One cell per mechanism rung and screen point."""
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_cell_key(row)].append(row)
    cells = []
    for key in sorted(grouped, key=lambda k: tuple(str(part) for part in k)):
        cell = _cell_header(key)
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


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _screen_cell(cell: dict[str, Any], role: str, key: str) -> str:
    """``mean/voyages-with-any`` for one tally, as the table prints it."""
    block = cell["preboarding_assessment"][f"{role}_{key}"]
    return f"{_fmt(block['mean_per_voyage'], 3)}/{block['voyages_with_any']}"


def _table_row(cell: dict[str, Any]) -> str:
    spread = cell["secondary_infection_spread"]
    conditional = cell["conditional_on_posting"][
        "reported_case_attack_rate_passenger"
    ]
    imports = cell["imports"]
    return (
        f"| {cell['boarding_mechanism_rung']} "
        f"| {cell['platform_id']} "
        f"| {_fmt(cell['voyage_days'], 1)} "
        f"| {_fmt(cell['boarding_passenger_prevalence'], 4)}"
        f"/{_fmt(cell['boarding_crew_prevalence'], 4)} "
        f"| {_fmt(cell['preboarding_crew_declaration_compliance'], 2)}"
        f"/{_fmt(cell['preboarding_crew_recall_halflife_days'], 1)}"
        f"/{_fmt(cell['preboarding_crew_denial_probability'], 2)} "
        f"| {cell['n_voyages']} "
        f"| {_fmt(cell['posting_frequency_per_1000'], 1)} "
        f"| {cell['n_posted_crew_only']} "
        f"| {_fmt(imports.get('mean_imported_total'), 2)} "
        f"| {_fmt(imports.get('mean_symptomatic'), 3)} "
        f"| {_fmt(imports.get('mean_cleared'), 2)} "
        f"| {_screen_cell(cell, 'crew', 'eligible')} "
        f"| {_screen_cell(cell, 'crew', 'declared')} "
        f"| {_screen_cell(cell, 'crew', 'preboarding_reportable')} "
        f"| {_screen_cell(cell, 'crew', 'screened_out')} "
        f"| {_fmt(spread.get('mean'), 1)} "
        f"| {_fmt(spread.get('fraction_zero'))} "
        f"| {_fmt(conditional['median'], 4)} |"
    )


def render_markdown(report: dict[str, Any]) -> str:
    """One row per rung and screen point."""
    lines = [
        "# The introduction realism ladder: what each rung does to posting",
        "",
        f"Posting rule: reported cases >= {report['posting_threshold']:.0%} of "
        "passengers or of crew. `secondary` infections are infections net of "
        "the realised boarding cohort. Screen columns are "
        "`mean per voyage / voyages with any`, because an eligible host "
        "needs a symptomatic boarder and a per-voyage mean cannot "
        "distinguish a rare event from a structural zero. `crew c/h/d` is "
        "the declaration compliance, recall half-life in days and denial "
        "probability the cell was run at; `n/a` means the tier did not "
        "sweep that coordinate.",
        "",
        "| rung | platform | days | prev pax/crew | crew c/h/d | voyages "
        "| post/1,000 | crew-only | imports | sympt | cleared | eligible "
        "| declared | reportable | denied | mean secondary | zero "
        "| median pax AR |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
        "---|---|",
    ]
    lines.extend(_table_row(cell) for cell in report["cells"])
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
    parser.add_argument("--arm", action="append", required=True, type=_parse_arm,
                        help="name=results_root, repeatable")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
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
    markdown = render_markdown(report)
    if args.markdown:
        _write(args.markdown, markdown)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
