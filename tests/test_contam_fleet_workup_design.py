"""Pre-results design of the fleet native-vs-ContamX workup.

Ledger ``CONTAM-FLEET-WORKUP-PROTOCOL-01``. These tests lock the planning
rules on small fixtures and the committed artifacts offline; no field is
solved and no solver is timed.
"""

from __future__ import annotations

import csv
import io
import json

import pytest

from tools import contam_fleet_workup_design as design

_PLENUM_REASON = "sealed life-support"


def _airflow(groups):
    return {
        "oa_fraction": 0.2,
        "hvac_duty": 0.5,
        "hvac_zones": groups,
        "ambient_openings": [
            {"zone": "A", "type": "door", "exchange_m3h": 10.0,
             "wind_speed_m_s": 2.0},
            {"zone": "B", "type": "door", "exchange_m3h": 5.0},
        ],
        "cross_zone_links": [{}],
        "adjacency": [{}, {}],
    }


def _facts(groups, overrides=None):
    spatial = {"zones": [{"id": "A"}, {"id": "B"}]}
    return design.hull_facts(spatial, _airflow(groups), overrides or {})


_MIXED = [
    {"id": "S1", "ach": 6.0, "oa_fraction": 0.4},
    {"id": "S2", "ach": 6.0, "oa_fraction": 1.0},
    {"id": "X1", "ach": 10.0, "oa_fraction": 1.0, "hvac_duty": 0.0},
]


def _by_status(rows):
    out = {}
    for row in rows:
        out.setdefault(row["planned_status"], []).append(row)
    return out


def test_group_facts_count_supply_recirculating_and_export_mismatch():
    facts = _facts(_MIXED)
    assert facts["hvac_group_count"] == 3
    assert facts["supply_group_count"] == 2
    assert facts["duty0_group_count"] == 1
    assert facts["recirculating_supply_group_count"] == 1
    # Export resolves the pack default 0.2 for both supply groups.
    assert facts["export_oa_differs_group_count"] == 2
    assert facts["cross_ventilated_opening_count"] == 1


def test_override_map_removes_export_mismatch():
    facts = _facts(_MIXED, {"oa_fraction": {"S1": 0.4, "_default": 1.0}})
    assert facts["export_oa_differs_group_count"] == 0


def test_default_wind_is_the_exporter_default():
    facts = _facts(_MIXED)
    assert facts["authored_wind_speed_m_s"] == 1.0
    assert facts["authored_wind_direction_deg"] == 0.0
    assert facts["wall_azimuth_basis"] == "display_coordinate_heuristic"


def test_ordinary_hull_rows():
    rows = design.plan_rows("h", _facts(_MIXED))
    assert len(rows) == 2 * len(design.SETTINGS) + 2
    assert len({r["row_id"] for r in rows}) == len(rows)
    grouped = _by_status(rows)
    assert design.NOT_APPLICABLE not in grouped
    nonresponse = grouped[design.NONRESPONSE]
    assert len(nonresponse) == 7
    assert {r["lane"] for r in nonresponse} == {design.LANE_NATIVE}
    assert {r["measured_reps"] for r in nonresponse} == {0}


def test_weather_on_contamx_is_one_sided_not_matched():
    rows = design.plan_rows("h", _facts(_MIXED))
    weather = [
        r for r in rows
        if r["family"].startswith("weather")
        and r["lane"] == design.LANE_COMMISSIONED
    ]
    assert {r["contrast_type"] for r in weather} == {"one_sided_structural"}
    assert {r["planned_status"] for r in weather} == {design.EXECUTE}


def test_operational_rows_are_matched_in_both_lanes():
    rows = design.plan_rows("h", _facts(_MIXED))
    duty = [r for r in rows if r["setting_id"] == "supply_duty_x0p5"]
    assert [r["lane"] for r in duty] == [
        design.LANE_NATIVE, design.LANE_COMMISSIONED,
    ]
    assert {r["contrast_type"] for r in duty} == {"matched_perturbation"}


def test_sealed_hull_weather_is_not_applicable_in_both_lanes():
    facts = _facts(_MIXED, {
        "life_support_plenum": {"enabled": True},
        "relative_wind_speed_m_s": 0.0,
    })
    rows = design.plan_rows("h", facts)
    weather = [r for r in rows if r["family"].startswith("weather")]
    assert len(weather) == 14
    assert {r["planned_status"] for r in weather} == {design.NOT_APPLICABLE}
    assert all(_PLENUM_REASON in r["reason"] for r in weather)
    assert {r["contamx_solves_planned"] for r in weather} == {0}


