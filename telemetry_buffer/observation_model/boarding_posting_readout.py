"""What the introduction mechanism does to posting and to its spread.

The archived posting campaigns (``expedition_posting_v2``,
``hull_posting_v1``) declared ``fiat_index_case`` with one seeded host;
``boarding_posting_v1`` omits that key and lets ``engines/initiation.py``
draw an embarking cohort at the profile's own role-specific prevalence. The
mean reported incidence of the fiat arm already sits on A8's bands while its
posting frequency runs an order of magnitude above A9's short-voyage row, so
the quantity in question is not a level but a **between-voyage
distribution**: in the fiat arm most voyages stay at the index case and the
whole mean is carried by a thin tail of large epidemics.

This readout therefore measures, per design cell, three things rather than
two:

1. **Posting frequency** on the VSP rule (reported cases reaching
   ``POSTING_THRESHOLD`` in passengers *or* crew), with the passenger-only
   and crew-only channels separated, because the or-rule lets a voyage post
   on a handful of crew and A9's numerator is effectively the passenger
   channel.
2. **The level conditional on posting** -- the reported passenger attack
   rate VSP publishes and A4 targets, beside the infection attack rate on
   the same voyages, so a departure stays separable into transmission and
   ascertainment.
3. **The spread across voyages**: how many voyages carry no onward
   transmission at all, the quantiles of secondary infections, the share of
   all secondary infections held by the largest 1% and 10% of voyages, and
   the variance-to-mean ratio. These are what distinguish an all-or-nothing
   establishment lottery from a process that spreads the same mean over many
   voyages, and none of them is visible in a mean or in a posting count.

*Secondary* infections are infections net of the boarding cohort, read from
each run's realised draw (``resolved_pathogen_profiles.json``) rather than
from the configured prevalence, because the draw is stochastic and the
imports would otherwise be counted as transmission. In the fiat arm the
import count is the declared ``n_init``.

Cells are keyed by the boarding coordinates as well as by platform,
surveillance, release scale and voyage length: the campaign sweeps the two
sourced prevalence intervals at their corners and the Grade C presymptomatic
share, and pooling across those would report a mixture. Nothing here selects,
fits or adopts anything; A4 and A9 are printed beside the measured values.

    python3 -m telemetry_buffer.observation_model.boarding_posting_readout \\
        --arm boarding=telemetry_buffer/boarding_posting_v1 \\
        --arm fiat=telemetry_buffer/hull_posting_v1 \\
        --out telemetry_buffer/observation_model/boarding_posting_v1.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from simulation_utils.paths import resolve_repo_path, validated_open
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
SUMMARY_NAME = "summary.json"
PROFILE_NAME = "resolved_pathogen_profiles.json"

# Tail shares are reported at these two depths: 1% isolates the handful of
# runaway voyages that carry the fiat arm's mean, 10% is the conventional
# decile and is robust at a 450-voyage cell.
TAIL_FRACTIONS = (0.01, 0.10)

BOARDING_KEYS = (
    "boarding_passenger_prevalence",
    "boarding_crew_prevalence",
    "presymptomatic_share_of_presenting",
    "never_symptomatic_fraction",
)


def _run_dirs(archive: zipfile.ZipFile) -> dict[str, str]:
    """Map each run's directory prefix to its summary member name."""
    found: dict[str, str] = {}
    for name in archive.namelist():
        if name == SUMMARY_NAME:
            found[""] = name
        elif name.endswith(f"/{SUMMARY_NAME}"):
            found[name[: -len(SUMMARY_NAME)]] = name
    return found


def _read_json(archive: zipfile.ZipFile, name: str) -> dict[str, Any] | None:
    try:
        return dict(json.loads(archive.read(name)))
    except KeyError:
        return None


def _pairs(path: Path) -> Iterable[tuple[dict[str, Any], dict[str, Any] | None]]:
    """Yield each run's summary beside its resolved profile, if present."""
    with zipfile.ZipFile(path) as archive:
        for prefix, summary_name in _run_dirs(archive).items():
            summary = _read_json(archive, summary_name)
            if summary is None:
                continue
            yield summary, _read_json(archive, f"{prefix}{PROFILE_NAME}")


