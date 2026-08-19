"""Tests for clinical presentation, impression, and pathogen-aware instruments."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

from crusher_labs.clinical_instrument_params import (  # noqa: E402
    expand_tier_tests_for_agent,
    impression_sensitivity_for_day,
    load_clinical_instrument_params,
    panels_for_syndromes,
    resolve_instrument_params,
    resolve_panel_params,
)
from crusher_labs.clinical_presentation import (  # noqa: E402
    annotate_agent_clinical_presentation,
    resolve_phase,
)
from crusher_labs.observation_core import (  # noqa: E402
    ClinicalImpression,
    ClinicalMultiplexPanel,
    ClinicalRapidDiagnostic,
)
from orchestrator_init import init_observation_engine  # noqa: E402
from telemetry_buffer.agent_axes import (  # noqa: E402
    COMPLIANCE_COMPLIANT,
    INFECTION_INFECTED,
    PRESENTATION_SYMPTOMATIC,
)


def _profiles() -> dict:
    path = REPO_ROOT / "data/pathogens/edison_10pathogen_profiles.json"
    data = json.loads(path.read_text())
    return {p["pathogen_id"]: p for p in data["pathogens"]}


def _agent(
    pid: str,
    *,
    dpi: int = 3,
    symptomatic: bool = True,
    shedding: float = 5000.0,
    syndromes: list[str] | None = None,
) -> dict:
    illness = "SYMPTOMATIC" if symptomatic else "ASYMPTOMATIC"
    agent = {
        "agent_id": 1,
        "infection_state": INFECTION_INFECTED,
        "symptom_presentation": PRESENTATION_SYMPTOMATIC if symptomatic else "asymptomatic",
        "compliance_status": COMPLIANCE_COMPLIANT,
        "shedding_rate": shedding,
        "location": "cabin",
        "pathogen_infections": {
            pid: {
                "status": "INFECTED",
                "illness": illness,
                "days_post_infection": dpi,
            },
        },
    }
    annotate_agent_clinical_presentation(agent, _profiles())
    if syndromes is not None:
        agent["observed_syndromes"] = syndromes
    return agent


class TestClinicalPresentation:
    def test_measles_phase_changes_with_dpi(self) -> None:
        profiles = _profiles()
        presentation = profiles["measles_virus"]["clinical_presentation"]
        early = resolve_phase(presentation, 1)
        classic = resolve_phase(presentation, 4)
        assert early is not None
        assert classic is not None
        assert "maculopapular_rash" not in (early.get("features") or [])
        assert "maculopapular_rash" in (classic.get("features") or [])

    def test_symptomatic_infection_yields_syndromes(self) -> None:
        agent = _agent("norovirus_gii4", dpi=1)
        assert "gastrointestinal" in agent["observed_syndromes"]
        assert agent["days_since_symptom_onset"] >= 1

    def test_asymptomatic_infection_yields_no_syndromes(self) -> None:
        agent = _agent("norovirus_gii4", symptomatic=False, dpi=2)
        assert agent["observed_syndromes"] == []


class TestInstrumentParamsConfig:
    def test_loader_and_schema_file_exist(self) -> None:
        params = load_clinical_instrument_params(repo_root=str(REPO_ROOT))
        assert "instruments" in params
        assert "panels" in params
        assert "gi" in params["panels"]

    def test_hantavirus_rdt_uncovered(self) -> None:
        params = load_clinical_instrument_params(repo_root=str(REPO_ROOT))
        resolved = resolve_instrument_params(params, "clinical_rdt", "andes_hantavirus")
        assert resolved.covers_pathogen is False

    def test_config_sensitivity_panel_membership(self) -> None:
        params = load_clinical_instrument_params(repo_root=str(REPO_ROOT))
        assert resolve_panel_params(params, "gi", "norovirus_gii4") is not None
        assert resolve_panel_params(params, "gi", "measles_virus") is None
        assert resolve_panel_params(params, "rp", "sars_cov2_resp") is not None

    def test_syndrome_routes_gi_and_rp(self) -> None:
        params = load_clinical_instrument_params(repo_root=str(REPO_ROOT))
        assert panels_for_syndromes(params, ["gastrointestinal"]) == ["gi"]
        assert "rp" in panels_for_syndromes(params, ["respiratory"])
        assert "pneumonia" in panels_for_syndromes(params, ["respiratory"])


class TestClinicalImpression:
    def test_sensitivity_rises_with_day(self) -> None:
        params = load_clinical_instrument_params(repo_root=str(REPO_ROOT))
        resolved = resolve_instrument_params(params, "clinical_impression", "measles_virus")
        d1 = impression_sensitivity_for_day(resolved, 1)
        d5 = impression_sensitivity_for_day(resolved, 5)
        assert d5 > d1

    def test_outbreak_bonus_increases_sensitivity(self) -> None:
        params = load_clinical_instrument_params(repo_root=str(REPO_ROOT))
        resolved = resolve_instrument_params(params, "clinical_impression", "ebola_virus")
        base = impression_sensitivity_for_day(resolved, 3, outbreak_aware=False)
        boosted = impression_sensitivity_for_day(resolved, 3, outbreak_aware=True)
        assert boosted > base

    def test_impression_can_suspect_measles(self) -> None:
        params = load_clinical_instrument_params(repo_root=str(REPO_ROOT))
        inst = ClinicalImpression(instrument_params=params, rng=np.random.default_rng(0))
        agent = _agent("measles_virus", dpi=5, shedding=100.0)
        # Force high draw-success path with many trials
        hits = 0
        for seed in range(40):
            inst.rng = np.random.default_rng(seed)
            result = inst.test_agent(
                1, 100.0, True, INFECTION_INFECTED, PRESENTATION_SYMPTOMATIC,
                COMPLIANCE_COMPLIANT, "cabin",
                pathogen_infections=agent["pathogen_infections"],
                days_since_symptom_onset=5,
                candidate_pathogens=["measles_virus"],
            )
            assert result["informative"] is True
            if result.get("suspected_pathogen") == "measles_virus":
                hits += 1
        assert hits > 0


class TestMultiplexVsRdt:
    def test_multiplex_not_aliased_to_rdt(self) -> None:
        obs = init_observation_engine({}, seed=42, pathogen_profiles=_profiles())
        assert obs.clin_multiplex is not None
        assert obs.clin_multiplex is not obs.clin_rdt
        agent = _agent("norovirus_gii4", dpi=2, shedding=8000.0)
        results = obs.clinical_correlation.run_agent_tests(
            obs, agent, test_keys=("clinical_multiplex_panel",),
        )
        mpx = results["clinical_multiplex_panel"]
        assert mpx["instrument"] == "clinical_multiplex_panel"
        assert "target_results" in mpx

    def test_off_panel_measles_multiplex_uninformative(self) -> None:
        params = load_clinical_instrument_params(repo_root=str(REPO_ROOT))
        mpx = ClinicalMultiplexPanel(instrument_params=params, rng=np.random.default_rng(1))
        agent = _agent("measles_virus", dpi=4, shedding=1000.0, syndromes=["rash"])
        result = mpx.test_agent(
            1, 1000.0, True, INFECTION_INFECTED, PRESENTATION_SYMPTOMATIC,
            COMPLIANCE_COMPLIANT, "cabin",
            pathogen_infections=agent["pathogen_infections"],
            observed_syndromes=["rash"],
        )
        assert result["informative"] is False
        assert result["positive"] is False
        assert result.get("identified_pathogen") is None

    def test_hantavirus_rdt_uninformative(self) -> None:
        params = load_clinical_instrument_params(repo_root=str(REPO_ROOT))
        rdt = ClinicalRapidDiagnostic(
            instrument_params=params, rng=np.random.default_rng(2),
        )
        result = rdt.test_agent(
            1, 1000.0, True, INFECTION_INFECTED, PRESENTATION_SYMPTOMATIC,
            COMPLIANCE_COMPLIANT, "cabin",
            pathogen_id="andes_hantavirus",
        )
        assert result["informative"] is False
        assert result["positive"] is False

    def test_gi_panel_can_identify_norovirus(self) -> None:
        params = load_clinical_instrument_params(repo_root=str(REPO_ROOT))
        mpx = ClinicalMultiplexPanel(instrument_params=params, rng=np.random.default_rng(0))
        agent = _agent("norovirus_gii4", dpi=2, shedding=20000.0)
        hits = 0
        for seed in range(30):
            mpx.rng = np.random.default_rng(seed)
            result = mpx.test_agent(
                1, 20000.0, True, INFECTION_INFECTED, PRESENTATION_SYMPTOMATIC,
                COMPLIANCE_COMPLIANT, "cabin",
                pathogen_infections=agent["pathogen_infections"],
                observed_syndromes=["gastrointestinal"],
            )
            assert result["informative"] is True
            if result.get("identified_pathogen") == "norovirus_gii4":
                hits += 1
        assert hits > 0

    def test_co_infection_dual_syndromes_expand_panels(self) -> None:
        params = load_clinical_instrument_params(repo_root=str(REPO_ROOT))
        agent = {
            "agent_id": 9,
            "pathogen_infections": {
                "norovirus_gii4": {
                    "status": "INFECTED", "illness": "SYMPTOMATIC", "days_post_infection": 2,
                },
                "sars_cov2_resp": {
                    "status": "INFECTED", "illness": "SYMPTOMATIC", "days_post_infection": 2,
                },
            },
        }
        annotate_agent_clinical_presentation(agent, _profiles())
        panels = panels_for_syndromes(params, agent["observed_syndromes"])
        assert "gi" in panels
        assert "rp" in panels

    def test_expand_tier_adds_impression_for_rash(self) -> None:
        params = load_clinical_instrument_params(repo_root=str(REPO_ROOT))
        agent = _agent("measles_virus", dpi=4, syndromes=["rash"])
        expanded = expand_tier_tests_for_agent(
            params,
            ["clinical_multiplex_panel"],
            agent,
            prefer_multiplex=True,
        )
        assert "clinical_impression" in expanded


class TestCascadeOutcomeRespectsInformative:
    def test_uninformative_does_not_advance(self) -> None:
        from crusher_labs.diagnostic_cascade import DiagnosticCascadeEngine, DiagnosticTier

        tier = DiagnosticTier(
            tier_id=1,
            name="t1",
            tests=["clinical_multiplex_panel"],
            sensitivity=0.9,
            specificity=0.9,
            cost_per_agent={},
            tat_epochs=0,
            regret_level="low",
            actions_on_positive=["advance_to_tier_2"],
            confinement_on_positive=False,
            sop_gate=None,
        )
        engine = DiagnosticCascadeEngine([tier], [])
        positive = engine._determine_test_outcome(
            {},
            {"clinical_multiplex_panel": {
                "positive": False, "informative": False,
            }},
            tier,
        )
        assert positive is False


@pytest.mark.parametrize(
    "schema_name,data_rel",
    [
        (
            "clinical_instrument_params.schema.json",
            "data/config/clinical_instrument_params.json",
        ),
        ("pathogen_profiles.schema.json", "data/pathogens/edison_10pathogen_profiles.json"),
        ("pathogen_profiles.schema.json", "data/pathogens/active_profiles.json"),
    ],
)
def test_json_schema_clinical_configs(schema_name: str, data_rel: str) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((REPO_ROOT / "schemas" / schema_name).read_text())
    data = json.loads((REPO_ROOT / data_rel).read_text())
    jsonschema.validate(instance=data, schema=schema)
