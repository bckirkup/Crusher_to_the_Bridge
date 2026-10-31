"""``first_paper_scalar`` extraction profile (first-paper data access task).

One wide ``first_paper_vectors`` row per selected actual execution:
``summary.json``-only member reads, a declared field projection with
per-field provenance (source key + member + producing-definition
version), and explicit missingness — a field that is absent emits
``null`` with status ``missing`` and a recomputed pair with a missing or
zero denominator emits ``null`` and never borrows one. All-leaf
scalarization, distributions/ECDF materialization and census decode are
suppressed; the projection contract is the versioned definition
(``contracts/FIRST_PAPER_SCALAR.json``).

Optional ``source_role: "scan_rows"`` sources contribute the scan-row
fields (``posted`` and friends) joined onto each vector by the run
archive's object key (scan rows carry the zip key verbatim). The join
is full-key only — off and ps_ship arms share seeds within a hull, so a
``(hull, seed)`` fallback could bind the wrong arm's row; a full-key
miss instead emits the scan fields as ``scan_source_absent`` and an
index-level key collision as ``scan_key_conflict`` (never
first-row-wins). Scan-role sources process before run sources
deterministically and are not counted as executions.
"""
from __future__ import annotations

import json
from typing import Any

from . import contracts
from .rows import ReductionContext, SourceSpec, canonical_json, row_id

PROFILE_ID = "first_paper_scalar"
SCAN_ROLE = "scan_rows"

_POINTER_UNESCAPE = {"~1": "/", "~0": "~"}


def profile() -> dict:
    """The frozen projection contract for this profile."""
    return contracts.load(contracts.FIRST_PAPER_SCALAR)


def defaults() -> dict:
    """Spec defaults the profile imposes (request fields may widen)."""
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
    return contracts.sha256(contracts.FIRST_PAPER_SCALAR)


def _pointer_get(doc: Any, pointer: str) -> tuple[bool, Any]:
    """``/a/b`` lookup; (found, node) — null is found."""
    node = doc
    for part in pointer.strip("/").split("/"):
        for esc, real in _POINTER_UNESCAPE.items():
            part = part.replace(esc, real)
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return False, None
    return True, node


def _object_key(uri: str) -> str:
    if uri.startswith("s3://"):
        return uri.split("/", 3)[3] if uri.count("/") >= 3 else uri
    return uri.split("#", 1)[0]


def _field_value(kind: str, node: Any) -> Any:
    if kind == "json":
        return canonical_json(node)
    return node


def _domain_ok(domain: str, node: Any) -> bool:
    """Count/rate domain validation — bool/negative/nonfinite rejected."""
    if domain in ("count", "rate", "number"):
        if isinstance(node, bool) or not isinstance(node, (int, float)):
            return False
        if node != node or node in (float("inf"), float("-inf")):
            return False
        if domain in ("count", "rate") and node < 0:
            return False
    return True


def _project_fields(
    doc: Any,
    fields: list[dict],
    prov_base: dict,
) -> tuple[dict, dict, list[str]]:
    """Declared-field projection with explicit missingness."""
    values: dict[str, Any] = {}
    prov: dict[str, dict] = {}
    missing: list[str] = []
    for f in fields:
        col = f["column"]
        found, node = _pointer_get(doc, f["native"])
        if not found:
            values[col] = None
            status = "missing"
            missing.append(col)
        elif node is None:
            values[col] = None
            status = "null_emitted"
        elif not _domain_ok(f.get("domain", ""), node):
            values[col] = None
            status = "domain_invalid"
            missing.append(col)
        else:
            values[col] = _field_value(f["kind"], node)
            status = "exact_emitted"
        prov[col] = {**prov_base, "native_path": f["native"], "status": status}
    return values, prov, missing


