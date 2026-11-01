"""Optional long-table extraction + parquet decode (ticket D2).

Base materialization emits the operational tables plus ``distributions``
and ``weights``. The scientific long tables are produced only when the
request names them — and only from decoded structure that actually
exists in the source documents. Nothing is fabricated: a member key the
adapter decoded but the doc does not carry produces no row, and a
requested structure absent from the doc produces a typed
``data_gaps.not_saved`` row instead.

Extraction is shape-driven, not family-driven: for each ``DecodedDoc``
the extractor looks for the declared array keys (``timeseries``,
``events``, ``agents``/``roster``, ``observations``, ``population``,
``mechanism_objects``) anywhere in the document and maps each element
onto the contract row shape, copying the whole element into the row's
``*_json`` payload so no field is silently dropped.
"""
from __future__ import annotations

import io
from typing import Any, Iterable

from .payloads import AdapterResult
from .rows import ReductionContext, SourceSpec, row_id

REQUESTABLE_TABLES: frozenset[str] = frozenset(
    {
        "epoch_metrics",
        "events",
        "event_participants",
        "times_to_event",
        "population_intervals",
        "agents",
        "memberships",
        "observations",
        "mechanism_objects",
        "metrics",
    }
)

# document key -> long table; checked at every dict node of each doc.
_ARRAY_KEYS: dict[str, str] = {
    "timeseries": "epoch_metrics",
    "epochs": "epoch_metrics",
    "epoch_metrics": "epoch_metrics",
    "epoch_series": "epoch_metrics",
    "events": "events",
    "agents": "agents",
    "roster": "agents",
    "observations": "observations",
    "mechanism_objects": "mechanism_objects",
    "objects": "mechanism_objects",
    "population": "population_intervals",
    "population_intervals": "population_intervals",
    "times_to_event": "times_to_event",
}

_SERIES_KIND = {
    "infected": "state",
    "susceptible": "state",
    "recovered": "state",
    "exposed": "state",
    "new_infections": "incidence",
    "incidence": "incidence",
    "cumulative": "cumulative",
    "attack_rate": "rate",
    "rate": "rate",
}


def _num(elem: Any, *keys: str) -> float | None:
    if isinstance(elem, dict):
        for k in keys:
            v = elem.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return float(v)
    return None


def _text(elem: Any, *keys: str) -> str | None:
    if isinstance(elem, dict):
        for k in keys:
            v = elem.get(k)
            if v is not None and not isinstance(v, (dict, list)):
                return str(v)
    return None


def _iter_arrays(doc: Any) -> Iterable[tuple[str, list]]:
    """Yield (array_key, elements) for declared keys at any dict node."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            if isinstance(v, list) and k in _ARRAY_KEYS:
                yield k, v
            yield from _iter_arrays(v)
    elif isinstance(doc, list):
        for item in doc:
            yield from _iter_arrays(item)


def _emit_elements(
    ddoc,
    key: str,
    elements: list,
    table: str,
    spec: SourceSpec,
    ctx: ReductionContext,
    seen: set[str],
) -> Iterable[dict]:
    for i, elem in enumerate(elements):
        if not isinstance(elem, dict):
            continue
        rows_out = _ELEMENT_EMITTERS.get(table, lambda *a: None)(
            elem, i, ddoc, spec, ctx, key
        )
        if rows_out is None:
            continue
        if isinstance(rows_out, dict):
            rows_out = [rows_out]
        for row in rows_out:
            if row["row_id"] in seen:
                continue
            seen.add(row["row_id"])
            yield row


def _add_unique(rows: list[dict], seen: set[str], additions) -> None:
    for row in additions:
        if row["row_id"] not in seen:
            seen.add(row["row_id"])
            rows.append(row)


def emit_long_tables(
    result: AdapterResult,
    spec: SourceSpec,
    ctx: ReductionContext,
    requested: Iterable[str],
    metric_bindings: dict | None = None,
) -> dict[str, list[dict]]:
    """Extract requested long tables from this source's decoded docs."""
    want = set(requested) & REQUESTABLE_TABLES
    out: dict[str, list[dict]] = {t: [] for t in want}
    seen: set[str] = set()
    for ddoc in result.docs:
        for key, elements in _iter_arrays(ddoc.doc):
            table = _ARRAY_KEYS[key]
            if table in want:
                out[table].extend(
                    _emit_elements(ddoc, key, elements, table, spec, ctx, seen)
                )
    if "times_to_event" in want:
        _add_unique(
            out["times_to_event"], seen,
            _tte_from_events(result, spec, ctx),
        )
    if "events" in want or "event_participants" in want:
        for table, row in _participants_from_events(result, spec, ctx, want):
            _add_unique(out.setdefault(table, []), seen, [row])
    if "metrics" in want:
        out["metrics"].extend(
            _metric_rows(result, spec, ctx, metric_bindings or {})
        )
    return out


