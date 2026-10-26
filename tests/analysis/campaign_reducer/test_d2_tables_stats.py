"""D2 coverage tests — stat emitters, metric bindings, parquet decode.

Targets the uncovered branches in ``query_engine`` statistic paths and
``long_tables`` secondary emitters, all offline.
"""
from __future__ import annotations

import io
import socket
import subprocess
import sys
from types import SimpleNamespace

import pytest

from picard_framework.analysis.campaign_reducer.long_tables import (
    _metric_rows,
    decode_parquet_object,
    emit_long_tables,
)
from picard_framework.analysis.campaign_reducer.payloads import DecodedDoc
from picard_framework.analysis.campaign_reducer.query_engine import (
    QueryError,
    _riskset_rows,
    _stat_rows,
)
from picard_framework.analysis.campaign_reducer.rows import (
    ReductionContext,
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


CTX = ReductionContext(
    reduction_id="red-t",
    snapshot_id="snap-t",
    request_sha256="",
    inventory_sha256=None,
    implementation_sha="",
    adapter_registry_sha256="",
    image_digest="",
    phase="materialize",
    admission_id=None,
    parent_reduction_id=None,
    discovery_root="",
    listing_start_utc="",
    listing_end_utc="",
    fingerprint="",
)


def _rows(vals):
    return [{"value": v, "numerator": v, "denominator": 10.0,
             "dim": "a"} for v in vals]


@pytest.mark.parametrize("stat", [
    "cross_tab", "joint_support", "exact_ecdf", "mean",
    "pooled_rate", "quantile", "covariance",
])
def test_stat_rows_grouped_variants(stat):
    query = {"statistic": stat, "group_by": ["dim"]}
    rows = _stat_rows(query, _rows([1.0, 2.0, 3.0]))
    assert rows
    assert all(r["group_json"] == {"dim": "a"} for r in rows)


def test_stat_rows_exact_and_unsupported():
    raw = _rows([1.0])
    assert _stat_rows({"statistic": "exact_rows"}, raw) == raw
    with pytest.raises(QueryError):
        _stat_rows({"statistic": "bogus"}, raw)


def test_riskset_rows_km():
    members = [
        {"endpoint_id": "death", "censor_type": "exact",
         "upper_hours": 5.0},
        {"endpoint_id": "death", "censor_type": "exact",
         "upper_hours": 8.0},
        {"endpoint_id": "death", "censor_type": "right",
         "exit_hours": 10.0},
        {"endpoint_id": "death", "censor_type": "interval",
         "lower_hours": 3.0, "upper_hours": 6.0},
    ]
    rows = _riskset_rows(
        {"statistic": "survival"}, members, ["endpoint_id"], "survival"
    )
    times = {(r["endpoint_id"], r["time_hours"]): r for r in rows}
    first = times[("death", 5.0)]
    assert first["n_event"] == 1
    assert first["n_censored_other"] == 1
    last = times[("death", 8.0)]
    assert last["survival"] == pytest.approx(1 / 3)


def _adapter_result(scalars, docs):
    return SimpleNamespace(scalars=scalars, docs=docs, runs=[])


def test_metric_rows_binding(tmp_path):
    spec = SimpleNamespace()
    scalars = [
        SimpleNamespace(native_path="/infected", value=4.0,
                        run_uid="run-1"),
        SimpleNamespace(native_path="/population", value=8.0,
                        run_uid="run-1"),
    ]
    result = _adapter_result(scalars, [])
    bindings = {
        "m.attack": {
            "numerator": "/infected",
            "denominator": "/population",
            "unit": "1",
            "endpoint_domain": "final_size",
        }
    }
    rows = _metric_rows(result, spec, CTX, bindings)
    assert len(rows) == 1
    assert rows[0]["value"] == pytest.approx(0.5)
    assert rows[0]["value_status"] == "exact_derived"

    scalars[1].value = 0.0
    assert _metric_rows(result, spec, CTX, bindings) == []


def test_decode_parquet_object(tmp_path):
    pq = pytest.importorskip("pyarrow.parquet")
    pa = pytest.importorskip("pyarrow")
    table = pa.table({"x": [1, 2], "y": ["a", "b"]})
    buf = io.BytesIO()
    pq.write_table(table, buf)

    class _Obj:
        pin = SimpleNamespace(version_id=None, etag=None)

        def read_whole(self):
            return buf.getvalue()

    class _Ref:
        campaign_id = "camp-p"
        uri = "side.parquet"
        seed = 1
        original_run_id = "orig-p"
        hull_id = "h"
        cell_id = "c"
        engine_sha = ""
        image_digest = ""

        def run_id(self):
            return "run-p"

        def source_id(self):
            return "src"

        def member_path(self):
            return "side.parquet"

        def etag(self):
            return None

    result = _adapter_result([], [])
    decode_parquet_object(_Obj(), _Ref(), result)
    assert len(result.scalars) >= 2
    assert len(result.docs) == 2
    assert result.runs


def test_emit_long_tables_events_and_tte():
    doc = {
        "events": [
            {"subject_id": "s1", "event_hours": 2.0,
             "censor_type": "exact", "endpoint_id": "ep",
             "actor": "a1", "recipient": "a2",
             "zone_id": "z1"},
            {"subject_id": "s2", "exit_hours": 4.0,
             "censor_type": "right"},
        ],
        "epochs": [
            {"epoch": 0, "infected": 3, "recovered": 1},
        ],
        "observations": [{"obs_id": "o1", "value": 1.0}],
        "agents": [{"agent_id": "a1"}],
        "mechanism_objects": [{"object_id": "m1"}],
        "population_intervals": [{"interval_id": "p1"}],
    }
    ddoc = DecodedDoc(
        run_uid="run-1", asset_id="mem-x",
        member_path="doc.json", doc=doc,
    )
    result = _adapter_result([], [ddoc])
    spec = SimpleNamespace(family="campaign_summary_zip")
    tables = emit_long_tables(
        result, spec, CTX,
        requested=(
            "events", "times_to_event", "epoch_metrics", "observations",
            "agents", "mechanism_objects", "population_intervals",
            "participants",
        ),
        metric_bindings={},
    )
    assert tables.get("events")
    assert tables.get("times_to_event")
    tte = tables["times_to_event"][0]
    assert tte["censor_type"] == "exact"
    assert tte["endpoint_id"] == "event"
    assert len(tables["epoch_metrics"]) >= 2
    assert tables["epoch_metrics"][0]["metric_id"].startswith(
        "campaign_summary_zip.epochs."
    )
    for name in ("observations", "agents", "mechanism_objects",
                 "population_intervals"):
        assert tables.get(name), name


def test_tte_unknown_censor_normalized():
    ddoc = DecodedDoc(
        run_uid="run-1", asset_id="mem-x",
        member_path="doc.json",
        doc={"times_to_event": [
            {"subject_id": "s", "censor_type": "weird"},
        ]},
    )
    result = _adapter_result([], [ddoc])
    spec = SimpleNamespace(family="f")
    tables = emit_long_tables(
        result, spec, CTX,
        requested=("times_to_event",),
        metric_bindings={},
    )
    assert tables["times_to_event"][0]["censor_type"] == "unknown"
