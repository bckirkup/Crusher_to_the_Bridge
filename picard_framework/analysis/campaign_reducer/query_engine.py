"""Bounded query engine over a committed catalog snapshot (ticket D2).

Implements the ``query`` operation of QUERY.schema.json: a bounded
projection/filter AST over TABLE_ROWS partitions — never SQL, never an
unbounded scan. Hard rules from CANONICAL_INTERFACE:

- Every page is written create-only under
  ``campaign/_derived/reducer/v1/queries/{query_id}/`` with a
  ``query_pages`` row and a final ``RECEIPT.json``.
- Continuation tokens bind ``(query_sha256, catalog_snapshot_id,
  last row key)``; a mismatch is a typed error, not a silent restart.
- Joins are declared and cardinality-checked: ``one_to_one`` and
  ``many_to_one`` verify right-side key uniqueness;
  ``one_to_many_explicit`` is admitted only when the query's ``grain``
  names the many side — anything that would silently multiply run-level
  replicate counts raises ``unsupported_join``.
- ``None``/missing fields participate in filters with tri-state
  semantics; ``eq`` against ``null`` is ``is_null``.
- Caps are honored: ``page_rows`` (contract cap 10000),
  ``max_export_rows``, ``max_export_bytes`` per page, ``page_rows``,
  and the ``scan_budget`` fields; an oversized row yields a
  ``ROW_TOO_LARGE`` entry with a narrower-column hint.
- Only ``completed`` may be claimed when every selected row shipped;
  anything else is qualified (``partial``/``budget_stopped``/``blocked``).
"""
from __future__ import annotations

import base64
import json
import math
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

from .catalog import Catalog, CatalogError, load_catalog, query_page_row, receipt_row
from .contracts import QUERY_SCHEMA, load
from .identity import sha256_hex
from .ledger import BudgetLedger
from .rows import canonical_json

_MAX_PAGE_ROWS = 10000
# Absolute server-side ceilings on request-declared export caps — a
# request can declare smaller caps, never larger (S6680).
_MAX_EXPORT_ROWS = 10_000_000
_MAX_EXPORT_BYTES = 1 << 30  # 1 GiB
_RUN_GRAIN_TABLES = frozenset(
    {"runs", "run_scalars", "metrics", "distributions", "weights"}
)


class QueryError(Exception):
    """Typed query failure -> typed outcome, never a silent fall-through."""

    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


@dataclass
class QueryOutcome:
    status: str  # completed | partial | budget_stopped | blocked
    query_id: str
    pages: list[dict] = field(default_factory=list)
    page_keys: list[str] = field(default_factory=list)
    next_cursor: dict | None = None
    complete: bool = False
    errors: list[dict] = field(default_factory=list)
    scanned_rows: int = 0
    scanned_bytes: int = 0
    receipt: dict | None = None


# ---------------------------------------------------------------- filters


def _eval_bool_op(op: str, arg: Any, row: dict) -> bool | None:
    if op == "and":
        vals = [_eval_filter(n, row) for n in arg]
        if all(v is True for v in vals):
            return True
        return False if any(v is False for v in vals) else None
    if op == "or":
        vals = [_eval_filter(n, row) for n in arg]
        if any(v is True for v in vals):
            return True
        return None if any(v is None for v in vals) else False
    inner = _eval_filter(arg, row)  # op == "not"
    return None if inner is None else not inner


def _cmp_eq(v: Any, target: Any) -> bool:
    return v == target if target is not None or v is not None else True


def _cmp_ne(v: Any, target: Any) -> bool | None:
    if target is None:
        return v is not None
    return v != target if v is not None else None


def _cmp_in(v: Any, target: Any) -> bool:
    return (v in target) if v is not None else (None in target)


