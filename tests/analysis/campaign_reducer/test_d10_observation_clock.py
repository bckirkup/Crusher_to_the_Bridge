"""first_paper_observation_clock profile tests (Edison obs/clock sidecar).

- OBSERVED clock is the retained timeseries, never the configured
  ``num_epochs`` (which is ``meta.epochs`` — the declared horizon).
- First-report/threshold epochs carry category/role/origin/clock/window
  labels; a threshold never crossed is ``null + not_crossed_in_window``
  (distinct from ``timeseries_absent`` and ``missing``).
- Unserialized sets emit typed availability (never inferred).
- The conflated ``infections_by_route_consistent`` stays as
  ``historical_evidence``; the corrected checks compare acquired-only
  and imports+acquired separately.
"""
from __future__ import annotations

import io
import json
import zipfile

from picard_framework.analysis.campaign_reducer.materialize import (
    run_materialization,
)
from tests.analysis.campaign_reducer.test_d7_first_paper_scalar import (  # noqa: E501
    _rig,
    _run_zip,
    _scan_entry,
    _scan_rows_obj,
    _spec,
    _src,
)
from tests.analysis.campaign_reducer.test_d8_correction_spec import (  # noqa: E501
    _scan_spec,
)

VEC = "first_paper_observation_clock_vectors.jsonl"


def _obs_zip(seed=8000, n_rows=288, noise0=5, pax_first=12, crew_first=57,
             detection=262, vsp_epoch=None, omit=()):
    """A run zip whose timeseries carries the observation counters.

    Terminal ts counters equal the ``_run_zip`` summary block (rep_pax=2,
    rep_crew=3, ever_infected=15) so the ts-vs-summary equality checks
    hold under the fixture's own numbers.
    """
    body = _run_zip(seed=seed)
    zin = zipfile.ZipFile(io.BytesIO(body))
    summary = json.loads(zin.read("summary.json"))
    summary["parameters"]["num_epochs"] = 288
    summary["summary"]["cumulative_reported_noise_cases"] = noise0
    ts = []
    for e in range(n_rows):
        ts.append({
            "epoch": e,
            "cumulative_reported_cases_passenger": 2 if e >= pax_first
            else 0,
            "cumulative_reported_cases_crew": 3 if e >= crew_first else 0,
            "cumulative_reported_cases": (
                (2 if e >= pax_first else 0)
                + (3 if e >= crew_first else 0)),
            "cumulative_reported_noise_cases": noise0,
            "cumulative_ever_infected": 15 if e == n_rows - 1 else 0,
            "passenger_reported_case_rate_exceeded":
                vsp_epoch is not None and e >= vsp_epoch,
            "crew_reported_case_rate_exceeded": False,
            "symptomatic": 1 if e >= pax_first else 0,
            "quarantined": 0,
            "isolated": 0,
            "trigger_status": (
                "SUSPECTED" if detection is not None and e >= detection
                else "ALERT"),
        })
    summary["timeseries"] = ts
    summary["derived"]["vsp_trigger_epoch"] = vsp_epoch
    summary["derived"]["detection_epoch"] = detection
    for path in omit:
        node = summary
        parts = path.split(".")
        for p in parts[:-1]:
            node = node[p]
        del node[parts[-1]]
    zout = io.BytesIO()
    with zipfile.ZipFile(zout, "w") as z:
        for name in zin.namelist():
            z.writestr(
                name,
                json.dumps(summary).encode()
                if name == "summary.json"
                else zin.read(name),
            )
    return zout.getvalue()


def _obs_vector_rows(store, rid="red-fp"):
    prefix = f"campaign/_derived/reducer/v1/attempts/{rid}/shards/"
    return [
        json.loads(line)
        for key in store.list(prefix)
        if key.endswith("/" + VEC)
        for line in store.get(key).splitlines()
    ]


def _obs_spec(sources):
    return _spec(
        sources, extraction_profile="first_paper_observation_clock")


def _run_src(uri="run_a.zip", **kw):
    # no cell_id — matches d8: the scan source registers no cell and a
    # mixed str/None key set breaks coverage_cell_rows' sort.
    return _src(uri, family="campaign_summary_zip", seed=kw.pop("seed", 8000),
                hull_id="expedition_cruise_450",
                member_allowlist=("summary.json",), emit_scalars=False,
                **kw)