def _recomputed_pairs(
    values: dict, prov: dict, fields_prov: dict, doc: dict
) -> list[str]:
    """Ratios only from valid matching pairs; never a borrowed denominator."""
    missing_cols: list[str] = []
    for pair in profile()["recomputed_pairs"]:
        col = pair["column"]
        num = values.get(pair["numerator"])
        den = values.get(pair["denominator"])
        if (
            isinstance(num, bool)
            or isinstance(den, bool)
            or not isinstance(num, (int, float))
            or not isinstance(den, (int, float))
            or not (num == num and den == den)
            or num in (float("inf"), float("-inf"))
            or den in (float("inf"), float("-inf"))
        ):
            status = "invalid_pair_missing_operand"
            missing_cols.append(col)
        elif den == 0:
            status = "invalid_pair_zero_denominator"
            missing_cols.append(col)
        else:
            values[col] = num / den
            status = "recomputed_pair"
        prov[col] = {
            "native_path": None,
            "member": "derived:pair",
            "operands": {
                "numerator": pair["numerator"],
                "denominator": pair["denominator"],
            },
            "operand_status": {
                "numerator": fields_prov[pair["numerator"]]["status"],
                "denominator": fields_prov[pair["denominator"]]["status"],
            },
            "status": status,
        }
        if status.startswith("invalid_pair"):
            values[col] = None
    return missing_cols


def _sum_checks(
    values: dict, prov: dict, fields_prov: dict
) -> list[str]:
    """Dict-member sums recomputed and compared against report totals."""
    missing_cols: list[str] = []
    for check in profile()["sum_checks"]:
        raw = values.get(check["dict_column"])
        total = values.get(check["total_column"])
        members = json.loads(raw) if isinstance(raw, str) else raw
        sum_col = check["sum_column"]
        role_totals = check.get("role_totals") or {}
        role_nested = isinstance(members, dict) and any(
            isinstance(v, dict) for v in members.values()
        )

        def _flat(d: dict) -> bool:
            return all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                and v == v and v not in (float("inf"), float("-inf"))
                for v in d.values()
            )

        if role_nested:
            flat_members = {}
            ok = isinstance(members, dict)
            for role, sub in (members or {}).items():
                if isinstance(sub, dict) and _flat(sub):
                    flat_members[role] = sub
                else:
                    ok = False
            role_sums = {r: sum(sub.values())
                         for r, sub in flat_members.items()}
            member_sum = sum(role_sums.values()) if ok else None
            roles_ok = ok and all(
                isinstance(values.get(role_totals.get(r, "")), (int, float))
                and not isinstance(values.get(role_totals.get(r, "")), bool)
                and role_sums[r] == values[role_totals[r]]
                for r in role_totals
            ) if role_totals else ok
            computable = (
                ok
                and member_sum is not None
                and isinstance(total, (int, float))
                and not isinstance(total, bool)
            )
            values[sum_col + "_by_role"] = (
                canonical_json(role_sums) if ok else None
            )
        else:
            member_sum = None
            computable = (
                isinstance(members, dict)
                and _flat(members)
                and isinstance(total, (int, float))
                and not isinstance(total, bool)
            )
            if computable:
                member_sum = sum(members.values())
            roles_ok = computable
            values[sum_col + "_by_role"] = None

        if not computable:
            values[sum_col] = None
            values[check["column"]] = None
            status = "sum_uncomputable"
            missing_cols.append(sum_col)
            missing_cols.append(check["column"])
        else:
            values[sum_col] = member_sum
            consistent = member_sum == total and roles_ok
            values[check["column"]] = consistent
            status = "sum_consistent" if consistent else "sum_divergent"
        for col in (sum_col, check["column"]):
            prov[col] = {
                "native_path": None,
                "member": "derived:sum_check",
                "operands": {
                    "members": check["dict_column"],
                    "total": check["total_column"],
                },
                "operand_status": {
                    "members": fields_prov[check["dict_column"]]["status"],
                    "total": fields_prov[check["total_column"]]["status"],
                },
                "status": status,
            }
    return missing_cols


