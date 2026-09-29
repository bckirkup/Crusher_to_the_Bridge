"""COVID-COOP-02 — cooperative-packet dose-response arm tests."""

from __future__ import annotations

import math

import numpy as np
import pytest

from engines.cooperative_packet import (
    PATHWAY_COOP_CLASS,
    classify_pathway_doses,
    coop_class_weights,
    packet_share,
    poisson_tail,
)
from engines.infection_dynamics_bridge import (
    InfectionStatus,
    KorkinAgent,
)
from engines.transmission_core import ContactTracingMatrix, TransmissionCore

PID = "coop_test_pathogen"
ZONE = "Coop_Test_Zone"
ALPHA = 0.18
BETA = 58.0


def _profile(
    n_star: int = 3,
    mu_dry: float = 0.05,
    mu_wet: float = 20.0,
    model: str = "cooperative_packet",
) -> dict:
    dose_response: dict = {"model": model, "alpha": ALPHA, "beta": BETA}
    if model == "cooperative_packet":
        dose_response["n_star"] = n_star
        dose_response["carrier_loading"] = {"dry": mu_dry, "wet": mu_wet}
    return {
        "dose_response": dose_response,
        "shedding_curve_log10": [2.0] * 12,
        "asymptomatic_shedding_log10": [2.0] * 12,
    }


def _agent(agent_id: int, zone: str = ZONE) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone=zone,
        dining_zone=zone,
        work_zone=zone,
        free_zone=zone,
        schedule=["Free"] * 24,
    )
    agent.current_location = zone
    return agent


def _core(profile: dict, seed: int = 7) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 100.0},
        zone_types={ZONE: "Free"},
        pathogen_profiles={PID: profile},
    )
    core.initialize_zones([ZONE])
    return core


def _inject_dose(
    core: TransmissionCore,
    dose: float,
    pathway: str,
    coop: dict[str, float] | None = None,
) -> None:
    """Fixed-dose injection that also records the pathway key, so the
    cooperative arm sees the channel the dose arrived on."""

    def inject(
        _epoch: int,
        agents: list[KorkinAgent],
        _zone_occupants: dict[str, list[KorkinAgent]],
        _zone_pathogen_mass: dict[str, float],
        _hvac_downstream_zones: dict[str, list[str]] | None,
        _multi_pathogen_mass: dict[str, dict[str, float]] | None,
        pathogen_id: str,
        _agent_doses: dict[int, float],
        agent_pathway_doses: dict[int, dict[str, float]],
        agent_pathogen_doses: dict[int, dict[str, float]],
        _matrix: object,
        _events: list[object],
        agent_coop_doses: dict[int, dict[str, float]] | None = None,
    ) -> None:
        for agent in agents:
            agent_pathogen_doses.setdefault(
                agent.agent_id, {},
            )[pathogen_id] = dose
            pw = agent_pathway_doses.setdefault(agent.agent_id, {})
            key = f"{pathway}:{pathogen_id}"
            pw[key] = pw.get(key, 0.0) + dose
            if coop is not None and agent_coop_doses is not None:
                slot = agent_coop_doses.setdefault(agent.agent_id, {})
                for cls, cls_dose in coop.items():
                    skey = f"{cls}:{pathogen_id}"
                    slot[skey] = slot.get(skey, 0.0) + cls_dose

    core._execute_pathogen_pathways = inject


def _infection_count(
    core: TransmissionCore,
    population: int = 3000,
) -> tuple[int, dict[int, float]]:
    agents = [_agent(aid) for aid in range(population)]
    core.execute_transmission(
        epoch=0, agents=agents, zone_pathogen_mass={ZONE: 0.0},
    )
    infected = sum(
        agent.infection_status == InfectionStatus.INFECTED
        for agent in agents
    )
    susceptibility = {
        a.agent_id: a.dose_response_susceptibility.get(PID)
        for a in agents
    }
    return infected, susceptibility


# ── occupancy helpers ─────────────────────────────────────────────────


