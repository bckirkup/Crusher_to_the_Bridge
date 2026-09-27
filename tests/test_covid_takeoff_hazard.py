"""Coverage for the accrued-hazard instrument on TakeoffAttributionLedger.

The ledger observes each epoch's dose-response challenges; a host's
accrued hazard Lambda = sum of susc * p_dose * (1 - protection) over the
epochs it was challenged and still susceptible, so its counterfactual
infection probability is 1 - exp(-Lambda).
"""
from types import SimpleNamespace

import pytest

from tools.covid_takeoff_attribution import PATHOGEN_ID, TakeoffAttributionLedger

PID = PATHOGEN_ID


class _FakeCore:
    """The five methods the ledger wraps, plus protection lookup."""

    def __init__(self):
        self.infect_on_resolve = False

    def _record_droplet_exposure(self, *a, **k):
        return None

    def _cabin_mate_droplet_addback(self, *a, **k):
        return 0.0

    def _near_field_droplet_dose(self, *a, **k):
        return 0.0

    def _near_field_unit(self, *a, **k):
        return 0.0

    def _challenge_protection(self, agent, pid, epoch):
        return 0.25

    def _resolve_pathogen_challenge(
        self, epoch, agent, pathogen_id, apd, apw, matrix, events,
    ):
        if self.infect_on_resolve:
            agent.infections[pathogen_id] = object()


def _agent(aid, susc):
    return SimpleNamespace(
        agent_id=aid,
        infections={},
        dose_response_susceptibility={PID: susc},
        current_location="zCabin",
        role="passenger",
        is_infected_with=lambda pid: pid in SimpleNamespace(
            **{}
        ) or False,
    )


def _sim(agents):
    engine = SimpleNamespace(
        agents=agents,
        explicit_seed_agent_ids=set(),
        quarantined_ids=set(),
    )
    return SimpleNamespace(engine=engine)


def _work(epoch):
    return SimpleNamespace(epoch=epoch, tracing_matrix=None, tx_events=[])


def _make():
    agents = [_agent(1, 0.5), _agent(2, 2.0)]
    for a in agents:
        a.is_infected_with = (
            lambda pid, _a=a: pid in _a.infections
        )
        a.has_departed = lambda epoch: False
    sim = _sim(agents)
    sim.tx_core = _FakeCore()
    ledger = TakeoffAttributionLedger()
    ledger.observe(sim, _work(0))  # installs the wrappers
    return ledger, sim, agents


def _challenge(sim, agent, epoch, p_dose):
    sim.tx_core._resolve_pathogen_challenge(
        epoch, agent, PID, {agent.agent_id: {PID: p_dose}},
        {}, None, [],
    )


def test_accrued_hazard_accumulates_per_challenged_host():
    ledger, sim, agents = _make()
    _challenge(sim, agents[0], 0, 0.4)
    _challenge(sim, agents[1], 0, 0.1)
    ledger.observe(sim, _work(0))
    # susc * p_dose * (1 - protection): host1 0.5*0.4*0.75, host2 2*0.1*0.75.
    assert ledger.accrued_hazard[1] == pytest.approx(0.15)
    assert ledger.accrued_hazard[2] == pytest.approx(0.15)

    _challenge(sim, agents[0], 1, 0.4)
    ledger.observe(sim, _work(1))
    assert ledger.accrued_hazard[1] == pytest.approx(0.30)
    assert ledger.accrued_hazard[2] == pytest.approx(0.15)


def test_accrued_hazard_includes_terminal_epoch_for_infected():
    ledger, sim, agents = _make()
    sim.engine.quarantined_ids = set()
    _challenge(sim, agents[0], 0, 0.4)
    ledger.observe(sim, _work(0))
    sim.tx_core.infect_on_resolve = True
    _challenge(sim, agents[0], 1, 0.4)
    # Onset event for host 1 at epoch 1.
    ev = SimpleNamespace(
        target_agent_id=1, zone="zCabin",
        acquired_particles_by_route={"droplet": 0.4},
    )
    work = _work(1)
    work.tx_events = [ev]
    # _onset_row needs the sim surface it reads.
    sim.clock = SimpleNamespace(day_index=lambda e: int(e) // 24)
    sim.run_spec = SimpleNamespace(random_seed=0)
    sim.engine.agents[0].infections[PID] = object()
    ledger.observe(sim, work)
    # Λ for host 1 = two challenged epochs * 0.15; the onset row carries it.
    assert ledger.accrued_hazard[1] == pytest.approx(0.30)
    row = ledger.onsets[0]
    assert row["hazard_at_onset"] == pytest.approx(0.30)
    # Host never challenged keeps no entry.
    assert 2 not in ledger.accrued_hazard


def test_challenge_with_no_dose_records_nothing():
    ledger, sim, agents = _make()
    _challenge(sim, agents[0], 0, 0.0)
    ledger.observe(sim, _work(0))
    assert ledger.accrued_hazard == {}


def test_summarise_reports_counterfactual_p_infection():
    import math

    from tools.covid_takeoff_attribution import summarise

    ledger, sim, agents = _make()
    sim.clock = SimpleNamespace(day_index=lambda e: int(e) // 24)
    sim.run_spec = SimpleNamespace(random_seed=0)
    sim.tx_core.pathogen_profiles = {}
    # Host 1 challenged twice (Λ=0.30), host 2 once (Λ=0.15).
    _challenge(sim, agents[0], 0, 0.4)
    _challenge(sim, agents[1], 0, 0.1)
    ledger.observe(sim, _work(0))
    _challenge(sim, agents[0], 1, 0.4)
    ledger.observe(sim, _work(1))

    out = summarise(
        sim, ledger, {"observables": {"recorded_onsets": 0}}, 10,
    )
    acc = out["mechanism"]["susceptibility"]["accrued_hazard"]
    p1 = 1.0 - math.exp(-0.30)
    p2 = 1.0 - math.exp(-0.15)
    assert acc["challenged_uninfected_p_infection_mean"] == pytest.approx(
        (p1 + p2) / 2,
    )
    # _quantiles uses nearest-index (s[int(p*n)]): median of two = upper.
    assert acc["challenged_uninfected"]["median"] == pytest.approx(0.30)
    assert acc["challenged_uninfected_share_p_ge_0p5"] == pytest.approx(0.0)
    assert acc["never_challenged_hosts"] == 0
