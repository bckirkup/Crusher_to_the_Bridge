"""Score simulation output against the anchors A1-A5, A8 and A9.

Reads run zips produced by the campaign runner and reports, per
hull x response x dose cell and conditional on take-off, the anchor
quantities defined in ``anchor_measurement_spec.md``.  Ratios are reported
both per-seed (median of ratios) and as a ratio of cell medians, because the
two diverge whenever a denominator is small.

A1, A2 and A5 are literature targets.  A3 is a construction constraint of the
observation layer rather than independent evidence
(``docs/norovirus/norovirus_parameter_freedom_audit.md``), so it is reported
as a diagnostic band and carries no verdict: the observation model's own
parameters are what put reported/symptomatic where it is, and a quantity the
layer was built to produce cannot also test the layer.  A4's target is not
a literature figure at all: it is derived at runtime, per hull class and per
era, from ``vsp_outbreak_series.csv`` by ``vsp_class_era_scoring.py``, and a
hull with too few postings gets no A4 verdict.

Usage:
    python3 -m telemetry_buffer.observation_model.score_anchors \
        <results-root> [--out report.md] [--vsp-era pre|post]

``<results-root>`` is a directory searched recursively for ``*.zip`` runs,
each containing ``summary.json`` with ``parameters`` and ``derived`` blocks.
A8 is unconditional incidence per 100,000 travel-days and A9 is unconditional
VSP posting probability, both sourced from the MIDRS record.
"""

from __future__ import annotations

import argparse
import json
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from engines.sim_clock import HOURS, HOURS_PER_DAY, LEGACY_EPOCH_DAY, SimClock
from simulation_utils.paths import validated_open
from telemetry_buffer.observation_model.midrs_incidence_targets import (
    HULL_TO_GRT_BAND,
    MIDRS_DENOMINATOR_UNIT,
    MIDRS_DENOMINATOR_WINDOW,
    MIDRS_TOTAL_VOYAGES,
    UNMAPPED_GRT_BANDS,
    a8_targets,
    a9_targets,
)
from telemetry_buffer.observation_model.vsp_class_era_scoring import (
    HULL_PASSENGER_CAPACITY,
    MIN_POSTINGS_FOR_TARGET,
    SCORED_ERAS,
    vsp_attack_rate_targets,
)

SUMMARY_NAME = "summary.json"
TAKEOFF_PEAK_PREVALENCE = 10
A9_POSTING_THRESHOLD = 0.03
A8_A9_NO_REPORTING = (
    "undefined (arm does not model reporting: sick_call_probability = 0)"
)

# A1 Wikswo whole-ship cohort illness; A2 asymptomatic ratio (GII.4-weighted
# lower bound 0.59); A5 passenger:crew reported ratio.
ANCHORS: dict[str, tuple[float, float]] = {
    "A1_ever_ill_passenger": (0.10, 0.22),
    "A2_ill_per_infected": (0.59, 0.81),
    "A5_passenger_crew_ratio": (2.5, 4.5),
}

# A3 is reported over *symptomatic*, because that is the denominator this
# scorer has: the 0.60 infirmary-capture figure is reported over AGE-eligible,
# and the five-state observation layer puts reported/symptomatic at 0.40 for
# the same parameter set (eligibility [0,.55,.98,1,1] absorbs the difference).
# Reported/eligible is not available here because the runs do not emit an
# AGE-eligible count.
#
# The 0.35-0.45 band is therefore what the observation layer's own capture and
# eligibility parameters construct, not an independent measurement of it, so
# it is a construction band and not an anchor: it is reported beside the
# measured ratio and excluded from every verdict. Scoring it would test the
# observation model against a target derived from the observation model.
CONSTRUCTION_BANDS: dict[str, tuple[float, float]] = {
    "A3_reported_per_symptomatic": (0.35, 0.45),
}
IN_BAND = "in band (not scored)"
OUT_OF_BAND = "out of band (not scored)"
BAND_UNDEFINED = "n/a (not scored)"


def load_summary(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read(SUMMARY_NAME))


