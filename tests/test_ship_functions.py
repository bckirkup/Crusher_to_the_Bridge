"""Ship-function capacity: the availability read, pooled demand, and the
feedback writers (``docs/proposals/ship_function_capacity_spec.md`` §3–§6).

Every constant under test is a declared operational parameter, so these
tests pin arithmetic and wiring — pool sharing, thresholded writers,
referential load errors — and none of them asserts an epidemiological
outcome.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from engines.ship_functions import (
    DutyState,
    FunctionCapacityRunner,
    available_for_duty,
    merge_capacity_modifiers,
    on_watch,
    parse_ship_functions,
    validate_ship_function_refs,
)
from engines.ship_systems import build_ship_systems

# ── fixtures ────────────────────────────────────────────────────────────


class _Agent:
    """The roster attributes the availability read consumes."""

    def __init__(
        self,
        agent_id: int,
        role: str = "crew",
        agent_class: str = "crew_galley",
        work_zone: str = "Galley",
        current_activity: str = "Work",
    ) -> None:
        self.agent_id = agent_id
        self.role = role
        self.agent_class = agent_class
        self.work_zone = work_zone
        self.current_activity = current_activity
        self.schedule = ["Sleep"] * 24
        self.sustenance_deficit = 0.0


def _crew(n: int, cls: str = "crew_galley", **kwargs) -> list[_Agent]:
    return [_Agent(1000 + i, agent_class=cls, **kwargs) for i in range(n)]


class _State:
    def __init__(self) -> None:
        self.quarantined_ids: set[int] = set()
        self.isolated_ids: set[int] = set()
        self.info_suppression_closed_zones: set[str] = set()


class _Clock:
    hours_per_epoch = 1.0
    day_fraction_per_epoch = 1.0 / 24.0


class _Engine:
    def __init__(self) -> None:
        self.agent_behavior = {
            "dining_meal_weights": {
                "breakfast": {"buffet": 0.8, "mdr": 0.2},
                "lunch": {"buffet": 0.6, "mdr": 0.4},
            },
        }


def _block(functions, enabled: bool = True, **extra) -> dict:
    return {"enabled": enabled, "functions": functions, **extra}


def _fn(**kwargs) -> dict:
    base = {
        "function_id": "food_service",
        "serves": "passengers",
        "staffing": {"crew_galley": {"required_on_watch": 4}},
        "capacity_model": "staffing_fraction",
    }
    base.update(kwargs)
    return base


def _runner(functions, systems=None) -> FunctionCapacityRunner:
    enabled, specs = parse_ship_functions(_block(functions))
    assert enabled
    return FunctionCapacityRunner(specs, systems)


def _step(runner, agents, **kw):
    return runner.step(
        hour=kw.pop("hour", 8),
        agents=agents,
        symptomatic_ids=kw.pop("symptomatic_ids", set()),
        state=kw.pop("state", _State()),
        tracker=kw.pop("tracker", None),
        merged_mods=kw.pop("merged_mods", {}),
        engine=kw.pop("engine", _Engine()),
        tx_core=kw.pop("tx_core", SimpleNamespace(cleaning_coverage_scale=1.0)),
        clock=kw.pop("clock", _Clock()),
        zone_type_by_id=kw.pop(
            "zone_type_by_id",
            {"Galley": "Dining", "Mess_Hall": "Dining", "MainTheater": "Free"},
        ),
    )


# ── availability read ────────────────────────────────────────────────────


def test_on_watch_reads_recorded_token() -> None:
    agent = _Agent(1, current_activity="Work")
    assert on_watch(agent, 3)
    agent.current_activity = "Eat"
    assert not on_watch(agent, 3)


def test_on_watch_falls_back_to_schedule() -> None:
    agent = _Agent(1, current_activity="")
    agent.schedule = ["Work" if h == 7 else "Sleep" for h in range(24)]
    assert on_watch(agent, 7)
    assert not on_watch(agent, 8)


def test_available_for_duty_states() -> None:
    agent = _Agent(1)
    none: set[int] = set()
    assert available_for_duty(
        agent, 8, symptomatic_ids=set(),
        excluded_ids=none, quarantined_ids=none, isolated_ids=none,
    ) is DutyState.FIT
    assert available_for_duty(
        agent, 8, symptomatic_ids={1},
        excluded_ids=none, quarantined_ids=none, isolated_ids=none,
    ) is DutyState.IMPAIRED
    assert available_for_duty(
        agent, 8, symptomatic_ids=set(),
        excluded_ids=none, quarantined_ids={1}, isolated_ids=none,
    ) is DutyState.ABSENT
    agent.current_activity = "Sleep"
    assert available_for_duty(
        agent, 8, symptomatic_ids=set(),
        excluded_ids=none, quarantined_ids=none, isolated_ids=none,
    ) is DutyState.ABSENT


# ── declaration parsing ─────────────────────────────────────────────────


def test_parse_rejects_exclusive_staffing_modes() -> None:
    with pytest.raises(ValueError, match="exclusive"):
        parse_ship_functions(_block([_fn(
            staffing_by_duty_zone={"Galley": {"required_on_watch": 2}},
        )]))


def test_parse_rejects_bad_enums_and_duplicate_instances() -> None:
    with pytest.raises(ValueError, match="serves"):
        parse_ship_functions(_block([_fn(serves="aliens")]))
    with pytest.raises(ValueError, match="capacity_model"):
        parse_ship_functions(_block([_fn(capacity_model="vibes")]))
    with pytest.raises(ValueError, match="feedback.kind"):
        parse_ship_functions(_block([_fn(feedback={"kind": "wishing"})]))
    with pytest.raises(ValueError, match="scalar_name"):
        parse_ship_functions(_block([_fn(feedback={
            "kind": "route_scalar_scale", "scalar_name": "vibes_scalar",
        })]))
    with pytest.raises(ValueError, match="duplicate"):
        parse_ship_functions(_block([_fn(), _fn()]))


def test_parse_absent_and_disabled_are_identity() -> None:
    assert parse_ship_functions(None) == (False, [])
    enabled, specs = parse_ship_functions(_block([_fn()], enabled=False))
    assert not enabled
    assert len(specs) == 1


def test_validate_refs_is_a_load_error() -> None:
    _, specs = parse_ship_functions(_block([
        _fn(required_zone_ids=["NoSuchZone"]),
        _fn(serves="mission", required_systems=["warp_core"]),
    ]))
    with pytest.raises(ValueError, match="unknown zone"):
        validate_ship_function_refs(
            specs, class_ids={"crew_galley"}, zone_names={"Galley"},
            zone_types={"Dining"}, system_ids={"warp_core"},
        )
    with pytest.raises(ValueError, match="not in ship_systems"):
        validate_ship_function_refs(
            specs, class_ids={"crew_galley"},
            zone_names={"Galley", "NoSuchZone"}, zone_types={"Dining"},
            system_ids=set(),
        )
    with pytest.raises(ValueError, match="agent_classes"):
        validate_ship_function_refs(
            specs, class_ids=set(),
            zone_names={"Galley", "NoSuchZone"}, zone_types={"Dining"},
            system_ids={"warp_core"},
        )


# ── capacity math ────────────────────────────────────────────────────────


def test_full_pool_gives_full_capacity() -> None:
    runner = _runner([_fn()])
    record = _step(runner, _crew(4))
    fn = record["functions"]["food_service:passengers"]
    assert fn["capacity"] == pytest.approx(1.0)
    assert fn["binding"] is None


def test_shared_pool_degrades_instances_jointly() -> None:
    """Two instances on one class compete for the same watch-hours."""
    runner = _runner([
        _fn(),  # passengers: requires 4
        _fn(serves="crew"),  # crew: requires 4 — same crew_galley pool
    ])
    # 4 fit crew against summed demand 8 -> each instance gets share 0.5.
    record = _step(runner, _crew(4))
    for key in ("food_service:passengers", "food_service:crew"):
        assert record["functions"][key]["capacity"] == pytest.approx(0.5)
        assert record["functions"][key]["binding"] == "staffing:crew_galley"


def test_impaired_watch_delivers_at_effectiveness() -> None:
    runner = _runner([_fn()])
    agents = _crew(4)
    record = _step(runner, agents, symptomatic_ids={1000, 1001})
    fn = record["functions"]["food_service:passengers"]
    # 2 fit + 2 impaired x 0.7 = 3.4 of 4 required.
    assert fn["capacity"] == pytest.approx(0.85)
    assert fn["staffing"]["crew_galley"]["impaired"] == 2


def test_zone_and_system_factors_compose() -> None:
    systems = build_ship_systems([{
        "system_id": "galley_power",
        "health_start": 0.1,  # below failure_threshold: already failed
        "failure_threshold": 0.3,
        "effects": {"food_service": {"capacity_multiplier_at_failure": 0.5}},
    }])
    runner = _runner([_fn(
        required_zone_ids=["Galley", "Mess_Hall"],
        required_systems=["galley_power"],
    )], systems)
    state = _State()
    state.info_suppression_closed_zones.add("Galley")
    record = _step(runner, _crew(4), state=state)
    fn = record["functions"]["food_service:passengers"]
    # zone_share 0.5 x system_multiplier 0.5 on full staffing.
    assert fn["capacity"] == pytest.approx(0.25)
    assert fn["zone_share"] == pytest.approx(0.5)
    assert fn["system_multiplier"] == pytest.approx(0.5)


def test_zone_type_needs_one_open_zone() -> None:
    runner = _runner([_fn(required_zone_types=["Dining"])])
    record = _step(runner, _crew(4), merged_mods={"close_zones": ["Galley"]})
    assert record["functions"]["food_service:passengers"]["zone_share"] == pytest.approx(1.0)
    record = _step(
        runner, _crew(4),
        merged_mods={"close_zones": ["Galley", "Mess_Hall"]},
    )
    assert record["functions"]["food_service:passengers"]["zone_share"] == pytest.approx(0.0)


def test_bottleneck_min_hard_gate_on_watch_minimum() -> None:
    runner = _runner([_fn(
        staffing={"crew_galley": {"required_on_watch": 4, "minimum_on_watch": 2}},
        capacity_model="bottleneck_min",
    )])
    # 1 crew of demand 4 -> fair-share allocation 1 < minimum 2: does not run.
    record = _step(runner, _crew(1))
    assert record["functions"]["food_service:passengers"]["capacity"] == pytest.approx(0.0)
    record = _step(runner, _crew(2))
    assert record["functions"]["food_service:passengers"]["capacity"] > 0.0


def test_capacity_schedule_scales_demand() -> None:
    runner = _runner([_fn(capacity_schedule={"8": 2.0, "9": 1.0})])
    record = _step(runner, _crew(4), hour=8)
    assert record["functions"]["food_service:passengers"]["capacity"] == pytest.approx(0.5)
    record = _step(runner, _crew(4), hour=9)
    assert record["functions"]["food_service:passengers"]["capacity"] == pytest.approx(1.0)


# ── feedback writers ─────────────────────────────────────────────────────


def test_cleaning_scale_tracks_capacity_continuously() -> None:
    runner = _runner([_fn(
        function_id="housekeeping", serves="both",
        staffing={"crew_galley": {"required_on_watch": 4}},
        feedback={"kind": "cleaning_coverage_scale"},
    )])
    tx = SimpleNamespace(cleaning_coverage_scale=1.0)
    _step(runner, _crew(2), tx_core=tx)
    assert tx.cleaning_coverage_scale == pytest.approx(0.5)
    _step(runner, _crew(4), tx_core=tx)
    assert tx.cleaning_coverage_scale == pytest.approx(1.0)


def test_dining_weights_swap_is_thresholded_and_restores() -> None:
    runner = _runner([_fn(
        staffing={"crew_galley": {"required_on_watch": 4}},
        feedback={
            "kind": "dining_weights",
            "threshold": 0.5,
            "sustained_hours": 2.0,
            "degraded_weights": {"buffet": 0.0},
        },
    )])
    engine = _Engine()
    _step(runner, _crew(1), engine=engine)  # capacity 0.25, count 1
    assert engine.agent_behavior["dining_meal_weights"]["lunch"]["buffet"] == pytest.approx(0.6)
    _step(runner, _crew(1), engine=engine)  # count 2 -> swap
    assert engine.agent_behavior["dining_meal_weights"]["lunch"]["buffet"] == pytest.approx(0.0)
    _step(runner, _crew(4), engine=engine)  # recovered -> baseline restored
    assert engine.agent_behavior["dining_meal_weights"]["lunch"]["buffet"] == pytest.approx(0.6)


def test_zone_modifier_contrib_is_emitted_for_next_epoch() -> None:
    runner = _runner([_fn(
        staffing={"crew_galley": {"required_on_watch": 4}},
        feedback={
            "kind": "zone_modifiers", "threshold": 0.5,
            "sustained_hours": 1.0, "zone_close_on_loss": ["MainTheater"],
        },
    )])
    _step(runner, _crew(1))
    assert runner.pending_modifiers == {"close_zones": ["MainTheater"]}
    _step(runner, _crew(4))
    assert runner.pending_modifiers == {}


def test_route_scalar_is_recomputed_not_compounded() -> None:
    runner = _runner([_fn(
        staffing={"crew_galley": {"required_on_watch": 4}},
        feedback={
            "kind": "route_scalar_scale",
            "scalar_name": "direct_contact_scalar", "floor": 0.0,
        },
    )])
    _step(runner, _crew(2))
    assert runner.pending_modifiers["direct_contact_scalar"] == pytest.approx(0.5)
    _step(runner, _crew(2))
    assert runner.pending_modifiers["direct_contact_scalar"] == pytest.approx(0.5)
    _step(runner, _crew(4))
    assert "direct_contact_scalar" not in runner.pending_modifiers


def test_feedback_disabled_writes_nothing() -> None:
    runner = _runner([_fn(
        staffing={"crew_galley": {"required_on_watch": 4}},
        feedback={"kind": "route_scalar_scale", "enabled": False,
                  "scalar_name": "fomite_scalar"},
    )])
    _step(runner, _crew(1))
    assert runner.pending_modifiers == {}


def test_crew_sustenance_lands_on_crew_only() -> None:
    runner = _runner([_fn(
        serves="crew",
        staffing={"crew_galley": {"required_on_watch": 4}},
        feedback={"kind": "readout_only", "crew_sustenance": True},
    )])
    agents = _crew(2) + [_Agent(7, role="passenger", agent_class="passenger_general")]
    # capacity 0.5 -> deficit (1.0 - 0.5) * rate 1.0 on each crew member.
    _step(runner, agents)
    assert all(a.sustenance_deficit == pytest.approx(0.5) for a in agents[:2])
    assert agents[2].sustenance_deficit == pytest.approx(0.0)


def test_merge_capacity_modifiers_follows_protocol_rules() -> None:
    merged = merge_capacity_modifiers(
        {"close_zones": ["A"], "direct_contact_scalar": 0.9},
        {"close_zones": ["B"], "direct_contact_scalar": 0.5},
        lambda key, old, new: (
            sorted(set(list(old if isinstance(old, list) else [old]) +
                       (new if isinstance(new, list) else [new])))
            if isinstance(new, list) else min(old, new)
        ),
    )
    assert merged["close_zones"] == ["A", "B"]
    assert merged["direct_contact_scalar"] == pytest.approx(0.5)


# ── ship systems ─────────────────────────────────────────────────────────


def test_systems_degrade_and_repair_in_priority_order() -> None:
    systems = build_ship_systems([
        {"system_id": "b", "degradation": {"rate_per_day": 0.0},
         "repair": {"labor_class": "eng", "rate_per_person_hour": 0.1},
         "repair_priority": 1},
        {"system_id": "a", "health_start": 0.5,
         "degradation": {"rate_per_day": 0.0},
         "repair": {"labor_class": "eng", "rate_per_person_hour": 0.1},
         "repair_priority": 0},
    ])
    assert systems is not None
    # 4 residual person-hours: repairs a first (0.5 -> 0.9), no hours left for b.
    systems.step(0.0, {"eng": 4.0})
    assert systems.health["a"] == pytest.approx(0.9)
    assert systems.health["b"] == pytest.approx(1.0)


def test_system_failure_multiplies_dependent_function() -> None:
    systems = build_ship_systems([{
        "system_id": "plant", "health_start": 0.2, "failure_threshold": 0.5,
        "effects": {"food_service": {"capacity_multiplier_at_failure": 0.0}},
    }])
    assert systems is not None
    assert systems.capacity_multiplier("food_service") == pytest.approx(0.0)
    assert systems.capacity_multiplier("navigation") == pytest.approx(1.0)


def test_ship_systems_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        build_ship_systems([{"system_id": "x"}, {"system_id": "x"}])


def test_dexterity_impairment_scales_repair_labor() -> None:
    """PPE dexterity loss cuts the residual hours a pool can spend on repair."""
    systems = build_ship_systems([
        {"system_id": "plant", "health_start": 0.5,
         "degradation": {"rate_per_day": 0.0},
         "repair": {"labor_class": "eng", "rate_per_person_hour": 0.1},
         "repair_priority": 0},
    ])
    runner = _runner([_fn(
        staffing={"crew_galley": {"required_on_watch": 2}},
    )], systems)
    # 4 eng on watch, demand 0 for eng -> 4 residual person-hours before
    # dexterity; two workers at 50% impairment deliver only 3.
    eng = _crew(4, cls="eng")
    eng[0].ppe_dexterity_impairment = 0.5
    eng[1].ppe_dexterity_impairment = 0.5
    _step(runner, eng)
    assert systems.health["plant"] == pytest.approx(0.8)  # 0.5 + 3 h x 0.1
    systems_2 = build_ship_systems([
        {"system_id": "plant", "health_start": 0.5,
         "degradation": {"rate_per_day": 0.0},
         "repair": {"labor_class": "eng", "rate_per_person_hour": 0.1},
         "repair_priority": 0},
    ])
    runner_2 = _runner([_fn(
        staffing={"crew_galley": {"required_on_watch": 2}},
    )], systems_2)
    _step(runner_2, _crew(4, cls="eng"))  # no field: full 4 hours
    assert systems_2.health["plant"] == pytest.approx(0.9)  # 0.5 + 4 h x 0.1


# ── wired into the epoch ─────────────────────────────────────────────────


def _picard_spec(tmp_path, ship_functions=None):
    """A 24-epoch destroyer run, optionally carrying a ship_functions override."""
    import json

    spec = {
        "schema_version": "1.0.0",
        "catalog": {
            "platform_id": "destroyer_baseline",
            "pathogen_bundle_id": "active_profiles",
        },
        "run": {"random_seed": 7, "num_epochs": 24, "write_ground_truth": False},
        "legacy_yaml": "crusher_labs/config.yaml",
        "actors": [], "incentives": {},
    }
    if ship_functions is not None:
        spec["config_overrides"] = {"voyage": {"ship_functions": ship_functions}}
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec))
    return str(path)


def test_epoch_record_carries_function_capacity(tmp_path) -> None:
    from picard_framework import PicardRunSpec, ShipSimulation

    block = _block([_fn(
        serves="crew",
        staffing={"crew_galley": {"required_on_watch": 2}},
        required_zone_ids=["Galley"],
    )])
    spec = PicardRunSpec.from_picard_json(".", _picard_spec(tmp_path, block))
    sim = ShipSimulation(spec, display=False)
    sim.run()
    record = sim.state.simulation_history[-1]
    assert "function_capacity" in record
    fn = record["function_capacity"]["functions"]["food_service:crew"]
    assert 0.0 <= fn["capacity"] <= 1.0
    assert "staffing" in fn
    assert "crew_galley" in fn["staffing"]


def test_absent_block_is_bit_identical(tmp_path) -> None:
    """Disabled/absent arms reproduce the baseline history field-for-field."""
    from picard_framework import PicardRunSpec, ShipSimulation

    runs = []
    for block in (None, _block([_fn()], enabled=False)):
        spec = PicardRunSpec.from_picard_json(
            ".", _picard_spec(tmp_path, block),
        )
        sim = ShipSimulation(spec, display=False)
        sim.run()
        hist = [
            {k: v for k, v in rec.items() if k != "function_capacity"}
            for rec in sim.state.simulation_history
        ]
        runs.append(hist)
        assert all(
            "function_capacity" not in rec for rec in hist
        )
    assert runs[0] == runs[1]
