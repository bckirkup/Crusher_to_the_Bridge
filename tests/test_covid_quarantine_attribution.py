"""covid_quarantine_attribution_v1: the arm axis, override wiring, ledger.

No hull runs here (the smoke driver owns those). The design file loads and
enumerates, overrides are applied to a real fit run-spec and read back, and
the payload window arithmetic runs against stub simulations with a real
SimClock so day-boundary behaviour is graded, not guessed.
"""

from __future__ import annotations

import copy
import importlib.util
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from engines.sim_clock import SimClock
from picard_framework.covid_boarding_screen import (
    BoardingScreenDesign,
    QuarantineAttributionLedger,
    ScreenCell,
    apply_arm_overrides,
    cell_payload,
    enumerate_cells,
    load_design,
    merge_screen,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import (
    PATHOGEN_ID,
    HullObservables,
    build_fit_run_spec,
    load_covid_profile,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DESIGN_PATH = (
    REPO_ROOT
    / "picard_framework/runs/covid_quarantine_attribution_v1_design.json"
)
ARM_IDS = (
    "A0_declared",
    "A1_crew_confined",
    "A2_pool_transport_off",
    "A3_near_field_off",
    "A4_crew_confined_and_pool_off",
    "A5_all_shared_air_off",
)


def _load_entrypoint():
    path = REPO_ROOT / "deploy" / "aws" / "covid_boarding_screen_entrypoint.py"
    spec = importlib.util.spec_from_file_location(
        "covid_boarding_screen_entrypoint", path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def design() -> BoardingScreenDesign:
    return load_design(str(DESIGN_PATH))


# ── design + enumeration ──────────────────────────────────────────────────

def test_design_loads_the_declared_240_cells(design):
    cells = enumerate_cells(design)
    assert len(cells) == 240
    assert [c.index for c in cells] == list(range(240))
    assert len({c.key for c in cells}) == 240
    assert all(c.key.endswith(f"_arm{c.arm_id}.json") for c in cells)
    assert design.arm_ids == ARM_IDS
    assert design.baseline_arm_id == "A0_declared"


def test_cell_order_keeps_an_arms_seeds_contiguous(design):
    cells = enumerate_cells(design)
    first = cells[0:20]
    assert all(c.arm_id == "A0_declared" for c in first)
    assert all(c.theta == pytest.approx(1e5) for c in first)
    assert [c.seed for c in first] == list(range(20200205, 20200225))
    assert all(c.arm_id == "A1_crew_confined" for c in cells[20:40])
    assert all(c.arm_id == "A0_declared" for c in cells[120:140])
    assert all(c.theta == pytest.approx(1e9) for c in cells[120:140])


def test_key_stability_for_arm_free_cells():
    cell = ScreenCell(
        index=0, scenario_id="diamond_princess_2020", theta=1e5,
        infection_age_days=3.3, imports=1, seed=20200205, arm_id=None,
    )
    assert cell.key == (
        "screen_diamond_princess_2020_theta1e5p00_age3p3d"
        "_imports1_seed20200205.json"
    )


def test_v9_design_still_enumerates_arm_free(design):
    v9 = load_design(
        str(REPO_ROOT / "picard_framework/runs/covid_theta_screen_v9_design.json"),
    )
    cells = enumerate_cells(v9)
    assert len(cells) == 600
    assert all(c.arm_id is None for c in cells)
    assert all("_arm" not in c.key for c in cells)


def test_arm_free_design_enumerates_with_none():
    d = BoardingScreenDesign(
        design_id="x", scenario_id="diamond_princess_2020",
        thetas=(1e5,), infection_age_days=(0.0,), imports=(1,),
        sanitary_visit_mode="none", seed_base=1, seeds=2,
        takeoff_recorded_onsets=10,
    )
    assert all(c.arm_id is None for c in enumerate_cells(d))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda arms: [{**a, "overrides": {"not_a_key": 1}} if i else a
                      for i, a in enumerate(arms)],
        lambda arms: [arms[0], {**arms[1], "arm_id": arms[0]["arm_id"]},
                      *arms[2:]],
        lambda arms: [{**arms[0], "arm_id": ""}, *arms[1:]],
        lambda arms: [{**arms[0], "overrides": {"near_field_air_mode": "off"}},
                      *arms[1:]],
    ],
    ids=["unknown_key", "duplicate_id", "empty_id", "nonempty_baseline"],
)
def test_arm_validation_raises(design, mutate):
    arms = tuple(mutate(list(design.arms)))
    with pytest.raises(ValueError):
        replace(design, arms=arms)


# ── overrides reaching the run spec ───────────────────────────────────────

def _raw_spec():
    return build_fit_run_spec("diamond_princess_2020", 1e5, 20200205)


def test_empty_overrides_leave_the_spec_deep_equal():
    raw = _raw_spec()
    before = copy.deepcopy(raw)
    apply_arm_overrides(raw, {}, profile=load_covid_profile())
    assert raw == before


def test_scheduled_protocol_swap_preserves_the_window():
    raw = _raw_spec()
    apply_arm_overrides(
        raw, {"scheduled_protocol_id": "SOP-017-ALLHANDS"},
        profile=load_covid_profile(),
    )
    protocols = raw["config_overrides"]["scenario_schedule"]["protocols"]
    entry = next(
        p for p in protocols if p["protocol_id"] == "SOP-017-ALLHANDS"
    )
    assert (entry["start_day"], entry["end_day"]) == (16, 30)
    assert all(p["protocol_id"] != "SOP-017" for p in protocols)


def test_protocol_swap_raises_without_the_scheduled_entry():
    raw = _raw_spec()
    raw["config_overrides"]["scenario_schedule"]["protocols"] = []
    profile = load_covid_profile()
    with pytest.raises(ValueError):
        apply_arm_overrides(
            raw, {"scheduled_protocol_id": "SOP-017-ALLHANDS"},
            profile=profile,
        )


def test_near_field_mode_writes_the_transmission_block():
    raw = _raw_spec()
    apply_arm_overrides(
        raw, {"near_field_air_mode": "off"}, profile=load_covid_profile(),
    )
    assert (
        raw["config_overrides"]["transmission"]["near_field_air"]["mode"]
        == "off"
    )


def test_near_field_mode_rejects_unknown_modes():
    raw = _raw_spec()
    profile = load_covid_profile()
    with pytest.raises(ValueError):
        apply_arm_overrides(
            raw, {"near_field_air_mode": "one_box"},
            profile=profile,
        )


def test_route_multipliers_merge_onto_the_shipped_mapping():
    raw = _raw_spec()
    profile = load_covid_profile()
    apply_arm_overrides(
        raw,
        {"profile_route_efficiency_multipliers": {
            "droplet": 0.0, "hvac_airborne": 0.0}},
        profile=profile,
    )
    merged = raw["pathogen_overrides"][PATHOGEN_ID][
        "route_efficiency_multipliers"]
    shipped = profile["route_efficiency_multipliers"]
    assert merged["droplet"] == pytest.approx(0.0)
    assert merged["hvac_airborne"] == pytest.approx(0.0)
    for key, value in shipped.items():
        if key not in ("droplet", "hvac_airborne"):
            assert merged[key] == pytest.approx(float(value))
    # The theta override keys already written are undisturbed.
    assert "dose_response" in raw["pathogen_overrides"][PATHOGEN_ID]


@pytest.mark.parametrize(
    "arm_values",
    [{"not_a_route": 0.0}, {"droplet": -0.5}],
    ids=["unknown_route", "negative_value"],
)
def test_route_multipliers_reject_bad_input(arm_values):
    raw = _raw_spec()
    profile = load_covid_profile()
    with pytest.raises(ValueError):
        apply_arm_overrides(
            raw,
            {"profile_route_efficiency_multipliers": arm_values},
            profile=profile,
        )


def test_unknown_override_key_raises():
    raw = _raw_spec()
    profile = load_covid_profile()
    with pytest.raises(ValueError):
        apply_arm_overrides(raw, {"bogus": 1}, profile=profile)


def test_pool_transport_threads_through_prepare(design):
    cells = enumerate_cells(design)
    cell_a2 = next(c for c in cells if c.arm_id == "A2_pool_transport_off")
    cell_a0 = next(c for c in cells if c.arm_id == "A0_declared")
    raw_a2 = prepare_cell_run_spec(design, cell_a2)
    raw_a0 = prepare_cell_run_spec(design, cell_a0)
    assert raw_a2["config_overrides"]["hvac"]["pathogen_pool_transport"] == "none"
    assert "pathogen_pool_transport" not in raw_a0["config_overrides"].get(
        "hvac", {},
    )


# ── ledger + payload window arithmetic on stubs ───────────────────────────

_EPOCHS_PER_DAY = 24  # 1 h epochs


class _Agent:
    def __init__(self, agent_id, role, home_zone, infections=None):
        self.agent_id = agent_id
        self.role = role
        self.home_zone = home_zone
        self.infections = infections or {}


class _Engine:
    def __init__(self, agents, seeded=(), quarantined=()):
        self.agents = agents
        self.explicit_seed_agent_ids = list(seeded)
        self.quarantined_ids = set(quarantined)
        self.vsp_reported_case_fraction_max = 0.0


class _Syndromic:
    def onset_observation_curve(self, pathogen_id):
        return {}

    def campaign_specimen_log(self, pathogen_id):
        return []


class _Sim:
    """Just enough of ShipSimulation for the ledger and payload read-out."""

    def __init__(self, agents, *, quarantined=(), seeded=()):
        self.clock = SimClock(epoch_duration_hours=1.0, mode="hours")
        self.engine = _Engine(agents, seeded=seeded, quarantined=quarantined)
        self.zone_types = {}
        self.state = SimpleNamespace(quarantined_ids=set(quarantined))
        self.repo_root = str(REPO_ROOT)
        self.cfg = {}
        self.modalities = {"syndromic": _Syndromic()}
        self.tx_core = SimpleNamespace(sanitary_telemetry={})
        self.pathogen_profiles = {PATHOGEN_ID: {}}


def _ev(epoch, zone, pathway, target, particles=None):
    return SimpleNamespace(
        epoch=epoch, zone=zone, pathway=pathway, target_agent_id=target,
        acquired_particles_by_route=particles or {},
    )


def _work(epoch, tx_events=(), active_mods=None, quarantined=()):
    return SimpleNamespace(
        epoch=epoch, tx_events=list(tx_events), active_mods=active_mods,
        state=SimpleNamespace(quarantined_ids=set(quarantined)),
    )


def _confine_order(protocol_id="SOP-017", exempt=()):
    return {
        "protocol_id": protocol_id,
        "modifiers": {
            "confine_all_to_quarters": True,
            "confinement_enforced": True,
            "exempt_classes": list(exempt),
        },
    }


def _attribution_for(sim, ledger, raw):
    design = BoardingScreenDesign(
        design_id="x", scenario_id="diamond_princess_2020",
        thetas=(1e5,), infection_age_days=(3.3,), imports=(1,),
        sanitary_visit_mode="none", seed_base=1, seeds=1,
        takeoff_recorded_onsets=10,
        arms=({"arm_id": "A0", "overrides": {}},),
    )
    cell = ScreenCell(
        index=0, scenario_id="diamond_princess_2020", theta=1e5,
        infection_age_days=3.3, imports=1, seed=1, arm_id="A0",
    )
    payload = cell_payload(design, cell, sim, ledger, raw)
    return {k: v for k, v in payload.items() if "quarantine" in k or "arm" in k}


@pytest.mark.parametrize(
    "infection_epoch,bucket",
    [
        (15 * 24 + 23, "before"),   # last epoch of day 15
        (16 * 24, "during"),        # first epoch of day 16
        (30 * 24 + 23, "during"),   # last epoch of day 30
        (31 * 24, "after"),         # first epoch of day 31
    ],
    ids=["day15_last", "day16_first", "day30_last", "day31_first"],
)
def test_window_day_boundaries(infection_epoch, bucket):
    agents = [
        _Agent(1, "passenger", "PC_1",
               {PATHOGEN_ID: {"infection_epoch": infection_epoch}}),
    ]
    sim = _Sim(agents)
    ledger = QuarantineAttributionLedger()
    ledger.observe(sim, _work(epoch=0, active_mods=[_confine_order()]))
    raw = _raw_spec()
    out = _attribution_for(sim, ledger, raw)
    for name in ("before", "during", "after"):
        assert out[f"infections_{name}_quarantine"] == (
            1 if name == bucket else 0
        )


def test_window_counts_sum_to_total_and_dedupe():
    agents = [
        _Agent(1, "passenger", "PC_1",
               {PATHOGEN_ID: {"infection_epoch": 20 * 24}}),
        _Agent(2, "crew", "CC_1",
               {PATHOGEN_ID: {"infection_epoch": 25 * 24}}),
        _Agent(3, "passenger", "PC_3",
               {PATHOGEN_ID: {"infection_epoch": 40 * 24}}),
    ]
    sim = _Sim(agents)
    ledger = QuarantineAttributionLedger()
    # A repeated target records only its first infection; a seeded target is
    # skipped outright.
    sim.engine.quarantined_ids = {1}
    ledger.observe(sim, _work(epoch=20 * 24, tx_events=[
        _ev(20 * 24, "PC_1", "droplet", 1),
        _ev(20 * 24, "PC_2", "fomite", 1),
        _ev(20 * 24, "PC_9", "droplet", 9),   # unknown target: recorded
    ], active_mods=[_confine_order()]))
    sim.engine.quarantined_ids = {1, 2}
    ledger.observe(sim, _work(epoch=25 * 24, tx_events=[
        _ev(25 * 24, "Crew_Mess_Main", "direct_contact", 2),
    ]))
    assert len(ledger.events) == 3
    assert ledger.events[0]["confined"] is True

    sim2 = _Sim(agents, seeded=(3,))
    ledger2 = QuarantineAttributionLedger()
    ledger2.observe(sim2, _work(epoch=40 * 24, tx_events=[
        _ev(40 * 24, "PC_3", "droplet", 3),
    ]))
    assert ledger2.events == []


def test_during_splits_and_confined_count():
    agents = [
        _Agent(1, "passenger", "PC_Home",
               {PATHOGEN_ID: {"infection_epoch": 20 * 24}}),
        _Agent(2, "crew", "CC_1",
               {PATHOGEN_ID: {"infection_epoch": 21 * 24}}),
        _Agent(3, "crew", "CC_2",
               {PATHOGEN_ID: {"infection_epoch": 22 * 24}}),
        _Agent(4, "passenger", "PC_Other",
               {PATHOGEN_ID: {"infection_epoch": 23 * 24}}),
    ]
    sim = _Sim(agents, quarantined=(1, 4))
    sim.zone_types = {
        "PC_Home": "Cabin_Corridor",
        "PC_Corridor": "Cabin_Corridor",
        "Crew_Mess_Main": "Dining",
        "Main_Galley_Aft": "Dining",
        "Void": "Service",
    }
    ledger = QuarantineAttributionLedger()
    ledger.observe(sim, _work(epoch=20 * 24, tx_events=[
        _ev(20 * 24, "PC_Home", "droplet", 1),            # cabin, confined
        _ev(21 * 24, "Crew_Mess_Main", "direct_contact", 2),  # crew_mess
        _ev(22 * 24, "Main_Galley_Aft", "food", 3),       # galley
        _ev(23 * 24, "PC_Corridor", "hvac_airborne", 4),  # corridor
        _ev(24 * 24, "Void", "teleport", 1),              # dedupe: already
    ], active_mods=[_confine_order()], quarantined={1, 4}))
    raw = _raw_spec()
    out = _attribution_for(sim, ledger, raw)
    assert out["during_quarantine_by_role"] == {"passenger": 2, "crew": 2}
    zones = out["during_quarantine_by_zone_class"]
    assert zones["cabin"] == 1
    assert zones["corridor"] == 1
    assert zones["crew_mess"] == 1
    assert zones["galley"] == 1
    assert zones["other"] == 0
    routes = out["during_quarantine_by_route"]
    assert routes["droplet"] == 1
    assert routes["direct_contact"] == 1
    assert routes["hvac_airborne"] == 1
    assert routes["food"] == 1
    assert out["confined_passenger_infections_during_quarantine"] == 2
    witness = out["quarantine_witness"]
    assert witness["activated"] is True
    assert witness["activation_epoch"] == 20 * 24
    assert witness["confined_at_activation"] == 2
    assert witness["window_days"] == [16, 30]
    assert witness["protocol_id"] == "SOP-017"
    assert witness["invalid_reason"] is None


def test_never_activated_is_an_invalid_marker_not_zeros():
    agents = [
        _Agent(1, "passenger", "PC_1",
               {PATHOGEN_ID: {"infection_epoch": 20 * 24}}),
    ]
    sim = _Sim(agents)
    ledger = QuarantineAttributionLedger()
    out = _attribution_for(sim, ledger, _raw_spec())
    assert out["quarantine_witness"]["activated"] is False
    assert out["quarantine_witness"]["invalid_reason"] == (
        "quarantine_never_activated")
    assert out["infections_during_quarantine"] is None
    assert out["during_quarantine_by_role"] is None
    assert out["during_quarantine_by_zone_class"] is None
    assert out["during_quarantine_by_route"] is None
    assert out["confined_passenger_infections_during_quarantine"] is None
    # before/after are still computed off the record channel.
    assert out["infections_before_quarantine"] == 0
    assert out["infections_after_quarantine"] == 0


def test_ledger_pathway_uses_dominant_dose_then_stripped_key():
    sim = _Sim([_Agent(1, "passenger", "PC_1")])
    ledger = QuarantineAttributionLedger()
    ledger.observe(sim, _work(epoch=1, tx_events=[
        _ev(1, "Z", "droplet:sars_cov2_resp", 1,
            particles={"droplet": 0.5, "hvac_airborne": 0.9}),
        _ev(1, "Z", "fomite:sars_cov2_resp", 2),
        _ev(1, "Z", "", 3),
    ]))
    assert ledger.events[0]["pathway"] == "hvac_airborne"
    assert ledger.events[1]["pathway"] == "fomite"
    assert ledger.events[2]["pathway"] == "unknown"


def test_witness_reports_intersection_and_protocol_ids():
    sim = _Sim([], quarantined=(1, 2, 3))
    ledger = QuarantineAttributionLedger()
    ledger.observe(sim, _work(epoch=16 * 24, active_mods=[
        _confine_order("SOP-017", exempt=["a", "b"]),
        _confine_order("SOP-017-ALLHANDS", exempt=["b"]),
    ], quarantined={1, 2, 3}))
    assert ledger.exempt_classes == ["b"]
    assert ledger.protocol_ids == ["SOP-017", "SOP-017-ALLHANDS"]
    out = _attribution_for(sim, ledger, _raw_spec())
    assert out["quarantine_witness"]["exempt_classes"] == ["b"]
    assert out["quarantine_witness"]["protocol_ids"] == [
        "SOP-017", "SOP-017-ALLHANDS"]


def test_witness_reads_confinement_in_force_during_transmission():
    # The record step's new admissions only reach the engine next epoch, so a
    # target admitted this epoch is still unconfined in the event record.
    agents = [_Agent(7, "passenger", "PC_7")]
    sim = _Sim(agents, quarantined=())
    ledger = QuarantineAttributionLedger()
    sim.engine.quarantined_ids = set()
    ledger.observe(sim, _work(
        epoch=16 * 24, tx_events=[_ev(16 * 24, "PC_7", "droplet", 7)],
        active_mods=[_confine_order()],
        quarantined={7},  # admitted this epoch's record step
    ))
    assert ledger.events[0]["confined"] is False
    assert ledger.confined_at_activation == 1  # read from state, not engine


# ── merge ─────────────────────────────────────────────────────────────────

def _stub_payload(cell: ScreenCell, *, visits: float = 100.0) -> dict:
    total = 100 + (cell.seed % 7)
    obs = HullObservables(
        scenario_id=cell.scenario_id, theta=cell.theta, seed=cell.seed,
        recorded_onsets=total,
        onsets_before_split_day=30,
        onsets_on_or_after_split_day=total - 30,
        passenger_onsets_before=1, passenger_onsets_after=1,
        crew_onsets_before=1, crew_onsets_after=1,
        campaign_specimens=2000, campaign_positives=300,
        campaign_asymptomatic_positives=150,
    )
    payload = {
        "design_id": "x",
        "cell": cell.as_dict(),
        "observables": obs.as_dict(),
        "onset_curve": {},
        "first_onset_day": 20,
        "sanitary_activity": {"visits": visits},
        "infections_total": total,
        "aboard_total": 3711,
        "attack_rate": total / 3711,
        "vsp_reported_case_fraction_max": 0.04,
    }
    if cell.arm_id is not None:
        payload["arm_id"] = cell.arm_id
    return payload


def test_merge_groups_by_arm_with_the_first_arm_baseline(design):
    cells = enumerate_cells(design)
    payloads = {c.key: _stub_payload(c) for c in cells}
    surface = merge_screen(design, payloads)["surface"]
    assert len(surface) == 12  # 2 theta x 6 arms
    by_arm = {(e["theta"], e["arm_id"]): e for e in surface}
    entry = by_arm[(1e5, "A0_declared")]
    assert entry["is_baseline"] is True
    for arm_id in ARM_IDS[1:]:
        arm_entry = by_arm[(1e5, arm_id)]
        assert arm_entry["is_baseline"] is False
        assert arm_entry["delta_vs_baseline"]["n"] == 20


def test_merge_of_a_non_arm_design_keeps_its_shape(design):
    v9 = load_design(
        str(REPO_ROOT / "picard_framework/runs/covid_theta_screen_v9_design.json"),
    )
    cells = enumerate_cells(v9)
    payloads = {c.key: _stub_payload(c) for c in cells}
    surface = merge_screen(v9, payloads)["surface"]
    assert len(surface) > 1
    assert all(e["arm_id"] is None for e in surface)
    assert all("delta_vs_baseline" in e for e in surface)


def test_entrypoint_children_cover_all_240_cells_once(design):
    entry = _load_entrypoint()
    cells = enumerate_cells(design)
    seen = []
    for index in range(240):
        seen.extend(c.index for c in entry.child_cells(cells, index, 1))
    assert sorted(seen) == list(range(240))