_EPOCH_NON_METRIC_KEYS = {
    "epoch", "t", "index", "bin", "hour", "value", "count", "n",
    "level", "metric", "metric_id", "kind", "name",
    "bin_start_hours", "start_hours", "bin_end_hours", "end_hours",
    "denominator", "n_at_risk", "population", "population_id",
    "cohort", "window_id",
}


def _epoch_rows(elem, i, ddoc, spec, ctx, key) -> list[dict] | None:
    epoch = _num(elem, "epoch", "t", "index", "bin", "hour")
    # Long form {metric, value} emits a single row; wide form
    # {epoch, infected, susceptible, ...} emits one row per state column.
    if _num(elem, "value", "count", "n", "level") is not None:
        metrics = [
            (
                _text(elem, "metric", "metric_id", "kind", "name")
                or "value",
                _num(elem, "value", "count", "n", "level"),
            )
        ]
    else:
        metrics = [
            (k, float(v))
            for k, v in elem.items()
            if k not in _EPOCH_NON_METRIC_KEYS
            and isinstance(v, (int, float))
            and not isinstance(v, bool)
        ]
    if not metrics or epoch is None:
        return None
    return [
        _epoch_row(elem, i, ddoc, spec, ctx, key, metric, epoch, value)
        for metric, value in metrics
    ]


def _epoch_row(elem, i, ddoc, spec, ctx, key, metric, epoch, value) -> dict:
    return {
        "row_id": row_id("em", ddoc.asset_id, metric, epoch, i),
        "reduction_id": ctx.reduction_id,
        "run_uid": ddoc.run_uid,
        "source_asset_id": ddoc.asset_id,
        "metric_id": f"{spec.family}.{key}.{metric}",
        "series_kind": _SERIES_KIND.get(metric, "state"),
        "source_epoch": int(epoch) if epoch is not None else i,
        "bin_start_hours": _num(elem, "bin_start_hours", "start_hours"),
        "bin_end_hours": _num(elem, "bin_end_hours", "end_hours"),
        "value": value,
        "denominator": _num(elem, "denominator", "n_at_risk", "population"),
        "population_id": _text(elem, "population_id", "cohort"),
        "window_id": _text(elem, "window_id"),
        "value_status": "exact_emitted" if value is not None else "unavailable",
    }


def _event_rows(elem, i, ddoc, spec, ctx, key) -> dict | None:
    eid = _text(elem, "event_id", "id") or f"ev-{i}"
    return {
        "row_id": row_id("ev", ddoc.asset_id, eid),
        "reduction_id": ctx.reduction_id,
        "event_id": eid,
        "run_uid": ddoc.run_uid,
        "source_asset_id": ddoc.asset_id,
        "episode_id": _text(elem, "episode_id"),
        "event_type": _text(elem, "event_type", "type", "kind"),
        "start_hours": _num(elem, "start_hours", "time", "hour", "t"),
        "end_hours": _num(elem, "end_hours", "duration_end"),
        "dominant_route": _text(elem, "dominant_route", "route"),
        "dose_acquired": _num(elem, "dose_acquired", "dose"),
        "dose_delivered": _num(elem, "dose_delivered"),
        "dose_route": _text(elem, "dose_route"),
        "entry_channel": _text(elem, "entry_channel", "channel"),
        "event_weight": _num(elem, "weight"),
        "object_id": _text(elem, "object_id"),
        "zone_id": _text(elem, "zone_id", "zone"),
        "payload_json": dict(elem),
    }


