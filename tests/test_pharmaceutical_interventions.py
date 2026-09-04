"""Behaviour of the vaccination and oseltamivir intervention axes.

The tests here are about separation: coverage from efficacy, efficacy
against acquisition from efficacy against illness, and treatment from
prophylaxis. Each of those pairs is a distinct quantity in the evidence,
and a run must be able to move one and leave the other where it was.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from engines.pharmaceutical_interventions import (
    DEFAULT_PROPHYLAXIS_EFFICACY_AGAINST_ILLNESS,
    DEFAULT_TREATMENT_ILLNESS_REDUCTION_DAYS,
    DEFAULT_VACCINE_EFFICACY_AGAINST_ILLNESS,
    apply_treatment_at_onset,
    assign_host_pharmacology,
    illness_multiplier,
    resolve_pharmacology,
)

PID = "influenza_a"


class _Host:
    """The three attributes the intervention layer reads from an agent."""

    def __init__(self, agent_id: int, role: str) -> None:
        self.agent_id = agent_id
        self.role = role
        self.susceptibility_multiplier: dict[str, float] = {PID: 1.0}
        self.pharma_by_pathogen: dict[str, dict[str, Any]] = {}


def _population(passengers: int = 200, crew: int = 200) -> list[_Host]:
    return [
        *[_Host(i, "passenger") for i in range(passengers)],
        *[_Host(passengers + i, "crew") for i in range(crew)],
    ]


def _assign(config: dict[str, Any], seed: int = 7) -> list[_Host]:
    agents = _population()
    assign_host_pharmacology(
        agents,
        resolve_pharmacology({"pharmaceutical_interventions": {PID: config}}),
        np.random.default_rng(seed),
    )
    return agents


def _share(agents: list[_Host], key: str, role: str) -> float:
    matching = [a for a in agents if a.role == role]
    return sum(
        bool(a.pharma_by_pathogen[PID][key]) for a in matching
    ) / len(matching)


class TestConfigurationBounds:
    def test_absent_config_leaves_the_run_untouched(self) -> None:
        assert resolve_pharmacology({}) == {}
        assert resolve_pharmacology(None) == {}
        assert illness_multiplier(_Host(0, "crew"), PID) == pytest.approx(1.0)

    @pytest.mark.parametrize("bad", [-0.01, 1.01, float("nan")])
    def test_coverage_outside_the_unit_interval_is_rejected(
        self, bad: float,
    ) -> None:
        with pytest.raises(ValueError, match="coverage_by_role"):
            resolve_pharmacology({
                "pharmaceutical_interventions": {
                    PID: {"vaccination": {"coverage_by_role": {"crew": bad}}},
                },
            })

    @pytest.mark.parametrize("bad", [-0.5, 1.5])
    def test_efficacy_outside_the_unit_interval_is_rejected(
        self, bad: float,
    ) -> None:
        with pytest.raises(ValueError, match="efficacy_against_illness"):
            resolve_pharmacology({
                "pharmaceutical_interventions": {
                    PID: {"vaccination": {"efficacy_against_illness": bad}},
                },
            })

    def test_negative_treatment_duration_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="shedding_reduction_days"):
            resolve_pharmacology({
                "pharmaceutical_interventions": {
                    PID: {
                        "antiviral": {
                            "treatment": {"shedding_reduction_days": -1.0},
                        },
                    },
                },
            })

    def test_defaults_are_the_sourced_pooled_effects(self) -> None:
        """Change-detector on the three defaults that carry a citation."""
        resolved = resolve_pharmacology({
            "pharmaceutical_interventions": {
                PID: {"vaccination": {}, "antiviral": {}},
            },
        })[PID]
        assert resolved.vaccination is not None
        assert resolved.antiviral is not None
        # Ge 2025 pooled VE against laboratory-confirmed influenza.
        assert resolved.vaccination.efficacy_against_illness == pytest.approx(
            0.4848,
        )
        # Zhao 2024 WHO NMA, oseltamivir PEP RR 0.40 against symptomatic.
        assert resolved.antiviral.prophylaxis_efficacy_against_illness == (
            pytest.approx(0.60)
        )
        # Neither intervention is credited with preventing infection itself.
        assert resolved.vaccination.efficacy_against_acquisition == pytest.approx(
            0.0,
        )
        assert (
            resolved.antiviral.prophylaxis_efficacy_against_acquisition
            == pytest.approx(0.0)
        )
        # Ng 2010's transmission interval spans no effect, so no effect.
        assert resolved.antiviral.treatment_transmission_multiplier == pytest.approx(
            1.0,
        )


class TestCoverage:
    @pytest.mark.parametrize(
        "coverage", [0.0, 0.25, 0.5, 0.9, 1.0],
    )
    def test_realised_coverage_tracks_the_declared_share(
        self, coverage: float,
    ) -> None:
        agents = _assign(
            {"vaccination": {"coverage_by_role": {"crew": coverage}}},
        )
        assert _share(agents, "vaccinated", "crew") == pytest.approx(
            coverage, abs=0.08,
        )

    def test_coverage_is_per_role(self) -> None:
        """Millman's ships covered crew heavily and passengers not at all."""
        agents = _assign(
            {"vaccination": {"coverage_by_role": {"crew": 0.955}}},
        )
        assert _share(agents, "vaccinated", "crew") > 0.9
        assert _share(agents, "vaccinated", "passenger") == pytest.approx(0.0)

    def test_an_unnamed_role_is_uncovered(self) -> None:
        agents = _assign(
            {"vaccination": {"coverage_by_role": {"engineer": 1.0}}},
        )
        assert _share(agents, "vaccinated", "crew") == pytest.approx(0.0)
        assert _share(agents, "vaccinated", "passenger") == pytest.approx(0.0)


