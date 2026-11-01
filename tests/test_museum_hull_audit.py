"""
test_museum_hull_audit.py – mechanical audit metrics for museum/GA hulls
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Offline tests for ``tools/museum_hull_audit.py`` against the committed
fixtures under ``tests/fixtures/museum_audit/``:

- ``toy_hull``: clean references; one duty-0 sanitary group (extract leg
  post-CONTAM-DUTY0-01),
  one cross-zone link the native engine drops (room-id endpoint), one
  void link, one volume-bearing zone referenced nowhere (orphan).
- ``toy_broken``: hvac/adjacency/cross-zone references to zones that do
  not exist, systems-notes and import-digest drift, and a committed
  ``contam/platform.prj`` encoding a different zone name + ACH than the
  JSON declares.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import museum_hull_audit as mha  # noqa: E402

FIXTURES = "tests/fixtures/museum_audit"
TOY = Path(FIXTURES) / "toy_hull"
BROKEN = Path(FIXTURES) / "toy_broken"


def _load(pid: str) -> tuple[dict, dict]:
    base = Path(FIXTURES) / pid
    spatial = json.loads((base / "spatial_layout.json").read_text())
    airflow = json.loads((base / "air_flow_paths.json").read_text())
    return spatial, airflow


# ── pure statistics ─────────────────────────────────────────────────────


class TestSpearman:
    def test_monotonic(self) -> None:
        assert mha.spearman([1.0, 2.0, 3.0, 4.0], [10.0, 20.0, 30.0, 40.0]) == pytest.approx(1.0)
        assert mha.spearman([1.0, 2.0, 3.0, 4.0], [40.0, 30.0, 20.0, 10.0]) == pytest.approx(-1.0)

    def test_flat_and_short(self) -> None:
        assert mha.spearman([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) == pytest.approx(0.0)
        assert mha.spearman([1.0, 2.0], [1.0, 2.0]) == pytest.approx(0.0)
        assert mha.spearman([1.0, 2.0, 3.0], [1.0, 2.0]) == pytest.approx(0.0)

    def test_tied_ranks(self) -> None:
        ranks = mha._ranks([5.0, 1.0, 5.0, 9.0])
        assert ranks == [2.5, 1.0, 2.5, 4.0]

    def test_pearson_degrees(self) -> None:
        assert mha._pearson([1.0], [2.0]) == pytest.approx(0.0)
        assert mha._pearson([1.0, 2.0], [2.0, 4.0]) == pytest.approx(1.0)


# ── divergence table parsing ────────────────────────────────────────────


def test_load_mean_l1() -> None:
    out = mha.load_mean_l1(f"{FIXTURES}/fleet_table.md")
    assert out == {"toy_hull": 100.0, "toy_broken": 900.0}


# ── Q1 reference/orphan checks ──────────────────────────────────────────


class TestQ1:
    def test_toy_hull_clean_refs(self) -> None:
        spatial, airflow = _load("toy_hull")
        q1 = mha.audit_q1(str(REPO_ROOT / TOY), spatial, airflow)
        assert q1["missing_zone_refs"] == []
        assert q1["hvac_groups_all_rooms_missing"] == []
        assert q1["dangling_xzone_endpoints"] == []
        assert q1["orphan_zones"] == ["ghost"]
        # void is a real room id — post-CONTAM-XZONE-01 the engine
        # resolves the link; the classifier lists it as the room-endpoint
        # class the fix targets.
        assert q1["room_id_xzone_endpoints"] == ["hv_main->void"]
        assert q1["provenance_absent"] is True
        assert q1["prj"] is None

    def test_toy_broken_hard_errors(self) -> None:
        spatial, airflow = _load("toy_broken")
        q1 = mha.audit_q1(str(REPO_ROOT / BROKEN), spatial, airflow)
        assert q1["missing_zone_refs"] == ["ghost_room", "gone", "nowhere"]
        assert q1["hvac_groups_all_rooms_missing"] == ["hv_empty"]
        assert q1["dangling_xzone_endpoints"] == ["hv_a->phantom_zone"]
        # phantom_zone is neither group nor room — not a room-id
        # endpoint, and the engine now raises on it.
        assert q1["room_id_xzone_endpoints"] == []
        assert q1["notes_only_zones"] == ["extra_notes_zone"]
        assert q1["unnoted_zones"] == ["aux", "cabin_b"]
        assert q1["zone_count_drift"] == 2
        assert q1["prj"]["prj_only_zones"] == ["aux_prj"]
        assert q1["prj"]["json_only_zones"] == ["aux"]
        assert q1["prj"]["n_prj_zones"] == 3
        assert q1["prj"]["volume_drift_zones"] == {}

    def test_orphan_requires_volume(self) -> None:
        spatial, airflow = _load("toy_hull")
        spatial["zones"][4]["volume_m3"] = 0.0  # ghost → zero volume
        assert mha._orphan_zones(spatial, airflow) == []

    def test_referenced_ids_and_link_resolution(self) -> None:
        _spatial, airflow = _load("toy_hull")
        refs = mha._referenced_zone_ids(airflow)
        assert refs == {"main", "cabin_a", "hd_head"}
        zone_ids = {"main", "cabin_a", "hd_head", "void"}
        assert mha._resolve_link_rooms("hv_main", airflow, zone_ids) == [
            "main", "cabin_a"]
        assert mha._resolve_link_rooms("void", airflow, zone_ids) == ["void"]
        assert mha._resolve_link_rooms("nope", airflow, zone_ids) == []


# ── Q2 zone-graph classes ───────────────────────────────────────────────


class TestZoneClasses:
    def test_classes(self) -> None:
        edges = [("a", "b"), ("b", "a"), ("c", "d"), ("e", "ambient")]
        out = mha._zone_classes({"a", "b", "c", "d", "e"}, edges, "a")
        assert out["sinks"] == ["d"]
        assert out["unreachable"] == ["c", "d", "e"]
        assert set(out["dead"]) == {"c", "d", "e"}

    def test_no_injection(self) -> None:
        out = mha._zone_classes({"a"}, [("a", "ambient")], None)
        assert out["unreachable"] == []
        assert out["dead"] == []

    def test_contamx_edges(self) -> None:
        entries = [
            {"from_zone": "a", "to_zone": "b", "is_hvac_ducted": False,
             "crusher_transfer": True},
            {"from_zone": "b", "to_zone": "phantom", "is_hvac_ducted": True,
             "crusher_transfer": True},
            {"from_zone": "c", "to_zone": "phantom", "is_hvac_ducted": True,
             "crusher_transfer": True, "declared_flow_m3h": 0.0},
        ]
        edges = mha._contamx_edges(entries, {"a", "b", "c"})
        assert ("a", "b") in edges  # passive orifice …
        assert ("b", "a") in edges  # … is bidirectional
        assert ("b", "phantom") in edges
        assert ("phantom", "b") not in edges
        assert ("c", "phantom") not in edges  # zero-flow terminal dropped

    def test_reachable(self) -> None:
        assert mha._reachable([("a", "b"), ("b", "c")], "a") == {"a", "b", "c"}

    def test_toy_hull_dead_end_topology(self) -> None:
        spatial, airflow = _load("toy_hull")
        q2 = mha.audit_q2(str(REPO_ROOT / TOY), spatial, airflow)
        assert q2["injection_zone"] == "main"
        # Native post-CONTAM-XZONE-01: void is a room-id endpoint — its
        # deck_leak link resolves, making void a REACHABLE sink (one-way
        # in-link, no out leg: the residual class fix #4 targets). The
        # duty-0 head exfils through its exhaust leg (no sink, DUTY0-01);
        # ghost stays isolated.
        assert q2["native"]["sinks"] == ["void"]
        assert q2["native"]["orphans"] == ["ghost"]
        assert q2["native"]["unreachable"] == ["ghost"]
        assert q2["native"]["dead"] == ["ghost", "void"]
        assert q2["native"]["dead_frac"] == pytest.approx(0.4)
        # ContamX: orifice links are bidirectional — only ghost stays dead.
        assert q2["contamx_export"]["dead"] == ["ghost"]
        assert q2["contamx_export"]["dead_frac"] == pytest.approx(0.2)
        assert q2["native_only_dead"] == ["void"]
        assert q2["contamx_committed"] is None
        assert q2["duty0_rooms"] == ["hd_head"]
        assert q2["native_dead_volume_share"] == pytest.approx(45.0 / 205.0)

    def test_toy_broken_committed_prj_drift(self) -> None:
        spatial, airflow = _load("toy_broken")
        q2 = mha.audit_q2(str(REPO_ROOT / BROKEN), spatial, airflow)
        assert q2["injection_zone"] == "main"
        # phantom_zone resolves to neither group nor room — the engine
        # raises (CONTAM-XZONE-01 fail-loudly); the audit reports it
        # rather than crashing.
        assert q2["native"] is None
        assert "phantom_zone" in q2["native_error"]
        # aux is unreachable in every lane; in the committed prj its
        # drifted name (aux_prj) leaves the JSON zone an orphan.
        assert q2["contamx_export"]["dead"] == ["aux"]
        assert q2["contamx_committed"]["orphans"] == ["aux"]


# ── Q3 declaration coverage ─────────────────────────────────────────────


class TestQ3:
    def test_toy_hull(self) -> None:
        _spatial, airflow = _load("toy_hull")
        q3 = mha.audit_q3(str(REPO_ROOT / TOY), airflow)
        assert q3["top_hvac_duty"] == pytest.approx(0.5)
        assert q3["duty_values"] == pytest.approx([0.0, 0.5])
        assert q3["n_duty0_groups"] == 1
        assert q3["ach_values"] == pytest.approx([8.0, 12.0])
        assert q3["oa_group_coverage"] == pytest.approx(1.0)
        assert q3["filter_declared_groups"] == 0
        assert q3["nbc_groups"] == 0
        assert q3["prj_ach_annotations"] is None

    def test_toy_broken(self) -> None:
        _spatial, airflow = _load("toy_broken")
        q3 = mha.audit_q3(str(REPO_ROOT / BROKEN), airflow)
        assert q3["top_hvac_duty"] is None
        assert q3["duty_values"] == [0.0, 1.0]
        assert q3["oa_group_coverage"] == pytest.approx(1.0 / 3.0)
        assert q3["filter_declared_groups"] == 1
        assert q3["nbc_groups"] == 1
        assert q3["prj_ach_annotations"] == {"hv_a": 9.0, "hv_aux": 6.0}
        assert q3["prj_ach_mismatch"] == [
            {"group": "hv_a", "json_ach": 6.0, "prj_ach": 9.0}]
        assert q3["prj_ahs_missing_groups"] == ["hv_empty"]
        assert q3["prj_ahs_unknown_groups"] == []


# ── whole-platform audit + correlation ──────────────────────────────────


def test_audit_platform() -> None:
    r = mha.audit_platform("toy_broken", root=FIXTURES)
    assert r["platform"] == "toy_broken"
    assert r["ga_imported"] is True
    assert r["has_prj"] is True
    assert r["n_zones"] == 3
    assert r["total_volume_m3"] == pytest.approx(180.0)
    assert r["q1"]["missing_zone_refs"]
    assert r["q2"]["n_zones"] == 3
    assert r["q3"]["n_groups"] == 3


def test_fleet_correlations() -> None:
    def _q2(dead_frac: float) -> dict:
        return {
            "n_zones": 10,
            "native": {"dead_frac": dead_frac, "sinks": ["x"],
                       "unreachable": ["x"]},
            "contamx_export": {"dead_frac": dead_frac / 2},
            "contamx_committed": {"dead_frac": dead_frac / 2},
            "native_dead_volume_share": dead_frac,
            "native_only_dead_frac": dead_frac,
            "duty0_rooms": [],
        }

    results = {
        f"p{i}": {"q2": _q2(frac)} for i, frac in
        enumerate([0.1, 0.2, 0.4, 0.8], start=1)
    }
    mean_l1 = {f"p{i}": v for i, v in enumerate([10.0, 20.0, 40.0, 80.0], 1)}
    corr = mha.fleet_correlations(results, mean_l1)
    assert corr["n_hulls"] == 4
    assert corr["vs_mean_l1"]["native_dead_frac"] == pytest.approx(1.0)
    assert corr["vs_mean_l1"]["contamx_dead_frac"] == pytest.approx(1.0)


def test_write_table(tmp_path: Path) -> None:
    results = {
        pid: mha.audit_platform(pid, root=FIXTURES)
        for pid in ("toy_hull", "toy_broken")
    }
    out = REPO_ROOT / "telemetry_buffer" / "test_museum_audit" / "table.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    mha.write_table(results, {"toy_hull": 100.0, "toy_broken": 900.0},
                    str(out))
    text = out.read_text(encoding="utf-8")
    assert "| platform | zones | L1 |" in text
    assert "| toy_hull | 5 | 100.0 |" in text
    assert "| toy_broken | 3 | 900.0 |" in text


def test_main_fixtures() -> None:
    rc = mha.main([
        "--platforms", "toy_hull", "toy_broken",
        "--platforms-root", FIXTURES,
        "--divergence-table", f"{FIXTURES}/fleet_table.md",
        "--committed-dose", f"{FIXTURES}/dose.json",
        "--out", "telemetry_buffer/test_museum_audit",
        "--md-out", "telemetry_buffer/test_museum_audit/table.md",
    ])
    assert rc == 0
    report = json.loads(
        (REPO_ROOT / "telemetry_buffer" / "test_museum_audit"
         / "museum_hull_audit_latest.json").read_text())
    # Post-CONTAM-XZONE-01: the room-endpoint link resolves, so void is a
    # reachable one-way sink; toy_broken's phantom endpoint makes its
    # native lane unbuildable (reported, not fatal).
    assert report["hulls"]["toy_hull"]["q2"]["native"]["sinks"] == ["void"]
    assert report["hulls"]["toy_broken"]["q2"]["native"] is None
    assert "phantom_zone" in \
        report["hulls"]["toy_broken"]["q2"]["native_error"]
    assert report["correlations"]["n_hulls"] == 2
    assert "vs_committed_dose_l1" in report["correlations"]


def test_main_missing_platform() -> None:
    rc = mha.main([
        "--platforms", "not_a_real_platform",
        "--platforms-root", FIXTURES,
    ])
    assert rc == 0