def _status_columns(values, prov, doc, hit) -> list[str]:
    """Completion/follow-up/clock status from actual evidence.

    A readable archive is not a completed voyage: ``completion_status``
    is ``completed`` only when the summary decoded AND the epoch clock
    closed at the declared horizon. ``clock_status`` compares the
    emitted ``num_epochs`` against the declared
    ``parameters.num_epochs``; ``follow_up_status`` reads the scan
    row's ``posted`` flag. Any missing operand yields ``unknown``,
    never a guessed status.
    """
    missing: list[str] = []
    emitted = values.get("num_epochs")
    params = doc.get("parameters") or {}
    declared = params.get("num_epochs")
    if isinstance(emitted, (int, float)) and not isinstance(emitted, bool) \
            and isinstance(declared, (int, float)) \
            and not isinstance(declared, bool):
        if emitted == declared:
            clock = "complete"
        elif emitted < declared:
            clock = "truncated"
        else:
            clock = "overrun"
    else:
        clock = "unknown"
        missing.append("clock_status")
    values["clock_status"] = clock
    prov["clock_status"] = {
        "native_path": "/num_epochs + /parameters/num_epochs",
        "member": "derived:clock",
        "status": "recomputed" if clock != "unknown" else "unknown",
    }

    if clock == "complete":
        completion = "completed"
    elif clock in ("truncated", "overrun"):
        completion = clock
    else:
        completion = "unknown"
        missing.append("completion_status")
    values["completion_status"] = completion
    prov["completion_status"] = {
        "native_path": "derived:clock_status",
        "member": "derived:completion",
        "status": "recomputed" if completion != "unknown" else "unknown",
    }

    posted = hit["line"].get("posted") if hit else None
    if posted is True:
        follow = "posted"
    elif posted is False or posted is None and hit is not None:
        follow = "unposted"
    else:
        follow = "unknown"
        missing.append("follow_up_status")
    values["follow_up_status"] = follow
    prov["follow_up_status"] = {
        "native_path": "scan:posted",
        "member": "derived:follow_up",
        "status": "recomputed" if follow != "unknown" else "unknown",
    }
    return missing


def absorb_scan_rows(acc, spec: SourceSpec, result) -> None:
    """Index a scan_rows-role source's per-line docs for the join."""
    fields = profile()["scan_fields"]
    for ddoc in result.docs:
        line = ddoc.doc
        key = line.get("key")
        values, prov, _ = _project_fields(
            line,
            fields,
            {
                "member": ddoc.member_path,
                "source_key": _object_key(spec.uri),
                "source_id": spec.source_id,
            },
        )
        bundle = {
            "values": values,
            "prov": prov,
            "line": line,
        }
        if key:
            if key in acc.scan_index:
                acc.scan_conflicts.append(
                    {
                        "kind": "scan_key_conflict",
                        "key": key,
                        "kept_source_id": acc.scan_index[key]["source_id"],
                        "dropped_source_id": spec.source_id,
                    }
                )
            else:
                acc.scan_index[key] = {
                    **bundle,
                    "source_id": spec.source_id,
                }


def _scan_lookup(
    acc,
    object_key: str,
    hull: Any,
    seed: Any,
) -> tuple[dict | None, str | None]:
    """Full-key scan-row lookup with key/hull/seed agreement.

    Returns ``(hit, conflict_kind)``. A full-key miss yields
    ``(None, None)`` — the caller emits ``scan_source_absent``. A hit
    whose row disagrees with the run's declared hull/seed yields
    ``(None, "scan_key_conflict")`` — the wrong arm's row must never
    bind (off and ps_ship share seeds within a hull), so the conflict is
    recorded and the scan fields emit typed-missing.
    """
    hit = acc.scan_index.get(object_key)
    if hit is None:
        return None, None
    line = hit["line"]
    if (
        (hull is not None and line.get("hull") != hull)
        or (seed is not None and line.get("seed") != seed)
    ):
        acc.scan_conflicts.append(
            {
                "kind": "scan_agreement_conflict",
                "key": object_key,
                "expected_hull": hull,
                "expected_seed": seed,
                "line_hull": line.get("hull"),
                "line_seed": line.get("seed"),
                "source_id": hit["source_id"],
            }
        )
        return None, "scan_agreement_conflict"
    return hit, None


def vector_rows(
    spec,
    src: SourceSpec,
    result,
    ctx: ReductionContext,
    acc,
) -> list[dict]:
    """One wide row per decoded ``summary.json`` doc of a run source."""
    doc = profile()
    object_key = _object_key(src.uri)
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
        values, prov, missing = _project_fields(
            ddoc.doc, doc["summary_fields"], {**summary_base}
        )
        missing += _recomputed_pairs(values, prov, prov, ddoc.doc)
        missing += _sum_checks(values, prov, prov)
        hit, scan_status = _scan_lookup(
            acc,
            object_key,
            values.get("platform_id") or src.hull_id,
            values.get("seed") or src.seed,
        )
        missing += _status_columns(values, prov, ddoc.doc, hit)
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
        rows.append(
            {
                "row_id": row_id("fpv", ddoc.run_uid),
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
