"""Correction-spec acceptance tests (DEVIN_PR1119_FOLLOWUP).

- JOIN SAFETY: full-key join only; (hull,seed) is ambiguous across arms
  (off/ps_ship share seeds), so a key miss is ``scan_source_absent`` and
  a hull/seed disagreement is a typed conflict — never first-row-wins.
- COMPLETION STATUS: completion/follow-up/clock columns derive from
  real evidence, ``unknown`` by default; role-nested sums validate
  against role totals then combined totals; count/rate domain rejects
  bool/negative/nonfinite.
- SEAMS: <=1MiB unique-named JSONL pages + collector-compatible
  manifest + authoritative status.json + asset_index.json; bounded
  page selection for collect.
- RESUME: a non-completed COMMIT is terminal — rerun is typed blocked
  with lineage, never a re-finalize conflict.
"""
from __future__ import annotations

import json

from picard_framework.analysis.campaign_reducer.materialize import (
    _PAGE_MAX_BYTES,
    run_materialization,
)
from picard_framework.analysis.campaign_reducer.return_path import (
    _select_pages,
)
from picard_framework.analysis.campaign_reducer.rows import SourceSpec
from tests.analysis.campaign_reducer.test_d7_first_paper_scalar import (  # noqa: E501
    _rig,
    _run_zip,
    _scan_entry,
    _scan_rows_obj,
    _spec,
    _src,
    _vector_rows,
)


def _scan_spec():
    return _src(
        "_scan_rows/arm.jsonl",
        family="observation_jsonl",
        source_role="scan_rows",
    )


def _run_source(uri="run_a.zip", seed=8000):
    return SourceSpec(
        uri=uri, family="growth_census_zip", source_id=uri,
        campaign_id="noro", seed=seed, hull_id="expedition_cruise_450",
        member_allowlist=("summary.json",), emit_scalars=False,
    )


def test_full_key_only_join_no_hull_seed_fallback():
    """A scan row sharing (hull,seed) but not the object key is absent."""
    transport, store, ledger = _rig()
    transport.put("run_a.zip", _run_zip(seed=8000))
    transport.put(
        "_scan_rows/arm.jsonl",
        _scan_rows_obj([_scan_entry("run_OTHER.zip", 8000, posted=True)]),
    )
    spec = _spec(
        [_scan_spec(), _run_source()],
        extraction_profile="first_paper_scalar",
    )
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "completed"
    row = _vector_rows(store)[0]
    assert row["values"]["scan_posted"] is None
    assert row["provenance"]["scan_posted"]["status"] == (
        "scan_source_absent")


def test_scan_agreement_conflict_is_typed_missing():
    """Key hit but hull disagreement -> conflict + typed missing."""
    transport, store, ledger = _rig()
    transport.put("run_a.zip", _run_zip(seed=8000))
    transport.put(
        "_scan_rows/arm.jsonl",
        _scan_rows_obj([
            _scan_entry("run_a.zip", 8000, hull="WRONG_HULL",
                        posted=True)]),
    )
    spec = _spec(
        [_scan_spec(), _run_source()],
        extraction_profile="first_paper_scalar",
    )
    result = run_materialization(spec, transport, store, ledger)
    row = _vector_rows(store)[0]
    assert row["values"]["scan_posted"] is None
    assert row["provenance"]["scan_posted"]["status"] == (
        "scan_agreement_conflict")
    commit = json.loads(store.get(result.commit_key))
    assert commit["coverage"]["scan_join_conflicts"] == 1


