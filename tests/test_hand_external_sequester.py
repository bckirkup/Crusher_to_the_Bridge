"""Behavioral guards for the EXTERNAL-SEQUESTER hand-reservoir arm (D2'').

The arm (``docs/proposals/hand_external_sequester_spec.md``) lets
externally acquired hand mass migrate into the wash-proof protected
compartment, bounded by a per-host capacity drawn from the shipped
sequester band, and adds a per-epoch residual mouth draw on the discrete
arm so retained load is re-exposed to a swallow. Both selectors keep
bit-identical defaults (``stool_only`` / ``pickup_only``); the arm adds
zero new constants. Sensitivity-first per ci-test-design: bounds on the
capacity and migration, draw-free bookkeeping, config refusals and the
inert-mode warnings -- no hash goldens.
"""

from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import engines.transmission_core as transmission_core  # noqa: E402
from tests.test_fomite_per_surface import (  # noqa: E402
    PATHOGEN,
    _agent,
    _core,
)

ANY_LOAD = {"hand_sequester_fill": "any_load"}
PER_EPOCH = {
    "hand_residual_mouthing": "per_epoch",
    "contamination_solver": "discrete",
}


# ── config resolution and warnings ───────────────────────────────────


def test_defaults_resolve_and_bad_arms_raise() -> None:
    core = _core({})
    assert core.hand_sequester_fill == "stool_only"
    assert core.hand_residual_mouthing == "pickup_only"
    assert core.hand_partition == {}
    assert core.hand_provenance == {}

    for tx in (
        {"hand_sequester_fill": "nope"},
        {"hand_residual_mouthing": "sometimes"},
    ):
        with pytest.raises(ValueError):
            _core(tx)


def test_any_load_warns_under_non_hygiene_cycle() -> None:
    # The fill only acts under the hygiene_cycle reservoir mode; under
    # the other modes it is inert and must say so.
    for mode in ("wash_reuptake", "spike_decay"):
        with pytest.warns(UserWarning, match="hand_sequester_fill"):
            _core({"hand_reservoir_mode": mode, **ANY_LOAD})

    # The shipped default is hygiene_cycle: the arm's domain, no warning.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _core(ANY_LOAD)


def test_per_epoch_warns_under_continuous_solver() -> None:
    with pytest.warns(UserWarning, match="hand_residual_mouthing"):
        _core({"hand_residual_mouthing": "per_epoch"})

    # The discrete declaration is the arm's domain: no warning.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _core(PER_EPOCH)


# ── capacity draw ────────────────────────────────────────────────────


def test_capacity_lands_in_the_shipped_band_and_is_memoized() -> None:
    core = _core({})
    low, high = transmission_core.HAND_PROTECTED_SEQUESTER_GEC_RANGE
    agent = _agent(1, "Lounge_A")
    first = core._hand_sequester_capacity(agent, PATHOGEN)
    assert low <= first <= high
    # Memoized on the agent: re-reading returns the same value and
    # consumes no further draws.
    assert core._hand_sequester_capacity(agent, PATHOGEN) == first
    # Draws differ across hosts (different positions in the stream).
    other = core._hand_sequester_capacity(_agent(2, "Lounge_A"), PATHOGEN)
    assert low <= other <= high


# ── external sequester fill ──────────────────────────────────────────


def test_external_sequester_migrates_within_capacity() -> None:
    core = _core(ANY_LOAD)
    agent = _agent(1, "Lounge_A")
    capacity = 1000.0
    agent.hand_sequester_capacity_by_pathogen[PATHOGEN] = capacity

    # protected 200 + pending 100 leaves room for 700; accessible 500
    # migrates fully.
    agent.hand_protected_pending_by_pathogen[PATHOGEN] = 100.0
    remainder = core._hand_external_sequester(agent, PATHOGEN, 200.0, 500.0)
    assert remainder == pytest.approx(0.0)
    pending = agent.hand_protected_pending_by_pathogen[PATHOGEN]
    assert pending == pytest.approx(600.0)

    # Booked as an internal flow, provenance witnessed.
    migrated = core.hand_partition[PATHOGEN]["internal_sequester_migrated"]
    assert migrated == pytest.approx(500.0)
    prov = core.hand_provenance[PATHOGEN][agent.agent_id]
    assert prov["fill_external"] is True