class TestEfficacyAxesAreSeparate:
    def test_illness_efficacy_leaves_acquisition_alone(self) -> None:
        agents = _assign({
            "vaccination": {
                "coverage_by_role": {"crew": 1.0},
                "efficacy_against_acquisition": 0.0,
                "efficacy_against_illness": 0.4848,
            },
        })
        crew = [a for a in agents if a.role == "crew"]
        assert all(
            a.susceptibility_multiplier[PID] == pytest.approx(1.0)
            for a in crew
        )
        assert all(
            illness_multiplier(a, PID) == pytest.approx(1.0 - 0.4848)
            for a in crew
        )

    def test_acquisition_efficacy_scales_susceptibility(self) -> None:
        agents = _assign({
            "vaccination": {
                "coverage_by_role": {"crew": 1.0},
                "efficacy_against_acquisition": 0.3,
                "efficacy_against_illness": 0.0,
            },
        })
        crew = [a for a in agents if a.role == "crew"]
        assert all(
            a.susceptibility_multiplier[PID] == pytest.approx(0.7)
            for a in crew
        )
        assert all(
            illness_multiplier(a, PID) == pytest.approx(1.0) for a in crew
        )

    @pytest.mark.parametrize(
        "efficacy", [0.0, 0.2, 0.4848, 0.8, 1.0],
    )
    def test_illness_multiplier_is_graded_in_efficacy(
        self, efficacy: float,
    ) -> None:
        agents = _assign({
            "vaccination": {
                "coverage_by_role": {"crew": 1.0},
                "efficacy_against_illness": efficacy,
            },
        })
        crew = next(a for a in agents if a.role == "crew")
        assert illness_multiplier(crew, PID) == pytest.approx(1.0 - efficacy)

    def test_vaccination_and_prophylaxis_compound_on_the_illness_axis(
        self,
    ) -> None:
        agents = _assign({
            "vaccination": {
                "coverage_by_role": {"crew": 1.0},
                "efficacy_against_illness": 0.5,
            },
            "antiviral": {
                "prophylaxis": {
                    "coverage_by_role": {"crew": 1.0},
                    "efficacy_against_illness": 0.6,
                },
            },
        })
        crew = next(a for a in agents if a.role == "crew")
        assert illness_multiplier(crew, PID) == pytest.approx(0.5 * 0.4)
        assert crew.susceptibility_multiplier[PID] == pytest.approx(1.0)


