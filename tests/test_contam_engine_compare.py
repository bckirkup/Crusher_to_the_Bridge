"""
test_contam_engine_compare.py – Contam dual-engine compare suite
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Offline-safe tests for ``tools/contam_engine_compare.py`` and ContamX
discovery under ``third_party/contamx/``. Live ContamX comparisons skip
when no binary is present.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.contamx_runner import find_contamx  # noqa: E402
from tools import contam_engine_compare as cec  # noqa: E402

_SUITE = REPO_ROOT / "data" / "config" / "contam_compare" / "suite.json"
_JOBS_DIR = REPO_ROOT / "data" / "config" / "contam_compare" / "jobs"


def test_suite_and_jobs_exist_and_validate() -> None:
    assert _SUITE.is_file()
    suite, jobs = cec.load_suite(str(_SUITE.relative_to(REPO_ROOT)))
    assert suite.get("jobs")
    assert len(jobs) >= 4
    for job in jobs:
        assert "id" in job
        assert job["mode"] in ("transport", "full_sim")
        assert "platform" in job
        platform_dir = REPO_ROOT / "data" / "platforms" / job["platform"]
        assert (platform_dir / "spatial_layout.json").is_file()
        assert (platform_dir / "air_flow_paths.json").is_file()


def test_third_party_readme_tracked_and_dir_ready() -> None:
    readme = REPO_ROOT / "third_party" / "contamx" / "README.md"
    assert readme.is_file()
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "third_party/contamx/**" in gitignore
    assert "!third_party/contamx/README.md" in gitignore


def test_find_contamx_discovers_third_party_drop(tmp_path, monkeypatch) -> None:
    # Point the runner's repo-root third_party via a fake executable name search
    # by setting CONTAMX_HOME to a temp dir with a stub "contamx" file.
    stub = tmp_path / "contamx"
    stub.write_text("#!/bin/sh\n", encoding="utf-8")
    stub.chmod(0o755)
    monkeypatch.delenv("CONTAMX_BINARY", raising=False)
    monkeypatch.setenv("CONTAMX_HOME", str(tmp_path))
    found = find_contamx({})
    assert found == str(stub.resolve())


def test_transport_job_native_only_offline() -> None:
    job = json.loads(
        (_JOBS_DIR / "destroyer_transport.json").read_text(encoding="utf-8"),
    )
    # Force offline ContamX by clearing discovery env and using empty config path
    job = {**job, "repeats": 1, "epochs": 3}
    report = cec.run_transport_job(job)
    assert report["mode"] == "transport"
    assert report["native"]["timing"]["seconds_mean"] >= 0.0
    assert report["native"]["final_concentrations"]
    inv = report["native"]["path_inventory"]
    assert inv["n_paths"] == report["native"]["n_paths"]
    assert inv["by_type"]
    assert inv["injection_connectivity"]
    assert inv["injection_connectivity"][0]["zone"] == "Bridge"
    assert inv["injection_connectivity"][0]["out_degree"] > 0
    # ContamX may or may not be present; structure must always be valid
    assert "contamx_available" in report
    if report["contamx_available"]:
        assert report["divergence"] is not None
        assert "final_l1" in report["divergence"]
        assert report["contamx"]["timing"]["seconds_mean"] >= 0.0
        assert "path_inventory" in report["contamx"]
        assert "contamx_injection_isolated" in report
    else:
        assert report.get("contamx_error")


def test_path_inventory_marks_isolated_injection() -> None:
    spatial = json.loads(
        (REPO_ROOT / "data/platforms/destroyer_baseline/spatial_layout.json")
        .read_text(encoding="utf-8")
    )
    airflow = json.loads(
        (REPO_ROOT / "data/platforms/destroyer_baseline/air_flow_paths.json")
        .read_text(encoding="utf-8")
    )
    eng = cec.ContamTransportEngine(
        spatial_layout=spatial,
        air_flow_paths=airflow,
    )
    # Empty path list → every inject zone is ContamX-isolated style
    eng.airflow_paths = []
    inv = cec._path_inventory(eng, {"Bridge": 1.0e6})
    assert inv["n_paths"] == 0
    assert inv["injection_connectivity"][0]["isolated"] is True
    assert inv["edges_sample"] == []


def test_full_sim_job_native_offline() -> None:
    job = {
        "id": "destroyer_fullsim_smoke",
        "mode": "full_sim",
        "platform": "destroyer_baseline",
        "epochs": 2,
        "seed": 7,
        "repeats": 1,
    }
    report = cec.run_full_sim_job(job)
    assert report["mode"] == "full_sim"
    assert report["native"]["summary"]["n_agents"] > 0
    assert report["native"]["timing"]["seconds_mean"] > 0.0


def test_cli_suite_writes_report(tmp_path, monkeypatch) -> None:
    # Write under repo telemetry path (validated_open requires repo root)
    out_rel = "telemetry_buffer/contam_compare/test_cli_report.json"
    out_full = REPO_ROOT / out_rel
    if out_full.exists():
        out_full.unlink()
    # Use a tiny one-job suite via --job for speed
    rc = cec.main([
        "--job", "data/config/contam_compare/jobs/destroyer_transport.json",
        "--json-out", out_rel,
    ])
    assert rc == 0
    assert out_full.is_file()
    data = json.loads(out_full.read_text(encoding="utf-8"))
    assert data["jobs"]
    assert data["jobs"][0]["id"] == "destroyer_transport"
    out_full.unlink(missing_ok=True)


@pytest.mark.skipif(
    find_contamx({}) is None,
    reason="ContamX binary not available",
)
def test_live_contamx_transport_compare() -> None:
    job = {
        "id": "live_destroyer_transport",
        "mode": "transport",
        "platform": "destroyer_baseline",
        "epochs": 4,
        "inject": ["Bridge:1e6"],
        "repeats": 1,
    }
    report = cec.run_transport_job(job)
    assert report["contamx_available"] is True
    assert report["divergence"]["final_l1"] >= 0.0
    assert report["speedup_native_over_contamx"] is not None
