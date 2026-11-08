"""Phase 2 CONTAM four-cruise contrast campaign contract tests.

Pins the frozen design before any cell runs: the manifest §3 hull panel
recomputed from the platform JSONs, source pools and seed mapping, the
1,200-trajectory / 60-block matrix, the seven arm op specs (including the
PR #1187 ``scale_ach`` scope on ``ach_150_supply``), the 32-field pre-stage
plan, the pilot cell and frozen §7 thresholds, entrypoint argv, the worker's
arm application and output contract, and the readout's coverage / contrast /
pilot aggregation.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_DIR = ROOT / "campaigns" / "contam" / "phase2_cruise_contrasts_01"
DESIGN_DIR = CAMPAIGN_DIR / "design"
DESIGN_PATH = DESIGN_DIR / "phase2_cruise_contrasts_design.json"
POOLS_PATH = CAMPAIGN_DIR / "source_pools.json"
CAMPAIGN_PATH = CAMPAIGN_DIR / "campaign.json"

HULLS = [
    "expedition_cruise_450",
    "classic_cruise_1900",
    "spirit_cruise_3000",
    "mega_cruise_5000",
]
ARMS = [
    "baseline", "oa_050", "filter_090", "oa_050_filter_090",
    "eq_gain_025_filter", "ach_150_supply", "oa_080",
]
SEEDS = list(range(1, 21))
PILOT_BLOCK = "mega_cruise_5000_e_baseline"

# Manifest §3 hull panel: zones, volume m³, path-map entries, supply / duty-0 groups.
HULL_PANEL = {
    "expedition_cruise_450": (47, 19_358.98, 343, 9, 13),
    "classic_cruise_1900": (79, 56_403.33, 835, 13, 17),
    "spirit_cruise_3000": (115, 84_704.15, 1302, 17, 28),
    "mega_cruise_5000": (192, 403_554.55, 2623, 20, 63),
}
# Manifest §5 materialized pools (large_venue 4, sanitary_branch 3, remote_weak 3).
POOLS = {
    "expedition_cruise_450": [
        "MainDining", "TheaterLng", "CasualDining", "ExpedLounge",
        "HD_5P_F", "HD_5P_M", "HD_7S_F", "PoolDeck", "Library", "MedBay",
    ],
    "classic_cruise_1900": [
        "MainTheater", "MainDining_L", "MainDining_U", "LidoBuffet",
        "HD_4M_M", "HD_5L_F", "HD_9L_F", "PoolDeck", "IsolRoom", "Bridge",
    ],
    "spirit_cruise_3000": [
        "MainTheater", "MainDining_L", "MainDining_U", "Promenade",
        "HD_4M_F_1", "HD_4M_F_2", "HD_5L_M", "SportsDeck", "AftPool", "MainPool",
    ],
    "mega_cruise_5000": [
        "Royal_Promenade", "Main_Theater", "CentralPark", "Windjammer",
        "HD_3D_F", "HD_3D_M", "HD_5P_F_1", "Sports_Court", "Waterpark", "Aqua_Theater",
    ],
}
# Manifest §2.2 arm op specs (fleet-compare grammar) and AHS gains r = (1-f)(1-eta).
ARM_OPS = {
    "baseline": [],
    "oa_050": [{"op": "set_oa", "value": 0.5, "scope": "supply_groups"}],
    "filter_090": [{"op": "set_filter", "value": 0.9}],
    "oa_050_filter_090": [
        {"op": "set_oa", "value": 0.5, "scope": "supply_groups"},
        {"op": "set_filter", "value": 0.9},
    ],
    "eq_gain_025_filter": [{"op": "set_filter", "value": 0.6875}],
    "ach_150_supply": [{"op": "scale_ach", "factor": 1.5, "scope": "supply_groups"}],
    "oa_080": [{"op": "set_oa", "value": 0.8, "scope": "supply_groups"}],
}
ARM_GAIN = {
    "baseline": 0.40, "oa_050": 0.25, "filter_090": 0.08, "oa_050_filter_090": 0.05,
    "eq_gain_025_filter": 0.25, "ach_150_supply": 0.40, "oa_080": 0.10,
}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_mod = _load("contam_phase2_build", DESIGN_DIR / "build.py")
cell_mod = _load("contam_phase2_cell", CAMPAIGN_DIR / "cell.py")
entry_mod = _load("contam_phase2_entry", CAMPAIGN_DIR / "entry.py")
readout_mod = _load("contam_phase2_readout", CAMPAIGN_DIR / "readout.py")


@pytest.fixture(scope="module")
def design() -> dict[str, Any]:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pools_doc() -> dict[str, Any]:
    return json.loads(POOLS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def campaign() -> dict[str, Any]:
    return json.loads(CAMPAIGN_PATH.read_text(encoding="utf-8"))


def _trajectory_cells(campaign_doc: dict[str, Any]) -> set[tuple[str, str, str, int]]:
    cells = set()
    for block in campaign_doc["blocks"].values():
        args = block.get("args") or {}
        if args.get("mode") != "trajectory":
            continue
        for seed in block["seeds"]:
            cells.add((str(args["hull"]), str(args["lane"]), str(args["arm"]), int(seed)))
    return cells


class TestFrozenDesign:
    def test_generated_artifacts_match_builder(self, design, pools_doc, campaign) -> None:
        assert build_mod.build_design() == design
        assert build_mod._campaign_spec() == campaign
        assert pools_doc["design_id"] == design["design_id"]
        assert pools_doc["source_pools"] == {
            hull: payload["pool"] for hull, payload in design["source_pools"].items()
        }

    def test_design_freezes_manifest_identity(self, design) -> None:
        assert design["design_id"] == "contam_phase2_cruise_contrasts_01"
        assert design["status"] == "frozen_before_first_cell"
        assert design["manifest"] == "docs/proposals/contam_phase2_scope_manifest.md"
        assert design["manifest_pr"] == 1183
        assert design["manifest_amendment_pr"] == 1185
        assert design["scale_ach_scope_pr"] == 1187
        assert design["baseline_sha"]["registry_baseline_sha"] == "f5d32477"
        assert len(design["baseline_sha"]["repinned_main_sha"]) == 40
        assert design["hulls"] == HULLS
        assert design["bundled_p_lane_hulls"] == HULLS
        assert design["p_lane_arms"] == ["baseline"]
        assert design["arm_order"] == ARMS

    def test_tracer_protocol_is_phase1_verbatim(self, design) -> None:
        tracer = design["tracer"]
        assert tracer["mass_per_seed"] == pytest.approx(1_000_000.0)
        assert tracer["natural_decay_rate"] == pytest.approx(0.0)
        assert tracer["filter_efficiency"] == pytest.approx(0.5)
        assert tracer["baseline_oa_fraction"] == pytest.approx(0.2)
        assert tracer["unchanged_from_phase1"] is True
        assert set(tracer["timing_patterns"]) == {"t0_pulse", "t0_t1_split"}
        assert design["matrix"]["epochs"] == 12
        assert design["matrix"]["epoch_hours"] == pytest.approx(1.0)

    @pytest.mark.parametrize("hull", HULLS)
    def test_hull_panel_recomputes_from_platform_jsons(self, design, hull) -> None:
        zones, volume, entries, supply, duty0 = HULL_PANEL[hull]
        panel = design["hull_panel"][hull]
        assert panel["zones"] == zones
        assert panel["volume_m3"] == pytest.approx(volume, abs=0.005)
        assert panel["path_map_entries"] == entries
        assert panel["supply_groups"] == supply
        assert panel["duty0_groups"] == duty0
        assert panel["hvac_groups"] == supply + duty0
        assert panel["sanitary_zones"] == duty0
        assert panel["supply_oa_fractions"] == pytest.approx([0.2])
        assert panel["duty0_oa_fractions"] == pytest.approx([1.0])
        assert panel["duty0_ach_values"] == pytest.approx([19.2])
        assert panel["r_base"] == pytest.approx([0.4])
        assert panel["dc04_r_low"] == pytest.approx([0.1])
        assert panel["committed_prj"] is True
        assert design["source_pools"][hull]["zone_count"] == zones

    def test_hull_panel_totals_match_manifest(self, design) -> None:
        panel = design["hull_panel"]
        assert sum(row["zones"] for row in panel.values()) == 433
        assert sum(row["volume_m3"] for row in panel.values()) == pytest.approx(564_021.01, abs=0.05)
        assert sum(row["path_map_entries"] for row in panel.values()) == 5103
        assert sum(row["supply_groups"] for row in panel.values()) == 59
        assert sum(row["duty0_groups"] for row in panel.values()) == 121

    @pytest.mark.parametrize("hull", HULLS)
    def test_source_pools_are_the_manifest_pools(self, design, hull) -> None:
        pool = design["source_pools"][hull]["pool"]
        assert [item["id"] for item in pool] == POOLS[hull]
        assert [item["category"] for item in pool] == (
            ["large_venue"] * 4 + ["sanitary_branch"] * 3 + ["remote_weak"] * 3
        )
        assert design["source_pools"][hull]["counts"] == {
            "large_venue": 4, "sanitary_branch": 3, "remote_weak": 3,
        }
        for item in pool:
            if item["category"] == "sanitary_branch":
                assert item["type"] == "Sanitary"
            if item["category"] == "remote_weak":
                assert item["type"] != "Sanitary"
                assert (not item["served"]) or item["adjacency_degree"] <= 1

    def test_expedition_pool_is_identical_to_phase1(self, design) -> None:
        phase1 = json.loads(
            (ROOT / "campaigns" / "contam" / "phase1_hvac_tracer_01" / "source_pools.json")
            .read_text(encoding="utf-8")
        )
        assert design["source_pools"]["expedition_cruise_450"]["pool"] == (
            phase1["source_pools"]["expedition_cruise_450"]
        )

    def test_seed_mapping_is_the_manifest_rule(self, design) -> None:
        grid = design["seed_mapping"]["grid"]
        assert set(grid) == {str(seed) for seed in SEEDS}
        for seed in SEEDS:
            k = seed - 1
            expected_timing = "t0_pulse" if k % 2 == 0 else "t0_t1_split"
            for hull in HULLS:
                row = grid[str(seed)][hull]
                assert row["k"] == k
                assert row["timing_pattern"] == expected_timing
                assert row["pool_index"] == (k // 2) % 10

    def test_seeds_enumerate_each_pool_zone_with_both_timings(self, design) -> None:
        for hull in HULLS:
            realizations = {
                (design["seed_mapping"]["grid"][str(seed)][hull]["pool_index"],
                 design["seed_mapping"]["grid"][str(seed)][hull]["timing_pattern"])
                for seed in SEEDS
            }
            assert len(realizations) == 20
            assert {index for index, _timing in realizations} == set(range(10))

    def test_arm_specs_match_manifest_exactly(self, design) -> None:
        assert set(design["arms"]) == set(ARMS)
        for arm, ops in ARM_OPS.items():
            assert design["arms"][arm]["ops"] == ops
            assert design["arms"][arm]["declared_gain_r"] == pytest.approx(ARM_GAIN[arm])
            f = design["arms"][arm]["supply_oa_fraction"]
            eta = design["arms"][arm]["filter_efficiency"]
            assert (1.0 - f) * (1.0 - eta) == pytest.approx(ARM_GAIN[arm])

    def test_scale_ach_scope_covers_dc04_arm_shapes(self, design) -> None:
        a_ops = design["arms"]["ach_150_supply"]["ops"]
        assert a_ops == [{"op": "scale_ach", "factor": 1.5, "scope": "supply_groups"}]
        assert design["arms"]["ach_150_supply"]["turnover_factor"] == pytest.approx(1.5)
        assert design["arms"]["oa_080"]["ops"][0]["scope"] == "supply_groups"
        assert design["contrasts"]["DC04"]["alpha"] == pytest.approx(1.5)
        for arm in ("oa_050", "oa_050_filter_090", "oa_080"):
            assert all(op.get("scope") != "all_groups" for op in design["arms"][arm]["ops"])

    def test_matrix_is_1200_trajectories_in_60_blocks(self, design) -> None:
        matrix = design["matrix"]
        assert matrix["primary_trajectories"] == 1120
        assert matrix["p_contrast_trajectories"] == 80
        assert matrix["total_trajectories"] == 1200
        assert matrix["hourly_steps"] == 14_400
        assert matrix["blocks"] == 60
        assert matrix["primary_blocks"] == 56
        assert matrix["p_blocks"] == 4
        assert matrix["array_size_per_block"] == 20
        assert design["execution"]["trajectory_blocks"] == 60
        assert design["execution"]["trajectory_array_children"] == 1200
        assert design["execution"]["total_array_children"] == 1200

    def test_field_prestage_enumerates_32_fields(self, design) -> None:
        prestage = design["execution"]["field_cache_prestage"]
        assert prestage["mode"] == "local_only"
        assert prestage["aws_submit"] is False
        assert prestage["field_count"] == 32
        assert len(prestage["fields"]) == 32
        keys = [row["key"] for row in prestage["fields"]]
        assert len(set(keys)) == 32
        e_fields = [row for row in prestage["fields"] if row["lane"] == "E"]
        p_fields = [row for row in prestage["fields"] if row["lane"] == "P"]
        assert len(e_fields) == 28
        assert len(p_fields) == 4
        assert {row["arm"] for row in p_fields} == {"baseline"}
        assert all(row["fresh_solve_required"] for row in prestage["fields"])
        assert [row["key"] for row in prestage["fields"] if row["phase1_reusable_control"]] == [
            "expedition_cruise_450:E:baseline", "expedition_cruise_450:P:baseline",
        ]
        for row in e_fields:
            assert row["ops"] == ARM_OPS[row["arm"]]
        assert prestage["s3_uri"] == (
            "s3://crusherbucket-994254241749-us-east-1-an/"
            "campaign/contam_phase2_cruise_contrasts_01/field_cache/field_cache.json"
        )
        assert prestage["trajectory_consumer_arg"] == "--field-cache-uri"

    def test_contamx_provenance_is_the_phase1_binary(self, design) -> None:
        contamx = design["execution"]["field_cache_prestage"]["contamx"]
        assert contamx["version"] == "3.4.0.3 64 bit"
        assert contamx["binary_sha256"] == (
            "d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b"
        )
        assert contamx["tarball_sha256"] == (
            "3612798dff9a4f1ea4f0279c4c7b526b244b88875dea425fafd868f3570df4fa"
        )
        assert contamx["download_url"] == "https://www.nist.gov/document/contam-x-3403-linux-64bittargz"

    def test_pilot_and_thresholds_are_frozen(self, design) -> None:
        pilot = design["pilot"]
        assert pilot["hull"] == "mega_cruise_5000"
        assert pilot["lane"] == "E"
        assert pilot["arm"] == "baseline"
        assert pilot["seeds"] == SEEDS
        assert pilot["trajectory_block"] == PILOT_BLOCK
        thresholds = design["thresholds"]
        assert thresholds["pilot_succeeded_cells"] == 20
        assert thresholds["blocked_engine_fallback_count"] == 0
        assert thresholds["commissioned_field_solve_seconds_max"] == pytest.approx(30.0)
        assert thresholds["trajectory_wall_p95_seconds_max"] == pytest.approx(60.0)
        assert thresholds["array_wall_clock_minutes_max"] == pytest.approx(30.0)
        assert thresholds["cpu_hours_max"] == pytest.approx(1.0)
        assert thresholds["peak_rss_mib_max"] == 1792
        assert thresholds["artifact_bytes_max"] == 25 * 1024 * 1024
        assert thresholds["dropped_endpoint_count"] == 0
        assert thresholds["unknown_real_zone_count"] == 0
        assert thresholds["alias_collision_count"] == 0
        assert thresholds["full_panel_cpu_hours_extrapolated_max"] == pytest.approx(1.697352)
        assert thresholds["full_panel_artifact_bytes_extrapolated_max"] == 126_060_180
        assert design["acceptance_gates"]["stop_after_canary"] is True
        assert design["execution"]["image_digest_pinned"] is False
        assert design["execution"]["pin_image_digest_before_submit"] is True

    def test_dc03_is_a_fixture_with_zero_trajectories(self, design) -> None:
        dc03 = design["contrasts"]["DC03"]
        assert dc03["trajectories"] == 0
        assert dc03["fixture"].startswith("tests/test_contam_analytic_fixtures.py::")
        assert (ROOT / dc03["fixture"].split("::")[0]).is_file()
        assert "DC03" not in {arm for spec in design["arms"].values() for arm in spec["serves"]}


class TestCampaignRegistration:
    def test_campaign_identity_and_prefix(self, campaign) -> None:
        assert campaign["name"] == "contam_phase2_cruise_contrasts_01"
        assert campaign["pathogen"] == "contam"
        assert campaign["manifest"].endswith("phase2_cruise_contrasts_design.json")
        assert campaign["s3_prefix"] == "campaign/contam_phase2_cruise_contrasts_01/"
        assert campaign["queue"] == "picard-campaign-queue"
        assert campaign["readout"].endswith("phase2_cruise_contrasts_01/readout.py")
        assert campaign["resources"] == {"vcpu": "1", "memory": "2048"}
        assert campaign["epochs"] == 12

    def test_blocks_cover_matrix_without_field_cache_block(self, campaign) -> None:
        assert "field_cache" not in campaign["blocks"]
        cells = _trajectory_cells(campaign)
        expected = {
            (hull, lane, arm, seed)
            for hull in HULLS
            for lane, arms in (("N", ARMS), ("E", ARMS), ("P", ["baseline"]))
            for arm in arms
            for seed in SEEDS
        }
        assert cells == expected
        assert len(cells) == 1200
        assert len(campaign["blocks"]) == 60

    def test_block_names_args_and_array_sizes(self, campaign) -> None:
        for name, block in campaign["blocks"].items():
            args = block["args"]
            assert name == f"{args['hull']}_{args['lane'].lower()}_{args['arm']}"
            assert args["mode"] == "trajectory"
            assert args["hull"] in HULLS
            assert args["lane"] in {"N", "E", "P"}
            assert args["arm"] in ARMS
            assert block["worker"].endswith("phase2_cruise_contrasts_01/cell.py")
            assert block["artifact"] == "cell_{seed}.json"
            assert block["seeds"] == SEEDS
        assert PILOT_BLOCK in campaign["blocks"]
        p_blocks = [n for n, b in campaign["blocks"].items() if b["args"]["lane"] == "P"]
        assert sorted(p_blocks) == sorted(f"{hull}_p_baseline" for hull in HULLS)


class TestEntryArgv:
    def test_local_trajectory_uses_inline_field_and_names_arm(self, campaign) -> None:
        block = campaign["blocks"]["mega_cruise_5000_e_ach_150_supply"]
        args = SimpleNamespace(epochs=12, epoch_hours=1.0, local=True, s3_prefix=None)
        argv, artifact = entry_mod.build_argv(args, block, 7, Path("/tmp/out"))
        text = " ".join(argv)
        assert "--mode trajectory" in text
        assert "--hull mega_cruise_5000" in text
        assert "--lane E" in text
        assert "--arm ach_150_supply" in text
        assert "--seed 7" in text
        assert "--inline-field" in text
        assert artifact.name == "cell_7.json"

    def test_batch_trajectory_reads_field_cache_uri(self, campaign) -> None:
        block = campaign["blocks"][PILOT_BLOCK]
        args = SimpleNamespace(
            epochs=12, epoch_hours=1.0, local=False,
            s3_prefix="s3://bucket/campaign/contam_phase2_cruise_contrasts_01/",
        )
        argv, _artifact = entry_mod.build_argv(args, block, 7, Path("/tmp/out"))
        text = " ".join(argv)
        assert "--field-cache-uri s3://bucket/campaign/contam_phase2_cruise_contrasts_01/field_cache/field_cache.json" in text
        assert "--arm baseline" in text
        assert "--inline-field" not in text


@pytest.fixture(scope="module")
def mega() -> tuple[dict[str, Any], dict[str, Any], dict[str, float]]:
    spatial, airflow = cell_mod._load_platform("mega_cruise_5000")
    return spatial, airflow, cell_mod._zone_volumes(spatial)


class TestCellWorkerContracts:
    def test_baseline_arm_is_a_no_op_copy(self, design, mega) -> None:
        _spatial, airflow, volumes = mega
        mutated, record = cell_mod._apply_arm(design, airflow, volumes, "baseline")
        assert mutated == airflow
        assert mutated is not airflow
        assert record["edits"] == []
        assert record["filter_efficiency"] == pytest.approx(0.5)
        assert record["oa_fraction"] == pytest.approx(0.2)
        assert record["realized_groups"]["groups_changed"] == 0
        assert record["realized_gain_r_supply"] == pytest.approx([0.4])
        assert record["dc04_matched_removal"] is None

    @pytest.mark.parametrize("arm", ["oa_050", "oa_050_filter_090", "ach_150_supply", "oa_080"])
    def test_group_ops_change_only_the_20_supply_groups(self, design, mega, arm) -> None:
        _spatial, airflow, volumes = mega
        _mutated, record = cell_mod._apply_arm(design, airflow, volumes, arm)
        groups = record["realized_groups"]
        assert groups["supply_groups"] == 20
        assert groups["duty0_groups"] == 63
        assert groups["groups_changed"] == 20
        assert groups["supply_groups_changed"] == 20
        assert groups["duty0_groups_changed"] == 0
        assert groups["groups_unchanged"] == 63
        assert record["realized_gain_r_supply"] == pytest.approx([ARM_GAIN[arm]])

    @pytest.mark.parametrize("arm", ["filter_090", "eq_gain_025_filter"])
    def test_filter_ops_change_no_group(self, design, mega, arm) -> None:
        _spatial, airflow, volumes = mega
        mutated, record = cell_mod._apply_arm(design, airflow, volumes, arm)
        assert mutated == airflow
        assert record["realized_groups"]["groups_changed"] == 0
        assert record["filter_efficiency"] == pytest.approx(design["arms"][arm]["filter_efficiency"])
        assert record["realized_gain_r_supply"] == pytest.approx([ARM_GAIN[arm]])

    def test_ach_150_supply_scales_turnover_and_passes_dc04_feasibility(self, design, mega) -> None:
        _spatial, airflow, volumes = mega
        mutated, record = cell_mod._apply_arm(design, airflow, volumes, "ach_150_supply")
        before = {g["id"]: g for g in airflow["hvac_zones"]}
        for group in mutated["hvac_zones"]:
            prior = before[group["id"]]
            if float(prior.get("hvac_duty", airflow["hvac_duty"])) > 0.0:
                assert group["ach"] == pytest.approx(1.5 * prior["ach"])
            else:
                assert group["ach"] == pytest.approx(prior["ach"])
        assert record["edits"] == ["ach x1.5 on supply groups; preserved 63 duty-0 group(s)"]
        dc04 = record["dc04_matched_removal"]
        assert dc04["alpha"] == pytest.approx(1.5)
        assert dc04["supply_groups"] == 20
        assert dc04["r_low_min"] == pytest.approx(0.1)
        assert dc04["r_low_max"] == pytest.approx(0.1)
        assert dc04["feasible"] is True

    def test_dc04_fails_closed_when_r_low_leaves_unit_interval(self, design) -> None:
        airflow = {
            "oa_fraction": 0.2, "hvac_duty": 0.5,
            "hvac_zones": [{"id": "weak", "rooms": ["A"], "ach": 6.0, "oa_fraction": 0.5}],
            "cross_zone_links": [], "adjacency": [],
        }
        with pytest.raises(SystemExit, match="DC04 matched-removal infeasible"):
            cell_mod._apply_arm(design, airflow, {"A": 100.0}, "ach_150_supply")

    def test_equal_gain_arms_share_the_supply_gain(self, design, mega) -> None:
        _spatial, airflow, volumes = mega
        _m_o, o = cell_mod._apply_arm(design, airflow, volumes, "oa_050")
        _m_g, g = cell_mod._apply_arm(design, airflow, volumes, "eq_gain_025_filter")
        assert o["realized_gain_r_supply"] == pytest.approx(g["realized_gain_r_supply"])
        assert o["filter_efficiency"] != pytest.approx(g["filter_efficiency"])

    def test_native_engine_receives_arm_filter_and_mutated_airflow(self, design, mega) -> None:
        spatial, airflow, volumes = mega
        mutated, record = cell_mod._apply_arm(design, airflow, volumes, "oa_050_filter_090")
        engine = cell_mod._native_engine(spatial, mutated, 1.0, record["filter_efficiency"])
        assert engine.filter_efficiency == pytest.approx(0.9)
        assert engine.natural_decay_rate == pytest.approx(0.0)
        assert engine.clock.hours_per_epoch == pytest.approx(1.0)

    def test_p_lane_rejects_json_only_mutations(self, design) -> None:
        with pytest.raises(SystemExit, match="baseline-only"):
            cell_mod._check_lane_arm(design, "P", "oa_080")
        cell_mod._check_lane_arm(design, "P", "baseline")
        cell_mod._check_lane_arm(design, "E", "oa_080")

    def test_unknown_arm_is_rejected(self, design) -> None:
        with pytest.raises(SystemExit, match="unknown arm"):
            cell_mod._arm_spec(design, "bogus")

    def test_stale_cached_field_is_rejected(self, design, mega) -> None:
        _spatial, airflow, volumes = mega
        _mutated, record = cell_mod._apply_arm(design, airflow, volumes, "oa_080")
        stale = {"ops": [], "filter_efficiency": 0.5, "realized_groups": []}
        with pytest.raises(SystemExit, match="stale field"):
            cell_mod._check_field_matches_arm(stale, "mega_cruise_5000:E:oa_080", record)

    def test_matching_cached_field_is_accepted(self, design, mega) -> None:
        _spatial, airflow, volumes = mega
        _mutated, record = cell_mod._apply_arm(design, airflow, volumes, "oa_080")
        field = {
            "ops": record["ops"],
            "filter_efficiency": record["filter_efficiency"],
            "realized_groups": record["realized_groups"]["groups"],
        }
        cell_mod._check_field_matches_arm(field, "mega_cruise_5000:E:oa_080", record)

    def test_seed_source_uses_frozen_pool_index(self, design) -> None:
        zone, timing, category, index = cell_mod._seed_source(design, "mega_cruise_5000", 3)
        row = design["seed_mapping"]["grid"]["3"]["mega_cruise_5000"]
        item = design["source_pools"]["mega_cruise_5000"]["pool"][row["pool_index"]]
        assert zone == item["id"] == "Main_Theater"
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
    HULL = "mega_cruise_5000"

    def _cell(self, lane: str, arm: str, seed: int, bv: float, zones: dict[str, float] | None = None) -> dict[str, Any]:
        zone_stats = {
            zone: {
                "auc_concentration_per_m3_h": value,
                "first_above_floor_h": None if value == 0.0 else 1.0,
                "time_to_peak_h": None if value == 0.0 else 2.0,
            }
            for zone, value in (zones or {"Royal_Promenade": bv, "Main_Theater": bv / 2.0, "Waterpark": 0.0}).items()
        }
        return {
            "schema": cell_mod.SCHEMA_CELL,
            "design_id": "contam_phase2_cruise_contrasts_01",
            "hull": self.HULL,
            "lane": lane,
            "arm": arm,
            "seed": seed,
            "source_zone": "Royal_Promenade",
            "source_category": "large_venue",
            "tracer_mass": 1_000_000.0,
            "timing_pattern": "t0_pulse" if seed % 2 else "t0_t1_split",
            "metrics": {
                "retained_fraction_curve": [bv / 10.0],
                "volume_weighted_concentration_burden_h": bv,
                "concentration_auc_sum_per_m3_h": bv * 3.0,
                "peak_concentration_per_m3": bv * 4.0,
                "source_zone_final_mass": bv,
                "zone_stats": zone_stats,
            },
            "path_flow_summary": {
                "path_count": 2, "total_flow_m3h": 100.0 + seed, "ducted_flow_m3h": 50.0,
                "by_path_type": {"passive": {"count": 1.0, "flow_m3h": 40.0 + seed, "ducted_flow_m3h": 0.0}},
            },
            "ahs_flow_table": [{"ahs_nr": 1, "ahs_supply_m3h": 10.0}] if lane != "N" else [],
            "field_audit": {"dropped_endpoint_count": 0, "unknown_real_zone_count": 0, "alias_collision_count": 0},
            "field_source": "field_cache" if lane != "N" else "native_layout",
            "timing": {"trajectory_seconds": 1.5, "field_seconds": 0.0, "peak_rss_mib": 100.0},
        }

    BV = {
        "baseline": 0.40, "oa_050": 0.25, "filter_090": 0.08, "oa_050_filter_090": 0.05,
        "eq_gain_025_filter": 0.25, "ach_150_supply": 0.20, "oa_080": 0.10,
    }

    def _panel(self, lanes: tuple[str, ...] = ("N", "E"), e_scale: float = 1.0) -> list[tuple[str, dict[str, Any], int]]:
        cells = []
        for lane in lanes:
            scale = e_scale if lane == "E" else 1.0
            for arm, bv in self.BV.items():
                for seed in SEEDS:
                    cells.append((f"{lane}{arm}{seed}", self._cell(lane, arm, seed, bv * scale), 1000))
        return cells

    def test_coverage_counts_against_the_1200_cell_matrix(self, campaign, design) -> None:
        report = readout_mod.build_report(self._panel(), campaign, design)
        assert report["coverage"]["expected_cells"] == 1200
        assert report["coverage"]["observed_cells"] == 280
        assert report["coverage"]["missing_cells"] == 920
        assert report["coverage"]["blocked_engine_fallback_count"] == 0
        assert len(report["coverage"]["blocks"]) == 60

    def test_dc01_dc02_dc04_dc05_contrasts(self, campaign, design) -> None:
        report = readout_mod.build_report(self._panel(e_scale=0.9), campaign, design)
        dc01 = report["dc01_ordering_control"][self.HULL]["N"]
        assert dc01["b_v_ordering_pass"] == 20
        assert dc01["b_v_ordering_violations"] == []
        dc02 = report["dc02_equal_gain_control"][self.HULL]["N"]
        assert dc02["b_v_h"]["mean"] == pytest.approx(0.0)
        assert dc02["exact_zero_seeds"] == 20
        dc04 = report["dc04_matched_removal"][self.HULL]["N"]
        assert dc04["A_minus_R"]["b_v_h"]["mean"] == pytest.approx(0.10)
        assert dc04["reduction_R_A"]["mean"] == pytest.approx(0.5)
        assert dc04["reduction_R_R"]["mean"] == pytest.approx(0.75)
        assert dc04["reduction_gap_A_minus_R"]["mean"] == pytest.approx(-0.25)
        assert dc04["edison_tie_band_5pp_report_only"]["selector"] is False
        parity = report["dc05_arm_effect_parity"][self.HULL]["oa_080"]
        assert parity["n"] == 20
        assert parity["sign_agreement"] == 20
        assert parity["N_effect_minus_E_effect"]["mean"] == pytest.approx(-0.03)
        lane = report["lane_contrasts"][self.HULL]["N_minus_E"]["baseline"]["b_v_h"]
        assert lane["n"] == 20
        assert lane["mean"] == pytest.approx(0.04)

    def test_dc01_violation_is_listed_not_hidden(self, campaign, design) -> None:
        cells = self._panel(lanes=("N",))
        cells = [
            (key, payload, size) if not (payload["arm"] == "filter_090" and payload["seed"] == 5)
            else (key, {**payload, "metrics": {**payload["metrics"], "volume_weighted_concentration_burden_h": 0.30}}, size)
            for key, payload, size in cells
        ]
        dc01 = readout_mod.build_report(cells, campaign, design)["dc01_ordering_control"][self.HULL]["N"]
        assert dc01["b_v_ordering_pass"] == 19
        assert dc01["b_v_ordering_violations"] == [{"seed": 5, "pairs": ["filter_090>oa_050"]}]

    def test_dc07_splits_local_and_remote_receptors(self, campaign, design) -> None:
        report = readout_mod.build_report(self._panel(lanes=("N",)), campaign, design)
        row = report["dc07_source_receptor_responses"][f"{self.HULL}:N:baseline"]["large_venue"]
        assert row["cells"] == 20
        assert row["local_e_i_per_emitted"]["n"] + row["remote_e_i_per_emitted"]["n"] == 40
        assert row["never_reached_receptors"] == 20
        assert row["first_arrival_h"]["p50"] == pytest.approx(1.0)

    def test_pilot_gate_with_field_cache_and_extrapolation(self, campaign, design) -> None:
        cells = [(f"e{seed}", self._cell("E", "baseline", seed, 0.4), 30_000) for seed in SEEDS]
        field_cache = {
            "fields": {
                "mega_cruise_5000:E:baseline": {"field_seconds": 0.5},
                "spirit_cruise_3000:E:oa_080": {"field_seconds": 0.9},
            },
            "phase1_control": {"fields": []},
        }
        report = readout_mod.build_report(cells, campaign, design, field_cache=field_cache, array_wall_clock_minutes=2.0)
        checks = report["pilot_gate"]["checks"]
        assert report["pilot_gate"]["block"] == PILOT_BLOCK
        assert checks["seeds_complete"] is True
        assert checks["commissioned_field_solve_seconds"] == pytest.approx(0.5)
        assert checks["max_field_solve_seconds_all_fields"] == pytest.approx(0.9)
        assert checks["trajectory_wall_p95_seconds"] == pytest.approx(1.5)
        assert checks["artifact_bytes_total"] == 600_000
        assert checks["full_panel_cpu_hours_extrapolated"] == pytest.approx(1200 * 1.5 / 3600.0)
        assert checks["full_panel_artifact_bytes_extrapolated"] == pytest.approx(36_000_000)
        assert checks["go"] is True

    def test_pilot_gate_is_not_go_without_full_seed_set(self, campaign, design) -> None:
        cells = [("e1", self._cell("E", "baseline", 1, 0.4), 100)]
        report = readout_mod.build_report(cells, campaign, design, array_wall_clock_minutes=1.0)
        assert report["pilot_gate"]["checks"]["seeds_complete"] is False
        assert report["pilot_gate"]["checks"]["go"] is False

    def test_pilot_gate_fails_on_extrapolation_bound(self, campaign, design) -> None:
        cells = [(f"e{seed}", self._cell("E", "baseline", seed, 0.4), 200_000) for seed in SEEDS]
        field_cache = {"fields": {"mega_cruise_5000:E:baseline": {"field_seconds": 0.5}}}
        report = readout_mod.build_report(cells, campaign, design, field_cache=field_cache, array_wall_clock_minutes=2.0)
        checks = report["pilot_gate"]["checks"]
        assert checks["full_panel_artifact_bytes_extrapolated"] == pytest.approx(240_000_000)
        assert checks["go"] is False
