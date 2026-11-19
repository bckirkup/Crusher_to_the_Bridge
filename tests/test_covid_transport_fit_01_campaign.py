"""TRANSPORT-FIT-01 campaign contract tests.

Pins the campaign grammar for campaigns/covid/transport_fit_01/: the two
frozen designs enumerate the declared grids, the ``transport_engine``
arm key writes ``config_overrides.hvac.transport_engine`` (``auto``
refused — a silent native fallback is an unmeasured arm divergence),
the delivery block echoes declared and resolved solver, the campaign
blocks cover each grid once, the entry hook renders argv, and the
readout audits coverage against the spec's expected cell set.
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
    / "covid_transport_fit_01_dp_design.json"
)
GM_DESIGN = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_transport_fit_01_gm_design.json"
)
PARENT_DESIGN = (
    REPO_ROOT / "picard_framework" / "runs"
    / "covid_crew_reach_01_design.json"
)
CAMPAIGN_DIR = REPO_ROOT / "campaigns" / "covid" / "transport_fit_01"

DP_SEEDS = list(range(20200205, 20200225))
GM_SEEDS = list(range(20200205, 20200255))


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
    return _load("transport_fit_01_entry", CAMPAIGN_DIR / "entry.py")


@pytest.fixture(scope="module")
def cell_mod() -> types.ModuleType:
    return _load("transport_fit_01_cell", CAMPAIGN_DIR / "cell.py")


@pytest.fixture(scope="module")
def readout_mod() -> types.ModuleType:
    return _load("transport_fit_01_readout", CAMPAIGN_DIR / "readout.py")


# ------------------------------------------------------------------ designs


class TestDesigns:
    def test_dp_design_enumerates_40_cells(self) -> None:
        from picard_framework.covid_boarding_screen import (
            enumerate_cells,
            load_design,
        )
        design = load_design(str(DP_DESIGN))
        assert design.design_id == "covid_transport_fit_01_dp"
        cells = enumerate_cells(design)
        assert len(cells) == 40
        assert {c.arm_id for c in cells} == {"native", "contamx"}
        assert {c.seed for c in cells} == set(DP_SEEDS)

    def test_dp_baseline_arm_empty_and_theta(self) -> None:
        raw = json.loads(DP_DESIGN.read_text())
        assert [a["arm_id"] for a in raw["arms"]] == ["native", "contamx"]
        assert raw["arms"][0]["overrides"] == {}
        assert raw["arms"][1]["overrides"] == {
            "transport_engine": "contamx",
        }
        assert raw["thetas"] == [7900000.0]

    def test_dp_base_overrides_equal_parent_boxed_arm(self) -> None:
        raw = json.loads(DP_DESIGN.read_text())
        parent = json.loads(PARENT_DESIGN.read_text())
        boxed = next(
            a for a in parent["arms"] if a["arm_id"] == "boxed_s1s2"
        )
        merged = dict(parent["base_overrides"])
        merged.update(boxed["overrides"])
        assert raw["base_overrides"] == merged

    def test_gm_design_enumerates_100_cells(self) -> None:
        from picard_framework.covid_boarding_screen import (
            enumerate_cells,
            load_design,
        )
        design = load_design(str(GM_DESIGN))
        cells = enumerate_cells(design)
        assert len(cells) == 100
        assert {c.arm_id for c in cells} == {"native", "contamx"}
        assert {c.seed for c in cells} == set(GM_SEEDS)
        assert design.split_day == 20
        assert design.turn_day == 8
        assert design.funnel_echo is True


# -------------------------------------------------------------- arm grammar


class TestTransportEngineKey:
    def test_contamx_lands_on_hvac(self) -> None:
        from picard_framework.covid_boarding_screen import (
            apply_arm_overrides,
        )
        raw = {"config_overrides": {}}
        apply_arm_overrides(
            raw, {"transport_engine": "contamx"},
            profile={}, theta=7.9e6,
        )
        assert (
            raw["config_overrides"]["hvac"]["transport_engine"]
            == "contamx"
        )

    def test_native_lands_on_hvac(self) -> None:
        from picard_framework.covid_boarding_screen import (
            apply_arm_overrides,
        )
        raw = {"config_overrides": {}}
        apply_arm_overrides(
            raw, {"transport_engine": "native"}, profile={},
        )
        assert (
            raw["config_overrides"]["hvac"]["transport_engine"]
            == "native"
        )

    def test_auto_refused(self) -> None:
        """'auto' would silently fall back to native — in a campaign that
        is an unmeasured arm divergence, so the grammar refuses it."""
        from picard_framework.covid_boarding_screen import (
            apply_arm_overrides,
        )
        with pytest.raises(ValueError, match="transport_engine"):
            apply_arm_overrides(
                {"config_overrides": {}},
                {"transport_engine": "auto"}, profile={},
            )

    def test_unknown_engine_refused(self) -> None:
        from picard_framework.covid_boarding_screen import (
            apply_arm_overrides,
        )
        with pytest.raises(ValueError, match="transport_engine"):
            apply_arm_overrides(
                {"config_overrides": {}},
                {"transport_engine": "contamw"}, profile={},
            )


# ------------------------------------------------------------------ campaign


class TestCampaignJson:
    def test_blocks_cover_the_grid_once(self, campaign: dict) -> None:
        cells = {
            (b["args"]["design"], b["args"]["arm_id"], seed)
            for b in campaign["blocks"].values()
            for seed in b["seeds"]
        }
        assert len(cells) == 140

    def test_image_digest_pinned(self, campaign: dict) -> None:
        import re
        assert re.fullmatch(
            r"sha256:[0-9a-f]{64}", campaign["image_digest"],
        )

    def test_binary_pin_is_the_nist_digest(self) -> None:
        cell = (CAMPAIGN_DIR / "cell.py").read_text()
        assert (
            "d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309"
            "d6590cec652274b2b" in cell
        )

    def test_build_argv(self, entry_mod: types.ModuleType) -> None:
        import argparse
        args = argparse.Namespace(platform="ec2")
        block = {
            "artifact": "cell_{seed}.json",
            "args": {
                "design": "picard_framework/runs/"
                          "covid_transport_fit_01_dp_design.json",
                "theta": 7900000,
                "arm_id": "contamx",
            },
        }
        command, artifact = entry_mod.build_argv(
            args, block, 20200211, Path("/tmp/out"),
        )
        assert command[command.index("--arm") + 1] == "contamx"
        assert command[command.index("--seed") + 1] == "20200211"
        assert command[command.index("--theta") + 1] == "7900000"
        assert artifact.name == "cell_20200211.json"


# --------------------------------------------------------------- cell worker


class TestCellHelpers:
    def test_declared_engine_reads_arm(self, cell_mod) -> None:
        from picard_framework.covid_boarding_screen import load_design
        design = load_design(str(DP_DESIGN))
        assert cell_mod._declared_engine(design, "native") == "native"
        assert cell_mod._declared_engine(design, "contamx") == "contamx"

    def test_match_cell_unique(self, cell_mod) -> None:
        from picard_framework.covid_boarding_screen import load_design
        design = load_design(str(DP_DESIGN))
        cell = cell_mod._match_cell(design, 7900000.0, "contamx", 20200210)
        assert cell.arm_id == "contamx" and cell.seed == 20200210

    def test_match_cell_miss_refuses(self, cell_mod) -> None:
        from picard_framework.covid_boarding_screen import load_design
        design = load_design(str(DP_DESIGN))
        with pytest.raises(SystemExit):
            cell_mod._match_cell(design, 7900000.0, "contamx", 1)

    def test_base_overrides_from_design(self, cell_mod) -> None:
        base = cell_mod.base_overrides(
            "picard_framework/runs/covid_transport_fit_01_dp_design.json",
        )
        assert base["scheduled_protocol_id"] == "SOP-017-MESSBOX"

    def test_local_binary_resolves(self, cell_mod) -> None:
        """The repo's third_party drop wins the resolution order; the S3
        leg is exercised on Batch, where the image lacks the binary."""
        path = cell_mod._ensure_contamx_binary({})
        assert path is not None and "contamx3" in path


# ------------------------------------------------------------------- readout


def _payload(
    seed: int, arm: str, *, design: str = "covid_transport_fit_01_dp",
    resolved: str | None = None, recorded: int = 0, lab: int = 0,
) -> dict:
    return {
        "design_id": design,
        "cell": {"arm_id": arm, "seed": seed},
        "delivery": {
            "transport_engine": arm,
            "transport_engine_resolved": resolved or {
                "native": "ContamTransportEngine",
                "contamx": "ContamXTransportEngine",
            }[arm],
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
        ch = readout_mod._channels(_payload(1, "native"))
        assert ch["asym_share_final"] is None
        assert ch["dated_share"] is None
        assert ch["campaign_asym_share"] is None
        row = readout_mod._row([ch["asym_share_final"], None])
        assert row["n"] == 0

    def test_funnel_asym_counts_and_window(self, readout_mod) -> None:
        p = _payload(1, "native", recorded=4, lab=4)
        p["funnel_hosts"] = {
            "a": {"confirmed_day": 5, "presented_day": 6},
            "b": {"confirmed_day": 6, "presented_day": None},
            "c": {"confirmed_day": 7, "presented_day": 7},
            "d": {"confirmed_day": 40, "presented_day": None},
        }
        asym, conf = readout_mod._funnel_asym(p, None)
        assert (asym, conf) == (3, 4)
        asym31, conf31 = readout_mod._funnel_asym(p, 31)
        assert (asym31, conf31) == (2, 3)

    def test_audit_flags_missing_and_wrong_engine(
        self, readout_mod,
    ) -> None:
        audit = readout_mod._audit([
            _payload(20200205, "native"),
            _payload(20200205, "contamx",
                     resolved="ContamTransportEngine"),
        ])
        assert audit["wrong_engine"] == [
            ("covid_transport_fit_01_dp", "contamx", 20200205),
        ]
        assert audit["missing_cells"]  # 138 expected cells absent

    def test_main_scores_and_pairs(
        self, readout_mod, tmp_path: Path,
    ) -> None:
        cells = tmp_path / "cells"
        cells.mkdir()
        for arm in ("native", "contamx"):
            for seed in DP_SEEDS:
                p = _payload(seed, arm, recorded=100 + seed % 5)
                (cells / f"cell_{arm}_{seed}.json").write_text(
                    json.dumps(p),
                )
        (cells / "cell_native_20200205.json").write_text(
            json.dumps(_payload(20200205, "native", recorded=101)),
        )
        out = tmp_path / "report.json"
        assert readout_mod.main(
            ["--cells-dir", str(cells), "--out", str(out)],
        ) == 0
        report = json.loads(out.read_text())
        assert not report["audit"]["wrong_engine"]
        gm = report["scenarios"]["covid_transport_fit_01_dp"]
        assert "paired_delta_contamx_minus_native" in gm
        assert gm["native"]["recorded_onsets"]["n"] == 20
        turns = gm["native"]["onset_turn_directions"]
        assert turns == {"pax_flat/crew_flat": 20}

    def test_paired_delta_subtracts_per_seed(self, readout_mod) -> None:
        native = [
            _payload(20200205, "native", recorded=10),
            _payload(20200206, "native", recorded=20),
        ]
        contamx = [
            _payload(20200205, "contamx", recorded=15),
            _payload(20200206, "contamx", recorded=50),
            _payload(20200207, "contamx", recorded=99),
        ]
        delta = readout_mod._paired_delta(
            native, contamx, "recorded_onsets",
        )
        assert delta["n"] == 2
        assert delta["median"] == pytest.approx(17.5)
