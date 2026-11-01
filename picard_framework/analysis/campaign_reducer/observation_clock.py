"""``first_paper_observation_clock`` extraction profile.

One wide ``first_paper_observation_clock_vectors`` row per selected
execution — the observation/clock sidecar joined by exact existing
execution/source identity (``source_key`` + ``run_uid``, never a
positional or first-row-wins join). Everything it emits is recoverable
from ``summary.json`` alone: report counts by role, the *observed*
terminal epoch and retained trajectory coverage (separate from the
configured ``num_epochs`` — the emitted top-level ``num_epochs`` equals
``meta.epochs`` = the configured horizon, never the observed one),
first-report and threshold-crossing times labelled with
category/clock/origin/window, scanner provenance, and typed
availability declarations for the fields the producing version never
serialized (per-role noise counts, etiologic/noise person-set overlap
and union).

Fields not saved emit ``null`` with a typed ``availability`` /
``reason_code`` — never a manufactured value, never an inference from
population proportions.
"""
from __future__ import annotations

from typing import Any

from . import contracts, first_paper
from .rows import ReductionContext, SourceSpec, canonical_json

PROFILE_ID = "first_paper_observation_clock"
SCAN_ROLE = "scan_rows"


def profile() -> dict:
    """The frozen projection contract for this profile."""
    return contracts.load(contracts.FIRST_PAPER_OBSERVATION_CLOCK)


def defaults() -> dict:
    doc = profile()
    return {
        "member_allowlist": tuple(doc["member_allowlist"]),
        "suppress_tables": frozenset(doc["suppress_tables"]),
        "emit_scalars": bool(doc["emit_scalars"]),
        "scan_role": doc["scan_role"],
    }


def definition_version() -> str:
    return profile()["definition_version"]


def definition_sha256() -> str:
    return contracts.sha256(contracts.FIRST_PAPER_OBSERVATION_CLOCK)


def _series(doc: Any) -> tuple[list, str | None]:
    """The retained per-epoch series; ``(rows, absent_reason)``."""
    ts = (doc or {}).get("timeseries")
    if isinstance(ts, list) and ts:
        return ts, None
    return [], "timeseries_absent"


def _put_obs_field(
    values: dict, prov: dict, window: str,
    col: str, value: Any, status: str, field: dict,
) -> None:
    """One observation column plus its provenance labels."""
    values[col] = value
    prov[col] = {
        "member": "summary.json",
        "native_path": "/timeseries",
        "status": status,
        "clock": "epoch index on natural_history_clock units",
        "observation_window": window,
    }
    for label in ("category", "role", "origin"):
        if field.get(label) is not None:
            prov[col][label] = field[label]


def _obs_epoch(value: Any, *, crossed: bool) -> tuple[Any, str, bool]:
    """``(value, status, missing)`` for a threshold that may never fire."""
    if crossed:
        status = "observed" if value is not None else "not_crossed_in_window"
        return value, status, False
    status = "observed" if value is not None else "missing"
    return value, status, value is None


def _derive_first_epoch(_field, ts, _n_rows, _values):
    return ts[0].get("epoch"), "observed", False


def _derive_last_epoch(_field, ts, _n_rows, _values):
    return ts[-1].get("epoch"), "observed", False


def _derive_row_count(_field, _ts, n_rows, _values):
    return n_rows, "observed", False


def _derive_contiguous(_field, ts, n_rows, _values):
    epochs = [row.get("epoch") for row in ts]
    return epochs == list(range(n_rows)), "observed", False


def _derive_coverage(field, _ts, n_rows, values):
    den = values.get(field.get("denominator", ""))
    if first_paper._finite_num(den) and den:
        return n_rows / den, "observed", False
    return None, "missing", True


def _derive_last_value(field, ts, _n_rows, _values):
    return _obs_epoch(ts[-1].get(field["ts_key"]), crossed=False)