class TestTreatmentIsSeparateFromProphylaxis:
    def _infection(self) -> dict[str, Any]:
        return {"shedding_multiplier": 1.0}

    def _profile(self) -> dict[str, Any]:
        return {"recovery_day": 5, "shedding_duration_days": 7}

    def test_prophylaxis_alone_doses_nobody_at_onset(self) -> None:
        agents = _assign({
            "antiviral": {
                "prophylaxis": {"coverage_by_role": {"crew": 1.0}},
            },
        })
        crew = next(a for a in agents if a.role == "crew")
        infection = self._infection()
        assert not apply_treatment_at_onset(
            crew, PID, infection, self._profile(),
        )
        assert "shedding_duration_days" not in infection
        assert illness_multiplier(crew, PID) == pytest.approx(
            1.0 - DEFAULT_PROPHYLAXIS_EFFICACY_AGAINST_ILLNESS,
        )

    def test_treatment_alone_changes_no_susceptibility_or_illness_risk(
        self,
    ) -> None:
        agents = _assign({
            "antiviral": {
                "treatment": {"coverage_by_role": {"crew": 1.0}},
            },
        })
        crew = next(a for a in agents if a.role == "crew")
        assert crew.susceptibility_multiplier[PID] == pytest.approx(1.0)
        assert illness_multiplier(crew, PID) == pytest.approx(1.0)

    def test_treatment_shortens_illness_and_shedding(self) -> None:
        agents = _assign({
            "antiviral": {
                "treatment": {"coverage_by_role": {"crew": 1.0}},
            },
        })
        crew = next(a for a in agents if a.role == "crew")
        infection = self._infection()
        assert apply_treatment_at_onset(crew, PID, infection, self._profile())
        assert infection["recovery_day"] == pytest.approx(
            5 - DEFAULT_TREATMENT_ILLNESS_REDUCTION_DAYS,
        )
        assert infection["shedding_duration_days"] == pytest.approx(
            7 - DEFAULT_TREATMENT_ILLNESS_REDUCTION_DAYS,
        )
        assert crew.pharma_by_pathogen[PID]["treated"] is True

    @pytest.mark.parametrize(
        "reduction", [0.0, 1.0, 2.0, 3.0],
    )
    def test_shedding_reduction_is_graded_and_floored_at_zero(
        self, reduction: float,
    ) -> None:
        agents = _assign({
            "antiviral": {
                "treatment": {
                    "coverage_by_role": {"crew": 1.0},
                    "shedding_reduction_days": reduction,
                    "illness_reduction_days": 0.0,
                },
            },
        })
        crew = next(a for a in agents if a.role == "crew")
        infection = self._infection()
        apply_treatment_at_onset(crew, PID, infection, {
            "recovery_day": 2, "shedding_duration_days": 2,
        })
        assert infection["shedding_duration_days"] == pytest.approx(
            max(0.0, 2.0 - reduction),
        )
        assert infection["shedding_duration_days"] >= 0.0

    def test_a_dose_arriving_after_the_window_has_no_effect(self) -> None:
        agents = _assign({
            "antiviral": {
                "treatment": {
                    "coverage_by_role": {"crew": 1.0},
                    "start_hours_after_onset": 72.0,
                    "window_hours": 48.0,
                },
            },
        })
        crew = next(a for a in agents if a.role == "crew")
        infection = self._infection()
        assert not apply_treatment_at_onset(
            crew, PID, infection, self._profile(),
        )
        assert infection == {"shedding_multiplier": 1.0}

    @pytest.mark.parametrize("multiplier", [0.25, 1.0])
    def test_onward_transmission_multiplier_scales_shedding(
        self, multiplier: float,
    ) -> None:
        agents = _assign({
            "antiviral": {
                "treatment": {
                    "coverage_by_role": {"crew": 1.0},
                    "transmission_multiplier": multiplier,
                },
            },
        })
        crew = next(a for a in agents if a.role == "crew")
        infection = self._infection()
        apply_treatment_at_onset(crew, PID, infection, self._profile())
        assert infection["shedding_multiplier"] == pytest.approx(multiplier)

    def test_an_untreated_host_keeps_the_profile_natural_history(self) -> None:
        agents = _assign({
            "antiviral": {
                "treatment": {"coverage_by_role": {"crew": 0.0}},
            },
        })
        crew = next(a for a in agents if a.role == "crew")
        infection = self._infection()
        assert not apply_treatment_at_onset(
            crew, PID, infection, self._profile(),
        )
        assert "recovery_day" not in infection


class TestDefaultVaccinePosture:
    def test_a_bare_vaccination_block_protects_against_illness_only(
        self,
    ) -> None:
        agents = _assign({
            "vaccination": {"coverage_by_role": {"crew": 1.0}},
        })
        crew = next(a for a in agents if a.role == "crew")
        assert crew.susceptibility_multiplier[PID] == pytest.approx(1.0)
        assert illness_multiplier(crew, PID) == pytest.approx(
            1.0 - DEFAULT_VACCINE_EFFICACY_AGAINST_ILLNESS,
        )
