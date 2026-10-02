"""Tests for the PPE wear-fatigue channel (ship_function_capacity_spec §7).

Covers the registry/typing parse, the declared-source accumulator, the
§7.3 fatigue-refusal draw writing into the shared compliance machinery,
the §7.4 endogenous onset landing on the symptomatic-presentation axis,
and the paired-seed proof that absent and present-but-disabled are
bit-identical.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from engines.infection_dynamics_bridge import KorkinAgent
from engines.non_pharmaceutical_interventions import resolve_npi
from engines.ppe_fatigue import (
    PpeFatiguePolicy,
    PpeFatigueTracker,
    build_ppe_fatigue_tracker,
    resolve_ppe_types,
)
from orchestrator_epoch import step_ppe_fatigue
from orchestrator_types import SimulationState

REGISTRY = {
    "surgical_mask": {
        "fatigue_rate_per_epoch": 0.2,
        "heat_load": 0.1,
        "dexterity_impairment": 0.0,
        "fatigue_conditions": [
            {"condition_id": "mask_dermatitis", "rate_per_wear_hour": 0.0,
             "symptomatic": True},
        ],
    },
    "n95": {
        "fatigue_rate_per_epoch": 0.5,
        "heat_load": 0.3,
        "dexterity_impairment": 0.0,
        "fatigue_conditions": [
            {"condition_id": "sinonasal_complaints",
             "rate_per_wear_hour": 2.0, "symptomatic": True},
        ],
    },
    "chemical_gloves": {
        "fatigue_rate_per_epoch": 0.3,
        "heat_load": 0.2,
        "dexterity_impairment": 0.3,
    },
}

NPI_BLOCK = {
    "medical_ppe": {
        "source": "test fixture",
        "coverage_by_role": {
            "crew": {"coverage": 1.0, "ppe_type": ["n95", "chemical_gloves"]},
            "passenger": 1.0,
        },
        "compliance": 1.0,
        "reference_multipliers": {"fomite": 0.5},
    },
}


def _cfg(**ppe_fatigue) -> dict:
    return {
        "ppe_types": REGISTRY,
        "ppe_fatigue": {"enabled": True, **ppe_fatigue},
        "non_pharmaceutical_interventions": NPI_BLOCK,
    }


def _agent(agent_id: int = 0, role: str = "crew") -> KorkinAgent:
    return KorkinAgent(
        agent_id=agent_id,
        role=role,
        immune=False,
        home_zone="cabin_a",
        dining_zone="galley",
        work_zone="deck",
        free_zone="lounge",
        schedule=[],
    )


def _covered_agent(agent_id: int = 0, role: str = "crew") -> KorkinAgent:
    agent = _agent(agent_id, role)
    agent.npi_measures = ("medical_ppe",)
    agent.dose_reduction_multipliers = {"fomite": 0.5}
    return agent


class TestCoverageTyping:
    def test_typed_and_bare_entries(self) -> None:
        measures = resolve_npi({"non_pharmaceutical_interventions": NPI_BLOCK})
        measure = measures["medical_ppe"]
        assert measure.coverage_by_role == {"crew": 1.0, "passenger": 1.0}
        assert measure.ppe_types_by_role == {
            "crew": ("n95", "chemical_gloves"),
            "passenger": None,
        }

    def test_bare_float_keeps_legacy_semantics(self) -> None:
        measures = resolve_npi({"non_pharmaceutical_interventions": {
            "legacy": {
                "source": "t",
                "coverage_by_role": {"crew": 0.5},
                "reference_multipliers": {"fomite": 0.5},
            },
        }})
        assert measures["legacy"].coverage_by_role == {"crew": 0.5}
        assert measures["legacy"].ppe_types_by_role == {"crew": None}

    def test_bad_entry_rejected(self) -> None:
        with pytest.raises(ValueError, match="ppe_type"):
            resolve_npi({"non_pharmaceutical_interventions": {
                "bad": {
                    "source": "t",
                    "coverage_by_role": {
                        "crew": {"coverage": 0.5, "ppe_type": 3},
                    },
                    "reference_multipliers": {"fomite": 0.5},
                },
            }})


class TestRegistry:
    def test_parse(self) -> None:
        types = resolve_ppe_types({"ppe_types": REGISTRY})
        assert set(types) == {"surgical_mask", "n95", "chemical_gloves"}
        assert types["n95"].fatigue_rate_per_epoch == 0.5
        assert types["n95"].fatigue_conditions[0].condition_id == (
            "sinonasal_complaints"
        )

    def test_absent_is_empty(self) -> None:
        assert resolve_ppe_types({}) == {}
        assert resolve_ppe_types(None) == {}

    def test_negative_rate_rejected(self) -> None:
        bad = dict(REGISTRY)
        bad["n95"] = {"fatigue_rate_per_epoch": -1.0, "heat_load": 0.0,
                      "dexterity_impairment": 0.0}
        with pytest.raises(ValueError, match="fatigue_rate_per_epoch"):
            resolve_ppe_types({"ppe_types": bad})

    def test_enabled_unknown_type_rejected(self) -> None:
        cfg = _cfg()
        cfg["non_pharmaceutical_interventions"] = {
            "m": {
                "source": "t",
                "coverage_by_role": {
                    "crew": {"coverage": 1.0, "ppe_type": "moonboots"},
                },
                "reference_multipliers": {"fomite": 0.5},
            },
        }
        with pytest.raises(ValueError, match="moonboots"):
            build_ppe_fatigue_tracker(cfg)

    def test_disabled_allows_unknown_type(self) -> None:
        cfg = _cfg(enabled=False)
        cfg["non_pharmaceutical_interventions"] = {
            "m": {
                "source": "t",
                "coverage_by_role": {
                    "crew": {"coverage": 1.0, "ppe_type": "moonboots"},
                },
                "reference_multipliers": {"fomite": 0.5},
            },
        }
        tracker = build_ppe_fatigue_tracker(cfg)
        assert not tracker.active


class TestAccumulator:
    def test_wear_hours_and_fatigue_sum(self) -> None:
        tracker = build_ppe_fatigue_tracker(
            _cfg(), rng=np.random.default_rng(7),
        )
        agent = _covered_agent()
        tracker.step_epoch(0, [agent], hours_per_epoch=24.0)
        assert agent.ppe_wear_hours_by_type == {
            "n95": 24.0, "chemical_gloves": 24.0,
        }
        # 24 h * (0.5 + 0.3) declared rate; no refusal draw below threshold.
        assert agent.fatigue_score == pytest.approx(24.0 * 0.8)
        assert agent.ppe_dexterity_impairment == pytest.approx(0.3)
        tracker.step_epoch(1, [agent], hours_per_epoch=24.0)
        assert agent.ppe_wear_hours_by_type["n95"] == 48.0
        assert agent.fatigue_score == pytest.approx(48.0 * 0.8)

    def test_default_type_resolution(self) -> None:
        tracker = build_ppe_fatigue_tracker(
            _cfg(), rng=np.random.default_rng(7),
        )
        agent = _covered_agent(role="passenger")
        tracker.step_epoch(0, [agent], hours_per_epoch=24.0)
        assert set(agent.ppe_wear_hours_by_type) == {"surgical_mask"}
        assert agent.fatigue_score == pytest.approx(24.0 * 0.2)

    def test_uncovered_agent_accrues_nothing(self) -> None:
        tracker = build_ppe_fatigue_tracker(
            _cfg(), rng=np.random.default_rng(7),
        )
        agent = _agent()  # no npi_measures
        tracker.step_epoch(0, [agent], hours_per_epoch=24.0)
        assert agent.ppe_wear_hours_by_type == {}
        assert agent.fatigue_score == 0.0

    def test_sustenance_deficit_reads_presence_guarded(self) -> None:
        tracker = build_ppe_fatigue_tracker(
            _cfg(), rng=np.random.default_rng(7),
        )
        # Absent field (KorkinAgent carries no slot for it): no crash, no sum.
        agent = _covered_agent()
        tracker.step_epoch(0, [agent], hours_per_epoch=24.0)
        assert agent.fatigue_score == pytest.approx(24.0 * 0.8)

        # Present field: the sibling sustenance arm's declared per-epoch
        # input adds into the same accumulator.
        stub = SimpleNamespace(
            agent_id=1, role="crew", agent_class="crew",
            npi_measures=("medical_ppe",),
            ppe_wear_hours_by_type={}, fatigue_score=0.0,
            ppe_dexterity_impairment=0.0, ppe_condition_ids=set(),
            ppe_fatigue_refused=False, ppe_symptomatic_active=False,
            dose_reduction_multipliers={"fomite": 0.5},
            sustenance_deficit=2.0,
            has_departed=lambda epoch: False,
        )
        tracker.step_epoch(0, [stub], hours_per_epoch=24.0)
        assert stub.fatigue_score == pytest.approx(24.0 * 0.8 + 2.0)


class TestRefusal:
    def _tracker(self, probability: float = 1.0) -> PpeFatigueTracker:
        return build_ppe_fatigue_tracker(
            _cfg(
                fatigue_refusal_threshold=1.0,
                fatigue_refusal_probability_per_epoch=probability,
            ),
            rng=np.random.default_rng(3),
        )

    def test_refusal_drops_multipliers_and_sticks(self) -> None:
        tracker = self._tracker(probability=1.0)
        agent = _covered_agent()
        refused, _ = tracker.step_epoch(0, [agent], hours_per_epoch=24.0)
        # fatigue 19.2 >= threshold 1.0, draw probability 1.0 -> refuses.
        assert refused == [agent.agent_id]
        assert agent.ppe_fatigue_refused is True
        assert agent.dose_reduction_multipliers == {}
        assert agent.agent_id in tracker.refusers
        # Sticky: a later epoch does not re-log or re-reduce.
        refused2, _ = tracker.step_epoch(1, [agent], hours_per_epoch=24.0)
        assert refused2 == []
        # And the refuser stops accruing wear while keeping the deficit sum.
        assert agent.ppe_wear_hours_by_type["n95"] == 24.0

    def test_below_threshold_never_refuses(self) -> None:
        tracker = self._tracker(probability=1.0)
        tracker.policy = PpeFatiguePolicy(
            enabled=True, fatigue_refusal_threshold=1e9,
            fatigue_refusal_probability_per_epoch=1.0,
        )
        agent = _covered_agent()
        refused, _ = tracker.step_epoch(0, [agent], hours_per_epoch=24.0)
        assert refused == []
        assert agent.dose_reduction_multipliers == {"fomite": 0.5}

    def test_compliance_log_write(self) -> None:
        tracker = self._tracker(probability=1.0)
        agent = _covered_agent()
        state = SimulationState()
        clock = type("C", (), {"hours_per_epoch": 24.0})()
        step_ppe_fatigue(0, [agent], state, clock, tracker)
        assert state.compliance_log == [{
            "epoch": 0, "agent_id": agent.agent_id,
            "action": "refused_ppe_fatigue", "compliance_class": None,
        }]


class TestEndogenousOnset:
    def test_symptomatic_onset_lands_on_presentation_axis(self) -> None:
        tracker = build_ppe_fatigue_tracker(
            _cfg(), rng=np.random.default_rng(5),
        )
        agent = _covered_agent()
        _, onsets = tracker.step_epoch(0, [agent], hours_per_epoch=24.0)
        # rate 2.0/h -> hazard ~1.0; sinonasal_complaints onset is certain.
        assert (agent.agent_id, "sinonasal_complaints") in onsets
        assert "sinonasal_complaints" in agent.ppe_condition_ids
        assert agent.ppe_symptomatic_active is True
        exported = agent.to_schema_dict()
        assert exported["symptom_presentation"] == "symptomatic"
        # Not infected: the infectious state is untouched.
        assert exported["infection_state"] == "susceptible"

    def test_onset_is_sticky_once_held(self) -> None:
        tracker = build_ppe_fatigue_tracker(
            _cfg(), rng=np.random.default_rng(5),
        )
        agent = _covered_agent()
        tracker.step_epoch(0, [agent], hours_per_epoch=24.0)
        _, onsets = tracker.step_epoch(1, [agent], hours_per_epoch=24.0)
        assert onsets == []


@pytest.mark.timeout(300)
def test_disabled_block_is_bit_identical_to_absent() -> None:
    """Paired seeded smoke: declared-and-off must equal never-declared."""
    from picard_framework import PicardRunSpec, ShipSimulation

    spec_path = os.path.join(
        REPO_ROOT, "picard_framework/runs/smoke_2epoch.json",
    )
    spec_off = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
    # Declared but disabled — the shape config.yaml ships.
    spec_off.legacy_cfg.setdefault("ppe_fatigue", {})["enabled"] = False
    spec_off.legacy_cfg.setdefault("ppe_types", dict(REGISTRY))

    spec_absent = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
    spec_absent.legacy_cfg.pop("ppe_fatigue", None)
    spec_absent.legacy_cfg.pop("ppe_types", None)

    run_off = ShipSimulation(spec_off, display=False, repo_root=REPO_ROOT).run()
    run_absent = ShipSimulation(
        spec_absent, display=False, repo_root=REPO_ROOT,
    ).run()
    assert run_off.history == run_absent.history
