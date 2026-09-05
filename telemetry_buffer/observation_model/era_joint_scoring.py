"""Score the pre/post-2020 arms jointly, on levels and on A7c (task #11).

``vsp_covid_discontinuity_design.md`` §7 fixes an order that only means
something if it is enforced mechanically, so it is enforced here:

1. The common dose is fitted on the **pre** arm alone.  ``fit_common_dose``
   refuses any run not labelled ``era = "pre"``, so the fit cannot see the arm
   whose contrast it will later be tested against.  What it returns is not a
   value: it is the set of dose cells the pre-2020 levels leave admissible,
   and that set may be empty.
2. The **post** arm runs at those same doses, with the independently
   constructed configuration of #10 and nothing else.  A post run at a dose
   the pre arm rejected is reported as unscored rather than quietly scored,
   and a post run whose era sweep position is missing a coordinate is an
   error, not a box corner.
3. A7c is then read **out of sample**: it is a prediction of the frozen dose
   set and the sourced configuration, never an input to either.  Nothing in
   this module chooses a dose, a coordinate or a multiplier by looking at how
   close A7c came, and there is no search over the post arm.

The scored discontinuity is A7c, the passenger-specific component
``(post/pre passenger median) / (post/pre crew median)``, not A7a and not A6.
A7a alone cannot be scored because the 3% posting floor truncates both arms
from below in a composition-dependent way; A6 is a superspreader proxy and is
a different anchor.  ``anchor_measurement_spec.md`` measures A7c at 0.668
(0.532-0.907), and holding hull composition roughly fixed moves it to
0.581-1.053 --- an interval that contains 1, so the composition-controlled
figure is reported beside the verdict and never substituted for it.

Simulated voyages enter the statistic only if they pass VSP's own posting
rule, applied identically to both arms: at least 100 passengers, a 3-21 day
voyage, and at least 3% of passengers or of crew reported ill.  Comparing a
simulated fleet mean against a posted-outbreak median would compare two
different populations.

An empty admissible region is a result of this scorer, not a failure of it.
Nothing here widens a target, drops an anchor or reweights a cell when
nothing survives.

Usage::

    PYTHONPATH=. python3 telemetry_buffer/observation_model/era_joint_scoring.py \
        --pre-root <pre-arm results> --post-root <post-arm results> [--out report.md]

Reports are written inside the post-arm results tree, as ``score_anchors``
writes inside the tree it scored: a CLI path is not trusted to name a
destination outside the run it describes.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from simulation_utils.paths import validated_open
from telemetry_buffer.observation_model import score_anchors
from telemetry_buffer.observation_model.era_configuration_sets import (
    UNREPRESENTED,
    levers,
    swept_lever_names,
)
from telemetry_buffer.observation_model.vsp_class_era_scoring import (
    vsp_attack_rate_targets,
)
from telemetry_buffer.observation_model.vsp_discontinuity_analysis import (
    LARGE_SHIP_MIN_PAX,
)

# A7c as measured, from ``anchor_measurement_spec.md``: the scored interval is
# the measurement's own 95% bootstrap interval, rounded outwards to the two
# digits the spec publishes.  The composition-controlled interval is context.
A7C_TARGET: tuple[float, float] = (0.53, 0.91)
A7C_POINT_ESTIMATE = 0.668
A7C_COMPOSITION_INTERVAL: tuple[float, float] = (0.581, 1.053)

# VSP's posting rule, as published on the outbreak pages, applied to simulated
# voyages before any era statistic is taken.
POSTING_MIN_PASSENGERS = 100
POSTING_VOYAGE_DAYS: tuple[float, float] = (3.0, 21.0)
POSTING_RATE_THRESHOLD = score_anchors.A9_POSTING_THRESHOLD

PASS = "PASS"
FAIL = "FAIL"
UNSCORED_DOSE = "not scored (dose rejected by the pre-2020 levels)"
NO_POSTINGS = "n/a (no simulated voyage passed the posting rule)"
ZERO_CREW = "n/a (crew median is zero: the ratio is undefined)"

EMPTY_REGION_NOTE = (
    "The admissible region is empty. That is a result: at no dose the "
    "pre-2020 levels admit does the independently sourced post-2020 "
    "configuration reproduce A7c. It is not licence to widen a target, to "
    "drop an anchor, or to fit a post-2020 lever until the contrast appears."
)


def _require_era(rows: Sequence[dict[str, Any]], era: str) -> None:
    """Refuse rows that are not labelled as the arm they were passed as."""
    wrong = sorted({str(row.get("era", "")) for row in rows} - {era})
    if wrong:
        labels = ", ".join(repr(label) for label in wrong)
        raise RuntimeError(
            f"expected only era {era!r} runs here, found {labels}; the arm a "
            "run belongs to is the train/test split A7c is scored against, so "
            "it is read from the run and never inferred",
        )


def _require_coordinates(rows: Sequence[dict[str, Any]], era: str) -> None:
    """Every swept lever of the era must carry a coordinate in every run."""
    expected = set(swept_lever_names(era))
    for row in rows:
        seen = set(row.get("era_coordinates", {}))
        if seen != expected:
            missing = ", ".join(sorted(expected - seen)) or "none"
            extra = ", ".join(sorted(seen - expected)) or "none"
            raise RuntimeError(
                f"{row.get('_source_path', row.get('run_id'))} does not state "
                f"the {era} sweep position: missing [{missing}], "
                f"unknown [{extra}]",
            )


def coordinate_key(coordinates: Mapping[str, float]) -> str:
    """A stable name for one corner of the era's swept box."""
    return ",".join(f"{name}={coordinates[name]:g}" for name in sorted(coordinates))