def _tte_rows(elem, i, ddoc, spec, ctx, key) -> dict | None:
    return _tte_row(elem, i, ddoc, spec, ctx, endpoint=_text(elem, "endpoint_id", "endpoint"))


def _tte_row(elem, i, ddoc, _spec, ctx, endpoint=None) -> dict | None:
    censor = _text(elem, "censor_type", "censor") or "unknown"
    if censor not in (
        "exact", "right", "left", "interval",
        "structural_nonoccurrence", "not_at_risk",
    ):
        censor = "unknown"
    subject = _text(elem, "subject_id", "agent_id", "id") or f"subj-{i}"
    ep = endpoint or _text(elem, "endpoint_id", "endpoint", "type")
    return {
        "row_id": row_id("tte", ddoc.asset_id, subject, ep or "", i),
        "reduction_id": ctx.reduction_id,
        "run_uid": ddoc.run_uid,
        "source_asset_id": ddoc.asset_id,
        "subject_id": subject,
        "subject_kind": _text(elem, "subject_kind") or "agent",
        "endpoint_id": ep,
        "event_domain": _text(elem, "event_domain", "domain") or "latent",
        "event_observed": censor == "exact",
        "censor_type": censor,
        "competing_endpoint_id": _text(elem, "competing_endpoint_id"),
        "origin_hours": _num(elem, "origin_hours", "origin"),
        "entry_hours": _num(elem, "entry_hours", "entry"),
        "exit_hours": _num(elem, "exit_hours", "exit"),
        "lower_hours": _num(elem, "lower_hours", "lower", "event_hours", "time"),
        "upper_hours": _num(elem, "upper_hours", "upper"),
        "time_origin_id": _text(elem, "time_origin_id"),
        "window_id": _text(elem, "window_id"),
        "original_time_json": dict(elem),
    }


_CENSOR_FIELDS = ("censor", "censor_type", "entry_hours", "lower_hours")
_PARTICIPANT_KINDS = (
    "actor", "source", "recipient", "exposed",
    "reporter", "tested", "observer",
)


def _event_elements(result) -> Iterable[tuple]:
    """Yield (ddoc, index, event atom) for every events array in the docs."""
    for ddoc in result.docs:
        for key, elements in _iter_arrays(ddoc.doc):
            if _ARRAY_KEYS[key] != "events":
                continue
            for i, elem in enumerate(elements):
                if isinstance(elem, dict):
                    yield ddoc, i, elem


def _tte_from_events(result, spec, ctx) -> list[dict]:
    """times_to_event rows derived from event atoms carrying censor fields."""
    rows = []
    for ddoc, i, elem in _event_elements(result):
        if not any(k in elem for k in _CENSOR_FIELDS):
            continue
        row = _tte_row(
            elem, i, ddoc, spec, ctx,
            endpoint=_text(elem, "event_type", "type") or "event",
        )
        if row is not None:
            rows.append(row)
    return rows


def _participant_rows(ddoc, eid, kind, agents, ctx) -> Iterable[dict]:
    for agent in agents:
        yield {
            "row_id": row_id("ep", ddoc.asset_id, eid, kind, str(agent)),
            "reduction_id": ctx.reduction_id,
            "event_id": eid,
            "run_uid": ddoc.run_uid,
            "source_asset_id": ddoc.asset_id,
            "agent_id": str(agent),
            "membership_id": None,
            "participation_kind": kind,
            "participation_status": "observed",
            "dose_share": None,
            "role_definition_id": None,
        }


