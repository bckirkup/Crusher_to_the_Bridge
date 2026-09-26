"""Coverage for tools/noro_diag/observation_channel_funnel.py pure helpers."""

from types import SimpleNamespace

import pytest

from orchestrator_types import STATUS_BASELINE, STATUS_SUSPECTED
from tools.noro_diag.observation_channel_funnel import (
    ChannelCapture,
    build_funnel,
    build_readout,
    declared_channel_table,
    funnel_ratios,
    illness_class,
)

PID = "norwalk_gi"

PROFILE = {
    "severity_model": {
        "states": [
            "asymptomatic", "subclinical", "mild", "moderate",
            "severe_critical",
        ],
    },
    "observation_model": {
        "syndrome_case_eligibility_by_severity": [0, 0.55, 0.98, 1, 1],
        "reporting_probability_by_severity_pre_recognition": [
            0, 0.45, 0.7, 0.94, 1,
        ],
        "reporting_probability_by_severity_post_recognition": [
            0, 0.5, 0.76, 0.96, 1,
        ],
        "lab_sampling_probability_by_severity": [0, 0.05, 0.2, 0.6, 0.9],
        "episode_reporting_window_days": 2.0,
    },
}


def _record(
    aid,
    *,
    role="passenger",
    presented=True,
    severity="mild",
    vomiting=True,
    diarrhoea=False,
    imported=False,
    onset_offset=24,
):
    axes = {"vomiting": vomiting, "diarrhoea": diarrhoea} if presented else {}
    return {
        "agent_id": aid,
        "role": role,
        "infection_epoch": 10,
        "imported": imported,
        "presented": presented,
        "onset_offset": onset_offset if presented else None,
        "true_onset_epoch": (10 + onset_offset) if presented else None,
        "severity_peak": severity,
        "severity_end": severity,
        "vomiting": axes.get("vomiting", False),
        "diarrhoea": axes.get("diarrhoea", False),
        "axes_drawn": bool(axes),
        "illness_end": "RECOVERED",
        "status_end": "INFECTED",
    }


def _work(epoch, status=STATUS_BASELINE, syn=None, agents=None):
    return SimpleNamespace(
        epoch=epoch,
        state=SimpleNamespace(trigger_status=status),
        syn_result=syn,
        information_state={},
        agents=agents or [],
    )


def _agent_dict(aid, pid_illness=None, compliance="compliant"):
    pinfs = (
        {PID: {"illness": pid_illness, "epochs_since_symptom_onset": 3}}
        if pid_illness is not None
        else {}
    )
    return {
        "agent_id": aid,
        "pathogen_infections": pinfs,
        "symptom_presentation": (
            "symptomatic" if pid_illness == "SYMPTOMATIC" else "asymptomatic"
        ),
        "compliance_status": compliance,
        "location": "zCabin",
    }


def test_illness_class_buckets():
    assert illness_class(_record(1, vomiting=True, diarrhoea=True)) == (
        "vomiting_and_diarrhoea"
    )
    assert illness_class(_record(1, vomiting=True, diarrhoea=False)) == (
        "vomiting_only"
    )
    assert illness_class(_record(1, vomiting=False, diarrhoea=True)) == (
        "diarrhoea_only"
    )
    assert illness_class(_record(1, vomiting=False, diarrhoea=False)) == (
        "neither_axis"
    )
    assert illness_class(_record(1, presented=False)) == "undrawn"