def _drawn(profile: dict[str, Any] | None) -> dict[str, Any]:
    """The realised infectious boarding cohort, or empty when fiat-seeded.

    ``drawn_by_role`` counts infectious introductions; the full drawn
    RNA-positive cohort — including any ``cleared`` hosts, which carry no
    infection record — lives in ``composition``.
    """
    initiation = (profile or {}).get("initiation") or {}
    boarding = initiation.get("boarding") or {}
    drawn = {"passenger": 0, "crew": 0, "composition": {}, "mode": None}
    for pathogen_id, record in boarding.items():
        roles = record.get("drawn_by_role") or {}
        drawn["passenger"] += int(roles.get("passenger", 0))
        drawn["crew"] += int(roles.get("crew", 0))
        drawn["composition"] = record.get("composition") or {}
        drawn["mode"] = (initiation.get("boarding_mode") or {}).get(pathogen_id)
    drawn["initiation_mode"] = initiation.get("mode")
    return drawn


def _counts(derived: dict[str, Any]) -> dict[str, int]:
    """Head-counts behind the summary's attack-rate fractions."""
    pax = int(derived.get("passenger_complement") or 0)
    crew = int(derived.get("crew_complement") or 0)
    return {
        "passenger_complement": pax,
        "crew_complement": crew,
        "reported_cases_passenger": round(
            float(derived["reported_case_attack_rate_passenger"]) * pax,
        ),
        "infections_passenger": round(
            float(derived["infection_attack_rate_passenger"]) * pax,
        ),
        "infections_crew": round(
            float(derived.get("infection_attack_rate_crew") or 0.0) * crew,
        ),
    }


def _row(summary: dict[str, Any], profile: dict[str, Any] | None) -> dict[str, Any]:
    params = summary["parameters"]
    derived = summary["derived"]
    drawn = _drawn(profile)
    counts = _counts(derived)
    imported = drawn["passenger"] + drawn["crew"]
    if drawn["initiation_mode"] != "boarding":
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
        "initiation_mode": drawn["initiation_mode"] or "fiat",
        "imported": imported,
        "imported_passenger": drawn["passenger"],
        "imported_crew": drawn["crew"],
        "composition": drawn["composition"],
        "infections_total": infections,
        "secondary_infections": max(infections - imported, 0),
        "peak_prevalence": derived.get("peak_prevalence"),
    }
    row.update(counts)
    row.update({key: params.get(key) for key in BOARDING_KEYS})
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
        *(row[key] for key in BOARDING_KEYS),
    )


def _tail_share(values: list[int], fraction: float) -> float | None:
    """Share of the total held by the largest ``fraction`` of voyages."""
    total = sum(values)
    if not values or total <= 0:
        return None
    take = max(1, round(len(values) * fraction))
    ordered = sorted(values, reverse=True)[:take]
    return sum(ordered) / total


def _dispersion(values: list[int]) -> dict[str, Any]:
    """How unevenly onward transmission is spread across voyages."""
    if not values:
        return {"n": 0}
    mean = statistics.fmean(values)
    variance = statistics.pvariance(values) if len(values) > 1 else 0.0
    quantiles = sorted(values)
    def at(p: float) -> int:
        return quantiles[min(len(quantiles) - 1, int(p * len(quantiles)))]
    record: dict[str, Any] = {
        "n": len(values),
        "mean": mean,
        "fraction_zero": sum(1 for value in values if value == 0) / len(values),
        "median": statistics.median(values),
        "p90": at(0.90),
        "p99": at(0.99),
        "max": max(values),
        "variance_to_mean": variance / mean if mean > 0 else None,
    }
    for fraction in TAIL_FRACTIONS:
        label = f"top_{int(fraction * 100)}pct_share"
        record[label] = _tail_share(values, fraction)
    return record