def _summary_entries(path: Path) -> list[tuple[str, dict[str, Any]]]:
    """Read root summaries and summaries nested in fused shard archives."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        summary_names = [
            name for name in names
            if name == SUMMARY_NAME or name.endswith(f"/{SUMMARY_NAME}")
        ]
        return [
            (
                f"{path}!{name}" if name != SUMMARY_NAME else str(path),
                json.loads(archive.read(name)),
            )
            for name in summary_names
        ]


def _valid_complement(value: Any) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
    )


def _recover_complements(
    summary: dict[str, Any],
    num_agents: int,
) -> tuple[int, int] | None:
    """Recover complements from pre-complement archives using rounded rates."""
    summary_values = summary.get("summary", {})
    pairs = (
        (
            "cumulative_ever_infected_passenger",
            "infection_attack_rate_passenger",
            "cumulative_ever_infected_crew",
            "infection_attack_rate_crew",
        ),
        (
            "cumulative_ever_ill_passenger",
            "ever_ill_rate_passenger",
            "cumulative_ever_ill_crew",
            "ever_ill_rate_crew",
        ),
        (
            "cumulative_reported_cases_passenger",
            "reported_case_rate_passenger",
            "cumulative_reported_cases_crew",
            "reported_case_rate_crew",
        ),
    )
    for pax_count_key, pax_rate_key, crew_count_key, crew_rate_key in pairs:
        pax_rate = summary_values.get(pax_rate_key, 0.0)
        crew_rate = summary_values.get(crew_rate_key, 0.0)
        pax_count = summary_values.get(pax_count_key)
        crew_count = summary_values.get(crew_count_key)
        if not pax_rate or not crew_rate or pax_count is None or crew_count is None:
            continue
        try:
            passenger = round(float(pax_count) / float(pax_rate))
            crew = round(float(crew_count) / float(crew_rate))
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if (
            _valid_complement(passenger)
            and _valid_complement(crew)
            and passenger + crew == num_agents
            and round(float(pax_count) / passenger, 6) == pax_rate
            and round(float(crew_count) / crew, 6) == crew_rate
        ):
            return passenger, crew
    return None


def _resolve_complements(
    summary: dict[str, Any],
    num_agents: int,
    path: str,
) -> tuple[int, int]:
    """Prefer emitted complements, with legacy recovery as a fallback."""
    derived = summary.get("derived", {})
    explicit = (
        derived.get("passenger_complement"),
        derived.get("crew_complement"),
    )
    if any(value is not None for value in explicit):
        if not all(_valid_complement(value) for value in explicit):
            raise RuntimeError(f"{path} has invalid emitted role complements")
        passenger, crew = explicit
        if passenger + crew != num_agents:
            raise RuntimeError(
                f"{path} has role complements that do not sum to "
                f"num_agents ({num_agents})",
            )
        recovered = _recover_complements(summary, num_agents)
        if recovered is not None and recovered != (passenger, crew):
            raise RuntimeError(
                f"{path} emitted role complements disagree with recoverable "
                "summary complements",
            )
        return passenger, crew
    recovered = _recover_complements(summary, num_agents)
    if recovered is None:
        raise RuntimeError(
            f"{path} predates passenger_complement and its complements are "
            "unrecoverable",
        )
    return recovered


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator > 0 else None


def _hours_per_epoch(clock_name: str, path: Path) -> float:
    """Resolve the declared natural-history clock through ``SimClock``."""
    try:
        mode = str(clock_name)
        if mode == HOURS:
            return SimClock(epoch_duration_hours=1.0, mode=HOURS).hours_per_epoch
        if mode == LEGACY_EPOCH_DAY:
            return SimClock(mode=LEGACY_EPOCH_DAY).hours_per_epoch
    except ValueError as error:
        raise RuntimeError(f"{path} has invalid natural_history_clock") from error
    raise RuntimeError(f"{path} has invalid natural_history_clock: {clock_name!r}")


def _ingest_archive(
    path: Path,
    by_run_id: dict[str, tuple[dict[str, Any], str]],
    stats: dict[str, Any],
) -> None:
    """Fold every summary in one archive into the run index."""
    try:
        entries = _summary_entries(path)
    except (KeyError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        raise RuntimeError(f"{path} contains an unreadable summary") from error
    if not entries:
        stats["skipped_archives"].append(str(path))
        return
    for source_path, summary in entries:
        _index_run(_read_row(summary, source_path), source_path, by_run_id, stats)


def _index_run(
    row: dict[str, Any],
    source_path: str,
    by_run_id: dict[str, tuple[dict[str, Any], str]],
    stats: dict[str, Any],
) -> None:
    """Keep one row per run id, collapsing identical duplicate archives."""
    run_id = row["run_id"]
    previous = by_run_id.get(run_id)
    if previous is None:
        by_run_id[run_id] = (row, source_path)
        counter = (
            "runs_with_explicit_complements"
            if row["_complement_source"] == "explicit"
            else "runs_with_recovered_complements"
        )
        stats[counter] += 1
        return
    if _row_without_source(row) != _row_without_source(previous[0]):
        raise RuntimeError(
            f"conflicting duplicate run_id {run_id!r} in "
            f"{previous[1]} and {source_path}",
        )
    stats["duplicates_collapsed"] += 1


def read_rows(
    root: Path,
    archive_stats: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Collect rows, recovering complements only for pre-complement archives.

    The archive scan accepts both per-run zips and fused shard aggregates,
    deduplicating runs by ``run_id``.  Legacy archives use validated
    count/rate pairs in their summary to recover role complements.
    """
    rows: list[dict[str, Any]] = []
    stats = archive_stats if archive_stats is not None else {}
    stats.update({
        "archives_read": 0,
        "duplicates_collapsed": 0,
        "runs_with_recovered_complements": 0,
        "runs_with_explicit_complements": 0,
        "skipped_archives": [],
    })
    by_run_id: dict[str, tuple[dict[str, Any], str]] = {}
    for path in sorted(root.rglob("*.zip")):
        stats["archives_read"] += 1
        _ingest_archive(path, by_run_id, stats)
    rows.extend(row for row, _source in by_run_id.values())
    stats["runs_kept"] = len(rows)
    if not rows:
        skipped = ", ".join(stats["skipped_archives"])
        suffix = f"; skipped archives: {skipped}" if skipped else ""
        raise RuntimeError(f"no run zips found under {root}{suffix}")
    return rows