def test_capture_tracks_status_and_reports():
    cap = ChannelCapture(PID)
    cap.observe(None, _work(1, STATUS_BASELINE, syn={
        "true_positive_ids": [7], "sick_call_agents": [7, 8],
        "noise_ids": [8],
    }))
    cap.observe(None, _work(2, STATUS_SUSPECTED, syn={
        "true_positive_ids": [7, 9], "sick_call_agents": [7, 9],
        "noise_ids": [],
    }))
    assert cap.first_report_epoch[7] == 1
    assert cap.first_report_epoch[9] == 2
    assert cap.reported_symptomatic_ids == {7, 9}
    assert cap.sick_call_count == 4
    assert cap.noise_report_count == 1
    # Report at epoch 2 reads status from end of epoch 1 (BASELINE -> pre).
    assert cap.recognized_at_report(2) is False
    # Report at epoch 3 would read end-of-2 status (SUSPECTED -> post).
    assert cap.recognized_at_report(3) is True
    # Empty syn_result is safe.
    cap.observe(None, _work(3, STATUS_SUSPECTED, syn=None))
    assert cap.status_by_epoch[3] == STATUS_SUSPECTED


def test_capture_exposure_splits_visibility():
    cap = ChannelCapture(PID)
    agents = [
        _agent_dict(1, "SYMPTOMATIC", compliance="compliant"),
        _agent_dict(2, "SYMPTOMATIC", compliance="isolated"),
        _agent_dict(3, "RECOVERED"),
        _agent_dict(4, None),
    ]
    cap.observe(None, _work(5, agents=agents))
    assert cap.exposure[1].visible == 1
    assert cap.exposure[1].first_symptomatic_epoch == 5
    assert cap.exposure[1].onset_epoch_witness == 2
    assert cap.exposure[2].isolated == 1
    assert 3 not in cap.exposure
    assert 4 not in cap.exposure


def test_declared_table_is_graded():
    out = declared_channel_table(PROFILE)
    assert out["episode_reporting_window_days"] == pytest.approx(2.0)
    mild = out["per_severity"]["mild"]
    assert mild["episode_p_pre"] == pytest.approx(0.98 * 0.7)
    # Per-day hazard of a 0.686 episode over a 2-day window.
    assert mild["per_day_hazard_pre"] == pytest.approx(
        1.0 - (1.0 - 0.686) ** 0.5,
    )
    assert mild["lab_sampling"] == pytest.approx(0.2)
    assert out["per_severity"]["asymptomatic"]["episode_p_pre"] == (
        pytest.approx(0.0)
    )
    # A different vector moves the hazard (graded sensitivity).
    other = {
        "severity_model": PROFILE["severity_model"],
        "observation_model": {
            **PROFILE["observation_model"],
            "reporting_probability_by_severity_pre_recognition": [
                0, 0.2, 0.3, 0.4, 0.5,
            ],
        },
    }
    other_out = declared_channel_table(other)
    assert other_out["per_severity"]["mild"]["episode_p_pre"] == pytest.approx(
        0.98 * 0.3,
    )
    assert (
        other_out["per_severity"]["mild"]["per_day_hazard_pre"]
        < mild["per_day_hazard_pre"]
    )


def _capture_with(reported_epochs=None, statuses=None, symptomatic_ids=None):
    cap = ChannelCapture(PID)
    epochs = sorted({1, *(reported_epochs or {}).values(), *(statuses or {1: STATUS_BASELINE})})
    agents = [
        _agent_dict(aid, "SYMPTOMATIC") for aid in (symptomatic_ids or [])
    ]
    for epoch in range(1, max(epochs) + 1):
        status = (statuses or {}).get(epoch, STATUS_BASELINE)
        syn = {"true_positive_ids": [
            aid for aid, e in (reported_epochs or {}).items() if e == epoch
        ]}
        cap.observe(None, _work(epoch, status, syn=syn, agents=agents))
    return cap