def _derive_first_gt0(field, ts, _n_rows, _values):
    key = field["ts_key"]
    hit = next(
        (
            row.get("epoch")
            for row in ts
            if first_paper._finite_num(row.get(key)) and row[key] > 0
        ),
        None,
    )
    return _obs_epoch(hit, crossed=True)


def _derive_first_any_flag(field, ts, _n_rows, _values):
    keys = field.get("ts_keys") or []
    hit = next(
        (
            row.get("epoch")
            for row in ts
            if any(row.get(key) for key in keys)
        ),
        None,
    )
    return _obs_epoch(hit, crossed=True)


def _derive_first_status_in(field, ts, _n_rows, _values):
    wanted = set(field.get("values") or [])
    key = field["ts_key"]
    hit = next(
        (
            row.get("epoch")
            for row in ts
            if row.get(key) in wanted
        ),
        None,
    )
    return _obs_epoch(hit, crossed=True)


_OBS_DERIVE = {
    "first_epoch": _derive_first_epoch,
    "last_epoch": _derive_last_epoch,
    "row_count": _derive_row_count,
    "contiguous": _derive_contiguous,
    "coverage": _derive_coverage,
    "last_value": _derive_last_value,
    "first_gt0": _derive_first_gt0,
    "first_any_flag": _derive_first_any_flag,
    "first_status_in": _derive_first_status_in,
}


def _observatory_fields(
    values: dict, prov: dict, doc: Any, window: str,
    fields: list[dict] | None = None,
) -> list[str]:
    """Timeseries-derived observation/clock fields.

    Every emitted value carries provenance labels — member, native
    path, the report ``category`` and ``origin`` from the contract, the
    ``clock`` (epoch index on ``natural_history_clock`` units), and the
    ``observation_window`` actually scanned. A threshold never crossed
    inside the retained window emits ``null`` +
    ``not_crossed_in_window`` (distinct from ``timeseries_absent`` and
    from ``missing``). ``fields`` defaults to this profile's own
    ``observation_fields``; ``first_paper_scalar``/1.3.0 passes its
    compact observed-window subset through the same code path.
    """
    missing: list[str] = []
    ts, absent = _series(doc)
    n_rows = len(ts)
    spec_fields = (
        fields if fields is not None else profile()["observation_fields"]
    )
    for field in spec_fields:
        col = field["column"]
        if absent is not None:
            _put_obs_field(values, prov, window, col, None, absent, field)
            missing.append(col)
            continue
        derive = _OBS_DERIVE.get(field["derive"])
        if derive is None:
            continue
        value, status, is_missing = derive(field, ts, n_rows, values)
        _put_obs_field(values, prov, window, col, value, status, field)
        if is_missing:
            missing.append(col)
    return missing


def _equality_checks(
    values: dict, prov: dict, fields_prov: dict
) -> list[str]:
    """Two-operand equality — ts-vs-summary, ts-vs-derived agreement."""
    missing_cols: list[str] = []
    for check in profile()["equality_checks"]:
        col = check["column"]
        left = values.get(check["left"])
        right = values.get(check["right"])
        l_ok = left is not None
        r_ok = right is not None
        if l_ok and r_ok:
            values[col] = left == right
            status = (
                "agreement_consistent" if left == right
                else "agreement_divergent"
            )
        elif not l_ok and not r_ok:
            values[col] = True
            status = "both_absent_consistent"
        else:
            values[col] = None
            status = "agreement_uncomputable"
            missing_cols.append(col)
        prov[col] = {
            "native_path": None,
            "member": "derived:equality_check",
            "operands": {"left": check["left"], "right": check["right"]},
            "operand_status": {
                "left": fields_prov.get(check["left"], {}).get("status"),
                "right": fields_prov.get(check["right"], {}).get("status"),
            },
            "status": status,
        }
    return missing_cols


