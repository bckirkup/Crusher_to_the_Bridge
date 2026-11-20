"""THETA-REFIT-01 campaign contract tests.

Pins the campaign grammar for campaigns/covid/theta_refit_01/: the DP
design enumerates one baseline arm on the boxed_s1s2 cell shape across a
declared Theta grid, the GM held-out design mirrors it, the campaign
blocks cover the grid once per hull, the entry hook renders argv, and
the readout's audit flags a cell whose resolved repair toggles are not
the shipped post-B1-B3 defaults.
"""
from __future__ import annotations

import importlib.util
import json
import math
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DP_DESIGN = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_theta_refit_01_dp_design.json"
)
GM_DESIGN = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_theta_refit_01_gm_design.json"
)
CAMPAIGN_DIR = REPO_ROOT / "campaigns" / "covid" / "theta_refit_01"

GRID = tuple([7.9e6] + [10.0 ** (7 + 0.5 * i) for i in range(11)])


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
    return _load("theta_refit_01_entry", CAMPAIGN_DIR / "entry.py")


@pytest.fixture(scope="module")
def cell_mod() -> types.ModuleType:
    return _load("theta_refit_01_cell", CAMPAIGN_DIR / "cell.py")


@pytest.fixture(scope="module")
def readout_mod() -> types.ModuleType:
    return _load("theta_refit_01_readout", CAMPAIGN_DIR / "readout.py")


# ------------------------------------------------------------------ designs


class TestDesign:
    def test_dp_design_enumerates_240_cells(self) -> None:
        from picard_framework.covid_boarding_screen import (
            enumerate_cells,
            load_design,
        )
        design = load_design(str(DP_DESIGN))
        assert design.design_id == "covid_theta_refit_01_dp"
        cells = enumerate_cells(design)
        assert len(cells) == 240
        assert len({c.theta for c in cells}) == len(GRID)
        assert {c.arm_id for c in cells} == {"baseline"}

    def test_gm_design_enumerates_600_cells(self) -> None:
        from picard_framework.covid_boarding_screen import (
            enumerate_cells,
            load_design,
        )
        design = load_design(str(GM_DESIGN))
        assert design.design_id == "covid_theta_refit_01_gm"
        assert len(enumerate_cells(design)) == 600

    def test_dp_design_keeps_boxed_s1s2_base_overrides(self) -> None:
        tf = json.loads(
            (REPO_ROOT / "picard_framework" / "runs"
             / "covid_transport_fit_01_dp_design.json").read_text(),
        )
        design = json.loads(DP_DESIGN.read_text())
        assert design["base_overrides"] == tf["base_overrides"]

    def test_grid_brackets_current_fit(self) -> None:
        assert GRID[0] == 7.9e6
        assert math.isclose(GRID[-1], 1e12)


# ------------------------------------------------------------------ campaign


class TestCampaignSpec:
    def test_blocks_cover_the_grid_once(self, campaign: dict) -> None:
        seen: dict[str, set] = {"dp": set(), "gm": set()}
        for name, block in campaign["blocks"].items():
            hull, _ = name.split("_", 1)
            seen[hull].add(block["args"]["theta"])
        assert seen["dp"] == set(GRID)
        assert seen["gm"] == set(GRID)
        dp_cells = sum(
            len(b["seeds"]) for n, b in campaign["blocks"].items()
            if n.startswith("dp_")
        )
        gm_cells = sum(
            len(b["seeds"]) for n, b in campaign["blocks"].items()
            if n.startswith("gm_")
        )
        assert dp_cells == 240
        assert gm_cells == 600


# ------------------------------------------------------------------ entry


class TestEntry:
    def test_build_argv_renders_cell_args(
        self, entry_mod: types.ModuleType, campaign: dict,
    ) -> None:
        block = campaign["blocks"]["dp_theta_10p00"]
        args = types.SimpleNamespace(platform="linux")
        command, artifact = entry_mod.build_argv(
            args, block, 20200205, Path("/tmp/out"),
        )
        assert command[1].endswith("theta_refit_01/cell.py")
        assert "--theta" in command
        assert command[command.index("--theta") + 1] == "10000000000.0"
        assert command[command.index("--arm") + 1] == "baseline"
        assert artifact.name == "cell_20200205.json"


# ------------------------------------------------------------------ readout


class TestReadoutAudit:
    def _payload(self, **toggles) -> dict:
        delivery = {
            "room_air_removal": {
                "mode": "first_order",
                "map_arm": toggles.get("map_arm", "ambient_on"),
            },
            "near_field_air": {
                "mode": toggles.get("near", "two_box"),
                "interzonal_airflow_m3_per_hour": 204.0,
                "neighbour_table_ratio": 0.43,
            },
            "pathogen_pool_transport": toggles.get("pool", "airflow"),
            "duty0_terminal_mode": toggles.get("duty0", "extract"),
            "transport_engine_resolved": toggles.get(
                "engine", "ContamTransportEngine"),
        }
        return {
            "cell": {
                "scenario_id": "diamond_princess_2020",
                "theta": 7.9e6, "seed": 20200205,
            },
            "delivery": delivery,
            "observables": {
                "scenario_id": "diamond_princess_2020",
                "theta": 7.9e6, "seed": 20200205,
                "recorded_onsets": 0,
                "onsets_before_split_day": 0,
                "onsets_on_or_after_split_day": 0,
                "passenger_onsets_before": 0,
                "passenger_onsets_after": 0,
                "crew_onsets_before": 0,
                "crew_onsets_after": 0,
                "campaign_specimens": 0,
                "campaign_positives": 0,
                "campaign_asymptomatic_positives": 0,
            },
        }

    def _write_and_load(
        self, readout_mod: types.ModuleType, tmp_path: Path, payload: dict,
    ) -> list[str]:
        (tmp_path / "blk").mkdir(exist_ok=True)
        (tmp_path / "blk" / "cell_20200205.json").write_text(
            json.dumps(payload),
        )
        _, findings = readout_mod._load_cells(tmp_path)
        return findings

    def test_clean_payload_passes_audit(
        self, readout_mod: types.ModuleType, tmp_path: Path,
    ) -> None:
        assert self._write_and_load(
            readout_mod, tmp_path, self._payload()) == []

    def test_audit_flags_wrong_toggles(
        self, readout_mod: types.ModuleType, tmp_path: Path,
    ) -> None:
        findings = self._write_and_load(
            readout_mod, tmp_path,
            self._payload(map_arm="ambient_off", pool="none"),
        )
        assert any("map_arm" in f for f in findings)
        assert any("pathogen_pool_transport" in f for f in findings)

    def test_audit_flags_wrong_engine(
        self, readout_mod: types.ModuleType, tmp_path: Path,
    ) -> None:
        findings = self._write_and_load(
            readout_mod, tmp_path,
            self._payload(engine="ContamXTransportEngine"),
        )
        assert any("engine" in f for f in findings)