def _imports(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The realised boarding cohort, averaged over the cell's voyages."""
    if not rows:
        return {}
    states = ("never_symptomatic", "presymptomatic", "convalescent", "incubating")
    record: dict[str, Any] = {
        "mean_imported_passenger": statistics.fmean(
            [row["imported_passenger"] for row in rows],
        ),
        "mean_imported_crew": statistics.fmean(
            [row["imported_crew"] for row in rows],
        ),
        "mean_imported_total": statistics.fmean([row["imported"] for row in rows]),
    }
    for state in states:
        record[f"mean_{state}"] = statistics.fmean(
            [float((row["composition"] or {}).get(state, 0)) for row in rows],
        )
    return record


def summarise_cell(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Posting frequency, the posting-conditional levels, and the spread."""
    trials = len(rows)
    posted = [row for row in rows if row["posted"]]
    crew_only = [row for row in rows if row["posted_crew"] and not row["posted_passenger"]]
    cell: dict[str, Any] = {
        "n_voyages": trials,
        "n_posted": len(posted),
        "n_posted_passenger_channel": sum(row["posted_passenger"] for row in rows),
        "n_posted_crew_only": len(crew_only),
        "posting_frequency": len(posted) / trials if trials else None,
        "posting_frequency_ci95": jeffreys_interval(len(posted), trials),
        "posting_frequency_per_1000": (
            1000.0 * len(posted) / trials if trials else None
        ),
        "imports": _imports(rows),
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
    return cell


def _cell_header(key: tuple[Any, ...]) -> dict[str, Any]:
    arm, platform, surveillance, dose, epochs = key[:5]
    header = {
        "arm": arm,
        "platform_id": platform,
        "surveillance": surveillance,
        "environmental_faecal_release_log10_g_per_epoch": dose,
        "num_epochs": epochs,
        # clock-exempt: num_epochs counts 1-hour epochs in this campaign, so
        # the division is an hours-to-days presentation conversion.
        "voyage_days": epochs / 24.0,  # clock-exempt: epochs->days
    }
    header.update(dict(zip(BOARDING_KEYS, key[5:])))
    return header


def build_report(rows: list[dict[str, Any]], era: str) -> dict[str, Any]:
    """One cell per design point, with the observed comparators attached."""
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
        "tail_fractions": list(TAIL_FRACTIONS),
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


def _table_row(cell: dict[str, Any]) -> str:
    spread = cell["secondary_infection_spread"]
    conditional = cell["conditional_on_posting"][
        "reported_case_attack_rate_passenger"
    ]
    return (
        f"| {cell['arm']} "
        f"| {cell['platform_id']} "
        f"| {cell['surveillance']} "
        f"| {_fmt(cell['environmental_faecal_release_log10_g_per_epoch'], 1)} "
        f"| {_fmt(cell['voyage_days'], 1)} "
        f"| {_fmt(cell['boarding_passenger_prevalence'], 4)}"
        f"/{_fmt(cell['boarding_crew_prevalence'], 4)} "
        f"| {_fmt(cell['presymptomatic_share_of_presenting'], 3)} "
        f"| {cell['n_voyages']} "
        f"| {_fmt(cell['posting_frequency_per_1000'], 1)} "
        f"| {cell['n_posted_crew_only']} "
        f"| {_fmt(cell['imports'].get('mean_imported_total'), 2)} "
        f"| {_fmt(spread.get('mean'), 1)} "
        f"| {_fmt(spread.get('fraction_zero'))} "
        f"| {_fmt(spread.get('top_10pct_share'))} "
        f"| {_fmt(spread.get('variance_to_mean'), 1)} "
        f"| {_fmt(conditional['median'], 4)} |"
    )


def render_markdown(report: dict[str, Any]) -> str:
    """One row per cell: posting rate, import cohort, and spread."""
    lines = [
        "# Introduction mechanism, posting frequency and between-voyage spread",
        "",
        f"Posting rule: reported cases >= {report['posting_threshold']:.0%} of "
        "passengers or of crew. `secondary` infections are infections net of "
        "the realised boarding cohort, so the import is not counted as "
        "transmission. `zero` is the fraction of voyages with no onward "
        "transmission at all and `top10%` the share of all secondary "
        "infections held by the largest tenth of voyages; together they say "
        "whether the mean is carried by a thin tail.",
        "",
        "| arm | platform | surv | release | days | prev pax/crew | presympt "
        "| voyages | post/1,000 | crew-only | mean imports | mean secondary "
        "| zero | top10% | var/mean | median pax AR |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
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