class TestPoissonTail:
    def test_n_le_zero_is_certain(self) -> None:
        assert poisson_tail(0.05, 0) == pytest.approx(1.0)
        assert poisson_tail(0.05, -1) == pytest.approx(1.0)

    def test_nonpositive_mu_is_zero(self) -> None:
        assert poisson_tail(0.0, 2) == pytest.approx(0.0)
        assert poisson_tail(-1.0, 2) == pytest.approx(0.0)

    def test_tail_one_matches_survival(self) -> None:
        assert poisson_tail(0.5, 1) == pytest.approx(1.0 - math.exp(-0.5))

    def test_monotone_in_n_and_mu(self) -> None:
        for n in (2, 3, 5):
            assert poisson_tail(0.05, n) < poisson_tail(0.05, n - 1)
            assert poisson_tail(0.5, n) > poisson_tail(0.05, n)

    def test_bounded(self) -> None:
        for mu in (0.004, 0.1, 1.0, 20.0, 500.0):
            for n in (1, 2, 3, 5):
                assert 0.0 <= poisson_tail(mu, n) <= 1.0


class TestPacketShare:
    def test_share_is_bounded_above_one(self) -> None:
        for mu in (0.004, 0.1, 1.0, 20.0, 500.0):
            for n in (1, 2, 3, 5):
                assert 0.0 < packet_share(mu, n) <= 1.0 + 1e-12

    def test_share_collapses_to_poisson_limit(self) -> None:
        # small mu: P(K>=n)/mu -> mu**(n-1)/n!
        assert packet_share(0.001, 3) == pytest.approx(0.001**2 / 6.0,
                                                     rel=1e-3)

    def test_strict_law_suppresses_far_field(self) -> None:
        # dry envelope: n*=3 nearly zeroes the small-carrier share
        assert packet_share(0.05, 3) < 0.005
        assert packet_share(0.05, 5) < 1e-5


class TestCoopClassWeights:
    def test_weights_cover_classes(self) -> None:
        weights = coop_class_weights(_profile()["dose_response"])
        assert set(weights) == {"dry", "wet", "bolus"}
        assert weights["bolus"] == pytest.approx(1.0)
        assert weights["dry"] == pytest.approx(packet_share(0.05, 3))
        assert weights["wet"] == pytest.approx(packet_share(20.0, 3))

    @pytest.mark.parametrize("n_star", [0, -1, 2.5, "3", True])
    def test_n_star_validation(self, n_star: object) -> None:
        with pytest.raises(ValueError):
            coop_class_weights({"n_star": n_star, "carrier_loading": {
                "dry": 0.05, "wet": 20.0}})

    def test_missing_fields_rejected(self) -> None:
        with pytest.raises(ValueError):
            coop_class_weights({})
        with pytest.raises(ValueError):
            coop_class_weights({"n_star": 3})
        with pytest.raises(ValueError):
            coop_class_weights({"n_star": 3, "carrier_loading": {
                "dry": 0.05}})
        with pytest.raises(ValueError):
            coop_class_weights({"n_star": 3, "carrier_loading": {
                "dry": -1.0, "wet": 20.0}})
        with pytest.raises(ValueError):
            coop_class_weights({"n_star": 3, "carrier_loading": {
                "dry": math.inf, "wet": 20.0}})


# ── class split bookkeeping ────────────────────────────────────────────


