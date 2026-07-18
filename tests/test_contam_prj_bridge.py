"""
test_contam_prj_bridge.py – CONTAM geometry + .prj interoperability tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Covers:
- New optional zone geometry fields in schemas/spatial_layout.schema.json
  (floor_area_m2, ceiling_height_m, elevation_m).
- Volume-derivation logic in derive_volume_m3 / ContamZoneNode /
  ContamTransportEngine._build_zone_nodes.
- CONTAM .prj export -> import round-trip preserving zone volumes and the
  full airflow connectivity graph.
- sanity_checker geometry consistency warning.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.py_contam_bridge import (
    ContamTransportEngine,
    ContamZoneNode,
    derive_volume_m3,
)
from tools import contam_prj_bridge
from tools.sanity_checker import (
    Report,
    SpatialLayout,
    _check_zone_geometry,
)

_SPATIAL_SCHEMA = REPO_ROOT / "schemas" / "spatial_layout.schema.json"


def _load_spatial_schema() -> dict:
    with open(_SPATIAL_SCHEMA, encoding="utf-8") as fh:
        return json.load(fh)


def _base_zone(**overrides) -> dict:
    zone = {
        "id": "Z1",
        "type": "Free",
        "traffic": "low",
        "volume_m3": 100.0,
        "display": {"x": 1, "y": 2},
    }
    zone.update(overrides)
    return zone


# ── Schema field tests ──────────────────────────────────────────────────

@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
class TestSchemaGeometryFields:
    def test_new_fields_accepted(self) -> None:
        schema = _load_spatial_schema()
        doc = {
            "platform": "t",
            "zones": [
                _base_zone(
                    volume_m3=60.0, floor_area_m2=20.0,
                    ceiling_height_m=3.0, elevation_m=5.5,
                ),
            ],
        }
        jsonschema.validate(doc, schema)  # should not raise

    def test_fields_are_optional(self) -> None:
        """A zone with only volume_m3 (no new fields) still validates."""
        schema = _load_spatial_schema()
        doc = {"platform": "t", "zones": [_base_zone()]}
        jsonschema.validate(doc, schema)

    def test_negative_elevation_allowed(self) -> None:
        schema = _load_spatial_schema()
        doc = {"platform": "t", "zones": [_base_zone(elevation_m=-4.0)]}
        jsonschema.validate(doc, schema)

    @pytest.mark.parametrize("field", ["floor_area_m2", "ceiling_height_m"])
    def test_nonpositive_area_height_rejected(self, field: str) -> None:
        """Law 3: floor_area_m2 / ceiling_height_m must be > 0."""
        schema = _load_spatial_schema()
        doc = {"platform": "t", "zones": [_base_zone(**{field: 0})]}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, schema)


# ── Volume derivation tests ──────────────────────────────────────────────

class TestVolumeDerivation:
    def test_explicit_volume_wins(self) -> None:
        # Golden: explicit volume is returned even if area*height differs.
        assert derive_volume_m3(150.0, 20.0, 3.0) == pytest.approx(150.0)

    def test_derives_from_area_times_height(self) -> None:
        # Golden: 20 m2 * 3 m = 60 m3.
        assert derive_volume_m3(None, 20.0, 3.0) == pytest.approx(60.0)

    def test_falls_back_to_default(self) -> None:
        assert derive_volume_m3(None, None, None, default=100.0) == pytest.approx(100.0)
        assert derive_volume_m3(None, 20.0, None) == pytest.approx(100.0)

    def test_zone_node_stores_geometry(self) -> None:
        node = ContamZoneNode(
            "z", volume_m3=60.0, floor_area_m2=20.0,
            ceiling_height_m=3.0, elevation_m=5.0,
        )
        assert node.floor_area_m2 == pytest.approx(20.0)
        assert node.ceiling_height_m == pytest.approx(3.0)
        assert node.elevation_m == pytest.approx(5.0)

    def test_build_zone_nodes_derives_volume(self) -> None:
        layout = {
            "zones": [
                {"id": "A", "floor_area_m2": 25.0, "ceiling_height_m": 4.0},
                {"id": "B", "volume_m3": 42.0},
            ],
        }
        engine = ContamTransportEngine(layout, {"hvac_zones": [], "cross_zone_links": [], "adjacency": []})
        assert engine.zone_nodes["A"].volume_m3 == pytest.approx(100.0)  # 25*4
        assert engine.zone_nodes["A"].floor_area_m2 == pytest.approx(25.0)
        assert engine.zone_nodes["B"].volume_m3 == pytest.approx(42.0)
        assert engine.zone_nodes["B"].floor_area_m2 is None

    def test_backward_compat_volume_only(self) -> None:
        """Platforms specifying only volume_m3 are unchanged."""
        layout = {"zones": [{"id": "A", "volume_m3": 80.0}]}
        engine = ContamTransportEngine(layout, {"hvac_zones": [], "cross_zone_links": [], "adjacency": []})
        assert engine.zone_nodes["A"].volume_m3 == pytest.approx(80.0)


# ── .prj round-trip tests ─────────────────────────────────────────────────

def _destroyer_layout() -> tuple[dict, dict]:
    base = REPO_ROOT / "data" / "platforms" / "destroyer_baseline"
    with open(base / "spatial_layout.json", encoding="utf-8") as fh:
        spatial = json.load(fh)
    with open(base / "air_flow_paths.json", encoding="utf-8") as fh:
        airflow = json.load(fh)
    return spatial, airflow


class TestPrjRoundTrip:
    def test_zone_volumes_preserved(self) -> None:
        spatial, airflow = _destroyer_layout()
        prj = contam_prj_bridge.export_prj(spatial, airflow)
        r_spatial, _ = contam_prj_bridge.import_prj(prj)

        orig = {z["id"]: z["volume_m3"] for z in spatial["zones"]}
        got = {z["id"]: z["volume_m3"] for z in r_spatial["zones"]}
        assert orig.keys() == got.keys()
        for zid in orig:
            assert got[zid] == pytest.approx(orig[zid])

    def test_airflow_connectivity_preserved(self) -> None:
        spatial, airflow = _destroyer_layout()
        prj = contam_prj_bridge.export_prj(spatial, airflow)
        _, r_airflow = contam_prj_bridge.import_prj(prj)

        def _adj_pairs(d):
            return {(e["from"], e["to"]) for e in d["adjacency"]}

        def _hvac_rooms(d):
            return {(h["id"], frozenset(h["rooms"]), h["ach"]) for h in d["hvac_zones"]}

        assert _adj_pairs(r_airflow) == _adj_pairs(airflow)
        assert _hvac_rooms(r_airflow) == _hvac_rooms(airflow)
        # Cross-zone links resolve to representative rooms with same flows
        assert len(r_airflow["cross_zone_links"]) == len(airflow["cross_zone_links"])
        orig_flows = sorted(e["flow_rate_m3h"] for e in airflow["cross_zone_links"])
        got_flows = sorted(e["flow_rate_m3h"] for e in r_airflow["cross_zone_links"])
        assert got_flows == orig_flows

    def test_geometry_fields_round_trip(self) -> None:
        spatial = {
            "platform": "geo_test",
            "zones": [
                {
                    "id": "RoomA", "type": "Free", "traffic": "low",
                    "volume_m3": 60.0, "floor_area_m2": 20.0,
                    "ceiling_height_m": 3.0, "elevation_m": 2.5,
                    "deck": "main", "display": {"x": 10, "y": 20},
                },
            ],
        }
        airflow = {"platform": "geo_test", "hvac_zones": [], "cross_zone_links": [], "adjacency": []}
        prj = contam_prj_bridge.export_prj(spatial, airflow)
        r_spatial, _ = contam_prj_bridge.import_prj(prj)
        z = r_spatial["zones"][0]
        assert z["floor_area_m2"] == pytest.approx(20.0)
        assert z["ceiling_height_m"] == pytest.approx(3.0)
        assert z["volume_m3"] == pytest.approx(60.0)

    def test_volume_only_zone_gets_derived_geometry_on_contamw34(self) -> None:
        """ContamW 3.4 export derives area/height; simplify keeps them."""
        spatial, airflow = _destroyer_layout()
        prj = contam_prj_bridge.export_prj(spatial, airflow)
        r_spatial, _ = contam_prj_bridge.import_prj(prj)
        for z in r_spatial["zones"]:
            assert z.get("floor_area_m2", 0) > 0
            assert z.get("ceiling_height_m", 0) > 0

    def test_legacy_interchange_preserves_absent_geometry(self) -> None:
        spatial, airflow = _destroyer_layout()
        prj = contam_prj_bridge.export_prj_interchange(spatial, airflow)
        r_spatial, _ = contam_prj_bridge.import_prj(prj)
        for z in r_spatial["zones"]:
            assert "floor_area_m2" not in z
            assert "ceiling_height_m" not in z

    def test_exported_prj_has_contamw34_signature(self) -> None:
        spatial, airflow = _destroyer_layout()
        prj = contam_prj_bridge.export_prj(spatial, airflow)
        assert prj.splitlines()[0].startswith("ContamW 3.4")

    def test_import_rejects_non_prj(self) -> None:
        with pytest.raises(ValueError):
            contam_prj_bridge.import_prj("not a contam file\n")

    def test_file_round_trip(self, tmp_path) -> None:
        spatial, airflow = _destroyer_layout()
        prj = contam_prj_bridge.export_prj(spatial, airflow)
        prj_file = tmp_path / "ship.prj"
        prj_file.write_text(prj, encoding="utf-8")
        text = prj_file.read_text(encoding="utf-8")
        r_spatial, r_airflow = contam_prj_bridge.import_prj(text)
        assert len(r_spatial["zones"]) == len(spatial["zones"])
        assert len(r_airflow["adjacency"]) == len(airflow["adjacency"])

    def test_path_map_includes_cross_and_adjacency(self) -> None:
        spatial, airflow = _destroyer_layout()
        _prj, path_map = contam_prj_bridge.export_prj_with_path_map(spatial, airflow)
        kinds = {e["kind"] for e in path_map}
        assert any(e["crusher_transfer"] for e in path_map)
        assert "cross_zone" in kinds or any(
            e["kind"] not in ("ahs_oa", "ahs_exhaust", "ahs_recirc", "ahs_supply", "ahs_return")
            and e["crusher_transfer"]
            for e in path_map
        )
        transfer = [e for e in path_map if e["crusher_transfer"]]
        assert len(transfer) >= len(airflow["adjacency"]) + len(airflow["cross_zone_links"])


# ── sanity_checker geometry check ─────────────────────────────────────────

class TestGeometryConsistencyCheck:
    def _layout(self, **zone_over) -> SpatialLayout:
        return SpatialLayout.model_validate({
            "platform": "t",
            "zones": [_base_zone(**zone_over)],
        })

    def test_consistent_geometry_no_warning(self) -> None:
        report = Report()
        _check_zone_geometry(
            self._layout(volume_m3=60.0, floor_area_m2=20.0, ceiling_height_m=3.0),
            report,
        )
        assert not report.warnings

    def test_mismatch_warns(self) -> None:
        report = Report()
        # 20*3 = 60, but volume says 999 -> should warn.
        _check_zone_geometry(
            self._layout(volume_m3=999.0, floor_area_m2=20.0, ceiling_height_m=3.0),
            report,
        )
        geo = [f for f in report.warnings if f.rule == "GEOMETRY"]
        assert len(geo) == 1

    def test_missing_geometry_no_warning(self) -> None:
        report = Report()
        _check_zone_geometry(self._layout(volume_m3=100.0), report)
        assert not report.warnings

    def test_within_tolerance_no_warning(self) -> None:
        report = Report()
        # 20*3 = 60; 60.3 is 0.5% off, under the 1% tolerance.
        _check_zone_geometry(
            self._layout(volume_m3=60.3, floor_area_m2=20.0, ceiling_height_m=3.0),
            report,
        )
        assert not report.warnings