def _row_without_source(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key not in {"_source_path", "_complement_source"}
    }


def _era_coordinates(params: dict[str, Any], path: str) -> dict[str, float]:
    """The era sweep position a run was generated at, if it declares one.

    Coordinates are read as stated and not defaulted: a partially declared
    position is an error here rather than a silently completed box corner.
    """
    raw = params.get("era_coordinates", {})
    if not isinstance(raw, dict):
        raise RuntimeError(f"{path} has non-mapping era_coordinates: {raw!r}")
    out: dict[str, float] = {}
    for name, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeError(
                f"{path} era coordinate {name!r} is not numeric: {value!r}",
            )
        out[str(name)] = float(value)
    return out


def _read_row(summary: dict[str, Any], path: str) -> dict[str, Any]:
    """Build one scorer row from a root or nested archive summary."""
    params = summary.get("parameters", {})
    derived = summary.get("derived", {})
    required = (
        "num_epochs",
        "num_agents",
        "natural_history_clock",
        "sick_call_probability",
    )
    missing = [key for key in required if key not in params]
    if missing:
        raise RuntimeError(f"{path} missing parameters: {', '.join(missing)}")
    if "infection_attack_rate_passenger" not in derived:
        raise RuntimeError(
            f"{path} predates the denominator fix: no "
            "infection_attack_rate_passenger in derived",
        )
    ever_ill = float(derived["ever_ill_attack_rate_passenger"])
    infected = float(derived["infection_attack_rate_passenger"])
    reported = float(derived["reported_case_attack_rate_passenger"])
    reported_crew = float(derived["reported_case_attack_rate_crew"])
    hull = str(
        params.get("platform_id")
        or params.get("platform")
        or params.get("hull")
        or "",
    )
    if not hull:
        raise RuntimeError(
            f"{path} carries no hull identity: pooling hulls into one cell "
            "would silently average different complements",
        )
    strategy = str(params.get("surveillance") or "")
    if not strategy:
        raise RuntimeError(f"{path} carries no surveillance strategy")
    if hull not in HULL_PASSENGER_CAPACITY:
        raise RuntimeError(f"{path} carries unknown hull {hull!r}")
    complements_are_explicit = (
        derived.get("passenger_complement") is not None
    )
    passenger_complement, crew_complement = _resolve_complements(
        summary,
        int(params["num_agents"]),
        path,
    )
    hours_per_epoch = _hours_per_epoch(
        str(params["natural_history_clock"]),
        Path(path.split("!", maxsplit=1)[0]),
    )
    voyage_days = float(params["num_epochs"]) * hours_per_epoch / HOURS_PER_DAY
    if voyage_days <= 0:
        raise RuntimeError(f"{path} has non-positive voyage duration")
    return {
        "run_id": summary.get("run_id", path.split("!", maxsplit=1)[0]),
        "hull": hull,
        "strategy": strategy,
        "sick_call_probability": float(params["sick_call_probability"]),
        "dose_adjustment": float(params.get("dose_adjustment", 0.0)),
        # Which A7 arm the run belongs to, and where in the era's swept box it
        # sat.  Empty when the run was not produced by an era sweep; the joint
        # scorer (era_joint_scoring.py) refuses an unlabelled arm rather than
        # assuming one, because guessing the arm is guessing the train/test
        # split A7c is scored against.
        "era": str(params.get("era", "")),
        "era_coordinates": _era_coordinates(params, path),
        "seed": int(params.get("seed", -1)),
        "num_epochs": int(params["num_epochs"]),
        "num_agents": int(params["num_agents"]),
        "natural_history_clock": str(params["natural_history_clock"]),
        "hours_per_epoch": hours_per_epoch,
        "voyage_days": voyage_days,
        "passenger_complement": passenger_complement,
        "crew_complement": crew_complement,
        "_complement_source": (
            "explicit" if complements_are_explicit else "recovered"
        ),
        "peak_prevalence": int(derived.get("peak_prevalence", 0)),
        "took_off": int(derived.get("peak_prevalence", 0))
        >= TAKEOFF_PEAK_PREVALENCE,
        "A1_ever_ill_passenger": ever_ill,
        "infection_attack_rate_passenger": infected,
        "infection_attack_rate_crew": float(
            derived["infection_attack_rate_crew"],
        ),
        "reported_case_attack_rate_passenger": reported,
        "reported_case_attack_rate_crew": reported_crew,
        "ever_ill_attack_rate_crew": float(
            derived["ever_ill_attack_rate_crew"],
        ),
        "A2_ill_per_infected": _ratio(ever_ill, infected),
        "A3_reported_per_symptomatic": _ratio(reported, ever_ill),
        "A5_passenger_crew_ratio": _ratio(reported, reported_crew),
        "vsp_trigger_epoch": derived.get("vsp_trigger_epoch"),
        "_source_path": path,
    }


