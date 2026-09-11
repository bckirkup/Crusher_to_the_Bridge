"""The emesis bolus doses the room it was expelled in.

Behaviour and invariant tests for the emesis-aerosol source-zone pathway:
an emesis event emits an aerosol fraction that used to reach only
HVAC-downstream zones (``_pathway_hvac_airborne`` skips
``target_zone == source_zone``) and only after the one-epoch drain lag.
The source-zone pathway doses the emitting zone's susceptible occupants in
the emission epoch, under its own ``emesis_aerosol`` route key, with no new
constant and no duct-attenuation scalar. No golden numbers: expectations
are positivity, ordering, bounds, and single-epoch persistence.
"""

from __future__ import annotations

import numpy as np
import pytest

from engines.infection_dynamics_bridge import IllnessStatus, KorkinAgent
from engines.sim_clock import HOURS, SimClock
from engines.transmission_core import TransmissionCore

PATHOGEN = "norwalk_gi"
ZONE = "Cabin_A"
DOWNSTREAM = "Cabin_B"

AEROSOL_RANGE = (7.2e-7, 2.67e-4)


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
        "dose_response": {"model": "exponential", "k": 0.01},
        "airborne_emission_mode": "emesis_conditioned",
        "emesis_aerosol_fraction_range": list(AEROSOL_RANGE),
        "emesis_episodes_range": [1, 1],
    }
    profile.update(overrides)
    return profile


def _agent(aid: int, *, zone: str = ZONE, infected: bool = False) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=zone,
        dining_zone=zone,
        work_zone=zone,
        free_zone=zone,
        schedule=["Free"] * 24,
    )
    agent.current_location = zone
    if infected:
        agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=0)
        agent.infections[PATHOGEN]["onset_time_infected"] = 0
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    return agent


def _core(
    profile: dict,
    *,
    seed: int = 11,
    volume: float = 50.0,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: volume, DOWNSTREAM: volume},
        pathogen_profiles={PATHOGEN: profile},
        zone_types={ZONE: "Room", DOWNSTREAM: "Room"},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
    )
    core.initialize_zones([ZONE, DOWNSTREAM])
    return core


def _emetic_shedder(core: TransmissionCore, *, event_age: float = 0.0) -> KorkinAgent:
    shedder = _agent(1, infected=True)
    shedder.clock = core.clock
    shedder.emesis_episode_schedule_by_pathogen[PATHOGEN] = [event_age]
    return shedder


def _emesis_dose_rows(matrix: object) -> list[dict]:
    return list(matrix.emesis_aerosol_exposures)


def _run_epoch(
    core: TransmissionCore,
    agents: list[KorkinAgent],
    epoch: int,
    **kwargs: object,
):
    return core.execute_transmission(
        epoch=epoch,
        agents=agents,
        zone_pathogen_mass={ZONE: 0.0, DOWNSTREAM: 0.0},
        **kwargs,
    )


class TestSensitivity:
    def test_emitting_zone_occupant_is_dosed_in_the_event_epoch(self) -> None:
        core = _core(_profile())
        shedder = _emetic_shedder(core)
        target = _agent(2)
        matrix, _ = _run_epoch(core, [shedder, target], epoch=1)
        rows = _emesis_dose_rows(matrix)
        assert len(rows) == 1
        assert rows[0]["target_id"] == 2
        assert rows[0]["source_agent_ids"] == [1]
        assert rows[0]["dose"] > 0.0
        route = core._last_pathogen_route_doses[PATHOGEN][2]
        assert route["emesis_aerosol"] > 0.0

    def test_dose_grows_with_the_aerosol_fraction(self) -> None:
        """Same seed, same emitted episode: a higher aerosol fraction moves
        more of the bolus to air, and the source-zone dose follows."""
        doses = []
        for fraction_range in (
            [7.2e-9, 2.67e-6],
            [7.2e-7, 2.67e-4],
            [7.2e-5, 2.67e-2],
        ):
            core = _core(
                _profile(emesis_aerosol_fraction_range=fraction_range),
            )
            shedder = _emetic_shedder(core)
            target = _agent(2)
            matrix, _ = _run_epoch(core, [shedder, target], epoch=1)
            doses.append(_emesis_dose_rows(matrix)[0]["dose"])
        assert all(d > 0.0 for d in doses)
        assert doses[0] < doses[1] < doses[2]

    def test_dose_dilutes_with_zone_volume(self) -> None:
        doses = []
        for volume in (25.0, 50.0, 200.0):
            core = _core(_profile(), volume=volume)
            shedder = _emetic_shedder(core)
            target = _agent(2)
            matrix, _ = _run_epoch(core, [shedder, target], epoch=1)
            doses.append(_emesis_dose_rows(matrix)[0]["dose"])
        assert doses[0] > doses[1] > doses[2]

    def test_no_emesis_no_source_zone_dose(self) -> None:
        core = _core(_profile())
        shedder = _agent(1, infected=True)
        target = _agent(2)
        matrix, _ = _run_epoch(core, [shedder, target], epoch=1)
        assert _emesis_dose_rows(matrix) == []
        assert "emesis_aerosol" not in core._last_pathogen_route_doses.get(
            PATHOGEN, {},
        ).get(2, {})

    def test_non_emetic_profile_yields_no_source_zone_dose(self) -> None:
        profile = _profile()
        del profile["airborne_emission_mode"]
        del profile["emesis_aerosol_fraction_range"]
        core = _core(profile)
        shedder = _emetic_shedder(core)
        target = _agent(2)
        matrix, _ = _run_epoch(core, [shedder, target], epoch=1)
        assert _emesis_dose_rows(matrix) == []

    def test_the_accumulator_does_not_persist(self) -> None:
        """An epoch with no new emesis event delivers no source-zone dose."""
        core = _core(_profile())
        shedder = _emetic_shedder(core)
        target = _agent(2)
        matrix, _ = _run_epoch(core, [shedder, target], epoch=1)
        assert _emesis_dose_rows(matrix)
        shedder.infections[PATHOGEN]["time_infected"] += 24
        matrix2, _ = _run_epoch(core, [shedder, target], epoch=2)
        assert _emesis_dose_rows(matrix2) == []


