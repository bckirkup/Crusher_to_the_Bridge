"""Telemetry output paths follow the process-wide telemetry directory override."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import orchestrator_record
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


def test_finalize_simulation_routes_all_notebook_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("CTTB_TELEMETRY_DIR", str(tmp_path))
    state = SimpleNamespace(simulation_history=[], escalation_log=[])
    engine = SimpleNamespace(get_summary=lambda: {})
    cost_ledger = SimpleNamespace(generate_financial_audit=lambda: {})
    protocol_engine = SimpleNamespace(generate_protocol_summary=lambda: {})
    proto_ctx = SimpleNamespace(
        cost_ledger=cost_ledger,
        protocol_engine=protocol_engine,
    )

    def run_finalize(
        notebook_path: str | None,
        logging_config: dict,
    ) -> None:
        monkeypatch.setattr(
            orchestrator_record,
            "load_logging_profile",
            lambda _path: ({}, {}, logging_config),
        )
        orchestrator_record.finalize_simulation(
            state=state,
            engine=engine,
            obs=SimpleNamespace(
                lab_notebook_enabled=True,
                notebook=ArtificialLabNotebook(),
            ),
            proto_ctx=proto_ctx,
            pathogen_profiles={},
            zone_names=[],
            num_agents=0,
            num_epochs=0,
            lab_notebook_path=notebook_path,
            display=False,
        )

    run_finalize(None, {})
    assert (tmp_path / "artificial_lab_notebook.json").exists()

    explicit_path = tmp_path / "explicit.json"
    run_finalize(str(explicit_path), {})
    assert explicit_path.exists()

    configured_path = tmp_path / "configured.json"
    run_finalize(None, {"lab_notebook": {"output_path": str(configured_path)}})
    assert configured_path.exists()


def test_telemetry_output_rejects_paths_outside_allowed_roots() -> None:
    with pytest.raises(ValueError, match="escapes allowed roots"):
        orchestrator_record._resolve_telemetry_output(
            "/tmp/outside-telemetry.json",
            allowed_roots=(str(REPO_ROOT),),
        )


def test_ground_truth_default_path_follows_env_set_after_import(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("CTTB_TELEMETRY_DIR", str(tmp_path))
    payload = make_ground_truth(epoch=3, agents=[make_agent(1)], spaces={})

    write_ground_truth(payload)

    assert (tmp_path / "ground_truth.json").exists()
    assert read_ground_truth() == payload


@pytest.mark.parametrize(
    "configured, expected_name",
    [
        ("telemetry_buffer/artificial_lab_notebook.json", "artificial_lab_notebook.json"),
        ("telemetry_buffer/notebook.json", "notebook.json"),
        ("./telemetry_buffer/nested/../renamed.json", "renamed.json"),
    ],
)
def test_telemetry_buffer_relative_outputs_follow_override(
    monkeypatch,
    tmp_path: Path,
    configured: str,
    expected_name: str,
) -> None:
    monkeypatch.setenv("CTTB_TELEMETRY_DIR", str(tmp_path))
    resolved = orchestrator_record._resolve_telemetry_output(
        configured, allowed_roots=(str(REPO_ROOT), telemetry_dir()),
    )
    assert resolved == os.path.join(os.path.realpath(tmp_path), expected_name)


def test_non_telemetry_relative_output_stays_under_repo(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CTTB_TELEMETRY_DIR", str(tmp_path))
    resolved = orchestrator_record._resolve_telemetry_output(
        "picard_framework/runs/out.json", allowed_roots=(str(REPO_ROOT), telemetry_dir()),
    )
    assert resolved == str(REPO_ROOT / "picard_framework" / "runs" / "out.json")