def _participants_from_events(result, _spec, ctx, _want) -> list[tuple[str, dict]]:
    """event_participants rows from participant sublists on event atoms."""
    rows: list[tuple[str, dict]] = []
    for ddoc, i, elem in _event_elements(result):
        eid = _text(elem, "event_id", "id") or f"ev-{i}"
        for kind in _PARTICIPANT_KINDS:
            vals = elem.get(kind) or elem.get(f"{kind}s")
            if vals is None:
                continue
            if not isinstance(vals, list):
                vals = [vals]
            rows.extend(
                ("event_participants", r)
                for r in _participant_rows(ddoc, eid, kind, vals, ctx)
            )
    return rows


def _population_rows(elem, i, ddoc, spec, ctx, key) -> dict | None:
    basis = _text(elem, "basis", "population_basis", "kind") or "observed_roster"
    if basis not in (
        "boarding_complement", "unique_ever_aboard", "susceptible_at_start",
        "eligible_course_cohort", "eligible_onboard", "dynamic_at_risk",
        "test_eligible", "source_eligible", "response_eligible",
        "observed_roster",
    ):
        basis = "observed_roster"
    pop = _text(elem, "population_id", "name", "cohort") or f"pop-{i}"
    return {
        "row_id": row_id("pi", ddoc.asset_id, pop, i),
        "reduction_id": ctx.reduction_id,
        "run_uid": ddoc.run_uid,
        "source_asset_id": ddoc.asset_id,
        "population_id": pop,
        "population_basis": basis,
        "n_at_start": _num(elem, "n_at_start", "n_start", "count"),
        "n_at_end": _num(elem, "n_at_end", "n_end"),
        "n_unique": _num(elem, "n_unique", "n_ever"),
        "person_hours": _num(elem, "person_hours"),
        "susceptible_person_hours": _num(elem, "susceptible_person_hours"),
        "count_evidence": _text(elem, "count_evidence", "evidence"),
        "risk_set_rule": _text(elem, "risk_set_rule"),
        "role_definition_id": _text(elem, "role_definition_id", "role"),
        "window_id": _text(elem, "window_id"),
        "window_start_hours": _num(elem, "window_start_hours", "start_hours"),
        "window_end_hours": _num(elem, "window_end_hours", "end_hours"),
    }


def _agent_rows(elem, i, ddoc, spec, ctx, key) -> dict | None:
    aid = _text(elem, "agent_id", "id", "name")
    if aid is None:
        return None
    return {
        "row_id": row_id("ag", ddoc.asset_id, aid),
        "reduction_id": ctx.reduction_id,
        "run_uid": ddoc.run_uid,
        "source_asset_id": ddoc.asset_id,
        "agent_id": aid,
        "roster_scope": "full_at_risk",
        "primary_role_id": _text(elem, "primary_role_id", "role", "duty"),
        "boarding_state": _text(elem, "boarding_state", "status"),
        "attributes_json": dict(elem),
    }


def _observation_rows(elem, i, ddoc, spec, ctx, key) -> dict | None:
    oid = _text(elem, "observation_id", "id") or f"obs-{i}"
    return {
        "row_id": row_id("ob", ddoc.asset_id, oid),
        "reduction_id": ctx.reduction_id,
        "run_uid": ddoc.run_uid,
        "source_asset_id": ddoc.asset_id,
        "observation_id": oid,
        "parent_observation_id": _text(elem, "parent_observation_id"),
        "specimen_id": _text(elem, "specimen_id", "specimen"),
        "subject_id": _text(elem, "subject_id", "agent_id"),
        "subject_kind": _text(elem, "subject_kind") or "agent",
        "modality": _text(elem, "modality", "kind", "test"),
        "collection_hours": _num(elem, "collection_hours", "time", "hour"),
        "result_hours": _num(elem, "result_hours"),
        "result_json": dict(elem),
        "latent_truth_json": elem.get("latent_truth"),
        "eligibility_population_id": _text(elem, "eligibility_population_id"),
        "feedback_action_id": _text(elem, "feedback_action_id"),
    }