def test_once_through_hull_has_no_outdoor_air_arm():
    facts = _facts([{"id": "S", "ach": 6.0, "oa_fraction": 1.0}])
    rows = design.plan_rows("h", facts)
    status = {r["setting_id"]: r["planned_status"] for r in rows
              if r["lane"] == design.LANE_NATIVE}
    assert status["supply_oa_x0p5"] == design.NOT_APPLICABLE
    assert status["supply_recirc_x0p5"] == design.NOT_APPLICABLE
    assert status["supply_duty_x0p5"] == design.EXECUTE


def test_hull_without_supply_groups_has_no_operational_arm():
    facts = _facts([{"id": "X", "ach": 6.0, "oa_fraction": 1.0,
                     "hvac_duty": 0.0}])
    rows = design.plan_rows("h", facts)
    operational = [r for r in rows if r["family"].startswith("operational")]
    assert {r["planned_status"] for r in operational} == {
        design.NOT_APPLICABLE,
    }


def test_separate_baselines_are_single_rows():
    rows = design.plan_rows("h", _facts(_MIXED))
    for lane in (design.LANE_AS_COMMITTED, design.LANE_AUTHORED):
        own = [r for r in rows if r["lane"] == lane]
        assert [r["setting_id"] for r in own] == ["baseline"]
        assert own[0]["block"] != design.BLOCK_COMPARATIVE


def test_roster_needs_every_bundle_file():
    listing = {
        f"data/platforms/full/{name}": "0" * 40 for name in design.HULL_FILES
    }
    listing["data/platforms/partial/contam/platform.prj"] = "0" * 40
    listing["data/platforms/partial/spatial_layout.json"] = "0" * 40
    listing["data/platforms/README.md"] = "0" * 40
    platforms, bundled = design.classify_roster(listing)
    assert platforms == ["full", "partial"]
    assert bundled == ["full"]


def test_canary_rule_is_deterministic():
    facts = {
        "a": {"zone_count": 5, "life_support_plenum": False},
        "b": {"zone_count": 50, "life_support_plenum": False},
        "c": {"zone_count": 20, "life_support_plenum": True},
        "d": {"zone_count": 20, "life_support_plenum": True},
        "destroyer_baseline": {"zone_count": 9, "life_support_plenum": False},
    }
    assert design.select_canary(facts) == ["a", "b", "c", "destroyer_baseline"]


def test_summary_counts_and_workload():
    matrix = design.plan_rows("h", _facts(_MIXED))
    coverage = [design.coverage_row("h", "t", _facts(_MIXED), matrix, True)]
    summary = design.summarize(matrix, coverage)
    executed = 2 * len(design.SETTINGS) + 2 - 7
    assert summary["rows_by_planned_status"] == {
        design.EXECUTE: executed, design.NONRESPONSE: 7,
    }
    work = summary["timing_workload"]
    assert work["cold_cell_executions_total"] == executed * 6
    assert work["cold_cell_executions_measured"] == executed * 5
    assert work["contamx_solver_invocations"] == (len(design.SETTINGS) + 2) * 6
    assert work["rows_not_timed"] == 7


# ── committed artifacts (offline) ─────────────────────────────────────────

@pytest.fixture(scope="module")
def committed():
    return design.read_committed()


def test_committed_artifacts_pass_offline_checks(committed):
    design.check_artifacts(committed)


def test_committed_totals(committed):
    summary = json.loads(committed["dry_run_summary.json"])
    assert summary["platforms_at_pin"] == 82
    assert summary["hulls_in_scope"] == 77
    assert summary["rows_total"] == 77 * 28
    assert sum(summary["rows_by_planned_status"].values()) == 77 * 28
    assert summary["platforms_excluded"] == [
        "expedition_cruise_300", "fletcher_class_destroyer",
        "legend_class_nsc", "messy_cruise_500", "san_antonio_class_lpd",
    ]


def test_committed_manifest_hashes_five_files_per_hull(committed):
    manifest = json.loads(committed["input_manifest.json"])
    assert manifest["input_commit"] == design.INPUT_PIN
    assert len(manifest["hulls"]) == 77
    for hull, entry in manifest["hulls"].items():
        names = [f["path"].split(f"/{hull}/", 1)[1] for f in entry["files"]]
        assert tuple(names) == design.HULL_FILES
        assert all(len(f["sha256"]) == 64 for f in entry["files"])


def test_tampered_matrix_is_rejected(committed):
    broken = dict(committed)
    broken["run_matrix.csv"] = committed["run_matrix.csv"].replace(
        b"planned_execute", b"not_applicable", 1,
    )
    with pytest.raises(design.DesignError):
        design.check_artifacts(broken)


def test_duplicate_row_is_rejected(committed):
    rows = list(csv.DictReader(io.StringIO(
        committed["run_matrix.csv"].decode(),
    )))
    summary = json.loads(committed["dry_run_summary.json"])
    with pytest.raises(design.DesignError):
        design.check_matrix(rows + rows[:1], summary)


