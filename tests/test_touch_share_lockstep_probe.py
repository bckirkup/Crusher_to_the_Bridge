"""Identity tests for the NORO-TOUCH-SHARE-02 epoch-lockstep probe.

The probe is read-only: a ``TracingGenerator`` proxy plus read-only
``TransmissionCore`` wrappers must leave the pooled default path bit-
identical (root and core RNG state, surface pools, hand loads), and a
paired A/A run must produce identical traces. The classification unit test
pins the frozen rule's three labels.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from picard_framework.run_spec import PicardRunSpec
from picard_framework.simulation.ship_simulation import ShipSimulation
from simulation_utils.paths import validated_open
from tools.noro_diag import touch_share_lockstep_probe as probe
from tools.noro_diag.per_host_dose_challenge import build_spec

EPOCHS = 6
NUM_AGENTS = 60


def _spec_dict(seed: int, fomite_representation: str | None = None) -> dict:
    return build_spec(
        seed=seed, platform="classic_cruise_1900",
        bundle="active_profiles", epochs=EPOCHS, num_agents=NUM_AGENTS,
        pathogen_id="norwalk_gi", alpha=None, beta=1.0,
        fomite_representation=fomite_representation,
        fomite_touch_share=(
            "areal" if fomite_representation == "per_surface" else None
        ),
    )


def _sim(spec_dict: dict, tmp_path) -> ShipSimulation:
    path = tmp_path / "spec.json"
    with validated_open(str(path), "w", allowed_roots=(str(tmp_path),)) as fh:
        fh.write(json.dumps(spec_dict))
    spec = PicardRunSpec.from_picard_json(str(probe.REPO_ROOT), str(path))
    sim = ShipSimulation(spec, display=False)
    sim.initialize()
    return sim


def _hand_loads(sim: ShipSimulation) -> dict[int, float]:
    return {
        agent.agent_id: agent.hand_load_by_pathogen.get("norwalk_gi", 0.0)
        for agent in sim.engine.agents
    }


def _surface_pools(sim: ShipSimulation) -> dict[str, float]:
    return dict(sim.tx_core.surface_pools_by_pathogen.get("norwalk_gi", {}))


def _states(sim: ShipSimulation) -> tuple[dict, dict]:
    return (
        sim.rng.bit_generator.state,
        sim.tx_core.rng.bit_generator.state,
    )


def test_instrumentation_is_bit_identical_on_pooled_default(tmp_path):
    plain = _sim(_spec_dict(8105), tmp_path)
    for _ in range(EPOCHS):
        plain.step()

    traced = _sim(_spec_dict(8105), tmp_path)
    arm = probe.Arm("plain", traced)
    with probe.lockstep_instrumented(probe._ACTIVE):
        for _ in range(EPOCHS):
            arm.begin_epoch()
            probe._ACTIVE["arm"] = arm
            traced.step()
    probe._ACTIVE["arm"] = None

    state_plain, state_traced = _states(plain), _states(traced)
    for gen in range(2):
        assert probe._state_equal(state_plain[gen], state_traced[gen]), (
            f"generator {gen} bit-state moved under instrumentation"
        )
    assert _surface_pools(plain) == pytest.approx(_surface_pools(traced))
    assert _hand_loads(plain) == pytest.approx(_hand_loads(traced))
    assert arm.core_rng.draws > 0


def test_paired_arm_traces_are_identical(tmp_path):
    arm_a = probe.Arm("a", _sim(_spec_dict(8106, "per_surface"), tmp_path))
    arm_b = probe.Arm("b", _sim(_spec_dict(8106, "per_surface"), tmp_path))
    with probe.lockstep_instrumented(probe._ACTIVE):
        for _ in range(3):
            for arm in (arm_a, arm_b):
                arm.begin_epoch()
                probe._ACTIVE["arm"] = arm
                arm.sim.step()
            probe._ACTIVE["arm"] = None
            assert arm_a.core_rng.trace == arm_b.core_rng.trace
            assert probe._state_equal(
                arm_a.core_rng.bit_generator.state,
                arm_b.core_rng.bit_generator.state,
            )


def test_classification_labels():
    archetype = probe.classify_divergence(
        {"surface_mass|Z": {"a": 1e-13, "d": 0.0}},
    )
    assert archetype["class"] == "archetype"
    assert archetype["gate_quantities"] == ["surface_mass|Z"]

    expected = probe.classify_divergence(
        {"class_mass|Z|c": {"a": 0.3, "d": 0.2}},
    )
    assert expected["class"] == "expected"

    assert probe.classify_divergence({})["class"] == "other"


def test_zone_gate_classification():
    """Frozen rule on the zone-pool gate quantity itself."""
    expected = probe.classify_divergence(
        {"zone_pool_gec": {"a": 0.0, "d": 3.2e-7}},
    )
    assert expected["class"] == "expected"

    archetype = probe.classify_divergence(
        {"zone_pool_gec": {"a": 0.0, "d": 5e-13}},
    )
    assert archetype["class"] == "archetype"
    assert archetype["gate_quantities"] == ["zone_pool_gec"]


def test_tracer_passes_through_state_and_returns(tmp_path):
    gen = np.random.default_rng(1)
    tracer = probe.TracingGenerator(gen)
    assert tracer.bit_generator is gen.bit_generator
    assert tracer.state == gen.bit_generator.state
    draw = tracer.uniform(0.0, 1.0)
    expected = np.random.default_rng(1).uniform(0.0, 1.0)
    assert tracer.trace[-1][1] == "uniform"
    assert draw == pytest.approx(expected)
    # Return value is the real generator's, unchanged.
    gen2 = np.random.default_rng(2)
    tr2 = probe.TracingGenerator(gen2)
    ref = np.random.default_rng(2)
    assert tr2.normal(5.0, 2.0, 4) == pytest.approx(ref.normal(5.0, 2.0, 4))
