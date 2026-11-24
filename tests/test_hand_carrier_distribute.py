"""Behavioral guards for the CARRIER-DISTRIBUTE (D3'') arm.

The arm (``docs/proposals/hand_carrier_distribute_spec.md``) lets a
non-shedder host whose accessible hand load passes the shipped
``pickup_gate_open`` gate join the direct-contact donor pool
(``hand_donor_mode='carriers'``), alongside the already-shipped deposit
arm (``hand_redeposit_mode='carriers'``). Both selectors keep
bit-identical defaults; the arm adds zero new constants and no new RNG
draws. Sensitivity-first per ci-test-design: pool membership, donation
mechanics, provenance witnesses and config refusals -- no hash goldens.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.infection_dynamics_bridge import (  # noqa: E402
    IllnessStatus,
    KorkinAgent,
)
from engines.sim_clock import HOURS, SimClock  # noqa: E402
from engines.transmission_core import (  # noqa: E402
    ContactTracingMatrix,
    TransmissionCore,
)
from tools.noro_diag import per_host_dose_challenge as pdc  # noqa: E402

PATHOGEN = "test_pathogen"
ZONE = "Public_Lounge"

DONOR_CARRIERS = {"hand_donor_mode": "carriers"}
REDEPOSIT_CARRIERS = {"hand_redeposit_mode": "carriers"}
BOTH_CARRIERS = {**DONOR_CARRIERS, **REDEPOSIT_CARRIERS}


def _profile() -> dict:
    return {
        "shedding_curve_log10": [11.0] * 12,
        "asymptomatic_shedding_log10": [11.0] * 12,
        "symptom_onset_day": 0.0,
        "dose_response": {"model": "exponential", "k": 0.01},
        "hand_inactivation_rate_per_hour": 0.61,
        "hand_hygiene_rate_per_hour": 0.0,
    }


def _agent(
    agent_id: int,
    *,
    infected: bool = False,
    hand_load: float | None = None,
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
    if infected:
        agent.infect_with_pathogen(PATHOGEN, 1.0, 0, time_infected=24)
        agent.infections[PATHOGEN]["illness"] = IllnessStatus.SYMPTOMATIC
    if hand_load is not None:
        agent.hand_load_by_pathogen[PATHOGEN] = hand_load
    return agent


def _core(tx: dict, seed: int = 7) -> TransmissionCore:
    merged = {"contact_mode": "per_partner_contact", **tx}
    core = TransmissionCore(
        rng=np.random.default_rng(seed),
        zone_volumes={ZONE: 50.0},
        pathogen_profiles={PATHOGEN: _profile()},
        zone_types={ZONE: "Free"},
        clock=SimClock(epoch_duration_hours=1.0, mode=HOURS),
        cfg={"transmission": merged},
    )
    core.initialize_zones([ZONE])
    return core


def _shedders_of(
    core: TransmissionCore, occupants: list[KorkinAgent],
) -> list[tuple[KorkinAgent, float]]:
    return core._get_shedders(
        occupants, PATHOGEN, core.pathogen_profiles[PATHOGEN],
    )


# ── config resolution ────────────────────────────────────────────────


def test_defaults_resolve_and_bad_arms_raise() -> None:
    core = _core({})
    assert core.hand_donor_mode == "shedders_only"
    assert core.hand_redeposit_mode == "shedders_only"
    assert core.hand_carrier_activity == {}

    for tx in (
        {"hand_donor_mode": "nope"},
        {"hand_redeposit_mode": "nope"},
    ):
        with pytest.raises(ValueError):
            _core(tx)


# ── donor pool membership ────────────────────────────────────────────


def test_donor_pool_default_returns_the_shedder_list_itself() -> None:
    core = _core({})
    shedder = _agent(1, infected=True, hand_load=1.0e6)
    carrier = _agent(2, hand_load=1.0e4)
    occupants = [shedder, carrier]
    shedders = _shedders_of(core, occupants)
    donors = core._get_hand_donors(occupants, shedders, PATHOGEN)
    assert donors is shedders
    assert [agent.agent_id for agent, _ in donors] == [1]


def test_donor_pool_widens_only_to_gated_loaded_carriers() -> None:
    core = _core(DONOR_CARRIERS)
    shedder = _agent(1, infected=True, hand_load=1.0e6)
    carrier = _agent(2, hand_load=1.0e4)
    empty = _agent(3, hand_load=0.0)
    below_gate = _agent(4, hand_load=0.5)
    occupants = [shedder, carrier, empty, below_gate]
    shedders = _shedders_of(core, occupants)
    donors = core._get_hand_donors(occupants, shedders, PATHOGEN)
    assert [agent.agent_id for agent, _ in donors] == [1, 2]
    # Carriers enter the pool with a zero shedding value -- the donation
    # debit reads their hand load, not this marker.
    assert dict((a.agent_id, sv) for a, sv in donors)[2] == pytest.approx(
        0.0, abs=0.0,
    )


def test_donor_and_redeposit_selectors_are_independent() -> None:
    donor_core = _core(DONOR_CARRIERS)
    redeposit_core = _core(REDEPOSIT_CARRIERS)
    shedder = _agent(1, infected=True, hand_load=1.0e6)
    carrier = _agent(2, hand_load=1.0e4)
    occupants = [shedder, carrier]
    shedders = _shedders_of(donor_core, occupants)

    # The donor arm leaves the deposit pool shedder-only...
    assert [
        a.agent_id for a, _ in donor_core._get_hand_depositors(
            occupants, PATHOGEN, donor_core.pathogen_profiles[PATHOGEN],
        )
    ] == [1]
    # ...and the deposit arm leaves the donor pool shedder-only.
    assert [
        a.agent_id
        for a, _ in redeposit_core._get_hand_donors(
            occupants, shedders, PATHOGEN,
        )
    ] == [1]


def test_carrier_only_donor_pool_keeps_the_unit_alive() -> None:
    """The early exit is on donors, so a carrier alone sustains contact."""
    core = _core(DONOR_CARRIERS)
    carrier = _agent(1, hand_load=1.0e6)
    target = _agent(2)
    occupants = [carrier, target]
    shedders = _shedders_of(core, occupants)
    assert shedders == []
    donors = core._get_hand_donors(occupants, shedders, PATHOGEN)
    assert [a.agent_id for a, _ in donors] == [1]

    core._contact_count_draw = lambda ctx, target_agent: 1  # deterministic
    doses: dict[int, float] = {}
    matrix = ContactTracingMatrix(epoch=0)
    core._direct_contact_unit(
        0, ZONE, occupants, False, doses, matrix, None,
        PATHOGEN, core.pathogen_profiles[PATHOGEN], None,
    )
    acquired = target.hand_load_by_pathogen.get(PATHOGEN, 0.0)
    assert acquired > 0.0
    assert carrier.hand_load_by_pathogen[PATHOGEN] < 1.0e6
    prov = core.hand_provenance[PATHOGEN]
    assert prov[carrier.agent_id]["donated_carrier"] is True
    assert prov[target.agent_id]["acquired"] is True
    activity = core.hand_carrier_activity[PATHOGEN]
    assert activity["donate_calls"] == 1
    assert activity["donate_gec"] > 0.0
    assert activity["donate_hosts"] == {carrier.agent_id}


# ── donation mechanics and witnesses ─────────────────────────────────


def test_carrier_donor_moves_hand_load_and_is_witnessed() -> None:
    core = _core(DONOR_CARRIERS)
    carrier = _agent(1, hand_load=1.0e6)
    target = _agent(2)
    dose, moved = core._per_partner_contact_dose(
        target, [(carrier, 0.0)], False, PATHOGEN, 0,
    )
    amount = sum(m for _, m in moved)
    assert amount > 0.0
    assert carrier.hand_load_by_pathogen[PATHOGEN] == pytest.approx(
        1.0e6 - amount, rel=1e-12,
    )
    assert dose >= 0.0
    prov = core.hand_provenance[PATHOGEN]
    assert prov[carrier.agent_id]["donated_carrier"] is True
    assert prov[target.agent_id]["acquired"] is True
    partition = core.hand_partition[PATHOGEN]
    assert partition["internal_host_transfer"] == pytest.approx(amount)


def test_shedder_donor_is_never_marked_as_a_carrier_donor() -> None:
    core = _core(DONOR_CARRIERS)
    shedder = _agent(1, infected=True, hand_load=1.0e6)
    target = _agent(2)
    _dose, moved = core._per_partner_contact_dose(
        target, [(shedder, 1.0e11)], False, PATHOGEN, 0,
    )
    assert moved
    prov = core.hand_provenance.get(PATHOGEN, {}).get(shedder.agent_id, {})
    assert "donated_carrier" not in prov
    activity = core.hand_carrier_activity.get(PATHOGEN, {})
    assert (activity or {}).get("donate_calls", 0) == 0


def test_carrier_depositor_is_witnessed_on_surfaces() -> None:
    core = _core(BOTH_CARRIERS)
    carrier = _agent(1, hand_load=1.0e6)
    deposits = core._shedder_surface_deposits(
        ZONE, [(carrier, 0.0)], 0, PATHOGEN,
        core.pathogen_profiles[PATHOGEN],
    )
    assert len(deposits) == 1
    assert deposits[0][1] > 0.0
    prov = core.hand_provenance[PATHOGEN]
    assert prov[carrier.agent_id]["deposited_carrier"] is True
    activity = core.hand_carrier_activity[PATHOGEN]
    assert activity["deposit_calls"] == 1
    assert activity["deposit_gec"] == pytest.approx(deposits[0][1])
    partition = core.hand_partition[PATHOGEN]
    assert partition["sink_redeposited"] == pytest.approx(deposits[0][1])


def test_shedder_depositor_is_never_marked_as_a_carrier() -> None:
    core = _core(BOTH_CARRIERS)
    shedder = _agent(1, infected=True, hand_load=1.0e6)
    sv = shedder.get_pathogen_shedding(
        PATHOGEN, core.pathogen_profiles[PATHOGEN],
    )
    assert sv > 0.0
    deposits = core._shedder_surface_deposits(
        ZONE, [(shedder, sv)], 0, PATHOGEN,
        core.pathogen_profiles[PATHOGEN],
    )
    assert deposits
    prov = core.hand_provenance.get(PATHOGEN, {}).get(shedder.agent_id, {})
    assert "deposited_carrier" not in prov


# ── worker plumbing ──────────────────────────────────────────────────


def test_build_spec_writes_the_two_selector_keys() -> None:
    spec = pdc.build_spec(
        seed=9000, platform="classic_cruise_1900",
        bundle="active_profiles", epochs=20, num_agents=1910,
        pathogen_id="norwalk_gi", alpha=None, beta=1.0,
        sweep=pdc.TransmissionSweepKnobs(
            hand_redeposit_mode="carriers",
            hand_donor_mode="carriers",
        ),
    )
    assert spec["config_overrides"]["transmission"] == {
        "hand_redeposit_mode": "carriers",
        "hand_donor_mode": "carriers",
    }


def test_parse_args_accepts_and_rejects_the_selectors() -> None:
    args = pdc.parse_args(
        [
            "--out", "x",
            "--hand-redeposit-mode", "carriers",
            "--hand-donor-mode", "carriers",
        ],
    )
    assert args.hand_redeposit_mode == "carriers"
    assert args.hand_donor_mode == "carriers"
    for flag in ("--hand-redeposit-mode", "--hand-donor-mode"):
        with pytest.raises(SystemExit):
            pdc.parse_args(["--out", "x", flag, "everyone"])


def test_manifest_mode_forbids_the_selector_flags() -> None:
    for flag in ("--hand-redeposit-mode", "--hand-donor-mode"):
        with pytest.raises(SystemExit):
            pdc.parse_args(
                [
                    "--out", "x",
                    "--manifest", "m.json", "--tier", "t",
                    flag, "carriers",
                ],
            )
