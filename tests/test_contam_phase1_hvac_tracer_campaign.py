"""Phase 1 CONTAM tracer campaign contract tests.

Pins the frozen design before any cell runs: source pools and seed mapping,
campaign block coverage and dry-run child count, entrypoint argv for the
field-cache/trajectory split, the worker's engine constants and slim output
contract, and the readout's coverage/contrast/pilot aggregation.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_DIR = ROOT / "campaigns" / "contam" / "phase1_hvac_tracer_01"
DESIGN_DIR = CAMPAIGN_DIR / "design"
DESIGN_PATH = DESIGN_DIR / "phase1_hvac_tracer_design.json"
POOLS_PATH = CAMPAIGN_DIR / "source_pools.json"
CAMPAIGN_PATH = CAMPAIGN_DIR / "campaign.json"

HULLS = [
    "destroyer_baseline",
    "expedition_cruise_450",
    "fletcher_class_destroyer",
    "lexington_cv2",
    "saratoga_cv3",
    "missouri_bb63",
]
BUNDLED_HULLS = [hull for hull in HULLS if hull != "fletcher_class_destroyer"]
SEEDS = list(range(1, 21))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_mod = _load("contam_phase1_build", DESIGN_DIR / "build.py")
cell_mod = _load("contam_phase1_cell", CAMPAIGN_DIR / "cell.py")
entry_mod = _load("contam_phase1_entry", CAMPAIGN_DIR / "entry.py")
readout_mod = _load("contam_phase1_readout", CAMPAIGN_DIR / "readout.py")


@pytest.fixture(scope="module")
def design() -> dict[str, Any]:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pools_doc() -> dict[str, Any]:
    return json.loads(POOLS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def campaign() -> dict[str, Any]:
    return json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))


def _trajectory_cells(campaign_doc: dict[str, Any]) -> set[tuple[str, str, int]]:
    cells = set()
    for block in campaign_doc["blocks"].values():
        args = block.get("args") or {}
        if args.get("mode") != "trajectory":
            continue
        for seed in block["seeds"]:
            cells.add((str(args["hull"]), str(args["lane"]), int(seed)))
    return cells


class TestFrozenDesign:
    def test_generated_artifacts_match_builder(self, design, pools_doc, campaign) -> None:
        assert build_mod.build_design() == design
        assert build_mod._campaign_spec() == campaign
        assert pools_doc["design_id"] == design["design_id"]
        assert pools_doc["source_pools"] == {
            hull: payload["pool"] for hull, payload in design["source_pools"].items()
        }

    def test_design_freezes_manifest_constants(self, design) -> None:
        assert design["status"] == "frozen_before_first_cell"
        assert design["manifest_pr"] == 1172
        assert design["hulls"] == HULLS
        assert design["bundled_p_lane_hulls"] == BUNDLED_HULLS
        assert design["matrix"]["primary_trajectories"] == 240
        assert design["matrix"]["p_contrast_trajectories"] == 100
        assert design["matrix"]["total_trajectories"] == 340
        assert design["tracer"]["mass_per_seed"] == pytest.approx(1_000_000.0)
        assert design["tracer"]["natural_decay_rate"] == pytest.approx(0.0)
        assert design["tracer"]["filter_efficiency"] == pytest.approx(0.5)
        assert design["pilot"]["hull"] == "missouri_bb63"
        assert design["pilot"]["lane"] == "E"
        assert design["pilot"]["seeds"] == SEEDS
        assert design["thresholds"]["commissioned_field_solve_seconds_max"] == pytest.approx(30.0)
        assert design["thresholds"]["trajectory_wall_p95_seconds_max"] == pytest.approx(60.0)
        assert design["thresholds"]["artifact_bytes_max"] == 25 * 1024 * 1024
        assert design["acceptance_gates"]["stop_after_canary"] is True

    def test_source_pools_are_deterministic_and_capped(self, design) -> None:
        pools = design["source_pools"]
        assert set(pools) == set(HULLS)
        for hull in HULLS:
            payload = pools[hull]
            pool = payload["pool"]
            assert len(pool) <= 10
            assert len({item["id"] for item in pool}) == len(pool)
            counts = {category: 0 for category in ("large_venue", "sanitary_branch", "remote_weak")}
            for item in pool:
                assert item["category"] in counts
                counts[item["category"]] += 1
                if item["category"] == "sanitary_branch":
                    assert item["type"] == "Sanitary"
                if item["category"] == "remote_weak":
                    assert item["type"] != "Sanitary"
                    assert (not item["served"]) or item["adjacency_degree"] <= 1
            assert payload["counts"] == counts
            assert payload["zone_count"] > 0

    def test_seed_mapping_is_the_manifest_rule(self, design) -> None:
        grid = design["seed_mapping"]["grid"]
        assert set(grid) == {str(seed) for seed in SEEDS}
        for seed in SEEDS:
            k = seed - 1
            expected_timing = "t0_pulse" if k % 2 == 0 else "t0_t1_split"
            for hull in HULLS:
                row = grid[str(seed)][hull]
                pool_length = len(design["source_pools"][hull]["pool"])
                assert row["k"] == k
                assert row["timing_pattern"] == expected_timing
                assert row["pool_index"] == (k // 2) % pool_length

    def test_seed_mapping_pairs_lanes_by_hull_seed(self, design) -> None:
        for seed in SEEDS:
            for hull in HULLS:
                row = design["seed_mapping"]["grid"][str(seed)][hull]
                pool_item = design["source_pools"][hull]["pool"][row["pool_index"]]
                assert pool_item["id"]
                assert row["timing_pattern"] in {"t0_pulse", "t0_t1_split"}


class TestCampaignRegistration:
    def test_campaign_identity_and_prefix(self, campaign) -> None:
        assert campaign["name"] == "contam_phase1_hvac_tracer_01"
        assert campaign["pathogen"] == "contam"
        assert campaign["manifest"].endswith("phase1_hvac_tracer_design.json")
        assert campaign["s3_prefix"] == "campaign/contam_phase1_hvac_tracer_01/"
        assert campaign["queue"] == "picard-campaign-queue"
        assert campaign["readout"].endswith("readout.py")
        assert campaign["resources"] == {"vcpu": "1", "memory": "2048"}

    def test_blocks_cover_matrix_and_field_cache(self, campaign, design) -> None:
        assert campaign["blocks"]["field_cache"]["artifact"] == "field_cache.json"
        assert campaign["blocks"]["field_cache"]["args"] == {"mode": "field_cache"}
        assert campaign["blocks"]["field_cache"]["seeds"] == [1]
        cells = _trajectory_cells(campaign)
        expected = {
            (hull, lane, seed)
            for hull in HULLS
            for lane in (["N", "E"] if hull == "fletcher_class_destroyer" else ["N", "E", "P"])
            for seed in SEEDS
        }
        assert cells == expected
        assert len(cells) == 340
        assert design["execution"]["trajectory_array_children"] == 340
        assert design["execution"]["total_array_children"] == 341
        assert len(campaign["blocks"]) == 18

    def test_block_args_match_frozen_lanes(self, campaign) -> None:
        for name, block in campaign["blocks"].items():
            if name == "field_cache":
                continue
            args = block["args"]
            assert args["mode"] == "trajectory"
            assert args["hull"] in HULLS
            assert args["lane"] in {"N", "E", "P"}
            assert block["worker"].endswith("cell.py")
            assert block["artifact"] == "cell_{seed}.json"
            assert block["seeds"] == SEEDS
        assert "fletcher_class_destroyer_p" not in campaign["blocks"]
        for hull in BUNDLED_HULLS:
            assert f"{hull}_p" in campaign["blocks"]


class TestEntryArgv:
    def test_local_trajectory_uses_inline_field(self, campaign) -> None:
        block = campaign["blocks"]["missouri_bb63_e"]
        args = SimpleNamespace(
            epochs=12, epoch_hours=1.0, local=True, s3_prefix=None,
        )
        argv, artifact = entry_mod.build_argv(args, block, 7, Path("/tmp/out"))
        text = " ".join(argv)
        assert "--mode trajectory" in text
        assert "--hull missouri_bb63" in text
        assert "--lane E" in text
        assert "--seed 7" in text
        assert "--inline-field" in text
        assert artifact.name == "cell_7.json"

    def test_batch_trajectory_reads_field_cache_uri(self, campaign) -> None:
        block = campaign["blocks"]["missouri_bb63_e"]
        args = SimpleNamespace(
            epochs=12,
            epoch_hours=1.0,
            local=False,
            s3_prefix="s3://bucket/campaign/contam_phase1_hvac_tracer_01/",
        )
        argv, _artifact = entry_mod.build_argv(args, block, 7, Path("/tmp/out"))
        text = " ".join(argv)
        assert "--field-cache-uri s3://bucket/campaign/contam_phase1_hvac_tracer_01/field_cache/field_cache.json" in text
        assert "--inline-field" not in text

    def test_field_cache_block_argv(self, campaign) -> None:
        block = campaign["blocks"]["field_cache"]
        args = SimpleNamespace(epochs=12, epoch_hours=1.0, local=False, s3_prefix=None)
        argv, artifact = entry_mod.build_argv(args, block, 1, Path("/tmp/out"))
        text = " ".join(argv)
        assert "--mode field-cache" in text
        assert artifact.name == "field_cache.json"


class TestCellWorkerContracts:
    def test_native_engine_receives_frozen_tracer_constants(self) -> None:
        spatial, airflow = cell_mod._load_platform("destroyer_baseline")
        engine = cell_mod._native_engine(spatial, airflow, 1.0)
        assert engine.filter_efficiency == pytest.approx(0.5)
        assert engine.natural_decay_rate == pytest.approx(0.0)
        assert engine.clock.hours_per_epoch == pytest.approx(1.0)

    def test_seed_source_uses_frozen_pool_index(self, design) -> None:
        zone, timing, category, index = cell_mod._seed_source(design, "missouri_bb63", 3)
        row = design["seed_mapping"]["grid"]["3"]["missouri_bb63"]
        item = design["source_pools"]["missouri_bb63"]["pool"][row["pool_index"]]
        assert zone == item["id"]
        assert timing == row["timing_pattern"] == "t0_pulse"
        assert category == item["category"]
        assert index == row["pool_index"] == 1

    def test_run_trajectory_metrics_cover_manifest_fields(self) -> None:
        class FakeEngine:
            zone_nodes: dict[str, Any] = {}
            airflow_paths: list[Any] = []

            @staticmethod
            def transport_step(mass: dict[str, float], **_kwargs: Any) -> dict[str, float]:
                a = mass.get("A", 0.0)
                b = mass.get("B", 0.0)
                moved = a * 0.1
                return {"A": a - moved, "B": b + moved}

        metrics = cell_mod._run_trajectory(
            FakeEngine(), ["A", "B"], {"A": 10.0, "B": 20.0},
            "A", "t0_t1_split", 2, 1.0,
        )
        assert metrics["retained_fraction_curve"] == pytest.approx([1.0, 1.0])
        assert metrics["peak_concentration_zone"] == "A"
        assert metrics["peak_concentration_hour"] == pytest.approx(1.0)
        assert metrics["zone_stats"]["A"]["time_to_peak_h"] == pytest.approx(1.0)
        assert metrics["zone_stats"]["A"]["first_above_floor_h"] == pytest.approx(1.0)
        assert metrics["zone_stats"]["B"]["auc_concentration_per_m3_h"] > 0.0
        assert metrics["volume_weighted_concentration_burden_h"] > 0.0
        assert metrics["top_receptor_contrasts"]

    def test_field_audit_native_has_full_key_contract(self) -> None:
        audit = cell_mod._field_audit(object(), None, {"A"})
        assert audit["field_source"] == "native_layout"
        assert audit["dropped_endpoint_count"] == 0
        assert audit["unknown_real_zone_count"] == 0
        assert audit["alias_collision_count"] == 0


class TestReadout:
    def _cell(self, hull: str, lane: str, seed: int, retained: float) -> dict[str, Any]:
        return {
            "schema": cell_mod.SCHEMA_CELL,
            "design_id": "contam_phase1_hvac_tracer_01",
            "hull": hull,
            "lane": lane,
            "seed": seed,
            "source_zone": "SRC",
            "timing_pattern": "t0_pulse" if seed % 2 else "t0_t1_split",
            "metrics": {
                "retained_fraction_curve": [retained],
                "volume_weighted_concentration_burden_h": retained * 2.0,
                "concentration_auc_sum_per_m3_h": retained * 3.0,
                "peak_concentration_per_m3": retained * 4.0,
                "source_zone_final_mass": retained,
            },
            "path_flow_summary": {
                "path_count": 2,
                "total_flow_m3h": 100.0 + seed,
                "ducted_flow_m3h": 50.0,
                "by_path_type": {
                    "contamx_path": {"count": 1.0, "flow_m3h": 60.0, "ducted_flow_m3h": 50.0},
                    "passive": {"count": 1.0, "flow_m3h": 40.0 + seed, "ducted_flow_m3h": 0.0},
                },
            },
            "field_audit": {
                "dropped_endpoint_count": 0,
                "unknown_real_zone_count": 0,
                "alias_collision_count": 0,
            },
            "field_source": "field_cache",
            "timing": {"trajectory_seconds": 1.5, "field_seconds": 0.0, "peak_rss_mib": 100.0},
        }

    def test_build_report_coverage_contrasts_and_path_flows(self, campaign, design) -> None:
        cells = []
        for seed in SEEDS:
            cells.extend([
                (f"n{seed}", self._cell("missouri_bb63", "N", seed, 0.2), 100),
                (f"e{seed}", self._cell("missouri_bb63", "E", seed, 0.1), 100),
            ])
        field_cache = {"fields": {"missouri_bb63:E": {"field_seconds": 0.25}}}
        report = readout_mod.build_report(
            cells, campaign, design, field_cache=field_cache,
            array_wall_clock_minutes=1.0,
        )
        assert report["coverage"]["expected_cells"] == 340
        assert report["coverage"]["observed_cells"] == 40
        assert report["coverage"]["missing_cells"] == 300
        contrast = report["paired_contrasts"]["missouri_bb63"]["N_minus_E"]["retained_final"]
        assert contrast["n"] == 20
        assert contrast["mean"] == pytest.approx(0.1)
        assert contrast["ci95_half_width"] == pytest.approx(0.0)
        flows = report["path_flow_by_hull_lane"]["missouri_bb63:N"]
        assert flows["cells"] == 20
        assert flows["path_count"] == pytest.approx(2.0)
        assert flows["by_path_type"]["passive"]["flow_m3h"] == pytest.approx(50.5)
        pilot = report["pilot_gate"]["checks"]
        assert pilot["cell_count"] == 20
        assert pilot["expected_cell_count"] == 20
        assert pilot["seeds_complete"] is True
        assert pilot["commissioned_field_solve_seconds"] == pytest.approx(0.25)
        assert pilot["trajectory_wall_p95_seconds"] == pytest.approx(1.5)
        assert pilot["go"] is True

    def test_pilot_gate_is_not_go_without_full_seed_set(self, campaign, design) -> None:
        cells = [("e1", self._cell("missouri_bb63", "E", 1, 0.1), 100)]
        report = readout_mod.build_report(
            cells, campaign, design, array_wall_clock_minutes=1.0,
        )
        assert report["pilot_gate"]["checks"]["seeds_complete"] is False
        assert report["pilot_gate"]["checks"]["go"] is False
