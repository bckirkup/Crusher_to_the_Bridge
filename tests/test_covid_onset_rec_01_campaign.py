"""ONSET-REC-01 campaign contract tests.

Pins the campaign grammar for campaigns/covid/onset_rec_01/: the two
blocks cover the design grid exactly once, the design's declared
``base_overrides`` equals the parent's ``sect_mess_boxed`` arm verbatim
(the bit-identity clause), arm 0 carries empty overrides, the period
arm's channel block is the frozen declaration, entry.build_argv maps
(block args, seed) onto the worker argv, and the worker's ``_match_cell``
+ ``base_overrides`` composition resolves each cell uniquely. Readout
audit/verdict functions are exercised on synthetic payloads.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_onset_rec_01_design.json"
)
PARENT_PATH = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_crew_mess_01_design.json"
)
CAMPAIGN_DIR = REPO_ROOT / "campaigns" / "covid" / "onset_rec_01"

SEEDS = list(range(20200205, 20200225))
CHANNEL_BLOCK = {
    "symptomatic_at_confirmation_required": True,
    "report_probability": 0.56,
}


def _load(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def design_raw() -> dict:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def parent_raw() -> dict:
    return json.loads(PARENT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def campaign() -> dict:
    return json.loads(
        (CAMPAIGN_DIR / "campaign.json").read_text(encoding="utf-8"),
    )


@pytest.fixture(scope="module")
def cell_mod() -> types.ModuleType:
    return _load("onset_rec_01_cell", CAMPAIGN_DIR / "cell.py")


@pytest.fixture(scope="module")
def entry_mod() -> types.ModuleType:
    return _load("onset_rec_01_entry", CAMPAIGN_DIR / "entry.py")


@pytest.fixture(scope="module")
def readout_mod() -> types.ModuleType:
    return _load("onset_rec_01_readout", CAMPAIGN_DIR / "readout.py")


# ---------------------------------------------------------------- design


def test_arm_zero_is_empty_baseline(design_raw: dict) -> None:
    arms = design_raw["arms"]
    assert arms[0]["arm_id"] == "boxed_declared"
    assert arms[0]["overrides"] == {}


def test_period_arm_carries_frozen_channel(design_raw: dict) -> None:
    period = design_raw["arms"][1]
    assert period["arm_id"] == "boxed_period"
    block = period["overrides"]["pathogen_overrides"]["sars_cov2_resp"][
        "observation_model"
    ]["onset_recording"]
    assert block == CHANNEL_BLOCK


def test_base_overrides_equals_sect_mess_boxed(
    design_raw: dict, parent_raw: dict,
) -> None:
    """The bit-identity clause: declared base == parent's boxed arm."""
    boxed = next(
        a for a in parent_raw["arms"] if a["arm_id"] == "sect_mess_boxed"
    )
    assert design_raw["base_overrides"] == boxed["overrides"]


def test_design_grid_and_scoring_frozen(design_raw: dict) -> None:
    assert design_raw["scenario_id"] == "diamond_princess_2020"
    assert design_raw["thetas"] == [7900000.0]
    assert design_raw["seeds"] == 20
    assert design_raw["cells"] == 40
    scoring = design_raw["scoring"]
    assert scoring["declared_before_running"] is True
    assert scoring["primary"]["declared_expectation_band"] == [0.43, 0.55]
    assert "bit_identity_clause" in scoring


# --------------------------------------------------------------- campaign


def test_blocks_cover_design_grid_exactly_once(
    campaign: dict, design_raw: dict,
) -> None:
    covered = set()
    for block in campaign["blocks"].values():
        arm = block["args"]["arm_id"]
        theta = block["args"]["theta"]
        for seed in block["seeds"]:
            assert (theta, arm, seed) not in covered
            covered.add((theta, arm, seed))
    expected = {
        (7900000, arm["arm_id"], seed)
        for arm in design_raw["arms"] for seed in SEEDS
    }
    assert covered == expected
    assert len(covered) == design_raw["cells"]


