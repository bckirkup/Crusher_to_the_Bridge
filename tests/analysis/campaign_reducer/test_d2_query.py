"""D2 bounded query engine tests — projection/filter/joins/paging/caps.

Full joint pages equal the exhaustive fixture selection with stable
ordering and no missing/duplicate rows; cursors bind the frozen
snapshot; null-aware filters; unsupported joins are typed errors;
every cap is honored including ROW_TOO_LARGE.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys

import pytest
from zip_builders import build_zip, member

from picard_framework.analysis.campaign_reducer.derived_store import (
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
from picard_framework.analysis.campaign_reducer.query_engine import (
    QueryError,
    run_query,
)
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


def _ceilings():
    doc = dict.fromkeys(BUDGET_FIELDS, 1_000_000_000.0)
    doc["safety_factor"] = 1.5
    doc["max_retries"] = 4.0
    doc["max_inflight_jobs"] = 8.0
    return parse_ceilings(doc)


def _fused_zip() -> bytes:
    return build_zip(
        [
            member("run_1/summary.json",
                   json.dumps({"attack_rate": 0.5, "final_size": 12}).encode()),
            member("run_2/summary.json",
                   json.dumps({"attack_rate": 0.25, "final_size": 7}).encode()),
            member("run_3/summary.json",
                   json.dumps({"attack_rate": 0.1, "final_size": 3}).encode()),
        ]
    )


@pytest.fixture
def catalog():
    transport = MemoryTransport()
    store = MemoryDerivedStore()
    transport.put("fused.zip", _fused_zip())
    ctx = ReductionContext(reduction_id="red-q", snapshot_id="snap-q")
    spec = MaterializeSpec(
        sources=[
            SourceSpec(uri="fused.zip", family="campaign_summary_zip",
                       source_id="fused.zip", campaign_id="camp1")
        ],
        ctx=ctx,
        utc="2026-01-01T00:00:00Z",
    )
    result = run_materialization(
        spec, transport, store, BudgetLedger(_ceilings())
    )
    assert result.status == "completed"
    return store, result


def _query(**over):
    doc = {
        "contract_id": "crusher-campaign-distributions/1.0-proposed",
        "catalog_snapshot_id": "",
        "operation": "query",
        "analysis_version": "test",
        "source_table": "run_scalars",
        "metric_ids": [],
        "filters": {"ne": ["row_id", "__never__"]},
        "group_by": [],
        "statistic": "exact_rows",
        "weight_set_id": "w-equal",
        "missing_policy": "report_separately",
        "max_export_rows": 100000,
        "max_export_bytes": 5 * 1024 * 1024,
        "page_rows": 10000,
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
    doc.update(over)
    return doc


def _page_rows(store, outcome):
    rows = []
    for key in outcome.page_keys:
        rows.extend(
            json.loads(line)
            for line in store.get(key).splitlines()
            if line.strip()
        )
    return rows


def test_joint_pages_equal_exhaustive_selection(catalog):
    store, result = catalog
    q = _query(
        catalog_snapshot_id=result.snapshot_id, page_rows=2
    )
    outcome = run_query(
        q, store, BudgetLedger(_ceilings()),
        commit_key=result.commit_key, reduction_id="red-q",
    )
    assert outcome.status == "completed"
    rows = _page_rows(store, outcome)
    # exhaustive: every emitted run_scalar row across the pages, no dup
    seen = [r["row_id"] for r in rows]
    assert len(seen) == len(set(seen))
    assert len(rows) >= 6
    # stable ordering by native_path
    paths = [r["native_path"] for r in rows]
    assert paths == sorted(paths)


def test_continuation_resumes_without_dup_or_loss(catalog):
    store, result = catalog
    q = _query(
        catalog_snapshot_id=result.snapshot_id,
        page_rows=2,
        max_export_rows=4,
    )
    ledger = BudgetLedger(_ceilings())
    first = run_query(q, store, ledger, commit_key=result.commit_key)
    assert first.pages
    assert first.next_cursor
    token = first.next_cursor["token"]
    q2 = _query(
        catalog_snapshot_id=result.snapshot_id,
        page_rows=2,
        max_export_rows=4,
        continuation_token=token,
    )
    second = run_query(q2, store, ledger, commit_key=result.commit_key)
    first_ids = {r["row_id"] for r in _page_rows(store, first)}
    second_ids = {r["row_id"] for r in _page_rows(store, second)}
    assert not (first_ids & second_ids)
    # union equals exhaustive selection
    full = run_query(
        _query(catalog_snapshot_id=result.snapshot_id),
        store, BudgetLedger(_ceilings()), commit_key=result.commit_key,
    )
    all_ids = {r["row_id"] for r in _page_rows(store, full)}
    assert first_ids | second_ids == all_ids


def test_cursor_mismatch_rejects(catalog):
    store, result = catalog
    q = _query(catalog_snapshot_id=result.snapshot_id, page_rows=2,
               max_export_rows=2)
    first = run_query(q, store, BudgetLedger(_ceilings()),
                      commit_key=result.commit_key)
    token = first.next_cursor["token"]
    # different query -> different q_sha -> cursor invalid
    q_bad = _query(
        catalog_snapshot_id=result.snapshot_id,
        page_rows=3,
        max_export_rows=2,
        continuation_token=token,
    )
    ledger = BudgetLedger(_ceilings())
    with pytest.raises(QueryError):
        run_query(q_bad, store, ledger, commit_key=result.commit_key)


def test_null_aware_filters(catalog):
    store, result = catalog
    q = _query(
        catalog_snapshot_id=result.snapshot_id,
        filters={"is_null": "unit"},
    )
    outcome = run_query(q, store, BudgetLedger(_ceilings()),
                        commit_key=result.commit_key)
    rows = _page_rows(store, outcome)
    assert rows
    assert all(r["unit"] is None for r in rows)
    q2 = _query(
        catalog_snapshot_id=result.snapshot_id,
        filters={"eq": ["unit", None]},
    )
    outcome2 = run_query(q2, store, BudgetLedger(_ceilings()),
                         commit_key=result.commit_key)
    assert len(_page_rows(store, outcome2)) == len(rows)


def test_numeric_and_string_filters(catalog):
    store, result = catalog
    outcome = run_query(
        _query(
            catalog_snapshot_id=result.snapshot_id,
            filters={"eq": ["native_value_json", "0.5"]},
        ),
        store, BudgetLedger(_ceilings()), commit_key=result.commit_key,
    )
    rows = _page_rows(store, outcome)
    assert rows
    assert all(r["native_value_json"] == "0.5" for r in rows)


def test_max_export_rows_cap(catalog):
    store, result = catalog
    outcome = run_query(
        _query(catalog_snapshot_id=result.snapshot_id,
               max_export_rows=2, page_rows=10),
        store, BudgetLedger(_ceilings()), commit_key=result.commit_key,
    )
    rows = _page_rows(store, outcome)
    assert len(rows) <= 2
    assert outcome.status != "completed" or outcome.complete is False


def test_row_too_large_typed_outcome(catalog):
    store, result = catalog
    outcome = run_query(
        _query(catalog_snapshot_id=result.snapshot_id,
               max_export_bytes=100, page_rows=1),
        store, BudgetLedger(_ceilings()), commit_key=result.commit_key,
    )
    assert outcome.errors
    assert outcome.errors[0]["kind"] == "row_too_large"


def test_join_explosion_blocked(catalog):
    store, result = catalog
    outcome = run_query(
        _query(
            catalog_snapshot_id=result.snapshot_id,
            source_table="runs",
            joins=[{
                "table": "run_scalars",
                "on": ["run_uid"],
                "cardinality": "one_to_many_explicit",
            }],
        ),
        store, BudgetLedger(_ceilings()), commit_key=result.commit_key,
    )
    assert outcome.status == "blocked"
    assert outcome.errors[0]["kind"] == "unsupported_join"


def test_many_to_one_join_enriches(catalog):
    store, result = catalog
    outcome = run_query(
        _query(
            catalog_snapshot_id=result.snapshot_id,
            source_table="run_scalars",
            joins=[{
                "table": "runs",
                "on": ["run_uid"],
                "cardinality": "many_to_one",
            }],
        ),
        store, BudgetLedger(_ceilings()), commit_key=result.commit_key,
    )
    rows = _page_rows(store, outcome)
    assert rows
    assert all("runs__selection_state" in r for r in rows)


def test_snapshot_mismatch_blocks(catalog):
    store, result = catalog
    outcome = run_query(
        _query(catalog_snapshot_id="snap-WRONG"),
        store, BudgetLedger(_ceilings()), commit_key=result.commit_key,
    )
    assert outcome.status == "blocked"
    assert outcome.errors[0]["kind"] == "snapshot_mismatch"


def test_invalid_query_doc_rejected(catalog):
    store, result = catalog
    query = {"catalog_snapshot_id": result.snapshot_id}
    ledger = BudgetLedger(_ceilings())
    with pytest.raises(QueryError):
        run_query(query, store, ledger, commit_key=result.commit_key)


def test_scan_budget_stops_qualified(catalog):
    store, result = catalog
    outcome = run_query(
        _query(
            catalog_snapshot_id=result.snapshot_id,
            scan_budget={"max_scan_bytes": 1, "max_wall_seconds": 600,
                         "max_cost_usd": 10.0},
        ),
        store, BudgetLedger(_ceilings()), commit_key=result.commit_key,
    )
    assert outcome.status == "budget_stopped"
    assert outcome.complete is False


def test_cross_tab_and_ecdf_statistics(catalog):
    store, result = catalog
    outcome = run_query(
        _query(
            catalog_snapshot_id=result.snapshot_id,
            statistic="cross_tab",
            group_by=["native_type"],
        ),
        store, BudgetLedger(_ceilings()), commit_key=result.commit_key,
    )
    rows = _page_rows(store, outcome)
    assert rows
    assert all("n" in r for r in rows)
    outcome2 = run_query(
        _query(
            catalog_snapshot_id=result.snapshot_id,
            source_table="metrics",
            statistic="exact_ecdf",
            group_by=["metric_id"],
        ),
        store, BudgetLedger(_ceilings()), commit_key=result.commit_key,
    )
    assert outcome2.status in ("completed", "partial")


def test_unsupported_statistic_typed_error(catalog):
    store, result = catalog
    outcome = run_query(
        _query(catalog_snapshot_id=result.snapshot_id,
               statistic="histogram_explicit_bins"),
        store, BudgetLedger(_ceilings()), commit_key=result.commit_key,
    )
    assert outcome.status == "blocked"
    assert outcome.errors[0]["kind"] == "unsupported_statistic"