class TestClassifyPathwayDoses:
    def test_non_droplet_class_map(self) -> None:
        classes = classify_pathway_doses(
            {f"{name}:{PID}": 1.0 for name in PATHWAY_COOP_CLASS},
            PID, None, p_dose=float(len(PATHWAY_COOP_CLASS)),
        )
        for name, cls in PATHWAY_COOP_CLASS.items():
            assert classes[cls] == pytest.approx(1.0) or classes[
                cls] >= 1.0
        assert classes["bolus"] == pytest.approx(4.0)
        assert classes["dry"] == pytest.approx(3.0)

    def test_susceptibility_ratio_rescales(self) -> None:
        classes = classify_pathway_doses(
            {f"hvac_airborne:{PID}": 2.0}, PID, None, p_dose=6.0,
        )
        assert classes["dry"] == pytest.approx(6.0)

    def test_other_pathogen_keys_ignored(self) -> None:
        classes = classify_pathway_doses(
            {f"hvac_airborne:{PID}": 2.0, "hvac_airborne:other_pid": 9.0},
            PID, None, p_dose=2.0,
        )
        assert classes["dry"] == pytest.approx(2.0)

    def test_default_pathogen_bare_keys(self) -> None:
        classes = classify_pathway_doses(
            {"hvac_airborne": 2.0, "droplet": 3.0},
            "_default",
            {"dry": 0.5, "wet": 2.0},
            p_dose=5.0,
        )
        assert classes["dry"] == pytest.approx(0.5 + 2.0)
        assert classes["wet"] == pytest.approx(2.0)

    def test_droplet_split_comes_from_coop_ledger(self) -> None:
        classes = classify_pathway_doses(
            {f"droplet:{PID}": 10.0},
            PID,
            {f"dry:{PID}": 4.0, f"wet:{PID}": 6.0},
            p_dose=10.0,
        )
        assert classes["dry"] == pytest.approx(4.0)
        assert classes["wet"] == pytest.approx(6.0)
        assert classes["bolus"] == pytest.approx(0.0)

    def test_droplet_lump_without_split_falls_back_wet(self) -> None:
        classes = classify_pathway_doses(
            {f"droplet:{PID}": 10.0, f"hvac_airborne:{PID}": 1.0},
            PID, None, p_dose=11.0,
        )
        assert classes["wet"] == pytest.approx(10.0)
        assert classes["dry"] == pytest.approx(1.0)

    def test_unknown_pathway_is_dry(self) -> None:
        classes = classify_pathway_doses(
            {f"unlisted:{PID}": 4.0}, PID, None, p_dose=4.0,
        )
        assert classes["dry"] == pytest.approx(4.0)


# ── engine-level arm behaviour ─────────────────────────────────────────


class TestArmHazard:
    def test_bolus_only_matches_baseline_exactly(self) -> None:
        baseline = _core(_profile(model="beta_poisson"), seed=19)
        _inject_dose(baseline, 500.0, "direct_contact")
        coop = _core(_profile(), seed=19)
        _inject_dose(coop, 500.0, "direct_contact")
        base_infected, base_susc = _infection_count(baseline)
        coop_infected, coop_susc = _infection_count(coop)
        # bolus weight 1.0 + preserved frailty draw = identical draw stream
        assert base_infected == coop_infected
        assert base_susc == coop_susc

    def test_dry_dose_is_suppressed_under_strict_law(self) -> None:
        baseline = _core(_profile(model="beta_poisson"), seed=23)
        _inject_dose(baseline, 500.0, "hvac_airborne")
        base_infected, _ = _infection_count(baseline)
        coop = _core(_profile(n_star=3, mu_dry=0.05), seed=23)
        _inject_dose(coop, 500.0, "hvac_airborne")
        coop_infected, _ = _infection_count(coop)
        assert base_infected > 0
        assert coop_infected < base_infected * 0.1

    def test_n_star_orders_suppression(self) -> None:
        counts = []
        for n_star in (2, 3, 5):
            coop = _core(_profile(n_star=n_star, mu_dry=0.05), seed=23)
            _inject_dose(coop, 500.0, "hvac_airborne")
            counts.append(_infection_count(coop)[0])
        assert counts[0] >= counts[1] >= counts[2]
        assert counts[0] > counts[2]

    def test_wet_dose_less_suppressed_than_dry(self) -> None:
        # wet carrier_loading mu=20 with n*=2 keeps a real share; dry at
        # mu=0.05 under the same law is far more suppressed
        wet_run = _core(
            _profile(n_star=2, mu_dry=0.05, mu_wet=20.0), seed=29)
        _inject_dose(
            wet_run, 500.0, "droplet",
            coop={"wet": 500.0},
        )
        dry_run = _core(
            _profile(n_star=2, mu_dry=0.05, mu_wet=20.0), seed=29)
        _inject_dose(dry_run, 500.0, "hvac_airborne")
        wet_infected, _ = _infection_count(wet_run)
        dry_infected, _ = _infection_count(dry_run)
        assert wet_infected > dry_infected

    def test_unknown_model_rejected(self) -> None:
        core = _core(_profile(model="coop_typo"))
        with pytest.raises(ValueError, match="unknown dose_response"):
            core._dose_response_model(PID)

    def test_frailty_draw_preserved(self) -> None:
        # same draw object the baseline hazard consumes
        coop = _core(_profile(), seed=31)
        agent = _agent(0)
        susc = coop._dose_response_susceptibility(agent, PID)
        base = _core(_profile(model="beta_poisson"), seed=31)
        base_agent = _agent(0)
        base_susc = base._dose_response_susceptibility(base_agent, PID)
        assert susc == base_susc

    def test_cooperative_hazard_matches_packet_share(self) -> None:
        core = _core(_profile(n_star=3, mu_dry=0.05, mu_wet=20.0), seed=37)
        agent = _agent(0)
        agent.dose_response_susceptibility[PID] = 1.0
        hazard = core._cooperative_hazard(
            agent, PID, 10.0, 10.0,
            {0: {f"hvac_airborne:{PID}": 10.0}},
            {0: {}},
        )
        expected = -math.expm1(-1.0 * 10.0 * packet_share(0.05, 3))
        assert hazard == pytest.approx(expected)

    def test_protection_scales_class_doses(self) -> None:
        core = _core(_profile(), seed=41)
        agent = _agent(0)
        agent.dose_response_susceptibility[PID] = 1.0
        classes = {f"fomite:{PID}": 10.0}
        full = core._cooperative_hazard(
            agent, PID, 10.0, 10.0, {0: classes}, None,
        )
        half = core._cooperative_hazard(
            agent, PID, 10.0, 5.0, {0: classes}, None,
        )
        assert half == pytest.approx(
            -math.expm1(-1.0 * 5.0 * 1.0),
        )
        assert full > half