def test_campaign_fargate_targets(campaign: dict) -> None:
    assert campaign["queue"] == "picard-analysis-fargate-queue"
    assert campaign["s3_prefix"] == "campaign/covid_onset_rec_01/"
    assert campaign["image_tag"] == "covid-onset-rec-01"


def test_entry_build_argv(
    entry_mod: types.ModuleType, campaign: dict,
) -> None:
    args = MagicMock(platform="linux")
    block = campaign["blocks"]["boxed_period"]
    argv, artifact = entry_mod.build_argv(
        args, block, 20200210, Path("out/onset_rec_01"),
    )
    assert argv[0] == sys.executable
    assert "campaigns/covid/onset_rec_01/cell.py" in argv[1]
    flat = dict(zip(argv[2::2], argv[3::2]))
    assert flat["--design"].endswith("covid_onset_rec_01_design.json")
    assert flat["--theta"] == "7900000"
    assert flat["--arm"] == "boxed_period"
    assert flat["--seed"] == "20200210"
    assert artifact.name == "cell_20200210.json"


def test_match_cell_unique(cell_mod: types.ModuleType) -> None:
    from picard_framework.covid_boarding_screen import load_design

    design = load_design(str(DESIGN_PATH))
    cell = cell_mod._match_cell(design, 7900000.0, "boxed_period", 20200211)
    assert cell.seed == 20200211 and cell.arm_id == "boxed_period"
    with pytest.raises(SystemExit):
        cell_mod._match_cell(design, 7900000.0, "boxed_period", 19990101)


def test_base_overrides_loaded_from_design(
    cell_mod: types.ModuleType, design_raw: dict,
) -> None:
    assert cell_mod.base_overrides() == design_raw["base_overrides"]


def test_prepared_spec_matches_parent_boxed_spec(
    cell_mod: types.ModuleType,
) -> None:
    """Spec-level bit-identity: boxed_declared resolves the parent arm's
    run spec exactly (num_epochs pinned so specs are comparable)."""
    from picard_framework.covid_boarding_screen import (
        apply_arm_overrides, enumerate_cells, load_design,
        prepare_cell_run_spec,
    )
    from picard_framework.covid_theta_fit import load_covid_profile

    design = load_design(str(DESIGN_PATH))
    parent = load_design(str(PARENT_PATH))
    new_cell = next(
        c for c in enumerate_cells(design)
        if c.arm_id == "boxed_declared" and c.seed == 20200210
    )
    old_cell = next(
        c for c in enumerate_cells(parent)
        if c.arm_id == "sect_mess_boxed" and c.seed == 20200210
    )
    profile = load_covid_profile(str(REPO_ROOT))
    spec_new = prepare_cell_run_spec(
        design, new_cell, num_epochs=3, repo_root=str(REPO_ROOT),
    )
    apply_arm_overrides(
        spec_new, cell_mod.base_overrides(),
        profile=profile, theta=new_cell.theta,
    )
    spec_old = prepare_cell_run_spec(
        parent, old_cell, num_epochs=3, repo_root=str(REPO_ROOT),
    )
    # Cell-identity stamps differ (arm_id); compare the engine-facing spec.
    assert spec_new == spec_old


# ---------------------------------------------------------------- readout


def _payload(arm: str, seed: int, rec: float, conf: float) -> dict:
    return {
        "cell": {"arm_id": arm, "seed": seed, "theta": 7900000.0},
        "observables": {
            "recorded_onsets": rec,
            "campaign_positives": conf,
            "campaign_asymptomatic_positives": conf * 0.5,
        },
        "lab_confirmed_total": conf,
        "lab_confirmed_by_role": {
            "crew": conf * 0.4, "passenger": conf * 0.6,
        },
        "onset_recording": (
            None if arm == "boxed_declared" else dict(CHANNEL_BLOCK)
        ),
        "quarantine_witness": {
            "protocol_id": "SOP-017-MESSBOX",
            "window_days": [16, 30],
            "activated": True,
            "exempt_classes": list(readout_shipped_exempt()),
        },
        "crew_window": {
            "crew_meal_service": {
                "mode": "boxed", "diner_redirects": 100,
            },
            "service_deliveries": 160000,
        },
        "index_onset_day": -1.0,
        "index_shedding_at_day0": True,
        "delivery": {
            "caregiver": {"mode": "on"},
            "droplet_field_split": {
                "far_field_share": 0.175, "settled_share": 0.0,
            },
        },
        "confined_passenger_infections_during_quarantine": 35,
    }


