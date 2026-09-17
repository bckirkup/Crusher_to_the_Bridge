"""Blackwater holding tank and copies/L assay: conservation, LOD, gating.

Slice 2 of the environmental-observability work
(``docs/norovirus/environmental_observation_v1.md`` §3): excreta mass that
was dropped on the floor reaches a CSTR holding tank, and a mass-based
copies/L qPCR assay with a sourced composite LOD reads it. Everything is
additive and default-off — the tank removes nothing from any existing pool.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import numpy as np
import pytest

from crusher_labs.observation_core import (
    WW_ASSAY_LOD_COPIES_PER_UL,
    WastewaterHoldingTankAssay,
)
from engines.infection_dynamics_bridge import IllnessStatus, KorkinAgent
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import (
    CABIN_COMPARTMENT_SEPARATOR,
    FLUSH_STOOL_MASS_G,
    TransmissionCore,
)
from engines.wastewater_plumbing import (
    BLACKWATER_L_PER_PERSON_DAY,
    BLACKWATER_RESIDENCE_HOURS,
    BlackwaterHoldingTank,
)

PATHOGEN = "norwalk_gi"
HEAD = "HD_5T_M"
THEATER = "TheaterLng"
ZONE = "Cabin_A"
CABIN_ZONE = "PC_D5_P_F"
COMPARTMENT = f"{CABIN_ZONE}{CABIN_COMPARTMENT_SEPARATOR}1"


# ── Tank dynamics ────────────────────────────────────────────────────────


class TestLodDerivation:
    def test_composite_lod_matches_the_workflow_derivation(self) -> None:
        assay = WastewaterHoldingTankAssay(rng=np.random.default_rng(1))
        assert assay.lod_copies_per_l() == pytest.approx(
            WW_ASSAY_LOD_COPIES_PER_UL["GII"] * 100.0 / (0.1 * 0.25),
            rel=1e-6,
        )

    def test_gi_lod_is_strictly_lower_and_loq_above_lod(self) -> None:
        gi = WastewaterHoldingTankAssay(
            genogroup="GI", rng=np.random.default_rng(1),
        )
        gii = WastewaterHoldingTankAssay(rng=np.random.default_rng(1))
        assert gi.lod_copies_per_l() < gii.lod_copies_per_l()
        for inst in (gi, gii):
            assert inst.loq_copies_per_l() > inst.lod_copies_per_l()


class TestTankConservation:
    def test_copies_sum_and_telemetry_tracks_inflow(self) -> None:
        tank = BlackwaterHoldingTank()
        for copies in (1.0e6, 2.5e6, 4.0e5):
            tank.add_copies(PATHOGEN, copies, "stool")
        tank.add_copies("other_pid", 1.0e3, "emesis")
        assert tank.copies_by_pathogen[PATHOGEN] == pytest.approx(3.9e6)
        assert tank.telemetry["copies_in"] == pytest.approx(3.901e6)
        assert tank.telemetry["stool_events"] == 3
        assert tank.telemetry["emesis_events"] == 1

    def test_nonfinite_and_zero_copies_are_ignored(self) -> None:
        tank = BlackwaterHoldingTank()
        for bad in (0.0, -5.0, math.inf, math.nan):
            tank.add_copies(PATHOGEN, bad, "stool")
        assert tank.copies_by_pathogen == {}
        assert tank.telemetry["copies_in"] == pytest.approx(0.0)
        assert tank.telemetry["stool_events"] == 0


class TestCstrDischarge:
    def test_one_epoch_discharges_exactly_the_residence_fraction(self) -> None:
        tank = BlackwaterHoldingTank()
        tank.complement = 500
        tank.add_copies(PATHOGEN, 1.0e9, "stool")
        tank.advance_epoch(hours_per_epoch=1.0, day_fraction_per_epoch=1.0 / 24)
        drain = 1.0 / BLACKWATER_RESIDENCE_HOURS
        volume_in = 500 * BLACKWATER_L_PER_PERSON_DAY / 24.0
        assert tank.volume_l == pytest.approx(volume_in * (1.0 - drain))
        assert tank.copies_by_pathogen[PATHOGEN] == pytest.approx(
            1.0e9 * (1.0 - drain),
        )
        kept = tank.copies_by_pathogen[PATHOGEN]
        assert kept + tank.telemetry["copies_discharged"] == pytest.approx(
            1.0e9,
        )


class TestSteadyState:
    def test_volume_converges_to_rate_times_residence(self) -> None:
        tank = BlackwaterHoldingTank()
        tank.complement = 500
        for _ in range(24 * 200):
            tank.advance_epoch(1.0, 1.0 / 24)
        # Discrete-time steady state of the implemented update
        # (inflow then drain at h/residence): inflow x (1 - f) / f, the
        # CSTR limit rate x residence up to the epoch-step correction.
        inflow = 500 * BLACKWATER_L_PER_PERSON_DAY / 24.0
        drain = 1.0 / BLACKWATER_RESIDENCE_HOURS
        assert tank.volume_l == pytest.approx(
            inflow * (1.0 - drain) / drain, rel=0.01,
        )

    def test_longer_residence_retains_more_copies(self) -> None:
        retained = []
        for residence in (10.0, 62.0, 150.0):
            tank = BlackwaterHoldingTank(residence_hours=residence)
            tank.complement = 100
            for _ in range(48):
                tank.add_copies(PATHOGEN, 1.0e6, "stool")
                tank.advance_epoch(1.0, 1.0 / 24)
            retained.append(tank.copies_by_pathogen[PATHOGEN])
        assert retained == sorted(retained)


class TestAssayDetection:
    @pytest.mark.parametrize("volume", [1.0e3, 1.0e4, 1.0e5])
    def test_dilution_is_exact(self, volume: float) -> None:
        assay = WastewaterHoldingTankAssay(rng=np.random.default_rng(1))
        result = assay.assay(volume, {PATHOGEN: 1.0e7})
        assert result["concentration_copies_per_l"] == pytest.approx(
            1.0e7 / volume,
        )

    def test_detection_is_monotone_and_crosses_once_at_the_lod(self) -> None:
        assay_lod = WastewaterHoldingTankAssay(
            rng=np.random.default_rng(1),
        ).lod_copies_per_l()
        detected = []
        for exponent in range(2, 9):
            concentration = 10.0 ** exponent
            result = WastewaterHoldingTankAssay(
                rng=np.random.default_rng(3),
            ).assay(1.0e6, {PATHOGEN: concentration * 1.0e6})
            detected.append(result["detected"])
            if not result["detected"] and result["concentration_copies_per_l"] > 0:
                assert result["censored_below_lod"] is True
        # Non-decreasing, and the single crossing brackets the LOD.
        assert detected == sorted(detected)
        assert detected[0] is False
        assert detected[-1] is True
        crossing = detected.index(True)
        assert 10.0 ** (crossing + 2) <= assay_lod * 30.0

    def test_zero_inputs_are_safe(self) -> None:
        assay = WastewaterHoldingTankAssay(rng=np.random.default_rng(1))
        for volume, copies in ((0.0, {PATHOGEN: 1.0e9}), (1.0e3, {}), (-1.0, {PATHOGEN: 5.0})):
            result = assay.assay(volume, copies)
            assert result["concentration_copies_per_l"] == pytest.approx(0.0)
            assert result["detected"] is False
            assert result["quantifiable"] is False
            assert result["censored_below_lod"] is False
            assert result["ct_value"] is None
            assert result["log10_copies_per_l"] is None
            for key in (
                "tank_volume_l", "tank_copies_total", "sampled_copies",
                "recovered_copies", "eluate_copies_per_ul",
                "copies_per_reaction", "lod_copies_per_l", "loq_copies_per_l",
            ):
                value = float(result[key])
                assert math.isfinite(value)
                assert value >= 0.0

    def test_municipal_sewage_concentration_is_detected(self) -> None:
        """Sourced-anchor invariant: measured raw municipal sewage GII runs
        5.2-7.9 log10 copies/L (Jahne et al. 2020,
        doi:10.1016/j.watres.2019.115213; Fumian et al. 2019,
        doi:10.1016/j.envint.2018.11.054, GII median ~6.4 log10), far above
        the 3.74 log10 composite LOD — detection is expected, not tuned."""
        assay = WastewaterHoldingTankAssay(rng=np.random.default_rng(1))
        result = assay.assay(1.0e4, {PATHOGEN: 10.0 ** 6.1 * 1.0e4})
        assert result["detected"] is True
        assert result["quantifiable"] is True
        assert result["censored_below_lod"] is False


# ── Core routing fixtures ────────────────────────────────────────────────


def _profile(**overrides: object) -> dict:
    profile: dict[str, object] = {
        "symptom_onset_day": 0.0,
        "recovery_day": 5,
        "clinical_presentation": {
            "phases": [
                {
                    "name": "acute",
                    "dpi_min": 0,
                    "dpi_max": 2,
                    "features": ["vomiting"],
                },
                {
                    "name": "resolving",
                    "dpi_min": 3,
                    "dpi_max": None,
                    "features": ["watery_diarrhea"],
                },
            ],
        },
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "stool_events_per_day": {"baseline": 5.63, "diarrhoeal": 5.63},
        "dose_response": {"model": "exponential", "k": 0.01},
    }
    profile.update(overrides)
    return profile


def _agent(aid: int = 1, location: str = THEATER) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 24,
    )
    agent.current_location = location
    return agent


def _shedder(core: TransmissionCore, aid: int = 1,
             location: str = THEATER) -> KorkinAgent:
    agent = _agent(aid, location)
    agent.clock = core.clock
    agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=0)
    agent.infections[PATHOGEN]["onset_time_infected"] = 0
    agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    agent.hand_load_by_pathogen[PATHOGEN] = 10.0
    return agent


def _core(
    flush_fraction: float | None = None,
    *,
    blackwater: bool | dict = False,
    mode: str = "dwell_weighted",
    seed: int = 11,
) -> TransmissionCore:
    tx: dict[str, object] = {
        "sanitary_visit_mode": mode,
        "blackwater_plumbing": blackwater,
    }
    if flush_fraction is not None:
        tx["flush_aerosol_fraction"] = flush_fraction
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={HEAD: 30.0, THEATER: 4000.0, CABIN_ZONE: 800.0},
        zone_types={
            HEAD: "Sanitary",
            THEATER: "Free",
            CABIN_ZONE: "Cabin_Corridor",
        },
        zone_floor_areas={HEAD: 27.0},
        sanitary_zone_map={THEATER: {"male": HEAD}},
        pathogen_profiles={PATHOGEN: _profile()},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        cfg={"transmission": tx},
    )
    return core


def _force_stool_event(core: TransmissionCore, agent: KorkinAgent,
                       zone_name: str) -> None:
    core._stool_event_occurs = lambda rate: True
    core._replenish_hand(
        agent, PATHOGEN, core.pathogen_profiles[PATHOGEN],
        zone_name=zone_name,
    )


# ── Routing conservation ─────────────────────────────────────────────────


class TestStoolRouting:
    @pytest.mark.parametrize("fraction", [0.0, 1e-6])
    def test_bowl_deposit_conserves_across_air_and_tank(
        self, fraction: float,
    ) -> None:
        """aerosol + blackwater == bowl copies at both f_aero extremes;
        at 0.0 the tank still credits (the early-return regression)."""
        core = _core(fraction, blackwater=True, seed=7)
        shedder = _shedder(core)
        titre = shedder.get_pathogen_stool_titre_log10(
            PATHOGEN, core.pathogen_profiles[PATHOGEN],
        )
        _force_stool_event(core, shedder, THEATER)
        bowl = 10.0 ** titre * FLUSH_STOOL_MASS_G
        tank = core.blackwater_tank
        assert tank is not None
        assert tank.copies_by_pathogen.get(PATHOGEN, 0.0) == pytest.approx(
            bowl * (1.0 - fraction), rel=1e-9,
        )
        aerosol = core.sanitary_telemetry["flush_aerosol_emitted"]
        assert aerosol + tank.copies_by_pathogen[PATHOGEN] == pytest.approx(
            bowl, rel=1e-9,
        )
        assert tank.telemetry["stool_events"] == 1


class TestEmesisDrainRouting:
    def _deposit(
        self, core: TransmissionCore, agent: KorkinAgent,
    ) -> dict:
        agent.clock = core.clock
        agent.infections[PATHOGEN]["time_infected"] = 0
        agent.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0]
        core._deposit_emesis(agent, PATHOGEN, ZONE, 0, core.pathogen_profiles[PATHOGEN])
        records = agent.emesis_deposition_records_by_pathogen.get(PATHOGEN, [])
        return records[0] if records else {}

    def _emesis_core(self, blackwater: bool | dict,
                     seed: int = 7) -> TransmissionCore:
        core = TransmissionCore(
            rng=np.random.default_rng(seed),
            zone_volumes={ZONE: 50.0},
            pathogen_profiles={PATHOGEN: _profile()},
            zone_types={ZONE: "Cabin_Corridor"},
            clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
            cfg={"transmission": {"blackwater_plumbing": blackwater}},
        )
        core.initialize_zones([ZONE])
        return core

    def test_non_touchable_reaches_the_tank_and_pool_is_unchanged(self) -> None:
        with_tank = self._emesis_core(True)
        shedder_a = _shedder(with_tank)
        shedder_a.infections[PATHOGEN]["time_infected"] = 0
        shedder_a.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0]
        record = self._deposit(with_tank, shedder_a)
        tank = with_tank.blackwater_tank
        assert tank is not None
        assert tank.copies_by_pathogen[PATHOGEN] == pytest.approx(
            record["non_touchable"],
        )
        assert tank.telemetry["emesis_events"] == 1
        # Same seed, no tank: the fomite pool and record are identical.
        without_tank = self._emesis_core(False)
        shedder_b = _shedder(without_tank)
        shedder_b.infections[PATHOGEN]["time_infected"] = 0
        shedder_b.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0]
        record_b = self._deposit(without_tank, shedder_b)
        assert without_tank.blackwater_tank is None
        assert record["pool_gain"] == pytest.approx(record_b["pool_gain"])
        assert with_tank.surface_pools.get(ZONE, 0.0) == pytest.approx(
            without_tank.surface_pools.get(ZONE, 0.0),
        )

    def test_capture_fraction_scales_the_credit(self) -> None:
        core = self._emesis_core(
            {"emesis_drain_capture_fraction": 0.5},
        )
        shedder = _shedder(core)
        shedder.infections[PATHOGEN]["time_infected"] = 0
        shedder.emesis_episode_schedule_by_pathogen[PATHOGEN] = [0.0]
        record = self._deposit(core, shedder)
        assert core.blackwater_tank.copies_by_pathogen[
            PATHOGEN
        ] == pytest.approx(record["non_touchable"] * 0.5)


# ── Default-off ──────────────────────────────────────────────────────────


class TestDefaultOff:
    def test_no_tank_by_default_and_paired_run_is_identical(self) -> None:
        """blackwater_tank is None unless the key is set; off vs absent are
        bit-identical (the tank consumes no RNG)."""
        def fingerprint(cfg_extra: dict | None) -> tuple[dict, dict, list[float]]:
            tx = {"sanitary_visit_mode": "dwell_weighted"}
            if cfg_extra:
                tx.update(cfg_extra)
            core = TransmissionCore(
                rng=np.random.default_rng(99),
                zone_volumes={HEAD: 30.0, THEATER: 4000.0, CABIN_ZONE: 800.0},
                zone_types={
                    HEAD: "Sanitary",
                    THEATER: "Free",
                    CABIN_ZONE: "Cabin_Corridor",
                },
                zone_floor_areas={HEAD: 27.0},
                sanitary_zone_map={THEATER: {"male": HEAD}},
                pathogen_profiles={PATHOGEN: _profile()},
                clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
                cfg={"transmission": tx},
            )
            agents = [_shedder(core, 1), _agent(2, THEATER), _agent(3, THEATER)]
            route_doses = []
            for epoch in range(3):
                core.execute_transmission(
                    epoch=epoch, agents=agents,
                    zone_pathogen_mass={HEAD: 0.0, THEATER: 0.0},
                )
                route_doses.append(
                    {
                        aid: dict(pw)
                        for aid, pw in core._last_pathogen_route_doses.get(
                            PATHOGEN, {},
                        ).items()
                    },
                )
            hand = {
                a.agent_id: a.hand_load_by_pathogen.get(PATHOGEN, 0.0)
                for a in agents
            }
            tail = [float(core.rng.random()) for _ in range(5)]
            return core, route_doses, hand, tail

        core_off, doses_a, hand_a, tail_a = fingerprint(None)
        core_false, doses_b, hand_b, tail_b = fingerprint(
            {"blackwater_plumbing": False},
        )
        core_on, _, _, _ = fingerprint({"blackwater_plumbing": True})
        assert core_off.blackwater_tank is None
        assert core_false.blackwater_tank is None
        assert core_on.blackwater_tank is not None
        assert doses_a == doses_b
        assert hand_a == hand_b
        assert tail_a == tail_b

    def test_no_assay_record_without_mode_and_safe_degradation(self) -> None:
        """Default config records nothing; holding_tank mode with no tank
        produces no record and does not raise."""
        from orchestrator_epoch import run_observation_sampling

        engine = MagicMock()
        engine.get_pathogen_zone_mass.return_value = {}
        obs = MagicMock()
        obs.turnaround = None
        obs.lab_notebook_enabled = False
        obs.air_sniffer.sample_all_zones.return_value = {}
        obs.surface_swab.swab_zones.return_value = {}
        obs.wastewater_seq.sample_all_zones.return_value = {}
        obs.wastewater_assay = MagicMock()
        common = dict(
            epoch=1, obs=obs, agents=[], spaces={}, zone_names=["Bridge"],
            zone_volumes={"Bridge": 100.0}, zone_microflora_shifts={},
            trigger_status="BASELINE", high_traffic=["Bridge"],
            syn_result={"sick_call_agents": []}, engine=engine,
            pathogen_profiles={},
        )
        # Default mode: instrument exists but the mode is none -> no call.
        *_, ww_ht = run_observation_sampling(
            cfg={"observation": {"enabled": True}}, **common,
        )
        assert ww_ht is None
        obs.wastewater_assay.assay.assert_not_called()
        # holding_tank mode with tx_core=None degrades to no record.
        *_, ww_ht = run_observation_sampling(
            cfg={
                "observation": {
                    "enabled": True, "wastewater_assay_mode": "holding_tank",
                },
            },
            **common,
        )
        assert ww_ht is None
        obs.wastewater_assay.assay.assert_not_called()
