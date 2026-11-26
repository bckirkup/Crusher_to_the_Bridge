"""DP-UNION-01: the declared matrix, the union arm, and the joint contract."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CAMPAIGN = _REPO_ROOT / "campaigns/covid/dp_union_01"
_RUNS = _REPO_ROOT / "picard_framework/runs"
_DESIGN = json.loads(
    (_RUNS / "covid_dp_union_01_design.json").read_text(encoding="utf-8"),
)
_CONTRACT = _DESIGN["joint_contract"]
_ORDER = "SOP-017-DEDQUARTER"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dp_union_01_{name}", _CAMPAIGN / f"{name}.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _arm(design: dict, arm_id: str) -> dict:
    return {a["arm_id"]: a["overrides"] for a in design["arms"]}[arm_id]


def test_blocks_are_generated_from_the_lattice_and_count_the_design():
    """campaign.json is build.py's output; union-arm cells equal the design."""
    spec = json.loads((_CAMPAIGN / "campaign.json").read_text(encoding="utf-8"))
    build = _load("design/build")
    assert spec["blocks"] == build.build_blocks(_DESIGN)
    assert sum(len(b["seeds"]) for b in spec["blocks"].values()) == _DESIGN["cells"]
    assert _DESIGN["cells"] == len(_DESIGN["thetas"]) * _DESIGN["seeds"]
    thetas = {b["args"]["theta"] for b in spec["blocks"].values()}
    assert thetas == set(_DESIGN["thetas"])
    assert {b["args"]["arm_id"] for b in spec["blocks"].values()} == {"union_niid"}


def test_pilot_is_a_prefix_of_the_canary_blocks_on_lattice_decades():
    """Pilot cells are the first seeds of declared blocks, not extra cells."""
    spec = json.loads((_CAMPAIGN / "campaign.json").read_text(encoding="utf-8"))
    pilot = _DESIGN["theta_grid"]["pilot"]
    assert set(pilot["thetas"]) <= set(_DESIGN["thetas"])
    for theta in pilot["thetas"]:
        (block,) = [
            b for name, b in spec["blocks"].items()
            if name.endswith("_canary") and b["args"]["theta"] == theta
        ]
        assert block["seeds"][:len(pilot["seeds"])] == pilot["seeds"]


def test_scored_grid_is_a_subset_of_the_lattice():
    grid = _DESIGN["theta_grid"]
    scored = grid["scored_thetas"] or []
    assert set(scored) <= set(_DESIGN["thetas"])
    assert (grid["canary_theta"] is None) == (not scored)
    if scored:
        assert grid["canary_theta"] in scored


def test_pilot_reads_the_t3_side_from_pilot_seeds_only():
    readout = _load("readout")
    contract = _DESIGN["joint_contract"]
    grid = {"pilot": {"thetas": [1e7, 1e8], "seeds": [20200205, 20200206, 20200207]}}

    def row(theta, p31):
        return {
            "theta": theta, "dead": False, "saturated": False,
            "reported_only": {"p31_per_seed": p31},
        }

    rows = [
        row(1e7, {"20200205": 0, "20200206": 100, "20200207": 700, "20200208": 9000}),
        row(1e8, {"20200205": 634, "20200206": 800}),
        row(3.16e8, {"20200205": 900}),
    ]
    pilot = readout._pilot(rows, grid, contract)
    assert [p["theta"] for p in pilot] == [1e7, 1e8]
    assert [p["median_p31"] for p in pilot] == [100, 717.0]
    assert [p["at_or_above_t3"] for p in pilot] == [False, True]
    assert [p["n"] for p in pilot] == [3, 2]
    assert all(
        "does not establish whether a separate pilot ran" in p["provenance"]
        for p in pilot
    )


def test_union_arm_is_replay_niid_plus_exactly_the_declared_deltas():
    fit = json.loads(
        (_RUNS / "covid_dp_theta_fit_01_design.json").read_text(encoding="utf-8"),
    )
    parent = _arm(fit, "replay_niid")
    union = _arm(_DESIGN, "union_niid")
    changed = {
        key for key in set(parent) | set(union)
        if parent.get(key) != union.get(key)
    }
    assert changed == {
        "scheduled_protocol_id", "crew_duty_exclusion", "observation_overrides",
    }
    assert union["scheduled_protocol_id"] == _ORDER
    assert union["crew_duty_exclusion"] == {"enabled": True}
    assert union["observation_overrides"] == {
        "retest_negative_sweeps": True, "campaign_waves": ["crew_wave"],
    }
    # theta is the only swept quantity; the non-arm scalars are FIT-01's.
    for key in ("scenario_id", "voyage_mode", "infection_age_days", "imports",
                "sanitary_visit_mode", "seed_base", "seeds"):
        assert _DESIGN[key] == fit[key]


