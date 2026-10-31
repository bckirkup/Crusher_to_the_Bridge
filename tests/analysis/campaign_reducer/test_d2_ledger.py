"""D2 ledger tests — reservation/budget ceilings, retries, resume, concurrency.

Every ceiling is charged: bytes, objects, members, rows, wall-clock,
concurrency and retries — each probed at limit-1, limit and limit+1.
``None`` is never unlimited: unset ceilings fail admission.
"""
from __future__ import annotations

import socket
import subprocess
import sys

import pytest

from picard_framework.analysis.campaign_reducer.ledger import (
    BUDGET_FIELDS,
    BudgetBlocked,
    BudgetExceeded,
    BudgetLedger,
    UnknownPrice,
    parse_ceilings,
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
    doc = dict.fromkeys(BUDGET_FIELDS, 1000.0)
    doc["safety_factor"] = 1.5
    doc["max_retries"] = 3.0
    doc["max_inflight_jobs"] = 2.0
    doc["max_jobs"] = 4.0
    doc.update(over)
    return doc


def test_parse_ceilings_rejects_missing_and_none():
    with pytest.raises(BudgetBlocked):
        parse_ceilings(None)
    doc = _ceilings()
    del doc["max_wall_seconds"]
    with pytest.raises(BudgetBlocked):
        parse_ceilings(doc)
    doc = _ceilings(max_output_bytes=None)
    with pytest.raises(BudgetBlocked):
        parse_ceilings(doc)


def test_parse_ceilings_rejects_nonpositive_and_nonfinite():
    for bad in (0, -5, float("inf"), float("nan"), "x", True):
        ceilings = _ceilings(max_wall_seconds=bad)
        with pytest.raises(BudgetBlocked):
            parse_ceilings(ceilings)
    legal = _ceilings(max_retries=0)  # zero retries is legal
    parse_ceilings(legal)
    negative = _ceilings(max_retries=-1)
    with pytest.raises(BudgetBlocked):
        parse_ceilings(negative)


def test_parse_ceilings_ok():
    ceilings = parse_ceilings(_ceilings())
    assert ceilings["max_output_bytes"] == 1000.0


@pytest.mark.parametrize(
    "field,amount",
    [
        ("max_api_calls_total", 10),
        ("max_head_requests", 10),
        ("max_get_requests", 10),
        ("max_list_pages", 10),
        ("max_source_objects", 10),
        ("max_source_object_bytes_referenced", 100),
        ("max_compressed_bytes_read", 100),
        ("max_uncompressed_bytes", 100),
        ("max_output_bytes", 100),
        ("max_spool_bytes", 100),
        ("max_queue_wait_seconds", 10),
        ("max_vcpu_seconds", 10),
        ("max_memory_mib_seconds", 10),
        ("max_cost_usd", 10),
    ],
)
def test_cumulative_charge_limit_boundary(field, amount):
    ledger = BudgetLedger(parse_ceilings(_ceilings(**{field: 100})))
    ledger.charge(field, 100 - amount)  # limit-1 ok
    ledger.charge(field, amount)  # limit ok
    with pytest.raises(BudgetExceeded):
        ledger.charge(field, 1)  # limit+1 fails


def test_per_event_cap_member_bytes():
    ledger = BudgetLedger(parse_ceilings(_ceilings(max_member_bytes=100)))
    ledger.cap("max_member_bytes", 99)
    ledger.cap("max_member_bytes", 100)
    with pytest.raises(BudgetExceeded):
        ledger.cap("max_member_bytes", 101)


def test_concurrency_slots_shared_and_cumulative_jobs():
    ledger = BudgetLedger(
        parse_ceilings(_ceilings(max_inflight_jobs=2, max_jobs=3))
    )
    ledger.acquire_job()
    ledger.acquire_job()  # at limit
    with pytest.raises(BudgetExceeded):
        ledger.acquire_job()  # limit+1 inflight
    ledger.release_job()
    ledger.acquire_job()  # third job ok
    with pytest.raises(BudgetExceeded):
        ledger.acquire_job()  # fourth cumulative job exceeds max_jobs


def test_retries_charge_shared_ledger():
    ledger = BudgetLedger(
        parse_ceilings(_ceilings(max_retries=2, max_api_calls_total=10))
    )
    ledger.charge_retry()
    ledger.charge_retry()  # at limit
    with pytest.raises(BudgetExceeded):
        ledger.charge_retry()  # limit+1
    assert ledger.spent["max_api_calls_total"] == 2


def test_wall_clock_charges_cumulatively():
    ledger = BudgetLedger(parse_ceilings(_ceilings(max_wall_seconds=100)))
    ledger.charge_wall(99)
    ledger.charge_wall(1)
    with pytest.raises(BudgetExceeded):
        ledger.charge_wall(1)


def test_shard_reservations_disjoint_and_atomic():
    ledger = BudgetLedger(parse_ceilings(_ceilings(max_output_bytes=100)))
    a = ledger.shard({"max_output_bytes": 60})
    with pytest.raises(BudgetExceeded):
        ledger.shard({"max_output_bytes": 50})  # 60+50 > 100
    b = ledger.shard({"max_output_bytes": 40})  # exactly fills
    a.charge("max_output_bytes", 60)
    b.charge("max_output_bytes", 40)
    with pytest.raises(BudgetExceeded):
        ledger.charge("max_output_bytes", 1)
    a.commit()
    b.commit()
    assert ledger.spent["max_output_bytes"] == 100


def test_reservation_release_frees_capacity():
    ledger = BudgetLedger(parse_ceilings(_ceilings(max_output_bytes=100)))
    res = ledger.reserve({"max_output_bytes": 80})
    ledger.reserve({"max_output_bytes": 20})
    res.release()
    ledger.reserve({"max_output_bytes": 80})  # freed again


def test_checkpoint_reserves_not_spendable_by_work():
    ledger = BudgetLedger(
        parse_ceilings(_ceilings(checkpoint_reserve_bytes=50))
    )
    with pytest.raises(BudgetBlocked):
        ledger.charge("checkpoint_reserve_bytes", 1)
    ledger.charge_checkpoint("checkpoint_reserve_bytes", 50)
    with pytest.raises(BudgetExceeded):
        ledger.charge_checkpoint("checkpoint_reserve_bytes", 1)


def test_unspendable_fields_rejected():
    ledger = BudgetLedger(parse_ceilings(_ceilings()))
    with pytest.raises(BudgetBlocked):
        ledger.charge("safety_factor", 1)
    with pytest.raises(BudgetBlocked):
        ledger.charge("no_such_ceiling", 1)  # undeclared != unlimited


def test_cost_model_unknown_price_blocks():
    ledger = BudgetLedger(
        parse_ceilings(_ceilings()),
        prices={"scan_byte": 0.001},
        require_prices=True,
    )
    ledger.charge_cost("scan_byte", 100)
    assert ledger.spent["max_cost_usd"] == pytest.approx(0.1)
    with pytest.raises(UnknownPrice):
        ledger.charge_cost("unknown_op", 1)


def test_resume_carries_spent_not_reset():
    ceilings = parse_ceilings(_ceilings(max_output_bytes=100))
    ledger = BudgetLedger(ceilings)
    ledger.charge("max_output_bytes", 90)
    snap = ledger.snapshot()
    resumed = BudgetLedger.resume(ceilings, snap)
    resumed.charge("max_output_bytes", 10)
    with pytest.raises(BudgetExceeded):
        resumed.charge("max_output_bytes", 1)
    assert resumed.jobs == ledger.jobs
