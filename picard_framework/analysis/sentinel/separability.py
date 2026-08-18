"""Design separability: is ``lambda_port`` separable from ``fleet_time``, before any fit.

The fleet model (``picard_framework/analysis/stan/sentinel_fleet.stan``) writes

    log lambda_visit[i] = log lambda_port[visit_port[i]]
                          + sigma_visit * z_visit[i]
                          + fleet_time[visit_week[i]]

so every observation sees a port effect plus a calendar-week effect and never
either alone. That is a property of the *itinerary*, not of the draws: a design
can be diagnosed before a single sample is drawn, which is the point of this
module — the existing per-port flag in ``sentinel.fleet`` reports the same
degeneracy only after the compute is spent.

Identification convention
-------------------------
The model's fleet-time effect is deliberately uncentered (``fleet_time =
sigma_time * z_time``, no sum-to-zero constraint), so adding a constant to every
``log lambda_port`` and subtracting it from every ``fleet_time`` leaves the
likelihood unchanged. That one direction is *always* in the null space of the
port x week design; only the priors pin it. This module replicates that
parameterisation rather than centering the weeks — centering would assert the
fleet-wide level is zero, which is the assumption the fleet-time effect exists to
avoid (spec 3) — and therefore reports:

- ``rank``: rank of the (weighted) port x week design,
- ``identified_rank``: ``n_ports + n_weeks - 1``, the most any such design can
  reach under this convention,
- ``excess_rank_deficiency``: ``identified_rank - rank``, which equals
  ``(number of connected components of the port-week visit graph) - 1``. Every
  extra component is an extra unidentified level shift: port hazards in
  different components cannot be put on a common scale by the data at all.

Per-port metric
---------------
What a fit can actually report about a port is a *contrast*, never a level. The
estimable contrast used here is the port against the mean of the ports in its own
connected component,

    c_p = e_p - (1 / |C|) * sum_{q in C} e_q      (zero on all week columns)

which is orthogonal to that component's level-shift null direction and so is
estimable whenever the component holds more than one port. Its variance under
the port+week design, ``c_p' M^+ c_p`` with ``M = X' W X``, is compared with the
variance of the same contrast under a port-only design (fleet time known):

    variance_inflation = var(c_p | port + week) / var(c_p | port only)  >= 1

That ratio is the separability number: 1.0 means the week effects cost this port
nothing, large means the port's hazard and its weeks' shocks are nearly the same
column, and ``inf`` means they are the same column. A port alone in its component
(every visit in a week when no other port was called) has no estimable contrast
at all — this is exactly the condition ``fleet.fleet_time_confounded_ports``
flags from the fitted meta, reproduced here from the design.

Structural vs exposure-weighted
-------------------------------
Two weightings are reported for the same design because they answer different
questions:

- **structural** (``W = I``, one unit per ship-port-week visit): can the design
  separate the effects at all, and how badly do the week columns inflate the
  port contrasts.
- **exposure-weighted** (``W = person_hours * reference_hazard``): how *well*.
  For Poisson onsets the information about a log hazard is the expected count,
  ``lambda * person_hours``, so a port called at by many ships with tiny ashore
  person-hours is weakly identified even when structurally separable. The
  reference hazard only sets the common scale of the reported standard errors;
  it does not change any inflation ratio or any rank.
"""

from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np

from picard_framework.analysis._io import (
    ensure_out_dir,
    write_csv,
    write_json,
)
from picard_framework.analysis.sentinel.design_presets import expand_preset, preset_names
from picard_framework.analysis.sentinel.visit_table import (
    PortVisit,
    load_visit_table,
    write_visit_table,
)
from picard_framework.analysis.stan._sentinel_data import DEFAULT_HAZARD_PRIOR_MEDIAN

# Reference hazard for the exposure weighting: the fleet model's own prior median
# port hazard per person-hour. Standard errors are reported at this hazard, so
# they are comparable across designs but not calibrated to any one pathogen.
DEFAULT_REFERENCE_HAZARD = DEFAULT_HAZARD_PRIOR_MEDIAN