def _median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _run_reports_illness(row: dict[str, Any]) -> bool:
    """Whether a run models reporting at all.

    A run reports iff its ``sick_call_probability`` is strictly positive.  No
    tolerance is applied: reading a tiny-but-nonzero probability as report-free
    would hide a genuine zero prediction behind the no-reporting sentinel.
    """
    probability = row["sick_call_probability"]
    if probability < 0.0:
        raise RuntimeError(
            f"{row.get('_source_path', '<row>')} has a negative "
            f"sick_call_probability: {probability!r}",
        )
    return probability > 0.0


def _cell_is_report_free(rows: list[dict[str, Any]]) -> bool:
    """Whether a whole cell is report-free; a mixed cell has no A8/A9."""
    reporting = [_run_reports_illness(row) for row in rows]
    if any(reporting) and not all(reporting):
        raise RuntimeError(
            "cell mixes report-free and reporting runs; A8/A9 are undefined",
        )
    return not any(reporting)


def _a9_eligible_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Runs inside the MIDRS complement and voyage-length eligibility window."""
    return [
        row for row in rows
        if row["passenger_complement"] >= 100
        and 3.0 <= row["voyage_days"] <= 21.0
    ]


def _no_reporting_channels() -> dict[str, Any]:
    """A8/A9 fields for a cell whose arm does not model reporting."""
    return {
        "A8_pax_incidence": A8_A9_NO_REPORTING,
        "A8_crew_incidence": A8_A9_NO_REPORTING,
        "A9_posting_probability": A8_A9_NO_REPORTING,
        "A9_posted_eligible": 0,
        "A9_flag_disagreements": 0,
    }


def _a8_a9_channels(
    rows: list[dict[str, Any]],
    eligible: list[dict[str, Any]],
) -> dict[str, Any]:
    """Travel-day-weighted incidence and posting probability over all runs."""
    pax_case_days = sum(
        row["reported_case_attack_rate_passenger"] * row["passenger_complement"]
        for row in rows
    )
    crew_case_days = sum(
        row["reported_case_attack_rate_crew"] * row["crew_complement"]
        for row in rows
    )
    pax_travel_days = sum(
        row["passenger_complement"] * row["voyage_days"] for row in rows
    )
    crew_travel_days = sum(
        row["crew_complement"] * row["voyage_days"] for row in rows
    )
    posted = [
        row for row in eligible
        if row["reported_case_attack_rate_passenger"] >= A9_POSTING_THRESHOLD
        or row["reported_case_attack_rate_crew"] >= A9_POSTING_THRESHOLD
    ]
    disagreements = sum(
        (
            row["reported_case_attack_rate_passenger"] >= A9_POSTING_THRESHOLD
        ) != (row["vsp_trigger_epoch"] is not None)
        for row in rows
    )
    # Cases = reported rate × complement; travel-days = complement × days.
    # Dividing gives incidence = 1e5 × reported rate / voyage days.
    return {
        "A8_pax_incidence": 1e5 * pax_case_days / pax_travel_days,
        "A8_crew_incidence": 1e5 * crew_case_days / crew_travel_days,
        "A9_eligible_runs": len(eligible),
        "A9_posted_eligible": len(posted),
        "A9_flag_disagreements": disagreements,
        "A9_posting_probability": (
            len(posted) / len(eligible) if eligible else None
        ),
    }


def _add_conditional_medians(
    cell: dict[str, Any],
    took_off: list[dict[str, Any]],
) -> None:
    """Add the take-off-conditional anchor levels and ratios to a cell."""
    levels = [
        "A1_ever_ill_passenger",
        "infection_attack_rate_passenger",
        "infection_attack_rate_crew",
        "reported_case_attack_rate_passenger",
        "reported_case_attack_rate_crew",
        "ever_ill_attack_rate_crew",
    ]
    for key in levels:
        cell[key] = _median([row[key] for row in took_off])

    for key in ("A2_ill_per_infected", "A3_reported_per_symptomatic",
                "A5_passenger_crew_ratio"):
        defined = [row[key] for row in took_off if row[key] is not None]
        cell[f"{key}__per_seed_median"] = _median(defined)
        cell[f"{key}__n_defined"] = len(defined)
        cell[f"{key}__n_undefined"] = len(took_off) - len(defined)

    # Ratios of cell medians: same quantity, different order of operations.
    cell["A2_ill_per_infected__of_medians"] = _ratio(
        cell["A1_ever_ill_passenger"] or 0.0,
        cell["infection_attack_rate_passenger"] or 0.0,
    )
    cell["A3_reported_per_symptomatic__of_medians"] = _ratio(
        cell["reported_case_attack_rate_passenger"] or 0.0,
        cell["A1_ever_ill_passenger"] or 0.0,
    )
    cell["A5_passenger_crew_ratio__of_medians"] = _ratio(
        cell["reported_case_attack_rate_passenger"] or 0.0,
        cell["reported_case_attack_rate_crew"] or 0.0,
    )


def summarise_cell(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarise conditional anchors and unconditional A8/A9 channels."""
    took_off = [row for row in rows if row["took_off"]]
    cell: dict[str, Any] = {
        "n_seeds": len(rows),
        "n_takeoff": len(took_off),
        "takeoff_fraction": len(took_off) / len(rows) if rows else 0.0,
    }
    eligible = _a9_eligible_rows(rows)
    cell["A9_eligible_runs"] = len(eligible)
    cell["A9_ineligible_runs"] = len(rows) - len(eligible)
    no_reporting = _cell_is_report_free(rows)
    cell["A8_A9_no_reporting"] = no_reporting
    cell.update(
        _no_reporting_channels()
        if no_reporting
        else _a8_a9_channels(rows, eligible),
    )
    # Short aliases keep the JSON compact while retaining descriptive names.
    cell["A8_pax"] = cell["A8_pax_incidence"]
    cell["A8_crew"] = cell["A8_crew_incidence"]
    cell["A9"] = cell["A9_posting_probability"]
    if took_off:
        _add_conditional_medians(cell, took_off)
    return cell


