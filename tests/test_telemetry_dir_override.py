"""Telemetry output paths follow the process-wide telemetry directory override."""

from __future__ import annotations

import os
from pathlib import Path

from crusher_labs.lab_notebook import ArtificialLabNotebook
from picard_framework.run_spec import TelemetryPaths
from telemetry_buffer import (
    make_agent,
    make_ground_truth,
    make_space,
    read_ground_truth,
    telemetry_dir,
    write_ground_truth,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_telemetry_dir_override_controls_defaults(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("CTTB_TELEMETRY_DIR", str(tmp_path))
    override = os.path.realpath(tmp_path)

    assert telemetry_dir(str(REPO_ROOT)) == override
    paths = TelemetryPaths(repo_root=str(REPO_ROOT))
    assert paths.ground_truth.startswith(override + os.sep)
    assert paths.simulation_history.startswith(override + os.sep)
    assert paths.lab_notebook.startswith(override + os.sep)

    payload = make_ground_truth(
        epoch=0,
        agents=[make_agent(0)],
        spaces={"Bridge": make_space()},
    )
    output = tmp_path / "ground_truth.json"
    write_ground_truth(payload, path=str(output))
    assert read_ground_truth(path=str(output)) == payload

    notebook = ArtificialLabNotebook()
    notebook_path = tmp_path / "artificial_lab_notebook.json"
    notebook.serialize(str(notebook_path))
    assert notebook_path.exists()


def test_telemetry_dir_defaults_to_repository(monkeypatch) -> None:
    monkeypatch.delenv("CTTB_TELEMETRY_DIR", raising=False)
    paths = TelemetryPaths(repo_root=str(REPO_ROOT))

    assert telemetry_dir(str(REPO_ROOT)) == str(REPO_ROOT / "telemetry_buffer")
    assert paths.ground_truth == str(REPO_ROOT / "telemetry_buffer" / "ground_truth.json")
    assert paths.simulation_history == str(
        REPO_ROOT / "telemetry_buffer" / "simulation_history.json",
    )
    assert paths.lab_notebook == str(
        REPO_ROOT / "telemetry_buffer" / "artificial_lab_notebook.json",
    )
