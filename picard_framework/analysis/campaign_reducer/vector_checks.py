"""Narrow, deterministic verification helpers for the published
``first_paper_vectors`` page set.

These are the check tools the delivery bundle ships so a verifier (Edison /
Kosmos) can CONFIRM a claim cheaply instead of trusting the precomputed
aggregate doc or decoding the source corpus. Each helper is a single-point
check with a documented cost bound:

- Input is the PUBLISHED page set only: local ``page-*.jsonl`` files from a
  bounded collect, plus their ``*.pages_manifest.json``. No helper reads
  run zips, summary members, or the source corpus.
- Cost bound per call: one linear pass over the pages handed in —
  O(total page bytes) read, O(1) extra memory (a matched row is kept only
  until the check resolves). ``paired_contrast`` keeps at most the two
  matched rows.
- Deterministic: no randomness, no wall-clock, no network. Same inputs →
  byte-identical check receipt.

Every helper returns a check receipt dict shaped::

    {"check": <name>, "ok": bool, ...check-specific fields...}

``ok`` is False on ANY disagreement — a missing row, a hash mismatch, a
declared-vs-observed count drift — never an exception for bad-but-valid
data. Exceptions are reserved for malformed inputs (unreadable page,
non-numeric field where a numeric op was asked).
"""

from __future__ import annotations

import hashlib
import json
import math
import os

_KIND = "crusher-reducer-vector-check/v1"


def _iter_rows(pages):
    """Yield (page_name, row) for every JSONL row across the given pages.

    ``pages`` is an iterable of filesystem paths to published
    ``page-*.jsonl`` files. Cost bound: each page is opened once, streamed
    line-by-line, closed; nothing seeks or re-reads.
    """
    for path in pages:
        name = os.path.basename(path)
        with open(path, "rb") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                yield name, json.loads(line)


def verify_page(page_path: str, manifest_entry: dict) -> dict:
    """Verify ONE published page against its manifest entry.

    Confirms byte count, sha256, and row count — the whole integrity check
    a verifier needs for one page, no decode beyond line counting.

    ``manifest_entry`` is the page's dict from the pages manifest
    (``page_id``, ``uri``, ``bytes``, ``rows``, ``sha256``).
    """
    body = open(page_path, "rb").read()
    observed_sha = hashlib.sha256(body).hexdigest()
    observed_rows = sum(1 for line in body.splitlines() if line.strip())
    declared_sha = manifest_entry.get("sha256")
    declared_bytes = manifest_entry.get("bytes")
    declared_rows = manifest_entry.get("rows")
    mismatches = []
    if declared_sha is not None and observed_sha != declared_sha:
        mismatches.append(
            {"field": "sha256", "declared": declared_sha,
             "observed": observed_sha})
    if declared_bytes is not None and len(body) != declared_bytes:
        mismatches.append(
            {"field": "bytes", "declared": declared_bytes,
             "observed": len(body)})
    if declared_rows is not None and observed_rows != declared_rows:
        mismatches.append(
            {"field": "rows", "declared": declared_rows,
             "observed": observed_rows})
    return {
        "check": "verify_page",
        "kind": _KIND,
        "ok": not mismatches,
        "page_id": manifest_entry.get("page_id"),
        "uri": manifest_entry.get("uri"),
        "sha256": observed_sha,
        "bytes": len(body),
        "rows": observed_rows,
        "mismatches": mismatches,
    }


def _numeric(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"values.{field} is not numeric in a scanned row: {value!r}")
    if not math.isfinite(value):
        raise ValueError(f"values.{field} is non-finite: {value!r}")
    return value


def _fold_aggregate(acc, op: str, value, matched):
    """One running accumulator step. ``count`` ignores ``value``."""
    if op == "count":
        return matched
    if op in ("sum", "mean"):
        return value if acc is None else acc + value
    if op == "min":
        return value if acc is None else min(acc, value)
    return value if acc is None else max(acc, value)


def _aggregate_result(
    *, ok, op, field, where, matched, scanned, pages_scanned, value,
    reason=None, sample_rows=None,
) -> dict:
    out = {
        "check": "recompute_aggregate", "kind": _KIND, "ok": ok,
        "op": op, "field": field, "where": where,
        "rows_matched": matched, "rows_scanned": scanned,
        "pages_scanned": pages_scanned,
        "value": value,
    }
    if ok:
        out["sample_rows"] = sample_rows
    else:
        out["reason"] = reason
    return out