A4_NO_TARGET = "n/a (insufficient VSP postings)"


def _conditional_anchor_verdicts(cell: dict[str, Any]) -> dict[str, str]:
    """PASS/FAIL for the take-off-conditional literature anchors."""
    out: dict[str, str] = {}
    for anchor, (low, high) in ANCHORS.items():
        value = cell.get(anchor) if anchor == "A1_ever_ill_passenger" else (
            cell.get(f"{anchor}__per_seed_median")
        )
        if value is None:
            out[anchor] = "n/a"
        else:
            out[anchor] = "PASS" if low <= value <= high else "FAIL"
    return out


def construction_band_states(cell: dict[str, Any]) -> dict[str, str]:
    """Where the construction-constrained ratios sit, without a verdict.

    A3 is what the observation layer's capture and eligibility parameters
    construct, so its band is a diagnostic: the states this returns never
    enter ``verdicts`` and never become a PASS or a FAIL.
    """
    out: dict[str, str] = {}
    for name, (low, high) in CONSTRUCTION_BANDS.items():
        value = cell.get(f"{name}__per_seed_median")
        if value is None:
            out[name] = BAND_UNDEFINED
        else:
            out[name] = IN_BAND if low <= value <= high else OUT_OF_BAND
    return out


def _a4_verdict(
    hull: str,
    cell: dict[str, Any],
    targets: dict[str, dict[str, float] | None],
) -> str:
    """PASS/FAIL of the posted reported attack rate against the VSP IQR."""
    target = targets.get(hull)
    if target is None:
        return A4_NO_TARGET
    reported = cell.get("reported_case_attack_rate_passenger")
    if reported is None:
        return "n/a"
    return "PASS" if target["q1"] <= reported <= target["q3"] else "FAIL"


def _endpoint_ratio(value: float, endpoint: float) -> float:
    return value / endpoint if endpoint else float("inf")