def test_domain_invalid_negative_count():
    """A negative count field emits domain_invalid, never the value."""
    transport, store, ledger = _rig()
    body = _run_zip(seed=8000)
    import io
    import zipfile
    zin = zipfile.ZipFile(io.BytesIO(body))
    summary = json.loads(zin.read("summary.json"))
    summary["summary"]["cumulative_ever_infected"] = -3
    zout = io.BytesIO()
    with zipfile.ZipFile(zout, "w") as z:
        for name in zin.namelist():
            data = zin.read(name)
            if name == "summary.json":
                data = json.dumps(summary).encode()
            z.writestr(name, data)
    transport.put("run_a.zip", zout.getvalue())
    spec = _spec([_run_source()], extraction_profile="first_paper_scalar")
    run_materialization(spec, transport, store, ledger)
    row = _vector_rows(store)[0]
    assert row["values"]["cumulative_ever_infected"] is None
    assert row["provenance"]["cumulative_ever_infected"]["status"] == (
        "domain_invalid")


def test_status_columns_from_evidence():
    """clock/completion/follow-up columns derive from real fields."""
    transport, store, ledger = _rig()
    transport.put("run_a.zip", _run_zip(seed=8000))
    transport.put(
        "_scan_rows/arm.jsonl",
        _scan_rows_obj([_scan_entry("run_a.zip", 8000, posted=True)]),
    )
    spec = _spec(
        [_scan_spec(), _run_source()],
        extraction_profile="first_paper_scalar",
    )
    run_materialization(spec, transport, store, ledger)
    row = _vector_rows(store)[0]
    # declared parameters.num_epochs absent from _run_zip parameters:
    # clock is unknown by default, never guessed.
    assert row["values"]["clock_status"] == "unknown"
    assert row["values"]["completion_status"] == "unknown"
    assert row["values"]["follow_up_status"] == "posted"

    # now with a declared horizon equal to the emitted clock
    transport2, store2, ledger2 = _rig()
    import io
    import zipfile
    body = _run_zip(seed=8000)
    zin = zipfile.ZipFile(io.BytesIO(body))
    summary = json.loads(zin.read("summary.json"))
    summary["parameters"]["num_epochs"] = 288
    zout = io.BytesIO()
    with zipfile.ZipFile(zout, "w") as z:
        for name in zin.namelist():
            z.writestr(
                name,
                json.dumps(summary).encode()
                if name == "summary.json"
                else zin.read(name),
            )
    transport2.put("run_a.zip", zout.getvalue())
    spec2 = _spec([_run_source()],
                  extraction_profile="first_paper_scalar")
    run_materialization(spec2, transport2, store2, ledger2)
    row2 = _vector_rows(store2)[0]
    assert row2["values"]["clock_status"] == "complete"
    assert row2["values"]["completion_status"] == "completed"
    assert row2["values"]["follow_up_status"] == "unknown"


def test_terminal_attempt_is_blocked_with_lineage():
    """A budget_stopped COMMIT is terminal: rerun is typed blocked."""
    transport, store, ledger = _rig()
    commit_key = (
        "campaign/_derived/reducer/v1/attempts/red-fp/COMMIT.json"
    )
    store.put_idempotent(
        commit_key,
        json.dumps({
            "status": "budget_stopped",
            "catalog_snapshot_id": "snap-old",
            "partitions": [],
            "counts": {},
        }).encode(),
    )
    transport.put("run_a.zip", _run_zip(seed=8000))
    spec = _spec([_run_source()], extraction_profile="first_paper_scalar")
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "blocked"
    kinds = [e["kind"] for e in result.errors]
    assert "attempt_terminal" in kinds
    err = next(e for e in result.errors
               if e["kind"] == "attempt_terminal")
    assert err["prior_snapshot"] == "snap-old"


