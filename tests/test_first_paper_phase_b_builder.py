"""Phase B cohort-builder tests — manifest, request, reconciliation."""

from __future__ import annotations

import json
import sys

import pytest

from deploy.aws import build_first_paper_phase_b as builder


def _scan_dir(tmp_path, rows_per_arm=2):
    scan = tmp_path / "scan"
    scan.mkdir()
    for arm in builder.ARMS:
        hull = arm.split("_12d_scr_")[0]
        rows = [
            {
                "key": f"campaign/noro_provisioned_source_01/"
                       f"{arm}/run_{i}.zip",
                "hull": f"{hull}_hull",
                "seed": 8000 + i,
            }
            for i in range(rows_per_arm)
        ]
        (scan / f"{arm}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n")
    return scan


def _run(tmp_path, monkeypatch, scan):
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "builder", "--scan-dir", str(scan), "--out-dir", str(out)])
    assert builder.main() == 0
    return out


def test_builder_emits_manifest_request_cohort(tmp_path, monkeypatch):
    scan = _scan_dir(tmp_path)
    out = _run(tmp_path, monkeypatch, scan)

    manifest = json.loads((out / "red-fps01-b-sources.json").read_text())
    assert manifest["schema"] == "crusher-reducer-sources/v1"
    sources = manifest["sources"]
    # 8 scan sources + 16 run sources
    assert len(sources) == 24
    scans = [s for s in sources if s.get("source_role") == "scan_rows"]
    assert len(scans) == 8
    assert scans == sources[:8]
    runs = [s for s in sources if s.get("source_role") != "scan_rows"]
    assert all(r["family"] == "campaign_summary_zip" for r in runs)
    assert all(r["uri"].startswith("s3://") for r in sources)

    request = json.loads((out / "red-fps01-b-request.json").read_text())
    assert request["schema"] == "crusher-reducer-spec/v1"
    assert request["extraction_profile"] == "first_paper_scalar"
    assert request["declared_source_count"] == 24
    assert request["sources_sha256"] == builder._canonical_sha(manifest)

    cohort = json.loads((out / "red-fps01-b-cohort.json").read_text())
    assert cohort["expected_runs"] == 16
    assert cohort["unique_keys"] == 16
    assert cohort["duplicate_keys"] == []
    # off/ps_ship rows share (hull, seed) per hull → 8 complete pairs
    assert cohort["pairs_complete"] == 8
    assert cohort["pairs_incomplete"] == {}


def test_builder_aborts_on_missing_scan_file(tmp_path, monkeypatch):
    scan = tmp_path / "scan"
    scan.mkdir()
    (scan / f"{builder.ARMS[0]}.jsonl").write_text(
        json.dumps({"key": "k.zip"}) + "\n")
    with pytest.raises(SystemExit):
        _run(tmp_path, monkeypatch, scan)


def test_builder_aborts_on_row_without_zip_key(tmp_path, monkeypatch):
    scan = _scan_dir(tmp_path)
    bad = scan / f"{builder.ARMS[0]}.jsonl"
    bad.write_text(json.dumps({"key": "not-a-zip"}) + "\n")
    with pytest.raises(SystemExit):
        _run(tmp_path, monkeypatch, scan)


def test_builder_flags_duplicate_and_unpaired(tmp_path, monkeypatch):
    scan = _scan_dir(tmp_path)
    # duplicate key across the two exp arms, breaking one pair
    dup = scan / "fl_exp_12d_scr_ps_ship.jsonl"
    dup.write_text(json.dumps({
        "key": "campaign/noro_provisioned_source_01/"
               "fl_exp_12d_scr_off/run_0.zip",
        "hull": "fl_exp_hull",
        "seed": 8000,
    }) + "\n")
    out = _run(tmp_path, monkeypatch, scan)
    cohort = json.loads((out / "red-fps01-b-cohort.json").read_text())
    assert len(cohort["duplicate_keys"]) == 1
    assert cohort["pairs_complete"] < 8
    assert cohort["pairs_incomplete"]
