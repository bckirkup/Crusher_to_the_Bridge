"""D2 worker tests — the offline argv shim and local transports.

``worker.main`` is driven end-to-end with a request document on disk:
materialize writes the derived namespace under a LocalDirStore, then a
query phase exports bounded pages. LocalTransport is confined to the
declared source root.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys

import pytest
from zip_builders import build_zip, member

from picard_framework.analysis.campaign_reducer.ledger import BUDGET_FIELDS
from picard_framework.analysis.campaign_reducer.pinned_reader import (
    TransportError,
)
from picard_framework.analysis.campaign_reducer.worker import (
    EXIT_COMPLETE,
    EXIT_INVALID_CONTRACT,
    LocalTransport,
    main,
)


@pytest.fixture(autouse=True)
def _forbid_external(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*a, **k):
        raise AssertionError("network access forbidden in offline tests")

    monkeypatch.setattr(socket, "create_connection", _raise)
    monkeypatch.setattr(socket.socket, "connect", _raise)
    monkeypatch.setattr(subprocess, "run", _raise)
    monkeypatch.setattr(subprocess, "Popen", _raise)
    monkeypatch.setitem(sys.modules, "boto3", None)
    monkeypatch.setitem(sys.modules, "botocore", None)


def _budgets():
    doc = dict.fromkeys(BUDGET_FIELDS, 1_000_000_000.0)
    doc["safety_factor"] = 1.5
    return doc


def _fixture(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    fused = build_zip(
        [
            member("run_1/summary.json",
                   json.dumps({"attack_rate": 0.5}).encode()),
            member("run_2/summary.json",
                   json.dumps({"attack_rate": 0.25}).encode()),
        ]
    )
    (src / "fused.zip").write_bytes(fused)
    request = {
        "reduction_id": "red-w",
        "snapshot_id": "snap-w",
        "budgets": _budgets(),
        "source_root": str(src),
        "shard_size": 1,
        "utc": "2026-01-01T00:00:00Z",
        "sources": [
            {
                "uri": "fused.zip",
                "family": "campaign_summary_zip",
                "source_id": "fused.zip",
                "campaign_id": "camp1",
            }
        ],
    }
    req_path = tmp_path / "request.json"
    req_path.write_text(json.dumps(request))
    out_dir = tmp_path / "derived"
    return req_path, out_dir, request


def test_worker_materialize_then_query(tmp_path, capsys, monkeypatch):
    # The offline store confines out-uri to the process working directory.
    monkeypatch.chdir(tmp_path)
    req_path, out_dir, request = _fixture(tmp_path)
    rc = main([
        "--phase", "materialize",
        "--request-uri", str(req_path),
        "--out-uri", str(out_dir),
    ])
    assert rc == EXIT_COMPLETE
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "completed"

    commit_key = (
        "campaign/_derived/reducer/v1/attempts/red-w/COMMIT.json"
    )
    commit = json.loads((out_dir / commit_key).read_text())
    assert commit["status"] == "completed"

    query = {
        "contract_id": "crusher-campaign-distributions/1.0-proposed",
        "catalog_snapshot_id": commit["catalog_snapshot_id"],
        "operation": "query",
        "analysis_version": "test",
        "source_table": "run_scalars",
        "metric_ids": [],
        "filters": {"ne": ["row_id", "__never__"]},
        "group_by": [],
        "statistic": "exact_rows",
        "weight_set_id": "w-equal",
        "missing_policy": "report_separately",
        "max_export_rows": 1000,
        "max_export_bytes": 5 * 1024 * 1024,
        "page_rows": 100,
        "allow_raw_agent_export": False,
        "scan_budget": {
            "max_scan_bytes": 10**9,
            "max_wall_seconds": 600,
            "max_cost_usd": 10.0,
        },
        "grain": "run",
        "joins": [],
        "order_by": ["native_path"],
        "continuation_token": None,
    }
    q_req = dict(request)
    q_req["query"] = query
    q_req["commit_uri"] = commit_key
    q_path = tmp_path / "query_request.json"
    q_path.write_text(json.dumps(q_req))
    rc = main([
        "--phase", "query",
        "--request-uri", str(q_path),
        "--out-uri", str(out_dir),
    ])
    assert rc == EXIT_COMPLETE
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] in ("completed", "partial")
    pages = list(
        (out_dir / "campaign/_derived/reducer/v1/queries").glob(
            "*/page-*.jsonl"
        )
    )
    assert pages
    rows = [
        json.loads(line)
        for p in pages
        for line in p.read_text().splitlines()
    ]
    attack = [r for r in rows if r["native_path"] == "/attack_rate"]
    assert len(attack) == 2


def test_worker_rejects_bad_request_uri(tmp_path, capsys):
    rc = main([
        "--phase", "materialize",
        "--request-uri", str(tmp_path / "absent.json"),
    ])
    assert rc == EXIT_INVALID_CONTRACT


def test_local_transport_confined_to_root(tmp_path):
    (tmp_path / "ok.bin").write_bytes(b"data")
    transport = LocalTransport(tmp_path)
    info = transport.head("ok.bin")
    assert info.content_length == 4
    resp = transport.get("ok.bin", start=1, end=2)
    assert resp.body == b"at"
    with pytest.raises(TransportError):
        transport.head("../outside.bin")
    with pytest.raises(TransportError):
        transport.head("missing.bin")
