"""Guards for carrier hand redeposition and ordered fomite phases.

NORO-HAND-CASCADE-01a adds two default-off arms: non-shedder carriers may
redeposit whole-copy hand loads, and fomite phases can run in causal order
(pickups before redeposition, food before end-of-epoch hygiene). These tests
pin the gates and conservation law; they are not campaign readouts.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from engines.infection_dynamics_bridge import IllnessStatus, KorkinAgent
from engines.sim_clock import HOURS, SimClock
from engines.strain_dose_ledger import (
    StrainDoseLedger,
    attribution,
    single_strain_mix,
)
from engines.transmission_core import ContactTracingMatrix, TransmissionCore

PATHOGEN = "test_pathogen"
ZONE = "MainDining_L"


def _profile(**overrides: object) -> dict:
    profile: dict[str, object] = {
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "symptom_onset_day": 0.0,
        "dose_response": {"model": "exponential", "k": 0.01},
        "hand_inactivation_rate_per_hour": 0.61,
        "hand_hygiene_rate_per_hour": 0.0,
    }
    profile.update(overrides)
    return profile


def _agent(
    agent_id: int = 1,
    *,
    infected: bool = False,
    hand_load: float = 0.0,
) -> KorkinAgent:
    agent = KorkinAgent(
        agent_id=agent_id,
        role="passenger",
        immune=False,
        home_zone=ZONE,
        dining_zone=ZONE,
        work_zone=ZONE,
        free_zone=ZONE,
        schedule=["Free"] * 24,
    )
    agent.current_location = ZONE
    agent.hand_load_by_pathogen[PATHOGEN] = hand_load
    if infected:
        agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=24)
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    return agent


def _core(
    *,
    tx: dict | None = None,
    profile: dict | None = None,
    seed: int = 7,
) -> TransmissionCore:
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 50.0},
        pathogen_profiles={PATHOGEN: profile or _profile()},
        zone_types={ZONE: "Dining"},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        cfg={"transmission": tx} if tx is not None else None,
    )
    core.initialize_zones([ZONE])
    return core


def _carriers_core(**kwargs: object) -> TransmissionCore:
    return _core(
        tx={
            "hand_redeposit_mode": "carriers",
            "intra_epoch_causal_order": "ordered",
        },
        **kwargs,  # type: ignore[arg-type]
    )


def test_redeposit_and_order_arms_default_to_legacy() -> None:
    core = _core()
    assert core.hand_redeposit_mode == "shedders_only"
    assert core.intra_epoch_order == "legacy"
    carrier = _agent(hand_load=10.0)
    assert core._get_hand_depositors([carrier], PATHOGEN) == []


def test_carrier_gate_requires_whole_copy_hand_load() -> None:
    core = _carriers_core()
    profile = core.pathogen_profiles[PATHOGEN]
    subcopy = _agent(agent_id=1, hand_load=0.5)
    carrier = _agent(agent_id=2, hand_load=2.0)
    assert core._get_hand_depositors([subcopy], PATHOGEN, profile) == []
    assert core._get_hand_depositors([carrier], PATHOGEN, profile) == [
        (carrier, 0.0),
    ]


def test_carrier_redeposit_conserves_hand_to_surface_mass() -> None:
    core = _carriers_core()
    profile = core.pathogen_profiles[PATHOGEN]
    carrier = _agent(hand_load=1.0e6)
    core.surface_pools[ZONE] = 0.0
    core.surface_pools_by_pathogen[PATHOGEN][ZONE] = 0.0
    hand_before = carrier.hand_load_by_pathogen[PATHOGEN]

    core._fomite_surface_deposits(ZONE, [carrier], 0, PATHOGEN, profile)

    hand_after = carrier.hand_load_by_pathogen[PATHOGEN]
    pool_after = core.surface_pools_by_pathogen[PATHOGEN][ZONE]
    hand_delta = hand_before - hand_after
    assert hand_delta > 0.0
    assert pool_after == pytest.approx(hand_delta, rel=1e-9)
    assert hand_after >= 0.0
    assert pool_after >= 0.0


def test_carrier_hand_replenish_decays_without_shedder_practice() -> None:
    core = _carriers_core()
    profile = core.pathogen_profiles[PATHOGEN]
    carrier = _agent(hand_load=100.0)

    core._replenish_hand(carrier, PATHOGEN, profile, ZONE)

    expected = 100.0 * math.exp(-0.61 * core.clock.hours_per_epoch)
    assert carrier.hand_load_by_pathogen[PATHOGEN] == pytest.approx(
        expected, rel=1e-9,
    )


def test_ordered_fomite_defers_hygiene_until_food_pathway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile(food_contamination={"enabled": True})
    core = _core(
        tx={"intra_epoch_causal_order": "ordered"},
        profile=profile,
    )
    agent = _agent()
    hygiene_calls: list[int] = []
    monkeypatch.setattr(
        core,
        "_fomite_hygiene",
        lambda occupants, pathogen_id, profile_arg: hygiene_calls.append(
            len(occupants),
        ),
    )

    core._pathway_fomite(
        0,
        {ZONE: [agent]},
        {},
        ContactTracingMatrix(epoch=0),
        [],
        pathogen_id=PATHOGEN,
        profile=profile,
    )

    assert hygiene_calls == []
    assert PATHOGEN in core._ordered_hygiene_occupants

    core._pathway_food_contamination(
        0,
        {ZONE: [agent]},
        {},
        ContactTracingMatrix(epoch=0),
        [],
        pathogen_id=PATHOGEN,
        profile=profile,
    )

    assert hygiene_calls == [1]
    assert PATHOGEN not in core._ordered_hygiene_occupants


def test_record_hand_strain_keeps_dominant_source_lineage() -> None:
    carriers = _carriers_core()
    legacy = _core()
    target = _agent()
    attr = attribution(
        StrainDoseLedger(),
        single_strain_mix("strainA", source_agent_id=7),
    )

    legacy._record_hand_strain(target, PATHOGEN, attr)
    assert PATHOGEN not in target.hand_strain_by_pathogen

    carriers._record_hand_strain(target, PATHOGEN, attr)
    assert target.hand_strain_by_pathogen[PATHOGEN] == "strainA"


def test_per_partner_contact_records_donor_hand_lineage() -> None:
    core = _carriers_core()
    donor = _agent(agent_id=2, hand_load=100.0)
    donor.hand_strain_by_pathogen[PATHOGEN] = "strainB"
    target = _agent(agent_id=1)

    _dose, moved = core._per_partner_contact_dose(
        target, [(donor, 1.0)], False, PATHOGEN, 0,
    )

    assert moved
    assert target.hand_strain_by_pathogen[PATHOGEN] == "strainB"
    assert target.hand_load_by_pathogen[PATHOGEN] >= 0.0


def test_carrier_hand_replenish_zeros_below_residue_floor() -> None:
    core = _carriers_core()
    profile = core.pathogen_profiles[PATHOGEN]
    carrier = _agent(hand_load=1e-13)
    carrier.hand_strain_by_pathogen[PATHOGEN] = "strainC"

    core._replenish_hand(carrier, PATHOGEN, profile, ZONE)

    assert carrier.hand_load_by_pathogen[PATHOGEN] == 0.0
    assert PATHOGEN not in carrier.hand_strain_by_pathogen


def test_ordered_fomite_without_food_runs_hygiene_inline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = _core(tx={"intra_epoch_causal_order": "ordered"})
    agent = _agent()
    hygiene_calls: list[int] = []
    monkeypatch.setattr(
        core,
        "_fomite_hygiene",
        lambda occupants, pathogen_id, profile_arg: hygiene_calls.append(
            len(occupants),
        ),
    )

    core._pathway_fomite(
        0,
        {ZONE: [agent]},
        {},
        ContactTracingMatrix(epoch=0),
        [],
        pathogen_id=PATHOGEN,
        profile=core.pathogen_profiles[PATHOGEN],
    )

    assert hygiene_calls == [1]
    assert PATHOGEN not in core._ordered_hygiene_occupants
