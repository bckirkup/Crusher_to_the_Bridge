"""REPAIR-ISOLATION-01 campaign contract tests.

Pins the campaign grammar for campaigns/covid/repair_isolation_01/: the
design enumerates six arms on the DP boxed_s1s2 cell shape, the new
``room_air_map_arm`` and ``duty0_terminal_mode`` arm keys land where the
engine reads them (``room_air_map_arm`` is a build-time argument like
``pathogen_pool_transport``; ``duty0_terminal_mode`` writes
``config_overrides.hvac``), the campaign blocks cover the grid once,
the entry hook renders argv, and the readout audits coverage and pairs
each off-arm against the baseline arm seed-for-seed.
"""
from __future__ import annotations

import importlib.util
import json
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DP_DESIGN = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_repair_isolation_01_dp_design.json"
)
PARENT_DESIGN = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_crew_reach_01_design.json"
)
CAMPAIGN_DIR = REPO_ROOT / "campaigns" / "covid" / "repair_isolation_01"

DP_SEEDS = list(range(20200205, 20200225))
ARMS = [
    "baseline", "room_air_off", "nearfield_off", "pool_off",
    "duty0_off", "all_off",
]


def _load(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def campaign() -> dict:
    return json.loads(
        (CAMPAIGN_DIR / "campaign.json").read_text(encoding="utf-8"),
    )


@pytest.fixture(scope="module")
def entry_mod() -> types.ModuleType:
    return _load("repair_isolation_01_entry", CAMPAIGN_DIR / "entry.py")


@pytest.fixture(scope="module")
def cell_mod() -> types.ModuleType:
    return _load("repair_isolation_01_cell", CAMPAIGN_DIR / "cell.py")


@pytest.fixture(scope="module")
def readout_mod() -> types.ModuleType:
    return _load("repair_isolation_01_readout", CAMPAIGN_DIR / "readout.py")


# ------------------------------------------------------------------ designs


class TestDesign:
    def test_design_enumerates_120_cells(self) -> None:
        from picard_framework.covid_boarding_screen import (
            enumerate_cells,
            load_design,
        )
        design = load_design(str(DP_DESIGN))
        assert design.design_id == "covid_repair_isolation_01_dp"
        cells = enumerate_cells(design)
        assert len(cells) == 120
        assert {c.arm_id for c in cells} == set(ARMS)
        assert {c.seed for c in cells} == set(DP_SEEDS)

    def test_baseline_arm_empty_and_theta(self) -> None:
        raw = json.loads(DP_DESIGN.read_text())
        assert [a["arm_id"] for a in raw["arms"]] == ARMS
        assert raw["arms"][0]["overrides"] == {}
        assert raw["thetas"] == [7900000.0]

    def test_all_off_composes_every_baseline(self) -> None:
        raw = json.loads(DP_DESIGN.read_text())
        arms = {a["arm_id"]: a["overrides"] for a in raw["arms"]}
        assert arms["all_off"] == {
            "room_air_map_arm": "ambient_off",
            "near_field_air_mode": "off",
            "pathogen_pool_transport": "none",
            "duty0_terminal_mode": "sealed",
        }
        for arm in ARMS[1:-1]:
            items = arms[arm].items()
            assert len(items) == 1
            key, value = next(iter(items))
            assert arms["all_off"][key] == value

    def test_base_overrides_equal_parent_boxed_arm(self) -> None:
        raw = json.loads(DP_DESIGN.read_text())
        parent = json.loads(PARENT_DESIGN.read_text())
        boxed = next(
            a for a in parent["arms"] if a["arm_id"] == "boxed_s1s2"
        )
        merged = dict(parent["base_overrides"])
        merged.update(boxed["overrides"])
        assert raw["base_overrides"] == merged


# -------------------------------------------------------------- arm grammar


class TestRepairArmKeys:
    def test_room_air_map_arm_writes_map_arm(self) -> None:
        """Build-time argument — lands on
        config_overrides.transmission.room_air_removal.map_arm."""
        from picard_framework.covid_theta_fit import (
            _declare_room_air_map_arm,
        )
        overrides = {"transmission": {}}
        _declare_room_air_map_arm(overrides, "ambient_off")
        assert (
            overrides["transmission"]["room_air_removal"]["map_arm"]
            == "ambient_off"
        )

    def test_room_air_map_arm_keeps_declared_mode(self) -> None:
        from picard_framework.covid_theta_fit import (
            _declare_room_air_map_arm,
        )
        overrides = {"transmission": {"room_air_removal": "first_order"}}
        _declare_room_air_map_arm(overrides, "ambient_on")
        block = overrides["transmission"]["room_air_removal"]
        assert block == {"mode": "first_order", "map_arm": "ambient_on"}

    def test_room_air_map_arm_refuses_unknown(self) -> None:
        from picard_framework.covid_theta_fit import (
            _declare_room_air_map_arm,
        )
        with pytest.raises(ValueError, match="room_air_map_arm"):
            _declare_room_air_map_arm({"transmission": {}}, "vent")

    def test_duty0_terminal_mode_lands_on_hvac(self) -> None:
        from picard_framework.covid_boarding_screen import (
            apply_arm_overrides,
        )
        raw = {"config_overrides": {}}
        apply_arm_overrides(
            raw, {"duty0_terminal_mode": "sealed"}, profile={},
        )
        assert (
            raw["config_overrides"]["hvac"]["duty0_terminal_mode"]
            == "sealed"
        )

    def test_duty0_terminal_mode_refuses_unknown(self) -> None:
        from picard_framework.covid_boarding_screen import (
            apply_arm_overrides,
        )
        with pytest.raises(ValueError, match="duty0_terminal_mode"):
            apply_arm_overrides(
                {"config_overrides": {}},
                {"duty0_terminal_mode": "vent"}, profile={},
            )

    def test_spec_composes_every_arm(self) -> None:
        """prepare_cell_run_spec + the boxed_s1s2 base leave each arm's
        toggle where the engine reads it — the grammar claim the
        campaign result stands on."""
        from picard_framework.covid_boarding_screen import (
            apply_arm_overrides,
            enumerate_cells,
            load_design,
            prepare_cell_run_spec,
        )
        from picard_framework.covid_theta_fit import load_covid_profile

        design = load_design(str(DP_DESIGN))
        cells = {
            c.arm_id: c for c in enumerate_cells(design)
            if c.seed == 20200205
        }
        raw = json.loads(DP_DESIGN.read_text())
        base = raw["base_overrides"]
        profile = load_covid_profile(str(REPO_ROOT))
        expect = {
            "baseline": ({}, None, None),
            "room_air_off": ({}, None, {"map_arm": "ambient_off"}),
            "nearfield_off": ({}, "off", None),
            "pool_off": ({"pathogen_pool_transport": "none"}, None, None),
            "duty0_off": ({"duty0_terminal_mode": "sealed"}, None, None),
            "all_off": (
                {"pathogen_pool_transport": "none",
                 "duty0_terminal_mode": "sealed"},
                "off",
                {"map_arm": "ambient_off"},
            ),
        }
        for arm_id, cell in cells.items():
            spec = prepare_cell_run_spec(
                design, cell, num_epochs=2, repo_root=str(REPO_ROOT),
            )
            apply_arm_overrides(
                spec, base, profile=profile, theta=cell.theta,
            )
            co = spec["config_overrides"]
            hvac_exp, nf_exp, rar_exp = expect[arm_id]
            assert co.get("hvac", {}) == hvac_exp
            tx = co.get("transmission", {})
            nf = tx.get("near_field_air")
            assert (nf or {}).get("mode") == nf_exp
            assert tx.get("room_air_removal") == rar_exp


# ------------------------------------------------------------------ campaign


class TestCampaignJson:
    def test_blocks_cover_the_grid_once(self, campaign: dict) -> None:
        cells = {
            (b["args"]["design"], b["args"]["arm_id"], seed)
            for b in campaign["blocks"].values()
            for seed in b["seeds"]
        }
        assert len(cells) == 120
        assert {a for _, a, _ in cells} == set(ARMS)

    def test_image_digest_pinned(self, campaign: dict) -> None:
        import re
        assert re.fullmatch(
            r"sha256:[0-9a-f]{64}", campaign["image_digest"],
        )

    def test_build_argv(self, entry_mod: types.ModuleType) -> None:
        import argparse
        args = argparse.Namespace(platform="ec2")
        block = {
            "artifact": "cell_{seed}.json",
            "args": {
                "design": "picard_framework/runs/"
                          "covid_repair_isolation_01_dp_design.json",
                "theta": 7900000,
                "arm_id": "all_off",
            },
        }
        command, artifact = entry_mod.build_argv(
            args, block, 20200211, Path("/tmp/out"),
        )
        assert command[command.index("--arm") + 1] == "all_off"
        assert command[command.index("--seed") + 1] == "20200211"
        assert artifact.name == "cell_20200211.json"


# --------------------------------------------------------------- cell worker


class TestCellHelpers:
    def test_match_cell_unique(self, cell_mod) -> None:
        from picard_framework.covid_boarding_screen import load_design
        design = load_design(str(DP_DESIGN))
        cell = cell_mod._match_cell(design, 7900000.0, "all_off", 20200210)
        assert cell.arm_id == "all_off" and cell.seed == 20200210

    def test_match_cell_miss_refuses(self, cell_mod) -> None:
        from picard_framework.covid_boarding_screen import load_design
        design = load_design(str(DP_DESIGN))
        with pytest.raises(SystemExit):
            cell_mod._match_cell(design, 7900000.0, "all_off", 1)

    def test_base_overrides_from_design(self, cell_mod) -> None:
        base = cell_mod.base_overrides(
            "picard_framework/runs/"
            "covid_repair_isolation_01_dp_design.json",
        )
        assert base["scheduled_protocol_id"] == "SOP-017-MESSBOX"


# ------------------------------------------------------------------- readout


_RESOLVED_BY_ARM = {
    "baseline": {
        "room_air_map_arm": "ambient_on",
        "near_field_air_mode": "two_box",
        "pathogen_pool_transport": "airflow",
        "duty0_terminal_mode": "extract",
    },
    "room_air_off": {
        "room_air_map_arm": "ambient_off",
        "near_field_air_mode": "two_box",
        "pathogen_pool_transport": "airflow",
        "duty0_terminal_mode": "extract",
    },
    "nearfield_off": {
        "room_air_map_arm": "ambient_on",
        "near_field_air_mode": "off",
        "pathogen_pool_transport": "airflow",
        "duty0_terminal_mode": "extract",
    },
    "pool_off": {
        "room_air_map_arm": "ambient_on",
        "near_field_air_mode": "two_box",
        "pathogen_pool_transport": "none",
        "duty0_terminal_mode": "extract",
    },
    "duty0_off": {
        "room_air_map_arm": "ambient_on",
        "near_field_air_mode": "two_box",
        "pathogen_pool_transport": "airflow",
        "duty0_terminal_mode": "sealed",
    },
    "all_off": {
        "room_air_map_arm": "ambient_off",
        "near_field_air_mode": "off",
        "pathogen_pool_transport": "none",
        "duty0_terminal_mode": "sealed",
    },
}


def _payload(
    seed: int, arm: str, *, design: str = "covid_repair_isolation_01_dp",
    resolved: str = "ContamTransportEngine", recorded: int = 0,
    lab: int = 0, toggles: dict | None = None,
) -> dict:
    resolved_toggles = dict(toggles or _RESOLVED_BY_ARM[arm])
    return {
        "design_id": design,
        "cell": {"arm_id": arm, "seed": seed},
        "delivery": {
            "transport_engine": "native",
            "transport_engine_resolved": resolved,
            "room_air_removal": {
                "mode": "first_order",
                "map_arm": resolved_toggles["room_air_map_arm"],
            },
            "near_field_air": {
                "mode": resolved_toggles["near_field_air_mode"],
            },
            "pathogen_pool_transport": (
                resolved_toggles["pathogen_pool_transport"]
            ),
            "duty0_terminal_mode": resolved_toggles["duty0_terminal_mode"],
        },
        "observables": {
            "recorded_onsets": recorded,
            "onsets_before_split_day": 0,
            "passenger_onsets_before": 0,
            "passenger_onsets_after": 0,
            "crew_onsets_before": 0,
            "crew_onsets_after": 0,
            "campaign_positives": 0,
            "campaign_asymptomatic_positives": 0,
        },
        "lab_confirmed_total": lab,
        "lab_confirmed_by_role": {"crew": 0, "passenger": lab},
        "funnel_hosts": {},
        "infections_total": 0,
    }


class TestReadout:
    def test_undefined_shares_stay_null(self, readout_mod) -> None:
        ch = readout_mod._channels(_payload(1, "baseline"))
        assert ch["asym_share_final"] is None
        assert ch["dated_share"] is None
        row = readout_mod._row([ch["asym_share_final"], None])
        assert row["n"] == 0

    def test_audit_flags_wrong_engine_and_missing(
        self, readout_mod,
    ) -> None:
        audit = readout_mod._audit([
            _payload(20200205, "baseline"),
            _payload(20200205, "all_off",
                     resolved="ContamXTransportEngine"),
        ])
        assert audit["wrong_engine"] == [
            ("covid_repair_isolation_01_dp", "all_off", 20200205),
        ]
        assert audit["wrong_toggles"] == []
        assert audit["missing_cells"]

    def test_audit_flags_wrong_toggles(self, readout_mod) -> None:
        """A voyage whose declared toggle never reached the engine is a
        wrong-toggles cell, the same audit class as a wrong engine."""
        bad = _payload(
            20200205, "all_off",
            toggles=_RESOLVED_BY_ARM["baseline"],
        )
        audit = readout_mod._audit([bad])
        assert audit["wrong_toggles"] == [
            ("covid_repair_isolation_01_dp", "all_off", 20200205),
        ]

    def test_paired_delta_against_baseline(self, readout_mod) -> None:
        baseline = [
            _payload(s, "baseline", recorded=10) for s in DP_SEEDS
        ]
        arm = [
            _payload(s, "all_off", recorded=20) for s in DP_SEEDS
        ]
        row = readout_mod._paired_delta(
            baseline, arm, "recorded_onsets",
        )
        assert row["n"] == 20
        assert row["median"] == 10

    def test_paired_delta_skips_undefined(self, readout_mod) -> None:
        baseline = [_payload(20200205, "baseline", lab=0)]
        arm = [_payload(20200205, "all_off", lab=5)]
        row = readout_mod._paired_delta(
            baseline, arm, "dated_share",
        )
        assert row["n"] == 0

    def test_main_scores_and_pairs(
        self, readout_mod, tmp_path: Path,
    ) -> None:
        cells = tmp_path / "cells"
        cells.mkdir()
        for arm in ARMS:
            for seed in DP_SEEDS:
                p = _payload(seed, arm, recorded=100 + seed % 5)
                (cells / f"cell_{arm}_{seed}.json").write_text(
                    json.dumps(p),
                )
        out = tmp_path / "readout.json"
        assert readout_mod.main(
            ["--cells-dir", str(cells), "--out", str(out)],
        ) == 0
        report = json.loads(out.read_text())
        assert report["audit"]["cells"] == 120
        assert report["audit"]["missing_cells"] == []
        assert report["audit"]["wrong_engine"] == []
        scenario = report["scenarios"]["covid_repair_isolation_01_dp"]
        assert set(scenario) - set(ARMS) == {
            f"paired_delta_{a}_minus_baseline" for a in ARMS[1:]
        }
        assert scenario["baseline"]["takeoff_share"] == 1.0