# A port whose contrast variance is inflated more than this by the week columns
# is reported as weakly separable rather than separable: the effects come apart,
# but at a cost that a fit will show as a wide interval.
WEAK_INFLATION_THRESHOLD = 5.0
# Standard error on the log-hazard contrast above which a port is weakly
# informed at the reference hazard: 0.7 is a factor of ~2 either way.
WEAK_STANDARD_ERROR = 0.7

VERDICT_DEGENERATE = "degenerate"
VERDICT_WEAK = "weak"
VERDICT_IDENTIFIABLE = "identifiable"

STRUCTURAL = "structural"
EXPOSURE_WEIGHTED = "exposure_weighted"

PORT_COLUMNS = (
    "design_id",
    "weighting",
    "port_id",
    "component_id",
    "component_n_ports",
    "n_visits",
    "n_ships",
    "n_weeks",
    "person_hours_ashore",
    "separable",
    "contrast_variance",
    "variance_inflation",
    "standard_error",
    "reason",
)

@dataclass(frozen=True)
class PortSeparability:
    """Separability of one port's hazard from the fleet-time effect."""

    port_id: str
    component_id: int
    component_n_ports: int
    n_visits: int
    n_ships: int
    n_weeks: int
    person_hours_ashore: float
    separable: bool
    contrast_variance: float
    variance_inflation: float
    standard_error: float
    reason: str


@dataclass(frozen=True)
class DesignDiagnostic:
    """Per-port separability under one weighting, plus its summary numbers."""

    weighting: str
    ports: tuple[PortSeparability, ...]
    max_variance_inflation: float
    median_variance_inflation: float
    max_standard_error: float
    n_not_separable: int
    verdict: str


@dataclass(frozen=True)
class SeparabilityReport:
    """Everything computable about one visit design before a fit."""

    design_id: str
    n_ports: int
    n_weeks: int
    n_ships: int
    n_visits: int
    n_cells: int
    n_columns: int
    rank: int
    identified_rank: int
    excess_rank_deficiency: int
    n_components: int
    person_hours_ashore: float
    reference_hazard: float
    structural: DesignDiagnostic
    exposure_weighted: DesignDiagnostic
    verdict: str
    notes: tuple[str, ...]