def _a8_verdict(
    hull: str,
    cell: dict[str, Any],
    era: str,
) -> tuple[str, dict[str, float]]:
    """A8 verdict plus its endpoint-keyed ratios for one hull's cell."""
    try:
        incidence_target = a8_targets(hull, era)
    except ValueError:
        incidence_target = None
    band = HULL_TO_GRT_BAND.get(hull)
    if incidence_target is None or band in UNMAPPED_GRT_BANDS:
        reason = (
            "n/a (GRT band has no project hull)"
            if band in UNMAPPED_GRT_BANDS
            else "n/a (unknown hull)"
        )
        return reason, {}
    pax_value = cell.get("A8_pax_incidence")
    crew_value = cell.get("A8_crew_incidence")
    if not isinstance(pax_value, (int, float)) or not isinstance(
        crew_value, (int, float)
    ):
        return "n/a", {}
    pax_target = incidence_target["passenger"]
    crew_target = incidence_target["crew"]
    ratios = {
        "A8_pax_ratio_to_end_of_period": _endpoint_ratio(
            pax_value, pax_target["end_of_period"],
        ),
        "A8_pax_ratio_to_pooled_band": _endpoint_ratio(
            pax_value, pax_target["pooled_band"],
        ),
        "A8_crew_ratio_to_end_of_period": _endpoint_ratio(
            crew_value, crew_target["end_of_period"],
        ),
        "A8_crew_ratio_to_pooled_band": _endpoint_ratio(
            crew_value, crew_target["pooled_band"],
        ),
    }
    # The two endpoints come from different stratifications, so the pair is
    # not ordered by construction; sorting keeps the band non-empty.
    pax_low, pax_high = sorted(
        (pax_target["end_of_period"], pax_target["pooled_band"]),
    )
    crew_low, crew_high = sorted(
        (crew_target["end_of_period"], crew_target["pooled_band"]),
    )
    inside = (
        pax_low <= pax_value <= pax_high
        and crew_low <= crew_value <= crew_high
    )
    return ("PASS" if inside else "FAIL"), ratios


def _a9_verdict(
    cell: dict[str, Any],
    era: str,
) -> tuple[str, dict[str, float]]:
    """A9 verdict plus its ratios against the investigated/posted interval."""
    target_a9 = a9_targets(era)
    if target_a9 is None:
        return "n/a (post arm has no MIDRS observation)", {}
    value = cell.get("A9_posting_probability")
    low, high = target_a9["fleet"]["interval"]
    if value is None or not isinstance(value, (int, float)):
        return "n/a (no eligible runs)", {}
    ratios = {
        "A9_ratio_to_investigated": value / (low / 1000),
        "A9_ratio_to_posted": value / (high / 1000),
    }
    return ("PASS" if low / 1000 <= value <= high / 1000 else "FAIL"), ratios


def verdicts(
    hull: str,
    cell: dict[str, Any],
    targets: dict[str, dict[str, float] | None],
    era: str = "pre",
) -> tuple[dict[str, str], dict[str, float]]:
    """PASS/FAIL per anchor on conditional and unconditional channels.

    ``targets`` comes from ``vsp_attack_rate_targets`` for the scored era; a
    hull whose target is ``None`` has too few postings to anchor A4 at all.
    """
    out = _conditional_anchor_verdicts(cell)
    out["A4_vsp_iqr"] = _a4_verdict(hull, cell, targets)
    ratios: dict[str, float] = {}
    if cell.get("A8_A9_no_reporting"):
        out["A8"] = f"n/a ({A8_A9_NO_REPORTING})"
        out["A9"] = f"n/a ({A8_A9_NO_REPORTING})"
        return out, ratios
    if era == "post":
        reason = "n/a (post arm has no MIDRS observation)"
        out["A8"] = reason
        out["A9"] = reason
        return out, ratios
    out["A8"], a8_ratios = _a8_verdict(hull, cell, era)
    out["A9"], a9_ratios = _a9_verdict(cell, era)
    ratios.update(a8_ratios)
    ratios.update(a9_ratios)
    return out, ratios


def _validated_report_path(path: Path, results_root: Path) -> Path:
    """Keep report writes inside the results tree supplied to the scorer."""
    resolved = path.expanduser().resolve()
    root = results_root.expanduser().resolve()
    if root not in resolved.parents:
        raise ValueError("report path must be inside results_root")
    return resolved


def _write_report(
    output_path: Path,
    report: str,
    rows: list[dict[str, Any]],
    cells: dict[tuple[str, str, float], dict[str, Any]],
    results_root: Path,
) -> None:
    """Write the markdown report and its JSON companion."""
    safe_output_path = _validated_report_path(output_path, results_root)
    allowed_roots = (str(results_root.expanduser().resolve()),)
    with validated_open(
        str(safe_output_path),
        "w",
        allowed_roots=allowed_roots,
        encoding="utf-8",
    ) as handle:
        handle.write(report)
    json_path = safe_output_path.with_suffix(".json")
    with validated_open(
        str(json_path),
        "w",
        allowed_roots=allowed_roots,
        encoding="utf-8",
    ) as handle:
        json.dump(
            {
                "rows": rows,
                "cells": {
                    f"{hull}|{strategy}|{dose}": cell
                    for (hull, strategy, dose), cell in cells.items()
                },
            },
            handle,
            indent=2,
            default=float,
        )