def readout_shipped_exempt() -> tuple[str, ...]:
    return (
        "crew_engineering", "crew_galley", "crew_general", "crew_medical",
    )


def test_audit_clean_payload(readout_mod: types.ModuleType) -> None:
    assert readout_mod._audit_cell(
        _payload("boxed_period", 20200210, 100, 200),
    ) == []
    assert readout_mod._audit_cell(
        _payload("boxed_declared", 20200210, 100, 200),
    ) == []


def test_audit_flags_channel_echo_mismatch(
    readout_mod: types.ModuleType,
) -> None:
    bad = _payload("boxed_period", 20200210, 100, 200)
    bad["onset_recording"] = None
    assert any("onset_recording" in v for v in readout_mod._audit_cell(bad))
    bad2 = _payload("boxed_declared", 20200210, 100, 200)
    bad2["onset_recording"] = dict(CHANNEL_BLOCK)
    assert any(
        "onset_recording" in v for v in readout_mod._audit_cell(bad2)
    )


def test_audit_flags_missing_base(readout_mod: types.ModuleType) -> None:
    bad = _payload("boxed_period", 20200210, 100, 200)
    bad["quarantine_witness"]["protocol_id"] = "SOP-017"
    violations = readout_mod._audit_cell(bad)
    assert any("SOP-017-MESSBOX" in v for v in violations)


def test_verdict_grammar(readout_mod: types.ModuleType) -> None:
    assert "RECORD-MATCHED" in readout_mod._verdict("boxed_period", 0.28)
    assert "CHANNEL-INSUFFICIENT" in readout_mod._verdict(
        "boxed_period", 0.45,
    )
    assert "OVER-CLOSED" in readout_mod._verdict("boxed_period", 0.20)
    assert "BASELINE" in readout_mod._verdict("boxed_declared", 0.84)


def test_row_metrics_pooled_dated_share(
    readout_mod: types.ModuleType,
) -> None:
    payloads = [
        _payload("boxed_period", 20200205, 50, 200),
        _payload("boxed_period", 20200206, 100, 300),
    ]
    m = readout_mod._row_metrics(payloads, 10)
    assert m["pooled_dated_share"] == pytest.approx(150 / 500)
    assert m["lab_confirmed_crew_share_median"] == pytest.approx(0.4)
    assert m["symptomatic_at_specimen_median"] == pytest.approx(0.5)


def test_lab_confirmed_role_counts_splits_roles() -> None:
    """The payload witness counts lab confirmations per host role."""
    from picard_framework.covid_boarding_screen import (
        _lab_confirmed_role_counts,
    )

    syndromic = MagicMock()
    syndromic._lab_confirmed = {
        ("sars_cov2_resp", 1): 100,
        ("sars_cov2_resp", 2): 110,
        ("sars_cov2_resp", 3): 120,
        ("other_pathogen", 4): 130,
    }
    agents = {
        1: MagicMock(role="crew"),
        2: MagicMock(role="passenger"),
        3: MagicMock(role="crew"),
        4: MagicMock(role="passenger"),
    }
    counts = _lab_confirmed_role_counts(syndromic, agents)
    assert counts == {"passenger": 1, "crew": 2}


def test_lab_confirmed_role_counts_tolerates_stub() -> None:
    from picard_framework.covid_boarding_screen import (
        _lab_confirmed_role_counts,
    )

    assert _lab_confirmed_role_counts(object(), {}) == {
        "passenger": 0, "crew": 0,
    }
