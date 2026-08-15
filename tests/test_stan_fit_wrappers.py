"""Coverage for Stan wrapper data assembly and no-CmdStan status paths."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from picard_framework.analysis.stan import (
    _boundary_data,
    _data,
    fit_boundary_hurdle,
    fit_norovirus_hurdle,
    fit_norovirus_outbreak,
    fit_norovirus_trajectory,
)


def _write_analysis(path: Path) -> None:
    path.mkdir()
    rows = [
        {
            "run_id": "run_noro_a",
            "pathogen": "norovirus",
            "pathogen_id": "norovirus_only",
            "platform_id": "mega_cruise_5000",
            "surveillance_strategy": "syndromic",
            "dose_adjustment": "10.6",
            "density_exponent": "0.75",
            "vsp_lockdown_threshold": "0.05",
            "seed": "1",
            "num_agents": "100",
            "initial_infected": "3",
            "outbreak_occurred": "1",
            "attack_rate": "0.2",
        },
        {
            "run_id": "run_noro_b",
            "pathogen": "norovirus",
            "pathogen_id": "norovirus_only",
            "platform_id": "expedition_cruise_450",
            "surveillance_strategy": "none_true",
            "dose_adjustment": "10.4",
            "density_exponent": "0.8",
            "vsp_lockdown_threshold": "never",
            "seed": "2",
            "num_agents": "80",
            "initial_infected": "2",
            "outbreak_occurred": "0",
            "attack_rate": "0.0",
        },
        {
            "run_id": "run_flu",
            "pathogen": "influenza",
            "pathogen_id": "influenza_only",
            "platform_id": "mega_cruise_5000",
            "surveillance_strategy": "syndromic",
            "dose_adjustment": "10.6",
            "density_exponent": "0.75",
            "vsp_lockdown_threshold": "0.05",
            "seed": "3",
            "num_agents": "90",
            "initial_infected": "3",
            "outbreak_occurred": "1",
            "attack_rate": "0.3",
        },
    ]
    with (path / "run_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    epoch_rows = []
    for run_id in ("run_noro_a", "run_noro_b"):
        epoch_rows.extend(
            [
                {
                    "run_id": run_id,
                    "epoch": "0",
                    "infected": "3",
                    "symptomatic": "1",
                    "recovered": "0",
                    "new_infections": "2",
                    "quarantined": "0",
                    "trigger_status": "SUSPECTED",
                },
                {
                    "run_id": run_id,
                    "epoch": "1",
                    "infected": "4",
                    "symptomatic": "2",
                    "recovered": "1",
                    "new_infections": "1",
                    "quarantined": "1",
                    "trigger_status": "CONFIRMED",
                },
            ]
        )
    with (path / "epoch_timeseries.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(epoch_rows[0]))
        writer.writeheader()
        writer.writerows(epoch_rows)


def test_data_assembly_helpers_cover_filters_and_shapes() -> None:
    rows = [
        {
            "run_id": "a",
            "pathogen": "norovirus",
            "pathogen_id": "norovirus_only",
            "platform_id": "mega_cruise_5000",
            "surveillance_strategy": "syndromic",
            "dose_adjustment": "10.6",
            "vsp_lockdown_threshold": "never",
            "seed": "1",
            "num_agents": "20",
            "outbreak_occurred": "1",
            "attack_rate": "0.0",
            "initial_infected": "2",
        },
        {
            "run_id": "b",
            "pathogen": "sars-cov-2",
            "pathogen_id": "covid",
            "platform_id": "expedition_cruise_450",
            "surveillance_strategy": "none",
            "dose_adjustment": "10.3",
            "outbreak_occurred": "1",
            "attack_rate": "1.0",
            "initial_infected": "4",
        },
    ]

    outbreak, outbreak_meta = _data.build_outbreak_stan_data(rows)
    boundary, boundary_meta = _boundary_data.build_boundary_outbreak_stan_data(
        rows,
        pathogen="sarscov2",
    )
    boundary_ar, ar_meta = _boundary_data.build_boundary_ar_stan_data(
        rows,
        pathogen="sarscov2",
    )

    assert outbreak["N_runs"] == 1
    assert outbreak["outbreak"] == [1]
    assert outbreak["vsp_threshold"] == [1.0]
    assert outbreak_meta["n_outbreaks"] == 1
    assert boundary["N_runs"] == 1
    assert boundary["log_k"][0] == pytest.approx(1.38629436112)
    assert boundary_meta["pathogen"] == "sarscov2"
    assert boundary_ar["N_runs"] == 1
    assert 0 < boundary_ar["ar"][0] < 1
    assert ar_meta["mean_ar"] > 0


def test_fit_wrappers_write_skipped_status_without_cmdstan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    analysis = tmp_path / "analysis"
    _write_analysis(analysis)
    monkeypatch.setattr(fit_norovirus_outbreak, "cmdstan_available", lambda: False)
    monkeypatch.setattr(fit_norovirus_trajectory, "cmdstan_available", lambda: False)
    monkeypatch.setattr(fit_boundary_hurdle, "cmdstan_available", lambda: False)

    outbreak = fit_norovirus_outbreak.fit_model("analysis", "outbreak")
    trajectory = fit_norovirus_trajectory.fit_model("analysis", "trajectory")
    boundary = fit_boundary_hurdle.fit_boundary_hurdle(
        "analysis",
        "boundary",
        pathogen="norovirus",
    )

    assert outbreak["status"] == "skipped"
    assert trajectory["status"] == "skipped"
    assert boundary["status"] == "partial"
    assert json.loads(
        (tmp_path / "outbreak" / "fit_status.json").read_text(encoding="utf-8")
    )["status"] == "skipped"
    assert json.loads(
        (tmp_path / "trajectory" / "fit_status.json").read_text(encoding="utf-8")
    )["status"] == "skipped"
    assert json.loads(
        (tmp_path / "boundary" / "outbreak" / "fit_status.json").read_text(
            encoding="utf-8"
        )
    )["status"] == "skipped"


def test_fit_wrapper_argument_parsers_and_combined_hurdle_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    analysis = tmp_path / "analysis"
    _write_analysis(analysis)
    monkeypatch.setattr(fit_norovirus_outbreak, "cmdstan_available", lambda: False)
    monkeypatch.setattr(fit_norovirus_trajectory, "cmdstan_available", lambda: False)

    outbreak_code = fit_norovirus_outbreak.main(
        ["analysis", "--out", "parsed-out", "--no-show-progress"]
    )
    trajectory_code = fit_norovirus_trajectory.main(
        ["analysis", "--out", "parsed-trajectory", "--no-show-progress"]
    )
    hurdle_code = fit_norovirus_hurdle.main(
        ["analysis", "--out-dir", "hurdle-out", "--no-show-progress"]
    )

    assert outbreak_code == 0
    assert trajectory_code == 0
    assert hurdle_code == 0
    combined = json.loads(
        (tmp_path / "hurdle-out" / "fit_status.json").read_text(encoding="utf-8")
    )
    assert combined["status"] == "skipped"