def _a4_target_lines(
    era: str,
    targets: dict[str, dict[str, float] | None],
) -> list[str]:
    """State the era and the postings behind every A4 target that was used."""
    lines = [
        f"A4 targets are derived from `vsp_outbreak_series.csv` for the "
        f"`{era}` era by `vsp_class_era_scoring.py`, and are conditional on "
        "VSP posting the voyage. A hull with fewer than "
        f"{MIN_POSTINGS_FOR_TARGET} postings carries no A4 anchor.",
        "",
        "| Hull | A4 target IQR | postings |",
        "|---|---|---:|",
    ]
    for hull, target in sorted(targets.items()):
        if target is None:
            lines.append(f"| {hull} | none — {A4_NO_TARGET} | - |")
        else:
            lines.append(
                f"| {hull} | {target['q1']:.4f}-{target['q3']:.4f} "
                f"(median {target['median']:.4f}) | {int(target['n'])} |",
            )
    return [*lines, ""]


def _fmt(value: Any, digits: int = 4) -> str:
    """Format a cell value, passing sentinel strings through unchanged."""
    if value is None:
        return "-"
    if isinstance(value, str):
        return value
    return f"{float(value):.{digits}f}"


def _report_preamble_lines(
    era: str,
    targets: dict[str, dict[str, float] | None],
    archive_stats: dict[str, Any] | None,
) -> list[str]:
    """Heading, anchor provenance, ingestion provenance and table header."""
    stats = archive_stats or {}
    return [
        "# Literature anchor scoring",
        "",
        "Conditional on take-off (peak prevalence >= "
        f"{TAKEOFF_PEAK_PREVALENCE}). Ratios are per-seed medians; the "
        "ratio-of-medians is given alongside because the two diverge when a "
        "denominator is small. Targets and definitions: "
        "`anchor_measurement_spec.md`.",
        "",
        *_a4_target_lines(era, targets),
        "A3 is a construction constraint of the observation layer, not an "
        "anchor: the "
        f"{CONSTRUCTION_BANDS['A3_reported_per_symptomatic'][0]:.2f}-"
        f"{CONSTRUCTION_BANDS['A3_reported_per_symptomatic'][1]:.2f} band is "
        "what that layer's own capture and eligibility parameters produce, so "
        "it is reported for diagnosis and carries no verdict. The verdict "
        "column covers A1, A2, A4, A5, A8 and A9 only.",
        "",
        "A4 and A7 are conditional on posting; A8 and A9 are unconditional. "
        "The pre-arm A8 target is a plausibility band, not a confidence "
        "interval: its fleet-wide calendar endpoint and pooled GRT-band rate "
        "come from different stratifications. For <=30,000 GRT, the "
        "fleet endpoint is 16.9 and the pooled rate is 10.9, so the pair is "
        "not ordered by construction; no band-specific calendar endpoint is "
        "invented. The post arm has no observation.",
        "",
        "A9's denominator is declared, not assumed: "
        f"{MIDRS_TOTAL_VOYAGES:,} {MIDRS_DENOMINATOR_UNIT} "
        f"({MIDRS_DENOMINATOR_WINDOW[0]}-{MIDRS_DENOMINATOR_WINDOW[1]}, "
        "Jenkins 2021 Table 1). It is a pooled period total in one CDC voyage "
        "unit; the annual counts Freeland 2016 publishes for 2008-2014 are in "
        "another unit that does not reconcile with it, and are carried as a "
        "diagnostic by `vsp_voyage_denominator.py` rather than scored. No "
        "voyage count of any kind is published for the post arm.",
        "",
        (
            "Archive ingestion: "
            f"{stats.get('archives_read', 0)} archives read, "
            f"{stats.get('runs_kept', 0)} runs kept, "
            f"{stats.get('duplicates_collapsed', 0)} duplicates collapsed, "
            f"{stats.get('runs_with_recovered_complements', 0)} "
            "runs with recovered complements, "
            f"{stats.get('runs_with_explicit_complements', 0)} "
            "with explicit complements."
        ),
        "",
        "| Hull | Response | Dose | Takeoff | A1 ever-ill | inf AR (pax) | "
        "A2 ill/inf | A3 rep/ill (construction) | A4 reported | "
        "A5 pax/crew | "
        "A8 pax/crew per 100k-days | A9 per 1k voyages | Verdicts |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|",
    ]


def _verdict_state(verdict: dict[str, str]) -> str:
    """Collapse per-anchor verdicts into the table's verdict column."""
    failed = [name for name, state in verdict.items() if state == "FAIL"]
    if not failed:
        return "all PASS"
    return "FAIL: " + ",".join(name.split("_")[0] for name in sorted(failed))


