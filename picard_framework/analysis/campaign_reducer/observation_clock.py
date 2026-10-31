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
from .rows import ReductionContext, SourceSpec, canonical_json, row_id

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


def _observatory_fields(
    values: dict, prov: dict, doc: Any, window: str
) -> list[str]:
    """Timeseries-derived observation/clock fields.

    Every emitted value carries provenance labels — member, native
    path, the report ``category`` and ``origin`` from the contract, the
    ``clock`` (epoch index on ``natural_history_clock`` units), and the
    ``observation_window`` actually scanned. A threshold never crossed
    inside the retained window emits ``null`` +
    ``not_crossed_in_window`` (distinct from ``timeseries_absent`` and
    from ``missing``).
    """
    missing: list[str] = []
    ts, absent = _series(doc)
    n_rows = len(ts)

    def put(col: str, value: Any, status: str, f: dict) -> None:
        values[col] = value
        prov[col] = {
            "member": "summary.json",
            "native_path": "/timeseries",
            "status": status,
            "clock": "epoch index on natural_history_clock units",
            "observation_window": window,
        }
        for label in ("category", "role", "origin"):
            if f.get(label) is not None:
                prov[col][label] = f[label]

    for f in profile()["observation_fields"]:
        col = f["column"]
        derive = f["derive"]
        if absent is not None:
            put(col, None, absent, f)
            missing.append(col)
            continue
        if derive == "first_epoch":
            put(col, ts[0].get("epoch"), "observed", f)
        elif derive == "last_epoch":
            put(col, ts[-1].get("epoch"), "observed", f)
        elif derive == "row_count":
            put(col, n_rows, "observed", f)
        elif derive == "contiguous":
            epochs = [e.get("epoch") for e in ts]
            ok = epochs == list(range(n_rows))
            put(col, ok, "observed", f)
        elif derive == "coverage":
            den = values.get(f.get("denominator", ""))
            if first_paper._finite_num(den) and den:
                put(col, n_rows / den, "observed", f)
            else:
                put(col, None, "missing", f)
                missing.append(col)
        elif derive == "last_value":
            v = ts[-1].get(f["ts_key"])
            put(col, v, "observed" if v is not None else "missing", f)
            if v is None:
                missing.append(col)
        elif derive == "first_gt0":
            hit = next(
                (
                    e.get("epoch")
                    for e in ts
                    if first_paper._finite_num(e.get(f["ts_key"]))
                    and e[f["ts_key"]] > 0
                ),
                None,
            )
            put(
                col,
                hit,
                "observed" if hit is not None else "not_crossed_in_window",
                f,
            )
        elif derive == "first_any_flag":
            keys = f.get("ts_keys") or []
            hit = next(
                (
                    e.get("epoch")
                    for e in ts
                    if any(e.get(k) for k in keys)
                ),
                None,
            )
            put(
                col,
                hit,
                "observed" if hit is not None else "not_crossed_in_window",
                f,
            )
        elif derive == "first_status_in":
            wanted = set(f.get("values") or [])
            hit = next(
                (
                    e.get("epoch")
                    for e in ts
                    if e.get(f["ts_key"]) in wanted
                ),
                None,
            )
            put(
                col,
                hit,
                "observed" if hit is not None else "not_crossed_in_window",
                f,
            )
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


def _scan_agreement_checks(
    values: dict, prov: dict, fields_prov: dict, hit
) -> list[str]:
    """Cross-source agreement between scanner counters and our own."""
    missing_cols: list[str] = []
    for check in profile().get("scan_agreement_checks") or []:
        col = check["column"]
        scan_v = values.get(check["scan_column"])
        own = values.get(check["own_column"])
        if check.get("own_compare") == "present":
            own = own is not None
        if scan_v is None or hit is None:
            values[col] = None
            status = (
                "scan_source_absent" if hit is None
                else "agreement_uncomputable"
            )
            missing_cols.append(col)
        elif check.get("own_compare") is None and own is None:
            values[col] = None
            status = "agreement_uncomputable"
            missing_cols.append(col)
        else:
            values[col] = scan_v == own
            status = (
                "agreement_consistent" if scan_v == own
                else "agreement_divergent"
            )
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
    if first_paper._finite_num(emitted) and first_paper._finite_num(
        declared
    ):
        clock = (
            "complete" if emitted == declared
            else "truncated" if emitted < declared
            else "overrun"
        )
    else:
        clock = "unknown"
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

    ts, absent = _series(doc)
    observed = values.get("observed_terminal_epoch")
    retained = values.get("retained_epoch_rows")
    if absent is None and first_paper._finite_num(retained) and (
        first_paper._finite_num(declared)
    ):
        obs_clock = (
            "complete" if retained >= declared
            else "truncated" if retained < declared
            else "overrun"
        )
    elif first_paper._finite_num(observed) and first_paper._finite_num(
        declared
    ):
        obs_clock = (
            "complete" if observed + 1 >= declared
            else "truncated"
        )
    else:
        obs_clock = "unknown"
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

    posted = hit["line"].get("posted") if hit else None
    if posted is True:
        posted_status = "posted"
    elif hit is not None:
        posted_status = "unposted"
    else:
        posted_status = "unknown"
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
    spec,
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
        for f in doc["scan_fields"]:
            col = f["column"]
            if hit is None:
                values[col] = None
                prov[col] = {
                    "member": None,
                    "source_key": None,
                    "native_path": f["native"],
                    "status": scan_status or "scan_source_absent",
                }
                missing.append(col)
            else:
                values[col] = hit["values"].get(col)
                prov[col] = {
                    "member": hit["prov"][col]["member"],
                    "source_key": hit["prov"][col]["source_key"],
                    "source_id": hit["source_id"],
                    "native_path": f["native"],
                    "status": hit["prov"][col]["status"],
                }
                if hit["prov"][col]["status"] == "missing":
                    missing.append(col)
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
            {
                "row_id": row_id("fpoc", ddoc.run_uid),
                "reduction_id": ctx.reduction_id,
                "run_uid": ddoc.run_uid,
                "source_id": src.source_id,
                "campaign_id": src.campaign_id,
                "cell_id": src.cell_id,
                "hull_id": src.hull_id,
                "seed": src.seed if src.seed is not None
                else values.get("seed"),
                "original_run_id": src.original_run_id,
                "engine_sha": src.engine_sha,
                "image_digest": src.image_digest,
                "source_uri": src.uri,
                "source_key": object_key,
                "member": member,
                "member_asset_id": ddoc.asset_id,
                "definition_version": doc["definition_version"],
                "definition_sha256": definition_sha256(),
                "values": values,
                "provenance": prov,
                "missing": sorted(set(missing)),
            }
        )
    return rows
