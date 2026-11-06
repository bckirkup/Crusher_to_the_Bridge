"""Role-checkpoint sidecar (PAPER1-SENS Child A): set identities, timing,
missingness, and paired off/on invariance on a seeded smoke voyage."""
from __future__ import annotations

import copy
import os

import pytest

from orchestrator_init import update_ever_reported_ids
from orchestrator_types import SimulationState
from picard_framework.simulation import role_checkpoints as rc
from telemetry_buffer.agent_axes import (
    AGENT_SYMPTOM_PRESENTATION,
    PRESENTATION_ASYMPTOMATIC,
    PRESENTATION_SYMPTOMATIC,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _agent(aid: int, role: str, symptomatic: bool = False) -> dict:
    return {
        "agent_id": aid,
        "role": role,
        "agent_class": f"{role}_general",
        AGENT_SYMPTOM_PRESENTATION: (
            PRESENTATION_SYMPTOMATIC if symptomatic else PRESENTATION_ASYMPTOMATIC
        ),
    }


def _state(**sets: set[int]) -> SimulationState:
    state = SimulationState()
    for name, ids in sets.items():
        getattr(state, name).update(ids)
    return state


# ── timing ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("hours", "expected"),
    [
        (1.0, {3: 71, 7: 167, 10: 239, 12: 287}),
        (24.0, {3: 2, 7: 6, 10: 9, 12: 11}),
        (8.0, {3: 8, 7: 20, 10: 29, 12: 35}),
    ],
)
def test_checkpoint_epoch_index_is_last_epoch_before_day_boundary(hours, expected):
    for day, idx in expected.items():
        got, exact = rc.checkpoint_epoch_index(day, hours)
        assert got == idx
        assert exact is True
        # the snapshot covers exactly 24*day hours of voyage
        assert (got + 1) * hours == 24 * day


def test_checkpoint_epoch_index_inexact_boundary_rounds_to_covering_epoch():
    idx, exact = rc.checkpoint_epoch_index(1, 7.0)  # 24/7 = 3.43 epochs
    assert exact is False
    assert idx == 3  # end of the 4th epoch covers the 24 h boundary


def test_resolve_config_defaults_and_disable():
    assert rc.resolve_config({}) == (True, rc.DEFAULT_CHECKPOINT_DAYS)
    assert rc.resolve_config(None) == (True, rc.DEFAULT_CHECKPOINT_DAYS)
    enabled, days = rc.resolve_config(
        {"role_checkpoints": {"enabled": False, "days": [12, 3, 3]}},
    )
    assert enabled is False
    assert days == (3, 12)


# ── set algebra ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("overlap", [0, 1, 3])
def test_role_counts_union_and_overlap_are_set_cardinalities(overlap):
    etio = {1, 2, 3, 4}
    noise = set(sorted(etio)[:overlap]) | {10, 11}  # ``overlap`` ids ⊂ etio
    role_ids = set(range(1, 20))
    counts = rc.role_counts(
        role_ids, infected=etio | {5}, ill=etio | {10}, etiologic=etio,
        noise=noise,
    )
    assert counts["reporter_overlap"] == len(etio & noise) == overlap
    assert counts["unique_person_union"] == len(etio | noise)
    # inclusion–exclusion holds because every number is a set size
    assert counts["unique_person_union"] == (
        counts["unique_etiologic_reporters"]
        + counts["unique_clinical_noise_reporters"]
        - counts["reporter_overlap"]
    )
    # the union partitions by clinical eligibility
    assert counts["union_ever_ill"] + counts["union_not_ill"] \
        == counts["unique_person_union"]
    assert counts["noise_reporters_ever_ill"] == len(noise & (etio | {10}))
    assert counts["infected"] == 5
    assert counts["complement"] == 19


def test_role_counts_restrict_to_role_ids():
    counts = rc.role_counts(
        {1, 2}, infected={1, 2, 3}, ill={3}, etiologic={2, 3}, noise={3},
    )
    assert counts == {
        "complement": 2, "infected": 2, "ill": 0,
        "unique_etiologic_reporters": 1, "unique_clinical_noise_reporters": 0,
        "reporter_overlap": 0, "unique_person_union": 1,
        "union_ever_ill": 0, "union_not_ill": 1, "noise_reporters_ever_ill": 0,
    }


def test_person_reporting_twice_is_one_person():
    """Two sick-call epochs by the same symptomatic agent = one reporter."""
    agents = [_agent(1, "passenger", symptomatic=True), _agent(2, "crew")]
    state = SimulationState()
    for _ in range(2):
        update_ever_reported_ids(
            agents, {"true_positive_ids": [1], "noise_ids": [2]},
            state.ever_reported_ids, state.ever_reported_noise_ids,
        )
    snap = rc.snapshot(
        agents, state, day=1, epoch=23, hours_per_epoch=1.0,
        exact_boundary=True,
    )
    assert snap["passenger"]["unique_etiologic_reporters"] == 1
    assert snap["crew"]["unique_clinical_noise_reporters"] == 1
    assert snap["all"]["unique_person_union"] == 2
    assert snap["epochs_completed"] == 24
    assert snap["hours_elapsed"] == pytest.approx(24.0)