def test_quarter_order_differs_from_the_dedicated_order_only_in_the_gate():
    catalog = json.loads(
        (_REPO_ROOT / "data/config/protocols_covid_dp_dedicated.json")
        .read_text(encoding="utf-8"),
    )
    by_id = {p["protocol_id"]: p for p in catalog["protocols"]}
    parent, quarter = by_id["SOP-017-DEDICATED"], by_id[_ORDER]
    text_keys = {"protocol_id", "name", "description", "modifiers"}
    assert {k: v for k, v in parent.items() if k not in text_keys} == {
        k: v for k, v in quarter.items() if k not in text_keys
    }
    p_mod, q_mod = dict(parent["modifiers"]), dict(quarter["modifiers"])
    assert p_mod.pop("exempt_work_zones")
    assert q_mod.pop("exempt_fraction") == {"crew_general": 0.25}
    assert p_mod == q_mod


@pytest.mark.parametrize(
    "day_max, reachable, confirmed, capture",
    [(29, 3, 2, 2 / 3), (10, 1, 1, 1.0), (0, 0, 0, None)],
)
def test_capture_block_conditions_on_the_reachable_day(
    day_max, reachable, confirmed, capture,
):
    hosts = {
        "1": {"infection_day": 5, "confirmed_day": 20},
        "2": {"infection_day": 29, "confirmed_day": 34},
        "3": {"infection_day": 20, "confirmed_day": None},
        "4": {"infection_day": 30, "confirmed_day": 34},
        "5": {"infection_day": None, "confirmed_day": None},
    }
    block = _load("cell").capture_block(hosts, day_max)
    assert block["infections_funnel"] == 4
    assert block["confirmed_funnel"] == 3
    assert block["infections_reachable"] == reachable
    assert block["confirmed_reachable"] == confirmed
    assert block["conditioned_capture"] == capture


@pytest.mark.parametrize("mass, day", [(3, 4), (4, 9), (5, None)])
def test_timing_block_finds_the_first_day_cumulative_mass_is_reached(mass, day):
    by_day = {"9": 1, "2": 1, "4": 2}
    block = _load("cell").timing_block(by_day, mass)
    assert block["ignition_day"] == day
    assert block["infections_by_day"] == {"2": 1, "4": 2, "9": 1}