def _eval_cmp(op: str, v: Any, target: Any) -> bool | None:
    """Tri-state field-vs-literal comparison (None propagates)."""
    if op == "eq":
        return _cmp_eq(v, target)
    if op == "ne":
        return _cmp_ne(v, target)
    if op == "in":
        return _cmp_in(v, target)
    if v is None or target is None:
        return None
    if op == "lt":
        return v < target
    if op == "le":
        return v <= target
    if op == "gt":
        return v > target
    return v >= target  # op == "ge"


def _eval_filter(node: Any, row: dict) -> bool | None:
    """Tri-state filter eval: True / False / None (unknown)."""
    if not isinstance(node, dict) or len(node) != 1:
        raise QueryError("invalid_filter", f"filter node {node!r} is not a single-key op")
    op, arg = next(iter(node.items()))
    if op in ("and", "or", "not"):
        return _eval_bool_op(op, arg, row)
    if op == "is_null":
        return row.get(arg) is None
    if op not in ("eq", "ne", "in", "lt", "le", "gt", "ge"):
        raise QueryError("invalid_filter", f"unknown filter op {op!r}")
    field_, *rest = arg
    return _eval_cmp(op, row.get(field_), rest[0])


def _apply_filters(rows: list[dict], filters: dict | None) -> list[dict]:
    if not filters:
        return list(rows)
    return [r for r in rows if _eval_filter(filters, r) is True]


# ------------------------------------------------------------------ joins


def _join_key(row: dict, cols: list[str]) -> tuple:
    return tuple(row.get(c) for c in cols)


def _join_one(rows, index, on, table, card) -> list[dict]:
    dup = [k for k, v in index.items() if len(v) > 1]
    if dup:
        raise QueryError(
            "unsupported_join",
            f"{card} join to {table} has {len(dup)} duplicated keys",
        )
    return [
        {**r, **{_qualify(table, k2): v2 for k2, v2 in match[0].items()
                 if k2 not in on}}
        for r in rows
        for match in [index.get(_join_key(r, on), [])]
        if match
    ]


def _join_many(rows, index, on, table, grain) -> list[dict]:
    if grain not in (table, "explicit"):
        raise QueryError(
            "unsupported_join",
            f"one_to_many join to {table} would multiply the "
            f"{grain or 'run'} grain; declare the many-side grain "
            "or pre-aggregate",
        )
    return [
        {**r, **{_qualify(table, k2): v2 for k2, v2 in r2.items()
                 if k2 not in on}}
        for r in rows
        for r2 in index.get(_join_key(r, on), [])
    ]


def _apply_joins(query: dict, catalog: Catalog, rows: list[dict]) -> list[dict]:
    for join in query.get("joins") or []:
        table = join["table"]
        on = list(join.get("on") or [])
        card = join.get("cardinality")
        if not on:
            raise QueryError("unsupported_join", f"join to {table} has no 'on'")
        index: dict[tuple, list[dict]] = {}
        for r in catalog.rows(table):
            index.setdefault(_join_key(r, on), []).append(r)
        if card in ("one_to_one", "many_to_one"):
            rows = _join_one(rows, index, on, table, card)
        elif card == "one_to_many_explicit":
            rows = _join_many(rows, index, on, table, query.get("grain"))
        else:
            raise QueryError("unsupported_join", f"cardinality {card!r}")
    return rows


def _qualify(table: str, field_: str) -> str:
    return f"{table}__{field_}"


# ---------------------------------------------------------------- ordering


def _order(rows: list[dict], order_by: list[str]) -> list[dict]:
    """Deterministic ordering: requested keys then ``row_id`` tiebreak."""

    def key(r: dict) -> tuple:
        parts = []
        for spec in order_by or []:
            field_ = spec.lstrip("+-")
            v = r.get(field_)
            if spec.startswith("-"):
                parts.append((v is None, _desc_key(v)))
            else:
                parts.append((v is None, _sort_key(v)))
        parts.append((False, (1, str(r.get("row_id") or ""))))
        return tuple(parts)

    return sorted(rows, key=key)