def _scan_agreement_value(check: dict, values: dict, hit):
    """``(column, value, status, missing)`` for one scan-agreement check."""
    col = check["column"]
    scan_v = values.get(check["scan_column"])
    own = values.get(check["own_column"])
    if check.get("own_compare") == "present":
        own = own is not None
    if scan_v is None or hit is None:
        status = (
            "scan_source_absent" if hit is None
            else "agreement_uncomputable"
        )
        return col, None, status, True
    if check.get("own_compare") is None and own is None:
        return col, None, "agreement_uncomputable", True
    status = (
        "agreement_consistent" if scan_v == own else "agreement_divergent"
    )
    return col, scan_v == own, status, False


def _scan_agreement_checks(
    values: dict, prov: dict, fields_prov: dict, hit
) -> list[str]:
    """Cross-source agreement between scanner counters and our own."""
    missing_cols: list[str] = []
    for check in profile().get("scan_agreement_checks") or []:
        col, value, status, missing = _scan_agreement_value(
            check, values, hit)
        values[col] = value
        if missing:
            missing_cols.append(col)
        prov[col] = {
            "native_path": None,
            "member": "derived:scan_agreement_check",
            "operands": {
                "scan": check["scan_column"],
                "own": check["own_column"],
            },
            "operand_status": {
                "scan": fields_prov.get(check["scan_column"], {}).get(
                    "status"
                ),
                "own": fields_prov.get(check["own_column"], {}).get(
                    "status"
                ),
            },
            "status": status,
        }
    return missing_cols


def _availability_fields(values: dict, prov: dict) -> None:
    """Declared-unavailable fields: null + typed availability evidence."""
    for f in profile()["availability_fields"]:
        col = f["column"]
        values[col] = None
        prov[col] = {
            "member": None,
            "native_path": None,
            "status": f["availability"],
            "availability": f["availability"],
            "reason_code": f["reason_code"],
            "evidence": f["evidence"],
        }


def _both_finite(left, right) -> bool:
    return first_paper._finite_num(left) and first_paper._finite_num(right)


def _eq_clock(left, right) -> str:
    """complete / truncated / overrun for an equality comparison."""
    if left == right:
        return "complete"
    if left < right:
        return "truncated"
    return "overrun"


def _ge_clock(span, declared) -> str:
    """complete when the retained span covers the declared horizon."""
    if span >= declared:
        return "complete"
    if span < declared:
        return "truncated"
    return "overrun"


def _configured_clock_status(emitted, declared) -> tuple[str, bool]:
    """``(label, missing)`` for configured-vs-configured ``clock_status``."""
    if _both_finite(emitted, declared):
        return _eq_clock(emitted, declared), False
    return "unknown", True


def _observed_clock_label(absent, retained, observed, declared) -> tuple[str, bool]:
    """``(label, missing)`` for the retained-span clock witness."""
    if absent is None and _both_finite(retained, declared):
        return _ge_clock(retained, declared), False
    if _both_finite(observed, declared):
        if observed + 1 >= declared:
            return "complete", False
        return "truncated", False
    return "unknown", True


def _posted_label(hit) -> tuple[str, bool]:
    """``(label, missing)`` for the scanner's own posted rollup."""
    posted = hit["line"].get("posted") if hit else None
    if posted is True:
        return "posted", False
    if hit is not None:
        return "unposted", False
    return "unknown", True