def recompute_aggregate(pages, field: str, op: str,
                        where: dict | None = None) -> dict:
    """Recompute ONE aggregate over one ``values`` field.

    ``op`` is ``sum`` | ``count`` | ``mean`` | ``min`` | ``max``.
    ``where`` (optional) is equality predicates on TOP-LEVEL row fields
    (``hull_id``, ``cell_id``, ``seed``, ``run_uid``, ``reduction_id``, ...)
    — e.g. ``{"hull_id": "classic_cruise_1900"}``.

    Cost bound: single pass over the given pages, keeps only the running
    accumulator — O(page bytes) read, O(1) memory.
    """
    if op not in ("sum", "count", "mean", "min", "max"):
        raise ValueError(f"unsupported aggregate op: {op!r}")
    where = dict(where or {})
    matched = scanned = 0
    acc = None
    pages_scanned = 0
    last_page = None
    matched_refs = []
    for page, row in _iter_rows(pages):
        if page != last_page:
            last_page = page
            pages_scanned += 1
        scanned += 1
        if any(row.get(k) != v for k, v in where.items()):
            continue
        matched += 1
        if op != "count":
            value = _numeric((row.get("values") or {}).get(field), field)
        else:
            value = None
        acc = _fold_aggregate(acc, op, value, matched)
        if len(matched_refs) < 8:
            matched_refs.append(
                {"page": page, "run_uid": row.get("run_uid")})
    if matched == 0:
        return _aggregate_result(
            ok=False, op=op, field=field, where=where, matched=0,
            scanned=scanned, pages_scanned=pages_scanned, value=None,
            reason="no rows matched the predicates",
        )
    value = acc / matched if op == "mean" else acc
    return _aggregate_result(
        ok=True, op=op, field=field, where=where, matched=matched,
        scanned=scanned, pages_scanned=pages_scanned, value=value,
        sample_rows=matched_refs,
    )


def _arm_of(row: dict) -> str | None:
    cell = row.get("cell_id")
    if not isinstance(cell, str):
        return None
    if cell.endswith("_ps_ship"):
        return "ps_ship"
    if cell.endswith("_off"):
        return "off"
    return None


def paired_contrast(pages, hull_id: str, seed: int, field: str) -> dict:
    """Re-derive ONE off-vs-ps_ship paired contrast for (hull_id, seed).

    Finds the ``values[field]`` of the ``off``-arm row and the
    ``ps_ship``-arm row sharing ``hull_id`` + ``seed``, and returns both
    values and ``delta = ps_ship - off``. Pairing is by (hull, seed) ONLY —
    the same rule the cohort register declares.

    Cost bound: single pass, early-ends once both arms are found;
    keeps at most the two matched rows.
    """
    found: dict[str, dict] = {}
    scanned = 0
    pages_scanned = 0
    last_page = None
    for page, row in _iter_rows(pages):
        if page != last_page:
            last_page = page
            pages_scanned += 1
        scanned += 1
        if row.get("hull_id") != hull_id or row.get("seed") != seed:
            continue
        arm = _arm_of(row)
        if arm is None or arm in found:
            continue
        found[arm] = {
            "page": page,
            "run_uid": row.get("run_uid"),
            "cell_id": row.get("cell_id"),
            "value": _numeric(
                (row.get("values") or {}).get(field), field),
        }
        if len(found) == 2:
            break
    missing = [a for a in ("off", "ps_ship") if a not in found]
    receipt = {
        "check": "paired_contrast", "kind": _KIND,
        "ok": not missing,
        "hull_id": hull_id, "seed": seed, "field": field,
        "rows_scanned": scanned, "pages_scanned": pages_scanned,
        "arms": found,
        "missing_arms": missing,
    }
    if not missing:
        receipt["delta"] = found["ps_ship"]["value"] - found["off"]["value"]
        receipt["pair_rule"] = "within-hull seed match (off vs ps_ship)"
    else:
        receipt["reason"] = "paired row(s) not found in the supplied pages"
    return receipt