def test_matrix_carries_no_zone_or_path_identifier(committed):
    header = committed["run_matrix.csv"].split(b"\n", 1)[0].decode()
    assert header.split(",") == list(design.MATRIX_COLUMNS)
    assert not {"zone", "path", "room", "deck"} & set(header.split(","))


def test_regeneration_from_pin_is_byte_identical():
    try:
        design._rev(f"{design.INPUT_PIN}^{{commit}}")
    except design.DesignError:
        pytest.skip("input pin not present in this clone")
    design.verify_against_pin()


# ── end to end on a small fixture repository ──────────────────────────────

def _commit_fixture_repo(root):
    import subprocess

    def put(rel, payload):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        text = payload if isinstance(payload, str) else json.dumps(payload)
        path.write_text(text, encoding="utf-8")

    spatial = {"zones": [{"id": "A"}, {"id": "B"}]}
    for hull, overrides in (
        ("alpha", {}),
        ("sealed", {"life_support_plenum": True,
                    "relative_wind_speed_m_s": 0.0}),
    ):
        base = f"data/platforms/{hull}"
        put(f"{base}/spatial_layout.json", spatial)
        put(f"{base}/air_flow_paths.json", _airflow(_MIXED))
        put(f"{base}/contam/hobbyist_overrides.json", overrides)
        put(f"{base}/contam/platform.prj", "ContamW 3.4\n")
        put(f"{base}/contam/path_map.json", [])
    put("data/platforms/legacy/spatial_layout.json", spatial)
    put("data/platforms/README.md", "roster\n")
    put("data/contam_hobbyist/schedule_templates.json",
        {"defaults": {"oa_fraction": 0.2}})
    put("tool.py", "pass\n")
    env = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    for args in (["init", "-q"], ["add", "-A"],
                 [*env, "commit", "-q", "-m", "fixture"]):
        subprocess.run(["git", *args], cwd=root, check=True)
    done = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True,
    )
    return done.stdout.strip()


@pytest.fixture
def fixture_repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    pin = _commit_fixture_repo(root)
    monkeypatch.setattr(design, "REPO_ROOT", str(root))
    monkeypatch.setattr(design, "INPUT_PIN", pin)
    monkeypatch.setattr(design, "EXPECTED_PLATFORMS", 3)
    monkeypatch.setattr(design, "EXPECTED_BUNDLES", 2)
    monkeypatch.setattr(design, "TOOL_PATH_FILES", ("tool.py",))
    return root


def test_fixture_repo_write_then_verify(fixture_repo, capsys):
    assert design.main(["--write"]) == 0
    assert design.main(["--verify-only"]) == 0
    assert design.main(["--check-artifacts"]) == 0
    capsys.readouterr()
    assert design.main(["--dry-run"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["platforms_excluded"] == ["legacy"]
    assert summary["rows_total"] == 2 * (2 * len(design.SETTINGS) + 2)
    assert summary["rows_by_planned_status"][design.NOT_APPLICABLE] == 14


def test_fixture_repo_reads_the_pin_not_the_working_tree(fixture_repo):
    before = design.build()
    edited = fixture_repo / "data/platforms/alpha/air_flow_paths.json"
    edited.write_text("{}", encoding="utf-8")
    assert design.build() == before


def test_fixture_repo_manifest_matches_file_bytes(fixture_repo):
    import hashlib

    manifest = json.loads(design.build()["input_manifest.json"])
    entry = manifest["hulls"]["alpha"]["files"][0]
    data = (fixture_repo / entry["path"]).read_bytes()
    assert entry["sha256"] == hashlib.sha256(data).hexdigest()
    assert entry["size_bytes"] == len(data)
    assert manifest["tool_path_at_input_pin"][0]["path"] == "tool.py"


def test_stale_committed_artifact_fails_verify(fixture_repo, capsys):
    assert design.main(["--write"]) == 0
    stale = fixture_repo / design.OUT_REL / "coverage.csv"
    stale.write_text(stale.read_text() + "x\n", encoding="utf-8")
    assert design.main(["--verify-only"]) == 1
    assert "coverage.csv" in capsys.readouterr().err


def test_roster_mismatch_stops_the_build(fixture_repo, monkeypatch):
    monkeypatch.setattr(design, "EXPECTED_BUNDLES", 3)
    with pytest.raises(design.DesignError, match="roster does not reconcile"):
        design.build()


def test_unknown_pin_is_reported(fixture_repo, monkeypatch, capsys):
    monkeypatch.setattr(design, "INPUT_PIN", "0" * 40)
    assert design.main(["--dry-run"]) == 1
    assert "FAIL" in capsys.readouterr().err


def test_empty_pin_is_rejected_not_defaulted(fixture_repo):
    with pytest.raises(design.DesignError):
        design.build("")