def test_pages_layer_bounded_and_indexed():
    """Completed finalize emits <=1MiB pages + manifest + status + index."""
    transport, store, ledger = _rig()
    for i in range(4):
        transport.put(f"run_{i}.zip", _run_zip(seed=8000 + i))
    sources = [_run_source(f"run_{i}.zip", 8000 + i) for i in range(4)]
    spec = _spec(sources, extraction_profile="first_paper_scalar")
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "completed"
    prefix = "campaign/_derived/reducer/v1/attempts/red-fp/"
    pages = [k for k in store.list(f"{prefix}pages/")
             if k.endswith(".jsonl")]
    assert pages
    for key in pages:
        assert len(store.get(key)) <= _PAGE_MAX_BYTES
    manifest = json.loads(store.get(
        f"{prefix}pages/first_paper_vectors.pages_manifest.json"))
    assert manifest["kind"] == "first_paper_pages_manifest"
    assert manifest["page_count"] == len(manifest["entries"])
    total = sum(e["rows"] for e in manifest["entries"])
    assert total == 4
    for e in manifest["entries"]:
        body = store.get(e["uri"])
        import hashlib
        assert hashlib.sha256(body).hexdigest() == e["sha256"]
    status = json.loads(store.get(f"{prefix}status.json"))
    assert status["status"] == "completed"
    assert status["counts"]["first_paper_vectors"] == 4
    index = json.loads(store.get(f"{prefix}asset_index.json"))
    kinds = {a["kind"] for a in index["assets"]}
    assert {"pages_manifest", "status", "vector_page"} <= kinds


def test_select_pages_bounded():
    entries = [
        {"page_id": f"page-{i:05d}", "uri": f"u{i}"} for i in range(5)
    ]
    picked = _select_pages({"collect_page_ids": ["page-00002"]}, entries)
    assert picked == [{"page_id": "page-00002", "uri": "u2"}]
    picked = _select_pages({"collect_page_limit": 2}, entries)
    assert len(picked) == 2
    picked = _select_pages({}, entries)
    assert len(picked) == 5
    import pytest

    from picard_framework.analysis.campaign_reducer.return_path import (
        ReturnFailure,
    )
    with pytest.raises(ReturnFailure):
        _select_pages({"collect_page_ids": ["page-99999"]}, entries)


def test_role_nested_sum_validates_role_then_combined():
    """Role-nested dicts validate per-role totals then combined."""
    transport, store, ledger = _rig()
    import io
    import zipfile
    body = _run_zip(seed=8000, rep_pax=2, rep_crew=3)
    zin = zipfile.ZipFile(io.BytesIO(body))
    summary = json.loads(zin.read("summary.json"))
    # make the dict role-nested and consistent
    summary["summary"]["reported_cases_by_channel"] = {
        "passenger": {"syndromic": 2},
        "crew": {"syndromic": 3},
    }
    zout = io.BytesIO()
    with zipfile.ZipFile(zout, "w") as z:
        for name in zin.namelist():
            z.writestr(
                name,
                json.dumps(summary).encode()
                if name == "summary.json"
                else zin.read(name),
            )
    transport.put("run_a.zip", zout.getvalue())
    spec = _spec([_run_source()], extraction_profile="first_paper_scalar")
    run_materialization(spec, transport, store, ledger)
    row = _vector_rows(store)[0]
    assert row["values"]["reported_by_channel_consistent"] is True
    by_role = json.loads(
        row["values"]["reported_by_channel_sum_by_role"])
    assert by_role == {"passenger": 2, "crew": 3}
    assert row["values"]["reported_by_channel_sum"] == 5

    # role-level divergence -> typed divergent
    transport2, store2, ledger2 = _rig()
    summary["summary"]["cumulative_reported_cases_crew"] = 4
    zout = io.BytesIO()
    with zipfile.ZipFile(zout, "w") as z:
        for name in zin.namelist():
            z.writestr(
                name,
                json.dumps(summary).encode()
                if name == "summary.json"
                else zin.read(name),
            )
    transport2.put("run_a.zip", zout.getvalue())
    spec2 = _spec([_run_source()],
                  extraction_profile="first_paper_scalar")
    run_materialization(spec2, transport2, store2, ledger2)
    row2 = _vector_rows(store2)[0]
    assert row2["values"]["reported_by_channel_consistent"] is False
    assert row2["provenance"]["reported_by_channel_consistent"][
        "status"] == "sum_divergent"
