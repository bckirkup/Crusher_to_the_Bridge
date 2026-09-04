"""Tests for multi-pathogen Phase A: route weights, dose_adjustment, nonsusceptibility."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

from engines.infection_dynamics_bridge import (  # noqa: E402
    IllnessStatus,
    InfectionStatus,
    KorkinAgent,
)
from engines.transmission_core import (  # noqa: E402
    DEFAULT_ROUTE_WEIGHTS,
    TransmissionCore,
)
from orchestrator_init import init_multi_pathogen  # noqa: E402


def _agent(aid: int, loc: str, *, infected: bool = False) -> KorkinAgent:
    a = KorkinAgent(
        agent_id=aid,
        role="passenger",
        immune=False,
        home_zone=loc,
        dining_zone=loc,
        work_zone=loc,
        free_zone=loc,
        schedule=["Free"] * 24,
    )
    a.current_location = loc
    if infected:
        a.infection_status = InfectionStatus.INFECTED
        a.illness_status = IllnessStatus.SYMPTOMATIC
        a.time_infected = 1
        a.infect_with_pathogen("test_pathogen", 1e4, 0, time_infected=1)
    return a


class TestRouteWeights:
    def test_identity_weights_are_noop(self) -> None:
        """Absent weights and explicit all-1.0 weights leave doses unchanged."""
        core = TransmissionCore(rng=np.random.default_rng(0))
        doses_a = {1: 10.0, 2: 5.0}
        pw_a = {
            1: {"direct_contact": 6.0, "droplet": 4.0},
            2: {"fomite": 5.0},
        }
        doses_b = {1: 10.0, 2: 5.0}
        pw_b = {
            1: {"direct_contact": 6.0, "droplet": 4.0},
            2: {"fomite": 5.0},
        }
        core._apply_route_weights({}, doses_a, pw_a)
        core._apply_route_weights(
            {"transmission_route_weights": dict(DEFAULT_ROUTE_WEIGHTS)},
            doses_b,
            pw_b,
        )
        assert doses_a == doses_b
        assert pw_a == pw_b
        assert doses_a[1] == pytest.approx(10.0)

    def test_zero_hvac_weight_nulls_hvac_pathway_dose(self) -> None:
        profiles = {
            "test_pathogen": {
                "dose_response": {"model": "beta_poisson", "alpha": 0.111, "beta": 32.81},
                "transmission_route_weights": {
                    **DEFAULT_ROUTE_WEIGHTS,
                    "hvac_airborne": 0.0,
                },
            },
        }
        core = TransmissionCore(
            rng=np.random.default_rng(0),
            pathogen_profiles=profiles,
        )
        p_doses = {1: 10.0}
        p_pw = {1: {"hvac_airborne": 10.0, "direct_contact": 2.0}}
        core._apply_route_weights(profiles["test_pathogen"], p_doses, p_pw)
        assert p_pw[1]["hvac_airborne"] == pytest.approx(0.0)
        assert p_pw[1]["direct_contact"] == pytest.approx(2.0)
        assert p_doses[1] == pytest.approx(2.0)

    def test_legionella_env_only_weights(self) -> None:
        edison = json.loads(
            (REPO_ROOT / "data/pathogens/edison_10pathogen_profiles.json").read_text(),
        )
        leg = next(p for p in edison["pathogens"] if p["pathogen_id"] == "legionella_pneumophila")
        w = leg["transmission_route_weights"]
        assert w["environmental_source"] == pytest.approx(1.0)
        assert sum(w.values()) == pytest.approx(1.0)
        assert all(w[k] == 0.0 for k in w if k != "environmental_source")


class TestDoseAdjustmentContracts:
    @pytest.mark.parametrize(
        "bundle",
        ["active_profiles.json", "edison_10pathogen_profiles.json"],
    )
    def test_every_profile_declares_a_release_normalizer(
        self, bundle: str,
    ) -> None:
        """No profile may fall back to the norovirus release default.

        The accepted names are the precedence list in
        ``environmental_release_log10_per_day``: a respiratory profile
        declares release of exhaled material, not grams of stool, so
        requiring the enteric name of the key would force it to misdeclare
        its own matrix.
        """
        accepted = (
            "environmental_release_log10_per_day",
            "environmental_faecal_release_log10_g_per_epoch",
            "dose_adjustment",
        )
        data = json.loads((REPO_ROOT / "data/pathogens" / bundle).read_text())
        for p in data["pathogens"]:
            declared = [key for key in accepted if key in p]
            assert declared, p["pathogen_id"]
            for key in declared:
                assert isinstance(p[key], (int, float)), (
                    f"{p['pathogen_id']}.{key}"
                )


class TestNorovirusAirborneContracts:
    @pytest.mark.parametrize(
        "bundle,pathogen_id",
        [
            ("active_profiles.json", "norwalk_gi"),
            ("edison_10pathogen_profiles.json", "norovirus_gii4"),
        ],
    )
    def test_norovirus_uses_emesis_conditioned_airborne_range(
        self,
        bundle: str,
        pathogen_id: str,
    ) -> None:
        data = json.loads((REPO_ROOT / "data/pathogens" / bundle).read_text())
        profile = next(
            p for p in data["pathogens"] if p["pathogen_id"] == pathogen_id
        )
        assert profile["airborne_emission_mode"] == "emesis_conditioned"
        assert profile["emesis_aerosol_fraction_range"] == [7.2e-7, 2.67e-4]
        assert "airborne_emission_fraction" not in profile
        assert "surface_deposition_fraction" not in profile

    @pytest.mark.parametrize("bundle", ["active_profiles.json", "edison_10pathogen_profiles.json"])
    def test_covid_continuous_airborne_scope_guard(self, bundle: str) -> None:
        data = json.loads((REPO_ROOT / "data/pathogens" / bundle).read_text())
        profile = next(
            p for p in data["pathogens"] if p["pathogen_id"] == "sars_cov2_resp"
        )
        key = (
            "airborne_emission_fraction"
            if bundle == "active_profiles.json"
            else "surface_deposition_fraction"
        )
        assert profile[key] == pytest.approx(5e-5)
        assert "airborne_emission_mode" not in profile


class TestInfluenzaPresentationContract:
    def test_influenza_uses_dose_independent_presentation(self) -> None:
        data = json.loads(
            (REPO_ROOT / "data/pathogens/edison_10pathogen_profiles.json").read_text(),
        )
        influenza = next(
            p for p in data["pathogens"] if p["pathogen_id"] == "influenza_a"
        )
        assert influenza["symptomatic_fraction"] == pytest.approx(0.669)
        assert "illness_probability" not in influenza


class TestInnateNonsusceptibility:
    def test_nonsus_fraction_zeroes_multiplier(self) -> None:
        class _FakeEngine:
            def __init__(self) -> None:
                self.agents = [
                    KorkinAgent(
                        agent_id=i,
                        role="passenger",
                        immune=False,
                        home_zone="A",
                        dining_zone="A",
                        work_zone="A",
                        free_zone="A",
                        schedule=["Free"] * 24,
                    )
                    for i in range(200)
                ]

            def initialize_pathogen(self, _pid: str) -> None:
                return None

        engine = _FakeEngine()
        profiles = {
            "norovirus_gii4": {
                "base_susceptibility": 1.0,
                "innate_nonsusceptible_fraction": 0.20,
                "introduction_epoch": 1,  # skip seeding
            },
            "sars_cov2_resp": {
                "base_susceptibility": 1.0,
                "innate_nonsusceptible_fraction": 0.0,
                "introduction_epoch": 1,
            },
        }
        rng = np.random.default_rng(123)
        init_multi_pathogen(engine, profiles, {"multi_pathogen": {}}, rng)
        noro_zero = sum(
            1 for a in engine.agents
            if a.susceptibility_multiplier.get("norovirus_gii4", 1.0) == 0.0
        )
        sars_zero = sum(
            1 for a in engine.agents
            if a.susceptibility_multiplier.get("sars_cov2_resp", 1.0) == 0.0
        )
        assert 25 <= noro_zero <= 55  # ~20% of 200
        assert sars_zero == 0

    def test_active_norwalk_nonsus_zero_for_goldens(self) -> None:
        data = json.loads(
            (REPO_ROOT / "data/pathogens/active_profiles.json").read_text(),
        )
        norwalk = next(p for p in data["pathogens"] if p["pathogen_id"] == "norwalk_gi")
        assert norwalk.get("innate_nonsusceptible_fraction", 0.0) == pytest.approx(0.0)

    def test_edison_noro_has_fut2_fraction(self) -> None:
        data = json.loads(
            (REPO_ROOT / "data/pathogens/edison_10pathogen_profiles.json").read_text(),
        )
        noro = next(p for p in data["pathogens"] if p["pathogen_id"] == "norovirus_gii4")
        assert noro["innate_nonsusceptible_fraction"] == pytest.approx(0.20)
        assert noro["nonsusceptible_mechanism"] == "FUT2_nonsecretor"
