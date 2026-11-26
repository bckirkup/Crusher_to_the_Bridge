"""DP-UNION-02 ascertainment-conditioned design and generated campaign blocks."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DESIGN_PATH = _REPO_ROOT / "picard_framework/runs/covid_dp_union_02_design.json"
_DESIGN = json.loads(_DESIGN_PATH.read_text(encoding="utf-8"))
_BUILD_PATH = _REPO_ROOT / "campaigns/covid/dp_union_02/design/build.py"
_CAMPAIGN_PATH = _REPO_ROOT / "campaigns/covid/dp_union_02/campaign.json"


def _load_build():
    spec = importlib.util.spec_from_file_location("dp_union_02_build", _BUILD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_explicit_seed_values_drive_enumeration_and_validate_shape(tmp_path):
    from picard_framework.covid_boarding_screen import load_design

    assert len(_DESIGN["seed_values"]) == _DESIGN["seeds"] == 24
    assert len(set(_DESIGN["seed_values"])) == 24
    design = load_design(str(_DESIGN_PATH), repo_root=str(_REPO_ROOT))
    assert list(design.seed_values) == _DESIGN["seed_values"]

    malformed = dict(_DESIGN)
    malformed["seed_values"] = malformed["seed_values"][:-1]
    path = tmp_path / "malformed.json"
    path.write_text(json.dumps(malformed), encoding="utf-8")
    with pytest.raises(ValueError, match="exactly seeds"):
        load_design(str(path), repo_root=str(tmp_path))


def test_active_covid_gate_covers_the_shape_negative_support():
    from picard_framework.covid_theta_fit import load_covid_profile

    profile = load_covid_profile(str(_REPO_ROOT))
    first_day = min(
        int(row["day"]) for row in profile["emission_shape"]["daily"]
    )
    assert first_day == -5
    assert profile["presymptomatic_shedding_days"] == pytest.approx(5.0)


def test_index_geometry_reads_the_epoch_represented_seed_age():
    from types import SimpleNamespace

    from engines.sim_clock import HOURS, SimClock
    from picard_framework.covid_boarding_screen import _index_infection_age

    raw = {
        "config_overrides": {
            "initiation": {
                "explicit_seeds": [{"infection_age_days": 2.8}],
            },
        },
    }
    clock = SimClock(epoch_duration_hours=1.0, mode=HOURS)
    cell = SimpleNamespace(infection_age_days=6.8)
    assert _index_infection_age(raw, cell, clock) == pytest.approx(67 / 24)


def test_blocks_are_generated_from_the_frozen_conditioned_cohort():
    build = _load_build()
    spec = json.loads(_CAMPAIGN_PATH.read_text(encoding="utf-8"))
    assert spec["blocks"] == build.build_blocks(_DESIGN)
    assert sum(len(block["seeds"]) for block in spec["blocks"].values()) == (
        len(_DESIGN["thetas"]) * _DESIGN["seeds"]
    )
    assert len(spec["blocks"]) == 2 * len(_DESIGN["thetas"])
    for name, block in spec["blocks"].items():
        assert block["args"]["design"] == (
            "picard_framework/runs/covid_dp_union_02_design.json"
        )
        assert block["args"]["arm_id"] == "union_niid"
        assert set(block["seeds"]) <= set(_DESIGN["seed_values"])
        assert len(block["seeds"]) == (20 if name.endswith("_canary") else 4)


def test_probe_selection_is_event_class_only_and_complete():
    probe_path = _REPO_ROOT / "campaigns/covid/dp_union_02/ascertainment_probe.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    assert probe["selected_seeds"] == _DESIGN["seed_values"]
    assert len(probe["positive_seeds"]) >= 24
    assert "outcome" not in probe["selection_rule"].split("no outcome")[0]
    rows = {row["seed"]: row for row in probe["rows"]}
    assert all(
        rows[seed]["index_shedding_at_day0"] is True
        for seed in probe["selected_seeds"]
    )
    positive_positions = [
        index for index, row in enumerate(probe["rows"])
        if row["index_shedding_at_day0"] is True
    ]
    selected_positions = [
        index for index, row in enumerate(probe["rows"])
        if row["seed"] in set(probe["selected_seeds"])
    ]
    assert selected_positions == positive_positions[:24]
