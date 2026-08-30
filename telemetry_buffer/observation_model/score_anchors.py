"""Score simulation output against the five literature anchors (A1-A5).

Reads run zips produced by the campaign runner and reports, per
hull x response x dose cell and conditional on take-off, the anchor
quantities defined in ``anchor_measurement_spec.md``.  Ratios are reported
both per-seed (median of ratios) and as a ratio of cell medians, because the
two diverge whenever a denominator is small.

Usage:
    python3 score_anchors.py <results-root> [--out report.md]

``<results-root>`` is a directory searched recursively for ``*.zip`` runs,
each containing ``summary.json`` with ``parameters`` and ``derived`` blocks.
"""

from __future__ import annotations

import argparse
import json
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

TAKEOFF_PEAK_PREVALENCE = 10

VSP_TARGETS: dict[str, dict[str, float]] = {
    "expedition_cruise_450": {"median": 0.0856, "q1": 0.0451, "q3": 0.1360},
    "classic_cruise_1900": {"median": 0.0559, "q1": 0.0446, "q3": 0.0776},
    "spirit_cruise_3000": {"median": 0.0564, "q1": 0.0444, "q3": 0.0790},
    "mega_cruise_5000": {"median": 0.0561, "q1": 0.0340, "q3": 0.0745},
}

# A1 Wikswo whole-ship cohort illness; A2 asymptomatic ratio (GII.4-weighted
# lower bound 0.59); A3 capture; A5 passenger:crew reported ratio.
#
# A3 is reported over *symptomatic*, because that is the denominator this
# scorer has: the 0.60 infirmary-capture figure is reported over AGE-eligible,
# and the five-state observation layer puts reported/symptomatic at 0.40 for
# the same parameter set (eligibility [0,.55,.98,1,1] absorbs the difference).
# Scoring the measured reported/symptomatic against 0.60 would demand 1.5x the
# reporting the literature chain allows. Reported/eligible is not scored here
# because the runs do not emit an AGE-eligible count.
ANCHORS: dict[str, tuple[float, float]] = {
    "A1_ever_ill_passenger": (0.10, 0.22),
    "A2_ill_per_infected": (0.59, 0.81),
    "A3_reported_per_symptomatic": (0.35, 0.45),
    "A5_passenger_crew_ratio": (2.5, 4.5),
}


def load_summary(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read("summary.json"))


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator > 0 else None


def read_rows(root: Path) -> list[dict[str, Any]]:
    """Collect one row per completed run, with the anchor inputs and ratios."""
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.zip")):
        summary = load_summary(path)
        params = summary.get("parameters", {})
        derived = summary.get("derived", {})
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
        rows.append({
            "run_id": summary.get("run_id", path.stem),
            "hull": hull,
            "strategy": strategy,
            "dose_adjustment": float(params.get("dose_adjustment", 0.0)),
            "seed": int(params.get("seed", -1)),
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
        })
    if not rows:
        raise RuntimeError(f"no run zips found under {root}")
    return rows


