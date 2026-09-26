"""Coverage for tools/covid_route_attribution.py pure helpers."""

import math
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
    out = ascertainment_funnel(sim, record_dating_rate_confirmed=197.0 / 712.0)
    assert out["infected_truth"] == 3  # agent 4 excluded as seeded
    assert out["symptomatic_at_end"] == 3
    assert out["eligible_severity_course"] == 2  # subclinical not eligible
    assert out["lab_confirmed_total"] == 3
    assert out["confirmed_datable"] == 2
    assert out["dated_onsets"] == 2
    assert out["dated_by_severity"] == {"mild": 1, "moderate": 1}
    assert out["dating_rate_confirmed_datable"] == pytest.approx(1.0)
    assert out["dating_rate_confirmed"] == pytest.approx(2 / 3)
    assert out["record_dating_rate_confirmed"] == pytest.approx(197.0 / 712.0)


def test_ascertainment_funnel_record_rate_is_optional():
    agents = [_agent(1, _infected(IllnessStatus.SYMPTOMATIC, "mild"))]
    sim = _funnel_sim(agents, confirmed={1}, dated={1: {"symptom_severity": "mild"}})
    assert "record_dating_rate_confirmed" not in ascertainment_funnel(sim)
    other_pid = "norwalk_gi"
    sim.pathogen_profiles[other_pid] = sim.pathogen_profiles.pop(PATHOGEN_ID)
    agents[0].infections = {other_pid: agents[0].infections.pop(PATHOGEN_ID)}
    sim.modalities["syndromic"]._lab_confirmed = {(other_pid, 1): 100}
    sim.modalities["syndromic"]._onset_observations = {
        (other_pid, 1): {"symptom_severity": "mild"}
    }
    out = ascertainment_funnel(sim, pathogen_id=other_pid)
    assert out["infected_truth"] == 1
    assert out["dated_onsets"] == 1


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


def _cabin_sim(agents, quarantined=frozenset(), seed=8105, profiles=None):
    engine = SimpleNamespace(agents=agents)
    tx_core = SimpleNamespace(
        _quarantined_ids=set(quarantined),
        pathogen_profiles=profiles or {},
    )
    return SimpleNamespace(
        engine=engine,
        tx_core=tx_core,
        run_spec=SimpleNamespace(random_seed=seed),
        _epoch=0,
    )


def _cabin_agent(aid, mate_ids, infections=None, susc=None):
    return SimpleNamespace(
        agent_id=aid,
        cabin_mate_ids=set(mate_ids),
        home_zone="zCabin",
        infections=infections or {},
        dose_response_susceptibility=susc or {},
    )


def _observe_work(epoch, **records):
    matrix = SimpleNamespace(
        droplet_exposures=records.get("droplet", []),
        shared_room_exposures=records.get("contact", []),
        hvac_downstream_exposures=records.get("hvac", []),
        emesis_aerosol_exposures=records.get("emesis", []),
        flush_aerosol_exposures=records.get("flush", []),
    )
    return SimpleNamespace(epoch=epoch, tracing_matrix=matrix)


from tools.covid_route_attribution import (  # noqa: E402
    CabinPairChallengeLedger,
    cabin_compartment_key,
    cabin_pair_challenge_table,
)