def _funnel(**over):
    records = [
        _record(1, severity="mild"),                       # reported mild
        _record(2, severity="moderate", role="crew"),      # reported post
        _record(3, severity="subclinical"),                # eligible, missed
        _record(4, severity="mild"),                       # never reported
        _record(5, presented=False, severity="asymptomatic"),
    ]
    over.setdefault("capture", _capture_with(
        reported_epochs={1: 2, 2: 5},
        statuses={1: STATUS_BASELINE, 2: STATUS_BASELINE,
                  3: STATUS_SUSPECTED, 4: STATUS_SUSPECTED},
        symptomatic_ids=[1, 2, 3, 4],
    ))
    over.setdefault("lab_sampled", {1, 2})
    over.setdefault("lab_confirmed", {1, 2})
    over.setdefault("confirmed_epoch_of", {1: 2, 2: 5})
    over.setdefault("dated", {1: {"onset_epoch": 34}})
    over.setdefault("ever_reported_ids", {1, 2})
    return build_funnel(
        records, over["capture"], PROFILE,
        lab_sampled=over["lab_sampled"],
        lab_confirmed=over["lab_confirmed"],
        confirmed_epoch_of=over["confirmed_epoch_of"],
        dated=over["dated"],
        ever_reported_ids=over["ever_reported_ids"],
    )


def test_build_funnel_rungs_and_splits():
    out = _funnel()
    rungs = out["rungs"]
    assert rungs["infected"]["total"] == 5
    assert rungs["infected"]["crew"] == 1
    assert rungs["symptomatic_course"]["total"] == 4
    assert rungs["symptomatic_onboard"]["total"] == 4
    # asymptomatic peak is the only ineligible symptomatic course here;
    # hosts 1-4 are all eligibility>0.
    assert rungs["syndrome_eligible"]["total"] == 4
    assert rungs["eligible_onboard"]["total"] == 4
    assert rungs["reported_infirmary"]["total"] == 2
    assert rungs["reported_infirmary"]["crew"] == 1
    assert rungs["reported_infirmary"]["pre_recognition"] == 1
    assert rungs["reported_infirmary"]["post_recognition"] == 1
    assert rungs["lab_confirmed"]["total"] == 2
    assert rungs["onset_dated"]["total"] == 1
    # Rung monotonicity: each rung is a subset of the previous.
    assert (
        rungs["onset_dated"]["total"]
        <= rungs["lab_confirmed"]["total"]
        <= rungs["reported_infirmary"]["total"]
        <= rungs["syndrome_eligible"]["total"]
        <= rungs["symptomatic_course"]["total"]
        <= rungs["infected"]["total"]
    )
    assert out["severity_tables"]["reported"] == {"mild": 1, "moderate": 1}
    # host 2 confirmed at epoch 5 while already symptomatic on-board but
    # never landed in the dated record.
    assert out["confirmed_never_dated"] == {"symptomatic_course_before_confirm": 1}
    fidelity = out["dating_fidelity"]
    assert fidelity["dated_hosts"] == 1
    assert fidelity["compared"] == 1


def test_build_funnel_empty_is_safe():
    out = build_funnel(
        [], ChannelCapture(PID), PROFILE,
        lab_sampled=set(), lab_confirmed=set(), confirmed_epoch_of={},
        dated={}, ever_reported_ids=set(),
    )
    assert out["rungs"]["infected"]["total"] == 0
    ratios = funnel_ratios(out)
    assert ratios["reported_per_eligible"] is None
    assert ratios["dated_per_confirmed"] is None


def test_funnel_ratios_chain():
    ratios = funnel_ratios(_funnel())
    assert ratios["infected"] == 5
    assert ratios["symptomatic_per_infected"] == pytest.approx(0.8)
    assert ratios["eligible_per_symptomatic"] == pytest.approx(1.0)
    assert ratios["reported_per_eligible"] == pytest.approx(0.5)
    assert ratios["confirmed_per_reported"] == pytest.approx(1.0)
    assert ratios["dated_per_confirmed"] == pytest.approx(0.5)
    assert ratios["reported_crew_share"] == pytest.approx(1.0)