def _median(values: list[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def summarise_cell(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-cell medians, per-seed ratio medians, and ratios of medians."""
    took_off = [row for row in rows if row["took_off"]]
    cell: dict[str, Any] = {
        "n_seeds": len(rows),
        "n_takeoff": len(took_off),
        "takeoff_fraction": len(took_off) / len(rows) if rows else 0.0,
    }
    if not took_off:
        return cell

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
    return cell


def verdicts(hull: str, cell: dict[str, Any]) -> dict[str, str]:
    """PASS/FAIL per anchor on the per-seed medians, plus A4 against VSP."""
    out: dict[str, str] = {}
    for anchor, (low, high) in ANCHORS.items():
        value = cell.get(anchor) if anchor == "A1_ever_ill_passenger" else (
            cell.get(f"{anchor}__per_seed_median")
        )
        if value is None:
            out[anchor] = "n/a"
        else:
            out[anchor] = "PASS" if low <= value <= high else "FAIL"
    reported = cell.get("reported_case_attack_rate_passenger")
    target = VSP_TARGETS.get(hull)
    if reported is None or target is None:
        out["A4_vsp_iqr"] = "n/a"
    else:
        out["A4_vsp_iqr"] = (
            "PASS" if target["q1"] <= reported <= target["q3"] else "FAIL"
        )
    return out


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
) -> None:
    """Write the markdown report and its JSON companion."""
    output_path.write_text(report, encoding="utf-8")
    json_path = output_path.with_suffix(".json")
    json_path.write_text(
        json.dumps(
            {
                "rows": rows,
                "cells": {
                    f"{hull}|{strategy}|{dose}": cell
                    for (hull, strategy, dose), cell in cells.items()
                },
            },
            indent=2,
            default=float,
        ),
        encoding="utf-8",
    )


def render(cells: dict[tuple[str, str, float], dict[str, Any]]) -> str:
    """Markdown report: one row per cell, levels then ratios then verdicts."""
    lines = [
        "# Literature anchor scoring",
        "",
        "Conditional on take-off (peak prevalence >= "
        f"{TAKEOFF_PEAK_PREVALENCE}). Ratios are per-seed medians; the "
        "ratio-of-medians is given alongside because the two diverge when a "
        "denominator is small. Targets and definitions: "
        "`anchor_measurement_spec.md`.",
        "",
        "| Hull | Response | Dose | Takeoff | A1 ever-ill | inf AR (pax) | "
        "A2 ill/inf | A3 rep/ill | A4 reported | A5 pax/crew | Verdicts |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    def fmt(value: Any, digits: int = 4) -> str:
        if value is None:
            return "-"
        return f"{float(value):.{digits}f}"

    for (hull, strategy, dose), cell in sorted(cells.items()):
        verdict = verdicts(hull, cell)
        failed = [name for name, state in verdict.items() if state == "FAIL"]
        state = "all PASS" if not failed else "FAIL: " + ",".join(
            name.split("_")[0] for name in sorted(failed)
        )
        lines.append(
            f"| {hull} | {strategy} | {dose} | "
            f"{cell['n_takeoff']}/{cell['n_seeds']} | "
            f"{fmt(cell.get('A1_ever_ill_passenger'))} | "
            f"{fmt(cell.get('infection_attack_rate_passenger'))} | "
            f"{fmt(cell.get('A2_ill_per_infected__per_seed_median'), 3)}"
            f" ({fmt(cell.get('A2_ill_per_infected__of_medians'), 3)}) | "
            f"{fmt(cell.get('A3_reported_per_symptomatic__per_seed_median'), 3)}"
            f" ({fmt(cell.get('A3_reported_per_symptomatic__of_medians'), 3)}) | "
            f"{fmt(cell.get('reported_case_attack_rate_passenger'))} | "
            f"{fmt(cell.get('A5_passenger_crew_ratio__per_seed_median'), 2)}"
            f" ({fmt(cell.get('A5_passenger_crew_ratio__of_medians'), 2)}) | "
            f"{state} |",
        )

    lines += ["", "## Undefined ratios (zero denominators, excluded)", ""]
    for (hull, strategy, dose), cell in sorted(cells.items()):
        notes = [
            f"{key.split('__')[0]}={cell[key]}"
            for key in sorted(cell)
            if key.endswith("__n_undefined") and cell[key]
        ]
        if notes:
            lines.append(f"- {hull} / {strategy} / {dose}: " + ", ".join(notes))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_root", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    rows = read_rows(args.results_root)
    grouped: dict[tuple[str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["hull"], row["strategy"], row["dose_adjustment"])].append(row)
    cells = {key: summarise_cell(group) for key, group in grouped.items()}

    report = render(cells)
    if args.out:
        _write_report(
            _validated_report_path(args.out, args.results_root),
            report,
            rows,
            cells,
        )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
