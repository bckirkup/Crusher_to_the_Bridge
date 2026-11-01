"""D1 regression suite — pinned readers, ZIP members, adapter registry.

The 16 old-source edge probes from ACCEPTANCE_MATRIX.json land as named
tests (``range_*``, ``D1_endpoint_*``, ``empty_*_witness``,
``all_crew_complement_edge``, ``role_classification_control``,
``acquisition_*``, ``embedded_timeseries``, ``multi_summary_first``).
All transports are ``MemoryTransport`` fakes; the module-level fixture rigs
socket/boto3/subprocess to raise so a stray network path fails the suite.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys

import pytest
from zip_builders import build_zip, gzip_wrap, member

from picard_framework.analysis.campaign_reducer import adapters, readout_helpers
from picard_framework.analysis.campaign_reducer.adapters import (
    ADAPTER_REGISTRY,
    SourceRef,
    adapter_for,
    family_capabilities,
    verify_registry,
)
from picard_framework.analysis.campaign_reducer.identity import (
    member_asset_id,
    object_id,
    run_uid,
)
from picard_framework.analysis.campaign_reducer.pinned_reader import (
    STATE_ARCHIVED,
    STATE_AVAILABLE,
    STATE_MISSING_OBJECT,
    STATE_RESOURCE_LIMIT,
    STATE_SOURCE_CHANGED,
    STATE_TRANSPORT_ERROR,
    STATE_UNPINNED_BLOCKED,
    MemoryTransport,
    ReadBudget,
    ReadOutcome,
    SourceReadError,
    TransportError,
    open_pinned,
    read_object,
)
from picard_framework.analysis.campaign_reducer.zip_members import (
    index_zip,
    read_member,
    read_member_named,
)


@pytest.fixture(autouse=True)
def _forbid_external(monkeypatch: pytest.MonkeyPatch) -> None:
    """D1 must run fully offline — any network/AWS reach fails the test."""

    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("network/subprocess/AWS call attempted")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(subprocess, "run", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setitem(sys.modules, "boto3", None)
    monkeypatch.setitem(sys.modules, "botocore", None)


def _ref(name: str = "s.zip", **kw) -> SourceRef:
    return SourceRef(
        source_id=kw.pop("source_id", "src-1"),
        uri=kw.pop("uri", f"s3://bucket/{name}"),
        campaign_id=kw.pop("campaign_id", "campaign-x"),
        **kw,
    )


def _put(transport: MemoryTransport, name: str, body: bytes, **kw) -> None:
    transport.put(name, body, **kw)


# ---------- pinned reader behaviour ----------


def test_version_pinned_read_uses_version_id() -> None:
    t = MemoryTransport()
    _put(t, "a.bin", b"payload-1234")
    outcome = read_object(t, "bucket", "a.bin")
    assert outcome.state == STATE_AVAILABLE
    assert outcome.body == b"payload-1234"
    get_calls = [c for c in t.calls if c[0] == "get"]
    assert get_calls[0][4] == "v1"  # version_id kwarg, not If-Match


def test_null_version_uses_if_match_etag() -> None:
    t = MemoryTransport()
    _put(t, "a.bin", b"body", version_id="null")
    obj = open_pinned(t, "bucket", "a.bin")
    assert obj.pin.kind == "if_match_etag"
    t.mutate("a.bin", b"mutated")
    with pytest.raises(SourceReadError) as err:
        obj.read_whole()
    assert err.value.state == STATE_SOURCE_CHANGED


def test_unpinnable_object_is_blocked_not_silent() -> None:
    t = MemoryTransport()
    _put(t, "a.bin", b"body", version_id=None)
    t._objects["a.bin"]["etag"] = None  # HEAD reports no pin evidence at all
    outcome = read_object(t, "bucket", "a.bin")
    assert outcome.state == STATE_UNPINNED_BLOCKED


def test_missing_and_denied_and_archived_are_typed() -> None:
    t = MemoryTransport()
    assert read_object(t, "bucket", "nope").state == STATE_MISSING_OBJECT
    _put(t, "denied.bin", b"x")
    t.fail_head["denied.bin"] = "access_denied"
    assert read_object(t, "bucket", "denied.bin").state == "access_denied"
    _put(t, "arch.bin", b"x")
    t.fail_head["arch.bin"] = "invalid_object_state"
    assert read_object(t, "bucket", "arch.bin").state == STATE_ARCHIVED


def test_whole_body_fallback_to_range_is_capped() -> None:
    t = MemoryTransport()
    t.honor_ranges = False
    body = b"x" * (2 * (1 << 20))
    _put(t, "big.bin", body)
    obj = open_pinned(t, "bucket", "big.bin")
    obj.budget.max_range_bytes = 1 << 20
    with pytest.raises(SourceReadError) as err:
        obj.read_range(0, 99)
    assert err.value.state == STATE_RESOURCE_LIMIT


def test_whole_body_fallback_within_cap_slices() -> None:
    t = MemoryTransport()
    t.honor_ranges = False
    _put(t, "mid.bin", b"0123456789")
    obj = open_pinned(t, "bucket", "mid.bin")
    assert obj.read_range(2, 5) == b"2345"


def test_content_range_total_mismatch_is_source_changed() -> None:
    t = MemoryTransport()
    _put(t, "a.bin", b"0123456789")
    obj = open_pinned(t, "bucket", "a.bin")

    class LyingTransport:
        def get(self, key, **kwargs):
            from picard_framework.analysis.campaign_reducer.pinned_reader import (
                GetResponse,
            )

            return GetResponse(206, b"0123", content_range="bytes 0-3/9999")

    obj.transport = LyingTransport()
    with pytest.raises(SourceReadError) as err:
        obj.read_range(0, 3)
    assert err.value.state == STATE_SOURCE_CHANGED


def test_retryable_transient_then_success_charges_budget() -> None:
    t = MemoryTransport()
    _put(t, "a.bin", b"data!")
    obj = open_pinned(t, "bucket", "a.bin")
    calls = {"n": 0}
    real_get = t.get

    def flaky(key, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TransportError("throttled", "slow down")
        return real_get(key, **kw)

    t.get = flaky
    assert obj.read_whole() == b"data!"
    assert calls["n"] == 2
    assert obj.budget.requests_used >= 2


def test_unclassified_transport_error_is_typed_not_leaked() -> None:
    t = MemoryTransport()
    _put(t, "a.bin", b"x")
    t.fail_get["a.bin"] = "signature_broken"
    outcome = read_object(t, "bucket", "a.bin")
    assert outcome.state == STATE_TRANSPORT_ERROR


def test_budget_is_cumulative_across_reads() -> None:
    t = MemoryTransport()
    _put(t, "a.bin", b"0123456789")
    budget = ReadBudget(max_requests=3)
    obj = open_pinned(t, "bucket", "a.bin", budget)
    obj.read_range(0, 1)
    obj.read_range(2, 3)
    with pytest.raises(SourceReadError) as err:
        obj.read_range(4, 5)
    assert err.value.state == STATE_RESOURCE_LIMIT


# ---------- the 16 named edge probes ----------


def test_range_stored() -> None:
    t = MemoryTransport()
    blob = build_zip([member("summary.json", b'{"ok": true}', method=0)])
    _put(t, "s.zip", blob)
    obj = open_pinned(t, "bucket", "s.zip")
    idx = index_zip(obj)
    out = read_member_named(obj, idx, "summary.json")
    assert out.state == STATE_AVAILABLE
    assert json.loads(out.body) == {"ok": True}


def test_range_deflate() -> None:
    t = MemoryTransport()
    payload = b"deflated-" * 500
    blob = build_zip([member("big.json", payload, method=8)])
    _put(t, "d.zip", blob)
    obj = open_pinned(t, "bucket", "d.zip")
    idx = index_zip(obj)
    out = read_member_named(obj, idx, "big.json")
    assert out.state == STATE_AVAILABLE
    assert out.body == payload


def test_range_nested_exact_name() -> None:
    t = MemoryTransport()
    blob = build_zip([
        member("run_001/summary.json", b'{"run": 1}'),
        member("run_002/summary.json", b'{"run": 2}'),
    ])
    _put(t, "fused.zip", blob)
    obj = open_pinned(t, "bucket", "fused.zip")
    idx = index_zip(obj)
    out = read_member_named(obj, idx, "run_002/summary.json")
    assert out.state == STATE_AVAILABLE
    assert json.loads(out.body)["run"] == 2


def test_range_max_zip_comment() -> None:
    t = MemoryTransport()
    comment = b"c" * 65000 + b"PK\x05\x06" + b"d" * (65535 - 65000 - 4)
    blob = build_zip([member("a.json", b"{}")], comment=comment)
    _put(t, "c.zip", blob)
    obj = open_pinned(t, "bucket", "c.zip")
    idx = index_zip(obj)
    assert idx.member_names() == ["a.json"]


def test_range_crc_not_checked() -> None:
    # The legacy reader returned the bytes without checking CRC; the
    # reducer must type it as crc_failure.
    t = MemoryTransport()
    blob = build_zip([member("bad.json", b"payload", crc_override=0)])
    _put(t, "crc.zip", blob)
    obj = open_pinned(t, "bucket", "crc.zip")
    idx = index_zip(obj)
    out = read_member_named(obj, idx, "bad.json")
    assert out.state == "crc_failure"


def test_range_no_version_pin() -> None:
    t = MemoryTransport()
    blob = build_zip([member("a.json", b"{}")])
    _put(t, "np.zip", blob, version_id="null")
    obj = open_pinned(t, "bucket", "np.zip")
    index_zip(obj)
    ranged = [c for c in t.calls if c[0] == "get" and c[2] is not None]
    assert ranged
    assert all(c[5] == obj.pin.etag for c in ranged)
    assert all(c[4] is None for c in ranged)


def test_D1_endpoint_4() -> None:
    assert readout_helpers.inclusive_endpoint_hit("4", "4")
    assert not readout_helpers.inclusive_endpoint_hit("3.9999", "4")


def test_D1_endpoint_9() -> None:
    assert readout_helpers.inclusive_endpoint_hit("0.90", "0.90")
    assert not readout_helpers.inclusive_endpoint_hit("0.8999999999999999", "0.90")


def test_empty_off_witness() -> None:
    row = readout_helpers.rate_row(0, 0)
    assert row["denominator_status"] == "no_denominator"
    assert row["rate"] is None


def test_empty_ind_witness() -> None:
    row = readout_helpers.rate_row(0, 0)
    assert row["center"] is None
    assert row["lo"] is None


def test_all_crew_complement_edge() -> None:
    t = MemoryTransport()
    doc = {"crew_complement": 50, "passenger_complement": 0, "crew_infected": 5}
    t.put("cell.json", json.dumps(doc).encode())
    ref = _ref("cell.json", campaign_id="covid_screen_json", seed=7)
    result = adapter_for("covid_screen_json")(ref, t, ReadBudget())
    paths = {s.native_path for s in result.scalars}
    assert "/passenger_complement" in paths
    pax_scalar = [s for s in result.scalars if s.native_path == "/passenger_complement"]
    assert pax_scalar[0].native_value_json == "0"
    crew = readout_helpers.rate_row(5, 50)
    assert crew["denominator_status"] == "measured"
    pax = readout_helpers.rate_row(0, 0)
    assert pax["rate"] is None


def test_role_classification_control() -> None:
    doc = {
        "role": "crew", "role_subtype": "galley",
        "compliant": False, "mask": None, "count": 0,
    }
    t = MemoryTransport()
    t.put("row.json", json.dumps(doc).encode())
    ref = _ref("row.json", campaign_id="covid_screen_json")
    result = adapter_for("covid_screen_json")(ref, t, ReadBudget())
    by_path = {s.native_path: s for s in result.scalars}
    assert by_path["/compliant"].native_value_json == "false"
    assert by_path["/mask"].native_value_json == "null"
    assert by_path["/count"].native_value_json == "0"
    assert by_path["/role_subtype"].native_value_json == '"galley"'


def test_acquisition_overlap_duplicates() -> None:
    t = MemoryTransport()
    blob = build_zip([
        member("summary.json", b'{"v": 1}'),
        member("summary.json", b'{"v": 2}'),
    ])
    _put(t, "dup.zip", blob)
    obj = open_pinned(t, "bucket", "dup.zip")
    idx = index_zip(obj)
    assert "summary.json" in idx.duplicates
    out = read_member_named(obj, idx, "summary.json")
    assert out.state == "duplicate_members"


def test_acquisition_field_order() -> None:
    doc_a = {"a": 1, "b": 2}
    doc_b = {"b": 2, "a": 1}
    t = MemoryTransport()
    for i, doc in enumerate((doc_a, doc_b)):
        t.put(f"r{i}.json", json.dumps(doc).encode())
        ref = _ref(f"r{i}.json", campaign_id="covid_screen_json")
        result = adapter_for("covid_screen_json")(ref, t, ReadBudget())
        assert {s.native_path for s in result.scalars} == {"/a", "/b"}


def test_embedded_timeseries() -> None:
    doc = {"summary": 1, "timeseries": [{"new_infections": 3}]}
    t = MemoryTransport()
    blob = build_zip([member("summary.json", json.dumps(doc).encode())])
    _put(t, "ts.zip", blob)
    ref = _ref("ts.zip", campaign_id="campaign_summary_zip")
    result = adapter_for("campaign_summary_zip")(ref, t, ReadBudget())
    assert any(
        s.native_path == "/timeseries/0/new_infections" for s in result.scalars
    )


def test_multi_summary_first() -> None:
    t = MemoryTransport()
    blob = build_zip([
        member("run_1/summary.json", b'{"which": 1}'),
        member("run_2/summary.json", b'{"which": 2}'),
    ])
    _put(t, "fused.zip", blob)
    obj = open_pinned(t, "bucket", "fused.zip")
    idx = index_zip(obj)
    groups = idx.run_groups()
    assert set(groups) == {"run_1", "run_2"}
    out = read_member_named(obj, idx, "run_2/summary.json")
    assert json.loads(out.body)["which"] == 2


# ---------- ZIP64 + hostile structures ----------


def test_zip64_chain_resolves() -> None:
    t = MemoryTransport()
    blob = build_zip([member("z.json", b'{"z": 1}', method=8)], zip64=True)
    _put(t, "z64.zip", blob)
    obj = open_pinned(t, "bucket", "z64.zip")
    idx = index_zip(obj)
    assert idx.zip64
    out = read_member_named(obj, idx, "z.json")
    assert json.loads(out.body) == {"z": 1}


def test_unsupported_compression_is_typed() -> None:
    t = MemoryTransport()
    blob = build_zip([member("m.bin", b"data", method=99)])
    _put(t, "u.zip", blob)
    obj = open_pinned(t, "bucket", "u.zip")
    idx = index_zip(obj)
    out = read_member_named(obj, idx, "m.bin")
    assert out.state == "unsupported_compression"


def test_truncated_member_is_corrupt() -> None:
    t = MemoryTransport()
    blob = build_zip([
        member("t.bin", b"0123456789", comp_override=500),
    ])
    _put(t, "t.zip", blob)
    obj = open_pinned(t, "bucket", "t.zip")
    idx = index_zip(obj)
    entry = idx.members_named("t.bin")[0]
    with pytest.raises(SourceReadError) as err:
        read_member(obj, entry)
    assert err.value.state == "corrupt_archive"


def test_missing_member_is_typed() -> None:
    t = MemoryTransport()
    blob = build_zip([member("a.json", b"{}")])
    _put(t, "m.zip", blob)
    obj = open_pinned(t, "bucket", "m.zip")
    idx = index_zip(obj)
    out = read_member_named(obj, idx, "absent.json")
    assert out.state == "missing_member"


# ---------- registry, identity, capabilities ----------


def test_registry_covers_every_contract_family() -> None:
    report = verify_registry()
    assert report["ok"], report
    assert report["family_count"] == len(report["registered"])
    assert report["family_count"] == len(report["families"])
    assert not report["missing_adapters"]
    assert not report["extra_adapters"]


def test_registry_keys_are_contract_schema_families() -> None:
    assert set(ADAPTER_REGISTRY) == set(adapters.contract_families())


def test_family_capabilities_map_contract_status() -> None:
    caps = family_capabilities()
    by_axis = {(c.family, c.axis): c.availability for c in caps}
    from picard_framework.analysis.campaign_reducer import contracts
    fams = {
        e["schema_family"]: e for e in contracts.load(contracts.SOURCE_FAMILIES)
    }
    assert len(fams) == len({c.family for c in caps})
    fomite = fams["fomite_diagnostic_gzip"]
    if fomite["mechanism"]["status"] == "known_saved":
        assert by_axis[("fomite_diagnostic_gzip", "mechanism")] == "recoverable_unread"
    growth = fams["growth_census_zip"]
    if growth["AR"]["status"] == "documented_unverified":
        assert by_axis[("growth_census_zip", "AR")] == "partial"


def test_seed_identity_never_collides_across_attempts() -> None:
    a = run_uid(
        campaign_id="c", attempt_id="a1", vessel_id="hull-1",
        case_id="cell-1", engine_sha="e", image_digest="i",
        seed=8105, original_run_id="r1",
    )
    b = run_uid(
        campaign_id="c", attempt_id="a2", vessel_id="hull-2",
        case_id="cell-2", engine_sha="e", image_digest="i",
        seed=8105, original_run_id="r1",
    )
    assert a != b


def test_object_and_member_hashes_are_distinct_roles() -> None:
    oid = object_id("bucket", "k.zip", "v1", '"e"')
    mid = member_asset_id(oid, "summary.json")
    assert oid != mid
    assert oid.startswith("obj-")
    assert mid.startswith("mem-")


def test_gzip_json_adapter_decodes() -> None:
    doc = {"hand_occupancy": [0.1, 0.2]}
    t = MemoryTransport()
    t.put("f.json.gz", gzip_wrap(json.dumps(doc).encode()))
    ref = _ref("f.json.gz", campaign_id="fomite_diagnostic_gzip")
    result = adapter_for("fomite_diagnostic_gzip")(ref, t, ReadBudget())
    assert result.links[0].read_state == STATE_AVAILABLE
    assert any(
        s.native_path == "/hand_occupancy/1" for s in result.scalars
    )


def test_jsonl_adapter_preserves_rows_and_types() -> None:
    rows = '{"point": 1, "x": 0}\n{"point": 2, "x": null}\n'
    t = MemoryTransport()
    t.put("shard_0000.jsonl", rows.encode())
    ref = _ref("shard_0000.jsonl", campaign_id="bounded_region_jsonl")
    result = adapter_for("bounded_region_jsonl")(ref, t, ReadBudget())
    zero = [s for s in result.scalars if s.native_value_json == "0"]
    nulls = [s for s in result.scalars if s.native_value_json == "null"]
    assert zero
    assert nulls


def test_unknown_legacy_inventories_without_fabricating() -> None:
    t = MemoryTransport()
    t.put("mystery.bin", b"\x00\x01\x02")
    ref = _ref("mystery.bin", campaign_id="unknown_legacy")
    result = adapter_for("unknown_legacy")(ref, t, ReadBudget())
    assert result.gaps
    assert result.gaps[0].reason == "unknown_schema"


def test_read_outcome_is_never_exception_as_data() -> None:
    t = MemoryTransport()
    outcome = read_object(t, "bucket", "gone.zip")
    assert isinstance(outcome, ReadOutcome)
    assert outcome.state == STATE_MISSING_OBJECT


# ---------- branch coverage: tails, malformed archives, parquet, payloads ----------


def test_read_tail_pulls_terminal_bytes_only() -> None:
    t = MemoryTransport()
    body = bytes(range(256)) * 40
    _put(t, "tail.bin", body)
    obj = open_pinned(t, "bucket", "tail.bin", ReadBudget())
    assert obj.read_tail(64) == body[-64:]


def test_read_tail_clamps_to_object_size() -> None:
    t = MemoryTransport()
    _put(t, "tail.bin", b"abc")
    obj = open_pinned(t, "bucket", "tail.bin", ReadBudget())
    assert obj.read_tail(10) == b"abc"


def test_eocd_missing_is_corrupt_archive() -> None:
    from picard_framework.analysis.campaign_reducer.zip_members import open_zip

    t = MemoryTransport()
    _put(t, "notzip.bin", b"this is definitely not a zip archive at all!")
    obj = open_pinned(t, "bucket", "notzip.bin", ReadBudget())
    index, err = open_zip(obj)
    assert index is None
    assert err is not None
    assert err.state == "corrupt_archive"


def test_eocd_zip64_counts_without_locator_is_corrupt() -> None:
    from picard_framework.analysis.campaign_reducer.zip_members import open_zip

    blob = bytearray(build_zip([member("a.txt", b"hi")]))
    # EOCD sits at the tail end of a comment-less zip: patch the two
    # entry-count fields to 0xFFFF without a ZIP64 locator present.
    blob[-14:-12] = b"\xff\xff"
    blob[-12:-10] = b"\xff\xff"
    t = MemoryTransport()
    _put(t, "fake64.zip", bytes(blob))
    obj = open_pinned(t, "bucket", "fake64.zip", ReadBudget())
    index, err = open_zip(obj)
    assert index is None
    assert err is not None
    assert err.state == "corrupt_archive"


def test_encrypted_member_is_unsupported_compression() -> None:
    z = build_zip([member("secret.txt", b"hunter2", flags=0x0001)])
    t = MemoryTransport()
    _put(t, "enc.zip", z)
    obj = open_pinned(t, "bucket", "enc.zip", ReadBudget())
    index = index_zip(obj)
    with pytest.raises(SourceReadError) as exc:
        read_member(obj, index.entries[0])
    assert exc.value.state == "unsupported_compression"


def test_member_declared_sizes_over_cap_are_typed() -> None:
    z = build_zip([member("big.bin", b"x" * 100)])
    t = MemoryTransport()
    _put(t, "big.zip", z)
    obj = open_pinned(t, "bucket", "big.zip", ReadBudget(max_member_bytes=10))
    index = index_zip(obj)
    with pytest.raises(SourceReadError) as exc:
        read_member(obj, index.entries[0])
    assert exc.value.state == STATE_RESOURCE_LIMIT


def test_stored_member_size_lie_is_corrupt() -> None:
    z = build_zip(
        [member("lie.bin", b"real-bytes", method=0, comp_override=999)]
    )
    t = MemoryTransport()
    _put(t, "lie.zip", z)
    obj = open_pinned(t, "bucket", "lie.zip", ReadBudget())
    index = index_zip(obj)
    with pytest.raises(SourceReadError) as exc:
        read_member(obj, index.entries[0])
    assert exc.value.state in ("corrupt_archive", "resource_limit")


def test_parquet_adapter_verifies_par1_magic() -> None:
    t = MemoryTransport()
    _put(t, "region.parquet", b"PAR1" + b"\x00" * 50 + b"PAR1")
    result = adapters.reduce_source(
        "bounded_region_jsonl", _ref("region.parquet"), t,
    )
    assert result.assets
    assert result.assets[0].read_state == "indexed"


def test_parquet_adapter_rejects_non_par1() -> None:
    t = MemoryTransport()
    _put(t, "fake.parquet", b"NOPExxxx")
    result = adapters.reduce_source(
        "bounded_region_jsonl", _ref("fake.parquet"), t,
    )
    assert result.links[-1].read_state == "unsupported_schema"
    assert result.gaps[-1].reason == "unknown_schema"


def test_reduce_source_unknown_family_raises() -> None:
    ref = _ref("x.json")
    transport = MemoryTransport()
    with pytest.raises(KeyError):
        adapters.reduce_source("not_a_family", ref, transport)


def test_read_outcome_for_typed_inventory() -> None:
    t = MemoryTransport()
    outcome = adapters.read_outcome_for(_ref("ghost.json"), t)
    assert outcome.state == STATE_MISSING_OBJECT


def test_json_adapter_non_json_body_is_typed() -> None:
    t = MemoryTransport()
    _put(t, "broken.json", b"{not json at all")
    result = adapters.reduce_source("covid_screen_json", _ref("broken.json"), t)
    assert result.links[-1].read_state == "unsupported_schema"
    assert result.gaps[-1].reason == "unknown_schema"


def test_verify_registry_flags_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapters, "contract_families",
                        lambda: ["growth_census_zip", "made_up_family"])
    report = verify_registry()
    assert not report["ok"]
    assert "made_up_family" in report["missing_adapters"]
    assert report["family_count"] == 2


def test_json_pointer_escapes_tilde_and_slash() -> None:
    from picard_framework.analysis.campaign_reducer.payloads import json_pointer

    assert json_pointer("a~b", "c/d") == "/a~0b/c~1d"
    assert json_pointer() == "/"


def test_native_token_distinguishes_zero_false_null() -> None:
    from picard_framework.analysis.campaign_reducer.payloads import native_token

    assert native_token(0) == ("0", "number")
    assert native_token(False) == ("false", "boolean")
    assert native_token(None) == ("null", "null")
    tok, ntype = native_token({"k": 1})
    assert ntype == "object"
    assert json.loads(tok) == {"k": 1}


def test_canonical_state_mapping_covers_internal_states() -> None:
    from picard_framework.analysis.campaign_reducer.pinned_reader import (
        canonical_source_read_state,
    )

    assert canonical_source_read_state("duplicate_members") == "corrupt_archive"
    assert canonical_source_read_state("unpinned_blocked") == "access_denied"
    assert canonical_source_read_state("transport_error") == "not_yet_read"
    assert canonical_source_read_state(STATE_AVAILABLE) == "available"


def test_identity_id_roles_and_prefixes() -> None:
    from picard_framework.analysis.campaign_reducer.identity import case_id

    oid = object_id("bucket", "key", "v1", None)
    mid = member_asset_id("zip-1", "run_3/summary.json")
    assert oid.startswith("obj-")
    assert mid.startswith("mem-")
    assert oid != mid
    assert case_id("hull", "cell", "cfg").startswith("cell-")


def test_wilson_zero_denominator_emits_na_rows() -> None:
    row = readout_helpers.rate_row(0, 0)
    assert row["rate"] is None
    assert row["denominator_status"] == "no_denominator"
    assert readout_helpers.wilson_interval(3, 0) is None