def _cell(
    seed: int, *, p31: int = 634, wave_pos: int = 57, during: int = 250,
    onsets: int = 200, before: int = 35, reach: int = 800, conf: int = 700,
    infections: int = 850, wave_specimens: int = 831, founders: int = 12,
    ignition: int | None = 8,
) -> dict:
    # Seeds straddle the target so the side rule reads "compatible".
    if p31:
        p31 += 10 if seed % 2 else -10
    by_day = {"16": {"specimens": 3000, "positives": p31}}
    if wave_specimens:
        by_day["34"] = {"specimens": wave_specimens, "positives": wave_pos}
    waves = {"crew_wave": wave_specimens} if wave_specimens else {}

    def _block(through: int) -> dict:
        late = through >= 34 and bool(wave_specimens)
        return {
            "positives_through_day": p31 + (wave_pos if late else 0),
            "specimens_through_day": 3000 + (wave_specimens if late else 0),
            "last_specimen_day": 34 if wave_specimens else 16,
            "specimens_by_wave": waves,
            "by_day": by_day,
        }

    return {
        "design_id": "covid-dp-union-01",
        "infections_total": infections,
        "aboard_total": 3711,
        "attack_rate": infections / 3711,
        "lab_confirmed_total": conf,
        "infections_before_quarantine": 400,
        "infections_during_window": during,
        "index_onset_day": 3.0,
        "index_shedding_at_day0": True,
        "dose_response": {"susceptibility_scale": 1e9 * 58.18 / 0.18},
        "quarantine_witness": {"activated": True, "activation_epoch": 391},
        "platform_fidelity": {
            "resolved_platform_id": "diamond_princess",
            "protocols_path": "data/config/protocols_covid_dp_dedicated.json",
            "fired_protocol_ids": [_ORDER],
            "close_zones_fired_flag": False,
        },
        "seed_ring": {"aboard_window_acquisitions": founders},
        "crew_window": {
            "exempt_fraction": {"crew_general": 0.25},
            "exempt_work_zones": None,
            "exempt_fraction_drawn": {_ORDER: {"crew_general": 261}},
            "at_activation": {"total_crew": 1045, "realized_exempt_share": 0.25},
        },
        "crew_duty_exclusion": {"resolved": {"enabled": True}, "excluded_hosts": 4},
        "specimen_channel": {
            "retest_negatives_on_sweep": True, "campaign_waves": ["crew_wave"],
        },
        "observables": {
            "recorded_onsets": onsets,
            "onsets_before_split_day": before,
            "campaign_positives": p31 + (wave_pos if wave_specimens else 0),
        },
        "dp_union": {
            "seed": seed, "theta": 1e9, "arm_id": "union_niid",
            "timing": {"ignition_day": ignition},
            "t3": _block(31),
            "onboard_table": _block(34),
            "capture": {
                "infections_funnel": infections, "confirmed_funnel": conf,
                "infections_reachable": reach, "confirmed_reachable": conf,
                "conditioned_capture": conf / reach if reach else None,
            },
        },
    }


def _row(n: int = 24, **kwargs) -> dict:
    by_seed = {seed: _cell(seed, **kwargs) for seed in range(n)}
    return _load("readout")._theta_row(1e9, by_seed, _CONTRACT, 24)


def test_all_legs_pass_on_a_record_like_cell():
    row = _row()
    assert row["failing_legs"] == []
    assert row["consistent"] is True
    assert row["audit_deviations"] == {}
    assert row["dead"] is False and row["saturated"] is False
    assert row["median_not_representative"] is False


@pytest.mark.parametrize(
    "kwargs, failing",
    [
        ({"p31": 900}, ["t3", "onboard_table"]),
        ({"p31": 600}, ["t3", "onboard_table"]),
        ({"wave_pos": 80}, ["onboard_table"]),
        ({"during": 149}, ["during"]),
        ({"during": 351}, ["during"]),
        ({"before": 56}, ["timing_before_share"]),
        ({"before": 14}, ["timing_before_share"]),
        ({"ignition": 10}, ["timing_ignition"]),
        ({"ignition": None}, ["timing_ignition"]),
        ({"infections": 711}, ["attack"]),
        ({"infections": 961}, ["attack"]),
        ({"conf": 630}, ["capture"]),
    ],
)
def test_each_leg_fails_alone_when_its_statistic_leaves_its_band(kwargs, failing):
    row = _row(**kwargs)
    assert row["failing_legs"] == failing
    assert row["consistent"] is False


@pytest.mark.parametrize(
    "kwargs",
    [{"during": 150}, {"during": 350}, {"before": 54}, {"conf": 640},
     {"ignition": 9}, {"infections": 712}, {"infections": 960}],
)
def test_band_edges_are_inclusive(kwargs):
    assert _row(**kwargs)["failing_legs"] == []


def test_legs_are_scored_on_the_founder_class_not_on_all_seeds():
    """Off-class seeds with wild values must not move any scored leg."""
    readout = _load("readout")
    by_seed = {seed: _cell(seed) for seed in range(12)}
    by_seed.update({
        seed: _cell(seed, founders=2, ignition=None, during=0, infections=3,
                    p31=1, wave_pos=0, onsets=0, before=0, reach=3, conf=0)
        for seed in range(12, 24)
    })
    row = readout._theta_row(1e9, by_seed, _CONTRACT, 24)
    assert row["class_n"] == {"founder": 12, "takeoff": 12, "all": 24}
    assert row["failing_legs"] == []
    assert row["consistent"] is True
    on_all = row["reported_only"]["legs_on_all_seeds"]
    assert on_all["timing_ignition"]["pass"] is False
    assert on_all["timing_ignition"]["never_ignited"] == 12