class TestCabinPairChallengeLedger:
    """CABIN-OCC-01's lambda instrument on synthetic exposure records."""

    def test_cabin_compartment_key_uses_zone_and_min_member(self):
        a = _cabin_agent(7, {3})
        assert cabin_compartment_key(a) == "zCabin::cabin3"
        assert cabin_compartment_key(_cabin_agent(9, set())) is None

    def test_observe_tallies_directed_dose_per_channel(self):
        mates = [_cabin_agent(1, {2}), _cabin_agent(2, {1}),
                 _cabin_agent(9, set())]
        ledger = CabinPairChallengeLedger()
        sim = _cabin_sim(mates, quarantined={1, 2})
        ledger.observe(sim, _observe_work(5, droplet=[
            {"air_unit": "zCabin::cabin1", "target_id": 2,
             "pathogen_id": "p", "dose": 1.0, "near_field_dose": 0.25},
        ]))
        ledger.observe(sim, _observe_work(6, hvac=[
            {"air_unit": "zCabin::cabin1", "target_id": 2,
             "pathogen_id": "p", "dose": 0.5},
            {"air_unit": "other", "target_id": 2,
             "pathogen_id": "p", "dose": 99.0},
        ]))
        key = (1, 2)
        doses = ledger.directed_dose[(key, 2)]["p"]
        assert doses["pool"] == pytest.approx(0.75)
        assert doses["plume"] == pytest.approx(0.25)
        assert doses["hvac"] == pytest.approx(0.5)
        assert ledger.shared_epochs[key] == 2
        assert ledger.confined_epochs[key] == 2
        assert ledger.confined_first[key] == 5
        assert ledger.confined_last[key] == 6

    def test_observe_skips_non_members_and_zero_dose(self):
        mates = [_cabin_agent(1, {2}), _cabin_agent(2, {1})]
        ledger = CabinPairChallengeLedger()
        sim = _cabin_sim(mates)
        ledger.observe(sim, _observe_work(0, droplet=[
            {"air_unit": "zCabin::cabin1", "target_id": 9,
             "pathogen_id": "p", "dose": 5.0},
            {"air_unit": "zCabin::cabin1", "target_id": 2,
             "pathogen_id": "p", "dose": 0.0},
        ]))
        assert ledger.directed_dose == {}

    def test_observe_without_matrix_only_counts_confinement(self):
        mates = [_cabin_agent(1, {2}), _cabin_agent(2, {1})]
        ledger = CabinPairChallengeLedger()
        sim = _cabin_sim(mates, quarantined={1, 2})
        ledger.observe(sim, SimpleNamespace(epoch=3, tracing_matrix=None))
        assert ledger.confined_epochs[(1, 2)] == 1
        assert ledger.directed_dose == {}

    def test_table_engine_draw_lambda_and_implied_sar(self):
        profiles = {"p": {"dose_response": {"alpha": 2.0, "beta": 8.0}}}
        mates = [
            _cabin_agent(1, {2}, infections={"p": {"infection_epoch": 4}},
                         susc={"p": 0.5}),
            _cabin_agent(2, {1}, susc={"p": 0.5}),
        ]
        ledger = CabinPairChallengeLedger()
        sim = _cabin_sim(mates, quarantined={1, 2}, profiles=profiles)
        ledger.observe(sim, _observe_work(7, droplet=[
            {"air_unit": "zCabin::cabin1", "target_id": 2,
             "pathogen_id": "p", "dose": 2.0},
        ]))
        table = cabin_pair_challenge_table(ledger, sim)
        row = table["rows"][0]
        assert row["lambda"] == pytest.approx(1.0)
        assert row["susceptibility"] == "engine_draw"
        assert row["implied_sar"] == pytest.approx(1 - math.exp(-1))
        assert table["mate_index_pairs"] == 1
        assert table["observed_mate_case_attack"] == pytest.approx(0.0)
        assert table["confined_index_pairs"] == 1
        assert table["observed_mate_case_attack_confined"] == pytest.approx(0.0)

    def test_table_counterfactual_draw_and_confined_conversion(self):
        profiles = {"p": {"dose_response": {"alpha": 1.0, "beta": 1.0}}}
        mates = [
            _cabin_agent(1, {2}, infections={"p": {"infection_epoch": 1,
                                                  "first_infection_epoch": 1}}),
            _cabin_agent(2, {1}, infections={"p": {"infection_epoch": 6,
                                                  "first_infection_epoch": 6}}),
        ]
        ledger = CabinPairChallengeLedger()
        sim = _cabin_sim(mates, profiles=profiles)
        ledger.observe(sim, _observe_work(0))
        sim2 = _cabin_sim(mates, quarantined={1, 2}, profiles=profiles)
        ledger.observe(sim2, _observe_work(6, contact=[
            {"compartment": "zCabin::cabin1", "target_id": 2,
             "pathogen_id": "p", "dose": 3.0},
        ]))
        table = cabin_pair_challenge_table(ledger, sim2)
        row = table["rows"][0]
        assert row["susceptibility"] == "counterfactual"
        assert 0.0 < row["lambda"]
        assert table["observed_mate_case_attack_confined"] == pytest.approx(1.0)

    def test_table_exponential_model_and_preconfined_mate(self):
        profiles = {"p": {"dose_response": {"model": "exponential",
                                          "k": 0.01}}}
        mates = [
            _cabin_agent(1, {2}, infections={"p": {"infection_epoch": 1,
                                                  "first_infection_epoch": 1}}),
            # Mate seroconverted before confinement began at epoch 6.
            _cabin_agent(2, {1}, infections={"p": {"infection_epoch": 3,
                                                  "first_infection_epoch": 3}}),
        ]
        ledger = CabinPairChallengeLedger()
        sim = _cabin_sim(mates, profiles=profiles)
        ledger.observe(sim, _observe_work(0))
        sim2 = _cabin_sim(mates, quarantined={1, 2}, profiles=profiles)
        ledger.observe(sim2, _observe_work(6, droplet=[
            {"air_unit": "zCabin::cabin1", "target_id": 2,
             "pathogen_id": "p", "dose": 4.0},
        ]))
        table = cabin_pair_challenge_table(ledger, sim2)
        row = table["rows"][0]
        assert row["susceptibility"] == "counterfactual"
        assert row["lambda"] == pytest.approx(0.04)
        # Pre-confinement conversion: pair confined but mate held no
        # confined-exposure slot, so the confined denominator is empty.
        assert table["confined_index_pairs"] == 1
        assert table["observed_mate_case_attack_confined"] is None
        assert table["observed_mate_case_attack"] == pytest.approx(1.0)

    def test_table_skips_uninfected_and_unconfined_pairs(self):
        profiles = {"p": {"dose_response": {"alpha": 1.0, "beta": 1.0}}}
        # pair_a's index is infected but the pair never confines; pair_b's
        # member is infected with a pathogen the pair never exchanged.
        pair_a = [_cabin_agent(
            1, {2}, infections={"p": {"infection_epoch": 1}}),
            _cabin_agent(2, {1})]
        pair_b = [_cabin_agent(
            3, {4}, infections={"q": {"infection_epoch": 1}}),
            _cabin_agent(4, {3})]
        pair_c = [_cabin_agent(5, {6}), _cabin_agent(6, {5})]
        ledger = CabinPairChallengeLedger()
        sim = _cabin_sim(pair_a + pair_b + pair_c, quarantined={3, 4, 5, 6},
                         profiles=profiles)
        ledger.observe(sim, _observe_work(2, droplet=[
            {"air_unit": "zCabin::cabin1", "target_id": 2,
             "pathogen_id": "p", "dose": 1.0},
            {"air_unit": "zCabin::cabin3", "target_id": 4,
             "pathogen_id": "p", "dose": 1.0},
            {"air_unit": "zCabin::cabin5", "target_id": 6,
             "pathogen_id": "p", "dose": 1.0},
        ]))
        table = cabin_pair_challenge_table(ledger, sim)
        assert len(table["rows"]) == 3
        # pair_a contributes an index pair (one infected member) with no
        # secondary; pair_b's infection is off-pathogen so it is skipped.
        assert table["mate_index_pairs"] == 1
        assert table["observed_mate_case_attack"] == pytest.approx(0.0)
        # pair_a never confined; pair_b's confinement tally can't reach the
        # confined-window branch — no confined index pair forms.
        assert table["confined_index_pairs"] == 0
        assert table["observed_mate_case_attack_confined"] is None

    def test_table_empty_ledger_is_safe(self):
        ledger = CabinPairChallengeLedger()
        sim = _cabin_sim([], profiles={})
        table = cabin_pair_challenge_table(ledger, sim)
        assert table["pairs_observed"] == 0
        assert table["observed_mate_case_attack"] is None
        assert table["observed_mate_case_attack_confined"] is None