def test_profile_emits_observation_fields_and_labels():
    transport, store, ledger = _rig()
    transport.put("run_a.zip", _obs_zip(seed=8000))
    transport.put("_scan_rows/arm.jsonl", _scan_rows_obj(
        [_scan_entry("run_a.zip", 8000, posted=True)]))
    spec = _obs_spec([
        _run_src(),
        _scan_spec(),
    ])
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "completed"
    assert "run_scalars" not in result.table_counts
    rows = _obs_vector_rows(store)
    assert len(rows) == 1
    v = rows[0]["values"]
    p = rows[0]["provenance"]
    assert v["observed_terminal_epoch"] == 287
    assert v["retained_epoch_rows"] == 288
    assert v["observed_coverage_fraction"] == 1.0
    assert v["epoch_index_contiguous"] is True
    assert v["first_etiologic_report_passenger_epoch"] == 12
    assert v["first_etiologic_report_crew_epoch"] == 57
    assert v["first_noise_report_epoch"] == 0
    assert v["detection_epoch_ts"] == 262
    # labels on an observed field
    pp = p["first_etiologic_report_passenger_epoch"]
    assert pp["category"] == "etiologic_report"
    assert pp["role"] == "passenger"
    assert pp["origin"] == "timeseries:cumulative_reported_cases_passenger"
    assert pp["observation_window"] == "[0,287]"
    assert pp["status"] == "observed"
    # terminal ts == summary block -> consistent
    assert v["terminal_ts_reported_vs_summary_consistent"] is True
    assert v["terminal_ts_noise_vs_summary_consistent"] is True
    assert v["detection_ts_vs_derived_consistent"] is True
    # VSP never crossed -> null + not_crossed_in_window
    assert v["vsp_either_channel_first_epoch"] is None
    assert p["vsp_either_channel_first_epoch"]["status"] == \
        "not_crossed_in_window"
    assert v["vsp_ts_vs_derived_consistent"] is True
    # observed-clock statuses + historical configured comparison
    assert v["observed_clock_status"] == "complete"
    assert v["observed_completion_status"] == "completed"
    assert v["clock_status"] == "complete"
    assert p["clock_status"]["historical_evidence"] is True
    # corrected checks split; historical flag diverges by n_imports
    assert v["infections_by_route_consistent"] is False
    assert p["infections_by_route_consistent"][
        "historical_evidence"] is True
    assert v["infections_by_route_vs_acquired_consistent"] is True
    assert v["imports_plus_acquired_vs_ever_infected_consistent"] is True
    # typed availability — never inferred
    assert v["noise_reports_passenger"] is None
    assert p["noise_reports_passenger"]["status"] == "not_recorded"
    assert p["reported_persons_union_etiologic_noise"]["reason_code"] == \
        "person_id_sets_not_serialized"
    assert p["embarkation_wall_date"]["reason_code"] == \
        "date_anchor_is_campaign_manifest_level"
    # scan fields joined + scan_posted_status
    assert v["scan_posted_status"] == "posted"
    assert v["scan_n_acquired"] == 6


def test_absent_timeseries_types_everything():
    transport, store, ledger = _rig()
    transport.put("run_a.zip", _obs_zip(omit=("timeseries",)))
    spec = _obs_spec([_run_src()])
    result = run_materialization(spec, transport, store, ledger)
    assert result.status == "completed"
    row = _obs_vector_rows(store)[0]
    v, p = row["values"], row["provenance"]
    assert v["observed_terminal_epoch"] is None
    assert p["observed_terminal_epoch"]["status"] == "timeseries_absent"
    assert "observed_terminal_epoch" in row["missing"]
    assert v["observed_clock_status"] == "unknown"
    assert v["observed_completion_status"] == "unknown"
    assert v["scan_posted_status"] == "unknown"


def test_missing_scan_source_is_absent_not_first_row_wins():
    transport, store, ledger = _rig()
    transport.put("run_a.zip", _obs_zip(seed=8000))
    spec = _obs_spec([_run_src()])
    run_materialization(spec, transport, store, ledger)
    row = _obs_vector_rows(store)[0]
    v, p = row["values"], row["provenance"]
    assert v["scan_n_acquired"] is None
    assert p["scan_n_acquired"]["status"] == "scan_source_absent"
    # agreement checks degrade to typed absent/uncomputable
    for col, pr in p.items():
        if col.endswith("_consistent") and pr.get("member") == \
                "derived:scan_agreement_check":
            assert pr["status"] == "scan_source_absent"


def test_partial_coverage_and_vsp_crossing():
    transport, store, ledger = _rig()
    transport.put("run_a.zip", _obs_zip(
        n_rows=200, vsp_epoch=150, detection=None))
    spec = _obs_spec([_run_src()])
    run_materialization(spec, transport, store, ledger)
    row = _obs_vector_rows(store)[0]
    v, p = row["values"], row["provenance"]
    assert v["observed_terminal_epoch"] == 199
    assert v["retained_epoch_rows"] == 200
    assert abs(v["observed_coverage_fraction"] - 200 / 288) < 1e-9
    assert v["observed_clock_status"] == "truncated"
    assert v["observed_completion_status"] == "truncated"
    # VSP flag crossing observed at 150; detection never crossed
    assert v["vsp_either_channel_first_epoch"] == 150
    assert v["detection_epoch_ts"] is None
    assert p["detection_epoch_ts"]["status"] == "not_crossed_in_window"


def test_derived_absent_means_both_absent_consistent():
    transport, store, ledger = _rig()
    transport.put("run_a.zip", _obs_zip(
        omit=("derived.vsp_trigger_epoch",)))
    spec = _obs_spec([_run_src()])
    run_materialization(spec, transport, store, ledger)
    row = _obs_vector_rows(store)[0]
    p = row["provenance"]
    # both sides absent -> consistent by both_absent (not uncomputable)
    assert p["vsp_ts_vs_derived_consistent"]["status"] == \
        "both_absent_consistent"
    assert row["values"]["vsp_ts_vs_derived_consistent"] is True