def test_non_report_decomposition():
    records = [
        _record(1, severity="mild"),
        _record(2, severity="mild"),
        _record(3, severity="mild"),
    ]
    cap = ChannelCapture(PID)
    agents = {
        1: _agent_dict(1, "SYMPTOMATIC", compliance="isolated"),
        2: _agent_dict(2, "SYMPTOMATIC", compliance="compliant"),
        3: _agent_dict(3, "SYMPTOMATIC", compliance="compliant"),
    }
    cap.observe(None, _work(1, agents=[agents[1], agents[2], agents[3]]))
    cap.observe(None, _work(2, agents=[
        _agent_dict(1, "SYMPTOMATIC", compliance="isolated"),
        _agent_dict(2, "SYMPTOMATIC", compliance="isolated"),
        _agent_dict(3, "SYMPTOMATIC", compliance="compliant"),
    ]))
    out = build_funnel(
        records, cap, PROFILE,
        lab_sampled=set(), lab_confirmed=set(), confirmed_epoch_of={},
        dated={}, ever_reported_ids=set(),
    )
    reasons = out["non_report_decomposition"]
    assert reasons["isolated_whole_symptomatic_course"] == 1
    assert reasons["partially_isolated_but_draw_missed"] == 1
    assert reasons["visible_whole_course_draw_missed"] == 1


def test_build_readout_pools_ratios():
    rows = [
        {"seed": s, "ratios": {
            "infected": float(10 + s),
            "symptomatic_per_infected": 0.5 + 0.1 * s,
            "reported_per_eligible": 0.5,
            "confirmed_per_reported": None,
            "dated_per_confirmed": 1.0,
        }, "rungs": {
            "infected": {"total": 10 + s, "passenger": 8, "crew": 2},
            "symptomatic_course": {"total": 5, "passenger": 4, "crew": 1},
            "symptomatic_onboard": {"total": 4, "passenger": 3, "crew": 1},
        },
         "dating_fidelity": {"dated_hosts": 2, "exact_share": 1.0,
                             "max_abs_error": 0},
         "confirmed_never_dated": {}, "non_report_decomposition": {}}
        for s in range(3)
    ]
    out = build_readout(rows)
    assert out["n_seeds"] == 3
    assert out["rung_ratios"]["symptomatic_per_infected"]["median"] == (
        pytest.approx(0.6)
    )
    assert out["rung_ratios"]["confirmed_per_reported"]["median"] is None
    assert out["dating_fidelity"]["dated_hosts_total"] == 6
    # pooled ratios divide summed counts, not a mean of per-seed ratios.
    assert out["pooled_rung_totals"]["infected"]["total"] == 33
    assert out["pooled_ratios"]["symptomatic_per_infected"] == pytest.approx(
        15 / 33
    )
    # zero reporters over three crew symptomatic-onboard hosts -> 0.0,
    # and confirmed/reported is undefined only when nobody reported.
    assert out["pooled_ratios"]["reported_crew_share"] == pytest.approx(0.0)
    assert out["pooled_ratios"]["confirmed_per_reported"] is None


def test_build_readout_pooled_crew_share():
    row = {
        "seed": 1,
        "ratios": {"infected": 4.0},
        "rungs": {
            "infected": {"total": 4, "passenger": 3, "crew": 1},
            "symptomatic_course": {"total": 4, "passenger": 3, "crew": 1},
            "symptomatic_onboard": {"total": 4, "passenger": 3, "crew": 1},
            "syndrome_eligible": {"total": 4, "passenger": 3, "crew": 1},
            "eligible_onboard": {"total": 4, "passenger": 3, "crew": 1},
            "reported_infirmary": {
                "total": 2, "passenger": 1, "crew": 1,
                "pre_recognition": 1, "post_recognition": 1,
            },
            "lab_sampled": {"total": 2, "passenger": 1, "crew": 1},
            "lab_confirmed": {"total": 2, "passenger": 1, "crew": 1},
            "onset_dated": {"total": 2, "passenger": 1, "crew": 1},
        },
        "dating_fidelity": {"dated_hosts": 2, "exact_share": 1.0,
                            "max_abs_error": 0},
        "confirmed_never_dated": {}, "non_report_decomposition": {},
    }
    out = build_readout([row])
    assert out["pooled_ratios"]["reported_crew_share"] == pytest.approx(1.0)
    assert out["pooled_ratios"]["dated_per_confirmed"] == pytest.approx(1.0)