class TestInvariants:
    def test_the_pending_dict_still_drains_once(self) -> None:
        """The same emitted mass is transport, not a second emission: the
        production drain still returns it once and empties."""
        core = _core(_profile())
        shedder = _emetic_shedder(core)
        target = _agent(2)
        _run_epoch(core, [shedder, target], epoch=1)
        drained = core.drain_emesis_aerosol(PATHOGEN)
        assert drained.get(ZONE, 0.0) > 0.0
        assert core.drain_emesis_aerosol(PATHOGEN) == {}

    def test_dose_is_bounded_by_the_emitted_mass(self) -> None:
        """dose <= episode_load x aerosol_high / volume x inhaled volume."""
        core = _core(_profile())
        shedder = _emetic_shedder(core)
        target = _agent(2)
        matrix, _ = _run_epoch(core, [shedder, target], epoch=1)
        row = _emesis_dose_rows(matrix)[0]
        record = shedder.emesis_deposition_records_by_pathogen[PATHOGEN][0]
        upper = (
            record["episode_load"] * AEROSOL_RANGE[1]
            / 50.0 * core.inhaled_air_volume_m3_per_epoch
        )
        assert np.isfinite(row["dose"])
        assert 0.0 <= row["dose"] <= upper

    def test_route_separation(self) -> None:
        """Emesis-on doses land under emesis_aerosol only; droplet and
        hvac_airborne totals are unchanged at the same seed."""
        core_off = _core(_profile(airborne_emission_mode=None))
        core_off.pathogen_profiles[PATHOGEN].pop("airborne_emission_mode")
        core_on = _core(_profile())
        rows = {}
        for label, core in (("off", core_off), ("on", core_on)):
            shedder = _emetic_shedder(core)
            target = _agent(2)
            matrix, _ = _run_epoch(core, [shedder, target], epoch=1)
            rows[label] = core._last_pathogen_route_doses[PATHOGEN].get(2, {})
        off = rows["off"]
        on = rows["on"]
        assert on.get("emesis_aerosol", 0.0) > 0.0
        assert "emesis_aerosol" not in off
        assert on.get("droplet", 0.0) == pytest.approx(
            off.get("droplet", 0.0), rel=1e-12,
        )
        assert on.get("hvac_airborne", 0.0) == pytest.approx(
            off.get("hvac_airborne", 0.0), rel=1e-12,
        )

    def test_downstream_dose_survives_at_the_next_epoch(self) -> None:
        """The drained mass still reaches an HVAC-downstream zone one epoch
        later — the transport lag this change deliberately keeps."""
        core = _core(_profile())
        shedder = _emetic_shedder(core)
        target = _agent(2)
        _run_epoch(core, [shedder, target], epoch=1)
        drained = core.drain_emesis_aerosol(PATHOGEN)
        # A fresh susceptible arrives in the downstream zone: the epoch-1
        # target is already infected by its own route doses.
        downstream_target = _agent(3, zone=DOWNSTREAM)
        shedder.infections[PATHOGEN]["time_infected"] += 24
        matrix2, _ = core.execute_transmission(
            epoch=2,
            agents=[shedder, downstream_target],
            zone_pathogen_mass={ZONE: 0.0, DOWNSTREAM: drained[ZONE]},
            hvac_downstream_zones={ZONE: [DOWNSTREAM]},
        )
        downstream = [
            r for r in matrix2.hvac_downstream_exposures
            if r["target_zone"] == DOWNSTREAM
        ]
        assert downstream
        assert downstream[0]["dose"] > 0.0