def _sort_key(v: Any) -> tuple:
    if v is None:
        return (2, "")
    if isinstance(v, bool):
        return (1, int(v))
    if isinstance(v, (int, float)):
        return (0, float(v))
    return (1, str(v))


def _desc_key(v: Any) -> tuple:
    t, k = _sort_key(v)
    if isinstance(k, float):
        return (t, -k)
    if isinstance(k, int):
        return (t, -k)
    return (t, "".join(chr(0x10FFFF - ord(c)) for c in str(k)))


# -------------------------------------------------------------- statistics


def _numeric(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _groups(rows: list[dict], dims: list[str]) -> dict[tuple, list[dict]]:
    out: dict[tuple, list[dict]] = {}
    for r in rows:
        out.setdefault(tuple(r.get(d) for d in dims), []).append(r)
    return out


def _stat_rows(query: dict, rows: list[dict]) -> list[dict]:
    stat = query.get("statistic", "exact_rows")
    dims = list(query.get("group_by") or [])
    if stat == "exact_rows":
        return rows
    if stat in ("cross_tab", "joint_support"):
        return _grouped(query, rows, dims, _count_rows)
    if stat == "exact_ecdf":
        return _ecdf_rows(query, rows, dims)
    if stat == "mean":
        return _grouped(query, rows, dims, _mean_row)
    if stat == "pooled_rate":
        return _grouped(query, rows, dims, _pooled_rate_row)
    if stat == "quantile":
        return _grouped(query, rows, dims, _quantile_rows)
    if stat == "covariance":
        return _grouped(query, rows, dims, _covariance_row)
    if stat in ("survival", "competing_risk"):
        return _riskset_rows(query, rows, dims, stat)
    raise QueryError(
        "unsupported_statistic",
        f"statistic {stat!r} is declared but not implemented; "
        "typed unsupported rather than approximated",
    )


def _grouped(query, rows, dims, fn) -> list[dict]:
    out = []
    for key, members in sorted(
        _groups(rows, dims).items(), key=lambda kv: str(kv[0])
    ):
        out.extend(fn(query, key, dims, members))
    return out


def _count_rows(query, key, dims, members) -> list[dict]:
    return [
        {
            "row_id": f"agg-{sha256_hex(canonical_json(key).encode())[:12]}",
            "group_json": dict(zip(dims, key)),
            "n": len(members),
        }
    ]


def _mean_row(query, key, dims, members) -> list[dict]:
    vals = [_numeric(m.get("value")) for m in members]
    vals = [v for v in vals if v is not None]
    return [
        {
            "row_id": f"agg-{sha256_hex(canonical_json(key).encode())[:12]}",
            "group_json": dict(zip(dims, key)),
            "mean": statistics.fmean(vals) if vals else None,
            "n": len(vals),
        }
    ]


def _pooled_rate_row(query, key, dims, members) -> list[dict]:
    num = sum(_numeric(m.get("numerator")) or 0.0 for m in members)
    den = sum(_numeric(m.get("denominator")) or 0.0 for m in members)
    return [
        {
            "row_id": f"agg-{sha256_hex(canonical_json(key).encode())[:12]}",
            "group_json": dict(zip(dims, key)),
            "numerator": num,
            "denominator": den,
            "value": (num / den) if den else None,
        }
    ]


def _quantile_rows(query, key, dims, members) -> list[dict]:
    vals = sorted(
        v for v in (_numeric(m.get("value")) for m in members) if v is not None
    )
    out = []
    for p in (0.25, 0.5, 0.75):
        q = _inverse_ecdf(vals, p)
        out.append(
            {
                "row_id": f"agg-{sha256_hex(canonical_json([*key, p]).encode())[:12]}",
                "group_json": dict(zip(dims, key)),
                "quantile": p,
                "value": q,
                "n": len(vals),
            }
        )
    return out


def _inverse_ecdf(vals: list[float], p: float) -> float | None:
    """Smallest support value whose empirical CDF is >= p (step rule)."""
    if not vals:
        return None
    idx = max(0, math.ceil(p * len(vals)) - 1)
    return vals[idx]


def _covariance_row(query, key, dims, members) -> list[dict]:
    xs = [_numeric(m.get("numerator")) for m in members]
    ys = [_numeric(m.get("denominator")) for m in members]
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    cov = None
    if len(pairs) > 1:
        mx = statistics.fmean(p[0] for p in pairs)
        my = statistics.fmean(p[1] for p in pairs)
        cov = statistics.fmean(
            (p[0] - mx) * (p[1] - my) for p in pairs
        ) * len(pairs) / (len(pairs) - 1)
    return [
        {
            "row_id": f"agg-{sha256_hex(canonical_json(key).encode())[:12]}",
            "group_json": dict(zip(dims, key)),
            "covariance": cov,
            "n": len(pairs),
        }
    ]


def _ecdf_rows(_query, rows, dims) -> list[dict]:
    out = []
    for key, members in sorted(
        _groups(rows, dims).items(), key=lambda kv: str(kv[0])
    ):
        vals = sorted(
            v
            for v in (_numeric(m.get("value")) for m in members)
            if v is not None
        )
        n_missing = len(members) - len(vals)
        total = len(vals)
        for i, v in enumerate(vals):
            out.append(
                {
                    "row_id": f"ecdf-{sha256_hex(canonical_json([*key, i]).encode())[:12]}",
                    "group_json": dict(zip(dims, key)),
                    "support_value": v,
                    "mass_count": 1,
                    "weight_sum": 1.0,
                    "cdf": (i + 1) / total if total else None,
                    "n_eligible": len(members),
                    "n_observed": total,
                    "n_missing": n_missing,
                }
            )
    return out


def _riskset_rows(_query, rows, dims, stat) -> list[dict]:
    """Risk-set accounting for survival/competing_risk.

    Emits per (group, endpoint) risk-set rows: entries, exact events,
    censored counts by censor_type, and the KM step survival for the
    exact+right subset only — interval/left censored subjects are
    counted, never collapsed into the KM denominator.
    """
    out = []
    for key, members in sorted(
        _groups(rows, dims).items(), key=lambda kv: str(kv[0])
    ):
        endpoints = sorted(
            {m.get("endpoint_id") or "" for m in members} | {""}
        )
        for ep in endpoints:
            out.extend(_riskset_endpoint(key, members, ep, dims, stat))
    return out


def _riskset_endpoint(key, members, ep, dims, stat) -> list[dict]:
    sub = [m for m in members if (m.get("endpoint_id") or "") == ep]
    exact = [m for m in sub if m.get("censor_type") == "exact"]
    right = [m for m in sub if m.get("censor_type") == "right"]
    other = [
        m for m in sub if m.get("censor_type") not in ("exact", "right")
    ]
    km_rows = exact + right
    times = sorted({_t_obs(m) for m in km_rows})
    surv = 1.0
    out = []
    for t in times:
        at = [m for m in km_rows if _t_obs(m) >= t]
        d = sum(
            1 for m in at
            if m.get("censor_type") == "exact" and _t_obs(m) == t
        )
        risk = len(at)
        if risk:
            surv *= 1 - d / risk
        out.append(
            {
                "row_id": f"rs-{sha256_hex(canonical_json([*key, ep, t]).encode())[:12]}",
                "group_json": dict(zip(dims, key)),
                "endpoint_id": ep or None,
                "time_hours": t,
                "n_at_risk": risk,
                "n_event": d,
                "n_censored_other": len(other),
                "survival": surv if stat == "survival" else None,
            }
        )
    return out


def _t_obs(m: dict) -> float:
    return m.get("upper_hours") or m.get("exit_hours") or 0.0


# ----------------------------------------------------------------- cursor


def _encode_cursor(query_sha: str, snapshot_id: str, last_row_id: str | None,
                   seq: int) -> str:
    doc = {
        "v": 1,
        "q": query_sha,
        "s": snapshot_id,
        "k": last_row_id,
        "n": seq,
    }
    return base64.urlsafe_b64encode(
        canonical_json(doc).encode()
    ).decode().rstrip("=")


def _decode_cursor(token: str) -> dict:
    try:
        pad = "=" * (-len(token) % 4)
        return json.loads(base64.urlsafe_b64decode(token + pad))
    except ValueError as exc:
        raise QueryError("cursor_invalid", f"continuation token undecodable: {exc}")


# ----------------------------------------------------------------- driver


def _validate_query(query: dict) -> None:
    import jsonschema

    schema = load(QUERY_SCHEMA)
    try:
        jsonschema.validate(query, schema)
    except jsonschema.ValidationError as exc:
        raise QueryError("invalid_contract", exc.message[:300])


def run_query(
    query: dict,
    store,
    ledger: BudgetLedger,
    *,
    commit_key: str,
    reduction_id: str = "",
    clock=None,
    write_pages: bool = True,
) -> QueryOutcome:
    """Execute one bounded query against a COMMIT-frozen catalog."""
    clock = clock or time.monotonic
    _validate_query(query)
    # The token is transport, not query identity: hash without it so a
    # resumed query validates against the cursor that issued it.
    q_doc = dict(query)
    q_doc["continuation_token"] = None
    q_sha = sha256_hex(canonical_json(q_doc).encode())
    # Each export invocation (including a resume) is its own create-only
    # query run; the cursor still binds the token-stripped q_sha.
    query_id = (
        query.get("query_id")
        or f"q-{sha256_hex(canonical_json(query).encode())[:16]}"
    )
    out = QueryOutcome(status="blocked", query_id=query_id)
    start_cursor = _resume_cursor(query, q_sha)
    try:
        catalog = load_catalog(store, commit_key)
    except CatalogError as exc:
        out.errors.append({"kind": exc.kind, "detail": exc.detail})
        return out
    if catalog.snapshot_id != query.get("catalog_snapshot_id"):
        out.errors.append(
            {
                "kind": "snapshot_mismatch",
                "detail": f"query wants {query.get('catalog_snapshot_id')} "
                f"but commit is {catalog.snapshot_id}",
            }
        )
        return out
    if start_cursor and start_cursor["s"] != catalog.snapshot_id:
        out.errors.append({"kind": "cursor_invalid", "detail": "snapshot changed"})
        return out

    scan = _ScanBudget(query, clock)
    rows = _select(query, catalog, out, scan)
    if scan.stopped:
        out.status = "budget_stopped"
        out.errors.append(scan.error)
    try:
        rows = _apply_filters(rows, query.get("filters"))
        rows = _apply_joins(query, catalog, rows)
        rows = _order(rows, list(query.get("order_by") or []))
        if start_cursor:
            rows = _after(rows, start_cursor["k"])
        result_rows = _stat_rows(query, rows)
    except QueryError as exc:
        out.errors.append({"kind": exc.kind, "detail": exc.detail})
        return out
    result_rows = _project(result_rows, query.get("projection"))
    _paginate(query, query_id, q_sha, catalog.snapshot_id, result_rows,
              store, ledger, out, start_cursor, write_pages, reduction_id)
    if scan.stopped:
        out.complete = False
        out.status = "budget_stopped"
    elif out.status == "blocked":
        out.status = "completed" if out.complete else "partial"
    return out


def _resume_cursor(query: dict, q_sha: str) -> dict | None:
    token = query.get("continuation_token")
    if not token:
        return None
    cur = _decode_cursor(token)
    if cur.get("q") != q_sha:
        raise QueryError("cursor_invalid", "query changed since token issued")
    return cur


def _after(rows: list[dict], last_row_id: str | None) -> list[dict]:
    if last_row_id is None:
        return rows
    for i, r in enumerate(rows):
        if r.get("row_id") == last_row_id:
            return rows[i + 1 :]
    raise QueryError("cursor_invalid", f"last row key {last_row_id} not in snapshot")


class _ScanBudget:
    """Per-query scan caps from scan_budget, charged to the ledger too."""

    def __init__(self, query: dict, clock) -> None:
        sb = query.get("scan_budget") or {}
        self.max_scan_bytes = sb.get("max_scan_bytes")
        self.max_wall_seconds = sb.get("max_wall_seconds")
        self.max_cost_usd = sb.get("max_cost_usd")
        self.clock = clock
        self.start = clock()
        self.bytes = 0
        self.stopped = False
        self.error: dict | None = None

    def charge(self, bytes_: int) -> None:
        self.bytes += bytes_
        if self.max_scan_bytes is not None and self.bytes > self.max_scan_bytes:
            self.stopped = True
            self.error = {
                "kind": "budget_stopped",
                "detail": "max_scan_bytes exceeded",
            }
        elif (
            self.max_wall_seconds is not None
            and self.clock() - self.start > self.max_wall_seconds
        ):
            self.stopped = True
            self.error = {
                "kind": "budget_stopped",
                "detail": "max_wall_seconds exceeded",
            }


def _select(query: dict, catalog: Catalog, out: QueryOutcome,
            scan: _ScanBudget) -> list[dict]:
    table = query["source_table"]
    bytes_scanned = sum(
        e.get("bytes_stored") or 0
        for e in catalog.partitions
        if e.get("table_name") == table
    )
    scan.charge(bytes_scanned)
    rows = catalog.rows(table)
    metric_ids = query.get("metric_ids") or []
    if metric_ids:
        if table in ("run_scalars", "metrics", "epoch_metrics", "distributions"):
            keep = set(metric_ids)
            rows = [r for r in rows if r.get("metric_id") in keep]
    out.scanned_rows = len(rows)
    out.scanned_bytes = bytes_scanned
    return rows


def _project(rows: list[dict], projection: list[str] | None) -> list[dict]:
    if not projection:
        return rows
    keep = set(projection) | {"row_id"}
    return [{k: v for k, v in r.items() if k in keep} for r in rows]


def _paginate(
    query: dict,
    query_id: str,
    q_sha: str,
    snapshot_id: str,
    result_rows: list[dict],
    store,
    ledger: BudgetLedger,
    out: QueryOutcome,
    start_cursor: dict | None,
    write_pages: bool,
    reduction_id: str,
) -> None:
    page_rows = min(int(query.get("page_rows") or _MAX_PAGE_ROWS), _MAX_PAGE_ROWS)
    max_export_rows = query.get("max_export_rows")
    max_export_bytes = query.get("max_export_bytes") or 5 * 1024 * 1024
    seq = (start_cursor or {}).get("n") or 0
    emitted = 0
    oversized: list[dict] = []
    i = 0
    while i < len(result_rows):
        page, i, emitted = _fill_page(
            result_rows, i, emitted,
            page_rows, max_export_rows, max_export_bytes, oversized,
        )
        if not page:
            break
        seq += 1
        # Only exhausting the selection is final; a cap stop is resumable.
        final = i >= len(result_rows)
        _write_page(
            page, seq, final, query_id, q_sha, snapshot_id,
            reduction_id, store, ledger, out,
            (len(result_rows), emitted), oversized, write_pages,
        )
        if final:
            break
    out.complete = i >= len(result_rows) and not oversized
    if oversized:
        out.errors.append(
            {"kind": "row_too_large", "detail": f"{len(oversized)} rows over page cap"}
        )
    if write_pages:
        _write_query_tail(query_id, reduction_id, q_sha, snapshot_id, out, store)


def _fill_page(
    result_rows, i, emitted,
    page_rows, max_export_rows, max_export_bytes, oversized,
) -> tuple[list[dict], int, int]:
    """Assemble one page within the row/byte caps; collect oversized rows."""
    page_rows = min(int(page_rows), _MAX_PAGE_ROWS)
    if max_export_rows is not None:
        max_export_rows = min(int(max_export_rows), _MAX_EXPORT_ROWS)
    max_export_bytes = min(float(max_export_bytes), _MAX_EXPORT_BYTES)
    page = []
    page_bytes = 0
    n = i
    for idx in range(i, len(result_rows)):
        if len(page) >= page_rows:
            break
        if max_export_rows is not None and emitted >= max_export_rows:
            break
        row = result_rows[idx]
        size = len(canonical_json(row).encode())
        if size > max_export_bytes:
            oversized.append(
                {
                    "row_id": row.get("row_id"),
                    "bytes": size,
                    "outcome": "ROW_TOO_LARGE",
                    "hint": "request a narrower projection",
                }
            )
            n = idx + 1
            continue
        if page_bytes + size > max_export_bytes and page:
            break
        page.append(row)
        page_bytes += size
        emitted += 1
        n = idx + 1
    return page, n, emitted


def _write_page(
    page, seq, final, query_id, q_sha, snapshot_id,
    reduction_id, store, ledger, out,
    selected_emitted: tuple[int, int], oversized, write_pages,
) -> str:
    """Write one create-only page object plus its query_pages row."""
    n_selected, emitted = selected_emitted
    cursor_doc = None if final else {
        "token": _encode_cursor(
            q_sha, snapshot_id, page[-1].get("row_id"), seq
        )
    }
    body = b"".join(
        (canonical_json(r) + "\n").encode() for r in page
    )
    key = f"campaign/_derived/reducer/v1/queries/{query_id}/page-{seq:05d}.jsonl"
    if write_pages:
        store.put_idempotent(key, body)
        ledger.charge("max_api_calls_total", 1, "page put")
        ledger.charge("max_output_bytes", len(body), key)
    page_doc = query_page_row(
        reduction_id=reduction_id,
        query_id=query_id,
        page_id=f"page-{seq:05d}",
        snapshot_id=snapshot_id,
        query_sha256=q_sha,
        uri=key,
        sha256=sha256_hex(body),
        returned_rows=len(page),
        scanned=(out.scanned_rows, out.scanned_bytes),
        complete=final and not out.errors,
        next_cursor=cursor_doc,
        selection_counts={"selected": n_selected, "emitted": emitted},
        oversized_rows=oversized,
    )
    out.pages.append(page_doc)
    out.page_keys.append(key)
    out.next_cursor = cursor_doc
    return key


def _write_query_tail(query_id, reduction_id, _q_sha, snapshot_id,
                      out: QueryOutcome, store) -> None:
    pages_key = (
        f"campaign/_derived/reducer/v1/queries/{query_id}/query_pages.jsonl"
    )
    store.put_idempotent(
        pages_key,
        b"".join(
            (canonical_json(p) + "\n").encode() for p in out.pages
        ),
    )
    receipt = receipt_row(
        reduction_id=reduction_id,
        request_id=query_id,
        receipt_id=f"receipt-{query_id}",
        status=out.status if out.status != "blocked" else "partial",
        catalog_uri="",
        catalog_sha256=snapshot_id,
        budget={},
        error=out.errors[0] if out.errors else None,
        continuation=out.next_cursor,
        created_utc="",
        receipt_uri=f"campaign/_derived/reducer/v1/queries/{query_id}/RECEIPT.json",
        receipt_sha256="",
    )
    body = json.dumps(receipt, sort_keys=True, indent=2).encode()
    receipt["receipt_sha256"] = sha256_hex(body)
    store.put_idempotent(
        receipt["receipt_uri"], json.dumps(receipt, sort_keys=True, indent=2).encode()
    )
    out.receipt = receipt
