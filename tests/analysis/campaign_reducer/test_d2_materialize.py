"""D2 materialization tests — streaming shards, checkpoints, COMMIT status.

Fused ZIP fixtures prove every run member is materialized (never a
first-row helper); kill/resume hooks prove a kill after a partition
write and before COMMIT resumes to the same logical row set with no
conflicting overwrite; the COMMIT disqualifiers each block an
unqualified ``completed`` status.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys

import pytest
from zip_builders import build_zip, member

from picard_framework.analysis.campaign_reducer.derived_store import (
    DerivedConflict,
    LocalDirStore,
    MemoryDerivedStore,
)
from picard_framework.analysis.campaign_reducer.ledger import (
    BUDGET_FIELDS,
    BudgetLedger,
    parse_ceilings,
)
from picard_framework.analysis.campaign_reducer.materialize import (
    MaterializeSpec,
    run_materialization,
)
from picard_framework.analysis.campaign_reducer.pinned_reader import MemoryTransport
from picard_framework.analysis.campaign_reducer.rows import (
    ReductionContext,
    SourceSpec,
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


def _ceilings(**over):
    doc = dict.fromkeys(BUDGET_FIELDS, 1_000_000.0)
    doc["safety_factor"] = 1.5
    doc["max_retries"] = 4.0
    doc["max_inflight_jobs"] = 8.0
    doc.update(over)
    return parse_ceilings(doc)


def _ctx(rid="red-test"):
    return ReductionContext(
        reduction_id=rid,
        snapshot_id="snap-test",
        request_sha256="reqsha",
        inventory_sha256="invsha",
        implementation_sha="implsha",
        adapter_registry_sha256="regsha",
        image_digest="imgdigest",
    )


def _src(uri, family="campaign_summary_zip", **kw):
    kw.setdefault("source_id", uri)
    kw.setdefault("campaign_id", "camp1")
    return SourceSpec(uri=uri, family=family, **kw)


def _fused_zip() -> bytes:
    summary_1 = json.dumps({"attack_rate": 0.5, "final_size": 12}).encode()
    summary_2 = json.dumps({"attack_rate": 0.25, "final_size": 7}).encode()
    ts = json.dumps({"epochs": [{"epoch": 0, "infected": 1},
                                {"epoch": 1, "infected": 3}]}).encode()
    return build_zip(
        [
            member("run_1/summary.json", summary_1),
            member("run_1/timeseries.json", ts),
            member("run_2/summary.json", summary_2),
            member("run_2/timeseries.json", ts),
        ]
    )


def _spec(sources, **kw):
    kw.setdefault("shard_size", 2)
    kw.setdefault("utc", "2026-01-01T00:00:00Z")
    return MaterializeSpec(sources=sources, ctx=_ctx(), **kw)


def _rig():
    transport = MemoryTransport()
    store = MemoryDerivedStore()
    ledger = BudgetLedger(_ceilings())
    return transport, store, ledger


def test_materialize_completed_fused_zip_all_run_members():
    transport, store, ledger = _rig()
    transport.put("fused.zip", _fused_zip())
    transport.put("cell.json", json.dumps({"screen_rate": 0.1}).encode())
    spec = _spec(
        [
            _src("fused.zip"),
            _src("cell.json", family="covid_screen_json"),
        ]
    )
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "completed"
    run_rows = [
        json.loads(line)
        for key in store.list(
            "campaign/_derived/reducer/v1/attempts/red-test/shards/"
        )
        if key.endswith("/runs.jsonl")
        for line in store.get(key).splitlines()
    ]
    assert len(run_rows) == 3  # two fused runs + one json run
    uids = {r["run_uid"] for r in run_rows}
    assert len(uids) == 3
    scalar_tables = [
        k for k in store.list()
        if k.endswith("/run_scalars.jsonl")
    ]
    n_scalars = sum(
        len(store.get(k).splitlines()) for k in scalar_tables
    )
    assert n_scalars >= 5  # summary fields + timeseries elements + screen
    commit = json.loads(store.get(result.commit_key))
    assert commit["status"] == "completed"
    assert commit["lineage"]["request_sha256"] == "reqsha"


def test_kill_before_commit_resumes_identical():
    for kill_event in ("partition_written", "checkpoint_written", "pre_commit"):
        transport = MemoryTransport()
        store = MemoryDerivedStore()
        transport.put("fused.zip", _fused_zip())
        spec = _spec([_src("fused.zip")], shard_size=1)

        class Kill(Exception):
            pass

        def killer(event, idx):
            if event == kill_event:
                raise Kill()

        ledger1 = BudgetLedger(_ceilings())
        with pytest.raises(Kill):
            run_materialization(
                spec, transport, store, ledger1, on_shard=killer
            )
        ledger2 = BudgetLedger(_ceilings())
        result = run_materialization(spec, transport, store, ledger2)
        assert result.status == "completed", kill_event
        commit = json.loads(store.get(result.commit_key))
        assert commit["status"] == "completed"
        # byte-identical re-derivation: no conflicting overwrite occurred
        assert store.head(result.commit_key)


def test_put_idempotent_conflict_rejects():
    store = MemoryDerivedStore()
    store.put_if_absent("k", b"abc")
    assert store.put_idempotent("k", b"abc") is False
    with pytest.raises(DerivedConflict):
        store.put_idempotent("k", b"different")
    with pytest.raises(DerivedConflict):
        store.put_if_absent("k", b"abc")


def test_local_dir_store_create_only(tmp_path):
    store = LocalDirStore(tmp_path / "derived")
    store.put_if_absent("a/b.json", b"{}")
    assert store.get("a/b.json") == b"{}"
    with pytest.raises(DerivedConflict):
        store.put_if_absent("a/b.json", b"{ }")


def test_unsupported_family_prevents_completed():
    transport, store, ledger = _rig()
    transport.put("mystery.bin", b"\x00\x01\x02")
    spec = _spec([_src("mystery.bin", family="unknown_legacy")])
    result = run_materialization(spec, transport, store, ledger)
    assert result.status != "completed"
    commit = json.loads(store.get(result.commit_key))
    assert commit["status"] in ("quarantined", "partial")


def test_missing_object_partial_not_complete():
    transport, store, ledger = _rig()
    spec = _spec([_src("gone.zip")])
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "partial"
    gaps = [
        json.loads(line)
        for key in store.list()
        if key.endswith("/data_gaps.jsonl")
        for line in store.get(key).splitlines()
    ]
    assert any(g["reason"] for g in gaps)


def test_incomplete_inventory_prevents_completed():
    transport, store, ledger = _rig()
    transport.put("fused.zip", _fused_zip())
    spec = _spec(
        [_src("fused.zip")], declared_source_count=5
    )
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "partial"
    commit = json.loads(store.get(result.commit_key))
    assert "incomplete_inventory" in commit["coverage"]["disqualifiers"]


def test_oversized_row_prevents_completed():
    transport, store, ledger = _rig()
    big = json.dumps({"blob": "x" * 100_000}).encode()
    transport.put("big.json", big)
    spec = _spec([_src("big.json", family="covid_screen_json")])
    result = run_materialization(spec, transport, store, ledger)
    assert result.status != "completed"
    commit = json.loads(store.get(result.commit_key))
    assert "oversized_row" in commit["coverage"]["disqualifiers"]


def test_corrupt_archive_quarantined():
    transport, store, ledger = _rig()
    transport.put("broken.zip", b"PK not a real archive")
    spec = _spec([_src("broken.zip")])
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "quarantined"


def test_requested_long_tables_emitted():
    transport, store, ledger = _rig()
    transport.put("fused.zip", _fused_zip())
    spec = _spec(
        [_src("fused.zip")],
        requested_tables=("epoch_metrics",),
    )
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "completed"
    epoch_keys = [
        k for k in store.list() if k.endswith("/epoch_metrics.jsonl")
    ]
    assert epoch_keys
    rows = [
        json.loads(line)
        for k in epoch_keys
        for line in store.get(k).splitlines()
    ]
    assert any(r["metric_id"].endswith("infected") for r in rows)


def test_coverage_cells_row_reconciles():
    transport, store, ledger = _rig()
    transport.put("fused.zip", _fused_zip())
    spec = _spec([_src("fused.zip", declared_runs=2)])
    run_materialization(spec, transport, store, ledger)
    cells = [
        json.loads(line)
        for key in store.list()
        if key.endswith("/coverage_cells.jsonl")
        for line in store.get(key).splitlines()
    ]
    assert cells
    cell = cells[0]
    assert cell["declared_runs"] == 2
    assert cell["selected_unique_runs"] == 2
    assert cell["coverage_status"] == "complete"


def test_budget_stop_forces_budget_stopped_status():
    transport, store, _ = _rig()
    transport.put("fused.zip", _fused_zip())
    ledger = BudgetLedger(_ceilings(max_get_requests=2))
    spec = _spec([_src("fused.zip")])
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "budget_stopped"
    commit = json.loads(store.get(result.commit_key))
    assert commit["status"] == "budget_stopped"


def test_distributions_and_weights_base_tables():
    transport, store, ledger = _rig()
    transport.put("fused.zip", _fused_zip())
    spec = _spec([_src("fused.zip")])
    run_materialization(spec, transport, store, ledger)
    dist_keys = [
        k for k in store.list() if k.endswith("/distributions.jsonl")
    ]
    weights_keys = [
        k for k in store.list() if k.endswith("/weights.jsonl")
    ]
    assert dist_keys and weights_keys
    dists = [
        json.loads(line)
        for k in dist_keys
        for line in store.get(k).splitlines()
    ]
    assert any(
        d["metric_id"].endswith("attack_rate") for d in dists
    )
    cdfs = sorted(d["cdf"] for d in dists if d["cdf"] is not None)
    assert cdfs and cdfs[-1] == pytest.approx(1.0)
    weights = [
        json.loads(line)
        for k in weights_keys
        for line in store.get(k).splitlines()
    ]
    assert all(w["weight"] == 1.0 for w in weights)
    assert all(w["weight_set_id"] == "w-equal" for w in weights)
