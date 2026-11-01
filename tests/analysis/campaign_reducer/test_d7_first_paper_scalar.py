"""first_paper_scalar extraction profile + #1116 restart equality.

Acceptance coverage (offline-rigged):
- unequal fused-run metrics never overwrite: per-folder vectors stay
  bound to their own run_uid/doc;
- unique selected executions: one vector row per execution, never a
  duplicate run_uid;
- field/member binding: only summary.json is ranged-read, and vector
  provenance names the member + source key + definition version;
- missing is never zero and denominators are never borrowed;
- restart equality: kill/resume reproduces every derived object
  byte-identically, including rebuilt distributions (issue #1116);
- pre-read scan budgets honored: member allowlist and read ceilings.
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
from picard_framework.analysis.campaign_reducer.pinned_reader import (
    MemoryTransport,
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


def _ceilings(**over):
    doc = dict.fromkeys(BUDGET_FIELDS, 1_000_000.0)
    doc["safety_factor"] = 1.5
    doc["max_retries"] = 4.0
    doc["max_inflight_jobs"] = 8.0
    doc.update(over)
    return parse_ceilings(doc)


def _ctx(rid="red-fp"):
    return ReductionContext(
        reduction_id=rid,
        snapshot_id="snap-test",
        request_sha256="reqsha",
        inventory_sha256="invsha",
        implementation_sha="implsha",
        adapter_registry_sha256="regsha",
        image_digest="imgdigest",
    )


def _src(uri, family="growth_census_zip", **kw):
    kw.setdefault("source_id", uri)
    kw.setdefault("campaign_id", "noro")
    return SourceSpec(uri=uri, family=family, **kw)


def _spec(sources, **kw):
    kw.setdefault("shard_size", 2)
    kw.setdefault("utc", "2026-01-01T00:00:00Z")
    return MaterializeSpec(sources=sources, ctx=_ctx(), **kw)


def _rig():
    return MemoryTransport(), MemoryDerivedStore(), BudgetLedger(
        _ceilings())


def _run_zip(ar_pax=0.5, n=316, crew=134, inf_pax=6, inf_crew=9,
             rep_pax=2, rep_crew=3, extra_members=True, seed=8000,
             omit=()):
    summary = {
        "run_id": f"fl_x_s{seed}",
        "trigger_status": "ALERT",
        "num_epochs": 288,
        "parameters": {"seed": seed, "engine_git_sha": "abc123",
                       "platform_id": "expedition_cruise_450",
                       "tier_id": "off"},
        "summary": {
            "passenger_complement": n,
            "crew_complement": crew,
            "cumulative_ever_infected": inf_pax + inf_crew,
            "cumulative_ever_infected_passenger": inf_pax,
            "cumulative_ever_infected_crew": inf_crew,
            "cumulative_ever_ill": 4,
            "cumulative_ever_ill_passenger": 3,
            "cumulative_ever_ill_crew": 1,
            "cumulative_reported_cases": rep_pax + rep_crew,
            "cumulative_reported_cases_passenger": rep_pax,
            "cumulative_reported_cases_crew": rep_crew,
            "cumulative_reported_noise_cases": 0,
            "infection_attack_rate": (inf_pax + inf_crew) / (n + crew),
            "infection_attack_rate_passenger": inf_pax / n,
            "infection_attack_rate_crew": inf_crew / crew,
            "ever_ill_rate_passenger": 3 / n,
            "ever_ill_rate_crew": 1 / crew,
            "reported_case_rate_passenger": rep_pax / n,
            "reported_case_rate_crew": rep_crew / crew,
            "reported_cases_by_channel": {"syndromic": rep_pax + rep_crew},
            "reported_cases_by_dominant_route": {
                "fomite": rep_pax + rep_crew},
            "infections_by_dominant_route": {
                # acquired infections only (imports are never
                # route-tagged): inf_pax + inf_crew - n_imports
                "fomite": inf_pax + inf_crew - 4},
            "infection_dose_share_by_route": {"fomite": 9.9},
        },
        "census": {"ignited": True, "n_imports": 4, "n_acquired": 11,
                   "acquisitions_by_gen": {"0": 4, "1": 7}},
        "mechanisms": {"common_source_events": 1,
                       "common_source_takers": 2},
        "derived": {"vsp_trigger_epoch": 40, "peak_epoch": 53,
                    "detection_epoch": 42, "confirmation_epoch": 44,
                    "detection_lag": 2, "peak_prevalence": 17,
                    "outbreak_occurred": True,
                    "r_effective_at_peak": 2.1},
        "timeseries": [{"epoch": e} for e in range(288)],
    }
    for path in omit:
        node = summary
        parts = path.split(".")
        for p in parts[:-1]:
            node = node[p]
        del node[parts[-1]]
    members = [member("summary.json", json.dumps(summary).encode())]
    if extra_members:
        members += [
            member("growth_census.json.gz", b"\x1f\x8b" + b"x" * 4000),
            member("rss_samples.json", json.dumps({"voyage": 1}).encode()),
        ]
    return build_zip(members)


def _scan_rows_obj(entries):
    lines = b"".join((json.dumps(e) + "\n").encode() for e in entries)
    return lines


def _scan_entry(key, seed, hull="expedition_cruise_450", posted=False,
                cell="exp 12d scr"):
    return {
        "key": key, "seed": seed, "cell": cell, "hull": hull,
        "posted": posted, "pax_comp": 316, "crew_comp": 134,
        "rep_pax_ar": 0.0, "rep_crew_ar": 0.0075,
        "inf_ar_pax": 0.0032, "inf_crew_ar": 0.0672,
        "ever_ill_pax": 0.0, "rep_pax_n": 0, "rep_crew_n": 1,
        "n_acquired": 6, "n_imports": 4, "ignited": True,
        "vsp_trigger": False, "peak_prevalence": 7,
        "cs_events_summary": 0, "cs_takers_summary": 0,
        "cs_echo": {"mode": "off"}, "cs_sha_echo": "a9f4a517",
        "num_epochs": 288,
        "census": {"n_events": 0, "n_objects": 0,
                   "telemetry": {"objects_provisioned_lot": 0,
                                 "objects_ill_handler": 0,
                                 "objects_ill_diner": 0},
                   "early": [], "burst48": 0.5, "burst24": 0.33,
                   "burst12": 0.33, "burst6": 0.33,
                   "burst48_centre": 53.0, "n_early_obj": 0,
                   "n_early_ev": 0, "n_late_obj": 0, "n_late_ev": 0},
    }


def _vector_rows(store, rid="red-fp"):
    prefix = f"campaign/_derived/reducer/v1/attempts/{rid}/shards/"
    return [
        json.loads(line)
        for key in store.list(prefix)
        if key.endswith("/first_paper_vectors.jsonl")
        for line in store.get(key).splitlines()
    ]


def test_summary_only_member_reads_and_binding():
    transport, store, ledger = _rig()
    transport.put("run_a.zip", _run_zip(seed=8000))
    spec = _spec(
        [_src("run_a.zip", seed=8000, hull_id="expedition_cruise_450")],
        extraction_profile="first_paper_scalar",
    )
    spec.sources[0] = SourceSpec(
        **{**spec.sources[0].__dict__,
           "member_allowlist": ("summary.json",), "emit_scalars": False})
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "completed"
    get_keys = [c[1] for c in transport.calls if c[0] == "get"]
    assert not any("growth_census" in str(k) for k in get_keys)
    # ranged reads stay small: no multi-MB member body was fetched
    assert ledger.spent["max_compressed_bytes_read"] < 1_000_000
    assert "run_scalars" not in result.table_counts
    assert "distributions" not in result.table_counts
    assert "weights" not in result.table_counts
    rows = _vector_rows(store)
    assert len(rows) == 1
    row = rows[0]
    prov = row["provenance"]["cumulative_ever_infected_passenger"]
    assert prov["member"] == "summary.json"
    assert prov["source_key"] == "run_a.zip"
    assert prov["status"] == "exact_emitted"
    assert row["definition_version"] == "first_paper_scalar/1.3.0"
    assert row["definition_sha256"]
    # 1.3.0 observed-window witness fields (same machinery as obsclock)
    assert row["values"]["observed_first_epoch"] == 0
    assert row["values"]["observed_terminal_epoch"] == 287
    assert row["values"]["retained_epoch_rows"] == 288
    assert row["values"]["epoch_index_contiguous"] is True
    assert row["provenance"]["observed_terminal_epoch"]["status"] \
        == "observed"
    assert row["provenance"]["observed_terminal_epoch"]["member"] \
        == "summary.json"
    assert row["values"]["cumulative_ever_infected_passenger"] == 6
    assert row["values"]["trigger_status"] == "ALERT"
    assert row["values"]["census_n_acquired"] == 11
    assert row["values"]["reported_by_channel_consistent"] is True
    # historical conflated flag: route sum (11) vs ever_infected (15)
    # diverges by exactly n_imports (4) — retained as evidence
    assert row["values"]["infections_by_route_consistent"] is False
    assert row["provenance"]["infections_by_route_consistent"][
        "historical_evidence"] is True
    # corrected checks: route sums vs acquired, imports+acquired vs
    # ever-infected, each separately
    assert row["values"][
        "infections_by_route_vs_acquired_consistent"] is True
    assert row["values"][
        "imports_plus_acquired_vs_ever_infected_consistent"] is True
    assert row["values"]["imports_plus_acquired_sum"] == 15
    # no scan source declared: posted is explicit missing, never fabricated
    assert row["values"]["scan_posted"] is None
    assert row["provenance"]["scan_posted"]["status"] == "scan_source_absent"


def test_fused_runs_bind_per_folder_and_stay_unique():
    transport, store, ledger = _rig()
    z1 = json.dumps({"summary": {"passenger_complement": 316},
                     "parameters": {"seed": 8000}}).encode()
    z2 = json.dumps({"summary": {"passenger_complement": 450},
                     "parameters": {"seed": 8001}}).encode()
    fused = build_zip([
        member("run_1/summary.json", z1),
        member("run_1/growth_census.json.gz", b"\x1f\x8ba" * 2000),
        member("run_2/summary.json", z2),
        member("run_2/growth_census.json.gz", b"\x1f\x8bb" * 2000),
    ])
    transport.put("fused.zip", fused)
    spec = _spec(
        [_src("fused.zip", member_allowlist=("summary.json",),
              emit_scalars=False)],
        extraction_profile="first_paper_scalar",
    )
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "completed"
    rows = _vector_rows(store)
    assert len(rows) == 2
    uids = {r["run_uid"] for r in rows}
    assert len(uids) == 2
    vals = sorted(r["values"]["passenger_complement"] for r in rows)
    assert vals == [316, 450]
    # member binding: provenance names each folder's own member
    members = {r["provenance"]["passenger_complement"]["member"]
               for r in rows}
    assert members == {"run_1/summary.json", "run_2/summary.json"}


def test_missing_never_zero_and_no_borrowed_denominators():
    transport, store, ledger = _rig()
    # omit the crew complement + ever_ill block entirely
    blob = _run_zip(
        seed=8000,
        omit=("summary.crew_complement",),
        extra_members=False,
    )
    transport.put("run_a.zip", blob)
    spec = _spec(
        [_src("run_a.zip", member_allowlist=("summary.json",),
              emit_scalars=False)],
        extraction_profile="first_paper_scalar",
    )
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "completed"
    row = _vector_rows(store)[0]
    assert row["values"]["crew_complement"] is None
    assert "crew_complement" in row["missing"]
    assert row["provenance"]["crew_complement"]["status"] == "missing"
    # recomputed crew rates: no borrowed denominator
    assert row["values"]["attack_rate_infection_crew_recomputed"] is None
    st = row["provenance"]["attack_rate_infection_crew_recomputed"]
    assert st["status"] == "invalid_pair_missing_operand"
    # pax pair still recomputes from its own valid pair
    assert row["values"]["attack_rate_infection_pax_recomputed"] == (
        pytest.approx(6 / 316))
    assert row["provenance"]["attack_rate_infection_pax_recomputed"][
        "status"] == "recomputed_pair"


def test_scan_rows_join_posted_and_diagnostics():
    transport, store, ledger = _rig()
    transport.put("run_a.zip", _run_zip(seed=8000))
    transport.put(
        "_scan_rows/arm.jsonl",
        _scan_rows_obj([_scan_entry("run_a.zip", 8000, posted=True)]),
    )
    spec = _spec(
        [
            _src("_scan_rows/arm.jsonl", family="observation_jsonl",
                 source_role="scan_rows"),
            _src("run_a.zip", seed=8000, hull_id="expedition_cruise_450",
                 member_allowlist=("summary.json",), emit_scalars=False),
        ],
        extraction_profile="first_paper_scalar",
    )
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "completed"
    row = _vector_rows(store)[0]
    assert row["values"]["scan_posted"] is True
    assert row["provenance"]["scan_posted"]["source_key"] == (
        "_scan_rows/arm.jsonl")
    assert row["provenance"]["scan_posted"]["status"] == "exact_emitted"
    assert row["values"]["trigger_status"] == "ALERT"
    # the scan file is not an execution: runs table holds only the zip run
    run_rows = [
        json.loads(line)
        for key in store.list()
        if key.endswith("/runs.jsonl")
        for line in store.get(key).splitlines()
    ]
    assert len(run_rows) == 1
    commit = json.loads(store.get(result.commit_key))
    assert commit["coverage"]["selected_unique_runs"] == 1
    assert commit["coverage"]["scan_join_conflicts"] == 0


def test_restart_byte_identical_store():
    """Issue #1116: kill after shard 1, resume -> identical derived bytes."""
    transport = MemoryTransport()
    for i in range(4):
        transport.put(f"r{i}.zip", _run_zip(seed=8000 + i))
    sources = [
        _src(f"r{i}.zip", seed=8000 + i,
             member_allowlist=("summary.json",))
        for i in range(4)
    ]
    spec = _spec(sources, shard_size=1)

    def run_uninterrupted():
        store = MemoryDerivedStore()
        res = run_materialization(
            spec, transport, store, BudgetLedger(_ceilings()))
        return store, res

    store_a, res_a = run_uninterrupted()
    assert res_a.status == "completed"

    store_b = MemoryDerivedStore()

    class Kill(Exception):
        """Sentinel marking the simulated shard-1 kill."""

    def killer(event, idx):
        if event == "checkpoint_written" and idx == 1:
            raise Kill()

    ledger = BudgetLedger(_ceilings())
    with pytest.raises(Kill):
        run_materialization(spec, transport, store_b, ledger, on_shard=killer)
    res_b = run_materialization(
        spec, transport, store_b, BudgetLedger(_ceilings()))
    assert res_b.status == "completed"
    keys_a = sorted(store_a.list())
    keys_b = sorted(store_b.list())
    assert keys_a == keys_b
    for key in keys_a:
        assert store_a.get(key) == store_b.get(key), key