def test_etiologic_reporters_require_symptomatic_presentation():
    """A true-positive id that is not symptomatic never becomes an
    etiologic reporter, so the etiologic set is clinically eligible by
    construction; a noise reporter is not."""
    agents = [_agent(1, "crew", symptomatic=False), _agent(2, "crew")]
    state = SimulationState()
    update_ever_reported_ids(
        agents, {"true_positive_ids": [1], "noise_ids": [2]},
        state.ever_reported_ids, state.ever_reported_noise_ids,
    )
    snap = rc.snapshot(
        agents, state, day=1, epoch=0, hours_per_epoch=24.0,
        exact_boundary=True,
    )
    crew = snap["crew"]
    assert crew["unique_etiologic_reporters"] == 0
    assert crew["unique_clinical_noise_reporters"] == 1
    assert crew["union_ever_ill"] == 0
    assert crew["union_not_ill"] == 1


def test_snapshot_separates_roles_from_agent_dicts():
    agents = [_agent(1, "passenger"), _agent(2, "crew"), _agent(3, "crew")]
    state = _state(
        ever_infected_ids={1, 2}, ever_ill_ids={2}, ever_reported_ids={2},
        ever_reported_noise_ids={1, 3},
    )
    snap = rc.snapshot(
        agents, state, day=3, epoch=71, hours_per_epoch=1.0,
        exact_boundary=True,
    )
    assert snap["passenger"]["complement"] == 1
    assert snap["crew"]["complement"] == 2
    assert snap["passenger"]["unique_clinical_noise_reporters"] == 1
    assert snap["crew"]["unique_etiologic_reporters"] == 1
    assert snap["crew"]["unique_person_union"] == 2
    assert snap["all"]["unique_person_union"] == 3


# ── recording / block ───────────────────────────────────────────────────────

def test_maybe_record_snapshots_only_at_declared_epochs_and_is_read_only():
    agents = [_agent(1, "passenger"), _agent(2, "crew")]
    state = _state(ever_infected_ids={1}, ever_reported_ids={1})
    before = copy.deepcopy({
        k: getattr(state, k) for k in (
            "ever_infected_ids", "ever_ill_ids", "ever_reported_ids",
            "ever_reported_noise_ids",
        )
    })
    cfg = {"role_checkpoints": {"days": [1, 2]}}
    for epoch in range(48):
        rc.maybe_record(state, agents, epoch=epoch, cfg=cfg, hours_per_epoch=1.0)
        if epoch == 22:
            assert state.role_checkpoints == {}
    assert set(state.role_checkpoints) == {"day_1", "day_2"}
    assert state.role_checkpoints["day_1"]["epoch_index"] == 23
    assert state.role_checkpoints["day_2"]["epoch_index"] == 47
    for k, v in before.items():
        assert getattr(state, k) == v


def test_finalize_block_marks_unreached_days_unavailable_never_zero():
    state = _state()
    cfg = {"role_checkpoints": {"days": [3, 12]}}
    rc.maybe_record(state, [], epoch=71, cfg=cfg, hours_per_epoch=1.0)
    block = rc.finalize_block(
        state, cfg=cfg, hours_per_epoch=1.0, clock_mode="hours", num_epochs=100,
    )
    assert block["clock"]["epoch_mapping"] == {"day_3": 71, "day_12": 287}
    assert block["checkpoints"]["day_3"]["available"] is True
    d12 = block["checkpoints"]["day_12"]
    assert d12["available"] is False
    assert d12["status"] == "not_reached"
    assert all(v is None for v in d12["passenger"].values())
    assert all(v is None for v in d12["crew"].values())
    assert set(d12["passenger"]) == set(rc.MEASURES)
    assert "timing" in block["definitions"]


def test_finalize_block_disabled_is_none():
    assert rc.finalize_block(
        _state(), cfg={"role_checkpoints": {"enabled": False}},
        hours_per_epoch=1.0, clock_mode="hours", num_epochs=288,
    ) is None


@pytest.mark.timeout(600)
def test_paired_seed_off_vs_on_history_identical_except_sidecar():
    """Emitter off vs on, same seed: every history record equal; the only
    difference is the ``role_checkpoints`` key on the final record."""
    from picard_framework import PicardRunSpec, ShipSimulation

    spec_path = os.path.join(REPO_ROOT, "picard_framework/runs/smoke_2epoch.json")

    def _run(enabled: bool):
        spec = PicardRunSpec.from_picard_json(REPO_ROOT, spec_path)
        spec.legacy_cfg["role_checkpoints"] = {"enabled": enabled, "days": [1]}
        sim = ShipSimulation(spec, display=False, repo_root=REPO_ROOT)
        result = sim.run()
        return result, sim.rng.bit_generator.state

    off, rng_off = _run(False)
    on, rng_on = _run(True)
    assert rng_off == rng_on
    assert "role_checkpoints" not in off.history[-1]
    block = on.history[-1].pop("role_checkpoints")
    assert off.history == on.history
    assert block["schema"] == rc.SCHEMA
    # 2-epoch voyage never reaches the day-1 boundary (epoch 23)
    d1 = block["checkpoints"]["day_1"]
    assert d1["available"] is False
    assert d1["epoch_index"] == 23
