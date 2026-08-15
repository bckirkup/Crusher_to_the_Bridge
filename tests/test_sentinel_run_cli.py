"""The operator layer: fit directory -> artifacts -> figures + report.

These tests exercise the reading half of the sentinel pipeline, so they build
fit directories directly instead of sampling: the estimator has its own suites
(``test_sentinel_fleet_validation``), and what can silently go wrong here is
presentation — a port ranked the wrong way round, a reference-walker interval
quoted as a posterior, a wastewater section that implies its own hazard, or a
skipped fit reported as if it had results.

Everything runs from a scratch directory inside the repository because
``picard_framework.analysis._io`` confines reads and writes to the process CWD
(Sonar S8707); a fit directory under ``/tmp`` is refused by design.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import sys
from typing import Any, Iterator, Sequence

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis.sentinel import figures as figures_module
from picard_framework.analysis.sentinel import run_sentinel
from picard_framework.analysis.sentinel.artifacts import (
    MODE_FLEET,
    MODE_SINGLE,
    as_bool,
    as_float,
    load_fit_artifacts,
)
from picard_framework.analysis.sentinel.figures import write_sentinel_figures
from picard_framework.analysis.sentinel.report import write_report

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(REPO, "out_test_sentinel_cli")

_FLEET_COLUMNS = (
    "port_id",
    "pathogen",
    "hazard_mean",
    "hazard_q05",
    "hazard_q95",
    "n_attributed_cases",
    "attribution_share",
    "n_visits",
    "person_hours_ashore",
    "fleet_time_confounded",
    "port_resolution_adequate",
)
# Graded hazards: MXCZM > MXCTM > KYGEC, so a ranking bug is visible as an order
# change rather than as a value change.
_PORT_ROWS = (
    {
        "port_id": "KYGEC",
        "pathogen": "norovirus",
        "hazard_mean": 1e-05,
        "hazard_q05": 2e-06,
        "hazard_q95": 3e-05,
        "n_attributed_cases": 1.0,
        "attribution_share": 0.05,
        "n_visits": 2,
        "person_hours_ashore": 64260.0,
        "fleet_time_confounded": False,
        "port_resolution_adequate": True,
    },
    {
        "port_id": "MXCTM",
        "pathogen": "norovirus",
        "hazard_mean": 2e-05,
        "hazard_q05": 5e-06,
        "hazard_q95": 6e-05,
        "n_attributed_cases": 2.0,
        "attribution_share": 0.10,
        "n_visits": 2,
        "person_hours_ashore": 70500.0,
        "fleet_time_confounded": True,
        "port_resolution_adequate": True,
    },
    {
        "port_id": "MXCZM",
        "pathogen": "norovirus",
        "hazard_mean": 4e-05,
        "hazard_q05": 9e-06,
        "hazard_q95": 9e-05,
        "n_attributed_cases": 3.0,
        "attribution_share": 0.20,
        "n_visits": 2,
        "person_hours_ashore": 93150.0,
        "fleet_time_confounded": False,
        "port_resolution_adequate": True,
    },
)
_VISIT_ROWS = (
    {
        "visit_key": "KYGEC@2026-W03",
        "port_id": "KYGEC",
        "week": "2026-W03",
        "hazard_mean": 1.1e-05,
        "hazard_q05": 2e-06,
        "hazard_q95": 3e-05,
        "n_attributed_cases": 0.6,
        "person_hours_ashore": 42840.0,
    },
    {
        "visit_key": "MXCZM@2026-W04",
        "port_id": "MXCZM",
        "week": "2026-W04",
        "hazard_mean": 3.9e-05,
        "hazard_q05": 8e-06,
        "hazard_q95": 8e-05,
        "n_attributed_cases": 1.4,
        "person_hours_ashore": 31050.0,
    },
)
_WEEK_ROWS = (
    {
        "week": "2026-W03",
        "log_effect_mean": 0.12,
        "log_effect_q05": -0.2,
        "log_effect_q95": 0.4,
        "hazard_multiplier_mean": 1.13,
    },
    {
        "week": "2026-W04",
        "log_effect_mean": -0.05,
        "log_effect_q05": -0.5,
        "log_effect_q95": 0.3,
        "hazard_multiplier_mean": 0.95,
    },
)
_ONBOARD = {
    "import_share_mean": 0.27,
    "import_share_q05": 0.01,
    "import_share_q95": 0.62,
    "aboard_cases_mean": 6.8,
    "secondary_cases_mean": 7.1,
    "ships": [
        {
            "ship_id": "AURORA",
            "lambda_aboard_mean": 2.8e-06,
            "r_onboard_mean": 0.51,
            "r_onboard_q05": 0.2,
            "r_onboard_q95": 0.99,
        },
    ],
}
_CREW = {
    "crew_hazard_ratio_mean": 1.16,
    "crew_hazard_ratio_q05": 0.5,
    "crew_hazard_ratio_q95": 2.17,
    "repeat_hazard_ratio_mean": 0.96,
    "repeat_hazard_ratio_q05": 0.52,
    "repeat_hazard_ratio_q95": 2.26,
}
_WASTEWATER = {
    "enabled": True,
    "fitted": True,
    "n_pooled_samples": 4,
    "n_raw_samples": 7,
    "slope_mean": 0.52,
    "slope_q05": 0.46,
    "slope_q95": 0.59,
    "concentration_mean": 2991.5,
    "residence_lag_epochs": 12,
    "loglik_clinical": -62.8,
    "loglik_wastewater": -23.9,
}
_META = {"pathogen": "norovirus", "n_cases": 13, "censoring_corrected": True}


def _write_csv(path: str, rows: Sequence[dict[str, Any]], columns: Sequence[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)


@pytest.fixture()
def scratch() -> Iterator[str]:
    shutil.rmtree(SCRATCH, ignore_errors=True)
    os.makedirs(SCRATCH)
    try:
        yield SCRATCH
    finally:
        shutil.rmtree(SCRATCH, ignore_errors=True)


def _fleet_fit_dir(scratch: str, *, engine: str = "numpy_rw_mh", name: str = "fit") -> str:
    fit = os.path.join(scratch, name)
    os.makedirs(fit, exist_ok=True)
    _write_csv(
        os.path.join(fit, "fleet_port_hazards.csv"), _PORT_ROWS, _FLEET_COLUMNS,
    )
    _write_csv(
        os.path.join(fit, "visit_hazards.csv"), _VISIT_ROWS, tuple(_VISIT_ROWS[0]),
    )
    _write_csv(os.path.join(fit, "fleet_time.csv"), _WEEK_ROWS, tuple(_WEEK_ROWS[0]))
    _write_json(os.path.join(fit, "onboard_summary.json"), _ONBOARD)
    _write_json(os.path.join(fit, "crew_exposure.json"), _CREW)
    _write_json(os.path.join(fit, "wastewater_channel.json"), _WASTEWATER)
    _write_json(os.path.join(fit, "stan_data_meta.json"), _META)
    _write_json(
        os.path.join(fit, "fit_status.json"),
        {"status": "smoke" if engine == "numpy_rw_mh" else "ok", "engine": engine},
    )
    return fit


def _single_fit_dir(scratch: str) -> str:
    fit = os.path.join(scratch, "single")
    os.makedirs(fit, exist_ok=True)
    _write_csv(os.path.join(fit, "port_hazards.csv"), _PORT_ROWS, _FLEET_COLUMNS)
    _write_json(
        os.path.join(fit, "onboard_summary.json"),
        {
            "import_share_mean": 0.36,
            "aboard_cases_mean": 1.8,
            "r_onboard_mean": 0.63,
            "r_onboard_q05": 0.13,
            "r_onboard_q95": 1.13,
        },
    )
    _write_json(os.path.join(fit, "stan_data_meta.json"), _META)
    _write_json(os.path.join(fit, "fit_status.json"), {"status": "ok", "engine": "cmdstan"})
    return fit


def _relative(path: str) -> str:
    """Paths handed to the CLI must be relative to the CWD it confines to."""
    return os.path.relpath(path, os.getcwd())


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def test_fleet_fit_dir_loads_every_optional_table(scratch: str) -> None:
    artifacts = load_fit_artifacts(_relative(_fleet_fit_dir(scratch)))
    assert artifacts.mode == MODE_FLEET
    assert [r["port_id"] for r in artifacts.port_rows] == ["KYGEC", "MXCTM", "MXCZM"]
    assert len(artifacts.visit_rows) == len(_VISIT_ROWS)
    assert len(artifacts.week_rows) == len(_WEEK_ROWS)
    assert artifacts.crew
    assert artifacts.wastewater
    assert artifacts.onboard
    assert artifacts.pathogen == "norovirus"
    assert artifacts.engine == "numpy_rw_mh"
    assert artifacts.is_reference_walker is True


def test_single_ship_fit_dir_is_not_read_as_a_fleet(scratch: str) -> None:
    artifacts = load_fit_artifacts(_relative(_single_fit_dir(scratch)))
    assert artifacts.mode == MODE_SINGLE
    assert artifacts.visit_rows == []
    assert artifacts.week_rows == []
    assert artifacts.is_reference_walker is False


def test_fit_with_no_hazard_table_is_refused_not_reported(scratch: str) -> None:
    """A skipped fit must raise, not yield an artifacts object with no ports.

    Reporting on a fit that never sampled is the failure this guard exists for:
    the report would carry a title, a pathogen, and no hazards at all.
    """
    fit = os.path.join(scratch, "skipped")
    os.makedirs(fit)
    _write_json(
        os.path.join(fit, "fit_status.json"),
        {"status": "skipped", "reason": "cmdstanpy not installed"},
    )
    with pytest.raises(SystemExit) as exc:
        load_fit_artifacts(_relative(fit))
    message = str(exc.value)
    assert "skipped" in message
    assert "cmdstanpy not installed" in message


def test_missing_directory_is_refused(scratch: str) -> None:
    with pytest.raises(SystemExit):
        load_fit_artifacts(_relative(os.path.join(scratch, "absent")))


@pytest.mark.parametrize(
    ("text", "expected"),
    [("True", True), ("true", True), ("1", True), ("False", False), ("", False)],
)
def test_csv_booleans_survive_the_round_trip(text: str, expected: bool) -> None:
    """``bool('False')`` is True, so the CSV text must be parsed, not cast."""
    assert as_bool(text) is expected


def test_blank_csv_cells_do_not_become_zero() -> None:
    assert as_float("") != as_float("", default=1.0)
    assert as_float("2.5") == pytest.approx(2.5)
    assert as_float("not-a-number", default=-1.0) == pytest.approx(-1.0)


def test_report_ranks_ports_by_hazard_and_flags_the_confounded_one(
    scratch: str,
) -> None:
    artifacts = load_fit_artifacts(_relative(_fleet_fit_dir(scratch)))
    text = _read(write_report(_relative(os.path.join(scratch, "out")), artifacts))
    order = [text.index(f"| {port} |") for port in ("MXCZM", "MXCTM", "KYGEC")]
    assert order == sorted(order), "highest hazard must be listed first"
    confounded = next(line for line in text.splitlines() if line.startswith("| MXCTM |"))
    clean = next(line for line in text.splitlines() if line.startswith("| MXCZM |"))
    assert confounded.rstrip().endswith("| yes |")
    assert clean.rstrip().endswith("| no |")


def test_report_marks_reference_walker_intervals_as_uncalibrated(
    scratch: str,
) -> None:
    walker = load_fit_artifacts(_relative(_fleet_fit_dir(scratch)))
    nuts = load_fit_artifacts(
        _relative(_fleet_fit_dir(scratch, engine="cmdstan", name="nuts")),
    )
    walker_text = _read(
        write_report(_relative(os.path.join(scratch, "walker")), walker),
    )
    nuts_text = _read(write_report(_relative(os.path.join(scratch, "nuts_out")), nuts))
    assert "Reference walker, not NUTS" in walker_text
    assert "Reference walker, not NUTS" not in nuts_text
    assert "`cmdstan`" in nuts_text


def test_report_presents_wastewater_as_a_shared_incidence_channel(
    scratch: str,
) -> None:
    artifacts = load_fit_artifacts(_relative(_fleet_fit_dir(scratch)))
    text = _read(write_report(_relative(os.path.join(scratch, "out")), artifacts))
    assert "same latent incidence curve" in text
    assert "never get a port" in text
    assert "Log-likelihood, clinical" in text
    assert "Log-likelihood, wastewater" in text
    assert "Pooled samples: 4 (from 7 raw)" in text


def test_report_reports_an_unfitted_wastewater_channel_without_a_slope(
    scratch: str,
) -> None:
    fit = _fleet_fit_dir(scratch)
    _write_json(
        os.path.join(fit, "wastewater_channel.json"),
        {"enabled": True, "fitted": False, "n_pooled_samples": 0},
    )
    text = _read(
        write_report(
            _relative(os.path.join(scratch, "out")),
            load_fit_artifacts(_relative(fit)),
        ),
    )
    assert "Enabled but not fitted" in text
    assert "Shedding-to-read slope" not in text
    assert "Concentration scale" not in text


def test_report_omits_fleet_sections_for_a_single_voyage(scratch: str) -> None:
    artifacts = load_fit_artifacts(_relative(_single_fit_dir(scratch)))
    text = _read(write_report(_relative(os.path.join(scratch, "out")), artifacts))
    assert "Scope: single voyage" in text
    assert "## Per-visit hazards" not in text
    assert "## Fleet-time effect" not in text
    assert "## Wastewater channel" not in text
    assert "- R_onboard: 0.63" in text


def test_figure_count_follows_the_tables_the_fit_wrote(scratch: str) -> None:
    """A fleet fit supports strictly more figures than a single-voyage fit."""
    if not figures_module.have_matplotlib():
        pytest.skip("matplotlib not installed")
    fleet = write_sentinel_figures(
        _relative(os.path.join(scratch, "fleet_figs")),
        load_fit_artifacts(_relative(_fleet_fit_dir(scratch))),
    )
    single = write_sentinel_figures(
        _relative(os.path.join(scratch, "single_figs")),
        load_fit_artifacts(_relative(_single_fit_dir(scratch))),
    )
    names = {os.path.basename(p) for p in fleet}
    assert names == {
        "port_hazards.png",
        "visit_hazards.png",
        "fleet_time.png",
        "incidence_decomposition.png",
    }
    assert all(os.path.getsize(p) > 0 for p in fleet)
    assert len(single) < len(fleet)
    assert {os.path.basename(p) for p in single} == {"port_hazards.png"}


def test_figures_are_skipped_when_matplotlib_is_missing(
    scratch: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(figures_module, "have_matplotlib", lambda: False)
    artifacts = load_fit_artifacts(_relative(_fleet_fit_dir(scratch)))
    assert write_sentinel_figures(_relative(os.path.join(scratch, "none")), artifacts) == []


def test_cli_renders_an_existing_fit_without_sampling(scratch: str) -> None:
    fit = _fleet_fit_dir(scratch)
    out = os.path.join(scratch, "render")
    code = run_sentinel.main(
        ["--from-fit", _relative(fit), "--out", _relative(out), "--no-figures"],
    )
    assert code == 0
    assert os.path.isfile(os.path.join(out, "report.md"))
    assert not os.path.isdir(os.path.join(out, "figures"))
    assert not os.path.isfile(os.path.join(out, "fleet_port_hazards.csv")), (
        "--from-fit must not rewrite the fit it read"
    )


def test_cli_requires_an_input_selection() -> None:
    with pytest.raises(SystemExit) as exc:
        run_sentinel.main(["--out", "out_test_sentinel_cli_unused"])
    assert exc.value.code == 2


def test_cli_reports_a_skipped_fit_instead_of_writing_a_report(
    scratch: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No CmdStan and no --smoke: exit clean, but write no report."""
    monkeypatch.setattr(
        run_sentinel,
        "fit_sentinel_fleet",
        lambda *a, **k: {"status": "skipped", "reason": "cmdstanpy not installed"},
    )
    out = os.path.join(scratch, "skipped_run")
    manifest = os.path.join(
        "picard_framework", "analysis", "sentinel", "data", "example_fleet.json",
    )
    code = run_sentinel.main(["--manifest", manifest, "--out", _relative(out)])
    assert code == 0
    assert not os.path.isfile(os.path.join(out, "report.md"))