def test_external_sequester_respects_full_and_clamps() -> None:
    core = _core(ANY_LOAD)
    agent = _agent(1, "Lounge_A")
    agent.hand_sequester_capacity_by_pathogen[PATHOGEN] = 1000.0
    agent.hand_protected_pending_by_pathogen[PATHOGEN] = 300.0

    # Room is 1000 - 600 - 300 = 100, so only 100 of 500 migrates.
    remainder = core._hand_external_sequester(agent, PATHOGEN, 600.0, 500.0)
    assert remainder == pytest.approx(400.0)
    assert agent.hand_protected_pending_by_pathogen[PATHOGEN] == (
        pytest.approx(400.0)
    )

    # An over-filled compartment cannot reverse the migration.
    remainder = core._hand_external_sequester(
        agent, PATHOGEN, 5000.0, 500.0,
    )
    assert remainder == pytest.approx(500.0)


def test_external_sequester_inert_and_draw_free_off_arm() -> None:
    core = _core({})
    agent = _agent(1, "Lounge_A")
    before = core.rng.uniform(0.0, 1.0)  # consume one to anchor the stream
    _ = before
    state = core.rng.bit_generator.state
    remainder = core._hand_external_sequester(agent, PATHOGEN, 0.0, 500.0)
    assert remainder == pytest.approx(500.0)
    assert core.rng.bit_generator.state == state
    assert PATHOGEN not in agent.hand_sequester_capacity_by_pathogen
    assert core.hand_partition == {}


# ── residual mouth sweep ─────────────────────────────────────────────


def test_residual_sweep_mouths_susceptible_carriers_once() -> None:
    core = _core(PER_EPOCH)
    carrier = _agent(1, "Lounge_A")
    carrier.hand_load_by_pathogen[PATHOGEN] = 1e5
    infected = _agent(2, "Lounge_A", infected=True)
    infected.hand_load_by_pathogen[PATHOGEN] = 1e5
    occupants = {
        "Lounge_A": [carrier, infected],
        # Dedupe: the same carrier listed under a second zone is
        # swept once, not twice.
        "Diner_A": [carrier],
    }
    doses: dict[int, float] = {}
    pathway: dict[int, dict[str, float]] = {}

    core._hand_residual_mouth_sweep(
        0, occupants, doses, pathway, PATHOGEN,
    )

    dose = doses.get(carrier.agent_id, 0.0)
    assert dose > 0.0
    assert carrier.hand_load_by_pathogen[PATHOGEN] == pytest.approx(
        1e5 - dose,
    )
    assert pathway[carrier.agent_id]["fomite"] == pytest.approx(dose)
    # Infected hosts are outside the sweep; clean hands contribute zero.
    assert infected.agent_id not in doses
    assert core.hand_partition[PATHOGEN]["sink_mouth_residual"] == (
        pytest.approx(dose)
    )


def test_residual_sweep_inert_and_draw_free_off_arm() -> None:
    core = _core({})
    carrier = _agent(1, "Lounge_A")
    carrier.hand_load_by_pathogen[PATHOGEN] = 1e5
    state = core.rng.bit_generator.state
    doses: dict[int, float] = {}
    core._hand_residual_mouth_sweep(
        0, {"Lounge_A": [carrier]}, doses, None, PATHOGEN,
    )
    assert doses == {}
    assert carrier.hand_load_by_pathogen[PATHOGEN] == pytest.approx(1e5)
    assert core.rng.bit_generator.state == state
    assert core.hand_partition == {}


# ── partition bookkeeping ────────────────────────────────────────────


def test_partition_add_accumulates_and_skips_zero() -> None:
    core = _core({})
    core._hand_partition_add(PATHOGEN, "source_delivered", 0.0)
    assert core.hand_partition == {}
    core._hand_partition_add(PATHOGEN, "source_delivered", 5.0)
    core._hand_partition_add(PATHOGEN, "source_delivered", 7.0)
    core._hand_partition_add(PATHOGEN, "sink_wash_routine", 2.0)
    core._hand_partition_add("other", "source_delivered", 1.0)
    assert core.hand_partition[PATHOGEN] == {
        "source_delivered": 12.0,
        "sink_wash_routine": 2.0,
    }
