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


# ── classifier, witnesses and record shapes on dict fixtures ─────────


def test_classifier_threshold_table():
    cases = [
        (0.0, 5e-13, "archetype"),
        (0.0, 1e-9, "expected"),
        (1e-9, 2e-9, "expected"),
        (5e-13, 7e-13, "archetype"),
    ]
    for va, vd, label in cases:
        result = probe.classify_divergence({"q": {"a": va, "d": vd}})
        assert result["class"] == label, (va, vd, result)


def _gate_event(kind: str, pathogen: str, zone: str) -> dict:
    return {
        "kind": kind, "pathogen": pathogen, "zone": zone,
        "draw_start": 0, "draw_end": 10,
    }


def _snap(zone_masses: dict, class_masses: dict | None = None) -> dict:
    return {
        "zone_gec": dict(zone_masses),
        "zone_class_gec": dict(class_masses or {}),
    }


def test_zone_gate_prefers_the_exact_zero_branch():
    # KidsClub pools differ but are both macroscopic; PoolDeck is an exact
    # 0.0 in A vs residue-free mass in D -- the gate that diverged.
    enc_a = {"containing": _gate_event(
        "class_pickup_requests", "norwalk_gi", "KidsClub",
    )}
    enc_d = {"containing": _gate_event(
        "pickup_by_class", "norwalk_gi", "PoolDeck",
    )}
    snap_a = _snap({"norwalk_gi|KidsClub": 1e-3, "norwalk_gi|PoolDeck": 0.0})
    snap_d = _snap({"norwalk_gi|KidsClub": 5e-4, "norwalk_gi|PoolDeck": 5e-8})
    gate = probe._zone_gate(enc_a, enc_d, snap_a, snap_d, [], [])
    assert gate["gate"] == "_pathway_fomite surface_mass <= 0"
    assert gate["pathogen"] == "norwalk_gi"
    assert gate["is_norwalk_gi"] is True
    assert gate["zone"] == "PoolDeck"
    assert gate["pool_gec"] == {"a": 0.0, "d": 5e-8}


def _delivery(zone: str, delivered: dict, pathogen: str = "norwalk_gi"):
    return {
        "kind": "deliver_by_class", "zone": zone, "pathogen": pathogen,
        "delivered_by_class_gec": dict(delivered),
    }


def test_ordering_witness_rules():
    same = [_delivery("Z", {"c1": 1e-6}), _delivery("Y", {"c1": 2e-6})]
    assert probe._ordering_witness(same, same, 3) is None
    # Below the residue floor on either side: ignored.
    residue = [_delivery("Z", {"c1": 5e-13})]
    other = [_delivery("Z", {"c1": 7e-13})]
    assert probe._ordering_witness(residue, other, 0) is None
    # A real first difference: returns epoch/zone/class row.
    arm_d = [_delivery("Z", {"c1": 1e-6}), _delivery("Y", {"c1": 4e-6})]
    hit = probe._ordering_witness(same, arm_d, 7)
    assert hit["epoch"] == 7
    assert hit["event_index"] == 1
    assert hit["zone"] == "Y"
    assert hit["item_class"] == "c1"
    assert hit["a_gec"] == pytest.approx(2e-6)
    assert hit["d_gec"] == pytest.approx(4e-6)
    # Pathogen filter keeps it norovirus-only when asked.
    flu_a = [_delivery("Z", {"c1": 1e-6}, pathogen="influenza_a")]
    flu_d = [_delivery("Z", {"c1": 2e-6}, pathogen="influenza_a")]
    assert probe._ordering_witness(flu_a, flu_d, 0, pathogen="norwalk_gi") is None
    assert probe._ordering_witness(flu_a, flu_d, 0) is not None


def test_enclosing_event_and_structural_diff():
    inner = {"kind": "h2m", "agent_id": 1, "draw_start": 5, "draw_end": 8}
    outer = {"kind": "path", "agent_id": 1, "draw_start": 0, "draw_end": 20}
    tail = {"kind": "h2m", "agent_id": 2, "draw_start": 30, "draw_end": 33}
    enc = probe._enclosing_event([outer, inner, tail], 6)
    assert enc["containing"] is inner  # innermost span wins
    gap = probe._enclosing_event([outer, inner, tail], 25)
    assert gap["before"] is inner  # last event in list order before d_star
    assert gap["after"] is tail

    events_a = [
        {"kind": "a", "zone": "Z", "agent_id": 1},
        {"kind": "b", "zone": "Z", "agent_id": 2},
    ]
    events_d = [
        {"kind": "a", "zone": "Z", "agent_id": 1},
        {"kind": "b", "zone": "Z", "agent_id": 9},
    ]
    last_aligned, diff = probe._structural_diff(events_a, events_d)
    assert last_aligned == 0
    assert diff["index"] == 1
    assert diff["a"]["agent_id"] == 2
    assert diff["d"]["agent_id"] == 9
    assert probe._structural_diff(events_a, events_a) == (1, None)


def _stub_arm(trace: list, events: list):
    from types import SimpleNamespace

    return SimpleNamespace(
        core_rng=SimpleNamespace(trace=trace),
        root_rng=SimpleNamespace(trace=[]),
        events=events,
    )


def test_divergence_record_shape():
    h2m = probe._ctx_id("hand_to_mouth")
    event = {
        "kind": "hand_to_mouth", "pathogen": "norwalk_gi", "zone": None,
        "agent_id": 5, "hand_load_gec": 1e-6, "dose_gec": 1e-8,
        "draw_start": 0, "draw_end": 5, "phase": "pathway_fomite|norwalk_gi",
    }
    arm = _stub_arm([(h2m, "uniform", ("0.008", "0.012"))], [event])
    snap = _snap({})
    counts = {"all": {k: 0 for k in probe.COUNTER_KEYS}}
    record = probe._divergence_record(
        3, "core", 0, arm, arm, snap, snap, {5: 1e-6}, {5: 1e-6},
        {"a": counts, "d": counts}, None, None,
    )
    assert record["epoch"] == 3
    assert record["generator"] == "core"
    assert record["d_star_index"] == 0
    assert record["counts_identical_before_divergence"] is True
    assert record["enclosing_event_a"]["containing"] is event
    assert record["first_structural_diff"] is None
    assert record["zone_gate"] is None
    for key in (
        "entry_a", "entry_d", "window_a", "window_d", "mass_diffs",
        "events_a", "events_d", "hand_loads_at_epoch_start",
        "ordering_witness", "classification",
    ):
        assert key in record


# ── end-to-end CLI path ──────────────────────────────────────────────


def test_main_end_to_end_two_epochs(tmp_path):
    import os
    import tempfile

    # --out must sit under the repo root or home (the _safe_path contract).
    with tempfile.TemporaryDirectory(dir=os.path.expanduser("~")) as home_tmp:
        out = os.path.join(home_tmp, "probe_out.json")
        rc = probe.main([
            "--seeds", "8001", "--epochs", "2", "--num-agents", "60",
            "--out", out,
        ])
        assert rc == 0
        payload = json.loads(open(out).read())
    assert payload["measured_at"]
    seed = payload["seeds"]["8001"]
    divergence = seed["divergence"]
    if divergence is not None:
        assert divergence["counts_identical_before_divergence"] is True
        assert divergence["epoch"] in range(2)
    assert len(seed["epoch_rows"]) == 2
    for row in seed["epoch_rows"]:
        h2m = row["hand_to_mouth_calls"]
        for key in ("a_all", "d_all", "a_norwalk", "d_norwalk"):
            assert isinstance(h2m[key], int)
            assert h2m[key] >= 0
