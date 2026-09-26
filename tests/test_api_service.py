"""Tests for the api/ FastAPI simulation service.

Opt-in only: each test spins real voyages, so the module is skipped during
CI, routine ``pytest tests/``, and campaign work. Run it explicitly with
``CTTB_API_TESTS=1 python3 -m pytest tests/test_api_service.py``.
Also skipped when the ``api`` extra (fastapi/uvicorn) is not installed.
"""

from __future__ import annotations

import os
import sys
import time

import pytest

if not os.environ.get("CTTB_API_TESTS"):
    pytest.skip(
        "API service tests are opt-in (CTTB_API_TESTS=1); they run real voyages",
        allow_module_level=True,
    )
pytest.importorskip("fastapi")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from starlette.testclient import TestClient

from api.app import create_app
from telemetry_buffer.schema import resolve_telemetry_path

SMOKE_SPEC = {
    "schema_version": "1.0.0",
    "catalog": {
        "platform_id": "destroyer_baseline",
        "pathogen_bundle_id": "active_profiles",
    },
    "run": {"random_seed": 42, "num_epochs": 2, "write_ground_truth": False},
    "legacy_yaml": "crusher_labs/config.yaml",
    "actors": [],
    "incentives": {},
}

TERMINAL = {"succeeded", "failed", "cancelled"}
POLL_DEADLINE_S = 120.0


def _client(**kwargs) -> TestClient:
    return TestClient(create_app(repo_root=REPO_ROOT, **kwargs))


def _wait_terminal(client: TestClient, job_id: str) -> dict:
    deadline = time.monotonic() + POLL_DEADLINE_S
    while time.monotonic() < deadline:
        body = client.get(f"/v1/runs/{job_id}").json()
        if body["status"] in TERMINAL:
            return body
        time.sleep(0.5)
    pytest.fail(f"job {job_id} did not reach a terminal state in {POLL_DEADLINE_S}s")


def test_health_is_open() -> None:
    response = _client().get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_catalog_lists_platforms_and_bundles() -> None:
    response = _client().get("/v1/catalog")
    assert response.status_code == 200
    body = response.json()
    assert "destroyer_baseline" in body["platforms"]
    assert "active_profiles" in body["pathogen_bundles"]


def test_submit_rejects_schema_violation() -> None:
    response = _client().post("/v1/runs", json={"catalog": {}})
    assert response.status_code == 422


def test_submit_rejects_unknown_platform() -> None:
    spec = dict(SMOKE_SPEC, catalog=dict(SMOKE_SPEC["catalog"], platform_id="nope"))
    response = _client().post("/v1/runs", json=spec)
    assert response.status_code == 422


def test_submit_rejects_non_object_body() -> None:
    response = _client().post("/v1/runs", json=[1, 2, 3])
    assert response.status_code == 422


def test_run_lifecycle_succeeds() -> None:
    client = _client()
    submitted = client.post("/v1/runs", json=SMOKE_SPEC)
    assert submitted.status_code == 202
    job_id = submitted.json()["job_id"]

    detail = _wait_terminal(client, job_id)
    assert detail["status"] == "succeeded"
    assert detail["epochs_completed"] == detail["num_epochs"] == 2
    assert detail["error"] is None

    result = detail["result"]
    assert result["num_epochs"] == 2
    assert len(result["history"]) == 2
    assert isinstance(result["final_trigger_status"], str)

    telemetry = detail["telemetry"]
    assert f"api_jobs/{job_id}" in telemetry["simulation_history"]
    # telemetry_buffer/… paths resolve under telemetry_dir(), which xdist
    # workers redirect via CTTB_TELEMETRY_DIR — resolve, don't join.
    history_path = resolve_telemetry_path(
        telemetry["simulation_history"], REPO_ROOT,
    )
    assert os.path.isfile(history_path)

    listing = client.get("/v1/runs").json()
    assert [j["job_id"] for j in listing][0] == job_id


def test_cancel_then_delete() -> None:
    client = _client()
    long_spec = dict(SMOKE_SPEC, run=dict(SMOKE_SPEC["run"], num_epochs=100000))
    job_id = client.post("/v1/runs", json=long_spec).json()["job_id"]

    cancelled = client.post(f"/v1/runs/{job_id}/cancel")
    assert cancelled.status_code == 202

    detail = _wait_terminal(client, job_id)
    assert detail["status"] == "cancelled"
    assert detail["cancel_requested"] is True

    assert client.delete(f"/v1/runs/{job_id}").status_code == 204
    assert client.get(f"/v1/runs/{job_id}").status_code == 404


def test_delete_running_job_conflicts() -> None:
    client = _client()
    long_spec = dict(SMOKE_SPEC, run=dict(SMOKE_SPEC["run"], num_epochs=100000))
    job_id = client.post("/v1/runs", json=long_spec).json()["job_id"]
    try:
        # Queued or running, a delete without cancel is a conflict.
        assert client.delete(f"/v1/runs/{job_id}").status_code == 409
    finally:
        client.post(f"/v1/runs/{job_id}/cancel")
        _wait_terminal(client, job_id)


def test_bearer_auth_gates_api_not_health() -> None:
    client = _client(auth_token="s3cret")
    assert client.get("/health").status_code == 200
    assert client.get("/v1/catalog").status_code == 401
    assert (
        client.get("/v1/catalog", headers={"Authorization": "Bearer s3cret"})
        .status_code
        == 200
    )
    assert (
        client.get("/v1/catalog", headers={"Authorization": "Bearer wrong"})
        .status_code
        == 401
    )


def test_cancel_terminal_job_conflicts() -> None:
    client = _client()
    job_id = client.post("/v1/runs", json=SMOKE_SPEC).json()["job_id"]
    detail = _wait_terminal(client, job_id)
    assert detail["status"] == "succeeded"
    assert client.post(f"/v1/runs/{job_id}/cancel").status_code == 409