def test_cli_returns_nonzero_for_a_failed_fit(
    scratch: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        run_sentinel,
        "fit_sentinel_fleet",
        lambda *a, **k: {"status": "error", "reason": "compile failed"},
    )
    out = os.path.join(scratch, "error_run")
    manifest = os.path.join(
        "picard_framework", "analysis", "sentinel", "data", "example_fleet.json",
    )
    assert run_sentinel.main(["--manifest", manifest, "--out", _relative(out)]) == 1


def test_smoke_staging_copies_the_manifest_and_every_voyage_it_names(
    scratch: str,
) -> None:
    """Staging is what makes --smoke work from a directory outside the repo."""
    manifest = run_sentinel.stage_smoke_inputs(
        _relative(os.path.join(scratch, "staged")),
    )
    assert os.path.isfile(manifest)
    payload = json.loads(_read(manifest))
    staged = os.path.dirname(manifest)
    for entry in payload["voyages"]:
        for field in ("itinerary", "observations"):
            assert os.path.isfile(os.path.join(staged, entry[field]))


def test_module_entrypoint_is_the_run_cli_not_the_line_list_export() -> None:
    source_path = os.path.join(
        REPO, "picard_framework", "analysis", "sentinel", "__main__.py",
    )
    source = _read(source_path)
    assert "run_sentinel import main" in source
    assert "export_line_list" not in source.split('"""')[2]