def _labels(visits: Sequence[PortVisit]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    ports = tuple(sorted({v.port_id for v in visits}))
    weeks = tuple(sorted({v.week for v in visits}))
    return ports, weeks


def cell_weights(
    visits: Sequence[PortVisit],
    ports: Sequence[str],
    weeks: Sequence[str],
    *,
    weighting: str,
    reference_hazard: float = DEFAULT_REFERENCE_HAZARD,
) -> np.ndarray:
    """``n_ports x n_weeks`` weight table: visits, or Poisson information.

    Visits sharing a port and a week are pooled, which is the model's own visit
    unit: two ships calling at one port in one week share ``lambda_visit``.
    """
    port_index = {p: i for i, p in enumerate(ports)}
    week_index = {w: i for i, w in enumerate(weeks)}
    table = np.zeros((len(ports), len(weeks)), dtype=float)
    for visit in visits:
        weight = (
            1.0
            if weighting == STRUCTURAL
            else visit.person_hours_ashore * reference_hazard
        )
        table[port_index[visit.port_id], week_index[visit.week]] += weight
    return table


def information_matrix(table: np.ndarray) -> np.ndarray:
    """``X' W X`` for the port x week design, ports first then weeks.

    The cross block is the weight table itself, and the diagonal blocks are its
    row and column sums: exactly the design the Stan model's linear predictor
    implies.
    """
    n_ports, n_weeks = table.shape
    info = np.zeros((n_ports + n_weeks, n_ports + n_weeks), dtype=float)
    info[:n_ports, :n_ports] = np.diag(table.sum(axis=1))
    info[n_ports:, n_ports:] = np.diag(table.sum(axis=0))
    info[:n_ports, n_ports:] = table
    info[n_ports:, :n_ports] = table.T
    return info


def _components(table: np.ndarray) -> np.ndarray:
    """Connected-component id per port in the bipartite port-week visit graph.

    Ports in different components share no week with each other, directly or
    through a chain of shared weeks, so no data links their levels.
    """
    n_ports, n_weeks = table.shape
    parent = list(range(n_ports + n_weeks))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for p, w in zip(*np.nonzero(table > 0.0)):
        a, b = find(int(p)), find(n_ports + int(w))
        if a != b:
            parent[a] = b
    roots = sorted({find(p) for p in range(n_ports)})
    label = {root: i for i, root in enumerate(roots)}
    return np.array([label[find(p)] for p in range(n_ports)], dtype=int)


def _null_basis(info: np.ndarray) -> np.ndarray:
    """Orthonormal basis of the null space of the (symmetric) information matrix."""
    values, vectors = np.linalg.eigh(info)
    tol = max(float(values.max()), 1.0) * info.shape[0] * np.finfo(float).eps * 16.0
    return vectors[:, values <= tol]


def _port_contrast(
    port: int,
    component_ports: Sequence[int],
    n_columns: int,
) -> np.ndarray:
    """Port minus the mean of the ports in its component; zero on week columns."""
    contrast = np.zeros(n_columns, dtype=float)
    contrast[port] = 1.0
    for q in component_ports:
        contrast[q] -= 1.0 / len(component_ports)
    return contrast


def _contrast_variance(
    contrast: np.ndarray,
    info_pinv: np.ndarray,
    null_basis: np.ndarray,
) -> float:
    """``c' M^+ c``, or ``inf`` when ``c`` is not estimable under this design."""
    if null_basis.size and float(np.abs(null_basis.T @ contrast).max()) > 1e-9:
        return math.inf
    variance = float(contrast @ info_pinv @ contrast)
    return variance if variance > 0.0 else math.inf


def _port_only_variance(contrast: np.ndarray, row_sums: np.ndarray) -> float:
    """Variance of the same contrast when the fleet-time effects are known.

    The port-only design is diagonal, so this is the ideal against which the
    week columns' cost is measured.
    """
    port_part = contrast[: row_sums.size]
    live = row_sums > 0.0
    zero_port = np.isclose(port_part, 0.0, rtol=0.0, atol=0.0)
    if not np.all(live | zero_port):
        return math.inf
    return float(np.sum(port_part[live] ** 2 / row_sums[live]))


def _degeneracy_reason(
    port_id: str,
    weeks: Sequence[str],
    ships: Sequence[str],
    component_n_ports: int,
) -> str:
    if component_n_ports > 1:
        return ""
    return (
        f"{port_id} is called at only in week(s) {', '.join(weeks)}, and in those "
        f"weeks no other port is called at by any ship "
        f"(ship(s) {', '.join(ships)}); its hazard and those weeks' fleet-time "
        "effects are the same column"
    )


def _weak_reason(inflation: float, standard_error: float) -> str:
    reasons = []
    if inflation > WEAK_INFLATION_THRESHOLD:
        reasons.append(
            f"week columns inflate the port contrast variance {inflation:.1f}x",
        )
    if standard_error > WEAK_STANDARD_ERROR:
        reasons.append(
            f"contrast standard error {standard_error:.2f} on the log-hazard scale",
        )
    return "; ".join(reasons)


def _port_facts(
    visits: Sequence[PortVisit],
    port_id: str,
) -> tuple[tuple[str, ...], tuple[str, ...], float]:
    at_port = [v for v in visits if v.port_id == port_id]
    weeks = tuple(sorted({v.week for v in at_port}))
    ships = tuple(sorted({v.ship_id for v in at_port}))
    return weeks, ships, float(sum(v.person_hours_ashore for v in at_port))


def _diagnose_port(
    *,
    port: int,
    ports: Sequence[str],
    visits: Sequence[PortVisit],
    component_ports: Sequence[int],
    component_id: int,
    info_pinv: np.ndarray,
    null_basis: np.ndarray,
    row_sums: np.ndarray,
    n_columns: int,
    n_visits: int,
) -> PortSeparability:
    port_id = ports[port]
    weeks, ships, hours = _port_facts(visits, port_id)
    contrast = _port_contrast(port, component_ports, n_columns)
    variance = _contrast_variance(contrast, info_pinv, null_basis)
    baseline = _port_only_variance(contrast, row_sums)
    inflation = (
        math.inf
        if not math.isfinite(variance) or baseline <= 0.0
        else variance / baseline
    )
    separable = math.isfinite(variance)
    reason = _degeneracy_reason(port_id, weeks, ships, len(component_ports))
    standard_error = math.sqrt(variance) if separable else math.inf
    if separable and not reason:
        reason = _weak_reason(inflation, standard_error)
    return PortSeparability(
        port_id=port_id,
        component_id=component_id,
        component_n_ports=len(component_ports),
        n_visits=n_visits,
        n_ships=len(ships),
        n_weeks=len(weeks),
        person_hours_ashore=hours,
        separable=separable,
        contrast_variance=variance,
        variance_inflation=inflation,
        standard_error=standard_error,
        reason=reason,
    )


def _diagnostic_verdict(ports: Sequence[PortSeparability]) -> str:
    if any(not p.separable for p in ports):
        return VERDICT_DEGENERATE
    weak = any(
        p.variance_inflation > WEAK_INFLATION_THRESHOLD
        or p.standard_error > WEAK_STANDARD_ERROR
        for p in ports
    )
    return VERDICT_WEAK if weak else VERDICT_IDENTIFIABLE


def _finite_max(values: Iterable[float]) -> float:
    finite = [v for v in values if math.isfinite(v)]
    return max(finite) if finite else math.inf


def diagnose(
    visits: Sequence[PortVisit],
    *,
    weighting: str,
    reference_hazard: float = DEFAULT_REFERENCE_HAZARD,
) -> DesignDiagnostic:
    """Per-port separability under one weighting of the same design."""
    ports, weeks = _labels(visits)
    table = cell_weights(
        visits, ports, weeks, weighting=weighting, reference_hazard=reference_hazard,
    )
    info = information_matrix(table)
    info_pinv = np.linalg.pinv(info, hermitian=True)
    null_basis = _null_basis(info)
    component_of = _components(table)
    row_sums = table.sum(axis=1)
    visit_counts = dict.fromkeys(ports, 0)
    for visit in visits:
        visit_counts[visit.port_id] += 1
    entries = tuple(
        _diagnose_port(
            port=p,
            ports=ports,
            visits=visits,
            component_ports=[
                q for q in range(len(ports)) if component_of[q] == component_of[p]
            ],
            component_id=int(component_of[p]),
            info_pinv=info_pinv,
            null_basis=null_basis,
            row_sums=row_sums,
            n_columns=len(ports) + len(weeks),
            n_visits=visit_counts[ports[p]],
        )
        for p in range(len(ports))
    )
    inflations = [e.variance_inflation for e in entries]
    return DesignDiagnostic(
        weighting=weighting,
        ports=entries,
        max_variance_inflation=_finite_max(inflations),
        median_variance_inflation=float(np.median(inflations)),
        max_standard_error=_finite_max(e.standard_error for e in entries),
        n_not_separable=sum(1 for e in entries if not e.separable),
        verdict=_diagnostic_verdict(entries),
    )


def _report_notes(
    excess_deficiency: int,
    structural: DesignDiagnostic,
    exposure: DesignDiagnostic,
) -> tuple[str, ...]:
    notes: list[str] = []
    if excess_deficiency > 0:
        notes.append(
            f"{excess_deficiency + 1} disconnected blocks of ports and weeks: port "
            "hazards in different blocks cannot be placed on a common scale, only "
            "ranked within a block",
        )
    if structural.n_not_separable:
        notes.append(
            f"{structural.n_not_separable} port(s) have no estimable contrast: "
            "every one of their visits falls in a week when no other port was "
            "called at",
        )
    weakened = sum(
        1
        for s, e in zip(structural.ports, exposure.ports)
        if s.separable and e.standard_error > WEAK_STANDARD_ERROR
    )
    if weakened:
        notes.append(
            f"{weakened} structurally separable port(s) are weakly informed by "
            "their ashore person-hours at the reference hazard",
        )
    return tuple(notes)


def evaluate_design(
    visits: Sequence[PortVisit],
    *,
    design_id: str = "design",
    reference_hazard: float = DEFAULT_REFERENCE_HAZARD,
) -> SeparabilityReport:
    """Full separability diagnostic for one ship x port x week visit design."""
    if not visits:
        raise ValueError("no port visits: nothing to diagnose")
    if reference_hazard <= 0.0:
        raise ValueError("reference_hazard must be positive")
    ports, weeks = _labels(visits)
    table = cell_weights(visits, ports, weeks, weighting=STRUCTURAL)
    info = information_matrix(table)
    rank = int(np.linalg.matrix_rank(info))
    identified_rank = len(ports) + len(weeks) - 1
    structural = diagnose(visits, weighting=STRUCTURAL)
    exposure = diagnose(
        visits, weighting=EXPOSURE_WEIGHTED, reference_hazard=reference_hazard,
    )
    excess = identified_rank - rank
    verdict = (
        VERDICT_DEGENERATE
        if excess > 0
        else max(
            (structural.verdict, exposure.verdict),
            key=(VERDICT_IDENTIFIABLE, VERDICT_WEAK, VERDICT_DEGENERATE).index,
        )
    )
    return SeparabilityReport(
        design_id=design_id,
        n_ports=len(ports),
        n_weeks=len(weeks),
        n_ships=len({v.ship_id for v in visits}),
        n_visits=len(visits),
        n_cells=int(np.count_nonzero(table)),
        n_columns=len(ports) + len(weeks),
        rank=rank,
        identified_rank=identified_rank,
        excess_rank_deficiency=excess,
        n_components=int(_components(table).max()) + 1,
        person_hours_ashore=float(sum(v.person_hours_ashore for v in visits)),
        reference_hazard=float(reference_hazard),
        structural=structural,
        exposure_weighted=exposure,
        verdict=verdict,
        notes=_report_notes(excess, structural, exposure),
    )


def _diagnostic_summary(diagnostic: DesignDiagnostic) -> dict[str, Any]:
    return {
        "weighting": diagnostic.weighting,
        "verdict": diagnostic.verdict,
        "n_not_separable": diagnostic.n_not_separable,
        "max_variance_inflation": diagnostic.max_variance_inflation,
        "median_variance_inflation": diagnostic.median_variance_inflation,
        "max_standard_error": diagnostic.max_standard_error,
        "not_separable_ports": [
            p.port_id for p in diagnostic.ports if not p.separable
        ],
    }


def report_summary(report: SeparabilityReport) -> dict[str, Any]:
    """JSON-ready summary: the compact verdict per design."""
    return {
        "design_id": report.design_id,
        "verdict": report.verdict,
        "n_ports": report.n_ports,
        "n_weeks": report.n_weeks,
        "n_ships": report.n_ships,
        "n_visits": report.n_visits,
        "n_cells": report.n_cells,
        "n_columns": report.n_columns,
        "rank": report.rank,
        "identified_rank": report.identified_rank,
        "excess_rank_deficiency": report.excess_rank_deficiency,
        "n_components": report.n_components,
        "person_hours_ashore": report.person_hours_ashore,
        "reference_hazard": report.reference_hazard,
        "structural": _diagnostic_summary(report.structural),
        "exposure_weighted": _diagnostic_summary(report.exposure_weighted),
        "notes": list(report.notes),
    }


def port_rows(report: SeparabilityReport) -> list[dict[str, Any]]:
    """Flatten both weightings' per-port entries for CSV output."""
    rows: list[dict[str, Any]] = []
    for diagnostic in (report.structural, report.exposure_weighted):
        for entry in diagnostic.ports:
            rows.append(
                {
                    "design_id": report.design_id,
                    "weighting": diagnostic.weighting,
                    "port_id": entry.port_id,
                    "component_id": entry.component_id,
                    "component_n_ports": entry.component_n_ports,
                    "n_visits": entry.n_visits,
                    "n_ships": entry.n_ships,
                    "n_weeks": entry.n_weeks,
                    "person_hours_ashore": round(entry.person_hours_ashore, 3),
                    "separable": entry.separable,
                    "contrast_variance": entry.contrast_variance,
                    "variance_inflation": entry.variance_inflation,
                    "standard_error": entry.standard_error,
                    "reason": entry.reason,
                },
            )
    return rows


def build_parser() -> argparse.ArgumentParser:
    """CLI mirroring ``run_sentinel``: named inputs, one output directory."""
    p = argparse.ArgumentParser(
        prog="python3 -m picard_framework.analysis.sentinel.separability",
        description=(
            "Diagnose whether a ship x port x week design can separate port "
            "hazards from the fleet-time effect, before any fit is run"
        ),
    )
    p.add_argument("--visits", default=None, help="visit table JSON or CSV")
    p.add_argument(
        "--preset",
        action="append",
        default=None,
        metavar="NAME",
        help="named regional geometry preset; repeatable",
    )
    p.add_argument(
        "--all-presets",
        action="store_true",
        help="diagnose every bundled preset and compare them",
    )
    p.add_argument(
        "--list-presets", action="store_true", help="print preset names and exit",
    )
    p.add_argument(
        "--out", default="separability_run", help="output directory under CWD",
    )
    p.add_argument(
        "--reference-hazard",
        type=float,
        default=DEFAULT_REFERENCE_HAZARD,
        help="hazard per person-hour used to scale the exposure weighting",
    )
    p.add_argument(
        "--write-visits",
        action="store_true",
        help="also write each expanded preset's visit table",
    )
    return p


def _print_verdict(report: SeparabilityReport) -> None:
    print(
        f"{report.design_id}: {report.verdict} "
        f"(ports={report.n_ports} weeks={report.n_weeks} ships={report.n_ships} "
        f"rank={report.rank}/{report.identified_rank} "
        f"excess_deficiency={report.excess_rank_deficiency} "
        f"max_vif={report.structural.max_variance_inflation:.2f} "
        f"max_se={report.exposure_weighted.max_standard_error:.3f})",
        flush=True,
    )
    for note in report.notes:
        print(f"  note: {note}", flush=True)


def _reports_from_args(args: argparse.Namespace, out_dir: str) -> list[SeparabilityReport]:
    reports: list[SeparabilityReport] = []
    if args.visits:
        reports.append(
            evaluate_design(
                load_visit_table(args.visits),
                design_id=os.path.basename(str(args.visits)),
                reference_hazard=args.reference_hazard,
            ),
        )
    names = list(args.preset or [])
    if args.all_presets:
        names = list(preset_names())
    for name in names:
        visits = expand_preset(name)
        if args.write_visits:
            write_visit_table(os.path.join(out_dir, f"visits_{name}.json"), visits)
        reports.append(
            evaluate_design(
                visits, design_id=name, reference_hazard=args.reference_hazard,
            ),
        )
    return reports


def main(argv: list[str] | None = None) -> int:
    """Diagnose the named designs, writing a summary JSON and a per-port CSV."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_presets:
        for name in preset_names():
            print(name, flush=True)
        return 0
    if not (args.visits or args.preset or args.all_presets):
        parser.error("give --visits, --preset NAME, --all-presets, or --list-presets")

    out_dir = ensure_out_dir(args.out)
    reports = _reports_from_args(args, out_dir)
    rows = [row for report in reports for row in port_rows(report)]
    write_csv(os.path.join(out_dir, "separability_ports.csv"), rows, PORT_COLUMNS)
    summary_path = os.path.join(out_dir, "separability_summary.json")
    write_json(summary_path, {"designs": [report_summary(r) for r in reports]})
    for report in reports:
        _print_verdict(report)
    print(f"summary: {summary_path}", flush=True)
    return int(not reports)


if __name__ == "__main__":
    raise SystemExit(main())