def test_side_rule_scales_eighteen_of_twenty_four_to_the_class():
    readout = _load("readout")
    assert readout._side([700] * 9 + [600] * 3, 634, 0.75)["side"] == "above"
    assert readout._side([700] * 8 + [600] * 4, 634, 0.75)["side"] == "compatible"
    assert readout._side([600] * 18 + [700] * 6, 634, 0.75)["side"] == "below"


def test_partial_row_is_provisional_and_issues_no_verdict():
    row = _row(n=20)
    assert row["provisional"] is True
    assert row["consistent"] is None
    assert row["failing_legs"] == []


def test_no_leg_passes_without_founder_class_mass():
    row = _row(founders=9)
    assert row["class_n"]["founder"] == 0
    assert row["passing_legs"] == []
    assert all(
        leg["verdict"] == "insufficient class mass"
        for leg in row["legs"].values()
    )


@pytest.mark.parametrize(
    "infections, saturated", [(3524, False), (3525, True)],
)
def test_saturation_edge_excludes_the_index_exactly_once(infections, saturated):
    assert _row(infections=infections)["saturated"] is saturated


def test_dead_cell_and_machinery_gap_are_surfaced():
    row = _row(p31=0, wave_pos=0)
    assert row["dead"] is True
    assert row["consistent"] is False
    assert row["reported_only"]["machinery_gap_seeds"] == list(range(24))


@pytest.mark.parametrize(
    "mutate, deviation",
    [
        (lambda c: c.update(index_shedding_at_day0=False),
         "index_shedding_at_day0"),
        (lambda c: c["platform_fidelity"].update(
            fired_protocol_ids=["SOP-017-DEDICATED"]), "quarter_order_fired"),
        (lambda c: c["crew_window"].update(
            exempt_fraction_drawn={_ORDER: {"crew_general": 260}}),
         "exempt_fraction_drawn"),
        (lambda c: c["crew_duty_exclusion"]["resolved"].update(enabled=False),
         "crew_duty_exclusion"),
        (lambda c: c["specimen_channel"].update(campaign_waves=[]),
         "campaign_waves_armed"),
        (lambda c: c["specimen_channel"].update(retest_negatives_on_sweep=False),
         "retest_sweeps_armed"),
        (lambda c: c["dp_union"]["onboard_table"].update(last_specimen_day=35),
         "no_specimen_after_wave_day"),
    ],
)
def test_audit_names_the_arming_key_that_did_not_resolve(mutate, deviation):
    readout = _load("readout")
    cell = _cell(0)
    mutate(cell)
    assert readout._audit_cell(cell, 1e9, _CONTRACT) == [deviation]


def test_audit_requires_the_wave_to_have_run():
    readout = _load("readout")
    found = readout._audit_cell(_cell(0, wave_specimens=0), 1e9, _CONTRACT)
    assert found == ["wave_ran"]


def test_joint_reports_the_leg_that_fails_at_every_theta():
    readout = _load("readout")
    rows = [_row(before=80), _row(before=80, during=500)]
    joint = readout._joint(rows)
    assert joint["consistent_thetas"] == []
    assert joint["legs_failing_at_every_theta"] == ["timing_before_share"]
    assert joint["split_verdict"] is False


def test_joint_treats_an_all_audit_dirty_grid_as_unreadable():
    readout = _load("readout")
    row = _row()
    row["audit_deviations"] = {"0": ["platform"]}
    row["audit_clean"] = False
    row["consistent"] = False
    joint = readout._joint([row])
    assert joint["legs_failing_at_every_theta"] == []
    assert joint["split_verdict"] is False
    assert joint["audit_deviation_thetas"] == [1e9]


def test_joint_reports_a_split_verdict_and_its_disjoint_leg_pair():
    readout = _load("readout")
    low, high = _row(during=500), _row(infections=1500)
    high["theta"] = 1e10
    joint = readout._joint([low, high])
    assert joint["consistent_thetas"] == []
    assert joint["legs_failing_at_every_theta"] == []
    assert joint["split_verdict"] is True
    assert joint["disjoint_leg_pairs"] == [["attack", "during"]]
    assert joint["leg_pass_thetas"]["during"] == [1e10]
    assert joint["leg_pass_thetas"]["attack"] == [1e9]
