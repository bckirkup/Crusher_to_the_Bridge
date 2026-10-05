"""CREW-WINDOW-01 campaigns/ spec: block decomposition, argv hook, audit sweep.

The campaign runs the frozen boarding-screen design through the generic
``deploy/aws/campaign_entrypoint.py`` grammar — 12 blocks (theta x arm) x
20 seeds — so these tests pin that the block map covers the design's cell
enumeration exactly once, that ``entry.py`` emits the worker argv the
entrypoint expects, and that the readout's audit-invariant sweep accepts a
conforming payload and flags each broken echo.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "campaigns" / "covid" / "crew_window_01"
DESIGN = ROOT / "picard_framework" / "runs" / "covid_crew_window_01_design.json"


def _load(mod_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


cell_mod = _load("crew_window_cell", CAMPAIGN / "cell.py")
entry_mod = _load("crew_window_entry", CAMPAIGN / "entry.py")
readout_mod = _load("crew_window_readout", CAMPAIGN / "readout.py")

from picard_framework.covid_boarding_screen import (  # noqa: E402
    enumerate_cells,
    load_design,
)


@pytest.fixture(scope="module")
def spec() -> dict:
    return json.loads((CAMPAIGN / "campaign.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def design():
    return load_design(str(DESIGN))


def test_blocks_cover_the_design_grid_exactly_once(spec, design):
    pairs = [
        (float(b["args"]["theta"]), b["args"]["arm_id"])
        for b in spec["blocks"].values()
    ]
    assert len(pairs) == len(set(pairs)) == 12
    for block in spec["blocks"].values():
        assert sorted(block["seeds"]) == block["seeds"]
        assert set(block["seeds"]) == set(design.seed_values)
    expected = {
        (c.theta, c.arm_id, c.seed) for c in enumerate_cells(design)
    }
    covered = {
        (float(b["args"]["theta"]), b["args"]["arm_id"], seed)
        for b in spec["blocks"].values() for seed in b["seeds"]
    }
    assert covered == expected


def test_entry_build_argv_maps_block_args_and_seed(spec):
    block = spec["blocks"]["t7p9e6_crewduty"]
    argv, artifact = entry_mod.build_argv(
        SimpleNamespace(platform="diamond_princess_2020"),
        block, 20200211, Path("/tmp/out"),
    )
    text = " ".join(argv)
    assert "--theta 7900000" in text
    assert "--arm CREWDUTY" in text
    assert "--seed 20200211" in text
    assert Path(argv[1]).name == "cell.py"
    assert artifact.name == "cell_20200211.json"


def test_cell_match_resolves_one_cell_per_block(spec, design):
    for block in spec["blocks"].values():
        cell = cell_mod._match_cell(
            design, float(block["args"]["theta"]),
            block["args"]["arm_id"], block["seeds"][0],
        )
        assert cell.arm_id == block["args"]["arm_id"]
        assert cell.seed == block["seeds"][0]


def _payload(arm: str = "D0_declared", **overrides) -> dict:
    base = {
        "cell": {
            "arm_id": arm, "theta": 1e6, "seed": 20200205,
            "key": "screen_x_seed20200205_arm" + arm + ".json",
        },
        "quarantine_witness": {
            "window_days": [16, 30],
            "activated": True,
            "exempt_classes": [
                "crew_engineering", "crew_galley", "crew_general",
                "crew_medical",
            ],
        },
        "crew_duty_exclusion": {
            "resolved": {"enabled": False},
            "realized": {"excluded_hosts": 0},
        },
        "index_onset_day": -1.0,
        "index_shedding_at_day0": True,
        "propensity_draw": {"units_drawn": 12},
        "delivery": {"caregiver": {"mode": "on"}},
        "presentation_draw_mode": "once_per_course",
        "hand_reservoir_mode": "hygiene_cycle",
    }
    base.update(overrides)
    return base


def test_audit_cell_clean_on_a_conforming_payload():
    assert readout_mod._audit_cell(_payload()) == []


def test_audit_cell_flags_a_wrong_exempt_subset():
    payload = _payload(
        "EXEMPT_ENGMED",
        quarantine_witness={
            "window_days": [16, 30],
            "activated": True,
            "exempt_classes": ["crew_engineering", "crew_medical",
                               "crew_galley"],
        },
    )
    assert any("exempt_classes" in v for v in readout_mod._audit_cell(payload))


def test_audit_cell_flags_a_mess_split_echo_mismatch():
    conforming = _payload(
        "MESS_0P5",
        delivery={
            "caregiver": {"mode": "on"},
            "droplet_field_split": {
                "far_field_share": 0.0875,
                "settled_share": 0.0875,
                "active": True,
            },
        },
    )
    assert readout_mod._audit_cell(conforming) == []
    broken = _payload(
        "MESS_0P5",
        delivery={
            "caregiver": {"mode": "on"},
            "droplet_field_split": {
                "far_field_share": 0.175,
                "settled_share": 0.0,
                "active": True,
            },
        },
    )
    assert any(
        "far_field_share" in v or "settled_share" in v
        for v in readout_mod._audit_cell(broken)
    )


def test_audit_cell_flags_crewduty_not_resolved():
    payload = _payload(
        "CREWDUTY",
        crew_duty_exclusion={
            "resolved": {"enabled": False},
            "realized": {"excluded_hosts": 0},
        },
    )
    assert any(
        "crew_duty_exclusion" in v for v in readout_mod._audit_cell(payload)
    )


def _metrics(**over) -> dict:
    base = {
        "n": 20, "takeoff_n": 17,
        "during_median": 680.0, "during_median_takeoff": 240.0,
        "before_median": 300.0, "before_delta_median": 0.0,
        "before_delta_max_abs": 0.0, "before_delta_nonzero": 0,
        "crew_share_median": 0.4,
    }
    base.update(over)
    return base


def test_verdict_grammar_classification():
    reach = {"kind": "k", "reached": True}
    assert readout_mod._verdict(
        "CREWDUTY", _metrics(), reach, 0.9,
    ) == "CHANNEL-LANDED"
    assert readout_mod._verdict(
        "CREWDUTY", _metrics(during_median_takeoff=400.0), reach, 0.9,
    ) == "UNDER-ATTENUATED"
    assert readout_mod._verdict(
        "CREWDUTY", _metrics(during_median_takeoff=100.0), reach, 0.9,
    ) == "OVER-ATTENUATED"
    unmoved = readout_mod._verdict(
        "CREWDUTY", _metrics(), {"kind": "k", "reached": False}, 0.9,
    )
    assert unmoved.startswith("UNMOVED")
    assert readout_mod._verdict(
        "D0_declared", _metrics(), reach, 0.9,
    ) == "BASELINE"
