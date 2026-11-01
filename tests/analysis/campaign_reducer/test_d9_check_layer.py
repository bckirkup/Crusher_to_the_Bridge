"""D9 — check layer + chunked collect.

Owner refinement (Devin Bot): the delivery bundle ships narrow validated
helpers so a verifier confirms computations cheaply, and the tranche
collect covers every page in bounded legs via ``collect_all_pages``.
"""
import hashlib
import json

import pytest

from picard_framework.analysis.campaign_reducer.return_path import (
    ReturnFailure,
    _collect_chunks,
)
from picard_framework.analysis.campaign_reducer.vector_checks import (
    paired_contrast,
    recompute_aggregate,
    verify_page,
)


def _row(hull, seed, arm, **values):
    return {
        "hull_id": hull, "seed": seed,
        "cell_id": f"fl_x_12d_scr_{arm}",
        "run_uid": f"run-{hull}-{seed}-{arm}",
        "values": values,
    }


def _write_pages(tmp_path, rows, per_page=2):
    pages = []
    for i in range(0, len(rows), per_page):
        p = tmp_path / f"page-{len(pages):05d}.jsonl"
        p.write_text("\n".join(json.dumps(r)
                               for r in rows[i:i + per_page]) + "\n")
        pages.append(str(p))
    return pages


# ---------------------------------------------------------------- chunks


def test_collect_all_pages_chunks_under_both_caps():
    entries = [{"page_id": f"p{i}", "uri": f"u{i}", "bytes": 1_000_000}
               for i in range(45)]
    chunks = _collect_chunks(
        {"collect_all_pages": True}, entries, base_total=5_000_000)
    assert len(chunks) == 3
    assert sum(len(c) for c in chunks) == 45
    for c in chunks:
        assert len(c) <= 20
        assert sum(e["bytes"] for e in c) <= 50_000_000 - 5_000_000


def test_collect_without_flag_still_capped():
    entries = [{"page_id": f"p{i}", "uri": f"u{i}", "bytes": 100}
               for i in range(21)]
    with pytest.raises(ReturnFailure):
        _collect_chunks({}, entries, base_total=0)


def test_collect_all_pages_requires_entry_bytes():
    with pytest.raises(ReturnFailure):
        _collect_chunks({"collect_all_pages": True},
                        [{"uri": "u0"}], base_total=0)


def test_collect_all_pages_single_oversized_page_fails():
    entries = [{"page_id": "big", "uri": "ub", "bytes": 60_000_000}]
    with pytest.raises(ReturnFailure):
        _collect_chunks({"collect_all_pages": True}, entries, base_total=0)


# ------------------------------------------------------------- verify_page


def test_verify_page_ok_and_mismatch(tmp_path):
    rows = [{"a": 1}, {"a": 2}]
    body = "\n".join(json.dumps(r) for r in rows).encode() + b"\n"
    p = tmp_path / "page-00001.jsonl"
    p.write_bytes(body)
    entry = {"page_id": "page-00001", "uri": "u",
             "bytes": len(body), "rows": 2,
             "sha256": hashlib.sha256(body).hexdigest()}
    out = verify_page(str(p), entry)
    assert out["ok"] is True
    assert out["rows"] == 2
    bad = verify_page(str(p), dict(entry, rows=3))
    assert bad["ok"] is False
    assert bad["mismatches"][0]["field"] == "rows"


# ------------------------------------------------------ recompute_aggregate


def test_recompute_aggregate_sum_and_where(tmp_path):
    rows = [
        _row("h1", 1, "off", n=10),
        _row("h1", 1, "ps_ship", n=4),
        _row("h2", 1, "off", n=8),
    ]
    pages = _write_pages(tmp_path, rows)
    out = recompute_aggregate(
        pages, "n", "sum", where={"hull_id": "h1"})
    assert out["ok"] is True
    assert out["value"] == 14
    assert out["rows_matched"] == 2
    out = recompute_aggregate(pages, "n", "mean")
    assert out["value"] == pytest.approx((10 + 4 + 8) / 3)
    out = recompute_aggregate(
        pages, "n", "sum", where={"hull_id": "nope"})
    assert out["ok"] is False
    assert out["rows_matched"] == 0


def test_recompute_aggregate_rejects_non_numeric(tmp_path):
    rows = [_row("h1", 1, "off", n="not-a-number")]
    pages = _write_pages(tmp_path, rows)
    with pytest.raises(ValueError):
        recompute_aggregate(pages, "n", "sum")


# -------------------------------------------------------- paired_contrast


def test_paired_contrast_finds_both_arms(tmp_path):
    rows = [
        _row("h1", 7, "off", ar=0.30),
        _row("h1", 7, "ps_ship", ar=0.10),
        _row("h1", 8, "off", ar=0.50),
        _row("h2", 7, "off", ar=0.99),
    ]
    pages = _write_pages(tmp_path, rows)
    out = paired_contrast(pages, "h1", 7, "ar")
    assert out["ok"] is True
    assert out["arms"]["off"]["value"] == 0.30
    assert out["arms"]["ps_ship"]["value"] == 0.10
    assert out["delta"] == pytest.approx(-0.20)


def test_paired_contrast_missing_arm_is_not_ok(tmp_path):
    rows = [_row("h1", 7, "off", ar=0.30)]
    pages = _write_pages(tmp_path, rows)
    out = paired_contrast(pages, "h1", 7, "ar")
    assert out["ok"] is False
    assert out["missing_arms"] == ["ps_ship"]