def _status_columns(values: dict, prov: dict, doc: Any, hit) -> list[str]:
    """Observation/scan status columns.

    ``clock_status`` is the configured-vs-configured comparison
    (emitted ``num_epochs`` equals ``parameters.num_epochs`` on every
    PS01 archive — the emitted value IS the configured horizon); it is
    retained labelled ``historical_evidence`` because it carries no
    observed-clock information. ``observed_clock_status`` compares the
    retained timeseries span against the configured horizon — the real
    clock witness. ``scan_posted_status`` is the scanner's own
    ``posted`` rollup (not follow-up-completeness evidence).
    """
    missing: list[str] = []
    emitted = values.get("num_epochs")
    declared = (doc.get("parameters") or {}).get("num_epochs")
    clock, clock_missing = _configured_clock_status(emitted, declared)
    if clock_missing:
        missing.append("clock_status")
    values["clock_status"] = clock
    prov["clock_status"] = first_paper._status_prov(
        "derived:clock", "/num_epochs + /parameters/num_epochs", clock)
    prov["clock_status"]["historical_evidence"] = True
    prov["clock_status"]["note"] = (
        "configured-vs-configured: the emitted num_epochs equals the "
        "declared horizon on every archive; carries no observed-clock "
        "information (see observed_clock_status)."
    )

    _ts, absent = _series(doc)
    observed = values.get("observed_terminal_epoch")
    retained = values.get("retained_epoch_rows")
    obs_clock, obs_missing = _observed_clock_label(
        absent, retained, observed, declared)
    if obs_missing:
        missing.append("observed_clock_status")
    values["observed_clock_status"] = obs_clock
    prov["observed_clock_status"] = first_paper._status_prov(
        "derived:observed_clock",
        "/timeseries rows + /parameters/num_epochs",
        obs_clock,
    )

    completion = {"complete": "completed"}.get(obs_clock, obs_clock)
    if completion == "unknown":
        missing.append("observed_completion_status")
    values["observed_completion_status"] = completion
    prov["observed_completion_status"] = first_paper._status_prov(
        "derived:observed_completion",
        "derived:observed_clock_status",
        completion,
    )

    posted_status, posted_missing = _posted_label(hit)
    if posted_missing:
        missing.append("scan_posted_status")
    values["scan_posted_status"] = posted_status
    prov["scan_posted_status"] = first_paper._status_prov(
        "derived:scan_posted", "scan:posted", posted_status)
    return missing


def absorb_scan_rows(acc, spec: SourceSpec, result) -> None:
    """Index this profile's scan fields for the full-key join."""
    first_paper.absorb_scan_rows(
        acc, spec, result, scan_fields=profile()["scan_fields"])


def vector_rows(
    _spec,
    src: SourceSpec,
    result,
    ctx: ReductionContext,
    acc,
) -> list[dict]:
    """One wide sidecar row per decoded ``summary.json`` doc."""
    doc = profile()
    object_key = first_paper._object_key(src.uri)
    rows = []
    for ddoc in result.docs:
        member = (ddoc.member_path or "").rsplit("/", 1)[-1]
        if member != doc["member_allowlist"][0]:
            continue
        summary_base = {
            "member": ddoc.member_path,
            "source_key": object_key,
            "source_id": src.source_id,
        }
        values, prov, missing = first_paper._project_fields(
            ddoc.doc, doc["summary_fields"], {**summary_base}
        )
        hit, scan_status = first_paper._scan_lookup(
            acc,
            object_key,
            values.get("platform_id") or src.hull_id,
            values.get("seed") or src.seed,
        )
        missing += first_paper._absorb_scan_fields(
            doc, hit, scan_status, values, prov)
        ts, absent = _series(ddoc.doc)
        window = (
            "unavailable"
            if absent
            else canonical_json(
                [
                    ts[0].get("epoch"),
                    ts[-1].get("epoch"),
                ]
            )
        )
        missing += _observatory_fields(values, prov, ddoc.doc, window)
        missing += _equality_checks(values, prov, prov)
        missing += _status_columns(values, prov, ddoc.doc, hit)
        missing += first_paper._sum_checks(values, prov, prov)
        missing += first_paper._operand_sum_checks(values, prov, prov)
        missing += _scan_agreement_checks(values, prov, prov, hit)
        _availability_fields(values, prov)
        rows.append(
            first_paper._row_envelope(
                "fpoc", ddoc, src, ctx, object_key, member, doc,
                values, prov, missing, definition_sha256())
        )
    return rows
