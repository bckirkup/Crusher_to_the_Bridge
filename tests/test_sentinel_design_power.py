"""Behavioral checks for the sentinel design-stage projection."""

from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest

from picard_framework.analysis.sentinel.design_power import (
    build_design_data,
    build_synthetic_fleet,
    ceiling_projection,
    fit_projection,
    load_presets,
    scaling_sweep,
    week_scaling_check,
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
    (("ships", (4, 8, 16)), ("weeks", (2, 4, 8)), ("calls", (2, 3, 4, 5))),
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
        assert (max(sds) - min(sds)) / np.mean(sds) < 0.25
        broad = scaling_sweep(load_presets()["caribbean"], "ships", (15, 30, 60))
        broad_sds = [row["sd_log_lambda_hot"] for row in broad]
        assert broad_sds[0] / broad_sds[-1] > 2.0


def test_ceiling_has_positive_information_and_mdhr_decreases() -> None:
    design = load_presets()["pilot"]
    values = []
    for ships in (4, 8, 16):
        values.append(ceiling_projection(replace(design, n_ships=ships)))
    assert all(np.isfinite(item["width90_log_lambda"]) for item in values)
    assert all(item["width90_log_lambda"] > 0 for item in values)
    assert all(item["mdhr"] > 1 for item in values)
    assert values[0]["information_positive_definite"]
    assert values[0]["mdhr"] > values[-1]["mdhr"]
    assert values[0]["sd_log_lambda_hot"] / values[-1]["sd_log_lambda_hot"] == pytest.approx(
        2.0,
        rel=0.25,
    )


def test_week_scaling_check_reports_shortcut_bias() -> None:
    result = week_scaling_check(load_presets()["pilot"])
    assert result["explicit_weeks"] == 3
    assert result["sd_log_lambda_hot_scaled"] > 0.0
    assert result["sd_log_lambda_hot_explicit"] > 0.0
    assert result["scaled_to_explicit_ratio"] < 1.0


def test_fit_power_is_sensitive_to_true_hot_ratio() -> None:
    powers = []
    design = replace(
        load_presets()["pilot"],
        fit_scale_ships=3,
        fit_scale_weeks=2,
        fit_scale_ports=4,
    )
    for ratio in (1.0, 16.0):
        result = fit_projection(
            design,
            draws=40,
            warmup=80,
            replicates=2,
            seed=111 if ratio == 1.0 else 1701,
            hot_ratio=ratio,
        )
        powers.append(result["detection_power"])
        assert 0.0 <= result["detection_power"] <= 1.0
        assert 0.0 <= result["coverage_hot_background_ratio_truth"] <= 1.0
        assert 0.0 <= result["coverage_pooled_lambda_hot_truth"] <= 1.0
        assert 0.0 <= result["coverage_pooled_lambda_background_truth"] <= 1.0
        assert result["realized_width90_log_ratio_mean"] > 0.0
    assert powers[0] <= 0.5
    assert powers[-1] > powers[0]


def test_all_preset_ceiling_invariants() -> None:
    for design in load_presets().values():
        ceiling = ceiling_projection(design)
        assert np.isfinite(ceiling["sd_log_lambda_hot"])
        assert ceiling["width90_log_lambda"] > 0.0
        assert ceiling["mdhr"] > 1.0
        assert ceiling["information_positive_definite"]
        assert ceiling["voyage_calls_per_port"] > 0.0


def test_cli_smoke_writes_payload_and_scaling_tables(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["--preset", "pilot", "--engine", "ceiling"]) == 0
    payload = tmp_path / "tmp_design_power_out" / "design_power.json"
    assert payload.exists()
    data = json.loads(payload.read_text(encoding="utf-8"))
    assert data["caveats"]
    assert (payload.parent / "scaling_ships.csv").read_text(encoding="utf-8").strip()