# ── droplet sub-term recording ─────────────────────────────────────────


class TestDropletClassBookkeeping:
    def _droplet_core(self, cabin_mode: bool) -> TransmissionCore:
        cfg = {"transmission": {"cabin_air_mode": (
            "cabin_compartment" if cabin_mode else "zone_pool")}}
        zone = "CC_Block" if cabin_mode else ZONE
        core = TransmissionCore(
            rng=np.random.default_rng(3),
            zone_volumes={zone: 300.0},
            zone_types={
                zone: "Cabin_Corridor" if cabin_mode else "Free",
            },
            pathogen_profiles={PID: _profile()},
            cfg=cfg,
        )
        core.initialize_zones([zone])
        return core

    def test_corridor_pool_records_dry(self) -> None:
        core = self._droplet_core(cabin_mode=False)
        shedder = _agent(1)
        target = _agent(2)
        core._get_shedders = lambda occ, pid, prof: [(shedder, 5.0)]
        core._get_susceptible = lambda occ, pid: [target]
        p_coop: dict[int, dict[str, float]] = {}
        p_pw: dict[int, dict[str, float]] = {}
        core._pathway_droplet(
            0, {ZONE: [shedder, target]}, {}, ContactTracingMatrix(epoch=0),
            [], p_pw, pathogen_id=PID, profile=_profile(), ledger=None,
            agent_coop_doses=p_coop,
        )
        slot = p_coop.get(2, {})
        lump = p_pw.get(2, {}).get("droplet", 0.0)
        assert lump > 0.0
        assert slot.get("dry", 0.0) > 0.0
        assert slot.get("dry", 0.0) + slot.get("wet", 0.0) == pytest.approx(
            lump,
        )

    def test_compartment_pool_records_wet(self) -> None:
        core = self._droplet_core(cabin_mode=True)
        shedder = _agent(1, "CC_Block")
        target = _agent(2, "CC_Block")
        shedder.cabin_mate_ids = frozenset({2})
        target.cabin_mate_ids = frozenset({1})
        core.register_cabin_berths([shedder, target])
        core._get_shedders = lambda occ, pid, prof: [(shedder, 5.0)]
        core._get_susceptible = lambda occ, pid: [target]
        p_coop: dict[int, dict[str, float]] = {}
        p_pw: dict[int, dict[str, float]] = {}
        core._pathway_droplet(
            0, {"CC_Block": [shedder, target]}, {},
            ContactTracingMatrix(epoch=0), [], p_pw,
            pathogen_id=PID, profile=_profile(), ledger=None,
            agent_coop_doses=p_coop,
        )
        slot = p_coop.get(2, {})
        lump = p_pw.get(2, {}).get("droplet", 0.0)
        assert lump > 0.0
        assert slot.get("wet", 0.0) > 0.0
        assert slot.get("dry", 0.0) == pytest.approx(0.0)
        assert slot["wet"] == pytest.approx(lump)