def passes_posting_rule(row: dict[str, Any]) -> bool:
    """VSP's published posting rule, applied to one simulated voyage."""
    low, high = POSTING_VOYAGE_DAYS
    if row["passenger_complement"] < POSTING_MIN_PASSENGERS:
        return False
    if not low <= row["voyage_days"] <= high:
        return False
    return (
        row["reported_case_attack_rate_passenger"] >= POSTING_RATE_THRESHOLD
        or row["reported_case_attack_rate_crew"] >= POSTING_RATE_THRESHOLD
    )


def posted(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """The simulated voyages VSP would have posted."""
    return [row for row in rows if passes_posting_rule(row)]


def large_ships_only(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Restrict to the hull sizes the composition control keeps."""
    return [
        row for row in rows
        if row["passenger_complement"] >= LARGE_SHIP_MIN_PAX
    ]


def _median(rows: Sequence[dict[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows]
    return float(statistics.median(values)) if values else None


def _ratio(post: float | None, pre: float | None) -> float | None:
    if post is None or pre is None or math.isclose(pre, 0.0, abs_tol=1e-12):
        return None
    return post / pre


def a7c(
    pre_posted: Sequence[dict[str, Any]],
    post_posted: Sequence[dict[str, Any]],
) -> float | None:
    """A7c over posted simulated voyages: the passenger-specific component."""
    passenger = _ratio(
        _median(post_posted, "reported_case_attack_rate_passenger"),
        _median(pre_posted, "reported_case_attack_rate_passenger"),
    )
    crew = _ratio(
        _median(post_posted, "reported_case_attack_rate_crew"),
        _median(pre_posted, "reported_case_attack_rate_crew"),
    )
    if passenger is None or crew is None:
        return None
    if math.isclose(crew, 0.0, abs_tol=1e-12):
        return None
    return passenger / crew


@dataclass(frozen=True)
class CommonDoseFit:
    """The dose cells the pre-2020 levels admit, and what rejected the rest.

    ``arms_seen`` is part of the record: the fit is only valid if it saw the
    pre arm and nothing else, and ``score_discontinuity`` checks it rather
    than trusting the caller to have used the right constructor.
    """

    doses: tuple[float, ...]
    rejected: Mapping[float, tuple[str, ...]]
    cell_verdicts: Mapping[str, Mapping[str, str]]
    arms_seen: tuple[str, ...] = ("pre",)

    @property
    def is_empty(self) -> bool:
        return not self.doses


def _cell_key(hull: str, strategy: str, dose: float) -> str:
    return f"{hull}|{strategy}|{dose:g}"


def _scored_states(verdict: Mapping[str, str]) -> list[str]:
    """The PASS/FAIL states, dropping the anchors this cell cannot score."""
    return [state for state in verdict.values() if state in {PASS, FAIL}]


def fit_common_dose(pre_rows: Sequence[dict[str, Any]]) -> CommonDoseFit:
    """Fit the common dose on the pre-2020 arm alone.

    A dose survives when no pre-2020 cell at that dose fails a scored anchor
    and at least one cell reaches a verdict.  Nothing about the post arm or
    about A7 enters, and the result is a set, not a point: a dose is admitted
    or rejected, never ranked, so no dose can be preferred for landing closer
    to any target.
    """
    _require_era(pre_rows, "pre")
    _require_coordinates(pre_rows, "pre")
    targets = vsp_attack_rate_targets("pre")
    grouped: dict[tuple[str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in pre_rows:
        grouped[(row["hull"], row["strategy"], row["dose_adjustment"])].append(row)
    failures: dict[float, list[str]] = defaultdict(list)
    scored: dict[float, int] = defaultdict(int)
    cell_verdicts: dict[str, Mapping[str, str]] = {}
    for (hull, strategy, dose), rows in sorted(grouped.items()):
        cell = score_anchors.summarise_cell(rows)
        verdict, _ratios = score_anchors.verdicts(hull, cell, targets, era="pre")
        cell_verdicts[_cell_key(hull, strategy, dose)] = verdict
        states = _scored_states(verdict)
        scored[dose] += len(states)
        failures[dose].extend(
            f"{hull}/{strategy}:{anchor}"
            for anchor, state in sorted(verdict.items())
            if state == FAIL
        )
    doses = tuple(
        dose for dose in sorted(scored)
        if scored[dose] > 0 and not failures[dose]
    )
    rejected = {
        dose: tuple(reasons or ("no cell reached a verdict",))
        for dose, reasons in sorted(failures.items())
        if dose not in doses
    }
    return CommonDoseFit(
        doses=doses,
        rejected=rejected,
        cell_verdicts=cell_verdicts,
    )


@dataclass(frozen=True)
class DiscontinuityPoint:
    """A7c at one (dose, post-2020 configuration) point of the sweep."""

    dose: float
    coordinates: str
    n_pre_posted: int
    n_post_posted: int
    value: float | None
    composition_controlled: float | None
    verdict: str

    @property
    def admissible(self) -> bool:
        return self.verdict == PASS


def _a7c_verdict(value: float | None, n_post: int) -> str:
    if n_post == 0:
        return NO_POSTINGS
    if value is None:
        return ZERO_CREW
    low, high = A7C_TARGET
    return PASS if low <= value <= high else FAIL


def _point(
    dose: float,
    coordinates: str,
    pre_posted: Sequence[dict[str, Any]],
    post_rows: Sequence[dict[str, Any]],
) -> DiscontinuityPoint:
    post_posted = posted(post_rows)
    value = a7c(pre_posted, post_posted)
    return DiscontinuityPoint(
        dose=dose,
        coordinates=coordinates,
        n_pre_posted=len(pre_posted),
        n_post_posted=len(post_posted),
        value=value,
        composition_controlled=a7c(
            large_ships_only(pre_posted),
            large_ships_only(post_posted),
        ),
        verdict=_a7c_verdict(value, len(post_posted)),
    )


def score_discontinuity(
    fit: CommonDoseFit,
    pre_rows: Sequence[dict[str, Any]],
    post_rows: Sequence[dict[str, Any]],
) -> list[DiscontinuityPoint]:
    """Read A7c at each post-2020 sweep point, out of sample.

    The dose set arrives frozen from ``fit_common_dose``; this function never
    revisits it, so a post-arm point that misses A7c cannot promote a dose the
    pre-2020 levels rejected, and a post-arm point that hits it cannot rescue
    one either.
    """
    if fit.arms_seen != ("pre",):
        raise RuntimeError(
            f"the common dose was fitted on arms {fit.arms_seen}; A7c is only "
            "evidence if the fit never saw the post arm",
        )
    _require_era(pre_rows, "pre")
    _require_era(post_rows, "post")
    _require_coordinates(post_rows, "post")
    pre_by_dose: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for row in pre_rows:
        pre_by_dose[row["dose_adjustment"]].append(row)
    grouped: dict[tuple[float, str], list[dict[str, Any]]] = defaultdict(list)
    for row in post_rows:
        key = (row["dose_adjustment"], coordinate_key(row["era_coordinates"]))
        grouped[key].append(row)
    points: list[DiscontinuityPoint] = []
    for (dose, coordinates), rows in sorted(grouped.items()):
        if dose not in pre_by_dose:
            raise RuntimeError(
                f"post-arm dose {dose:g} has no pre-arm counterpart: A7c is a "
                "ratio across the eras at one dose, so the arms must be run "
                "at the same doses",
            )
        if dose not in fit.doses:
            points.append(
                DiscontinuityPoint(
                    dose=dose,
                    coordinates=coordinates,
                    n_pre_posted=len(posted(pre_by_dose[dose])),
                    n_post_posted=len(posted(rows)),
                    value=None,
                    composition_controlled=None,
                    verdict=UNSCORED_DOSE,
                ),
            )
            continue
        points.append(
            _point(dose, coordinates, posted(pre_by_dose[dose]), rows),
        )
    return points


def admissible_region(
    points: Sequence[DiscontinuityPoint],
) -> tuple[tuple[float, str], ...]:
    """The (dose, post-2020 configuration) points that survive both halves."""
    return tuple(
        (point.dose, point.coordinates) for point in points if point.admissible
    )


def unrepresented_mechanisms(era: str = "post") -> tuple[tuple[str, str], ...]:
    """The era's documented mechanisms that carry no number into a run.

    Reported with every verdict: a scorer that says the post-2020
    configuration was applied while these are absent is overstating what ran.
    """
    return tuple(
        (lever.name, lever.note)
        for lever in levers(era)
        if lever.kind == UNREPRESENTED
    )


def _fmt(value: float | None, digits: int = 4) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _anchor_names(fit: CommonDoseFit) -> list[str]:
    seen: set[str] = set()
    for verdict in fit.cell_verdicts.values():
        seen.update(verdict)
    return sorted(seen)


def _level_lines(fit: CommonDoseFit) -> list[str]:
    lines = ["## Pre-2020 levels: the fit, on the pre arm alone", ""]
    if not fit.cell_verdicts:
        lines.append("No pre-2020 cells were read.")
        return lines
    anchors = _anchor_names(fit)
    lines.append("| cell | " + " | ".join(anchors) + " |")
    lines.append("|---" * (len(anchors) + 1) + "|")
    for cell, verdict in sorted(fit.cell_verdicts.items()):
        lines.append(
            f"| {cell} | " + " | ".join(verdict.get(a, "n/a") for a in anchors) + " |",
        )
    lines.extend([
        "",
        "Doses admitted by the pre-2020 levels: "
        + (", ".join(f"{dose:g}" for dose in fit.doses) or "none"),
    ])
    for dose, reasons in sorted(fit.rejected.items()):
        lines.append(f"- dose {dose:g} rejected by: " + ", ".join(reasons))
    return lines


def _discontinuity_lines(points: Sequence[DiscontinuityPoint]) -> list[str]:
    low, high = A7C_TARGET
    clow, chigh = A7C_COMPOSITION_INTERVAL
    lines = [
        "",
        "## A7c out of sample: the post arm at the same dose",
        "",
        f"Scored against {low:g}-{high:g} (measured {A7C_POINT_ESTIMATE:g}). "
        f"The composition-controlled column is context, not a second verdict: "
        f"its measured interval {clow:g}-{chigh:g} contains 1.",
        "",
        "| dose | post configuration | posted pre | posted post | A7c | "
        "A7c (large ships) | verdict |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for point in points:
        lines.append(
            f"| {point.dose:g} | {point.coordinates} | {point.n_pre_posted} | "
            f"{point.n_post_posted} | {_fmt(point.value)} | "
            f"{_fmt(point.composition_controlled)} | {point.verdict} |",
        )
    return lines


def render(
    fit: CommonDoseFit,
    points: Sequence[DiscontinuityPoint],
) -> str:
    """The joint report: levels, A7c, the region, and what did not run."""
    region = admissible_region(points)
    lines = [
        "# Joint scoring: pre/post-2020 levels and the A7c discontinuity",
        "",
        "Task #11. The common dose is fitted on the pre-2020 arm alone; the "
        "post-2020 arm runs at that same dose under the sourced configuration "
        "of #10; A7c is read as a prediction of both.",
        "",
    ]
    lines.extend(_level_lines(fit))
    lines.extend(_discontinuity_lines(points))
    lines.extend([
        "",
        "## Admissible region",
        "",
    ])
    if region:
        lines.extend(
            f"- dose {dose:g}, {coordinates}" for dose, coordinates in region
        )
    else:
        lines.append(EMPTY_REGION_NOTE)
    lines.extend([
        "",
        "## Post-2020 mechanisms that carried no number into these runs",
        "",
    ])
    lines.extend(
        f"- `{name}`: {note}" for name, note in unrepresented_mechanisms("post")
    )
    return "\n".join(lines) + "\n"


def score(pre_root: Path, post_root: Path) -> tuple[CommonDoseFit, list[DiscontinuityPoint]]:
    """Read both arms from disk and score them in the fixed order."""
    pre_rows = score_anchors.read_rows(pre_root)
    fit = fit_common_dose(pre_rows)
    post_rows = score_anchors.read_rows(post_root)
    return fit, score_discontinuity(fit, pre_rows, post_rows)


def _summary(
    fit: CommonDoseFit,
    points: Sequence[DiscontinuityPoint],
) -> dict[str, Any]:
    return {
        "doses_admitted_by_levels": list(fit.doses),
        "doses_rejected_by_levels": {
            f"{dose:g}": list(reasons) for dose, reasons in fit.rejected.items()
        },
        "a7c_target": list(A7C_TARGET),
        "points": [
            {
                "dose": point.dose,
                "coordinates": point.coordinates,
                "a7c": point.value,
                "a7c_large_ships": point.composition_controlled,
                "verdict": point.verdict,
            }
            for point in points
        ],
        "admissible_region": [
            {"dose": dose, "coordinates": coordinates}
            for dose, coordinates in admissible_region(points)
        ],
    }


def _write_inside(root: Path, path: Path, text: str) -> None:
    """Write *text* to *path*, which must lie inside the scored results tree."""
    base = str(root.expanduser().resolve())
    with validated_open(
        str(path.expanduser().resolve()),
        "w",
        allowed_roots=(base,),
        encoding="utf-8",
    ) as handle:
        handle.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pre-root", type=Path, required=True)
    parser.add_argument("--post-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    fit, points = score(args.pre_root, args.post_root)
    report = render(fit, points)
    if args.out is not None:
        _write_inside(args.post_root, args.out, report)
    else:
        print(report)
    if args.json_out is not None:
        _write_inside(
            args.post_root,
            args.json_out,
            json.dumps(_summary(fit, points), indent=2, sort_keys=True) + "\n",
        )
    return 0 if admissible_region(points) else 1


if __name__ == "__main__":
    raise SystemExit(main())