def test_restart_byte_identical_store_with_scalars():
    """Same restart equality in full-scalar mode (distributions rebuilt)."""
    transport = MemoryTransport()
    for i in range(4):
        transport.put(f"r{i}.zip", _run_zip(seed=8000 + i))
    sources = [_src(f"r{i}.zip", seed=8000 + i) for i in range(4)]
    spec = _spec(sources, shard_size=1)

    store_a = MemoryDerivedStore()
    res_a = run_materialization(
        spec, transport, store_a, BudgetLedger(_ceilings()))
    assert res_a.status in ("completed", "partial")

    store_b = MemoryDerivedStore()

    class Kill(Exception):
        """Sentinel marking the simulated shard-1 kill."""

    def killer(event, idx):
        if event == "checkpoint_written" and idx == 1:
            raise Kill()

    ledger = BudgetLedger(_ceilings())
    with pytest.raises(Kill):
        run_materialization(spec, transport, store_b, ledger, on_shard=killer)
    res_b = run_materialization(
        spec, transport, store_b, BudgetLedger(_ceilings()))
    assert res_b.status == res_a.status
    keys_a = sorted(store_a.list())
    assert keys_a == sorted(store_b.list())
    for key in keys_a:
        assert store_a.get(key) == store_b.get(key), key


def test_pre_read_scan_budgets_honored():
    """Tight GET ceiling stops the materialize phase, checkpointed."""
    transport, store, _ledger = _rig()
    for i in range(3):
        transport.put(f"r{i}.zip", _run_zip(seed=8000 + i))
    sources = [_src(f"r{i}.zip", seed=8000 + i) for i in range(3)]
    spec = _spec(sources, shard_size=1)
    ledger = BudgetLedger(_ceilings(max_get_requests=2.0))
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "budget_stopped"
    commit = json.loads(store.get(result.commit_key))
    assert commit["status"] == "budget_stopped"
