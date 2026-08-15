"""Behavioral tests for the Sentinel design separability diagnostic."""

from __future__ import annotations

import csv
import math

import pytest

from picard_framework.analysis.sentinel.design_presets import (
    expand_preset,
    geometry,
    preset_names,
)
from picard_framework.analysis.sentinel.separability import evaluate_design
from picard_framework.analysis.sentinel.visit_table import (
    load_visit_table,
    write_visit_table,
)


def _report(name: str, overrides: dict | None = None):
    return evaluate_design(expand_preset(name, overrides), design_id=name)


def test_degenerate_and_identifiable_controls() -> None:
    degenerate = _report("degenerate_lockstep")
    assert degenerate.excess_rank_deficiency > 0
    assert degenerate.n_components > 1
    assert degenerate.verdict == "degenerate"
    assert all(not port.separable for port in degenerate.structural.ports)
    assert all(math.isinf(port.contrast_variance) for port in degenerate.structural.ports)
    assert all(math.isinf(port.variance_inflation) for port in degenerate.structural.ports)

    identifiable = _report("staggered_control")
    assert identifiable.excess_rank_deficiency == 0
    assert identifiable.n_components == 1
    assert identifiable.verdict == "identifiable"
    assert all(port.separable for port in identifiable.structural.ports)
    assert all(math.isfinite(port.variance_inflation) for port in identifiable.structural.ports)


def test_structural_stagger_sweep_is_monotone() -> None:
    reports = [
        _report("sweep_base_ten_day", {"sail_day_stagger": stagger})
        for stagger in (1, 2, 3, 4, 5, 7)
    ]
    ranks = [report.rank for report in reports]
    components = [report.n_components for report in reports]
    assert ranks == sorted(ranks)
    assert components == sorted(components, reverse=True)
    assert ranks[0] < ranks[-1]
    assert components[0] > components[-1]


def test_exposure_sweep_changes_precision_not_structure() -> None:
    base_hours = geometry("pilot_eight_ship").hours_ashore_per_call
    reports = [
        _report(
            "pilot_eight_ship",
            {"hours_ashore_per_call": base_hours * factor},
        )
        for factor in (0.25, 1.0, 4.0)
    ]
    errors = [report.exposure_weighted.max_standard_error for report in reports]
    medians = [
        sorted(port.standard_error for port in report.exposure_weighted.ports)[
            len(report.exposure_weighted.ports) // 2
        ]
        for report in reports
    ]
    assert errors[0] > errors[1] > errors[2]
    assert medians[0] > medians[1] > medians[2]
    assert errors[0] / errors[-1] == pytest.approx(4.0, rel=0.15)
    for report in reports[1:]:
        assert report.rank == reports[0].rank
        assert report.n_components == reports[0].n_components
        assert [
            port.variance_inflation for port in report.structural.ports
        ] == pytest.approx(
            [port.variance_inflation for port in reports[0].structural.ports],
        )


def test_low_exposure_ports_are_structurally_separable_but_weak() -> None:
    report = _report("caribbean_partial_overlap")
    structural = {port.port_id: port for port in report.structural.ports}
    exposure = {port.port_id: port for port in report.exposure_weighted.ports}
    prefix = geometry("caribbean_partial_overlap").port_prefix
    low_ports = {
        f"{prefix}{index:03d}"
        for index in geometry("caribbean_partial_overlap").port_exposure_scale
    }
    low_errors = [exposure[port].standard_error for port in low_ports]
    median_error = sorted(
        port.standard_error for port in report.exposure_weighted.ports
    )[len(exposure) // 2]
    assert all(structural[port].separable for port in low_ports)
    assert all(structural[port].variance_inflation == pytest.approx(1.0, abs=0.02)
               for port in low_ports)
    assert min(low_errors) >= 3.0 * median_error


def test_bundled_preset_invariants() -> None:
    for name in preset_names():
        report = _report(name)
        assert report.rank <= report.n_columns
        assert report.identified_rank == report.n_ports + report.n_weeks - 1
        assert report.excess_rank_deficiency == report.n_components - 1
        assert report.excess_rank_deficiency >= 0
        for diagnostic in (report.structural, report.exposure_weighted):
            for port in diagnostic.ports:
                assert port.contrast_variance >= 0.0
                assert port.variance_inflation >= 0.0
                assert port.standard_error >= 0.0
                if port.separable:
                    assert port.variance_inflation >= 1.0 - 1e-9
                    assert math.isfinite(port.contrast_variance)
                    assert math.isfinite(port.variance_inflation)
                    assert math.isfinite(port.standard_error)


def test_preset_expansion_is_deterministic_and_seed_only_changes_exposure() -> None:
    for name in preset_names():
        assert expand_preset(name) == expand_preset(name)
    original = expand_preset("pilot_eight_ship")
    reseeded = expand_preset("pilot_eight_ship", {"seed": 12345})
    assert [
        (visit.ship_id, visit.port_id, visit.week) for visit in original
    ] == [(visit.ship_id, visit.port_id, visit.week) for visit in reseeded]
    assert _report("pilot_eight_ship").rank == _report(
        "pilot_eight_ship", {"seed": 12345}
    ).rank
    assert _report("pilot_eight_ship").n_components == _report(
        "pilot_eight_ship", {"seed": 12345}
    ).n_components
    assert [visit.person_hours_ashore for visit in original] != [
        visit.person_hours_ashore for visit in reseeded
    ]


def test_visit_table_round_trip_csv_and_path_safety(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    visits = expand_preset("pilot_eight_ship")
    json_path = write_visit_table("visits.json", visits)
    loaded = load_visit_table(json_path)
    assert [(v.ship_id, v.port_id, v.week) for v in loaded] == [
        (v.ship_id, v.port_id, v.week) for v in visits
    ]
    assert [v.person_hours_ashore for v in loaded] == pytest.approx(
        [round(v.person_hours_ashore, 6) for v in visits],
    )

    with open("visits.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "ship_id", "port_id", "week", "person_hours_ashore",
        ])
        writer.writeheader()
        writer.writerows({
            "ship_id": v.ship_id,
            "port_id": v.port_id,
            "week": v.week,
            "person_hours_ashore": v.person_hours_ashore,
        } for v in visits)
    csv_visits = load_visit_table("visits.csv")
    assert csv_visits == visits
    with pytest.raises(SystemExit, match="escapes allowed base"):
        load_visit_table("../outside.json")


def test_preset_geometry_sanity_bands() -> None:
    caribbean = expand_preset("caribbean_partial_overlap")
    alaska = expand_preset("alaska_full_overlap")
    assert 3.3 < len(caribbean) / (120 * 12) < 4.0
    assert 35 <= len({visit.port_id for visit in caribbean}) <= 45
    assert 110 <= len({visit.ship_id for visit in caribbean}) <= 130
    assert 8 <= len({visit.port_id for visit in alaska}) <= 12
    assert 20 <= len({visit.ship_id for visit in alaska}) <= 30
