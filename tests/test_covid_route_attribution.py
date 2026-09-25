"""Coverage for tools/covid_route_attribution.py pure helpers."""

from types import SimpleNamespace

import pytest

from engines.infection_dynamics_bridge import IllnessStatus
from picard_framework.covid_boarding_screen import PATHOGEN_ID
from tools.covid_route_attribution import (
    HazardRateLedger,
    NearFieldShareLedger,
    ascertainment_funnel,
    hazard_rate_table,
    near_field_share_table,
    route_window_tables,
    window_of,
)


def test_window_of_partitions_days():
    assert window_of(0, 16, 30) == "before"
    assert window_of(15, 16, 30) == "before"
    assert window_of(16, 16, 30) == "during"
    assert window_of(30, 16, 30) == "during"
    assert window_of(31, 16, 30) == "after"
    # No end day: everything from start on is "during".
    assert window_of(200, 16, None) == "during"


def _stub_sim(agents, zone_types=None):
    clock = SimpleNamespace(day_index=lambda e: int(e) // 24)
    engine = SimpleNamespace(
        agents=agents, explicit_seed_agent_ids=set(),
    )
    return SimpleNamespace(
        clock=clock,
        engine=engine,
        zone_types=zone_types or {},
    )


def _agent(aid, infections=None, role="passenger", home_zone="zCabin"):
    return SimpleNamespace(
        agent_id=aid,
        infections=infections or {},
        role=role,
        home_zone=home_zone,
    )


def test_route_window_tables_tallies_every_event(monkeypatch):
    import tools.covid_route_attribution as mod

    monkeypatch.setattr(mod, "_zone_class_lookup", lambda sim: {})
    agents = {
        1: _agent(1, role="passenger", home_zone="zCabin"),
        2: _agent(2, role="crew", home_zone="zCrew"),
    }
    sim = _stub_sim(
        list(agents.values()),
        zone_types={"zCabin": "Cabin_Corridor", "zHall": "Cabin_Corridor"},
    )
    ledger = SimpleNamespace(events=[
        # before quarantine (day 10)
        {"epoch": 240, "zone": "zCabin", "pathway": "droplet",
         "target_agent_id": 1, "confined": False},
        # during quarantine (day 20)
        {"epoch": 480, "zone": "zHall", "pathway": "hvac_airborne",
         "target_agent_id": 2, "confined": True},
        # after quarantine (day 31)
        {"epoch": 744, "zone": "zCabin", "pathway": "fomite",
         "target_agent_id": 1, "confined": False},
    ])
    out = route_window_tables(sim, ledger, 16, 30)
    assert out["events"] == 3
    assert out["route_by_window"]["before"] == {"droplet": 1}
    assert out["route_by_window"]["during"] == {"hvac_airborne": 1}
    assert out["route_by_window"]["after"] == {"fomite": 1}
    # zCabin is agent 1's home zone -> cabin; zHall is not agent 2's -> corridor.
    assert out["zone_by_window"]["before"] == {"cabin": 1}
    assert out["zone_by_window"]["during"] == {"corridor": 1}
    assert out["role_by_window"]["before"] == {"passenger": 1}
    assert out["role_by_window"]["during"] == {"crew": 1}


def _funnel_sim(agents, confirmed, dated, eligibility=None, seeded=None):
    sim = _stub_sim(agents)
    sim.engine.explicit_seed_agent_ids = set(seeded or ())
    sim.modalities = {
        "syndromic": SimpleNamespace(
            _lab_confirmed={(PATHOGEN_ID, aid): 100 for aid in confirmed},
            _onset_observations={
                (PATHOGEN_ID, aid): rec for aid, rec in dated.items()
            },
        )
    }
    sim.pathogen_profiles = {
        PATHOGEN_ID: {
            "severity_model": {
                "states": ["asymptomatic", "subclinical", "mild",
                           "moderate", "severe_critical"],
            },
            "observation_model": (
                {"syndrome_case_eligibility_by_severity": eligibility}
                if eligibility is not None else {}
            ),
        }
    }
    return sim


def _infected(illness, severity):
    return {
        PATHOGEN_ID: {
            "illness": illness,
            "symptom_severity": severity,
            "infection_epoch": 0,
        }
    }


def test_ascertainment_funnel_counts_rungs():
    eligibility = [0.0, 0.0, 1.0, 1.0, 1.0]
    agents = [
        _agent(1, _infected(IllnessStatus.SYMPTOMATIC, "mild")),
        _agent(2, _infected(IllnessStatus.SYMPTOMATIC, "moderate")),
        _agent(3, _infected(IllnessStatus.SYMPTOMATIC, "subclinical")),
        _agent(4, _infected(IllnessStatus.NOT_ILL, "asymptomatic")),
        _agent(5),  # never infected
    ]
    sim = _funnel_sim(
        agents, confirmed={1, 2, 3},
        dated={1: {"symptom_severity": "mild"},
               2: {"symptom_severity": "moderate"}},
        eligibility=eligibility,
        seeded={4},
    )
    out = ascertainment_funnel(sim)
    assert out["infected_truth"] == 3  # agent 4 excluded as seeded
    assert out["symptomatic_at_end"] == 3
    assert out["eligible_severity_course"] == 2  # subclinical not eligible
    assert out["lab_confirmed_total"] == 3
    assert out["confirmed_datable"] == 2
    assert out["dated_onsets"] == 2
    assert out["dated_by_severity"] == {"mild": 1, "moderate": 1}
    assert out["dating_rate_confirmed_datable"] == pytest.approx(1.0)
    assert out["dating_rate_confirmed"] == pytest.approx(2 / 3)
    assert 0.0 < out["record_dating_rate_confirmed"] < 1.0


def test_ascertainment_funnel_empty_is_safe():
    sim = _funnel_sim([_agent(9)], confirmed=set(), dated={})
    out = ascertainment_funnel(sim)
    assert out["infected_truth"] == 0
    assert out["dated_onsets"] == 0
    assert out["dating_rate_confirmed"] is None
    assert out["dating_rate_confirmed_datable"] is None


def _work(epoch, tx_events=()):
    return SimpleNamespace(epoch=epoch, tx_events=list(tx_events))


def _tx(epoch, target):
    return SimpleNamespace(epoch=epoch, target_agent_id=target)


class _FakeCore:
    """Stands in for TransmissionCore's wrappable dose functions."""

    def __init__(self):
        self.calls = {"accumulate": 0}

    def _near_field_droplet_dose(self, zone_name, target, *a, **kw):
        return kw.get("dose", 0.0)

    def _cabin_mate_droplet_addback(self, target, *a, **kw):
        return kw.get("dose", 0.0)

    def _accumulate(self, target_id, pathway, dose, *a, **kw):
        self.calls["accumulate"] += 1
        return dose


def test_near_field_share_table_splits_dose():
    ledger = NearFieldShareLedger()
    core = _FakeCore()
    sim = SimpleNamespace(tx_core=core)
    t1, t2 = SimpleNamespace(agent_id=1), SimpleNamespace(agent_id=2)
    # First observe installs the wrappers and records the infection epochs.
    ledger.observe(sim, _work(0, tx_events=[_tx(0, 1), _tx(0, 2)]))
    # Agent 1: 120 total droplet, 90 near, 30 addback -> ring share 1.0.
    # Agent 2: 110 total droplet, 10 near, 0 addback -> ring share 10/110.
    core._accumulate(1, "droplet", 120.0)
    core._near_field_droplet_dose("z", t1, dose=90.0)
    core._cabin_mate_droplet_addback(t1, dose=30.0)
    core._accumulate(2, "droplet", 110.0)
    core._near_field_droplet_dose("z", t2, dose=10.0)
    core._accumulate(2, "hvac_airborne", 999.0)  # non-droplet ignored
    out = near_field_share_table(ledger)
    assert out["infected_with_droplet_dose"] == 2
    assert out["dose_weighted_ring_share"] == pytest.approx(130 / 230)
    assert out["dose_weighted_near_field_share"] == pytest.approx(100 / 230)
    assert out["dose_weighted_addback_share"] == pytest.approx(30 / 230)
    assert out["ring_share_q05"] == pytest.approx(10 / 110)
    assert out["ring_share_q95"] == pytest.approx(1.0)
    assert out["share_majority_ring_dose"] == pytest.approx(0.5)


def test_near_field_share_table_empty_is_safe():
    out = near_field_share_table(NearFieldShareLedger())
    assert out["infected_with_droplet_dose"] == 0
    assert out["dose_weighted_ring_share"] is None
    assert out["ring_share_median"] is None
    assert out["share_majority_ring_dose"] is None


class _FakeHazardCore:
    """Stands in for TransmissionCore's _dose_response_hazard."""

    def _dose_response_hazard(self, agent, pathogen_id, effective_dose):
        return -(-0.5)  # sentinel: wrapper must pass the return through


def _susceptible(aid, susc):
    return SimpleNamespace(
        agent_id=aid,
        dose_response_susceptibility={PATHOGEN_ID: susc},
    )


def test_hazard_rate_table_records_lambda_and_infecting():
    ledger = HazardRateLedger()
    core = _FakeHazardCore()
    sim = SimpleNamespace(tx_core=core)
    ledger.observe(sim, _work(0))  # installs the wrapper
    a1 = _susceptible(1, 2.0)
    a2 = _susceptible(2, 0.5)
    # Agent 1 challenged twice (lam 4.0, 6.0), agent 2 once (lam 0.05).
    assert core._dose_response_hazard(a1, PATHOGEN_ID, 2.0) == pytest.approx(0.5)
    core._dose_response_hazard(a1, PATHOGEN_ID, 3.0)
    core._dose_response_hazard(a2, PATHOGEN_ID, 0.1)
    ledger.observe(sim, _work(0, tx_events=[_tx(0, 1)]))
    out = hazard_rate_table(ledger)
    assert out["lambda_all"]["n"] == 3
    assert out["lambda_all"]["median"] == pytest.approx(4.0)
    assert out["lambda_all"]["share_ge_1"] == pytest.approx(2 / 3)
    assert out["lambda_all"]["share_lt_0p01"] == pytest.approx(0.0)
    # Agent 1's infecting challenge is its last recorded lambda.
    assert out["lambda_infecting"]["n"] == 1
    assert out["lambda_infecting"]["median"] == pytest.approx(6.0)


def test_hazard_rate_table_empty_is_safe():
    out = hazard_rate_table(HazardRateLedger())
    assert out["lambda_all"]["n"] == 0
    assert out["lambda_all"]["median"] is None
    assert out["lambda_infecting"]["n"] == 0
