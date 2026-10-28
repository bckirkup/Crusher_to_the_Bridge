"""D6 schema-pilot + quote tests — offline-rigged only.

Covers: quote-from-receipt math including dated-labeling and the
absent-price stop; stratified specimen selection over a rigged
frozen_inventory including the missing-witness case; submit argv/phase
validation; the mega sibling ``_scan_rows`` join by embedded source key
(P14/P15); and reuse-audit classification (complete summary / partial
precision / census missingness / unknown provenance / no rows).
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import rel
from d4_fixtures import BUCKET, execution_request

from picard_framework.analysis.campaign_reducer import (
    cli,
    contracts,
    pilot,
    s3_store,
    submit,
)


@pytest.fixture(autouse=True)
def _forbid_external(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*a, **k):
        raise AssertionError("network/subprocess forbidden in offline tests")

    monkeypatch.setattr(socket, "create_connection", _raise)
    monkeypatch.setattr(socket.socket, "connect", _raise)
    monkeypatch.setattr(subprocess, "run", _raise)
    monkeypatch.setattr(subprocess, "Popen", _raise)
    monkeypatch.setitem(sys.modules, "boto3", None)


def _write(path: Path, doc) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc))
    return path


_PRICES = {
    "s3_list_per_1000_requests_usd": 0.005,
    "s3_head_per_1000_requests_usd": 0.0004,
    "s3_get_per_1000_requests_usd": 0.0004,
    "s3_put_per_1000_requests_usd": 0.005,
    "batch_vcpu_hour_usd": 0.04,
    "batch_memory_gib_hour_usd": 0.0044,
    "s3_storage_gb_month_usd": 0.023,
    "s3_data_transfer_out_gb_usd": 0.09,
}


def _evidence(kind: str = "pilot_receipt", **over) -> dict:
    doc = {
        "schema": "crusher-reducer-pilot-evidence/v1",
        "kind": kind,
        "inventory_sha256": "a" * 64,
        "utc": "2026-10-27T00:00:00Z",
        "price_snapshot": {
            "id": "price-snap-1",
            "as_of_utc": "2026-10-27T00:00:00Z",
            "unit_prices_json": dict(_PRICES),
        },
        "scope": {
            "counts_basis": "fresh_inventory",
            "as_of": "2026-10-20T00:00:00Z",
            "families": [
                {"family": "campaign_summary_zip",
                 "objects": 1000, "bytes": 10**9},
                {"family": "growth_census_zip",
                 "objects": 4, "bytes": 10**6},
                {"family": "wastewater_campaign_zip",
                 "objects": 10, "bytes": 10**6},
            ],
        },
        "per_class": [
            {"class": "summary_archive",
             "family": "campaign_summary_zip",
             "objects": 2, "compressed_bytes": 1000,
             "uncompressed_bytes": 2000, "member_bytes": 2000,
             "api_list": 2, "api_head": 2, "api_get": 4, "api_put": 1,
             "wall_seconds": 10, "vcpu_seconds": 20,
             "memory_mib_seconds": 10240, "peak_memory_mib": 1024,
             "spool_bytes": 4000, "output_bytes": 100, "retries": 1},
            {"class": "census", "family": "growth_census_zip",
             "objects": 1, "compressed_bytes": 2000,
             "uncompressed_bytes": 4000, "member_bytes": 4000,
             "api_list": 1, "api_head": 1, "api_get": 2, "api_put": 1,
             "wall_seconds": 20, "vcpu_seconds": 40,
             "memory_mib_seconds": 20480, "peak_memory_mib": 2048,
             "spool_bytes": 8000, "output_bytes": 200, "retries": 0},
        ],
    }
    doc.update(over)
    return doc


def _quote_req(**over) -> dict:
    req = execution_request(reduction_id="red-d6q", phase="pilot")
    req["budgets"]["max_cost_usd"] = 10**6
    req.update(over)
    return req


def _invoke_quote(scratch: Path, request: dict, evidence: dict) -> int:
    req = _write(scratch / "q_req.json", request)
    ev = _write(scratch / "ev.json", evidence)
    return cli.main([
        "quote", "--request", rel(req), "--out", rel(scratch / "q"),
        "--evidence", rel(ev)])


def test_quote_from_pilot_receipt_math(scratch: Path) -> None:
    rc = _invoke_quote(scratch, _quote_req(), _evidence())
    # unmeasured scope family -> explicit partial-coverage exit
    assert rc == contracts.EXIT_PARTIAL_COVERAGE
    pq = json.loads((scratch / "q" / "phase_quote.json").read_text())
    m = next(p for p in pq["phase_rows"] if p["phase"] == "materialize")
    # summary_archive units x500 scope factor, census x4 scope factor
    assert m["objects"] == pytest.approx(2 * 500 + 1 * 4)
    assert m["compressed_bytes_read"] == pytest.approx(
        1000 * 500 + 2000 * 4)
    get = m["cost"]["components"]["s3_get"]
    assert get["usd"] == pytest.approx(
        get["quantity"] * get["unit_price"])
    assert get["quantity"] == pytest.approx(
        (4 * 500 + 2 * 4) / 1000)
    unc = json.loads((scratch / "q" / "uncertainty.json").read_text())
    rows = {r["field"]: r for r in unc["bands"]}
    # unmeasured family is an explicit row, not folded into totals
    assert rows["wastewater_campaign_zip"]["basis"] == \
        "unmeasured_family"
    assert (scratch / "q" / "blocking_inputs.json").exists()


def test_quote_dated_counts_labeled(scratch: Path) -> None:
    ev = _evidence()
    ev["scope"]["counts_basis"] = "dated_register_oct19"
    assert _invoke_quote(scratch, _quote_req(), ev) == \
        contracts.EXIT_PARTIAL_COVERAGE
    unc = json.loads((scratch / "q" / "uncertainty.json").read_text())
    row = next(
        r for r in unc["bands"]
        if r["field"] == "campaign_summary_zip")
    assert row["counts_are_dated_not_current"] is True
    assert row["counts_basis"] == "dated_register_oct19"


def test_quote_absent_price_stops(scratch: Path) -> None:
    ev = _evidence()
    ev["price_snapshot"]["unit_prices_json"].pop(
        "batch_vcpu_hour_usd")
    rc = _invoke_quote(scratch, _quote_req(), ev)
    assert rc == contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED
    blocking = json.loads(
        (scratch / "q" / "blocking_inputs.json").read_text())
    assert any(b["kind"] == "price_absent"
               for b in blocking["blocking"])
    status = json.loads((scratch / "q" / "status.json").read_text())
    assert status["status"] != "complete"


def test_quote_no_prices_at_all_blocks(scratch: Path) -> None:
    ev = _evidence()
    del ev["price_snapshot"]
    req = _quote_req()
    del req["quote"]
    assert _invoke_quote(scratch, req, ev) == contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED


def test_quote_bad_evidence_is_contract_failure(scratch: Path) -> None:
    req = _write(scratch / "q_req.json", _quote_req())
    ev = _write(scratch / "ev.json", {"kind": "nonsense"})
    rc = cli.main([
        "quote", "--request", rel(req), "--out",
        rel(scratch / "q"), "--evidence", rel(ev)])
    assert rc == contracts.EXIT_INVALID_CONTRACT


# ---- specimen selection --------------------------------------------------


def _family(prefix: str, family: str, record: str,
            *, group: str | None = None, fresh: str = "present") -> dict:
    return {"prefix": prefix, "schema_family": family,
            "record_id": record, "record_kind": "campaign_archive",
            "program_group": group or f"g-{record}",
            "fresh_observation": fresh}


def _frozen() -> dict:
    return {
        "request_id": "req-d5",
        "source_bucket": BUCKET,
        "observation_window": {"as_of": "2026-10-20T00:00:00Z"},
        "families": [
            _family("campaign/noro_provisioned_source_01/",
                    "unknown", "nps01",
                    group="norovirus_provisioned_source_PS01"),
            _family("campaign/noro_provisioned_source_01_mega/",
                    "unknown", "nps01mega",
                    group="norovirus_provisioned_source_PS01"),
            _family("campaign/sum1/", "campaign_summary_zip", "sum1"),
            _family("campaign/sum2/", "campaign_summary_zip", "sum2"),
            _family("campaign/cen1/", "growth_census_zip", "cen1"),
            _family("campaign/cen2/", "growth_census_zip", "cen2"),
            _family("campaign/obs1/", "observation_jsonl", "obs1"),
            _family("campaign/leg1/", "unknown_legacy", "leg1"),
            _family("campaign/cov1/", "covid_screen_json", "cov1"),
            _family("campaign/flu1/", "flu_cell_json", "flu1"),
            _family("campaign/ww1/", "wastewater_campaign_zip",
                    "ww1", fresh="absent"),
            _family("campaign/missing/", "perturbation_json",
                    "missing1", fresh="blocked"),
        ],
    }


def _register() -> list[dict]:
    return [
        {"record_id": "nps01",
         "prefix": "campaign/noro_provisioned_source_01/",
         "program_group": "norovirus_provisioned_source_PS01",
         "vessels": ["classic_cruise_1900", "expedition_cruise_450",
                     "spirit_cruise_3000"]},
        {"record_id": "nps01mega",
         "prefix": "campaign/noro_provisioned_source_01_mega/",
         "program_group": "norovirus_provisioned_source_PS01",
         "vessels": ["mega_cruise_5000"]},
    ]


def _objects() -> list[dict]:
    rows = []
    for i, (vessel, size) in enumerate([
            ("classic_cruise_1900", 100), ("expedition_cruise_450", 200),
            ("spirit_cruise_3000", 300), ("other_ship_9", 50)]):
        rows.append({
            "key": f"campaign/noro_provisioned_source_01/{vessel}/"
                   f"run_1/summary.zip",
            "bytes": size, "storage_class": "STANDARD",
            "etag": f"e{i}"})
    rows.append({
        "key": "campaign/noro_provisioned_source_01_mega/"
               "mega_cruise_5000/run_1/summary.zip",
        "bytes": 999, "etag": "em"})
    for pfx, n in [("campaign/sum1/", 1), ("campaign/sum2/", 2),
                   ("campaign/cen1/", 3), ("campaign/cen2/", 4),
                   ("campaign/obs1/", 5), ("campaign/leg1/", 6),
                   ("campaign/cov1/", 7), ("campaign/flu1/", 8),
                   ("campaign/ww1/", 9)]:
        rows.append({"key": f"{pfx}obj_{n}.zip", "bytes": n * 10,
                     "etag": f"x{n}"})
    rows.append({"key": "campaign/obs1/unknown_meta.json",
                 "bytes": 1, "schema_candidate": "unknown_candidate"})
    rows.append({"key": "campaign/cen1/mega_scan_rows.jsonl",
                 "is_scan_rows_key": True, "bytes": 5})
    return rows


def _versions() -> list[dict]:
    return [
        {"key": "campaign/noro_provisioned_source_01/"
                "classic_cruise_1900/run_1/summary.zip",
         "version_id": "v-1900", "is_latest": True},
    ]


def test_select_specimens_covers_classes(scratch: Path) -> None:
    doc = pilot.select_specimens(
        _frozen(), _register(), _objects(), _versions())
    classes = {s["class"] for s in doc["specimens"]}
    for need in ("summary_archive", "census", "embedded_timeseries",
                 "legacy_nested", "clinical_non_age"):
        assert need in classes
    ps01 = [s for s in doc["specimens"]
            if s["class"].startswith("ps01_hull:")]
    vessels = {s["class"].split(":", 1)[1] for s in ps01}
    assert vessels == {"classic_cruise_1900", "expedition_cruise_450",
                       "spirit_cruise_3000", "mega_cruise_5000"}
    hull = next(s for s in ps01 if "classic" in s["class"])
    assert hull["pin"]["pin_kind"] == "version_id"
    assert hull["pin"]["version_id"] == "v-1900"
    mega = next(s for s in ps01 if "mega" in s["class"])
    assert mega["pin"]["pin_kind"] == "etag"
    missing = [s for s in doc["specimens"]
               if s["class"] == "missing_witness"]
    assert missing and missing[0]["key"] is None
    assert missing[0]["pin"]["pin_kind"] == "unpinned"
    assert missing[0]["fresh_observation"] == "blocked"
    # every uncovered class is an explicit entry, never a silent skip
    for u in doc["uncovered"]:
        assert u["class"] and u["reason"]
    # deterministic: second call identical
    again = pilot.select_specimens(
        _frozen(), _register(), _objects(), _versions())
    assert again["specimens"] == doc["specimens"]


def test_select_specimens_unsupported_witness(scratch: Path) -> None:
    doc = pilot.select_specimens(
        _frozen(), _register(), _objects(), [])
    unsup = [s for s in doc["specimens"]
             if s["class"] == "unsupported_witness"]
    assert unsup
    assert unsup[0]["key"] == "campaign/obs1/unknown_meta.json"


# ---- mega sibling _scan_rows join + reuse audit --------------------------

SIBLING = [
    "campaign/noro_provisioned_source_01_mega/"
    "mega_cruise_5000/run_7/summary.zip",
    "campaign/noro_provisioned_source_01_mega/"
    "mega_cruise_5000/run_8/result.zip",
]


def test_scan_rows_join_embedded_key() -> None:
    rows = [
        {"source_key": "s3://b/" + SIBLING[0], "payload": 1},
        {"source_uri": "result.zip"},
        {"no_key": "noise"},
    ]
    out = pilot.join_scan_rows(rows, list(SIBLING))
    assert len(out["matched"]) == 2
    assert len(out["stale_rows"]) == 1
    assert out["unmatched_keys"] == []
    kinds = {m["match_kind"] for m in out["matched"]}
    assert kinds == {"exact", "basename"}


def test_reuse_audit_classes() -> None:
    assert pilot.reuse_audit(None, [])["classification"] == \
        "no_scan_rows"
    unknown = pilot.reuse_audit(
        [{"a": 1, "b": 2}], list(SIBLING))
    assert unknown["classification"] == "unknown_provenance"
    complete = pilot.reuse_audit(
        [{"source_key": "s3://b/" + SIBLING[0]},
         {"source_key": SIBLING[1]}], list(SIBLING))
    assert complete["classification"] == "complete_summary"
    partial = pilot.reuse_audit(
        [{"source_key": "s3://b/" + SIBLING[0]}],
        list(SIBLING))
    assert partial["classification"] == "partial_precision"
    census = pilot.reuse_audit(
        [{"source_key": "s3://b/" + SIBLING[0]}],
        list(SIBLING) + ["other/census_1.zip"],
        census_keys=["other/census_1.zip"])
    assert census["classification"] == "census_missingness"


# ---- submit --phase pilot -------------------------------------------------


class _FakeBatch:
    def __init__(self):
        self.calls = []

    def submit_job(self, **kw):
        self.calls.append(kw)
        return {"jobId": "job-abc", "jobArn": "arn:aws:batch:x:job-abc"}

    def tag_resource(self, **kw):
        self.calls.append(kw)


def _specimens_doc() -> dict:
    return {
        "schema": "crusher-reducer-pilot-specimens/v1",
        "source_bucket": BUCKET,
        "specimens": [
            {"class": "summary_archive",
             "family": "campaign_summary_zip",
             "record_id": "sum1",
             "key": "campaign/sum1/obj_1.zip",
             "uri": f"s3://{BUCKET}/campaign/sum1/obj_1.zip",
             "bytes": 10, "source_id": "sum1",
             "pin": {"pin_kind": "etag", "etag": "x1"}},
            {"class": "missing_witness",
             "family": "perturbation_json",
             "record_id": "missing1",
             "key": None,
             "pin": {"pin_kind": "unpinned"}},
        ],
    }


def _invoke_submit(scratch: Path, monkeypatch, request: dict,
                   specimens=None, phase: str = "pilot",
                   batch=None, store=None) -> int:
    req = _write(scratch / "exec_req.json", request)
    argv = ["submit", "--request", rel(req),
            "--out", rel(scratch / "s"), "--phase", phase]
    if specimens is not None:
        spec = _write(scratch / "specimens.json", specimens)
        argv += ["--specimens", rel(spec)]
    if batch is not None:
        monkeypatch.setattr(
            submit, "_batch_client", lambda *a, **k: batch)
    if store is not None:
        monkeypatch.setattr(
            submit, "_s3_client", lambda *a, **k: store)
    import datetime as _dt
    monkeypatch.setattr(
        submit, "_now_utc",
        lambda: _dt.datetime(
            2026, 10, 27, 12, tzinfo=_dt.timezone.utc))
    return cli.main(argv)


def test_submit_phase_mismatch(scratch: Path, monkeypatch) -> None:
    req = execution_request(phase="materialize")
    rc = _invoke_submit(scratch, monkeypatch, req)
    assert rc == contracts.EXIT_INVALID_CONTRACT
    status = json.loads(
        (scratch / "s" / "status.json").read_text())
    assert status["error"]["kind"] == "phase_mismatch"


def test_submit_admission_expired(scratch: Path, monkeypatch) -> None:
    req = execution_request(phase="pilot")
    req["approval"]["expires_utc"] = "2020-01-01T00:00:00Z"
    rc = _invoke_submit(scratch, monkeypatch, req)
    assert rc == contracts.EXIT_ADMISSION_REQUIRED_OR_EXCEEDED
    status = json.loads(
        (scratch / "s" / "status.json").read_text())
    assert status["error"]["kind"] == "admission_expired"


def test_submit_phase_not_wired(scratch: Path, monkeypatch) -> None:
    req = execution_request(phase="finalize")
    rc = _invoke_submit(
        scratch, monkeypatch, req, phase="finalize")
    assert rc == contracts.EXIT_ACCESS_OR_RESOURCE_BLOCKED
    assert json.loads((scratch / "s" / "status.json").read_text())[
        "error"]["kind"] == "phase_not_wired"


def test_submit_pilot_happy_path(scratch: Path, monkeypatch) -> None:
    batch = _FakeBatch()
    req = execution_request(phase="pilot")
    monkeypatch.setattr(
        s3_store, "S3DerivedStore", lambda *a, **k: _FakeStore())
    rc = _invoke_submit(
        scratch, monkeypatch, req,
        specimens=_specimens_doc(), batch=batch, store=object())
    assert rc == 0
    receipt = json.loads(
        (scratch / "s" / "durable_attempt_receipt.json").read_text())
    assert receipt["specimen_count"] == 1  # missing witness skipped
    call = batch.calls[0]
    assert call["jobDefinition"] == \
        req["job_binding"]["job_definition_revision_arn"]
    argv = call["containerOverrides"]["command"]
    assert "--phase" in argv and argv[argv.index("--phase") + 1] \
        == "pilot"
    assert "--request-sha256" in argv


class _FakeStore:
    def __init__(self):
        self.puts = {}

    def put_idempotent(self, key: str, body: bytes):
        self.puts[key] = body
        return True


def test_submit_pilot_worker_doc_scratch(scratch: Path,
                                         monkeypatch) -> None:
    store = _FakeStore()
    batch = _FakeBatch()
    req = execution_request(phase="pilot")
    monkeypatch.setattr(
        s3_store, "S3DerivedStore", lambda *a, **k: store)
    rc = _invoke_submit(
        scratch, monkeypatch, req,
        specimens=_specimens_doc(), batch=batch, store=object())
    assert rc == 0
    key, body = next(iter(store.puts.items()))
    assert key.endswith("-pilot.json")
    doc = json.loads(body)
    assert doc["phase"] == "pilot"
    assert len(doc["sources"]) == 1
    src = doc["sources"][0]
    assert src["specimen_class"] == "summary_archive"
    assert src["etag"] == "x1"


# ---- committed docs sanity -----------------------------------------------

CANARY = Path("docs/campaign_reduction/canary")


def test_committed_pilot_request_is_valid_envelope() -> None:
    req = json.loads((CANARY / "pilot_request.json").read_text())
    assert req["phase"] == "pilot"
    assert req["approval"]["admission_id"] == \
        "github-environment-approval:aws-campaign"


def test_committed_bootstrap_evidence_loads(scratch: Path) -> None:
    ev = json.loads(
        (CANARY / "pilot_bootstrap_evidence.json").read_text())
    rc = _invoke_quote(scratch, _quote_req(), ev)
    # bootstrap evidence carries all declared prices + scope
    assert rc in (0, contracts.EXIT_PARTIAL_COVERAGE)
    pq = json.loads((scratch / "q" / "phase_quote.json").read_text())
    assert pq["phase_rows"]
