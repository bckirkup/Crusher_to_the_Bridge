"""Tests for the environmental/chemical hazard arm (ship_function_capacity_spec §8).

Covers: the voyage-block profile merge and its validation, the
cumulative-toxicity dose-response arm landing on the §7 symptomatic-
presentation seam without incubation or shedding, the chemical-sensor
modality surface, and the paired-seed proof that declared-disabled is
bit-identical to absent.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from crusher_labs.modalities.chemical_sensor import (
    ChemicalAirSensor,
    ChemicalSurfaceSensor,
    build_chemical_sensors,
)
from engines.environmental_hazards import (
    cumulative_toxicity_spec,
    merge_environmental_hazard_profiles,
)
from engines.infection_dynamics_bridge import KorkinAgent
from engines.transmission_core import ContactTracingMatrix, TransmissionCore
from telemetry_buffer.agent_axes import agent_has_symptomatic_presentation

ZONE = "Engine_Room"
PID = "voc_refrigerant_leak"


def _hazard(**over) -> dict:
    hazard = {
        "pathogen_id": PID,
        "name": "VOC refrigerant leak (declared)",
        "category": "chemical",
        "transmission_routes": ["hvac_airborne"],
        "initial_infected": 0,
        "introduction_epoch": 0,
        "dose_response": {
            "model": "cumulative_toxicity",
            "haber_ct_threshold": 5.0,
            "symptomatic": True,
        },
        "environmental_contamination": {
            "enabled": True,
            "source_type": "machinery_space_leak",
            "source_zones": [ZONE],
            "baseline_environmental_load": 4.0,
            "base_emission_rate_per_day": 240.0,
            "exposure_probability_per_day": 240.0,
            "spore_decay_rate_per_day": 0.0,
            "colonization_rate_per_day": 0.0,
            "person_to_person": False,
        },
        "chemical_sensor": {
            "enabled": True,
            "air": {"lod_mass_per_m3": 0.01},
            "surface": {"lod_mass_per_cm2": 0.001},
        },
    }
    hazard.update(over)
    return hazard


class TestMergeGate:
    def test_absent_block_returns_registry_untouched(self) -> None:
        profiles = {"norwalk_gi": {"pathogen_id": "norwalk_gi"}}
        assert merge_environmental_hazard_profiles(profiles, {}) is profiles
        assert merge_environmental_hazard_profiles(profiles, None) is profiles

    def test_disabled_block_returns_registry_untouched(self) -> None:
        profiles = {"norwalk_gi": {"pathogen_id": "norwalk_gi"}}
        voyage = {"environmental_hazards": {
            "enabled": False, "hazards": [_hazard()],
        }}
        assert merge_environmental_hazard_profiles(profiles, voyage) is profiles

    def test_enabled_block_merges_hazards(self) -> None:
        profiles = {"norwalk_gi": {"pathogen_id": "norwalk_gi"}}
        voyage = {"environmental_hazards": {
            "enabled": True, "hazards": [_hazard()],
        }}
        merged = merge_environmental_hazard_profiles(profiles, voyage)
        assert set(merged) == {"norwalk_gi", PID}
        assert merged[PID]["category"] == "chemical"
        # The input registry is not mutated.
        assert PID not in profiles

    def test_hazard_level_disabled_entry_is_skipped(self) -> None:
        voyage = {"environmental_hazards": {
            "enabled": True, "hazards": [_hazard(enabled=False)],
        }}
        assert merge_environmental_hazard_profiles({}, voyage) == {}

    @pytest.mark.parametrize("mut,match", [
        (lambda h: h.update(category="enteric_viral"), "category"),
        (lambda h: h.pop("category"), "category"),
        (lambda h: h.update(
            dose_response={"model": "beta_poisson", "alpha": 1, "beta": 1},
        ), "cumulative_toxicity"),
        (lambda h: h.update(initial_infected=1), "initial_infected"),
        (lambda h: h.update(introduction_epoch=5), "introduction_epoch"),
    ])
    def test_validation_rejects_dishonest_declarations(self, mut, match) -> None:
        hazard = _hazard()
        mut(hazard)
        voyage = {"environmental_hazards": {
            "enabled": True, "hazards": [hazard],
        }}
        with pytest.raises(ValueError, match=match):
            merge_environmental_hazard_profiles({}, voyage)

    def test_hazard_cannot_shadow_a_pathogen(self) -> None:
        voyage = {"environmental_hazards": {
            "enabled": True, "hazards": [_hazard(pathogen_id="norwalk_gi")],
        }}
        with pytest.raises(ValueError, match="shadow"):
            merge_environmental_hazard_profiles(
                {"norwalk_gi": {}}, voyage,
            )


class TestCumulativeToxicitySpec:
    def test_non_toxicity_model_returns_none(self) -> None:
        assert cumulative_toxicity_spec({}) is None
        assert cumulative_toxicity_spec(
            {"dose_response": {"model": "exponential", "k": 0.5}},
        ) is None

    def test_parse(self) -> None:
        spec = cumulative_toxicity_spec(_hazard())
        assert spec == {
            "haber_ct_threshold": 5.0, "symptomatic": True,
        }
        assert cumulative_toxicity_spec(
            _hazard(dose_response={
                "model": "cumulative_toxicity", "haber_ct_threshold": 2.0,
            }),
        )["symptomatic"] is True

    @pytest.mark.parametrize("threshold", [None, 0.0, -1.0, float("nan")])
    def test_threshold_must_be_finite_positive(self, threshold) -> None:
        dr = {"model": "cumulative_toxicity"}
        if threshold is not None:
            dr["haber_ct_threshold"] = threshold
        with pytest.raises(ValueError, match="haber_ct_threshold"):
            cumulative_toxicity_spec({"dose_response": dr})

    def test_unknown_keys_rejected(self) -> None:
        with pytest.raises(ValueError, match="does not parameterise"):
            cumulative_toxicity_spec({"dose_response": {
                "model": "cumulative_toxicity",
                "haber_ct_threshold": 1.0,
                "alpha": 2.0,
            }})


def _core(profiles: dict) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(7),
        zone_volumes={ZONE: 100.0},
        zone_types={ZONE: "Free"},
        cfg={"transmission": {
            "cabin_air_mode": "zone_pool",
            "near_field_air": {"mode": "off"},
        }},
        pathogen_profiles=profiles,
    )
    core.initialize_zones([ZONE])
    return core


def _crew_agent(aid: int = 1) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=aid,
        role="crew",
        immune=False,
        home_zone=ZONE,
        dining_zone="Galley",
        work_zone=ZONE,
        free_zone="Bridge",
        schedule=["home"] * 24,
    )
    agent.current_location = ZONE
    return agent


def _challenge(
    core: TransmissionCore, agent: KorkinAgent, epoch: int, dose: float,
) -> None:
    core._resolve_pathogen_challenge(  # noqa: SLF001 — arm-level drive
        epoch, agent, PID,
        {agent.agent_id: {PID: dose}},
        {},
        ContactTracingMatrix(epoch),
        [],
    )


class TestToxicityArm:
    def test_threshold_crossing_presents_without_infection(self) -> None:
        core = _core({PID: _hazard()})
        agent = _crew_agent()
        # Doses below the threshold accrue without onset.
        _challenge(core, agent, 0, 2.0)
        _challenge(core, agent, 1, 2.5)
        assert agent.hazard_onset_epochs == {}
        assert agent.hazard_symptomatic_active is False
        # Crossing at 5.5 books the onset epoch and the §7 flag.
        _challenge(core, agent, 2, 1.0)
        assert agent.hazard_onset_epochs == {PID: 2}
        assert agent.hazard_symptomatic_active is True
        exported = agent.to_schema_dict()
        assert exported["symptom_presentation"] == "symptomatic"
        assert agent_has_symptomatic_presentation(exported)
        # No incubation, no infection record, no shedding.
        assert exported["infection_state"] == "susceptible"
        assert agent.is_infected_with(PID) is False
        assert agent.get_pathogen_shedding(PID, _hazard()) == 0.0

    def test_arm_draws_no_rng(self) -> None:
        """A deterministic threshold law consumes no draws."""
        rng = np.random.default_rng(7)
        before = rng.bit_generator.state
        core = _core({PID: _hazard()})
        core.rng = rng  # instrument the stream the arm would draw on
        agent = _crew_agent()
        _challenge(core, agent, 0, 100.0)
        assert agent.hazard_symptomatic_active is True
        assert rng.bit_generator.state == before

    def test_onset_records_first_crossing_only(self) -> None:
        core = _core({PID: _hazard()})
        agent = _crew_agent()
        _challenge(core, agent, 3, 100.0)
        _challenge(core, agent, 4, 100.0)
        assert agent.hazard_onset_epochs == {PID: 3}

    def test_non_symptomatic_declaring_hazard_never_presents(self) -> None:
        hazard = _hazard()
        hazard["dose_response"]["symptomatic"] = False
        core = _core({PID: hazard})
        agent = _crew_agent()
        _challenge(core, agent, 0, 100.0)
        assert agent.hazard_onset_epochs == {PID: 0}
        assert agent.hazard_symptomatic_active is False
        exported = agent.to_schema_dict()
        assert exported["symptom_presentation"] == "asymptomatic"

    def test_cumulative_ledger_is_never_cleared(self) -> None:
        """Toxicity keeps booking dose; the infectious arm's clear-on-
        establish never fires because nothing establishes."""
        core = _core({PID: _hazard()})
        agent = _crew_agent()
        _challenge(core, agent, 0, 100.0)
        _challenge(core, agent, 1, 50.0)
        assert agent.cumulative_exposure[PID] == 150.0


class TestChemicalSensors:
    def test_air_sensor_detects_above_lod(self) -> None:
        sensor = ChemicalAirSensor(
            lod_mass_per_m3=0.01, noise_sigma_log=0.0,
            rng=np.random.default_rng(1),
        )
        out = sensor.sample("Engine_Room", 5.0, 100.0)
        assert out["detected"] is True
        assert out["concentration_per_m3"] == pytest.approx(0.05)
        assert "ct_value" not in out
        out_low = sensor.sample("Engine_Room", 0.1, 100.0)
        assert out_low["detected"] is False

    def test_surface_sensor_detects_above_lod(self) -> None:
        sensor = ChemicalSurfaceSensor(
            lod_mass_per_cm2=0.001, noise_sigma_log=0.0,
            rng=np.random.default_rng(1),
        )
        assert sensor.sample("Engine_Room", 0.005)["detected"] is True
        assert sensor.sample("Engine_Room", 0.0005)["detected"] is False

    def test_build_only_for_enabled_chemical_profiles(self) -> None:
        sensors = build_chemical_sensors(
            {
                PID: _hazard(),
                "norwalk_gi": {"category": "enteric_viral"},
                "sleeping": {
                    "category": "chemical",
                    "chemical_sensor": {"enabled": False},
                },
            },
            seed=3,
        )
        assert set(sensors) == {PID}
        assert set(sensors[PID]) == {"air", "surface"}

    def test_sensor_lod_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="lod_mass_per_m3"):
            ChemicalAirSensor(lod_mass_per_m3=0.0, rng=np.random.default_rng(1))
        with pytest.raises(ValueError, match="lod_mass_per_cm2"):
            ChemicalSurfaceSensor(
                lod_mass_per_cm2=-1.0, rng=np.random.default_rng(1),
            )


def _voyage_hazards(enabled: bool) -> dict:
    return {"environmental_hazards": {
        "enabled": enabled,
        "hazards": [_hazard()],
    }}


@pytest.mark.timeout(300)
def test_declared_disabled_is_bit_identical_to_absent() -> None:
    """Paired seeded smoke: declared-and-off must equal never-declared."""
    from picard_framework import PicardRunSpec, ShipSimulation

    spec_path = os.path.join(
        REPO_ROOT, "picard_framework/runs/smoke_2epoch.json",
    )
    spec_off = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
    spec_off.legacy_cfg["voyage"] = _voyage_hazards(enabled=False)

    spec_absent = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
    spec_absent.legacy_cfg.pop("voyage", None)

    run_off = ShipSimulation(spec_off, display=False, repo_root=REPO_ROOT).run()
    run_absent = ShipSimulation(
        spec_absent, display=False, repo_root=REPO_ROOT,
    ).run()
    assert run_off.history == run_absent.history


@pytest.mark.timeout(300)
def test_enabled_hazard_presents_symptomatic_and_detects() -> None:
    """An enabled leak exposes Engine_Room crew, crosses the Haber
    threshold, and the chemical sensors see the pool."""
    from picard_framework import PicardRunSpec, ShipSimulation

    spec_path = os.path.join(
        REPO_ROOT, "picard_framework/runs/smoke_2epoch.json",
    )
    spec = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
    hazard = _hazard()
    hazard["dose_response"]["haber_ct_threshold"] = 1.0
    spec.legacy_cfg["voyage"] = {"environmental_hazards": {
        "enabled": True, "hazards": [hazard],
    }}
    sim = ShipSimulation(spec, display=False, repo_root=REPO_ROOT)
    sim.run()

    # Onset on the §7 seam: a symptomatic presentation with no infection.
    symptomatic_susceptibles = [
        a
        for rec in sim.state.simulation_history
        for a in rec.get("agents", [])
        if a.get("symptom_presentation") == "symptomatic"
        and a.get("infection_state") == "susceptible"
    ]
    assert symptomatic_susceptibles, (
        "no agent carried the chemical onset onto the "
        "symptom_presentation axis"
    )

    # The sensor surface reported the substance pools.
    chem_records = [
        r for r in sim.obs.notebook.records
        if r.get("assay_type") == "chemical_detector"
    ]
    assert chem_records
    assert all(r.get("substance_id") == PID for r in chem_records)
    assert any(
        r.get("binary_result") == "DETECTED" for r in chem_records
    )
