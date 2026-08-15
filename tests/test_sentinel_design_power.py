"""Behavioral checks for the sentinel design-stage projection."""

from __future__ import annotations

import numpy as np
import pytest

from picard_framework.analysis.sentinel.design_power import (
    build_design_data,
    build_synthetic_fleet,
    ceiling_projection,
    fit_projection,
    load_presets,
    scaling_sweep,
)
from picard_framework.analysis.sentinel.fleet import fleet_time_confounded_ports
from picard_framework.analysis.sentinel.run_design_power import main


def test_all_presets_have_crossed_identifiable_fit_scale() -> None:
    for design in load_presets().values():
        fit = design.fit_design()
        _, meta = build_design_data(fit)
        assert not fleet_time_confounded_ports(meta)
        port_zero = [
            voyage.ship_id
            for voyage in build_synthetic_fleet(fit)
            if "P00" in voyage.voyage.port_ids
        ]
        assert len(set(port_zero)) > 1
        weeks = {
            call.calendar_date.isocalendar().week
            for voyage in build_synthetic_fleet(fit)
            for call in voyage.voyage.port_calls
            if call.port_id == "P00" and call.calendar_date is not None
        }
        assert len(weeks) > 1


@pytest.mark.parametrize(
    ("dimension", "values"),
    (("ships", (4, 8, 16)), ("weeks", (2, 4, 8)), ("calls", (2, 3, 4))),
)
def test_ceiling_precision_improves_with_scale(
    dimension: str,
    values: tuple[int, ...],
) -> None:
    design = load_presets()["pilot"]
    rows = scaling_sweep(design, dimension, values)
    sds = [row["sd_log_lambda_hot"] for row in rows]
    if dimension in {"ships", "weeks"}:
        assert sds == sorted(sds, reverse=True)
        assert sds[0] / sds[-1] > 1.2
    else:
        assert max(sds) - min(sds) > 0.01


def test_ceiling_has_positive_information_and_mdhr_decreases() -> None:
    design = load_presets()["pilot"]
    values = []
    for ships in (4, 8, 16):
        values.append(ceiling_projection(design.__class__(**{
            **design.__dict__,
            "n_ships": ships,
        })))
    assert all(np.isfinite(item["width90_log_lambda"]) for item in values)
    assert all(item["width90_log_lambda"] > 0 for item in values)
    assert all(item["mdhr"] > 1 for item in values)
    assert values[0]["information_positive_definite"]
    assert values[0]["mdhr"] > values[-1]["mdhr"]


def test_cli_smoke_writes_payload_and_scaling_tables(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["--preset", "pilot", "--engine", "ceiling"]) == 0
    payload = tmp_path / "tmp_design_power_out" / "design_power.json"
    assert payload.exists()
    import json

    data = json.loads(payload.read_text(encoding="utf-8"))
    assert data["caveats"]
    assert (payload.parent / "scaling_ships.csv").read_text(encoding="utf-8").strip()


@pytest.mark.timeout(60)
def test_smoke_fit_reports_bounds_and_caveats() -> None:
    design = load_presets()["pilot"]
    result = fit_projection(design, draws=40, warmup=80, replicates=2, seed=17)
    assert result["caveats"]
    assert 0.0 <= result["detection_power"] <= 1.0
    assert 0.0 <= result["coverage_hot_background_ratio_truth"] <= 1.0
    assert result["realized_width90_log_ratio_mean"] > 0.0
    assert result["provenance"].startswith("Engine B")