def _mechanism_rows(elem, i, ddoc, spec, ctx, key) -> dict | None:
    oid = _text(elem, "object_id", "id", "name")
    if oid is None:
        return None
    return {
        "row_id": row_id("mo", ddoc.asset_id, oid),
        "reduction_id": ctx.reduction_id,
        "run_uid": ddoc.run_uid,
        "source_asset_id": ddoc.asset_id,
        "object_id": oid,
        "object_kind": _text(elem, "object_kind", "kind", "type"),
        "source_kind": _text(elem, "source_kind"),
        "source_id": _text(elem, "source_id"),
        "station_id": _text(elem, "station_id", "station"),
        "zone_id": _text(elem, "zone_id", "zone"),
        "start_hours": _num(elem, "start_hours"),
        "end_hours": _num(elem, "end_hours"),
        "end_reason": _text(elem, "end_reason"),
        "attributes_json": dict(elem),
    }


def _metric_rows(result, _spec, ctx, bindings: dict) -> list[dict]:
    """metrics rows only for request-declared numerator/denominator bindings.

    A binding maps a FIELD_CONTRACTS metric_id onto two native paths in
    the decoded payload; both must resolve to a numeric scalar for a row
    to be emitted. ``denominator`` of zero is a typed ``denominator_zero``
    gap outcome — never silently dropped.
    """
    rows = []
    scalars: dict[str, Any] = {}
    for s in result.scalars:
        scalars[s.native_path] = s.value
    for metric_id, bind in sorted(bindings.items()):
        num = scalars.get(bind.get("numerator"))
        den = scalars.get(bind.get("denominator"))
        if den in (0, 0.0):
            continue  # caller records denominator_zero via data_gaps
        value = (num / den) if num is not None and den else None
        for run_uid in {s.run_uid for s in result.scalars}:
            rows.append(
                {
                    "row_id": row_id("m", metric_id, run_uid),
                    "reduction_id": ctx.reduction_id,
                    "metric_id": metric_id,
                    "definition_version": bind.get("definition_version"),
                    "run_uid": run_uid,
                    "source_asset_id": None,
                    "numerator": num,
                    "denominator": den,
                    "numerator_exact_json": {"native_path": bind.get("numerator")},
                    "denominator_exact_json": {"native_path": bind.get("denominator")},
                    "value": value,
                    "value_status": (
                        "exact_derived" if value is not None else "undefined"
                    ),
                    "unit": bind.get("unit"),
                    "endpoint_domain": bind.get("endpoint_domain"),
                    "condition_id": bind.get("condition_id"),
                    "window_id": bind.get("window_id"),
                    "population_id": bind.get("population_id"),
                    "membership_time_rule": None,
                }
            )
    return rows


_ELEMENT_EMITTERS = {
    "epoch_metrics": _epoch_rows,
    "events": _event_rows,
    "times_to_event": _tte_rows,
    "population_intervals": _population_rows,
    "agents": _agent_rows,
    "observations": _observation_rows,
    "mechanism_objects": _mechanism_rows,
}


def decode_parquet_object(obj, ref, result: AdapterResult) -> None:
    """D2 parquet decode: bounded read → row scalars + decoded docs.

    D1 verified the PAR1 envelope and indexed the asset; the
    materialization path reads the body through the same pinned object
    and flattens every row into lossless scalars (``/{row}/{column}``
    native paths) plus one DecodedDoc per record batch so long-table
    extraction sees the same shapes as JSON members.
    """
    import pyarrow.parquet as pq

    from .adapters import _asset_id, _run_record, _scalars_from_doc
    from .payloads import DecodedDoc as _Doc

    body = obj.read_whole()
    aid = _asset_id(obj, ref, None)
    pf = pq.ParquetFile(io.BytesIO(body))
    row_no = 0
    for batch in pf.iter_batches():
        table = batch.to_pylist()
        for row in table:
            result.scalars.extend(
                _scalars_from_doc(
                    ref.run_id(), row, str(row_no), "parquet_sidecar",
                    asset_id=aid,
                )
            )
            result.docs.append(
                _Doc(run_uid=ref.run_id(), asset_id=aid,
                     member_path=f"row:{row_no}", doc=row),
            )
            row_no += 1
    # parquet rows are executions; one run record per object stands for
    # the shard the merged parquet was written from.
    result.runs.append(_run_record(ref))