def _cell_line(
    key: tuple[str, str, float],
    cell: dict[str, Any],
    display_cell: dict[str, Any],
    verdict: dict[str, str],
) -> str:
    """One markdown table row for a hull/response/dose cell."""
    hull, strategy, dose = key
    band_states = construction_band_states(cell)
    return (
        f"| {hull} | {strategy} | {dose} | "
        f"{cell['n_takeoff']}/{cell['n_seeds']} | "
        f"{_fmt(cell.get('A1_ever_ill_passenger'))} | "
        f"{_fmt(cell.get('infection_attack_rate_passenger'))} | "
        f"{_fmt(cell.get('A2_ill_per_infected__per_seed_median'), 3)}"
        f" ({_fmt(cell.get('A2_ill_per_infected__of_medians'), 3)}) | "
        f"{_fmt(cell.get('A3_reported_per_symptomatic__per_seed_median'), 3)}"
        f" ({_fmt(cell.get('A3_reported_per_symptomatic__of_medians'), 3)})"
        f" [{band_states['A3_reported_per_symptomatic']}] | "
        f"{_fmt(cell.get('reported_case_attack_rate_passenger'))} | "
        f"{_fmt(cell.get('A5_passenger_crew_ratio__per_seed_median'), 2)}"
        f" ({_fmt(cell.get('A5_passenger_crew_ratio__of_medians'), 2)}) | "
        f"{_fmt(display_cell.get('A8_pax_incidence'), 2)} / "
        f"{_fmt(display_cell.get('A8_crew_incidence'), 2)} "
        f"(ratios {_fmt(display_cell.get('A8_pax_ratio_to_end_of_period'), 2)}/"
        f"{_fmt(display_cell.get('A8_pax_ratio_to_pooled_band'), 2)}; "
        f"{_fmt(display_cell.get('A8_crew_ratio_to_end_of_period'), 2)}/"
        f"{_fmt(display_cell.get('A8_crew_ratio_to_pooled_band'), 2)}) | "
        f"{_fmt(display_cell.get('A9_posting_probability'), 4)} "
        f"(ratios {_fmt(display_cell.get('A9_ratio_to_investigated'), 2)}/"
        f"{_fmt(display_cell.get('A9_ratio_to_posted'), 2)}) | "
        f"{_verdict_state(verdict)} |"
    )


def _undefined_ratio_lines(
    cells: dict[tuple[str, str, float], dict[str, Any]],
) -> list[str]:
    """Name the cells whose per-seed ratios had zero denominators."""
    lines = ["", "## Undefined ratios (zero denominators, excluded)", ""]
    for (hull, strategy, dose), cell in sorted(cells.items()):
        notes = [
            f"{key.split('__')[0]}={cell[key]}"
            for key in sorted(cell)
            if key.endswith("__n_undefined") and cell[key]
        ]
        if notes:
            lines.append(f"- {hull} / {strategy} / {dose}: " + ", ".join(notes))
    return lines


def _skipped_archive_lines(archive_stats: dict[str, Any] | None) -> list[str]:
    """Name archives that carried no summary and were therefore skipped."""
    skipped = archive_stats.get("skipped_archives", []) if archive_stats else []
    if not skipped:
        return []
    return [
        "",
        "## Archives skipped because they contained no summary",
        "",
        *(f"- `{path}`" for path in skipped),
    ]


def render(
    cells: dict[tuple[str, str, float], dict[str, Any]],
    era: str,
    targets: dict[str, dict[str, float] | None],
    archive_stats: dict[str, Any] | None = None,
) -> str:
    """Markdown report: one row per cell, levels then ratios then verdicts."""
    lines = _report_preamble_lines(era, targets, archive_stats)
    for key, cell in sorted(cells.items()):
        hull = key[0]
        verdict, ratios = verdicts(hull, cell, targets, era)
        lines.append(_cell_line(key, cell, {**cell, **ratios}, verdict))
    lines += _undefined_ratio_lines(cells)
    lines += _skipped_archive_lines(archive_stats)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_root", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--vsp-era", choices=SCORED_ERAS, default="pre")
    args = parser.parse_args()

    targets = vsp_attack_rate_targets(args.vsp_era)

    archive_stats: dict[str, Any] = {}
    rows = read_rows(args.results_root, archive_stats)
    grouped: dict[tuple[str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["hull"], row["strategy"], row["dose_adjustment"])].append(row)
    cells = {key: summarise_cell(group) for key, group in grouped.items()}

    report = render(cells, args.vsp_era, targets, archive_stats)
    if args.out:
        _write_report(
            _validated_report_path(args.out, args.results_root),
            report,
            rows,
            cells,
            args.results_root,
        )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
